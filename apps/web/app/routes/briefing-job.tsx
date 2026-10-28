import { useEffect, useRef, useState } from 'react';
import { Link, useParams } from 'react-router';
import {
  BriefingJobError,
  EvidenceError,
  getBriefingJob,
  cancelBriefingJob,
  getEvidence,
  type BriefingJobView,
  type BriefingQuoteView,
} from '@issuedigest/api-client';
import BrandHeader from '../brand-header';
import { EvidenceDrawer, type EvidenceReaderState } from '../research-evidence';
import '../research.css';
import '../evidence/reader.css';
import '../briefing-job.css';
const active = (job: BriefingJobView) =>
  ['pending', 'running'].includes(job.status);
const labels = {
  pending: '브리핑을 준비하고 있습니다.',
  running: '근거를 읽고 브리핑을 작성하고 있습니다.',
  completed: '브리핑 작성 완료',
  cancelled: '브리핑이 취소되었습니다.',
  failed: '브리핑을 작성하지 못했습니다.',
  indeterminate: '브리핑의 처리 결과를 확인하기 어렵습니다.',
};
function failure(error: unknown) {
  return error instanceof BriefingJobError
    ? error.kind
    : error instanceof EvidenceError
      ? error.kind === 'authentication'
        ? 'unauthorized'
        : error.kind === 'not-found'
          ? 'not-found'
          : error.kind === 'invalid-response'
            ? 'malformed'
            : error.kind
      : 'unavailable';
}
// JSON property order is not part of the wire contract.
function sameQuote(a: BriefingQuoteView, b: BriefingQuoteView) {
  return (
    a.snapshot_id.toLowerCase() === b.snapshot_id.toLowerCase() &&
    a.citation_id.toLowerCase() === b.citation_id.toLowerCase() &&
    a.source_title === b.source_title &&
    a.citation_quote === b.citation_quote &&
    a.start === b.start &&
    a.end === b.end &&
    a.text === b.text
  );
}
function containsQuote(job: BriefingJobView, quote: BriefingQuoteView) {
  return (
    job.status === 'completed' &&
    job.result !== null &&
    [
      ...job.result.additional_quotes,
      ...job.result.modules.flatMap((module) =>
        module.claims.flatMap((claim) => claim.quotes),
      ),
    ].some((currentQuote) => sameQuote(currentQuote, quote))
  );
}
export function BriefingJobReader({
  workspaceId,
  jobId,
}: {
  workspaceId: string;
  jobId: string;
}) {
  const [job, setJob] = useState<BriefingJobView | null>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false),
    [opening, setOpening] = useState(false),
    [reader, setReader] = useState<EvidenceReaderState | null>(null);
  const current = useRef<BriefingJobView | null>(null),
    generation = useRef(0),
    pending = useRef<AbortController | null>(null),
    cancelLock = useRef(false);
  function begin() {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    const token = ++generation.current;
    return {
      controller,
      valid: () => !controller.signal.aborted && generation.current === token,
    };
  }
  function fail(cause: unknown) {
    const kind = failure(cause);
    if (kind === 'aborted') return;
    setReader(null);
    setError(kind);
    if (!['network', 'timeout'].includes(kind)) {
      current.current = null;
      setJob(null);
    }
  }
  function accept(next: BriefingJobView) {
    if (current.current && !active(current.current) && active(next)) return;
    current.current = next;
    setJob(next);
    setError('');
  }
  async function refresh() {
    if (cancelLock.current) return;
    const { controller, valid } = begin();
    setReader(null);
    setOpening(false);
    try {
      const { data } = await getBriefingJob(workspaceId, jobId, {
        signal: controller.signal,
      });
      if (valid()) accept(data);
    } catch (cause) {
      if (valid()) fail(cause);
    }
  }
  useEffect(() => {
    void refresh();
    const check = () => {
      if (document.visibilityState !== 'hidden') {
        cancelLock.current = false;
        setBusy(false);
        void refresh();
      }
    };
    window.addEventListener('focus', check);
    document.addEventListener('visibilitychange', check);
    return () => {
      generation.current++;
      pending.current?.abort();
      window.removeEventListener('focus', check);
      document.removeEventListener('visibilitychange', check);
    };
  }, [workspaceId, jobId]);
  useEffect(() => {
    if (!job || !active(job) || error || busy) return;
    const timer = setTimeout(() => void refresh(), 1600);
    return () => clearTimeout(timer);
  });
  async function cancel() {
    if (cancelLock.current || !current.current || !active(current.current))
      return;
    cancelLock.current = true;
    setBusy(true);
    setOpening(false);
    setReader(null);
    const { controller, valid } = begin();
    try {
      const { data } = await cancelBriefingJob(workspaceId, jobId, {
        signal: controller.signal,
      });
      if (valid()) accept(data);
    } catch (cause) {
      if (valid()) fail(cause);
    } finally {
      if (valid()) {
        cancelLock.current = false;
        setBusy(false);
      }
    }
  }
  async function open(quote: BriefingQuoteView) {
    if (cancelLock.current) return;
    const origin =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;
    const { controller, valid } = begin();
    setReader(null);
    setOpening(true);
    try {
      const { data } = await getBriefingJob(workspaceId, jobId, {
        signal: controller.signal,
      });
      if (!valid()) return;
      accept(data);
      if (!containsQuote(data, quote)) throw new BriefingJobError('malformed');
      const proof = await getEvidence(workspaceId, quote.snapshot_id, {
        signal: controller.signal,
      });
      if (!valid()) return;
      const citation = proof.data.citations.find(
        (c) => c.citation_id.toLowerCase() === quote.citation_id.toLowerCase(),
      );
      if (
        !citation ||
        citation.selector.quote !== quote.citation_quote ||
        Array.from(citation.selector.quote)
          .slice(quote.start, quote.end)
          .join('') !== quote.text
      )
        throw new BriefingJobError('malformed');
      // Evidence membership does not establish the originating job's current authority.
      const latest = await getBriefingJob(workspaceId, jobId, {
        signal: controller.signal,
      });
      if (!valid()) return;
      if (
        latest.data.question !== data.question ||
        !containsQuote(latest.data, quote)
      )
        throw new BriefingJobError('malformed');
      accept(latest.data);
      setReader({
        identity: `${workspaceId}/${jobId}`,
        snapshotId: quote.snapshot_id,
        citationId: quote.citation_id,
        data: proof.data,
        title: quote.source_title,
        origin,
      });
    } catch (cause) {
      if (valid()) fail(cause);
    } finally {
      if (valid()) setOpening(false);
    }
  }
  function quotes(items: BriefingQuoteView[]) {
    return items.map((q, i) => (
      <blockquote key={`${q.citation_id}/${i}`}>
        <p>{q.text}</p>
        <cite>{q.source_title}</cite>
        <button type="button" onClick={() => void open(q)} disabled={opening}>
          원문 열기
        </button>
      </blockquote>
    ));
  }
  function claimContent(
    claim: NonNullable<
      BriefingJobView['result']
    >['modules'][number]['claims'][number],
  ) {
    return (
      <>
        {claim.event_date && (
          <time className="briefing-job-date" dateTime={claim.event_date}>
            {claim.event_date}
          </time>
        )}
        <p className="briefing-job-label">
          {claim.epistemic_status === 'source_statement'
            ? '자료의 서술'
            : '확인하기 어려움'}
        </p>
        <p className="briefing-job-claim">{claim.text}</p>
        <details>
          <summary>근거 읽기</summary>
          {quotes(claim.quotes)}
        </details>
      </>
    );
  }
  return (
    <>
      <div className="briefing-job-shell">
        <BrandHeader />
        <main className="briefing-job">
          <Link className="briefing-job-back" to="/">
            홈으로 돌아가기
          </Link>
          {job ? (
            <>
              <header className="briefing-job-heading">
                <p className="briefing-job-eyebrow">AI 브리핑</p>
                <h1>{job.question}</h1>
                <p className="briefing-job-note">
                  자료에 근거한 AI 요약입니다. 자료의 서술은 독립적으로 확인된
                  사실을 뜻하지 않습니다.
                </p>
              </header>
              <p
                className={job.status === 'completed'
                  ? 'briefing-job-status-completed'
                  : 'briefing-job-status'}
                role="status"
                aria-live="polite"
              >
                {busy ? '취소 중…' : labels[job.status]}
              </p>
              {active(job) && (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void cancel()}
                >
                  브리핑 취소
                </button>
              )}
              {job.result?.outcome === 'insufficient_evidence' ? (
                <p>{job.result.message}</p>
              ) : (
                job.result?.modules.map((module, i) => (
                  <section
                    key={i}
                    aria-label={module.title}
                    className={`briefing-job-module briefing-job-${module.kind}`}
                  >
                    {module.kind === 'summary' ? (
                      <>
                        <h2>{module.title}</h2>
                        {module.claims.map((claim, j) => (
                          <article key={j}>{claimContent(claim)}</article>
                        ))}
                      </>
                    ) : (
                      <details className="briefing-job-detail">
                        <summary>
                          <span className="briefing-job-detail-kind">
                            {module.kind === 'comparison' ? '자료 비교' : '시간순 정리'}
                          </span>
                          <h2>{module.title}</h2>
                        </summary>
                        {module.kind === 'timeline' ? (
                          <ol
                            className="briefing-job-timeline-list"
                            aria-label={`${module.title} 항목`}
                          >
                            {module.claims.map((claim, j) => (
                              <li key={j}>{claimContent(claim)}</li>
                            ))}
                          </ol>
                        ) : module.kind === 'comparison' ? (
                          <ul
                            className="briefing-job-comparison-list"
                            aria-label={`${module.title} 항목`}
                          >
                            {module.claims.map((claim, j) => (
                              <li key={j}>{claimContent(claim)}</li>
                            ))}
                          </ul>
                        ) : null}
                      </details>
                    )}
                  </section>
                ))
              )}
              {Boolean(job.result?.additional_quotes.length) && (
                <details>
                  <summary>더 살펴볼 근거</summary>
                  {quotes(job.result!.additional_quotes)}
                </details>
              )}
            </>
          ) : (
            !error && (
              <p role="status" aria-live="polite">
                브리핑을 불러오고 있습니다.
              </p>
            )
          )}
          {error && (
            <div role="alert">
              <p>
                {error === 'unauthorized'
                  ? '로그인이 필요합니다.'
                  : ['forbidden', 'not-found'].includes(error)
                    ? '이 브리핑에 접근할 수 없습니다.'
                    : ['timeout', 'network'].includes(error)
                      ? '연결을 확인하지 못했습니다. 다시 조회해 주세요.'
                      : '브리핑을 확인하지 못했습니다. 다시 조회해 주세요.'}
              </p>
              {error === 'unauthorized' ? (
                <Link to="/login">로그인</Link>
              ) : (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void refresh()}
                >
                  다시 조회
                </button>
              )}
            </div>
        )}
        {opening && <p role="status">현재 권한과 원문을 확인하고 있습니다.</p>}
        {reader && (
          <EvidenceDrawer
            reader={reader}
            workspaceId={workspaceId}
            onClose={() => setReader(null)}
          />
        )}
      </main>
      </div>
    </>
  );
}
export default function BriefingJobRoute() {
  const { workspaceId = '', jobId = '' } = useParams();
  return (
    <BriefingJobReader
      key={`${workspaceId}/${jobId}`}
      workspaceId={workspaceId}
      jobId={jobId}
    />
  );
}
