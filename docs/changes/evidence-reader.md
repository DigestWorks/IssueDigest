# 저장된 근거를 읽는 웹 화면

2026-10-13. 관련 R1·R2·R4, P1/P2. 공개 배포는 사용자 요청으로 유예한다. 실제 자료 조사·AI 결과 저장/재열람·두 사용자 접근·비용/오류 품질 검증까지의 단계적 구현을 계속하며 이번 부분 완료를 PoC 출시 완료로 표시하지 않는다.

## Spec

현재 근거 조회 API와 인용 계약이 있으나 웹은 연결 확인만 제공한다. 같은 출처의 보호된 근거 GET을 소비하고 원문·페이지·인용 위치를 읽는 실제 화면을 연결한다. 실제 계정 발급·자료 이관·AI·운영 연결은 별도다. 앱에 예시 자료를 기본 삽입하거나 자료가 있다고 꾸미지 않는다.

## Global Constraints

- 기존 GET `/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}`와 `EvidenceBundle`, 서버 쿠키 인증·멤버십을 그대로 사용한다. 신규 서버 경로·DB schema·공급자 로그인·세션 발급·기존 generated 계약 변경 없음.
- API 클라이언트는 같은 출처 relative URL·credentials same-origin·cache no-store로 요청한다. 토큰/자료를 localStorage·sessionStorage·URL query·로그에 저장하지 않는다. 서버 request UUID를 확인하며 실패 응답의 body/detail은 화면에 반영하지 않는다.
- 임의 JSON을 TypeScript 타입 cast만으로 성공 처리하지 않는다. 화면이 사용하는 envelope·ID chain·페이지/표/셀·selector·정확 quote/인접 문맥을 검증한다. 서버의 전체 도메인 검증·인증/원문 진위·semantic support를 대체하는 클라이언트 검증은 아니다.
- 원문은 React text로 표시한다. HTML 실행·외부 이미지 자동 로드·생성 요약/예시 삽입 없음. 외부 출처 링크는 HTTP(S), credential 없음만 허용하고 새 창 rel=noopener noreferrer. 위치 일치가 주장 지지의 검증을 의미하지 않음을 한 문장으로 안내한다.
- Home의 기존 빈 자료·실제 연결 확인을 유지한다. 빈 자료 자동 샘플이나 AI를 실행하는 척하는 동작 없음. 공개 앱 배포·main 병합·운영 DB migration/권한 변경·수집 원문 변경·모델 호출을 하지 않는다. 의존성/lockfile 변경 없음.
- 디자인은 기존 cream/green 계열의 조용한 문서 읽기 화면이다. 원문과 인용 목록 두 영역, 모바일에서는 세로 배치. 장식 카드·추가 탭·기술 설명 패널 없이 필요한 상태와 액션만 보여준다. 키보드·focus·loading live status·overflow와 reduced-motion을 확인한다.

## Task 1: 보호 근거 HTTP 클라이언트와 원문 읽기 화면

Worktree: 현재 격리된 `feat/evidence-reader`. Task brief에 전역 제약을 포함하며 이 spec이 권위다.

1. `packages/api-client/src/evidence.ts`에 `getEvidence(workspaceId, snapshotId, options?)`를 구현하고 public index에서 export한다. 경로 ID는 UUID4를 fetch 전에 검증. 기본 timeout 10,000ms, 양의 finite integer만 허용. options의 AbortSignal에 이미 취소/후속 취소 모두 반응하며 header와 body를 포함한 deadline을 둔다. 결과는 `{data: EvidenceBundle, requestId: string}`. 오류는 sanitized EvidenceError와 `invalid-link | authentication | not-found | unavailable | invalid-response | network | timeout | aborted` 종류이며 requestId는 유효 서버 UUID4만 전달한다. 401/404/503 및 기타 HTTP는 안전한 상태로 분류한다. JSON media type·valid request ID·no-store 응답·schema version·요청 workspace와 응답 chain·표시할 필드 타입·중복 ID·ordered bounded PageSpan·각 citation kind/reference/정확 quote/context·PDF page bounds·table cell quote를 확인한다. 전문 schema 재구현 대신 검증에 쓰는 부분을 명확히 문서화하며 사용하는 메타데이터는 모두 검증한다.
2. `apps/web/app/routes/evidence.tsx`와 필요하면 focused `apps/web/app/evidence/reader.tsx`, `reader.css`를 만들고 `/workspaces/:workspaceId/evidence/:snapshotId` route를 등록한다. 최초 요청·재시도 중에는 읽는 중 상태, 401 로그인 필요(존재하지 않는 로그인 링크 생성 안 함), 404 자료/권한 없음, 503 미준비/서버 문제, malformed/timeout/network 각각 안전한 문구와 필요한 재시도. ID 변경/언마운트/재시도 때 요청을 취소하고 전 자료·인용·requestId를 즉시 지워 이전/늦은 응답이 다시 표시되지 않게 한다. 미구성 API에 성공 자료를 보이지 않는다.
3. 성공 화면은 공급처/source ID·원문 출처 링크(없으면 미등록)·수집 시각, 파싱 텍스트/실제 page number 목록과 선택, 저장된 인용 목록을 제공한다. PDF/text 선택은 기존 getCitationUtf16Range로 Unicode 위치를 강조하고 해당 실제 페이지/텍스트로 이동한다. text citation은 전체 텍스트; PDF는 페이지 경계, table_cell은 검증된 해당 표 셀 내용을 선택/표시한다. 인용이 없거나 텍스트가 비어 있을 때 정확한 empty state. 초기 첫 인용을 자동 선택하지 않는다. 단순 표시/선택/페이지 이동은 모델 호출·추가 GET 없음. 요청 UUID는 실패 지원용 details에만 나타내며 UI를 지배하지 않는다. 선택된 인용 상태를 키보드/보조기기에 알린다.
4. Home에 한 개의 '근거 링크 열기' form을 추가한다. 같은 출처의 위 route absolute URL 또는 root-relative path만 허용한다. 다른 origin·query·fragment·credential·형식 오류는 거부한다. UUID 두 개를 사용자가 직접 타이핑하는 여러 폼을 만들지 않는다. 제출은 React Router로 이동하고 실제 근거 GET이 화면을 채운다. 소유/로그인 권한을 링크 자체가 부여한다고 설명하지 않는다.
5. TDD: client+component+Home 새 동작의 실제 assertion RED를 먼저 보존하고 최소 구현 후 GREEN. 기존 합성 Canvas fixture 또는 검증된 새로운 작은 synthetic EvidenceBundle만 테스트에 사용한다. 200의 불완전/교차 workspace/버전/reference/인용/URL·Unicode·PDF page/table mismatch, 401/404/503/HTTP·malformed headers/body, fetch/body timeout, 이미/중간 취소, invalid inputs와 fetch 없음, 실제 렌더 인용 선택/페이지 이동/표·빈 인용, loading·retry·route change 중 late response·unmount, unsafe HTML·외부 링크·Home 링크 형식/실제 navigation을 검증한다. 인증 fixture·운영 자료를 production 앱에 추가하지 않는다. focused files를 분리한다. README에 진입 경로·인증 미연결·서버 도메인 검증과 display validation의 경계·배포 유예를 기록한다.
6. 최종 focused tests·JS lint/typecheck/build/contract check를 실행하고 본인 diff self-review, report와 commit. Controller가 실제 합성 PostgreSQL 포함 전체 검사·독립 task/final 리뷰·개발용 실제 API/브라우저 QA·Draft PR·Sites·사용자 폴더/서버 worktree 인계를 담당한다. 체크는 구현 항목만 완료하고 controller 결합 항목은 남겨 둔다.

- [ ] 보호 GET 클라이언트·display validation·취소/오류 구현.
- [ ] 실제 읽기 화면·근거 링크 진입·상태/Unicode/키보드 구현.
- [ ] assertion RED/GREEN·회귀·문서/자체 검사·commit.

## Controller 결합

- [ ] 전용 loopback 합성 PostgreSQL 전체 검사·독립 작업/전체 리뷰.
- [ ] 실제 합성 FastAPI→Vite→브라우저에서 보호 GET·원문/인용·오류·1366/390·키보드 확인. fixture session은 QA 전용 HTTPS browser cookie로만 주입하고 공개 API에 발급 route를 만들지 않는다. 실제 수집 자료·운영 DB는 사용하지 않는다.
- [ ] 선행 PR #14 위 Draft PR·Sites 요약/배포 유예·이전 기록 보존·개발 worktree 인계. main/실제 앱 게시 없음.
