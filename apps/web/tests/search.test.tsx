import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router';
import { expect, it, vi } from 'vitest';
import canvas from '../../../tests/fixtures/canvas-synthetic.json';
import Home from '../app/routes/home';
import EvidenceRoute from '../app/routes/evidence';
import { catalog, otherWorkspace, response, session, snapshot, workspace } from './workspace-data';
import type { EvidenceSearchHit, EvidenceSearchResult } from '@issuedigest/api-client';

const evidence = structuredClone(canvas.research.evidence[0]);
const searchPath = `/workspaces/${workspace}/evidence/${snapshot}`;
const hit = (selector: EvidenceSearchHit['selector'] = evidence.citations[0].selector as EvidenceSearchHit['selector']): EvidenceSearchHit => ({
  workspace_id: workspace, snapshot_id: snapshot, document_id: evidence.document.document_id,
  version_id: evidence.version.version_id, representation_id: evidence.representation.representation_id,
  provider: evidence.document.provider, source_id: evidence.document.source_id, source_kind: 'other',
  canonical_url: null, collected_at: evidence.version.collected_at, unit_ordinal: 0,
  profile: 'literal-ngrams-v1', selector, matched_terms: ['합성'], anchor_status: 'matched', support_status: 'not_evaluated',
});
const result = (hits: EvidenceSearchHit[] = [hit()]): EvidenceSearchResult => ({
  workspace_id: workspace, query: { terms: ['합성'], limit: 20, provider: null, source_id: null, source_kind: null, collected_from: null, collected_to: null },
  hits, coverage: { total_snapshots: 3, indexed_snapshots: 2, missing_snapshots: 1, skipped_empty_cells: 1, skipped_large_cells: 2 },
  scanned_candidates: hits.length, truncated: false,
});
const setup = (search: (url: string, init?: RequestInit) => Promise<Response>) => {
  const fetch = vi.fn((url: string, init?: RequestInit) => {
    if (url.endsWith('/session')) return Promise.resolve(response(session()));
    if (url.includes('/evidence?limit=')) return Promise.resolve(response(catalog(url.includes(otherWorkspace) ? otherWorkspace : workspace)));
    return search(url, init);
  });
  vi.stubGlobal('fetch', fetch);
  return { fetch, ...render(<MemoryRouter><Home /></MemoryRouter>) };
};

it('starts with no results and shows pending, coverage, exact location and limits after submit', async () => {
  let complete!: (value: Response) => void;
  const { fetch } = setup(() => new Promise(resolve => { complete = resolve; }));
  const user = userEvent.setup();
  await screen.findByRole('searchbox', { name: '원문 검색' });
  expect(screen.queryByRole('link', { name: '원문 위치 열기' })).not.toBeInTheDocument();
  expect(fetch.mock.calls.filter(([url]) => url.includes('/search'))).toHaveLength(0);
  await user.type(screen.getByRole('searchbox', { name: '원문 검색' }), '합성');
  await user.click(screen.getByRole('button', { name: '검색' }));
  expect(screen.getByRole('button', { name: '검색 중…' })).toBeDisabled();
  expect(screen.getByRole('status', { name: '검색 상태' })).toHaveTextContent('검색 중');
  await act(async () => complete(response(result())));
  expect(await screen.findByRole('link', { name: '원문 위치 열기' })).toHaveAttribute('href', searchPath);
  expect(screen.getByText('본문 문자 0–38')).toBeInTheDocument();
  expect(screen.getByText(/색인 2\/3개/)).toBeInTheDocument();
  expect(screen.getByText(/미색인 1개/)).toBeInTheDocument();
  expect(screen.getByText(/빈 셀 제외 1개.*큰 셀 제외 2개/)).toBeInTheDocument();
  expect(screen.queryByText(/후보 1\/200개/)).not.toBeInTheDocument();
  expect(screen.getByText(/최대 20개 위치/)).toBeInTheDocument();
  expect(screen.getByText(evidence.citations[0].selector.quote)).toBeInTheDocument();
});

it('distinguishes empty, failure and retry with the last submitted terms', async () => {
  let attempts = 0;
  const { fetch } = setup(async () => { attempts++; return attempts === 1 ? response(result([])) : attempts === 2 ? response({}, 503) : response(result()); });
  const user = userEvent.setup();
  await user.type(await screen.findByRole('searchbox', { name: '원문 검색' }), '합성');
  await user.click(screen.getByRole('button', { name: '검색' }));
  expect(await screen.findByText(/일치한 위치가 없습니다/)).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: '검색' }));
  expect(await screen.findByRole('button', { name: '같은 검색 재시도' })).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: '같은 검색 재시도' }));
  expect(await screen.findByRole('link', { name: '원문 위치 열기' })).toBeInTheDocument();
  const bodies = fetch.mock.calls.filter(([url]) => url.includes('/search')).map(([, init]) => JSON.parse(init!.body as string).terms);
  expect(bodies).toEqual([['합성'], ['합성'], ['합성']]);
});

it('shows actual PDF page, full table cell and a candidate or result limit warning', async () => {
  const pdf = hit(evidence.citations[1].selector as EvidenceSearchHit['selector']);
  const cell = { ...hit(evidence.citations[2].selector as EvidenceSearchHit['selector']), unit_ordinal: 1 };
  setup(async () => response({ ...result([pdf, cell]), coverage: { total_snapshots: 2, indexed_snapshots: 2, missing_snapshots: 0, skipped_empty_cells: 0, skipped_large_cells: 0 }, truncated: true, scanned_candidates: 200 }));
  const user = userEvent.setup(); await user.type(await screen.findByRole('searchbox', { name: '원문 검색' }), '합성');
  await user.click(screen.getByRole('button', { name: '검색' }));
  expect(await screen.findByText('PDF 1쪽 · 문자 0–38')).toBeInTheDocument();
  expect(screen.getByText('표 synthetic-table · 셀 synthetic-cell')).toBeInTheDocument();
  expect(screen.getByText(/후보 또는 결과 한도/)).toBeInTheDocument();
  expect(screen.getByText('자료 색인 2/2개')).toBeInTheDocument();
  expect(screen.queryByText(/미색인|제외/)).not.toBeInTheDocument();
  expect(screen.getByRole('status', { name: '검색 상태' })).toHaveTextContent('위치 2개');
});

it('keeps invalid input local and clears displayed results when terms change', async () => {
  const { fetch } = setup(async () => response(result()));
  const user = userEvent.setup(); const input = await screen.findByRole('searchbox', { name: '원문 검색' });
  await user.click(screen.getByRole('button', { name: '검색' }));
  expect(await screen.findByText(/검색어를 확인해 주세요/)).toBeInTheDocument();
  expect(fetch.mock.calls.filter(([url]) => url.includes('/search'))).toHaveLength(0);
  await user.type(input, '합성'); await user.click(screen.getByRole('button', { name: '검색' }));
  expect(await screen.findByRole('link', { name: '원문 위치 열기' })).toBeInTheDocument();
  await user.type(input, ' 추가');
  expect(screen.queryByRole('link', { name: '원문 위치 열기' })).not.toBeInTheDocument();
});

it('clears and cancels when workspace changes and ignores the late response', async () => {
  let late!: (value: Response) => void; let signal: AbortSignal | undefined;
  setup((_url, init) => { signal = init?.signal as AbortSignal; return new Promise(resolve => { late = resolve; }); });
  const user = userEvent.setup(); await user.type(await screen.findByRole('searchbox', { name: '원문 검색' }), '합성');
  await user.click(screen.getByRole('button', { name: '검색' }));
  await user.selectOptions(screen.getByRole('combobox', { name: '작업 공간' }), otherWorkspace);
  expect(signal?.aborted).toBe(true);
  expect(screen.getByRole('searchbox', { name: '원문 검색' })).toHaveValue('');
  await act(async () => late(response(result())));
  expect(screen.queryByRole('link', { name: '원문 위치 열기' })).not.toBeInTheDocument();
});

it('clears and cancels search as soon as logout starts, including a late search response', async () => {
  let late!: (value: Response) => void; let signal: AbortSignal | undefined;
  setup((url, init) => url.endsWith('/logout') ? new Promise(() => {}) : new Promise(resolve => { signal = init?.signal as AbortSignal; late = resolve; }));
  const user = userEvent.setup(); await user.type(await screen.findByRole('searchbox', { name: '원문 검색' }), '합성');
  await user.click(screen.getByRole('button', { name: '검색' }));
  await user.click(screen.getByRole('button', { name: '로그아웃' }));
  expect(signal?.aborted).toBe(true);
  expect(screen.queryByRole('searchbox', { name: '원문 검색' })).not.toBeInTheDocument();
  await act(async () => late(response(result())));
  expect(screen.queryByRole('link', { name: '원문 위치 열기' })).not.toBeInTheDocument();
});

it('aborts a pending search on unmount and ignores its late response', async () => {
  let late!: (value: Response) => void; let signal: AbortSignal | undefined;
  const { unmount } = setup((_url, init) => { signal = init?.signal as AbortSignal; return new Promise(resolve => { late = resolve; }); });
  const user = userEvent.setup(); await user.type(await screen.findByRole('searchbox', { name: '원문 검색' }), '합성');
  await user.click(screen.getByRole('button', { name: '검색' }));
  unmount(); expect(signal?.aborted).toBe(true);
  await act(async () => late(response(result())));
  expect(screen.queryByRole('link', { name: '원문 위치 열기' })).not.toBeInTheDocument();
});

it('uses router state to select an exact search hit, then clears it on page or saved citation choice', async () => {
  vi.stubGlobal('fetch', async () => response(evidence));
  const router = createMemoryRouter([{ path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute }], { initialEntries: [{ pathname: searchPath, state: { kind: 'search-hit', hit: hit(evidence.citations[1].selector as EvidenceSearchHit['selector']) } }] });
  render(<RouterProvider router={router} />);
  expect(await screen.findByText('검색된 원문 위치 선택됨')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '1쪽' })).toHaveAttribute('aria-pressed', 'true');
  expect(document.querySelector('mark')).toHaveTextContent(evidence.citations[1].selector.quote);
  await userEvent.setup().click(screen.getByRole('button', { name: '전체 텍스트' }));
  expect(screen.queryByText('검색된 원문 위치 선택됨')).not.toBeInTheDocument();
  expect(document.querySelector('mark')).toBeNull();
  await userEvent.setup().click(screen.getByRole('button', { name: /인용 3 · 표 셀/ }));
  expect(screen.getByLabelText('선택한 표 셀')).toHaveTextContent('합성 표 인용');
  await act(async () => { await router.navigate(searchPath, { state: { kind: 'search-hit', hit: hit(evidence.citations[2].selector as EvidenceSearchHit['selector']) } }); });
  expect(screen.getByText('검색된 원문 위치 선택됨')).toBeInTheDocument();
  expect(screen.getByLabelText('선택한 표 셀')).toHaveTextContent('합성 표 인용');
  expect(screen.getByRole('button', { name: /인용 3 · 표 셀/ })).toHaveAttribute('aria-pressed', 'false');
});

it('shows a fixed notice for stale router state without blocking the original text', async () => {
  vi.stubGlobal('fetch', async () => response(evidence));
  const router = createMemoryRouter([{ path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute }], { initialEntries: [{ pathname: searchPath, state: { kind: 'search-hit', hit: { ...hit(), document_id: '00000000-0000-4000-8000-000000000098' } } }] });
  render(<RouterProvider router={router} />);
  expect(await screen.findByText('검색 위치가 현재 원문과 일치하지 않습니다. 원문을 직접 확인해 주세요.')).toBeInTheDocument();
  expect(screen.getByLabelText('원문 텍스트')).toBeInTheDocument();
  expect(document.querySelector('mark')).toBeNull();
});
