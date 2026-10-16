import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import Home from '../app/routes/home';
import { MemoryRouter } from 'react-router';
import { renderToString } from 'react-dom/server';
import { response } from './workspace-data';

it('offers basic navigation with explicit login inside the guest account menu', async () => {
  vi.stubGlobal('fetch', async () => response({}, 401));
  render(<MemoryRouter><Home /></MemoryRouter>);
  expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('무엇이 궁금한가요?');
  expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toHaveTextContent('브리핑');
  expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toHaveTextContent('브리핑 기록');
  await screen.findByRole('button', {name: '질문하기'}); await userEvent.setup().click(screen.getByRole('button', {name: '계정 메뉴'}));
  expect(screen.getByRole('menuitem', { name: '로그인' })).toHaveAttribute('href', '/login');
});

it('prerenders a truthful loading shell without API requests', () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch);
  const html = renderToString(<MemoryRouter><Home /></MemoryRouter>);
  expect(html).toContain('로그인 상태를 확인하는 중'); expect(html).not.toContain('아직 등록된 자료'); expect(html).toContain('무엇이 궁금한가요?'); expect(fetch).not.toHaveBeenCalled();
});
