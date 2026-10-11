import { afterEach, describe, expect, it, vi } from 'vitest';
import { getStatus } from '../src/index';

const payload = { service: 'issuedigest-api', api_version: 'v1', status: 'ok' };
const requestId = '8ff9af27-d021-4fb3-a46e-cf8c3d093c44';
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId },
});
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

describe('versioned API status boundary', () => {
  it('uses the same-origin status path and returns validated status and request ID', async () => {
    vi.stubGlobal('fetch', async (url: string, options: RequestInit) => {
      expect(url).toBe('/api/v1/status');
      expect(options.signal).toBeInstanceOf(AbortSignal);
      return response(payload);
    });
    await expect(getStatus()).resolves.toEqual({ data: payload, requestId });
  });
  it('reports an HTTP failure with its server request ID', async () => {
    vi.stubGlobal('fetch', async () => response({ detail: 'Unavailable' }, 503));
    await expect(getStatus()).rejects.toMatchObject({ kind: 'http', requestId });
  });
  it.each([
    null, [], {}, { ...payload, api_version: 'v2' }, { ...payload, service: 'other' },
    { ...payload, status: 'down' }, { ...payload, unexpected: true }, { service: 'issuedigest-api', status: 'ok' },
  ].map((body) => ({ body })))('rejects an invalid status contract: %j', async ({ body }) => {
    vi.stubGlobal('fetch', async () => response(body));
    await expect(getStatus()).rejects.toMatchObject({ kind: 'invalid-response' });
  });
  it('rejects malformed JSON', async () => {
    vi.stubGlobal('fetch', async () => new Response('{', { headers: { 'X-Request-ID': requestId } }));
    await expect(getStatus()).rejects.toMatchObject({ kind: 'invalid-response' });
  });
  it.each([null, 'untrusted'])('rejects a missing or malformed request ID: %s', async (id) => {
    vi.stubGlobal('fetch', async () => new Response(JSON.stringify(payload), { headers: id ? { 'X-Request-ID': id } : {} }));
    await expect(getStatus()).rejects.toMatchObject({ kind: 'invalid-response' });
  });
  it('reports a network failure', async () => {
    vi.stubGlobal('fetch', async () => { throw new TypeError('offline'); });
    await expect(getStatus()).rejects.toMatchObject({ kind: 'network' });
  });
  it('aborts a slow request at the timeout', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', (_url: string, options: RequestInit) => new Promise((_resolve, reject) => {
      options.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    }));
    const result = getStatus({ timeoutMs: 50 }).then(() => ({ kind: 'unexpected-success' }), (error: unknown) => error);
    await vi.advanceTimersByTimeAsync(50);
    expect(await result).toMatchObject({ kind: 'timeout' });
  });
  it('preserves the server request ID when reading the response body times out', async () => {
    vi.useFakeTimers();
    vi.stubGlobal('fetch', async () => new Response(new ReadableStream({ start() { /* stalled body */ } }), { headers: { 'X-Request-ID': requestId } }));
    const result = getStatus({ timeoutMs: 50 }).then(() => ({ kind: 'unexpected-success' }), (error: unknown) => error);
    await vi.advanceTimersByTimeAsync(50);
    expect(await result).toMatchObject({ kind: 'timeout', requestId });
  });
});
