import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useSearchParams } from 'react-router';
import BrandHeader from '../brand-header';
import { readGuestQuestionDraft } from '../guest-question';

const feedback = new Map([
  ['denied', '로그인을 취소했습니다.'],
  ['invalid', '로그인 요청을 확인하지 못했습니다. 다시 시도해 주세요.'],
  ['unavailable', '로그인 서비스가 아직 준비되지 않았거나 서버에 문제가 있습니다.'],
]);
export default function Login() {
  const [params] = useSearchParams();
  const {key: locationKey} = useLocation();
  const errors = params.getAll('error');
  const message = errors.length === 1 ? feedback.get(errors[0]) : undefined;
  const [draft, setDraft] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const submitted = useRef(false);
  useEffect(() => {
    setDraft(readGuestQuestionDraft());
    const reset = () => { submitted.current = false; setPending(false); setDraft(readGuestQuestionDraft()); };
    window.addEventListener('pageshow', reset);
    return () => window.removeEventListener('pageshow', reset);
  }, [locationKey]);
  function submit(event: FormEvent<HTMLFormElement>) {
    if (submitted.current) { event.preventDefault(); return; }
    submitted.current = true; setPending(true);
  }
  return <div className="workspace login-workspace">
    <BrandHeader />
    <main>
      <p className="eyebrow">질문을 이어가는 곳</p>
      <h1>궁금한 이슈를<br />근거와 함께 살펴보세요.</h1>
      <p className="intro">현재는 운영자가 초대한 Google 계정으로 로그인할 수 있습니다.</p>
      <section className="login-panel" aria-label="로그인">
        {draft && <section className="guest-draft-preview" aria-label="이어갈 질문"><h2>이어갈 질문</h2><p>{draft}</p><small>로그인 후 내용을 고치고 직접 조사를 시작할 수 있습니다.</small></section>}
        {message && <p role="alert" className="login-feedback">{message}</p>}
        <form method="post" action="/api/v1/auth/google/start" onSubmit={submit} aria-busy={pending}>
          <button type="submit" disabled={pending} className="login-button">{pending ? 'Google로 이동 중…' : 'Google로 로그인'}</button>
          <p role="status" aria-live="polite" className="catalog-note">{pending ? 'Google 로그인 화면으로 이동합니다.' : '승인된 작업 공간의 자료만 읽을 수 있습니다.'}</p>
        </form>
        <Link to="/" className="action-link">홈으로</Link>
      </section>
    </main>
    <footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer>
  </div>;
}
