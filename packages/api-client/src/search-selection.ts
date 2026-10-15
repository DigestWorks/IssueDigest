import type { EvidenceBundle } from './index';
import type { EvidenceSearchHit } from './search';
import { isSearchSelector } from './search';
import { getCitationUtf16Range } from './citations';
import { isObject } from './protected-request';

export type SearchSelection = { selector: EvidenceSearchHit['selector']; range: { start: number; end: number } | null };
const uuid = /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i;
const sameId = (a: unknown, b: unknown) => typeof a === 'string' && typeof b === 'string' && uuid.test(a) && uuid.test(b) && a.toLowerCase() === b.toLowerCase();

/** Router state is untrusted. Only an exact location in the loaded canonical bundle can be selected. */
export function resolveSearchSelection(state: unknown, bundle: EvidenceBundle, workspaceId: string, snapshotId: string): SearchSelection | null {
  if (!isObject(state) || state.kind !== 'search-hit' || !isObject(state.hit)) return null;
  const hit = state.hit;
  const { document, version, representation } = bundle;
  if (!sameId(hit.workspace_id, workspaceId) || !sameId(document.workspace_id, workspaceId) ||
      !sameId(hit.snapshot_id, snapshotId) || !sameId(hit.document_id, document.document_id) ||
      !sameId(hit.version_id, version.version_id) || !sameId(hit.representation_id, representation.representation_id) ||
      hit.provider !== document.provider || hit.source_id !== document.source_id || hit.source_kind !== document.source_kind ||
      hit.canonical_url !== document.canonical_url || hit.collected_at !== version.collected_at ||
      hit.profile !== 'literal-ngrams-v1' || hit.anchor_status !== 'matched' || hit.support_status !== 'not_evaluated' ||
      !isSearchSelector(hit.selector)) return null;
  const selector = hit.selector;
  if (selector.kind === 'table_cell') {
    const cell = representation.tables.find(table => table.table_id === selector.table_id)?.cells.find(cell => cell.cell_id === selector.cell_id);
    return cell?.text === selector.quote ? { selector, range: null } : null;
  }
  try {
    const range = getCitationUtf16Range(representation.text, selector);
    if (selector.kind === 'pdf') {
      const page = representation.pages.find(page => page.page_number === selector.page_number);
      if (!page || selector.start < page.start || selector.end > page.end) return null;
    }
    return { selector, range };
  } catch { return null; }
}
