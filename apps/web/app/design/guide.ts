/**
 * IssueDigest 스타일 가이드 규칙. /style 페이지가 이 데이터를 렌더링한다.
 * 규칙을 바꾸거나 구현 상태가 바뀌면 이 파일을 함께 고친다.
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
    summary: "제품이 지키는 네 가지 기준",
    rules: [
      { title: "잘 보여주기", rule: "답은 글보다 시각 기록으로 전달한다. 채팅 답변은 요약과 출처만 짧게 쓰고 내용은 스테이지에서 보여 준다.", status: "구현", where: "stage/scenarios/*" },
      { title: "출처 있는 답", rule: "근거가 없는 질문에는 답을 유보하고, 유보 상태를 채팅과 스테이지에 함께 표시한다.", status: "구현", where: "stage/hud/stage-hud.tsx" },
      { title: "판독성 우선", rule: "효과가 글자와 수치를 가리면 효과를 줄인다. 글자가 있는 요소는 항상 선명하게 둔다.", status: "부분", where: "피사계 심도가 장면 속 라벨까지 흐림. 라벨 제외 처리 필요" },
      { title: "색은 데이터에만", rule: "배경·패널·선·선택 표시는 무채색이다. 색은 지역별 값, 차트 계열, 입장처럼 데이터 값에만 쓴다.", status: "구현", where: "design/palette.ts, design/palette.test.ts" },
    ],
  },
  {
    id: "layers",
    number: 2,
    title: "UI 구분",
    summary: "화면 고정 UI, 공간 속 UI, 데이터 객체",
    rules: [
      { title: "화면 고정 UI", rule: "채팅, 상태, 범례만 화면에 고정한다. 그 밖의 정보는 공간 속에 둔다.", status: "구현", where: "chat/chat-panel.tsx, stage/hud/stage-hud.tsx" },
      { title: "공간 속 UI", rule: "결과 패널은 3D 공간에 놓인다. 카메라가 수직에 가까우면 지면에 눕고, 낮으면 지면 위에 선다.", status: "구현", where: "stage/panels/panel-layer.tsx" },
      { title: "데이터 객체가 곧 UI", rule: "지도와 그래프는 배경 그림이 아니라 조작할 수 있는 기록이다. 선택하면 출처와 관련 기록으로 이어진다.", status: "부분", where: "지역·노드 선택 시 초점 이동은 구현. 선택한 기록의 출처 표시는 미구현" },
    ],
  },
  {
    id: "system",
    number: 3,
    title: "시스템 정의",
    summary: "출처가 붙은 조사 기록",
    rules: [
      { title: "기록 단위", rule: "화면의 표시 하나는 온톨로지의 노드·관계·값 하나에 대응하고 출처를 하나 이상 가진다.", status: "부분", where: "노드·패널·지도 값은 출처 필수(stage/events.ts). 엣지는 출처 필드 없음" },
      { title: "조사 순서", rule: "탐색 경로를 선으로 남기고, 경로 위 기록에 단계 번호를 붙인다.", status: "부분", where: "탐색 경로 선과 파티클은 구현. 단계 번호 미구현" },
      { title: "명시와 추론", rule: "원천 데이터에 명시된 관계는 실선, 모델이 추론한 관계는 점선으로 그린다.", status: "미구현", where: "GraphEdge 에 근거 종류(basis) 필드 추가 필요" },
      { title: "시점", rule: "모든 기록은 시점을 가진다. 질문 시점보다 오래된 기록은 맥락 단계로 옅게 그리고 날짜를 붙인다.", status: "미구현", where: "Source.retrievedAt 은 있음. 화면 처리 미구현" },
    ],
  },
  {
    id: "style",
    number: 4,
    title: "스타일 정의",
    summary: "프로그램이 생성하는 기술 도면",
    rules: [
      { title: "프로그램 생성", rule: "화면은 에이전트가 질문마다 생성한다. 단순한 도형, 점, 선, 압출 형상만으로 구성해 어떤 데이터에도 같은 양식이 적용되게 한다.", status: "구현", where: "stage/graph, stage/map" },
      { title: "도면 양식 주석", rule: "수치와 관계는 형태를 채우기보다 가는 지시선, 짧은 눈금, 작은 수치 글자로 주석한다.", status: "미구현", where: "지역·노드 주석 컴포넌트 필요" },
      { title: "광원과 발광", rule: "깊이는 명도, 그림자, 거리 흐림만으로 만든다. 조명은 형상을 비추는 데에만 쓰고 광원 자체는 화면에 그리지 않는다.", status: "구현", where: "stage/scene/environment.tsx, effects.tsx" },
    ],
  },
  {
    id: "ingredients",
    number: 5,
    title: "시각 재료",
    summary: "점, 선, 면",
    rules: [
      { title: "점(노드)", rule: "노드는 무광 평면 기호다. 유형은 모양(원·사각형·삼각형·마름모)과 채움으로 구분하고 모두 무채색이다.", status: "구현", where: "stage/graph/glyphs.ts, graph-node.tsx" },
      { title: "선(관계)", rule: "관계는 가는 선이다. 탐색 경로는 관련 단계, 그 밖의 관계는 맥락 단계 불투명도로 그린다.", status: "부분", where: "불투명도 토큰 대신 고정 회색 사용 중" },
      { title: "가려진 선", rule: "형상 뒤로 지나가는 선은 배경 단계 불투명도로 이어서 그린다.", status: "미구현", where: "가림 구간 렌더링 필요" },
      { title: "면(지역)", rule: "지역은 압출된 면이다. 색은 범주, 높이는 크기를 나타낸다. 재질은 불투명이다.", status: "구현", where: "stage/map/map-layer.tsx" },
    ],
  },
  {
    id: "color",
    number: 6,
    title: "색과 불투명도",
    summary: "무채색 위계 위에 데이터 색",
    rules: [
      { title: "작업 순서", rule: "먼저 검정과 불투명도 네 단계만으로 위계를 만들고, 마지막에 데이터 값에만 색을 더한다.", status: "부분", where: "design/tokens.ts 의 OPACITY. 장면 적용은 일부" },
      { title: "선택 표시", rule: "선택과 초점은 데이터가 아니므로 검정 선과 초점 단계 불투명도로 표시한다.", status: "구현", where: "graph-node.tsx, map-layer.tsx" },
    ],
  },
  {
    id: "type",
    number: 7,
    title: "글자와 판독성",
    summary: "Pretendard, 역할별 굵기, 35° 규칙",
    rules: [
      { title: "역할별 굵기", rule: "가는 굵기는 큰 제목, 중간 굵기는 공간 속 라벨, 굵은 굵기는 강조 수치에만 쓴다. 수치는 고정폭 숫자를 쓴다.", status: "부분", where: "design/tokens.ts 의 TYPE_ROLES. 화면 전체 적용은 미완료" },
      { title: "35° 규칙", rule: "공간 속 글자는 카메라 시선에 대해 35° 안쪽으로만 기운다. 결과 패널은 눕힘·세움 사이를 짧게 전환하고 중간 상태에 머무르지 않는다.", status: "미구현", where: "panel-layer.tsx 가 연속 보간 중" },
      { title: "배경 층", rule: "색이 있는 면 위의 글자에는 바로 뒤에 반투명 흰 층을 깐다.", status: "미구현", where: "지도 라벨" },
    ],
  },
  {
    id: "depth",
    number: 8,
    title: "깊이와 효과",
    summary: "그림자, 거리 흐림, 초점",
    rules: [
      { title: "그림자와 거리 흐림", rule: "형상은 흰 지면에 부드러운 그림자를 드리우고, 멀어질수록 배경색으로 흐려진다.", status: "구현", where: "stage/scene/environment.tsx" },
      { title: "피사계 심도", rule: "초점에서 먼 형상만 흐린다. 글자와 수치는 항상 선명하게 둔다.", status: "부분", where: "형상과 라벨이 함께 흐려짐" },
      { title: "모서리 선 강조", rule: "선택한 형상은 모서리를 따라 선이 그려지는 방식으로 강조한다.", status: "미구현", where: "현재는 고리 표시" },
    ],
  },
  {
    id: "motion",
    number: 9,
    title: "모션",
    summary: "점 → 선 → 글자",
    rules: [
      { title: "순서대로 등장", rule: "기록은 점이 찍히고, 선이 출발점에서 도착점으로 그려지고, 글자가 나타나는 순서로 등장한다.", status: "부분", where: "선 그리기는 구현. 노드와 글자는 함께 등장" },
      { title: "동작 줄이기", rule: "운영체제의 동작 줄이기 설정이 켜지면 모든 등장과 카메라 이동을 즉시 전환으로 바꾼다.", status: "구현", where: "design/use-reduced-motion.ts" },
    ],
  },
  {
    id: "camera",
    number: 10,
    title: "카메라",
    summary: "답의 초점이 화면 구성의 기준",
    rules: [
      { title: "초점 기준 구성", rule: "카메라는 답의 초점 기록을 기준으로 이동하고, 주변 맥락이 화면에 남도록 거리를 둔다.", status: "구현", where: "stage/scene/camera-rig.tsx" },
      { title: "사용자 조작", rule: "사용자는 언제든 회전, 기울이기, 이동, 확대·축소를 할 수 있고, 공간 속 패널은 카메라를 따라 읽히는 방향을 유지한다.", status: "구현", where: "camera-rig.tsx, panel-layer.tsx" },
    ],
  },
  {
    id: "panels",
    number: 11,
    title: "패널",
    summary: "The Division 양식 결과 패널",
    rules: [
      { title: "틀", rule: "틀은 선과 점으로만 만든다. 위쪽 보조선은 틀 밖으로 연장되고, 왼쪽 세로선과 아래 짧은 가로선이 L자 꺾쇠를 이루며, 모서리에 사각점을 둔다. 바탕은 흐림 처리한 어두운 반투명 면이고 모서리는 직각이다. 왼쪽 위 모서리 점과 머리선 시작점은 주황이다.", status: "구현", where: "stage/schematic/primitives.tsx, stage/panels/panel-layer.tsx" },
      { title: "머리", rule: "작은 고정폭 번호와 보조 글자, 가는 굵기의 제목, 시작점이 있는 머리선 순서로 쌓는다. 같은 번호를 크고 아주 옅게(배경 단계) 깔아 잔상 층을 만든다.", status: "구현", where: "SchematicFrame" },
      { title: "차트", rule: "축 상자 대신 기준선과 짧은 눈금, 배경 단계의 점선 격자를 쓴다. 계열은 가는 선과 정사각형 점이고, 끝값은 꺾인 지시선과 수치로 주석한다. 계열은 흰색과 불투명도로 그리고 강조할 계열 하나만 주황으로 그린다.", status: "구현", where: "stage/schematic/schematic-chart.tsx" },
      { title: "타임라인", rule: "세로 축선 위의 사각점과 꺾인 지시선으로 날짜와 항목을 잇는다. 선택한 항목은 채운 사각점과 꺾쇠 눈금으로 표시한다.", status: "구현", where: "stage/schematic/schematic-timeline.tsx" },
      { title: "주장 비교", rule: "입장 머리는 짧은 굵은 막대로 표시한다(첫 입장 주황, 둘째 입장 흰색). 주장마다 근거 사각점과 꺾인 지시선으로 인용 위치를 잇고, 선택한 주장은 주황 사각점과 꺾쇠 눈금으로 표시한다.", status: "구현", where: "stage/schematic/schematic-claims.tsx" },
      { title: "등장", rule: "틀의 선 → 점 → 지시선 → 글자 순서로 그려진다. 시간은 MOTION 토큰을 따른다.", status: "구현", where: "stage/schematic/*" },
    ],
  },
  {
    id: "map",
    number: 12,
    title: "지도",
    summary: "The Division 양식 3D 인터랙티브 지도 (시험 중)",
    rules: [
      { title: "지역 층", rule: "지역 높이는 벽이 있는 덩어리 대신 일정 간격으로 쌓은 수평 외곽선 층의 수로 나타낸다(홀로그램 표현). 층 사이는 비어 있어 뒤가 보이고, 맨 위 층이 가장 밝으며 아래 층일수록 배경색에 가깝다. 층 색은 범주를 나타낸다. 색은 답과 관련된 일부 지역(colored)에만 쓰고, 나머지 지역은 높이만 두고 면을 거의 채우지 않은 중립색으로 그린다. 중립 지역도 선택하면 데이터 색으로 바뀐다. 판독성을 위해 맨 위 층 외곽선만 굵고 밝은 선(1.8px, 가리키거나 선택하면 2.4px)으로 강조한다.", status: "부분", where: "stage/schematic/map/map-scene.tsx 의 RegionVolume·buildLayers, 스테이지 적용 전" },
      { title: "경계와 틀", rule: "바닥 경계선은 흰색 맥락 단계로 그린다. 지도 범위는 모서리 꺾쇠로 두르고, 경도·위도 눈금, 축척 막대, 경계 자료 출처를 지면에 적는다.", status: "부분", where: "map-scene.tsx 의 MapFrame" },
      { title: "선택 표시", rule: "선택한 지역은 층 수를 유지한 채 층 간격이 최대 1.5배로 벌어져 묶음이 위로 늘어나고(늘어나는 높이는 최대 0.6, 해제하면 원래 간격으로 돌아감), 주황 외곽선이 윗면과 바닥을 따라 한 바퀴 그려지고 한 번 바깥으로 커지며 사라진다. 윗면 중심에서 주황 수직 지시선이 올라가고 그 끝에 코드·이름·값·출처 주석이 붙는다. 나머지 지역은 옅어진다.", status: "부분", where: "map-scene.tsx 의 FocusMarker, region-callout.tsx" },
      { title: "지역 이름", rule: "카메라가 높으면 윗면에 눕고, 낮으면 윗면 위에 선다. 카메라 방위를 따라 돌아 바로 읽히는 방향을 유지한다.", status: "부분", where: "map-scene.tsx 의 RegionLabel, scene/view-angle.ts" },
      { title: "방위 고리", rule: "지도 둘레에 5° 눈금, 30° 마다 각도, 동서남북 문자가 있는 고리를 둔다.", status: "부분", where: "map-scene.tsx 의 Compass" },
      { title: "조작과 화면 고정 주석", rule: "회전·이동·확대를 지원한다. 지역을 클릭하면 선택하고, 배경을 클릭하거나 Esc 를 누르면 해제한다. 누른 곳과 뗀 곳이 4px 보다 멀면 끌기로 보고 선택을 바꾸지 않는다. 화면 모서리에 제목, 보기 전환(전체·위에서·낮게), 범례와 출처, 카메라 방위·기울기·거리, 가리킨 지역을 둔다.", status: "부분", where: "stage/schematic/map/schematic-map.tsx" },
      { title: "색 모드", rule: "패널과 지도는 어두운 모드(기본)와 밝은 모드를 갖는다. 밝은 모드는 흰 장면 값(바탕 #ffffff, 글자 #111111)을 쓰고, 주황은 흰 바탕 대비를 위해 선·점 #E06C00, 글자 #B35900 으로 어둡게 바꾼다.", status: "부분", where: "design/tokens.ts 의 SCHEMATIC_THEMES, /style 의 모드 전환. 스테이지는 어두운 모드 고정" },
      { title: "등장", rule: "틀과 방위 고리 → 지역 바닥 외곽선 → 층이 아래부터 하나씩 쌓임 → 이름 순서로 나타난다.", status: "부분", where: "map-scene.tsx 의 T" },
    ],
  },
]

export function statusCounts() {
  const counts: Record<RuleStatus, number> = { 구현: 0, 부분: 0, 미구현: 0 }
  for (const c of CHAPTERS) for (const r of c.rules) counts[r.status]++
  return counts
}
