import type { components } from './schema';
import { getCitationUtf16Range } from './citations';

type EvidenceBundle = components['schemas']['EvidenceBundle'];
export type EvidenceFailure = 'invalid-link' | 'authentication' | 'not-found' | 'unavailable' | 'invalid-response' | 'network' | 'timeout' | 'aborted';
export class EvidenceError extends Error {
  constructor(public readonly kind: EvidenceFailure, public readonly requestId?: string) {
    super(`Evidence request failed: ${kind}`);
    this.name = 'EvidenceError';
  }
}
export type EvidenceOptions = { timeoutMs?: number; signal?: AbortSignal };
export type EvidenceResult = { data: EvidenceBundle; requestId: string };
const uuid4 = /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;
const hash = /^[\da-f]{64}$/i;
function object(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}
function nonempty(value: unknown): value is string { return typeof value === 'string' && value.trim().length > 0; }
function id(value: unknown): value is string { return typeof value === 'string' && uuid4.test(value); }
function sameId(a: unknown, b: unknown) { return id(a) && id(b) && a.toLowerCase() === b.toLowerCase(); }
function integer(value: unknown): value is number { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0; }
function nullableText(value: unknown): value is string | null { return value === null || typeof value === 'string'; }
function sourceUrl(value: unknown) {
  if (value === null) return true;
  if (typeof value !== 'string') return false;
  try {
    const url = new URL(value);
    const authority = /^https?:\/\/([^/?#]*)/i.exec(value)?.[1];
    return ['https:', 'http:'].includes(url.protocol) && authority !== undefined && !authority.includes('@') && !url.username && !url.password;
  }
  catch { return false; }
}
function timestamp(value: unknown) {
  if (typeof value !== 'string') return false;
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(\.\d+)?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!parts || !Number.isFinite(Date.parse(value))) return false;
  const [, year, month, day, hour, minute, second] = parts.map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year > 0 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1] && hour < 24 && minute < 60 && second < 60;
}

/** Display boundary only: envelope, required metadata types, reference chain, page/cell
 * identities and exact selectors. Does not reproduce domain integrity/hash/semantic checks,
 * authenticate the source, or validate unused optional table research metadata.
 */
export function isDisplayEvidence(value: unknown, workspaceId: string): value is EvidenceBundle {
  if (!object(value) || value.schema_version !== 1 || !object(value.document) || !object(value.version) || !object(value.representation) || !Array.isArray(value.citations)) return false;
  const { document: doc, version, representation: rep, citations } = value;
  if (!sameId(doc.workspace_id, workspaceId) || !id(doc.document_id) || !nonempty(doc.provider) || !nonempty(doc.source_id) || typeof doc.source_kind !== 'string' || !['bill', 'legal_text', 'government_document', 'news', 'poll', 'statistics', 'petition', 'other'].includes(doc.source_kind) || !sourceUrl(doc.canonical_url)) return false;
  if (!sameId(version.document_id, doc.document_id) || !id(version.version_id) || !id(version.raw_object_id) || !timestamp(version.collected_at) || !nonempty(version.media_type) || typeof version.raw_sha256 !== 'string' || !hash.test(version.raw_sha256)) return false;
  if (!sameId(rep.document_version_id, version.version_id) || !id(rep.representation_id) || typeof rep.text !== 'string' || typeof rep.text_sha256 !== 'string' || !hash.test(rep.text_sha256) || !nonempty(rep.parser_name) || !nonempty(rep.parser_version) || !nonempty(rep.normalization_profile) || !Array.isArray(rep.pages) || !Array.isArray(rep.tables)) return false;
  const length = Array.from(rep.text).length;
  const pages = new Map<number, { start: number; end: number }>();
  let lastEnd = 0;
  for (const page of rep.pages) {
    if (!object(page) || !integer(page.page_number) || page.page_number < 1 || pages.has(page.page_number) || !integer(page.start) || !integer(page.end) || page.start < lastEnd || page.end <= page.start || page.end > length) return false;
    pages.set(page.page_number, { start: page.start, end: page.end });
    lastEnd = page.end;
  }
  const tables = new Map<string, Map<string, string>>();
  for (const table of rep.tables) {
    if (!object(table) || !nonempty(table.table_id) || tables.has(table.table_id) || !Array.isArray(table.cells)) return false;
    const cells = new Map<string, string>();
    for (const cell of table.cells) {
      if (!object(cell) || !nonempty(cell.cell_id) || cells.has(cell.cell_id) || typeof cell.text !== 'string') return false;
      cells.set(cell.cell_id, cell.text);
    }
    tables.set(table.table_id, cells);
  }
  const citationIds = new Set<string>();
  for (const citation of citations) {
    if (!object(citation) || !id(citation.citation_id) || citationIds.has(citation.citation_id.toLowerCase()) || !sameId(citation.document_version_id, version.version_id) || !sameId(citation.representation_id, rep.representation_id) || !object(citation.selector)) return false;
    citationIds.add(citation.citation_id.toLowerCase());
    const selector = citation.selector;
    if (typeof selector.quote !== 'string') return false;
    if (selector.kind === 'table_cell') {
      if (!nonempty(selector.table_id) || !nonempty(selector.cell_id) || tables.get(selector.table_id)?.get(selector.cell_id) !== selector.quote) return false;
    } else if (selector.kind === 'text' || selector.kind === 'pdf') {
      if (!integer(selector.start) || !integer(selector.end) || !nullableText(selector.prefix) || !nullableText(selector.suffix)) return false;
      // Construct the checked range instead of casting the untrusted selector.
      const range = { kind: 'text' as const, start: selector.start, end: selector.end, quote: selector.quote, prefix: selector.prefix, suffix: selector.suffix };
      try { getCitationUtf16Range(rep.text, range); } catch { return false; }
      if (selector.kind === 'pdf') {
        if (!integer(selector.page_number) || selector.page_number < 1 || !Array.isArray(selector.regions)) return false;
        const page = pages.get(selector.page_number);
        if (!page || selector.start < page.start || selector.end > page.end) return false;
        for (const box of selector.regions) {
          if (!object(box) || !['x0', 'y0', 'x1', 'y1'].every(key => typeof box[key] === 'number' && Number.isFinite(box[key]) && box[key] >= 0 && box[key] <= 1) || Number(box.x0) >= Number(box.x1) || Number(box.y0) >= Number(box.y1)) return false;
        }
      }
    } else return false;
  }
  return true;
}

/** Same-origin protected GET; deadline and external cancellation cover headers + body. */
export async function getEvidence(workspaceId: string, snapshotId: string, { timeoutMs = 10_000, signal }: EvidenceOptions = {}): Promise<EvidenceResult> {
  if (!id(workspaceId) || !id(snapshotId) || !Number.isFinite(timeoutMs) || !Number.isInteger(timeoutMs) || timeoutMs <= 0) throw new EvidenceError('invalid-link');
  if (signal?.aborted) throw new EvidenceError('aborted');
  const controller = new AbortController();
  let requestId: string | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  let cancel!: () => void;
  const interruption = new Promise<never>((_resolve, reject) => {
    cancel = () => { reject(new EvidenceError('aborted', requestId)); controller.abort(); };
    signal?.addEventListener('abort', cancel, { once: true });
    // Browsers/Node clamp overflowing timers to an immediate deadline. Chunk long
    // valid durations instead, retaining one timer and the same cancellation path.
    const schedule = (remaining: number) => {
      const duration = Math.min(remaining, 2_147_483_647);
      timer = setTimeout(() => {
        if (remaining > duration) schedule(remaining - duration);
        else { reject(new EvidenceError('timeout', requestId)); controller.abort(); }
      }, duration);
    };
    schedule(timeoutMs);
  });
  const request = async (): Promise<EvidenceResult> => {
    const response = await fetch(`/api/v1/workspaces/${workspaceId}/evidence/${snapshotId}`, {
      credentials: 'same-origin', cache: 'no-store', signal: controller.signal, headers: { Accept: 'application/json' },
    });
    const header = response.headers.get('X-Request-ID'); requestId = id(header) ? header : undefined;
    if (!response.ok) throw new EvidenceError(response.status === 401 ? 'authentication' : [403, 404].includes(response.status) ? 'not-found' : 'unavailable', requestId);
    const mediaType = response.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase();
    const noStore = response.headers.get('Cache-Control')?.split(',').some(token => token.trim().toLowerCase() === 'no-store');
    if (!requestId || !mediaType || !/^application\/(json|[a-z0-9!#$&^_.+-]+\+json)$/.test(mediaType) || !noStore) throw new EvidenceError('invalid-response', requestId);
    let data: unknown;
    try { data = await response.json(); } catch { throw new EvidenceError('invalid-response', requestId); }
    if (!isDisplayEvidence(data, workspaceId)) throw new EvidenceError('invalid-response', requestId);
    return { data, requestId };
  };
  try { return await Promise.race([request(), interruption]); }
  catch (error) { if (error instanceof EvidenceError) throw error; throw new EvidenceError('network', requestId); }
  finally { clearTimeout(timer); signal?.removeEventListener('abort', cancel); }
}
