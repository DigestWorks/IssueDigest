import { useEffect, useMemo, useRef, useState, type RefObject } from "react"
import { CameraControls, Grid, Html, Text } from "@react-three/drei"
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber"
import {
  BufferGeometry,
  Color,
  DoubleSide,
  ExtrudeGeometry,
  Float32BufferAttribute,
  MathUtils,
  NoToneMapping,
  ShapeGeometry,
  Vector3,
  type Group,
  type LineBasicMaterial,
  type MeshBasicMaterial,
} from "three"

import { dataColor } from "~/design/palette"
import { OPACITY, SCHEMATIC_THEME } from "~/design/tokens"
import type { RegionValue } from "../../events"
import {
  fitProjection,
  loadRegionCollection,
  projectRegions,
  type ProjectedRegion,
  type RegionCollection,
} from "../../map/geo"
import { FONT_LIGHT, FONT_MEDIUM } from "../../scene/fonts"
import { uprightAmount } from "../../scene/view-angle"
import { RegionCallout } from "./region-callout"

export type MapView = "overview" | "top" | "low"
export type MapSource = { label: string; span?: string }

export type MapSceneProps = {
  values: Record<string, RegionValue>
  source: MapSource
  focus: string | null
  hovered: string | null
  onFocus: (code: string | null) => void
  onHover: (region: { code: string; name: string } | null) => void
  /** 보기 전환 요청. n 이 바뀔 때마다 카메라를 그 보기로 옮긴다 */
  view: { name: MapView; n: number }
  /** 카메라 방위·기울기·거리를 적을 DOM 요소 */
  readout: RefObject<HTMLSpanElement | null>
  reducedMotion: boolean
}

const MAP_SIZE = 16
const BASE_H = 0.1
const MAX_H = 1.8
/** 홀로그램 층 간격(장면 단위). 높이는 이 간격의 층 수로 나타낸다 */
const LAYER_GAP = 0.18
/** 주사선이 바닥에서 MAX_H 위까지 한 번 지나가는 시간(ms) */
const SCAN = { ms: 3200 }
const LEADER = 2.6
const INK = SCHEMATIC_THEME.ink
const ACCENT = SCHEMATIC_THEME.accent
const SCENE = SCHEMATIC_THEME.scene
/** 값이 없는 지역의 선 색 */
const LINE_DIM = "#8b9598"

/** 등장 시각(ms, 경계 데이터를 받은 시점 기준). 틀 → 외곽선 → 면 → 글자 순서다. */
const T = {
  frame: { at: 0, ms: 600 },
  compass: { at: 0, ms: 1200 },
  outline: { at: 200, ms: 500, step: 30 },
  fill: { at: 900, ms: 1100, step: 35 },
  label: { at: 1500, ms: 300, step: 20 },
  focusTrace: 700,
  focusPulse: { at: 500, ms: 1000 },
  focusLeader: { at: 400, ms: 400 },
}

const VIEWS: Record<MapView, { position: [number, number, number]; target: [number, number, number] }> = {
  overview: { position: [0, 17, 16], target: [0, 0, 0.6] },
  top: { position: [0, 25, 0.001], target: [0, 0, 0] },
  low: { position: [0, 4.2, 20], target: [0, 1.2, 0] },
}

/**
 * 도면 양식(The Division UI 스타일 가이드) 3D 지도 장면.
 * - 지역 높이는 일정 간격으로 쌓은 수평 외곽선 층(홀로그램 표현)으로 그린다. 색은 범주, 층 수는 크기다.
 * - 경계선·틀·방위 고리·좌표 눈금은 흰색과 불투명도 단계로만 그린다.
 * - 선택한 지역은 주황 외곽선이 한 바퀴 그려지고 한 번 바깥으로 커지며 사라진 뒤, 수직 지시선 끝에 주석이 붙는다.
 * - 발광(Bloom)은 쓰지 않는다.
 * schematic-map.tsx 가 브라우저에서만 불러온다.
 */
export default function MapScene(props: MapSceneProps) {
  return (
    <Canvas
      dpr={[1, 2]}
      camera={{ position: [0, 30, 30], fov: 36, near: 0.1, far: 200 }}
      gl={{ antialias: true, toneMapping: NoToneMapping }}
    >
      <color attach="background" args={[SCENE]} />
      <fog attach="fog" args={[SCENE, 30, 70]} />
      {/* 모든 재질이 조명을 받지 않는 MeshBasic·LineBasic 이므로 조명을 두지 않는다 */}
      <Grid
        position-y={-0.005}
        args={[120, 120]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#141a1e"
        sectionSize={4}
        sectionThickness={0.8}
        sectionColor="#1e262b"
        fadeDistance={48}
        fadeStrength={1.4}
        infiniteGrid
      />
      <MapContent {...props} />
      <MapCamera {...props} />
    </Canvas>
  )
}

function MapContent({ values, source, focus, hovered, onFocus, onHover, reducedMotion }: MapSceneProps) {
  const [data, setData] = useState<{ collection: RegionCollection; regions: ProjectedRegion[]; t0: number } | null>(null)
  const heights = useRef(new Map<string, number>())

  useEffect(() => {
    let alive = true
    loadRegionCollection()
      .then((collection) => {
        if (alive) setData({ collection, regions: projectRegions(collection, MAP_SIZE), t0: performance.now() })
      })
      .catch((e: unknown) => console.warn("[map]", e))
    return () => {
      alive = false
    }
  }, [])

  useEffect(() => {
    if (!data) return
    for (const r of data.regions) focusCentroids.set(r.code, r.centroid)
  }, [data])

  if (!data) return null
  const { collection, regions, t0 } = data
  const focused = focus ? regions.find((r) => r.code === focus) : undefined

  return (
    <group>
      {regions.map((r, i) => {
        const common = {
          region: r,
          order: i,
          t0,
          focused: focus === r.code,
          dimmed: focus !== null && focus !== r.code,
          hovered: hovered === r.code,
          heights: heights.current,
          reducedMotion,
        }
        return (
          <group key={r.code}>
            <RegionVolume {...common} value={values[r.code]} onFocus={onFocus} onHover={onHover} />
            <RegionLabel {...common} />
          </group>
        )
      })}
      <MapFrame collection={collection} regions={regions} t0={t0} reducedMotion={reducedMotion} />
      <Compass radius={12.5} t0={t0} reducedMotion={reducedMotion} />
      {focused ? (
        <FocusMarker
          key={focused.code}
          region={focused}
          value={values[focused.code]}
          source={source}
          heights={heights.current}
          reducedMotion={reducedMotion}
        />
      ) : null}
    </group>
  )
}

type RegionCommon = {
  region: ProjectedRegion
  order: number
  t0: number
  focused: boolean
  dimmed: boolean
  hovered: boolean
  heights: Map<string, number>
  reducedMotion: boolean
}

/**
 * 지역 하나: 바닥 외곽선과 수평 층 묶음(홀로그램 표현).
 * 높이는 벽이 있는 덩어리 대신 일정 간격으로 쌓은 외곽선 층의 수로 나타낸다. 층 사이는 비어 있어
 * 뒤가 보인다. 맨 위 층이 가장 밝고 아래로 갈수록 배경색에 가까워진다.
 * 등장할 때 층이 아래에서부터 하나씩 쌓이고, 장면 전체를 아래에서 위로 지나가는 주사선이
 * 층을 지날 때 그 높이의 외곽선을 밝게 그린다.
 */
function RegionVolume({
  region,
  value,
  order,
  t0,
  focused,
  dimmed,
  hovered,
  heights,
  reducedMotion,
  onFocus,
  onHover,
}: RegionCommon & Pick<MapSceneProps, "onFocus" | "onHover"> & { value: RegionValue | undefined }) {
  const count = value ? Math.max(1, Math.round((value.magnitude * MAX_H) / LAYER_GAP)) : 1
  const color = useMemo(() => new Color(value ? dataColor(value.category) : LINE_DIM), [value])
  const layers = useMemo(() => buildLayers(region, count, color, !!value), [region, count, color, value])
  // 포인터 판정용 보이지 않는 기둥. 층 사이 빈 곳을 가리켜도 지역이 잡히게 한다.
  const hit = useMemo(
    () => new ExtrudeGeometry(region.shapes, { depth: 1, bevelEnabled: false, curveSegments: 1 }),
    [region.shapes]
  )
  const outline = useMemo(() => outlineGeometry(region.outlines), [region.outlines])
  const plate = useMemo(() => new ShapeGeometry(region.shapes, 1).rotateX(-Math.PI / 2), [region.shapes])

  const hitColumn = useRef<Group>(null)
  const lineMat = useRef<LineBasicMaterial>(null)
  const fillMat = useRef<MeshBasicMaterial>(null)
  const base = useRef<LineBasicMaterial>(null)
  const scan = useRef<Group>(null)
  const scanMat = useRef<LineBasicMaterial>(null)
  const scanFill = useRef<MeshBasicMaterial>(null)

  useFrame(() => {
    const now = performance.now()
    const tOutline = progress(now, t0 + T.outline.at + order * T.outline.step, T.outline.ms, reducedMotion)
    const tFill = progress(now, t0 + T.fill.at + order * T.fill.step, T.fill.ms, reducedMotion)
    // 층이 아래에서부터 하나씩 쌓인다
    const shown = Math.ceil(count * easeOutCubic(tFill))
    const h = shown * LAYER_GAP
    heights.set(region.code, Math.max(h, BASE_H))
    hitColumn.current?.scale.set(1, 1, Math.max(0.001, h))
    setDrawProgress(outline, tOutline)
    layers.lines.setDrawRange(0, shown * layers.lineStride)
    layers.fills.setDrawRange(0, shown * layers.fillStride)

    if (base.current) base.current.opacity = dimmed ? OPACITY.faint.value : OPACITY.context.value
    const o = focused || hovered ? 1 : dimmed ? 0.22 : value ? 0.85 : 0.4
    if (lineMat.current) lineMat.current.opacity = o
    if (fillMat.current) fillMat.current.opacity = o * (focused || hovered ? 0.7 : 0.5)

    // 주사선: 모든 지역에서 같은 높이로 아래에서 위로 지나간다
    if (scan.current && scanMat.current && scanFill.current) {
      const y = (((now - t0) % SCAN.ms) / SCAN.ms) * (MAX_H + LAYER_GAP * 2)
      const inside = !reducedMotion && tFill >= 1 && y <= h + 0.001
      scan.current.position.y = y
      scanMat.current.opacity = inside ? (dimmed ? 0.3 : 1) : 0
      scanFill.current.opacity = inside ? (dimmed ? 0.05 : 0.16) : 0
    }
  })

  const select = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    // 회전하려고 끈 경우는 선택으로 보지 않는다
    if (e.delta > 4) return
    onFocus(focused ? null : region.code)
  }

  return (
    <group>
      <lineSegments geometry={outline} position-y={0.004}>
        <lineBasicMaterial ref={base} color={INK} transparent opacity={0} depthWrite={false} />
      </lineSegments>
      <lineSegments geometry={layers.lines}>
        <lineBasicMaterial ref={lineMat} vertexColors transparent opacity={0} depthWrite={false} />
      </lineSegments>
      <mesh geometry={layers.fills}>
        <meshBasicMaterial ref={fillMat} vertexColors transparent opacity={0} depthWrite={false} side={DoubleSide} />
      </mesh>
      <group ref={scan}>
        <lineSegments geometry={outline}>
          <lineBasicMaterial ref={scanMat} color={color.clone().lerp(new Color(INK), 0.85)} transparent opacity={0} depthWrite={false} />
        </lineSegments>
        <mesh geometry={plate}>
          <meshBasicMaterial ref={scanFill} color={color.clone().lerp(new Color(INK), 0.4)} transparent opacity={0} depthWrite={false} side={DoubleSide} />
        </mesh>
      </group>
      <group rotation-x={-Math.PI / 2}>
        <group ref={hitColumn} scale={[1, 1, BASE_H]}>
          <mesh
            geometry={hit}
            onClick={select}
            onPointerOver={(e) => {
              e.stopPropagation()
              onHover({ code: region.code, name: region.name })
              document.body.style.cursor = "pointer"
            }}
            onPointerOut={() => {
              onHover(null)
              document.body.style.cursor = ""
            }}
          >
            <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
          </mesh>
        </group>
      </group>
    </group>
  )
}

/**
 * 층 묶음 형상. 층 k(1..count)는 높이 k × LAYER_GAP 에 놓인다.
 * 색은 꼭짓점 색으로 넣는다. 맨 위 층은 데이터 색을 흰색 쪽으로 밝힌 값이고, 아래 층일수록 배경색에 가깝다.
 * 면은 맨 위 층만 진하게, 나머지는 아주 옅게 채운다.
 * 층 순서대로 이어 붙였으므로 drawRange 로 아래 층부터 보이게 할 수 있다.
 */
function buildLayers(region: ProjectedRegion, count: number, color: Color, hasValue: boolean) {
  const scene = new Color(SCENE)
  const top = color.clone().lerp(new Color(INK), hasValue ? 0.3 : 0.1)
  const c = new Color()

  // 외곽선 층
  const ring: number[] = []
  for (const r of region.outlines)
    for (let i = 0; i < r.length - 1; i++) ring.push(r[i].x, r[i].z, r[i + 1].x, r[i + 1].z)
  const lineStride = ring.length / 2
  const lp = new Float32Array(lineStride * 3 * count)
  const lc = new Float32Array(lineStride * 3 * count)

  // 면 층: 지면 형상(ShapeGeometry 의 x, y)을 (x, 높이, -y) 로 옮긴다
  const shape = new ShapeGeometry(region.shapes, 1)
  const sp = shape.getAttribute("position")
  const si = shape.getIndex()!
  const fillStride = si.count
  const fp = new Float32Array(sp.count * 3 * count)
  const fc = new Float32Array(sp.count * 3 * count)
  const fi: number[] = []

  for (let k = 0; k < count; k++) {
    const y = (k + 1) * LAYER_GAP
    const isTop = k === count - 1
    const a = isTop ? 1 : 0.22 + 0.5 * ((k + 1) / count) ** 1.5
    c.copy(scene).lerp(top, a)
    for (let v = 0; v < lineStride; v++) {
      const o = (k * lineStride + v) * 3
      lp.set([ring[v * 2], y, ring[v * 2 + 1]], o)
      lc.set([c.r, c.g, c.b], o)
    }
    c.copy(scene).lerp(color, isTop ? 0.55 : 0.12)
    for (let v = 0; v < sp.count; v++) {
      const o = (k * sp.count + v) * 3
      fp.set([sp.getX(v), y, -sp.getY(v)], o)
      fc.set([c.r, c.g, c.b], o)
    }
    for (let j = 0; j < si.count; j++) fi.push(si.getX(j) + k * sp.count)
  }
  shape.dispose()

  const lines = new BufferGeometry()
  lines.setAttribute("position", new Float32BufferAttribute(lp, 3))
  lines.setAttribute("color", new Float32BufferAttribute(lc, 3))
  const fills = new BufferGeometry()
  fills.setAttribute("position", new Float32BufferAttribute(fp, 3))
  fills.setAttribute("color", new Float32BufferAttribute(fc, 3))
  fills.setIndex(fi)
  return { lines, fills, lineStride, fillStride }
}

/**
 * 지역 이름. 카메라가 높으면 윗면에 눕고, 낮으면 윗면 위에 선다(결과 패널과 같은 각도 기준).
 * 카메라 방위를 따라 돌아 글자가 바로 읽히는 방향을 유지한다. 선택한 지역은 주석이 이름을 대신한다.
 */
function RegionLabel({ region, order, t0, focused, dimmed, hovered, heights, reducedMotion }: RegionCommon) {
  const group = useRef<Group>(null)
  const text = useRef<TextLike | null>(null)
  const up = useRef(0)
  const controls = useThree((s) => s.controls) as CameraControls | null
  const fontSize = 0.26

  useFrame((_, delta) => {
    const g = group.current
    if (!g) return
    const t = controls ? uprightAmount(controls.polarAngle) : 0
    up.current = reducedMotion ? t : MathUtils.damp(up.current, t, 6, delta)
    const h = heights.get(region.code) ?? BASE_H
    g.position.set(region.centroid.x, h + 0.02 + up.current * fontSize * 0.7, region.centroid.z)
    g.rotation.set(MathUtils.lerp(-Math.PI / 2, 0, up.current), controls?.azimuthAngle ?? 0, 0, "YXZ")
    const a = progress(performance.now(), t0 + T.label.at + order * T.label.step, T.label.ms, reducedMotion)
    if (text.current) text.current.fillOpacity = a * (focused ? 0 : hovered ? 1 : dimmed ? 0.3 : 0.8)
  })

  return (
    <group ref={group}>
      <Text
        ref={(t: unknown) => void (text.current = t as TextLike | null)}
        font={hovered ? FONT_MEDIUM : FONT_LIGHT}
        fontSize={fontSize}
        letterSpacing={0.08}
        color={INK}
        fillOpacity={0}
        anchorX="center"
        anchorY="middle"
        renderOrder={5}
      >
        {region.name}
      </Text>
    </group>
  )
}

/**
 * 선택 표시: 주황 외곽선이 윗면과 바닥을 따라 한 바퀴 그려지고, 윗면 외곽선이 한 번 바깥으로 커지며 사라진다.
 * 이어서 윗면 중심에서 수직 지시선이 올라가고 그 끝에 주석이 붙는다.
 */
function FocusMarker({
  region,
  value,
  source,
  heights,
  reducedMotion,
}: {
  region: ProjectedRegion
  value: RegionValue | undefined
  source: MapSource
  heights: Map<string, number>
  reducedMotion: boolean
}) {
  const at = useMemo(() => performance.now(), [])
  // 중심 기준 좌표로 만들어 확대 표시를 중심에서 확대할 수 있게 한다
  const trace = useMemo(() => outlineGeometry(region.outlines, region.centroid), [region])
  const pulseGeo = useMemo(() => outlineGeometry(region.outlines, region.centroid), [region])
  const leaderGeo = useMemo(() => {
    const g = new BufferGeometry()
    g.setAttribute("position", new Float32BufferAttribute([0, 0, 0, 0, 1, 0], 3))
    return g
  }, [])

  const top = useRef<Group>(null)
  const pulse = useRef<Group>(null)
  const pulseMat = useRef<LineBasicMaterial>(null)
  const leader = useRef<Group>(null)
  const foot = useRef<MeshBasicMaterial>(null)
  const callout = useRef<Group>(null)

  useFrame(() => {
    const now = performance.now()
    const h = heights.get(region.code) ?? BASE_H
    setDrawProgress(trace, progress(now, at, T.focusTrace, reducedMotion))
    top.current?.position.setY(h + 0.006)

    const p = progress(now, at + T.focusPulse.at, T.focusPulse.ms, reducedMotion)
    if (pulse.current) {
      pulse.current.position.y = h + 0.006
      pulse.current.scale.setScalar(1 + 0.5 * easeOutCubic(p))
    }
    if (pulseMat.current) pulseMat.current.opacity = reducedMotion || p <= 0 ? 0 : (1 - p) * 0.8

    const l = easeOutCubic(progress(now, at + T.focusLeader.at, T.focusLeader.ms, reducedMotion))
    if (leader.current) {
      leader.current.position.y = h
      leader.current.scale.y = Math.max(0.001, LEADER * l)
    }
    if (foot.current) foot.current.opacity = l
    callout.current?.position.setY(h + LEADER)
  })

  const { x, z } = region.centroid
  return (
    <group position={[x, 0, z]}>
      <group ref={top}>
        <lineSegments geometry={trace} renderOrder={6}>
          <lineBasicMaterial color={ACCENT} transparent depthTest={false} />
        </lineSegments>
      </group>
      <lineSegments geometry={trace} position-y={0.008}>
        <lineBasicMaterial color={ACCENT} transparent opacity={OPACITY.related.value} />
      </lineSegments>
      <group ref={pulse}>
        <lineSegments geometry={pulseGeo}>
          <lineBasicMaterial ref={pulseMat} color={ACCENT} transparent opacity={0} depthWrite={false} />
        </lineSegments>
      </group>
      <group ref={leader}>
        <lineSegments geometry={leaderGeo} renderOrder={6}>
          <lineBasicMaterial color={ACCENT} transparent depthTest={false} />
        </lineSegments>
        {/* 지시선 아래 끝: 윗면의 작은 사각점 */}
        <mesh rotation-x={-Math.PI / 2} renderOrder={6}>
          <planeGeometry args={[0.14, 0.14]} />
          <meshBasicMaterial ref={foot} color={ACCENT} transparent opacity={0} depthTest={false} />
        </mesh>
      </group>
      <group ref={callout}>
        <Html zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
          <RegionCallout code={region.code} name={region.name} value={value} source={source} animate={!reducedMotion} />
        </Html>
      </group>
    </group>
  )
}

/**
 * 지도 틀: 경계 범위를 둘러싼 꺾쇠, 경도·위도 눈금, 축척 막대, 출처 표기.
 * 화면의 지도가 측정 기록이라는 것을 보여 주는 주석이다.
 */
function MapFrame({
  collection,
  regions,
  t0,
  reducedMotion,
}: {
  collection: RegionCollection
  regions: ProjectedRegion[]
  t0: number
  reducedMotion: boolean
}) {
  const built = useMemo(() => buildFrame(collection, regions), [collection, regions])
  const texts = useRef<(TextLike | null)[]>([])

  useFrame(() => {
    const now = performance.now()
    const t = progress(now, t0 + T.frame.at, T.frame.ms, reducedMotion)
    setDrawProgress(built.strong, t)
    setDrawProgress(built.faint, t)
    const a = progress(now, t0 + T.frame.at + T.frame.ms, 300, reducedMotion)
    for (const tx of texts.current) if (tx) tx.fillOpacity = a * OPACITY.related.value
  })

  return (
    <group position-y={0.003}>
      <lineSegments geometry={built.strong}>
        <lineBasicMaterial color={INK} transparent opacity={OPACITY.related.value} />
      </lineSegments>
      <lineSegments geometry={built.faint}>
        <lineBasicMaterial color={INK} transparent opacity={OPACITY.context.value} />
      </lineSegments>
      {built.labels.map((l, i) => (
        <Text
          key={l.text + i}
          ref={(t: unknown) => void (texts.current[i] = t as TextLike | null)}
          font={l.strong ? FONT_MEDIUM : FONT_LIGHT}
          position={[l.x, 0, l.z]}
          rotation-x={-Math.PI / 2}
          fontSize={l.size}
          letterSpacing={0.08}
          color={INK}
          fillOpacity={0}
          anchorX={l.anchorX}
          anchorY="middle"
        >
          {l.text}
        </Text>
      ))}
    </group>
  )
}

type FrameLabel = { text: string; x: number; z: number; size: number; anchorX: "left" | "center" | "right"; strong?: boolean }

function buildFrame(collection: RegionCollection, regions: ProjectedRegion[]) {
  const projection = fitProjection(collection, MAP_SIZE)
  let minX = Infinity
  let maxX = -Infinity
  let minZ = Infinity
  let maxZ = -Infinity
  for (const r of regions)
    for (const ring of r.outlines)
      for (const p of ring) {
        minX = Math.min(minX, p.x)
        maxX = Math.max(maxX, p.x)
        minZ = Math.min(minZ, p.z)
        maxZ = Math.max(maxZ, p.z)
      }
  const m = 0.9
  minX -= m
  maxX += m
  minZ -= m
  maxZ += m

  const strong: number[] = []
  const faint: number[] = []
  const labels: FrameLabel[] = []
  const seg = (out: number[], x1: number, z1: number, x2: number, z2: number) => out.push(x1, 0, z1, x2, 0, z2)

  // 모서리 꺾쇠와 옅은 테두리
  const b = 1.1
  for (const [cx, cz, dx, dz] of [
    [minX, minZ, 1, 1],
    [maxX, minZ, -1, 1],
    [minX, maxZ, 1, -1],
    [maxX, maxZ, -1, -1],
  ] as const) {
    seg(strong, cx, cz, cx + dx * b, cz)
    seg(strong, cx, cz, cx, cz + dz * b)
  }
  seg(faint, minX + b, minZ, maxX - b, minZ)
  seg(faint, minX + b, maxZ, maxX - b, maxZ)
  seg(faint, minX, minZ + b, minX, maxZ - b)
  seg(faint, maxX, minZ + b, maxX, maxZ - b)

  // 경도 눈금(아래 변)과 위도 눈금(왼쪽 변). 메르카토르에서 x 는 경도만, z 는 위도만의 함수다.
  const [lonMin, latMax] = projection.invert!([minX, minZ])!
  const [lonMax, latMin] = projection.invert!([maxX, maxZ])!
  const latMid = (latMin + latMax) / 2
  const lonMid = (lonMin + lonMax) / 2
  const STEP = 0.05
  for (let k = Math.ceil(lonMin / STEP); k * STEP <= lonMax; k++) {
    const lon = k * STEP
    const x = projection([lon, latMid])![0]
    const major = k % 2 === 0
    seg(major ? strong : faint, x, maxZ, x, maxZ + (major ? 0.45 : 0.25))
    if (major) labels.push({ text: `${lon.toFixed(1)}°E`, x, z: maxZ + 0.8, size: 0.22, anchorX: "center" })
  }
  for (let k = Math.ceil(latMin / STEP); k * STEP <= latMax; k++) {
    const lat = k * STEP
    const z = projection([lonMid, lat])![1]
    const major = k % 2 === 0
    seg(major ? strong : faint, minX, z, minX - (major ? 0.45 : 0.25), z)
    if (major) labels.push({ text: `${lat.toFixed(1)}°N`, x: minX - 0.6, z, size: 0.22, anchorX: "right" })
  }

  // 축척 막대 5 km. 경도 1°의 거리는 구면 근사 111.32 km × cos(위도)로 계산한다.
  const km = 5
  const dLon = km / (111.32 * Math.cos((latMid * Math.PI) / 180))
  const len = projection([lonMid + dLon, latMid])![0] - projection([lonMid, latMid])![0]
  const sx2 = maxX - 0.5
  const sx1 = sx2 - len
  const sz = maxZ - 0.55
  seg(strong, sx1, sz, sx2, sz)
  seg(strong, sx1, sz - 0.15, sx1, sz + 0.15)
  seg(strong, sx2, sz - 0.15, sx2, sz + 0.15)
  seg(faint, (sx1 + sx2) / 2, sz - 0.1, (sx1 + sx2) / 2, sz + 0.1)
  labels.push({ text: `${km} km`, x: sx2, z: sz - 0.4, size: 0.22, anchorX: "right" })

  // 표제와 출처
  labels.push({ text: "서울특별시 자치구 경계", x: minX, z: minZ - 0.95, size: 0.34, anchorX: "left", strong: true })
  labels.push({ text: "통계청 센서스용 행정구역경계 2013 · 메르카토르 투영", x: minX, z: minZ - 0.45, size: 0.2, anchorX: "left" })

  return { strong: lineGeometry(strong), faint: lineGeometry(faint), labels }
}

/** 방위 고리: 5° 눈금, 30° 마다 각도, 동서남북 문자. 원과 눈금이 한 바퀴 돌며 그려진다. */
function Compass({ radius, t0, reducedMotion }: { radius: number; t0: number; reducedMotion: boolean }) {
  const { circle, minor, major, degrees } = useMemo(() => {
    const c: number[] = []
    const n = 256
    for (let i = 0; i < n; i++) {
      const a1 = (i / n) * Math.PI * 2
      const a2 = ((i + 1) / n) * Math.PI * 2
      c.push(Math.sin(a1) * radius, 0, -Math.cos(a1) * radius, Math.sin(a2) * radius, 0, -Math.cos(a2) * radius)
    }
    const mi: number[] = []
    const ma: number[] = []
    const deg: { text: string; angle: number }[] = []
    for (let d = 0; d < 360; d += 5) {
      const a = (d * Math.PI) / 180
      const len = d % 45 === 0 ? 0.7 : d % 15 === 0 ? 0.35 : 0.18
      const out = d % 15 === 0 ? ma : mi
      out.push(Math.sin(a) * radius, 0, -Math.cos(a) * radius)
      out.push(Math.sin(a) * (radius + len), 0, -Math.cos(a) * (radius + len))
      if (d % 30 === 0 && d % 90 !== 0) deg.push({ text: String(d).padStart(3, "0"), angle: a })
    }
    return { circle: lineGeometry(c), minor: lineGeometry(mi), major: lineGeometry(ma), degrees: deg }
  }, [radius])
  const texts = useRef<(TextLike | null)[]>([])

  useFrame(() => {
    const now = performance.now()
    const t = progress(now, t0 + T.compass.at, T.compass.ms, reducedMotion)
    setDrawProgress(circle, t)
    setDrawProgress(minor, t)
    setDrawProgress(major, t)
    const a = progress(now, t0 + T.compass.at + T.compass.ms * 0.6, 400, reducedMotion)
    texts.current.forEach((tx, i) => {
      if (tx) tx.fillOpacity = a * (i < 4 ? OPACITY.related.value : OPACITY.context.value)
    })
  })

  const letters = [
    { text: "N", angle: 0 },
    { text: "E", angle: Math.PI / 2 },
    { text: "S", angle: Math.PI },
    { text: "W", angle: (Math.PI * 3) / 2 },
  ]
  const all = [...letters.map((l) => ({ ...l, r: radius + 1.6, size: 0.8 })), ...degrees.map((d) => ({ ...d, r: radius + 1.1, size: 0.26 }))]

  return (
    <group position-y={0.002}>
      <lineSegments geometry={circle}>
        <lineBasicMaterial color={INK} transparent opacity={OPACITY.context.value} />
      </lineSegments>
      <lineSegments geometry={minor}>
        <lineBasicMaterial color={INK} transparent opacity={OPACITY.faint.value * 2} />
      </lineSegments>
      <lineSegments geometry={major}>
        <lineBasicMaterial color={INK} transparent opacity={OPACITY.related.value} />
      </lineSegments>
      {all.map((l, i) => (
        <Text
          key={l.text}
          ref={(t: unknown) => void (texts.current[i] = t as TextLike | null)}
          font={FONT_LIGHT}
          position={[Math.sin(l.angle) * l.r, 0, -Math.cos(l.angle) * l.r]}
          rotation={[-Math.PI / 2, 0, -l.angle]}
          fontSize={l.size}
          letterSpacing={0.06}
          color={INK}
          fillOpacity={0}
          anchorX="center"
          anchorY="middle"
        >
          {l.text}
        </Text>
      ))}
    </group>
  )
}

/** 카메라: 보기 전환, 선택 지역으로 이동, 방위·기울기·거리 표시 */
function MapCamera({ view, focus, readout, reducedMotion }: MapSceneProps) {
  const controls = useRef<CameraControls>(null)
  const animate = !reducedMotion

  useEffect(() => {
    const v = VIEWS[view.name]
    void controls.current?.setLookAt(...v.position, ...v.target, animate)
  }, [view, animate])

  useEffect(() => {
    const c = controls.current
    if (!c || !focus) return
    // 지역 높이가 정해진 뒤 읽도록 한 프레임 미룬다
    const id = requestAnimationFrame(() => {
      const p = focusCentroids.get(focus)
      if (!p) return
      const from = c.camera.position.clone().sub(c.getTarget(new Vector3())).normalize().multiplyScalar(21)
      void c.setLookAt(p.x + from.x, from.y + 0.8, p.z + from.z, p.x, 0.8, p.z, animate)
    })
    return () => cancelAnimationFrame(id)
  }, [focus, animate])

  useFrame(() => {
    const c = controls.current
    const el = readout.current
    if (!c || !el) return
    const az = ((MathUtils.radToDeg(-c.azimuthAngle) % 360) + 360) % 360
    const tilt = MathUtils.radToDeg(c.polarAngle)
    el.textContent = `방위 ${String(Math.round(az) % 360).padStart(3, "0")}° · 기울기 ${String(Math.round(tilt)).padStart(2, "0")}° · 거리 ${c.distance.toFixed(1)}`
  })

  useEffect(() => {
    // 개발 중 검증 스크립트가 카메라를 돌린다
    if (import.meta.env.DEV) Object.assign(window, { __mapControls: controls.current })
  }, [])

  return (
    <CameraControls
      ref={controls}
      makeDefault
      smoothTime={0.6}
      minDistance={6}
      maxDistance={45}
      maxPolarAngle={Math.PI * 0.47}
    />
  )
}

/** troika Text 메시 중 매 프레임 바꾸는 속성. 색·불투명도 변경은 sync() 없이 다음 렌더에 반영된다. */
type TextLike = { fillOpacity: number }

/** 지역 중심(지면 좌표). 카메라 이동이 읽는다. */
const focusCentroids = new Map<string, Vector3>()

function outlineGeometry(rings: Vector3[][], origin?: Vector3) {
  const pts: number[] = []
  const ox = origin?.x ?? 0
  const oz = origin?.z ?? 0
  for (const ring of rings)
    for (let i = 0; i < ring.length - 1; i++)
      pts.push(ring[i].x - ox, 0, ring[i].z - oz, ring[i + 1].x - ox, 0, ring[i + 1].z - oz)
  return lineGeometry(pts)
}

function lineGeometry(pts: number[]) {
  const g = new BufferGeometry()
  g.setAttribute("position", new Float32BufferAttribute(pts, 3))
  return g
}

/** 선분 묶음을 앞에서부터 t 비율만큼 그린다(선이 출발점에서 도착점으로 그려지는 등장) */
function setDrawProgress(g: BufferGeometry, t: number) {
  const n = g.getAttribute("position").count
  g.setDrawRange(0, Math.floor((n * t) / 2) * 2)
}

function progress(now: number, start: number, ms: number, reduced: boolean) {
  if (reduced) return 1
  return Math.min(1, Math.max(0, (now - start) / ms))
}

const easeOutCubic = (t: number) => 1 - (1 - t) ** 3
