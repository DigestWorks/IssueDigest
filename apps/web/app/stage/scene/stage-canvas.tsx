import { useState } from "react"
import { Stats } from "@react-three/drei"
import { Canvas } from "@react-three/fiber"
import { ACESFilmicToneMapping, type Mesh } from "three"

import { useReducedMotion } from "~/design/use-reduced-motion"
import { GraphLayer } from "../graph/graph-layer"
import { CameraRig } from "./camera-rig"
import { ALL_EFFECTS, Effects, type EffectName } from "./effects"
import { Environment, LightSource } from "./environment"

/** 시각화 스테이지의 3D 장면. 브라우저에서만 불러온다(stage-view.tsx). */
export default function StageCanvas({ debug, effects = ALL_EFFECTS }: { debug: boolean; effects?: EffectName[] | null }) {
  const reducedMotion = useReducedMotion()
  const [sun, setSun] = useState<Mesh | null>(null)

  return (
    <Canvas
      shadows
      dpr={[1, 2]}
      camera={{ position: [0, 9, 19], fov: 38, near: 0.1, far: 200 }}
      gl={{ antialias: false, powerPreference: "high-performance", toneMapping: ACESFilmicToneMapping }}
    >
      <Environment reducedMotion={reducedMotion} />
      <LightSource ref={setSun} />
      <GraphLayer reducedMotion={reducedMotion} />
      <CameraRig reducedMotion={reducedMotion} />
      {effects ? <Effects sun={sun} reducedMotion={reducedMotion} enabled={effects} /> : null}
      {debug ? <Stats /> : null}
    </Canvas>
  )
}
