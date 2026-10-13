import { useEffect, useMemo, useRef, useState, type RefObject } from "react"
import { CameraControls, Html, Line, Text } from "@react-three/drei"
import { Canvas, useFrame, useThree, type ThreeEvent } from "@react-three/fiber"
import {
  AdditiveBlending,
  BufferGeometry,
  Color,
  DoubleSide,
  ExtrudeGeometry,
  Float32BufferAttribute,
  MathUtils,
  NormalBlending,
  NoToneMapping,
  ShapeGeometry,
  Vector2,
  Vector3,
  type Group,
  type LineBasicMaterial,
  type MeshBasicMaterial,
  type ShaderMaterial,
} from "three"

import { dataColor } from "~/design/palette"
import { HOLOGRAM, MAP_MOTION, OPACITY, type SchematicPalette } from "~/design/tokens"
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
import { SceneBackdrop } from "../scene/backdrop"
import {
  DRAG_PX,
  easeOutCubic,
  fringeMaterialProps,
  lineGeometry,
  outlineGeometry,
  progress,
  setDrawProgress,
  type TextLike,
} from "../scene/draw"
import { SceneEffects } from "../scene/effects"
import { focusPoints } from "../scene/registry"
import { isDarkTheme, ThemeContext, useTheme } from "../scene/theme"
import { RegionCallout } from "./region-callout"

export type MapView = "overview" | "top" | "low"
export type MapSource = { label: string; span?: string }

export type MapSceneProps = {
  values: Record<string, RegionValue>
  /** 색으로 표시할 지역 코드. 없으면 값이 있는 모든 지역. 나머지는 높이만 두고 중립색으로 그린다 */
  colored?: string[]
  source: MapSource
  focus: string | null
  hovered: string | null
  onFocus: (code: string | null) => void
  onHover: (region: { code: string; name: string } | null) => void
  /** 보기 전환 요청. n 이 바뀔 때마다 카메라를 그 보기로 옮긴다 */
  view: { name: MapView; n: number }
  /** 장면 색(SCHEMATIC_THEMES 의 한 모드) */
  theme: SchematicPalette
  /** 카메라 방위·기울기·거리를 적을 DOM 요소 */
  readout: RefObject<HTMLSpanElement | null>
  reducedMotion: boolean
}

const MAP_SIZE = 16
const EXPAND_FROM = MAP_MOTION.expandFrom
const BASE_H = 0.1
const MAX_H = HOLOGRAM.maxHeight
const FRINGE = HOLOGRAM.fringe

const LAYER_GAP = HOLOGRAM.layerGap
const FOCUS_SPREAD = HOLOGRAM.focusSpread
const FOCUS_RISE_MAX = HOLOGRAM.focusRiseMax

const LEADER = 2.6
/** 등장 시각. 값과 설명은 design/tokens.ts 의 MAP_MOTION */
const T = MAP_MOTION

const VIEWS: Record<MapView, { position: [number, number, number]; target: [number, number, number] }> = {
  overview: { position: [0, 21, 20], target: [0, 0, 0.6] },
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
  // 배경 클릭으로 선택을 푼다. 회전·이동하려고 끈 경우는 클릭으로 보지 않는다.
  const down = useRef<{ x: number; y: number } | null>(null)
  return (
    <Canvas
      onPointerDown={(e) => (down.current = { x: e.clientX, y: e.clientY })}
      onPointerMissed={(e) => {
        const d = down.current
        if (d && Math.hypot(e.clientX - d.x, e.clientY - d.y) <= DRAG_PX) props.onFocus(null)
      }}
      dpr={[1, 2]}
      camera={{ position: [0, 30, 30], fov: 36, near: 0.1, far: 200 }}
      gl={{ antialias: true, toneMapping: NoToneMapping }}
    >
      <SceneBackdrop theme={props.theme} />
      <ThemeContext.Provider value={props.theme}>
        <MapHologram {...props} />
        <MapCamera {...props} />
      </ThemeContext.Provider>
      <SceneEffects
        target={(out) => {
          const p = props.focus ? focusPoints.region.get(props.focus) : undefined
          return p ? out.copy(p) : null
        }}
      />
    </Canvas>
  )
}

export type MapHologramProps = Pick<
  MapSceneProps,
  "values" | "colored" | "source" | "focus" | "hovered" | "onFocus" | "onHover" | "reducedMotion"
>

/** 지도 홀로그램(지역 층·이름·틀·방위 고리·선택 표시). 지도 페이지와 메인 스테이지가 같은 장면 안에 둔다. */
export function MapHologram({ values, colored, source, focus, hovered, onFocus, onHover, reducedMotion }: MapHologramProps) {
  const colorSet = useMemo(() => (colored ? new Set(colored) : null), [colored])
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
    for (const r of data.regions) focusPoints.region.set(r.code, r.centroid)
  }, [data])

  // 지도 중심에서 가장 먼 지역 중심까지의 거리. 퍼지는 고리가 이 거리에 닿을 때 마지막 지역이 나타난다.
  const maxDist = useMemo(
    () => (data ? Math.max(...data.regions.map((r) => Math.hypot(r.centroid.x, r.centroid.z))) : 1),
    [data]
  )
  const expand = useRef<Group>(null)
  useFrame(() => {
    if (!data || !expand.current) return
    const e = easeOutCubic(progress(performance.now(), data.t0, T.expand.ms, reducedMotion))
    const k = EXPAND_FROM + (1 - EXPAND_FROM) * e
    expand.current.scale.set(k, 1, k)
  })

  if (!data) return null
  const { collection, regions, t0 } = data
  const focused = focus ? regions.find((r) => r.code === focus) : undefined

  return (
    <group ref={expand} scale={[EXPAND_FROM, 1, EXPAND_FROM]}>
      <ExpandWave radius={maxDist + 1.5} t0={t0} reducedMotion={reducedMotion} />
      {regions.map((r) => {
        const common = {
          region: r,
          delay: T.wave.at + (Math.hypot(r.centroid.x, r.centroid.z) / maxDist) * T.wave.ms,
          t0,
          focused: focus === r.code,
          dimmed: focus !== null && focus !== r.code,
          hovered: hovered === r.code,
          heights: heights.current,
          reducedMotion,
        }
        return (
          <group key={r.code}>
            <RegionVolume
              {...common}
              value={values[r.code]}
              // 선택한 지역은 중립색이었더라도 데이터 색을 보여 준다
              neutral={!values[r.code] || (colorSet !== null && !colorSet.has(r.code) && focus !== r.code)}
              onFocus={onFocus}
              onHover={onHover}
            />
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

/**
 * 등장 고리: 바닥에서 가운데부터 바깥으로 퍼지는 원. 고리가 지나간 자리에 지역이 나타난다.
 * 퍼지는 동안 옅어지고 끝나면 보이지 않는다(한 번만 재생).
 */
function ExpandWave({ radius, t0, reducedMotion }: { radius: number; t0: number; reducedMotion: boolean }) {
  const th = useTheme()
  const ring = useMemo(() => {
    const pts: number[] = []
    const n = 192
    for (let i = 0; i < n; i++) {
      const a1 = (i / n) * Math.PI * 2
      const a2 = ((i + 1) / n) * Math.PI * 2
      pts.push(Math.sin(a1), 0, -Math.cos(a1), Math.sin(a2), 0, -Math.cos(a2))
    }
    return lineGeometry(pts)
  }, [])
  const outer = useRef<Group>(null)
  const inner = useRef<Group>(null)
  const mats = useRef<(LineBasicMaterial | null)[]>([])

  useFrame(() => {
    const p = progress(performance.now(), t0 + T.wave.at, T.wave.ms, reducedMotion)
    const r = Math.max(0.001, radius * p)
    outer.current?.scale.set(r, 1, r)
    inner.current?.scale.set(r * 0.92, 1, r * 0.92)
    const o = reducedMotion || p <= 0 || p >= 1 ? 0 : 0.9 * (1 - p ** 3)
    if (mats.current[0]) mats.current[0].opacity = o
    if (mats.current[1]) mats.current[1].opacity = o * 0.35
  })

  return (
    <group position-y={0.01}>
      {[outer, inner].map((g, i) => (
        <group key={i} ref={g}>
          <lineSegments geometry={ring}>
            <lineBasicMaterial ref={(m) => void (mats.current[i] = m)} color={th.ink} transparent opacity={0} depthWrite={false} />
          </lineSegments>
        </group>
      ))}
    </group>
  )
}

type RegionCommon = {
  region: ProjectedRegion
  /** 등장 지연(ms, t0 기준). 지도 중심에서의 거리에 비례한다 */
  delay: number
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
 * 맨 위 층 외곽선은 판독성을 위해 화면 픽셀 두께의 굵은 선(drei Line)으로 강조한다
 * (WebGL 기본 선은 두께가 1px 로 고정이다).
 * 등장할 때 층이 아래에서부터 하나씩 쌓인다.
 * 선택하면 층 수는 그대로 두고 층 간격이 벌어지며(최대 FOCUS_SPREAD 배, 늘어나는 높이 최대 FOCUS_RISE_MAX) 묶음이 위로 늘어나고,
 * 선택을 풀면 원래 간격으로 돌아온다. 층은 두께가 없는 평면이므로 묶음의 세로 배율만 바꾼다.
 */
function RegionVolume({
  region,
  value,
  delay,
  t0,
  focused,
  dimmed,
  hovered,
  heights,
  reducedMotion,
  onFocus,
  onHover,
  neutral,
}: RegionCommon & Pick<MapSceneProps, "onFocus" | "onHover"> & { value: RegionValue | undefined; neutral: boolean }) {
  const th = useTheme()
  const count = value ? Math.max(1, Math.round((value.magnitude * MAX_H) / LAYER_GAP)) : 1
  const color = useMemo(() => new Color(value && !neutral ? dataColor(value.category) : th.neutral), [value, neutral, th])
  const layers = useMemo(() => buildLayers(region, count, color, !neutral, th), [region, count, color, neutral, th])
  // 포인터 판정용 보이지 않는 기둥. 층 사이 빈 곳을 가리켜도 지역이 잡히게 한다.
  const hit = useMemo(
    () => new ExtrudeGeometry(region.shapes, { depth: 1, bevelEnabled: false, curveSegments: 1 }),
    [region.shapes]
  )
  const outline = useMemo(() => outlineGeometry(region.outlines), [region.outlines])
  const topPoints = useMemo(() => {
    const pts: Vector3[] = []
    for (const r of region.outlines) for (let i = 0; i < r.length - 1; i++) pts.push(r[i], r[i + 1])
    return pts
  }, [region.outlines])
  const topColor = useMemo(() => color.clone().lerp(new Color(th.ink), neutral ? 0.2 : 0.5), [color, neutral, th])

  const hitColumn = useRef<Group>(null)
  const lineMat = useRef<LineBasicMaterial>(null)
  const fillMat = useRef<MeshBasicMaterial>(null)
  const base = useRef<LineBasicMaterial>(null)
  const top = useRef<Group>(null)
  const stack = useRef<Group>(null)
  const fringeMats = useRef<(ShaderMaterial | null)[]>([])
  const res = useMemo(() => new Vector2(), [])
  const dpr = useThree((st) => st.viewport.dpr)
  const dark = useMemo(() => isDarkTheme(th), [th])
  const fringeProps = useMemo(
    () =>
      (["#ff2d55", "#00d8ff"] as const).map((c, i) =>
        fringeMaterialProps(c, (i === 0 ? -1 : 1) * FRINGE.px * dpr, dark ? AdditiveBlending : NormalBlending)
      ),
    [dpr, dark]
  )
  const spread = useRef(1)
  const topLine = useRef<{ material: { opacity: number } } | null>(null)

  useFrame((state, delta) => {
    const now = performance.now()
    const tOutline = progress(now, t0 + delay, T.region.outlineMs, reducedMotion)
    // 바닥에 포개져 있던 층 사이가 벌어지며 위로 펼쳐진다
    const unfold = easeOutCubic(progress(now, t0 + delay + T.region.unfoldAt, T.region.unfoldMs, reducedMotion))
    const full = count * LAYER_GAP
    const target = focused ? Math.min(FOCUS_SPREAD, 1 + FOCUS_RISE_MAX / full) : 1
    spread.current = reducedMotion ? target : MathUtils.damp(spread.current, target, 5, delta)
    const k = Math.max(0.001, unfold * spread.current)
    stack.current?.scale.set(1, k, 1)
    const h = full * k
    heights.set(region.code, Math.max(h, BASE_H))
    hitColumn.current?.scale.set(1, 1, Math.max(0.001, h))
    setDrawProgress(outline, tOutline)

    if (base.current) base.current.opacity = (dimmed ? OPACITY.faint.value : OPACITY.context.value) * tOutline
    const o = (focused || hovered ? 1 : dimmed ? 0.22 : neutral ? 0.6 : 0.85) * tOutline
    if (lineMat.current) lineMat.current.opacity = o

    // 층 외곽선 색 번짐: 빨강·청록 사본을 화면 픽셀 단위로 좌우에 어긋나게 둔다
    const f = (neutral ? FRINGE.neutral : FRINGE.colored) * (dimmed ? 0.4 : 1) * (dark ? 1 : 0.8) * tOutline
    state.gl.getDrawingBufferSize(res)
    for (const m of fringeMats.current) {
      if (!m) continue
      m.uniforms.uOpacity.value = f
      m.uniforms.uRes.value.copy(res)
    }
    if (fillMat.current) fillMat.current.opacity = o * (focused || hovered ? 0.7 : 0.5)

    // 맨 위 층 강조선: 펼쳐지는 맨 위 층을 따라간다
    top.current?.position.setY(h + 0.002)
    if (topLine.current) topLine.current.material.opacity = (dimmed ? 0.3 : 1) * tOutline
  })

  const select = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    // 회전하려고 끈 경우는 선택으로 보지 않는다
    if (e.delta > DRAG_PX) return
    onFocus(region.code)
  }

  return (
    <group>
      <lineSegments geometry={outline} position-y={0.004}>
        <lineBasicMaterial ref={base} color={th.ink} transparent opacity={0} depthWrite={false} />
      </lineSegments>
      <group ref={stack}>
        {fringeProps.map((props, i) => (
          <lineSegments key={`${i}-${dark}-${dpr}`} geometry={layers.lines}>
            <shaderMaterial ref={(m) => void (fringeMats.current[i] = m)} {...props} />
          </lineSegments>
        ))}
        <lineSegments geometry={layers.lines}>
          <lineBasicMaterial ref={lineMat} vertexColors transparent opacity={0} depthWrite={false} />
        </lineSegments>
        <mesh geometry={layers.fills}>
          <meshBasicMaterial ref={fillMat} vertexColors transparent opacity={0} depthWrite={false} side={DoubleSide} />
        </mesh>
      </group>
      <group ref={top}>
        <Line
          ref={(l: unknown) => void (topLine.current = l as typeof topLine.current)}
          points={topPoints}
          segments
          color={topColor}
          lineWidth={focused || hovered ? 2.4 : neutral ? 1.2 : 1.8}
          transparent
          opacity={0}
          depthWrite={false}
        />
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
function buildLayers(region: ProjectedRegion, count: number, color: Color, colored: boolean, th: SchematicPalette) {
  const scene = new Color(th.scene)
  const top = color.clone().lerp(new Color(th.ink), colored ? 0.3 : 0.1)
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
    const a = (isTop ? 1 : 0.22 + 0.5 * ((k + 1) / count) ** 1.5) * (colored ? 1 : 0.7)
    c.copy(scene).lerp(top, a)
    for (let v = 0; v < lineStride; v++) {
      const o = (k * lineStride + v) * 3
      lp.set([ring[v * 2], y, ring[v * 2 + 1]], o)
      lc.set([c.r, c.g, c.b], o)
    }
    // 중립 지역은 면을 거의 채우지 않아 색이 있는 지역보다 뒤로 물러나 보이게 한다
    c.copy(scene).lerp(color, colored ? (isTop ? 0.7 : 0.14) : isTop ? 0.16 : 0.04)
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
function RegionLabel({ region, delay, t0, focused, dimmed, hovered, heights, reducedMotion }: RegionCommon) {
  const th = useTheme()
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
    const a = progress(performance.now(), t0 + delay + T.label.at, T.label.ms, reducedMotion)
    if (text.current) text.current.fillOpacity = a * (focused ? 0 : hovered ? 1 : dimmed ? 0.3 : 0.8)
  })

  return (
    <group ref={group}>
      <Text
        ref={(t: unknown) => void (text.current = t as TextLike | null)}
        font={hovered ? FONT_MEDIUM : FONT_LIGHT}
        fontSize={fontSize}
        letterSpacing={0.08}
        color={th.ink}
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
  const th = useTheme()
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
          <lineBasicMaterial color={th.accent} transparent depthTest={false} />
        </lineSegments>
      </group>
      <lineSegments geometry={trace} position-y={0.008}>
        <lineBasicMaterial color={th.accent} transparent opacity={OPACITY.related.value} />
      </lineSegments>
      <group ref={pulse}>
        <lineSegments geometry={pulseGeo}>
          <lineBasicMaterial ref={pulseMat} color={th.accent} transparent opacity={0} depthWrite={false} />
        </lineSegments>
      </group>
      <group ref={leader}>
        <lineSegments geometry={leaderGeo} renderOrder={6}>
          <lineBasicMaterial color={th.accent} transparent depthTest={false} />
        </lineSegments>
        {/* 지시선 아래 끝: 윗면의 작은 사각점 */}
        <mesh rotation-x={-Math.PI / 2} renderOrder={6}>
          <planeGeometry args={[0.14, 0.14]} />
          <meshBasicMaterial ref={foot} color={th.accent} transparent opacity={0} depthTest={false} />
        </mesh>
      </group>
      <group ref={callout}>
        {/* 화면 고정 주석 뒤 어두운 층(z-10) 위, 화면 고정 주석(z-20) 아래에 둔다 */}
        <Html zIndexRange={[15, 15]} style={{ pointerEvents: "none" }}>
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
  const th = useTheme()
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
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.related.value} />
      </lineSegments>
      <lineSegments geometry={built.faint}>
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.context.value} />
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
          color={th.ink}
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
  const th = useTheme()
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
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.context.value} />
      </lineSegments>
      <lineSegments geometry={minor}>
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.faint.value * 2} />
      </lineSegments>
      <lineSegments geometry={major}>
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.related.value} />
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
          color={th.ink}
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
      const p = focusPoints.region.get(focus)
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

