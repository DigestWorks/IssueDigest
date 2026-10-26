# 질문 제출·생성 상태·브리핑 읽기 연결

2026-10-26. 질문 중심 B2C 방향과 기존 공유 초기 검증 권한을 유지한다. 신규 질문은 실제 분석→최종 생성 코어로 보내고 완료 접수 후 기존 정확 원문 읽기 화면으로 이동한다. 이전 research URL/결과·공개 브리핑·Google 세션·예산·SDK/model/version/slot은 보존한다. 원문/범위/ID/모델/예약 입력을 사용자에게 요구하지 않는다. 예시·가상 생성·자동 유료 재시도·오류 시 이전 모델로 fallback하지 않는다.

OpenSpec root=null이므로 저장소 계약+Superpowers 구현/검토를 적용한다. 기존 isolated worktree를 사용한다. main/운영 변경과 실제 제공자 호출은 하지 않는다. 로컬 합성 QA25607만 쓰며 개인 개발 서버 전환은 검증 뒤 가능 여부를 별도로 기록한다. 기존 실행의 승인 수정만 아래에 한정한다. 서버 접속/키/실제 비공개 원문을 기록하지 않는다.

## 계약

질문은 POST `/api/v1/workspaces/{workspace_id}/question-briefings`, body exact object `{request_id:UUID4,question:nonblank<=1500}`. 기존 cookie·CSRF/same-origin·16,384 UTF8bytes·중복 key/NaN/비JSON/extra/query 거부·no-store·서버 X-Request-ID·경로 오류 고정문구/redirect 비공개 처리를 유지한다. 모델/원문/예약/부모AI맥락은 받지 않는다.

공유 packages/agents/question_submission.py의 Protocol QuestionExecutionService는 async start/aclose/authorize(token,workspace,request,question)->bool/run(...)->QuestionSubmissionResult다. authorize False는404이며 known QuestionSubmissionError(kind unauthorized|forbidden|conflict|budget|unavailable)만고정으로 전달한다. 실제 worker service는 현재 writer로 원래 plan을 먼저 고정(예약/AI0)하고 run_question_briefing을 호출한다. 프로토콜은 apps를 import하지 않는다. API는 worker 내부를 import하지 않고 명시 service 주입만 받는다. root scripts/question_briefing_app.py만 API/worker를 구성한다.

HTTP stream은 authorize 성공 뒤 시작한다. progress event data `{request_id,stage:'analysing'}`를 한 번, 10초마다 `: keepalive\n\n`, 마지막 result event data QuestionSubmissionResult(request_id,kind briefing|no_match|blocked,job_id UUID4|null)를 보낸다. briefing에만 job_id가 존재한다. error event data `{request_id,kind:<safe kind>}`는 고정 enum만. text/event-stream UTF8/no-store/X-Accel-Buffering:no이며 결과 없이 EOF이면 클라이언트는 실패다. request tracing ID와 애플리케이션 request_id를 혼동하지 않는다. 임의/변조 서비스 응답은 검증 후 unavailable로 정리한다. raw 예외/token/질문/DSN을 오류·로그에 넣지 않는다. 연결 종료/취소 시 해당 caller coroutine을 취소하고 await하며 DBOS에 넘긴 자식/최종 작업·예약은 자동 반환/재호출하지 않는다. 이미 접수된 durable 작업이 남을 수 있다. 같은 request_id로 명시 재시도한다.

새 domain/question_submission.py에 strict/frozen/extra-forbid 요청/result/progress/error·BriefingJobSummary(job_id,question,status)·BriefingJobList(items<=50) DTO를 둔다. 요청 validation은 실제str/UTF8/UUID4/extra 엄격. 상태는 기존6종만. GET `/api/v1/workspaces/{workspace_id}/briefing-jobs`는 현재 공유 권한으로 최대50개 metadata만 반환한다. 기존 BriefingJobRepository에 list_current(token,workspace)만 추가하고 같은 transaction의 현재 requester/original writer/모든 원문 검증을 거친다. 결과/인용/모델/비용은 목록에 넣지 않는다. job UUID 오름차순의 안정된 제한이며 최신순이라고 표시하지 않는다. canonical 결과 검증은 기존 상세 조회가 담당한다. 기존 private 공유 범위를 개인 소유/공개로 바꾸지 않는다.

새 runtime은 API loop와 분리된 소유 worker event-loop thread를 사용한다. caller만 run_coroutine_threadsafe/wrap_future로 연결한다. AsyncOpenAI·DBOS·실행·종료는 같은 worker loop에 속하며 원래 sync evidence SQL이 API loop를 막지 않게 한다. API engine은 owned lifetime의 공유 thread-safe Engine. 기존 research_worker_lock을 얻은 단일 executor만 사용하고 API/worker import는 root composition에서만 수행한다. 다른 DBOS singleton을 소유하거나 destroy하지 않는다(고정 SDK에서 read-only 존재 guard가 필요하면 좁게 검사하고 이유/한계를 기록). startup partial failure도 자신의 client/runtime/thread/lock만 정리한다.

기존 evidence register_evidence_workflow와 추출한 briefing의 pure registration을 DBOS.launch 전에 호출해 recovery 시 workflow 이름을 먼저 등록한다. briefing_queue.py는 기존 queue 설정과 workflow 등록 본문을 각각 configure_briefing_queue/register_briefing_workflow로 추출하고 기존 register_briefing_queue는 이 둘을 조합한다. 함수/step/workflow 이름·paid bytes·queue1/1/never_update·UUID/ownership guards는 그대로다. DBOS.launch와 OpenAI 생성은 worker loop에서; launch 뒤 queue설정 SQL은 to_thread. DBOS run_migrations=False, 별도 고정 기본schema issuedigest_question_briefing, 고정appversion question-briefing-http-v1. schema/앱DB migration은 자동 실행하지 않는다. private env만 명시로 읽고 secret discovery/logging 금지. migrations용 DBOS.migrate CLI는 문서의 수동 작업이며 여기서 remote 실행하지 않는다. configured runtime의 service_factory callback/lifespan만 추가하고 default configured factory는 명시 service없음으로 안전하게503. dev launcher의 명시 ISSUEDIGEST_QUESTION_BRIEFING_ENABLED=1인 configured 환경만 root factory/--all-packages로 선택한다. 기본 launcher/main 배포는 바꾸지 않는다.

shutdown은 새 caller를 막고 자신의 caller를 취소한다. worker loop를 유지한 채 DBOS.destroy를 to_thread로 최대70초 drain, 남은 자신의 loop tasks를 취소/gather, provider를 같은 loop에서 닫고 DBOSClient/lease를 정리한 뒤 loop/thread를 종료한다. engine dispose는 마지막이다. current intent/usage 보존과 자동 paid retry0을 유지한다. worker 프로세스가 끊긴 caller parent는 여전히 동일 요청으로 명시 재개하며 자격 증명을 DBOS journal에 저장하지 않는다.

UI는 기존 paper/ink/green tokens·BrandHeader·44px/keyboard/focus·두테마·모바일/reducedmotion을 유지한다. 로그인·guest question handoff는 현재 그대로. 로그인한 새 질문(`view=research`이고 legacy run param없음)은 새 QuestionComposer로 제출하고 즉시 aria-busy/role=status 표시, 최종 briefing job이면 `/workspaces/:workspaceId/briefings/:jobId`로 이동한다. no_match/blocked는 실제 상태의 짧은 설명만 보여준다. 공개 목록과 기존 legacy run URL/history 읽기는 유지한다. saved view에는 현재 SQL의 신규 briefing 목록을 함께 표시하며 링크에 ID를 이름으로 쓰지 않는다. 예시/가짜진행률/불필요한 로그인 문구/새 관리자 UI 금지.

클라이언트는 고정 same-origin cookie fetchPOST·기존 trace/error보안 규칙으로 bounded incremental SSE를 읽는다. body<=128KiB/event<=8KiB, fatalUTF8·CRLF/경계·잘못된schema/enum/UUID/extra·requestID다름·중복 terminal/terminal이후data/EOF무결과를 거부한다. heartbeat/comment만 idle을 갱신(20초idle/620초overall), AbortSignal/reader.cancel cleanup과 늦은 응답 staleguard. 자동 재호출0. sessionStorage에 actor+workspace별 원래 요청UUID/질문을 bounded validated 저장하여 새로고침 뒤 명시 재시도만 허용한다. 동일 질문 retry는 같은ID, 명시 다른 질문은 새UUID; 성공/권한상실/logout/actor변경 시 해당 pending 상태를 정리한다. body source나 키는 저장하지 않는다. parent legacy AI는 새 요청에 섞지 않는다.

## Task 1 — DTO·stream API·저장 목록

- [x] TDD 구현/태스크 검토.

새 domain/question_submission.py, agents/question_submission.py, api/question_submissions.py, api/tests/test_question_submissions_api.py, storage/tests/test_briefing_job_list.py. 승인 수정: BriefingJobRepository에 list_current만 추가(기존함수 AST 유지), api/main.py service 인수/router/no-store 경계·list endpoint 연결, api/contracts.py 새 DTO schema등록, 기존 api/briefing_jobs.py에 collection GET만 추가, 생성 OpenAPI/schema.d.ts. 기존 api/tests/test_contracts.py 정확 경로 집합3곳에 새 경로2개씩 추가만 허용한다. metadata 반환만인 목록은 모델/예약0을 증명한다. service없는 상태/세션·Origin/body/query오류·strictDTO·stream완료/heartbeat/error·클라이언트 disconnect cancellation·native권한/read list/source/writer손실·offloop·sanitized unknown·requestID/header/보호경로·추가예약/모델0·listcap/order/sharedscope를 검사한다. 기존 테스트/도메인/SDK를 약화하지 않는다. scopedRuff/format/mypy/OpenAPI+새 tests GREEN 후 owned파일만커밋·SDD보고. 서브에이전트 금지.

## Task 2 — 소유 worker host·root factory·실제 HTTP 통합

- [ ] TDD 구현/태스크 검토.

Task1 DTO/Protocol을 사용한다. 새 worker/question_service.py, scripts/question_briefing_app.py, worker/tests/test_question_service.py, api/tests/test_question_briefing_runtime.py. 승인 수정: worker/briefing_queue.py 등록 본문/설정 추출만(기존 step/workflow 본문 AST/이름/정책 유지); api/runtime.py optional service_factory callback/lifespan만, scripts/dev.mjs 명시 flag factory선택, scripts/dev.test.mjs 새 경우 추가(기존assertions 유지). 필요 시 mypy 설정에는 새 root script만 추가(기존 entry 유지)한다. 실제 native DBOS/MockSSE·ASGI stream→등록분석→final→기존HTTP read까지 증명하고 same request2concurrent/replay0increment를 확인한다. loop/thread/provider close 동일성·lease foreign singleton/기동실패정리·currentauthority/예산·신규secret환경 validation·미리migration되지않은schemafailclosed·startupworkflow등록순서·APIliveness responsiveness·shutdown intent를 검사한다. 테스트고유 qwh_UUID schema만 migrate/drop하고 user/default schema는 바꾸지 않는다. 기존 helper/provider/version bytes 변화0. scopedtests/mypy/format/Ruff·보고/owned커밋. 실제 provider/remote0. 서브에이전트 금지.

## Task 3 — 클라이언트·질문/기록 화면 연결

- [ ] TDD 구현/태스크 검토.

새 api-client/question-submissions.ts, web/question-composer.tsx, web/question-pending.ts, web/briefing-job-list.tsx, web/question-composer.css 및 새 client/화면 tests .test.tsx. 승인 수정: api-client/index.ts 새exports, web/routes/home.tsx 새질문/기록 컴포넌트 연결만. 기존 ResearchDesk·historical read·public·login·header·briefing reader는 수정하지 않는다. 기존 home/guest 테스트는 실제 변경된 신규질문 trigger를 새 endpoint로 맞추는 부분만 허용하고 기존auth/guest/legacyassertion을 삭제/약화하지 않는다. 기존 독립 ResearchDesk tests는 그대로다. strictSSEparser/auth/headers/idle/total/abort/stale/bodycap·후속EOF/UTF8·requestid mismatch·진짜새요청/같은retry·승인된guesthandoff·account/logoutscoping·loading/실제nav/no_match/blocked·old history/newSQLlist·에러후수동재시도·중복클릭0·XSS plaintext·서버metadataUI미노출을 검증한다. frontend-design skill을 적용하되 기존브랜드미감/문구절제를 우선한다. 기존 테스트를구현에맞춰약화하는 대신 실제UI동작을검사한다. 범위lint/type/test/build·보고/커밋. controller실제브라우저QA는 원래authfixture/mockSSE 응답으로 두테마/모바일/키보드 확인하고 제품에예시를넣지않는다. 서브에이전트 금지.

## Controller gates

- [ ] 태스크/전체 독립 검토·전체 체크·허용diff/oldAST·privacy.
- [ ] 실제 브라우저·7문서·Draft PR·Sites·전용 QA 정리. server/main 반영 여부 별도 명시.
