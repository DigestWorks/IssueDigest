import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../app/root';
import Home from '../app/routes/home';
import EvidenceRoute from '../app/routes/evidence';
import {
  readPendingQuestion,
  writePendingQuestion,
} from '../app/question-pending';
import { response, session, workspace, otherWorkspace, snapshot } from './workspace-data';
const actor = session().user_id;
const requestId = '11111111-1111-4111-8111-111111111111';
afterEach(() => {
  sessionStorage.removeItem('issuedigest.question.pending.v1');
  vi.unstubAllGlobals();
});
function mount(entry = "/") {
  const router = createMemoryRouter([
    {
      path: '/',
      Component: App,
      children: [
        { index: true, Component: Home },
        { path: 'login', element: <p>다른 화면</p> },
        { path: 'workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute },
      ],
    },
  ], {initialEntries: [entry]});
  render(<RouterProvider router={router} />);
  return router;
}
it('retains A pending through first-membership reorder to B then A and retries original ID only explicitly', async () => {
  writePendingQuestion(actor, otherWorkspace, {
    request_id: requestId,
    question: 'A 질문',
  });
  let memberships = [
    { workspace_id: workspace, role: 'editor' },
    { workspace_id: otherWorkspace, role: 'editor' },
  ];
  const posted: Record<string, unknown>[] = [];
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    if (path.endsWith('/session'))
      return response({ ...session(), memberships });
    if (options.method === 'POST') {
      posted.push(JSON.parse(options.body as string));
      return response({}, 503);
    }
    return response({}, 404);
  });
  const router = mount();
  expect(await screen.findByRole('textbox')).toHaveValue('');
  expect(readPendingQuestion(actor, otherWorkspace)?.request_id).toBe(
    requestId,
  );
  expect(posted).toHaveLength(0);
  await act(async () => router.navigate('/login'));
  memberships = [memberships[1]];
  await act(async () => router.navigate('/'));
  expect(await screen.findByRole('textbox')).toHaveValue('A 질문');
  expect(posted).toHaveLength(0);
  await userEvent.click(
    screen.getByRole('button', { name: '같은 질문 다시 확인' }),
  );
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0].request_id).toBe(requestId);
});
it.each([401, 403, 404, 503])(
  'handles interrupted submit then saved HTTP %s with scoped authority cleanup or transient retention',
  async (status) => {
    const posted: Record<string, unknown>[] = [];
    vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
      if (path.endsWith('/session'))
        return response({
          ...session(),
          memberships: [{ workspace_id: workspace, role: 'editor' }],
        });
      if (path.endsWith('/question-briefings')) {
        posted.push(JSON.parse(options.body as string));
        return new Promise<Response>(() => {});
      }
      if (path.endsWith('/briefing-jobs')) return response({}, status);
      if (path.endsWith('/research'))
        return response({ workspace_id: workspace, items: [] });
      return response({}, 404);
    });
    const router = mount();
    const user = userEvent.setup();
    await user.type(await screen.findByRole('textbox'), '중단된 질문');
    await user.click(screen.getByRole('button', { name: '질문하기' }));
    expect(posted).toHaveLength(1);
    await user.click(screen.getByRole('button', { name: '브리핑 기록' }));
    await screen.findByText('브리핑 기록을 불러오지 못했습니다.');
    await user.click(screen.getByRole('button', { name: '브리핑' }));
    const input = await screen.findByRole('textbox');
    if (status === 503) {
      expect(input).toHaveValue('중단된 질문');
      expect(readPendingQuestion(actor, workspace)?.request_id).toBe(
        posted[0].request_id,
      );
      expect(
        screen.getByRole('button', { name: '같은 질문 다시 확인' }),
      ).toBeEnabled();
    } else {
      expect(input).toHaveValue('');
      expect(input).toBeDisabled();
      expect(readPendingQuestion(actor, workspace)).toBeNull();
      expect(posted).toHaveLength(1);
      await user.click(
        screen.getByRole('button', { name: '접근 상태 다시 확인' }),
      );
      expect(await screen.findByRole('textbox')).toBeEnabled();
      expect(screen.getByRole('textbox')).toHaveValue('');
      expect(posted).toHaveLength(1);
    }
    expect(router.state.location.pathname).toBe('/');
  },
);

it.each([
  ['original', 401], ['original', 403], ['original', 404], ['original', 503],
  ['legacy', 401], ['legacy', 403], ['legacy', 404], ['legacy', 503],
] as const)('handles real submitted pending after %s HTTP %s through the shared authority boundary', async (origin, status) => {
  const posted: Record<string, unknown>[] = [];
  writePendingQuestion(actor, otherWorkspace, {request_id: requestId, question: '다른 공간 질문'});
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    if (path.endsWith('/session')) return response({...session(), memberships: [
      {workspace_id: workspace, role: 'editor'},
      {workspace_id: otherWorkspace, role: 'editor'},
    ]});
    if (path.endsWith('/question-briefings')) {
      posted.push(JSON.parse(options.body as string));
      return response({}, 503);
    }
    if (path.endsWith(`/evidence/${snapshot}`) || path.endsWith(`/research/${requestId}`)) return response({}, status);
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: []});
    return response({}, 404);
  });
  const router = mount(); const user = userEvent.setup();
  await user.type(await screen.findByRole('textbox'), '접근 거부 후 지울 제출 질문');
  await user.click(screen.getByRole('button', {name: '질문하기'}));
  await screen.findByRole('button', {name: '같은 질문 다시 확인'});
  expect(posted).toHaveLength(1);
  expect(readPendingQuestion(actor, workspace)?.request_id).toBe(posted[0].request_id);
  await act(async () => router.navigate(origin === 'original'
    ? `/workspaces/${workspace}/evidence/${snapshot}` : `/?view=research&run=${requestId}`));
  await screen.findByText(origin === 'original'
    ? status === 401 ? '다른 화면' : status === 503 ? '자료 읽기가 아직 준비되지 않았거나 서버에 문제가 있습니다.' : '자료가 없거나 접근 권한이 없습니다.'
    : status === 401 ? '로그인이 필요합니다.' : status === 403 ? '이 작업을 할 권한이 없습니다.' : status === 404 ? '자료 또는 브리핑을 찾을 수 없습니다.' : 'AI 연결을 기다리는 중이거나 서비스에 일시적인 문제가 있습니다.');
  await act(async () => router.navigate('/'));
  expect(await screen.findByRole('textbox')).toHaveValue(status === 503 ? '접근 거부 후 지울 제출 질문' : '');
  expect(readPendingQuestion(actor, workspace)).toEqual(status === 503 ? posted[0] : null);
  expect(readPendingQuestion(actor, otherWorkspace)).toEqual({request_id: requestId, question: '다른 공간 질문'});
  expect(posted).toHaveLength(1);
});
it('keeps saved and legacy sibling identities distinct across navigation without duplicate key errors', async () => {
  const errors = vi.spyOn(console, 'error');
  try {
    vi.stubGlobal('fetch', async (path: string) => {
      if (path.endsWith('/session')) return response({...session(), memberships: [{workspace_id: workspace, role: 'editor'}]});
      if (path.endsWith('/briefing-jobs')) return response({items: []});
      if (path.endsWith('/research')) return response({workspace_id: workspace, items: []});
      return response({}, 404);
    });
    const router = mount();
    await screen.findByRole('textbox');
    for (let i = 0; i < 2; i++) {
      await act(async () => router.navigate('/?view=saved'));
      await screen.findByText('저장된 질문 브리핑이 없습니다.');
      await act(async () => router.navigate(`/?view=research&run=${requestId}`));
      await screen.findByText('자료 또는 브리핑을 찾을 수 없습니다.');
      await act(async () => router.navigate('/'));
      await screen.findByRole('textbox');
    }
    expect(errors.mock.calls.filter(call => call.some(value => typeof value === 'string' && /same key|unique.*key/i.test(value)))).toEqual([]);
  } finally { errors.mockRestore(); }
});

it.each([404, 503])('scopes fresh direct-reader HTTP %s cleanup before Home identifies the actor', async status => {
  writePendingQuestion(actor, workspace, {request_id: requestId, question: '새로고침 전 보류 질문'});
  writePendingQuestion(actor, otherWorkspace, {request_id: requestId, question: '다른 공간 보류 질문'});
  vi.stubGlobal('fetch', async (path: string) => {
    if (path.endsWith(`/evidence/${snapshot}`)) return response({}, status);
    if (path.endsWith('/session')) return response({...session(), memberships: [
      {workspace_id: workspace, role: 'editor'}, {workspace_id: otherWorkspace, role: 'editor'},
    ]});
    return response({}, 404);
  });
  const router = mount(`/workspaces/${workspace}/evidence/${snapshot}`);
  await screen.findByText(status === 404 ? '자료가 없거나 접근 권한이 없습니다.' : '자료 읽기가 아직 준비되지 않았거나 서버에 문제가 있습니다.');
  await act(async () => router.navigate('/'));
  expect(await screen.findByRole('textbox')).toHaveValue(status === 404 ? '' : '새로고침 전 보류 질문');
  expect(readPendingQuestion(actor, workspace)).toEqual(status === 404 ? null : {request_id: requestId, question: '새로고침 전 보류 질문'});
  expect(readPendingQuestion(actor, otherWorkspace)?.question).toBe('다른 공간 보류 질문');
});
