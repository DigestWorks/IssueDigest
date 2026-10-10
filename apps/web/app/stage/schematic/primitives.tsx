import type { CSSProperties, ReactNode } from "react"
import { motion } from "motion/react"

import { EASE_OUT, MOTION, OPACITY, schematicVars } from "~/design/tokens"

/**
 * 도면 양식 패널의 기본 요소(The Division UI 스타일 가이드 양식).
 * - 닫힌 상자 대신 가는 선(1px), 틀 밖으로 연장되는 보조선, L자 꺾쇠, 작은 사각점으로 틀을 만든다.
 * - 글자는 따뜻한 흰색, 강조는 주황(--sch-accent) 하나만 쓴다.
 * - 선과 글자의 위계는 OPACITY 네 단계로 만든다.
 * 색 값은 SchematicTheme 이 CSS 변수로 내려준다.
 */

export const op = (step: keyof typeof OPACITY) => OPACITY[step].value
export const INK = "var(--sch-ink)"
export const ACCENT = "var(--sch-accent)"
const sec = (ms: number, animate: boolean) => (animate ? ms / 1000 : 0)

/** 등장 시각(ms). 점 → 선 → 글자 순서를 패널 안에서 맞춘다. */
export const reveal = {
  point: (i = 0) => MOTION.stagger.duration * i,
  line: (i = 0) => MOTION.point.duration + MOTION.stagger.duration * i,
  text: (i = 0) => MOTION.point.duration + MOTION.line.duration + MOTION.stagger.duration * i,
}

/** 테마 변수를 내려주는 감싸개 */
export function SchematicTheme({ children, className, style }: { children: ReactNode; className?: string; style?: CSSProperties }) {
  return (
    <div className={className} style={{ ...schematicVars, color: INK, ...style }}>
      {children}
    </div>
  )
}

/** 작은 정사각형 점. emphasized 이면 주황으로 채우고 상하좌우에 꺾쇠 눈금을 붙인다. */
export function SquarePoint({
  size = 5,
  filled = true,
  emphasized = false,
  color,
}: {
  size?: number
  filled?: boolean
  emphasized?: boolean
  color?: string
}) {
  const c = emphasized ? ACCENT : (color ?? INK)
  const pad = 6
  const box = size + pad * 2
  const m = box / 2
  return (
    <svg width={box} height={box} viewBox={`0 0 ${box} ${box}`} aria-hidden className="shrink-0 overflow-visible">
      <rect
        x={pad}
        y={pad}
        width={size}
        height={size}
        style={{ fill: filled || emphasized ? c : "var(--sch-scene)", stroke: c }}
        strokeWidth={filled || emphasized ? 0 : 1}
        shapeRendering="crispEdges"
      />
      {emphasized ? (
        <g style={{ stroke: c }} strokeWidth={1} shapeRendering="crispEdges">
          <line x1={m} y1={0} x2={m} y2={3} />
          <line x1={m} y1={box - 3} x2={m} y2={box} />
          <line x1={0} y1={m} x2={3} y2={m} />
          <line x1={box - 3} y1={m} x2={box} y2={m} />
        </g>
      ) : null}
    </svg>
  )
}

/** 1px 가로선. 왼쪽 끝에 주황 시작점을 둔다. 왼쪽에서 오른쪽으로 그려지며 나타난다. */
export function Rule({ animate, delay = 0 }: { animate: boolean; delay?: number }) {
  return (
    <div className="relative flex items-center">
      <span className="absolute -left-[2px] size-[4px]" style={{ background: ACCENT }} />
      <motion.span
        className="h-px flex-1 origin-left"
        style={{ background: INK, opacity: op("context") }}
        initial={animate ? { scaleX: 0 } : false}
        animate={{ scaleX: 1 }}
        transition={{ delay: sec(delay, animate), duration: sec(MOTION.line.duration, animate), ease: EASE_OUT }}
      />
    </div>
  )
}

const lineStyle = (step: keyof typeof OPACITY): CSSProperties => ({ background: INK, opacity: op(step) })

/**
 * 패널 틀.
 * - 위쪽 보조선은 틀 양옆으로 연장되고 오른쪽 끝에 작은 사각점이 있다.
 * - 왼쪽 세로선과 아래 짧은 가로선이 L자 꺾쇠를 이룬다. 왼쪽 위 모서리는 주황 사각점이다.
 * - 바탕은 어두운 반투명 면(흐림 처리)이고 모서리는 직각이다.
 * - 머리: 고정폭 번호 | 보조 글자, 가는 굵기의 제목(그림자 층), 주황 시작점이 있는 머리선.
 *   같은 번호를 크고 아주 옅게 깔아 잔상 층을 만든다.
 */
export function SchematicFrame({
  index,
  caption,
  title,
  source,
  animate,
  children,
}: {
  index: number
  caption: string
  title: string
  source?: { label: string; span?: string }
  animate: boolean
  children: ReactNode
}) {
  const indexText = String(index).padStart(2, "0")
  const grow = (axis: "x" | "y", delay: number) => ({
    initial: animate ? (axis === "x" ? { scaleX: 0 } : { scaleY: 0 }) : false,
    animate: axis === "x" ? { scaleX: 1 } : { scaleY: 1 },
    transition: { delay: sec(delay, animate), duration: sec(MOTION.line.duration, animate), ease: EASE_OUT },
  })

  return (
    <section className="relative px-5 pt-4 pb-4" style={{ color: INK }}>
      <div className="absolute inset-0 backdrop-blur-[8px]" style={{ background: "var(--sch-backing)" }} aria-hidden />

      {/* 위쪽 보조선: 양옆으로 연장, 오른쪽 끝 사각점 */}
      <motion.span aria-hidden className="absolute top-0 -right-10 -left-4 h-px origin-left" style={lineStyle("context")} {...grow("x", 0)} />
      <span aria-hidden className="absolute -top-[1.5px] -right-10 size-[4px]" style={{ background: INK, opacity: op("context") }} />
      {/* L자 꺾쇠 */}
      <motion.span aria-hidden className="absolute top-0 bottom-0 left-0 w-px origin-top" style={lineStyle("related")} {...grow("y", reveal.line())} />
      <motion.span aria-hidden className="absolute bottom-0 left-0 h-px w-16 origin-left" style={lineStyle("related")} {...grow("x", reveal.line(2))} />
      {/* 모서리 사각점 */}
      <span aria-hidden className="absolute -top-[2px] -left-[2px] size-[5px]" style={{ background: ACCENT }} />
      <span aria-hidden className="absolute -bottom-[1.5px] left-16 size-[3px]" style={{ background: INK, opacity: op("related") }} />

      <div className="relative flex flex-col gap-3">
        <header className="relative flex flex-col gap-1.5">
          <span
            aria-hidden
            className="pointer-events-none absolute -top-3 right-0 text-[52px] leading-none font-extralight tracking-[-0.02em] tabular-nums select-none"
            style={{ opacity: op("faint") }}
          >
            {indexText}
          </span>
          <div className="flex items-center gap-2 text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
            <span className="font-mono tabular-nums">{indexText}</span>
            <span className="h-2.5 w-px" style={{ background: INK }} />
            <span>{caption}</span>
          </div>
          <motion.h3
            className="text-[19px] leading-tight font-extralight tracking-[0.06em]"
            style={{ textShadow: "0 1px 0 var(--sch-shadow)" }}
            initial={animate ? { opacity: 0, x: -6 } : false}
            animate={{ opacity: 0.88, x: 0 }}
            transition={{ delay: sec(reveal.text(), animate), duration: sec(MOTION.text.duration * 2, animate) }}
          >
            {title}
          </motion.h3>
          <Rule animate={animate} delay={reveal.line(1)} />
        </header>

        {children}

        {source ? (
          <motion.footer
            className="flex items-center gap-2 font-mono text-[10px] tracking-[0.06em]"
            initial={animate ? { opacity: 0 } : false}
            animate={{ opacity: op("related") }}
            transition={{ delay: sec(reveal.text(6), animate), duration: sec(MOTION.text.duration, animate) }}
          >
            <span className="h-2.5 w-px" style={{ background: INK }} />
            <span>출처</span>
            <span>{source.label}</span>
            {source.span ? <span>· {source.span}</span> : null}
          </motion.footer>
        ) : null}
      </div>
    </section>
  )
}
