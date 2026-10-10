import type { RegionValue, StageEvent } from "../events"
import { sampleSource, type Scenario, type ScenarioStep } from "./types"

/**
 * 3D 지도 샘플 시나리오: 서울시장 선거 지지율.
 * 후보 이름과 수치는 모두 가상이다. 지역 코드는 통계청 2013 센서스용
 * 행정구역 코드(서울 자치구)이며, 지도 경계 파일의 code 속성과 같다.
 */

export const SEOUL_GU: Record<string, string> = {
  "11010": "종로구",
  "11020": "중구",
  "11030": "용산구",
  "11040": "성동구",
  "11050": "광진구",
  "11060": "동대문구",
  "11070": "중랑구",
  "11080": "성북구",
  "11090": "강북구",
  "11100": "도봉구",
  "11110": "노원구",
  "11120": "은평구",
  "11130": "서대문구",
  "11140": "마포구",
  "11150": "양천구",
  "11160": "강서구",
  "11170": "구로구",
  "11180": "금천구",
  "11190": "영등포구",
  "11200": "동작구",
  "11210": "관악구",
  "11220": "서초구",
  "11230": "강남구",
  "11240": "송파구",
  "11250": "강동구",
}

const CANDIDATES = [
  { label: "후보 A", category: 1 },
  { label: "후보 B", category: 0 },
  { label: "후보 C", category: 2 },
]

/** 재현 가능한 샘플 값. 코드 문자열에서 결정적으로 만든다. */
function sampleValue(code: string): RegionValue {
  let h = 0
  for (const ch of code) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  const southEast = ["11220", "11230", "11240", "11250", "11030"].includes(code)
  // 후보 A(0)가 다수 구에서 앞서고, 동남권 5개 구는 후보 B(1)가 앞선다
  const lead = southEast ? 1 : h % 5 === 0 ? 2 : 0
  const margin = 0.15 + ((h >>> 3) % 70) / 100
  const c = CANDIDATES[lead]
  return {
    category: c.category,
    magnitude: Math.min(1, margin),
    label: `${c.label} 우세 · 격차 ${(margin * 12).toFixed(1)}%p`,
  }
}

function buildSteps(): ScenarioStep[] {
  const steps: ScenarioStep[] = []
  const ev = (at: number, event: StageEvent) => steps.push({ at, event })
  const values = Object.fromEntries(Object.keys(SEOUL_GU).map((c) => [c, sampleValue(c)]))
  const source = sampleSource("가상 여론조사", "자치구별 응답")

  ev(0, { type: "stage.reset" })
  ev(0, { type: "stage.status", status: "exploring", note: "지역 데이터 탐색 중" })
  steps.push({ at: 200, text: "샘플 데이터로 서울 자치구별 우세 현황을 표시합니다. " })
  ev(400, { type: "map.show", region: "seoul", level: "gu", title: "서울시장 선거 자치구별 우세 (샘플)" })
  ev(1800, {
    type: "map.choropleth",
    values,
    legend: CANDIDATES.map(({ label, category }) => ({ category, label })),
    source,
  })
  ev(3800, { type: "map.focus", regionId: "11230" })
  ev(5200, { type: "map.focus", regionId: "11110" })
  steps.push({
    at: 5600,
    text:
      "샘플 기준으로 후보 A가 다수 자치구에서 앞서고, 동남권 5개 구는 후보 B가 앞섭니다. " +
      "지도를 회전하거나 기울여 자치구별 격차를 높이로 비교할 수 있습니다.",
  })
  ev(5600, { type: "stage.status", status: "answered" })
  ev(6000, {
    type: "panel.add",
    id: "trend",
    panel: {
      kind: "chart",
      title: "후보별 지지율 추이",
      unit: "%",
      xKey: "week",
      source,
      series: CANDIDATES.map((c, i) => ({ key: `c${i}`, label: c.label, category: c.category })),
      rows: [
        { week: "1주", c0: 34, c1: 31, c2: 12 },
        { week: "2주", c0: 36, c1: 30, c2: 13 },
        { week: "3주", c0: 35, c1: 33, c2: 11 },
        { week: "4주", c0: 38, c1: 32, c2: 12 },
        { week: "5주", c0: 39, c1: 31, c2: 14 },
      ],
    },
  })
  ev(6500, {
    type: "panel.add",
    id: "regions",
    panel: {
      kind: "claims",
      title: "권역별 해석",
      sides: [
        {
          label: "후보 A 우세",
          category: 1,
          claims: [
            regionClaim("11110", "동북권에서 격차가 가장 크다"),
            regionClaim("11160", "서남권 대부분에서 앞선다"),
          ],
        },
        {
          label: "후보 B 우세",
          category: 0,
          claims: [
            regionClaim("11230", "동남권 5개 구에서 앞선다"),
            regionClaim("11030", "용산구는 격차가 작다"),
          ],
        },
      ],
    },
  })
  return steps
}

function regionClaim(code: string, text: string) {
  return {
    id: `claim-${code}`,
    text,
    target: { kind: "region" as const, id: code },
    source: sampleSource("가상 여론조사", SEOUL_GU[code]),
  }
}

export const electionSampleValue = sampleValue

export const electionMapScenario: Scenario = {
  id: "election-map",
  prompt: "서울시장 선거 지지율을 자치구별로 보여 주세요",
  match: (q) => /선거|지지율|서울|자치구|시장/.test(q),
  steps: buildSteps(),
}
