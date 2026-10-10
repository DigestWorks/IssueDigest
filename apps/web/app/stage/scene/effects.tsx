import { useRef } from "react"
import { useFrame } from "@react-three/fiber"
import {
  Bloom,
  DepthOfField,
  EffectComposer,
  GodRays,
  Noise,
  ToneMapping,
  Vignette,
} from "@react-three/postprocessing"
import { BlendFunction, KernelSize, ToneMappingMode, type DepthOfFieldEffect } from "postprocessing"
import { Vector3, type Mesh } from "three"

import { useStage } from "../store"
import { focusPoint } from "./registry"

const DEFAULT_TARGET = new Vector3(0, 2.5, 0)

/**
 * 후처리 효과. GodRays 와 DepthOfField 설정은 pmndrs/react-postprocessing
 * 문서(docs/effects/god-rays.mdx, _autodocs/api-reference/DepthOfField.md)를 따른다.
 * GodRays 는 가림 처리를 위해 EffectComposer autoClear={false} 가 필요하다.
 */
export type EffectName = "dof" | "godrays" | "bloom" | "noise" | "vignette"
export const ALL_EFFECTS: EffectName[] = ["dof", "godrays", "bloom", "noise", "vignette"]

export function Effects({
  sun,
  reducedMotion,
  enabled = ALL_EFFECTS,
}: {
  sun: Mesh | null
  reducedMotion: boolean
  /** ?fx=bloom,dof 처럼 효과별로 켜고 끈다(성능 측정용) */
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
    <EffectComposer autoClear={false} multisampling={0}>
      {reducedMotion || !on("dof") ? (
        <></>
      ) : (
        <DepthOfField ref={dofRef} target={[0, 2.5, 0]} focalLength={0.04} bokehScale={2.6} height={540} />
      )}
      {sun && !reducedMotion && on("godrays") ? (
        <GodRays
          sun={sun}
          samples={48}
          density={0.95}
          decay={0.93}
          weight={0.5}
          exposure={0.55}
          clampMax={1}
          width={512}
          height={512}
          kernelSize={KernelSize.SMALL}
          blur
        />
      ) : (
        <></>
      )}
      {on("bloom") ? <Bloom mipmapBlur intensity={0.85} luminanceThreshold={0.55} luminanceSmoothing={0.2} /> : <></>}
      {on("noise") ? <Noise premultiply blendFunction={BlendFunction.SCREEN} opacity={0.035} /> : <></>}
      {on("vignette") ? <Vignette offset={0.25} darkness={0.78} /> : <></>}
      <ToneMapping mode={ToneMappingMode.ACES_FILMIC} />
    </EffectComposer>
  )
}
