import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, MemoryRouter, RouterProvider } from 'react-router';
import { expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import EvidenceRoute from '../app/routes/evidence';
import fixture from '../../../tests/fixtures/canvas-synthetic.json';
import type { CanvasBundle, ResearchRun } from '@issuedigest/api-client';
import { catalog, response, snapshot, workspace } from './workspace-data';

const source = { snapshot_id: snapshot, document_id: '00000000-0000-4000-8000-000000000002', title: '공공기록법 일부개정법률안', source_kind: 'bill', bill_number: '2201234', proposed_on: '2024-09-02', collected_at: '2026-10-13T00:00:00Z', canonical_url: null, citation_count: 2, excerpt: '제안 이유의 일부' };
const session = { schema_version: 1, user_id: snapshot, memberships: [{ workspace_id: workspace, role: 'owner' }] };
const runId = '00000000-0000-4000-8000-000000000040';
const now = '2026-10-15T00:00:00Z';
function completedRun(): ResearchRun {
  const canvas = structuredClone(fixture) as CanvasBundle;
  const proof = canvas.research.evidence[0];
  proof.citations = [proof.citations[0]];
  canvas.research.evidence = [proof];
  canvas.research.claims = [{claim_id: '00000000-0000-4000-8000-000000000041', workspace_id: workspace, text: '합성 근거에 맞춘 AI 해석', basis: 'inference', speaker_entity_id: null, subject_entity_ids: [], citation_ids: [proof.citations[0].citation_id], valid_period: null, raw_event_time_text: null, derivation: {method: 'pydantic-ai', method_version: 'research-v1', rationale: '인용에 기반한 해석'}}];
  canvas.research.entities = []; canvas.research.relations = []; canvas.research.observations = []; canvas.research.support_reviews = [];
  canvas.revision.run_id = runId; canvas.revision.selected_version_ids = [proof.version.version_id];
  canvas.revision.draft.modules = [
    {kind: 'summary', module_id: '00000000-0000-4000-8000-000000000042', title: '핵심 정리', span: 'full', claim_ids: [canvas.research.claims[0].claim_id], citation_ids: [proof.citations[0].citation_id], actions: [{kind: 'open_evidence', citation_id: proof.citations[0].citation_id}]},
    {kind: 'evidence', module_id: '00000000-0000-4000-8000-000000000043', title: '근거', span: 'full', citation_ids: [proof.citations[0].citation_id], actions: [{kind: 'open_evidence', citation_id: proof.citations[0].citation_id}]},
  ];
  return {run_id: runId, workspace_id: workspace, request_id: '00000000-0000-4000-8000-000000000044', question: '법안의 핵심은?', snapshot_ids: [snapshot], parent_run_id: null, status: 'completed', error_code: null, created_at: now, updated_at: now, model: 'gpt-5.4-mini', input_tokens: 100, output_tokens: 50, events: [{sequence: 1, status: 'queued', created_at: now}, {sequence: 2, status: 'completed', created_at: now}], result: {canvas, source_titles: {[proof.document.document_id]: source.title}}} as ResearchRun;
}
function queuedRun(request: Record<string, unknown>): ResearchRun {
  return {...completedRun(), request_id: request.request_id as string, question: request.question as string, snapshot_ids: request.snapshot_ids as string[], parent_run_id: request.parent_run_id as string | null, status: 'queued', result: null, input_tokens: 0, output_tokens: 0, events: [{sequence: 1, status: 'queued', created_at: now}]};
}

it('shows named sources without creating an AI request on load and permits selecting a bill', async () => {
  const requests: {path: string; method: string}[] = [];
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    requests.push({path, method: options.method ?? 'GET'});
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: []});
    throw Error('unexpected request');
  });
  render(<MemoryRouter><Home /></MemoryRouter>);
  expect(await screen.findByText('공공기록법 일부개정법률안')).toBeInTheDocument();
  expect(screen.getByText(/의안번호 2201234/)).toBeInTheDocument();
  expect(screen.queryByText('synthetic-source')).not.toBeInTheDocument();
  expect(requests.every(request => request.method === 'GET')).toBe(true);
  await userEvent.setup().click(screen.getByRole('checkbox', {name: /공공기록법 일부개정법률안/}));
  expect(screen.getByText(/선택한 자료 1개/)).toBeInTheDocument();
  await waitFor(() => expect(requests.every(request => request.method === 'GET')).toBe(true));
});

it('keeps the selected source and unsent question when checking the source tab', async () => {
  vi.stubGlobal('fetch', async (path: string) => {
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: []});
    if (path.includes('/evidence?limit=')) return response(catalog());
    throw Error(`unexpected ${path}`);
  });
  render(<MemoryRouter><Home /></MemoryRouter>);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('checkbox', {name: /공공기록법 일부개정법률안/}));
  await user.type(screen.getByLabelText('무엇을 알아볼까요?'), '처리 상태는?');
  await user.click(screen.getByRole('button', {name: '자료'}));
  await user.click(screen.getByRole('button', {name: '이슈 조사'}));
  expect(screen.getByRole('checkbox', {name: /공공기록법 일부개정법률안/})).toBeChecked();
  expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('처리 상태는?');
});

it('shows verified titles in the secondary source catalog', async () => {
  vi.stubGlobal('fetch', async (path: string) => {
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: []});
    if (path.includes('/evidence?limit=')) return response(catalog());
    throw Error(`unexpected ${path}`);
  });
  render(<MemoryRouter initialEntries={['/?view=sources']}><Home /></MemoryRouter>);
  expect(await screen.findByRole('heading', {name: source.title})).toBeInTheDocument();
});

it('shows the monthly budget limit without inventing a result or losing the selected bill', async () => {
  let posts = 0;
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith('/research') && options.method === 'POST') {posts++; return response({}, 429);}
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: []});
    throw Error(`unexpected ${path}`);
  });
  render(<MemoryRouter><Home /></MemoryRouter>);
  await userEvent.setup().click(await screen.findByRole('button', {name: '핵심 정리'}));
  expect(await screen.findByText('이번 달 AI 조사 한도에 도달했습니다.')).toBeInTheDocument();
  expect(screen.getByRole('checkbox', {name: /공공기록법 일부개정법률안/})).toBeChecked();
  expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('선택한 법안의 주요 내용을 근거와 함께 정리해 주세요.');
  expect(screen.queryByRole('article', {name: '조사 화면'})).not.toBeInTheDocument();
  expect(posts).toBe(1);
});

it('starts one real run, shows progress, restores the generated result and opens its exact citation', async () => {
  let resolveRun!: (value: Response) => void;
  let postCount = 0;
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith('/research') && options.method === 'POST') { postCount++; return response(queuedRun(JSON.parse(options.body as string))); }
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: [completedRun()]});
    if (path.endsWith(`/research/${runId}`)) return new Promise<Response>(resolve => { resolveRun = resolve; });
    if (path.endsWith(`/evidence/${snapshot}`)) return response(completedRun().result!.canvas.research.evidence[0]);
    throw Error(`unexpected ${path}`);
  });
  const router = createMemoryRouter([{path: '/', Component: Home}, {path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute}]);
  render(<RouterProvider router={router} />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('checkbox', {name: /공공기록법 일부개정법률안/}));
  await user.type(screen.getByLabelText('무엇을 알아볼까요?'), '법안의 핵심은?');
  await user.click(screen.getByRole('button', {name: 'AI 조사 시작'}));
  expect(postCount).toBe(1);
  expect(screen.queryByText('합성 근거에 맞춘 AI 해석')).not.toBeInTheDocument();
  await waitFor(() => expect(resolveRun).toBeTypeOf('function'));
  expect(screen.getByRole('status', {name: '조사 상태'})).toHaveTextContent('요청 접수');
  await act(async () => resolveRun(response(completedRun())));
  expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
  expect(screen.getAllByText(source.title).length).toBeGreaterThan(1);
  expect(screen.getAllByRole('button', {name: /근거 열기: 공공기록법/})).toHaveLength(2);
  await user.click(screen.getAllByRole('button', {name: /근거 열기: 공공기록법/})[0]);
  expect(await screen.findByRole('heading', {name: source.title})).toBeInTheDocument();
  expect(router.state.location.pathname).toBe(`/workspaces/${workspace}/evidence/${snapshot}`);
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('인용 1'));
  expect(document.querySelector('mark')).toHaveTextContent('합성 테스트 전용');
  expect(screen.getByLabelText('원문 텍스트')).toHaveFocus();
  expect(postCount).toBe(1);
});

it('reopens a saved result with GET only and submits a follow-up linked to the completed run', async () => {
  const posted: Record<string, unknown>[] = [];
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith(`/research/${runId}`)) return response(completedRun());
    if (path.endsWith('/research') && options.method === 'POST') { posted.push(JSON.parse(options.body as string)); return response({}, 503); }
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: [completedRun()]});
    throw Error(`unexpected ${path}`);
  });
  const router = createMemoryRouter([{path: '/', Component: Home}], {initialEntries: [`/?view=research&run=${runId}`]});
  render(<RouterProvider router={router} />);
  const user = userEvent.setup();
  expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
  expect(posted).toHaveLength(0);
  await user.type(screen.getByLabelText('후속 질문'), '제안 이유는?');
  await user.click(screen.getByRole('button', {name: '후속 질문하기'}));
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(posted[0]).toMatchObject({parent_run_id: runId, snapshot_ids: [snapshot], question: '제안 이유는?'});
  expect(await screen.findByText(/AI 연결을 기다리는 중/)).toBeInTheDocument();
  expect(screen.getByLabelText('후속 질문')).toHaveValue('제안 이유는?');
});

it('lists automatically saved runs by question and opens a result without another POST', async () => {
  const methods: string[] = [];
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    methods.push(options.method ?? 'GET');
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith(`/research/${runId}`)) return response(completedRun());
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: [completedRun()]});
    throw Error(`unexpected ${path}`);
  });
  const router = createMemoryRouter([{path: '/', Component: Home}], {initialEntries: ['/?view=saved']});
  render(<RouterProvider router={router} />);
  await userEvent.setup().click(await screen.findByRole('button', {name: /법안의 핵심은\?/}));
  expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
  expect(router.state.location.search).toContain(`run=${runId}`);
  expect(methods.every(method => method === 'GET')).toBe(true);
});

it('allows a viewer to read a saved result while blocking AI submission', async () => {
  const methods: string[] = [];
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    methods.push(options.method ?? 'GET');
    if (path.endsWith('/session')) return response({...session, memberships: [{workspace_id: workspace, role: 'viewer'}]});
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith(`/research/${runId}`)) return response(completedRun());
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: [completedRun()]});
    throw Error(`unexpected ${path}`);
  });
  const router = createMemoryRouter([{path: '/', Component: Home}], {initialEntries: [`/?view=research&run=${runId}`]});
  render(<RouterProvider router={router} />);
  expect(await screen.findByText('합성 근거에 맞춘 AI 해석')).toBeInTheDocument();
  expect(screen.getByText('읽기 권한으로는 저장된 조사를 열람할 수 있습니다.')).toBeInTheDocument();
  expect(screen.getByRole('button', {name: '후속 질문하기'})).toBeDisabled();
  expect(methods.every(method => method === 'GET')).toBe(true);
});

it('cancels an active run and keeps its question visible', async () => {
  const queued = queuedRun({request_id: '00000000-0000-4000-8000-000000000044', question: '법안의 핵심은?', snapshot_ids: [snapshot], parent_run_id: null});
  const cancelled: ResearchRun = {...queued, status: 'cancelled', error_code: 'cancelled', events: [...queued.events, {sequence: 2, status: 'cancelled', created_at: now}]};
  let cancelCount = 0;
  vi.stubGlobal('fetch', async (path: string, options: RequestInit = {}) => {
    if (path.endsWith('/session')) return response(session);
    if (path.endsWith('/research/sources')) return response({workspace_id: workspace, items: [source]});
    if (path.endsWith('/research')) return response({workspace_id: workspace, items: [queued]});
    if (path.endsWith(`/research/${runId}/cancel`) && options.method === 'POST') {cancelCount++; return response(cancelled);}
    if (path.endsWith(`/research/${runId}`)) return response(queued);
    throw Error(`unexpected ${path}`);
  });
  const router = createMemoryRouter([{path: '/', Component: Home}], {initialEntries: [`/?view=research&run=${runId}`]});
  render(<RouterProvider router={router} />);
  await userEvent.setup().click(await screen.findByRole('button', {name: '조사 취소'}));
  expect(await screen.findByText('조사가 취소되었습니다')).toBeInTheDocument();
  expect(cancelCount).toBe(1);
  expect(screen.getByLabelText('무엇을 알아볼까요?')).toHaveValue('법안의 핵심은?');
});
