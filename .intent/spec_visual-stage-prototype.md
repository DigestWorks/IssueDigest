---
title: 시각화 스테이지 프로토타입
slug: visual-stage-prototype
stage: spec
status: accepted
date: 2026-10-11
---

# 시각화 스테이지 프로토타입 — spec

intent: `.intent/intent_visual-stage-prototype.md`

## 요구사항

| ID | 요구사항 | 확인 방법 |
| --- | --- | --- |
| R1 | 1280px 이상 화면에서 좌측 채팅(약 400px)과 우측 스테이지가 나란히 표시된다 | 브라우저 스크린샷 |
| R2 | UI 토큰(배경·전경·테두리·버튼 등)은 채도 0의 OKLCH 값이다. 색이 있는 값은 데이터 팔레트 토큰(`--data-*`)에만 있다 | 토큰 검사 단위 테스트 |
| R3 | 스테이지에 볼류메트릭 라이트, 파티클, 블룸, 피사계 심도, 거리 감쇠(fog), 그림자가 적용된다 | 스크린샷 |
| R4 | 스테이지는 이벤트(R10)만으로 상태가 바뀐다. 채팅 시나리오는 이벤트 열을 시간 간격을 두고 보낸다 | 리듀서 단위 테스트 |
| R5 | 탐색 시나리오: 노드·엣지가 이벤트마다 추가되고 등장 애니메이션을 가진다. 초점 노드로 카메라와 피사계 심도 초점이 이동한다. 탐색 경로 엣지를 따라 파티클이 이동한다 | 브라우저에서 재생 확인 |
| R6 | 그래프 노드는 3D 힘 기반 물리 시뮬레이션으로 배치된다. 노드를 드래그하면 연결된 노드가 따라 움직이고, 놓으면 시뮬레이션이 다시 안정된다 | 브라우저 조작 |
| R7 | 지도 시나리오: 서울 자치구 3D 지도가 나타나고 카메라가 서울로 이동한다. 자치구 면은 범주 색과 압출 높이로 값을 표시하고 높이 0에서 올라온다. 경계선은 흰 선, 지역명은 지면에 눕힌 글자다. 방위 고리가 있다 | 스크린샷 |
| R8 | 사용자는 스테이지에서 확대·축소, 회전, 기울이기, 이동을 할 수 있다 | 브라우저 조작 |
| R9 | 결과 패널(차트, 타임라인, 주장 비교)이 스테이지 3D 공간에 배치되고 등장 애니메이션을 가진다. 주장을 선택하면 근거 노드나 지역으로 초점이 이동한다 | 브라우저 조작 |
| R10 | 이벤트는 Zod 스키마로 검증한다. 잘못된 이벤트는 버리고 콘솔에 경고를 남긴다 | 단위 테스트 |
| R11 | 시나리오에 없는 질문은 근거 부족 상태를 채팅과 스테이지에 표시한다 | 브라우저 확인 |
| R12 | 샘플 데이터임을 스테이지와 채팅 답변에 표시한다. 인물·정당·법안 이름은 가상이다 | 스크린샷 |
| R13 | `prefers-reduced-motion`이면 파티클 이동·카메라 이동 애니메이션·등장 애니메이션을 즉시 전환으로 바꾸고 볼류메트릭 라이트와 피사계 심도를 끈다 | 브라우저 에뮬레이션 |
| R14 | 노드 300개 또는 서울 지도 표시 상태에서 Apple Silicon Mac Chrome 기준 초당 60프레임에 가깝다. `?debug`로 프레임 표시를 켠다 | 측정값 기록 |
| R15 | `pnpm typecheck`, `pnpm test`, `pnpm build`가 통과한다 | 명령 실행 |

## 설계

### 구조

저장소 루트를 pnpm workspace로 만들고 프론트엔드를 `apps/web`에 둔다. 이후 에이전트 서버(`apps/agent`)와 FastAPI(`services/api`)를 같은 저장소에 추가한다.

```
apps/web/app/
  routes/home.tsx            2단 레이아웃
  chat/                      ACF Thread + 시나리오 재생 런타임
  stage/
    events.ts                이벤트 Zod 스키마와 타입
    store.ts                 스테이지 상태(zustand) + 리듀서
    scenarios/               샘플 시나리오(이벤트 열과 채팅 텍스트)
    scene/                   Canvas, 카메라, 조명, 후처리, 파티클
    graph/                   힘 기반 그래프, 드래그, 탐색 파티클
    map/                     자치구 압출, 경계선, 지면 라벨, 방위 고리
    panels/                  차트, 타임라인, 주장 비교 패널
  styles/tokens.css          무채색 UI 토큰과 데이터 팔레트
```

### 스테이지 이벤트

`stage.reset`, `stage.status`(exploring | answered | insufficient), `graph.node.add`, `graph.edge.add`, `graph.focus`, `graph.traverse`(경로 노드 ID 목록), `map.show`(region, level), `map.choropleth`(지역 코드별 범주·값, 범례), `map.focus`(지역 코드), `panel.add`(종류: chart | timeline | claims, 데이터, 배치 기준 노드·지역), `claim.focus`(근거 노드·지역). 모든 이벤트에 `source`(샘플 여부 포함) 필드를 둔다. 실제 에이전트 연결 시 같은 스키마를 도구 인자로 사용한다.

### 채팅

`agent-chat-framework` 레지스트리의 `thread-aui`를 설치하고, assistant-ui `useLocalRuntime`에 시나리오 재생용 `ChatModelAdapter`를 넣는다. 어댑터는 질문을 시나리오와 매칭해 답변 텍스트를 스트리밍하면서 스테이지 이벤트를 보낸다. 빈 채팅에는 시나리오 질문을 제안으로 보여 준다.

### 스테이지 렌더링

- three 0.186 + `@react-three/fiber` 9.8 + `@react-three/drei` 10.7 + `@react-three/postprocessing` 3.2(postprocessing 6.39). peer 범위: fiber는 react `>=19 <19.4`, postprocessing은 three `>=0.168 <0.187`(npm registry, 2026-10-11 조회).
- 후처리: `EffectComposer autoClear={false}` 안에 `GodRays`(광원 메시 지정), `Bloom`, `DepthOfField`(`target`으로 초점), `Vignette`, `Noise`. 근거: pmndrs/react-postprocessing 문서 `docs/effects/god-rays.mdx`, `_autodocs/api-reference/DepthOfField.md`.
- 카메라: drei `CameraControls`로 사용자 조작과 초점 이동 애니메이션을 함께 처리한다.
- 물리: `d3-force-3d` 3.0 시뮬레이션. 드래그 중에는 노드의 `fx/fy/fz`를 고정하고 시뮬레이션을 다시 가열한다.
- 지도: `d3-geo` Mercator 투영으로 GeoJSON을 평면 좌표로 바꾸고, three `ExtrudeGeometry`로 압출한다. 경계선은 `EdgesGeometry` 흰 선이다. 지면 라벨은 drei `Text`(troika)를 쓰며 Pretendard `.woff`를 지정한다. troika는 `.woff2`를 지원하지 않는다(troika-three-text 문서).
- 결과 패널: 스테이지 위에 CSS 원근(perspective)을 준 DOM 층으로 쌓고, 깊이 방향에서 회전하며 들어오는 등장 애니메이션을 준다. shadcn chart(Recharts)와 shadcn 카드로 그린다. 패널이 보이면 카메라 focal offset으로 장면을 왼쪽으로 옮긴다. drei `Html transform`으로 3D 위치에 붙이는 방식은 카메라 이동 중 글자가 흔들리고 흐려져 데이터 판독 제약에 맞지 않아 쓰지 않았다(구현 중 변경).

### 디자인 토큰

- UI 토큰: `oklch(L 0 0)` 형식만 사용한다. 깊이는 명도 단계, 그림자, 빛으로 표현한다.
- 데이터 팔레트: 범주형 `--data-cat-1..6`, 노드 유형별 색. 데이터 인코딩에서만 참조한다.
- 글꼴: Pretendard(OFL). 수치는 `tabular-nums`.

### 외부 자료

- 서울 자치구 경계: [southkorea/seoul-maps](https://github.com/southkorea/seoul-maps) `kostat/2013/json/seoul_municipalities_geo_simple.json`(57,732 bytes). README 표기 라이선스 Apache v2.0, 원자료 통계청 센서스용 행정구역경계(2013). 다운로드 전 허락을 받는다. 저장소에 출처 표기를 남긴다.
- ACF 레지스트리: `~/code/framework/agent-chat-framework/public/r/*.json`을 로컬 정적 서버로 제공해 `@acf` 네임스페이스로 설치한다.

## 열린 질문

없음. 성능 기준은 intent 제안값(R14)을 따른다.
