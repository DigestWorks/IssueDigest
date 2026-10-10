import { AnimatePresence, motion } from "motion/react"

import { dataColor } from "~/design/palette"
import { GlyphIcon } from "../graph/glyph-icon"
import { NODE_TYPE_LABEL } from "../graph/glyphs"
import { useStage } from "../store"

const STATUS_LABEL = {
  idle: "대기",
  exploring: "탐색 중",
  answered: "탐색 완료",
  insufficient: "근거 부족",
} as const

/** 스테이지 위 고정 정보: 상태, 제목, 범례. 범례의 색만 데이터 색이다. */
export function StageHud() {
  const status = useStage((s) => s.status)
  const note = useStage((s) => s.statusNote)
  const nodes = useStage((s) => s.nodes)
  const map = useStage((s) => s.map)
  const choropleth = useStage((s) => s.choropleth)

  const types = [...new Set(nodes.map((n) => n.type))]
  const title = map?.title ?? (nodes.length ? "온톨로지 탐색" : null)

  return (
    <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-6">
      <div className="flex flex-col gap-1">
        <div className="flex items-center gap-2 text-xs tracking-[0.08em] text-muted-foreground">
          <span
            className={
              status === "exploring"
                ? "size-1.5 animate-pulse rounded-full bg-foreground"
                : "size-1.5 rounded-full bg-muted-foreground"
            }
          />
          {STATUS_LABEL[status]}
          {note && status === "exploring" ? <span>· {note}</span> : null}
        </div>
        <AnimatePresence mode="wait">
          {title ? (
            <motion.h2
              key={title}
              initial={{ opacity: 0, y: 8, filter: "blur(6px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -8, filter: "blur(6px)" }}
              transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
              className="text-2xl font-light tracking-[0.08em] text-foreground"
            >
              {title}
            </motion.h2>
          ) : null}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {status === "insufficient" ? (
          <motion.div
            key="insufficient"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            className="self-center rounded-xl border border-border bg-background/70 px-6 py-4 text-center backdrop-blur-md"
          >
            <p className="text-sm font-medium tracking-[0.2em] uppercase">근거 부족</p>
            <p className="mt-1 text-sm text-muted-foreground">{note}</p>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
        {choropleth
          ? choropleth.legend.map((l) => (
              <LegendItem key={l.label} color={dataColor(l.category)} label={l.label} />
            ))
          : types.map((t) => (
              <span key={t} className="flex items-center gap-1.5">
                <GlyphIcon type={t} />
                {NODE_TYPE_LABEL[t]}
              </span>
            ))}
      </div>
    </div>
  )
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  )
}

