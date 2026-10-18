import type {ResearchRun, SupportReview} from '../src';
import legacy from './fixtures/research-run-generated.json';

/** Manufactured v3 response, never modifies the historical fixture. */
export function classifiedRun(category: 'documented' | 'attributed' | 'uncertain' = 'documented', version: 'v3' | 'v4' = 'v3'): ResearchRun {
  const value = structuredClone(legacy) as ResearchRun;
  if (!value.result) throw new Error('Synthetic result required');
  const {research, revision} = value.result.canvas;
  revision.validated_at = '2026-10-13T00:00:00.123456Z';
  research.claims.forEach(claim => { claim.derivation!.method_version = `research-${version}`; });
  research.support_reviews = research.claims.map((claim, index): SupportReview => ({
    review_id: `00000000-0000-4000-8000-${String(index + 900).padStart(12, '0')}`,
    reviewer_kind: 'automated', reviewer_id: `issuedigest-research-${version}`, method: 'pydantic-ai',
    method_version: `research-${version}`, reviewed_at: revision.validated_at,
    rationale: '선택한 인용에 대한 합성 AI 설명입니다.', citation_ids: [...claim.citation_ids],
    target: {kind: 'claim', claim_id: claim.claim_id},
    scope: category === 'attributed' ? 'attribution' : 'content',
    assessment: category === 'uncertain' ? 'insufficient' : 'supported',
  }));
  return value;
}
