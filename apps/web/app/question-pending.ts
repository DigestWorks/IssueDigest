export type PendingQuestion = { request_id: string; question: string };
const key = 'issuedigest.question.pending.v1';
const uuid = (v: unknown): v is string =>
  typeof v === 'string' &&
  /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i.test(v);
export function clearPendingQuestion() {
  try {
    sessionStorage.removeItem(key);
  } catch {
    /* Storage may be unavailable. */
  }
}
export function readPendingQuestion(
  actor: string,
  workspace: string,
): PendingQuestion | null {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    if (raw.length > 12000) throw new Error();
    const v = JSON.parse(raw);
    if (
      Object.keys(v).length !== 4 ||
      v.actor !== actor ||
      v.workspace !== workspace ||
      !uuid(v.request_id) ||
      typeof v.question !== 'string' ||
      !v.question.trim() ||
      Array.from(v.question).length > 1500
    )
      throw new Error();
    return { request_id: v.request_id, question: v.question };
  } catch {
    clearPendingQuestion();
    return null;
  }
}
export function writePendingQuestion(
  actor: string,
  workspace: string,
  value: PendingQuestion,
) {
  try {
    sessionStorage.setItem(key, JSON.stringify({ actor, workspace, ...value }));
  } catch {
    /* Retry still works within this mounted form. */
  }
}
