import type { GraphNode, StageEventInput } from "../events"
import { sampleSource, type Scenario, type ScenarioStep } from "./types"

/**
 * 온톨로지 탐색 샘플 시나리오.
 * 법안·인물·정당·위원회 이름은 모두 가상이다.
 */

type N = Omit<GraphNode, "source"> & { span?: string }

const nodes: N[] = [
  { id: "issue", type: "issue", label: "지역 돌봄 공백", detail: "샘플 이슈" },
  { id: "bill", type: "bill", label: "샘플 법안 A", detail: "지역 돌봄 지원 확대안 (가상)" },
  { id: "m1", type: "member", label: "의원 가", detail: "대표발의" },
  { id: "m2", type: "member", label: "의원 나", detail: "공동발의" },
  { id: "m3", type: "member", label: "의원 다", detail: "공동발의" },
  { id: "m4", type: "member", label: "의원 라", detail: "공동발의" },
  { id: "m5", type: "member", label: "의원 마", detail: "반대 토론" },
  { id: "p1", type: "party", label: "정당 갑" },
  { id: "p2", type: "party", label: "정당 을" },
  { id: "cmt", type: "committee", label: "샘플 상임위원회" },
  { id: "mt1", type: "meeting", label: "제1차 법안심사소위", detail: "샘플 회의" },
  { id: "mt2", type: "meeting", label: "제2차 법안심사소위", detail: "샘플 회의" },
  { id: "mt3", type: "meeting", label: "전체회의", detail: "샘플 회의" },
  { id: "c1", type: "claim", label: "돌봄 인력 부족 해소", span: "제1차 소위 발언 12" },
  { id: "c2", type: "claim", label: "지자체 재정 부담 우려", span: "제1차 소위 발언 27" },
  { id: "c3", type: "claim", label: "단계적 시행 필요", span: "제2차 소위 발언 8" },
  { id: "c4", type: "claim", label: "수혜 대상 확대", span: "전체회의 발언 3" },
  { id: "s1", type: "statistic", label: "돌봄 대기 아동 수", detail: "샘플 통계" },
  { id: "s2", type: "statistic", label: "돌봄 시설 수 추이", detail: "샘플 통계" },
  { id: "s3", type: "statistic", label: "지자체 돌봄 예산", detail: "샘플 통계" },
  { id: "d1", type: "document", label: "부처 보도자료", detail: "샘플 문서" },
  { id: "d2", type: "document", label: "검토보고서", detail: "샘플 문서" },
  { id: "r1", type: "region", label: "수도권" },
  { id: "r2", type: "region", label: "비수도권" },
]

const edges: [string, string, string][] = [
  ["issue", "bill", "다루는 법안"],
  ["m1", "bill", "대표발의"],
  ["m2", "bill", "공동발의"],
  ["m3", "bill", "공동발의"],
  ["m4", "bill", "공동발의"],
  ["m1", "p1", "소속"],
  ["m2", "p1", "소속"],
  ["m3", "p2", "소속"],
  ["m4", "p1", "소속"],
  ["m5", "p2", "소속"],
  ["bill", "cmt", "회부"],
  ["bill", "mt1", "심사"],
  ["bill", "mt2", "심사"],
  ["bill", "mt3", "의결"],
  ["mt1", "cmt", "소속 회의"],
  ["mt2", "cmt", "소속 회의"],
  ["mt3", "cmt", "소속 회의"],
  ["m1", "c1", "주장"],
  ["m5", "c2", "주장"],
  ["m3", "c3", "주장"],
  ["m2", "c4", "주장"],
  ["c1", "mt1", "발언 회의"],
  ["c2", "mt1", "발언 회의"],
  ["c3", "mt2", "발언 회의"],
  ["c4", "mt3", "발언 회의"],
  ["c1", "s1", "근거"],
  ["c2", "s3", "근거"],
  ["c4", "s2", "근거"],
  ["d1", "bill", "언급"],
  ["d2", "bill", "검토"],
  ["d2", "c2", "인용"],
  ["s1", "r1", "지역"],
  ["s1", "r2", "지역"],
  ["s3", "r2", "지역"],
  ["issue", "r1", "지역"],
  ["issue", "r2", "지역"],
]

/**
 * 모델이 추론한 관계(점선). 주장과 통계 사이의 「근거」, 이슈·통계와 지역 사이의 「지역」은
 * 원천 문서에 직접 적힌 연결이 아니라 탐색 중에 이어 붙인 관계로 둔다(샘플).
 */
const INFERRED = new Set(["근거", "지역"])

const byId = new Map(nodes.map((n) => [n.id, n]))

/** 탐색 순서. 각 단계에서 노드를 추가하고, 이미 있는 노드와의 엣지를 잇는다. */
const exploration: { ids: string[]; focus: string; path?: string[] }[] = [
  { ids: ["issue"], focus: "issue" },
  { ids: ["bill", "r1", "r2"], focus: "bill", path: ["issue", "bill"] },
  { ids: ["m1", "m2", "m3", "m4"], focus: "m1", path: ["bill", "m1"] },
  { ids: ["p1", "p2", "m5"], focus: "p1", path: ["m1", "p1"] },
  { ids: ["cmt", "mt1", "mt2", "mt3"], focus: "mt1", path: ["bill", "mt1", "cmt"] },
  { ids: ["c1", "c2", "c3", "c4"], focus: "c2", path: ["mt1", "c2", "m5"] },
  { ids: ["s1", "s2", "s3"], focus: "s1", path: ["c1", "s1", "r1"] },
  { ids: ["d1", "d2"], focus: "d2", path: ["d2", "c2", "s3"] },
]

function buildSteps(): ScenarioStep[] {
  const steps: ScenarioStep[] = []
  const present = new Set<string>()
  const ev = (at: number, event: StageEventInput) => steps.push({ at, event })

  ev(0, { type: "stage.reset" })
  ev(0, { type: "stage.status", status: "exploring", note: "온톨로지 탐색 중" })
  steps.push({ at: 200, text: "샘플 데이터로 탐색합니다. " })

  let t = 500
  exploration.forEach((stage, i) => {
    for (const id of stage.ids) {
      const n = byId.get(id)!
      const { span, ...rest } = n
      ev(t, { type: "graph.node.add", node: { ...rest, source: sampleSource(n.detail ?? n.label, span) } })
      present.add(id)
      for (const [s, d, label] of edges) {
        if ((s === id || d === id) && present.has(s) && present.has(d)) {
          ev(t + 60, {
            type: "graph.edge.add",
            edge: { id: `${s}-${d}`, source: s, target: d, label, basis: INFERRED.has(label) ? "inferred" : "explicit" },
          })
        }
      }
      t += 140
    }
    if (stage.path) ev(t, { type: "graph.traverse", path: stage.path })
    ev(t + 100, { type: "graph.focus", nodeId: stage.focus })
    t += i === 0 ? 900 : 1300
  })

  steps.push({
    at: t,
    text:
      "샘플 법안 A는 의원 가가 대표발의했고, 소위원회 두 차례와 전체회의를 거쳤습니다. " +
      "쟁점은 돌봄 인력 부족 해소와 지자체 재정 부담입니다. 오른쪽에서 주장과 근거를 선택하면 해당 노드로 이동합니다.",
  })
  ev(t, { type: "stage.status", status: "answered" })
  ev(t + 300, {
    type: "panel.add",
    id: "timeline",
    panel: {
      kind: "timeline",
      title: "샘플 법안 A 처리 경과",
      source: sampleSource("의안 경과"),
      items: [
        { date: "2026-03-04", label: "발의", nodeId: "bill" },
        { date: "2026-04-11", label: "상임위 회부", nodeId: "cmt" },
        { date: "2026-05-20", label: "제1차 소위 심사", nodeId: "mt1" },
        { date: "2026-06-17", label: "제2차 소위 심사", nodeId: "mt2" },
        { date: "2026-07-08", label: "전체회의 의결", nodeId: "mt3" },
      ],
    },
  })
  ev(t + 700, {
    type: "panel.add",
    id: "claims",
    panel: {
      kind: "claims",
      title: "쟁점별 주장 비교",
      sides: [
        {
          label: "찬성",
          category: 2,
          claims: [
            claim("c1", "돌봄 인력 부족을 해소해야 한다"),
            claim("c4", "수혜 대상을 넓혀야 한다"),
          ],
        },
        {
          label: "신중",
          category: 0,
          claims: [
            claim("c2", "지자체 재정 부담이 커진다"),
            claim("c3", "단계적으로 시행해야 한다"),
          ],
        },
      ],
    },
  })
  ev(t + 1100, {
    type: "panel.add",
    id: "stat",
    panel: {
      kind: "chart",
      title: "돌봄 대기 아동 수",
      unit: "명",
      xKey: "year",
      source: sampleSource("돌봄 통계"),
      series: [
        { key: "capital", label: "수도권", category: 1 },
        { key: "local", label: "비수도권", category: 3 },
      ],
      rows: [
        { year: "2021", capital: 4200, local: 3100 },
        { year: "2022", capital: 4800, local: 3300 },
        { year: "2023", capital: 5300, local: 3900 },
        { year: "2024", capital: 5100, local: 4400 },
        { year: "2025", capital: 5600, local: 4700 },
      ],
    },
  })
  return steps
}

function claim(nodeId: string, text: string) {
  const n = byId.get(nodeId)!
  return {
    id: nodeId,
    text,
    target: { kind: "node" as const, id: nodeId },
    source: sampleSource("회의록", n.span),
  }
}

export const ontologyScenario: Scenario = {
  id: "ontology",
  prompt: "샘플 법안 A는 누가 발의했고 어떤 논의를 거쳤나요?",
  match: (q) => /법안|발의|논의|국회|돌봄/.test(q),
  steps: buildSteps(),
}
