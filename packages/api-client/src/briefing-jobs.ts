import type { components } from './schema';
import {
  hasKeys,
  isId,
  isObject,
  protectedRequest,
  type ProtectedFailure,
  type ProtectedOptions,
} from './protected-request';
export type BriefingJobView = components['schemas']['BriefingJobView'];
export type BriefingQuoteView = components['schemas']['BriefingQuoteView'];
export type BriefingJobOptions = ProtectedOptions;
export class BriefingJobError extends Error {
  constructor(
    public readonly kind: ProtectedFailure,
    public readonly requestId?: string,
  ) {
    super('브리핑 요청을 처리하지 못했습니다.');
    this.name = 'BriefingJobError';
  }
}
const text = (v: unknown, max: number): v is string =>
  typeof v === 'string' && v.trim().length > 0 && Array.from(v).length <= max;
const exact = (v: unknown, keys: string[]): v is Record<string, unknown> =>
  isObject(v) && hasKeys(v, keys);
const list = (
  v: unknown,
  min: number,
  max: number,
  check: (x: unknown) => boolean,
): v is unknown[] =>
  Array.isArray(v) && v.length >= min && v.length <= max && v.every(check);
function date(v: unknown) {
  if (
    typeof v !== 'string' ||
    !/^\d{4}-\d{2}-\d{2}$/.test(v) ||
    v.startsWith('0000')
  )
    return false;
  const d = new Date(`${v}T00:00:00Z`);
  return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === v;
}
function quote(v: unknown) {
  return (
    exact(v, [
      'snapshot_id',
      'citation_id',
      'source_title',
      'start',
      'end',
      'text',
      'citation_quote',
    ]) &&
    isId(v.snapshot_id) &&
    isId(v.citation_id) &&
    text(v.source_title, 500) &&
    text(v.text, 20000) &&
    text(v.citation_quote, 20000) &&
    typeof v.start === 'number' &&
    Number.isSafeInteger(v.start) &&
    v.start >= 0 &&
    typeof v.end === 'number' &&
    Number.isSafeInteger(v.end) &&
    v.end > v.start &&
    v.end <= Array.from(v.citation_quote).length &&
    Array.from(v.citation_quote).slice(v.start, v.end).join('') === v.text
  );
}
function moduleView(v: unknown) {
  if (
    !exact(v, ['kind', 'title', 'claims']) ||
    !['summary', 'comparison', 'timeline'].includes(String(v.kind)) ||
    !text(v.title, 100)
  )
    return false;
  return list(
    v.claims,
    v.kind === 'comparison' ? 2 : 1,
    4,
    (c) =>
      exact(c, ['text', 'epistemic_status', 'event_date', 'quotes']) &&
      text(c.text, 400) &&
      ['source_statement', 'uncertain'].includes(String(c.epistemic_status)) &&
      (v.kind === 'timeline' ? date(c.event_date) : c.event_date === null) &&
      list(c.quotes, 1, 960, quote),
  );
}
function result(v: unknown) {
  if (
    !exact(v, ['outcome', 'message', 'modules', 'additional_quotes']) ||
    !list(v.additional_quotes, 0, 960, quote) ||
    !list(v.modules, 0, 3, moduleView)
  )
    return false;
  return v.outcome === 'answer'
    ? v.message === null &&
        v.modules.length > 0 &&
        isObject(v.modules[0]) &&
        v.modules[0].kind === 'summary' &&
        v.modules.slice(1).every((m) => isObject(m) && m.kind !== 'summary')
    : v.outcome === 'insufficient_evidence' &&
        text(v.message, 500) &&
        v.modules.length === 0;
}
function valid(v: unknown, jobId: string): v is BriefingJobView {
  return (
    exact(v, ['job_id', 'question', 'status', 'result']) &&
    isId(v.job_id) &&
    v.job_id.toLowerCase() === jobId.toLowerCase() &&
    text(v.question, 1500) &&
    [
      'pending',
      'running',
      'completed',
      'failed',
      'cancelled',
      'indeterminate',
    ].includes(String(v.status)) &&
    (v.status === 'completed' ? result(v.result) : v.result === null)
  );
}
function request(
  workspaceId: string,
  jobId: string,
  cancel: boolean,
  options: ProtectedOptions,
) {
  if (!isId(workspaceId) || !isId(jobId))
    return Promise.reject(new BriefingJobError('invalid-query'));
  return protectedRequest(
    `/api/v1/workspaces/${workspaceId}/briefing-jobs/${jobId}${cancel ? '/cancel' : ''}`,
    cancel ? 'POST' : 'GET',
    (v): v is BriefingJobView => valid(v, jobId),
    (kind, id) => new BriefingJobError(kind, id),
    options,
    cancel ? '{}' : undefined,
  );
}
export const getBriefingJob = (
  workspaceId: string,
  jobId: string,
  options: ProtectedOptions = {},
) => request(workspaceId, jobId, false, options);
export const cancelBriefingJob = (
  workspaceId: string,
  jobId: string,
  options: ProtectedOptions = {},
) => request(workspaceId, jobId, true, options);
