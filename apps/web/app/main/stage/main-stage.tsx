import { lazy, Suspense, useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "motion/react"

import { dataColor } from "~/design/palette"
import { EASE_OUT, type SchematicMode } from "~/design/tokens"
import { useReducedMotion } from "~/design/use-reduced-motion"
import { ACCENT, ACCENT_TEXT, ControlButton, INK, op, Rule, SchematicFrame, SquarePoint } from "~/stage/schematic/primitives"
import { useStage } from "~/stage/store"
import { useStageUi, type StageView } from "./ui-store"

// three.js 는 브라우저 전용이다. SPA 빌드가 라우트를 미리 렌더하므로 마운트 후에만 불러온다.
const StageScene = lazy(() => import("./stage-scene"))

const STATUS_LABEL = {
  idle: "대기",
  exploring: "탐색 중",
  answered: "탐색 완료",
  insufficient: "근거 부족",
} as const

const VIEW_LABEL: Record<StageView, string> = { overview: "전체", top: "위에서", low: "낮게" }

/**
 * 메인 화면 오른쪽 3D 스테이지와 화면 고정 주석.
 * 왼쪽 위 상태·제목, 오른쪽 위 보기 전환, 왼쪽 아래 범례·출처, 오른쪽 아래 가리킴·카메라 수치·조작 안내.
 */
export function MainStage({ mode }: { mode: SchematicMode }) {
  const reducedMotion = useReducedMotion()
  const [mounted, setMounted] = useState(false)
  const readout = useRef<HTMLSpanElement>(null)
  useEffect(() => setMounted(true), [])

  const status = useStage((s) => s.status)
  const note = useStage((s) => s.statusNote)
  const map = useStage((s) => s.map)
  const choropleth = useStage((s) => s.choropleth)
  const hasNodes = useStage((s) => s.nodes.length > 0)
  const focus = useStage((s) => s.focus)
  const setFocus = useStage((s) => s.setFocus)
  const hovered = useStageUi((s) => s.hovered)
  const view = useStageUi((s) => s.view)
  const requestView = useStageUi((s) => s.requestView)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setFocus(null)
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [setFocus])

  const exploring = status === "exploring"
  const title = map?.title ?? (hasNodes ? "온톨로지 탐색" : null)
  const empty = !map && !hasNodes && status !== "insufficient"

  return (
    <section className="relative min-w-0 overflow-hidden select-none" style={{ background: "var(--sch-backdrop)" }} aria-label="시각화 스테이지">
      <div className="absolute inset-0">
        {mounted ? (
          <Suspense fallback={null}>
            <StageScene mode={mode} readout={readout} reducedMotion={reducedMotion} />
          </Suspense>
        ) : null}
      </div>

      {/* 화면 고정 주석 뒤의 어두운 층: 지면 글자와 겹쳐도 읽히게 한다 */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10"
        style={{
          background: "linear-gradient(to bottom, var(--sch-backdrop) 0%, transparent 22%, transparent 74%, var(--sch-backdrop) 100%)",
          opacity: 0.85,
        }}
      />

      <div className="pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-6" style={{ color: INK }}>
        <div className="flex items-start justify-between gap-6">
          {/* 상태와 제목 */}
          <div className="flex w-[420px] flex-col gap-1.5">
            <div className="flex items-center gap-1 text-[10px] tracking-[0.22em]">
              <motion.span
                animate={exploring && !reducedMotion ? { opacity: [1, 0.3, 1] } : { opacity: 1 }}
                transition={exploring && !reducedMotion ? { duration: 1.2, repeat: Infinity } : { duration: 0 }}
              >
                <SquarePoint size={5} emphasized={exploring} filled={exploring} />
              </motion.span>
              <span style={{ color: exploring ? ACCENT_TEXT : INK, opacity: exploring ? 1 : op("related") }}>{STATUS_LABEL[status]}</span>
              {note && exploring ? <span style={{ opacity: op("related") }}>· {note}</span> : null}
            </div>
            <AnimatePresence mode="wait">
              {title ? (
                <motion.div
                  key={title}
                  className="flex flex-col gap-1.5"
                  initial={reducedMotion ? false : { opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: reducedMotion ? 0 : 0.5, ease: EASE_OUT }}
                >
                  <h2 className="text-[24px] leading-tight font-extralight tracking-[0.06em]" style={{ opacity: 0.92, textShadow: "0 1px 0 var(--sch-shadow)" }}>
                    {title}
                  </h2>
                  <Rule animate={!reducedMotion} />
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>

          {/* 보기 전환 */}
          {map || hasNodes ? (
            <div className="pointer-events-auto flex flex-col items-end gap-1">
              <span className="mb-1 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
                보기
              </span>
              {(Object.keys(VIEW_LABEL) as StageView[]).map((v) => (
                <ControlButton key={v} active={view.name === v} onClick={() => requestView(v)}>
                  {VIEW_LABEL[v]}
                </ControlButton>
              ))}
              {focus ? (
                <ControlButton active={false} onClick={() => setFocus(null)}>
                  선택 해제
                </ControlButton>
              ) : null}
            </div>
          ) : null}
        </div>

        {/* 가운데: 빈 상태 안내, 근거 부족 */}
        <div className="flex justify-center">
          <AnimatePresence>
            {status === "insufficient" ? (
              <motion.div key="insufficient" className="w-[360px]" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
                <SchematicFrame index={0} caption="상태" title="근거 부족" animate={!reducedMotion}>
                  <p className="text-[13px] font-light tracking-[0.02em]" style={{ opacity: op("related") }}>
                    {note}
                  </p>
                </SchematicFrame>
              </motion.div>
            ) : empty ? (
              <motion.p
                key="empty"
                className="font-mono text-[11px] tracking-[0.18em]"
                style={{ opacity: op("context") }}
                initial={{ opacity: 0 }}
                animate={{ opacity: op("context") }}
                exit={{ opacity: 0 }}
              >
                질문을 보내면 조사 과정이 이 바닥 위에 그려집니다
              </motion.p>
            ) : null}
          </AnimatePresence>
        </div>

        <div className="flex items-end justify-between gap-6">
          {/* 범례와 출처 */}
          <div className="flex flex-col gap-2">
            {choropleth ? (
              <>
                <span className="font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
                  범례 · 색 범주 · 높이 격차
                </span>
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] tracking-[0.08em]">
                  {choropleth.legend.map((l) => (
                    <span key={l.label} className="flex items-center gap-2">
                      <span className="size-2" style={{ background: dataColor(l.category) }} />
                      <span style={{ opacity: 0.88 }}>{l.label}</span>
                    </span>
                  ))}
                </div>
                <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.06em]" style={{ opacity: op("related") }}>
                  <span className="h-2.5 w-px" style={{ background: INK }} />
                  출처 {choropleth.source.label}
                  {choropleth.source.span ? ` · ${choropleth.source.span}` : ""}
                </span>
              </>
            ) : hasNodes ? (
              <>
                <span className="font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
                  범례 · 관계 근거
                </span>
                <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] tracking-[0.08em]">
                  <LegendLine label="명시된 관계" opacity={op("related")} />
                  <LegendLine label="추론한 관계" dashed opacity={op("related")} />
                  <LegendLine label="탐색 경로" opacity={1} />
                  <span className="flex items-center gap-2">
                    <span className="size-2" style={{ background: ACCENT }} />
                    <span style={{ opacity: 0.88 }}>초점</span>
                  </span>
                </div>
              </>
            ) : null}
          </div>

          {/* 가리킴과 카메라 */}
          <div className="flex flex-col items-end gap-1.5 font-mono text-[10px] tracking-[0.12em] tabular-nums">
            <span style={{ opacity: hovered ? 1 : 0, color: ACCENT_TEXT }}>{hovered ? `가리킴 ${hovered.label}` : " "}</span>
            <span ref={readout} style={{ opacity: map || hasNodes ? op("related") : 0 }} />
            <span style={{ opacity: op("context") }}>드래그 회전 · 오른쪽 드래그 이동 · 휠 확대 · 클릭 선택 · 배경 클릭·Esc 해제</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function LegendLine({ label, dashed, opacity }: { label: string; dashed?: boolean; opacity: number }) {
  return (
    <span className="flex items-center gap-2">
      <svg width="22" height="6" aria-hidden className="overflow-visible">
        <line x1="0" y1="3" x2="22" y2="3" style={{ stroke: INK }} strokeWidth={1} strokeDasharray={dashed ? "3 2" : undefined} opacity={opacity} />
      </svg>
      <span style={{ opacity: 0.88 }}>{label}</span>
    </span>
  )
}
