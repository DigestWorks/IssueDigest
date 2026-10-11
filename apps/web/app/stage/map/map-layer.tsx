import { useEffect, useMemo, useRef, useState } from "react"
import { Text } from "@react-three/drei"
import { useFrame } from "@react-three/fiber"
import {
  BufferGeometry,
  Color,
  EdgesGeometry,
  ExtrudeGeometry,
  Float32BufferAttribute,
  type Group,
  type LineBasicMaterial,
  type MeshLambertMaterial,
} from "three"

import { dataColor, NEUTRAL } from "~/design/palette"
import type { RegionValue } from "../events"
import { FONT_LIGHT, FONT_MEDIUM } from "../scene/fonts"
import { regionCentroids } from "../scene/registry"
import { useStage } from "../store"
import { CompassRing } from "./compass-ring"
import { loadRegionCollection, projectRegions, type ProjectedRegion } from "./geo"

const BASE_HEIGHT = 0.12
const MAX_HEIGHT = 1.6
const MAP_SIZE = 16
const BASE_FILL = new Color("#ededed")
const DIM_FILL = new Color("#f6f6f6")
const WHITE = new Color("#ffffff")
const RISE_MS = 1300

/**
 * 서울 자치구 3D 지도. 지도 바탕과 경계선은 무채색이고, 지역 면의 색(범주)과
 * 압출 높이(크기)만 데이터를 나타낸다. 표현 기준은 docs/design/3d-map-concept.md.
 */
export function MapLayer({ reducedMotion }: { reducedMotion: boolean }) {
  const map = useStage((s) => s.map)
  const choropleth = useStage((s) => s.choropleth)
  const focus = useStage((s) => s.focus)
  const setFocus = useStage((s) => s.setFocus)
  const [regions, setRegions] = useState<ProjectedRegion[] | null>(null)

  useEffect(() => {
    if (!map || regions) return
    loadRegionCollection()
      .then((c) => setRegions(projectRegions(c, MAP_SIZE)))
      .catch((e: unknown) => console.warn("[stage] 지도", e))
  }, [map, regions])

  useEffect(() => {
    if (!regions) return
    for (const r of regions) regionCentroids.set(r.code, r.centroid.clone())
    return () => {
      for (const r of regions) regionCentroids.delete(r.code)
    }
  }, [regions])

  if (!map || !regions) return null
  const focusedCode = focus?.kind === "region" ? focus.id : null

  return (
    <group>
      {regions.map((r, i) => (
        <RegionMesh
          key={r.code}
          region={r}
          value={choropleth?.values[r.code]}
          valueAt={choropleth?.appliedAt ?? null}
          shownAt={map.shownAt}
          order={i}
          focused={focusedCode === r.code}
          dimmed={focusedCode !== null && focusedCode !== r.code}
          reducedMotion={reducedMotion}
          onSelect={() => setFocus({ kind: "region", id: r.code })}
        />
      ))}
      <CompassRing radius={11} shownAt={map.shownAt} reducedMotion={reducedMotion} />
    </group>
  )
}

type RegionProps = {
  region: ProjectedRegion
  value: RegionValue | undefined
  valueAt: number | null
  shownAt: number
  order: number
  focused: boolean
  dimmed: boolean
  reducedMotion: boolean
  onSelect: () => void
}

function RegionMesh({ region, value, valueAt, shownAt, order, focused, dimmed, reducedMotion, onSelect }: RegionProps) {
  const extrude = useMemo(
    () => new ExtrudeGeometry(region.shapes, { depth: 1, bevelEnabled: false, curveSegments: 1 }),
    [region.shapes]
  )
  const edges = useMemo(() => new EdgesGeometry(extrude, 20), [extrude])
  const outline = useMemo(() => {
    const g = new BufferGeometry()
    const pts: number[] = []
    for (const ring of region.outlines) {
      for (let i = 0; i < ring.length - 1; i++) {
        pts.push(ring[i].x, 0, ring[i].z, ring[i + 1].x, 0, ring[i + 1].z)
      }
    }
    g.setAttribute("position", new Float32BufferAttribute(pts, 3))
    return g
  }, [region.outlines])

  const column = useRef<Group>(null)
  const label = useRef<Group>(null)
  const fill = useRef<MeshLambertMaterial>(null)
  const edge = useRef<LineBasicMaterial>(null)
  const base = useRef<LineBasicMaterial>(null)
  const height = useRef(BASE_HEIGHT)

  const target = value ? BASE_HEIGHT + value.magnitude * MAX_HEIGHT : BASE_HEIGHT
  const color = useMemo(() => (value ? new Color(dataColor(value.category)) : BASE_FILL.clone()), [value])

  useFrame(() => {
    const now = performance.now()
    // 바닥 외곽선: 지도 표시 직후 순서대로 밝아진다
    const shown = reducedMotion ? 1 : clamp01((now - shownAt - order * 35) / 600)
    // 압출 높이: 값이 들어오면 중심에서 먼 구부터 차례로 올라온다
    const delay = order * 45
    const rise = valueAt === null ? 0 : reducedMotion ? 1 : clamp01((now - valueAt - delay) / RISE_MS)
    const h = valueAt === null ? BASE_HEIGHT * shown : BASE_HEIGHT + (target - BASE_HEIGHT) * easeOutCubic(rise)
    height.current = h

    const col = column.current
    if (col) col.scale.set(1, 1, Math.max(0.001, h))
    if (label.current) label.current.position.y = h + 0.03
    const c = regionCentroids.get(region.code)
    if (c) c.y = h

    if (fill.current) {
      // 등장: 흰색에서 지역 색으로 바뀐다. 재질은 항상 불투명이다.
      // 강조하지 않는 지역은 투명도 대신 흰색 쪽으로 옅게 만든다.
      fill.current.color.copy(WHITE).lerp(color, shown).lerp(DIM_FILL, dimmed ? 0.7 : 0)
    }
    if (edge.current) edge.current.opacity = (focused ? 0.9 : dimmed ? 0.15 : 0.45) * shown
    if (base.current) base.current.opacity = (focused ? 1 : 0.5) * shown
  })

  return (
    <group>
      {/* 바닥 외곽선: 무채색 */}
      <lineSegments geometry={outline} position-y={0.004}>
        <lineBasicMaterial ref={base} color={NEUTRAL.line} transparent opacity={0} />
      </lineSegments>

      <group rotation-x={-Math.PI / 2}>
        <group ref={column} scale={[1, 1, BASE_HEIGHT]}>
          <mesh
            geometry={extrude}
            castShadow
            receiveShadow
            onClick={(e) => {
              e.stopPropagation()
              onSelect()
            }}
            onPointerOver={() => (document.body.style.cursor = "pointer")}
            onPointerOut={() => (document.body.style.cursor = "")}
          >
            <meshLambertMaterial ref={fill} color="#ffffff" />
          </mesh>
          <lineSegments geometry={edges}>
            <lineBasicMaterial
              ref={edge}
              color={value ? color.clone().lerp(new Color(NEUTRAL.ink), 0.45) : new Color(NEUTRAL.lineDim)}
              transparent
              opacity={0}
             
            />
          </lineSegments>
        </group>
      </group>

      {/* 지역 이름: 압출 윗면에 눕힌 글자 */}
      <group ref={label} position={[region.centroid.x, BASE_HEIGHT, region.centroid.z]}>
        <Text
          font={focused ? FONT_MEDIUM : FONT_LIGHT}
          rotation-x={-Math.PI / 2}
          fontSize={focused ? 0.34 : 0.24}
          letterSpacing={0.08}
          color={focused ? NEUTRAL.ink : NEUTRAL.line}
          fillOpacity={dimmed ? 0.4 : 0.9}
          anchorX="center"
          anchorY="middle"
        >
          {region.name}
        </Text>
      </group>

      {focused ? <FocusRing region={region} reducedMotion={reducedMotion} /> : null}
    </group>
  )
}

/** 선택 지역 표시: 지면의 흰 고리. 선택은 화면 상태이므로 무채색이다. */
function FocusRing({ region, reducedMotion }: { region: ProjectedRegion; reducedMotion: boolean }) {
  const ring = useRef<Group>(null)
  useFrame((state) => {
    if (!ring.current) return
    const s = reducedMotion ? 1 : 1 + 0.04 * Math.sin(state.clock.elapsedTime * 2.4)
    ring.current.scale.setScalar(s)
  })
  const r = Math.min(region.radius * 1.1, 2.6)
  return (
    <group ref={ring} position={[region.centroid.x, 0.01, region.centroid.z]}>
      <mesh rotation-x={-Math.PI / 2}>
        <ringGeometry args={[r, r + 0.04, 96]} />
        <meshBasicMaterial color={NEUTRAL.ink} transparent opacity={0.95} />
      </mesh>
      <mesh rotation-x={-Math.PI / 2}>
        <ringGeometry args={[r + 0.16, r + 0.18, 96]} />
        <meshBasicMaterial color={NEUTRAL.ink} transparent opacity={0.35} />
      </mesh>
    </group>
  )
}

const clamp01 = (t: number) => Math.min(1, Math.max(0, t))
const easeOutCubic = (t: number) => 1 - (1 - t) ** 3
