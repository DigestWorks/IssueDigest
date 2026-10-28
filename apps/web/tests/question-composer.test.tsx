import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, useLocation } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import QuestionComposer from '../app/question-composer';
import {
  clearPendingQuestion,
  reconcilePendingQuestions,
  readPendingQuestion,
  writePendingQuestion,
} from '../app/question-pending';
const actor = '11111111-1111-4111-8111-111111111111';
const workspace = '22222222-2222-4222-8222-222222222222';
afterEach(() => {
  sessionStorage.clear();
  vi.unstubAllGlobals();
});
function Location() {
  return <div data-testid="location">{useLocation().pathname}</div>;
}
function mount(initialQuestion?: string) {
  render(
    <MemoryRouter>
      <QuestionComposer
        actor={actor}
        workspaceId={workspace}
        initialQuestion={initialQuestion}
        onInitialQuestionInitialized={() => {}}
        canEdit
      />
      <Location />
    </MemoryRouter>,
  );
}
it('shows busy immediately, prevents duplicate requests and navigates on real result', async () => {
  let finish!: (v: Response) => void;
  const fetch = vi.fn(
    () =>
      new Promise<Response>((resolve) => {
        finish = resolve;
      }),
  );
  vi.stubGlobal('fetch', fetch);
  mount('질문');
  const user = userEvent.setup();
  await user.click(screen.getByRole('button', { name: '질문하기' }));
  expect(screen.getByRole('button')).toBeDisabled();
  expect(screen.getByRole('status')).toHaveTextContent('접수');
  const body = JSON.parse(
    (fetch.mock.calls as unknown as [string, RequestInit][])[0][1]
      .body as string,
  );
  finish(
    new Response(
      `event: result\ndata: ${JSON.stringify({ request_id: body.request_id, kind: 'briefing', job_id: workspace })}\n\n`,
      {
        headers: {
          'Content-Type': 'text/event-stream; charset=utf-8',
          'Cache-Control': 'no-store',
          'X-Request-ID': actor,
          'X-Accel-Buffering': 'no',
        },
      },
    ),
  );
  await waitFor(() => expect(screen.getByRole('status')).toBeEmptyDOMElement());
  expect(screen.getByRole('status').parentElement).toHaveAttribute(
    'aria-busy',
    'false',
  );
  await waitFor(() =>
    expect(screen.getByTestId('location')).toHaveTextContent(
      `/workspaces/${workspace}/briefings/${workspace}`,
    ),
  );
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(readPendingQuestion(actor, workspace)).toBeNull();
});
it('restores pending question without execution and reuses its id only on explicit retry', async () => {
  writePendingQuestion(actor, workspace, {
    request_id: actor,
    question: '원래 질문',
  });
  const fetch = vi.fn().mockRejectedValue(new TypeError());
  vi.stubGlobal('fetch', fetch);
  mount();
  expect(screen.getByRole('textbox')).toHaveValue('원래 질문');
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(
    screen.getByRole('button', { name: '같은 질문 다시 확인' }),
  );
  await screen.findByText(/응답을 확인하지/);
  expect(JSON.parse(fetch.mock.calls[0][1].body).request_id).toBe(actor);
  await userEvent.clear(screen.getByRole('textbox'));
  await userEvent.type(screen.getByRole('textbox'), '다른 질문');
  await userEvent.click(screen.getByRole('button', { name: '질문하기' }));
  await waitFor(() => expect(fetch).toHaveBeenCalledTimes(2));
  expect(JSON.parse(fetch.mock.calls[1][1].body).request_id).not.toBe(actor);
});
it('clears pending data on actor mismatch', () => {
  writePendingQuestion(actor, workspace, {
    request_id: actor,
    question: '질문',
  });
  expect(readPendingQuestion(workspace, workspace)).toBeNull();
  expect(sessionStorage.length).toBe(0);
});
it.each(['no_match', 'blocked'] as const)(
  'shows truthful %s without navigation or fake percentage',
  async (kind) => {
    const fetch = vi.fn(async (_path: string, options: RequestInit) => {
      const input = JSON.parse(options.body as string);
      return new Response(
        `event: result\ndata: ${JSON.stringify({ request_id: input.request_id, kind, job_id: null })}\n\n`,
        {
          headers: {
            'Content-Type': 'text/event-stream; charset=utf-8',
            'Cache-Control': 'no-store',
            'X-Request-ID': actor,
            'X-Accel-Buffering': 'no',
          },
        },
      );
    });
    vi.stubGlobal('fetch', fetch);
    mount('질문');
    await userEvent.click(screen.getByRole('button', { name: '질문하기' }));
    expect(
      await screen.findByText(
        kind === 'no_match'
          ? '질문에 답할 수 있는 근거를 찾지 못했습니다.'
          : '현재 자료에서는 질문에 답할 충분한 근거를 확인하지 못했습니다.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('/');
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument();
    expect(readPendingQuestion(actor, workspace)).toBeNull();
    expect(screen.getByRole('textbox')).toHaveValue('질문');
    expect(screen.getByRole('button', { name: '질문하기' })).toBeEnabled();
    expect(screen.queryByText(/응답을 확인하지 못했습니다/)).not.toBeInTheDocument();
    expect(fetch).toHaveBeenCalledTimes(1);
  },
);
it.each([401, 403, 404])(
  'clears pending question and disables submission on lost authority %s',
  async (status) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('{}', { status })),
    );
    mount('비공개 질문');
    await userEvent.click(screen.getByRole('button', { name: '질문하기' }));
    await screen.findByText('접근 권한을 확인할 수 없습니다.');
    expect(screen.getByRole('textbox')).toHaveValue('');
    expect(screen.getByRole('button')).toBeDisabled();
    expect(readPendingQuestion(actor, workspace)).toBeNull();
  },
);
it('preserves workspace A request across B selection and explicitly retries A with its original UUID', async () => {
  writePendingQuestion(actor, workspace, {
    request_id: actor,
    question: 'A 질문',
  });
  expect(readPendingQuestion(actor, actor)).toBeNull();
  writePendingQuestion(actor, actor, {
    request_id: workspace,
    question: 'B 질문',
  });
  expect(readPendingQuestion(actor, workspace)).toEqual({
    request_id: actor,
    question: 'A 질문',
  });
  const fetch = vi.fn().mockRejectedValue(new TypeError());
  vi.stubGlobal('fetch', fetch);
  mount();
  expect(fetch).not.toHaveBeenCalled();
  await userEvent.click(
    screen.getByRole('button', { name: '같은 질문 다시 확인' }),
  );
  await screen.findByText(/응답을 확인하지/);
  expect(JSON.parse(fetch.mock.calls[0][1].body).request_id).toBe(actor);
});

it('scopes completion cleanup and reconciles membership loss separately', () => {
  writePendingQuestion(actor, workspace, { request_id: actor, question: 'A' });
  writePendingQuestion(actor, actor, { request_id: workspace, question: 'B' });
  clearPendingQuestion(actor, workspace);
  expect(readPendingQuestion(actor, actor)?.question).toBe('B');
  writePendingQuestion(actor, workspace, { request_id: actor, question: 'A' });
  reconcilePendingQuestions(actor, [workspace, actor]);
  expect(readPendingQuestion(actor, workspace)?.request_id).toBe(actor);
  reconcilePendingQuestions(actor, [workspace]);
  expect(readPendingQuestion(actor, actor)).toBeNull();
  expect(readPendingQuestion(actor, workspace)?.request_id).toBe(actor);
  clearPendingQuestion();
  expect(readPendingQuestion(actor, workspace)).toBeNull();
});
