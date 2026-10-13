import { useEffect, useRef, type RefObject } from "react"
import { CameraControls } from "@react-three/drei"
import { useFrame } from "@react-three/fiber"
import { MathUtils, Vector3 } from "three"

import { focusPoints } from "~/stage/schematic/scene/registry"
import { useStage } from "~/stage/store"
import { PANEL_SHIFT_RIGHT } from "./panels-in-space"
import { useStageUi, type StageView } from "./ui-store"

type Pose = { position: [number, number, number]; target: [number, number, number] }

/** 지도가 있을 때와 그래프만 있을 때의 보기. 지도 보기 값은 /map 과 같다 */
const MAP_VIEWS: Record<StageView, Pose> = {
  overview: { position: [0, 21, 20], target: [0, 0, 0.6] },
  top: { position: [0, 25, 0.001], target: [0, 0, 0] },
  low: { position: [0, 4.2, 20], target: [0, 1.2, 0] },
}
const GRAPH_VIEWS: Record<StageView, Pose> = {
  overview: { position: [0, 15, 19], target: [0, 0.6, 0] },
  top: { position: [0, 24, 0.001], target: [0, 0, 0] },
  low: { position: [0, 3.6, 18], target: [0, 1.2, 0] },
}
const IDLE: Pose = { position: [0, 18, 24], target: [0, 0, 0] }
/** 결과 패널이 나타났을 때: 지도·그래프와 그 너머에 선 패널이 함께 보이도록 물러선다 */
const PANEL_VIEW: Pose = { position: [0, 13, 27], target: [0, 2.4, -3] }

/**
 * 스테이지 카메라. 왼쪽 끌기로 회전, 오른쪽 끌기로 이동, 휠로 확대·축소한다.
 * - 지도·그래프가 처음 나타나면 그 보기로 옮겨진다. 보기 전환 요청(전체·위에서·낮게)을 따른다.
 * - 초점이 바뀌면 보는 방향을 유지한 채 대상으로 옮겨진다.
 * - 결과 패널이 나타나면 패널까지 보이게 물러서고, 시야를 오른쪽으로 옮긴다(패널 줄과 같은 거리).
 * - 화면 고정 주석에 방위·기울기·거리를 적는다.
 */
export function StageCamera({ readout, reducedMotion }: { readout: RefObject<HTMLSpanElement | null>; reducedMotion: boolean }) {
  const controls = useRef<CameraControls>(null)
  const animate = !reducedMotion
  const empty = useStage((s) => s.nodes.length === 0 && s.map === null)
  const mapAt = useStage((s) => s.choropleth?.appliedAt ?? null)
  const hasNodes = useStage((s) => s.nodes.length > 0)
  const focus = useStage((s) => s.focus)
  const hasPanels = useStage((s) => s.panels.length > 0)
  const view = useStageUi((s) => s.view)

  const go = (p: Pose) => void controls.current?.setLookAt(...p.position, ...p.target, animate)

  useEffect(() => {
    if (empty) go(IDLE)
  }, [empty, animate])

  useEffect(() => {
    if (mapAt !== null) go(MAP_VIEWS.overview)
  }, [mapAt, animate])

  useEffect(() => {
    if (hasNodes && useStage.getState().map === null) go(GRAPH_VIEWS.overview)
  }, [hasNodes, animate])

  useEffect(() => {
    if (view.n === 0) return
    go((useStage.getState().map ? MAP_VIEWS : GRAPH_VIEWS)[view.name])
  }, [view])

  useEffect(() => {
    const c = controls.current
    if (!c || !focus) return
    // 대상 위치가 다음 프레임에 확정될 수 있으므로(그래프 배치, 지도 경계 로드) 한 프레임 뒤에 읽는다
    const id = requestAnimationFrame(() => {
      const node = focusPoints[focus.kind].get(focus.id)
      if (!node) return
      // 노드 초점은 그래프 중심과 노드 사이를 바라봐 주변 맥락(이웃 노드, 결과 패널)이 화면에 남게 한다
      const p = focus.kind === "node" ? graphCentroid(new Vector3()).lerp(node, 0.55) : node.clone()
      const distance = focus.kind === "region" ? 21 : 23
      const from = c.camera.position.clone().sub(c.getTarget(new Vector3())).normalize().multiplyScalar(distance)
      void c.setLookAt(p.x + from.x, from.y + 0.8, p.z + from.z, p.x, 0.8, p.z, animate)
    })
    return () => cancelAnimationFrame(id)
  }, [focus, animate])

  useEffect(() => {
    void controls.current?.setFocalOffset(hasPanels ? PANEL_SHIFT_RIGHT : 0, 0, 0, animate)
    if (hasPanels) go(PANEL_VIEW)
  }, [hasPanels, animate])

  useFrame(() => {
    const c = controls.current
    const el = readout.current
    if (!c || !el) return
    const az = ((MathUtils.radToDeg(-c.azimuthAngle) % 360) + 360) % 360
    const tilt = MathUtils.radToDeg(c.polarAngle)
    el.textContent = `방위 ${String(Math.round(az) % 360).padStart(3, "0")}° · 기울기 ${String(Math.round(tilt)).padStart(2, "0")}° · 거리 ${c.distance.toFixed(1)}`
  })

  useEffect(() => {
    // 개발 중 검증 스크립트가 카메라를 돌린다
    if (import.meta.env.DEV) Object.assign(window, { __stageControls: controls.current })
  }, [])

  return <CameraControls ref={controls} makeDefault smoothTime={0.6} minDistance={6} maxDistance={48} maxPolarAngle={Math.PI * 0.47} />
}

/** 그래프 노드 위치의 평균(지면 좌표) */
function graphCentroid(out: Vector3) {
  out.set(0, 0, 0)
  if (!focusPoints.node.size) return out
  for (const p of focusPoints.node.values()) out.add(p)
  return out.divideScalar(focusPoints.node.size)
}
