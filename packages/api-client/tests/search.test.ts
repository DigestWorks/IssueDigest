import { afterEach, expect, it, vi } from 'vitest';
import { logout, searchEvidence } from '../src/index';

const workspace = '00000000-0000-4000-8000-000000000001';
const other = '00000000-0000-4000-8000-000000000002';
const requestId = '8ff9af27-d021-4fb3-a46e-cf8c3d093c44';
const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': requestId };
const query = () => ({ terms: ['한국어'], limit: 1 });
const hit = () => ({ workspace_id: workspace, snapshot_id: other, document_id: other, version_id: other, representation_id: other, provider: '합성 출처', source_id: 'source', source_kind: 'other', canonical_url: null, collected_at: '2026-10-14T00:00:00Z', unit_ordinal: 0, profile: 'literal-ngrams-v1', selector: { kind: 'text', start: 0, end: 3, quote: '한국어', prefix: null, suffix: null }, matched_terms: ['한국어'], anchor_status: 'matched', support_status: 'not_evaluated' });
const result = () => ({ workspace_id: workspace, query: { terms: ['한국어'], limit: 1, provider: null, source_id: null, source_kind: null, collected_from: null, collected_to: null }, hits: [hit()], coverage: { total_snapshots: 1, indexed_snapshots: 1, missing_snapshots: 0, skipped_empty_cells: 0, skipped_large_cells: 0 }, scanned_candidates: 1, truncated: false });
const response = (value: unknown) => new Response(JSON.stringify(value), { headers });
afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('posts literal terms with same-origin cookies and returns verified hits', async () => {
  const fetch = vi.fn(async () => response(result())); vi.stubGlobal('fetch', fetch);
  expect(await searchEvidence(workspace, query())).toEqual({ data: result(), requestId });
  expect(fetch).toHaveBeenCalledWith(`/api/v1/workspaces/${workspace}/evidence/search`, expect.objectContaining({ method: 'POST', credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json', 'Content-Type': 'application/json' }, body: JSON.stringify(query()), signal: expect.any(AbortSignal) }));
});

it.each([
  { terms: [] }, { terms: ['A', 'a'] }, { terms: [' x'] }, { terms: ['x'], limit: 21 }, { terms: ['x'], source_kind: 'invalid' }, { terms: ['x'], collected_from: '2026-10-14T00:00:00+09:00' },
])('rejects invalid query before fetch', async bad => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(searchEvidence(workspace, bad as never)).rejects.toMatchObject({ kind: 'invalid-query' });
  expect(fetch).not.toHaveBeenCalled();
});

it.each([
  ['workspace', d => { d.workspace_id = other; }],
  ['query', d => { d.query.terms = ['different']; }],
  ['hit workspace', d => { d.hits[0].workspace_id = other; }],
  ['matched terms', d => { d.hits[0].matched_terms = ['other']; }],
  ['quote', d => { d.hits[0].selector.quote = 'unrelated'; }],
  ['selector span', d => { d.hits[0].selector.end = 2; }],
  ['coverage', d => { d.coverage.indexed_snapshots = 0; }],
  ['count', d => { d.hits.push(hit()); }],
  ['unknown', d => { Object.assign(d.hits[0], { private: 'value' }); }],
] as [string, (data: ReturnType<typeof result>) => void][])('rejects altered response %s', async (_name, mutate) => {
  const data = result(); mutate(data); vi.stubGlobal('fetch', async () => response(data));
  await expect(searchEvidence(workspace, query())).rejects.toMatchObject({ kind: 'malformed', requestId });
});

it('rejects a hit outside the requested source filter', async () => {
  const data = result(); Object.assign(data.query, { provider: 'synthetic' });
  vi.stubGlobal('fetch', async () => response(data));
  await expect(searchEvidence(workspace, { ...query(), provider: 'synthetic' })).rejects.toMatchObject({ kind: 'malformed' });
});

it('preserves microsecond interval precision for input and included hits', async () => {
  const from = '2026-10-14T00:00:00.0000019Z';
  const to = '2026-10-14T00:00:00.000002+00:00';
  const data = result(); Object.assign(data.query, { collected_from: '2026-10-14T00:00:00.000001Z', collected_to: '2026-10-14T00:00:00.000002Z' });
  data.hits[0].collected_at = '2026-10-14T00:00:00.000001Z';
  vi.stubGlobal('fetch', async () => response(data));
  expect((await searchEvidence(workspace, { ...query(), collected_from: from, collected_to: to })).data.hits).toHaveLength(1);
});

it('rejects a changed echoed microsecond bound', async () => {
  const data = result(); Object.assign(data.query, { collected_from: '2026-10-14T00:00:00.000002Z', collected_to: '2026-10-14T00:00:00.000003Z' });
  data.hits[0].collected_at = '2026-10-14T00:00:00.000002Z';
  vi.stubGlobal('fetch', async () => response(data));
  await expect(searchEvidence(workspace, { ...query(), collected_from: '2026-10-14T00:00:00.000001Z', collected_to: '2026-10-14T00:00:00.000003Z' })).rejects.toMatchObject({ kind: 'malformed' });
});

it('excludes a hit exactly at the microsecond upper bound', async () => {
  const data = result(); Object.assign(data.query, { collected_from: '2026-10-14T00:00:00.000001Z', collected_to: '2026-10-14T00:00:00.000002Z' });
  data.hits[0].collected_at = '2026-10-14T00:00:00.000002Z';
  vi.stubGlobal('fetch', async () => response(data));
  await expect(searchEvidence(workspace, { ...query(), collected_from: '2026-10-14T00:00:00.000001Z', collected_to: '2026-10-14T00:00:00.000002Z' })).rejects.toMatchObject({ kind: 'malformed' });
});

it.each(['provider', 'source_id', 'table_id', 'cell_id'] as const)('accepts canonical long output %s', async field => {
  const data = result(); const longId = 'x'.repeat(1025);
  if (field === 'provider' || field === 'source_id') Object.assign(data.hits[0], { [field]: longId });
  else Object.assign(data.hits[0], { selector: { kind: 'table_cell', table_id: field === 'table_id' ? longId : 'table', cell_id: field === 'cell_id' ? longId : 'cell', quote: '한국어' } });
  vi.stubGlobal('fetch', async () => response(data));
  expect((await searchEvidence(workspace, query())).data.hits).toHaveLength(1);
});

it('keeps the 1024 code-point query-filter limit', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  await expect(searchEvidence(workspace, { ...query(), provider: 'x'.repeat(1025) })).rejects.toMatchObject({ kind: 'invalid-query' });
  expect(fetch).not.toHaveBeenCalled();
});

it('classifies fixed search errors without reading private bodies', async () => {
  for (const [status, kind] of [[401, 'unauthorized'], [403, 'forbidden'], [404, 'not-found'], [422, 'invalid-query'], [503, 'unavailable']] as const) {
    vi.stubGlobal('fetch', async () => new Response('PRIVATE', { status, headers }));
    await expect(searchEvidence(workspace, query())).rejects.toMatchObject({ kind, requestId });
  }
});

it('times out, aborts, and ignores late responses', async () => {
  vi.useFakeTimers(); let resolve!: (response: Response) => void;
  vi.stubGlobal('fetch', () => new Promise<Response>(done => { resolve = done; }));
  const pending = searchEvidence(workspace, query(), { timeoutMs: 10 });
  const assertion = expect(pending).rejects.toMatchObject({ kind: 'timeout' });
  await vi.advanceTimersByTimeAsync(10); await assertion; resolve(response(result()));
  const controller = new AbortController();
  vi.stubGlobal('fetch', () => new Promise(() => {}));
  const canceled = searchEvidence(workspace, query(), { signal: controller.signal });
  controller.abort(); await expect(canceled).rejects.toMatchObject({ kind: 'aborted' });
});

it('keeps concurrent search responses attached to their own requests', async () => {
  const resolvers: ((response: Response) => void)[] = [];
  vi.stubGlobal('fetch', () => new Promise<Response>(resolve => { resolvers.push(resolve); }));
  const first = searchEvidence(workspace, query());
  const second = searchEvidence(workspace, { terms: ['other'], limit: 1 });
  const later = result(); later.query.terms = ['other']; later.hits = []; later.scanned_candidates = 0;
  resolvers[1](response(later));
  expect((await second).data.query.terms).toEqual(['other']);
  resolvers[0](response(result()));
  expect((await first).data.query.terms).toEqual(['한국어']);
});

it('preserves the logout 204 contract after search POST support', async () => {
  vi.stubGlobal('fetch', async () => new Response(null, { status: 204, headers }));
  expect(await logout()).toEqual({ requestId });
});
