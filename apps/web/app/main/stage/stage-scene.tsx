import { useRef, type RefObject } from "react"
import { Canvas } from "@react-three/fiber"
import { NoToneMapping } from "three"

import { SCHEMATIC_THEMES, type SchematicMode } from "~/design/tokens"
import { MapHologram } from "~/stage/schematic/map/map-scene"
import { SceneBackdrop } from "~/stage/schematic/scene/backdrop"
import { DRAG_PX } from "~/stage/schematic/scene/draw"
import { SceneEffects } from "~/stage/schematic/scene/effects"
import { focusPoints } from "~/stage/schematic/scene/registry"
import { ThemeContext } from "~/stage/schematic/scene/theme"
import { useStage } from "~/stage/store"
import { GraphHologram } from "./graph-hologram"
import { PanelsInSpace } from "./panels-in-space"
import { StageCamera } from "./stage-camera"
import { useStageUi } from "./ui-store"

/**
 * 메인 스테이지 3D 장면. 지도 페이지와 같은 바탕(바닥 조명·격자·거리 감쇠)과 후처리를 쓰고,
 * 그래프 홀로그램·지도 홀로그램·결과 패널을 한 장면·한 카메라에 둔다.
 * main-stage.tsx 가 브라우저에서만 불러온다.
 */
export default function StageScene({
  mode,
  readout,
  reducedMotion,
}: {
  mode: SchematicMode
  readout: RefObject<HTMLSpanElement | null>
  reducedMotion: boolean
}) {
  const theme = SCHEMATIC_THEMES[mode]
  const down = useRef<{ x: number; y: number } | null>(null)
  const setFocus = useStage((s) => s.setFocus)
  const hasNodes = useStage((s) => s.nodes.length > 0)
  const map = useStage((s) => s.map)
  const choropleth = useStage((s) => s.choropleth)
  const focus = useStage((s) => s.focus)
  const hovered = useStageUi((s) => s.hovered)
  const setHovered = useStageUi((s) => s.setHovered)

  return (
    <Canvas
      // 배경 클릭으로 선택을 푼다. 회전·이동하려고 끈 경우는 클릭으로 보지 않는다.
      onPointerDown={(e) => (down.current = { x: e.clientX, y: e.clientY })}
      onPointerMissed={(e) => {
        const d = down.current
        if (d && Math.hypot(e.clientX - d.x, e.clientY - d.y) <= DRAG_PX) setFocus(null)
      }}
      dpr={[1, 2]}
      camera={{ position: [0, 26, 32], fov: 36, near: 0.1, far: 200 }}
      gl={{ antialias: true, toneMapping: NoToneMapping }}
    >
      <SceneBackdrop theme={theme} />
      <ThemeContext.Provider value={theme}>
        {hasNodes ? <GraphHologram reducedMotion={reducedMotion} /> : null}
        {/* 지도는 지역 값이 들어온 시점에 등장한다(등장 기준 시각이 값과 함께 시작) */}
        {map && choropleth ? (
          <MapHologram
            key={choropleth.appliedAt}
            values={choropleth.values}
            colored={choropleth.highlight}
            source={choropleth.source}
            focus={focus?.kind === "region" ? focus.id : null}
            hovered={hovered?.kind === "region" ? hovered.id : null}
            onFocus={(code) => setFocus(code ? { kind: "region", id: code } : null)}
            onHover={(r) => setHovered(r ? { kind: "region", id: r.code, label: r.name } : null)}
            reducedMotion={reducedMotion}
          />
        ) : null}
        <PanelsInSpace mode={mode} reducedMotion={reducedMotion} />
        <StageCamera readout={readout} reducedMotion={reducedMotion} />
      </ThemeContext.Provider>
      <SceneEffects
        target={(out) => {
          const f = useStage.getState().focus
          const p = f ? focusPoints[f.kind].get(f.id) : undefined
          return p ? out.copy(p) : null
        }}
      />
    </Canvas>
  )
}
