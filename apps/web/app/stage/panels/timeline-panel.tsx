import { motion } from "motion/react"

import type { Panel } from "../events"
import { useStage } from "../store"
import { PanelCard } from "./panel-card"

type TimelinePanelData = Extract<Panel, { kind: "timeline" }>

/** 처리 경과. 항목을 선택하면 해당 노드로 초점이 이동한다. 선택 표시는 무채색이다. */
export function TimelinePanel({ panel, animate }: { panel: TimelinePanelData; animate: boolean }) {
  const focus = useStage((s) => s.focus)
  const dispatch = useStage((s) => s.dispatch)

  return (
    <PanelCard eyebrow="타임라인" title={panel.title} source={panel.source}>
      <ol className="relative flex flex-col gap-2 pl-5">
        <motion.span
          aria-hidden
          className="absolute top-1.5 bottom-1.5 left-[5px] w-px origin-top bg-border"
          initial={animate ? { scaleY: 0 } : false}
          animate={{ scaleY: 1 }}
          transition={{ duration: 1.1, ease: [0.16, 1, 0.3, 1] }}
        />
        {panel.items.map((item, i) => {
          const active = focus?.kind === "node" && focus.id === item.nodeId
          return (
            <motion.li
              key={item.date + item.label}
              initial={animate ? { opacity: 0, x: 12 } : false}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: animate ? 0.25 + i * 0.12 : 0, duration: 0.5 }}
              className="relative"
            >
              <span
                aria-hidden
                className={
                  active
                    ? "absolute top-1.5 -left-5 size-[11px] rounded-full border-2 border-foreground bg-background"
                    : "absolute top-2 -left-[17px] size-[7px] rounded-full bg-muted-foreground"
                }
              />
              <button
                type="button"
                disabled={!item.nodeId}
                onClick={() => item.nodeId && dispatch({ type: "claim.focus", target: { kind: "node", id: item.nodeId } })}
                className="flex w-full flex-col items-start text-left outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <span className="font-mono text-[11px] text-muted-foreground tabular-nums">{item.date}</span>
                <span className={active ? "text-sm font-medium text-foreground" : "text-sm text-foreground/80"}>
                  {item.label}
                </span>
              </button>
            </motion.li>
          )
        })}
      </ol>
    </PanelCard>
  )
}
