import { Grid, Sparkles } from "@react-three/drei"

import { NEUTRAL } from "~/design/palette"

/**
 * 스테이지 바탕: 흰 지면, 격자, 조명, 부유 파티클.
 * 데이터가 아닌 요소이므로 모두 무채색이다. 깊이는 명도 차, 부드러운 그림자,
 * 거리 감쇠(fog)로 만든다. 화면에 보이는 광원 물체는 두지 않는다.
 */
export function Environment({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <>
      <color attach="background" args={[NEUTRAL.background]} />
      <fog attach="fog" args={[NEUTRAL.background, 26, 80]} />

      <ambientLight intensity={1.1} />
      <hemisphereLight args={["#ffffff", "#d8d8d8", 0.9]} />
      <directionalLight
        position={[-12, 24, 10]}
        intensity={1.6}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-26}
        shadow-camera-right={26}
        shadow-camera-top={26}
        shadow-camera-bottom={-26}
        shadow-radius={8}
        shadow-bias={-0.0004}
      />

      {/* 지면은 배경과 같은 흰색이고, 그림자만 받는다 */}
      <mesh rotation-x={-Math.PI / 2} position-y={-0.01} receiveShadow>
        <planeGeometry args={[200, 200]} />
        <shadowMaterial transparent opacity={0.1} />
      </mesh>
      <Grid
        position-y={0.002}
        args={[200, 200]}
        cellSize={1}
        cellThickness={0.6}
        cellColor={NEUTRAL.grid}
        sectionSize={5}
        sectionThickness={1}
        sectionColor={NEUTRAL.gridSection}
        fadeDistance={55}
        fadeStrength={1.4}
        infiniteGrid
      />

      <Sparkles
        count={260}
        scale={[48, 16, 48]}
        position={[0, 7, 0]}
        size={1.1}
        speed={reducedMotion ? 0 : 0.15}
        noise={reducedMotion ? 0 : 0.5}
        opacity={0.5}
        color={NEUTRAL.particle}
      />
    </>
  )
}
