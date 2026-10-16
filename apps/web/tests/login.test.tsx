import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import routes from '../app/routes';
import { headers, response, session } from './workspace-data';
import Login from '../app/routes/login';
function mount(query = '') {
  return render(<MemoryRouter initialEntries={[`/login${query}`]}><Login /></MemoryRouter>);
}
it('registers the real login route with a native fixed POST form and no client credentials', async () => {
  expect(routes.find(route => route.path === 'login')?.file).toBe('routes/login.tsx');
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch); await mount();
  const form = screen.getByRole('button', { name: 'Google로 로그인' }).closest('form');
  expect(form).toHaveAttribute('method', 'post'); expect(form).toHaveAttribute('action', '/api/v1/auth/google/start');
  expect(form?.querySelector('input')).toBeNull(); expect(fetch).not.toHaveBeenCalled();
  expect(screen.getByRole('link', { name: '홈으로' })).toHaveAttribute('href', '/');
});
it.each([['denied', '로그인을 취소했습니다.'], ['invalid', '로그인 요청을 확인하지 못했습니다. 다시 시도해 주세요.'], ['unavailable', '로그인 서비스가 아직 준비되지 않았거나 서버에 문제가 있습니다.']])('shows fixed Korean feedback for %s', async (error, message) => {
  await mount(`?error=${error}&error_description=PRIVATE`); expect(screen.getByRole('alert')).toHaveTextContent(message); expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
});
it.each(['?error=PRIVATE', '?error=denied&error=invalid', '?code=PRIVATE', '?error=constructor', '?error=__proto__'])('does not reflect or interpret other query values: %s', async query => {
  await mount(query); expect(screen.queryByRole('alert')).not.toBeInTheDocument(); expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
});
it('allows the first native submit, blocks duplicates and resets pending on bfcache pageshow', async () => {
  await mount(); const button = screen.getByRole('button', { name: 'Google로 로그인' }); const form = button.closest('form')!;
  const first = new Event('submit', { bubbles: true, cancelable: true }); fireEvent(form, first);
  expect(first.defaultPrevented).toBe(false); expect(screen.getByRole('button', { name: 'Google로 이동 중…' })).toBeDisabled();
  const duplicate = new Event('submit', { bubbles: true, cancelable: true }); fireEvent(form, duplicate); expect(duplicate.defaultPrevented).toBe(true);
  expect(screen.getByRole('status')).toHaveTextContent('이동'); fireEvent(window, new PageTransitionEvent('pageshow', { persisted: true }));
  expect(screen.getByRole('button', { name: 'Google로 로그인' })).toBeEnabled();
});
it('supports keyboard focus without fabricating a provider sign-in UI', async () => {
  await mount(); const user = userEvent.setup(); await user.tab(); await user.tab(); await user.tab(); await user.tab(); expect(screen.getByRole('button', { name: 'Google로 로그인' })).toHaveFocus();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  // Simulate the browser navigation boundary while exercising native keyboard submit.
  screen.getByRole('button', { name: 'Google로 로그인' }).closest('form')!.addEventListener('submit', event => event.preventDefault());
  await userEvent.setup().keyboard('{Enter}'); expect(screen.getByRole('button', { name: 'Google로 이동 중…' })).toBeDisabled();
});
it('can render the SPA login shell without browser APIs or side effects', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  expect(renderToString(<MemoryRouter initialEntries={['/login']}><Login /></MemoryRouter>)).toContain('Google로 로그인'); expect(fetch).not.toHaveBeenCalled();
});

it.each(['authenticated', 'guest', 'network'])('resolves %s account state lazily on login without starting OAuth', async state => {
  const fetch = vi.fn(async () => {
    if (state === 'network') throw new TypeError('offline');
    return response(state === 'authenticated' ? session() : {}, state === 'guest' ? 401 : 200);
  });
  vi.stubGlobal('fetch', fetch); mount(); expect(fetch).not.toHaveBeenCalled();
  await userEvent.setup().click(screen.getByRole('button', {name: '계정 메뉴'}));
  if (state === 'authenticated') {
    expect(await screen.findByRole('menuitem', {name: '로그아웃'})).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', {name: '로그인'})).not.toBeInTheDocument();
  } else if (state === 'guest') {
    expect(await screen.findByRole('menuitem', {name: '로그인'})).toHaveAttribute('href', '/login');
    expect(screen.queryByRole('menuitem', {name: '로그아웃'})).not.toBeInTheDocument();
  } else {
    expect(await screen.findByRole('menuitem', {name: '다시 확인'})).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', {name: '로그인'})).not.toBeInTheDocument();
    expect(screen.queryByRole('menuitem', {name: '로그아웃'})).not.toBeInTheDocument();
  }
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0]).toEqual(['/api/v1/auth/session', expect.objectContaining({method: 'GET', credentials: 'same-origin'})]);
  const form = screen.getByRole('button', {name: 'Google로 로그인'}).closest('form');
  expect(form).toHaveAttribute('method', 'post'); expect(form).toHaveAttribute('action', '/api/v1/auth/google/start');
});

const guestDraftKey = 'issuedigest.guest-question.v1';
afterEach(() => sessionStorage.removeItem(guestDraftKey));
it.each([true, false])('retains accurate login-route account and draft state after logout success=%s', async succeeds => {
  const storedDraft = JSON.stringify({version: 1, question: '보관한 질문', createdAt: Date.now()});
  sessionStorage.setItem(guestDraftKey, storedDraft);
  const fetch = vi.fn(async (path: string) => path.endsWith('/session') ? response(session()) : succeeds ? new Response(null, {status: 204, headers}) : response({}, 503));
  vi.stubGlobal('fetch', fetch);
  const router = createMemoryRouter([{path: '/login', Component: Login}], {initialEntries: ['/login']});
  render(<RouterProvider router={router} />); const user = userEvent.setup();
  expect(await screen.findByLabelText('이어갈 질문')).toHaveTextContent('보관한 질문');
  const account = screen.getByRole('button', {name: '계정 메뉴'}); await user.click(account);
  await user.click(await screen.findByRole('menuitem', {name: '로그아웃'}));
  if (succeeds) {
    await waitFor(() => expect(screen.queryByRole('menu')).not.toBeInTheDocument());
    expect(router.state.location.pathname).toBe('/login'); expect(account).toHaveFocus();
    expect(sessionStorage.getItem(guestDraftKey)).toBeNull();
    await waitFor(() => expect(screen.queryByLabelText('이어갈 질문')).not.toBeInTheDocument());
    await user.click(account); expect(await screen.findByRole('menuitem', {name: '로그인'})).toBeInTheDocument();
    expect(screen.queryByRole('menuitem', {name: '로그아웃'})).not.toBeInTheDocument();
  } else {
    expect(await screen.findByRole('alert')).toHaveTextContent('로그아웃하지 못했습니다');
    expect(screen.getByRole('menuitem', {name: '로그아웃'})).toBeEnabled();
    expect(screen.queryByRole('menuitem', {name: '로그인'})).not.toBeInTheDocument();
    expect(sessionStorage.getItem(guestDraftKey)).toBe(storedDraft);
    expect(screen.getByLabelText('이어갈 질문')).toHaveTextContent('보관한 질문');
  }
  expect(fetch).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls[1]).toEqual(['/api/v1/auth/logout', expect.objectContaining({method: 'POST', credentials: 'same-origin'})]);
});
