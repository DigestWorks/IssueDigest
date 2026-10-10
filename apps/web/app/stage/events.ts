import { z } from "zod"

import { NODE_TYPE_COLOR_INDEX, type NodeType } from "~/design/palette"

/**
 * 시각화 스테이지가 받는 이벤트.
 *
 * 스테이지는 이 이벤트만으로 상태를 바꾼다. 지금은 샘플 시나리오가 이벤트를
 * 보내고, 이후 실제 에이전트가 같은 스키마를 도구 인자로 보낸다.
 */

const nodeTypes = Object.keys(NODE_TYPE_COLOR_INDEX) as [NodeType, ...NodeType[]]

/** 출처. 샘플 데이터는 sample=true 로 표시한다. */
export const Source = z.object({
  label: z.string(),
  url: z.string().optional(),
  span: z.string().optional(),
  retrievedAt: z.string().optional(),
  sample: z.boolean(),
})

export const GraphNode = z.object({
  id: z.string(),
  type: z.enum(nodeTypes),
  label: z.string(),
  detail: z.string().optional(),
  source: Source,
})

export const GraphEdge = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  label: z.string().optional(),
})

export const RegionValue = z.object({
  /** 데이터 팔레트 범주 번호 */
  category: z.number().int().min(0),
  /** 0~1 로 정규화한 크기. 압출 높이에 쓴다 */
  magnitude: z.number().min(0).max(1),
  label: z.string(),
})

export const Claim = z.object({
  id: z.string(),
  text: z.string(),
  /** 근거 위치. 그래프 노드 ID 또는 지역 코드 */
  target: z.object({ kind: z.enum(["node", "region"]), id: z.string() }),
  source: Source,
})

const ChartPanel = z.object({
  kind: z.literal("chart"),
  title: z.string(),
  unit: z.string(),
  series: z.array(z.object({ key: z.string(), label: z.string(), category: z.number().int() })),
  rows: z.array(z.record(z.string(), z.union([z.string(), z.number()]))),
  xKey: z.string(),
  source: Source,
})

const TimelinePanel = z.object({
  kind: z.literal("timeline"),
  title: z.string(),
  items: z.array(
    z.object({ date: z.string(), label: z.string(), nodeId: z.string().optional() })
  ),
  source: Source,
})

const ClaimsPanel = z.object({
  kind: z.literal("claims"),
  title: z.string(),
  sides: z.array(
    z.object({ label: z.string(), category: z.number().int(), claims: z.array(Claim) })
  ),
})

export const Panel = z.discriminatedUnion("kind", [ChartPanel, TimelinePanel, ClaimsPanel])

export const StageStatus = z.enum(["idle", "exploring", "answered", "insufficient"])

export const StageEvent = z.discriminatedUnion("type", [
  z.object({ type: z.literal("stage.reset") }),
  z.object({
    type: z.literal("stage.status"),
    status: StageStatus,
    note: z.string().optional(),
  }),
  z.object({ type: z.literal("graph.node.add"), node: GraphNode }),
  z.object({ type: z.literal("graph.edge.add"), edge: GraphEdge }),
  z.object({ type: z.literal("graph.focus"), nodeId: z.string() }),
  z.object({ type: z.literal("graph.traverse"), path: z.array(z.string()).min(2) }),
  z.object({
    type: z.literal("map.show"),
    region: z.literal("seoul"),
    level: z.literal("gu"),
    title: z.string(),
  }),
  z.object({
    type: z.literal("map.choropleth"),
    values: z.record(z.string(), RegionValue),
    legend: z.array(z.object({ category: z.number().int(), label: z.string() })),
    source: Source,
  }),
  z.object({ type: z.literal("map.focus"), regionId: z.string().nullable() }),
  z.object({
    type: z.literal("panel.add"),
    id: z.string(),
    panel: Panel,
  }),
  z.object({
    type: z.literal("claim.focus"),
    target: z.object({ kind: z.enum(["node", "region"]), id: z.string() }),
  }),
])

export type Source = z.infer<typeof Source>
export type GraphNode = z.infer<typeof GraphNode>
export type GraphEdge = z.infer<typeof GraphEdge>
export type RegionValue = z.infer<typeof RegionValue>
export type Claim = z.infer<typeof Claim>
export type Panel = z.infer<typeof Panel>
export type StageStatus = z.infer<typeof StageStatus>
export type StageEvent = z.infer<typeof StageEvent>

/** 검증에 실패한 이벤트는 버리고 경고를 남긴다. */
export function parseStageEvent(input: unknown): StageEvent | null {
  const result = StageEvent.safeParse(input)
  if (result.success) return result.data
  console.warn("[stage] 잘못된 이벤트를 버렸습니다", result.error.issues, input)
  return null
}
