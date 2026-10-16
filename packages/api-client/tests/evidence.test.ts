import { createHash } from 'node:crypto';
import { afterEach, expect, it, vi } from 'vitest';
import * as client from '../src/index';
import canvas from '../../../tests/fixtures/canvas-synthetic.json';
import type { EvidenceBundle } from '../src/index';

const fixture = () => structuredClone(canvas.research.evidence[0]) as EvidenceBundle;
const workspace = '00000000-0000-4000-8000-000000000001';
const snapshot = '00000000-0000-4000-8000-000000000099';
const requestId = '8ff9af27-d021-4fb3-a46e-cf8c3d093c44';
const headers = { 'Content-Type': 'application/json; charset=utf-8', 'X-Request-ID': requestId, 'Cache-Control': 'no-store' };
const response = (body: unknown = fixture(), overrides: Record<string, string> = {}) => new Response(JSON.stringify(body), { headers: { ...headers, ...overrides } });
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('exports the protected saved-evidence client', () => {
  expect(client).toHaveProperty('getEvidence', expect.any(Function));
});
it('returns validated evidence through a same-origin no-store GET', async () => {
  const fetch = vi.fn(async () => response()); vi.stubGlobal('fetch', fetch);
  const result = await client.getEvidence(workspace, snapshot);
  expect(result).toEqual({ data: fixture(), requestId });
  expect(fetch).toHaveBeenCalledWith(`/api/v1/workspaces/${workspace}/evidence/${snapshot}`, expect.objectContaining({ credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }, signal: expect.any(AbortSignal) }));
});
it.each([['bad', snapshot, undefined], [workspace, 'bad', undefined], [workspace, snapshot, 0], [workspace, snapshot, 1.5], [workspace, snapshot, Infinity], [workspace, snapshot, -1]])('rejects invalid inputs before fetch (%s %s %s)', async (w, s, timeoutMs) => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(client.getEvidence(w, s, { timeoutMs })).rejects.toMatchObject({ kind: 'invalid-link' });
  expect(fetch).not.toHaveBeenCalled();
});
it.each([[401, 'authentication'], [404, 'not-found'], [503, 'unavailable'], [403, 'not-found'], [500, 'unavailable']])('sanitizes HTTP %s without disclosing body', async (status, kind) => {
  vi.stubGlobal('fetch', async () => new Response('PRIVATE DETAIL', { status: status as number, headers }));
  await expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind, requestId, message: `Evidence request failed: ${kind}` });
});
it.each(['Content-Type', 'X-Request-ID', 'Cache-Control'])('rejects malformed %s on 200', async (name) => {
  vi.stubGlobal('fetch', async () => response(fixture(), { [name]: 'invalid' }));
  await expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind: 'invalid-response' });
});
it('does not carry an invalid server request ID into an error', async () => {
  vi.stubGlobal('fetch', async () => new Response('secret', { status: 401, headers: { 'X-Request-ID': 'secret' } }));
  await expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind: 'authentication', requestId: undefined });
});
const corruptions: [string, (b: EvidenceBundle) => void][] = [
  ['schema version', b => { Object.assign(b, { schema_version: 2 }); }],
  ['missing version', b => { Reflect.deleteProperty(b, 'version'); }],
  ['cross workspace', b => { b.document.workspace_id = snapshot; }],
  ['version document chain', b => { b.version.document_id = snapshot; }],
  ['representation version chain', b => { b.representation.document_version_id = snapshot; }],
  ['citation version chain', b => { b.citations[0].document_version_id = snapshot; }],
  ['citation representation chain', b => { b.citations[0].representation_id = snapshot; }],
  ['duplicate citations', b => { b.citations.push(b.citations[0]); }],
  ['duplicate tables', b => { b.representation.tables.push(b.representation.tables[0]); }],
  ['duplicate cells', b => { b.representation.tables[0].cells.push(b.representation.tables[0].cells[0]); }],
  ['source kind type', b => { Object.assign(b.document, { source_kind: { toString: 42 } }); }],
  ['source URL empty credentials', b => { b.document.canonical_url = 'https://@example.com'; }],
  ['empty page span', b => { b.representation.pages[0].end = 0; b.citations = []; }],
  ['source type', b => { Object.assign(b.document, { provider: 42 }); }],
  ['source URL script', b => { b.document.canonical_url = 'javascript:alert(1)'; }],
  ['source URL credentials', b => { b.document.canonical_url = 'https://user:secret@example.com'; }],
  ['impossible collection date', b => { b.version.collected_at = '2026-02-30T00:00:00Z'; }],
  ['collection timestamp', b => { b.version.collected_at = 'yesterday'; }],
  ['selector kind', b => { Object.assign(b.citations[0].selector, { kind: 'html' }); }],
  ['quote mismatch', b => { b.citations[0].selector.quote = 'different'; }],
  ['context mismatch', b => { Object.assign(b.citations[0].selector, { suffix: 'different' }); }],
  ['context type', b => { Object.assign(b.citations[0].selector, { prefix: 5 }); }],
  ['page bound', b => { b.representation.pages[0].end = 1000; }],
  ['page order', b => { b.representation.pages.push({ page_number: 2, start: 0, end: 5 }); }],
  ['duplicate page', b => { b.representation.pages.push(b.representation.pages[0]); }],
  ['missing PDF page', b => { Object.assign(b.citations[1].selector, { page_number: 2 }); }],
  ['PDF page mismatch', b => { b.representation.pages[0].start = 1; }],
  ['PDF regions', b => { Object.assign(b.citations[1].selector, { regions: [{ x: -1 }] }); }],
  ['table reference', b => { Object.assign(b.citations[2].selector, { table_id: 'missing' }); }],
  ['cell reference', b => { Object.assign(b.citations[2].selector, { cell_id: 'missing' }); }],
  ['cell quote', b => { b.representation.tables[0].cells[0].text = 'different'; }],
];
it.each(corruptions)('rejects malformed 200: %s', async (_name, corrupt) => {
  const body = fixture(); corrupt(body); vi.stubGlobal('fetch', async () => response(body));
  await expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind: 'invalid-response', requestId });
});
it('validates Unicode code points and exact adjacent context', async () => {
  const body = fixture(); body.representation.text = '앞😀é뒤'; body.representation.pages = [{ page_number: 7, start: 0, end: 5 }];
  body.citations = [body.citations[0]];
  body.citations[0].selector = { kind: 'text', start: 1, end: 4, quote: '😀é', prefix: '앞', suffix: '뒤' };
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  vi.stubGlobal('fetch', async () => response(body));
  expect((await client.getEvidence(workspace, snapshot)).data.citations[0].selector.quote).toBe('😀é');
});
it('accepts empty parsed text with no citations/pages/tables', async () => {
  const body = fixture(); body.representation.text = ''; body.representation.pages = []; body.representation.tables = []; body.citations = [];
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  vi.stubGlobal('fetch', async () => response(body));
  expect((await client.getEvidence(workspace, snapshot)).data.representation.text).toBe('');
});
it('rejects malformed JSON without exposing it', async () => {
  vi.stubGlobal('fetch', async () => new Response('PRIVATE', { headers }));
  await expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind: 'invalid-response', message: 'Evidence request failed: invalid-response' });
});
it('classifies network errors safely', async () => {
  vi.stubGlobal('fetch', async () => { throw new Error('PRIVATE'); });
  await expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind: 'network', message: 'Evidence request failed: network' });
});
it.each(['headers', 'body'])('bounds the entire %s wait with default 10000ms deadline', async (phase) => {
  vi.useFakeTimers(); let signal: AbortSignal | undefined;
  vi.stubGlobal('fetch', async (_path: string, init: RequestInit) => { signal = init.signal as AbortSignal; return phase === 'headers' ? new Promise(() => {}) : { ok: true, headers: new Headers(headers), json: () => new Promise(() => {}) }; });
  const assertion = expect(client.getEvidence(workspace, snapshot)).rejects.toMatchObject({ kind: 'timeout' });
  await vi.advanceTimersByTimeAsync(9999); expect(signal?.aborted).toBe(false);
  await vi.advanceTimersByTimeAsync(1); await assertion; expect(signal?.aborted).toBe(true);
});
it('handles a custom positive integer deadline', async () => {
  vi.useFakeTimers(); vi.stubGlobal('fetch', () => new Promise(() => {}));
  const assertion = expect(client.getEvidence(workspace, snapshot, { timeoutMs: 5 })).rejects.toMatchObject({ kind: 'timeout' });
  await vi.advanceTimersByTimeAsync(5); await assertion;
});
it('rejects already aborted signals before fetching', async () => {
  const controller = new AbortController(); controller.abort(); const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(client.getEvidence(workspace, snapshot, { signal: controller.signal })).rejects.toMatchObject({ kind: 'aborted' });
  expect(fetch).not.toHaveBeenCalled();
});
it.each(['headers', 'body'])('immediately aborts a pending %s wait even if fetch ignores cancellation', async (phase) => {
  const controller = new AbortController(); let signal: AbortSignal | undefined;
  vi.stubGlobal('fetch', async (_path: string, init: RequestInit) => { signal = init.signal as AbortSignal; return phase === 'headers' ? new Promise(() => {}) : { ok: true, headers: new Headers(headers), json: () => new Promise(() => {}) }; });
  const assertion = expect(client.getEvidence(workspace, snapshot, { signal: controller.signal })).rejects.toMatchObject({ kind: 'aborted' });
  await Promise.resolve(); controller.abort(); await assertion; expect(signal?.aborted).toBe(true);
});

it('preserves a whitespace text quote', async () => {
  const body = fixture(); body.representation.text = '앞 뒤'; body.representation.pages = [];
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  body.citations = [body.citations[0]]; body.citations[0].selector = { kind: 'text', start: 1, end: 2, quote: ' ', prefix: '앞', suffix: '뒤' };
  vi.stubGlobal('fetch', async () => response(body));
  expect((await client.getEvidence(workspace, snapshot)).data.citations[0].selector.quote).toBe(' ');
});
it('accepts a saved empty table cell with its exact empty quote', async () => {
  const body = fixture(); body.representation.tables[0].cells[0].text = ''; body.citations = [body.citations[2]]; body.citations[0].selector.quote = '';
  vi.stubGlobal('fetch', async () => response(body));
  expect((await client.getEvidence(workspace, snapshot)).data.citations[0].selector.quote).toBe('');
});

it('keeps distinct actual page numbers in their stored text-span order', async () => {
  const body = fixture(); body.citations = []; body.representation.pages = [{ page_number: 7, start: 0, end: 5 }, { page_number: 3, start: 5, end: 38 }];
  vi.stubGlobal('fetch', async () => response(body));
  expect((await client.getEvidence(workspace, snapshot)).data.representation.pages.map(page => page.page_number)).toEqual([7, 3]);
});
it('does not overflow a large valid timeout into an immediate timeout', async () => {
  vi.useFakeTimers(); const controller = new AbortController(); vi.stubGlobal('fetch', () => new Promise(() => {}));
  let settled = false;
  const result = client.getEvidence(workspace, snapshot, { timeoutMs: 2_147_483_648, signal: controller.signal }).catch(error => { settled = true; return error; });
  await vi.advanceTimersByTimeAsync(1); expect(settled).toBe(false);
  controller.abort(); expect(await result).toMatchObject({ kind: 'aborted' });
});
