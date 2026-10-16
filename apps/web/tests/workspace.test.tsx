import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import canvas from '../../../tests/fixtures/canvas-synthetic.json';
import Home from '../app/routes/home';
import EvidenceRoute from '../app/routes/evidence';
import { catalog, headers, otherWorkspace, requestId, response, session, snapshot, workspace } from './workspace-data';

function mount() {
  const router = createMemoryRouter([{ path: '/', Component: Home }, { path: '/login', element: <h1>로그인 도착</h1> }, { path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute }], {initialEntries: ['/?view=sources']});
  const view = render(<RouterProvider router={router} />); return { router, ...view };
}
function stub() { vi.stubGlobal('fetch', async (path: string) => response(path.endsWith('/session') ? session() : catalog(path.includes(otherWorkspace) ? otherWorkspace : workspace))); }
afterEach(() => vi.useRealTimers());
it('checks session before requesting a catalog and announces loading without fake empty data', async () => {
  let resolve!: (r: Response) => void; const fetch = vi.fn(() => new Promise<Response>(done => { resolve = done; })); vi.stubGlobal('fetch', fetch); mount();
  expect(screen.getByRole('status', { name: '작업 공간 상태' })).toHaveTextContent('로그인 상태');
  expect(screen.queryByText('아직 등록된 자료가 없습니다.')).not.toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
  await act(async () => resolve(response({ ...session(), memberships: [] })));
  expect(screen.getByText('접근 가능한 작업 공간이 없습니다.')).toBeInTheDocument(); expect(fetch).toHaveBeenCalledTimes(1);
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
    } return response(catalog());
  }); mount(); const retry = await screen.findByRole('button', { name: '작업 공간 다시 확인' });
  expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument(); failure = false; await userEvent.setup().click(retry);
  expect(await screen.findByText('첫 공간 합성 원문')).toBeInTheDocument(); expect(screen.getByRole('combobox', { name: '작업 공간' })).toHaveValue(workspace);
  expect(screen.getAllByRole('option').map(option => option.getAttribute('value'))).toEqual([workspace, otherWorkspace]);
});
it('displays provider, source ID, collected instant, citation count and a safe reader link', async () => {
  stub(); mount(); expect(await screen.findByText('첫 공간 합성 원문')).toBeInTheDocument();
  expect(screen.getByText('합성 공급처')).toBeInTheDocument(); expect(screen.getByText('인용 3개')).toBeInTheDocument();
  expect(screen.getByText('synthetic-source').closest('details')).not.toHaveAttribute('open');
  expect(document.querySelector('time')).toHaveAttribute('datetime', '2026-10-13T00:00:00Z');
  expect(document.querySelector('time')).toHaveTextContent('2026. 10. 13.');
  expect(screen.getByText('기타 자료')).toBeInTheDocument();
  expect(screen.getByRole('link', { name: '근거 열기' })).toHaveAttribute('href', `/workspaces/${workspace}/evidence/${snapshot}`);
  expect(screen.getByText('읽기')).toHaveAttribute('title', '읽기 권한');
});
it('names a single shared workspace without displaying its UUID in the main view', async () => {
  vi.stubGlobal('fetch', async (path: string) => response(path.endsWith('/session') ? { ...session(), memberships: [session().memberships[0]] } : catalog()));
  mount(); await screen.findByText('첫 공간 합성 원문');
  expect(screen.getByText('공동 조사 자료')).toBeInTheDocument();
  expect(screen.queryByRole('combobox', { name: '작업 공간' })).not.toBeInTheDocument();
  expect(screen.queryByText(workspace)).not.toBeInTheDocument();
});
it('numbers multiple workspaces while preserving exact IDs in optional details', async () => {
  stub(); mount(); await screen.findByText('첫 공간 합성 원문');
  expect(screen.getAllByRole('option').map(option => option.textContent)).toEqual(['공간 1', '공간 2']);
  expect(screen.queryByText(workspace)).not.toBeInTheDocument();
});
it('clears the old list immediately, cancels it and ignores late responses while switching workspaces', async () => {
  let resolve!: (r: Response) => void; let firstSignal!: AbortSignal;
  vi.stubGlobal('fetch', (path: string, options: RequestInit) => {
    if (path.endsWith('/session')) return Promise.resolve(response(session()));
    if (path.includes(workspace)) { firstSignal = options.signal as AbortSignal; return new Promise<Response>(done => { resolve = done; }); }
    return Promise.resolve(response(catalog(otherWorkspace)));
  }); mount(); await screen.findByRole('combobox'); await userEvent.setup().selectOptions(screen.getByRole('combobox'), otherWorkspace);
  expect(firstSignal.aborted).toBe(true); expect(await screen.findByText('두 번째 공간 합성 원문')).toBeInTheDocument();
  await act(async () => resolve(response(catalog()))); expect(screen.queryByText('첫 공간 합성 원문')).not.toBeInTheDocument();
});
it('clears already visible items on selection and reloads a reselected workspace', async () => {
  let second!: (r: Response) => void;
  const fetch = vi.fn((path: string) => path.endsWith('/session') ? Promise.resolve(response(session())) : path.includes(otherWorkspace) ? new Promise<Response>(done => { second = done; }) : Promise.resolve(response(catalog()))); vi.stubGlobal('fetch', fetch);
  mount(); await screen.findByText('첫 공간 합성 원문'); const user = userEvent.setup(); await user.selectOptions(screen.getByRole('combobox'), otherWorkspace);
  expect(screen.queryByText('첫 공간 합성 원문')).not.toBeInTheDocument(); expect(screen.getByRole('status', { name: '자료 목록 상태' })).toHaveTextContent('읽는 중');
  await user.selectOptions(screen.getByRole('combobox'), workspace); expect(await screen.findByText('첫 공간 합성 원문')).toBeInTheDocument();
  await act(async () => second(response(catalog(otherWorkspace)))); expect(screen.queryByText('두 번째 공간 합성 원문')).not.toBeInTheDocument();
});
it.each(['403', '404', '503', 'cross-workspace', 'corrupt-json'])('safely handles catalog %s and retries', async kind => {
  let failure = true; vi.stubGlobal('fetch', async (path: string) => {
    if (path.endsWith('/session')) return response(session());
    if (!failure) return response(catalog());
    if (kind === 'corrupt-json') return new Response('{PRIVATE', { headers });
    if (kind === 'cross-workspace') return response(catalog(otherWorkspace));
    return response({ detail: 'PRIVATE' }, Number(kind));
  }); mount(); const retry = await screen.findByRole('button', { name: '자료 목록 다시 읽기' });
  expect(screen.queryByText('첫 공간 합성 원문')).not.toBeInTheDocument(); expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
  failure = false; await userEvent.setup().click(retry); expect(await screen.findByText('첫 공간 합성 원문')).toBeInTheDocument();
});
it('distinguishes a verified empty catalog from the bounded has_more catalog', async () => {
  let empty = true; vi.stubGlobal('fetch', async (path: string) => response(path.endsWith('/session') ? session() : { ...catalog(), items: empty ? [] : catalog().items, has_more: !empty }));
  mount(); expect(await screen.findByText('아직 등록된 자료가 없습니다.')).toBeInTheDocument();
  empty = false; await userEvent.setup().selectOptions(screen.getByRole('combobox'), otherWorkspace); // Wrong workspace intentionally rejected, then reselect.
  await userEvent.setup().selectOptions(screen.getByRole('combobox'), workspace);
  expect(await screen.findByText(/최대 50개/)).toHaveTextContent('더 있습니다');
});
it('keeps data on logout failure, prevents duplicates and clears content on successful logout', async () => {
  let finish!: (r: Response) => void; let count = 0;
  vi.stubGlobal('fetch', (path: string) => path.endsWith('/logout') ? (count++, new Promise<Response>(done => { finish = done; })) : Promise.resolve(response(path.endsWith('/session') ? session() : catalog())));
  const { router } = mount(); await screen.findByText('첫 공간 합성 원문'); const user = userEvent.setup(); await user.click(screen.getByRole('button', {name: '계정 메뉴'})); await user.click(screen.getByRole('menuitem', { name: '로그아웃' }));
  const pending = screen.getByRole('menuitem', { name: '로그아웃 중…' }); expect(pending).toBeDisabled(); await user.click(pending); expect(count).toBe(1);
  await act(async () => finish(response({ detail: 'PRIVATE' }, 503))); expect(screen.getByText('첫 공간 합성 원문')).toBeInTheDocument(); expect(screen.getByRole('alert')).toHaveTextContent('로그아웃');
  await user.click(screen.getByRole('menuitem', { name: '로그아웃' })); await act(async () => finish(new Response(null, { status: 204, headers })));
  await waitFor(() => expect(router.state.location.pathname).toBe('/login')); expect(screen.queryByText('첫 공간 합성 원문')).not.toBeInTheDocument();
});
it('aborts session and catalog fetches on unmount', async () => {
  let signal!: AbortSignal; vi.stubGlobal('fetch', (_path: string, options: RequestInit) => { signal = options.signal as AbortSignal; return new Promise(() => {}); });
  const first = mount(); first.unmount(); expect(signal.aborted).toBe(true);
  vi.stubGlobal('fetch', (path: string, options: RequestInit) => { if (path.endsWith('/session')) return Promise.resolve(response(session())); signal = options.signal as AbortSignal; return new Promise(() => {}); });
  const second = mount(); await screen.findByRole('combobox'); second.unmount(); expect(signal.aborted).toBe(true);
});
it('shows only a valid request UUID in expandable failure support', async () => {
  vi.stubGlobal('fetch', async () => response({ detail: 'PRIVATE' }, 503)); mount(); expect(await screen.findByText(requestId)).toBeInTheDocument(); expect(screen.getByText(requestId).closest('details')).not.toHaveAttribute('open');
});
it('keeps retry session data when a timed-out session arrives late', async () => {
  vi.useFakeTimers(); let finish!: (r: Response) => void; let sessions = 0;
  vi.stubGlobal('fetch', (path: string) => path.endsWith('/session') && sessions++ === 0 ? new Promise<Response>(done => { finish = done; }) : Promise.resolve(response(path.endsWith('/session') ? session() : catalog())));
  mount(); await act(async () => vi.advanceTimersByTimeAsync(10_000));
  expect(screen.getByRole('status', { name: '작업 공간 상태' })).toHaveTextContent('시간이 길어');
  const retry = screen.getByRole('button', { name: '작업 공간 다시 확인' }); await act(async () => retry.click());
  expect(screen.getByText('첫 공간 합성 원문')).toBeInTheDocument();
  await act(async () => finish(response({ ...session(), memberships: [] }))); expect(screen.getByText('첫 공간 합성 원문')).toBeInTheDocument();
});
it('times out catalog body reading and retries without displaying an old body', async () => {
  vi.useFakeTimers(); let finish!: (body: unknown) => void; let catalogs = 0;
  vi.stubGlobal('fetch', async (path: string) => path.endsWith('/session') ? response(session()) : catalogs++ === 0 ? { ok: true, status: 200, headers: new Headers(headers), json: () => new Promise(done => { finish = done; }) } : response(catalog()));
  mount(); await act(async () => {}); // Commit session success so the catalog deadline has started.
  await act(async () => vi.advanceTimersByTimeAsync(10_000));
  expect(screen.getByRole('status', { name: '자료 목록 상태' })).toHaveTextContent('시간이 길어');
  await act(async () => screen.getByRole('button', { name: '자료 목록 다시 읽기' }).click()); expect(screen.getByText('첫 공간 합성 원문')).toBeInTheDocument();
  await act(async () => finish({ ...catalog(), items: [] })); expect(screen.getByText('첫 공간 합성 원문')).toBeInTheDocument();
});
it('opens a catalog record in the existing protected read-only reader and returns home', async () => {
  const fetch = vi.fn<(path: string, options?: RequestInit) => Promise<Response>>(async path => response(path.endsWith('/session') ? session() : path.endsWith(`/${snapshot}`) ? canvas.research.evidence[0] : catalog())); vi.stubGlobal('fetch', fetch);
  const { router } = mount(); const link = await screen.findByRole('link', { name: '근거 열기' }); link.focus(); await userEvent.setup().keyboard('{Enter}');
  expect(await screen.findByRole('heading', { name: '원문과 인용' })).toBeInTheDocument(); expect(router.state.location.pathname).toBe(`/workspaces/${workspace}/evidence/${snapshot}`);
  const readerRequest = fetch.mock.calls.find(([path]) => path === `/api/v1/workspaces/${workspace}/evidence/${snapshot}`);
  expect(readerRequest).toEqual([`/api/v1/workspaces/${workspace}/evidence/${snapshot}`, expect.objectContaining({credentials: 'same-origin', cache: 'no-store'})]);
  expect(readerRequest?.[1]?.method ?? 'GET').toBe('GET');
  expect(screen.queryByText('첫 공간 합성 원문')).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /생성|저장|수정/ })).not.toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole('link', { name: '작업 공간으로' })); expect(await screen.findByText('첫 공간 합성 원문')).toBeInTheDocument();
});
it('cancels logout on unmount without applying a late success', async () => {
  let signal!: AbortSignal; let finish!: (r: Response) => void;
  vi.stubGlobal('fetch', (path: string, options: RequestInit) => path.endsWith('/logout') ? (signal = options.signal as AbortSignal, new Promise<Response>(done => { finish = done; })) : Promise.resolve(response(path.endsWith('/session') ? session() : catalog())));
  const { unmount, router } = mount(); await screen.findByText('첫 공간 합성 원문'); await userEvent.setup().click(screen.getByRole('button', {name: '계정 메뉴'})); await userEvent.setup().click(screen.getByRole('menuitem', { name: '로그아웃' }));
  unmount(); expect(signal.aborted).toBe(true); await act(async () => finish(new Response(null, { status: 204, headers }))); expect(router.state.location.pathname).toBe('/');
});

it('redirects a current catalog401 to fixed login without a body CTA after verified session', async () => {
  vi.stubGlobal('fetch', async (path: string) => path.endsWith('/session') ? response(session()) : response({detail: 'PRIVATE'}, 401));
  const {router} = mount(); await screen.findByRole('heading', {name: '로그인 도착'});
  expect(router.state.location.pathname).toBe('/login'); expect(router.state.location.search).toBe('');
  expect(screen.queryByRole('link', {name: '로그인'})).not.toBeInTheDocument(); expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
});
