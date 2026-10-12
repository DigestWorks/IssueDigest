import { Vector3 } from "three"

import type { FocusTarget } from "../store"

/**
 * 장면 객체의 현재 위치. 그래프 노드는 물리 시뮬레이션이 매 프레임 위치를
 * 바꾸므로 React 상태 대신 이 Map 에 쓴다. 카메라와 피사계 심도가 초점
 * 위치를 여기서 읽는다.
 */
export const nodePositions = new Map<string, Vector3>()
export const regionCentroids = new Map<string, Vector3>()

/** 화면 상태를 전역에서 바꾸지 않고 장면끼리 공유하는 값 */
export const sceneFlags = { dragging: false }

export function focusPoint(focus: FocusTarget | null, out: Vector3): Vector3 | null {
  if (!focus) return null
  const p = focus.kind === "node" ? nodePositions.get(focus.id) : regionCentroids.get(focus.id)
  return p ? out.copy(p) : null
}
