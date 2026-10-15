import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { cancelResearchRun, getEvidence, getResearchRun, getResearchSources, listResearchRuns, ResearchError, submitResearch, type CanvasAction, type ResearchRequest, type ResearchRun, type ResearchSourceCatalog } from '@issuedigest/api-client';
import { CanvasView } from '@issuedigest/ui';
import '@issuedigest/ui/styles.css';
import { sourceKind } from './evidence/presentation';
import './research.css';

type CatalogState = {kind: 'loading'} | {kind: 'ready'; data: ResearchSourceCatalog} | {kind: 'failure'; error: ResearchError};
type ListState = {kind: 'loading'} | {kind: 'ready'; items: ResearchRun[]} | {kind: 'failure'; error: ResearchError};
const active = (status: ResearchRun['status']) => ['queued', 'retrieving', 'generating', 'validating'].includes(status);
const stage: Record<ResearchRun['status'], string> = {
  queued: '요청 접수', retrieving: '관련 자료 찾는 중', generating: '자료 분석 중', validating: '인용 연결 확인 중',
  completed: '조사가 자동 저장되었습니다', failed: '조사를 완료하지 못했습니다', cancelled: '조사가 취소되었습니다',
};
const failures: Record<ResearchError['kind'], string> = {
  'invalid-query': '요청 형식을 확인할 수 없습니다.', unauthorized: '로그인이 필요합니다.', forbidden: '이 작업을 할 권한이 없습니다.', 'not-found': '자료 또는 조사를 찾을 수 없습니다.',
  conflict: '이 공간에서 진행 중인 조사가 있거나 요청이 충돌했습니다.', budget: '이번 달 AI 조사 한도에 도달했습니다.',
  unavailable: 'AI 연결을 기다리는 중이거나 서비스에 일시적인 문제가 있습니다.', malformed: '응답을 안전하게 읽을 수 없습니다.',
  network: '서버에 연결하지 못했습니다.', timeout: '응답을 기다리는 시간이 길어졌습니다.', aborted: '요청이 중단되었습니다.',
};
const runFailures: Record<NonNullable<ResearchRun['error_code']>, string> = {
  insufficient_evidence: '확인 가능한 자료가 부족합니다.', model_unavailable: 'AI 연결을 확인해 주세요.',
  generation_failed: '결과를 생성하지 못했습니다.', authority_changed: '조사 권한이 변경되었습니다.', cancelled: '조사가 취소되었습니다.',
};
const date = (value: string) => new Intl.DateTimeFormat('ko-KR', {timeZone: 'UTC', year: 'numeric', month: 'numeric', day: 'numeric'}).format(new Date(value));
function normalize(error: unknown) { return error instanceof ResearchError ? error : new ResearchError('network'); }

export default function ResearchDesk({workspaceId, canEdit, view}: {workspaceId: string; canEdit: boolean; view: 'research' | 'saved'}) {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const currentParams = useRef(params);
  currentParams.current = params;
  const runId = params.get('run');
  const [catalog, setCatalog] = useState<CatalogState>({kind: 'loading'});
  const [list, setList] = useState<ListState>({kind: 'loading'});
  const [listVersion, setListVersion] = useState(0);
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [runVersion, setRunVersion] = useState(0);
  const [selected, setSelected] = useState<string[]>([]);
  const [question, setQuestion] = useState('');
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [runError, setRunError] = useState<ResearchError | null>(null);
  const [requestError, setRequestError] = useState<ResearchError | null>(null);
  const [sending, setSending] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [readerError, setReaderError] = useState(false);
  const pendingInput = useRef<ResearchRequest | null>(null);
  const postController = useRef<AbortController | null>(null);
  const actionController = useRef<AbortController | null>(null);
  const cancelController = useRef<AbortController | null>(null);
  const locked = useRef(false);
  const lastSaved = useRef<string | null>(null);

  useEffect(() => () => { postController.current?.abort(); actionController.current?.abort(); cancelController.current?.abort(); }, []);
  useEffect(() => () => {
    invalidateSubmission();
    actionController.current?.abort();
    const controller = cancelController.current;
    if (controller) { cancelController.current = null; controller.abort(); setCancelling(false); }
  }, [runId]);
  useEffect(() => {
    const controller = new AbortController();
    setCatalog({kind: 'loading'});
    void getResearchSources(workspaceId, {signal: controller.signal}).then(({data}) => { if (!controller.signal.aborted) setCatalog({kind: 'ready', data}); }, error => {
      if (!controller.signal.aborted) setCatalog({kind: 'failure', error: normalize(error)});
    });
    return () => controller.abort();
  }, [workspaceId, catalogVersion]);
  useEffect(() => {
    const controller = new AbortController();
    setList({kind: 'loading'});
    void listResearchRuns(workspaceId, {signal: controller.signal}).then(({data}) => { if (!controller.signal.aborted) setList({kind: 'ready', items: data.items}); }, error => {
      if (!controller.signal.aborted) setList({kind: 'failure', error: normalize(error)});
    });
    return () => controller.abort();
  }, [workspaceId, listVersion]);
  useEffect(() => {
    if (!runId) { setRun(null); setRunError(null); return; }
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    setRun(current => current?.run_id === runId ? current : null); setRunError(null);
    const read = async () => {
      try {
        const {data} = await getResearchRun(workspaceId, runId, {signal: controller.signal});
        if (controller.signal.aborted) return;
        setRun(current => current?.run_id === data.run_id && !active(current.status) && active(data.status) ? current : data);
        setRunError(null); setSelected(data.snapshot_ids);
        setQuestion(value => data.status === 'completed' ? value === data.question ? '' : value : value || data.question);
        if (data.status === 'completed' && lastSaved.current !== data.run_id) {
          lastSaved.current = data.run_id; setListVersion(value => value + 1);
        }
        if (active(data.status)) timer = setTimeout(() => void read(), 1600);
      } catch (error) { if (!controller.signal.aborted) setRunError(normalize(error)); }
    };
    void read();
    return () => { controller.abort(); if (timer) clearTimeout(timer); };
  }, [workspaceId, runId, runVersion]);

  function invalidateSubmission() {
    const controller = postController.current;
    if (controller) { postController.current = null; controller.abort(); locked.current = false; setSending(false); pendingInput.current = null; setRequestError(null); }
  }
  function setCurrent(id: string | null, fromSubmission = false) {
    if (!fromSubmission) invalidateSubmission();
    const next = new URLSearchParams(currentParams.current);
    if (id) next.set('run', id); else next.delete('run');
    setParams(next);
  }
  function toggle(id: string) {
    setSelected(value => value.includes(id) ? value.filter(item => item !== id) : value.length < 3 ? [...value, id] : value);
  }
  function newResearch() {
    pendingInput.current = null; setRequestError(null); setSelected([]); setQuestion(''); setCurrent(null);
  }
  async function send(input: ResearchRequest) {
    if (locked.current || !canEdit) return;
    locked.current = true; setSending(true); setRequestError(null);
    const controller = new AbortController(); postController.current = controller;
    try {
      const {data} = await submitResearch(workspaceId, input, {signal: controller.signal});
      if (controller.signal.aborted) return;
      if (postController.current !== controller) return;
      pendingInput.current = null; setRun(data); setCurrent(data.run_id, true); setListVersion(value => value + 1);
    } catch (error) { if (!controller.signal.aborted) setRequestError(normalize(error)); }
    finally { if (postController.current === controller) { postController.current = null; locked.current = false; setSending(false); } }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || active(run?.status ?? 'completed') || !canEdit) return;
    const value = question.trim();
    if (!value || value.length > 1500 || selected.length < 1 || selected.length > 3) return;
    const input: ResearchRequest = {request_id: crypto.randomUUID(), question: value, snapshot_ids: selected, parent_run_id: run?.status === 'completed' ? run.run_id : null};
    pendingInput.current = input; void send(input);
  }
  function summarize(id: string) {
    if (locked.current || active(run?.status ?? 'completed') || !canEdit) return;
    const value = '선택한 법안의 주요 내용을 근거와 함께 정리해 주세요.';
    setSelected([id]); setQuestion(value);
    const input: ResearchRequest = {request_id: crypto.randomUUID(), question: value, snapshot_ids: [id], parent_run_id: null};
    pendingInput.current = input; void send(input);
  }
  async function cancel() {
    if (!run || !active(run.status) || cancelling) return;
    setCancelling(true); setRequestError(null);
    const controller = new AbortController(); cancelController.current = controller;
    try {
      const {data} = await cancelResearchRun(workspaceId, run.run_id, {signal: controller.signal});
      if (controller.signal.aborted) return;
      setRun(data); if (data.status === 'completed') setListVersion(value => value + 1);
    } catch (error) { if (!controller.signal.aborted) setRequestError(normalize(error)); }
    finally { if (cancelController.current === controller) { cancelController.current = null; setCancelling(false); } }
  }
  async function onCanvasAction(action: CanvasAction) {
    if (!run?.result) return;
    if (action.kind === 'open_evidence') {
      const proof = run.result.canvas.research.evidence.find(item => item.citations.some(citation => citation.citation_id === action.citation_id));
      if (!proof) return;
      setReaderError(false);
      actionController.current?.abort();
      const controller = new AbortController(); actionController.current = controller;
      const candidates = [...new Set([...run.snapshot_ids, ...sourceItems.filter(item => item.document_id === proof.document.document_id).map(item => item.snapshot_id)])];
      for (const snapshotId of candidates) {
        try {
          const {data} = await getEvidence(workspaceId, snapshotId, {signal: controller.signal});
          if (controller.signal.aborted) return;
          if (data.document.document_id !== proof.document.document_id || data.version.version_id !== proof.version.version_id || !data.citations.some(citation => citation.citation_id === action.citation_id)) continue;
          void navigate(`/workspaces/${workspaceId}/evidence/${snapshotId}`, {state: {kind: 'research-citation', citationId: action.citation_id, runId: run.run_id}});
          return;
        } catch { if (controller.signal.aborted) return; /* Another snapshot may be the cited version. */ }
      }
      setReaderError(true);
    } else if (action.kind === 'ask_question') { setQuestion(action.question); document.getElementById('research-question')?.focus(); }
    else if (action.kind === 'select_document') {
      const proof = run.result.canvas.research.evidence.find(item => item.document.document_id === action.document_id);
      const source = sourceItems.find(item => item.document_id === proof?.document.document_id);
      if (source) setSelected([source.snapshot_id]);
    }
  }
  const sourceItems = catalog.kind === 'ready' ? catalog.data.items : [];
  return <div className="research-desk">
    {view === 'research' ? <>
      <div className="research-grid">
        <aside className="research-sources" aria-label="조사 자료 선택">
          <div className="research-section-heading"><h2>조사할 자료</h2><span>최대 3개</span></div>
          {sourceItems.some(item => item.source_kind === 'bill') && <p className="research-help">법안 기본 정보는 현재 처리 상태·조문·영향을 확인한 자료가 아닙니다.</p>}
          {catalog.kind === 'loading' && <p role="status">자료를 읽는 중…</p>}
          {catalog.kind === 'failure' && <div role="status"><p>{failures[catalog.error.kind]}</p><button type="button" onClick={() => setCatalogVersion(value => value + 1)}>자료 다시 읽기</button></div>}
          {catalog.kind === 'ready' && (sourceItems.length === 0 ? <p className="research-empty">조사할 자료가 아직 없습니다.</p> : <ul className="research-source-list" tabIndex={0} aria-label="조사 자료 목록">{sourceItems.map(source => <li key={source.snapshot_id}>
            <label className="research-source-choice"><input type="checkbox" checked={selected.includes(source.snapshot_id)} disabled={!canEdit || (!selected.includes(source.snapshot_id) && selected.length >= 3) || sending || active(run?.status ?? 'completed')} onChange={() => toggle(source.snapshot_id)} /><span className="research-source-title">{source.title}</span></label>
            <p className="research-source-meta">{sourceKind(source.source_kind)}{source.bill_number && ` · 의안번호 ${source.bill_number}`}{source.proposed_on && ` · 제안 ${source.proposed_on}`} · 수집 {date(source.collected_at)}</p>
            {source.excerpt && <p className="research-source-excerpt">{source.excerpt}</p>}
            <div className="research-source-actions"><Link to={`/workspaces/${workspaceId}/evidence/${source.snapshot_id}`} state={{kind: 'research-source', runId}}>원문 읽기</Link>{source.source_kind === 'bill' && canEdit && <button type="button" onClick={() => summarize(source.snapshot_id)} disabled={sending || active(run?.status ?? 'completed')}>핵심 정리</button>}</div>
          </li>)}</ul>)}
        </aside>
        <section className="research-work" aria-label="이슈 조사 작업">
          <div className="research-section-heading"><h2>질문과 결과</h2>{run && <button type="button" onClick={newResearch} disabled={active(run.status) || sending}>새 조사</button>}</div>
          <p className="research-help">선택한 자료와 관련 저장 자료를 토대로 정리합니다. 인용을 열어 원문 위치를 확인할 수 있습니다.</p>
          <form onSubmit={submit} className="research-form">
            {run?.status === 'completed' && <p className="research-context">후속 질문 · {run.question}</p>}
            <label htmlFor="research-question">{run?.status === 'completed' ? '후속 질문' : '무엇을 알아볼까요?'}</label>
            <textarea id="research-question" value={question} maxLength={1500} rows={3} onChange={event => setQuestion(event.target.value)} disabled={!canEdit || sending || active(run?.status ?? 'completed')} placeholder="자료를 선택하고 질문을 입력하세요" />
            <div className="research-form-foot"><span>선택한 자료 {selected.length}개</span><button type="submit" disabled={!canEdit || sending || active(run?.status ?? 'completed') || !question.trim() || selected.length === 0}>{sending ? '요청 접수 중…' : run?.status === 'completed' ? '후속 질문하기' : 'AI 조사 시작'}</button></div>
            {!canEdit && <p role="status">읽기 권한으로는 저장된 조사를 열람할 수 있습니다.</p>}
          </form>
          {requestError && <div className="research-feedback" role="alert"><p>{failures[requestError.kind]}</p>{pendingInput.current && ['network','timeout','unavailable'].includes(requestError.kind) && <button type="button" onClick={() => void send(pendingInput.current!)} disabled={sending}>같은 요청 다시 확인</button>}</div>}
          {readerError && <p className="research-feedback" role="alert">인용의 저장 원문을 열 수 없습니다. 자료를 다시 확인해 주세요.</p>}
          {runId && runError && <div className="research-feedback" role="alert"><p>{failures[runError.kind]}</p><button type="button" onClick={() => setRunVersion(value => value + 1)}>조사 다시 읽기</button></div>}
          {runId && !run && !runError && <p role="status" aria-live="polite">조사를 다시 여는 중…</p>}
          {run && <div className="research-result">
            <div className="research-result-heading"><span role="status" aria-label="조사 상태" aria-live="polite">{stage[run.status]}</span>{active(run.status) && canEdit && <button type="button" onClick={() => void cancel()} disabled={cancelling}>{cancelling ? '취소 중…' : '조사 취소'}</button>}</div>
            {active(run.status) && <ol className="research-progress" aria-label="조사 진행 상태">{(['queued','retrieving','generating','validating'] as const).map((step, index) => <li key={step} aria-current={run.status === step ? 'step' : undefined} data-done={index <= ['queued','retrieving','generating','validating'].indexOf(run.status)}>{stage[step]}</li>)}</ol>}
            {(run.status === 'failed' || run.status === 'cancelled') && <p role="alert">{run.error_code ? runFailures[run.error_code] : stage[run.status]} 질문과 선택 자료를 확인하고 새 조사를 시작할 수 있습니다.</p>}
            {run.result && <><p className="research-question">질문 · {run.question}</p><CanvasView bundle={run.result.canvas} sourceTitles={run.result.source_titles} onAction={onCanvasAction} /></>}
          </div>}
          {!run && !runId && <p className="research-start">자료를 선택해 질문하거나 법안의 핵심 정리를 시작하세요.</p>}
        </section>
      </div>
    </> : <section className="research-saved" aria-label="저장한 조사 목록"><div className="research-section-heading"><h2>저장한 조사</h2><button type="button" onClick={() => setListVersion(value => value + 1)}>목록 새로고침</button></div>
      {list.kind === 'loading' && <p role="status">저장한 조사를 읽는 중…</p>}
      {list.kind === 'failure' && <p role="alert">{failures[list.error.kind]}</p>}
      {list.kind === 'ready' && (list.items.length === 0 ? <p className="research-empty">저장한 조사가 없습니다.</p> : <ul className="research-run-list">{list.items.map(item => <li key={item.run_id}><button type="button" onClick={() => setCurrent(item.run_id)} aria-current={runId === item.run_id ? 'true' : undefined}><strong>{item.question}</strong><span>{date(item.created_at)} · {stage[item.status]}</span></button></li>)}</ul>)}
      {runId && <button type="button" onClick={() => setCurrent(null)}>선택 해제</button>}
      {run && run.result && <div className="research-saved-result"><CanvasView bundle={run.result.canvas} sourceTitles={run.result.source_titles} onAction={onCanvasAction} /></div>}
      {run && active(run.status) && <p role="status" aria-live="polite">{stage[run.status]}</p>}
    </section>}
  </div>;
}
