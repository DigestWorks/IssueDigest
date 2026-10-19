import {expect, test, vi} from 'vitest';
import {validResearchClassifications, claimClassification, getResearchRun} from '../src';
import {validResearchCanvas} from '../src/research-validation';
import fixture from './fixtures/research-run-v6-generated.json';
import type {ResearchRun} from '../src';

const value = () => structuredClone(fixture) as ResearchRun;
async function read(run: ResearchRun) {
  const headers = {'Content-Type':'application/json', 'Cache-Control':'no-store', 'X-Request-ID':'00000000-0000-4000-8000-000000000003'};
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify(run), {headers}));
  try { return await getResearchRun(run.workspace_id, run.run_id); }
  finally { vi.unstubAllGlobals(); }
}
function valid(run: ResearchRun) {
  return validResearchCanvas(run.result!.canvas, run.workspace_id, run.run_id, run.result!.source_titles);
}
test('accepts the actual Python v6 builder result and its source attribution', () => {
  const run = value(), {research} = run.result!.canvas;
  expect(valid(run)).toBe(true);
  expect(claimClassification(research.claims[0]!, research.support_reviews)).toMatchObject({label:'출처의 주장'});
});
test.each(['missing', 'mixed-claim', 'mixed-review', 'reviewer', 'core-uncertain', 'core-not-first', 'subject'] as const)('rejects malformed v6 %s', mutation => {
  const run = value(), {research, revision} = run.result!.canvas;
  if (mutation === 'missing') research.support_reviews = [];
  if (mutation === 'mixed-claim') research.claims[0]!.derivation!.method_version = 'research-v5';
  if (mutation === 'mixed-review') research.support_reviews[0]!.method_version = 'research-v5';
  if (mutation === 'reviewer') research.support_reviews[0]!.reviewer_id = 'issuedigest-research-v5';
  if (mutation === 'core-uncertain') Object.assign(research.support_reviews[0]!, {scope:'content', assessment:'insufficient'});
  if (mutation === 'core-not-first') revision.draft.modules.reverse();
  if (mutation === 'subject') research.claims[0]!.text = '알 수 없는 기관에 따르면, 같은 방향입니다.';
  expect(valid(run)).toBe(false);
  expect(validResearchClassifications(research, revision)).toBe(false);
});

test('preserves an exact source subject containing the attribution separator', () => {
  const run = value(), {research, revision} = run.result!.canvas;
  research.evidence[0]!.citations[0]!.selector.quote = '합성에 따르면, 별칭';
  research.claims[0]!.text = '합성에 따르면, 별칭에 따르면, ' + '가'.repeat(400);
  expect(validResearchClassifications(research, revision)).toBe(true);
});

test('accepts actual Python 80-code-point subject and 400-code-point body through the full client', async () => {
  const {default: astral} = await import('./fixtures/research-run-v6-astral-generated.json');
  const run = structuredClone(astral) as ResearchRun;
  expect(run.result!.canvas.research.claims[0]!.text).toBe('😀'.repeat(80) + '에 따르면, ' + '🚀'.repeat(400));
  expect(valid(run)).toBe(true);
  expect((await read(run)).data).toEqual(run);
});
test.each(['v2', 'v3', 'v4', 'v5'])('preserves historical %s UTF16 raw validation', async version => {
  const {default: astral} = await import('./fixtures/research-run-v6-astral-generated.json');
  const run = structuredClone(astral) as ResearchRun, research = run.result!.canvas.research;
  research.claims.forEach(claim => { claim.derivation!.method_version = `research-${version}`; });
  research.support_reviews.forEach(review => { review.method_version = `research-${version}`; review.reviewer_id = `issuedigest-research-${version}`; });
  if (version === 'v2') research.support_reviews = [];
  run.result!.canvas.revision.draft.modules[0]!.title = '요약';
  expect(valid(run)).toBe(false);
});
test.each([' ', '\t\n', '\u3000'])('rejects canonical blank attribution suffix %j', async body => {
  const run = value(), {research, revision} = run.result!.canvas;
  research.claims[0]!.text = '제공 자료에 따르면, ' + body;
  expect(validResearchClassifications(research, revision)).toBe(false);
  expect(valid(run)).toBe(false);
  await expect(read(run)).rejects.toMatchObject({kind:'malformed'});
});
test.each(['body401', 'subject81'])('rejects oversized v6 astral %s', async mutation => {
  const {default: astral} = await import('./fixtures/research-run-v6-astral-generated.json');
  const run = structuredClone(astral) as ResearchRun, research = run.result!.canvas.research;
  const subject = '😀'.repeat(mutation === 'subject81' ? 81 : 80);
  research.evidence[0]!.citations[0]!.selector.quote = subject;
  research.claims[0]!.text = subject + '에 따르면, ' + '🚀'.repeat(mutation === 'body401' ? 401 : 400);
  expect(validResearchClassifications(research, run.result!.canvas.revision)).toBe(false);
  expect(valid(run)).toBe(false);
});
