import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import { AuthError, getSession, logout } from '@issuedigest/api-client';
import { clearGuestQuestionDraft } from './guest-question';
import { useResearchDrafts } from './research-drafts';
import { ThemeToggle } from './theme';

type Account = 'guest' | 'authenticated' | 'loading' | 'unavailable' | 'unchecked';
export default function BrandHeader({caption = '질문에서 시작하는 이슈 브리핑', account = 'unchecked', onLogout, logoutPending = false}: {caption?: string; account?: Account; onLogout?: () => void; logoutPending?: boolean}) {
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState<Account>('unchecked');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const root = useRef<HTMLDivElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const menu = useRef<HTMLDivElement>(null);
  const request = useRef<AbortController | null>(null);
  const navigate = useNavigate(); const drafts = useResearchDrafts();
  const effective = account === 'unchecked' ? checked : account;
  function close() {setOpen(false); trigger.current?.focus();}
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!open) return;
    function outside(event: PointerEvent) {if (!root.current?.contains(event.target as Node)) {if (!(event.target instanceof Element && event.target.closest('button, a, input, textarea, select, [tabindex]'))) event.preventDefault(); close();}}
    document.addEventListener('pointerdown', outside);
    return () => document.removeEventListener('pointerdown', outside);
  }, [open]);
  useEffect(() => {
    if (open) (menu.current?.querySelector<HTMLElement>('[role="menuitem"]') ?? trigger.current)?.focus();
  }, [open, effective]);
  useEffect(() => {
    if (!open || account !== 'unchecked' || checked !== 'unchecked') return;
    const controller = new AbortController(); request.current = controller;
    setChecked('loading');
    void getSession({signal: controller.signal}).then(() => {if (!controller.signal.aborted) setChecked('authenticated');}, error => {
      if (!controller.signal.aborted) setChecked(error instanceof AuthError && error.kind === 'unauthorized' ? 'guest' : 'unavailable');
    });
  }, [open, account, checked]);
  async function signOut() {
    if (onLogout) {onLogout(); return;}
    if (busy) return;
    const controller = new AbortController(); request.current = controller; setBusy(true); setError('');
    try {
      await logout({signal: controller.signal});
      if (!controller.signal.aborted) {drafts.clear(); clearGuestQuestionDraft(); setChecked('guest'); close(); void navigate('/login', {replace: true});}
    } catch {if (!controller.signal.aborted) setError('로그아웃하지 못했습니다. 다시 시도해 주세요.');}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  function keys(event: KeyboardEvent) {
    if (event.key === 'Escape') {event.preventDefault(); close();}
    if (['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) {
      event.preventDefault(); setOpen(true);
      const items = Array.from(menu.current?.querySelectorAll<HTMLElement>('[role="menuitem"]') ?? []);
      const current = items.indexOf(document.activeElement as HTMLElement);
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 : (current + (event.key === 'ArrowUp' ? -1 : 1) + items.length) % items.length;
      items[next]?.focus();
    }
  }
  return <header className="brand">
    <Link to="/" className="brand-identity" aria-label="IssueDigest 홈"><img className="brand-mark" src="/brand/issuedigest-mark-v1.png" width="32" height="32" alt="" /><span>IssueDigest</span></Link>
    <span className="brand-caption">{caption}</span>
    <div className="brand-actions"><ThemeToggle /><div className="account-control" ref={root} onKeyDown={keys} onBlur={event => {if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);}}>
      <button type="button" ref={trigger} className="account-trigger" aria-label="계정 메뉴" aria-haspopup="menu" aria-expanded={open} onClick={() => setOpen(value => !value)}><svg aria-hidden="true" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="8" r="3.5" /><path d="M5 21v-2a7 7 0 0 1 14 0v2" /></svg><span>계정</span></button>
      {open && <div className="account-menu" role="menu" aria-label="계정" ref={menu}>
        {effective === 'guest' && <Link role="menuitem" to="/login" onClick={() => setOpen(false)}>로그인</Link>}
        {effective === 'authenticated' && <button type="button" role="menuitem" disabled={logoutPending || busy} onClick={() => void signOut()}>{logoutPending || busy ? '로그아웃 중…' : '로그아웃'}</button>}
        {(effective === 'loading' || effective === 'unchecked') && <p role="status">계정 확인 중…</p>}
        {effective === 'unavailable' && <p>계정 상태를 확인하지 못했습니다.</p>}
        {effective === 'unavailable' && account === 'unchecked' && <button type="button" role="menuitem" onClick={() => setChecked('unchecked')}>다시 확인</button>}
        {error && <p role="alert">{error}</p>}
      </div>}
    </div></div>
  </header>;
}
