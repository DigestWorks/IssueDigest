import { useEffect, useLayoutEffect, useMemo, useRef } from "react"
import { useFrame, useThree, type ThreeEvent } from "@react-three/fiber"
import {
  forceCenter,
  forceLink,
  forceManyBody,
  forceSimulation,
  forceY,
  type LinkForce,
  type SimNode,
} from "d3-force-3d"
import {
  BufferAttribute,
  BufferGeometry,
  Color,
  InstancedMesh,
  Object3D,
  Plane,
  Vector3,
  type Group,
} from "three"

import { NEUTRAL, type NodeType } from "~/design/palette"
import { useStage } from "../store"
import { nodePositions, sceneFlags } from "../scene/registry"
import { GraphNodeMesh } from "./graph-node"

type SimN = SimNode & { type: NodeType }
type SimL = { id: string; source: string | SimN; target: string | SimN }

const MAX_EDGES = 2048
const EDGE_GROW_MS = 550
const PARTICLES = 18
const CENTER_Y = 3.2
const MIN_Y = 0.8
const MAX_Y = 7.5

/**
 * 온톨로지 그래프. d3-force-3d 힘 기반 시뮬레이션으로 노드를 배치하고,
 * 노드를 드래그하면 연결된 노드가 시뮬레이션에 따라 움직인다.
 */
export function GraphLayer({ reducedMotion }: { reducedMotion: boolean }) {
  const nodes = useStage((s) => s.nodes)
  const edges = useStage((s) => s.edges)
  const traversal = useStage((s) => s.traversal)
  const focus = useStage((s) => s.focus)
  const setFocus = useStage((s) => s.setFocus)

  const sim = useMemo(
    () =>
      forceSimulation<SimN>([], 3)
        .force(
          "link",
          forceLink<SimN, SimL>([])
            .id((d) => d.id)
            .distance(2.4)
            .strength(0.7)
        )
        .force("charge", forceManyBody<SimN>().strength(-3.2).distanceMax(9))
        .force("center", forceCenter<SimN>(0, CENTER_Y, 0).strength(0.8))
        // 그래프를 지면 위 일정 높이의 판에 가깝게 둔다
        .force("height", forceY<SimN>(CENTER_Y).strength(0.06))
        .alphaDecay(0.028)
        .velocityDecay(0.45)
        .stop(),
    []
  )
  const simNodes = useRef(new Map<string, SimN>())
  const groups = useRef(new Map<string, Group>())

  // 상태의 노드·엣지를 시뮬레이션에 반영한다. 새 노드는 현재 초점 근처에서 나타난다.
  useLayoutEffect(() => {
    const map = simNodes.current
    const ids = new Set(nodes.map((n) => n.id))
    for (const id of [...map.keys()]) {
      if (!ids.has(id)) {
        map.delete(id)
        nodePositions.delete(id)
      }
    }
    const current = useStage.getState().focus
    const anchor = current?.kind === "node" ? map.get(current.id) : undefined
    for (const n of nodes) {
      if (map.has(n.id)) continue
      const jitter = () => (Math.random() - 0.5) * 1.6
      const sn: SimN = {
        id: n.id,
        type: n.type,
        x: (anchor?.x ?? 0) + jitter(),
        y: (anchor?.y ?? CENTER_Y) + jitter(),
        z: (anchor?.z ?? 0) + jitter(),
      }
      map.set(n.id, sn)
      nodePositions.set(n.id, new Vector3(sn.x, sn.y, sn.z))
    }
    sim.nodes([...map.values()])
    ;(sim.force("link") as LinkForce<SimN, SimL>).links(
      edges.map((e) => ({ id: e.id, source: e.source, target: e.target }))
    )
    if (nodes.length) sim.alpha(Math.max(sim.alpha(), 0.35))
    if (reducedMotion) sim.tick(120)
  }, [nodes, edges, sim, reducedMotion])

  // 엣지 선분 버퍼
  const edgeGeometry = useMemo(() => {
    const g = new BufferGeometry()
    g.setAttribute("position", new BufferAttribute(new Float32Array(MAX_EDGES * 6), 3))
    g.setDrawRange(0, 0)
    return g
  }, [])
  const pathGeometry = useMemo(() => {
    const g = new BufferGeometry()
    g.setAttribute("position", new BufferAttribute(new Float32Array(64 * 6), 3))
    g.setDrawRange(0, 0)
    return g
  }, [])

  const particles = useRef<InstancedMesh>(null)
  const dummy = useMemo(() => new Object3D(), [])
  const a = useMemo(() => new Vector3(), [])
  const b = useMemo(() => new Vector3(), [])

  useFrame((state) => {
    if (sim.alpha() > sim.alphaMin() || sceneFlags.dragging) sim.tick()

    for (const [id, sn] of simNodes.current) {
      // 지면 아래로 내려가거나 너무 높이 뜨지 않게 한다
      if (sn.y !== undefined && (sn.y < MIN_Y || sn.y > MAX_Y)) {
        sn.y = Math.min(MAX_Y, Math.max(MIN_Y, sn.y))
        sn.vy = 0
      }
      const p = nodePositions.get(id)
      p?.set(sn.x ?? 0, sn.y ?? 0, sn.z ?? 0)
      const g = groups.current.get(id)
      if (g && p) g.position.copy(p)
    }

    // 엣지: 등장 시 출발 노드에서 도착 노드로 그려진다.
    const now = performance.now()
    const pos = edgeGeometry.attributes.position as BufferAttribute
    let count = 0
    for (const e of edges) {
      if (count >= MAX_EDGES) break
      const s = nodePositions.get(e.source)
      const t = nodePositions.get(e.target)
      if (!s || !t) continue
      const grow = reducedMotion ? 1 : Math.min(1, (now - e.addedAt) / EDGE_GROW_MS)
      a.copy(s)
      b.copy(s).lerp(t, easeOutCubic(grow))
      pos.setXYZ(count * 2, a.x, a.y, a.z)
      pos.setXYZ(count * 2 + 1, b.x, b.y, b.z)
      count++
    }
    edgeGeometry.setDrawRange(0, count * 2)
    pos.needsUpdate = true

    // 탐색 경로 강조선과 경로를 따라 이동하는 파티클
    const path = traversal?.path ?? []
    const pts = path.map((id) => nodePositions.get(id)).filter((v): v is Vector3 => !!v)
    const ppos = pathGeometry.attributes.position as BufferAttribute
    for (let i = 0; i < pts.length - 1; i++) {
      ppos.setXYZ(i * 2, pts[i].x, pts[i].y, pts[i].z)
      ppos.setXYZ(i * 2 + 1, pts[i + 1].x, pts[i + 1].y, pts[i + 1].z)
    }
    pathGeometry.setDrawRange(0, Math.max(0, pts.length - 1) * 2)
    ppos.needsUpdate = true

    const inst = particles.current
    if (inst) {
      const segs = pts.length - 1
      for (let i = 0; i < PARTICLES; i++) {
        if (segs < 1) {
          dummy.scale.setScalar(0)
        } else {
          const speed = reducedMotion ? 0 : 0.28
          const u = (state.clock.elapsedTime * speed + i / PARTICLES) % 1
          const f = u * segs
          const k = Math.min(segs - 1, Math.floor(f))
          dummy.position.copy(pts[k]).lerp(pts[k + 1], f - k)
          const fade = Math.sin(Math.PI * (f - k))
          dummy.scale.setScalar(0.4 + 0.6 * fade)
        }
        dummy.updateMatrix()
        inst.setMatrixAt(i, dummy.matrix)
      }
      inst.instanceMatrix.needsUpdate = true
    }
  })

  useEffect(() => () => void sim.stop(), [sim])

  const drag = useNodeDrag(simNodes, sim, setFocus)

  return (
    <group>
      <lineSegments geometry={edgeGeometry} frustumCulled={false}>
        <lineBasicMaterial color={NEUTRAL.line} transparent opacity={0.22} depthWrite={false} />
      </lineSegments>
      <lineSegments geometry={pathGeometry} frustumCulled={false}>
        <lineBasicMaterial color={NEUTRAL.light} transparent opacity={0.85} toneMapped={false} />
      </lineSegments>
      <instancedMesh ref={particles} args={[undefined, undefined, PARTICLES]} frustumCulled={false}>
        <sphereGeometry args={[0.045, 8, 8]} />
        <meshBasicMaterial color={new Color(NEUTRAL.light).multiplyScalar(3)} toneMapped={false} />
      </instancedMesh>

      {nodes.map((n) => (
        <GraphNodeMesh
          key={n.id}
          node={n}
          focused={focus?.kind === "node" && focus.id === n.id}
          reducedMotion={reducedMotion}
          registerGroup={(g) => {
            if (g) groups.current.set(n.id, g)
            else groups.current.delete(n.id)
          }}
          onPointerDown={(e) => drag.down(e, n.id)}
          onPointerMove={(e) => drag.move(e, n.id)}
          onPointerUp={(e) => drag.up(e, n.id)}
        />
      ))}
    </group>
  )
}

const easeOutCubic = (t: number) => 1 - (1 - t) ** 3

/** 노드 드래그. 카메라를 향한 평면 위에서 노드를 고정 위치로 끌고, 놓으면 풀어 준다. */
function useNodeDrag(
  simNodes: React.RefObject<Map<string, SimN>>,
  sim: ReturnType<typeof forceSimulation<SimN>>,
  setFocus: (f: { kind: "node"; id: string }) => void
) {
  const camera = useThree((s) => s.camera)
  const state = useRef<{ id: string; plane: Plane; moved: number; start: [number, number] } | null>(null)
  const hit = useMemo(() => new Vector3(), [])

  return {
    down(e: ThreeEvent<PointerEvent>, id: string) {
      e.stopPropagation()
      const sn = simNodes.current.get(id)
      if (!sn) return
      ;(e.target as unknown as Element).setPointerCapture(e.pointerId)
      const normal = camera.getWorldDirection(new Vector3()).negate()
      const plane = new Plane().setFromNormalAndCoplanarPoint(
        normal,
        new Vector3(sn.x, sn.y, sn.z)
      )
      state.current = { id, plane, moved: 0, start: [e.clientX, e.clientY] }
      sceneFlags.dragging = true
    },
    move(e: ThreeEvent<PointerEvent>, id: string) {
      const d = state.current
      if (!d || d.id !== id) return
      e.stopPropagation()
      d.moved = Math.hypot(e.clientX - d.start[0], e.clientY - d.start[1])
      if (!e.ray.intersectPlane(d.plane, hit)) return
      const sn = simNodes.current.get(id)
      if (!sn) return
      sn.fx = hit.x
      sn.fy = hit.y
      sn.fz = hit.z
      sim.alphaTarget(0.35)
      if (sim.alpha() < 0.35) sim.alpha(0.35)
    },
    up(e: ThreeEvent<PointerEvent>, id: string) {
      const d = state.current
      if (!d || d.id !== id) return
      e.stopPropagation()
      ;(e.target as unknown as Element).releasePointerCapture(e.pointerId)
      const sn = simNodes.current.get(id)
      if (sn) {
        sn.fx = null
        sn.fy = null
        sn.fz = null
      }
      sim.alphaTarget(0)
      sceneFlags.dragging = false
      if (d.moved < 4) setFocus({ kind: "node", id })
      state.current = null
    },
  }
}
