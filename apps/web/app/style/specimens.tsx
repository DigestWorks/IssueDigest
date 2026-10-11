import { useEffect, useState } from "react"
import { motion } from "motion/react"

import { Button } from "~/components/ui/button"
import { DATA_CATEGORICAL, dataColor, oklchToHex } from "~/design/palette"
import { EASE_OUT, MAX_TEXT_TILT_DEG, MOTION, OPACITY, SCHEMATIC_THEME, TYPE_ROLES } from "~/design/tokens"
import { useReducedMotion } from "~/design/use-reduced-motion"
import { GlyphIcon } from "~/stage/graph/glyph-icon"
import type { Panel } from "~/stage/events"
import { NODE_GLYPH, NODE_TYPE_LABEL, NODE_TYPES } from "~/stage/graph/glyphs"
import { SchematicTheme } from "~/stage/schematic/primitives"
import { SchematicMap, type SchematicMapProps } from "~/stage/schematic/map/schematic-map"
import { SchematicPanel } from "~/stage/schematic/schematic-panel"
import { useStage } from "~/stage/store"

/** UI 색 토큰. 값은 실행 중인 app.css 에서 읽는다. */
const UI_TOKENS = [
  "background",
  "foreground",
  "card",
  "muted",
  "muted-foreground",
  "border",
  "primary",
  "secondary",
  "ring",
] as const

export function UiColorSpecimen() {
  const [values, setValues] = useState<Record<string, string>>({})
  useEffect(() => {
    const css = getComputedStyle(document.documentElement)
    setValues(Object.fromEntries(UI_TOKENS.map((t) => [t, css.getPropertyValue(`--${t}`).trim()])))
  }, [])
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-5 lg:grid-cols-9">
      {UI_TOKENS.map((t) => (
        <div key={t} className="flex flex-col gap-1.5">
          <div className="h-14 rounded-md border border-border" style={{ background: `var(--${t})` }} />
          <span className="text-xs font-medium">{t}</span>
          <span className="font-mono text-[11px] text-muted-foreground">{values[t] ?? ""}</span>
        </div>
      ))}
    </div>
  )
}

export function DataPaletteSpecimen() {
  return (
    <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
      {DATA_CATEGORICAL.map((c, i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <div className="h-14 rounded-md" style={{ background: dataColor(i) }} />
          <span className="text-xs font-medium">data-cat-{i + 1}</span>
          <span className="font-mono text-[11px] text-muted-foreground">
            oklch({c.join(" ")}) · {oklchToHex(c)}
          </span>
        </div>
      ))}
    </div>
  )
}

export function OpacitySpecimen() {
  return (
    <div className="flex flex-col gap-3">
      {Object.entries(OPACITY).map(([key, o]) => (
        <div key={key} className="grid grid-cols-[88px_1fr_minmax(0,2fr)] items-center gap-4">
          <span className="font-mono text-xs tabular-nums">{Math.round(o.value * 100)}%</span>
          <div className="flex items-center gap-3">
            <span className="size-3 rounded-full bg-foreground" style={{ opacity: o.value }} />
            <span className="h-px flex-1 bg-foreground" style={{ opacity: o.value }} />
            <span className="text-sm font-medium" style={{ opacity: o.value }}>
              {o.label}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">{o.use}</span>
        </div>
      ))}
    </div>
  )
}

export function GlyphSpecimen() {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-5">
      {NODE_TYPES.map((t) => (
        <div key={t} className="flex items-center gap-3 rounded-md border border-border px-3 py-2.5">
          <GlyphIcon type={t} className="size-5" />
          <div className="flex flex-col">
            <span className="text-sm font-medium">{NODE_TYPE_LABEL[t]}</span>
            <span className="text-[11px] text-muted-foreground">
              {NODE_GLYPH[t].sides > 8 ? "원" : NODE_GLYPH[t].sides === 3 ? "삼각형" : NODE_GLYPH[t].start === 0 ? "마름모" : "사각형"}
              {" · "}
              {NODE_GLYPH[t].filled ? "채움" : "외곽선"}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

const LINES = [
  { label: "명시된 관계", note: "원천 데이터에 있는 관계 · 실선 · 맥락 단계", dash: undefined, opacity: OPACITY.context.value, width: 1.2 },
  { label: "추론한 관계", note: "모델이 추론한 관계 · 점선 · 맥락 단계", dash: "4 4", opacity: OPACITY.context.value, width: 1.2 },
  { label: "탐색 경로", note: "에이전트가 지나간 경로 · 실선 · 초점 단계", dash: undefined, opacity: OPACITY.focus.value, width: 1.6 },
  { label: "가려진 구간", note: "형상 뒤로 지나가는 구간 · 배경 단계", dash: undefined, opacity: OPACITY.faint.value, width: 1.2 },
] as const

export function LineSpecimen() {
  return (
    <div className="flex flex-col gap-3">
      {LINES.map((l) => (
        <div key={l.label} className="grid grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)] items-center gap-4 sm:grid-cols-[220px_160px_1fr]">
          <svg viewBox="0 0 220 12" className="h-3 w-full" aria-hidden>
            <circle cx="6" cy="6" r="3.5" className="fill-foreground" opacity={l.opacity} />
            <line x1="12" y1="6" x2="208" y2="6" className="stroke-foreground" strokeWidth={l.width} strokeDasharray={l.dash} opacity={l.opacity} />
            <circle cx="214" cy="6" r="3.5" className="fill-foreground" opacity={l.opacity} />
          </svg>
          <span className="text-sm font-medium">{l.label}</span>
          <span className="col-span-2 text-xs text-muted-foreground sm:col-span-1">{l.note}</span>
        </div>
      ))}
    </div>
  )
}

export function TypeSpecimen() {
  return (
    <div className="flex flex-col divide-y divide-border">
      {TYPE_ROLES.map((r) => (
        <div key={r.id} className="grid grid-cols-1 gap-2 py-4 sm:grid-cols-[180px_1fr] sm:items-baseline">
          <div className="flex flex-col">
            <span className="text-sm font-medium">{r.label}</span>
            <span className="font-mono text-[11px] text-muted-foreground">
              {r.size}px · {r.weight} · 자간 {r.tracking}
            </span>
          </div>
          <span
            className={"numeric" in r && r.numeric ? "tabular-nums" : undefined}
            style={{ fontSize: r.size, fontWeight: r.weight, letterSpacing: r.tracking }}
          >
            {r.sample}
          </span>
        </div>
      ))}
    </div>
  )
}

/** 35° 규칙: 카메라 시선과 글자 면의 각도 */
export function TiltSpecimen() {
  const ok = MAX_TEXT_TILT_DEG
  return (
    <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
      {[
        { deg: 0, ok: true },
        { deg: ok, ok: true },
        { deg: 60, ok: false },
        { deg: 80, ok: false },
      ].map(({ deg, ok: fine }) => (
        <div key={deg} className="flex items-center gap-4">
          <div className="flex h-24 w-44 items-center justify-center overflow-visible" style={{ perspective: 260 }}>
            <div
              className="rounded border border-foreground/30 bg-background px-3 py-1.5 text-sm font-medium"
              style={{ transform: `rotateX(${deg}deg)`, opacity: fine ? 1 : 0.4 }}
            >
              제1차 소위 심사
            </div>
          </div>
          <div className="flex flex-col">
            <span className="font-mono text-sm tabular-nums">{deg}°</span>
            <span className="text-xs text-muted-foreground">{fine ? "허용" : "판독 불가 · 쓰지 않음"}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

/** 점 → 선 → 글자 순서 등장. MOTION 토큰 값으로 재생한다. */
export function MotionSpecimen() {
  const reduced = useReducedMotion()
  const [run, setRun] = useState(0)
  const s = (ms: number) => (reduced ? 0 : ms / 1000)
  const points = [
    { x: 30, y: 92, label: "샘플 법안 A" },
    { x: 190, y: 36, label: "의원 가" },
    { x: 330, y: 92, label: "제1차 소위" },
  ]
  const lineStart = MOTION.point.duration + MOTION.stagger.duration * points.length
  const textStart = lineStart + MOTION.line.duration
  return (
    <div className="flex flex-col gap-3">
      <svg key={run} viewBox="0 0 400 120" className="h-36 w-full max-w-xl" aria-label="기록 등장 순서 견본">
        {points.slice(1).map((p, i) => (
          <motion.line
            key={`l${i}`}
            x1={points[i].x}
            y1={points[i].y}
            x2={p.x}
            y2={p.y}
            className="stroke-foreground"
            strokeWidth={1.2}
            opacity={OPACITY.related.value}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: s(lineStart + i * MOTION.stagger.duration), duration: s(MOTION.line.duration), ease: EASE_OUT }}
          />
        ))}
        {points.map((p, i) => (
          <g key={`p${i}`}>
            <motion.circle
              cx={p.x}
              cy={p.y}
              r={5}
              className="fill-foreground"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              style={{ transformOrigin: `${p.x}px ${p.y}px` }}
              transition={{ delay: s(i * MOTION.stagger.duration), duration: s(MOTION.point.duration), ease: EASE_OUT }}
            />
            <motion.text
              x={p.x}
              y={p.y + 22}
              textAnchor="middle"
              className="fill-foreground text-[11px]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: s(textStart + i * MOTION.stagger.duration), duration: s(MOTION.text.duration) }}
            >
              {p.label}
            </motion.text>
          </g>
        ))}
      </svg>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <Button variant="outline" size="sm" onClick={() => setRun((r) => r + 1)}>
          다시 재생
        </Button>
        {Object.entries(MOTION).map(([k, m]) => (
          <span key={k} className="text-xs text-muted-foreground">
            {m.label} <span className="font-mono tabular-nums text-foreground">{m.duration}ms</span>
          </span>
        ))}
      </div>
    </div>
  )
}

/**
 * 도면 양식 결과 패널 견본. 어두운 장면 위에 시나리오의 샘플 패널을 그대로 그리고
 * 등장을 다시 재생할 수 있다. 첫 화면에서는 타임라인의 한 항목을 선택 상태로 둔다.
 */
export function SchematicPanelSpecimen({ panels }: { panels: Panel[] }) {
  const reduced = useReducedMotion()
  const [run, setRun] = useState(0)
  const setFocus = useStage((s) => s.setFocus)
  useEffect(() => setFocus({ kind: "node", id: "mt1" }), [setFocus])
  return (
    <div className="flex flex-col gap-4">
      <div>
        <Button variant="outline" size="sm" onClick={() => setRun((r) => r + 1)}>
          등장 다시 재생
        </Button>
      </div>
      <SchematicTheme
        className="relative overflow-hidden px-10 py-12"
        style={{
          background: `radial-gradient(120% 90% at 30% 20%, #1b2127 0%, ${SCHEMATIC_THEME.scene} 70%)`,
        }}
      >
        <div key={run} className="grid grid-cols-1 gap-x-16 gap-y-14 md:grid-cols-2">
          {panels.map((p, i) => (
            <div key={i} className="w-full max-w-[380px]">
              <SchematicPanel panel={p} index={i + 1} animate={!reduced} />
            </div>
          ))}
        </div>
      </SchematicTheme>
    </div>
  )
}

/**
 * 도면 양식 3D 지도 견본. 지도 시나리오의 샘플 값을 그대로 쓰고, 선택 상태는 이 견본이 갖는다.
 * 첫 화면에서는 등장이 끝난 뒤 강남구를 선택해 선택 표시와 주석을 보여 준다.
 */
export function SchematicMapSpecimen({ data }: { data: Omit<SchematicMapProps, "focus" | "onFocus" | "className"> }) {
  const [run, setRun] = useState(0)
  const [focus, setFocus] = useState<string | null>(null)
  useEffect(() => {
    setFocus(null)
    const id = window.setTimeout(() => setFocus("11230"), 3200)
    return () => window.clearTimeout(id)
  }, [run])
  return (
    <div className="flex flex-col gap-4">
      <div>
        <Button variant="outline" size="sm" onClick={() => setRun((r) => r + 1)}>
          등장 다시 재생
        </Button>
      </div>
      <SchematicMap key={run} {...data} focus={focus} onFocus={setFocus} className="h-[720px]" />
    </div>
  )
}
