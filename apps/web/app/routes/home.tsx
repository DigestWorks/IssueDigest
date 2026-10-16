import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import '../evidence/reader.css';
import { AuthError, CatalogError, ConnectionError, getEvidenceCatalog, getResearchSources, getSession, getStatus, logout, type AuthFailure, type EvidenceCatalog, type SessionInfo } from '@issuedigest/api-client';
import EvidenceSearch from '../search';
import { CollectedDate, sourceKind, TechnicalDetails } from '../evidence/presentation';
import ResearchDesk from '../research';
import { useResearchDrafts } from '../research-drafts';
import { clearGuestQuestionDraft, consumeGuestQuestionDraft, writeGuestQuestionDraft } from '../guest-question';

type State = 'idle' | 'pending' | 'success' | 'failure';
const labels: Record<State, string> = {
  idle: '연결 확인', pending: '확인 중', success: '다시 확인', failure: '재시도',
};
type SessionState = { kind: 'loading' } | { kind: 'ready'; data: SessionInfo } | { kind: 'failure'; error: AuthError };
const messages: Record<AuthFailure, string> = {
  'invalid-query': '요청을 확인할 수 없습니다.', forbidden: '요청을 확인할 수 없습니다.',
  unauthorized: '로그인이 필요합니다.', 'not-found': '자료가 없거나 접근 권한이 없습니다.',
  unavailable: '작업 공간이 아직 준비되지 않았거나 서버에 문제가 있습니다.',
  malformed: '응답 형식을 확인할 수 없습니다.', network: '서버에 연결하지 못했습니다.',
  timeout: '응답을 기다리는 시간이 길어졌습니다.', aborted: '요청이 취소되었습니다.',
  conflict: '요청이 충돌했습니다.', budget: '이번 달 조사 한도에 도달했습니다.',
};
const roles = { viewer: '읽기', editor: '편집', owner: '관리' };

export default function Home() {
  const drafts = useResearchDrafts();
  const navigate = useNavigate();
  const [guestQuestion, setGuestQuestion] = useState('');
  const [guestError, setGuestError] = useState('');
  const [restoredQuestion, setRestoredQuestion] = useState<{userId: string; workspaceId: string; question: string} | null>(null);
  const [evidenceLink, setEvidenceLink] = useState('');
  const [linkError, setLinkError] = useState('');
  const [state, setState] = useState<State>('idle');
  const [reason, setReason] = useState('');
  const [session, setSession] = useState<SessionState>({ kind: 'loading' });
  const [sessionAttempt, setSessionAttempt] = useState(0);
  const [workspaceId, setWorkspaceId] = useState('');
  const [logoutPending, setLogoutPending] = useState(false);
  const [logoutError, setLogoutError] = useState<AuthError | null>(null);
  const [viewParams, setViewParams] = useSearchParams();
  const view = viewParams.get('view') === 'sources' ? 'sources' : viewParams.get('view') === 'saved' ? 'saved' : 'research';
  const entryParams = useRef(viewParams);
  entryParams.current = viewParams;
  const [researchVisited, setResearchVisited] = useState(view !== 'sources');
  useEffect(() => { if (view !== 'sources') setResearchVisited(true); }, [view]);
  function setView(value: 'research' | 'sources' | 'saved') {
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
        const params = entryParams.current;
        const newResearch = !params.has('run') && !['saved', 'sources'].includes(params.get('view') ?? '');
        const question = firstWorkspace && newResearch ? consumeGuestQuestionDraft() : null;
        setRestoredQuestion(question ? {userId: data.user_id, workspaceId: firstWorkspace, question} : null);
        setGuestQuestion(''); setSession({kind: 'ready', data}); setWorkspaceId(firstWorkspace);
      }
    }, error => { if (current) { if (error instanceof AuthError && error.kind === 'unauthorized') drafts.clear(); setSession({ kind: 'failure', error: error instanceof AuthError ? error : new AuthError('network') }); } });
    return () => { current = false; controller.abort(); };
  }, [sessionAttempt]);
  async function signOut() {
    if (logoutRequest.current) return;
    const controller = new AbortController(); logoutRequest.current = controller;
    setLogoutPending(true); setLogoutError(null);
    try {
      await logout({ signal: controller.signal });
      if (mounted.current) { drafts.clear(); clearGuestQuestionDraft(); setRestoredQuestion(null); setGuestQuestion(''); setSession({ kind: 'loading' }); setWorkspaceId(''); setEvidenceLink(''); void navigate('/login', { replace: true }); }
    } catch (error) {
      if (mounted.current) setLogoutError(error instanceof AuthError ? error : new AuthError('network'));
    } finally {
      logoutRequest.current = null;
      if (mounted.current) setLogoutPending(false);
    }
  }

  function continueGuestQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!writeGuestQuestionDraft(guestQuestion)) {
      setGuestError('질문을 임시 보관하지 못했습니다. 이 탭의 저장 설정을 확인하고 다시 시도해 주세요.'); return;
    }
    setGuestError(''); void navigate('/login');
  }

  function openEvidence(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = evidenceLink.trim();
    const uuid = '[\\da-f]{8}-[\\da-f]{4}-4[\\da-f]{3}-[89ab][\\da-f]{3}-[\\da-f]{12}';
    try {
      if ((!value.startsWith('/') && !/^https?:\/\//i.test(value)) || value.startsWith('//') || /[?#\\\s]/.test(value)) throw new Error();
      const url = new URL(value, window.location.origin);
      const rawPath = value.startsWith('/') ? value : value.replace(/^https?:\/\/[^/]+/i, '');
      const authority = /^https?:\/\/([^/?#]*)/i.exec(value)?.[1];
      if (url.origin !== window.location.origin || url.username || url.password || authority?.includes('@') || rawPath !== url.pathname || !new RegExp(`^/workspaces/${uuid}/evidence/${uuid}$`, 'i').test(url.pathname)) throw new Error();
      setLinkError('');
      void navigate(url.pathname);
    } catch {
      setLinkError('같은 사이트의 올바른 근거 링크를 입력해 주세요.');
    }
  }

  async function checkConnection() {
    if (state === 'pending') return;
    setState('pending');
    try {
      await getStatus();
      if (mounted.current) setState('success');
    } catch (error) {
      if (!mounted.current) return;
      setReason(error instanceof ConnectionError && error.kind === 'timeout'
        ? '응답을 기다리는 시간이 길어졌습니다.'
        : '서버 응답을 확인하지 못했습니다.');
      setState('failure');
    }
  }

  return (
    <div className="workspace home-workspace">
      <header className="brand"><span className="brand-mark" aria-hidden="true">iD</span> IssueDigest <span className="brand-caption">질문에서 시작하는 이슈 브리핑</span>{session.kind === 'ready' && <button type="button" onClick={() => void signOut()} disabled={logoutPending}>{logoutPending ? '로그아웃 중…' : '로그아웃'}</button>}</header>
      <main>
        <nav className="research-nav" aria-label="주요 메뉴"><button type="button" aria-current={view === 'research' ? 'page' : undefined} onClick={() => setView('research')}>홈</button><button type="button" aria-current={view === 'saved' ? 'page' : undefined} onClick={() => setView('saved')}>저장한 조사</button><button type="button" aria-current={view === 'sources' ? 'page' : undefined} onClick={() => setView('sources')}>자료</button></nav>
        {view === 'research' && <p className="home-kicker">질문에서 시작해, 근거까지</p>}
        <h1>{view === 'research' ? '무엇이 궁금한가요?' : view === 'sources' ? '자료' : '저장한 조사'}</h1>
        {logoutError && <div className="logout-feedback"><p role="alert">로그아웃하지 못했습니다. {messages[logoutError.kind]} 다시 시도해 주세요.</p><SupportInfo requestId={logoutError.requestId} /></div>}
        <section className="workspace-catalog" aria-label="작업 공간 자료">
          {session.kind === 'loading' && <p role="status" aria-label="작업 공간 상태" aria-live="polite">로그인 상태를 확인하는 중…</p>}
          {session.kind === 'failure' && <>
            <p role="status" aria-label="작업 공간 상태" aria-live="polite">{messages[session.error.kind]}</p>
            {session.error.kind === 'unauthorized' ? <>
              {view === 'research' && <form className="guest-composer" onSubmit={continueGuestQuestion}>
                <label className="visually-hidden" htmlFor="guest-question">무엇이 궁금한가요?</label>
                <textarea id="guest-question" rows={3} maxLength={1500} value={guestQuestion} onChange={event => {setGuestQuestion(event.target.value); setGuestError('');}} placeholder="궁금한 이슈나 알고 싶은 변화를 적어 주세요" aria-describedby="guest-question-note" />
                <div className="guest-compose-foot"><span id="guest-question-note">로그인 후 질문을 확인하고 조사를 시작합니다.</span><button type="submit" disabled={!guestQuestion.trim()}>로그인하고 질문 이어가기</button></div>
                {guestError && <p role="alert">{guestError}</p>}
              </form>}
              <div className="public-briefing-note"><h2>공개 브리핑을 준비하고 있습니다.</h2><p>지금은 초대받은 Google 계정으로 로그인해 자료를 살펴보고 질문할 수 있습니다.</p><Link to="/login" className="action-link">로그인</Link></div>
            </> : <button type="button" onClick={() => { setSession({ kind: 'loading' }); setSessionAttempt(value => value + 1); }}>작업 공간 다시 확인</button>}
            <SupportInfo requestId={session.error.requestId} />
          </>}
          {session.kind === 'ready' && (session.data.memberships.length === 0 ? <p role="status" aria-label="작업 공간 상태">접근 가능한 작업 공간이 없습니다.</p> : <>
            <div className="workspace-choice">
              {session.data.memberships.length === 1 ? <span className="workspace-name">공동 조사 자료</span> : <><label htmlFor="workspace-choice">작업 공간</label>
                <select id="workspace-choice" value={workspaceId} onChange={event => setWorkspaceId(event.target.value)}>
                  {session.data.memberships.map((membership, index) => <option key={membership.workspace_id} value={membership.workspace_id}>공간 {index + 1}</option>)}
                </select></>}
              {membership && <span className="role-label" title={`${roles[membership.role]} 권한`}>{roles[membership.role]}</span>}
              {membership && <TechnicalDetails><p>접근 권한: {roles[membership.role]}</p></TechnicalDetails>}
            </div>
            {workspaceId && !logoutPending && researchVisited && <div hidden={view === 'sources'}><ResearchDesk onInitialQuestionInitialized={() => setRestoredQuestion(null)} key={`${session.data.user_id}/${workspaceId}`} initialQuestion={restoredQuestion?.userId === session.data.user_id && restoredQuestion.workspaceId === workspaceId ? restoredQuestion.question : undefined} workspaceId={workspaceId} canEdit={membership?.role !== 'viewer'} view={view === 'saved' ? 'saved' : 'research'} /></div>}
            {workspaceId && !logoutPending && view === 'sources' && <EvidenceSearch key={`search/${workspaceId}`} workspaceId={workspaceId} />}
            {workspaceId && view === 'sources' && <WorkspaceCatalog key={workspaceId} workspaceId={workspaceId} />}
          </>)}
        </section>
        <details className="workspace-tools"><summary>연결 확인과 저장된 근거 링크</summary><aside aria-label="연결과 저장된 근거 링크">
        <section className="connection" aria-label="서비스 연결 확인">
          <div>
            <p className="connection-label">서비스 연결</p>
            <p role="status" aria-label="서비스 연결 상태" aria-live="polite" className={`connection-status ${state}`}>
              {state === 'idle' && '아직 확인하지 않았습니다.'}
              {state === 'pending' && '요청을 접수했습니다. 연결 확인 중…'}
              {state === 'success' && '연결됨 · 서버가 응답했습니다.'}
              {state === 'failure' && `연결 실패 · ${reason}`}
            </p>
          </div>
          <button type="button" onClick={() => void checkConnection()} disabled={state === 'pending'}>{labels[state]}</button>
        </section>
        <form className="evidence-link-form" onSubmit={openEvidence}>
          <label htmlFor="evidence-link">근거 링크</label>
          <div className="evidence-link-fields">
            <input id="evidence-link" type="text" value={evidenceLink} onChange={event => { setEvidenceLink(event.target.value); setLinkError(''); }} aria-describedby={linkError ? 'evidence-link-note evidence-link-error' : 'evidence-link-note'} aria-invalid={Boolean(linkError)} />
            <button type="submit">근거 링크 열기</button>
          </div>
          <p id="evidence-link-note">저장된 근거 링크로 원문과 인용을 읽습니다. 자료 접근에는 로그인과 작업 공간 권한이 필요합니다.</p>
          {linkError && <p id="evidence-link-error" role="alert">{linkError}</p>}
        </form>
        </aside></details>
      </main>
      <footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer>
    </div>
  );
}

function SupportInfo({ requestId }: { requestId?: string }) {
  return requestId ? <details className="support-details"><summary>실패 지원 정보</summary><p>요청 ID <code>{requestId}</code></p></details> : null;
}
function WorkspaceCatalog({ workspaceId }: { workspaceId: string }) {
  const [state, setState] = useState<{ kind: 'loading' } | { kind: 'ready'; data: EvidenceCatalog } | { kind: 'failure'; error: CatalogError }>({ kind: 'loading' });
  const [titles, setTitles] = useState<Record<string, string>>({});
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let current = true;
    void getEvidenceCatalog(workspaceId, { signal: controller.signal }).then(result => {
      if (current) setState({ kind: 'ready', data: result.data });
    }, error => { if (current) setState({ kind: 'failure', error: error instanceof CatalogError ? error : new CatalogError('network') }); });
    return () => { current = false; controller.abort(); };
  }, [workspaceId, attempt]);
  useEffect(() => {
    if (state.kind !== 'ready') return;
    const controller = new AbortController();
    void getResearchSources(workspaceId, {signal: controller.signal}).then(({data}) => {
      if (!controller.signal.aborted) setTitles(Object.fromEntries(data.items.map(item => [item.snapshot_id, item.title])));
    }, () => {});
    return () => controller.abort();
  }, [workspaceId, state.kind]);
  if (state.kind === 'loading') return <p role="status" aria-label="자료 목록 상태" aria-live="polite">자료 목록을 읽는 중…</p>;
  if (state.kind === 'failure') return <>
    <p role="status" aria-label="자료 목록 상태" aria-live="polite">{messages[state.error.kind]}</p>
    {state.error.kind === 'unauthorized' && <p><Link to="/login" className="action-link">로그인</Link></p>}
    <button type="button" onClick={() => { setState({ kind: 'loading' }); setAttempt(value => value + 1); }}>자료 목록 다시 읽기</button>
    <SupportInfo requestId={state.error.requestId} />
  </>;
  return <>
    <h2 className="catalog-title">저장된 자료</h2>
    <p role="status" aria-label="자료 목록 상태" aria-live="polite" className="catalog-note">저장된 자료 {state.data.items.length}개 · 최대 50개를 표시합니다.{state.data.has_more && ' 표시되지 않은 자료가 더 있습니다.'}</p>
    {state.data.items.length === 0 ? <div className="catalog-empty"><h2>아직 등록된 자료가 없습니다.</h2><p>이 작업 공간에 저장된 원자료가 준비되면 함께 살펴봅니다.</p></div> : <ul className="catalog-list">
      {state.data.items.map(item => <li key={item.snapshot_id}>
        <h3 className="catalog-item-title">{titles[item.snapshot_id] ?? `${sourceKind(item.source_kind)} 원문`}</h3>
        <div className="catalog-source"><span>{sourceKind(item.source_kind)}</span><span>{item.provider}</span></div>
        <p className="catalog-excerpt">{item.excerpt || '저장된 원문 텍스트가 없습니다.'}</p>
        <div className="catalog-meta"><CollectedDate value={item.collected_at} /><span>인용 {item.citation_count}개</span><Link className="action-link" to={`/workspaces/${workspaceId}/evidence/${item.snapshot_id}`} state={{kind: 'catalog-source'}}>근거 열기</Link></div>
        <TechnicalDetails><p>출처 ID <code>{item.source_id}</code></p><p>수집 시각 <code>{item.collected_at}</code></p></TechnicalDetails>
      </li>)}
    </ul>}
  </>;
}
