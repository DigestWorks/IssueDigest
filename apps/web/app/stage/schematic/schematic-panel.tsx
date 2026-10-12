import type { Panel } from "../events"
import { SchematicChart } from "./schematic-chart"
import { SchematicClaims } from "./schematic-claims"
import { SchematicTimeline } from "./schematic-timeline"

/** 도면 양식 결과 패널. 패널 종류에 맞는 컴포넌트를 고른다. */
export function SchematicPanel({ panel, index, animate }: { panel: Panel; index: number; animate: boolean }) {
  switch (panel.kind) {
    case "chart":
      return <SchematicChart panel={panel} index={index} animate={animate} />
    case "timeline":
      return <SchematicTimeline panel={panel} index={index} animate={animate} />
    case "claims":
      return <SchematicClaims panel={panel} index={index} animate={animate} />
  }
}
