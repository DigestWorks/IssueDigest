import { createContext, useContext, useRef, type ReactNode } from 'react';
import { clearPendingQuestion, reconcilePendingQuestions } from './question-pending';

type Draft = { question: string };
type Drafts = {
  identify: (userId: string, workspaces: string[]) => void;
  clear: () => void;
  read: (workspaceId: string, runId: string | null) => Draft | null;
  write: (workspaceId: string, runId: string | null, draft: Draft) => void;
  clearWorkspace: (workspaceId: string) => void;
};
const empty: Drafts = {
  identify: () => {}, clear: () => {}, read: () => null,
  write: () => {}, clearWorkspace: () => {},
};
const DraftContext = createContext<Drafts>(empty);
const key = (workspaceId: string, runId: string | null) => `${workspaceId.toLowerCase()}/${runId?.toLowerCase() ?? 'new'}`;

export function ResearchDraftProvider({children}: {children: ReactNode}) {
  const identity = useRef<string | null>(null);
  const drafts = useRef(new Map<string, Draft>());
  const store = useRef<Drafts>({
    identify(userId, workspaces) {
      const next = userId.toLowerCase();
      if (identity.current !== next) drafts.current.clear();
      identity.current = next;
      reconcilePendingQuestions(next, workspaces);
      const allowed = new Set(workspaces.map(id => id.toLowerCase()));
      for (const draftKey of drafts.current.keys()) {
        if (!allowed.has(draftKey.split('/')[0])) drafts.current.delete(draftKey);
      }
    },
    clear() { identity.current = null; drafts.current.clear(); clearPendingQuestion(); },
    read(workspaceId, runId) { return identity.current ? drafts.current.get(key(workspaceId, runId)) ?? null : null; },
    write(workspaceId, runId, draft) {
      if (identity.current) drafts.current.set(key(workspaceId, runId), {question: draft.question});
    },
    clearWorkspace(workspaceId) {
      clearPendingQuestion(identity.current ?? undefined, workspaceId);
      for (const draftKey of drafts.current.keys()) {
        if (draftKey.startsWith(`${workspaceId.toLowerCase()}/`)) drafts.current.delete(draftKey);
      }
    },
  });
  return <DraftContext.Provider value={store.current}>{children}</DraftContext.Provider>;
}

export const useResearchDrafts = () => useContext(DraftContext);
