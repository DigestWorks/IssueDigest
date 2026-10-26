import { afterEach, expect, it, vi } from 'vitest';
import { submitQuestion } from '../src/question-submissions';
const id = '11111111-1111-4111-8111-111111111111';
afterEach(() => vi.unstubAllGlobals());
function response(text: string) {
  return new Response(text, {
    headers: {
      'Content-Type': 'text/event-stream; charset=utf-8',
      'Cache-Control': 'no-store',
      'X-Request-ID': id,
      'X-Accel-Buffering': 'no',
    },
  });
}
it('posts once with cookies and accepts split CRLF progress and terminal', async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      response(
        `event: progress\r\ndata: {"request_id":"${id}","stage":"analysing"}\r\n\r\nevent: result\r\ndata: {"request_id":"${id}","kind":"no_match","job_id":null}\r\n\r\n`,
      ),
    );
  vi.stubGlobal('fetch', fetch);
  expect(
    (await submitQuestion(id, { request_id: id, question: '질문' })).data.kind,
  ).toBe('no_match');
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(fetch.mock.calls[0][1].credentials).toBe('same-origin');
});
it.each([
  '',
  `event: result\ndata: {"request_id":"${id}","kind":"briefing","job_id":null}\n\n`,
  `event: result\ndata: {"request_id":"${id}","kind":"no_match","job_id":null,"extra":true}\n\n`,
])('rejects incomplete or invalid streams', async (text) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(text)));
  await expect(
    submitQuestion(id, { request_id: id, question: '질문' }),
  ).rejects.toMatchObject({ kind: 'malformed' });
});
it.each([
  `event: result\ndata: {"request_id":"${id}","kind":"no_match","job_id":null}\n\nevent: result\ndata: {"request_id":"${id}","kind":"no_match","job_id":null}\n\n`,
  `event: unknown\ndata: {"request_id":"${id}"}\n\n`,
  `event: result\ndata: {"request_id":"22222222-2222-4222-8222-222222222222","kind":"no_match","job_id":null}\n\n`,
  `id: secret\n\n`,
  `event: progress\ndata: {"request_id":"${id}","stage":"other"}\n\n`,
  `: ${'x'.repeat(8192)}\n\n`,
])('rejects hostile frames', async (text) => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(text)));
  await expect(
    submitQuestion(id, { request_id: id, question: '질문' }),
  ).rejects.toMatchObject({ kind: 'malformed' });
});
it('decodes byte-split UTF8 and CRLF frames', async () => {
  const bytes = new TextEncoder().encode(
    `: 확인\r\n\r\nevent: result\r\ndata: {"request_id":"${id}","kind":"blocked","job_id":null}\r\n\r\n`,
  );
  const r = response('');
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(c) {
            for (const byte of bytes) c.enqueue(new Uint8Array([byte]));
            c.close();
          },
        }),
        { headers: r.headers },
      ),
    ),
  );
  expect(
    (await submitQuestion(id, { request_id: id, question: '질문' })).data.kind,
  ).toBe('blocked');
});
it('rejects malformed UTF8', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        new Response(new Uint8Array([255]), { headers: response('').headers }),
      ),
  );
  await expect(
    submitQuestion(id, { request_id: id, question: '질문' }),
  ).rejects.toMatchObject({ kind: 'malformed' });
});
it('aborts a stalled stream and cancels reader without retry', async () => {
  const cancel = vi.fn();
  const fetch = vi.fn().mockResolvedValue(
    new Response(new ReadableStream({ cancel }), {
      headers: response('').headers,
    }),
  );
  vi.stubGlobal('fetch', fetch);
  const controller = new AbortController();
  const promise = submitQuestion(
    id,
    { request_id: id, question: '질문' },
    { signal: controller.signal },
  );
  await Promise.resolve();
  controller.abort();
  await expect(promise).rejects.toMatchObject({ kind: 'aborted' });
  expect(fetch).toHaveBeenCalledTimes(1);
  expect(cancel).toHaveBeenCalled();
});
it.each([401, 403, 409, 429, 503])(
  'maps HTTP %s without parsing server error text',
  async (status) => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(new Response('private', { status })),
    );
    await expect(
      submitQuestion(id, { request_id: id, question: '질문' }),
    ).rejects.toMatchObject({
      kind: (
        {
          401: 'unauthorized',
          403: 'forbidden',
          409: 'conflict',
          429: 'budget',
          503: 'unavailable',
        } as Record<number, string>
      )[status],
    });
  },
);
it('times out idle while fetch is stalled', async () => {
  vi.useFakeTimers();
  vi.stubGlobal(
    'fetch',
    vi.fn(() => new Promise(() => {})),
  );
  const promise = submitQuestion(id, { request_id: id, question: '질문' });
  const check = expect(promise).rejects.toMatchObject({ kind: 'timeout' });
  await vi.advanceTimersByTimeAsync(20000);
  await check;
  vi.useRealTimers();
});
it('enforces whole body cap even with individually small heartbeats', async () => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(response(': keepalive\n\n'.repeat(12000))),
  );
  await expect(
    submitQuestion(id, { request_id: id, question: '질문' }),
  ).rejects.toMatchObject({ kind: 'malformed' });
});
it.each(['Cache-Control', 'Content-Type', 'X-Request-ID', 'X-Accel-Buffering'])(
  'rejects missing required %s header',
  async (header) => {
    const r = response('');
    r.headers.delete(header);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(r));
    await expect(
      submitQuestion(id, { request_id: id, question: '질문' }),
    ).rejects.toMatchObject({ kind: 'malformed' });
  },
);
it('bounds overall time despite regular heartbeat activity', async () => {
  vi.useFakeTimers();
  let stream!: ReadableStreamDefaultController<Uint8Array>;
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue(
      new Response(
        new ReadableStream({
          start(c) {
            stream = c;
          },
        }),
        { headers: response('').headers },
      ),
    ),
  );
  const promise = submitQuestion(id, { request_id: id, question: '질문' });
  const check = expect(promise).rejects.toMatchObject({ kind: 'timeout' });
  for (let t = 0; t < 61; t++) {
    await vi.advanceTimersByTimeAsync(10000);
    stream.enqueue(new TextEncoder().encode(': keepalive\n\n'));
    await Promise.resolve();
  }
  await vi.advanceTimersByTimeAsync(10000);
  await check;
  vi.useRealTimers();
});
it.each(['["no_match"]', '["unavailable"]'])(
  'rejects non-string enum %s',
  async (kind) => {
    const event = kind.includes('unavailable') ? 'error' : 'result';
    const job = event === 'result' ? ',"job_id":null' : '';
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          response(
            `event: ${event}\ndata: {"request_id":"${id}","kind":${kind}${job}}\n\n`,
          ),
        ),
    );
    await expect(
      submitQuestion(id, { request_id: id, question: '질문' }),
    ).rejects.toMatchObject({ kind: 'malformed' });
  },
);
it('counts CRLF and frame separators in the event byte cap', async () => {
  vi.stubGlobal(
    'fetch',
    vi
      .fn()
      .mockResolvedValue(
        response(
          `:${'x'.repeat(8188)}\r\n\r\nevent: result\ndata: {"request_id":"${id}","kind":"no_match","job_id":null}\n\n`,
        ),
      ),
  );
  await expect(
    submitQuestion(id, { request_id: id, question: '질문' }),
  ).rejects.toMatchObject({ kind: 'malformed' });
});
