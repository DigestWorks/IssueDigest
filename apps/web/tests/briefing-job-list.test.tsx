import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { afterEach, expect, it, vi } from 'vitest';
import BriefingJobHistory from '../app/briefing-job-list';
const id = '11111111-1111-4111-8111-111111111111';
afterEach(() => vi.unstubAllGlobals());
it('reads actual records, links by question and shows no invented date', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      new Response(
        JSON.stringify({
          items: [
            {
              job_id: id,
              question: '<script>원래 질문</script>',
              status: 'completed',
            },
          ],
        }),
        {
          headers: {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-store',
            'X-Request-ID': id,
          },
        },
      ),
    );
  vi.stubGlobal('fetch', fetch);
  render(
    <MemoryRouter>
      <BriefingJobHistory workspaceId={id} />
    </MemoryRouter>,
  );
  expect(
    await screen.findByRole('link', { name: '<script>원래 질문</script>' }),
  ).toHaveAttribute('href', `/workspaces/${id}/briefings/${id}`);
  expect(document.querySelector('script')).toBeNull();
  expect(screen.getByText('완료')).toBeInTheDocument();
  expect(screen.queryByText(id)).not.toBeInTheDocument();
  expect(fetch.mock.calls[0][0]).toBe(`/api/v1/workspaces/${id}/briefing-jobs`);
});
