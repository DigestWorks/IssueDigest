/**
 * IssueDigest 스타일 가이드 규칙. /style 페이지가 이 데이터를 렌더링한다.
 * 기준은 3D 지도(stage/schematic/map)와 결과 패널(stage/schematic)에서 확정한 표현이다(2026-10-11 재정의).
 * 규칙을 바꾸거나 구현 상태가 바뀌면 이 파일을 함께 고친다.
 *
 * 상태: 구현 = 해당 규칙이 다루는 화면에 적용됨, 부분 = 일부 화면에만 적용됨, 미구현 = 아직 없음.
 * 제품 전체에 걸친 규칙은 지도·패널에만 적용되고 홈 스테이지(온톨로지 그래프, 채팅)에는 아직 적용되지 않았으므로 「부분」이다.
 */

export type RuleStatus = "구현" | "부분" | "미구현"

export type Rule = {
  title: string
  rule: string
  status: RuleStatus
  /** 구현 위치(app/ 기준) 또는 남은 작업 */
  where: string
}

export type Chapter = {
  id: string
  number: number
  title: string
  summary: string
  rules: Rule[]
}

/** 폐기한 규칙. 무엇으로 바뀌었는지와 이유를 남긴다 */
export type RetiredRule = {
  rule: string
  reason: string
  /** 대신 따르는 규칙(장 제목 · 규칙 제목). 없으면 생략 */
  replacedBy?: string
}

const HOME = "홈 스테이지 미적용"

export const IDENTITY = {
  name: "출처가 붙은 조사 기록",
  statement:
    "IssueDigest 의 화면은 에이전트가 한국 사회 데이터를 조사한 기록이다. 화면의 모든 표시는 온톨로지에서 찾은 노드·관계·값 하나에 대응하고 출처를 가진다. 무엇을 찾았는지와 함께 어떤 순서로 찾았는지가 화면에 남는다.",
  consequences: [
    "모든 표시에 출처가 있다. 표시를 선택하면 원문과 인용 위치, 시점을 확인할 수 있다.",
    "조사 순서가 화면에 남는다. 탐색 경로와 단계 번호로 어떤 기록에서 어떤 기록으로 이어졌는지 보여 준다.",
    "불확실성을 그대로 표시한다. 명시된 관계는 실선, 모델이 추론한 관계는 점선, 근거가 없으면 유보 상태로 그린다.",
    "깊이감, 명도, 움직임은 기록의 위계를 보여 주는 데에만 쓴다.",
  ],
}

export const CHAPTERS: Chapter[] = [
  {
    id: "pillars",
    number: 1,
    title: "핵심 원칙",
    summary: "모든 장이 따르는 기준",
    rules: [
      { title: "잘 보여주기", rule: "답은 글보다 시각 기록으로 전달한다. 채팅 답변은 요약과 출처만 짧게 쓰고 내용은 스테이지에서 보여 준다.", status: "구현", where: "stage/scenarios/*" },
      { title: "색 원칙", rule: "데이터 색은 답과 관련된 부분에만 쓰고, 나머지 데이터는 중립색으로 그린다. 주황은 선택·초점에만 쓴다. 바탕·선·글자는 글자색과 불투명도 단계로 만든다.", status: "부분", where: `지도(colored), 패널. ${HOME}` },
      { title: "측정 기록", rule: "표시에는 측정 정보를 함께 적는다. 지도는 경위도 눈금·축척·경계 자료 출처, 패널과 주석은 출처 줄, 화면 고정 주석은 카메라 방위·기울기·거리를 적는다.", status: "부분", where: `stage/schematic/map/*, stage/schematic/*. ${HOME}` },
      { title: "출처 있는 답", rule: "근거가 없는 질문에는 답을 유보하고, 유보 상태를 채팅과 스테이지에 함께 표시한다.", status: "구현", where: "stage/hud/stage-hud.tsx" },
      { title: "판독성 우선", rule: "효과가 글자와 수치를 가리면 효과를 줄인다. 주석과 화면 고정 주석(DOM)은 아웃포커스·색수차를 받지 않는다.", status: "부분", where: "지도의 3D 지역 이름은 아웃포커스에 함께 흐려짐" },
    ],
  },
  {
    id: "scene",
    number: 2,
    title: "장면",
    summary: "바탕, 바닥, 격자, 거리 감쇠",
    rules: [
      { title: "기본 모드", rule: "어두운 모드가 기본이다. 밝은 모드는 전환해서 쓴다. 두 모드의 바탕·글자·주황·격자 값은 SCHEMATIC_THEMES 한 곳에서 정한다.", status: "부분", where: `design/tokens.ts 의 SCHEMATIC_THEMES, /style·/map 전환. ${HOME}(흰 배경)` },
      { title: "바닥 조명", rule: "지도 중심 바닥을 원형으로 밝히고(반지름 9까지 중앙색, 30에서 바깥색) 바깥은 어둡게 둔다. 광원 물체 없이 바닥 밝기만 바꾼다. 회전하면 밝은 원의 원근이 바뀌어 공간감을 준다.", status: "구현", where: "design/tokens.ts 의 FLOOR, map-scene.tsx 의 SpotFloor" },
      { title: "격자", rule: "격자는 옅은 선이고 지도 중심에서 멀어질수록 옅어져 바닥 조명 범위 안에만 보인다.", status: "구현", where: "map-scene.tsx 의 Grid(fadeFrom=0)" },
      { title: "거리 감쇠", rule: "카메라에서 멀어질수록 바닥 조명 바깥색(backdrop)으로 흐려진다. 화면 위아래 가장자리는 같은 색으로 어둡게 해 화면 고정 주석을 읽게 한다.", status: "구현", where: "map-scene.tsx 의 fog, schematic-map.tsx 의 가장자리 그라디언트" },
    ],
  },
  {
    id: "lines",
    number: 3,
    title: "선과 주석",
    summary: "가는 선, 불투명도 단계, 측정 주석",
    rules: [
      { title: "불투명도 단계", rule: "선과 글자의 위계는 초점 100%, 관련 66%, 맥락 33%, 배경 11% 네 단계로 만든다.", status: "부분", where: `design/tokens.ts 의 OPACITY, 지도·패널. ${HOME}` },
      { title: "맨 위 선 강조", rule: "층 묶음은 맨 위 층 외곽선만 굵고 밝게(1.8px, 가리키거나 선택하면 2.4px, 중립 지역 1.2px) 그린다. 나머지 선은 1px 이다.", status: "구현", where: "map-scene.tsx 의 RegionVolume(drei Line)" },
      { title: "측정 주석", rule: "지도 범위는 모서리 꺾쇠로 두르고, 경도·위도 눈금(0.05° 간격, 0.1° 마다 수치), 5 km 축척 막대, 경계 자료 출처를 지면에 적는다.", status: "구현", where: "map-scene.tsx 의 MapFrame" },
      { title: "지시선과 주석", rule: "값은 꺾인 지시선 또는 수직 지시선 끝의 주석으로 붙인다. 주석은 왼쪽 세로선과 위쪽 연장선으로 틀을 만들고, 코드 | 단위, 이름, 값, 출처 순서로 쌓는다.", status: "구현", where: "region-callout.tsx, schematic-chart.tsx" },
      { title: "명시와 추론", rule: "원천 데이터에 명시된 관계는 실선, 모델이 추론한 관계는 점선으로 그린다.", status: "미구현", where: "GraphEdge 에 근거 종류(basis) 필드 추가 필요" },
    ],
  },
  {
    id: "color",
    number: 4,
    title: "색",
    summary: "데이터 색 범위, 중립색, 주황",
    rules: [
      { title: "데이터 색 범위", rule: "답과 관련된 지역·계열에만 데이터 색을 쓴다. 나머지 지역은 높이는 두고 중립색으로 그리며 면을 거의 채우지 않는다. 중립 지역도 선택하면 데이터 색으로 바뀐다.", status: "구현", where: "SchematicMap 의 colored 속성, map-scene.tsx 의 neutral" },
      { title: "데이터 팔레트", rule: "범주 색은 OKLCH 로 정한 여섯 색이다. 같은 범주는 지도·범례·차트·주장 비교에서 같은 색이다.", status: "구현", where: "design/palette.ts 의 DATA_CATEGORICAL, palette.test.ts" },
      { title: "주황", rule: "주황은 선택·초점·진행 중 상태와 머리선 시작점에만 쓴다. 데이터 계열에는 쓰지 않는다. 밝은 모드는 흰 바탕 대비를 위해 선·점 #E06C00(3.33:1), 글자 #B35900(4.83:1)을 쓴다.", status: "구현", where: "design/tokens.ts 의 SCHEMATIC_THEMES accent·accentText, primitives.tsx 의 ACCENT·ACCENT_TEXT" },
      { title: "중립색", rule: "데이터가 아닌 요소와 중립 지역은 글자색(ink)과 중립색(neutral #8b9598)에 불투명도 단계를 곱해 그린다.", status: "구현", where: "SCHEMATIC_THEMES ink·neutral" },
    ],
  },
  {
    id: "volume",
    number: 5,
    title: "부피",
    summary: "수평 층 묶음(홀로그램)",
    rules: [
      { title: "층 묶음", rule: "높이는 벽이 있는 덩어리 대신 0.18 간격으로 쌓은 수평 외곽선 층의 수로 나타낸다. 층 사이는 비어 있어 뒤가 보이고, 맨 위 층이 가장 밝으며 아래 층일수록 바탕색에 가깝다.", status: "구현", where: "design/tokens.ts 의 HOLOGRAM, map-scene.tsx 의 buildLayers" },
      { title: "선택 시 확장", rule: "선택한 지역은 층 수를 유지한 채 층 간격을 최대 1.5배로 벌려 위로 늘어난다. 늘어나는 높이는 최대 0.6 이다. 해제하면 원래 간격으로 돌아온다.", status: "구현", where: "HOLOGRAM.focusSpread·focusRiseMax" },
    ],
  },
  {
    id: "effects",
    number: 6,
    title: "효과",
    summary: "아웃포커스, 색 번짐, 색수차",
    rules: [
      { title: "아웃포커스", rule: "선택 지역(없으면 지도 중심)에 초점을 맞춘다. 초점 거리와의 차이가 0 에서 14 까지 커지는 동안 흐림이 커진다. 흐림 계산은 화면 해상도 그대로 한다.", status: "구현", where: "design/tokens.ts 의 MAP_EFFECTS, map-scene.tsx 의 MapEffects" },
      { title: "층 색 번짐", rule: "층 외곽선에 빨강(왼쪽)·청록(오른쪽) 사본을 화면 픽셀 1.2px 씩 어긋나게 겹친다. 화면 픽셀로 옮기므로 카메라 각도와 관계없이 같은 모양이다.", status: "구현", where: "HOLOGRAM.fringe, map-scene.tsx 의 fringeMaterialProps" },
      { title: "화면 색수차", rule: "화면 가장자리로 갈수록 빨강·파랑 성분이 어긋난다. 화면 중심에서 가장자리까지 거리의 20% 안쪽은 어긋나지 않고, 그 바깥은 거리에 비례해 커진다(postprocessing 6.39 ChromaticAberration 셰이더).", status: "구현", where: "MAP_EFFECTS.caOffset·caModulationOffset" },
      { title: "쓰는 효과의 범위", rule: "효과는 아웃포커스, 색 번짐, 색수차, 바닥 조명 네 가지만 쓴다. 발광(Bloom), 화면에 보이는 광원, 화면 깨짐(글리치)은 쓰지 않는다.", status: "구현", where: "map-scene.tsx, effects.tsx" },
    ],
  },
  {
    id: "type",
    number: 7,
    title: "글자",
    summary: "Pretendard 와 고정폭 보조 글자",
    rules: [
      { title: "글꼴", rule: "본문과 제목은 Pretendard, 번호·코드·좌표·보조 글자는 고정폭(Geist Mono)이다. 수치는 고정폭 숫자(tabular-nums)를 쓴다.", status: "구현", where: "app.css, primitives.tsx" },
      { title: "제목", rule: "제목은 가는 굵기(200)에 자간 0.06em 이고 아래에 1px 그림자 층을 둔다. 크기는 화면 제목 24~26px, 패널·주석 제목 19~21px 이다.", status: "구현", where: "SchematicFrame, schematic-map.tsx, region-callout.tsx" },
      { title: "머리 줄", rule: "제목 위에 「번호 | 보조 글자」 줄(10px, 자간 0.22em, 관련 단계, 번호는 고정폭)을 두고, 제목 아래에 주황 시작점이 있는 머리선을 둔다.", status: "구현", where: "primitives.tsx 의 SchematicFrame·Rule" },
      { title: "공간 속 글자", rule: "카메라가 높으면(극각 32° 이하) 지면에 눕히고, 낮으면(58° 이상) 세운다. 카메라 방위를 따라 돌아 바로 읽히는 방향을 유지한다.", status: "부분", where: "scene/view-angle.ts, 지도 이름·결과 패널. 사이 각도에서 연속 보간 중(35° 규칙 미충족)" },
    ],
  },
  {
    id: "hud",
    number: 8,
    title: "화면 고정 주석",
    summary: "네 모서리 배치와 조작 요소",
    rules: [
      { title: "배치", rule: "왼쪽 위에 제목, 오른쪽 위에 조작(보기 전환 등), 왼쪽 아래에 범례와 출처, 오른쪽 아래에 가리킨 대상·카메라 수치·조작 안내를 둔다.", status: "구현", where: "stage/schematic/map/schematic-map.tsx" },
      { title: "조작 버튼", rule: "버튼은 글자와 오른쪽 사각점으로 만든다. 선택된 항목은 주황 사각점과 꺾쇠 눈금으로 표시한다. 상자와 둥근 모서리를 쓰지 않는다.", status: "구현", where: "schematic-map.tsx 의 ControlButton, primitives.tsx 의 SquarePoint" },
      { title: "범례", rule: "범례는 「범례 · 색 범주 · 높이 격차」 머리 줄 아래에 사각 견본과 이름을 늘어놓는다.", status: "구현", where: "schematic-map.tsx" },
    ],
  },
  {
    id: "panels",
    number: 9,
    title: "패널",
    summary: "결과 패널(차트·타임라인·주장 비교)",
    rules: [
      { title: "틀", rule: "틀은 선과 점으로만 만든다. 위쪽 보조선은 틀 밖으로 연장되고, 왼쪽 세로선과 아래 짧은 가로선이 L자 꺾쇠를 이루며, 모서리에 사각점을 둔다. 바탕은 흐림 처리한 반투명 면이고 모서리는 직각이다. 왼쪽 위 모서리 점과 머리선 시작점은 주황이다.", status: "구현", where: "stage/schematic/primitives.tsx, stage/panels/panel-layer.tsx" },
      { title: "번호 잔상", rule: "패널 번호를 크고 아주 옅게(배경 단계) 오른쪽 위에 깔아 잔상 층을 만든다.", status: "구현", where: "SchematicFrame" },
      { title: "차트", rule: "축 상자 대신 기준선과 짧은 눈금, 배경 단계의 점선 격자를 쓴다. 계열은 데이터 색의 가는 선과 정사각형 점이고, 끝값은 꺾인 지시선과 수치로 주석한다.", status: "구현", where: "stage/schematic/schematic-chart.tsx" },
      { title: "타임라인", rule: "세로 축선 위의 사각점과 꺾인 지시선으로 날짜와 항목을 잇는다. 선택한 항목은 주황 사각점과 꺾쇠 눈금, 주황 날짜로 표시한다.", status: "구현", where: "stage/schematic/schematic-timeline.tsx" },
      { title: "주장 비교", rule: "입장 머리는 그 입장의 데이터 색으로 짧은 굵은 막대를 그린다. 주장마다 근거 사각점과 꺾인 지시선으로 인용 위치를 잇고, 선택한 주장은 주황 사각점과 꺾쇠 눈금으로 표시한다.", status: "구현", where: "stage/schematic/schematic-claims.tsx" },
    ],
  },
  {
    id: "map",
    number: 10,
    title: "지도",
    summary: "3D 인터랙티브 지도",
    rules: [
      { title: "선택 표시", rule: "선택한 지역은 주황 외곽선이 윗면과 바닥을 따라 한 바퀴 그려지고 한 번 바깥으로 커지며 사라진다. 윗면 중심에서 주황 수직 지시선이 올라가고 그 끝에 주석이 붙는다. 나머지 지역은 옅어진다.", status: "구현", where: "map-scene.tsx 의 FocusMarker, region-callout.tsx" },
      { title: "지역 이름", rule: "지역 이름은 맨 위 층에 놓이고 「공간 속 글자」 규칙으로 눕거나 선다. 선택한 지역은 주석이 이름을 대신한다.", status: "구현", where: "map-scene.tsx 의 RegionLabel" },
      { title: "방위 고리", rule: "지도 둘레에 5° 눈금, 30° 마다 각도, 동서남북 문자가 있는 고리를 둔다.", status: "구현", where: "map-scene.tsx 의 Compass" },
      { title: "보기", rule: "전체(비스듬히), 위에서, 낮게 세 보기를 버튼으로 전환한다. 지역을 선택하면 보는 방향을 유지한 채 그 지역으로 카메라가 옮겨진다.", status: "구현", where: "map-scene.tsx 의 VIEWS·MapCamera" },
    ],
  },
  {
    id: "motion",
    number: 11,
    title: "모션",
    summary: "등장 순서와 선택 표시",
    rules: [
      { title: "등장 순서", rule: "기록은 점 → 선 → 글자 순서로 나타난다. 선은 출발점에서 도착점으로 그려진다.", status: "부분", where: `design/tokens.ts 의 MOTION, 패널. ${HOME}(노드와 글자가 함께 등장)` },
      { title: "지도 등장", rule: "지도 홀로그램이 가운데에서 펼쳐진다. 지도 전체가 가로 배율 0.3 에서 1 로 커지고, 바닥의 고리가 퍼지며 고리가 닿는 지역부터(중심 거리 순) 바닥 외곽선이 그려진 뒤, 포개져 있던 층이 아래에서 위로 펼쳐진다. 지역 이름과 지도 틀이 마지막이다. 전체 약 1.3초다.", status: "구현", where: "design/tokens.ts 의 MAP_MOTION, map-scene.tsx" },
      { title: "한 번만 재생", rule: "등장과 선택 표시는 한 번만 재생한다. 계속 반복되는 움직임은 진행 중 상태 표시에만 쓴다.", status: "부분", where: `map-scene.tsx, stage-hud.tsx. ${HOME}(그래프 초점 고리의 크기가 계속 반복해서 바뀜)` },
      { title: "동작 줄이기", rule: "운영체제의 동작 줄이기 설정이 켜지면 모든 등장과 카메라 이동을 즉시 전환으로 바꾼다.", status: "구현", where: "design/use-reduced-motion.ts" },
    ],
  },
  {
    id: "interaction",
    number: 12,
    title: "조작",
    summary: "선택, 해제, 카메라",
    rules: [
      { title: "선택과 해제", rule: "대상을 클릭하면 선택한다. 배경을 클릭하거나 Esc 를 누르면 해제한다. 누른 곳과 뗀 곳이 4px 보다 멀면 끌기로 보고 선택을 바꾸지 않는다.", status: "부분", where: `map-scene.tsx(DRAG_PX), schematic-map.tsx. ${HOME}` },
      { title: "카메라", rule: "왼쪽 끌기로 회전, 오른쪽 끌기로 이동, 휠로 확대·축소한다. 화면 고정 주석에 방위·기울기·거리를 적는다.", status: "구현", where: "map-scene.tsx 의 MapCamera" },
      { title: "가리킴", rule: "가리킨 대상은 선과 면을 밝히고, 화면 고정 주석에 코드와 이름을 주황 글자로 적는다.", status: "구현", where: "map-scene.tsx(hovered), schematic-map.tsx" },
    ],
  },
]

/** 2026-10-11 지도 기반 재정의로 폐기한 규칙 */
export const RETIRED: RetiredRule[] = [
  { rule: "배경은 흰색이다", reason: "제품 기본 모드를 어두운 모드로 정했다. 흰 장면 값은 밝은 모드에 남는다.", replacedBy: "장면 · 기본 모드" },
  { rule: "색상은 데이터에만 쓴다. UI·배경·선택 표시는 무채색이다", reason: "데이터 색을 모든 데이터에 칠하면 색이 너무 많았고, 선택 표시에 주황을 쓰기로 했다.", replacedBy: "핵심 원칙 · 색 원칙" },
  { rule: "선택과 초점은 검정 선과 초점 단계 불투명도로 표시한다", reason: "선택·초점 표시는 주황을 쓴다.", replacedBy: "색 · 주황" },
  { rule: "지역은 불투명한 압출 면이고 지면에 그림자를 드리운다", reason: "높이를 수평 층 묶음으로 나타내는 홀로그램 표현으로 바꿨다.", replacedBy: "부피 · 층 묶음" },
  { rule: "차트는 흰색 계열에 강조할 계열 하나만 주황으로 그린다", reason: "주황을 선택·초점에만 쓰기로 해서 계열은 데이터 색으로 그린다.", replacedBy: "패널 · 차트" },
  { rule: "색수차와 글리치는 쓰지 않는다", reason: "지도의 홀로그램 표현으로 색수차를 허용했다. 글리치는 계속 쓰지 않는다.", replacedBy: "효과 · 화면 색수차" },
  { rule: "층을 아래에서 위로 반복해서 지나가는 주사선", reason: "화면이 산만하다는 피드백으로 삭제했다.", replacedBy: "모션 · 한 번만 재생" },
  { rule: "빛무리가 퍼지며 홀로그램으로 바뀌는 지도 등장", reason: "빛 표현 품질이 기대에 못 미쳐 되돌렸다.", replacedBy: "모션 · 지도 등장" },
  { rule: "그래프 노드는 무광·무채색 평면 기호이고 유형은 모양으로 구분한다", reason: "홈 스테이지 적용 때 새 색 원칙과 부피 규칙으로 다시 정한다. 현재 홈 스테이지는 이 규칙으로 그려져 있다." },
]

export function statusCounts() {
  const counts: Record<RuleStatus, number> = { 구현: 0, 부분: 0, 미구현: 0 }
  for (const c of CHAPTERS) for (const r of c.rules) counts[r.status]++
  return counts
}
