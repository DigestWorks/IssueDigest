import type React from "react"

import { NEUTRAL } from "./palette"

/**
 * IssueDigest 디자인 토큰 중 색 외의 값: 불투명도 단계, 글자 역할, 모션.
 * 색은 palette.ts 와 app.css 에 있다. 장면(three.js)과 화면(DOM), /style 페이지가
 * 이 값을 함께 읽는다.
 */

/**
 * 불투명도 단계. 위계는 검정과 이 네 단계만으로 만든다.
 * 데이터 색은 위계가 정해진 뒤 데이터 값에만 더한다.
 */
export const OPACITY = {
  focus: { value: 1, label: "초점", use: "지금 답의 중심인 노드·지역·글자" },
  related: { value: 0.66, label: "관련", use: "초점과 직접 연결된 기록, 탐색 경로" },
  context: { value: 0.33, label: "맥락", use: "화면에 남아 있는 나머지 기록" },
  faint: { value: 0.11, label: "배경", use: "격자, 가려진 선, 지난 탐색의 흔적 선" },
} as const

export type OpacityStep = keyof typeof OPACITY

/**
 * 글자 역할. 본문·제목은 Pretendard, 번호·코드·좌표·보조 글자는 고정폭(mono)이다. 수치는 고정폭 숫자(tabular-nums)를 쓴다.
 * 값은 지도·패널·화면 고정 주석에서 쓰는 크기와 굵기다.
 */
export const TYPE_ROLES = [
  { id: "display", label: "화면 제목", size: 26, weight: 200, tracking: "0.06em", sample: "서울시장 선거 자치구별 우세" },
  { id: "title", label: "패널·주석 제목", size: 20, weight: 200, tracking: "0.06em", sample: "후보별 지지율 추이" },
  { id: "body", label: "본문·규칙", size: 13, weight: 400, tracking: "0.01em", sample: "샘플 법안 A는 소위원회 두 차례를 거쳤습니다." },
  { id: "label", label: "항목·버튼", size: 12, weight: 400, tracking: "0.12em", sample: "제1차 소위 심사 · 위에서" },
  { id: "numeric", label: "수치", size: 14, weight: 300, tracking: "0", sample: "38.4% · 5,600명", numeric: true },
  { id: "caption", label: "머리 줄·보조 글자", size: 10, weight: 400, tracking: "0.22em", sample: "03 | 차트 · 단위 명", mono: true },
] as const

/** 공간 속 글자가 카메라 시선에 대해 기울 수 있는 최대 각도(도) */
export const MAX_TEXT_TILT_DEG = 35

/**
 * 모션. 기록은 점 → 선 → 글자 순서로 나타난다.
 * 시간 단위는 ms, 곡선은 cubic-bezier 값이다.
 */
export const MOTION = {
  point: { duration: 240, label: "점 등장" },
  line: { duration: 480, label: "선이 출발점에서 도착점으로 그려짐" },
  text: { duration: 200, label: "글자 등장" },
  stagger: { duration: 60, label: "같은 단계 기록 사이 간격" },
  panel: { duration: 900, label: "결과 패널 등장" },
  camera: { duration: 600, label: "카메라 초점 이동(감쇠 시간)" },
} as const

export const EASE_OUT = [0.16, 1, 0.3, 1] as const

/**
 * 도면 양식(The Division UI 스타일 가이드) 테마. 어두운 모드가 기본이고 밝은 모드는 시험 중이다.
 * - 주색: 강조용 주황과 기본 상태 글자색. 주황은 초점·선택·강조 계열에만 아껴 쓴다.
 * - 나머지 위계는 글자색과 불투명도 단계로 만든다.
 * - accent 는 선·점·면에, accentText 는 주황 글자에 쓴다.
 * 어두운 모드 색 출처: The Division User Interface Style Guide 6.1 Primary Colors (VGLeaks 게시 이미지, 2014).
 * 밝은 모드 바탕·격자·글자색은 palette.ts 의 흰 장면 값(NEUTRAL)을 그대로 쓴다.
 * 밝은 모드 주황은 흰 바탕 대비(WCAG 2.x 상대 휘도 공식)로 정했다:
 *   #FF7F00 2.53:1(비텍스트 기준 3:1 미달) → 선·점 #E06C00 3.33:1, 글자 #B35900 4.83:1(본문 기준 4.5:1 충족).
 */
export type SchematicMode = "dark" | "light"

export type SchematicPalette = {
  ink: string
  accent: string
  accentText: string
  backing: string
  shadow: string
  scene: string
  grid: string
  gridSection: string
  /** 색으로 표시하지 않는 지도 지역의 중립색 */
  neutral: string
  /** 견본 바탕의 방사형 그라디언트 중심색 */
  glow: string
  /** 지도 바닥 조명 범위 밖의 색. 바닥 중앙은 scene, 바깥으로 갈수록 이 색이 된다 */
  backdrop: string
}

export const SCHEMATIC_THEMES: Record<SchematicMode, SchematicPalette> = {
  dark: {
    ink: "#F4FFFF",
    accent: "#FF7F00",
    accentText: "#FF7F00",
    backing: "rgb(10 12 14 / 0.62)",
    shadow: "rgb(0 0 0 / 0.33)",
    scene: "#0c0f12",
    grid: "#141a1e",
    gridSection: "#1e262b",
    neutral: "#8b9598",
    glow: "#1b2127",
    backdrop: "#050607",
  },
  light: {
    ink: NEUTRAL.ink,
    accent: "#E06C00",
    accentText: "#B35900",
    backing: "rgb(255 255 255 / 0.72)",
    shadow: "rgb(255 255 255 / 0.6)",
    scene: NEUTRAL.background,
    grid: NEUTRAL.grid,
    gridSection: NEUTRAL.gridSection,
    neutral: "#8b9598",
    glow: "#f3f4f4",
    backdrop: "#d9dcdb",
  },
}

/** 어두운 모드 값. 모드를 받지 않는 기존 호출부가 쓴다 */
export const SCHEMATIC_THEME = SCHEMATIC_THEMES.dark

export const schematicVars = (mode: SchematicMode = "dark") => {
  const t = SCHEMATIC_THEMES[mode]
  return {
    "--sch-ink": t.ink,
    "--sch-accent": t.accent,
    "--sch-accent-text": t.accentText,
    "--sch-backing": t.backing,
    "--sch-shadow": t.shadow,
    "--sch-scene": t.scene,
    "--sch-backdrop": t.backdrop,
  } as React.CSSProperties
}

/**
 * 홀로그램 부피(지도 지역의 층 묶음). 길이는 장면 단위, px 는 화면 픽셀이다.
 * - 높이는 벽이 있는 덩어리 대신 layerGap 간격으로 쌓은 수평 외곽선 층의 수로 나타낸다(최대 maxHeight).
 * - 선택하면 층 수는 그대로 두고 층 간격을 최대 focusSpread 배로 벌린다. 늘어나는 높이는 focusRiseMax 까지다.
 * - 층 외곽선에 빨강(왼쪽)·청록(오른쪽) 사본을 fringe.px 씩 어긋나게 겹친다.
 */
export const HOLOGRAM = {
  layerGap: 0.18,
  maxHeight: 1.8,
  focusSpread: 1.5,
  focusRiseMax: 0.6,
  fringe: { px: 1.2, colored: 0.5, neutral: 0.2 },
} as const

/**
 * 지도 후처리. @react-three/postprocessing 3.x 의 DepthOfField·ChromaticAberration 속성 값이다.
 * - focusRange: 초점 거리와의 차이가 0 에서 이 값(장면 단위)까지 커지는 동안 흐림이 smoothstep 으로 커진다.
 * - caOffset: 화면 가장자리 색수차 크기(화면 좌표 비율), caModulationOffset: 색수차가 없는 가운데 영역.
 */
export const MAP_EFFECTS = {
  focusRange: 14,
  bokehScale: 1.6,
  caOffset: [0.0014, 0.0009],
  caModulationOffset: 0.2,
} as const

/** 지도 바닥 조명: 지름 size 바닥에서 반지름 inner 까지 중앙색, outer 에서 바깥색(backdrop)이 된다 */
export const FLOOR = { size: 90, inner: 9, outer: 30 } as const

/**
 * 지도 등장 시각(ms, 경계 데이터를 받은 시점 기준). 지도 홀로그램이 가운데에서 펼쳐진다.
 * - expand: 지도 전체가 가로 배율 expandFrom 에서 1 로 커진다.
 * - wave: 바닥의 고리가 가운데에서 바깥으로 퍼지고, 고리가 닿는 지역부터 나타난다(중심 거리에 비례).
 * - region: 지역마다 바닥 외곽선이 그려진 뒤, 바닥에 포개져 있던 층 사이가 벌어지며 위로 펼쳐진다.
 * - label·frame: 지역 이름과 지도 틀은 마지막에 나타난다.
 * - focus*: 선택 표시(외곽선 추적, 바깥으로 커지며 사라지는 외곽선, 수직 지시선).
 */
export const MAP_MOTION = {
  expandFrom: 0.3,
  expand: { ms: 1000 },
  wave: { at: 60, ms: 850 },
  region: { outlineMs: 300, unfoldAt: 120, unfoldMs: 600 },
  label: { at: 600, ms: 250 },
  frame: { at: 850, ms: 450 },
  compass: { at: 0, ms: 1000 },
  focusTrace: 700,
  focusPulse: { at: 500, ms: 1000 },
  focusLeader: { at: 400, ms: 400 },
} as const
