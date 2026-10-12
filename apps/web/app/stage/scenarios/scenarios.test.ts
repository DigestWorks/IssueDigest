import { describe, expect, it } from "vitest"

import { StageEvent } from "../events"
import { initialStageState, reduceStage } from "../store"
import { insufficientScenario, pickScenario, SCENARIOS } from "./index"
import { playScenario } from "./player"

const all = [...SCENARIOS, insufficientScenario]

describe("샘플 시나리오", () => {
  it.each(all.map((s) => [s.id, s] as const))("%s 의 모든 이벤트가 스키마를 통과한다", (_, s) => {
    for (const step of s.steps) {
      if ("event" in step) expect(StageEvent.safeParse(step.event).success).toBe(true)
    }
  })

  it.each(all.map((s) => [s.id, s] as const))("%s 답변에 샘플 표시가 있다", (_, s) => {
    const text = s.steps.map((x) => ("text" in x ? x.text : "")).join("")
    expect(text).toContain("샘플")
  })

  it("탐색 시나리오를 재생하면 노드·엣지·패널이 쌓이고 답변 상태가 된다", async () => {
    let state = initialStageState
    let text = ""
    await playScenario(SCENARIOS[0], {
      immediate: true,
      onText: (t) => (text = t),
      // 실제 스테이지와 같이 검증·기본값 채우기를 거친 이벤트를 리듀서에 넣는다
      onEvent: (e) => (state = reduceStage(state, StageEvent.parse(e), 0)),
    })
    expect(state.nodes.length).toBeGreaterThan(20)
    expect(state.edges.length).toBeGreaterThan(20)
    expect(state.panels.map((p) => p.panel.kind).sort()).toEqual(["chart", "claims", "timeline"])
    expect(state.status).toBe("answered")
    expect(text.length).toBeGreaterThan(0)
  })

  it("질문을 시나리오에 매칭하고, 매칭되지 않으면 근거 부족으로 간다", () => {
    expect(pickScenario("서울시장 선거 지지율").id).toBe("election-map")
    expect(pickScenario("이 법안 누가 발의했어?").id).toBe("ontology")
    expect(pickScenario("오늘 날씨 어때").id).toBe("insufficient")
  })
})

describe("지도 시나리오 데이터 일관성", () => {
  it("주장 패널의 입장과 해당 지역의 우세 후보가 같다", async () => {
    const { electionMapScenario, electionSampleValue } = await import("./election-map")
    for (const step of electionMapScenario.steps) {
      if (!("event" in step) || step.event.type !== "panel.add" || step.event.panel.kind !== "claims") continue
      for (const side of step.event.panel.sides) {
        for (const c of side.claims) {
          expect(electionSampleValue(c.target.id).category, c.target.id).toBe(side.category)
        }
      }
    }
  })
})
