import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import '../evidence/reader.css';
import BrandHeader from '../brand-header';
import { AuthError, getSession, logout, type AuthFailure, type SessionInfo } from '@issuedigest/api-client';
import ResearchDesk from '../research';
import QuestionComposer from '../question-composer';
import BriefingJobHistory from '../briefing-job-list';
import {PublicBriefingList} from '../public-briefings';
import { useResearchDrafts } from '../research-drafts';
import { clearGuestQuestionDraft, consumeGuestQuestionDraft, readGuestQuestionDraft, writeGuestQuestionDraft } from '../guest-question';

type SessionState = { kind: 'loading' } | { kind: 'ready'; data: SessionInfo } | { kind: 'failure'; error: AuthError };
const messages: Record<AuthFailure, string> = {
  'invalid-query': '요청을 확인할 수 없습니다.', forbidden: '요청을 확인할 수 없습니다.',
  unauthorized: '로그인이 필요합니다.', 'not-found': '자료가 없거나 접근 권한이 없습니다.',
  unavailable: '자료 접근이 아직 준비되지 않았거나 서버에 문제가 있습니다.',
  malformed: '응답 형식을 확인할 수 없습니다.', network: '서버에 연결하지 못했습니다.',
  timeout: '응답을 기다리는 시간이 길어졌습니다.', aborted: '요청이 취소되었습니다.',
  conflict: '요청이 충돌했습니다.', budget: '이번 달 조사 한도에 도달했습니다.',
};

export default function Home() {
  const drafts = useResearchDrafts();
  const navigate = useNavigate();
  const [guestQuestion, setGuestQuestion] = useState(() => readGuestQuestionDraft() ?? '');
  const [guestError, setGuestError] = useState('');
  const [restoredQuestion, setRestoredQuestion] = useState<{userId: string; workspaceId: string; question: string} | null>(null);
  const [session, setSession] = useState<SessionState>({ kind: 'loading' });
  const [sessionAttempt, setSessionAttempt] = useState(0);
  const [workspaceId, setWorkspaceId] = useState('');
  const [logoutPending, setLogoutPending] = useState(false);
  const [deniedWorkspace, setDeniedWorkspace] = useState('');
  const [logoutError, setLogoutError] = useState<AuthError | null>(null);
  const [viewParams, setViewParams] = useSearchParams();
  const view = viewParams.get('view') === 'saved' ? 'saved' : 'research';
  const entryParams = useRef(viewParams);
  entryParams.current = viewParams;
  function setView(value: 'research' | 'saved') {
    if (value !== 'research' && session.kind === 'failure' && session.error.kind === 'unauthorized') {void navigate('/login'); return;}
    const next = new URLSearchParams(viewParams); next.set('view', value); setViewParams(next);
  }
  const logoutRequest = useRef<AbortController | null>(null);
  const mounted = useRef(true);
  const membership = session.kind === 'ready' ? session.data.memberships.find(item => item.workspace_id === workspaceId) : undefined;
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; logoutRequest.current?.abort(); };
  }, []);
  useEffect(() => {
    const controller = new AbortController(); let current = true;
    void getSession({ signal: controller.signal }).then(result => {
      if (current) {
        const data = result.data;
        drafts.identify(data.user_id, data.memberships.map(item => item.workspace_id));
        const firstWorkspace = data.memberships[0]?.workspace_id ?? '';
        setDeniedWorkspace('');
        const params = entryParams.current;
        const newResearch = !params.has('run') && params.get('view') !== 'saved';
        const question = firstWorkspace && newResearch ? consumeGuestQuestionDraft() : null;
        // An explicit incoming question replaces this member's new-question draft once.
        if (question !== null) drafts.write(firstWorkspace, null, {question});
        setRestoredQuestion(question ? {userId: data.user_id, workspaceId: firstWorkspace, question} : null);
        setGuestQuestion(''); setSession({kind: 'ready', data}); setWorkspaceId(firstWorkspace);
      }
    }, error => { if (current) { if (error instanceof AuthError && error.kind === 'unauthorized') {drafts.clear();} setSession({ kind: 'failure', error: error instanceof AuthError ? error : new AuthError('network') }); } });
    return () => { current = false; controller.abort(); };
  }, [sessionAttempt]);
  useEffect(() => {
    if (view !== 'research' && session.kind === 'failure' && session.error.kind === 'unauthorized') void navigate('/login', {replace: true});
  }, [view, session, navigate]);

  async function signOut() {
    if (logoutRequest.current) return;
    const controller = new AbortController(); logoutRequest.current = controller;
    setLogoutPending(true); setLogoutError(null);
    try {
      await logout({ signal: controller.signal });
      if (mounted.current) { drafts.clear(); clearGuestQuestionDraft(); setRestoredQuestion(null); setGuestQuestion(''); setSession({ kind: 'loading' }); setWorkspaceId(''); void navigate('/login', { replace: true }); }
    } catch (error) {
      if (mounted.current) setLogoutError(error instanceof AuthError ? error : new AuthError('network'));
    } finally {
      logoutRequest.current = null;
      if (mounted.current) setLogoutPending(false);
    }
  }

  function continueGuestQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!guestQuestion.trim()) return;
    if (!writeGuestQuestionDraft(guestQuestion)) {
      setGuestError('질문을 임시 보관하지 못했습니다. 이 탭의 저장 설정을 확인하고 다시 시도해 주세요.'); return;
    }
    setGuestError(''); void navigate('/login');
  }

  return (
    <div className="workspace home-workspace">
      <BrandHeader account={session.kind === 'ready' ? 'authenticated' : session.kind === 'loading' ? 'loading' : session.error.kind === 'unauthorized' ? 'guest' : 'unavailable'} onLogout={() => void signOut()} logoutPending={logoutPending} />
      <main>
        <nav className="research-nav" aria-label="주요 메뉴"><button type="button" aria-current={view === 'research' ? 'page' : undefined} onClick={() => setView('research')}>브리핑</button><button type="button" aria-current={view === 'saved' ? 'page' : undefined} onClick={() => setView('saved')}>브리핑 기록</button></nav>
        <div className={view === 'research' && viewParams.has('run') && session.kind === 'ready' ? 'visually-hidden' : 'question-intro'}>
          {view === 'saved' && <p className="eyebrow">다시 읽고, 이어서 질문하기</p>}
          <h1>{view === 'research' ? '무엇이 궁금한가요?' : '브리핑 기록'}</h1>
          {view === 'research' && <p className="question-description">질문하고, 브리핑에서 근거까지 살펴보세요.</p>}
        </div>
        {logoutError && <div className="logout-feedback"><p role="alert">로그아웃하지 못했습니다. {messages[logoutError.kind]} 다시 시도해 주세요.</p><SupportInfo requestId={logoutError.requestId} /></div>}
        <section className="workspace-catalog" aria-label="브리핑">
          {session.kind === 'loading' && <p role="status" aria-label="접근 상태" aria-live="polite">로그인 상태를 확인하는 중…</p>}
          {session.kind === 'failure' && <>
            {session.error.kind !== 'unauthorized' && <p role="status" aria-label="접근 상태" aria-live="polite">{messages[session.error.kind]}</p>}
            {session.error.kind === 'unauthorized' ? <>
              {view === 'research' && <form className="guest-composer" onSubmit={continueGuestQuestion}>
                <label className="visually-hidden" htmlFor="guest-question">무엇이 궁금한가요?</label>
                <textarea id="guest-question" rows={3} maxLength={1500} value={guestQuestion} onChange={event => {setGuestQuestion(event.target.value); setGuestError('');}} placeholder="궁금한 이슈나 알고 싶은 변화를 적어 주세요" />
                <div className="guest-compose-foot"><button type="submit" disabled={!guestQuestion.trim()}>질문하기<span className="submit-arrow" aria-hidden="true">↑</span></button></div>
                {guestError && <p role="alert">{guestError}</p>}
              </form>}
            </> : <button type="button" onClick={() => { setSession({ kind: 'loading' }); setSessionAttempt(value => value + 1); }}>접근 상태 다시 확인</button>}
            {session.error.kind !== 'unauthorized' && <SupportInfo requestId={session.error.requestId} />}
          </>}
          {session.kind === 'ready' && (session.data.memberships.length === 0 ? <p role="status" aria-label="접근 상태">접근 가능한 자료 범위가 없습니다.</p> : <>
            {deniedWorkspace === workspaceId && <button type="button" onClick={() => {setSession({kind: 'loading'}); setSessionAttempt(value => value + 1);}}>접근 상태 다시 확인</button>}
            {workspaceId && !logoutPending && <>
              {view === 'research' && !viewParams.has('run') ? <QuestionComposer actor={session.data.user_id} workspaceId={workspaceId} key={`${session.data.user_id}/${workspaceId}`} initialQuestion={restoredQuestion?.userId === session.data.user_id && restoredQuestion.workspaceId === workspaceId ? restoredQuestion.question : undefined} onInitialQuestionInitialized={() => setRestoredQuestion(null)} canEdit={membership?.role !== 'viewer' && deniedWorkspace !== workspaceId} /> : <>
                {view === 'saved' && <BriefingJobHistory key={`briefings/${session.data.user_id}/${workspaceId}`} workspaceId={workspaceId} onAuthorityLoss={() => {drafts.clearWorkspace(workspaceId); setRestoredQuestion(null); setDeniedWorkspace(workspaceId);}} />}
                <ResearchDesk onInitialQuestionInitialized={() => setRestoredQuestion(null)} key={`research/${session.data.user_id}/${workspaceId}`} initialQuestion={restoredQuestion?.userId === session.data.user_id && restoredQuestion.workspaceId === workspaceId ? restoredQuestion.question : undefined} workspaceId={workspaceId} canEdit={membership?.role !== 'viewer'} view={view} />
              </>}
            </>}
          </>)}
        </section>
        {view === 'research' && !viewParams.has('run') && <PublicBriefingList/>}
      </main>
      <footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer>
    </div>
  );
}

function SupportInfo({ requestId }: { requestId?: string }) {
  return requestId ? <details className="support-details"><summary>실패 지원 정보</summary><p>요청 ID <code>{requestId}</code></p></details> : null;
}
