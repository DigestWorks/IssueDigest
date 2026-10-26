import fixture from '../../../tests/fixtures/canvas-synthetic.json';
import { jobId, job, response, completed } from './briefing-job-client.test';
import {
  act,
  render,
  screen,
  waitFor,
  fireEvent,
} from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { BriefingJobReader } from '../app/routes/briefing-job';
import { ResearchDraftProvider } from '../app/research-drafts';
import { readFileSync } from 'node:fs';
function mount() {
  return render(
    <MemoryRouter>
      <ResearchDraftProvider>
        <BriefingJobReader workspaceId={jobId} jobId={jobId} />
      </ResearchDraftProvider>
    </MemoryRouter>,
  );
}
afterEach(() => vi.useRealTimers());
it('loads real summary comparison timeline as plaintext without submitting', async () => {
  const fetcher = vi
    .fn()
    .mockImplementation(() => Promise.resolve(response(completed())));
  vi.stubGlobal('fetch', fetcher);
  mount();
  expect(screen.getByRole('status')).toHaveTextContent('불러오고');
  await screen.findByText('시간 흐름');
  expect(screen.getByText('<script>자료의 서술</script>')).toBeVisible();
  expect(document.querySelector('script')).toBeNull();
  expect(screen.getByText('확인하기 어려움')).toBeVisible();
  expect(fetcher).toHaveBeenCalledTimes(1);
  expect(fetcher.mock.calls[0][1].method).toBe('GET');
});
it('polls pending then running and terminal completion', async () => {
  vi.useFakeTimers();
  let count = 0;
  const fetcher = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(
        response(
          count++ === 0
            ? job
            : count === 2
              ? { ...job, status: 'running' }
              : completed(),
        ),
      ),
    );
  vi.stubGlobal('fetch', fetcher);
  mount();
  await act(async () => {});
  expect(screen.getByRole('status')).toHaveTextContent('준비');
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1600);
  });
  expect(screen.getByRole('status')).toHaveTextContent('작성하고');
  await act(async () => {
    await vi.advanceTimersByTimeAsync(1600);
  });
  expect(screen.getByText('요약')).toBeVisible();
  await act(async () => {
    await vi.advanceTimersByTimeAsync(3200);
  });
  expect(fetcher).toHaveBeenCalledTimes(3);
});
it('locks duplicate cancellation and presents cancelled status', async () => {
  let resolve!: (r: Response) => void;
  const fetcher = vi
    .fn()
    .mockImplementation((_url: string, options: RequestInit) =>
      options.method === 'POST'
        ? new Promise((r) => {
            resolve = r;
          })
        : Promise.resolve(response(job)),
    );
  vi.stubGlobal('fetch', fetcher);
  mount();
  const button = await screen.findByRole('button', { name: '브리핑 취소' });
  fireEvent.click(button);
  fireEvent.click(button);
  expect(button).toBeDisabled();
  expect(fetcher.mock.calls.filter((c) => c[1].method === 'POST')).toHaveLength(
    1,
  );
  await act(async () => resolve(response({ ...job, status: 'cancelled' })));
  expect(screen.getByRole('status')).toHaveTextContent('취소되었습니다');
});
it.each([401, 403, 404, 409, 503])(
  'clears result on focus recheck %i',
  async (status) => {
    let checked = false;
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation(() =>
          Promise.resolve(
            response(checked ? {} : completed(), checked ? status : 200),
          ),
        ),
    );
    mount();
    await screen.findByText('요약');
    checked = true;
    fireEvent.focus(window);
    await waitFor(() => expect(screen.queryByText('요약')).toBeNull());
    expect(screen.getByRole('alert')).toBeVisible();
    if (status === 401)
      expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute(
        'href',
        '/login',
      );
  },
);
it('keeps summary after network failure but requires fresh job before original', async () => {
  let checked = false;
  const fetcher = vi
    .fn()
    .mockImplementation(() =>
      checked
        ? Promise.reject(new TypeError('offline'))
        : Promise.resolve(response(completed())),
    );
  vi.stubGlobal('fetch', fetcher);
  mount();
  await screen.findByText('요약');
  checked = true;
  fireEvent.focus(window);
  await screen.findByRole('alert');
  expect(screen.getByText('요약')).toBeVisible();
  fireEvent.click(screen.getAllByText('원문 열기')[0]);
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(3));
  expect(screen.queryByRole('dialog')).toBeNull();
});
it('shows insufficient evidence message only', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockImplementation(() =>
        Promise.resolve(
          response({
            ...job,
            status: 'completed',
            result: {
              outcome: 'insufficient_evidence',
              message: '근거가 부족합니다.',
              modules: [],
              additional_quotes: [],
            },
          }),
        ),
      ),
  );
  mount();
  await screen.findByText('근거가 부족합니다.');
  expect(screen.queryByText('요약')).toBeNull();
});
it('discards late requests after recheck and unmount', async () => {
  let resolve!: (r: Response) => void;
  let first = true;
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() =>
      first
        ? ((first = false),
          new Promise((r) => {
            resolve = r;
          }))
        : Promise.resolve(response(completed())),
    ),
  );
  const view = mount();
  fireEvent.focus(window);
  await screen.findByText('요약');
  await act(async () => resolve(response(job)));
  expect(screen.getByText('요약')).toBeVisible();
  view.unmount();
});
it('uses brand tokens, narrow layout, touch controls and reduced motion', () => {
  const css = readFileSync('apps/web/app/briefing-job.css', 'utf8');
  expect(css).toContain('var(--paper)');
  expect(css).toContain('min-height: 44px');
  expect(css).toContain('max-width: 480px');
  expect(css).toContain('prefers-reduced-motion');
});
it.each([false, true])(
  'opens only exact freshly authorized citation (mismatch=%s)',
  async (mismatch) => {
    const data = completed();
    const proof = structuredClone(fixture.research.evidence[0]);
    const citation = proof.citations[0];
    proof.document.workspace_id = jobId;
    const q = {
      snapshot_id: jobId,
      citation_id: citation.citation_id,
      source_title: '합성 원자료',
      start: 0,
      end: Array.from(citation.selector.quote).length,
      text: citation.selector.quote,
      citation_quote: citation.selector.quote,
    };
    data.result.modules = [
      {
        kind: 'summary',
        title: '요약',
        claims: [
          {
            text: '합성 자료',
            epistemic_status: 'source_statement',
            event_date: null,
            quotes: [q],
          },
        ],
      },
    ];
    if (mismatch) proof.citations = [];
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockImplementation((url: string) =>
          Promise.resolve(response(url.includes('/evidence/') ? proof : data)),
        ),
    );
    mount();
    await screen.findByText('요약');
    fireEvent.click(screen.getByText('근거 읽기'));
    const origin = screen.getByRole('button', { name: '원문 열기' });
    origin.focus();
    fireEvent.click(origin);
    if (mismatch) {
      await screen.findByRole('alert');
      expect(screen.queryByRole('dialog')).toBeNull();
      expect(screen.queryByText('요약')).toBeNull();
    } else {
      const dialog = await screen.findByRole('dialog');
      expect(dialog).toBeVisible();
      fireEvent(
        dialog,
        new Event('cancel', { bubbles: true, cancelable: true }),
      );
      await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
      expect(origin).toHaveFocus();
    }
  },
);
it('ignores late cancellation after a focus authority loss', async () => {
  let resolve!: (r: Response) => void;
  let revoked = false;
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation((_url: string, options: RequestInit) =>
      options.method === 'POST'
        ? new Promise((r) => {
            resolve = r;
          })
        : Promise.resolve(response(revoked ? {} : job, revoked ? 403 : 200)),
    ),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '브리핑 취소' }));
  revoked = true;
  fireEvent.focus(window);
  await screen.findByRole('alert');
  await act(async () => resolve(response(completed())));
  expect(screen.queryByText('요약')).toBeNull();
});
it('exposes cancellation connection failure and retry without treating it as withdrawal', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockImplementation((_url: string, options: RequestInit) =>
        options.method === 'POST'
          ? Promise.reject(new TypeError('offline'))
          : Promise.resolve(response(job)),
      ),
  );
  mount();
  fireEvent.click(await screen.findByRole('button', { name: '브리핑 취소' }));
  await screen.findByRole('alert');
  expect(screen.getByRole('button', { name: '브리핑 취소' })).toBeEnabled();
  expect(screen.getByRole('button', { name: '다시 조회' })).toBeEnabled();
});
