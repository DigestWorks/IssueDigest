import { useMemo, useRef } from "react"
import { Text } from "@react-three/drei"
import { useFrame } from "@react-three/fiber"
import { BufferGeometry, Float32BufferAttribute, type Group } from "three"

import { NEUTRAL } from "~/design/palette"
import { FONT_LIGHT } from "../scene/fonts"

const LETTERS = [
  { label: "N", angle: 0 },
  { label: "E", angle: Math.PI / 2 },
  { label: "S", angle: Math.PI },
  { label: "W", angle: (Math.PI * 3) / 2 },
]

/** 지도 둘레의 방위 고리. 카메라를 회전해도 방향을 알 수 있게 한다. 무채색이다. */
export function CompassRing({
  radius,
  shownAt,
  reducedMotion,
}: {
  radius: number
  shownAt: number
  reducedMotion: boolean
}) {
  const ticks = useMemo(() => {
    const pts: number[] = []
    for (let d = 0; d < 360; d += 5) {
      const a = (d * Math.PI) / 180
      const len = d % 45 === 0 ? 0.6 : d % 15 === 0 ? 0.32 : 0.16
      pts.push(Math.sin(a) * radius, 0, -Math.cos(a) * radius)
      pts.push(Math.sin(a) * (radius + len), 0, -Math.cos(a) * (radius + len))
    }
    const g = new BufferGeometry()
    g.setAttribute("position", new Float32BufferAttribute(pts, 3))
    return g
  }, [radius])
  const group = useRef<Group>(null)

  // 등장: 고리가 작게 시작해 제 크기로 펼쳐진다
  useFrame(() => {
    if (!group.current) return
    const t = reducedMotion ? 1 : Math.min(1, (performance.now() - shownAt) / 1200)
    const e = 1 - (1 - t) ** 3
    group.current.scale.setScalar(0.85 + 0.15 * e)
    group.current.visible = t > 0
  })

  return (
    <group ref={group} position-y={0.01}>
      <mesh rotation-x={-Math.PI / 2}>
        <ringGeometry args={[radius - 0.015, radius + 0.015, 256]} />
        <meshBasicMaterial color={NEUTRAL.lineDim} />
      </mesh>
      <lineSegments geometry={ticks}>
        <lineBasicMaterial color={NEUTRAL.lineDim} />
      </lineSegments>
      {LETTERS.map((l) => (
        <Text
          key={l.label}
          font={FONT_LIGHT}
          position={[Math.sin(l.angle) * (radius + 1.3), 0, -Math.cos(l.angle) * (radius + 1.3)]}
          rotation={[-Math.PI / 2, 0, -l.angle]}
          fontSize={0.9}
          color={NEUTRAL.line}
          anchorX="center"
          anchorY="middle"
        >
          {l.label}
        </Text>
      ))}
    </group>
  )
}
