import { createHash } from 'node:crypto';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import canvas from '../../../tests/fixtures/canvas-synthetic.json';
import type { EvidenceBundle } from '@issuedigest/api-client';

import EvidenceRoute from '../app/routes/evidence';
const workspace = '00000000-0000-4000-8000-000000000001';
const snapshot = '00000000-0000-4000-8000-000000000099';
const requestId = '8ff9af27-d021-4fb3-a46e-cf8c3d093c44';
const path = `/workspaces/${workspace}/evidence/${snapshot}`;
const fixture = () => structuredClone(canvas.research.evidence[0]) as EvidenceBundle;
const response = (body: unknown = fixture(), status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', 'X-Request-ID': requestId, 'Cache-Control': 'no-store' } });
function mount() {
  const router = createMemoryRouter([{ path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute }], { initialEntries: [path] });
  return { router, ...render(<RouterProvider router={router} />) };
}
afterEach(() => vi.useRealTimers());
it('announces loading while a real GET is pending, without evidence', () => {
  vi.stubGlobal('fetch', () => new Promise(() => {})); mount();
  expect(screen.getByRole('status')).toHaveTextContent('읽는 중');
  expect(screen.queryByText('원문과 인용')).not.toBeInTheDocument();
});
it('renders source metadata and requires explicit citation selection without another GET', async () => {
  const body = fixture(); body.document.canonical_url = 'https://example.com/source';
  const fetch = vi.fn(async () => response(body)); vi.stubGlobal('fetch', fetch); mount();
  expect(await screen.findByRole('heading', { name: '원문과 인용' })).toBeInTheDocument();
  expect(screen.getByText('synthetic-test')).toBeInTheDocument();
  expect(screen.getByText(body.document.source_id).closest('details')).not.toHaveAttribute('open');
  expect(screen.getByText('2026-01-01T00:00:00Z').closest('details')).not.toHaveAttribute('open');
  expect(screen.getByText('기타 자료')).toBeInTheDocument();
  expect(screen.getByText('수집 2026. 1. 1.')).toBeInTheDocument();
  const link = screen.getByRole('link', { name: '원문 출처 열기' }); expect(link).toHaveAttribute('href', 'https://example.com/source'); expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  expect(document.querySelector('mark')).toBeNull(); expect(screen.queryByText(requestId)).not.toBeInTheDocument();
  const button = screen.getByRole('button', { name: /인용 1 · 본문/ });
  await userEvent.setup().click(button);
  expect(button).toHaveAttribute('aria-pressed', 'true'); expect(document.querySelector('mark')).toHaveTextContent(body.representation.text);
  expect(screen.getByRole('status')).toHaveTextContent('인용 1'); expect(fetch).toHaveBeenCalledTimes(2);
});
it('highlights Unicode without slicing a surrogate or combining sequence and supports keyboard selection', async () => {
  const body = fixture(); body.representation.text = '앞😀é뒤'; body.representation.pages = [{ page_number: 7, start: 0, end: 5 }]; body.citations = [body.citations[0]];
  body.citations[0].selector = { kind: 'text', start: 1, end: 4, quote: '😀é', prefix: '앞', suffix: '뒤' };
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  vi.stubGlobal('fetch', async () => response(body)); mount();
  const button = await screen.findByRole('button', { name: /인용 1/ }); button.focus(); await userEvent.setup().keyboard('{Enter}');
  expect(document.querySelector('mark')?.textContent).toBe('😀é'); expect(screen.getByLabelText('원문 텍스트')).toHaveFocus();
  expect(screen.getByLabelText('원문 텍스트').textContent).toBe('앞😀é뒤');
});
it('uses actual PDF page numbers and displays the validated table cell', async () => {
  const body = fixture(); body.representation.text = '첫쪽😀인용끝'; body.representation.pages = [{ page_number: 3, start: 0, end: 2 }, { page_number: 7, start: 2, end: 7 }];
  body.citations[0].selector = { kind: 'text', start: 0, end: 2, quote: '첫쪽', prefix: null, suffix: null };
  body.citations[1].selector = { kind: 'pdf', page_number: 7, start: 2, end: 5, quote: '😀인용', prefix: '첫쪽', suffix: '끝', regions: [] };
  body.representation.pages[1].end = 6;
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  vi.stubGlobal('fetch', async () => response(body)); mount();
  await screen.findByRole('heading', { name: '원문과 인용' });
  expect(screen.getByRole('button', { name: '3쪽' })).toBeInTheDocument(); expect(screen.getByRole('button', { name: '7쪽' })).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole('button', { name: /인용 2 · PDF 7쪽/ }));
  expect(screen.getByRole('button', { name: '7쪽' })).toHaveAttribute('aria-pressed', 'true'); expect(screen.getByLabelText('원문 텍스트')).toHaveTextContent('😀인용끝'); expect(document.querySelector('mark')?.textContent).toBe('😀인용');
  await userEvent.setup().click(screen.getByRole('button', { name: /인용 3 · 표 셀/ }));
  expect(screen.getByLabelText('선택한 표 셀')).toHaveTextContent('합성 표 인용');
  expect(screen.getByRole('button', { name: '전체 텍스트' })).toHaveAttribute('aria-pressed', 'false');
  await userEvent.setup().click(screen.getByRole('button', { name: /인용 1 · 본문/ }));
  expect(screen.getByRole('button', { name: '전체 텍스트' })).toHaveAttribute('aria-pressed', 'true'); expect(screen.getByLabelText('원문 텍스트')).toHaveTextContent('첫쪽😀인용끝');
});
it('shows precise empty states and an unregistered source link', async () => {
  const body = fixture(); body.representation.text = ''; body.representation.pages = []; body.representation.tables = []; body.citations = [];
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  vi.stubGlobal('fetch', async () => response(body)); mount();
  expect(await screen.findByText('저장된 인용이 없습니다.')).toBeInTheDocument(); expect(screen.getByText('파싱된 텍스트가 비어 있습니다.')).toBeInTheDocument(); expect(screen.getByText('원문 출처 미등록')).toBeInTheDocument();
});
it.each([[401, '로그인이 필요합니다.'], [404, '자료가 없거나 접근 권한이 없습니다.'], [503, '자료 읽기가 아직 준비되지 않았거나 서버에 문제가 있습니다.'], [500, '자료 읽기가 아직 준비되지 않았거나 서버에 문제가 있습니다.']])('shows safe HTTP %s state and support details only', async (status, message) => {
  vi.stubGlobal('fetch', async () => response({ detail: 'PRIVATE' }, status as number)); mount();
  expect(await screen.findByText(message as string)).toBeInTheDocument(); expect(screen.queryByText('PRIVATE')).not.toBeInTheDocument();
  if (status === 401) expect(screen.getByRole('link', { name: '로그인' })).toHaveAttribute('href', '/login');
  else expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: '작업 공간으로' })).toHaveAttribute('href', '/');
  expect(screen.getByText(requestId).closest('details')).toBeInTheDocument();
});
it('retries through a cleared loading state and then a real response', async () => {
  let complete!: (response: Response) => void; let first = true;
  vi.stubGlobal('fetch', async () => { if (first) { first = false; return response({}, 503); } return new Promise<Response>(resolve => { complete = resolve; }); }); mount();
  await userEvent.setup().click(await screen.findByRole('button', { name: '다시 읽기' }));
  expect(screen.getByRole('status')).toHaveTextContent('읽는 중'); expect(screen.queryByText(requestId)).not.toBeInTheDocument();
  await act(async () => complete(response())); expect(await screen.findByRole('heading', { name: '원문과 인용' })).toBeInTheDocument();
});
it('rejects malformed HTML success and supports a retry', async () => {
  vi.stubGlobal('fetch', async () => new Response('<img src="https://example.com/tracker" onerror="alert(1)">', { headers: { 'Content-Type': 'text/html' } })); mount();
  expect(await screen.findByText('응답 형식을 확인할 수 없습니다.')).toBeInTheDocument(); expect(document.querySelector('img')).toBeNull(); expect(screen.getByRole('button', { name: '다시 읽기' })).toBeEnabled();
});
it('renders stored HTML as text without external image loading', async () => {
  const body = fixture(); body.representation.text = '<img src="https://example.com/tracker" onerror="alert(1)">'; body.representation.pages = []; body.citations = [];
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  vi.stubGlobal('fetch', async () => response(body)); mount();
  expect(await screen.findByText(body.representation.text)).toBeInTheDocument(); expect(document.querySelector('img')).toBeNull();
});
it('shows an offline state', async () => {
  vi.stubGlobal('fetch', async () => { throw new TypeError('PRIVATE offline'); }); mount();
  expect(await screen.findByText('서버에 연결하지 못했습니다.')).toBeInTheDocument();
});
it('shows a timeout state without displaying a delayed response', async () => {
  vi.useFakeTimers(); let complete!: (response: Response) => void;
  vi.stubGlobal('fetch', () => new Promise<Response>(resolve => { complete = resolve; })); mount();
  await act(async () => vi.advanceTimersByTimeAsync(10000)); expect(screen.getByText('응답을 기다리는 시간이 길어졌습니다.')).toBeInTheDocument();
  await act(async () => complete(response())); expect(screen.queryByText('원문과 인용')).not.toBeInTheDocument();
});
it('clears old evidence and selection synchronously on route ID change', async () => {
  let second!: (response: Response) => void; let count = 0;
  vi.stubGlobal('fetch', async () => { count++; if (count === 1) { return response(); } return new Promise<Response>(resolve => { second = resolve; }); });
  const { router } = mount(); await screen.findByRole('heading', { name: '원문과 인용' }); await userEvent.setup().click(screen.getByRole('button', { name: /인용 1/ }));
  await act(async () => { await router.navigate(path.replace(snapshot, '00000000-0000-4000-8000-000000000098')); });
  expect(screen.queryByText('원문과 인용')).not.toBeInTheDocument(); expect(document.querySelector('mark')).toBeNull(); expect(screen.getByRole('status')).toHaveTextContent('읽는 중');
  await act(async () => second(response())); await screen.findByRole('heading', { name: '원문과 인용' }); expect(document.querySelector('mark')).toBeNull();
});
it('ignores an earlier route response after the new route fails', async () => {
  let late!: (response: Response) => void; let signal: AbortSignal | undefined; let first = true;
  vi.stubGlobal('fetch', async (_url: string, init: RequestInit) => { if (first) { first = false; signal = init.signal as AbortSignal; return new Promise<Response>(resolve => { late = resolve; }); } return response({}, 404); });
  const { router } = mount(); await act(async () => { await router.navigate(path.replace(snapshot, '00000000-0000-4000-8000-000000000098')); });
  await screen.findByText('자료가 없거나 접근 권한이 없습니다.'); await act(async () => late(response())); expect(screen.queryByText('원문과 인용')).not.toBeInTheDocument(); expect(signal?.aborted).toBe(true);
});
it('aborts on unmount and ignores a late response', async () => {
  let late!: (response: Response) => void; let signal: AbortSignal | undefined;
  vi.stubGlobal('fetch', (_url: string, init: RequestInit) => { signal = init.signal as AbortSignal; return new Promise<Response>(resolve => { late = resolve; }); });
  const { unmount } = mount(); unmount(); expect(signal?.aborted).toBe(true); await act(async () => late(response())); expect(screen.queryByText('원문과 인용')).not.toBeInTheDocument();
});
it('does not fetch malformed route IDs', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  const router = createMemoryRouter([{ path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute }], { initialEntries: ['/workspaces/bad/evidence/bad'] }); render(<RouterProvider router={router} />);
  await waitFor(() => expect(screen.getByText('근거 링크 형식을 확인해 주세요.')).toBeInTheDocument()); expect(fetch).not.toHaveBeenCalled();
});

it('moves focus back to original text when the same citation is selected again', async () => {
  vi.stubGlobal('fetch', async () => response()); mount();
  const button = await screen.findByRole('button', { name: /인용 1/ }); const user = userEvent.setup();
  await user.click(button); expect(screen.getByLabelText('원문 텍스트')).toHaveFocus();
  button.focus(); await user.keyboard('{Enter}'); expect(screen.getByLabelText('원문 텍스트')).toHaveFocus();
});
it('keeps a timeout retry loading when the preceding ignored request arrives late', async () => {
  vi.useFakeTimers(); const completions: ((response: Response) => void)[] = [];
  vi.stubGlobal('fetch', () => new Promise<Response>(resolve => { completions.push(resolve); })); mount();
  await act(async () => vi.advanceTimersByTimeAsync(10000));
  fireEvent.click(screen.getByRole('button', { name: '다시 읽기' }));
  expect(screen.getByRole('status')).toHaveTextContent('읽는 중');
  await act(async () => completions[0](response())); expect(screen.getByRole('status')).toHaveTextContent('읽는 중'); expect(screen.queryByText('원문과 인용')).not.toBeInTheDocument();
  await act(async () => completions[1](response())); expect(screen.getByRole('heading', { name: '원문과 인용' })).toBeInTheDocument();
});

it('restores full text after table-only citation selection without pages or another GET', async () => {
  const body = fixture(); body.representation.pages = []; body.citations = [body.citations[2]];
  const fetch = vi.fn(async () => response(body)); vi.stubGlobal('fetch', fetch); mount();
  const citation = await screen.findByRole('button', { name: /인용 1 · 표 셀/ }); const user = userEvent.setup();
  await user.click(citation); expect(screen.getByLabelText('선택한 표 셀')).toHaveTextContent('합성 표 인용');
  const fullText = screen.queryByRole('button', { name: '전체 텍스트' });
  expect(fullText).toBeInTheDocument();
  await user.click(fullText!);
  expect(screen.getByLabelText('원문 텍스트')).toHaveTextContent(body.representation.text);
  expect(screen.queryByLabelText('선택한 표 셀')).not.toBeInTheDocument();
  expect(citation).toHaveAttribute('aria-pressed', 'false'); expect(fullText).toHaveAttribute('aria-pressed', 'true');
  expect(fetch).toHaveBeenCalledTimes(2);
});
it.each(['initial', 'repeated'])('scrolls the actual late highlighted quote on %s selection while keeping original focus', async phase => {
  const body = fixture(); const prefix = '먼 합성 원문.\n'.repeat(200); const quote = '끝😀인용';
  body.representation.text = prefix + quote; body.representation.pages = []; body.citations = [body.citations[0]];
  body.representation.text_sha256 = createHash('sha256').update(body.representation.text).digest('hex');
  body.citations[0].selector = { kind: 'text', start: Array.from(prefix).length, end: Array.from(prefix + quote).length, quote, prefix: null, suffix: null };
  // JSDOM has no layout/scroll implementation. Observe the native DOM boundary;
  // the controller browser check separately verifies actual viewport positioning.
  const targets: HTMLElement[] = [];
  const descriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'scrollIntoView');
  Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', { configurable: true, value: function (this: HTMLElement) { targets.push(this); } });
  try {
    vi.stubGlobal('fetch', async () => response(body)); mount(); const user = userEvent.setup();
    const button = await screen.findByRole('button', { name: /인용 1 · 본문/ }); await user.click(button);
    if (phase === 'repeated') { targets.length = 0; button.focus(); await user.keyboard('{Enter}'); }
    const mark = document.querySelector('mark'); expect(mark).toHaveTextContent(quote);
    expect(screen.getByLabelText('원문 텍스트')).toHaveFocus(); expect(targets.at(-1)).toBe(mark);
  } finally {
    if (descriptor) Object.defineProperty(HTMLElement.prototype, 'scrollIntoView', descriptor);
    else Reflect.deleteProperty(HTMLElement.prototype, 'scrollIntoView');
  }
});
