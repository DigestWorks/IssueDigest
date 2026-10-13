import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router';

const feedback = new Map([
  ['denied', '로그인을 취소했습니다.'],
  ['invalid', '로그인 요청을 확인하지 못했습니다. 다시 시도해 주세요.'],
  ['unavailable', '로그인 서비스가 아직 준비되지 않았거나 서버에 문제가 있습니다.'],
]);
export default function Login() {
  const [params] = useSearchParams();
  const errors = params.getAll('error');
  const message = errors.length === 1 ? feedback.get(errors[0]) : undefined;
  const [pending, setPending] = useState(false);
  const submitted = useRef(false);
  useEffect(() => {
    const reset = () => { submitted.current = false; setPending(false); };
    window.addEventListener('pageshow', reset);
    return () => window.removeEventListener('pageshow', reset);
  }, []);
  function submit(event: FormEvent<HTMLFormElement>) {
    if (submitted.current) { event.preventDefault(); return; }
    submitted.current = true; setPending(true);
  }
  return <div className="workspace login-workspace">
    <header className="brand"><span className="brand-mark" aria-hidden="true">iD</span> IssueDigest <span className="brand-caption">이슈 조사 작업 공간</span></header>
    <main>
      <p className="eyebrow">함께 읽는 원자료</p>
      <h1>근거를 살펴보는<br />작업 공간에 들어갑니다.</h1>
      <p className="intro">IssueDigest에서 원자료와 저장된 인용을 함께 읽습니다.<br />운영자가 초대한 Google 계정으로 로그인해 주세요.</p>
      <section className="login-panel" aria-label="작업 공간 로그인">
        {message && <p role="alert" className="login-feedback">{message}</p>}
        <form method="post" action="/api/v1/auth/google/start" onSubmit={submit} aria-busy={pending}>
          <button type="submit" disabled={pending} className="login-button">{pending ? 'Google로 이동 중…' : 'Google로 로그인'}</button>
          <p role="status" aria-live="polite" className="catalog-note">{pending ? 'Google 로그인 화면으로 이동합니다.' : '승인된 작업 공간의 자료만 읽을 수 있습니다.'}</p>
        </form>
        <Link to="/" className="action-link">작업 공간으로</Link>
      </section>
    </main>
    <footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer>
  </div>;
}
