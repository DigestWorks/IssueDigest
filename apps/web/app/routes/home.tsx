import { useState } from 'react';
import { ConnectionError, getStatus } from '@issuedigest/api-client';

type State = 'idle' | 'pending' | 'success' | 'failure';
const labels: Record<State, string> = {
  idle: '연결 확인', pending: '확인 중', success: '다시 확인', failure: '재시도',
};

export default function Home() {
  const [state, setState] = useState<State>('idle');
  const [reason, setReason] = useState('');

  async function checkConnection() {
    setState('pending');
    try {
      await getStatus();
      setState('success');
    } catch (error) {
      setReason(error instanceof ConnectionError && error.kind === 'timeout'
        ? '응답을 기다리는 시간이 길어졌습니다.'
        : '서버 응답을 확인하지 못했습니다.');
      setState('failure');
    }
  }

  return (
    <div className="workspace">
      <header className="brand"><span className="brand-mark" aria-hidden="true">iD</span> IssueDigest <span className="brand-caption">이슈 조사 작업 공간</span></header>
      <main>
        <p className="eyebrow">자료에서 시작하는 조사</p>
        <h1>이슈를 읽고,<br />근거를 비교합니다.</h1>
        <p className="intro">하나의 이슈를 여러 자료와 관점으로 살펴보는 작업 공간입니다.</p>
        <section className="empty-state" aria-labelledby="empty-title">
          <span className="empty-index" aria-hidden="true">—</span>
          <div>
            <h2 id="empty-title">아직 등록된 자료가 없습니다.</h2>
            <p>조사할 이슈와 원자료가 준비되면 이곳에서 근거를 함께 살펴봅니다.</p>
          </div>
        </section>
        <section className="connection" aria-label="서비스 연결 확인">
          <div>
            <p className="connection-label">서비스 연결</p>
            <p role="status" aria-live="polite" className={`connection-status ${state}`}>
              {state === 'idle' && '아직 확인하지 않았습니다.'}
              {state === 'pending' && '요청을 접수했습니다. 연결 확인 중…'}
              {state === 'success' && '연결됨 · 서버가 응답했습니다.'}
              {state === 'failure' && `연결 실패 · ${reason}`}
            </p>
          </div>
          <button type="button" onClick={() => void checkConnection()} disabled={state === 'pending'}>{labels[state]}</button>
        </section>
      </main>
      <footer>DigestWorks <span>자료와 근거를 차분히 살펴보는 곳</span></footer>
    </div>
  );
}
