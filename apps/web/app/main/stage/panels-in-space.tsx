import { useRef } from "react"
import { Html, type CameraControls } from "@react-three/drei"
import { useFrame, useThree } from "@react-three/fiber"
import { motion } from "motion/react"
import { MathUtils, type Group } from "three"

import { EASE_OUT, MOTION, type SchematicMode } from "~/design/tokens"
import type { Panel } from "~/stage/events"
import { uprightAmount } from "~/stage/scene/view-angle"
import { SchematicTheme } from "~/stage/schematic/primitives"
import { SchematicPanel } from "~/stage/schematic/schematic-panel"
import { useStage } from "~/stage/store"

/** 패널 가로 폭(px). Html transform 의 distanceFactor 와 함께 장면 크기를 정한다. */
const PANEL_WIDTH = 360
const DISTANCE_FACTOR = 7
/** 패널 폭의 장면 단위 값. drei Html transform 은 CSS 1px 을 distanceFactor/400 단위로 그린다. */
const PANEL_WORLD_WIDTH = (PANEL_WIDTH * DISTANCE_FACTOR) / 400
/** 패널 높이의 장면 단위 근삿값(차트·주장 패널 약 280~300px) */
const PANEL_WORLD_HEIGHT = 5.2
const GAP = 0.6
/** 지도·그래프가 차지하는 반지름 */
const CONTENT_RADIUS = 9.5
/** 세운 상태: 장면 중심에서 카메라 반대쪽으로 패널 줄까지의 거리 */
const BEYOND = 11
/** 패널 줄을 카메라 기준 오른쪽으로 옮기는 거리. 카메라 focal offset 과 맞춘다 */
export const PANEL_SHIFT_RIGHT = 3

/**
 * 결과 패널을 3D 공간에 띄운다.
 * - 카메라가 수직에 가까우면 패널을 바닥에 눕혀 지도·그래프 오른쪽에 위아래로 늘어놓는다.
 * - 카메라가 낮으면 지도·그래프 너머에 세워 좌우로 늘어놓는다. 두 배치는 기울기와 같은 비율로 잇는다.
 * - 패널은 카메라 방위각을 따라 돌아, 회전해도 글자가 바로 읽히는 방향을 유지한다.
 * 패널의 아래 가장자리 가운데가 기준점이며, 눕힐 때와 세울 때 모두 이 선을 축으로 접힌다.
 */
export function PanelsInSpace({ mode, reducedMotion }: { mode: SchematicMode; reducedMotion: boolean }) {
  const panels = useStage((s) => s.panels)
  return (
    <group>
      {panels.map(({ id, panel }, i) => (
        <PanelInSpace key={id} index={i} count={panels.length} panel={panel} mode={mode} reducedMotion={reducedMotion} />
      ))}
    </group>
  )
}

function PanelInSpace({
  index,
  count,
  panel,
  mode,
  reducedMotion,
}: {
  index: number
  count: number
  panel: Panel
  mode: SchematicMode
  reducedMotion: boolean
}) {
  const root = useRef<Group>(null)
  const yaw = useRef<Group>(null)
  const tilt = useRef<Group>(null)
  const upright = useRef(1)
  const controls = useThree((s) => s.controls) as CameraControls | null

  const centered = index - (count - 1) / 2
  const flatRight = CONTENT_RADIUS + PANEL_WORLD_WIDTH / 2 + 0.8
  const flatFar = centered * (PANEL_WORLD_HEIGHT + GAP) - PANEL_WORLD_HEIGHT / 2
  const uprightRight = centered * (PANEL_WORLD_WIDTH + GAP) + PANEL_SHIFT_RIGHT
  const uprightFar = BEYOND

  useFrame((_, delta) => {
    if (!controls || !root.current || !yaw.current || !tilt.current) return
    const target = uprightAmount(controls.polarAngle)
    upright.current = reducedMotion ? target : MathUtils.damp(upright.current, target, 6, delta)
    const t = upright.current

    // 카메라 방위각 θ 에서 오른쪽 r=(cosθ,0,-sinθ), 먼 쪽 f=(-sinθ,0,-cosθ)
    const az = controls.azimuthAngle
    const right = MathUtils.lerp(flatRight, uprightRight, t)
    const far = MathUtils.lerp(flatFar, uprightFar, t)
    const x = Math.cos(az) * right - Math.sin(az) * far
    const z = -Math.sin(az) * right - Math.cos(az) * far
    const p = root.current.position
    if (reducedMotion) p.set(x, 0.02, z)
    else {
      p.x = MathUtils.damp(p.x, x, 5, delta)
      p.z = MathUtils.damp(p.z, z, 5, delta)
    }
    yaw.current.rotation.y = az
    tilt.current.rotation.x = MathUtils.lerp(-Math.PI / 2, 0, t)
  })

  return (
    <group ref={root} position={[0, 0.02, -BEYOND]}>
      <group ref={yaw}>
        <group ref={tilt}>
          <Html transform distanceFactor={DISTANCE_FACTOR} zIndexRange={[12, 11]} style={{ pointerEvents: "auto" }}>
            {/* 아래 가장자리 가운데를 기준점에 맞춘다 */}
            <div style={{ width: PANEL_WIDTH, transform: "translate(0, -50%)" }}>
              {/* filter 를 쓰면 패널 바탕의 backdrop-filter 가 장면을 흐리지 못하므로 위치와 불투명도만 바꾼다 */}
              <motion.div
                initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reducedMotion ? 0 : MOTION.panel.duration / 1000, ease: EASE_OUT }}
              >
                <SchematicTheme mode={mode}>
                  <SchematicPanel panel={panel} index={index + 1} animate={!reducedMotion} />
                </SchematicTheme>
              </motion.div>
            </div>
          </Html>
        </group>
      </group>
    </group>
  )
}
