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

/** 글자 역할. 글꼴은 Pretendard 한 가족이고 숫자는 고정폭 숫자(tabular-nums)를 쓴다. */
export const TYPE_ROLES = [
  { id: "display", label: "스테이지 제목", size: 28, weight: 300, tracking: "0.04em", sample: "서울시장 선거 자치구별 우세" },
  { id: "title", label: "패널 제목", size: 15, weight: 600, tracking: "0", sample: "후보별 지지율 추이" },
  { id: "body", label: "본문", size: 14, weight: 400, tracking: "0", sample: "샘플 법안 A는 소위원회 두 차례를 거쳤습니다." },
  { id: "label", label: "공간 속 라벨", size: 13, weight: 500, tracking: "0.02em", sample: "제1차 법안심사소위" },
  { id: "caption", label: "보조 글자", size: 11, weight: 400, tracking: "0.12em", sample: "출처 · 회의록 · 발언 27" },
  { id: "numeric", label: "수치", size: 20, weight: 600, tracking: "0", sample: "38.4%  ·  5,600명", numeric: true },
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
