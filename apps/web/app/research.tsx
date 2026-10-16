import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';
import { cancelResearchRun, getResearchRun, getResearchSources, listResearchRuns, ResearchError, submitResearch, type CanvasAction, type ResearchRequest, type ResearchRun, type ResearchSourceCatalog } from '@issuedigest/api-client';
import { CanvasView } from '@issuedigest/ui';
import '@issuedigest/ui/styles.css';
import { sourceKind } from './evidence/presentation';
import './research.css';
import { useResearchDrafts } from './research-drafts';
import {suggestResearchSources} from './research-selection';
import {useResearchEvidence} from './research-evidence';

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

export default function ResearchDesk({workspaceId, canEdit, view, initialQuestion, onInitialQuestionInitialized}: {workspaceId: string; canEdit: boolean; view: 'research' | 'saved'; initialQuestion?: string; onInitialQuestionInitialized?: () => void}) {
  const drafts = useResearchDrafts();
  const [params, setParams] = useSearchParams();
  const currentParams = useRef(params);
  currentParams.current = params;
  const runId = params.get('run');
  const [catalog, setCatalog] = useState<CatalogState>({kind: 'loading'});
  const [list, setList] = useState<ListState>({kind: 'loading'});
  const [listVersion, setListVersion] = useState(0);
  const [catalogVersion, setCatalogVersion] = useState(0);
  const [runVersion, setRunVersion] = useState(0);
  const [selected, setSelected] = useState<string[]>(() => drafts.read(workspaceId, runId)?.selected ?? []);
  const restoredContext = useRef<string | null>(null);
  const draftRunId = useRef(runId);
  const initialDraft = useRef(!runId && view === 'research' ? initialQuestion ?? '' : '');
  const [question, setQuestion] = useState(() => drafts.read(workspaceId, runId)?.question ?? initialDraft.current);
  const selectedRef = useRef(selected);
  const questionRef = useRef(question);
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [runError, setRunError] = useState<ResearchError | null>(null);
  const [requestError, setRequestError] = useState<ResearchError | null>(null);
  const [sending, setSending] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [selectionRequired, setSelectionRequired] = useState(false);
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const pendingInput = useRef<ResearchRequest | null>(null);
  const postController = useRef<AbortController | null>(null);
  const cancelController = useRef<AbortController | null>(null);
  const locked = useRef(false);
  const lastSaved = useRef<string | null>(null);

  function saveSelected(value: string[]) {
    setSelectionRequired(false); selectedRef.current = value; setSelected(value);
    drafts.write(workspaceId, draftRunId.current, {selected: value, question: questionRef.current});
  }
  function saveQuestion(value: string) {
    setSelectionRequired(false); questionRef.current = value; setQuestion(value);
    drafts.write(workspaceId, draftRunId.current, {selected: selectedRef.current, question: value});
  }
  useEffect(() => {
    const context = `${workspaceId}/${runId ?? 'new'}`;
    // Effect replay must not erase a one-time OAuth question handoff.
    if (restoredContext.current === context) return;
    restoredContext.current = context;
    draftRunId.current = runId;
    const draft = drafts.read(workspaceId, runId);
    selectedRef.current = draft?.selected ?? []; questionRef.current = draft?.question ?? initialDraft.current;
    if (initialDraft.current && !runId) {
      drafts.write(workspaceId, null, {selected: selectedRef.current, question: questionRef.current});
      onInitialQuestionInitialized?.();
    }
    initialDraft.current = '';
    setSelected(selectedRef.current); setQuestion(questionRef.current);
  }, [drafts, workspaceId, runId, onInitialQuestionInitialized]);

  useEffect(() => () => { postController.current?.abort(); cancelController.current?.abort(); }, []);
  useEffect(() => () => {
    invalidateSubmission();
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
        setRunError(null);
        if (!drafts.read(workspaceId, runId)) {
          selectedRef.current = data.snapshot_ids; setSelected(data.snapshot_ids);
          const nextQuestion = data.status === 'completed' ? questionRef.current === data.question ? '' : questionRef.current : questionRef.current || data.question;
          questionRef.current = nextQuestion; setQuestion(nextQuestion);
        }
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
    const value = selectedRef.current;
    saveSelected(value.includes(id) ? value.filter(item => item !== id) : value.length < 3 ? [...value, id] : value);
  }
  function newResearch() {
    drafts.clearWorkspace(workspaceId);
    // Input may arrive before React Router commits the new URL.
    draftRunId.current = null;
    pendingInput.current = null; setRequestError(null); selectedRef.current = []; questionRef.current = ''; setSelected([]); setQuestion(''); setCurrent(null);
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
    if (!value || value.length > 1500) return;
    const choices = selected.length ? selected : suggested;
    if (choices.length < 1 || choices.length > 3) {setSelectionRequired(true);setSourcesOpen(true);return;}
    setSelectionRequired(false);
    if (!selected.length) saveSelected(choices);
    const input: ResearchRequest = {request_id: crypto.randomUUID(), question: value, snapshot_ids: choices, parent_run_id: run?.status === 'completed' ? run.run_id : null};
    pendingInput.current = input; void send(input);
  }
  function summarize(id: string) {
    if (locked.current || active(run?.status ?? 'completed') || !canEdit) return;
    const value = '선택한 법안의 주요 내용을 근거와 함께 정리해 주세요.';
    setSourcesOpen(true); saveSelected([id]); saveQuestion(value);
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
      await evidence.openCitation(action.citation_id);
    } else if (action.kind === 'ask_question') { saveQuestion(action.question); document.getElementById('research-question')?.focus(); }
    else if (action.kind === 'select_document') {
      const proof = run.result.canvas.research.evidence.find(item => item.document.document_id === action.document_id);
      const source = sourceItems.find(item => item.document_id === proof?.document.document_id);
      if (source) saveSelected([source.snapshot_id]);
    }
  }
  const sourceItems = catalog.kind === 'ready' ? catalog.data.items : [];
  const suggested = selected.length ? [] : suggestResearchSources(question, sourceItems);
  const displayedRun = !sending && run?.run_id === runId && run.workspace_id === workspaceId ? run : null;
  const accessDenied = [requestError, runError, catalog.kind === 'failure' ? catalog.error : null, list.kind === 'failure' ? list.error : null]
    .some(error => error && ['unauthorized','forbidden','not-found'].includes(error.kind));
  const evidence = useResearchEvidence(workspaceId, displayedRun, sourceItems, accessDenied);
  return <div className="research-desk">
    {view === 'research' ? <>
      <div className="research-grid">
        <section className="research-work" aria-label="이슈 조사 작업">
          <div className="research-section-heading"><h2>질문과 결과</h2>{displayedRun && <button type="button" onClick={newResearch} disabled={active(displayedRun.status) || sending}>새 조사</button>}</div>
          <p className="research-help">연결된 자료에서 질문과 겹치는 후보를 제안합니다. 조사 범위를 직접 선택하고 바꿀 수 있습니다.</p>
          <form onSubmit={submit} className="research-form">
            {displayedRun?.status === 'completed' && <p className="research-context">후속 질문 · {displayedRun.question}</p>}
            <label htmlFor="research-question">{displayedRun?.status === 'completed' ? '후속 질문' : '무엇을 알아볼까요?'}</label>
            <textarea id="research-question" value={question} maxLength={1500} rows={3} onChange={event => saveQuestion(event.target.value)} disabled={!canEdit || sending || active(displayedRun?.status ?? 'completed')} placeholder="알아보고 싶은 이슈를 질문하세요" />
            {selected.length > 0 && <p className="research-selected-scope">조사 범위 · {selected.map(id => sourceItems.find(item => item.snapshot_id === id)?.title).filter(Boolean).join(' / ') || `선택한 자료 ${selected.length}개`}</p>}
            {suggested.length > 0 && <div className="research-candidates" aria-label="질문과 겹치는 연결 자료 후보"><p>질문과 겹치는 연결 자료 후보 · {suggested.length}개</p><ul>{suggested.map(id => <li key={id}>{sourceItems.find(item => item.snapshot_id === id)?.title}</li>)}</ul><button type="button" onClick={() => {saveSelected(suggested);setSourcesOpen(true);}}>이 범위 선택하고 변경</button></div>}
            {selectionRequired && <p role="alert">질문과 겹치는 연결 자료가 없습니다. 조사할 자료를 선택해 주세요.</p>}
            <div className="research-form-foot"><span>선택한 자료 {selected.length}개</span><button type="submit" disabled={!canEdit || sending || active(displayedRun?.status ?? 'completed') || !question.trim()}>{sending ? '요청 접수 중…' : displayedRun?.status === 'completed' ? '후속 질문하기' : 'AI 조사 시작'}</button></div>
            {!canEdit && <p role="status">읽기 권한으로는 저장된 조사를 열람할 수 있습니다.</p>}
          </form>
          {requestError && <div className="research-feedback" role="alert"><p>{failures[requestError.kind]}</p>{pendingInput.current && ['network','timeout','unavailable'].includes(requestError.kind) && <button type="button" onClick={() => void send(pendingInput.current!)} disabled={sending}>같은 요청 다시 확인</button>}</div>}
          {runId && runError && <div className="research-feedback" role="alert"><p>{failures[runError.kind]}</p><button type="button" onClick={() => setRunVersion(value => value + 1)}>조사 다시 읽기</button></div>}
          {runId && !displayedRun && !runError && <p role="status" aria-live="polite">조사를 다시 여는 중…</p>}
          {displayedRun && <div className="research-result">
            <div className="research-result-heading"><span role="status" aria-label="조사 상태" aria-live="polite">{stage[displayedRun.status]}</span>{active(displayedRun.status) && canEdit && <button type="button" onClick={() => void cancel()} disabled={cancelling}>{cancelling ? '취소 중…' : '조사 취소'}</button>}</div>
            {active(displayedRun.status) && <ol className="research-progress" aria-label="조사 진행 상태">{(['queued','retrieving','generating','validating'] as const).map((step, index) => <li key={step} aria-current={displayedRun.status === step ? 'step' : undefined} data-done={index <= ['queued','retrieving','generating','validating'].indexOf(displayedRun.status)}>{stage[step]}</li>)}</ol>}
            {(displayedRun.status === 'failed' || displayedRun.status === 'cancelled') && <p role="alert">{displayedRun.error_code ? runFailures[displayedRun.error_code] : stage[displayedRun.status]} 질문과 선택 자료를 확인하고 새 조사를 시작할 수 있습니다.</p>}
            {displayedRun.status === 'completed' && displayedRun.result && <><p className="research-question">질문 · {displayedRun.question}</p><CanvasView presentation="briefing" bundle={displayedRun.result.canvas} sourceTitles={displayedRun.result.source_titles} onAction={onCanvasAction} /></>}
          </div>}
          {evidence.preview}
          {!displayedRun && !runId && <p className="research-start">궁금한 점을 질문하세요. 연결된 자료에 관련 후보가 없으면 자료를 직접 선택해 주세요.</p>}
        </section>
        <aside className="research-sources" aria-label="조사 자료 선택">
          <div className="research-section-heading"><h2>연결된 자료</h2><button type="button" aria-expanded={sourcesOpen} onClick={() => setSourcesOpen(value => !value)}>{sourcesOpen ? '선택 닫기' : '조사할 자료 선택'}</button></div>
          {sourceItems.some(item => item.source_kind === 'bill') && <p className="research-help">법안 기본 정보는 현재 처리 상태·조문·영향을 확인한 자료가 아닙니다.</p>}
          {catalog.kind === 'loading' && <p role="status">자료를 읽는 중…</p>}
          {catalog.kind === 'failure' && <div role="status"><p>{failures[catalog.error.kind]}</p><button type="button" onClick={() => setCatalogVersion(value => value + 1)}>자료 다시 읽기</button></div>}
          {catalog.kind === 'ready' && (sourceItems.length === 0 ? <p className="research-empty">조사할 자료가 아직 없습니다.</p> : <ul className="research-source-list" tabIndex={0} aria-label="조사 자료 목록">{sourceItems.map(source => <li key={source.snapshot_id}>
            <label className="research-source-choice">{sourcesOpen && <input type="checkbox" checked={selected.includes(source.snapshot_id)} disabled={!canEdit || (!selected.includes(source.snapshot_id) && selected.length >= 3) || sending || active(displayedRun?.status ?? 'completed')} onChange={() => toggle(source.snapshot_id)} />}<span className="research-source-title">{source.title}</span></label>
            <p className="research-source-meta">{sourceKind(source.source_kind)}{source.bill_number && ` · 의안번호 ${source.bill_number}`}{source.proposed_on && ` · 제안 ${source.proposed_on}`} · 수집 {date(source.collected_at)}</p>
            {sourcesOpen && source.excerpt && <p className="research-source-excerpt">{source.excerpt}</p>}
            <div className="research-source-actions"><Link to={`/workspaces/${workspaceId}/evidence/${source.snapshot_id}`} state={{kind: 'research-source', runId}}>원문 읽기</Link>{source.source_kind === 'bill' && canEdit && <button type="button" onClick={() => summarize(source.snapshot_id)} disabled={sending || active(displayedRun?.status ?? 'completed')}>핵심 정리</button>}</div>
          </li>)}</ul>)}
        </aside>
      </div>
    </> : <section className="research-saved" aria-label="저장한 조사 목록"><div className="research-section-heading"><h2>저장한 조사</h2><button type="button" onClick={() => setListVersion(value => value + 1)}>목록 새로고침</button></div>
      {list.kind === 'loading' && <p role="status">저장한 조사를 읽는 중…</p>}
      {list.kind === 'failure' && <p role="alert">{failures[list.error.kind]}</p>}
      {list.kind === 'ready' && (list.items.length === 0 ? <p className="research-empty">저장한 조사가 없습니다.</p> : <ul className="research-run-list">{list.items.map(item => <li key={item.run_id}><button type="button" onClick={() => setCurrent(item.run_id)} aria-current={runId === item.run_id ? 'true' : undefined}><strong>{item.question}</strong><span>{date(item.created_at)} · {stage[item.status]}</span></button></li>)}</ul>)}
      {runId && <button type="button" onClick={() => setCurrent(null)}>선택 해제</button>}
      {runId && runError && <div className="research-feedback" role="alert"><p>{failures[runError.kind]}</p><button type="button" onClick={() => setRunVersion(value => value + 1)}>조사 다시 읽기</button></div>}
      {runId && !displayedRun && !runError && <p role="status" aria-live="polite">조사를 다시 여는 중…</p>}
      {displayedRun && (displayedRun.status === 'failed' || displayedRun.status === 'cancelled') && <p role="alert">{displayedRun.error_code ? runFailures[displayedRun.error_code] : stage[displayedRun.status]}</p>}
      {displayedRun?.status === 'completed' && displayedRun.result && <div className="research-saved-result"><CanvasView presentation="briefing" bundle={displayedRun.result.canvas} sourceTitles={displayedRun.result.source_titles} onAction={onCanvasAction} /></div>}
      {displayedRun && active(displayedRun.status) && <p role="status" aria-live="polite">{stage[displayedRun.status]}</p>}
    </section>}
    {evidence.drawer}
  </div>;
}
