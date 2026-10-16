// A tab-local handoff across the full-page OAuth redirect. No identity or run data.
const key = 'issuedigest.guest-question.v1';
const lifetime = 30 * 60_000;
const validQuestion = (value: unknown): value is string => typeof value === 'string' && value.length <= 1500 && value.trim().length > 0;

export function writeGuestQuestionDraft(question: string): boolean {
  if (!validQuestion(question)) return false;
  try {
    window.sessionStorage.setItem(key, JSON.stringify({version: 1, question: question.trim(), createdAt: Date.now()}));
    return true;
  } catch { return false; }
}
export function clearGuestQuestionDraft(): void {
  try { window.sessionStorage.removeItem(key); } catch { /* Storage may be unavailable. */ }
}
export function readGuestQuestionDraft(): string | null {
  try {
    const raw = window.sessionStorage.getItem(key);
    if (raw === null) return null;
    if (raw.length > 12000) { clearGuestQuestionDraft(); return null; }
    const draft: unknown = JSON.parse(raw);
    if (typeof draft !== 'object' || draft === null || !('version' in draft) || draft.version !== 1
      || !('question' in draft) || !validQuestion(draft.question)
      || !('createdAt' in draft) || typeof draft.createdAt !== 'number' || !Number.isFinite(draft.createdAt)
      || draft.createdAt > Date.now() || Date.now() - draft.createdAt >= lifetime) {
      clearGuestQuestionDraft(); return null;
    }
    return draft.question.trim();
  } catch { clearGuestQuestionDraft(); return null; }
}
export function consumeGuestQuestionDraft(): string | null {
  const question = readGuestQuestionDraft();
  if (question === null) return null;
  try { window.sessionStorage.removeItem(key); return question; } catch { return null; }
}
