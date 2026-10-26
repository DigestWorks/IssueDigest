import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import App from '../app/root';
import Home from '../app/routes/home';
import {
  readPendingQuestion,
  writePendingQuestion,
} from '../app/question-pending';
import { response, session, workspace, otherWorkspace } from './workspace-data';
const actor = session().user_id;
const requestId = '11111111-1111-4111-8111-111111111111';
afterEach(() => {
  sessionStorage.removeItem('issuedigest.question.pending.v1');
  vi.unstubAllGlobals();
});
function mount() {
  const router = createMemoryRouter([
    {
      path: '/',
      Component: App,
      children: [
        { index: true, Component: Home },
        { path: 'login', element: <p>다른 화면</p> },
      ],
    },
  ]);
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
