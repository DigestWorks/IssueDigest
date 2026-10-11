/** Compile-only consumers: public types must come from materialized OpenAPI. */
import type {
  SourceIdentity, Entity, Claim, DerivationRecord, IdentityReview, SupportReview,
  EntityReference, ClaimReference, DocumentReference, RelationReference, Relation,
  DateInterval, Dimension, ComparisonContext, Observation, ComparisonReason,
  ComparisonAssessment, ResearchBundle,
} from '../src/index';
import type { components } from '../src/schema';

type Equal<A, B> = (<T>() => T extends A ? 1 : 2) extends (<T>() => T extends B ? 1 : 2) ? true : false;
type Assert<T extends true> = T;
export type PublicGeneratedTypes = Assert<Equal<
  [SourceIdentity, Entity, Claim, DerivationRecord, IdentityReview, SupportReview,
    EntityReference, ClaimReference, DocumentReference, RelationReference, Relation,
    DateInterval, Dimension, ComparisonContext, Observation, ComparisonReason,
    ComparisonAssessment, ResearchBundle],
  [components['schemas']['SourceIdentity'], components['schemas']['Entity'],
    components['schemas']['Claim'], components['schemas']['DerivationRecord'],
    components['schemas']['IdentityReview'], components['schemas']['SupportReview'],
    components['schemas']['EntityReference'], components['schemas']['ClaimReference'],
    components['schemas']['DocumentReference'], components['schemas']['RelationReference'],
    components['schemas']['Relation'], components['schemas']['DateInterval'],
    components['schemas']['Dimension'], components['schemas']['ComparisonContext'],
    components['schemas']['Observation'], components['schemas']['ComparisonReason'],
    components['schemas']['ComparisonAssessment'], components['schemas']['ResearchBundle']]
>>;

export const precision: Observation['value'] = '123456789012345678901234567890.00100';
export const unknownValue: Observation['value'] = null;
// @ts-expect-error transport values stay strings; numeric precision cannot be discarded
export const numberValue: Observation['value'] = 40;
// @ts-expect-error a document cannot be the target of semantic support review
export const documentReview: SupportReview['target'] = { kind: 'document', document_id: 'id' };
// @ts-expect-error causal predicates are outside the versioned ontology
export const causalRelation: Relation['predicate'] = 'causes';
// @ts-expect-error comparison does not authorize aggregation
export const allowedAggregation: ComparisonAssessment['aggregation_status'] = 'allowed';
