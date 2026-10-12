import { describe, expect, it, vi } from "vitest"

import { parseStageEvent, type StageEvent } from "./events"
import { initialStageState, reduceStage } from "./store"

const sample = { label: "샘플", sample: true }
const node = (id: string): StageEvent => ({
  type: "graph.node.add",
  node: { id, type: "bill", label: id, source: sample },
})

const run = (events: StageEvent[]) =>
  events.reduce((s, e, i) => reduceStage(s, e, i), initialStageState)

describe("reduceStage", () => {
  it("탐색 순서(trail)는 초점 이벤트 순서대로 한 번씩 쌓이고 초기화로 비워진다", () => {
    let s = run([node("a"), node("b"), { type: "graph.focus", nodeId: "a" }, { type: "graph.focus", nodeId: "b" }])
    s = reduceStage(s, { type: "graph.focus", nodeId: "a" }, 5)
    s = reduceStage(s, { type: "map.focus", regionId: "11030", label: "용산구" }, 6)
    expect(s.trail.map((t) => `${t.kind}:${t.id}:${t.label}`)).toEqual(["node:a:a", "node:b:b", "region:11030:용산구"])
    s = reduceStage(s, { type: "map.focus", regionId: null }, 7)
    expect(s.focus).toBeNull()
    expect(s.trail).toHaveLength(3)
    expect(reduceStage(s, { type: "stage.reset" }, 8).trail).toEqual([])
  })

  it("엣지 근거 종류는 생략하면 명시(explicit)다", () => {
    const e = parseStageEvent({ type: "graph.edge.add", edge: { id: "ab", source: "a", target: "b" } })
    expect(e?.type === "graph.edge.add" && e.edge.basis).toBe("explicit")
    const f = parseStageEvent({ type: "graph.edge.add", edge: { id: "ab", source: "a", target: "b", basis: "inferred" } })
    expect(f?.type === "graph.edge.add" && f.edge.basis).toBe("inferred")
  })

  it("노드와 엣지를 추가하고 중복은 무시한다", () => {
    const s = run([
      node("a"),
      node("b"),
      node("a"),
      { type: "graph.edge.add", edge: { id: "ab", source: "a", target: "b", basis: "explicit" } },
      { type: "graph.edge.add", edge: { id: "ab", source: "a", target: "b", basis: "explicit" } },
    ])
    expect(s.nodes.map((n) => n.id)).toEqual(["a", "b"])
    expect(s.edges).toHaveLength(1)
    expect(s.nodes[1].addedAt).toBe(1)
  })

  it("양 끝 노드가 없는 엣지는 버린다", () => {
    const s = run([node("a"), { type: "graph.edge.add", edge: { id: "ax", source: "a", target: "x", basis: "explicit" } }])
    expect(s.edges).toHaveLength(0)
  })

  it("초점은 노드·지역·주장 이벤트로 바뀐다", () => {
    let s = run([node("a"), { type: "graph.focus", nodeId: "a" }])
    expect(s.focus).toEqual({ kind: "node", id: "a" })
    s = reduceStage(s, { type: "map.focus", regionId: "11010" }, 9)
    expect(s.focus).toEqual({ kind: "region", id: "11010" })
    s = reduceStage(s, { type: "claim.focus", target: { kind: "node", id: "a" } }, 10)
    expect(s.focus).toEqual({ kind: "node", id: "a" })
    s = reduceStage(s, { type: "map.focus", regionId: null }, 11)
    expect(s.focus).toBeNull()
  })

  it("reset 은 초기 상태로 돌린다", () => {
    const s = run([node("a"), { type: "stage.status", status: "exploring" }, { type: "stage.reset" }])
    expect(s).toEqual(initialStageState)
  })
})

describe("parseStageEvent", () => {
  it("스키마에 맞지 않는 이벤트는 버리고 경고한다", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {})
    expect(parseStageEvent({ type: "graph.node.add", node: { id: "a" } })).toBeNull()
    expect(parseStageEvent({ type: "unknown" })).toBeNull()
    expect(warn).toHaveBeenCalledTimes(2)
    warn.mockRestore()
  })

  it("올바른 이벤트는 통과한다", () => {
    expect(parseStageEvent({ type: "graph.traverse", path: ["a", "b"] })).not.toBeNull()
  })
})
