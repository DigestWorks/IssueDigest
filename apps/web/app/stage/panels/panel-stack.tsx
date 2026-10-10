import { AnimatePresence, motion } from "motion/react"

import { useReducedMotion } from "~/design/use-reduced-motion"
import type { Panel } from "../events"
import { useStage } from "../store"
import { ChartPanel } from "./chart-panel"
import { ClaimsPanel } from "./claims-panel"
import { TimelinePanel } from "./timeline-panel"

/**
 * 결과 패널. 3D 장면 위에 원근(perspective)을 준 층으로 쌓는다.
 * 패널은 DOM 이라 수치와 글자를 선명하게 읽을 수 있고, 등장할 때는
 * 깊이 방향에서 회전하며 들어온다.
 */
export function PanelStack() {
  const panels = useStage((s) => s.panels)
  const reduced = useReducedMotion()

  return (
    <div
      className="pointer-events-none absolute top-20 right-6 bottom-16 flex w-[min(380px,34%)] flex-col gap-3 overflow-y-auto"
      style={{ perspective: 1400 }}
    >
      <AnimatePresence>
        {panels.map(({ id, panel }, i) => (
          <motion.div
            key={id}
            className="pointer-events-auto origin-right"
            initial={
              reduced
                ? { opacity: 0 }
                : { opacity: 0, x: 60, rotateY: -28, z: -160, filter: "blur(10px)" }
            }
            animate={{ opacity: 1, x: 0, rotateY: -6, z: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, x: 40, filter: "blur(8px)" }}
            transition={{ duration: reduced ? 0 : 0.9, delay: reduced ? 0 : i * 0.05, ease: [0.16, 1, 0.3, 1] }}
            style={{ transformStyle: "preserve-3d" }}
          >
            <PanelBody panel={panel} animate={!reduced} />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

function PanelBody({ panel, animate }: { panel: Panel; animate: boolean }) {
  switch (panel.kind) {
    case "chart":
      return <ChartPanel panel={panel} animate={animate} />
    case "timeline":
      return <TimelinePanel panel={panel} animate={animate} />
    case "claims":
      return <ClaimsPanel panel={panel} animate={animate} />
  }
}
