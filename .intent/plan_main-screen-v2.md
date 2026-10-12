---
title: 메인 화면 재작성
slug: main-screen-v2
stage: plan
status: accepted
intent: .intent/intent_main-screen-v2.md
spec: .intent/spec_main-screen-v2.md
date: 2026-10-12
---

# 메인 화면 재작성 — 구현 계획

## 바뀌는 파일

| 파일 | 무엇을 |
|---|---|
| `apps/web/app/stage/schematic/scene/*` (신규) | 테마 컨텍스트, 바닥·격자, 후처리, 초점 위치 등록부 |
| `apps/web/app/stage/schematic/map/map-scene.tsx` | 공용 부분을 scene 에서 가져오고 `MapHologram` 을 내보냄 |
| `apps/web/app/stage/schematic/callout.tsx` (신규), `map/region-callout.tsx` | 주석 틀 일반화 |
| `apps/web/app/routes/home.tsx`, `chat/*`, `stage/stage-view.tsx`, `stage/scene/{stage-canvas,environment,effects,camera-rig,registry}.tsx`, `stage/graph/{graph-layer,graph-node,glyph-icon}.tsx`, `stage/map/{map-layer,compass-ring}.tsx`, `stage/panels/*`, `stage/hud/*` | 삭제 |
| `apps/web/app/components/ui/*` | 쓰이지 않게 된 컴포넌트 삭제 |
| `apps/web/app/routes.ts`, `apps/web/app/routes/main.tsx` (신규) | index 라우트를 새 메인 화면으로 |
| `apps/web/app/main/*` (신규) | 메인 화면: 대화 열(`log/`), 스테이지(`stage/`) |
| `apps/web/app/stage/events.ts`, `store.ts`, `store.test.ts` | `GraphEdge.basis`, `trail` |
| `apps/web/app/stage/scenarios/ontology.ts` | 추론 관계 표시 |
| `apps/web/app/design/guide.ts`, `docs/design/style-guide.md` | 적용 결과 반영, 그래프 규칙 |
| `apps/web/scripts/shot-main.mjs` (신규) | 메인 화면에 질문을 보내고 시각별 스크린샷 |
| `apps/web/package.json` | 쓰이지 않게 된 UI 의존성 제거(@base-ui/react, @shadcn/react, class-variance-authority, lucide-react) |

## 작업 순서

1. 장면 공용 부분 분리와 주석 일반화 — `/map` 같은 각도 스크린샷 비교
2. 기존 홈 삭제, 새 index 라우트 뼈대(대화 열 + 지도만 있는 스테이지) — typecheck·build, `/style`·`/map` 확인
3. 이벤트·상태 확장(basis, trail)과 테스트 — `pnpm test`
4. 그래프 홀로그램 — 온톨로지 시나리오 시각별 스크린샷
5. 결과 패널 3D 배치, 스테이지 카메라·초점·화면 고정 주석 — 두 시나리오 스크린샷, 각도별 확인
6. 대화 열 완성(조사 기록, 단계, 출처, 제안 질문, 모드 전환) — 세 질문 흐름 확인
7. 규칙 문서 갱신, 전체 검증, push

## 가장 위험한 단계

- 1단계: 지도 장면을 쪼개다 `/map` 표현이 바뀔 수 있다. 같은 각도·시각 스크린샷을 비교해 차이가 있으면 되돌린다.
- 4단계: 힘 기반 배치가 바닥 범위를 벗어나거나 노드가 겹칠 수 있다. 범위 고정과 충돌 힘을 두고 스크린샷으로 확인한다.

## 검증

```
pnpm -C apps/web typecheck
pnpm -C apps/web test
pnpm -C apps/web build
```

화면 확인: `/`(어두운·밝은 모드), 제안 질문 두 개와 시나리오 밖 질문, 노드·지역 클릭·배경 클릭·Esc, 카메라 각도별 패널 방향, `/map`, `/style`.
