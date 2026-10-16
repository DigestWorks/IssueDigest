import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../app/root';
import Home from '../app/routes/home';
import Login from '../app/routes/login';
import { headers, response, session, workspace, otherWorkspace } from './workspace-data';
const key = 'issuedigest.guest-question.v1';
function seed(question = '로그인 전에 쓴 질문') { sessionStorage.setItem(key, JSON.stringify({version: 1, question, createdAt: Date.now()})); }
afterEach(() => { sessionStorage.removeItem(key); sessionStorage.removeItem('unrelated'); vi.restoreAllMocks(); });
function mount(entry = '/') {
  const router = createMemoryRouter([{path: '/', Component: App, children: [{index: true, Component: Home}, {path: 'login', Component: Login}]}], {initialEntries: [entry]});
  const view = render(<StrictMode><RouterProvider router={router} /></StrictMode>); return {router, ...view};
}
function signedIn(memberships = session().memberships) {
  const fetch = vi.fn<(path: string, options?: RequestInit) => Promise<Response>>(async path => {
    if (path.endsWith('/session')) return response({...session(), memberships});
    const workspaceId = path.includes(otherWorkspace) ? otherWorkspace : workspace;
    if (path.endsWith('/research/sources') || path.endsWith('/research')) return response({workspace_id: workspaceId, items: []});
    if (path.endsWith('/logout')) return new Response(null, {status: 204, headers});
    return response({}, 404);
  }); vi.stubGlobal('fetch', fetch); return fetch;
}
it('keeps typing ephemeral until explicit guest continuation, then previews the question on login without URL data', async () => {
  const fetch = vi.fn<(path: string) => Promise<Response>>(async () => response({}, 401)); vi.stubGlobal('fetch', fetch);
  const {router} = mount(); const user = userEvent.setup();
  const input = await screen.findByRole('textbox', {name: '무엇이 궁금한가요?'});
  await user.type(input, '청년 교통비는 어떻게 달라졌나요?'); expect(sessionStorage.getItem(key)).toBeNull();
  await user.click(screen.getByRole('button', {name: '질문하기'}));
  expect(router.state.location.pathname).toBe('/login'); expect(router.state.location.search).toBe('');
  expect(screen.getByLabelText('이어갈 질문')).toHaveTextContent('청년 교통비는 어떻게 달라졌나요?');
  expect(fetch.mock.calls.every(([path]) => path.endsWith('/session'))).toBe(true);
});
it.each(['denied', 'invalid', 'unavailable'])('preserves the preview after OAuth %s and browser pageshow', async error => {
  seed(); const {router} = mount(`/login?error=${error}`);
  expect(await screen.findByLabelText('이어갈 질문')).toHaveTextContent('로그인 전에 쓴 질문');
  fireEvent(window, new PageTransitionEvent('pageshow', {persisted: true}));
  expect(sessionStorage.getItem(key)).not.toBeNull();
  await act(async () => router.navigate('/login')); expect(screen.getByLabelText('이어갈 질문')).toHaveTextContent('로그인 전에 쓴 질문');
});
it('restores a new research question once after verified membership, allowing edits without submitting', async () => {
  seed(); const fetch = signedIn([{workspace_id: workspace, role: 'editor'}]); const {router} = mount();
  const input = await screen.findByRole('textbox', {name: '무엇을 알아볼까요?'});
  expect(input).toHaveValue('로그인 전에 쓴 질문'); expect(sessionStorage.getItem(key)).toBeNull();
  await userEvent.setup().clear(input); await userEvent.setup().type(input, '고쳐 쓴 질문');
  await act(async () => router.navigate('/login')); await act(async () => router.navigate('/'));
  expect(await screen.findByRole('textbox', {name: '무엇을 알아볼까요?'})).toHaveValue('고쳐 쓴 질문');
  expect(fetch.mock.calls.every(([, options]) => !options || (options as RequestInit).method !== 'POST')).toBe(true);
});
it.each(['/?run=00000000-0000-4000-8000-000000000040', '/?view=saved', '/?view=sources'])('does not mix a guest question into an existing run or another entry: %s', async entry => {
  seed(); signedIn([{workspace_id: workspace, role: 'editor'}]); mount(entry);
  await waitFor(() => expect(document.querySelector('.workspace-choice')).not.toBeNull());
  expect(screen.queryByDisplayValue('로그인 전에 쓴 질문')).not.toBeInTheDocument(); expect(sessionStorage.getItem(key)).not.toBeNull();
});
it('does not consume on network failure or no memberships and only offers guest entry on confirmed 401', async () => {
  seed(); vi.stubGlobal('fetch', async () => { throw new TypeError('offline'); }); const first = mount();
  await screen.findByRole('button', {name: '작업 공간 다시 확인'});
  expect(screen.queryByRole('textbox', {name: '무엇이 궁금한가요?'})).not.toBeInTheDocument(); expect(sessionStorage.getItem(key)).not.toBeNull(); first.unmount();
  signedIn([]); mount(); await screen.findByText('접근 가능한 작업 공간이 없습니다.'); expect(sessionStorage.getItem(key)).not.toBeNull();
});
it('clears guest storage only after successful logout and preserves other keys', async () => {
  let succeed = false; const fetch = signedIn();
  vi.stubGlobal('fetch', async (path: string) => path.endsWith('/logout') ? succeed ? new Response(null, {status: 204, headers}) : response({}, 503) : fetch(path));
  const {router} = mount('/?view=sources'); seed(); sessionStorage.setItem('unrelated', 'keep'); const user = userEvent.setup();
  await waitFor(() => expect(document.querySelector('.workspace-choice')).not.toBeNull()); await user.click(screen.getByRole('button', {name: '계정 메뉴'})); await user.click(screen.getByRole('menuitem', {name: '로그아웃'})); await screen.findByRole('alert'); expect(sessionStorage.getItem(key)).not.toBeNull();
  succeed = true; await user.click(screen.getByRole('menuitem', {name: '로그아웃'})); await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  expect(sessionStorage.getItem(key)).toBeNull(); expect(sessionStorage.getItem('unrelated')).toBe('keep'); expect(screen.queryByLabelText('이어갈 질문')).not.toBeInTheDocument();
});
it('keeps guest restoration within the selected membership', async () => {
  seed(); signedIn(); mount(); const user = userEvent.setup();
  expect(await screen.findByRole('textbox', {name: '무엇을 알아볼까요?'})).toHaveValue('로그인 전에 쓴 질문');
  await user.selectOptions(screen.getByRole('combobox', {name: '작업 공간'}), otherWorkspace);
  expect(await screen.findByRole('textbox', {name: '무엇을 알아볼까요?'})).toHaveValue('');
});
it('reports refused guest storage without navigating or losing the typed question', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401)); const {router} = mount(); const user = userEvent.setup();
  const input = await screen.findByRole('textbox', {name: '무엇이 궁금한가요?'}); await user.type(input, '보관할 질문');
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new DOMException('blocked', 'SecurityError'); });
  await user.click(screen.getByRole('button', {name: '질문하기'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('임시 보관하지 못했습니다'); expect(input).toHaveValue('보관할 질문'); expect(router.state.location.pathname).toBe('/');
});
