import { motion } from "motion/react"

import { EASE_OUT, MOTION } from "~/design/tokens"
import type { Panel } from "../events"
import { ACCENT, ACCENT_TEXT, INK, op, reveal, SchematicFrame } from "./primitives"

type ChartData = Extract<Panel, { kind: "chart" }>

const W = 320
const H = 150
const PAD = { left: 4, right: 64, top: 16, bottom: 24 }
const fmt = new Intl.NumberFormat("ko-KR", { notation: "compact", maximumFractionDigits: 1 })

/**
 * 도면 양식 선 차트.
 * 축 상자 없이 기준선과 짧은 눈금, 옅은 점선 격자, 오른쪽 끝 수치 주석으로 구성한다.
 * 계열은 흰색과 불투명도로 그리고, 강조할 첫 계열만 주황으로 그린다(세 번째 계열부터 점선).
 * 등장은 점 → 선 → 글자 순서다.
 */
function seriesStyle(i: number) {
  if (i === 0) return { color: ACCENT, opacity: 1, dash: undefined }
  if (i === 1) return { color: INK, opacity: op("related"), dash: undefined }
  return { color: INK, opacity: op("related"), dash: "3 3" }
}

export function SchematicChart({ panel, index, animate }: { panel: ChartData; index: number; animate: boolean }) {
  const s = (ms: number) => (animate ? ms / 1000 : 0)
  const values = panel.rows.flatMap((r) => panel.series.map((sr) => Number(r[sr.key])))
  const max = niceMax(Math.max(...values))
  const innerW = W - PAD.left - PAD.right
  const innerH = H - PAD.top - PAD.bottom
  const x = (i: number) => PAD.left + (panel.rows.length === 1 ? innerW / 2 : (i / (panel.rows.length - 1)) * innerW)
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH
  const ticks = [0, 0.5, 1].map((t) => t * max)

  // 끝 수치 라벨이 겹치지 않도록 세로 위치를 벌린다
  const ends = panel.series
    .map((sr) => ({ sr, v: Number(panel.rows.at(-1)![sr.key]) }))
    .sort((a, b) => b.v - a.v)
  let lastY = -Infinity
  const endY = new Map<string, number>()
  for (const e of ends) {
    const yy = Math.max(y(e.v), lastY + 27)
    endY.set(e.sr.key, yy)
    lastY = yy
  }

  return (
    <SchematicFrame index={index} caption={`차트 · 단위 ${panel.unit}`} title={panel.title} source={panel.source} animate={animate}>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full overflow-visible" role="img" aria-label={panel.title}>
        {/* 옅은 점선 격자와 눈금 수치 */}
        {ticks.map((t) => (
          <g key={t} opacity={op("context")}>
            <line
              x1={PAD.left}
              x2={W - PAD.right}
              y1={y(t)}
              y2={y(t)}
              stroke="currentColor"
              strokeDasharray="1 3"
              opacity={t === 0 ? 0 : 1}
            />
            <text x={W - PAD.right} y={y(t) - 3} textAnchor="end" className="fill-current font-mono text-[9px] tabular-nums">
              {t === 0 ? "" : fmt.format(t)}
            </text>
          </g>
        ))}

        {/* 기준선과 아래 눈금 */}
        <motion.line
          x1={PAD.left}
          x2={W - PAD.right + 8}
          y1={y(0)}
          y2={y(0)}
          stroke="currentColor"
          opacity={op("related")}
          initial={animate ? { pathLength: 0 } : false}
          animate={{ pathLength: 1 }}
          transition={{ duration: s(MOTION.line.duration), ease: EASE_OUT }}
        />
        {panel.rows.map((r, i) => (
          <g key={i} opacity={op("related")}>
            <line x1={x(i)} x2={x(i)} y1={y(0)} y2={y(0) + 4} stroke="currentColor" />
            <text x={x(i)} y={y(0) + 15} textAnchor="middle" className="fill-current font-mono text-[9px] tabular-nums">
              {String(r[panel.xKey])}
            </text>
          </g>
        ))}

        {/* 계열: 점 → 선 → 끝 수치 */}
        {panel.series.map((sr, si) => {
          const { color, opacity, dash } = seriesStyle(si)
          const pts = panel.rows.map((r, i) => [x(i), y(Number(r[sr.key]))] as const)
          const d = pts.map(([px, py], i) => `${i ? "L" : "M"}${px},${py}`).join(" ")
          const [lx, ly] = pts.at(-1)!
          const ey = endY.get(sr.key)!
          const value = Number(panel.rows.at(-1)![sr.key])
          return (
            <g key={sr.key}>
              <motion.path
                d={d}
                fill="none"
                style={{ stroke: color }}
                opacity={opacity}
                strokeDasharray={dash}
                strokeWidth={si === 0 ? 1.5 : 1}
                initial={animate ? { pathLength: 0 } : false}
                animate={{ pathLength: 1 }}
                transition={{ delay: s(reveal.line(si)), duration: s(MOTION.line.duration * 1.6), ease: EASE_OUT }}
              />
              {pts.map(([px, py], i) => (
                <motion.rect
                  key={i}
                  x={px - 2}
                  y={py - 2}
                  width={4}
                  height={4}
                  style={{ fill: i === pts.length - 1 ? color : "var(--sch-scene)", stroke: color }}
                  opacity={i === pts.length - 1 ? 1 : opacity}
                  strokeWidth={1}
                  shapeRendering="crispEdges"
                  initial={animate ? { opacity: 0 } : false}
                  animate={{ opacity: 1 }}
                  transition={{ delay: s(reveal.point(i + si)), duration: s(MOTION.point.duration) }}
                />
              ))}
              {/* 끝 수치 주석: 꺾인 지시선 + 수치 + 계열 이름 */}
              <motion.g
                initial={animate ? { opacity: 0 } : false}
                animate={{ opacity: 1 }}
                transition={{ delay: s(reveal.text(si)), duration: s(MOTION.text.duration) }}
              >
                <polyline
                  points={`${lx + 4},${ly} ${lx + 10},${ly} ${lx + 14},${ey} ${lx + 20},${ey}`}
                  fill="none"
                  stroke="currentColor"
                  opacity={op("context")}
                />
                <text x={lx + 24} y={ey + 1} className="text-[14px] font-light tabular-nums" style={{ fill: si === 0 ? ACCENT_TEXT : INK }}>
                  {fmt.format(value)}
                </text>
                <text x={lx + 24} y={ey + 12} className="text-[9px] tracking-[0.12em]" style={{ fill: INK }} opacity={op("related")}>
                  {sr.label}
                </text>
              </motion.g>
            </g>
          )
        })}
      </svg>
    </SchematicFrame>
  )
}

/** 최댓값보다 크거나 같은 가장 작은 「보기 좋은」 값(1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10 × 10^n) */
function niceMax(v: number) {
  const p = 10 ** Math.floor(Math.log10(v))
  const steps = [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
  return (steps.find((st) => st * p >= v) ?? 10) * p
}
