import type React from "react"

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
 * 도면 양식 패널 테마(The Division UI 스타일 가이드의 색 체계를 따른다).
 * - 주색: 강조용 주황(RGB 255,127,0)과 기본 상태용 따뜻한 흰색.
 * - 주황은 초점·선택·강조 계열에만 아껴 쓴다. 나머지는 흰색과 불투명도 단계로 위계를 만든다.
 * - 바탕은 어두운 반투명 면이다.
 * 출처: The Division User Interface Style Guide 6.1 Primary Colors (VGLeaks 게시 이미지, 2014).
 */
export const SCHEMATIC_THEME = {
  ink: "#F4FFFF",
  accent: "#FF7F00",
  backing: "rgb(10 12 14 / 0.62)",
  shadow: "rgb(0 0 0 / 0.33)",
  scene: "#0c0f12",
} as const

export const schematicVars = {
  "--sch-ink": SCHEMATIC_THEME.ink,
  "--sch-accent": SCHEMATIC_THEME.accent,
  "--sch-backing": SCHEMATIC_THEME.backing,
  "--sch-shadow": SCHEMATIC_THEME.shadow,
  "--sch-scene": SCHEMATIC_THEME.scene,
} as React.CSSProperties
