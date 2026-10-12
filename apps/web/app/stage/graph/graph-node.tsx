import { useMemo, useRef } from "react"
import { Billboard, Text } from "@react-three/drei"
import { useFrame, type ThreeEvent } from "@react-three/fiber"
import {
  BufferGeometry,
  CircleGeometry,
  RingGeometry,
  type Group,
} from "three"

import { NEUTRAL } from "~/design/palette"
import type { GraphNode } from "../events"
import { FONT_LIGHT, FONT_MEDIUM } from "../scene/fonts"
import { NODE_GLYPH, NODE_TYPE_LABEL, type Glyph } from "./glyphs"

const ENTER_MS = 600
const STROKE = 0.045
const MUTED = "#a3a3a3"

type Props = {
  node: GraphNode & { addedAt: number }
  focused: boolean
  /** 초점이거나 현재 탐색 경로 위에 있는 노드 */
  active: boolean
  reducedMotion: boolean
  registerGroup: (g: Group | null) => void
  onPointerDown: (e: ThreeEvent<PointerEvent>) => void
  onPointerMove: (e: ThreeEvent<PointerEvent>) => void
  onPointerUp: (e: ThreeEvent<PointerEvent>) => void
}

/**
 * 그래프 노드. 카메라를 향한 평면 기호로 그리고, 유형은 기호 모양으로 구분한다.
 * 색은 쓰지 않는다. 초점과 탐색 경로 위 노드는 검정, 나머지는 회색이다.
 * 노드에서 지면까지 수직선을 내려 공간 위치를 읽게 한다.
 */
export function GraphNodeMesh({ node, focused, active, reducedMotion, registerGroup, ...handlers }: Props) {
  const glyph = NODE_GLYPH[node.type]
  const geometry = useMemo(() => glyphGeometry(glyph), [glyph])
  const scaleRef = useRef<Group>(null)
  const ring = useRef<Group>(null)
  const drop = useRef<Group>(null)
  const ink = focused || active ? NEUTRAL.ink : MUTED
  // 초점 고리 바깥에 라벨을 둔다
  const labelX = glyph.size + (focused ? 0.34 : 0.18)

  useFrame((state) => {
    const g = scaleRef.current
    if (!g) return
    const t = reducedMotion ? 1 : Math.min(1, (performance.now() - node.addedAt) / ENTER_MS)
    g.scale.setScalar(easeOutBack(t))
    if (ring.current) {
      const pulse = reducedMotion ? 1 : 1 + 0.08 * Math.sin(state.clock.elapsedTime * 3)
      ring.current.scale.setScalar(pulse)
    }
    // 지면까지 내려가는 수직선: 그룹의 월드 높이만큼 늘린다
    const parent = g.parent
    if (drop.current && parent) {
      const h = Math.max(0.001, parent.position.y)
      drop.current.scale.set(1, h, 1)
      drop.current.position.y = -h / 2
    }
  })

  return (
    <group ref={registerGroup}>
      <group ref={drop}>
        <mesh>
          <cylinderGeometry args={[0.006, 0.006, 1, 4]} />
          <meshBasicMaterial color={focused || active ? NEUTRAL.lineDim : NEUTRAL.grid} />
        </mesh>
      </group>
      <group ref={scaleRef} scale={0}>
        <Billboard>
          {/* 포인터 판정용 투명 원 */}
          <mesh
            onPointerDown={handlers.onPointerDown}
            onPointerMove={handlers.onPointerMove}
            onPointerUp={handlers.onPointerUp}
            onPointerOver={() => (document.body.style.cursor = "grab")}
            onPointerOut={() => (document.body.style.cursor = "")}
          >
            <circleGeometry args={[Math.max(glyph.size, 0.3) * 1.4, 16]} />
            <meshBasicMaterial transparent opacity={0} depthWrite={false} />
          </mesh>
          {/* 엣지 선보다 나중에 그려 선이 기호 위로 지나가지 않게 한다 */}
          <mesh geometry={geometry} renderOrder={10}>
            <meshBasicMaterial color={ink} transparent />
          </mesh>
          {focused ? (
            <group ref={ring}>
              <mesh renderOrder={10}>
                <ringGeometry args={[glyph.size + 0.16, glyph.size + 0.19, 64]} />
                <meshBasicMaterial color={NEUTRAL.ink} transparent />
              </mesh>
            </group>
          ) : null}
          <Text
            font={focused ? FONT_MEDIUM : FONT_LIGHT}
            position={[labelX, 0.02, 0]}
            fontSize={focused ? 0.3 : 0.22}
            letterSpacing={0.02}
            color={focused || active ? NEUTRAL.ink : NEUTRAL.lineDim}
            anchorX="left"
            anchorY="bottom"
          >
            {node.label}
          </Text>
          <Text
            font={FONT_LIGHT}
            position={[labelX, -0.02, 0]}
            fontSize={0.13}
            letterSpacing={0.12}
            color={NEUTRAL.lineDim}
            anchorX="left"
            anchorY="top"
          >
            {focused && node.detail ? `${NODE_TYPE_LABEL[node.type]} · ${node.detail}` : NODE_TYPE_LABEL[node.type]}
          </Text>
        </Billboard>
      </group>
    </group>
  )
}

/** 채움 기호는 다각형, 외곽선 기호는 같은 모양의 고리로 만든다. */
function glyphGeometry(g: Glyph): BufferGeometry {
  if (g.filled) return new CircleGeometry(g.size, g.sides, g.start)
  if (g.sides > 8) return new RingGeometry(g.size - STROKE, g.size, g.sides)
  // 꼭짓점이 적은 고리는 RingGeometry 의 thetaStart 로 회전한다
  return new RingGeometry(g.size - STROKE * 1.4, g.size, g.sides, 1, g.start)
}

function easeOutBack(t: number) {
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
}
