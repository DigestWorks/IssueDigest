import { useRef } from "react"
import { Html } from "@react-three/drei"
import { useFrame, useThree } from "@react-three/fiber"
import { motion } from "motion/react"
import { MathUtils, type Group } from "three"
import type { CameraControls } from "@react-three/drei"

import { EASE_OUT, MOTION } from "~/design/tokens"
import type { Panel } from "../events"
import { uprightAmount } from "../scene/view-angle"
import { useStage } from "../store"
import { SchematicTheme } from "../schematic/primitives"
import { SchematicPanel } from "../schematic/schematic-panel"

/** 패널 가로 폭(px). Html transform 의 distanceFactor 와 함께 장면 크기를 정한다. */
const PANEL_WIDTH = 360
const DISTANCE_FACTOR = 7
/** 패널 폭의 장면 단위 값. drei Html transform 은 CSS 1px 을 distanceFactor/400 단위로 그린다. */
const PANEL_WORLD_WIDTH = (PANEL_WIDTH * DISTANCE_FACTOR) / 400
/** 패널 높이의 장면 단위 근삿값(차트·주장 패널 약 280~300px) */
const PANEL_WORLD_HEIGHT = 5.2
const GAP = 0.6
/** 지도·그래프가 차지하는 반지름 */
const CONTENT_RADIUS = 8
/** 세운 상태: 장면 중심에서 카메라 반대쪽으로 패널 줄까지의 거리 */
const BEYOND = 10
/** 패널 줄을 카메라 기준 오른쪽으로 옮기는 거리. 카메라 focal offset 과 맞춘다 */
export const PANEL_SHIFT_RIGHT = 3

/**
 * 결과 패널을 3D 공간에 띄운다.
 * - 카메라가 수직에 가까우면 패널을 지면(지도 평면)에 눕힌다.
 * - 카메라가 낮으면 패널을 지면 위에 세운다.
 * - 패널은 카메라 방위각을 따라 돌아, 회전해도 글자가 바로 읽히는 방향을 유지한다.
 * - 눕힌 상태에서는 지도(그래프) 오른쪽에 위아래로 늘어놓고, 세운 상태에서는 지도 너머에
 *   좌우로 나란히 놓는다. 두 배치는 기울기와 같은 비율로 보간한다.
 * 패널의 아래 가장자리 가운데가 기준점이며, 눕힐 때와 세울 때 모두 이 선을 축으로 접힌다.
 */
export function PanelLayer({ reducedMotion }: { reducedMotion: boolean }) {
  const panels = useStage((s) => s.panels)

  return (
    <group>
      {panels.map(({ id, panel }, i) => (
        <PanelInSpace
          key={id}
          index={i}
          count={panels.length}
          panel={panel}
          reducedMotion={reducedMotion}
        />
      ))}
    </group>
  )
}

function PanelInSpace({
  index,
  count,
  panel,
  reducedMotion,
}: {
  index: number
  count: number
  panel: Panel
  reducedMotion: boolean
}) {
  const root = useRef<Group>(null)
  const yaw = useRef<Group>(null)
  const tilt = useRef<Group>(null)
  const upright = useRef(1)
  const controls = useThree((s) => s.controls) as CameraControls | null

  const centered = index - (count - 1) / 2
  // 눕힌 배치: 오른쪽에 위아래로. 기준점이 아래 가장자리이므로 반 칸 내린다.
  const flatRight = CONTENT_RADIUS + PANEL_WORLD_WIDTH / 2 + 0.8
  const flatFar = centered * (PANEL_WORLD_HEIGHT + GAP) - PANEL_WORLD_HEIGHT / 2
  // 세운 배치: 지도 너머에 좌우로
  const uprightRight = centered * (PANEL_WORLD_WIDTH + GAP) + PANEL_SHIFT_RIGHT
  const uprightFar = BEYOND

  useFrame((_, delta) => {
    if (!controls || !root.current || !yaw.current || !tilt.current) return
    const polar = controls.polarAngle
    const target = uprightAmount(polar)
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
    // 방위각: 카메라 쪽을 향하게 돈다
    yaw.current.rotation.y = controls.azimuthAngle
    // 기울기: 눕힘(-90°)과 세움(0°) 사이
    tilt.current.rotation.x = MathUtils.lerp(-Math.PI / 2, 0, t)
  })

  return (
    <group ref={root} position={[0, 0.02, -BEYOND]}>
      <group ref={yaw}>
        <group ref={tilt}>
          <Html transform distanceFactor={DISTANCE_FACTOR} zIndexRange={[20, 0]} style={{ pointerEvents: "auto" }}>
            {/* 아래 가장자리 가운데를 기준점에 맞춘다 */}
            <div style={{ width: PANEL_WIDTH, transform: "translate(0, -50%)" }}>
              {/* filter 를 쓰면 패널 바탕의 backdrop-filter 가 장면을 흐리지 못하므로 위치와 불투명도만 바꾼다.
                  패널 안의 점 → 선 → 글자 등장은 SchematicPanel 에 구현되어 있다. */}
              <motion.div
                initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: reducedMotion ? 0 : MOTION.panel.duration / 1000, ease: EASE_OUT }}
              >
                <SchematicTheme>
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
