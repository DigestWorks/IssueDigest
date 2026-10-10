import { forwardRef } from "react"
import { Grid, Sparkles, SpotLight } from "@react-three/drei"
import type { Mesh } from "three"

import { NEUTRAL } from "~/design/palette"

/**
 * 스테이지 바탕: 지면, 격자, 조명, 볼류메트릭 라이트 광원, 부유 파티클.
 * 데이터가 아닌 요소이므로 모두 무채색이다. 깊이는 명도, 빛, 그림자,
 * 거리 감쇠(fog)로 만든다.
 */
export function Environment({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <>
      <color attach="background" args={[NEUTRAL.void]} />
      <fog attach="fog" args={[NEUTRAL.void, 18, 70]} />

      <ambientLight intensity={0.12} />
      <hemisphereLight args={[NEUTRAL.light, NEUTRAL.void, 0.25]} />
      <directionalLight
        position={[-14, 22, -10]}
        intensity={2.2}
        color={NEUTRAL.light}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-24}
        shadow-camera-right={24}
        shadow-camera-top={24}
        shadow-camera-bottom={-24}
        shadow-bias={-0.0004}
      />
      <pointLight position={[0, 9, 4]} intensity={18} distance={30} color={NEUTRAL.light} />
      {/* 위에서 내려오는 빛내림. 원뿔 형태의 볼류메트릭 조명 */}
      <SpotLight
        position={[1.5, 22, -2]}
        target-position={[0, 0, 0]}
        color={NEUTRAL.light}
        distance={34}
        angle={0.42}
        attenuation={16}
        anglePower={4}
        intensity={60}
        opacity={0.55}
        penumbra={0.8}
      />

      <mesh rotation-x={-Math.PI / 2} position-y={-0.01} receiveShadow>
        <planeGeometry args={[200, 200]} />
        <meshStandardMaterial color={NEUTRAL.ground} roughness={0.92} metalness={0.05} />
      </mesh>
      <Grid
        position-y={0.002}
        args={[200, 200]}
        cellSize={1}
        cellThickness={0.5}
        cellColor={NEUTRAL.grid}
        sectionSize={5}
        sectionThickness={0.9}
        sectionColor={NEUTRAL.lineDim}
        fadeDistance={60}
        fadeStrength={1.6}
        infiniteGrid
      />

      <Sparkles
        count={420}
        scale={[48, 18, 48]}
        position={[0, 8, 0]}
        size={1.6}
        speed={reducedMotion ? 0 : 0.18}
        noise={reducedMotion ? 0 : 0.6}
        opacity={0.45}
        color={NEUTRAL.particle}
      />
    </>
  )
}

/**
 * 볼류메트릭 라이트(GodRays)의 광원. 장면 뒤쪽 위에 둔 밝은 원판이다.
 * 노드와 지도 압출 형상이 이 빛을 가리면서 빛줄기가 생긴다.
 */
export const LightSource = forwardRef<Mesh>(function LightSource(_, ref) {
  return (
    <mesh ref={ref} position={[0, 15, -52]}>
      <circleGeometry args={[2.2, 48]} />
      <meshBasicMaterial color={NEUTRAL.line} fog={false} />
    </mesh>
  )
})
