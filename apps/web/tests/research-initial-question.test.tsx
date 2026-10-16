import { StrictMode } from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { expect, it, vi } from 'vitest';
import ResearchDesk from '../app/research';
import { response, workspace } from './workspace-data';
it('uses an optional initial question for a new desk without a draft provider or automatic POST, including StrictMode replay', async () => {
  const fetch = vi.fn<(path: string, options?: RequestInit) => Promise<Response>>(async () => response({workspace_id: workspace, items: []})); vi.stubGlobal('fetch', fetch);
  render(<StrictMode><MemoryRouter><ResearchDesk workspaceId={workspace} canEdit view="research" initialQuestion="직접 확인할 초안" /></MemoryRouter></StrictMode>);
  expect(await screen.findByRole('textbox', {name: '무엇을 알아볼까요?'})).toHaveValue('직접 확인할 초안');
  expect(fetch.mock.calls.every(([, options]) => !options || options.method !== 'POST')).toBe(true);
});
