import {
  AdditiveBlending,
  BufferGeometry,
  Color,
  Float32BufferAttribute,
  NormalBlending,
  Vector2,
  type Vector3,
} from "three"

/** 누른 곳과 뗀 곳이 이 거리(px)보다 멀면 클릭이 아니라 끌기로 본다 */
export const DRAG_PX = 4

/** troika Text 메시 중 매 프레임 바꾸는 속성. 색·불투명도 변경은 sync() 없이 다음 렌더에 반영된다. */
export type TextLike = { fillOpacity: number }

export function lineGeometry(pts: number[]) {
  const g = new BufferGeometry()
  g.setAttribute("position", new Float32BufferAttribute(pts, 3))
  return g
}

/** 닫힌 고리 목록을 선분 묶음으로. origin 을 주면 그 점 기준 좌표로 만든다 */
export function outlineGeometry(rings: Vector3[][], origin?: Vector3) {
  const pts: number[] = []
  const ox = origin?.x ?? 0
  const oz = origin?.z ?? 0
  for (const ring of rings)
    for (let i = 0; i < ring.length - 1; i++)
      pts.push(ring[i].x - ox, 0, ring[i].z - oz, ring[i + 1].x - ox, 0, ring[i + 1].z - oz)
  return lineGeometry(pts)
}

/** 선분 묶음을 앞에서부터 t 비율만큼 그린다(선이 출발점에서 도착점으로 그려지는 등장) */
export function setDrawProgress(g: BufferGeometry, t: number) {
  const n = g.getAttribute("position").count
  g.setDrawRange(0, Math.floor((n * t) / 2) * 2)
}

export function progress(now: number, start: number, ms: number, reduced: boolean) {
  if (reduced) return 1
  return Math.min(1, Math.max(0, (now - start) / ms))
}

export const easeOutCubic = (t: number) => 1 - (1 - t) ** 3

/**
 * 색 번짐 사본용 선 재질. 꼭짓점을 화면 가로 방향으로 uShift(화면 픽셀)만큼 옮긴다.
 * 장면 좌표가 아니라 화면 픽셀로 옮기므로 카메라 각도·거리와 관계없이 빨강은 왼쪽, 청록은 오른쪽에 같은 폭으로 생긴다.
 * 세로로 놓인 선에는 양옆에 색이 갈라지고, 가로로 놓인 선은 사본이 겹쳐 색이 거의 생기지 않는다(실제 색수차와 같은 모양).
 */
export function fringeMaterialProps(color: string, shift: number, blending: typeof AdditiveBlending | typeof NormalBlending) {
  return {
    uniforms: {
      uColor: { value: new Color(color) },
      uOpacity: { value: 0 },
      uShift: { value: shift },
      uRes: { value: new Vector2(1, 1) },
    },
    transparent: true,
    depthWrite: false,
    blending,
    vertexShader: `
      uniform float uShift;
      uniform vec2 uRes;
      void main() {
        vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        p.x += uShift * 2.0 / uRes.x * p.w;
        gl_Position = p;
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uOpacity;
      void main() {
        gl_FragColor = vec4(uColor, uOpacity);
        #include <colorspace_fragment>
      }
    `,
  }
}
