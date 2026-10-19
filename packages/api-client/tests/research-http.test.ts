import { expect, test } from 'vitest';
import { getResearchRun, submitResearch, type ResearchRequest } from '../src/research';
import generatedRun from './fixtures/research-run-generated.json';
import maximumCitations from './fixtures/research-run-36-citations.json';

const workspace = '00000000-0000-4000-8000-000000000001';
const snapshot = '00000000-0000-4000-8000-000000000002';
const request = '00000000-0000-4000-8000-000000000003';
const headers = { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': request };

test('question-only submission accepts queued empty provenance and sends only the declared input', async () => {
  const original = globalThis.fetch;
  const input = {request_id: request, question: '최근 변화는?', parent_run_id: null};
  let sent: unknown;
  globalThis.fetch = (async (_path, init) => {
    sent = JSON.parse(init?.body as string);
    expect(init).toMatchObject({credentials: 'same-origin', cache: 'no-store'});
    return new Response(JSON.stringify({...generatedRun, ...input, snapshot_ids: [], status: 'queued', error_code: null, result: null, events: [generatedRun.events[0]]}), {headers});
  }) as typeof fetch;
  try { expect((await submitResearch(workspace, input)).data.snapshot_ids).toEqual([]); expect(sent).toEqual(input); }
  finally { globalThis.fetch = original; }
});

test.each([{snapshot_ids: [snapshot]}, {arbitrary: true}])('rejects injected request fields before HTTP: %j', async extra => {
  const input = {request_id: request, question: '질문', parent_run_id: null, ...extra} as ResearchRequest;
  await expect(Promise.resolve().then(() => submitResearch(workspace, input))).rejects.toMatchObject({kind: 'malformed'});
});

test.each(['queued', 'no-hit'] as const)('reads %s with empty server provenance', async kind => {
  const original = globalThis.fetch;
  const status = kind === 'queued' ? 'queued' : 'failed';
  const value = {...generatedRun, snapshot_ids: [], status, error_code: kind === 'queued' ? null : 'insufficient_evidence', result: null, events: kind === 'queued' ? [generatedRun.events[0]] : [generatedRun.events[0], {sequence: 2, status, created_at: generatedRun.updated_at}]};
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { expect((await getResearchRun(workspace, value.run_id)).data.snapshot_ids).toEqual([]); }
  finally { globalThis.fetch = original; }
});

test.each(['research-v1', 'research-v2'])('reads saved %s derivation without rewriting it', async version => {
  const original = globalThis.fetch;
  const value = structuredClone(generatedRun);
  value.result.canvas.research.claims.forEach(claim => { claim.derivation.method_version = version; });
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { expect((await getResearchRun(workspace, value.run_id)).data.result?.canvas.research.claims[0]?.derivation?.method_version).toBe(version); }
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
  ['empty completed provenance', value => { objectAt(value).snapshot_ids = []; }],
  ['six sources', value => { objectAt(value).snapshot_ids = Array.from({length: 6}, (_, index) => `00000000-0000-4000-8000-${String(index+100).padStart(12, '0')}`); }],
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

test('three generated analysis modules can cite 36 distinct pieces of evidence', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify(maximumCitations), {headers})) as typeof fetch;
  try {
    const result = (await getResearchRun(workspace, maximumCitations.run_id)).data.result;
    expect(result?.canvas.revision.draft.modules.at(-1)?.citation_ids).toHaveLength(36);
  }
  finally { globalThis.fetch = original; }
});

test('an evidence module over the 36-citation generated maximum is rejected', async () => {
  const original = globalThis.fetch;
  const value = structuredClone(maximumCitations);
  const extra = structuredClone(citationAt(value, 0));
  extra.citation_id = '00000000-0000-4000-8000-000000000500';
  const proofCitations = proof(value).citations;
  const finalCitations = moduleAt(value, 3).citation_ids;
  const finalActions = moduleAt(value, 3).actions;
  if (!Array.isArray(proofCitations) || !Array.isArray(finalCitations) || !Array.isArray(finalActions)) throw new Error('Invalid synthetic fixture');
  proofCitations.push(extra);
  finalCitations.push(extra.citation_id);
  finalActions.push({kind: 'open_evidence', citation_id: extra.citation_id});
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { await expect(getResearchRun(workspace, maximumCitations.run_id)).rejects.toMatchObject({kind: 'malformed'}); }
  finally { globalThis.fetch = original; }
});

test('total usage respects the 24,000-token bound as well as output bound', async () => {
  const original = globalThis.fetch;
  try {
    for (const [input, accepted] of [[19_001, false], [19_000, true]] as const) {
      const value = structuredClone(generatedRun);
      objectAt(value).input_tokens = input;
      objectAt(value).output_tokens = 5_000;
      globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
      if (accepted) expect((await getResearchRun(workspace, value.run_id)).data.input_tokens).toBe(input);
      else await expect(getResearchRun(workspace, value.run_id)).rejects.toMatchObject({kind: 'malformed'});
    }
  }
  finally { globalThis.fetch = original; }
});


test.each(['generated', 'timeline-generated', 'nonanswer-generated', 'astral-generated'])('accepts actual Python v9 %s fixture through full client', async kind => {
  const value = (await import(`./fixtures/research-run-v9-${kind}.json`)).default;
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { expect((await getResearchRun(value.workspace_id, value.run_id)).data).toEqual(value); }
  finally { globalThis.fetch = original; }
});

test.each(['stripped', 'mixed', 'reviewer', 'core', 'prefix', 'unicode', 'date'])('rejects forged v9 %s through full client', async mutation => {
  const value = structuredClone((await import('./fixtures/research-run-v9-generated.json')).default);
  const claim = objectAt(research(value), 'claims', 0);
  const review = objectAt(research(value), 'support_reviews', 0);
  if (mutation === 'stripped') research(value).support_reviews = [];
  if (mutation === 'mixed') objectAt(claim, 'derivation').method_version = 'research-v8';
  if (mutation === 'reviewer') review.reviewer_id = 'issuedigest-research-v8';
  if (mutation === 'core') { review.scope = 'content'; review.assessment = 'insufficient'; }
  if (mutation === 'prefix') claim.text = '없는기관에 따르면, 합성';
  if (mutation === 'unicode') claim.text = '제공 자료에 따르면, \ufeff\u0085';
  if (mutation === 'date') claim.valid_period = {start_date:'2026-01-01',end_date:'2026-01-01'};
  const original = globalThis.fetch;
  globalThis.fetch = (async () => new Response(JSON.stringify(value), {headers})) as typeof fetch;
  try { await expect(getResearchRun(value.workspace_id, value.run_id)).rejects.toMatchObject({kind:'malformed'}); }
  finally { globalThis.fetch = original; }
});
