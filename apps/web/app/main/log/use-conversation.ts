import { useCallback, useEffect, useRef, useState } from "react"

import { pickScenario } from "~/stage/scenarios"
import { playScenario } from "~/stage/scenarios/player"
import { useStage, type StageState, type TrailStep } from "~/stage/store"

export type TurnStatus = "exploring" | "answered" | "insufficient" | "stopped"

export type Turn = {
  id: number
  question: string
  answer: string
  status: TurnStatus
  /** 끝난 질문의 탐색 단계와 출처. 진행 중인 질문은 스테이지 상태에서 바로 읽는다 */
  snapshot?: { trail: TrailStep[]; sources: string[] }
}

/** 스테이지 상태에 나타난 출처 이름(노드·지도 값·패널). 같은 이름은 한 번만 적는다 */
export function stageSources(s: StageState): string[] {
  const labels = [
    ...s.nodes.map((n) => n.source.label),
    ...(s.choropleth ? [s.choropleth.source.label] : []),
    ...s.panels.flatMap((p) => ("source" in p.panel ? [p.panel.source.label] : p.panel.sides.flatMap((side) => side.claims.map((c) => c.source.label)))),
  ]
  return [...new Set(labels)]
}

/**
 * 조사 기록 대화. 질문을 받으면 맞는 샘플 시나리오를 재생해 스테이지 이벤트와 답 글자를 흘린다.
 * 새 질문은 진행 중인 재생을 멈추고, 앞 질문의 탐색 단계·출처를 기록에 고정한다(스테이지는 질문마다 초기화된다).
 */
export function useConversation(reducedMotion: boolean) {
  const [turns, setTurns] = useState<Turn[]>([])
  const abort = useRef<AbortController | null>(null)

  useEffect(() => () => abort.current?.abort(), [])

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim()
      if (!q) return
      abort.current?.abort()
      const ac = new AbortController()
      abort.current = ac

      const before = useStage.getState()
      const frozen = { trail: before.trail, sources: stageSources(before) }
      const id = Date.now()
      setTurns((ts) => [
        ...ts.map((t) =>
          t.snapshot ? t : { ...t, snapshot: frozen, status: t.status === "exploring" ? ("stopped" as const) : t.status }
        ),
        { id, question: q, answer: "", status: "exploring" },
      ])

      const update = (patch: Partial<Turn>) => setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, ...patch } : t)))
      try {
        await playScenario(pickScenario(q), {
          onText: (answer) => update({ answer }),
          onEvent: (event) => useStage.getState().dispatch(event),
          signal: ac.signal,
          immediate: reducedMotion,
        })
        update({ status: useStage.getState().status === "insufficient" ? "insufficient" : "answered" })
      } catch {
        // 새 질문으로 멈춘 재생. 상태는 위에서 stopped 로 바뀌었다.
      }
    },
    [reducedMotion]
  )

  return { turns, ask }
}
