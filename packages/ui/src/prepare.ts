import {validResearchClassifications} from '@issuedigest/api-client';
import type {
  CanvasBundle, CanvasModule, Citation, Claim, Entity, EvidenceBundle, Observation,
  Relation, SourceDocument, SupportReview,
} from '@issuedigest/api-client';

export type CitationDisplay = { citation: Citation; proof: EvidenceBundle };
export type DisplayContext = {
  citations: Map<string, CitationDisplay>;
  claims: Map<string, Claim>;
  entities: Map<string, Entity>;
  relations: Map<string, Relation>;
  observations: Map<string, Observation>;
  documents: Map<string, SourceDocument>;
  supportReviews: SupportReview[];
};
export type PreparedCanvas =
  | { status: 'rejected' }
  | { status: 'message'; outcome: 'insufficient_evidence' | 'clarification_needed'; message: string }
  | { status: 'ready'; modules: CanvasModule[]; context: DisplayContext };

function requireDisplay(condition: unknown): asserts condition {
  if (!condition) throw new Error('Unsupported display');
}
function unique(ids: string[], minimum = 0) {
  requireDisplay(ids.length >= minimum && new Set(ids).size === ids.length);
}
function index<T>(records: T[], id: (record: T) => string): Map<string, T> {
  const result = new Map<string, T>();
  for (const record of records) {
    requireDisplay(!result.has(id(record)));
    result.set(id(record), record);
  }
  return result;
}
function consistent<T extends object>(records: Map<string, T>, id: string, value: T) {
  const previous = records.get(id);
  // Document/version metadata are flat scalar records. JSON property order is not identity.
  requireDisplay(previous === undefined || (Object.keys(previous).length === Object.keys(value).length
    && Object.keys(value).every(key => previous[key as keyof T] === value[key as keyof T])));
  records.set(id, value);
}
function basis(value: Claim['basis']) {
  requireDisplay(['source_assertion', 'observation', 'inference'].includes(value));
}
function interval(value: NonNullable<Claim['valid_period']>) {
  // The server validates calendar dates; display uses the contract's sortable exact date format.
  requireDisplay(/^\d{4}-\d{2}-\d{2}$/.test(value.start_date)
    && /^\d{4}-\d{2}-\d{2}$/.test(value.end_date) && value.start_date <= value.end_date);
}
function sameChartContext(values: Observation[]) {
  const fields = ['metric', 'unit', 'population', 'geography', 'question', 'methodology',
    'weighting', 'denominator', 'series_id', 'sample_size'] as const;
  for (const field of fields) {
    const first = values[0].context[field];
    requireDisplay(first !== null && first !== undefined);
    requireDisplay(values.every(value => value.context[field] === first));
  }
  const period = values[0].context.period;
  requireDisplay(period); interval(period);
  requireDisplay(values.every(value => value.context.period?.start_date === period.start_date
    && value.context.period.end_date === period.end_date));
  const dimensions = (value: Observation) => {
    unique(value.context.dimensions.map(dimension => dimension.key));
    return JSON.stringify([...value.context.dimensions].sort((a, b) => a.key.localeCompare(b.key))
      .map(dimension => [dimension.key, dimension.value]));
  };
  const first = dimensions(values[0]);
  requireDisplay(values.every(value => dimensions(value) === first));
}

/** Display references only. Input must already be server-validated; this is not an API JSON validator. */
export function prepareCanvas(bundle: CanvasBundle): PreparedCanvas {
  try {
    const { research, revision } = bundle;
    const draft = revision.draft;
    if (research.claims.some(claim => /^research-v[12345]$/.test(claim.derivation?.method_version ?? ''))
      || research.support_reviews.some(review => ['issuedigest-research-v3', 'issuedigest-research-v4', 'issuedigest-research-v5'].includes(review.reviewer_id ?? ''))) {
      requireDisplay(validResearchClassifications(research, revision));
    }
    requireDisplay(research.schema_version === 1 && revision.schema_version === 1
      && draft.schema_version === 1 && revision.validation_policy === 'issuedigest-canvas-v1'
      && research.workspace_id === revision.workspace_id);
    requireDisplay(Number.isSafeInteger(revision.revision_number) && revision.revision_number > 0);
    unique(revision.selected_version_ids);
    const entities = index(research.entities, value => value.entity_id);
    const claims = index(research.claims, value => value.claim_id);
    const relations = index(research.relations, value => value.relation_id);
    const observations = index(research.observations, value => value.observation_id);
    for (const value of [...research.entities, ...research.claims, ...research.relations, ...research.observations]) {
      requireDisplay(value.workspace_id === research.workspace_id);
    }
    const documents = new Map<string, SourceDocument>();
    const versions = new Map<string, EvidenceBundle['version']>();
    const representations = new Set<string>();
    const allCitations = new Map<string, CitationDisplay>();
    const citations = new Map<string, CitationDisplay>();
    const selectedDocuments = new Set<string>();
    const selected = new Set(revision.selected_version_ids);
    for (const proof of research.evidence) {
      requireDisplay(proof.schema_version === 1 && proof.document.workspace_id === research.workspace_id
        && proof.version.document_id === proof.document.document_id
        && proof.representation.document_version_id === proof.version.version_id
        && !representations.has(proof.representation.representation_id));
      consistent(documents, proof.document.document_id, proof.document);
      consistent(versions, proof.version.version_id, proof.version);
      representations.add(proof.representation.representation_id);
      if (selected.has(proof.version.version_id)) selectedDocuments.add(proof.document.document_id);
      for (const citation of proof.citations) {
        requireDisplay(!allCitations.has(citation.citation_id)
          && citation.document_version_id === proof.version.version_id
          && citation.representation_id === proof.representation.representation_id
          && ['text', 'pdf', 'table_cell'].includes(citation.selector.kind));
        const display = {citation, proof};
        allCitations.set(citation.citation_id, display);
        if (selected.has(proof.version.version_id)) citations.set(citation.citation_id, display);
      }
    }
    requireDisplay(revision.selected_version_ids.every(id => versions.has(id)));
    const context: DisplayContext = {citations, claims, entities, relations, observations, documents, supportReviews:research.support_reviews};
    const cite = (ids: string[], selectedOnly = true) => {
      unique(ids, 1);
      requireDisplay(ids.every(id => (selectedOnly ? citations : allCitations).has(id)));
    };
    const checkClaim = (claim: Claim, selectedOnly = true) => {
      basis(claim.basis);
      cite(claim.citation_ids, selectedOnly);
      requireDisplay(claim.speaker_entity_id === null || entities.has(claim.speaker_entity_id));
      unique(claim.subject_entity_ids);
      requireDisplay(claim.subject_entity_ids.every(id => entities.has(id)));
    };
    // No fallback by name or by array position, even for two identically named entities.
    const endpoint = (value: Relation['source']) => {
      switch (value.kind) {
        case 'entity': requireDisplay(entities.has(value.entity_id)); break;
        case 'claim': {
          const claim = claims.get(value.claim_id);
          requireDisplay(claim); checkClaim(claim); break;
        }
        case 'document': requireDisplay(selectedDocuments.has(value.document_id)); break;
        default: requireDisplay(false);
      }
    };
    index(draft.modules, value => value.module_id);
    requireDisplay(draft.outcome === 'answer' || draft.outcome === 'insufficient_evidence' || draft.outcome === 'clarification_needed');
    if (draft.outcome !== 'answer') {
      requireDisplay(draft.modules.length === 0 && typeof draft.message === 'string' && draft.message.trim());
      return {status: 'message', outcome: draft.outcome, message: draft.message};
    }
    requireDisplay(draft.modules.length > 0 && draft.message === null);
    for (const module of draft.modules) {
      requireDisplay(['half', 'full'].includes(module.span) && module.title.trim());
      cite(module.citation_ids);
      let records: {citation_ids: string[]}[] = [];
      switch (module.kind) {
        case 'evidence': break;
        case 'summary': case 'comparison': case 'timeline': {
          unique(module.claim_ids, module.kind === 'comparison' ? 2 : 1);
          records = module.claim_ids.map(id => {
            const claim = claims.get(id); requireDisplay(claim); checkClaim(claim);
            if (module.kind === 'timeline') { requireDisplay(claim.valid_period); interval(claim.valid_period); }
            return claim;
          });
          break;
        }
        case 'graph': {
          unique(module.relation_ids, 1);
          records = module.relation_ids.map(id => {
            const relation = relations.get(id); requireDisplay(relation);
            requireDisplay(relation.ontology_version === 'issuedigest-relations-v1'
              && ['introduced_by', 'reviewed_by', 'alternative_to', 'supports', 'contradicts', 'mentions'].includes(relation.predicate));
            basis(relation.basis); cite(relation.citation_ids);
            endpoint(relation.source); endpoint(relation.target);
            return relation;
          });
          break;
        }
        case 'chart': {
          requireDisplay(module.chart_type === 'bar');
          unique(module.observation_ids, 2);
          const values = module.observation_ids.map(id => {
            const value = observations.get(id); requireDisplay(value);
            requireDisplay(typeof value.value === 'string' && value.value.length <= 128
              && /^-?(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(value.value));
            cite(value.citation_ids);
            requireDisplay(value.subject_entity_id === null || entities.has(value.subject_entity_id));
            return value;
          });
          sameChartContext(values); records = values; break;
        }
        default: requireDisplay(false);
      }
      if (module.kind !== 'evidence') {
        const union = new Set(records.flatMap(record => record.citation_ids));
        requireDisplay(union.size === module.citation_ids.length && module.citation_ids.every(id => union.has(id)));
      }
      const actions = new Set<string>();
      for (const action of module.actions) {
        const key = JSON.stringify(action);
        requireDisplay(!actions.has(key)); actions.add(key);
        switch (action.kind) {
          case 'open_evidence': requireDisplay(module.citation_ids.includes(action.citation_id)); break;
          case 'select_document': requireDisplay(selectedDocuments.has(action.document_id)); break;
          case 'ask_question': requireDisplay(typeof action.question === 'string' && action.question.trim()); break;
          case 'sort': requireDisplay(['source_date', 'title'].includes(action.field) && ['asc', 'desc'].includes(action.direction)); break;
          default: requireDisplay(false);
        }
      }
    }
    return {status: 'ready', modules: draft.modules, context};
  } catch {
    // No exception details, identifiers, or source text in rejection diagnostics.
    return {status: 'rejected'};
  }
}
