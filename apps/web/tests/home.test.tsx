import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import { MemoryRouter } from 'react-router';

const success = () => new Response(JSON.stringify({ service: 'issuedigest-api', api_version: 'v1', status: 'ok' }), {
  headers: { 'X-Request-ID': '8ff9af27-d021-4fb3-a46e-cf8c3d093c44' },
});

it('keeps the empty research space with real connectivity and a saved-link entry', () => {
  render(<MemoryRouter><Home /></MemoryRouter>);
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('이슈');
  expect(screen.getByText('아직 등록된 자료가 없습니다.')).toBeInTheDocument();
  expect(screen.getAllByRole('button')).toHaveLength(2);
  expect(screen.getByRole('button', { name: '연결 확인' })).toBeEnabled();
});

it('shows confirmation in progress before rendering a real successful response', async () => {
  let resolveResponse!: (response: Response) => void;
  vi.stubGlobal('fetch', () => new Promise<Response>((resolve) => { resolveResponse = resolve; }));
  const user = userEvent.setup();
  render(<MemoryRouter><Home /></MemoryRouter>);
  await user.click(screen.getByRole('button', { name: '연결 확인' }));
  expect(screen.getByRole('status')).toHaveTextContent('확인 중');
  expect(screen.getByRole('button', { name: '확인 중' })).toBeDisabled();
  resolveResponse(success());
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('연결됨'));
  expect(screen.getByRole('button', { name: '다시 확인' })).toBeEnabled();
});

it('shows a connection failure and lets the user retry successfully', async () => {
  let available = false;
  vi.stubGlobal('fetch', async () => {
    if (!available) throw new TypeError('offline');
    return success();
  });
  const user = userEvent.setup();
  render(<MemoryRouter><Home /></MemoryRouter>);
  await user.click(screen.getByRole('button', { name: '연결 확인' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('연결 실패'));
  available = true;
  await user.click(screen.getByRole('button', { name: '재시도' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('연결됨'));
  expect(screen.getByText('아직 등록된 자료가 없습니다.')).toBeInTheDocument();
});

it('does not display a malformed API response as a successful connection', async () => {
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ status: 'ok' })));
  const user = userEvent.setup();
  render(<MemoryRouter><Home /></MemoryRouter>);
  await user.click(screen.getByRole('button', { name: '연결 확인' }));
  await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('연결 실패'));
  expect(screen.getByRole('button', { name: '재시도' })).toBeEnabled();
});
