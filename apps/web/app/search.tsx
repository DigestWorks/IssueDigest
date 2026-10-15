import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { SearchError, searchEvidence, type EvidenceSearchHit, type EvidenceSearchInput, type EvidenceSearchResult, type SearchFailure } from '@issuedigest/api-client';
import './search.css';

type SearchState = { kind: 'idle' } | { kind: 'loading' } | { kind: 'success'; data: EvidenceSearchResult } | { kind: 'failure'; error: SearchError };
const errors: Record<SearchFailure, string> = {
  'invalid-query': '검색어를 확인해 주세요. 공백으로 구분해 중복 없이 1~8개 단어를 입력해 주세요. 단어당 최대 64자입니다.',
  forbidden: '검색 요청을 확인할 수 없습니다. 화면을 새로고침해 주세요.',
  unauthorized: '로그인이 필요합니다.',
  'not-found': '작업 공간이 없거나 접근 권한이 없습니다.',
  unavailable: '검색이 아직 준비되지 않았거나 서버에 문제가 있습니다.',
  malformed: '응답 형식을 확인할 수 없습니다.',
  network: '서버에 연결하지 못했습니다.',
  timeout: '응답을 기다리는 시간이 길어졌습니다.',
  aborted: '검색이 취소되었습니다.',
};

function location(hit: EvidenceSearchHit) {
  const selector = hit.selector;
  return selector.kind === 'pdf' ? `PDF ${selector.page_number}쪽 · 문자 ${selector.start}–${selector.end}`
    : selector.kind === 'table_cell' ? `표 ${selector.table_id} · 셀 ${selector.cell_id}`
      : `본문 문자 ${selector.start}–${selector.end}`;
}

export default function EvidenceSearch({ workspaceId }: { workspaceId: string }) {
  const [input, setInput] = useState('');
  const [state, setState] = useState<SearchState>({ kind: 'idle' });
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const submitted = useRef<EvidenceSearchInput | null>(null);
  useEffect(() => () => { sequence.current++; controller.current?.abort(); }, []);

  function clear(value: string) {
    sequence.current++;
    controller.current?.abort(); controller.current = null;
    submitted.current = null;
    setInput(value); setState({ kind: 'idle' });
  }

  function run(query: EvidenceSearchInput) {
    if (state.kind === 'loading') return;
    const request = ++sequence.current;
    controller.current?.abort();
    const active = new AbortController(); controller.current = active;
    submitted.current = query;
    setState({ kind: 'loading' });
    void searchEvidence(workspaceId, query, { signal: active.signal }).then(
      ({ data }) => { if (sequence.current === request) setState({ kind: 'success', data }); },
      error => { if (sequence.current === request) setState({ kind: 'failure', error: error instanceof SearchError ? error : new SearchError('network') }); },
    ).finally(() => { if (sequence.current === request) controller.current = null; });
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state.kind === 'loading') return;
    run({ terms: input.trim().split(/\s+/u).filter(Boolean) });
  }

  const data = state.kind === 'success' ? state.data : null;
  const omissions = data ? [
    data.coverage.missing_snapshots > 0 ? `미색인 ${data.coverage.missing_snapshots}개` : null,
    data.coverage.skipped_empty_cells > 0 ? `빈 셀 제외 ${data.coverage.skipped_empty_cells}개` : null,
    data.coverage.skipped_large_cells > 0 ? `큰 셀 제외 ${data.coverage.skipped_large_cells}개` : null,
  ].filter(Boolean) : [];
  return <section className="evidence-search" aria-label="원문 검색">
    <form onSubmit={submit}>
      <label htmlFor="evidence-search-input">원문 검색</label>
      <div className="search-fields">
        <input id="evidence-search-input" type="search" value={input} onChange={event => clear(event.target.value)} autoComplete="off" aria-describedby="search-help" />
        <button type="submit" disabled={state.kind === 'loading'}>{state.kind === 'loading' ? '검색 중…' : '검색'}</button>
      </div>
      <p id="search-help">공백으로 나눈 단어를 모두 포함하는 원문 위치를 찾습니다.</p>
    </form>
    {state.kind === 'loading' && <p className="search-status" role="status" aria-label="검색 상태" aria-live="polite">원문 검색 중…</p>}
    {state.kind === 'failure' && <div className="search-feedback">
      <p role="status" aria-label="검색 상태" aria-live="polite">{errors[state.error.kind]}</p>
      {state.error.kind === 'unauthorized' && <Link to="/login" className="action-link">로그인</Link>}
      {submitted.current && state.error.kind !== 'invalid-query' && <button type="button" onClick={() => run(submitted.current!)}>같은 검색 재시도</button>}
      {state.error.requestId && <details className="support-details"><summary>실패 지원 정보</summary><p>요청 ID <code>{state.error.requestId}</code></p></details>}
    </div>}
    {data && <div className="search-results">
      <p role="status" aria-label="검색 상태" aria-live="polite" className="search-status">일치한 원문 위치 {data.hits.length}개 · 최대 {data.query.limit}개 위치 표시</p>
      <p className="search-coverage">자료 색인 {data.coverage.indexed_snapshots}/{data.coverage.total_snapshots}개{omissions.length > 0 && ` · ${omissions.join(' · ')}`}</p>
      {data.truncated && <p className="search-limit">후보 또는 결과 한도에 걸려 일부 일치 위치가 표시되지 않았을 수 있습니다.</p>}
      {data.hits.length === 0 ? <p className="search-empty">일치한 위치가 없습니다. {omissions.length > 0 ? '미색인 자료나 제외된 셀에는 일치하는 내용이 있을 수 있습니다.' : '검색 조건을 바꿔 다시 확인해 보세요.'}</p> : <ol className="search-hit-list">
        {data.hits.map(hit => <li key={`${hit.snapshot_id}/${hit.unit_ordinal}`}>
          <div className="search-hit-meta"><span>{hit.provider} · {hit.source_id}</span><time dateTime={hit.collected_at}>수집 {hit.collected_at}</time></div>
          <p className="search-hit-quote">{hit.selector.quote}</p>
          <div className="search-hit-foot"><span>{location(hit)}</span><Link className="action-link" to={`/workspaces/${workspaceId}/evidence/${hit.snapshot_id}`} state={{ kind: 'search-hit', hit }}>원문 위치 열기</Link></div>
        </li>)}
      </ol>}
    </div>}
  </section>;
}
