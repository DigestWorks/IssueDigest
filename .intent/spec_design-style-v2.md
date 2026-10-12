---
title: 지도 기반 디자인 스타일 재정의
slug: design-style-v2
stage: spec
status: accepted
intent: .intent/intent_design-style-v2.md
date: 2026-10-11
---

# 지도 기반 디자인 스타일 재정의 — 명세

## 요구사항

- [ ] R1 규칙: `design/guide.ts` 의 장을 지도에서 확정한 표현 기준으로 다시 쓴다. 장은 핵심 원칙, 장면, 선과 주석, 색, 부피, 효과, 글자, 화면 고정 주석, 패널, 지도, 모션, 조작이다.
- [ ] R2 색 원칙: 핵심 원칙의 색 규칙은 「데이터 색은 답과 관련된 부분에만, 주황은 선택·초점에만」이다. 「색상은 데이터에만 쓴다」는 폐기 기록으로 옮긴다.
- [ ] R3 기본 모드: 어두운 모드가 기본이다. `/style` 은 어두운 모드로 열리고 `?mode=light` 와 전환 버튼으로 밝은 모드를 본다.
- [ ] R4 폐기 기록: 지도 이전 규칙(흰 배경, 무채색 UI·주황 금지, 불투명 압출 지역, 반복 주사선, 빛무리 등장 등)은 `guide.ts` 의 폐기 목록으로 옮기고 폐기 이유를 적는다. 홈 스테이지에만 쓰이는 규칙(무광 기호 노드)은 「홈 스테이지 적용 때 재정의」로 표시한다.
- [ ] R5 토큰: 지도 코드의 표현 상수(층 간격, 선택 시 층 확장, 색 번짐, 아웃포커스, 색수차, 바닥 조명, 등장 시각)를 `design/tokens.ts` 로 옮기고 `map-scene.tsx` 는 토큰을 읽는다. 값은 바꾸지 않는다.
- [ ] R6 `/style` 페이지: shadcn 컴포넌트(Table, Badge, Button, Separator)를 쓰지 않고 도면 양식 요소(`stage/schematic/primitives.tsx`, `ControlButton`)로 만든다. 페이지 바탕과 글자는 테마 변수(`--sch-*`)를 쓴다.
- [ ] R7 견본: 장마다 실제 토큰·컴포넌트로 그린 견본을 둔다. 색(데이터·중립·주황·불투명도), 선과 주석, 글자, 화면 고정 주석 요소, 패널, 지도, 모션(지도 등장 다시 재생).
- [ ] R8 상태 표시: 규칙마다 구현 상태(구현·부분·미구현)와 구현 위치를 적고, 상태 개수를 정직하게 센다. 홈 스테이지에 적용되지 않은 규칙은 「부분」이며 위치에 그 사실을 적는다.
- [ ] R9 문서: `docs/design/style-guide.md` 를 새 원칙 요약, 결정 기록, 폐기 규칙 요약으로 정리한다. 정체성 기준 「출처가 붙은 조사 기록」은 유지한다.

## 설계

- 재사용: `SCHEMATIC_THEMES`·`schematicVars`·`SchematicTheme`·`SchematicModeProvider`, `SchematicFrame`·`Rule`·`SquarePoint`, `ControlButton`, `SchematicPanelSpecimen`, `SchematicMapSpecimen`, `OPACITY`·`TYPE_ROLES`·`MOTION`, `DATA_CATEGORICAL`·`dataColor`.
- 토큰: `tokens.ts` 에 `HOLOGRAM`(층 간격, 선택 확장, 색 번짐), `MAP_EFFECTS`(아웃포커스, 색수차), `FLOOR`(바닥 조명), `MAP_MOTION`(등장 시각)을 추가한다. `map-scene.tsx` 의 같은 이름 상수는 토큰을 가리키게 바꾼다.
- 규칙 데이터: `guide.ts` 의 `Chapter`·`Rule` 형식을 유지하고 `RETIRED`(폐기 규칙: 규칙, 폐기 날짜, 이유) 목록을 추가한다.
- 페이지: `routes/style.tsx` 를 `SchematicTheme` 바탕으로 다시 쓴다. 왼쪽 목차(번호 | 장 이름), 장마다 머리(번호·보조 글자·제목·머리선), 규칙 목록(제목, 내용, 상태 사각점, 위치), 견본 영역. 모드 전환은 목차 아래 `ControlButton`.
- 견본: `style/specimens.tsx` 를 도면 양식으로 다시 쓴다. 흰 바탕 shadcn 견본(UI 색 토큰, 노드 기호, 35° 기울기 판)은 지운다.

## 버린 대안

- 기존 표 레이아웃에 색만 바꾸기: 사용자가 shadcn 기본 요소 재사용을 거부했다.
- 홈 스테이지까지 한 번에 적용: 범위 밖으로 결정했다.

## 함정

- `/style` 은 미리 렌더되는 SPA 라우트다. three.js 는 지도 견본 안에서 지연 로드한다(현재 구조 유지).
- 패널 견본은 `useStage` 의 focus 를 쓴다. 다른 견본과 상태가 섞이지 않게 기존 동작을 유지한다.
- 장 id 를 바꾸면 `MODE_CHAPTERS` 와 앵커 링크(`#map`, `#panels`)가 깨진다. 검증 스크립트(`shot-map.mjs`)가 `#map canvas` 를 쓴다.
- 밝은 모드 주황 글자는 `ACCENT_TEXT` 를 써야 대비 기준을 지킨다.

## 완료 기준

```
pnpm -C apps/web typecheck   # 오류 없음
pnpm -C apps/web test        # 통과
pnpm -C apps/web build       # 성공
```

- `/style` 이 어두운 모드로 열리고, 전환 버튼과 `?mode=light` 로 밝은 모드가 된다.
- 페이지에 shadcn 컴포넌트 import 가 없다(`grep components/ui routes/style.tsx style/specimens.tsx` 결과 없음).
- 지도 견본과 `/map` 의 화면이 토큰 이동 전과 같다(같은 각도 스크린샷 비교).
