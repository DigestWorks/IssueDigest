import { afterEach, expect, it, vi } from 'vitest';
import * as client from '../src/index';

const workspace = '00000000-0000-4000-8000-000000000001';
const other = '00000000-0000-4000-8000-000000000002';
const requestId = '8ff9af27-d021-4fb3-a46e-cf8c3d093c44';
const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': requestId };
const session = () => ({ schema_version: 1, user_id: other, memberships: [{ workspace_id: workspace, role: 'viewer' }] });
const response = (data: unknown) => new Response(JSON.stringify(data), { headers });
const uniqueId = (index: number) => `00000000-0000-4000-8000-${index.toString(16).padStart(12, '0')}`;
const memberships = (count: number) => Array.from({ length: count }, (_, index) => ({ workspace_id: uniqueId(index + 1), role: 'viewer' }));
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('returns typed validated session using cookie-only no-store requests', async () => {
  const fetch = vi.fn(async () => response(session())); vi.stubGlobal('fetch', fetch);
  expect(await client.getSession()).toEqual({ data: session(), requestId });
  expect(fetch).toHaveBeenNthCalledWith(1, '/api/v1/auth/session', expect.objectContaining({ credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }, signal: expect.any(AbortSignal) }));
});
it('logs out by POST without client tokens or an invented Origin header', async () => {
  const fetch = vi.fn(async () => new Response(null, { status: 204, headers })); vi.stubGlobal('fetch', fetch);
  expect(await client.logout()).toEqual({ requestId });
  expect(fetch).toHaveBeenCalledWith('/api/v1/auth/logout', expect.objectContaining({ method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' } }));
});
const sessionCorruptions: [string, (data: ReturnType<typeof session>) => void][] = [
  ['schema', d => { d.schema_version = 2; }], ['user', d => { d.user_id = 'bad'; }], ['role', d => { d.memberships[0].role = 'admin'; }],
  ['duplicate workspace', d => { d.memberships.push(d.memberships[0]); }], ['sorting', d => { d.memberships.unshift({ workspace_id: other, role: 'owner' }); }],
  ['limit', d => { d.memberships = memberships(101); }], ['unknown field', d => { Object.assign(d, { token: 'private' }); }],
];
it.each(sessionCorruptions)('rejects malformed session: %s', async (_name, corrupt) => {
  const data = session(); corrupt(data); vi.stubGlobal('fetch', async () => response(data));
  await expect(client.getSession()).rejects.toMatchObject({ name: 'AuthError', kind: 'malformed', requestId });
});
it('accepts no memberships', async () => {
  vi.stubGlobal('fetch', async () => response({ ...session(), memberships: [] })); expect((await client.getSession()).data.memberships).toEqual([]);
});
it('accepts exactly 100 unique sorted memberships', async () => {
  const data = { ...session(), memberships: memberships(100) };
  vi.stubGlobal('fetch', async () => response(data));
  expect(await client.getSession()).toEqual({ data, requestId });
});
const calls = [() => client.getSession(), () => client.logout()];
it.each(calls)('sanitizes errors and preserves only valid request UUIDs (%#)', async call => {
  for (const [status, kind] of [[401, 'unauthorized'], [404, 'not-found'], [403, 'forbidden'], [503, 'unavailable']] as const) {
    vi.stubGlobal('fetch', async () => new Response('PRIVATE BODY', { status, headers }));
    await expect(call()).rejects.toMatchObject({ kind, requestId });
  }
  vi.stubGlobal('fetch', async () => new Response('PRIVATE BODY', { status: 503, headers: { 'X-Request-ID': 'PRIVATE ID' } }));
  await expect(call()).rejects.toMatchObject({ kind: 'unavailable', requestId: undefined });
  vi.stubGlobal('fetch', async () => { throw new Error('PRIVATE ERROR'); }); await expect(call()).rejects.toMatchObject({ kind: 'network' });
});
it.each(['Content-Type', 'Cache-Control', 'X-Request-ID'])('rejects malformed response header %s', async header => {
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify(session()), { headers: { ...headers, [header]: 'bad' } }));
  await expect(client.getSession()).rejects.toMatchObject({ kind: 'malformed' });
});
it('rejects broken JSON and unexpected logout success statuses', async () => {
  vi.stubGlobal('fetch', async () => new Response('{private', { headers })); await expect(client.getSession()).rejects.toMatchObject({ kind: 'malformed', requestId });
  vi.stubGlobal('fetch', async () => response(session())); await expect(client.logout()).rejects.toMatchObject({ kind: 'malformed', requestId });
});
it('rejects invalid client arguments before requests', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  for (const timeoutMs of [0, -1, 1.5, Infinity]) await expect(client.getSession({ timeoutMs })).rejects.toMatchObject({ kind: 'malformed' });
  expect(fetch).not.toHaveBeenCalled();
});
it.each(['headers', 'body'])('times out across %s with a late response ignored', async phase => {
  vi.useFakeTimers(); let resolve!: (value: Response) => void;
  const pending = new Promise<Response>(done => { resolve = done; });
  vi.stubGlobal('fetch', () => phase === 'headers' ? pending : { ok: true, status: 200, headers: new Headers(headers), json: () => new Promise(() => {}) });
  const result = client.getSession(); const assertion = expect(result).rejects.toMatchObject({ kind: 'timeout', requestId: phase === 'body' ? requestId : undefined });
  await vi.advanceTimersByTimeAsync(10_000); await assertion; resolve(response(session()));
});
it('cancels pending and pre-aborted requests without leaking late results', async () => {
  const controller = new AbortController(); const fetch = vi.fn(() => new Promise(() => {})); vi.stubGlobal('fetch', fetch);
  const result = client.getSession({ signal: controller.signal }); controller.abort(); await expect(result).rejects.toMatchObject({ kind: 'aborted' });
  await expect(client.getSession({ signal: controller.signal })).rejects.toMatchObject({ kind: 'aborted' }); expect(fetch).toHaveBeenCalledTimes(1);
});
