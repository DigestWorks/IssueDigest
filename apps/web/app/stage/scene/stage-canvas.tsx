import { Stats } from "@react-three/drei"
import { Canvas } from "@react-three/fiber"
import { NoToneMapping } from "three"

import { useReducedMotion } from "~/design/use-reduced-motion"
import { GraphLayer } from "../graph/graph-layer"
import { CameraRig } from "./camera-rig"
import { ALL_EFFECTS, Effects, type EffectName } from "./effects"
import { Environment } from "./environment"

/** 시각화 스테이지의 3D 장면. 브라우저에서만 불러온다(stage-view.tsx). */
export default function StageCanvas({
  debug,
  effects = ALL_EFFECTS,
}: {
  debug: boolean
  effects?: EffectName[] | null
}) {
  const reducedMotion = useReducedMotion()

  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: [0, 10, 24], fov: 38, near: 0.1, far: 200 }}
      // 흰 배경이 회색으로 바뀌지 않도록 톤 매핑을 쓰지 않는다.
      gl={{ antialias: true, powerPreference: "high-performance", toneMapping: NoToneMapping }}
    >
      <Environment reducedMotion={reducedMotion} />
      <GraphLayer reducedMotion={reducedMotion} />
      <CameraRig reducedMotion={reducedMotion} />
      {effects ? <Effects reducedMotion={reducedMotion} enabled={effects} /> : null}
      {debug ? <Stats /> : null}
    </Canvas>
  )
}
