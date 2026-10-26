import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import {
  listBriefingJobs,
  type BriefingJobList,
} from '@issuedigest/api-client';
import './question-composer.css';
const labels = {
  pending: '접수됨',
  running: '생성 중',
  completed: '완료',
  failed: '실패',
  cancelled: '취소됨',
  indeterminate: '상태 확인 필요',
};
export default function BriefingJobHistory({
  workspaceId,
}: {
  workspaceId: string;
}) {
  const [items, setItems] = useState<BriefingJobList | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let current = true;
    setItems(null);
    setFailed(false);
    void listBriefingJobs(workspaceId, { signal: controller.signal }).then(
      (result) => {
        if (current) setItems(result.data);
      },
      () => {
        if (current) setFailed(true);
      },
    );
    return () => {
      current = false;
      controller.abort();
    };
  }, [workspaceId, attempt]);
  return (
    <section className="briefing-job-list" aria-label="질문 브리핑 기록">
      <h2>질문 브리핑</h2>
      {failed ? (
        <>
          <p role="status">브리핑 기록을 불러오지 못했습니다.</p>
          <button onClick={() => setAttempt((x) => x + 1)}>
            다시 불러오기
          </button>
        </>
      ) : items ? (
        items.items.length ? (
          <ul>
            {items.items.map((item) => (
              <li key={item.job_id}>
                <Link
                  to={`/workspaces/${workspaceId}/briefings/${item.job_id}`}
                >
                  {item.question}
                </Link>
                <small>{labels[item.status]}</small>
              </li>
            ))}
          </ul>
        ) : (
          <p>저장된 질문 브리핑이 없습니다.</p>
        )
      ) : (
        <p role="status">브리핑 기록을 불러오는 중…</p>
      )}
    </section>
  );
}
