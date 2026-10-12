import type { Vector3 } from "three"

/**
 * 장면 객체의 현재 위치. 카메라 이동과 아웃포커스 초점이 읽는다.
 * 지도 지역 중심은 지면 좌표로 고정이고, 그래프 노드는 힘 기반 배치가 매 프레임 바꾼다.
 */
export const focusPoints = {
  region: new Map<string, Vector3>(),
  node: new Map<string, Vector3>(),
}
