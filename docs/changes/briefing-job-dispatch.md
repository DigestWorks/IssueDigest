# 최종 브리핑 실행 큐 연결

2026-10-26 KST. [브리핑 접수·저장](durable-briefing-jobs.md)의 후속이다. 현재 생성·저장 기능을 명시 실행할 수 있으나, 접수한 최종 작업을 DBOS에 전달하는 연결이 없다. 이 단계는 그 연결만 구현하며 질문 API·화면·개발 서버 반영 완료로 표시하지 않는다.

## Global Constraints

- 새 실행 파일4개만 추가: packages/agents/src/issuedigest_agents/briefing_dispatch.py, packages/agents/tests/test_briefing_dispatch.py, apps/worker/src/issuedigest_worker/briefing_queue.py, apps/worker/tests/test_briefing_queue.py. 기존 실행 파일·fixtures·exports·의존성·설정·migration·모델/지침/SDK·API/UI·기본 worker는 변경하지 않는다. 문서 변경은 허용한다. 운영/개발 서버·실제 제공자·main 변경은 없다.
- 새 dispatch는 이미 깊이 검증해 접수한 최종 작업만 전달한다. 비용 예약·접수·생성·현재 권한을 우회하거나 재구현하지 않는다. 반환은 queue acknowledgement이며 브리핑이나 의미 검증 결과가 아니다.
- 근거 분석과 최종 생성은 같은 DBOS queue `issuedigest_guarded_evidence_v1`의 global_concurrency=1/worker_concurrency=1을 사용한다. 별도 유료 lane을 만들지 않는다. 서로 다른 workflow 이름을 사용하고, 활성화 단계에는 같은 app_version의 worker에 두 workflow를 함께 등록해야 한다. 이번에는 등록 함수만 추가한다.
- 모든 SQL은 async 호출 안에서 asyncio.to_thread로 수행한다. client는 caller가 소유하며 생성/종료하지 않는다. 토큰·질문·원문·receipt·usage는 queue 인수/옵션/로그/ack에 넣지 않는다. DBOS에는 canonical UUID4 job 문자열 하나만 전달한다.

## Task 1: dispatch와 명시 workflow 등록

- [x] 구현·TDD·태스크 검토.

허용 파일은 packages/agents/src/issuedigest_agents/briefing_dispatch.py, packages/agents/tests/test_briefing_dispatch.py, apps/worker/src/issuedigest_worker/briefing_queue.py, apps/worker/tests/test_briefing_queue.py 네 개다. 기존 실행 코드·테스트·fixture·exports·의존성·설정·migration·API/UI를 수정하지 않는다.

신규 agents 모듈에 frozen `BriefingDispatch(job_id, workflow_id, status, queued)`와 `BriefingDispatchError(job_id, workflow_id)`를 정의한다. async `enqueue_briefing_job(repository, *, client:DBOSClient, app_version:str, token:str, workspace_id:UUID, job_id:UUID)->BriefingDispatch|None`는 app_version을 exact str / ASCII `[A-Za-z0-9._-]{1,128}`, 두 ID를 exact UUID4로 SQL 전에 확인한다. repository.get(token,workspace_id,job_id)을 offloop 호출해 현재 권한/원문/작업 상태를 재검사한다. None은 enqueue 없이 None, pending 이외 상태는 queuedFalse 상태 ack만 반환한다. pending은 enqueue 직전에 같은 get을 한 번 더 수행하고 같은 ID/workspace의 현재 DTO인지 확인한다. 마지막 get 이후 cancellation/권한 변경은 worker가 다시 검사하며 ack는 실행 성공을 의미하지 않는다.

DBOS enqueue_async options는 정확 workflow_name=`issuedigest_question_briefing_job_v1`, queue_name=`issuedigest_guarded_evidence_v1`, workflow_id=`question-briefing-<job UUID>`, app_version=명시 버전, workflow_id_reuse_policy=`return-existing`이다. argument는 str(job_id) 하나다. enqueue의 일반 예외는 원문/context 없는 고정 BriefingDispatchError로 바꾸며 job/workflow ID만 보존한다. 취소는 원래 취소를 전파한다. 접수된 작업·예약을 취소/환불/자동 재전송하지 않는다. 같은 job_id로 명시 재전달할 수 있다. 외부 enqueue의 모호한 ack 뒤에는 같은 workflow ID를 재사용한다.

신규 worker 모듈에 frozen `RegisteredBriefingQueue(workflow,queue)` 및 `register_briefing_queue(repository, *, client:AsyncOpenAI, check_ownership:Ownership)`를 둔다. caller가 DBOS를 구성/launch한 뒤 event loop 밖에서 명시 호출한다. shared queue를 on_conflict="never_update"로 register하고 공개 queue limits가1/1인지 검사하며 충돌 시 workflow를 등록하지 않는다. 새 step `issuedigest_question_briefing_call_v1`는 retries_allowed=False이며 기존 execute_briefing_job을 호출하고 결과를 DBOS journal에 반환하지 않는다. workflow `issuedigest_question_briefing_job_v1`는 인수가 exact str인 canonical UUID4이며 DBOS.workflow_id가 `question-briefing-`+같은 문자열인지 확인한 뒤 기존 ownership 확인·step·검증된 completed read를 수행하고 None을 반환한다. malformed/non-v4/noncanonical/wrongworkflow ID는 SQL/provider 전 거절한다. ownership 예외는 기존 fixed sanitization 규칙을 재사용한다. import/config/launch/client 생성·기본 worker 연결·자동 recover/retry는 하지 않는다. running 작업의 중단 여부는 추정하지 않으며 기존 explicit recover 경계를 유지한다.

검사: 실제 전용 SQL에서 pending 동일 ID 재전달/terminal skip/current auth·원문 변경/invalid IDs-version SQL 전 거절/SQL offloop/queue ack loss·고정 비밀값 비노출/native cancellation. worker는 실제 DBOS+AsyncOpenAI MockTransport SSE로 접수된 한 작업을 queue에서 완료하고 동일 ID 재전달/ack loss/완료 재열람에서 provider1회·추가 예약0·borrowed client 유지·shared queue1/1을 확인한다. 등록/잘못된 workflow identity·ownership 거절·충돌 config 실패도 검사한다. DBOS는 unique `qbf_<UUID>` schema를 migrate/config/client에 동일 지정하며, 모든 runtime/client 종료 후 자신이 만든 schema만 DropSchema한다. 다른 DBOS schema/queue configuration을 바꾸지 않는다. 기존 test fixtures를 바꾸지 않고 자체 새 fixture에서 import/sys.path/package attributes를 복원하며 final/evidence/plan 테이블을 전후 정리한다. 기존 worker test의 유효 seed/native mock body를 참고할 수 있으나 production provider를 mock generation object로 대체하지 않는다. scoped Ruff/format/mypy, RED→GREEN 보고·커밋. 서브에이전트 생성 금지.

## Controller gates

- [x] 독립 태스크/전체 검토·전체 검사·기존 실행 byte 보존·privacy.
- [x] 기록·Draft PR118·Sitesv140·전용 QA 정리. API/화면/서버는 후속.
