# 영속 근거 작업의 접수·DBOS queue 연결

2026-10-26 KST. [저장·복구 worker](durable-evidence-worker.md) 다음 단계다. 지금은 workflow를 명시 시작할 수 있지만 서버의 작업 접수와 queue 전달이 연결되지 않았다. 이 변경은 재사용 가능한 신뢰 서버용 dispatch와 별도 worker queue 등록을 만든다. 브라우저에 snapshot 선택/ID 입력을 요구하는 API를 만들지 않으며 D019 질문 전용 검색·브리핑 변환/표시는 다음 경계다.

## Global Constraints

- 신규4파일만 실행 변경: `packages/agents/src/issuedigest_agents/evidence_dispatch.py`, `packages/agents/tests/test_evidence_dispatch.py`, `apps/worker/src/issuedigest_worker/evidence_queue.py`, `apps/worker/tests/test_evidence_queue.py`. 기존481 실행 파일·이전 증거·DB migration/모델/SDK/registry/기본 worker/API/UI/의존성/설정/exports는 그대로 둔다. 문서 변경 허용. 실제 제공자 호출·운영 서버/DB·main 병합/앱 활성화0.
- 신뢰 서버 전용 async `submit_evidence_job(repository, *, client, app_version, token, workspace_id, request_id, snapshot_id, question, model, reservation_usd)`를 agents 모듈에 둔다. required borrowed `DBOSClient`, required exact nonblank app_version(ASCII letters/digits/._-, length1..128), 기존 EvidenceJobRepository를 사용한다. caller가 실제 접근 가능한 검색에서 선택한 snapshot만 전달하며 브라우저 endpoint/직접 source 선택 기능은 추가하지 않는다. 기존 repository의 정확 UUID4/질문/gpt-6.1-sol/Decimal·권한·source·멱등성·공유 예산 계약을 우회하지 않는다. DB 호출은 asyncio.to_thread로 event loop 밖에서 실행한다.
- 작업을 먼저 repository.submit으로 커밋한다. None이면 enqueue 없이 None. 새/기존 pending만 현재 token/workspace/source를 get으로 재확인한 뒤 enqueue한다. 현재 상태가 pending이 아니면 enqueue 없이 상태만 반환한다. 완료 receipt/질문/원문/사용량/자격 증명은 dispatch 반환에 포함하지 않는다. 반환은 frozen dataclass `EvidenceDispatch(job_id, workflow_id, status, queued)`이며 queued는 DBOS ack만 의미하고 AI 완료/실제 송신 보장이 아니다.
- DBOS enqueue_async는 정확 workflow_name `issuedigest_guarded_evidence_job_v1`, queue_name `issuedigest_guarded_evidence_v1`, workflow_id `guarded-evidence-<job UUID4>`, required app_version, workflow_id_reuse_policy `return-existing`, args는 canonical job UUID 문자열 하나만 전달한다. 질문/token/source/receipt/키는 queue payload/options/log에 넣지 않는다. client 생성/파괴·환경 접근·sync model bridge·자동 재시도·실제 provider 호출은 없다. 같은 요청의 사용자/서버 재시도는 같은 저장 job/DBOS ID를 사용하며 중복 예약/모델 실행을 만들지 않는다.
- SQL commit 후 enqueue 실패/ack loss는 작업을 failed/free로 바꾸지 않는다. 고정 메시지의 `EvidenceDispatchError`에 job_id/workflow_id만 남기고 원래 예외/비밀 정보를 반환하지 않는다. CancelledError는 전파하며 이미 저장된 예약/작업을 지우거나 재발행하지 않는다. 토큰/권한/source 거부도 sanitize·기존 예외 계약대로 보존한다. enqueue 재시도 loop는0이며 호출자가 같은 request로 재시도할 수 있다. 취소/권한 변경이 재확인 이후 발생해 queue에 들어가도 기존 worker가 현재 권한/상태를 다시 검사해 모델 호출을 막는다.
- 신규 worker의 explicit `register_evidence_queue(repository, *, client, check_ownership)`만 호출할 때 설치된 public DBOS.register_queue로 Queue `issuedigest_guarded_evidence_v1`을 global_concurrency=1/worker_concurrency=1로 등록하고 기존 register_evidence_workflow를 재사용한다. 반환된 실효 동시성1/1도 확인하고 다른 설정이면 실패한다. 명시 등록은 해당 전용 queue 설정을 DB에 저장하며 import는 쓰지 않는다. 반환 frozen `RegisteredEvidenceQueue(workflow, queue)` (정확 타입은 설치된 DBOS에 맞춤). import는 등록/DB/네트워크/실행을 하지 않는다. 설치된 SDK는 DBOS가 먼저 launch돼야 register_queue를 지원한다. caller가 구성·migration·명시 app_version·launch를 완료한 뒤 이 동기 factory를 event loop 밖에서 부른다. factory가 엔진을 시작하지 않으며 client lifecycle도 caller 소유. 기존 queue/workflow는 소비/수정하지 않는다.
- 테스트는 전용 합성 PostgreSQL·실제 DBOSClient/DBOS queue·native AsyncOpenAI MockTransport SSE를 사용한다. 기존 test_evidence_worker/helper는 읽기/재사용하되 수정하지 않는다. new table 정리와 SDK/Pydantic module+package attrs 격리를 자체 fixture로 보존한다. RED missing modules 후 최소 구현; 실제 SQL idempotency와 DBOS enqueue ack loss·재시도/중복 요청→HTTP1·예약1 검증. SDK 모델 완료 receipt는 unreviewed이며 dispatch가 Canvas/사실 인증으로 바꾸지 않는다. fullQA는 controller.

## Task 1: 접수와 queue의 명시 연결

- [ ] 네 파일 TDD. 입력 app_version 검증은 SQL/queue 이전, submit None/권한/예산/source 실패 enqueue0, 저장 먼저/queue payload UUID만, pending재시도/terminal무enqueue, enqueue 실패와 실제 commit-then-raise ack loss 재접수, cancellation, borrowed client 보존/import 무작업. 실제 DBOS queue를 등록/launch하고 두 접수를 같은 workflow ID로 보내 native SSE HTTP1/공통예약1/완료 unreviewed·기존 completed replay 무enqueue를 확인한다. queue 오류에 질문/토큰/예외 원문 노출0. 신규파일 Ruff/format/mypy와 집중 테스트 후 owned files+이 체크박스만 commit, 보고서에 정확 RED/GREEN/인터페이스/한계/스스로 검토 기록. Subagent 추가 금지.

## Controller gates

- [ ] 독립 태스크/전체 검토·전체 검사·과거 실행/증거 보존·privacy·문서/PR/Sites·자체QA 정리.
- [ ] 질문 전용 검색→다자료 근거→브리핑 변환/표시와 운영 예약/부하·개발 적용 인수. 이번 활성화 없음.

## 판단과 영향

1. 먼저 신뢰 서버의 저장→queue 경계를 연결한다. 기존 앱 계약을 보존하지만 질문 전용 검색·브리핑 UI는 이번 완료 범위가 아니다.
2. SQL 저장 뒤 queue ack가 불명확하면 같은 ID 재접수만 허용한다. 중복 모델 실행을 막지만 아직 queue에 안 들어간 pending도 예약을 유지한다.
3. app_version 명시와 별도 단일 동시 queue를 사용한다. 예측 가능한 routing을 얻지만 운영자는 같은 version/queue의 worker를 준비해야 하며 처리량 인수가 남는다.
