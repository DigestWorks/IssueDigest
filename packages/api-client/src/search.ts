import type { components } from './schema';
import { hasKeys, isId, isObject, protectedRequest, type ProtectedFailure, type ProtectedOptions } from './protected-request';

export type EvidenceSearchQuery = components['schemas']['EvidenceSearchQuery'];
export type EvidenceSearchResult = components['schemas']['EvidenceSearchResult'];
export type EvidenceSearchHit = components['schemas']['EvidenceSearchHit'];
export type SearchFailure = ProtectedFailure;
export type SearchOptions = ProtectedOptions;
export type EvidenceSearchInput = Pick<EvidenceSearchQuery, 'terms'> & Partial<Omit<EvidenceSearchQuery, 'terms'>>;

export class SearchError extends Error {
  constructor(public readonly kind: SearchFailure, public readonly requestId?: string) {
    super(`Search request failed: ${kind}`); this.name = 'SearchError';
  }
}

const kinds = ['bill', 'legal_text', 'government_document', 'news', 'poll', 'statistics', 'petition', 'other'];
const queryKeys = ['terms', 'limit', 'provider', 'source_id', 'source_kind', 'collected_from', 'collected_to'];
const integer = (value: unknown, max: number): value is number => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 && value <= max;
const validUnicode = (value: string) => !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value);
const fold = (value: string) => value.replace(/[A-Z]/g, char => char.toLowerCase());
const nonblank = (value: unknown, max: number): value is string => typeof value === 'string' && validUnicode(value) && value.trim().length > 0 && Array.from(value).length <= max;
const nullableText = (value: unknown): value is string | null => value === null || typeof value === 'string';
const sameId = (a: unknown, b: unknown) => isId(a) && isId(b) && a.toLowerCase() === b.toLowerCase();

function timestamp(value: unknown, utcOnly: boolean): value is string {
  if (typeof value !== 'string') return false;
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!parts || !Number.isFinite(Date.parse(value))) return false;
  const [, year, month, day, hour, minute, second] = parts.map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31];
  const offset = parts[8];
  const match = /^([+-])(\d{2}):(\d{2})$/.exec(offset);
  return year > 0 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1] && hour < 24 && minute < 60 && second < 60 && (!match || (Number(match[2]) <= 23 && Number(match[3]) <= 59)) && (!utcOnly || offset === 'Z' || offset === '+00:00' || offset === '-00:00');
}

function sourceUrl(value: unknown) {
  if (value === null) return true;
  if (typeof value !== 'string' || /[\s\\]/u.test(value) || Array.from(value).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)) return false;
  try {
    const url = new URL(value); const authority = /^https?:\/\/([^/?#]*)/i.exec(value)?.[1];
    return ['https:', 'http:'].includes(url.protocol) && Boolean(authority) && !authority?.includes('@') && !url.username && !url.password;
  } catch { return false; }
}

function terms(value: unknown): value is string[] {
  if (!Array.isArray(value) || value.length < 1 || value.length > 8) return false;
  const folded = new Set<string>();
  for (const term of value) {
    if (!nonblank(term, 64) || term !== term.trim() || Array.from(term).length < 1) return false;
    const key = fold(term);
    if (folded.has(key)) return false;
    folded.add(key);
  }
  return true;
}

function isQuery(value: unknown, full: boolean): value is EvidenceSearchQuery {
  if (!isObject(value) || Object.keys(value).some(key => !queryKeys.includes(key)) || !terms(value.terms)) return false;
  if (full && !hasKeys(value, queryKeys)) return false;
  const limit = value.limit === undefined ? 20 : value.limit;
  if (!integer(limit, 20) || limit < 1) return false;
  for (const key of ['provider', 'source_id']) if (value[key] !== undefined && value[key] !== null && !nonblank(value[key], 1024)) return false;
  if (value.source_kind !== undefined && value.source_kind !== null && !kinds.includes(value.source_kind as string)) return false;
  for (const key of ['collected_from', 'collected_to']) if (value[key] !== undefined && value[key] !== null && !timestamp(value[key], true)) return false;
  const from = value.collected_from, to = value.collected_to;
  if (typeof from === 'string' && typeof to === 'string' && Date.parse(from) >= Date.parse(to)) return false;
  return true;
}

function sameQuery(value: EvidenceSearchQuery, requested: EvidenceSearchInput): boolean {
  return value.terms.length === requested.terms.length && value.terms.every((term, i) => term === requested.terms[i]) && value.limit === (requested.limit ?? 20) && ['provider', 'source_id', 'source_kind'].every(key => value[key as keyof EvidenceSearchQuery] === (requested[key as keyof EvidenceSearchInput] ?? null)) && ['collected_from', 'collected_to'].every(key => {
    const actual = value[key as 'collected_from' | 'collected_to']; const expected = requested[key as 'collected_from' | 'collected_to'];
    return actual === (expected ?? null) || (typeof actual === 'string' && typeof expected === 'string' && Date.parse(actual) === Date.parse(expected));
  });
}

function selector(value: unknown): value is EvidenceSearchHit['selector'] {
  if (!isObject(value) || !nonblank(value.quote, 2_000_000)) return false;
  if (value.kind === 'table_cell') return hasKeys(value, ['kind', 'table_id', 'cell_id', 'quote']) && nonblank(value.table_id, 1024) && nonblank(value.cell_id, 1024);
  if (value.kind !== 'text' && value.kind !== 'pdf') return false;
  const keys = ['kind', 'start', 'end', 'quote', 'prefix', 'suffix'];
  if (value.kind === 'pdf') keys.push('page_number', 'regions');
  if (!hasKeys(value, keys) || !integer(value.start, Number.MAX_SAFE_INTEGER) || !integer(value.end, Number.MAX_SAFE_INTEGER) || value.end <= value.start || Array.from(value.quote).length !== value.end - value.start || !nullableText(value.prefix) || !nullableText(value.suffix)) return false;
  if (value.kind === 'pdf') {
    if (!integer(value.page_number, Number.MAX_SAFE_INTEGER) || value.page_number < 1 || !Array.isArray(value.regions)) return false;
    for (const region of value.regions) if (!isObject(region) || !hasKeys(region, ['x0', 'y0', 'x1', 'y1']) || !['x0', 'y0', 'x1', 'y1'].every(key => typeof region[key] === 'number' && Number.isFinite(region[key]) && region[key] >= 0 && region[key] <= 1) || (region.x0 as number) >= (region.x1 as number) || (region.y0 as number) >= (region.y1 as number)) return false;
  }
  return true;
}

function isHit(value: unknown, workspaceId: string, query: EvidenceSearchQuery): value is EvidenceSearchHit {
  if (!isObject(value) || !hasKeys(value, ['workspace_id', 'snapshot_id', 'document_id', 'version_id', 'representation_id', 'provider', 'source_id', 'source_kind', 'canonical_url', 'collected_at', 'unit_ordinal', 'profile', 'selector', 'matched_terms', 'anchor_status', 'support_status'])) return false;
  if (!sameId(value.workspace_id, workspaceId) || ![value.snapshot_id, value.document_id, value.version_id, value.representation_id].every(isId) || !nonblank(value.provider, 1024) || !nonblank(value.source_id, 1024) || !kinds.includes(value.source_kind as string) || !sourceUrl(value.canonical_url) || !timestamp(value.collected_at, false) || !integer(value.unit_ordinal, 5999) || value.profile !== 'literal-ngrams-v1' || value.anchor_status !== 'matched' || value.support_status !== 'not_evaluated' || !selector(value.selector) || !terms(value.matched_terms)) return false;
  const matched = value.matched_terms;
  const quote = value.selector.quote;
  return matched.length === query.terms.length && matched.every((term, index) => term === query.terms[index]) && query.terms.every(term => fold(quote).includes(fold(term))) && (query.provider === null || value.provider === query.provider) && (query.source_id === null || value.source_id === query.source_id) && (query.source_kind === null || value.source_kind === query.source_kind) && (query.collected_from === null || Date.parse(value.collected_at) >= Date.parse(query.collected_from)) && (query.collected_to === null || Date.parse(value.collected_at) < Date.parse(query.collected_to));
}

function isResult(value: unknown, workspaceId: string, requested: EvidenceSearchInput): value is EvidenceSearchResult {
  if (!isObject(value) || !hasKeys(value, ['workspace_id', 'query', 'hits', 'coverage', 'scanned_candidates', 'truncated']) || !sameId(value.workspace_id, workspaceId) || !isQuery(value.query, true) || !sameQuery(value.query, requested) || !Array.isArray(value.hits) || value.hits.length > value.query.limit || value.hits.length > 20 || !integer(value.scanned_candidates, 200) || value.hits.length > value.scanned_candidates || typeof value.truncated !== 'boolean') return false;
  const coverage = value.coverage;
  if (!isObject(coverage) || !hasKeys(coverage, ['total_snapshots', 'indexed_snapshots', 'missing_snapshots', 'skipped_empty_cells', 'skipped_large_cells']) || !Object.values(coverage).every(count => integer(count, Number.MAX_SAFE_INTEGER)) || coverage.total_snapshots !== Number(coverage.indexed_snapshots) + Number(coverage.missing_snapshots) || (value.hits.length > 0 && coverage.indexed_snapshots === 0)) return false;
  const identities = new Set<string>();
  const snapshots = new Set<string>();
  for (const hit of value.hits) {
    if (!isHit(hit, workspaceId, value.query)) return false;
    const key = `${hit.snapshot_id.toLowerCase()}:${hit.unit_ordinal}`;
    if (identities.has(key)) return false;
    identities.add(key);
    snapshots.add(hit.snapshot_id.toLowerCase());
  }
  return snapshots.size <= Number(coverage.indexed_snapshots);
}

export function searchEvidence(workspaceId: string, query: EvidenceSearchInput, options: SearchOptions = {}): Promise<{ data: EvidenceSearchResult; requestId: string }> {
  if (!isId(workspaceId) || !isQuery(query, false)) return Promise.reject(new SearchError('invalid-query'));
  const body = JSON.stringify(query);
  if (new TextEncoder().encode(body).length > 16_384) return Promise.reject(new SearchError('invalid-query'));
  return protectedRequest(`/api/v1/workspaces/${workspaceId}/evidence/search`, 'POST', (value): value is EvidenceSearchResult => isResult(value, workspaceId, query), (kind, requestId) => new SearchError(kind, requestId), options, body);
}
