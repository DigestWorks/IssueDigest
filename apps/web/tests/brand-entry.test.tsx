import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderToString } from 'react-dom/server';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import Login from '../app/routes/login';
import BrandHeader from '../app/brand-header';
import { response, session } from './workspace-data';

function mount(entry = '/') {
  const router = createMemoryRouter([{path: '/', Component: Home}, {path: '/login', Component: Login}], {initialEntries: [entry]});
  return {router, ...render(<RouterProvider router={router} />)};
}
afterEach(() => { localStorage.clear(); document.documentElement.removeAttribute('data-theme'); document.documentElement.removeAttribute('data-theme-source'); vi.restoreAllMocks(); });
it('shows the current theme and changes it explicitly, retaining the choice after route changes and remount', async () => {
  vi.stubGlobal('matchMedia', () => ({matches: true, addEventListener: vi.fn(), removeEventListener: vi.fn()}));
  const view = mount('/login'); const user = userEvent.setup();
  await user.click(await screen.findByRole('button', {name: '현재 어두운 테마 · 밝게 전환'}));
  expect(document.documentElement).toHaveAttribute('data-theme', 'light');
  expect(localStorage.getItem('issuedigest.theme.v1')).toBe('light');
  vi.stubGlobal('fetch', async () => response({}, 401));
  await user.click(screen.getByRole('link', {name: '홈으로'}));
  expect(await screen.findByRole('button', {name: '현재 밝은 테마 · 어둡게 전환'})).toBeInTheDocument();
  view.unmount(); mount('/login');
  expect(await screen.findByRole('button', {name: '현재 밝은 테마 · 어둡게 전환'})).toBeInTheDocument();
});
it('still switches theme when preference storage is denied and renders without browser APIs on the server', async () => {
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {throw new DOMException('denied');});
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {throw new DOMException('denied');});
  mount('/login'); await userEvent.setup().click(screen.getByRole('button', {name: '현재 밝은 테마 · 어둡게 전환'}));
  expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  const browserWindow = window; vi.stubGlobal('window', undefined);
  try {expect(renderToString(<MemoryRouter><Login /></MemoryRouter>)).toContain('Google로 로그인');}
  finally {vi.stubGlobal('window', browserWindow);}
});
it('keeps login inside the account menu and supports arrows, Escape, outside click and focus return', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401)); mount('/login'); const user = userEvent.setup(); const account = screen.getByRole('button', {name: '계정 메뉴'});
  expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  account.focus(); await user.keyboard('{ArrowDown}');
  expect(screen.getByRole('menuitem', {name: '로그인'})).toHaveFocus();
  await user.keyboard('{Escape}'); expect(screen.queryByRole('menu')).not.toBeInTheDocument(); expect(account).toHaveFocus();
  await user.click(account); await user.click(screen.getByRole('heading', {level: 1}));
  expect(screen.queryByRole('menu')).not.toBeInTheDocument(); expect(account).toHaveFocus();
});
it('shows a quiet guest home with one question action and no repeated login notices', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401)); mount();
  const submit = await screen.findByRole('button', {name: '질문하기'});
  expect(submit).toBeDisabled(); expect(screen.queryByText('로그인이 필요합니다.')).not.toBeInTheDocument();
  expect(screen.queryByText(/로그인 후/)).not.toBeInTheDocument();
  expect(screen.queryByRole('link', {name: '로그인'})).not.toBeInTheDocument();
  expect(screen.getByText('공개 브리핑을 준비하고 있습니다.')).toBeInTheDocument();
  const input = screen.getByRole('textbox', {name: '무엇이 궁금한가요?'}); await userEvent.setup().type(input, '   ');
  expect(submit).toBeDisabled(); expect(sessionStorage.getItem('issuedigest.guest-question.v1')).toBeNull();
});
it.each(['saved'])('opens login only after confirmed guest navigation to private %s', async () => {
  const fetch = vi.fn(async () => response({}, 401)); vi.stubGlobal('fetch', fetch); const {router} = mount();
  await screen.findByRole('textbox', {name: '무엇이 궁금한가요?'});
  await userEvent.setup().click(screen.getByRole('button', {name: '브리핑 기록'}));
  expect(router.state.location.pathname).toBe('/login'); expect(fetch.mock.calls).toHaveLength(1);
});
it.each(['saved', 'sources'])('waits for confirmed session before redirecting direct private %s without calling protected APIs', async view => {
  let finish!: (value: Response) => void; const fetch = vi.fn(() => new Promise<Response>(resolve => {finish = resolve;}));
  vi.stubGlobal('fetch', fetch); const {router} = mount(`/?view=${view}`);
  expect(router.state.location.pathname).toBe('/'); expect(fetch.mock.calls).toHaveLength(1);
  await act(async () => finish(response({}, 401)));
  await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  expect(fetch.mock.calls).toHaveLength(1);
});
it.each([403, 503, 'network'])('keeps private entry visible with retry on %s rather than treating it as guest', async failure => {
  const fetch = vi.fn(async () => {if (failure === 'network') throw new TypeError('offline'); return response({}, failure as number);});
  vi.stubGlobal('fetch', fetch); const {router} = mount('/?view=saved');
  await screen.findByRole('button', {name: '접근 상태 다시 확인'});
  expect(router.state.location.pathname).toBe('/'); expect(screen.queryByRole('textbox', {name: '무엇이 궁금한가요?'})).not.toBeInTheDocument(); expect(fetch.mock.calls).toHaveLength(1);
});
it('puts authenticated logout inside the account menu', async () => {
  vi.stubGlobal('fetch', async (path: string) => response(path.endsWith('/session') ? {...session(), memberships: []} : {})); mount();
  await screen.findByText('접근 가능한 자료 범위가 없습니다.'); expect(screen.queryByRole('button', {name: '로그아웃'})).not.toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole('button', {name: '계정 메뉴'})); expect(screen.getByRole('menuitem', {name: '로그아웃'})).toBeInTheDocument();
});
it('applies the same saved palette in the prepaint bootstrap before React mounts', async () => {
  const {themeBootstrap} = await import('../app/theme');
  localStorage.setItem('issuedigest.theme.v1', 'dark');
  vi.stubGlobal('matchMedia', () => ({matches: false}));
  // Run the exact inline script that root.tsx ships, without mounting a component.
  new Function(themeBootstrap)(); expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  localStorage.setItem('issuedigest.theme.v1', 'invalid');
  new Function(themeBootstrap)(); expect(document.documentElement).toHaveAttribute('data-theme', 'light');
});
it('bootstraps system dark even when reading device preferences is blocked, and is safe without a DOM', async () => {
  const {themeBootstrap} = await import('../app/theme');
  vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {throw new DOMException('denied');});
  vi.stubGlobal('matchMedia', () => ({matches: true}));
  new Function(themeBootstrap)(); expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  const browserDocument = document; vi.stubGlobal('document', undefined);
  try {expect(() => new Function(themeBootstrap)()).not.toThrow();} finally {vi.stubGlobal('document', browserDocument);}
});

it('closes account menu while preserving an intentional click into the guest question', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401)); mount(); const user = userEvent.setup();
  const input = await screen.findByRole('textbox', {name: '무엇이 궁금한가요?'});
  await user.click(screen.getByRole('button', {name: '계정 메뉴'})); await user.click(input);
  expect(screen.queryByRole('menu')).not.toBeInTheDocument(); expect(input).toHaveFocus();
});
it('lets Tab leave the open account menu toward the next page action', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401)); mount('/login'); const user = userEvent.setup();
  await user.click(screen.getByRole('button', {name: '계정 메뉴'}));
  expect(screen.getByRole('menuitem', {name: '로그인'})).toHaveFocus();
  await user.tab(); expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  expect(screen.getByRole('button', {name: 'Google로 로그인'})).toHaveFocus();
});

it('keeps Escape available while retrying reader account status without mistaking network failure for guest', async () => {
  let retry = false; vi.stubGlobal('fetch', async () => {if (!retry) throw new TypeError('offline'); return new Promise<Response>(() => {});});
  render(<MemoryRouter><BrandHeader caption="저장된 근거 읽기" /></MemoryRouter>); const user = userEvent.setup();
  await user.click(screen.getByRole('button', {name: '계정 메뉴'}));
  const again = await screen.findByRole('menuitem', {name: '다시 확인'}); expect(screen.queryByRole('menuitem', {name: '로그인'})).not.toBeInTheDocument();
  retry = true; await user.click(again); await user.keyboard('{Escape}');
  expect(screen.queryByRole('menu')).not.toBeInTheDocument(); expect(screen.getByRole('button', {name: '계정 메뉴'})).toHaveFocus();
});

it('follows changing system preference until the user chooses a theme', async () => {
  let change!: (event: MediaQueryListEvent) => void;
  vi.stubGlobal('matchMedia', () => ({matches: false, addEventListener: (_type: string, listener: typeof change) => {change = listener;}, removeEventListener: vi.fn()}));
  mount('/login');
  expect(typeof change).toBe('function');
  act(() => change({matches: true} as MediaQueryListEvent));
  expect(screen.getByRole('button', {name: '현재 어두운 테마 · 밝게 전환'})).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole('button', {name: '현재 어두운 테마 · 밝게 전환'}));
  act(() => change({matches: true} as MediaQueryListEvent));
  expect(document.documentElement).toHaveAttribute('data-theme', 'light');
});
