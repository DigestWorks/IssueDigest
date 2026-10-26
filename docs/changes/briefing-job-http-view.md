# 저장 브리핑 상태 API와 읽기 화면

2026-10-26 KST. [실행 큐](briefing-job-dispatch.md) 다음 연결이다. 이미 접수한 최종 브리핑의 상태·완료 결과·취소를 HTTP와 독립 읽기 화면으로 연결한다. 질문 접수→자료별 분석→최종 생성 전체 orchestration, 기존 질문 버튼 전환, 개발/운영 적용은 이 단계의 완료로 표시하지 않는다. 가짜 완료 결과·동작 없는 질문 버튼·ID 입력 UI를 만들지 않는다.

## Global Constraints

- 비공개 shared 검증 범위·Google 세션/쿠키·현재 원래 작성자/요청자 권한·모든 원문/분석 바인딩 유지. public 게시/인증 허용 범위는 확장하지 않는다. 조회/취소에서 모델·DBOS/예약/자동 복구를 호출하지 않는다. 현재 권한/원문이 없어졌으면 과거 결과·인용을 지운다.
- canonical 결과 검증을 API에 복제하거나 apps끼리 import하지 않는다. 기존 worker의 packet/binding/완료 검증만 agents의 재사용 모듈로 추출해 양쪽에서 재사용한다. provider·model·지침/SDK·실행·예약·workflow bytes/정책은 바꾸지 않는다. 변경 범위는 아래 task 파일과 문서, 생성 OpenAPI 계약이다. 의존성은 API→기존 workspace agents 추가만 허용한다.
- 모든 서버 SQL·검증은 API async event loop 밖에서 수행한다. 오류/응답/로그에 토큰·DSN·raw 예외를 넣지 않는다. protected route no-store·request ID·CSRF·현재 권한을 기존 패턴대로 적용한다. HTML/코드 생성 결과를 실행하지 않는다.
- 실제 제공자·외부 서버/DB·main/기본 runtime 활성화0. 전용 합성 SQL25603과 native AsyncOpenAI MockTransport만 사용한다. 변경 전 기존 실행 파일/hash와 이전 증거를 고정하며 허용 수정은 diff로 검토한다. 기존 테스트를 삭제/약화하지 않는다. 사용자 브라우저 탭을 열거나 이동하지 않는다.

## Task 1: 재사용 검증과 비공개 조회·취소 API

- [x] 구현·TDD·태스크 검토.

허용: 새 packages/agents/src/issuedigest_agents/briefing_receipts.py, 새 packages/domain/src/issuedigest_domain/briefing_job_view.py, 새 apps/api/src/issuedigest_api/briefing_jobs.py, 새 apps/api/tests/test_briefing_jobs_api.py. 수정 apps/worker/src/issuedigest_worker/briefing_worker.py(검증 helper 추출/위임만), apps/api/src/issuedigest_api/main.py(명시 repo 인수·router/protected path), runtime.py(동일 owned engine repo 주입만), apps/api/pyproject.toml(API→workspaceagents), uv.lock, packages/api-client/openapi.json와 src/schema.d.ts(생성만). 추가 허용: apps/api/src/issuedigest_api/errors.py의 path loc Literal에 job_id만 추가하고, apps/worker/tests/test_briefing_worker.py의 test_full_sdk_preflight_failure_precedes_reservation에서 monkeypatch 대상 api() 표현식 하나만 importlib.import_module("issuedigest_agents.briefing_receipts")로 바꾼다. 추출 후 실제 사용되는 helper를 테스트하며 기존 assertion과 실패 주입은 그대로다. private test hook을 위해 호환 wrapper를 만들지 않는다. 기존 provider·worker 실행 정책·다른 tests/exports는 유지한다.

재사용 모듈로 기존 worker `_packet`/`_bound`의 동작을 그대로 옮긴다. 이름은 validate_briefing_packet, validate_briefing_binding이고 worker는 기존 private 이름 alias로 import해 기존 동작을 유지한다. 새 `validate_stored_briefing(job,packet)`은 동일 깊은 child/현재 prompt/hash/binding·완료 receipt canonical SDK 검증 및 job.known_usage/usage_complete/stream_closed 일치를 확인해 QuestionBriefingGeneration을 반환한다. 완료가 아니거나 receipt가 없으면 fixed ValueError, 모델/DB/클라이언트 생성 없이 검증한다. worker read_completed는 동일 ownership checks/SQL prepare 후 새 helper에 위임한다. 기존 worker 경계 검사를 유지한다.

도메인 DTO는 strict/frozen/extra forbid: BriefingQuoteView(snapshot_id UUID4,citation_id UUID4,source_title nonblank<=500,start int>=0,end int>start,text nonblank<=20000,citation_quote nonblank<=20000), BriefingClaimView(text nonblank<=400,epistemic_status source_statement|uncertain,event_date date|null,quotes tuple1..960), BriefingModuleView(kind summary|comparison|timeline,title nonblank<=100,claims tuple1..4), BriefingResultView(outcome answer|insufficient_evidence,message nonblank<=500|null,modules tuple<=3,additional_quotes tuple<=960), BriefingJobView(job_id UUID4,question nonblank<=1500,status pending|running|completed|failed|cancelled|indeterminate,result BriefingResultView|null). result는 completed일 때만 필수이며 나머지는 null. answer는 summary첫모듈/메시지null, comparison은2claim이상, timeline만 날짜필수, insufficient는 message필수/modules비어있음. source_statement도 독립 사실 인증이 아니다.

서버 projection은 검증된 final briefing.modules/coverage만 사용한다. 각 claim references의 해당 source proposition과 transitive depends_on_ids를 원래 proposition 순서로 순회하고 supporting_refs를 (snapshot,citation,start,end,text)로 dedupe해 quotes에 담는다. source_title은 현재 SourcePresentation.title, citation_quote는 현재 bundle에서 같은 citation의 selector.quote이며 ref의 codepoint start:end가 text와 정확 일치한다. 빈/잘못된 quote는 fail closed. additional_quotes는 각 coverage.uncovered_linked_proposition_ids와 그 dependency closure의 supporting_refs를 같은 순서/키로 dedupe한 것이다. 최종 claim 텍스트/분류/날짜를 재해석하지 않는다. 충분한 참조가 없는 answer를 만들지 않는다.

명시 factory `briefing_jobs_router(repository:BriefingJobRepository|None, auth_service:AuthService|None)`와 create_app의 keyword `briefing_job_repository`를 추가한다. GET `/api/v1/workspaces/{workspace_id}/briefing-jobs/{job_id}`는 기존 COOKIE_AUTH 형식 검증 후 repo.get으로 현재 인증, completed이면 prepare + 공유 validate_stored + projection + get 재검증/같은 job DTO 일치를 한 synchronous thread 작업 안에서 수행한다. pending/running/terminal은 상태·질문·resultnull만 반환한다. tokenNone/잘못된token401, repo없음503, authdeny401, forbidden403, 다른workspace/None404, conflict409, integrity/알수없는오류503 고정문구. POST 같은경로 `/cancel`은 기존 AuthService _same_origin, query금지, content-type 정확application/json, body 최대16,384/정확b'{}'만허용. repo.cancel 후 같은 검증된 view를 반환하며 완료 결과가 이기면 그대로 읽는다. extra query·잘못된 UUID·slash redirect에서 원문·body·cookie를 노출하지 않고 protected middleware no-store/requestID를 유지한다. 기존 validation_error는 새 path도 안전하게 처리한다. runtime은 동일 engine으로 repo 구성만하고 migrations/모델/queue를 시작하지 않는다.

검사: 실제 SQL + 기존 유효 briefing seed/native SSE로 completed를 만들고 API 상태/완료projection/취소/완료취소 불변·회수/원문변경·같은workspace reader/다른workspace·재열람 모델0/추가예약0·terminal resultnull·badquery/UUID/body/origin/contenttype/초과body·secretfree503/no-store/requestID·모든SQLoffloop를 확인한다. source dependency closure/추가근거/불확실성/날짜/동일quote dedupe/HTML plaintext DTO/변조receipt를 포함한다. 기존 worker tests와 새 API 범위 검사·Ruff/format/mypy·OpenAPI생성은 수행하되 전체QA는 controller가 한번수행한다. 자기 fixture의 tables/modules/paths/packageattrs만 정리하고 기존fixtures 변경금지. RED→GREEN 보고/커밋. 서브에이전트 생성금지.

## Task 2: 타입 클라이언트와 실제 상태·결과 읽기 화면

- [x] 구현·TDD·태스크 검토.

Task1 확정 DTO를 사용한다. 허용: 새 packages/api-client/src/briefing-jobs.ts + index.ts의 export만, 새 apps/web/app/routes/briefing-job.tsx, 새 apps/web/app/briefing-job.css, apps/web/app/routes.ts에 `/workspaces/:workspaceId/briefings/:jobId` 추가, 새 apps/web/tests/briefing-job-client.test.ts와 briefing-job-view.test.tsx. 기존 질문 제출/공개브리핑/세션/OAuth/Canvas를 바꾸지 않고 기존 BrandHeader·테마·원문 EvidenceDrawer를 재사용한다. ID 입력/가상완료/비활성메뉴/자동모델요청은 없다. 읽기 URL은 내부 링크 대상이며 질문 전송 전체경로는 후속임을 기록한다.

클라이언트 getBriefingJob/cancelBriefingJob은 기존 protectedRequest/ProtectedOptions를 사용하고 exact DTOshape·UUID4·길이·배열/상태별 관계·숫자안전정수·날짜YYYY-MM-DD를 검사해 malformed를 거절한다. 요청 workspace/job 입력 UUID4, 응답 jobID 일치를 확인한다. 취소 POST '{}'. 오류 타입 BriefingJobError(kind ProtectedFailure,requestId?) 고정문구. type은 생성 schema에서 가져오고 result/quote의 codepoint start:end==text도 확인한다.

화면: BrandHeader와 하나의 읽기 칼럼. 첫 로딩과 pending/running을 role=status/aria-live로 명확히 표시하고 1600ms polling, timeout/network는 수동 재조회 제공. 완료는 질문제목→작은 'AI 브리핑' 설명→요약 우선, 실제로 반환된 comparison/timeline 모듈만 렌더링한다. source_statement는 '자료의 서술', uncertain은 '확인하기 어려움'으로 필요할 때 설명하며 '확인된 사실'로 승격하지 않는다. 각 claim에서 근거를 펼쳐 원문 인용·제목을 읽고, 원문열기는 getEvidence 현재권한 결과의 같은 citation ID/전체 quote/해당 codepoint fragment 일치를 확인한 뒤 기존 EvidenceDrawer를 연다. 추가 관련 근거가 있으면 '더 살펴볼 근거' details에 표시한다. insufficient_evidence는 실제message만 보여주고 허구 answer를 만들지 않는다.

취소는 pending/running에서만 제공, 완료/취소/실패/indeterminate를 구분한다. 취소중 표시·중복클릭잠금·늦은취소응답과 선택변경/unmount의 stale응답 차단. 완료상태가 오래된 pending응답으로 후퇴하지 않는다. focus/visibility/reentry에서 job을 다시검증하고401/403/404는 result/drawer/quote를 즉시정리하며401은 로그인링크만제공(지원안되는 returnTo흐름을 새로가정하지않음). 409 conflict·503 unavailable·malformed 응답도 검증 불가이므로 이전 result/drawer/quote를 지우되 원인 문구는 철회로 단정하지 않는다. 잠깐의 network/timeout오류는 철회로단정하지않고 이전요약을 유지할 수 있지만 drawer를 닫고 원문새열기는 job과 evidence 현재검증후만허용한다. drawer닫기초점복원·Escape·기존44pxcontrols·두테마·좁은화면가독성·reducedmotion을 유지한다. HTML은 React plaintext로만. UI는 기존브랜드/타이포/색상토큰을 재사용하고 과장카드/그라디언트/관리자문구를 추가하지 않는다.

테스트: get/cancel/protectedtransport/bodyabort·malformedshape/ID/date/status/quote·loading→pending→running→실제 summary/comparison/timeline·insufficient·cancel잠금/실패/terminal·재열람에서추가submit0·stale응답/취소/unmount/authorityloss/focus·정확원문/불일치거절/초점복원·XSSplaintext·반응형 CSS 기본규칙을 의미있게확인한다. 기존 기능 테스트를약화하지않는다. lint/type/test/build 관련범위·RED→GREEN 보고/커밋. 서브에이전트 생성금지.

## Controller gates

- [ ] 태스크별/전체 독립 검토, 전체 검사·계약·변경 범위·privacy.
- [ ] 기록·Draft PR·Sites·전용 QA 정리. 실제 화면/서버 적용과 질문 전송 전체경로는 별도.
