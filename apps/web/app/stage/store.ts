import { create } from "zustand"

import {
  parseStageEvent,
  type GraphEdge,
  type GraphNode,
  type Panel,
  type RegionValue,
  type Source,
  type StageEvent,
  type StageStatus,
} from "./events"

export type FocusTarget = { kind: "node" | "region"; id: string }

/** 탐색 순서의 한 단계. 조사 기록과 그래프의 단계 번호가 읽는다 */
export type TrailStep = FocusTarget & { label: string }

export type StageState = {
  status: StageStatus
  statusNote?: string
  nodes: (GraphNode & { addedAt: number })[]
  edges: (GraphEdge & { addedAt: number })[]
  traversal: { path: string[]; startedAt: number } | null
  focus: FocusTarget | null
  /** 에이전트가 초점을 옮긴 순서(graph.focus, map.focus). 같은 대상은 한 번만 적는다 */
  trail: TrailStep[]
  map: { title: string; shownAt: number } | null
  choropleth: {
    values: Record<string, RegionValue>
    legend: { category: number; label: string }[]
    source: Source
    highlight?: string[]
    appliedAt: number
  } | null
  panels: { id: string; panel: Panel; addedAt: number }[]
}

export const initialStageState: StageState = {
  status: "idle",
  nodes: [],
  edges: [],
  traversal: null,
  focus: null,
  trail: [],
  map: null,
  choropleth: null,
  panels: [],
}

/** 순수 리듀서. now 는 등장 애니메이션 기준 시각이다. */
export function reduceStage(state: StageState, event: StageEvent, now: number): StageState {
  switch (event.type) {
    case "stage.reset":
      return initialStageState
    case "stage.status":
      return { ...state, status: event.status, statusNote: event.note }
    case "graph.node.add":
      if (state.nodes.some((n) => n.id === event.node.id)) return state
      return { ...state, nodes: [...state.nodes, { ...event.node, addedAt: now }] }
    case "graph.edge.add": {
      const ids = new Set(state.nodes.map((n) => n.id))
      const { edge } = event
      if (!ids.has(edge.source) || !ids.has(edge.target)) return state
      if (state.edges.some((e) => e.id === edge.id)) return state
      return { ...state, edges: [...state.edges, { ...edge, addedAt: now }] }
    }
    case "graph.focus": {
      const label = state.nodes.find((n) => n.id === event.nodeId)?.label ?? event.nodeId
      return {
        ...state,
        focus: { kind: "node", id: event.nodeId },
        trail: addTrail(state.trail, { kind: "node", id: event.nodeId, label }),
      }
    }
    case "graph.traverse":
      return { ...state, traversal: { path: event.path, startedAt: now } }
    case "map.show":
      return { ...state, map: { title: event.title, shownAt: now } }
    case "map.choropleth":
      return {
        ...state,
        choropleth: {
          values: event.values,
          legend: event.legend,
          source: event.source,
          highlight: event.highlight,
          appliedAt: now,
        },
      }
    case "map.focus":
      if (!event.regionId) return { ...state, focus: null }
      return {
        ...state,
        focus: { kind: "region", id: event.regionId },
        trail: addTrail(state.trail, { kind: "region", id: event.regionId, label: event.label ?? event.regionId }),
      }
    case "panel.add":
      if (state.panels.some((p) => p.id === event.id)) return state
      return { ...state, panels: [...state.panels, { id: event.id, panel: event.panel, addedAt: now }] }
    case "claim.focus":
      return { ...state, focus: event.target }
  }
}

function addTrail(trail: TrailStep[], step: TrailStep) {
  return trail.some((t) => t.kind === step.kind && t.id === step.id) ? trail : [...trail, step]
}

type StageStore = StageState & {
  dispatch: (input: unknown) => void
  setFocus: (focus: FocusTarget | null) => void
}

export const useStage = create<StageStore>((set) => ({
  ...initialStageState,
  dispatch: (input) => {
    const event = parseStageEvent(input)
    if (!event) return
    set((s) => reduceStage(s, event, performance.now()))
  },
  setFocus: (focus) => set({ focus }),
}))
