import { useLayoutEffect, useMemo, useRef } from "react"
import { Html, Line, Text, type CameraControls } from "@react-three/drei"
import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber"
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation,
  type LinkForce,
  type SimNode,
} from "d3-force-3d"
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  Color,
  DoubleSide,
  Float32BufferAttribute,
  MathUtils,
  NormalBlending,
  Vector2,
  Vector3,
  type Group,
  type LineBasicMaterial,
  type LineSegments,
  type MeshBasicMaterial,
  type ShaderMaterial,
} from "three"

import { HOLOGRAM, MOTION, OPACITY, type SchematicPalette } from "~/design/tokens"
import type { GraphNode } from "~/stage/events"
import { NODE_TYPE_LABEL, type NodeType } from "~/stage/node-types"
import { FONT_LIGHT, FONT_MEDIUM } from "~/stage/scene/fonts"
import { uprightAmount } from "~/stage/scene/view-angle"
import { SchematicCallout } from "~/stage/schematic/callout"
import { DRAG_PX, easeOutCubic, fringeMaterialProps, progress, type TextLike } from "~/stage/schematic/scene/draw"
import { focusPoints } from "~/stage/schematic/scene/registry"
import { isDarkTheme, useTheme } from "~/stage/schematic/scene/theme"
import { useStage } from "~/stage/store"
import { useStageUi } from "./ui-store"

/**
 * 온톨로지 그래프 홀로그램(새 스타일).
 * - 노드는 바닥 위에 정사각 판을 층 간격(HOLOGRAM.layerGap)으로 쌓은 묶음이다. 맨 위 판 외곽선을 강조한다.
 *   유형은 색이나 모양이 아니라 보조 글자(「법안」「의원」…)로 적는다. 판 크기와 층 수는 유형별로 다르다.
 * - 데이터 색을 쓰지 않는다. 탐색 경로 위 노드·관계는 초점 단계, 나머지는 맥락 단계다. 초점 노드는 주황이다.
 * - 관계는 바닥 높이의 가는 선이다. 명시 관계는 실선, 추론 관계는 점선이다.
 *   탐색 경로는 출발점에서 도착점으로 한 번 그려지고, 그리는 동안 끝에 사각점이 붙는다.
 * - 탐색 순서는 노드 이름 아래 단계 번호(01, 02 …)로 남는다.
 * - 배치는 d3-force-3d 2차원 시뮬레이션이고 바닥(x, z)에 놓는다. 선택하면 층 간격이 벌어진다.
 * - 등장: 판이 바닥에서 펼쳐지고(점), 관계가 그려지고(선), 이름이 나타난다(글자).
 */

type SimN = SimNode & { type: NodeType }
type SimL = { id: string; source: string | SimN; target: string | SimN }

const NODE_SHAPE: Record<NodeType, { size: number; layers: number }> = {
  issue: { size: 1.0, layers: 7 },
  bill: { size: 0.85, layers: 6 },
  member: { size: 0.42, layers: 3 },
  party: { size: 0.62, layers: 4 },
  committee: { size: 0.66, layers: 4 },
  meeting: { size: 0.5, layers: 3 },
  statistic: { size: 0.55, layers: 4 },
  document: { size: 0.48, layers: 3 },
  claim: { size: 0.44, layers: 3 },
  region: { size: 0.6, layers: 4 },
}

const RADIUS = 9.5
const EDGE_Y = 0.04
const MAX_EDGES = 512
const EDGE_MS = MOTION.line.duration * 1.2
const PATH_STEP_MS = 380
const UNFOLD = { at: 80, ms: 600 }
const LABEL_AT = MOTION.point.duration + MOTION.line.duration
const LEADER = 2.0

const pad = (n: number) => String(n).padStart(2, "0")

export function GraphHologram({ reducedMotion }: { reducedMotion: boolean }) {
  const th = useTheme()
  const nodes = useStage((s) => s.nodes)
  const edges = useStage((s) => s.edges)
  const traversal = useStage((s) => s.traversal)
  const focus = useStage((s) => s.focus)
  const trail = useStage((s) => s.trail)
  const hovered = useStageUi((s) => s.hovered)

  const sim = useMemo(
    () =>
      forceSimulation<SimN>([], 2)
        .force(
          "link",
          forceLink<SimN, SimL>([])
            .id((d) => d.id)
            .distance(2.6)
            .strength(0.6)
        )
        .force("charge", forceManyBody<SimN>().strength(-11).distanceMax(12))
        .force("center", forceCenter<SimN>(0, 0).strength(0.5))
        .force("collide", forceCollide<SimN>((d) => NODE_SHAPE[d.type].size * 1.7))
        .alphaDecay(0.03)
        .velocityDecay(0.45)
        .stop(),
    []
  )
  const simNodes = useRef(new Map<string, SimN>())

  // 상태의 노드·관계를 시뮬레이션에 반영한다. 새 노드는 현재 초점 노드 근처에서 나타난다.
  useLayoutEffect(() => {
    const map = simNodes.current
    const ids = new Set(nodes.map((n) => n.id))
    for (const id of [...map.keys()]) {
      if (!ids.has(id)) {
        map.delete(id)
        focusPoints.node.delete(id)
      }
    }
    const current = useStage.getState().focus
    const anchor = current?.kind === "node" ? map.get(current.id) : undefined
    for (const n of nodes) {
      if (map.has(n.id)) continue
      const jitter = () => (Math.random() - 0.5) * 2
      const sn: SimN = { id: n.id, type: n.type, x: (anchor?.x ?? 0) + jitter(), y: (anchor?.y ?? 0) + jitter() }
      map.set(n.id, sn)
      focusPoints.node.set(n.id, new Vector3(sn.x, 0.6, sn.y))
    }
    sim.nodes([...map.values()])
    ;(sim.force("link") as LinkForce<SimN, SimL>).links(edges.map((e) => ({ id: e.id, source: e.source, target: e.target })))
    if (nodes.length) sim.alpha(Math.max(sim.alpha(), 0.4))
    if (reducedMotion) sim.tick(160)
  }, [nodes, edges, sim, reducedMotion])

  // 관계 선분: 명시(실선)·추론(점선)·탐색 경로 세 묶음
  const geos = useMemo(() => {
    const make = () => {
      const g = new BufferGeometry()
      g.setAttribute("position", new BufferAttribute(new Float32Array(MAX_EDGES * 6), 3))
      g.setDrawRange(0, 0)
      return g
    }
    return { explicit: make(), inferred: make(), path: make() }
  }, [])
  const inferredLines = useRef<LineSegments>(null)
  const head = useRef<Group>(null)
  const a = useMemo(() => new Vector3(), [])
  const b = useMemo(() => new Vector3(), [])

  const pathPairs = useMemo(() => {
    const p = traversal?.path ?? []
    return p.slice(1).map((id, i) => [p[i], id] as const)
  }, [traversal])
  const pathKeys = useMemo(() => new Set(pathPairs.flatMap(([s, d]) => [`${s}|${d}`, `${d}|${s}`])), [pathPairs])

  useFrame(() => {
    if (sim.alpha() > sim.alphaMin()) sim.tick()
    for (const [id, sn] of simNodes.current) {
      // 바닥 조명 범위를 벗어나지 않게 한다
      const r = Math.hypot(sn.x ?? 0, sn.y ?? 0)
      if (r > RADIUS) {
        sn.x = ((sn.x ?? 0) / r) * RADIUS
        sn.y = ((sn.y ?? 0) / r) * RADIUS
      }
      focusPoints.node.get(id)?.set(sn.x ?? 0, 0.6, sn.y ?? 0)
    }

    const now = performance.now()
    const counts = { explicit: 0, inferred: 0, path: 0 }
    const put = (key: keyof typeof counts, from: Vector3, to: Vector3) => {
      const arr = (geos[key].getAttribute("position") as BufferAttribute).array as Float32Array
      const o = counts[key] * 6
      if (o + 6 > arr.length) return
      arr.set([from.x, EDGE_Y, from.z, to.x, EDGE_Y, to.z], o)
      counts[key]++
    }
    const pos = (id: string, out: Vector3) => {
      const sn = simNodes.current.get(id)
      return sn ? out.set(sn.x ?? 0, 0, sn.y ?? 0) : null
    }

    for (const e of edges) {
      if (pathKeys.has(`${e.source}|${e.target}`)) continue
      if (!pos(e.source, a) || !pos(e.target, b)) continue
      const t = easeOutCubic(progress(now, e.addedAt, EDGE_MS, reducedMotion))
      b.sub(a).multiplyScalar(t).add(a)
      put(e.basis === "inferred" ? "inferred" : "explicit", a, b)
    }

    // 탐색 경로: 단계마다 차례로 그려진다(한 번만)
    let headVisible = false
    pathPairs.forEach(([s, d], k) => {
      if (!pos(s, a) || !pos(d, b) || !traversal) return
      const t = progress(now, traversal.startedAt + k * PATH_STEP_MS, PATH_STEP_MS, reducedMotion)
      if (t <= 0) return
      b.sub(a).multiplyScalar(easeOutCubic(t)).add(a)
      put("path", a, b)
      if (t < 1 && head.current) {
        head.current.position.set(b.x, EDGE_Y, b.z)
        headVisible = true
      }
    })
    if (head.current) head.current.visible = headVisible

    for (const key of ["explicit", "inferred", "path"] as const) {
      const g = geos[key]
      g.setDrawRange(0, counts[key] * 2)
      g.getAttribute("position").needsUpdate = true
      g.computeBoundingSphere()
    }
    inferredLines.current?.computeLineDistances()
  })

  const stepOf = useMemo(() => {
    const m = new Map<string, number>()
    trail.forEach((t, i) => t.kind === "node" && m.set(t.id, i + 1))
    return m
  }, [trail])
  const onPath = useMemo(() => new Set(traversal?.path ?? []), [traversal])
  const focusedId = focus?.kind === "node" ? focus.id : null

  return (
    <group>
      <lineSegments geometry={geos.explicit} frustumCulled={false}>
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.context.value} depthWrite={false} />
      </lineSegments>
      <lineSegments ref={inferredLines} geometry={geos.inferred} frustumCulled={false}>
        <lineDashedMaterial color={th.ink} dashSize={0.18} gapSize={0.14} transparent opacity={OPACITY.context.value} depthWrite={false} />
      </lineSegments>
      <lineSegments geometry={geos.path} frustumCulled={false}>
        <lineBasicMaterial color={th.ink} transparent opacity={OPACITY.focus.value} depthWrite={false} />
      </lineSegments>
      <group ref={head} visible={false}>
        <mesh rotation-x={-Math.PI / 2}>
          <planeGeometry args={[0.16, 0.16]} />
          <meshBasicMaterial color={th.ink} />
        </mesh>
      </group>

      {nodes.map((n) => (
        <NodeHologram
          key={n.id}
          node={n}
          sim={simNodes.current}
          step={stepOf.get(n.id) ?? null}
          focused={focusedId === n.id}
          active={onPath.has(n.id)}
          dimmed={focusedId !== null && focusedId !== n.id && !onPath.has(n.id)}
          hovered={hovered?.kind === "node" && hovered.id === n.id}
          reducedMotion={reducedMotion}
        />
      ))}
    </group>
  )
}

/** 정사각 판 층 묶음 형상. 맨 위 판이 가장 밝고 아래 판일수록 바탕색에 가깝다. */
function squareLayers(size: number, count: number, th: SchematicPalette) {
  const s = size
  const ring = [-s, -s, s, -s, s, -s, s, s, s, s, -s, s, -s, s, -s, -s]
  const scene = new Color(th.scene)
  const ink = new Color(th.ink)
  const c = new Color()
  const lp: number[] = []
  const lc: number[] = []
  for (let k = 0; k < count; k++) {
    const y = (k + 1) * HOLOGRAM.layerGap
    const a = k === count - 1 ? 1 : 0.22 + 0.5 * ((k + 1) / count) ** 1.5
    c.copy(scene).lerp(ink, a * 0.85)
    for (let i = 0; i < ring.length; i += 2) {
      lp.push(ring[i], y, ring[i + 1])
      lc.push(c.r, c.g, c.b)
    }
  }
  const g = new BufferGeometry()
  g.setAttribute("position", new Float32BufferAttribute(lp, 3))
  g.setAttribute("color", new Float32BufferAttribute(lc, 3))
  return g
}

function NodeHologram({
  node,
  sim,
  step,
  focused,
  active,
  dimmed,
  hovered,
  reducedMotion,
}: {
  node: GraphNode & { addedAt: number }
  sim: Map<string, SimN>
  step: number | null
  focused: boolean
  active: boolean
  dimmed: boolean
  hovered: boolean
  reducedMotion: boolean
}) {
  const th = useTheme()
  const dark = useMemo(() => isDarkTheme(th), [th])
  const setFocus = useStage((s) => s.setFocus)
  const setHovered = useStageUi((s) => s.setHovered)
  const controls = useThree((s) => s.controls) as CameraControls | null
  const dpr = useThree((s) => s.viewport.dpr)
  const { size, layers } = NODE_SHAPE[node.type]
  const full = layers * HOLOGRAM.layerGap

  const stackGeo = useMemo(() => squareLayers(size, layers, th), [size, layers, th])
  const topPoints = useMemo(
    () =>
      [
        [-size, -size],
        [size, -size],
        [size, -size],
        [size, size],
        [size, size],
        [-size, size],
        [-size, size],
        [-size, -size],
      ].map(([x, z]) => new Vector3(x, 0, z)),
    [size]
  )
  const fringeProps = useMemo(
    () =>
      (["#ff2d55", "#00d8ff"] as const).map((c, i) =>
        fringeMaterialProps(c, (i === 0 ? -1 : 1) * HOLOGRAM.fringe.px * dpr, dark ? AdditiveBlending : NormalBlending)
      ),
    [dpr, dark]
  )

  const root = useRef<Group>(null)
  const stack = useRef<Group>(null)
  const top = useRef<Group>(null)
  const label = useRef<Group>(null)
  const leader = useRef<Group>(null)
  const callout = useRef<Group>(null)
  const lineMat = useRef<LineBasicMaterial>(null)
  const fillMat = useRef<MeshBasicMaterial>(null)
  const topLine = useRef<{ material: { opacity: number } } | null>(null)
  const fringeMats = useRef<(ShaderMaterial | null)[]>([])
  const texts = useRef<(TextLike | null)[]>([])
  const spread = useRef(1)
  const up = useRef(0)
  const res = useMemo(() => new Vector2(), [])

  useFrame((state, delta) => {
    const sn = sim.get(node.id)
    if (root.current && sn) root.current.position.set(sn.x ?? 0, 0, sn.y ?? 0)
    const now = performance.now()

    const target = focused ? Math.min(HOLOGRAM.focusSpread, 1 + HOLOGRAM.focusRiseMax / full) : 1
    spread.current = reducedMotion ? target : MathUtils.damp(spread.current, target, 5, delta)
    const unfold = easeOutCubic(progress(now, node.addedAt + UNFOLD.at, UNFOLD.ms, reducedMotion))
    const appear = progress(now, node.addedAt, MOTION.point.duration, reducedMotion)
    const k = Math.max(0.001, unfold * spread.current)
    stack.current?.scale.set(1, k, 1)
    const h = full * k
    top.current?.position.setY(h + 0.002)

    const o = (focused || active || hovered ? 1 : dimmed ? 0.3 : 0.6) * appear
    if (lineMat.current) lineMat.current.opacity = o
    if (fillMat.current) fillMat.current.opacity = (focused || hovered ? 0.12 : 0.05) * appear
    if (topLine.current) topLine.current.material.opacity = (focused || active || hovered ? 1 : dimmed ? 0.3 : 0.55) * appear
    state.gl.getDrawingBufferSize(res)
    for (const m of fringeMats.current) {
      if (!m) continue
      m.uniforms.uOpacity.value = (focused || active ? HOLOGRAM.fringe.colored : HOLOGRAM.fringe.neutral) * (dimmed ? 0.4 : 1) * appear
      m.uniforms.uRes.value.copy(res)
    }

    // 이름: 카메라가 높으면 눕고 낮으면 선다(공간 속 글자 규칙)
    const t = controls ? uprightAmount(controls.polarAngle) : 0
    up.current = reducedMotion ? t : MathUtils.damp(up.current, t, 6, delta)
    if (label.current) {
      label.current.position.set(0, h + 0.05 + up.current * 0.25, 0)
      label.current.rotation.set(MathUtils.lerp(-Math.PI / 2, 0, up.current), controls?.azimuthAngle ?? 0, 0, "YXZ")
    }
    const a = progress(now, node.addedAt + LABEL_AT, MOTION.text.duration, reducedMotion)
    const textO = focused ? 0 : (active || hovered ? 1 : dimmed ? 0.3 : 0.7) * a
    texts.current.forEach((tx, i) => {
      if (tx) tx.fillOpacity = textO * (i === 0 ? 1 : OPACITY.related.value)
    })

    leader.current?.position.setY(h)
    callout.current?.position.setY(h + LEADER)
  })

  const select = (e: ThreeEvent<MouseEvent>) => {
    e.stopPropagation()
    if (e.delta > DRAG_PX) return
    setFocus({ kind: "node", id: node.id })
  }
  const caption = `${step ? `${pad(step)} · ` : ""}${NODE_TYPE_LABEL[node.type]}`

  return (
    <group ref={root}>
      <group ref={stack}>
        {fringeProps.map((props, i) => (
          <lineSegments key={`${i}-${dark}-${dpr}`} geometry={stackGeo}>
            <shaderMaterial ref={(m) => void (fringeMats.current[i] = m)} {...props} />
          </lineSegments>
        ))}
        <lineSegments geometry={stackGeo}>
          <lineBasicMaterial ref={lineMat} vertexColors transparent opacity={0} depthWrite={false} />
        </lineSegments>
      </group>
      <group ref={top}>
        <mesh rotation-x={-Math.PI / 2}>
          <planeGeometry args={[size * 2, size * 2]} />
          <meshBasicMaterial ref={fillMat} color={focused ? th.accent : th.ink} transparent opacity={0} depthWrite={false} side={DoubleSide} />
        </mesh>
        <Line
          ref={(l: unknown) => void (topLine.current = l as typeof topLine.current)}
          points={topPoints}
          segments
          color={focused ? th.accent : th.ink}
          lineWidth={focused || hovered ? 2.4 : active ? 1.8 : 1.2}
          transparent
          opacity={0}
          depthWrite={false}
        />
      </group>

      {/* 포인터 판정용 보이지 않는 상자 */}
      <mesh
        position-y={full / 2}
        onClick={select}
        onPointerOver={(e) => {
          e.stopPropagation()
          setHovered({ kind: "node", id: node.id, label: node.label })
          document.body.style.cursor = "pointer"
        }}
        onPointerOut={() => {
          setHovered(null)
          document.body.style.cursor = ""
        }}
      >
        <boxGeometry args={[size * 2, Math.max(full, 0.4), size * 2]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} colorWrite={false} />
      </mesh>

      <group ref={label}>
        <Text
          ref={(t: unknown) => void (texts.current[0] = t as TextLike | null)}
          font={focused || active ? FONT_MEDIUM : FONT_LIGHT}
          fontSize={0.24}
          letterSpacing={0.04}
          color={th.ink}
          fillOpacity={0}
          anchorX="center"
          anchorY="bottom"
          position-y={0.06}
          renderOrder={5}
        >
          {node.label}
        </Text>
        <Text
          ref={(t: unknown) => void (texts.current[1] = t as TextLike | null)}
          font={FONT_LIGHT}
          fontSize={0.13}
          letterSpacing={0.22}
          color={th.ink}
          fillOpacity={0}
          anchorX="center"
          anchorY="top"
          position-y={0.02}
          renderOrder={5}
        >
          {caption}
        </Text>
      </group>

      {focused ? (
        <>
          <group ref={leader}>
            <mesh position-y={LEADER / 2}>
              <boxGeometry args={[0.012, LEADER, 0.012]} />
              <meshBasicMaterial color={th.accent} />
            </mesh>
          </group>
          <group ref={callout}>
            <Html zIndexRange={[15, 15]} style={{ pointerEvents: "none" }}>
              <SchematicCallout
                code={step ? pad(step) : "··"}
                unit={NODE_TYPE_LABEL[node.type]}
                title={node.label}
                line={node.detail ? { text: node.detail } : null}
                source={node.source}
                animate={!reducedMotion}
                delay={300}
              />
            </Html>
          </group>
        </>
      ) : null}
    </group>
  )
}

