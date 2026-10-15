import { describe, expect, it } from 'vitest';
import canvas from '../../../tests/fixtures/canvas-synthetic.json';
import { resolveSearchSelection, type EvidenceBundle, type EvidenceSearchHit } from '../src/index';

const workspace = '00000000-0000-4000-8000-000000000001';
const snapshot = '00000000-0000-4000-8000-000000000099';
const bundle = () => structuredClone(canvas.research.evidence[0]) as EvidenceBundle;
const hit = (selector: EvidenceSearchHit['selector']): EvidenceSearchHit => {
  const data = bundle();
  return { workspace_id: workspace, snapshot_id: snapshot, document_id: data.document.document_id,
    version_id: data.version.version_id, representation_id: data.representation.representation_id,
    provider: data.document.provider, source_id: data.document.source_id, source_kind: data.document.source_kind,
    canonical_url: data.document.canonical_url, collected_at: data.version.collected_at, unit_ordinal: 0,
    profile: 'literal-ngrams-v1', selector, matched_terms: ['합성'], anchor_status: 'matched', support_status: 'not_evaluated' };
};
const state = (value: EvidenceSearchHit) => ({ kind: 'search-hit', hit: value });

describe('canonical search location', () => {
  it('accepts exact text, PDF page and full table cell without a citation ID', () => {
    const data = bundle();
    for (const citation of data.citations) {
      const selected = resolveSearchSelection(state(hit(citation.selector)), data, workspace, snapshot);
      expect(selected?.selector).toEqual(citation.selector);
    }
  });
  it('converts emoji and combining mark ranges only after exact adjacent context matches', () => {
    const data = bundle(); data.representation.text = '앞😀é뒤'; data.representation.pages = [{ page_number: 7, start: 0, end: 5 }];
    const selected = hit({ kind: 'text', start: 1, end: 4, quote: '😀é', prefix: '앞', suffix: '뒤' });
    expect(resolveSearchSelection(state(selected), data, workspace, snapshot)?.range).toEqual({ start: 1, end: 5 });
    selected.selector = { ...selected.selector, suffix: '다른' } as EvidenceSearchHit['selector'];
    expect(resolveSearchSelection(state(selected), data, workspace, snapshot)).toBeNull();
  });
  it('rejects changed identity, stale location, PDF page, cell and malformed state', () => {
    const data = bundle(); const original = hit(data.citations[0].selector);
    expect(resolveSearchSelection(null, data, workspace, snapshot)).toBeNull();
    expect(resolveSearchSelection(state({ ...original, workspace_id: '00000000-0000-4000-8000-000000000002' }), data, workspace, snapshot)).toBeNull();
    expect(resolveSearchSelection(state({ ...original, snapshot_id: '00000000-0000-4000-8000-000000000098' }), data, workspace, snapshot)).toBeNull();
    expect(resolveSearchSelection(state({ ...original, representation_id: '00000000-0000-4000-8000-000000000098' }), data, workspace, snapshot)).toBeNull();
    expect(resolveSearchSelection(state({ ...original, selector: { ...data.citations[0].selector, quote: '변조' } }), data, workspace, snapshot)).toBeNull();
    const pdf = data.citations[1].selector; const table = data.citations[2].selector;
    if (pdf.kind !== 'pdf' || table.kind !== 'table_cell') throw new Error('invalid test fixture');
    expect(resolveSearchSelection(state(hit({ ...pdf, page_number: 7 })), data, workspace, snapshot)).toBeNull();
    expect(resolveSearchSelection(state(hit({ ...table, cell_id: '다른 셀' })), data, workspace, snapshot)).toBeNull();
    expect(resolveSearchSelection({ kind: 'search-hit', hit: { ...original, selector: { kind: 'text', start: NaN } } }, data, workspace, snapshot)).toBeNull();
  });
});
