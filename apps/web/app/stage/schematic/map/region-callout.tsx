import { dataColor } from "~/design/palette"
import type { RegionValue } from "../../events"
import { SchematicCallout } from "../callout"
import type { MapSource } from "./map-scene"

/** 선택 지역 주석: 지역 코드 | 자치구, 지역 이름, 값(데이터 색 사각점), 출처 */
export function RegionCallout({
  code,
  name,
  value,
  source,
  animate,
}: {
  code: string
  name: string
  value: RegionValue | undefined
  source: MapSource
  animate: boolean
}) {
  return (
    <SchematicCallout
      code={code}
      unit="자치구"
      title={name}
      line={value ? { text: value.label, color: dataColor(value.category) } : null}
      source={source}
      animate={animate}
    />
  )
}
