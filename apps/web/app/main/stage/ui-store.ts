import { create } from "zustand"

export type StageView = "overview" | "top" | "low"

/**
 * 스테이지 화면 고정 주석(DOM)과 3D 장면이 함께 쓰는 화면 상태.
 * 장면은 지연 로드되는 Canvas 안에 있으므로 속성 대신 이 저장소로 주고받는다.
 */
export const useStageUi = create<{
  /** 포인터가 가리키는 대상 */
  hovered: { kind: "node" | "region"; id: string; label: string } | null
  /** 보기 전환 요청. n 이 바뀔 때마다 카메라가 그 보기로 옮겨진다 */
  view: { name: StageView; n: number }
  setHovered: (h: { kind: "node" | "region"; id: string; label: string } | null) => void
  requestView: (name: StageView) => void
}>((set) => ({
  hovered: null,
  view: { name: "overview", n: 0 },
  setHovered: (hovered) => set({ hovered }),
  requestView: (name) => set((s) => ({ view: { name, n: s.view.n + 1 } })),
}))
