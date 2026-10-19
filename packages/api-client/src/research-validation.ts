/** Raw-response validation for the bounded Canvas shape produced by research-v1/v2/v3/v4/v5/v6/v7/v8. */
import {validResearchClassifications} from './research-classification';
import { isDisplayEvidence } from './evidence';
import { hasKeys, isId, isObject } from './protected-request';

const same = (a: unknown, b: unknown) => isId(a) && isId(b) && a.toLowerCase() === b.toLowerCase();
const nonblank = (value: unknown, max: number, codePoints = false) =>
  typeof value === 'string' && (codePoints ? Array.from(value).length : value.length) <= max && value.trim().length > 0;

export {exactDay, exactTimestamp} from './research-time';
import {exactDay, exactTimestamp} from './research-time';

function ids(value: unknown, minimum: number, maximum: number): string[] | null {
  if (!Array.isArray(value) || value.length < minimum || value.length > maximum
    || value.some(item => !isId(item))) return null;
  const result = value as string[];
  return new Set(result.map(id => id.toLowerCase())).size === result.length ? result : null;
}

function selectedCitations(value: unknown, selected: Set<string>, max: number): string[] | null {
  const result = ids(value, 1, max);
  return result && result.every(id => selected.has(id.toLowerCase())) ? result : null;
}

function exactSet(actual: string[], expected: Set<string>): boolean {
  return actual.length === expected.size && actual.every(id => expected.has(id.toLowerCase()));
}

export function validResearchCanvas(
  value: unknown, workspace: string, runId: string, titles: unknown,
): boolean {
  if (!isObject(value) || !hasKeys(value, ['research', 'revision'])
    || !isObject(value.research) || !isObject(value.revision) || !isObject(titles)) return false;
  const { research, revision } = value;
  if (!hasKeys(research, ['schema_version', 'workspace_id', 'evidence', 'entities', 'claims',
    'relations', 'observations', 'support_reviews']) || research.schema_version !== 1
    || !same(research.workspace_id, workspace) || !Array.isArray(research.evidence)
    || research.evidence.length < 1 || research.evidence.length > 5
    || !Array.isArray(research.entities) || research.entities.length !== 0
    || !Array.isArray(research.relations) || research.relations.length !== 0
    || !Array.isArray(research.observations) || research.observations.length !== 0
    || !Array.isArray(research.support_reviews)
    || !Array.isArray(research.claims) || research.claims.length > 12) return false;
  if (!hasKeys(revision, ['schema_version', 'revision_id', 'workspace_id', 'run_id',
    'revision_number', 'parent_revision_id', 'selected_version_ids', 'draft',
    'validated_at', 'validation_policy']) || revision.schema_version !== 1
    || !isId(revision.revision_id) || !same(revision.workspace_id, workspace)
    || !same(revision.run_id, runId) || revision.revision_number !== 1
    || revision.parent_revision_id !== null || revision.validation_policy !== 'issuedigest-canvas-v1'
    || !exactTimestamp(revision.validated_at) || !isObject(revision.draft)) return false;

  const documents = new Set<string>();
  const documentMetadata = new Map<string, string>();
  const versions = new Set<string>();
  const representations = new Set<string>();
  const citations = new Set<string>();
  const quoteByCitation = new Map<string, string>();
  for (const proof of research.evidence) {
    if (!isDisplayEvidence(proof, workspace)) return false;
    const document = proof.document.document_id.toLowerCase();
    const version = proof.version.version_id.toLowerCase();
    const representation = proof.representation.representation_id.toLowerCase();
    const metadata = JSON.stringify(proof.document);
    if (versions.has(version) || representations.has(representation)
      || (documentMetadata.has(document) && documentMetadata.get(document) !== metadata)) return false;
    documents.add(document); versions.add(version); representations.add(representation);
    documentMetadata.set(document, metadata);
    for (const citation of proof.citations) {
      const id = citation.citation_id.toLowerCase();
      if (citations.has(id)) return false;
      citations.add(id); quoteByCitation.set(id, citation.selector.quote);
    }
  }
  const selected = ids(revision.selected_version_ids, 1, 5);
  if (!selected || !exactSet(selected, versions)) return false;
  if (Object.keys(titles).length !== documents.size
    || Object.entries(titles).some(([id, title]) => !isId(id) || !documents.has(id.toLowerCase())
      || !nonblank(title, 255) || isId(title))) return false;

  const claims = new Map<string, {citations: string[]; day: string | null}>();
  for (const claim of research.claims) {
    if (!isObject(claim) || !hasKeys(claim, ['claim_id', 'workspace_id', 'text', 'basis',
      'speaker_entity_id', 'subject_entity_ids', 'citation_ids', 'valid_period',
      'raw_event_time_text', 'derivation']) || !isId(claim.claim_id)
      || claims.has(claim.claim_id.toLowerCase()) || !same(claim.workspace_id, workspace)
      || !nonblank(claim.text, 500, isObject(claim.derivation) && ['research-v6', 'research-v7', 'research-v8'].includes(claim.derivation.method_version as string)) || claim.basis !== 'inference'
      || claim.speaker_entity_id !== null || !Array.isArray(claim.subject_entity_ids)
      || claim.subject_entity_ids.length !== 0 || claim.raw_event_time_text !== null
      || !isObject(claim.derivation)
      || !hasKeys(claim.derivation, ['method', 'method_version', 'rationale'])
      || claim.derivation.method !== 'pydantic-ai'
      || !['research-v1', 'research-v2', 'research-v3', 'research-v4', 'research-v5', 'research-v6', 'research-v7', 'research-v8'].includes(claim.derivation.method_version as string)
      || !nonblank(claim.derivation.rationale, 200)) return false;
    const claimCitations = selectedCitations(claim.citation_ids, citations, 3);
    if (!claimCitations) return false;
    let period: string | null = null;
    if (claim.valid_period !== null) {
      if (!isObject(claim.valid_period)
        || !hasKeys(claim.valid_period, ['start_date', 'end_date'])
        || !exactDay(claim.valid_period.start_date)
        || claim.valid_period.start_date !== claim.valid_period.end_date) return false;
      const citedDay = claim.valid_period.start_date;
      if (!claimCitations.some(id => quoteByCitation.get(id.toLowerCase())?.includes(citedDay))) return false;
      period = citedDay;
    }
    claims.set(claim.claim_id.toLowerCase(), {citations: claimCitations, day: period});
  }

  if (!validResearchClassifications(research, revision)) return false;

  const v6 = research.claims.some(claim => isObject(claim) && isObject(claim.derivation) && ['research-v6', 'research-v7', 'research-v8'].includes(claim.derivation.method_version as string));
  const draft = revision.draft;
  if (!hasKeys(draft, ['schema_version', 'draft_id', 'outcome', 'modules', 'message'])
    || draft.schema_version !== 1 || !isId(draft.draft_id)
    || !Array.isArray(draft.modules) || draft.modules.length > 4
    || !['answer', 'insufficient_evidence', 'clarification_needed'].includes(draft.outcome as string)) return false;
  if (draft.outcome !== 'answer') {
    return draft.modules.length === 0 && claims.size === 0 && nonblank(draft.message, 500);
  }
  if (draft.message !== null || draft.modules.length < 2) return false;

  const moduleIds = new Set<string>();
  const usedClaims = new Set<string>();
  const allCited = new Set<string>();
  let evidenceModules = 0;
  for (const [index, module] of draft.modules.entries()) {
    if (!isObject(module)) return false;
    const evidence = module.kind === 'evidence';
    const expectedKeys = ['module_id', 'title', 'span', 'citation_ids', 'actions', 'kind'];
    if (!hasKeys(module, evidence ? expectedKeys : [...expectedKeys, 'claim_ids'])
      || !isId(module.module_id) || moduleIds.has(module.module_id.toLowerCase())
      || !nonblank(module.title, 100, v6) || module.span !== 'full'
      || !['summary', 'comparison', 'timeline', 'evidence'].includes(module.kind as string)) return false;
    moduleIds.add(module.module_id.toLowerCase());
    const moduleCitations = selectedCitations(module.citation_ids, citations, evidence ? 36 : 12);
    if (!moduleCitations || !Array.isArray(module.actions)
      || module.actions.length !== moduleCitations.length) return false;
    const cited = new Set(moduleCitations.map(id => id.toLowerCase()));
    const actions = new Set<string>();
    for (const action of module.actions) {
      if (!isObject(action) || !hasKeys(action, ['kind', 'citation_id'])
        || action.kind !== 'open_evidence' || !isId(action.citation_id)
        || !cited.has(action.citation_id.toLowerCase())
        || actions.has(action.citation_id.toLowerCase())) return false;
      actions.add(action.citation_id.toLowerCase());
    }
    if (evidence) {
      evidenceModules += 1;
      if (index !== draft.modules.length - 1 || evidenceModules !== 1
        || !exactSet(moduleCitations, allCited)) return false;
      continue;
    }
    const claimIds = ids(module.claim_ids, module.kind === 'comparison' ? 2 : 1, 4);
    if (!claimIds) return false;
    const union = new Set<string>();
    for (const id of claimIds) {
      const claim = claims.get(id.toLowerCase());
      if (!claim || usedClaims.has(id.toLowerCase())
        || (module.kind === 'timeline' && claim.day === null)
        || (module.kind !== 'timeline' && claim.day !== null)) return false;
      usedClaims.add(id.toLowerCase());
      claim.citations.forEach(citation => union.add(citation.toLowerCase()));
    }
    if (!exactSet(moduleCitations, union)) return false;
    moduleCitations.forEach(id => allCited.add(id.toLowerCase()));
  }
  return evidenceModules === 1 && usedClaims.size === claims.size;
}
