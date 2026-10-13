import { fireEvent, render, screen } from '@testing-library/react';
import { renderToString } from 'react-dom/server';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import routes from '../app/routes';
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
  expect(screen.getByRole('link', { name: '작업 공간으로' })).toHaveAttribute('href', '/');
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
  await mount(); await userEvent.setup().tab(); expect(screen.getByRole('button', { name: 'Google로 로그인' })).toHaveFocus();
  expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  // Simulate the browser navigation boundary while exercising native keyboard submit.
  screen.getByRole('button', { name: 'Google로 로그인' }).closest('form')!.addEventListener('submit', event => event.preventDefault());
  await userEvent.setup().keyboard('{Enter}'); expect(screen.getByRole('button', { name: 'Google로 이동 중…' })).toBeDisabled();
});
it('can render the SPA login shell without browser APIs or side effects', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  expect(renderToString(<MemoryRouter initialEntries={['/login']}><Login /></MemoryRouter>)).toContain('Google로 로그인'); expect(fetch).not.toHaveBeenCalled();
});
