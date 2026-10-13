import type { StageEventInput } from "../events"

/** 시나리오 한 단계. at 은 시나리오 시작부터의 시간(ms)이다. */
export type ScenarioStep =
  | { at: number; text: string }
  | { at: number; event: StageEventInput }

export type Scenario = {
  id: string
  /** 빈 채팅에 보여 줄 제안 질문 */
  prompt: string
  /** 사용자 질문이 이 시나리오에 해당하는지 */
  match: (question: string) => boolean
  steps: ScenarioStep[]
}

export const SAMPLE = { label: "샘플 데이터", sample: true } as const

export const sampleSource = (label: string, span?: string) => ({
  label: `${label} (샘플)`,
  span,
  sample: true,
})
