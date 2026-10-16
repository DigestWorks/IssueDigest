import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import {completedRun} from './research-data';
import { headers, requestId, response, session, workspace } from './workspace-data';

function mount() {
  const router = createMemoryRouter([{ path: '/', Component: Home }, { path: '/login', element: <h1>로그인 도착</h1> }], {initialEntries: ['/?view=saved']});
  const view = render(<RouterProvider router={router} />); return { router, ...view };
}
afterEach(() => vi.useRealTimers());
it('checks session before requesting protected history and announces loading without fake empty data', async () => {
  let resolve!: (r: Response) => void; const fetch = vi.fn(() => new Promise<Response>(done => { resolve = done; })); vi.stubGlobal('fetch', fetch); mount();
  expect(screen.getByRole('status', { name: '접근 상태' })).toHaveTextContent('로그인 상태');
  expect(screen.queryByText('아직 등록된 자료가 없습니다.')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => resolve(response({ ...session(), memberships: [] })));
  expect(screen.getByText('접근 가능한 자료 범위가 없습니다.')).toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
});
it('offers actual login navigation on 401 without leaking server details', async () => {
  vi.stubGlobal('fetch', async () => response({ detail: 'PRIVATE' }, 401)); const { router } = mount();
  await screen.findByRole('heading', {name: '로그인 도착'}); expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument(); expect(router.state.location.pathname).toBe('/login');
});
it.each(['503', 'network', 'malformed'])('retries session error %s and displays only verified workspace data', async kind => {
  let failure = true; vi.stubGlobal('fetch', async (path: string) => {
    if (path.endsWith('/session')) {
      if (failure && kind === 'network') throw new Error('PRIVATE');
      return failure ? response(kind === 'malformed' ? {} : { detail: 'PRIVATE' }, kind === '503' ? 503 : 200) : response(session());
    } return response({workspace_id:workspace,items:[completedRun()]});
  }); mount(); const retry = await screen.findByRole('button', { name: '접근 상태 다시 확인' });
  expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument(); failure = false; await userEvent.setup().click(retry);
  expect(await screen.findByText('법안의 핵심은?')).toBeInTheDocument(); expect(screen.getByRole('button', {name:/법안의 핵심은/})).toBeInTheDocument();
});
it('keeps data on logout failure, prevents duplicates and clears content on successful logout', async () => {
  let finish!: (r: Response) => void; let count = 0;
  vi.stubGlobal('fetch', (path: string) => path.endsWith('/logout') ? (count++, new Promise<Response>(done => { finish = done; })) : Promise.resolve(response(path.endsWith('/session') ? session() : {workspace_id:workspace,items:[completedRun()]})));
  const { router } = mount(); await screen.findByText('법안의 핵심은?'); const user = userEvent.setup(); await user.click(screen.getByRole('button', {name: '계정 메뉴'})); await user.click(screen.getByRole('menuitem', { name: '로그아웃' }));
  const pending = screen.getByRole('menuitem', { name: '로그아웃 중…' }); expect(pending).toBeDisabled(); await user.click(pending); expect(count).toBe(1);
  await act(async () => finish(response({ detail: 'PRIVATE' }, 503))); expect(screen.getByText('법안의 핵심은?')).toBeInTheDocument(); expect(screen.getByRole('alert')).toHaveTextContent('로그아웃');
  await user.click(screen.getByRole('menuitem', { name: '로그아웃' })); await act(async () => finish(new Response(null, { status: 204, headers })));
  await waitFor(() => expect(router.state.location.pathname).toBe('/login')); expect(screen.queryByText('법안의 핵심은?')).not.toBeInTheDocument();
});
it('aborts session and history fetches on unmount', async () => {
  let signal!: AbortSignal; vi.stubGlobal('fetch', (_path: string, options: RequestInit) => { signal = options.signal as AbortSignal; return new Promise(() => {}); });
  const first = mount(); first.unmount(); expect(signal.aborted).toBe(true);
  let historySignal: AbortSignal | undefined;
  vi.stubGlobal('fetch', (path: string, options: RequestInit) => { if (path.endsWith('/session')) return Promise.resolve(response(session())); historySignal = options.signal as AbortSignal; return new Promise(() => {}); });
  const second = mount(); await waitFor(() => expect(historySignal).toBeInstanceOf(AbortSignal)); second.unmount(); expect(historySignal?.aborted).toBe(true);
});
it('shows only a valid request UUID in expandable failure support', async () => {
  vi.stubGlobal('fetch', async () => response({ detail: 'PRIVATE' }, 503)); mount(); expect(await screen.findByText(requestId)).toBeInTheDocument(); expect(screen.getByText(requestId).closest('details')).not.toHaveAttribute('open');
});
it('keeps retry session data when a timed-out session arrives late', async () => {
  vi.useFakeTimers(); let finish!: (r: Response) => void; let sessions = 0;
  vi.stubGlobal('fetch', (path: string) => path.endsWith('/session') && sessions++ === 0 ? new Promise<Response>(done => { finish = done; }) : Promise.resolve(response(path.endsWith('/session') ? session() : {workspace_id:workspace,items:[completedRun()]})));
  mount(); await act(async () => vi.advanceTimersByTimeAsync(10_000));
  expect(screen.getByRole('status', { name: '접근 상태' })).toHaveTextContent('시간이 길어');
  const retry = screen.getByRole('button', { name: '접근 상태 다시 확인' }); await act(async () => retry.click());
  expect(screen.getByText('법안의 핵심은?')).toBeInTheDocument();
  await act(async () => finish(response({ ...session(), memberships: [] }))); expect(screen.getByText('법안의 핵심은?')).toBeInTheDocument();
});
it('cancels logout on unmount without applying a late success', async () => {
  let signal!: AbortSignal; let finish!: (r: Response) => void;
  vi.stubGlobal('fetch', (path: string, options: RequestInit) => path.endsWith('/logout') ? (signal = options.signal as AbortSignal, new Promise<Response>(done => { finish = done; })) : Promise.resolve(response(path.endsWith('/session') ? session() : {workspace_id:workspace,items:[completedRun()]})));
  const { unmount, router } = mount(); await screen.findByText('법안의 핵심은?'); await userEvent.setup().click(screen.getByRole('button', {name: '계정 메뉴'})); await userEvent.setup().click(screen.getByRole('menuitem', { name: '로그아웃' }));
  unmount(); expect(signal.aborted).toBe(true); await act(async () => finish(new Response(null, { status: 204, headers }))); expect(router.state.location.pathname).toBe('/');
});
