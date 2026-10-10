import { useRef } from "react"
import { useFrame } from "@react-three/fiber"
import { DepthOfField, EffectComposer, Vignette } from "@react-three/postprocessing"
import type { DepthOfFieldEffect } from "postprocessing"
import { Vector3 } from "three"

import { useStage } from "../store"
import { focusPoint } from "./registry"

const DEFAULT_TARGET = new Vector3(0, 2.5, 0)

export type EffectName = "dof" | "vignette"
export const ALL_EFFECTS: EffectName[] = ["dof", "vignette"]

/**
 * 후처리 효과. 흰 배경에서는 Bloom 이 화면 전체를 번지게 하므로 쓰지 않는다.
 * DepthOfField 설정은 pmndrs/react-postprocessing 문서
 * (_autodocs/api-reference/DepthOfField.md)를 따른다.
 */
export function Effects({
  reducedMotion,
  enabled = ALL_EFFECTS,
}: {
  reducedMotion: boolean
  /** ?fx=dof 처럼 효과별로 켜고 끈다(성능 측정용) */
  enabled?: EffectName[]
}) {
  const on = (name: EffectName) => enabled.includes(name)
  const dofRef = useRef<DepthOfFieldEffect>(null)
  const target = useRef(new Vector3().copy(DEFAULT_TARGET))
  const scratch = useRef(new Vector3())

  // 초점 대상이 움직이므로(물리 시뮬레이션) 매 프레임 따라간다.
  useFrame((_, delta) => {
    const focus = useStage.getState().focus
    const p = focusPoint(focus, scratch.current) ?? DEFAULT_TARGET
    target.current.lerp(p, 1 - Math.exp(-delta * 4))
    dofRef.current?.target?.copy(target.current)
  })

  return (
    <EffectComposer multisampling={4}>
      {reducedMotion || !on("dof") ? (
        <></>
      ) : (
        <DepthOfField ref={dofRef} target={[0, 2.5, 0]} focalLength={0.06} bokehScale={1.1} height={540} />
      )}
      {on("vignette") ? <Vignette offset={0.35} darkness={0.22} /> : <></>}
    </EffectComposer>
  )
}
