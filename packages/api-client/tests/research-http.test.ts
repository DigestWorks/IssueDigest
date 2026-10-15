import { expect, test } from 'vitest';
import { getResearchRun, getResearchSources, submitResearch, ResearchError } from '../src/research';
import generatedRun from './fixtures/research-run-generated.json';

const workspace = '00000000-0000-4000-8000-000000000001';
const snapshot = '00000000-0000-4000-8000-000000000002';
const request = '00000000-0000-4000-8000-000000000003';
const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': request };

test('source catalog rejects an internal-id title and submit sends bounded JSON', async () => {
  const original = globalThis.fetch;
  const paths: string[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    paths.push(String(input));
    expect(init?.credentials).toBe('same-origin');
    expect(init?.cache).toBe('no-store');
    return new Response(JSON.stringify({workspace_id: workspace, items: [{ snapshot_id: snapshot, document_id: request, title: '법안 자료', source_kind: 'bill', bill_number: null, proposed_on: null, collected_at: '2026-10-15T00:00:00Z', canonical_url: null, citation_count: 0, excerpt: '' }]}), {headers});
  }) as typeof fetch;
  try {
    const result = await getResearchSources(workspace);
    expect(result.data.items[0]?.title).toBe('법안 자료');
    expect(() => submitResearch(workspace, {request_id: request, question: '', snapshot_ids: [snapshot], parent_run_id: null})).toThrowError(ResearchError);
    expect(paths).toHaveLength(1);
  } finally { globalThis.fetch = original; }
});

test('catalog rejects an impossible proposal date', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify({workspace_id: workspace, items: [{ snapshot_id: snapshot, document_id: request, title: '법안 자료', source_kind: 'bill', bill_number: '2200001', proposed_on: '2026-02-30', collected_at: '2026-10-15T00:00:00Z', canonical_url: null, citation_count: 0, excerpt: '' }]}), {headers})) as typeof fetch;
  try { await expect(getResearchSources(workspace)).rejects.toMatchObject({kind: 'malformed'}); }
  finally { globalThis.fetch = original; }
});

test('a server-produced completed Canvas with exact citations can be reopened', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify(generatedRun), {headers})) as typeof fetch;
  try {
    const documentId = Object.keys(generatedRun.result.source_titles)[0]!;
    expect((await getResearchRun(workspace, generatedRun.run_id)).data.result?.source_titles[documentId]).toBe('합성 문서');
  }
  finally { globalThis.fetch = original; }
});

function objectAt(root: unknown, ...path: (string | number)[]): Record<string, unknown> {
  let current: unknown = root;
  for (const segment of path) {
    if (typeof segment === 'number') {
      if (!Array.isArray(current)) throw new Error('Invalid synthetic fixture');
      current = current[segment];
    } else {
      if (typeof current !== 'object' || current === null || Array.isArray(current)) throw new Error('Invalid synthetic fixture');
      current = (current as Record<string, unknown>)[segment];
    }
  }
  if (typeof current !== 'object' || current === null || Array.isArray(current)) throw new Error('Invalid synthetic fixture');
  return current as Record<string, unknown>;
}

const canvas = (value: unknown) => objectAt(value, 'result', 'canvas');
const research = (value: unknown) => objectAt(canvas(value), 'research');
const revision = (value: unknown) => objectAt(canvas(value), 'revision');
const draft = (value: unknown) => objectAt(revision(value), 'draft');
const moduleAt = (value: unknown, index: number) => objectAt(draft(value), 'modules', index);
const proof = (value: unknown) => objectAt(research(value), 'evidence', 0);
const citationAt = (value: unknown, index: number) => objectAt(proof(value), 'citations', index);

const malformed: [string, (value: unknown) => void][] = [
  ['missing research collection', value => { delete research(value).entities; }],
  ['missing revision identity', value => { delete revision(value).revision_id; }],
  ['nonroot revision', value => { revision(value).revision_number = 2; }],
  ['missing validation time', value => { delete revision(value).validated_at; }],
  ['missing draft identity', value => { delete draft(value).draft_id; }],
  ['missing module span', value => { delete moduleAt(value, 0).span; }],
  ['incomplete derivation', value => { delete objectAt(research(value), 'claims', 0, 'derivation').method_version; }],
  ['unselected version', value => { revision(value).selected_version_ids = []; }],
  ['citation outside claim union', value => { moduleAt(value, 0).citation_ids = [citationAt(value, 1).citation_id]; }],
  ['timeline without period', value => { moduleAt(value, 0).kind = 'timeline'; }],
  ['impossible calendar timestamp', value => { objectAt(value).created_at = '2026-02-30T00:00:00Z'; }],
  ['over-budget output usage', value => { objectAt(value).output_tokens = 5001; }],
  ['object status coercion', value => { objectAt(value).status = ['completed']; }],
  ['duplicate progress event', value => { objectAt(value, 'events', 2).status = 'retrieving'; }],
  ['object source kind coercion', value => { objectAt(proof(value), 'document').source_kind = ['other']; }],
  ['duplicate evidence citation', value => { citationAt(value, 1).citation_id = citationAt(value, 0).citation_id; }],
];

test.each(malformed)('completed result rejects %s', async (_name, mutate) => {
  const original = globalThis.fetch;
  const value = structuredClone(generatedRun);
  mutate(value);
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { await expect(getResearchRun(workspace, generatedRun.run_id)).rejects.toMatchObject({kind: 'malformed'}); }
  finally { globalThis.fetch = original; }
});

test('a complete insufficient-evidence Canvas with no claims or modules can be reopened', async () => {
  const original = globalThis.fetch;
  const value = structuredClone(generatedRun);
  research(value).claims = [];
  draft(value).outcome = 'insufficient_evidence';
  draft(value).modules = [];
  draft(value).message = '인용 가능한 내용이 부족합니다.';
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { expect((await getResearchRun(workspace, generatedRun.run_id)).data.result?.canvas.revision.draft.outcome).toBe('insufficient_evidence'); }
  finally { globalThis.fetch = original; }
});
