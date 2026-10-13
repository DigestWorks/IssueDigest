import type { components } from './schema';
import { hasKeys, isId, isObject, protectedRequest, type ProtectedFailure, type ProtectedOptions } from './protected-request';

export type EvidenceCatalog = components['schemas']['EvidenceCatalog'];
export type EvidenceSummary = components['schemas']['EvidenceSummary'];
export type CatalogFailure = ProtectedFailure;
export type CatalogOptions = ProtectedOptions;
export class CatalogError extends Error {
  constructor(public readonly kind: CatalogFailure, public readonly requestId?: string) {
    super(`Catalog request failed: ${kind}`); this.name = 'CatalogError';
  }
}
const nonblank = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
function sourceUrl(value: unknown) {
  if (value === null) return true;
  if (typeof value !== 'string' || /[\s\\]/u.test(value) || Array.from(value).some(char => char.charCodeAt(0) < 32 || char.charCodeAt(0) === 127)) return false;
  try {
    const url = new URL(value); const authority = /^https?:\/\/([^/?#]*)/i.exec(value)?.[1];
    return ['https:', 'http:'].includes(url.protocol) && Boolean(authority) && !authority?.includes('@') && !url.username && !url.password;
  } catch { return false; }
}
function utcTimestamp(value: unknown) {
  if (typeof value !== 'string') return false;
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(?:Z|\+00:00)$/.exec(value);
  if (!parts || !Number.isFinite(Date.parse(value))) return false;
  const [, year, month, day, hour, minute, second] = parts.map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year > 0 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1] && hour < 24 && minute < 60 && second < 60;
}
function isCatalog(value: unknown, workspaceId: string): value is EvidenceCatalog {
  if (!isObject(value) || !hasKeys(value, ['schema_version', 'workspace_id', 'items', 'has_more']) || value.schema_version !== 1 || !isId(value.workspace_id) || value.workspace_id.toLowerCase() !== workspaceId.toLowerCase() || !Array.isArray(value.items) || value.items.length > 50 || typeof value.has_more !== 'boolean') return false;
  const snapshots = new Set<string>();
  for (const item of value.items) {
    if (!isObject(item) || !hasKeys(item, ['snapshot_id', 'document_id', 'provider', 'source_id', 'source_kind', 'canonical_url', 'collected_at', 'excerpt', 'citation_count']) || !isId(item.snapshot_id) || !isId(item.document_id) || snapshots.has(item.snapshot_id.toLowerCase()) || !nonblank(item.provider) || !nonblank(item.source_id) || typeof item.source_kind !== 'string' || !['bill', 'legal_text', 'government_document', 'news', 'poll', 'statistics', 'petition', 'other'].includes(item.source_kind) || !sourceUrl(item.canonical_url) || !utcTimestamp(item.collected_at) || typeof item.excerpt !== 'string' || Array.from(item.excerpt).length > 160 || typeof item.citation_count !== 'number' || !Number.isSafeInteger(item.citation_count) || item.citation_count < 0) return false;
    snapshots.add(item.snapshot_id.toLowerCase());
  }
  return true;
}
export function getEvidenceCatalog(workspaceId: string, options: CatalogOptions = {}): Promise<{ data: EvidenceCatalog; requestId: string }> {
  if (!isId(workspaceId)) return Promise.reject(new CatalogError('malformed'));
  return protectedRequest(`/api/v1/workspaces/${workspaceId}/evidence?limit=50`, 'GET', (value): value is EvidenceCatalog => isCatalog(value, workspaceId), (kind, requestId) => new CatalogError(kind, requestId), options);
}
