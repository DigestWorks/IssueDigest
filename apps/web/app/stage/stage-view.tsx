import { lazy, Suspense, useEffect, useState } from "react"
import { useSearchParams } from "react-router"

import { Badge } from "~/components/ui/badge"
import { StageHud } from "./hud/stage-hud"
import { ALL_EFFECTS, type EffectName } from "./scene/effects"

// three.js 는 브라우저 전용이다. SPA 빌드는 루트를 미리 렌더하므로
// 장면은 마운트 후에만 불러온다.
const StageCanvas = lazy(() => import("./scene/stage-canvas"))

/** ?fx=off 는 후처리 전체를 끄고, ?fx=bloom,dof 는 나열한 효과만 켠다. */
function parseEffects(value: string | null): EffectName[] | null | undefined {
  if (value === null) return undefined
  if (value === "off") return null
  return value.split(",").filter((v): v is EffectName => (ALL_EFFECTS as string[]).includes(v))
}

export function StageView() {
  const [mounted, setMounted] = useState(false)
  const [params] = useSearchParams()
  useEffect(() => setMounted(true), [])

  return (
    <section className="relative h-svh min-w-0 overflow-hidden bg-background" aria-label="시각화 스테이지">
      {mounted ? (
        <Suspense fallback={null}>
          <StageCanvas debug={params.has("debug")} effects={parseEffects(params.get("fx"))} />
        </Suspense>
      ) : null}
      <StageHud />
      <Badge variant="outline" className="absolute top-5 right-5 bg-background/60 backdrop-blur">
        샘플 데이터
      </Badge>
    </section>
  )
}
