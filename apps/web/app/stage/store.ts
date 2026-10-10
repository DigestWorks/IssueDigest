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

export type StageState = {
  status: StageStatus
  statusNote?: string
  nodes: (GraphNode & { addedAt: number })[]
  edges: (GraphEdge & { addedAt: number })[]
  traversal: { path: string[]; startedAt: number } | null
  focus: FocusTarget | null
  map: { title: string; shownAt: number } | null
  choropleth: {
    values: Record<string, RegionValue>
    legend: { category: number; label: string }[]
    source: Source
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
    case "graph.focus":
      return { ...state, focus: { kind: "node", id: event.nodeId } }
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
          appliedAt: now,
        },
      }
    case "map.focus":
      return {
        ...state,
        focus: event.regionId ? { kind: "region", id: event.regionId } : null,
      }
    case "panel.add":
      if (state.panels.some((p) => p.id === event.id)) return state
      return { ...state, panels: [...state.panels, { id: event.id, panel: event.panel, addedAt: now }] }
    case "claim.focus":
      return { ...state, focus: event.target }
  }
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
