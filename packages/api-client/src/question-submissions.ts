import type { components } from './schema';
import {
  hasKeys,
  isId,
  isObject,
  protectedRequest,
  type ProtectedFailure,
  type ProtectedOptions,
} from './protected-request';
export type QuestionRequest =
  components['schemas']['QuestionSubmissionRequest'];
export type QuestionResult = components['schemas']['QuestionSubmissionResult'];
export type BriefingJobList = components['schemas']['BriefingJobList'];
export class QuestionError extends Error {
  constructor(
    public readonly kind: ProtectedFailure,
    public readonly requestId?: string,
  ) {
    super('질문을 처리하지 못했습니다.');
    this.name = 'QuestionError';
  }
}
const exact = (v: unknown, keys: string[]): v is Record<string, unknown> =>
  isObject(v) && hasKeys(v, keys);
const question = (v: unknown): v is string =>
  typeof v === 'string' && v.trim().length > 0 && Array.from(v).length <= 1500;
const statuses = [
  'pending',
  'running',
  'completed',
  'failed',
  'cancelled',
  'indeterminate',
];
export function listBriefingJobs(
  workspace: string,
  options: ProtectedOptions = {},
) {
  if (!isId(workspace))
    return Promise.reject(new QuestionError('invalid-query'));
  return protectedRequest(
    `/api/v1/workspaces/${workspace}/briefing-jobs`,
    'GET',
    (v): v is BriefingJobList =>
      exact(v, ['items']) &&
      Array.isArray(v.items) &&
      v.items.length <= 50 &&
      v.items.every(
        (item) =>
          exact(item, ['job_id', 'question', 'status']) &&
          isId(item.job_id) &&
          question(item.question) &&
          typeof item.status === 'string' &&
          statuses.includes(item.status),
      ),
    (kind, id) => new QuestionError(kind, id),
    options,
  );
}
/** Bounded, single-attempt streaming transport. A terminal is accepted only after EOF. */
export async function submitQuestion(
  workspace: string,
  input: QuestionRequest,
  options: { signal?: AbortSignal; onProgress?: () => void } = {},
): Promise<{ data: QuestionResult; requestId: string }> {
  if (
    !isId(workspace) ||
    !exact(input, ['request_id', 'question']) ||
    !isId(input.request_id) ||
    !question(input.question)
  )
    throw new QuestionError('invalid-query');
  if (options.signal?.aborted) throw new QuestionError('aborted');
  const controller = new AbortController();
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  let trace: string | undefined;
  let idle: ReturnType<typeof setTimeout> | undefined;
  let active = true;
  const fail = (kind: ProtectedFailure) => new QuestionError(kind, trace);
  let rejectInterrupt: (e: Error) => void = () => {};
  const interruption = new Promise<never>((_, reject) => {
    rejectInterrupt = reject;
  });
  const interrupt = (kind: ProtectedFailure) => {
    if (!active) return;
    rejectInterrupt(fail(kind));
    controller.abort();
    void reader?.cancel().catch(() => {});
  };
  const abort = () => interrupt('aborted');
  const touch = () => {
    clearTimeout(idle);
    idle = setTimeout(() => interrupt('timeout'), 20_000);
  };
  options.signal?.addEventListener('abort', abort, { once: true });
  touch();
  const total = setTimeout(() => interrupt('timeout'), 620_000);
  const run = async () => {
    const response = await fetch(
      `/api/v1/workspaces/${workspace}/question-briefings`,
      {
        method: 'POST',
        credentials: 'same-origin',
        cache: 'no-store',
        signal: controller.signal,
        headers: {
          Accept: 'text/event-stream',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(input),
      },
    ).catch(() => {
      throw fail('network');
    });
    if (!active) {
      void response.body?.cancel().catch(() => {});
      throw fail('aborted');
    }
    const header = response.headers.get('X-Request-ID');
    trace = isId(header) ? header : undefined;
    if (!response.ok)
      throw fail(
        response.status === 401
          ? 'unauthorized'
          : response.status === 403
            ? 'forbidden'
            : response.status === 404
              ? 'not-found'
              : response.status === 409
                ? 'conflict'
                : response.status === 429
                  ? 'budget'
                  : 'unavailable',
      );
    if (
      !trace ||
      !response.headers
        .get('Cache-Control')
        ?.split(',')
        .some((x) => x.trim().toLowerCase() === 'no-store') ||
      !/^text\/event-stream(?:\s*;\s*charset=utf-8)?$/i.test(
        response.headers.get('Content-Type') ?? '',
      ) ||
      response.headers.get('X-Accel-Buffering') !== 'no' ||
      !response.body
    )
      throw fail('malformed');
    reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8', { fatal: true });
    let bytes = 0,
      buffer = '',
      event = '',
      data: string[] = [];
    let eventBytes = 0;
    let terminal: QuestionResult | undefined;
    let terminalError: ProtectedFailure | undefined;
    let progressed = false;
    const line = (value: string, rawBytes: number) => {
      eventBytes += rawBytes;
      if (eventBytes > 8192) throw fail('malformed');
      if (value === '') {
        if (!event && !data.length) {
          eventBytes = 0;
          return;
        }
        if (terminal || terminalError) throw fail('malformed');
        let value: unknown;
        try {
          value = JSON.parse(data.join('\n'));
        } catch {
          throw fail('malformed');
        }
        if (!isObject(value) || value.request_id !== input.request_id)
          throw fail('malformed');
        if (
          event === 'progress' &&
          exact(value, ['request_id', 'stage']) &&
          value.stage === 'analysing' &&
          !progressed
        ) {
          progressed = true;
          if (active) options.onProgress?.();
        } else if (
          event === 'result' &&
          exact(value, ['request_id', 'kind', 'job_id']) &&
          ((value.kind === 'briefing' && isId(value.job_id)) ||
            (typeof value.kind === 'string' &&
              ['no_match', 'blocked'].includes(value.kind) &&
              value.job_id === null))
        )
          terminal = value as QuestionResult;
        else if (
          event === 'error' &&
          exact(value, ['request_id', 'kind']) &&
          typeof value.kind === 'string' &&
          [
            'unauthorized',
            'forbidden',
            'conflict',
            'budget',
            'unavailable',
          ].includes(value.kind)
        )
          terminalError = value.kind as ProtectedFailure;
        else throw fail('malformed');
        touch();
        event = '';
        data = [];
        eventBytes = 0;
        return;
      }
      if (value.startsWith(':')) {
        touch();
        return;
      }
      if (terminal || terminalError) throw fail('malformed');
      const colon = value.indexOf(':');
      const field = colon < 0 ? value : value.slice(0, colon);
      let content = colon < 0 ? '' : value.slice(colon + 1);
      if (content.startsWith(' ')) content = content.slice(1);
      if (field === 'event' && !event) event = content;
      else if (field === 'data') data.push(content);
      else throw fail('malformed');
    };
    while (active) {
      const chunk = await reader.read();
      if (chunk.done) {
        buffer += decoder.decode();
        break;
      }
      bytes += chunk.value.byteLength;
      if (bytes > 131072) throw fail('malformed');
      buffer += decoder.decode(chunk.value, { stream: true });
      let end: number;
      while ((end = buffer.indexOf('\n')) >= 0) {
        let current = buffer.slice(0, end);
        const rawBytes = new TextEncoder().encode(current).length + 1;
        buffer = buffer.slice(end + 1);
        if (current.endsWith('\r')) current = current.slice(0, -1);
        if (current.includes('\r')) throw fail('malformed');
        line(current, rawBytes);
      }
      if (new TextEncoder().encode(buffer).length + eventBytes > 8192)
        throw fail('malformed');
    }
    if (buffer || event || data.length || (!terminal && !terminalError))
      throw fail('malformed');
    if (terminalError) throw fail(terminalError);
    return { data: terminal!, requestId: trace };
  };
  try {
    return await Promise.race([run(), interruption]);
  } catch (error) {
    if (error instanceof QuestionError) throw error;
    throw fail('malformed');
  } finally {
    active = false;
    clearTimeout(idle);
    clearTimeout(total);
    options.signal?.removeEventListener('abort', abort);
    controller.abort();
    await reader?.cancel().catch(() => {});
    reader?.releaseLock();
  }
}
