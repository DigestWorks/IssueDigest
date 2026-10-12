/** 온톨로지 노드 유형과 화면에 적는 이름. 유형은 색이나 모양이 아니라 보조 글자로 구분한다. */
export const NODE_TYPE_LABEL = {
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
} as const

export type NodeType = keyof typeof NODE_TYPE_LABEL
export const NODE_TYPES = Object.keys(NODE_TYPE_LABEL) as [NodeType, ...NodeType[]]
