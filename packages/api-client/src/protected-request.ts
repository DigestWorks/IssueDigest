/** Private transport shared by the session and catalog boundaries. */
export type ProtectedFailure = 'timeout' | 'aborted' | 'unauthorized' | 'not-found' | 'unavailable' | 'malformed' | 'network';
export type ProtectedOptions = { timeoutMs?: number; signal?: AbortSignal };
export const isId = (value: unknown): value is string => typeof value === 'string' && /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i.test(value);
export const isObject = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value);
export const hasKeys = (value: Record<string, unknown>, keys: string[]) => Object.keys(value).length === keys.length && keys.every(key => key in value);

export async function protectedRequest<T>(path: string, method: 'GET' | 'POST', validate: (data: unknown) => data is T, error: (kind: ProtectedFailure, requestId?: string) => Error, { timeoutMs = 10_000, signal }: ProtectedOptions = {}): Promise<{ data: T; requestId: string }> {
  if (!Number.isSafeInteger(timeoutMs) || timeoutMs <= 0) throw error('malformed');
  if (signal?.aborted) throw error('aborted');
  const controller = new AbortController();
  let requestId: string | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let cancel!: () => void;
  const interruption = new Promise<never>((_resolve, reject) => {
    cancel = () => { reject(error('aborted', requestId)); controller.abort(); };
    signal?.addEventListener('abort', cancel, { once: true });
    const schedule = (remaining: number) => {
      const duration = Math.min(remaining, 2_147_483_647);
      timer = setTimeout(() => {
        if (remaining > duration) schedule(remaining - duration);
        else { reject(error('timeout', requestId)); controller.abort(); }
      }, duration);
    };
    schedule(timeoutMs);
  });
  const request = async () => {
    let response: Response;
    try { response = await fetch(path, { method, credentials: 'same-origin', cache: 'no-store', signal: controller.signal, headers: { Accept: 'application/json' } }); }
    catch { throw error('network', requestId); }
    const header = response.headers.get('X-Request-ID'); requestId = isId(header) ? header : undefined;
    if (!response.ok) throw error(response.status === 401 ? 'unauthorized' : response.status === 404 ? 'not-found' : 'unavailable', requestId);
    const noStore = response.headers.get('Cache-Control')?.split(',').some(token => token.trim().toLowerCase() === 'no-store');
    if (!requestId || !noStore) throw error('malformed', requestId);
    let data: unknown;
    if (method === 'POST') {
      if (response.status !== 204) throw error('malformed', requestId);
      data = undefined;
    } else {
      const mediaType = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
      if (!mediaType || !/^application\/(json|[a-z0-9!#$&^_.+-]+\+json)$/.test(mediaType)) throw error('malformed', requestId);
      try { data = await response.json(); } catch { throw error('malformed', requestId); }
    }
    if (!validate(data)) throw error('malformed', requestId);
    return { data, requestId };
  };
  try { return await Promise.race([request(), interruption]); }
  finally { clearTimeout(timer); signal?.removeEventListener('abort', cancel); }
}
