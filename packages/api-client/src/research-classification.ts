/** Private execution metadata only; no truth or legacy-category inference. */
import type {Claim, SupportReview} from './index';
import {hasKeys, isId, isObject} from './protected-request';
import {exactTimestamp} from './research-time';

export const classificationLabels = {
  documented: '자료에 기록됨', attributed: '출처의 주장', uncertain: '확인하기 어려움',
} as const;

/** Normalize only validated UTC spellings and preserve all six fractional digits. */
function utcMicroseconds(value: unknown): string | null {
  if (!exactTimestamp(value)) return null;
  const [whole, fraction = ''] = value.replace(/(?:Z|\+00:00)$/, '').split('.');
  return `${whole}.${fraction.padEnd(6, '0')}`;
}

export function validResearchClassifications(research: Record<string, unknown>, revision: Record<string, unknown>): boolean {
  if (!Array.isArray(research.claims) || !Array.isArray(research.support_reviews)) return false;
  const claims = research.claims;
  const versions = new Set(claims.map(claim => isObject(claim) && isObject(claim.derivation) ? claim.derivation.method_version : null));
  if (!versions.has('research-v3') && !versions.has('research-v4') && !versions.has('research-v5')) return research.support_reviews.length === 0;
  if (versions.size !== 1 || claims.length > 12 || research.support_reviews.length !== claims.length) return false;
  const version = [...versions][0] as string;
  const claimById = new Map<string, Record<string, unknown>>();
  for (const claim of claims) {
    if (!isObject(claim) || !isId(claim.claim_id) || claim.basis !== 'inference'
      || !isObject(claim.derivation) || claim.derivation.method !== 'pydantic-ai'
      || !Array.isArray(claim.citation_ids) || claim.citation_ids.length < 1 || claim.citation_ids.length > 3
      || claim.citation_ids.some(id => !isId(id)) || new Set(claim.citation_ids).size !== claim.citation_ids.length
      || claimById.has(claim.claim_id.toLowerCase())) return false;
    claimById.set(claim.claim_id.toLowerCase(), claim);
  }
  const reviewed = new Set<string>(), reviewIds = new Set<string>();
  const validatedAt = utcMicroseconds(revision.validated_at);
  if (validatedAt === null) return false;
  for (const review of research.support_reviews) {
    if (!isObject(review) || !hasKeys(review, ['review_id', 'reviewer_kind', 'reviewer_id', 'method', 'method_version', 'reviewed_at', 'rationale', 'citation_ids', 'target', 'scope', 'assessment'])
      || !isId(review.review_id) || reviewIds.has(review.review_id.toLowerCase())
      || review.reviewer_kind !== 'automated' || review.reviewer_id !== `issuedigest-${version}`
      || review.method !== 'pydantic-ai' || review.method_version !== version
      || utcMicroseconds(review.reviewed_at) !== validatedAt
      || typeof review.rationale !== 'string' || !review.rationale.trim() || Array.from(review.rationale).length > 300
      || !isObject(review.target) || !hasKeys(review.target, ['kind', 'claim_id'])
      || review.target.kind !== 'claim' || !isId(review.target.claim_id)
      || !((review.scope === 'content' && ['supported', 'insufficient'].includes(review.assessment as string))
        || (review.scope === 'attribution' && review.assessment === 'supported'))) return false;
    const id = review.target.claim_id.toLowerCase(), claim = claimById.get(id);
    if (!claim || reviewed.has(id) || !Array.isArray(review.citation_ids)
      || !Array.isArray(claim.citation_ids) || review.citation_ids.length !== claim.citation_ids.length
      || review.citation_ids.some((citation, index) => !isId(citation) || citation.toLowerCase() !== (claim.citation_ids as string[])[index]?.toLowerCase())) return false;
    reviewed.add(id); reviewIds.add(review.review_id.toLowerCase());
  }
  return reviewed.size === claims.length;
}

/** Only call after the private v3/v4/v5 profile has been validated. */
export function claimClassification(claim: Claim, reviews: SupportReview[]) {
  if (!['research-v3', 'research-v4', 'research-v5'].includes(claim.derivation?.method_version ?? '')) return null;
  const review = reviews.find(item => item.target.kind === 'claim' && item.target.claim_id.toLowerCase() === claim.claim_id.toLowerCase());
  if (!review) return null;
  const category = review.scope === 'attribution' ? 'attributed' : review.assessment === 'insufficient' ? 'uncertain' : 'documented';
  return {label: classificationLabels[category], rationale: review.rationale};
}
