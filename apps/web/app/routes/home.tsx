import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import '../evidence/reader.css';
import { AuthError, CatalogError, ConnectionError, getEvidenceCatalog, getSession, getStatus, logout, type AuthFailure, type EvidenceCatalog, type SessionInfo } from '@issuedigest/api-client';

type State = 'idle' | 'pending' | 'success' | 'failure';
const labels: Record<State, string> = {
  idle: '연결 확인', pending: '확인 중', success: '다시 확인', failure: '재시도',
};
type SessionState = { kind: 'loading' } | { kind: 'ready'; data: SessionInfo } | { kind: 'failure'; error: AuthError };
const messages: Record<AuthFailure, string> = {
  unauthorized: '로그인이 필요합니다.', 'not-found': '자료가 없거나 접근 권한이 없습니다.',
  unavailable: '작업 공간이 아직 준비되지 않았거나 서버에 문제가 있습니다.',
  malformed: '응답 형식을 확인할 수 없습니다.', network: '서버에 연결하지 못했습니다.',
  timeout: '응답을 기다리는 시간이 길어졌습니다.', aborted: '요청이 취소되었습니다.',
};
const roles = { viewer: '읽기', editor: '편집', owner: '관리' };

export default function Home() {
  const navigate = useNavigate();
  const [evidenceLink, setEvidenceLink] = useState('');
  const [linkError, setLinkError] = useState('');
  const [state, setState] = useState<State>('idle');
  const [reason, setReason] = useState('');
  const [session, setSession] = useState<SessionState>({ kind: 'loading' });
  const [sessionAttempt, setSessionAttempt] = useState(0);
  const [workspaceId, setWorkspaceId] = useState('');
  const [logoutPending, setLogoutPending] = useState(false);
  const [logoutError, setLogoutError] = useState<AuthError | null>(null);
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
      if (current) { setSession({ kind: 'ready', data: result.data }); setWorkspaceId(result.data.memberships[0]?.workspace_id ?? ''); }
    }, error => { if (current) setSession({ kind: 'failure', error: error instanceof AuthError ? error : new AuthError('network') }); });
    return () => { current = false; controller.abort(); };
  }, [sessionAttempt]);
  async function signOut() {
    if (logoutRequest.current) return;
    const controller = new AbortController(); logoutRequest.current = controller;
    setLogoutPending(true); setLogoutError(null);
    try {
      await logout({ signal: controller.signal });
      if (mounted.current) { setSession({ kind: 'loading' }); setWorkspaceId(''); setEvidenceLink(''); void navigate('/login', { replace: true }); }
    } catch (error) {
      if (mounted.current) setLogoutError(error instanceof AuthError ? error : new AuthError('network'));
    } finally {
      logoutRequest.current = null;
      if (mounted.current) setLogoutPending(false);
    }
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
    <div className="workspace">
      <header className="brand"><span className="brand-mark" aria-hidden="true">iD</span> IssueDigest <span className="brand-caption">이슈 조사 작업 공간</span>{session.kind === 'ready' && <button type="button" onClick={() => void signOut()} disabled={logoutPending}>{logoutPending ? '로그아웃 중…' : '로그아웃'}</button>}</header>
      <main>
        <p className="eyebrow">자료에서 시작하는 조사</p>
        <h1>이슈를 읽고,<br />근거를 비교합니다.</h1>
        <p className="intro">하나의 이슈를 여러 자료와 관점으로 살펴보는 작업 공간입니다.</p>
        {logoutError && <div className="logout-feedback"><p role="alert">로그아웃하지 못했습니다. {messages[logoutError.kind]} 다시 시도해 주세요.</p><SupportInfo requestId={logoutError.requestId} /></div>}
        <section className="workspace-catalog" aria-label="작업 공간 자료">
          {session.kind === 'loading' && <p role="status" aria-label="작업 공간 상태" aria-live="polite">로그인 상태를 확인하는 중…</p>}
          {session.kind === 'failure' && <>
            <p role="status" aria-label="작업 공간 상태" aria-live="polite">{messages[session.error.kind]}</p>
            {session.error.kind === 'unauthorized' ? <><p className="catalog-note">승인된 Google 계정으로 작업 공간의 자료를 함께 읽습니다.</p><Link to="/login" className="action-link">로그인</Link></> : <button type="button" onClick={() => { setSession({ kind: 'loading' }); setSessionAttempt(value => value + 1); }}>작업 공간 다시 확인</button>}
            <SupportInfo requestId={session.error.requestId} />
          </>}
          {session.kind === 'ready' && (session.data.memberships.length === 0 ? <p role="status" aria-label="작업 공간 상태">접근 가능한 작업 공간이 없습니다.</p> : <>
            <div className="workspace-choice">
              <label htmlFor="workspace-choice">작업 공간</label>
              <select id="workspace-choice" value={workspaceId} onChange={event => setWorkspaceId(event.target.value)}>
                {session.data.memberships.map(membership => <option key={membership.workspace_id} value={membership.workspace_id}>{membership.workspace_id}</option>)}
              </select>
              {membership && <span className="role-label" title={`${roles[membership.role]} 권한`}>{roles[membership.role]}</span>}
            </div>
            {workspaceId && <WorkspaceCatalog key={workspaceId} workspaceId={workspaceId} />}
          </>)}
        </section>
        <aside className="workspace-tools" aria-label="연결과 저장된 근거 링크">
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
        </aside>
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
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController(); let current = true;
    void getEvidenceCatalog(workspaceId, { signal: controller.signal }).then(result => {
      if (current) setState({ kind: 'ready', data: result.data });
    }, error => { if (current) setState({ kind: 'failure', error: error instanceof CatalogError ? error : new CatalogError('network') }); });
    return () => { current = false; controller.abort(); };
  }, [workspaceId, attempt]);
  if (state.kind === 'loading') return <p role="status" aria-label="자료 목록 상태" aria-live="polite">자료 목록을 읽는 중…</p>;
  if (state.kind === 'failure') return <>
    <p role="status" aria-label="자료 목록 상태" aria-live="polite">{messages[state.error.kind]}</p>
    {state.error.kind === 'unauthorized' && <p><Link to="/login" className="action-link">로그인</Link></p>}
    <button type="button" onClick={() => { setState({ kind: 'loading' }); setAttempt(value => value + 1); }}>자료 목록 다시 읽기</button>
    <SupportInfo requestId={state.error.requestId} />
  </>;
  return <>
    <p role="status" aria-label="자료 목록 상태" aria-live="polite" className="catalog-note">저장된 자료 {state.data.items.length}개 · 최대 50개를 표시합니다.{state.data.has_more && ' 표시되지 않은 자료가 더 있습니다.'}</p>
    {state.data.items.length === 0 ? <div className="catalog-empty"><h2>아직 등록된 자료가 없습니다.</h2><p>이 작업 공간에 저장된 원자료가 준비되면 함께 살펴봅니다.</p></div> : <ul className="catalog-list">
      {state.data.items.map(item => <li key={item.snapshot_id}>
        <div className="catalog-source"><span>{item.provider}</span><span className="catalog-source-id">{item.source_id}</span></div>
        <p className="catalog-excerpt">{item.excerpt || '저장된 원문 텍스트가 없습니다.'}</p>
        <div className="catalog-meta"><time dateTime={item.collected_at}>수집 {item.collected_at}</time><span>인용 {item.citation_count}개</span><Link className="action-link" to={`/workspaces/${workspaceId}/evidence/${item.snapshot_id}`}>근거 열기</Link></div>
      </li>)}
    </ul>}
  </>;
}
