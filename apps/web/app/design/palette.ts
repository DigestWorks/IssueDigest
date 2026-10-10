/**
 * 데이터 팔레트의 기준 값.
 *
 * 디자인 원칙은 「색상은 데이터에만 쓴다」이다. 이 파일의 색은 지역별 값,
 * 차트 계열, 그래프 노드 유형처럼 데이터를 나타내는 곳에서만 참조한다.
 * app.css 의 --data-cat-* 는 같은 값을 갖고, palette.test.ts 가 대조한다.
 *
 * three.js 는 OKLCH 문자열을 읽지 못하므로 sRGB hex 로 바꿔 넘긴다.
 * 변환식 출처: Björn Ottosson, "A perceptual color space for image processing"
 * (https://bottosson.github.io/posts/oklab/).
 */

export type Oklch = readonly [l: number, c: number, h: number]

export const DATA_CATEGORICAL: readonly Oklch[] = [
  [0.72, 0.17, 25],
  [0.72, 0.14, 245],
  [0.76, 0.15, 150],
  [0.8, 0.14, 85],
  [0.7, 0.16, 320],
  [0.78, 0.11, 200],
]

export function oklchToHex([l, c, h]: Oklch): string {
  const hr = (h * Math.PI) / 180
  const a = c * Math.cos(hr)
  const b = c * Math.sin(hr)
  const l_ = (l + 0.3963377774 * a + 0.2158037573 * b) ** 3
  const m_ = (l - 0.1055613458 * a - 0.0638541728 * b) ** 3
  const s_ = (l - 0.0894841775 * a - 1.291485548 * b) ** 3
  const linear = [
    4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
    -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
    -0.0041960863 * l_ - 0.7034186147 * m_ + 1.707614701 * s_,
  ]
  return (
    "#" +
    linear
      .map((v) => {
        const x = Math.min(1, Math.max(0, v))
        const srgb = x <= 0.0031308 ? 12.92 * x : 1.055 * x ** (1 / 2.4) - 0.055
        return Math.round(srgb * 255)
          .toString(16)
          .padStart(2, "0")
      })
      .join("")
  )
}

export const dataColor = (index: number) =>
  oklchToHex(DATA_CATEGORICAL[index % DATA_CATEGORICAL.length])

/** 그래프 노드 유형별 데이터 색. 유형은 데이터이므로 색을 쓴다. */
export const NODE_TYPE_COLOR_INDEX = {
  issue: 3,
  bill: 1,
  member: 0,
  party: 4,
  committee: 5,
  meeting: 5,
  statistic: 2,
  document: 3,
  claim: 0,
  region: 2,
} as const

export type NodeType = keyof typeof NODE_TYPE_COLOR_INDEX

export const nodeColor = (type: NodeType) => dataColor(NODE_TYPE_COLOR_INDEX[type])

/**
 * 3D 장면의 무채색 값. 데이터가 아닌 요소(지면, 경계선, 광원, 파티클)는
 * 이 값만 쓴다. 모두 채도 0 이다.
 */
export const NEUTRAL = {
  void: "#050505",
  ground: "#0b0b0b",
  grid: "#2a2a2a",
  line: "#d9d9d9",
  lineDim: "#5a5a5a",
  light: "#ffffff",
  particle: "#e6e6e6",
} as const
