import { expect, it, vi } from 'vitest';
import {
  getBriefingJob,
  cancelBriefingJob,
} from '../../../packages/api-client/src/briefing-jobs';
export const jobId = '00000000-0000-4000-8000-000000000040';
export const job = {
  job_id: jobId,
  question: '자료의 내용은?',
  status: 'pending',
  result: null,
};
export function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store',
      'X-Request-ID': jobId,
    },
  });
}
it('uses protected GET and empty object cancellation', async () => {
  const fetcher = vi
    .fn()
    .mockImplementation(() => Promise.resolve(response(job)));
  vi.stubGlobal('fetch', fetcher);
  await getBriefingJob(jobId, jobId);
  await cancelBriefingJob(jobId, jobId);
  expect(fetcher.mock.calls[0][1]).toMatchObject({
    method: 'GET',
    cache: 'no-store',
    credentials: 'same-origin',
  });
  expect(fetcher.mock.calls[1][1]).toMatchObject({
    method: 'POST',
    body: '{}',
  });
});
it('rejects invalid identity and unexpected response keys', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(response({ ...job, extra: 1 })),
  );
  await expect(getBriefingJob('bad', jobId)).rejects.toMatchObject({
    kind: 'invalid-query',
  });
  await expect(getBriefingJob(jobId, jobId)).rejects.toMatchObject({
    kind: 'malformed',
  });
});
const quote = {
  snapshot_id: jobId,
  citation_id: jobId,
  source_title: '원자료',
  start: 1,
  end: 2,
  text: '😀',
  citation_quote: '가😀나',
};
export function completed() {
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
it.each(['id', 'extra', 'date', 'span', 'status', 'comparison', 'length'])(
  'rejects malformed %s',
  async (kind) => {
    const data = completed();
    if (kind === 'id') data.job_id = '00000000-0000-4000-8000-000000000041';
    if (kind === 'extra') Object.assign(data.result, { extra: true });
    if (kind === 'date')
      data.result.modules[2].claims[0].event_date = '2023-02-29';
    if (kind === 'span')
      data.result.modules[0].claims[0].quotes = [{ ...quote, end: 3 }];
    if (kind === 'status') data.status = 'running';
    if (kind === 'comparison') data.result.modules[1].claims.length = 1;
    if (kind === 'length') data.question = 'x'.repeat(1501);
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => Promise.resolve(response(data))),
    );
    await expect(getBriefingJob(jobId, jobId)).rejects.toMatchObject({
      kind: 'malformed',
    });
  },
);
it('accepts real modules with codepoint quote and aborts body reading', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockImplementation(() => Promise.resolve(response(completed()))),
  );
  expect((await getBriefingJob(jobId, jobId)).data.status).toBe('completed');
  const controller = new AbortController();
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
      headers: new Headers({
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
        'X-Request-ID': jobId,
      }),
      json: () => new Promise(() => {}),
    }),
  );
  const pending = getBriefingJob(jobId, jobId, { signal: controller.signal });
  await Promise.resolve();
  controller.abort();
  await expect(pending).rejects.toMatchObject({ kind: 'aborted' });
});
it.each(['status', 'epistemic_status', 'module_kind'])(
  'rejects array-valued enum %s without coercion',
  async (field) => {
    const data = completed();
    if (field === 'status')
      Object.assign(data, { status: ['pending'], result: null });
    if (field === 'epistemic_status')
      Object.assign(data.result.modules[0].claims[0], {
        epistemic_status: ['source_statement'],
      });
    if (field === 'module_kind') {
      Object.assign(data.result.modules[1], { kind: ['comparison'] });
      data.result.modules[1].claims.length = 1;
    }
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation(() => Promise.resolve(response(data))),
    );
    await expect(getBriefingJob(jobId, jobId)).rejects.toMatchObject({
      kind: 'malformed',
    });
  },
);
