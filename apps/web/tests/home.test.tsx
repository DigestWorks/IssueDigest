import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import { MemoryRouter } from 'react-router';
import { renderToString } from 'react-dom/server';
import { response } from './workspace-data';

const success = () => new Response(JSON.stringify({ service: 'issuedigest-api', api_version: 'v1', status: 'ok' }), {
  headers: { 'X-Request-ID': '8ff9af27-d021-4fb3-a46e-cf8c3d093c44' },
});

it('offers research, source, and saved-run navigation while asking an unauthenticated user to log in', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401));
  render(<MemoryRouter><Home /></MemoryRouter>);
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('무엇이 궁금한가요?');
  expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toHaveTextContent('홈');
  expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toHaveTextContent('자료');
  expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toHaveTextContent('저장한 조사');
  expect(await screen.findByRole('link', { name: '로그인' })).toBeInTheDocument();
  await userEvent.setup().click(screen.getByRole('button', { name: '자료' }));
  await userEvent.setup().click(screen.getByText('연결 확인과 저장된 근거 링크'));
  expect(screen.getByRole('button', { name: '연결 확인' })).toBeEnabled();
});

it('shows confirmation in progress before rendering a real successful response', async () => {
  let resolveResponse!: (response: Response) => void;
  vi.stubGlobal('fetch', (path: string) => path.endsWith('/session') ? Promise.resolve(response({}, 401)) : new Promise<Response>((resolve) => { resolveResponse = resolve; }));
  const user = userEvent.setup();
  render(<MemoryRouter><Home /></MemoryRouter>);
  await user.click(screen.getByRole('button', { name: '자료' }));
  await user.click(screen.getByText('연결 확인과 저장된 근거 링크'));
  await user.click(screen.getByRole('button', { name: '연결 확인' }));
  expect(screen.getByRole('status', { name: '서비스 연결 상태' })).toHaveTextContent('확인 중');
  expect(screen.getByRole('button', { name: '확인 중' })).toBeDisabled();
  resolveResponse(success());
  await waitFor(() => expect(screen.getByRole('status', { name: '서비스 연결 상태' })).toHaveTextContent('연결됨'));
  expect(screen.getByRole('button', { name: '다시 확인' })).toBeEnabled();
});

it('shows a connection failure and lets the user retry successfully', async () => {
  let available = false;
  vi.stubGlobal('fetch', async (path: string) => {
    if (path.endsWith('/session')) return response({}, 401);
    if (!available) throw new TypeError('offline');
    return success();
  });
  const user = userEvent.setup();
  render(<MemoryRouter><Home /></MemoryRouter>);
  await user.click(screen.getByRole('button', { name: '자료' }));
  await user.click(screen.getByText('연결 확인과 저장된 근거 링크'));
  await user.click(screen.getByRole('button', { name: '연결 확인' }));
  await waitFor(() => expect(screen.getByRole('status', { name: '서비스 연결 상태' })).toHaveTextContent('연결 실패'));
  available = true;
  await user.click(screen.getByRole('button', { name: '재시도' }));
  await waitFor(() => expect(screen.getByRole('status', { name: '서비스 연결 상태' })).toHaveTextContent('연결됨'));
  expect(screen.getByRole('link', { name: '로그인' })).toBeInTheDocument();
});

it('does not display a malformed API response as a successful connection', async () => {
  vi.stubGlobal('fetch', async (path: string) => path.endsWith('/session') ? response({}, 401) : new Response(JSON.stringify({ status: 'ok' })));
  const user = userEvent.setup();
  render(<MemoryRouter><Home /></MemoryRouter>);
  await user.click(screen.getByRole('button', { name: '자료' }));
  await user.click(screen.getByText('연결 확인과 저장된 근거 링크'));
  await user.click(screen.getByRole('button', { name: '연결 확인' }));
  await waitFor(() => expect(screen.getByRole('status', { name: '서비스 연결 상태' })).toHaveTextContent('연결 실패'));
  expect(screen.getByRole('button', { name: '재시도' })).toBeEnabled();
});
it('prerenders a truthful loading shell without API requests', () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  const html = renderToString(<MemoryRouter><Home /></MemoryRouter>);
  expect(html).toContain('로그인 상태를 확인하는 중'); expect(html).not.toContain('아직 등록된 자료'); expect(html).toContain('무엇이 궁금한가요?'); expect(fetch).not.toHaveBeenCalled();
});
