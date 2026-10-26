import fixture from '../../../tests/fixtures/canvas-synthetic.json';

import {
  act,
  render,
  screen,
  waitFor,
  fireEvent,
  within,
} from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import { BriefingJobReader } from '../app/routes/briefing-job';
import { ResearchDraftProvider } from '../app/research-drafts';
const jobId = '00000000-0000-4000-8000-000000000040';
const job = {
  job_id: jobId,
  question: '자료의 내용은?',
  status: 'pending',
  result: null,
};
function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
      'X-Request-ID': jobId,
    },
  });
}
const quote = {
  snapshot_id: jobId,
  citation_id: jobId,
  source_title: '원자료',
  start: 1,
  end: 2,
  text: '😀',
  citation_quote: '가😀나',
};
function completed() {
  return {
    ...job,
    status: 'completed',
    result: {
      outcome: 'answer',
      message: null,
      additional_quotes: [],
      modules: [
        {
          kind: 'summary',
          title: '요약',
          claims: [
            {
              text: '<script>자료의 서술</script>',
              epistemic_status: 'source_statement',
              event_date: null,
              quotes: [quote],
            },
          ],
        },
        {
          kind: 'comparison',
          title: '비교',
          claims: [
            {
              text: '첫 자료',
              epistemic_status: 'source_statement',
              event_date: null,
              quotes: [quote],
            },
            {
              text: '둘째 자료',
              epistemic_status: 'uncertain',
              event_date: null,
              quotes: [quote],
            },
          ],
        },
        {
          kind: 'timeline',
          title: '시간 흐름',
          claims: [
            {
              text: '발생',
              epistemic_status: 'source_statement',
              event_date: '2024-02-29',
              quotes: [quote],
            },
          ],
        },
      ],
    },
  };
}
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
    vi.fn().mockImplementation(() =>
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
it('groups comparison claims and exposes dated timeline items in order', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() => Promise.resolve(response(completed()))),
  );
  mount();
  const comparison = await screen.findByRole('region', { name: '비교' });
  const comparisonList = within(comparison).getByRole('list', {
    name: '비교 항목',
  });
  const claims = within(comparisonList).getAllByRole('listitem');
  expect(claims).toHaveLength(2);
  expect(within(claims[0]).getByText('첫 자료')).toBeVisible();
  expect(within(claims[1]).getByText('둘째 자료')).toBeVisible();
  const timeline = screen.getByRole('region', { name: '시간 흐름' });
  const events = within(timeline).getByRole('list', { name: '시간 흐름 항목' });
  expect(events.tagName).toBe('OL');
  const event = within(events).getByRole('listitem');
  expect(within(event).getByText('발생')).toBeVisible();
  expect(within(event).getByText('2024-02-29')).toHaveAttribute(
    'datetime',
    '2024-02-29',
  );
  expect(within(event).getByText('근거 읽기')).toBeVisible();
});
it('renders only a returned summary without inventing comparison or timeline', async () => {
  const data = completed();
  data.result.modules = [data.result.modules[0]];
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() => Promise.resolve(response(data))),
  );
  mount();
  await screen.findByRole('region', { name: '요약' });
  expect(screen.queryByRole('region', { name: '비교' })).toBeNull();
  expect(screen.queryByRole('region', { name: '시간 흐름' })).toBeNull();
  expect(screen.queryByRole('list')).toBeNull();
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
