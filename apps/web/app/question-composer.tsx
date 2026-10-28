import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router';
import { submitQuestion, QuestionError } from '@issuedigest/api-client';
import {
  clearPendingQuestion,
  readPendingQuestion,
  writePendingQuestion,
  type PendingQuestion,
} from './question-pending';
import './question-composer.css';
import { useResearchDrafts } from './research-drafts';
export default function QuestionComposer({
  actor,
  workspaceId,
  initialQuestion,
  onInitialQuestionInitialized,
  canEdit,
}: {
  actor: string;
  workspaceId: string;
  initialQuestion?: string;
  onInitialQuestionInitialized: () => void;
  canEdit: boolean;
}) {
  const drafts = useResearchDrafts();
  const navigate = useNavigate();
  const [pending, setPending] = useState(() =>
    readPendingQuestion(actor, workspaceId),
  );
  const [question, setQuestion] = useState(
    () =>
      initialQuestion ??
      drafts.read(workspaceId, null)?.question ??
      pending?.question ??
      '',
  );
  const [busy, setBusy] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [message, setMessage] = useState('');
  const [failed, setFailed] = useState(!!pending);
  const request = useRef<AbortController | null>(null);
  const current = useRef(true);
  useEffect(() => {
    if (!canEdit) {
      clearPendingQuestion(actor, workspaceId);
      setPending(null);
    }
    current.current = true;
    onInitialQuestionInitialized();
    return () => {
      current.current = false;
      request.current?.abort();
    };
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (request.current || !question.trim() || !canEdit || accessDenied) return;
    const value: PendingQuestion =
      pending?.question === question
        ? pending
        : { request_id: crypto.randomUUID(), question };
    setPending(value);
    writePendingQuestion(actor, workspaceId, value);
    const controller = new AbortController();
    request.current = controller;
    setBusy(true);
    setFailed(false);
    setMessage('질문을 접수하는 중…');
    try {
      const result = await submitQuestion(workspaceId, value, {
        signal: controller.signal,
        onProgress: () => {
          if (current.current)
            setMessage('질문을 분석하고 근거를 살펴보는 중…');
        },
      });
      if (!current.current) return;
      clearPendingQuestion(actor, workspaceId);
      setPending(null);
      if (result.data.kind === 'briefing') {
        setMessage('');
        void navigate(
          `/workspaces/${workspaceId}/briefings/${result.data.job_id}`,
        );
      } else
        setMessage(
          result.data.kind === 'no_match'
            ? '질문에 답할 수 있는 근거를 찾지 못했습니다.'
            : '현재 자료에서는 질문에 답할 충분한 근거를 확인하지 못했습니다.',
        );
    } catch (error) {
      if (!current.current) return;
      const kind = error instanceof QuestionError ? error.kind : 'unavailable';
      if (['unauthorized', 'forbidden', 'not-found'].includes(kind)) {
        clearPendingQuestion(actor, workspaceId);
        setPending(null);
        setQuestion('');
        drafts.clearWorkspace(workspaceId);
        setAccessDenied(true);
        setMessage('접근 권한을 확인할 수 없습니다.');
      } else {
        setFailed(true);
        setMessage(
          kind === 'budget'
            ? '이번 달 조사 한도에 도달했습니다.'
            : '응답을 확인하지 못했습니다. 같은 질문을 다시 확인할 수 있습니다.',
        );
      }
    } finally {
      if (current.current) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  return (
    <form
      className="guest-composer question-composer"
      onSubmit={(event) => void submit(event)}
      aria-busy={busy}
    >
      <label className="visually-hidden" htmlFor="member-question">
        무엇을 알아볼까요?
      </label>
      <textarea
        id="member-question"
        rows={3}
        maxLength={1500}
        value={question}
        disabled={busy || !canEdit || accessDenied}
        onChange={(event) => {
          setQuestion(event.target.value);
          drafts.write(workspaceId, null, { question: event.target.value });
          setFailed(false);
          setMessage('');
        }}
        placeholder="궁금한 이슈나 알고 싶은 변화를 적어 주세요"
      />
      <div className="guest-compose-foot">
        <button
          type="submit"
          disabled={busy || !canEdit || accessDenied || !question.trim()}
        >
          {busy
            ? '브리핑 만드는 중…'
            : failed && pending?.question === question
              ? '같은 질문 다시 확인'
              : '질문하기'}
          <span className="submit-arrow" aria-hidden="true">
            ↑
          </span>
        </button>
      </div>
      {!canEdit && <p>현재 권한으로는 질문을 제출할 수 없습니다.</p>}
      <p role="status" aria-live="polite">
        {message ||
          (failed
            ? '완료 응답을 확인하지 못한 질문이 있습니다. 직접 다시 확인해 주세요.'
            : '')}
      </p>
    </form>
  );
}
