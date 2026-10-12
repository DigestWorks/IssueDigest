import { useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { ChromaticAberration, DepthOfField, EffectComposer } from "@react-three/postprocessing"
import type { DepthOfFieldEffect } from "postprocessing"
import { Vector2, Vector3 } from "three"

import { MAP_EFFECTS } from "~/design/tokens"

/**
 * 후처리: 아웃포커스와 색수차(홀로그램 표현, 2026-10-11 민재 요청).
 * - 아웃포커스: target 이 돌려주는 위치(선택 대상, 없으면 장면 중심)에 초점을 맞춘다. 흐림 정도는 초점 거리와의 차이에 따라
 *   0 에서 FOCUS_RANGE(장면 단위)까지 smoothstep 으로 커진다(postprocessing 6.39 CircleOfConfusionMaterial).
 *   선택 주석과 화면 고정 주석은 DOM 이라 흐려지지 않는다.
 * - 색수차: 화면 가장자리로 갈수록 빨강·파랑 성분이 어긋난다(radialModulation).
 * 설정은 @react-three/postprocessing 3.x 의 DepthOfField·ChromaticAberration 속성을 따른다.
 */
const FOCUS_RANGE = MAP_EFFECTS.focusRange
const CA_OFFSET = new Vector2(...MAP_EFFECTS.caOffset)
const SCENE_CENTER = new Vector3(0, 0.6, 0)

export function SceneEffects({ target: read }: { target: (out: Vector3) => Vector3 | null }) {
  const dof = useRef<DepthOfFieldEffect>(null)
  const target = useRef(SCENE_CENTER.clone())
  const goal = useRef(new Vector3())
  const scratch = useRef(new Vector3())

  useFrame((_, delta) => {
    const c = read(scratch.current)
    goal.current.copy(c ?? SCENE_CENTER).setY(0.6)
    target.current.lerp(goal.current, 1 - Math.exp(-delta * 4))
    dof.current?.target?.copy(target.current)
  })

  return (
    <EffectComposer multisampling={4}>
      {/* 흐림 계산을 화면 해상도 그대로 한다. 낮은 해상도(예: 세로 540px)로 계산해 늘리면
          선 가장자리에서 흐림 경계가 계단처럼 보인다 */}
      <DepthOfField ref={dof} target={SCENE_CENTER} focusRange={FOCUS_RANGE} bokehScale={MAP_EFFECTS.bokehScale} resolutionScale={1} />
      <ChromaticAberration offset={CA_OFFSET} radialModulation modulationOffset={MAP_EFFECTS.caModulationOffset} />
    </EffectComposer>
  )
}

