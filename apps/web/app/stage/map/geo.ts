import { geoMercator } from "d3-geo"
import { Shape, Vector2, Vector3 } from "three"

/** 지도 경계 GeoJSON 중 이 프로젝트가 쓰는 부분 */
export type RegionFeature = {
  type: "Feature"
  properties: { code: string; name: string }
  geometry:
    | { type: "Polygon"; coordinates: number[][][] }
    | { type: "MultiPolygon"; coordinates: number[][][][] }
}
export type RegionCollection = { type: "FeatureCollection"; features: RegionFeature[] }

export type ProjectedRegion = {
  code: string
  name: string
  shapes: Shape[]
  /** 지면 위 중심점(world x, z) */
  centroid: Vector3
  /** 바닥 외곽선(world 좌표, 닫힌 고리) */
  outlines: Vector3[][]
  /** 외곽 크기 */
  radius: number
}

/**
 * 경위도를 지면 좌표로 바꾼다. 지도 전체가 size × size 안에 들어가게 맞춘다.
 * Shape 좌표는 (x, -z) 로 두고 장면에서 X축으로 -90° 회전해 지면에 눕힌다.
 */
export function projectRegions(collection: RegionCollection, size = 22): ProjectedRegion[] {
  const half = size / 2
  const projection = geoMercator().fitExtent(
    [
      [-half, -half],
      [half, half],
    ],
    collection as unknown as Parameters<ReturnType<typeof geoMercator>["fitExtent"]>[1]
  )

  return collection.features.map((f) => {
    const polygons = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates
    const shapes: Shape[] = []
    const outlines: Vector3[][] = []
    let sx = 0
    let sz = 0
    let n = 0
    let maxR = 0

    for (const rings of polygons) {
      const projected = rings.map((ring) =>
        ring.map(([lon, lat]) => {
          const [x, z] = projection([lon, lat]) ?? [0, 0]
          return new Vector2(x, -z)
        })
      )
      const shape = new Shape(projected[0])
      for (const hole of projected.slice(1)) shape.holes.push(new Shape(hole))
      shapes.push(shape)
      outlines.push(projected[0].map((p) => new Vector3(p.x, 0, -p.y)))
      for (const p of projected[0]) {
        sx += p.x
        sz += -p.y
        n++
      }
    }

    const centroid = new Vector3(sx / n, 0, sz / n)
    for (const ring of outlines) for (const p of ring) maxR = Math.max(maxR, p.distanceTo(centroid))
    return { code: f.properties.code, name: f.properties.name, shapes, centroid, outlines, radius: maxR }
  })
}
