import {expect, test} from 'vitest';
import {validResearchClassifications, claimClassification} from '../src';
import {validResearchCanvas} from '../src/research-validation';
import fixture from './fixtures/research-run-v6-generated.json';
import type {ResearchRun} from '../src';

const value = () => structuredClone(fixture) as ResearchRun;
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
