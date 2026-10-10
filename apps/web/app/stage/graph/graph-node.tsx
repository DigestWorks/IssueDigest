import { useMemo, useRef } from "react"
import { Billboard, Text } from "@react-three/drei"
import { useFrame, type ThreeEvent } from "@react-three/fiber"
import { Color, type Group, type Mesh } from "three"

import { NEUTRAL, nodeColor } from "~/design/palette"
import type { GraphNode } from "../events"
import { FONT_LIGHT, FONT_MEDIUM } from "../scene/fonts"

const RADIUS: Partial<Record<GraphNode["type"], number>> = {
  issue: 0.55,
  bill: 0.46,
  party: 0.38,
  committee: 0.36,
}
const ENTER_MS = 700

type Props = {
  node: GraphNode & { addedAt: number }
  focused: boolean
  reducedMotion: boolean
  registerGroup: (g: Group | null) => void
  onPointerDown: (e: ThreeEvent<PointerEvent>) => void
  onPointerMove: (e: ThreeEvent<PointerEvent>) => void
  onPointerUp: (e: ThreeEvent<PointerEvent>) => void
}

/**
 * 그래프 노드. 구의 색은 노드 유형(데이터)을 나타낸다.
 * 선택 표시는 화면 상태이므로 무채색 고리로 그린다.
 */
export function GraphNodeMesh({ node, focused, reducedMotion, registerGroup, ...handlers }: Props) {
  const radius = RADIUS[node.type] ?? 0.26
  const color = useMemo(() => new Color(nodeColor(node.type)), [node.type])
  const scaleRef = useRef<Group>(null)
  const ring = useRef<Mesh>(null)

  useFrame((state) => {
    const g = scaleRef.current
    if (!g) return
    const t = reducedMotion ? 1 : Math.min(1, (performance.now() - node.addedAt) / ENTER_MS)
    g.scale.setScalar(easeOutBack(t))
    if (ring.current) {
      const pulse = reducedMotion ? 1 : 1 + 0.06 * Math.sin(state.clock.elapsedTime * 3)
      ring.current.scale.setScalar(pulse)
    }
  })

  return (
    <group ref={registerGroup}>
      <group ref={scaleRef} scale={0}>
        <mesh
          castShadow
          onPointerDown={handlers.onPointerDown}
          onPointerMove={handlers.onPointerMove}
          onPointerUp={handlers.onPointerUp}
          onPointerOver={() => (document.body.style.cursor = "grab")}
          onPointerOut={() => (document.body.style.cursor = "")}
        >
          <sphereGeometry args={[radius, 32, 32]} />
          <meshStandardMaterial
            color={color}
            emissive={color}
            emissiveIntensity={focused ? 2.2 : 0.75}
            roughness={0.35}
            metalness={0.1}
          />
        </mesh>
        <mesh scale={1.9}>
          <sphereGeometry args={[radius, 16, 16]} />
          <meshBasicMaterial color={color} transparent opacity={focused ? 0.16 : 0.07} depthWrite={false} />
        </mesh>
        <Billboard>
          {focused ? (
            <mesh ref={ring}>
              <ringGeometry args={[radius * 1.9, radius * 1.9 + 0.035, 64]} />
              <meshBasicMaterial color={NEUTRAL.light} toneMapped={false} transparent opacity={0.9} />
            </mesh>
          ) : null}
          <Text
            font={focused ? FONT_MEDIUM : FONT_LIGHT}
            position={[0, radius + 0.34, 0]}
            fontSize={focused ? 0.34 : 0.24}
            letterSpacing={0.04}
            color={focused ? NEUTRAL.light : NEUTRAL.line}
            anchorX="center"
            anchorY="bottom"
            outlineWidth={0.012}
            outlineColor={NEUTRAL.void}
          >
            {node.label}
          </Text>
          {focused && node.detail ? (
            <Text
              font={FONT_LIGHT}
              position={[0, -radius - 0.28, 0]}
              fontSize={0.18}
              letterSpacing={0.06}
              color={NEUTRAL.lineDim}
              anchorX="center"
              anchorY="top"
            >
              {node.detail}
            </Text>
          ) : null}
        </Billboard>
      </group>
    </group>
  )
}

function easeOutBack(t: number) {
  const c1 = 1.70158
  const c3 = c1 + 1
  return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2
}
