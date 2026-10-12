import { motion } from "motion/react"

import { EASE_OUT, MOTION } from "~/design/tokens"
import type { Panel } from "../events"
import { useStage } from "../store"
import { ACCENT, ACCENT_TEXT, INK, op, reveal, SchematicFrame, SquarePoint } from "./primitives"

type TimelineData = Extract<Panel, { kind: "timeline" }>

/**
 * 도면 양식 타임라인. 세로 축선 위에 사각점을 두고, 꺾인 지시선으로 날짜와 항목을 잇는다.
 * 항목을 선택하면 그 기록으로 스테이지 초점이 옮겨지고, 사각점에 꺾쇠 눈금이 붙는다.
 */
export function SchematicTimeline({ panel, index, animate }: { panel: TimelineData; index: number; animate: boolean }) {
  const focus = useStage((s) => s.focus)
  const dispatch = useStage((s) => s.dispatch)
  const s = (ms: number) => (animate ? ms / 1000 : 0)

  return (
    <SchematicFrame index={index} caption="타임라인" title={panel.title} source={panel.source} animate={animate}>
      <ol className="relative flex flex-col">
        {/* 축선 */}
        <motion.span
          aria-hidden
          className="absolute top-2 bottom-2 left-[8px] w-px origin-top"
          style={{ background: INK, opacity: op("context") }}
          initial={animate ? { scaleY: 0 } : false}
          animate={{ scaleY: 1 }}
          transition={{ delay: s(reveal.line()), duration: s(MOTION.line.duration * 1.5), ease: EASE_OUT }}
        />
        {panel.items.map((item, i) => {
          const active = focus?.kind === "node" && focus.id === item.nodeId
          return (
            <li key={item.date + item.label} className="relative">
              <button
                type="button"
                disabled={!item.nodeId}
                onClick={() => item.nodeId && dispatch({ type: "claim.focus", target: { kind: "node", id: item.nodeId } })}
                className="group grid w-full grid-cols-[17px_18px_1fr] items-center py-1.5 text-left outline-none"
              >
                <motion.span
                  className="flex justify-center"
                  initial={animate ? { opacity: 0, scale: 0.4 } : false}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: s(reveal.point(i)), duration: s(MOTION.point.duration) }}
                >
                  <SquarePoint size={5} filled={false} emphasized={active} />
                </motion.span>
                {/* 지시선 */}
                <motion.span
                  aria-hidden
                  className="h-px origin-left"
                  style={{ background: active ? ACCENT : INK, opacity: active ? 1 : op("context") }}
                  initial={animate ? { scaleX: 0 } : false}
                  animate={{ scaleX: 1 }}
                  transition={{ delay: s(reveal.line(i + 1)), duration: s(MOTION.line.duration), ease: EASE_OUT }}
                />
                <motion.span
                  className="flex items-baseline gap-3 pl-1.5"
                  initial={animate ? { opacity: 0 } : false}
                  animate={{ opacity: 1 }}
                  transition={{ delay: s(reveal.text(i)), duration: s(MOTION.text.duration) }}
                >
                  <span className="font-mono text-[10px] tracking-[0.04em] tabular-nums" style={{ color: active ? ACCENT_TEXT : INK, opacity: active ? 1 : op("related") }}>
                    {item.date}
                  </span>
                  <span
                    className="text-[13px] tracking-[0.02em] group-hover:opacity-100"
                    style={{ opacity: active ? 0.88 : op("related"), fontWeight: active ? 500 : 300 }}
                  >
                    {item.label}
                  </span>
                </motion.span>
              </button>
            </li>
          )
        })}
      </ol>
    </SchematicFrame>
  )
}
