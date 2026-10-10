import { motion } from "motion/react"

import { dataColor } from "~/design/palette"
import type { Panel } from "../events"
import { useStage } from "../store"
import { PanelCard } from "./panel-card"

type ClaimsPanelData = Extract<Panel, { kind: "claims" }>

/**
 * 주장 비교. 입장(범주)은 데이터이므로 색을 쓴다. 주장을 선택하면 스테이지
 * 초점이 근거 노드나 지역으로 이동한다. 각 주장에 출처와 인용 위치를 붙인다.
 */
export function ClaimsPanel({ panel, animate }: { panel: ClaimsPanelData; animate: boolean }) {
  const focus = useStage((s) => s.focus)
  const dispatch = useStage((s) => s.dispatch)

  return (
    <PanelCard eyebrow="주장 비교" title={panel.title}>
      <div className="grid grid-cols-2 gap-3">
        {panel.sides.map((side, si) => (
          <div key={side.label} className="flex min-w-0 flex-col gap-2">
            <div className="flex items-center gap-1.5 text-xs font-medium">
              <span className="size-2 rounded-full" style={{ backgroundColor: dataColor(side.category) }} />
              {side.label}
            </div>
            {side.claims.map((c, ci) => {
              const active = focus?.kind === c.target.kind && focus.id === c.target.id
              return (
                <motion.button
                  key={c.id}
                  type="button"
                  initial={animate ? { opacity: 0, y: 10, filter: "blur(4px)" } : false}
                  animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
                  transition={{ delay: animate ? 0.3 + si * 0.15 + ci * 0.12 : 0, duration: 0.5 }}
                  onClick={() => dispatch({ type: "claim.focus", target: c.target })}
                  className={
                    active
                      ? "flex flex-col gap-1 rounded-lg border border-foreground/60 bg-foreground/10 p-2.5 text-left outline-none"
                      : "flex flex-col gap-1 rounded-lg border border-border bg-background/40 p-2.5 text-left outline-none hover:bg-foreground/5 focus-visible:ring-2 focus-visible:ring-ring"
                  }
                  style={{ borderLeftColor: dataColor(side.category), borderLeftWidth: 2 }}
                >
                  <span className="text-[13px] leading-snug">{c.text}</span>
                  <span className="truncate text-[11px] text-muted-foreground">
                    {c.source.label}
                    {c.source.span ? ` · ${c.source.span}` : ""}
                  </span>
                </motion.button>
              )
            })}
          </div>
        ))}
      </div>
    </PanelCard>
  )
}
