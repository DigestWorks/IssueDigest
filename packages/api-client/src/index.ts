import type { components, paths } from './schema';

export type ServiceStatus = components['schemas']['ServiceStatus'];
export type StatusResult = { data: ServiceStatus; requestId: string };
export type ConnectionFailure = 'http' | 'invalid-response' | 'network' | 'timeout';

export class ConnectionError extends Error {
  constructor(public readonly kind: ConnectionFailure, public readonly requestId?: string) {
    super(`API connection failed: ${kind}`);
    this.name = 'ConnectionError';
  }
}

const expectedStatus = { service: 'issuedigest-api', api_version: 'v1', status: 'ok' } satisfies ServiceStatus;
const statusPath = '/api/v1/status' satisfies keyof paths;
const uuid = /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;

function isStatus(value: unknown): value is ServiceStatus {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
  return Object.keys(value).length === Object.keys(expectedStatus).length
    && 'service' in value && value.service === expectedStatus.service
    && 'api_version' in value && value.api_version === expectedStatus.api_version
    && 'status' in value && value.status === expectedStatus.status;
}

/** Same-origin HTTP boundary. The deadline covers headers AND JSON body reading. */
export async function getStatus({ timeoutMs = 5000 }: { timeoutMs?: number } = {}): Promise<StatusResult> {
  const controller = new AbortController();
  let timer: ReturnType<typeof setTimeout> | undefined;
  let requestId: string | undefined;
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      controller.abort();
      reject(new ConnectionError('timeout', requestId));
    }, timeoutMs);
  });
  const request = async (): Promise<StatusResult> => {
    const response = await fetch(statusPath, {
      signal: controller.signal, credentials: 'same-origin', headers: { Accept: 'application/json' },
    });
    const header = response.headers.get('X-Request-ID');
    requestId = header && uuid.test(header) ? header : undefined;
    if (!response.ok) throw new ConnectionError('http', requestId);
    if (!requestId) throw new ConnectionError('invalid-response');
    let data: unknown;
    try { data = await response.json(); }
    catch { throw new ConnectionError('invalid-response', requestId); }
    if (!isStatus(data)) throw new ConnectionError('invalid-response', requestId);
    return { data, requestId };
  };
  try {
    return await Promise.race([request(), deadline]);
  } catch (error) {
    if (error instanceof ConnectionError) throw error;
    throw new ConnectionError(controller.signal.aborted ? 'timeout' : 'network', requestId);
  } finally {
    clearTimeout(timer);
  }
}
