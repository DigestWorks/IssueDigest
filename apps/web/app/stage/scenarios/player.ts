import type { StageEvent } from "../events"
import type { Scenario } from "./types"

type PlayHandlers = {
  /** 지금까지 누적된 답변 텍스트 */
  onText: (text: string) => void
  onEvent: (event: StageEvent) => void
  signal?: AbortSignal
  /** true 이면 지연 없이 재생한다(동작 줄이기 설정, 테스트) */
  immediate?: boolean
}

const wait = (ms: number, signal?: AbortSignal) =>
  new Promise<void>((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason)
    const id = setTimeout(resolve, ms)
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(id)
        reject(signal.reason)
      },
      { once: true }
    )
  })

/** 시나리오 단계를 시간 순서대로 재생한다. 텍스트는 글자 단위로 흘려보낸다. */
export async function playScenario(scenario: Scenario, h: PlayHandlers) {
  const steps = [...scenario.steps].sort((a, b) => a.at - b.at)
  const start = performance.now()
  let text = ""
  for (const step of steps) {
    if (!h.immediate) {
      const delay = step.at - (performance.now() - start)
      if (delay > 0) await wait(delay, h.signal)
    }
    if ("event" in step) {
      h.onEvent(step.event)
      continue
    }
    if (h.immediate) {
      text += step.text
      h.onText(text)
      continue
    }
    for (const ch of step.text) {
      text += ch
      h.onText(text)
      await wait(14, h.signal)
    }
  }
  return text
}
