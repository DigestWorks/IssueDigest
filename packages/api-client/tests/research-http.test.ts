import { expect, test } from 'vitest';
import { getResearchRun, getResearchSources, submitResearch, ResearchError } from '../src/research';
import fixture from '../../../tests/fixtures/canvas-synthetic.json';

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

test('a completed result with an exact citation can be reopened', async () => {
  const original = globalThis.fetch;
  const runId = '00000000-0000-4000-8000-000000000032';
  const evidence = structuredClone(fixture.research.evidence[0])!;
  const citationId = evidence.citations[0]!.citation_id;
  const claimId = '00000000-0000-4000-8000-000000000018';
  const canvas = {
    research: {workspace_id: workspace, evidence: [evidence], claims: [{claim_id: claimId, workspace_id: workspace, text: '합성 자료의 내용', basis: 'inference', citation_ids: [citationId], derivation: {method: 'pydantic-ai'}}]},
    revision: {workspace_id: workspace, run_id: runId, selected_version_ids: [evidence.version.version_id], draft: {outcome: 'answer', message: null, modules: [{kind: 'summary', module_id: '00000000-0000-4000-8000-000000000019', title: '요약', citation_ids: [citationId], claim_ids: [claimId], actions: [{kind: 'open_evidence', citation_id: citationId}]}]}}
  };
  const result = {canvas, source_titles: {[evidence.document.document_id]: '합성 문서'}};
  const run = {run_id: runId, workspace_id: workspace, request_id: request, question: '무엇인가요?', snapshot_ids: [snapshot], parent_run_id: null, status: 'completed', error_code: null, created_at: '2026-10-15T00:00:00Z', updated_at: '2026-10-15T00:00:00Z', events: [{sequence: 1, status: 'completed', created_at: '2026-10-15T00:00:00Z'}], result, model: 'gpt-5.4-mini', input_tokens: 10, output_tokens: 20};
  globalThis.fetch = (async () => new Response(JSON.stringify(run), {headers})) as typeof fetch;
  try { expect((await getResearchRun(workspace, runId)).data.result?.source_titles[evidence.document.document_id]).toBe('합성 문서'); }
  finally { globalThis.fetch = original; }
});
