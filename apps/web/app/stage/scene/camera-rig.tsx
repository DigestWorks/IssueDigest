import { useEffect, useRef } from "react"
import { CameraControls } from "@react-three/drei"
import { useFrame } from "@react-three/fiber"
import { Vector3 } from "three"

import { useStage } from "../store"
import { focusPoint, nodePositions, sceneFlags } from "./registry"

const HOME_POSITION = new Vector3(0, 10, 24)
const HOME_TARGET = new Vector3(0, 2.5, 0)
const MAP_POSITION = new Vector3(0, 17, 15)
const MAP_TARGET = new Vector3(0, 0, 0)

/**
 * 카메라. 사용자는 회전(왼쪽 드래그), 이동(오른쪽 드래그), 확대·축소(휠)를 한다.
 * 초점이 바뀌면 현재 보는 방향을 유지한 채 대상 쪽으로 이동한다.
 */
export function CameraRig({ reducedMotion }: { reducedMotion: boolean }) {
  const controls = useRef<CameraControls>(null)
  const focus = useStage((s) => s.focus)
  const mapShownAt = useStage((s) => s.map?.shownAt ?? null)
  const empty = useStage((s) => s.nodes.length === 0 && s.map === null)
  const animate = !reducedMotion

  useEffect(() => {
    const c = controls.current
    if (!c || !empty) return
    void c.setLookAt(...HOME_POSITION.toArray(), ...HOME_TARGET.toArray(), animate)
  }, [empty, animate])

  useEffect(() => {
    const c = controls.current
    if (!c || mapShownAt === null) return
    void c.setLookAt(...MAP_POSITION.toArray(), ...MAP_TARGET.toArray(), animate)
  }, [mapShownAt, animate])

  useEffect(() => {
    const c = controls.current
    if (!c || !focus) return
    // 노드 위치는 다음 프레임에 확정될 수 있으므로 한 프레임 뒤에 읽는다.
    const id = requestAnimationFrame(() => {
      const node = focusPoint(focus, new Vector3())
      if (!node) return
      // 노드 초점은 그래프 중심과 노드 사이를 바라봐 주변 맥락이 화면에 남게 한다.
      const p = focus.kind === "node" ? graphCentroid(new Vector3()).lerp(node, 0.6) : node
      const from = c.camera.position.clone().sub(c.getTarget(new Vector3())).normalize()
      const distance = focus.kind === "region" ? 13 : 24
      from.y = Math.max(from.y, focus.kind === "region" ? 0.75 : 0.3)
      from.normalize().multiplyScalar(distance)
      void c.setLookAt(p.x + from.x, p.y + from.y, p.z + from.z, p.x, p.y, p.z, animate)
    })
    return () => cancelAnimationFrame(id)
  }, [focus, animate])

  useFrame(() => {
    if (controls.current) controls.current.enabled = !sceneFlags.dragging
  })

  useEffect(() => {
    // 개발 중 검증 스크립트가 카메라 상태를 읽는다.
    if (import.meta.env.DEV) Object.assign(window, { __stageControls: controls.current })
  }, [])

  return (
    <CameraControls
      ref={controls}
      makeDefault
      smoothTime={0.6}
      minDistance={3}
      maxDistance={60}
      maxPolarAngle={Math.PI * 0.48}
    />
  )
}

function graphCentroid(out: Vector3) {
  out.set(0, 0, 0)
  if (nodePositions.size === 0) return out.copy(HOME_TARGET)
  for (const p of nodePositions.values()) out.add(p)
  return out.divideScalar(nodePositions.size)
}
