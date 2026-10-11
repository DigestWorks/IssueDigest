import { motion } from "motion/react"

import { dataColor } from "~/design/palette"
import { MOTION } from "~/design/tokens"
import type { RegionValue } from "../../events"
import { ACCENT, INK, op, Rule } from "../primitives"
import type { MapSource } from "./map-scene"

/**
 * 선택 지역 주석(도면 양식 라벨). 지시선 끝에 왼쪽 아래 모서리를 맞춘다.
 * 왼쪽 세로선은 주황 지시선과 이어지고, 위쪽 보조선은 상자 밖으로 연장된다.
 * 내용: 지역 코드 | 단위, 지역 이름, 값(데이터 색 사각점), 출처.
 */
export function RegionCallout({
  code,
  name,
  value,
  source,
  animate,
}: {
  code: string
  name: string
  value: RegionValue | undefined
  source: MapSource
  animate: boolean
}) {
  // 외곽선 추적(700ms)과 지시선(800ms)이 끝난 뒤에 나타난다
  const delay = animate ? 0.8 : 0
  const sec = (ms: number) => (animate ? ms / 1000 : 0)

  return (
    <div className="pointer-events-none w-[230px] -translate-y-full" style={{ color: INK }}>
      <motion.div
        className="relative px-3.5 pt-2.5 pb-3"
        initial={animate ? { opacity: 0, x: -8 } : false}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay, duration: sec(MOTION.text.duration * 1.5) }}
      >
        <div className="absolute inset-0 backdrop-blur-[6px]" style={{ background: "var(--sch-backing)" }} aria-hidden />
        <span aria-hidden className="absolute top-0 bottom-0 left-0 w-px" style={{ background: ACCENT }} />
        <span aria-hidden className="absolute top-0 -right-6 left-0 h-px" style={{ background: INK, opacity: op("context") }} />
        <span aria-hidden className="absolute -top-[1.5px] -right-6 size-[4px]" style={{ background: INK, opacity: op("context") }} />

        <div className="relative flex flex-col gap-1.5">
          <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.18em]" style={{ opacity: op("related") }}>
            <span className="tabular-nums">{code}</span>
            <span className="h-2.5 w-px" style={{ background: INK }} />
            <span>자치구</span>
          </div>
          <div className="text-[21px] leading-tight font-extralight tracking-[0.06em]" style={{ opacity: 0.92, textShadow: "0 1px 0 var(--sch-shadow)" }}>
            {name}
          </div>
          <Rule animate={animate} delay={(delay + 0.1) * 1000} />
          {value ? (
            <div className="flex items-center gap-2 text-[12px] tracking-[0.04em]">
              <span className="size-2 shrink-0" style={{ background: dataColor(value.category) }} />
              <span style={{ opacity: 0.9 }}>{value.label}</span>
            </div>
          ) : (
            <div className="text-[12px] tracking-[0.04em]" style={{ opacity: op("context") }}>
              값 없음
            </div>
          )}
          <div className="border-l pl-2 font-mono text-[10px] leading-snug tracking-[0.04em]" style={{ borderColor: INK, opacity: op("related") }}>
            출처 {source.label}
            {source.span ? ` · ${source.span}` : ""}
          </div>
        </div>
      </motion.div>
    </div>
  )
}
