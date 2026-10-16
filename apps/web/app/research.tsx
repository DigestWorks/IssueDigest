import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useSearchParams } from 'react-router';
import { cancelResearchRun, getResearchRun, listResearchRuns, ResearchError, submitResearch, type CanvasAction, type ResearchRequest, type ResearchRun } from '@issuedigest/api-client';
import { CanvasView } from '@issuedigest/ui';
import '@issuedigest/ui/styles.css';
import './research.css';
import { useResearchDrafts } from './research-drafts';
import {useResearchEvidence} from './research-evidence';

type ListState = {kind: 'loading'} | {kind: 'ready'; items: ResearchRun[]} | {kind: 'failure'; error: ResearchError};
const active = (status: ResearchRun['status']) => ['queued', 'retrieving', 'generating', 'validating'].includes(status);
const stage: Record<ResearchRun['status'], string> = {
  queued: '요청 접수', retrieving: '관련 자료 찾는 중', generating: '자료 분석 중', validating: '인용 연결 확인 중',
  completed: '브리핑 기록에 저장되었습니다', failed: '브리핑을 완료하지 못했습니다', cancelled: '생성이 취소되었습니다',
};
const failures: Record<ResearchError['kind'], string> = {
  'invalid-query': '요청 형식을 확인할 수 없습니다.', unauthorized: '로그인이 필요합니다.', forbidden: '이 작업을 할 권한이 없습니다.', 'not-found': '자료 또는 브리핑을 찾을 수 없습니다.',
  conflict: '이 자료 범위에서 생성 중인 브리핑이 있거나 요청이 충돌했습니다.', budget: '이번 달 AI 조사 한도에 도달했습니다.',
  unavailable: 'AI 연결을 기다리는 중이거나 서비스에 일시적인 문제가 있습니다.', malformed: '응답을 안전하게 읽을 수 없습니다.',
  network: '서버에 연결하지 못했습니다.', timeout: '응답을 기다리는 시간이 길어졌습니다.', aborted: '요청이 중단되었습니다.',
};
const runFailures: Record<NonNullable<ResearchRun['error_code']>, string> = {
  insufficient_evidence: '확인 가능한 자료가 부족합니다.', model_unavailable: 'AI 연결을 확인해 주세요.',
  generation_failed: '결과를 생성하지 못했습니다.', authority_changed: '조사 권한이 변경되었습니다.', cancelled: '생성이 취소되었습니다.',
};
const date = (value: string) => new Intl.DateTimeFormat('ko-KR', {timeZone: 'UTC', year: 'numeric', month: 'numeric', day: 'numeric'}).format(new Date(value));
const authorityFailure = (error: ResearchError) => ['unauthorized', 'forbidden', 'not-found'].includes(error.kind);
function normalize(error: unknown) { return error instanceof ResearchError ? error : new ResearchError('network'); }

export default function ResearchDesk({workspaceId, canEdit, view, initialQuestion, onInitialQuestionInitialized}: {workspaceId: string; canEdit: boolean; view: 'research' | 'saved'; initialQuestion?: string; onInitialQuestionInitialized?: () => void}) {
  const drafts = useResearchDrafts();
  const [params, setParams] = useSearchParams();
  const currentParams = useRef(params);
  currentParams.current = params;
  const runId = params.get('run');
  const context = `${workspaceId}/${runId ?? 'new'}`;
  const contextRef = useRef(context); contextRef.current = context;
  const deniedRef = useRef<string | null>(null);
  const [deniedContext, setDeniedContext] = useState<string | null>(null);
  const readController = useRef<AbortController | null>(null);
  const listController = useRef<AbortController | null>(null);
  const [list, setList] = useState<ListState>({kind: 'loading'});
  const [listVersion, setListVersion] = useState(0);
  const [runVersion, setRunVersion] = useState(0);
  const restoredContext = useRef<string | null>(null);
  const draftRunId = useRef(runId);
  const initialDraft = useRef(!runId && view === 'research' ? initialQuestion ?? '' : '');
  const [question, setQuestion] = useState(() => drafts.read(workspaceId, runId)?.question ?? initialDraft.current);
  const questionRef = useRef(question);
  const [run, setRun] = useState<ResearchRun | null>(null);
  const [runError, setRunError] = useState<ResearchError | null>(null);
  const [requestError, setRequestError] = useState<ResearchError | null>(null);
  const [sending, setSending] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const pendingInput = useRef<ResearchRequest | null>(null);
  const postController = useRef<AbortController | null>(null);
  const cancelController = useRef<AbortController | null>(null);
  const locked = useRef(false);
  const lastSaved = useRef<string | null>(null);

  function clearAuthority(error: ResearchError, origin = context) {
    if (contextRef.current !== origin) return;
    deniedRef.current = origin; setDeniedContext(origin);
    readController.current?.abort(); listController.current?.abort();
    invalidateSubmission(); cancelController.current?.abort(); setCancelling(false);
    pendingInput.current = null; drafts.clearWorkspace(workspaceId);
    initialDraft.current = ''; questionRef.current = ''; setQuestion('');
    setRun(null); setList(runId ? {kind: 'ready', items: []} : {kind: 'failure', error});
    if (runId) setRunError(error); else setRequestError(error);
  }
  function retryRun() {
    deniedRef.current = null; setDeniedContext(null);
    setRunVersion(value => value + 1);
  }
  function refreshList() {
    listController.current?.abort();
    deniedRef.current = null; setDeniedContext(null); setRequestError(null);
    setListVersion(value => value + 1);
  }
  function saveQuestion(value: string) {
    questionRef.current = value; setQuestion(value);
    drafts.write(workspaceId, draftRunId.current, {question: value});
  }
  useEffect(() => {
    // Effect replay must not erase a one-time OAuth question handoff.
    if (restoredContext.current === context) return;
    restoredContext.current = context;
    deniedRef.current = null; setDeniedContext(null);
    draftRunId.current = runId;
    const draft = drafts.read(workspaceId, runId);
    questionRef.current = draft?.question ?? initialDraft.current;
    if (initialDraft.current && !runId) {
      drafts.write(workspaceId, null, {question: questionRef.current});
      onInitialQuestionInitialized?.();
    }
    initialDraft.current = '';
    setQuestion(questionRef.current);
  }, [drafts, workspaceId, runId, onInitialQuestionInitialized]);

  useEffect(() => () => { postController.current?.abort(); cancelController.current?.abort(); }, []);
  useEffect(() => () => {
    invalidateSubmission();
    const controller = cancelController.current;
    if (controller) { cancelController.current = null; controller.abort(); setCancelling(false); }
  }, [runId]);
  useEffect(() => {
    const controller = new AbortController();
    listController.current = controller;
    if (deniedRef.current === context) return () => controller.abort();
    setList({kind: 'loading'});
    void listResearchRuns(workspaceId, {signal: controller.signal}).then(({data}) => { if (!controller.signal.aborted) setList({kind: 'ready', items: data.items}); }, error => {
      if (!controller.signal.aborted) { const failure = normalize(error); if (authorityFailure(failure)) clearAuthority(failure); else setList({kind: 'failure', error: failure}); }
    });
    return () => controller.abort();
  }, [workspaceId, runId, listVersion]);
  useEffect(() => {
    if (!runId) { setRun(null); setRunError(null); return; }
    const controller = new AbortController();
    readController.current = controller;
    let timer: ReturnType<typeof setTimeout> | undefined;
    setRun(current => current?.run_id === runId ? current : null); setRunError(null);
    const read = async () => {
      try {
        const {data} = await getResearchRun(workspaceId, runId, {signal: controller.signal});
        if (controller.signal.aborted || contextRef.current !== context || deniedRef.current === context) return;
        if (data.error_code === 'authority_changed') { clearAuthority(new ResearchError('forbidden')); return; }
        setRun(current => current?.run_id === data.run_id && !active(current.status) && active(data.status) ? current : data);
        setRunError(null);
        if (!drafts.read(workspaceId, runId)) {
          const nextQuestion = data.status === 'completed' ? questionRef.current === data.question ? '' : questionRef.current : questionRef.current || data.question;
          questionRef.current = nextQuestion; setQuestion(nextQuestion);
        }
        if (data.status === 'completed' && lastSaved.current !== data.run_id) {
          lastSaved.current = data.run_id; setListVersion(value => value + 1);
        }
        if (active(data.status)) timer = setTimeout(() => void read(), 1600);
      } catch (error) { if (!controller.signal.aborted) { const failure = normalize(error); if (authorityFailure(failure)) clearAuthority(failure); else setRunError(failure); } }
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
  function newResearch() {
    drafts.clearWorkspace(workspaceId); deniedRef.current = null; setDeniedContext(null);
    // Input may arrive before React Router commits the new URL.
    draftRunId.current = null;
    pendingInput.current = null; setRequestError(null); questionRef.current = ''; setQuestion(''); setCurrent(null);
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
    } catch (error) { if (!controller.signal.aborted) { const failure = normalize(error); if (authorityFailure(failure)) clearAuthority(failure); else setRequestError(failure); } }
    finally { if (postController.current === controller) { postController.current = null; locked.current = false; setSending(false); } }
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locked.current || active(run?.status ?? 'completed') || !canEdit) return;
    const value = question.trim();
    if (!value || value.length > 1500) return;
    const input: ResearchRequest = {request_id: crypto.randomUUID(), question: value, parent_run_id: run?.status === 'completed' ? run.run_id : null};
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
    } catch (error) { if (!controller.signal.aborted) { const failure = normalize(error); if (authorityFailure(failure)) clearAuthority(failure); else setRequestError(failure); } }
    finally { if (cancelController.current === controller) { cancelController.current = null; setCancelling(false); } }
  }
  async function onCanvasAction(action: CanvasAction) {
    if (!run?.result) return;
    if (action.kind === 'open_evidence') {
      await evidence.openCitation(action.citation_id);
    } else if (action.kind === 'ask_question') { saveQuestion(action.question); document.getElementById('research-question')?.focus(); }
  }
  const displayedRun = deniedContext !== context && !sending && run?.run_id === runId && run.workspace_id === workspaceId ? run : null;
  const evidence = useResearchEvidence(workspaceId, displayedRun, deniedContext === context, error => clearAuthority(new ResearchError(error.kind === 'authentication' ? 'unauthorized' : 'not-found')));
  const composer = <form onSubmit={submit} className="research-form">
    <label className={displayedRun?.status === 'completed' ? undefined : 'visually-hidden'} htmlFor="research-question">{displayedRun?.status === 'completed' ? '후속 질문' : '무엇을 알아볼까요?'}</label>
    <textarea id="research-question" value={question} maxLength={1500} rows={3} onChange={event => saveQuestion(event.target.value)} disabled={!canEdit || sending || active(displayedRun?.status ?? 'completed')} placeholder="알아보고 싶은 이슈를 질문하세요" />
    <div className="research-form-foot"><button type="submit" disabled={!canEdit || sending || active(displayedRun?.status ?? 'completed') || !question.trim()}>{sending ? '요청 접수 중…' : displayedRun?.status === 'completed' ? '후속 질문하기' : '브리핑 만들기'}</button></div>
    {!canEdit && <p role="status">읽기 권한으로는 브리핑 기록을 열람할 수 있습니다.</p>}
  </form>;
  return <div className="research-desk">
    {view === 'research' ? <>
      <div className="research-grid">
        <section className="research-work" aria-label="브리핑 작성">
          <h2 className="visually-hidden">질문과 결과</h2>
          {displayedRun?.status !== 'completed' && composer}
          {requestError && <div className="research-feedback" role="alert"><p>{failures[requestError.kind]}</p>{pendingInput.current && ['network','timeout','unavailable'].includes(requestError.kind) && <button type="button" onClick={() => void send(pendingInput.current!)} disabled={sending}>같은 요청 다시 확인</button>}</div>}
          {runId && runError && <div className="research-feedback" role="alert"><p>{failures[runError.kind]}</p><button type="button" onClick={retryRun}>브리핑 다시 읽기</button></div>}
          {runId && !displayedRun && !runError && <p role="status" aria-live="polite">브리핑을 다시 여는 중…</p>}
          {displayedRun && <div className="research-result">
            <div className="research-result-heading"><span role="status" aria-label="브리핑 상태" aria-live="polite">{stage[displayedRun.status]}</span><button type="button" onClick={newResearch} disabled={active(displayedRun.status) || sending}>새 질문</button>{active(displayedRun.status) && canEdit && <button type="button" onClick={() => void cancel()} disabled={cancelling}>{cancelling ? '취소 중…' : '생성 취소'}</button>}</div>
            {active(displayedRun.status) && <ol className="research-progress" aria-label="브리핑 진행 상태">{(['queued','retrieving','generating','validating'] as const).map((step, index) => <li key={step} aria-current={displayedRun.status === step ? 'step' : undefined} data-done={index <= ['queued','retrieving','generating','validating'].indexOf(displayedRun.status)}>{stage[step]}</li>)}</ol>}
            {(displayedRun.status === 'failed' || displayedRun.status === 'cancelled') && <p role="alert">{displayedRun.error_code ? runFailures[displayedRun.error_code] : stage[displayedRun.status]} 질문을 바꾸어 다시 시작할 수 있습니다.</p>}
            {displayedRun.status === 'completed' && displayedRun.result && <><h2 className="research-question">{displayedRun.question}</h2><CanvasView presentation="briefing" bundle={displayedRun.result.canvas} sourceTitles={displayedRun.result.source_titles} onAction={onCanvasAction} /></>}
          </div>}
          {displayedRun?.status === 'completed' && composer}
          {!displayedRun && !runId && <p className="research-start">궁금한 점을 질문하세요. 현재 접근 가능한 저장 자료에서 관련 근거를 찾습니다.</p>}
        </section>
      </div>
    </> : <section className="research-saved" aria-label="브리핑 기록 목록"><div className="research-section-heading"><h2 className="visually-hidden">브리핑 기록</h2><button type="button" onClick={refreshList}>목록 새로고침</button></div>
      <p className="research-help">초기 검증 참여자가 같은 자료 범위에서 만든 브리핑입니다.</p>
      {list.kind === 'loading' && <p role="status">브리핑 기록을 읽는 중…</p>}
      {list.kind === 'failure' && <p role="alert">{failures[list.error.kind]}</p>}
      {list.kind === 'ready' && (list.items.length === 0 ? <p className="research-empty">브리핑 기록이 없습니다.</p> : <ul className="research-run-list">{list.items.map(item => <li key={item.run_id}><button type="button" onClick={() => setCurrent(item.run_id)} aria-current={runId === item.run_id ? 'true' : undefined}><strong>{item.question}</strong><span>{date(item.created_at)} · {stage[item.status]}</span></button></li>)}</ul>)}
      {runId && <button type="button" onClick={() => setCurrent(null)}>선택 해제</button>}
      {runId && runError && <div className="research-feedback" role="alert"><p>{failures[runError.kind]}</p><button type="button" onClick={retryRun}>브리핑 다시 읽기</button></div>}
      {runId && !displayedRun && !runError && <p role="status" aria-live="polite">브리핑을 다시 여는 중…</p>}
      {displayedRun && (displayedRun.status === 'failed' || displayedRun.status === 'cancelled') && <p role="alert">{displayedRun.error_code ? runFailures[displayedRun.error_code] : stage[displayedRun.status]}</p>}
      {displayedRun?.status === 'completed' && displayedRun.result && <div className="research-saved-result"><h2 className="research-question">{displayedRun.question}</h2><CanvasView presentation="briefing" bundle={displayedRun.result.canvas} sourceTitles={displayedRun.result.source_titles} onAction={onCanvasAction} /></div>}
      {displayedRun && active(displayedRun.status) && <p role="status" aria-live="polite">{stage[displayedRun.status]}</p>}
    </section>}
    {evidence.drawer}
  </div>;
}
