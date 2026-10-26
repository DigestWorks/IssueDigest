export type PendingQuestion = { request_id: string; question: string };
type Entry = PendingQuestion & { workspace: string };
type PendingStore = { actor: string; entries: Entry[] };
const key = 'issuedigest.question.pending.v1';
const uuid = (v: unknown): v is string =>
  typeof v === 'string' &&
  /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/i.test(v);
function save(value: PendingStore) {
  try {
    if (value.entries.length)
      sessionStorage.setItem(key, JSON.stringify(value));
    else sessionStorage.removeItem(key);
  } catch {
    /* Storage may be unavailable. */
  }
}
function read(actor?: string): PendingStore {
  const empty = { actor: actor ?? '', entries: [] };
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return empty;
    if (raw.length > 600000) throw new Error();
    const value = JSON.parse(raw);
    // Accept the previous single entry without losing an outstanding request during upgrade.
    const store =
      Object.keys(value).length === 4 && 'workspace' in value
        ? {
            actor: value.actor,
            entries: [
              {
                workspace: value.workspace,
                request_id: value.request_id,
                question: value.question,
              },
            ],
          }
        : value;
    if (
      Object.keys(store).length !== 2 ||
      !uuid(store.actor) ||
      (actor !== undefined && store.actor !== actor) ||
      !Array.isArray(store.entries) ||
      store.entries.length > 50 ||
      !store.entries.every(
        (entry: Entry) =>
          entry &&
          Object.keys(entry).length === 3 &&
          uuid(entry.workspace) &&
          uuid(entry.request_id) &&
          typeof entry.question === 'string' &&
          entry.question.trim() &&
          Array.from(entry.question).length <= 1500,
      ) ||
      new Set(store.entries.map((entry: Entry) => entry.workspace)).size !==
        store.entries.length
    )
      throw new Error();
    return store;
  } catch {
    try {
      sessionStorage.removeItem(key);
    } catch {
      /* Storage may be unavailable. */
    }
    return empty;
  }
}
/** A direct protected reader can invalidate a workspace before session identification. */
export function clearPendingQuestion(actor?: string, workspace?: string) {
  if (workspace) {
    const store = read(actor);
    save({
      ...store,
      entries: store.entries.filter((entry) => entry.workspace !== workspace),
    });
  } else {
    try {
      sessionStorage.removeItem(key);
    } catch {
      /* Storage may be unavailable. */
    }
  }
}
/** Membership reconciliation is independent of whichever workspace is selected. */
export function reconcilePendingQuestions(actor: string, workspaces: string[]) {
  const store = read(actor);
  save({
    ...store,
    entries: store.entries.filter((entry) =>
      workspaces.includes(entry.workspace),
    ),
  });
}
export function readPendingQuestion(
  actor: string,
  workspace: string,
): PendingQuestion | null {
  const entry = read(actor).entries.find(
    (entry) => entry.workspace === workspace,
  );
  return entry
    ? { request_id: entry.request_id, question: entry.question }
    : null;
}
export function writePendingQuestion(
  actor: string,
  workspace: string,
  value: PendingQuestion,
) {
  if (
    !uuid(actor) ||
    !uuid(workspace) ||
    !uuid(value.request_id) ||
    !value.question.trim() ||
    Array.from(value.question).length > 1500
  )
    return;
  const store = read(actor);
  const entries = store.entries.filter(
    (entry) => entry.workspace !== workspace,
  );
  if (entries.length >= 50) return;
  save({ actor, entries: [...entries, { workspace, ...value }] });
}
