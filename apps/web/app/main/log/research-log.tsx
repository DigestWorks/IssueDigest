import { useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import { motion } from "motion/react"

import { EASE_OUT, type SchematicMode } from "~/design/tokens"
import { useReducedMotion } from "~/design/use-reduced-motion"
import { SCENARIOS } from "~/stage/scenarios"
import { ACCENT_TEXT, ControlButton, INK, op, Rule, SquarePoint } from "~/stage/schematic/primitives"
import { useStage, type TrailStep } from "~/stage/store"
import { stageSources, useConversation, type Turn, type TurnStatus } from "./use-conversation"

const STATUS_LABEL: Record<TurnStatus, string> = {
  exploring: "탐색 중",
  answered: "탐색 완료",
  insufficient: "근거 부족",
  stopped: "중단",
}

const pad = (n: number) => String(n).padStart(2, "0")
const hairline = `color-mix(in oklab, ${INK} 11%, transparent)`

/** 고정폭 머리 줄: 「이름 | 값」 */
function Caption({ name, value, accent }: { name: string; value: ReactNode; accent?: boolean }) {
  return (
    <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
      <span>{name}</span>
      <span className="h-2.5 w-px" style={{ background: INK }} />
      <span style={accent ? { color: ACCENT_TEXT, opacity: 1 } : undefined}>{value}</span>
    </div>
  )
}

/**
 * 메인 화면 왼쪽 대화 열: 「조사 기록」.
 * 질문마다 질문, 흘러나오는 답, 번호 붙은 탐색 단계, 출처를 쌓는다. 빈 상태에는 제안 질문을 보여 준다.
 * 진행 중인 질문의 탐색 단계를 선택하면 스테이지 초점이 그 대상으로 옮겨진다.
 */
export function ResearchLog({ mode, onMode }: { mode: SchematicMode; onMode: (m: SchematicMode) => void }) {
  const reducedMotion = useReducedMotion()
  const { turns, ask } = useConversation(reducedMotion)
  const [draft, setDraft] = useState("")
  const scroller = useRef<HTMLDivElement>(null)

  const trail = useStage((s) => s.trail)
  const nodes = useStage((s) => s.nodes)
  const choropleth = useStage((s) => s.choropleth)
  const panels = useStage((s) => s.panels)
  const focus = useStage((s) => s.focus)
  const setFocus = useStage((s) => s.setFocus)
  const liveSources = useMemo(() => stageSources(useStage.getState()), [nodes, choropleth, panels])

  const latest = turns.at(-1)
  useEffect(() => {
    const el = scroller.current
    if (el) el.scrollTop = el.scrollHeight
  }, [turns, trail.length])

  const send = (q: string) => {
    void ask(q)
    setDraft("")
  }

  return (
    <aside className="flex h-svh min-w-0 flex-col border-r" style={{ borderColor: hairline, color: INK }} aria-label="조사 기록">
      {/* 머리 */}
      <header className="flex flex-col gap-3 px-6 pt-6 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-[11px] tracking-[0.32em]">ISSUEDIGEST</span>
            <span className="text-[12px] tracking-[0.06em]" style={{ opacity: op("related") }}>
              출처가 붙은 조사 기록
            </span>
          </div>
          <div className="flex items-center gap-3">
            {(["dark", "light"] as const).map((m) => (
              <ControlButton key={m} active={mode === m} onClick={() => onMode(m)} point="start">
                {m === "dark" ? "다크" : "라이트"}
              </ControlButton>
            ))}
          </div>
        </div>
        <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.18em]" style={{ opacity: op("context") }}>
          <span className="h-2.5 w-px" style={{ background: INK }} />
          샘플 데이터 · 실제 에이전트 연결 전
        </span>
      </header>

      {/* 기록 */}
      <div ref={scroller} className="flex min-h-0 flex-1 flex-col gap-10 overflow-y-auto px-6 py-6" style={{ scrollbarWidth: "thin" }}>
        {turns.length === 0 ? (
          <section className="flex flex-col gap-4">
            <Caption name="제안 질문" value={pad(SCENARIOS.length)} />
            <div className="flex flex-col items-start gap-2">
              {SCENARIOS.map((s) => (
                <ControlButton key={s.id} active={false} onClick={() => send(s.prompt)} point="start">
                  {s.prompt}
                </ControlButton>
              ))}
            </div>
          </section>
        ) : null}

        {turns.map((t, i) => {
          const live = t === latest && !t.snapshot
          const steps = live ? trail : (t.snapshot?.trail ?? [])
          const sources = live ? liveSources : (t.snapshot?.sources ?? [])
          return (
            <TurnEntry
              key={t.id}
              turn={t}
              index={i + 1}
              steps={steps}
              sources={sources}
              live={live}
              focus={live ? focus : null}
              onStep={(s) => setFocus({ kind: s.kind, id: s.id })}
              reducedMotion={reducedMotion}
            />
          )
        })}
      </div>

      {/* 입력 */}
      <form
        className="flex flex-col gap-3 border-t px-6 pt-4 pb-6"
        style={{ borderColor: hairline }}
        onSubmit={(e) => {
          e.preventDefault()
          send(draft)
        }}
      >
        <Caption name="질문" value={pad(turns.length + 1)} />
        <div className="flex items-end gap-3">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="이슈에 대해 질문하세요"
            aria-label="질문 입력"
            className="min-w-0 flex-1 border-b bg-transparent pb-1.5 text-[14px] tracking-[0.02em] outline-none placeholder:opacity-40 focus:border-[var(--sch-accent)]"
            style={{ borderColor: `color-mix(in oklab, ${INK} 33%, transparent)`, color: INK }}
          />
          <ControlButton active={false} onClick={() => send(draft)}>
            보내기
          </ControlButton>
        </div>
        {turns.length > 0 ? (
          <div className="flex flex-wrap gap-x-4 gap-y-1">
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => send(s.prompt)}
                className="text-left text-[11px] tracking-[0.04em] hover:opacity-100"
                style={{ opacity: op("context") }}
              >
                {s.prompt}
              </button>
            ))}
          </div>
        ) : null}
      </form>
    </aside>
  )
}

function TurnEntry({
  turn,
  index,
  steps,
  sources,
  live,
  focus,
  onStep,
  reducedMotion,
}: {
  turn: Turn
  index: number
  steps: TrailStep[]
  sources: string[]
  live: boolean
  focus: { kind: "node" | "region"; id: string } | null
  onStep: (s: TrailStep) => void
  reducedMotion: boolean
}) {
  return (
    <motion.article
      className="flex flex-col gap-4"
      initial={reducedMotion ? false : { opacity: 0, x: -6 }}
      animate={{ opacity: live ? 1 : 0.72, x: 0 }}
      transition={{ duration: reducedMotion ? 0 : 0.4, ease: EASE_OUT }}
    >
      <div className="flex flex-col gap-1.5">
        <Caption name="질문" value={pad(index)} />
        <p className="text-[17px] leading-snug font-light tracking-[0.02em]">{turn.question}</p>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-1">
          <SquarePoint size={5} filled={turn.status !== "exploring"} emphasized={turn.status === "exploring"} />
          <Caption name="답" value={STATUS_LABEL[turn.status]} accent={turn.status === "exploring"} />
        </div>
        <Rule animate={false} />
        <p className="text-[13.5px] leading-relaxed tracking-[0.01em]" style={{ opacity: 0.88 }}>
          {turn.answer || " "}
        </p>
      </div>

      {steps.length ? (
        <div className="flex flex-col gap-2">
          <Caption name="탐색 단계" value={pad(steps.length)} />
          <ol className="flex flex-col">
            {steps.map((s, i) => {
              const active = focus?.kind === s.kind && focus.id === s.id
              return (
                <li key={`${s.kind}:${s.id}`}>
                  <button
                    type="button"
                    disabled={!live}
                    onClick={() => onStep(s)}
                    className="group grid w-full grid-cols-[24px_20px_1fr_auto] items-center py-1 text-left disabled:cursor-default"
                  >
                    <span className="font-mono text-[10px] tabular-nums" style={{ color: active ? ACCENT_TEXT : INK, opacity: active ? 1 : op("related") }}>
                      {pad(i + 1)}
                    </span>
                    <SquarePoint size={5} filled={false} emphasized={active} />
                    <span className="truncate text-[12.5px] tracking-[0.02em] group-enabled:group-hover:opacity-100" style={{ opacity: active ? 1 : 0.8, fontWeight: active ? 500 : 400 }}>
                      {s.label}
                    </span>
                    <span className="font-mono text-[10px] tracking-[0.12em]" style={{ opacity: op("context") }}>
                      {s.kind === "node" ? "노드" : "지역"}
                    </span>
                  </button>
                </li>
              )
            })}
          </ol>
        </div>
      ) : null}

      {sources.length ? (
        <div className="flex flex-col gap-1.5">
          <Caption name="출처" value={pad(sources.length)} />
          <ul className="flex flex-col gap-0.5 border-l pl-2.5" style={{ borderColor: `color-mix(in oklab, ${INK} 33%, transparent)` }}>
            {sources.slice(0, 8).map((s) => (
              <li key={s} className="font-mono text-[10.5px] leading-snug tracking-[0.02em]" style={{ opacity: op("related") }}>
                {s}
              </li>
            ))}
            {sources.length > 8 ? (
              <li className="font-mono text-[10.5px]" style={{ opacity: op("context") }}>
                외 {sources.length - 8}건
              </li>
            ) : null}
          </ul>
        </div>
      ) : null}
    </motion.article>
  )
}
