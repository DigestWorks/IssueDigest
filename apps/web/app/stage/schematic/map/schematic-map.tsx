import { lazy, Suspense, useEffect, useRef, useState, type ReactNode } from "react"
import { motion } from "motion/react"

import { dataColor } from "~/design/palette"
import { EASE_OUT, SCHEMATIC_THEMES, type SchematicMode } from "~/design/tokens"
import { useReducedMotion } from "~/design/use-reduced-motion"
import { cn } from "~/lib/utils"
import type { RegionValue } from "../../events"
import { ACCENT_TEXT, ControlButton, INK, op, Rule, SchematicTheme, useSchematicMode } from "../primitives"
import type { MapSource, MapView } from "./map-scene"

// three.js 는 브라우저 전용이다. SPA 빌드가 라우트를 미리 렌더하므로 마운트 후에만 불러온다.
const MapScene = lazy(() => import("./map-scene"))

const VIEW_LABEL: Record<MapView, string> = {
  overview: "전체",
  top: "위에서",
  low: "낮게",
}

export type SchematicMapProps = {
  title: string
  values: Record<string, RegionValue>
  /** 색으로 표시할 지역 코드. 없으면 값이 있는 모든 지역. 나머지는 높이만 두고 중립색으로 그린다 */
  colored?: string[]
  legend: { category: number; label: string }[]
  source: MapSource
  /** 선택한 지역 코드 */
  focus: string | null
  onFocus: (code: string | null) => void
  /** 보기 전환 아래에 덧붙일 조작(예: 다시 재생, 색 모드). ControlButton 으로 만든다 */
  controls?: ReactNode
  /** 색 모드. 주지 않으면 바깥 SchematicTheme 의 모드(없으면 어두운 모드) */
  mode?: SchematicMode
  className?: string
}

/**
 * 도면 양식 3D 인터랙티브 지도(서울 자치구).
 * - 회전(왼쪽 드래그), 이동(오른쪽 드래그), 확대·축소(휠), 지역 선택(지역 클릭), 선택 해제(배경 클릭, Esc).
 * - 화면 고정 주석: 제목, 보기 전환, 범례와 출처, 카메라 방위·기울기·거리, 가리킨 지역.
 * 스테이지 상태와 분리된 컴포넌트다. 값과 선택 상태는 속성으로 받는다.
 */
export function SchematicMap({ title, values, colored, legend, source, focus, onFocus, controls, mode, className }: SchematicMapProps) {
  const outer = useSchematicMode()
  const m = mode ?? outer
  const reducedMotion = useReducedMotion()
  const [mounted, setMounted] = useState(false)
  const [hovered, setHovered] = useState<{ code: string; name: string } | null>(null)
  const [view, setView] = useState<{ name: MapView; n: number }>({ name: "overview", n: 0 })
  const readout = useRef<HTMLSpanElement>(null)
  useEffect(() => setMounted(true), [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onFocus(null)
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onFocus])

  const count = Object.keys(values).length

  return (
    <SchematicTheme mode={m} className={cn("relative overflow-hidden select-none", className)} style={{ background: "var(--sch-backdrop)" }}>
      <div className="absolute inset-0">
        {mounted ? (
          <Suspense fallback={null}>
            <MapScene
              values={values}
              colored={colored}
              theme={SCHEMATIC_THEMES[m]}
              source={source}
              focus={focus}
              hovered={hovered?.code ?? null}
              onFocus={onFocus}
              onHover={setHovered}
              view={view}
              readout={readout}
              reducedMotion={reducedMotion}
            />
          </Suspense>
        ) : null}
      </div>

      {/* 화면 고정 주석 뒤의 어두운 층: 지면 글자와 겹쳐도 읽히게 한다 */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 z-10"
        style={{
          background:
            "linear-gradient(to bottom, var(--sch-backdrop) 0%, transparent 22%, transparent 74%, var(--sch-backdrop) 100%)",
          opacity: 0.85,
        }}
      />
      <div className="pointer-events-none absolute inset-0 z-20 flex flex-col justify-between p-6" style={{ color: INK }}>
        <div className="flex items-start justify-between gap-6">
          {/* 제목 */}
          <motion.div
            className="flex w-[380px] flex-col gap-1.5"
            initial={reducedMotion ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: reducedMotion ? 0 : 0.5, ease: EASE_OUT }}
          >
            <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("related") }}>
              <span>지도</span>
              <span className="h-2.5 w-px" style={{ background: INK }} />
              <span>서울 자치구 {count}</span>
            </div>
            <h3 className="text-[24px] leading-tight font-extralight tracking-[0.06em]" style={{ opacity: 0.92, textShadow: "0 1px 0 var(--sch-shadow)" }}>
              {title}
            </h3>
            <Rule animate={!reducedMotion} delay={200} />
          </motion.div>

          {/* 보기 전환 */}
          <div className="pointer-events-auto flex flex-col items-end gap-1">
            <span className="mb-1 font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
              보기
            </span>
            {(Object.keys(VIEW_LABEL) as MapView[]).map((v) => (
              <ControlButton key={v} active={view.name === v} onClick={() => setView((s) => ({ name: v, n: s.n + 1 }))}>
                {VIEW_LABEL[v]}
              </ControlButton>
            ))}
            {focus ? (
              <ControlButton active={false} onClick={() => onFocus(null)}>
                선택 해제
              </ControlButton>
            ) : null}
            {controls}
          </div>
        </div>

        <div className="flex items-end justify-between gap-6">
          {/* 범례와 출처 */}
          <div className="flex flex-col gap-2">
            <span className="font-mono text-[10px] tracking-[0.22em]" style={{ opacity: op("context") }}>
              범례 · 색 범주 · 높이 격차
            </span>
            <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-[11px] tracking-[0.08em]">
              {legend.map((l) => (
                <span key={l.label} className="flex items-center gap-2">
                  <span className="size-2" style={{ background: dataColor(l.category) }} />
                  <span style={{ opacity: 0.88 }}>{l.label}</span>
                </span>
              ))}
            </div>
            <span className="flex items-center gap-2 font-mono text-[10px] tracking-[0.06em]" style={{ opacity: op("related") }}>
              <span className="h-2.5 w-px" style={{ background: INK }} />
              출처 {source.label}
              {source.span ? ` · ${source.span}` : ""}
            </span>
          </div>

          {/* 카메라와 가리킨 지역 */}
          <div className="flex flex-col items-end gap-1.5 font-mono text-[10px] tracking-[0.12em] tabular-nums">
            <span style={{ opacity: hovered ? 1 : 0, color: ACCENT_TEXT }}>{hovered ? `가리킴 ${hovered.code} ${hovered.name}` : " "}</span>
            <span ref={readout} style={{ opacity: op("related") }} />
            <span style={{ opacity: op("context") }}>드래그 회전 · 오른쪽 드래그 이동 · 휠 확대 · 지역 클릭 선택 · 배경 클릭·Esc 해제</span>
          </div>
        </div>
      </div>
    </SchematicTheme>
  )
}
