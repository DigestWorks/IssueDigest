import {describe, expect, test, vi} from 'vitest';
import {getResearchRun, type ResearchRun, type SupportReview} from '../src';
import {classifiedRun} from './classification-data';

const headers = {'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': '00000000-0000-4000-8000-000000000003'};
async function read(value: ResearchRun) {
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify(value), {headers}));
  try { return await getResearchRun(value.workspace_id, value.run_id); }
  finally { vi.unstubAllGlobals(); }
}

test.each(['documented', 'attributed', 'uncertain'] as const)('accepts exact private v3 %s review without rewriting canonical payload', async category => {
  const value = classifiedRun(category);
  expect((await read(value)).data).toEqual(value);
});

type Mutation = (value: ResearchRun, review: SupportReview) => void;
const malformed: [string, Mutation][] = [
  ['missing review', value => { value.result!.canvas.research.support_reviews = []; }],
  ['duplicate review', (value, review) => { value.result!.canvas.research.support_reviews.push({...review, review_id:'00000000-0000-4000-8000-000000000999'}); }],
  ['unknown target', (_value, review) => { review.target = {kind:'claim', claim_id:'00000000-0000-4000-8000-000000000999'}; }],
  ['human impersonation', (_value, review) => { review.reviewer_kind = 'human'; }],
  ['incorrect fixed reviewer', (_value, review) => { review.reviewer_id = 'other'; }],
  ['incorrect method', (_value, review) => { review.method = 'other'; }],
  ['legacy reviewer', (_value, review) => { review.method_version = 'research-v2'; }],
  ['contradiction', (_value, review) => { review.assessment = 'contradicted'; }],
  ['attribution insufficient', (_value, review) => { review.scope = 'attribution'; review.assessment = 'insufficient'; }],
  ['wrong quote', (value, review) => { review.citation_ids = [value.result!.canvas.research.evidence[0]!.citations[1]!.citation_id]; }],
  ['different microsecond', (_value, review) => { review.reviewed_at = '2026-10-13T00:00:00.123457Z'; }],
  ['offset timestamp', (_value, review) => { review.reviewed_at = '2026-10-13T09:00:00.123456+09:00'; }],
  ['blank explanation', (_value, review) => { review.rationale = ' '; }],
  ['long explanation', (_value, review) => { review.rationale = 'x'.repeat(301); }],
  ['injected property', (_value, review) => { Object.assign(review, {truth:true}); }],
  ['legacy claim with review', value => { value.result!.canvas.research.claims[0]!.derivation!.method_version = 'research-v2'; }],
  ['v3 claim with downgraded remaining claims', value => {
    const claim = structuredClone(value.result!.canvas.research.claims[0]!);
    claim.claim_id = '00000000-0000-4000-8000-000000000999';
    claim.derivation!.method_version = 'research-v2';
    value.result!.canvas.research.claims.push(claim);
  }],
  ['review with no claims', value => {
    value.result!.canvas.research.claims = [];
    value.result!.canvas.revision.draft = {...value.result!.canvas.revision.draft, outcome:'insufficient_evidence', message:'부족', modules:[]};
  }],
  ['citation order differs', (value, review) => {
    const claim = value.result!.canvas.research.claims[0]!;
    claim.citation_ids.push(value.result!.canvas.research.evidence[0]!.citations[1]!.citation_id);
    review.citation_ids = [...claim.citation_ids].reverse();
  }],
];
test.each(malformed)('rejects malformed classification: %s', async (_name, mutate) => {
  const value = classifiedRun(); mutate(value, value.result!.canvas.research.support_reviews[0]!);
  await expect(read(value)).rejects.toMatchObject({kind:'malformed'});
});

test('accepts equivalent UTC spellings without truncating microseconds', async () => {
  const value = classifiedRun();
  value.result!.canvas.research.support_reviews[0]!.reviewed_at = '2026-10-13T00:00:00.123456+00:00';
  expect((await read(value)).data).toEqual(value);
});

describe.each(['v4', 'v5'] as const)('%s', version => {
test.each(['documented', 'attributed', 'uncertain'] as const)('accepts exact private classification %s', async category => {
  const value = classifiedRun(category, version);
  expect((await read(value)).data).toEqual(value);
});
test.each(malformed)('rejects malformed classification: %s', async (_name, mutate) => {
  const value = classifiedRun('documented', version);
  mutate(value, value.result!.canvas.research.support_reviews[0]!);
  await expect(read(value)).rejects.toMatchObject({kind:'malformed'});
});
test.each(['v3', 'v4', 'v5'].filter(other => other !== version).flatMap(other => ['review version', 'review identity', 'claim version'].map(kind => ({other, kind}))))('rejects mixed $other $kind', async ({other, kind}) => {
  const value = classifiedRun('attributed', version), research = value.result!.canvas.research;
  if (kind === 'review version') research.support_reviews[0]!.method_version = `research-${other}`;
  if (kind === 'review identity') research.support_reviews[0]!.reviewer_id = `issuedigest-research-${other}`;
  if (kind === 'claim version') research.claims[0]!.derivation!.method_version = `research-${other}`;
  await expect(read(value)).rejects.toMatchObject({kind:'malformed'});
});

});
