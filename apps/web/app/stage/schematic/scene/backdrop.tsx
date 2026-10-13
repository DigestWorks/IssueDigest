import { useMemo } from "react"
import { Grid } from "@react-three/drei"
import { Color } from "three"

import { FLOOR, type SchematicPalette } from "~/design/tokens"

/**
 * 장면 바탕: 배경색, 거리 감쇠, 바닥 조명, 격자. 지도 페이지와 메인 스테이지가 함께 쓴다.
 * 모든 재질이 조명을 받지 않는 MeshBasic·LineBasic 이므로 조명을 두지 않는다.
 */
export function SceneBackdrop({ theme }: { theme: SchematicPalette }) {
  return (
    <>
      <color attach="background" args={[theme.backdrop]} />
      <fog attach="fog" args={[theme.backdrop, 34, 75]} />
      <SpotFloor center={theme.scene} edge={theme.backdrop} />
      <Grid
        position-y={-0.005}
        args={[120, 120]}
        cellSize={1}
        cellThickness={0.5}
        cellColor={theme.grid}
        sectionSize={4}
        sectionThickness={0.8}
        sectionColor={theme.gridSection}
        // 격자는 카메라가 아니라 장면 중심(원점)에서 멀어질수록 옅어져 바닥 조명 범위 안에만 보인다
        fadeFrom={0}
        fadeDistance={26}
        fadeStrength={1.6}
        infiniteGrid
      />
    </>
  )
}

const FLOOR_SIZE = FLOOR.size
/** 바닥 조명 범위. 값과 설명은 design/tokens.ts 의 FLOOR */
const SPOT = FLOOR

/**
 * 바닥 조명. 지도 중심을 비추는 원형 밝기 분포를 바닥면에 직접 칠한다(광원 물체는 두지 않는다).
 * 회전하면 원근에 따라 밝은 원이 타원으로 바뀌어 바닥면의 방향과 깊이를 읽게 한다.
 * 8비트 출력에서 생기는 밝기 계단은 화면 좌표 잡음(±0.5/255)으로 흩는다.
 * 불투명 바닥이므로 깊이를 기록한다. 아웃포커스는 지도 영역의 깊이를 이 바닥에서 읽는다.
 */
function SpotFloor({ center, edge }: { center: string; edge: string }) {
  const uniforms = useMemo(
    () => ({
      uCenter: { value: new Color(center) },
      uEdge: { value: new Color(edge) },
      uInner: { value: SPOT.inner / (FLOOR_SIZE / 2) },
      uOuter: { value: SPOT.outer / (FLOOR_SIZE / 2) },
    }),
    [center, edge]
  )
  return (
    <mesh rotation-x={-Math.PI / 2} position-y={-0.02} renderOrder={-1}>
      <planeGeometry args={[FLOOR_SIZE, FLOOR_SIZE]} />
      <shaderMaterial
        key={center + edge}
        uniforms={uniforms}
        // 층·선은 반투명이라 깊이를 쓰지 않는다. 아웃포커스가 읽는 깊이는 이 바닥이 채운다.
        vertexShader={`
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          uniform vec3 uCenter;
          uniform vec3 uEdge;
          uniform float uInner;
          uniform float uOuter;
          varying vec2 vUv;
          float rand(vec2 co) { return fract(sin(dot(co, vec2(12.9898, 78.233))) * 43758.5453); }
          void main() {
            float d = distance(vUv, vec2(0.5)) * 2.0;
            float t = smoothstep(uInner, uOuter, d);
            gl_FragColor = vec4(mix(uCenter, uEdge, t), 1.0);
            #include <colorspace_fragment>
            gl_FragColor.rgb += (rand(gl_FragCoord.xy) - 0.5) / 255.0;
          }
        `}
      />
    </mesh>
  )
}

