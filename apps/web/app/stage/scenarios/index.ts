import { electionMapScenario } from "./election-map"
import { ontologyScenario } from "./ontology"
import type { Scenario } from "./types"

export const SCENARIOS: Scenario[] = [ontologyScenario, electionMapScenario]

/** 시나리오에 없는 질문: 근거 부족 상태를 표시한다. */
export const insufficientScenario: Scenario = {
  id: "insufficient",
  prompt: "",
  match: () => true,
  steps: [
    { at: 0, event: { type: "stage.reset" } },
    { at: 0, event: { type: "stage.status", status: "exploring", note: "온톨로지 탐색 중" } },
    {
      at: 1400,
      event: {
        type: "stage.status",
        status: "insufficient",
        note: "이 질문에 답할 근거가 샘플 데이터에 없습니다",
      },
    },
    {
      at: 1400,
      text: "샘플 데이터에서 이 질문에 답할 근거를 찾지 못해 답을 유보합니다. 제안 질문 중 하나를 선택해 보세요.",
    },
  ],
}

export function pickScenario(question: string): Scenario {
  return SCENARIOS.find((s) => s.match(question)) ?? insufficientScenario
}
