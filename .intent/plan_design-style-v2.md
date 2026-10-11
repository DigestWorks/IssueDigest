---
title: 지도 기반 디자인 스타일 재정의
slug: design-style-v2
stage: plan
status: accepted
intent: .intent/intent_design-style-v2.md
spec: .intent/spec_design-style-v2.md
date: 2026-10-11
---

# 지도 기반 디자인 스타일 재정의 — 구현 계획

## 바뀌는 파일

| 파일 | 무엇을 |
|---|---|
| `apps/web/app/design/tokens.ts` | `HOLOGRAM`·`MAP_EFFECTS`·`FLOOR`·`MAP_MOTION` 토큰 추가 |
| `apps/web/app/stage/schematic/map/map-scene.tsx` | 표현 상수를 토큰에서 읽음(값 그대로) |
| `apps/web/app/design/guide.ts` | 장 재작성, 색 원칙 교체, `RETIRED` 폐기 목록 |
| `apps/web/app/stage/schematic/schematic-chart.tsx`, `schematic-claims.tsx` | 차트 계열·입장 막대를 주황 대신 데이터 색으로(색 원칙 결정 3 적용) |
| `apps/web/app/routes/style.tsx` | 도면 양식 페이지로 재작성, 어두운 모드 기본 |
| `apps/web/app/style/specimens.tsx` | 도면 양식 견본으로 재작성, 흰 바탕 견본 삭제 |
| `docs/design/style-guide.md` | 원칙 요약·결정 기록·폐기 요약으로 정리 |

## 작업 순서

1. 토큰 이동 — 타입 검사 통과, `/map` 같은 각도 스크린샷이 이동 전과 같음
2. 규칙 데이터 재작성(`guide.ts`) — 타입 검사 통과, 상태 개수 확인
3. 견본 재작성(`specimens.tsx`) — 타입 검사 통과
4. 페이지 재작성(`style.tsx`) — 어두운·밝은 모드 전체 페이지 스크린샷 확인, shadcn import 없음
5. 문서 정리(`style-guide.md`) — 새 장 구성과 결정 기록 대조
6. 전체 검증, 커밋·push

단계마다 `feat:`·`refactor:`·`docs:` 태그로 커밋한다.

## 가장 위험한 단계

- 1단계 토큰 이동: 값을 옮기다 틀리면 지도 표현이 바뀐다. 같은 각도·같은 시각 스크린샷을 이동 전후로 비교하고, 다르면 되돌린다.
- 4단계 페이지: 패널·지도 견본이 들어 있는 긴 페이지라 레이아웃이 좁은 폭에서 깨질 수 있다. 1440px 와 1024px 폭에서 확인한다.

## 검증

```
pnpm -C apps/web typecheck
pnpm -C apps/web test
pnpm -C apps/web build
grep -n "components/ui" apps/web/app/routes/style.tsx apps/web/app/style/specimens.tsx
```

화면 확인: `/style`(어두운 모드), `/style?mode=light`, 목차 링크 이동, 패널·지도 견본 다시 재생, `/map` 등장.
