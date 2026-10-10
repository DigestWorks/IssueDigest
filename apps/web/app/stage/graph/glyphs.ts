/**
 * 그래프 노드 기호. 노드 유형은 색이 아니라 기호의 모양(원·사각형·삼각형·마름모)과
 * 채움 여부로 구분한다. 모두 무채색이다. HUD 범례도 이 정의를 쓴다.
 */
export type Glyph = {
  /** 꼭짓점 수. 원은 48 */
  sides: number
  /** 첫 꼭짓점 각도(rad) */
  start: number
  filled: boolean
  /** 외접원 반지름(장면 단위) */
  size: number
}

const circle = (size: number, filled: boolean): Glyph => ({ sides: 48, start: 0, filled, size })
const square = (size: number, filled: boolean): Glyph => ({ sides: 4, start: Math.PI / 4, filled, size })
const diamond = (size: number, filled: boolean): Glyph => ({ sides: 4, start: 0, filled, size })
const triangle = (size: number, filled: boolean): Glyph => ({ sides: 3, start: Math.PI / 2, filled, size })

export const NODE_GLYPH = {
  issue: circle(0.42, true),
  bill: square(0.38, true),
  member: circle(0.19, true),
  party: circle(0.3, false),
  committee: square(0.32, false),
  meeting: square(0.2, true),
  statistic: triangle(0.27, true),
  document: diamond(0.27, false),
  claim: diamond(0.23, true),
  region: triangle(0.3, false),
} as const satisfies Record<string, Glyph>

export type NodeType = keyof typeof NODE_GLYPH
export const NODE_TYPES = Object.keys(NODE_GLYPH) as [NodeType, ...NodeType[]]

export const NODE_TYPE_LABEL: Record<NodeType, string> = {
  issue: "이슈",
  bill: "법안",
  member: "의원",
  party: "정당",
  committee: "위원회",
  meeting: "회의",
  statistic: "통계",
  document: "문서",
  claim: "주장",
  region: "지역",
}

/** 기호의 꼭짓점(2D, 반지름 1 기준). SVG 범례와 장면 기하가 함께 쓴다. */
export function glyphPoints(g: Glyph, radius = 1): [number, number][] {
  return Array.from({ length: g.sides }, (_, i) => {
    const a = g.start + (i / g.sides) * Math.PI * 2
    return [Math.cos(a) * radius, Math.sin(a) * radius]
  })
}
