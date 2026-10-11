---
title: 시각화 스테이지 프로토타입
slug: visual-stage-prototype
stage: plan
status: accepted
intent: .intent/intent_visual-stage-prototype.md
spec: .intent/spec_visual-stage-prototype.md
date: 2026-10-11
---

# 시각화 스테이지 프로토타입 — 구현 계획

## 바뀌는 파일

| 파일 | 무엇을 |
|---|---|
| `package.json`, `pnpm-workspace.yaml` (신규) | 루트 workspace, `dev`·`typecheck`·`test`·`build` 스크립트 위임 |
| `apps/web/*` (신규) | `pnpm create react-router@latest`로 생성, `react-router.config.ts`에 `ssr: false` |
| `apps/web/components.json`, `apps/web/app/components/ui/*` (신규) | shadcn init, `@acf` 레지스트리 등록, 필요한 컴포넌트 설치 |
| `apps/web/app/components/assistant-ui/*` (신규) | ACF `thread-aui`와 의존 항목 |
| `apps/web/app/styles/tokens.css` (신규) | 무채색 UI 토큰, 데이터 팔레트 |
| `apps/web/app/stage/events.ts`, `store.ts` (신규) | 이벤트 스키마, 스테이지 상태와 리듀서 |
| `apps/web/app/stage/scene/*` (신규) | Canvas, 카메라, 조명, 후처리, 파티클 |
| `apps/web/app/stage/graph/*` (신규) | 힘 기반 그래프, 드래그, 탐색 파티클 |
| `apps/web/app/stage/map/*` (신규) | 자치구 압출, 경계선, 지면 라벨, 방위 고리 |
| `apps/web/app/stage/panels/*` (신규) | 차트, 타임라인, 주장 비교 패널 |
| `apps/web/app/stage/scenarios/*` (신규) | 탐색·지도·근거 부족 샘플 시나리오 |
| `apps/web/app/chat/*` (신규) | 시나리오 재생 `ChatModelAdapter`, 런타임 |
| `apps/web/app/routes/home.tsx` (신규) | 2단 레이아웃 |
| `apps/web/public/geo/seoul-gu.json`, `apps/web/public/geo/SOURCE.md` (신규) | 서울 자치구 경계와 출처 |
| `apps/web/app/**/*.test.ts` (신규) | 토큰·이벤트·리듀서 테스트 |
| `apps/web/app/design/tokens.ts`, `apps/web/app/design/guide.ts` (신규) | 불투명도·글자·모션 토큰, 스타일 가이드 규칙 데이터 |
| `apps/web/app/routes/style.tsx`, `apps/web/app/style/specimens.tsx` (신규) | `/style` 스타일 가이드 페이지와 견본 |
| `docs/design/style-guide.md` (신규) | 정체성 기준과 결정 기록 |
| `apps/web/app/stage/schematic/map/*`, `apps/web/app/stage/scene/view-angle.ts` (신규) | 도면 양식 3D 지도 컴포넌트, 눕힘·세움 각도 기준 |
| `README.md` (신규) | 실행 방법 |

## 작업 순서

1. 앱 생성: workspace, React Router SPA, shadcn init. Canvas는 클라이언트에서만 마운트한다 — 빈 Canvas 상태로 `pnpm build`가 통과한다.
2. 토큰과 레이아웃: tokens.css와 shadcn 생성 CSS의 UI 토큰을 무채색으로 덮어쓴다(`--chart-*`만 데이터 색 허용). 2단 레이아웃, 샘플 표시, 임시 입력창과 제안 질문 — 토큰 테스트 통과.
3. 이벤트와 상태: events.ts, store.ts, 시나리오 재생기, 테스트 — `pnpm test` 통과.
4. 스테이지 기본 장면: Canvas, CameraControls, 지면, 조명·그림자, fog, 파티클, 후처리 — 스크린샷을 사용자에게 공유.
5. 그래프: 힘 기반 배치, 노드 등장, 초점 이동, 탐색 파티클, 드래그 — 탐색 시나리오 재생, 스크린샷 공유.
6. 지도: 경계 데이터 다운로드(허락 후), 압출·경계선·라벨·방위 고리, 카메라 이동 — 지도 시나리오 재생, 스크린샷 공유.
7. 결과 패널: 차트·타임라인·주장 비교, 주장 선택 시 초점 이동 — 조작 확인.
8. 근거 부족 시나리오, reduced motion, `?debug` 프레임 표시 — 에뮬레이션과 측정.
9. 채팅: ACF 레지스트리를 `python3 -m http.server 3100 --directory ~/code/framework/agent-chat-framework/public`으로 제공하고 `thread-aui` 설치, 시나리오 재생 `ChatModelAdapter`로 임시 입력창 교체. 한 커밋 분량 안에 해결되지 않으면 임시 입력창을 유지하고 README에 기록한다.
10. 스타일 가이드(사용자 요청, 2026-10-11): 정체성 기준 「출처가 붙은 조사 기록」을 정하고, 토큰 모듈(`design/tokens.ts`)과 규칙 데이터(`design/guide.ts`)를 만들어 `/style` 페이지에서 렌더링한다 — 페이지 전체 스크린샷 확인.
11. 결과 패널 재디자인(사용자 요청, 2026-10-11): The Division 양식(선과 점으로 만든 틀, 주황 강조, 어두운 반투명 바탕)으로 `stage/schematic/*` 를 새로 만들어 `/style` 에서 먼저 확인받고, 승인 후 `panel-layer.tsx` 를 교체한다.
12. 3D 지도 인터랙티브 컴포넌트(사용자 요청, 2026-10-11): 스테이지 상태와 분리된 도면 양식 지도 `stage/schematic/map/*` 를 자체 Canvas·카메라로 만들어 `/style` 에서 먼저 확인받는다. 스테이지 교체는 승인 후 진행한다 — 극각별 스크린샷과 클릭·Esc·보기 전환 조작 확인.
13. 도면 양식 밝은 모드(사용자 요청, 2026-10-11): 테마 토큰을 다크·라이트 두 벌로 나누고 패널·지도가 모드를 따르게 한다. `/style` 에 모드 전환(?mode=light)을 두고, 어두운 모드가 기본이다 — 같은 각도의 다크·라이트 스크린샷 비교.
14. README, 전체 검증, 커밋·push.

단계마다 `feat:` 등 태그로 커밋한다.

## 가장 위험한 단계

- 4~6단계 후처리 조합: GodRays·DepthOfField·Bloom을 함께 쓰면 프레임이 R14 기준 아래로 떨어질 수 있다. 측정 후 GodRays 해상도와 DoF 해상도를 낮추고, 그래도 부족하면 효과별 on/off를 `?debug`에서 비교해 조정한다.
- 9단계 ACF 설치: 레지스트리 항목이 Next.js 전용 import를 포함하면 React Router에서 빌드가 깨진다. 이 경우 해당 파일만 수정하고 수정 내역을 README에 적는다.
- 되돌리기: 단계별 커밋이므로 깨진 단계의 커밋을 되돌린다.

## 검증

```
pnpm -C apps/web typecheck
pnpm -C apps/web test
pnpm -C apps/web build
```

브라우저 확인 경로:
- `/` 첫 화면: 무채색 레이아웃, 샘플 표시, 제안 질문
- 탐색 질문 → 노드 추가, 초점 이동, 탐색 파티클, 노드 드래그
- 지도 질문 → 카메라 이동, 자치구 압출, 회전·기울이기·확대
- 결과 패널의 주장 선택 → 초점 이동
- 시나리오 밖 질문 → 근거 부족 상태
- 동작 줄이기 에뮬레이션 → 애니메이션·효과 축소
- `/?debug` → 프레임 수치 기록
