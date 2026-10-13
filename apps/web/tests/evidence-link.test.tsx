import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, RouterProvider } from 'react-router';
import { expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import canvas from '../../../tests/fixtures/canvas-synthetic.json';
import EvidenceRoute from '../app/routes/evidence';
import { response } from './workspace-data';
const path = '/workspaces/00000000-0000-4000-8000-000000000001/evidence/00000000-0000-4000-8000-000000000099';
function mount() { const router = createMemoryRouter([{ path: '/', Component: Home }, { path: '/workspaces/:workspaceId/evidence/:snapshotId', Component: EvidenceRoute }]); render(<RouterProvider router={router} />); return router; }
it.each([path, `http://localhost:3000${path}`])('opens a valid saved evidence link using actual navigation and GET: %s', async link => {
  vi.stubGlobal('fetch', async (url: string) => url.endsWith('/session') ? response({}, 401) : new Response(JSON.stringify(canvas.research.evidence[0]), { headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store', 'X-Request-ID': '8ff9af27-d021-4fb3-a46e-cf8c3d093c44' } }));
  const router = mount(); const user = userEvent.setup(); await user.type(screen.getByLabelText('근거 링크'), link); await user.click(screen.getByRole('button', { name: '근거 링크 열기' }));
  expect(await screen.findByRole('heading', { name: '합성 문서 A' })).toBeInTheDocument(); expect(router.state.location.pathname).toBe(path);
});
it.each([`https://outside.example${path}`, `http://user:secret@localhost:3000${path}`, `${path}?token=secret`, `${path}#citation`, `//localhost:3000${path}`, '/workspaces/bad/evidence/bad', `${path}/`, `http://localhost:3000${path}?`, `http://localhost:3000${path}#`, `http://@localhost:3000${path}`, `/prefix/..${path}`, 'javascript:alert(1)'])('rejects unsafe or malformed evidence links without navigation: %s', async link => {
  const fetch = vi.fn(async (url: string) => response({}, url.endsWith('/session') ? 401 : 503)); vi.stubGlobal('fetch', fetch); const router = mount(); const user = userEvent.setup();
  await user.type(screen.getByLabelText('근거 링크'), link); await user.click(screen.getByRole('button', { name: '근거 링크 열기' }));
  expect(screen.getByRole('alert')).toHaveTextContent('근거 링크'); expect(router.state.location.pathname).toBe('/'); expect(fetch).toHaveBeenCalledTimes(1); expect(fetch.mock.calls[0][0]).toBe('/api/v1/auth/session');
});
