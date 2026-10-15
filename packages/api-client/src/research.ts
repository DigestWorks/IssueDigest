import type { components } from './schema';
import { hasKeys, isId, isObject, protectedRequest, type ProtectedFailure, type ProtectedOptions } from './protected-request';
import { isDisplayEvidence } from './evidence';

export type ResearchSourceCatalog = components['schemas']['ResearchSourceCatalog'];
export type ResearchRun = components['schemas']['ResearchRun'];
export type ResearchRunList = components['schemas']['ResearchRunList'];
export type ResearchRequest = components['schemas']['ResearchRequest'];
export type ResearchOptions = ProtectedOptions;
export type ResearchFailure = ProtectedFailure;
export class ResearchError extends Error {
  constructor(public readonly kind: ResearchFailure, public readonly requestId?: string) {
    super(`Research request failed: ${kind}`); this.name = 'ResearchError';
  }
}
const fail = (kind: ProtectedFailure, requestId?: string) => new ResearchError(kind, requestId);
const nonblank = (v: unknown): v is string => typeof v === 'string' && v.trim().length > 0;
const timestamp = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(v) && Number.isFinite(Date.parse(v));
const day = (v: unknown): v is string => {
  if (typeof v !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return false;
  const [year, month, date] = v.split('-').map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year > 0 && month >= 1 && month <= 12 && date >= 1 && date <= days[month - 1]!;
};
const nonnegative = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const same = (a: unknown, b: unknown) => isId(a) && isId(b) && a.toLowerCase() === b.toLowerCase();
const url = (v: unknown) => {
  if (v === null) return true;
  if (typeof v !== 'string' || /[\s\\]/u.test(v)) return false;
  try { const parsed = new URL(v); return ['http:', 'https:'].includes(parsed.protocol) && !parsed.username && !parsed.password && !/^https?:\/\/[^/?#]*@/i.test(v); } catch { return false; }
};
function validSources(value: unknown, workspace: string): value is ResearchSourceCatalog {
  if (!isObject(value) || !hasKeys(value, ['workspace_id','items']) || !same(value.workspace_id, workspace) || !Array.isArray(value.items) || value.items.length > 100) return false;
  const seen = new Set<string>();
  for (const item of value.items) {
    if (!isObject(item) || !hasKeys(item, ['snapshot_id','document_id','title','source_kind','bill_number','proposed_on','collected_at','canonical_url','citation_count','excerpt']) || !isId(item.snapshot_id) || !isId(item.document_id) || seen.has(item.snapshot_id.toLowerCase()) || !nonblank(item.title) || item.title.length > 255 || isId(item.title) || !['bill','legal_text','government_document','news','poll','statistics','petition','other'].includes(String(item.source_kind)) || (item.bill_number !== null && !/^[0-9]{7}$/.test(String(item.bill_number))) || (item.proposed_on !== null && !day(item.proposed_on)) || !timestamp(item.collected_at) || !url(item.canonical_url) || !nonnegative(item.citation_count) || typeof item.excerpt !== 'string' || Array.from(item.excerpt).length > 160) return false;
    seen.add(item.snapshot_id.toLowerCase());
  }
  return true;
}
const statuses = ['queued','retrieving','generating','validating','completed','failed','cancelled'];
const errors = ['insufficient_evidence','model_unavailable','generation_failed','authority_changed','cancelled'];
function validCanvas(value: unknown, workspace: string, runId: string, titles: unknown): boolean {
  if (!isObject(value) || !hasKeys(value, ['research','revision']) || !isObject(value.research) || !isObject(value.revision) || !same(value.research.workspace_id, workspace) || !same(value.revision.workspace_id, workspace) || !same(value.revision.run_id, runId) || !Array.isArray(value.research.evidence) || !Array.isArray(value.research.claims) || !isObject(value.revision.draft) || !Array.isArray(value.revision.draft.modules) || !isObject(titles)) return false;
  const docs = new Set<string>(); const citations = new Set<string>(); const versions = new Set<string>();
  for (const evidence of value.research.evidence) {
    if (!isDisplayEvidence(evidence, workspace) || !isObject(evidence.document) || !isObject(evidence.version) || !Array.isArray(evidence.citations)) return false;
    docs.add(String(evidence.document.document_id).toLowerCase()); versions.add(String(evidence.version.version_id).toLowerCase());
    evidence.citations.forEach(citation => { if (isObject(citation) && isId(citation.citation_id)) citations.add(citation.citation_id.toLowerCase()); });
  }
  if (Object.keys(titles).length !== docs.size || Object.entries(titles).some(([key, title]) => !docs.has(key.toLowerCase()) || !nonblank(title) || isId(title))) return false;
  if (!Array.isArray(value.revision.selected_version_ids) || value.revision.selected_version_ids.some(version => !isId(version) || !versions.has(version.toLowerCase()))) return false;
  const claims = new Set<string>();
  for (const claim of value.research.claims) {
    if (!isObject(claim) || !isId(claim.claim_id) || claims.has(claim.claim_id.toLowerCase()) || !same(claim.workspace_id, workspace) || !nonblank(claim.text) || claim.basis !== 'inference' || !isObject(claim.derivation) || !Array.isArray(claim.citation_ids) || !claim.citation_ids.length || claim.citation_ids.some(c => !isId(c) || !citations.has(c.toLowerCase()))) return false;
    claims.add(claim.claim_id.toLowerCase());
  }
  const draft = value.revision.draft;
  const modules = draft.modules;
  if (!Array.isArray(modules)) return false;
  if (!['answer','insufficient_evidence','clarification_needed'].includes(String(draft.outcome)) || (draft.outcome === 'answer' && (!modules.length || draft.message !== null)) || (draft.outcome !== 'answer' && (modules.length || !nonblank(draft.message)))) return false;
  for (const module of modules) {
    if (!isObject(module)) return false;
    const moduleCitations = module.citation_ids;
    if (!isId(module.module_id) || !nonblank(module.title) || !['summary','comparison','timeline','evidence'].includes(String(module.kind)) || !Array.isArray(moduleCitations) || !moduleCitations.length || moduleCitations.some(c => !isId(c) || !citations.has(c.toLowerCase())) || !Array.isArray(module.actions) || module.actions.some(action => !isObject(action) || action.kind !== 'open_evidence' || !isId(action.citation_id) || !moduleCitations.includes(action.citation_id))) return false;
    if (module.kind !== 'evidence' && (!Array.isArray(module.claim_ids) || !module.claim_ids.length || module.claim_ids.some(c => !isId(c) || !claims.has(c.toLowerCase())))) return false;
  }
  return true;
}
function validRun(value: unknown, workspace: string): value is ResearchRun {
  if (!isObject(value) || !hasKeys(value, ['run_id','workspace_id','request_id','question','snapshot_ids','parent_run_id','status','error_code','created_at','updated_at','events','result','model','input_tokens','output_tokens']) || !isId(value.run_id) || !same(value.workspace_id, workspace) || !isId(value.request_id) || !nonblank(value.question) || value.question.length > 1500 || !Array.isArray(value.snapshot_ids) || value.snapshot_ids.length < 1 || value.snapshot_ids.length > 3 || value.snapshot_ids.some(id => !isId(id)) || new Set(value.snapshot_ids).size !== value.snapshot_ids.length || (value.parent_run_id !== null && !isId(value.parent_run_id)) || !statuses.includes(String(value.status)) || (value.error_code !== null && !errors.includes(String(value.error_code))) || !timestamp(value.created_at) || !timestamp(value.updated_at) || value.model !== 'gpt-5.4-mini' || !nonnegative(value.input_tokens) || !nonnegative(value.output_tokens) || !Array.isArray(value.events) || !value.events.length) return false;
  for (let i = 0; i < value.events.length; i++) { const e = value.events[i]; if (!isObject(e) || !hasKeys(e, ['sequence','status','created_at']) || e.sequence !== i + 1 || !statuses.includes(String(e.status)) || !timestamp(e.created_at)) return false; }
  if (value.events[value.events.length - 1].status !== value.status) return false;
  if (value.status === 'completed') return isObject(value.result) && hasKeys(value.result, ['canvas','source_titles']) && validCanvas(value.result.canvas, workspace, value.run_id, value.result.source_titles);
  return value.result === null;
}
function validList(value: unknown, workspace: string): value is ResearchRunList {
  return isObject(value) && hasKeys(value, ['workspace_id','items']) && same(value.workspace_id, workspace) && Array.isArray(value.items) && value.items.length <= 100 && value.items.every(item => validRun(item, workspace));
}
function base(workspace: string) { if (!isId(workspace)) throw fail('malformed'); return `/api/v1/workspaces/${workspace}/research`; }
export function getResearchSources(workspace: string, options: ResearchOptions = {}) { const path = base(workspace); return protectedRequest(`${path}/sources`, 'GET', (value): value is ResearchSourceCatalog => validSources(value, workspace), fail, options); }
export function listResearchRuns(workspace: string, options: ResearchOptions = {}) { const path = base(workspace); return protectedRequest(path, 'GET', (value): value is ResearchRunList => validList(value, workspace), fail, options); }
export function getResearchRun(workspace: string, runId: string, options: ResearchOptions = {}) { const path = base(workspace); if (!isId(runId)) throw fail('malformed'); return protectedRequest(`${path}/${runId}`, 'GET', (value): value is ResearchRun => validRun(value, workspace) && same(value.run_id, runId), fail, options); }
export function submitResearch(workspace: string, input: ResearchRequest, options: ResearchOptions = {}) { const path = base(workspace); if (!isId(input.request_id) || !nonblank(input.question) || input.question.length > 1500 || !Array.isArray(input.snapshot_ids) || input.snapshot_ids.length < 1 || input.snapshot_ids.length > 3 || input.snapshot_ids.some(id => !isId(id)) || new Set(input.snapshot_ids.map(x => x.toLowerCase())).size !== input.snapshot_ids.length || (input.parent_run_id !== null && !isId(input.parent_run_id))) throw fail('malformed'); return protectedRequest(path, 'POST', (value): value is ResearchRun => validRun(value, workspace) && same(value.request_id, input.request_id), fail, options, JSON.stringify(input)); }
export function cancelResearchRun(workspace: string, runId: string, options: ResearchOptions = {}) { const path = base(workspace); if (!isId(runId)) throw fail('malformed'); return protectedRequest(`${path}/${runId}/cancel`, 'POST', (value): value is ResearchRun => validRun(value, workspace) && same(value.run_id, runId), fail, options, '{}'); }
