// d3-force-3d 3.0 은 타입 정의를 제공하지 않는다. 이 프로젝트가 쓰는 API 만 선언한다.
// 출처: https://github.com/vasturiano/d3-force-3d README
declare module "d3-force-3d" {
  export type SimNode = {
    id: string
    index?: number
    x?: number
    y?: number
    z?: number
    vx?: number
    vy?: number
    vz?: number
    fx?: number | null
    fy?: number | null
    fz?: number | null
  }

  export type SimLink<N extends SimNode> = {
    source: string | N
    target: string | N
  }

  export interface Force<N extends SimNode> {
    (alpha: number): void
    initialize?: (nodes: N[], ...args: unknown[]) => void
  }

  export interface Simulation<N extends SimNode> {
    nodes(): N[]
    nodes(nodes: N[]): this
    force(name: string): Force<N> | undefined
    force(name: string, force: Force<N> | null): this
    alpha(): number
    alpha(alpha: number): this
    alphaMin(): number
    alphaMin(min: number): this
    alphaDecay(decay: number): this
    alphaTarget(): number
    alphaTarget(target: number): this
    velocityDecay(decay: number): this
    tick(iterations?: number): this
    stop(): this
    restart(): this
  }

  export interface LinkForce<N extends SimNode, L extends SimLink<N>> extends Force<N> {
    links(): L[]
    links(links: L[]): this
    id(fn: (node: N) => string): this
    distance(d: number | ((link: L) => number)): this
    strength(s: number | ((link: L) => number)): this
  }

  export interface ManyBodyForce<N extends SimNode> extends Force<N> {
    strength(s: number | ((node: N) => number)): this
    distanceMax(d: number): this
  }

  export interface CenterForce<N extends SimNode> extends Force<N> {
    strength(s: number): this
  }

  export function forceSimulation<N extends SimNode>(nodes?: N[], numDimensions?: 1 | 2 | 3): Simulation<N>
  export function forceLink<N extends SimNode, L extends SimLink<N>>(links?: L[]): LinkForce<N, L>
  export function forceManyBody<N extends SimNode>(): ManyBodyForce<N>
  export function forceCenter<N extends SimNode>(x?: number, y?: number, z?: number): CenterForce<N>
  export function forceCollide<N extends SimNode>(radius?: number | ((node: N) => number)): Force<N>

  export interface PositionForce<N extends SimNode> extends Force<N> {
    strength(s: number | ((node: N) => number)): this
  }
  export function forceY<N extends SimNode>(y?: number): PositionForce<N>
}
