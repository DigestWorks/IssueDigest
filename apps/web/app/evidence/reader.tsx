import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { EvidenceError, getCitationUtf16Range, getEvidence, resolveSearchSelection, type Citation, type EvidenceBundle, type EvidenceFailure, type SearchSelection } from '@issuedigest/api-client';
import './reader.css';
import BrandHeader from '../brand-header';
import {useResearchDrafts} from '../research-drafts';
import { CollectedDate, sourceKind, TechnicalDetails } from './presentation';

type State = { kind: 'loading' } | { kind: 'ready'; data: EvidenceBundle } | { kind: 'failure'; error: EvidenceError };
const messages: Record<EvidenceFailure, string> = {
  'invalid-link': '근거 링크 형식을 확인해 주세요.',
  authentication: '로그인이 필요합니다.',
  'not-found': '자료가 없거나 접근 권한이 없습니다.',
  unavailable: '자료 읽기가 아직 준비되지 않았거나 서버에 문제가 있습니다.',
  'invalid-response': '응답 형식을 확인할 수 없습니다.',
  network: '서버에 연결하지 못했습니다.',
  timeout: '응답을 기다리는 시간이 길어졌습니다.',
  aborted: '자료 읽기가 취소되었습니다.',
};

export default function EvidenceReader({ workspaceId, snapshotId }: { workspaceId: string; snapshotId: string }) {
  const location = useLocation();
  const drafts = useResearchDrafts();
  const navigate = useNavigate();
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    void getEvidence(workspaceId, snapshotId, { signal: controller.signal }).then(
      result => {
        if (!current) return;
        setState({ kind: 'ready', data: result.data });

      },
      error => {
        if (!current) return;
        const failure = error instanceof EvidenceError ? error : new EvidenceError('network');
        if (['authentication', 'not-found'].includes(failure.kind)) drafts.clearWorkspace(workspaceId);
        if (failure.kind === 'authentication') {void navigate('/login', {replace: true}); return;}
        setState({ kind: 'failure', error: failure });
      },
    );
    return () => { current = false; controller.abort(); };
  }, [workspaceId, snapshotId, attempt, navigate, drafts]);
  function retry() { setState({ kind: 'loading' }); setAttempt(value => value + 1); }
  const navigation = location.state && typeof location.state === 'object' ? location.state as Record<string, unknown> : null;
  const researchOrigin = navigation?.kind === 'research-citation' || navigation?.kind === 'research-source';
  const returnTo = researchOrigin ? typeof navigation?.runId === 'string' && /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i.test(navigation.runId) ? `/?view=research&run=${navigation.runId}` : '/?view=research' : '/';
  return (
    <div className="workspace evidence-workspace">
      <BrandHeader caption="저장된 근거 읽기" />
      <main className="reader-main">
        <Link to={returnTo} className="action-link">브리핑으로</Link>
        {state.kind === 'loading' && <><h1>근거 읽기</h1><p role="status" aria-live="polite" className="reader-status">원문과 인용을 읽는 중…</p></>}
        {state.kind === 'failure' && <>
          <h1>근거 읽기</h1><p role="status" aria-live="polite" className="reader-status">{messages[state.error.kind]}</p>
          {state.error.kind !== 'invalid-link' && <button type="button" onClick={retry}>다시 읽기</button>}
          {state.error.requestId && <details className="support-details"><summary>실패 지원 정보</summary><p>요청 ID <code>{state.error.requestId}</code></p></details>}
        </>}
        {state.kind === 'ready' && <SavedEvidence data={state.data} workspaceId={workspaceId} snapshotId={snapshotId} searchState={location.state} title={null} />}
      </main>
      <footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer>
    </div>
  );
}

function citationLabel(citation: Citation, index: number) {
  const selector = citation.selector;
  return `인용 ${index + 1} · ${selector.kind === 'text' ? '본문' : selector.kind === 'pdf' ? `PDF ${selector.page_number}쪽` : '표 셀'}`;
}
function citationPosition(citation: Citation) {
  const selector = citation.selector;
  return selector.kind === 'table_cell' ? `표 ${selector.table_id} · 셀 ${selector.cell_id}` : `문자 ${selector.start}–${selector.end}`;
}
export function SavedEvidence({ data, workspaceId, snapshotId, searchState, title, publisher, publicCopy = false, onCitationSelect }: { onCitationSelect?:(id:string)=>void; publisher?:string; publicCopy?:boolean; data: EvidenceBundle; workspaceId: string; snapshotId: string; searchState: unknown; title: string | null }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [pageNumber, setPageNumber] = useState<number | null>(null);
  const [searchSelection, setSearchSelection] = useState<SearchSelection | null>(null);
  const [searchNotice, setSearchNotice] = useState(false);
  const original = useRef<HTMLDivElement>(null);
  const highlightedQuote = useRef<HTMLElement>(null);
  const focusOriginal = useRef(false);
  const { document, version, representation, citations } = data;
  const selected = citations.find(citation => citation.citation_id === selectedId);
  const selectedIndex = citations.findIndex(citation => citation.citation_id === selectedId);
  const page = representation.pages.find(page => page.page_number === pageNumber);
  const points = useMemo(() => Array.from(representation.text), [representation.text]);
  const start = page ? points.slice(0, page.start).join('').length : 0;
  const end = page ? points.slice(0, page.end).join('').length : representation.text.length;
  const text = representation.text.slice(start, end);
  const selector = selected?.selector ?? searchSelection?.selector;
  const range = useMemo(() => selected && selected.selector.kind !== 'table_cell' ? getCitationUtf16Range(representation.text, selected.selector) : searchSelection?.range ?? null, [representation.text, selected, searchSelection]);
  const highlight = range && range.start >= start && range.end <= end ? { start: range.start - start, end: range.end - start } : null;
  const cell = selector?.kind === 'table_cell' ? representation.tables.find(table => table.table_id === selector.table_id)?.cells.find(cell => cell.cell_id === selector.cell_id) : undefined;

  function choose(citation: Citation) {
    setSearchSelection(null); setSearchNotice(false);
    const destinationPage = citation.selector.kind === 'pdf' ? citation.selector.page_number : null;
    if (selectedId === citation.citation_id && pageNumber === destinationPage) {
      original.current?.focus({ preventScroll: true });
      (highlightedQuote.current ?? original.current)?.scrollIntoView?.({ block: 'nearest' });
    } else {
      setSelectedId(citation.citation_id);
      setPageNumber(destinationPage);
      // Focus after React replaces the currently displayed page/cell.
      focusOriginal.current = true;
    }
  }
  useEffect(() => {
    if (focusOriginal.current) {
      original.current?.focus({ preventScroll: true });
      (highlightedQuote.current ?? original.current)?.scrollIntoView?.({ block: 'nearest' });
      focusOriginal.current = false;
    }
  }, [selectedId, pageNumber]);
  function choosePage(number: number | null) {
    setSearchSelection(null); setSearchNotice(false);
    if (selectedId === null && pageNumber === number) {
      original.current?.focus();
      original.current?.scrollIntoView?.({ block: 'nearest' });
    } else { setSelectedId(null); setPageNumber(number); focusOriginal.current = true; }
  }
  useEffect(() => {
    if (searchState && typeof searchState === 'object' && 'kind' in searchState && searchState.kind === 'research-citation') {
      const id = 'citationId' in searchState ? searchState.citationId : null;
      const citation = typeof id === 'string' ? citations.find(item => item.citation_id === id) : undefined;
      setSearchSelection(null); setSearchNotice(!citation); setSelectedId(citation?.citation_id ?? null);
      setPageNumber(citation?.selector.kind === 'pdf' ? citation.selector.page_number : null);
      if (citation) focusOriginal.current = true;
      return;
    }
    const resolved = resolveSearchSelection(searchState, data, workspaceId, snapshotId);
    setSearchSelection(resolved);
    setSearchNotice(searchState !== null && searchState !== undefined && !resolved);
    setSelectedId(null);
    setPageNumber(resolved?.selector.kind === 'pdf' ? resolved.selector.page_number : null);
    if (resolved) {
      focusOriginal.current = true;
    }
  }, [searchState, data, workspaceId, snapshotId, citations]);
  useEffect(() => {
    if (searchSelection && focusOriginal.current) {
      original.current?.focus({ preventScroll: true });
      (highlightedQuote.current ?? original.current)?.scrollIntoView?.({ block: 'nearest' });
      focusOriginal.current = false;
    }
  }, [searchSelection]);
  return <>
    <p className="eyebrow">자료 읽기</p>
    <h1>{title ?? `${sourceKind(document.source_kind)} 원문`}</h1>
    <h2>원문과 인용</h2>
    <dl className="source-meta">
      <div><dt>자료 유형</dt><dd>{sourceKind(document.source_kind)}</dd></div>
      <div><dt>공급처</dt><dd>{publisher ?? document.provider}</dd></div>
      <div><dt>수집 날짜</dt><dd><CollectedDate value={version.collected_at} /></dd></div>
    </dl>
    {!publicCopy && <TechnicalDetails><p>출처 ID <code>{document.source_id}</code></p><p>수집 시각 <code>{version.collected_at}</code></p></TechnicalDetails>}
    <p className="source-link">{document.canonical_url ? <a href={document.canonical_url} target="_blank" rel="noopener noreferrer">원문 출처 열기 <span aria-hidden="true">↗</span></a> : '원문 출처 미등록'}</p>
    <p className="reader-note">인용 위치가 일치해도 해당 자료가 주장을 지지하는지는 별도 검토가 필요합니다.</p>
    {searchNotice && <p className="reader-note" role="status">{searchState && typeof searchState === 'object' && 'kind' in searchState && searchState.kind === 'research-citation' ? '인용 위치가 현재 원문과 일치하지 않습니다. 원문을 직접 확인해 주세요.' : '검색 위치가 현재 원문과 일치하지 않습니다. 원문을 직접 확인해 주세요.'}</p>}
    {searchSelection && <p className="reader-note search-selection-note" role="status">검색된 원문 위치 선택됨</p>}
    <div className="reading-layout">
      <section className="original-pane" aria-labelledby="original-title">
        <h2 id="original-title">저장된 자료 본문</h2>
        <nav className="page-navigation" aria-label="원문 페이지">
          <button type="button" aria-pressed={pageNumber === null && !cell} onClick={() => choosePage(null)}>전체 텍스트</button>
          {representation.pages.map(page => <button key={page.page_number} type="button" aria-pressed={pageNumber === page.page_number} onClick={() => choosePage(page.page_number)}>{page.page_number}쪽</button>)}
        </nav>
        <div ref={original} tabIndex={-1} className="original-text" aria-label={cell ? '선택한 표 셀' : '원문 텍스트'}>
          {cell && selector?.kind === 'table_cell' ? <><p className="cell-location">표 {selector.table_id} · 셀 {selector.cell_id}</p><p><mark ref={highlightedQuote}>{cell.text}</mark></p></> : text.length === 0 ? <p className="reader-note">{representation.text.length === 0 ? '파싱된 텍스트가 비어 있습니다.' : '이 페이지의 텍스트가 비어 있습니다.'}</p> : <p>{highlight ? <>{text.slice(0, highlight.start)}<mark ref={highlightedQuote}>{text.slice(highlight.start, highlight.end)}</mark>{text.slice(highlight.end)}</> : text}</p>}
        </div>
      </section>
      <section className="citations-pane" aria-labelledby="citations-title">
        <h2 id="citations-title">저장된 인용 <span className="citation-count">{citations.length}</span></h2>
        <p role="status" aria-live="polite" className="selection-status">{selected ? `${citationLabel(selected, selectedIndex)} 선택됨` : '인용을 선택하면 원문에서 위치를 확인합니다.'}</p>
        {citations.length === 0 ? <p className="reader-note">저장된 인용이 없습니다.</p> : <ol className="citation-list">
          {citations.map((citation, index) => <li key={citation.citation_id}><button type="button" aria-pressed={selectedId === citation.citation_id} onClick={() => onCitationSelect ? onCitationSelect(citation.citation_id) : choose(citation)}><span className="citation-label">{citationLabel(citation, index)}</span><span className="citation-quote">{citation.selector.quote}</span></button>{!publicCopy && <TechnicalDetails><p>{citationPosition(citation)}</p><p>인용 ID <code>{citation.citation_id}</code></p></TechnicalDetails>}</li>)}
        </ol>}
      </section>
    </div>
  </>;
}
