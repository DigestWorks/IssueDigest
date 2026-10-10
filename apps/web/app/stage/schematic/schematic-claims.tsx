import { motion } from "motion/react"

import { EASE_OUT, MOTION } from "~/design/tokens"
import type { Panel } from "../events"
import { useStage } from "../store"
import { ACCENT, INK, op, reveal, SchematicFrame, SquarePoint } from "./primitives"

type ClaimsData = Extract<Panel, { kind: "claims" }>

/**
 * 도면 양식 주장 비교.
 * 입장 머리는 짧은 굵은 막대로 표시한다. 첫 입장은 주황, 둘째 입장은 흰색이다.
 * 주장마다 근거 사각점과 꺾인 지시선으로 인용 위치를 잇는다.
 * 주장을 선택하면 스테이지 초점이 근거 기록으로 옮겨진다.
 */
export function SchematicClaims({ panel, index, animate }: { panel: ClaimsData; index: number; animate: boolean }) {
  const focus = useStage((s) => s.focus)
  const dispatch = useStage((s) => s.dispatch)
  const s = (ms: number) => (animate ? ms / 1000 : 0)
  let order = 0

  return (
    <SchematicFrame index={index} caption="주장 비교" title={panel.title} animate={animate}>
      <div className="grid grid-cols-2 gap-x-5">
        {panel.sides.map((side, si) => (
          <div key={side.label} className="flex min-w-0 flex-col">
            {/* 입장 머리: 데이터 색 막대 + 이름 + 개수 */}
            <div className="flex flex-col gap-1.5 pb-2">
              <motion.span
                className="h-[3px] w-5 origin-left"
                style={{ background: si === 0 ? ACCENT : INK, opacity: si === 0 ? 1 : op("related") }}
                initial={animate ? { scaleX: 0 } : false}
                animate={{ scaleX: 1 }}
                transition={{ delay: s(reveal.line(si)), duration: s(MOTION.line.duration), ease: EASE_OUT }}
              />
              <div className="flex items-baseline justify-between">
                <span className="text-[12px] font-normal tracking-[0.12em]">{side.label}</span>
                <span className="font-mono text-[10px] tabular-nums" style={{ opacity: op("related") }}>
                  {String(side.claims.length).padStart(2, "0")}
                </span>
              </div>
            </div>

            <ul className="relative flex flex-col">
              {/* 주장 묶음 세로선 */}
              <span aria-hidden className="absolute top-1 bottom-3 left-[8px] w-px" style={{ background: INK, opacity: op("context") }} />
              {side.claims.map((c) => {
                const i = order++
                const active = focus?.kind === c.target.kind && focus.id === c.target.id
                return (
                  <li key={c.id}>
                    <button
                      type="button"
                      onClick={() => dispatch({ type: "claim.focus", target: c.target })}
                      className="group grid w-full grid-cols-[17px_1fr] gap-x-1.5 py-1.5 text-left outline-none"
                    >
                      <motion.span
                        className="flex justify-center pt-[3px]"
                        initial={animate ? { opacity: 0 } : false}
                        animate={{ opacity: 1 }}
                        transition={{ delay: s(reveal.point(i)), duration: s(MOTION.point.duration) }}
                      >
                        <SquarePoint size={5} filled={false} emphasized={active} />
                      </motion.span>
                      <motion.span
                        className="flex min-w-0 flex-col gap-1"
                        initial={animate ? { opacity: 0, x: 4 } : false}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: s(reveal.text(i)), duration: s(MOTION.text.duration * 2) }}
                      >
                        <span
                          className="text-[13px] leading-snug tracking-[0.02em] group-hover:opacity-100"
                          style={{ opacity: active ? 0.88 : op("related"), fontWeight: active ? 500 : 300 }}
                        >
                          {c.text}
                        </span>
                        {/* 인용 위치: 꺾인 지시선 */}
                        <span className="flex items-center gap-1.5 font-mono text-[10px]" style={{ opacity: op("related") }}>
                          <span aria-hidden className="h-2 w-2 border-b border-l" style={{ borderColor: active ? ACCENT : INK }} />
                          <span className="truncate">
                            {c.source.label}
                            {c.source.span ? ` · ${c.source.span}` : ""}
                          </span>
                        </span>
                      </motion.span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </div>
    </SchematicFrame>
  )
}
