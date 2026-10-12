import { useEffect, useState, type ReactNode } from "react"
import { motion } from "motion/react"

import { DATA_CATEGORICAL, dataColor, oklchToHex } from "~/design/palette"
import {
  EASE_OUT,
  FLOOR,
  HOLOGRAM,
  MOTION,
  OPACITY,
  SCHEMATIC_THEMES,
  TYPE_ROLES,
  type SchematicMode,
} from "~/design/tokens"
import { useReducedMotion } from "~/design/use-reduced-motion"
import type { Panel, RegionValue } from "~/stage/events"
import { RegionCallout } from "~/stage/schematic/map/region-callout"
import { SchematicMap, type SchematicMapProps } from "~/stage/schematic/map/schematic-map"
import {
  ACCENT,
  ACCENT_TEXT,
  ControlButton,
  INK,
  op,
  Rule,
  SchematicTheme,
  SquarePoint,
  useSchematicMode,
} from "~/stage/schematic/primitives"
import { SchematicPanel } from "~/stage/schematic/schematic-panel"
import { useStage } from "~/stage/store"

/**
 * /style 페이지 견본. 모두 실제 토큰과 컴포넌트로 그린다.
 * 바탕과 글자는 바깥 SchematicTheme 의 모드를 따른다.
 */

const mono = "font-mono text-[10px] tracking-[0.12em] tabular-nums"
const hairline = `color-mix(in oklab, ${INK} 11%, transparent)`

/** 견본 안의 작은 이름표: 고정폭 보조 글자 */
function Tag({ children, step = "related" }: { children: ReactNode; step?: keyof typeof OPACITY }) {
  return (
    <span className={mono} style={{ opacity: op(step) }}>
      {children}
    </span>
  )
}

/** WCAG 2.x 상대 휘도 대비. 견본에 적는 수치를 토큰 값에서 직접 계산한다. */
function contrast(a: string, b: string) {
  const lum = (hex: string) => {
    const [r, g, bl] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    const f = (c: number) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(bl)
  }
  const [hi, lo] = [lum(a), lum(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/* 장면 */

/** 두 모드의 장면 값과 바닥 조명 범위 */
export function SceneSpecimen() {
  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
      {(["dark", "light"] as SchematicMode[]).map((m) => {
        const t = SCHEMATIC_THEMES[m]
        const inner = (FLOOR.inner / (FLOOR.size / 2)) * 100
        const outer = (FLOOR.outer / (FLOOR.size / 2)) * 100
        return (
          <SchematicTheme key={m} mode={m} className="flex flex-col gap-3 p-4" style={{ background: t.backdrop }}>
            <Tag>{m === "dark" ? "어두운 모드 · 기본" : "밝은 모드"}</Tag>
            {/* 바닥 조명: 중앙색(scene)에서 바깥색(backdrop)으로 */}
            <div
              className="relative h-28"
              style={{ background: `radial-gradient(closest-side, ${t.scene} ${inner}%, ${t.backdrop} ${outer}%)` }}
            >
              <span className="absolute top-2 left-2">
                <Tag step="context">
                  바닥 조명 · 반지름 {FLOOR.inner} → {FLOOR.outer}
                </Tag>
              </span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {(
                [
                  ["scene", t.scene],
                  ["backdrop", t.backdrop],
                  ["ink", t.ink],
                  ["neutral", t.neutral],
                  ["grid", t.grid],
                  ["gridSection", t.gridSection],
                  ["accent", t.accent],
                  ["accentText", t.accentText],
                ] as const
              ).map(([name, v]) => (
                <div key={name} className="flex flex-col gap-1">
                  <span className="h-6 border" style={{ background: v, borderColor: `${t.ink}33` }} />
                  <Tag>{name}</Tag>
                  <Tag step="context">{v}</Tag>
                </div>
              ))}
            </div>
          </SchematicTheme>
        )
      })}
    </div>
  )
}

/* 선과 주석 */

export function OpacitySpecimen() {
  return (
    <div className="flex flex-col gap-3">
      {Object.entries(OPACITY).map(([key, o]) => (
        <div key={key} className="grid grid-cols-[56px_1fr_minmax(0,1.4fr)] items-center gap-4">
          <Tag step="focus">{Math.round(o.value * 100)}%</Tag>
          <div className="flex items-center gap-2" style={{ opacity: o.value }}>
            <span className="size-[5px]" style={{ background: INK }} />
            <span className="h-px flex-1" style={{ background: INK }} />
            <span className="text-[13px] tracking-[0.04em]">{o.label}</span>
          </div>
          <span className="text-[12px]" style={{ opacity: op("related") }}>
            {o.use}
          </span>
        </div>
      ))}
    </div>
  )
}

/** 측정 주석: 모서리 꺾쇠, 경위도 눈금, 축척 막대, 출처 */
export function AnnotationSpecimen() {
  const ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8]
  return (
    <svg viewBox="0 0 560 190" className="w-full max-w-2xl overflow-visible" role="img" aria-label="측정 주석 견본">
      <g style={{ stroke: INK }} fill="none">
        <g opacity={op("related")}>
          <polyline points="20,46 20,20 46,20" />
          <polyline points="514,20 540,20 540,46" />
          <polyline points="20,124 20,150 46,150" />
          <polyline points="514,150 540,150 540,124" />
        </g>
        <g opacity={op("context")}>
          <line x1="46" y1="20" x2="514" y2="20" />
          <line x1="46" y1="150" x2="514" y2="150" />
        </g>
        {ticks.map((i) => (
          <line key={i} x1={60 + i * 55} y1="150" x2={60 + i * 55} y2={i % 2 ? 156 : 161} opacity={i % 2 ? op("context") : op("related")} />
        ))}
        <g opacity={op("related")}>
          <line x1="410" y1="128" x2="520" y2="128" />
          <line x1="410" y1="124" x2="410" y2="132" />
          <line x1="520" y1="124" x2="520" y2="132" />
          <line x1="465" y1="126" x2="465" y2="130" opacity={0.5} />
        </g>
      </g>
      <g style={{ fill: INK }} className="font-mono text-[9px] tracking-[0.08em]">
        {ticks
          .filter((i) => i % 2 === 0)
          .map((i) => (
            <text key={i} x={60 + i * 55} y="174" textAnchor="middle" opacity={op("related")}>
              {(126.8 + i * 0.05).toFixed(1)}°E
            </text>
          ))}
        <text x="520" y="118" textAnchor="end" opacity={op("related")}>
          5 km
        </text>
        <text x="22" y="10" opacity={op("related")}>
          서울특별시 자치구 경계 · 통계청 센서스용 행정구역경계 2013 · 메르카토르 투영
        </text>
      </g>
    </svg>
  )
}

/** 지시선 끝의 주석(지도 선택 주석 컴포넌트 그대로) */
export function CalloutSpecimen() {
  const reduced = useReducedMotion()
  const value: RegionValue = { category: 0, magnitude: 0.2, label: "후보 B 우세 · 격차 2.4%p" }
  return (
    // RegionCallout 은 기준점 위로 그려진다(왼쪽 아래 모서리가 기준점). 기준점을 주석 높이만큼 내려 둔다.
    <div className="relative h-[240px]">
      <span className="absolute top-[160px] left-[40px] h-[70px] w-px" style={{ background: ACCENT }} />
      <span className="absolute top-[227px] left-[37px] size-[7px]" style={{ background: ACCENT }} />
      <div className="absolute top-[160px] left-[40px]">
        <RegionCallout
          code="11030"
          name="용산구"
          value={value}
          source={{ label: "가상 여론조사 (샘플)", span: "자치구별 응답" }}
          animate={!reduced}
        />
      </div>
    </div>
  )
}

/* 색 */

export function DataPaletteSpecimen() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      {DATA_CATEGORICAL.map((c, i) => (
        <div key={i} className="flex flex-col gap-1.5">
          <span className="h-10" style={{ background: dataColor(i) }} />
          <Tag step="focus">data-cat-{i + 1}</Tag>
          <Tag step="context">oklch({c.join(" ")})</Tag>
          <Tag step="context">{oklchToHex(c)}</Tag>
        </div>
      ))}
    </div>
  )
}

/** 데이터 색 범위: 답과 관련된 칸만 데이터 색, 나머지는 중립색 */
export function ColorScopeSpecimen() {
  const t = SCHEMATIC_THEMES[useSchematicMode()]
  // 7 × 4 칸 중 가운데 몇 칸만 답과 관련된 데이터다
  const colored: Record<number, number> = { 9: 1, 10: 1, 11: 1, 17: 0, 18: 1 }
  return (
    <div className="flex flex-wrap items-end gap-8">
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: 28 }, (_, i) => {
          const cat = colored[i]
          const on = cat !== undefined
          return (
            <span
              key={i}
              className="size-7 border"
              style={{
                background: on ? `${dataColor(cat)}66` : `${t.neutral}14`,
                borderColor: on ? dataColor(cat) : `${t.neutral}88`,
              }}
            />
          )
        })}
      </div>
      <div className="flex flex-col gap-1.5 text-[12px]" style={{ opacity: 0.88 }}>
        <span>답과 관련된 칸 · 데이터 색</span>
        <span style={{ opacity: op("related") }}>나머지 칸 · 중립색, 면을 거의 채우지 않음</span>
      </div>
    </div>
  )
}

/** 주황: 선·점과 글자 값, 바탕 대비 */
export function AccentSpecimen() {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {(["dark", "light"] as SchematicMode[]).map((m) => {
        const t = SCHEMATIC_THEMES[m]
        return (
          <SchematicTheme key={m} mode={m} className="flex items-center gap-6 p-4" style={{ background: t.scene }}>
            <div className="flex items-center gap-2">
              <SquarePoint size={6} emphasized />
              <span className="h-px w-12" style={{ background: ACCENT }} />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-[13px] tracking-[0.04em]" style={{ color: ACCENT_TEXT }}>
                가리킴 11030 용산구
              </span>
              <Tag>
                선·점 {t.accent} {contrast(t.accent, t.scene).toFixed(2)}:1 · 글자 {t.accentText}{" "}
                {contrast(t.accentText, t.scene).toFixed(2)}:1
              </Tag>
            </div>
          </SchematicTheme>
        )
      })}
    </div>
  )
}

/* 부피 */

/** 층 묶음과 선택 시 확장. 같은 외곽선을 층 간격만큼 겹쳐 그린다. */
export function LayerSpecimen() {
  const reduced = useReducedMotion()
  const [selected, setSelected] = useState(false)
  const count = 8
  // HOLOGRAM.layerGap 을 견본 화면 크기에 옮긴 값(px)
  const gap = 9
  const spread = selected ? HOLOGRAM.focusSpread : 1
  const shape = "0,22 46,0 120,10 150,34 104,58 30,52"
  return (
    <div className="flex flex-wrap items-end gap-10">
      <svg viewBox="-10 -120 180 200" className="h-52 w-48 overflow-visible" aria-label="층 묶음 견본">
        {Array.from({ length: count }, (_, k) => {
          const top = k === count - 1
          const a = top ? 1 : 0.22 + 0.5 * ((k + 1) / count) ** 1.5
          return (
            <motion.polygon
              key={k}
              points={shape}
              fill={top ? `${dataColor(1)}99` : `${dataColor(1)}10`}
              style={{ stroke: top ? INK : dataColor(1) }}
              strokeWidth={top ? 1.8 : 1}
              opacity={a}
              initial={false}
              animate={{ y: -k * gap * spread }}
              transition={{ duration: reduced ? 0 : 0.6, ease: EASE_OUT }}
            />
          )
        })}
      </svg>
      <div className="flex flex-col gap-2">
        <ControlButton active={selected} onClick={() => setSelected((s) => !s)} point="start">
          {selected ? "선택됨 · 층 간격 확장" : "선택하기"}
        </ControlButton>
        <Tag>
          층 간격 {HOLOGRAM.layerGap} · 선택 시 최대 {HOLOGRAM.focusSpread}배 · 늘어나는 높이 최대 {HOLOGRAM.focusRiseMax}
        </Tag>
        <Tag step="context">맨 위 층 1.8px · 나머지 1px · 아래 층일수록 바탕색에 가까움</Tag>
      </div>
    </div>
  )
}

/* 효과 */

/** 층 색 번짐: 빨강(왼쪽)·청록(오른쪽) 사본을 화면 픽셀만큼 어긋나게 겹친다. 오른쪽은 같은 그림을 4배 확대한 것이다. */
export function FringeSpecimen() {
  const px = HOLOGRAM.fringe.px
  const lines = (
    <g fill="none">
      {[
        { color: "#ff2d55", dx: -px },
        { color: "#00d8ff", dx: px },
      ].map((c) => (
        <path
          key={c.color}
          d="M10,70 L60,20 L120,30 L170,8 M10,90 L60,40 L120,50 L170,28"
          stroke={c.color}
          opacity={HOLOGRAM.fringe.colored}
          transform={`translate(${c.dx} 0)`}
        />
      ))}
      <path d="M10,70 L60,20 L120,30 L170,8 M10,90 L60,40 L120,50 L170,28" style={{ stroke: INK }} opacity={0.85} />
    </g>
  )
  return (
    <div className="flex flex-wrap items-end gap-10">
      <div className="flex flex-col gap-2">
        <svg viewBox="0 0 180 100" width={180} height={100} className="overflow-visible" aria-hidden>
          {lines}
        </svg>
        <Tag>실제 크기 · 좌우 {px}px</Tag>
      </div>
      <div className="flex flex-col gap-2">
        <svg viewBox="40 10 60 40" width={240} height={160} aria-hidden>
          {lines}
        </svg>
        <Tag>4배 확대</Tag>
      </div>
    </div>
  )
}

/* 글자 */

export function TypeSpecimen() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex max-w-md flex-col gap-1.5">
        <div className="flex items-center gap-2 text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
          <span className="font-mono tabular-nums">03</span>
          <span className="h-2.5 w-px" style={{ background: INK }} />
          <span>차트 · 단위 명</span>
        </div>
        <span
          className="text-[24px] leading-tight font-extralight tracking-[0.06em]"
          style={{ opacity: 0.92, textShadow: "0 1px 0 var(--sch-shadow)" }}
        >
          돌봄 대기 아동 수
        </span>
        <Rule animate={false} />
        <Tag step="context">머리 줄 → 제목 → 머리선</Tag>
      </div>
      <div className="flex flex-col">
        {TYPE_ROLES.map((r) => (
          <div
            key={r.id}
            className="grid grid-cols-1 gap-1 border-t py-3 sm:grid-cols-[180px_1fr] sm:items-baseline"
            style={{ borderColor: hairline }}
          >
            <div className="flex flex-col">
              <span className="text-[12px]">{r.label}</span>
              <Tag step="context">
                {r.size}px · {r.weight} · 자간 {r.tracking}
              </Tag>
            </div>
            <span
              className={[("numeric" in r && r.numeric) || ("mono" in r && r.mono) ? "tabular-nums" : "", "mono" in r && r.mono ? "font-mono" : ""].join(" ")}
              style={{ fontSize: r.size, fontWeight: r.weight, letterSpacing: r.tracking, opacity: "mono" in r && r.mono ? op("related") : 0.92 }}
            >
              {r.sample}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* 화면 고정 주석 */

export function HudSpecimen() {
  const [view, setView] = useState("전체")
  return (
    <div className="grid grid-cols-1 gap-8 md:grid-cols-3">
      <div className="flex flex-col items-start gap-1">
        <Tag step="context">조작 버튼</Tag>
        {["전체", "위에서", "낮게"].map((v) => (
          <ControlButton key={v} active={view === v} onClick={() => setView(v)} point="start">
            {v}
          </ControlButton>
        ))}
      </div>
      <div className="flex flex-col gap-2">
        <Tag step="context">사각점</Tag>
        <div className="flex items-center gap-4">
          <SquarePoint size={5} />
          <SquarePoint size={5} filled={false} />
          <SquarePoint size={5} emphasized />
        </div>
        <Tag step="context">채움 · 비움 · 선택</Tag>
      </div>
      <div className="flex flex-col gap-2">
        <Tag step="context">범례 · 색 범주 · 높이 격차</Tag>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] tracking-[0.08em]">
          {[
            ["후보 A", 1],
            ["후보 B", 0],
            ["후보 C", 2],
          ].map(([l, c]) => (
            <span key={l} className="flex items-center gap-2">
              <span className="size-2" style={{ background: dataColor(c as number) }} />
              {l}
            </span>
          ))}
        </div>
        <Tag>방위 000° · 기울기 43° · 거리 28.6</Tag>
      </div>
    </div>
  )
}

/* 패널 · 지도 · 모션 */

/**
 * 결과 패널 견본. 시나리오의 샘플 패널을 그대로 그리고 등장을 다시 재생할 수 있다.
 * 첫 화면에서는 타임라인의 한 항목을 선택 상태로 둔다.
 */
export function SchematicPanelSpecimen({ panels }: { panels: Panel[] }) {
  const reduced = useReducedMotion()
  const [run, setRun] = useState(0)
  const setFocus = useStage((s) => s.setFocus)
  const theme = SCHEMATIC_THEMES[useSchematicMode()]
  useEffect(() => setFocus({ kind: "node", id: "mt1" }), [setFocus])
  return (
    <div className="flex flex-col gap-4">
      <ControlButton active={false} onClick={() => setRun((r) => r + 1)} point="start">
        등장 다시 재생
      </ControlButton>
      <div
        className="relative overflow-hidden px-10 py-12"
        style={{ background: `radial-gradient(120% 90% at 30% 20%, ${theme.glow} 0%, ${theme.scene} 70%)` }}
      >
        <div key={run} className="grid grid-cols-1 gap-x-16 gap-y-14 md:grid-cols-2">
          {panels.map((p, i) => (
            <div key={i} className="w-full max-w-[380px]">
              <SchematicPanel panel={p} index={i + 1} animate={!reduced} />
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/**
 * 3D 지도 견본. 지도 시나리오의 샘플 값을 그대로 쓰고, 선택 상태는 이 견본이 갖는다.
 * 첫 화면에서는 등장이 끝난 뒤 용산구를 선택해 선택 표시와 주석을 보여 준다.
 */
export function SchematicMapSpecimen({ data }: { data: Omit<SchematicMapProps, "focus" | "onFocus" | "className"> }) {
  const [run, setRun] = useState(0)
  const [focus, setFocus] = useState<string | null>(null)
  useEffect(() => {
    setFocus(null)
    const id = window.setTimeout(() => setFocus("11030"), 3200)
    return () => window.clearTimeout(id)
  }, [run])
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-6">
        <ControlButton active={false} onClick={() => setRun((r) => r + 1)} point="start">
          등장 다시 재생
        </ControlButton>
        <a href="/map" className="text-[12px] tracking-[0.12em]" style={{ opacity: op("related") }}>
          전체 화면으로 보기 · /map
        </a>
      </div>
      <SchematicMap key={run} {...data} focus={focus} onFocus={setFocus} className="h-[720px]" />
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
      <ControlButton active={false} onClick={() => setRun((r) => r + 1)} point="start">
        다시 재생
      </ControlButton>
      <svg key={run} viewBox="0 0 400 120" className="h-36 w-full max-w-xl overflow-visible" aria-label="기록 등장 순서 견본">
        {points.slice(1).map((p, i) => (
          <motion.line
            key={`l${i}`}
            x1={points[i].x}
            y1={points[i].y}
            x2={p.x}
            y2={p.y}
            style={{ stroke: INK }}
            strokeWidth={1}
            opacity={op("related")}
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ delay: s(lineStart + i * MOTION.stagger.duration), duration: s(MOTION.line.duration), ease: EASE_OUT }}
          />
        ))}
        {points.map((p, i) => (
          <g key={`p${i}`}>
            <motion.rect
              x={p.x - 3}
              y={p.y - 3}
              width={6}
              height={6}
              style={{ fill: INK, transformOrigin: `${p.x}px ${p.y}px` }}
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: s(i * MOTION.stagger.duration), duration: s(MOTION.point.duration), ease: EASE_OUT }}
            />
            <motion.text
              x={p.x}
              y={p.y + 22}
              textAnchor="middle"
              className="text-[11px]"
              style={{ fill: INK }}
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.88 }}
              transition={{ delay: s(textStart + i * MOTION.stagger.duration), duration: s(MOTION.text.duration) }}
            >
              {p.label}
            </motion.text>
          </g>
        ))}
      </svg>
      <div className="flex flex-wrap gap-x-6 gap-y-1">
        {Object.entries(MOTION).map(([k, m]) => (
          <Tag key={k}>
            {m.label} {m.duration}ms
          </Tag>
        ))}
      </div>
    </div>
  )
}
