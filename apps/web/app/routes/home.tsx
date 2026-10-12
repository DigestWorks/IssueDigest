import { ChatPanel } from "~/chat/chat-panel"
import { StageView } from "~/stage/stage-view"

import type { Route } from "./+types/home"

export function meta(_: Route.MetaArgs) {
  return [
    { title: "IssueDigest" },
    { name: "description", content: "이슈의 맥락과 근거를 탐색하고 시각적으로 보여 주는 서비스" },
  ]
}

export default function Home() {
  return (
    <main className="grid h-svh grid-cols-[400px_minmax(0,1fr)] overflow-hidden">
      <ChatPanel />
      <StageView />
    </main>
  )
}
