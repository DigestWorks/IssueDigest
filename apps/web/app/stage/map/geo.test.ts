import { readFileSync } from "node:fs"
import { fileURLToPath } from "node:url"
import { describe, expect, it } from "vitest"

import { SEOUL_GU } from "../scenarios/election-map"
import { projectRegions, type RegionCollection } from "./geo"

const collection = JSON.parse(
  readFileSync(fileURLToPath(new URL("../../../public/geo/seoul-gu.json", import.meta.url)), "utf8")
) as RegionCollection

describe("서울 자치구 경계", () => {
  it("시나리오의 지역 코드표와 경계 파일의 코드가 같다", () => {
    const codes = collection.features.map((f) => f.properties.code).sort()
    expect(codes).toEqual(Object.keys(SEOUL_GU).sort())
    for (const f of collection.features) expect(SEOUL_GU[f.properties.code]).toBe(f.properties.name)
  })

  it("투영 결과가 지정한 크기 안에 들어온다", () => {
    const regions = projectRegions(collection, 22)
    expect(regions).toHaveLength(25)
    for (const r of regions) {
      expect(Math.abs(r.centroid.x)).toBeLessThanOrEqual(11)
      expect(Math.abs(r.centroid.z)).toBeLessThanOrEqual(11)
      expect(r.radius).toBeGreaterThan(0.3)
      expect(r.radius).toBeLessThan(6)
    }
    // 북쪽(도봉구)이 남쪽(서초구)보다 화면 안쪽(-z)에 있다
    const z = (code: string) => regions.find((r) => r.code === code)!.centroid.z
    expect(z("11100")).toBeLessThan(z("11220"))
  })
})
