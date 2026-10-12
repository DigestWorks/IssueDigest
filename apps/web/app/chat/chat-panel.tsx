import { useRef, useState } from "react"
import { ArrowUpIcon, SquareIcon } from "lucide-react"

import { Badge } from "~/components/ui/badge"
import { Bubble, BubbleContent } from "~/components/ui/bubble"
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "~/components/ui/input-group"
import { Message, MessageContent } from "~/components/ui/message"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "~/components/ui/message-scroller"
import { prefersReducedMotion } from "~/design/use-reduced-motion"
import { pickScenario, SCENARIOS } from "~/stage/scenarios"
import { playScenario } from "~/stage/scenarios/player"
import { useStage } from "~/stage/store"

type ChatMessage = { id: string; role: "user" | "assistant"; text: string }

/**
 * 채팅 패널. 지금은 질문을 샘플 시나리오에 매칭해 답변 텍스트와 스테이지
 * 이벤트를 재생한다. 실제 에이전트를 붙이면 재생 대신 에이전트 응답을 쓴다.
 */
export function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [draft, setDraft] = useState("")
  const [running, setRunning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const dispatch = useStage((s) => s.dispatch)

  async function ask(question: string) {
    const q = question.trim()
    if (!q || running) return
    setDraft("")
    const answerId = crypto.randomUUID()
    setMessages((m) => [
      ...m,
      { id: crypto.randomUUID(), role: "user", text: q },
      { id: answerId, role: "assistant", text: "" },
    ])
    const controller = new AbortController()
    abortRef.current = controller
    setRunning(true)
    try {
      await playScenario(pickScenario(q), {
        signal: controller.signal,
        immediate: prefersReducedMotion(),
        onEvent: dispatch,
        onText: (text) =>
          setMessages((m) => m.map((x) => (x.id === answerId ? { ...x, text } : x))),
      })
    } catch {
      // 사용자가 중단했다. 지금까지 받은 텍스트와 스테이지 상태를 그대로 둔다.
    } finally {
      setRunning(false)
      abortRef.current = null
    }
  }

  return (
    <aside className="flex h-svh min-h-0 flex-col border-r border-border bg-sidebar">
      <header className="flex items-center justify-between gap-2 px-5 pt-5 pb-3">
        <div className="flex flex-col">
          <span className="text-sm font-semibold tracking-[0.2em] uppercase">IssueDigest</span>
          <span className="text-xs text-muted-foreground">온톨로지 탐색 프로토타입</span>
        </div>
        <Badge variant="outline">샘플 데이터</Badge>
      </header>

      <MessageScrollerProvider>
        <MessageScroller className="flex-1">
          <MessageScrollerViewport className="px-5">
            <MessageScrollerContent className="py-4">
              {messages.length === 0 ? (
                <MessageScrollerItem className="flex flex-col gap-3 pt-6">
                  <p className="text-sm text-muted-foreground">
                    질문하면 오른쪽 스테이지에서 탐색 과정과 결과를 보여 줍니다.
                  </p>
                  <div className="flex flex-col items-start gap-2">
                    {SCENARIOS.map((s) => (
                      <Bubble key={s.id} variant="outline">
                        <BubbleContent render={<button type="button" />} onClick={() => ask(s.prompt)}>
                          {s.prompt}
                        </BubbleContent>
                      </Bubble>
                    ))}
                  </div>
                </MessageScrollerItem>
              ) : (
                messages.map((m, i) => (
                  <MessageScrollerItem key={m.id} scrollAnchor={i === messages.length - 1}>
                    <Message align={m.role === "user" ? "end" : "start"}>
                      <MessageContent>
                        <Bubble
                          variant={m.role === "user" ? "secondary" : "ghost"}
                          align={m.role === "user" ? "end" : "start"}
                        >
                          <BubbleContent>{m.text || "탐색 중…"}</BubbleContent>
                        </Bubble>
                      </MessageContent>
                    </Message>
                  </MessageScrollerItem>
                ))
              )}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      <form
        className="px-5 pt-2 pb-5"
        onSubmit={(e) => {
          e.preventDefault()
          void ask(draft)
        }}
      >
        <InputGroup>
          <InputGroupTextarea
            value={draft}
            placeholder="이슈에 대해 질문하세요"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                void ask(draft)
              }
            }}
          />
          <InputGroupAddon align="block-end" className="justify-end">
            {running ? (
              <InputGroupButton size="icon-xs" variant="secondary" onClick={() => abortRef.current?.abort()}>
                <SquareIcon />
                <span className="sr-only">중단</span>
              </InputGroupButton>
            ) : (
              <InputGroupButton type="submit" size="icon-xs" variant="default" disabled={!draft.trim()}>
                <ArrowUpIcon />
                <span className="sr-only">보내기</span>
              </InputGroupButton>
            )}
          </InputGroupAddon>
        </InputGroup>
      </form>
    </aside>
  )
}
