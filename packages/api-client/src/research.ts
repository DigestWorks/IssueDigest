import type { components } from './schema';
import { hasKeys, isId, isObject, protectedRequest, type ProtectedFailure, type ProtectedOptions } from './protected-request';
import { exactTimestamp, validResearchCanvas } from './research-validation';

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
const timestamp = exactTimestamp;
const nonnegative = (v: unknown): v is number => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0;
const same = (a: unknown, b: unknown) => isId(a) && isId(b) && a.toLowerCase() === b.toLowerCase();
const statuses = ['queued','retrieving','generating','validating','completed','failed','cancelled'];
const errors = ['insufficient_evidence','model_unavailable','generation_failed','authority_changed','cancelled'];
const rank: Record<string, number> = { queued: 0, retrieving: 1, generating: 2, validating: 3, completed: 4, failed: 4, cancelled: 4 };
const validCanvas = validResearchCanvas;
function validRun(value: unknown, workspace: string): value is ResearchRun {
  if (!isObject(value) || !hasKeys(value, ['run_id','workspace_id','request_id','question','snapshot_ids','parent_run_id','status','error_code','created_at','updated_at','events','result','model','input_tokens','output_tokens']) || !isId(value.run_id) || !same(value.workspace_id, workspace) || !isId(value.request_id) || !nonblank(value.question) || value.question.length > 1500 || !Array.isArray(value.snapshot_ids) || value.snapshot_ids.length > 5 || value.snapshot_ids.some(id => !isId(id)) || new Set(value.snapshot_ids.map(id => id.toLowerCase())).size !== value.snapshot_ids.length || (value.parent_run_id !== null && !isId(value.parent_run_id)) || typeof value.status !== 'string' || !statuses.includes(value.status) || (value.error_code !== null && (typeof value.error_code !== 'string' || !errors.includes(value.error_code))) || !timestamp(value.created_at) || !timestamp(value.updated_at) || value.model !== 'gpt-5.4-mini' || !nonnegative(value.input_tokens) || value.input_tokens > 24000 || !nonnegative(value.output_tokens) || value.output_tokens > 5000 || value.input_tokens + value.output_tokens > 24000 || !Array.isArray(value.events) || value.events.length < 1 || value.events.length > 5) return false;
  for (let i = 0; i < value.events.length; i++) {
    const e = value.events[i];
    if (!isObject(e) || !hasKeys(e, ['sequence','status','created_at']) || e.sequence !== i + 1 || typeof e.status !== 'string' || !statuses.includes(e.status) || !timestamp(e.created_at) || (i === 0 && e.status !== 'queued') || (i > 0 && rank[e.status]! <= rank[String(value.events[i - 1].status)]!)) return false;
  }
  if (value.events[value.events.length - 1].status !== value.status || (value.status === 'completed' && value.error_code !== null) || (value.status === 'cancelled' && value.error_code !== 'cancelled') || (value.status === 'failed' && value.error_code === null) || (!['completed','cancelled','failed'].includes(value.status) && value.error_code !== null)) return false;
  if (value.status === 'completed') return value.snapshot_ids.length >= 1 && isObject(value.result) && hasKeys(value.result, ['canvas','source_titles']) && validCanvas(value.result.canvas, workspace, value.run_id, value.result.source_titles);
  return value.result === null;
}
function validList(value: unknown, workspace: string): value is ResearchRunList {
  return isObject(value) && hasKeys(value, ['workspace_id','items']) && same(value.workspace_id, workspace) && Array.isArray(value.items) && value.items.length <= 100 && value.items.every(item => validRun(item, workspace));
}
function base(workspace: string) { if (!isId(workspace)) throw fail('malformed'); return `/api/v1/workspaces/${workspace}/research`; }
export function listResearchRuns(workspace: string, options: ResearchOptions = {}) { const path = base(workspace); return protectedRequest(path, 'GET', (value): value is ResearchRunList => validList(value, workspace), fail, options); }
export function getResearchRun(workspace: string, runId: string, options: ResearchOptions = {}) { const path = base(workspace); if (!isId(runId)) throw fail('malformed'); return protectedRequest(`${path}/${runId}`, 'GET', (value): value is ResearchRun => validRun(value, workspace) && same(value.run_id, runId), fail, options); }
export function submitResearch(workspace: string, input: ResearchRequest, options: ResearchOptions = {}) { const path = base(workspace); if (!isObject(input) || !hasKeys(input, input.parent_run_id === undefined ? ['request_id', 'question'] : ['request_id', 'question', 'parent_run_id']) || !isId(input.request_id) || !nonblank(input.question) || input.question.length > 1500 || (input.parent_run_id != null && !isId(input.parent_run_id))) throw fail('malformed'); return protectedRequest(path, 'POST', (value): value is ResearchRun => validRun(value, workspace) && same(value.request_id, input.request_id), fail, options, JSON.stringify(input)); }
export function cancelResearchRun(workspace: string, runId: string, options: ResearchOptions = {}) { const path = base(workspace); if (!isId(runId)) throw fail('malformed'); return protectedRequest(`${path}/${runId}/cancel`, 'POST', (value): value is ResearchRun => validRun(value, workspace) && same(value.run_id, runId), fail, options, '{}'); }
