# 질문 분석→최종 브리핑 실행 연결

2026-10-26. 기존 질문별 자료 계획·순차 분석·최종 브리핑 접수/queue와 읽기 API를 잇기 위한 caller-lived 실행 연결부다. 이번 작업은 worker 코어이며 기존 HTTP 질문 버튼·런타임·서버를 전환하지 않는다. 원본 데이터/권한·모델 의미 품질·main/운영 반영은 별도다.

## 계약

새 apps/worker/src/issuedigest_worker/question_briefing_runner.py에 frozen dataclass QuestionBriefingRun(evidence:QuestionDispatch, briefing:BriefingDispatch|None)와 async run_question_briefing(plans, evidence_jobs, briefing_jobs, *, client, app_version, token, workspace_id, request_id, question, model, evidence_reservation_usd, briefing_reservation_usd, total_timeout_seconds=600)를 만든다. 사용자 질문·원래 request UUID를 수정/재선택하지 않고 기존 run_question_plan→submit_briefing_job→enqueue_briefing_job만 조합한다. 반환은 실행 접수 확인이며 최종 생성 결과/의미 인증이 아니다. 결과는 기존 조회 API에서 현재 권한과 영수증을 재검증해 읽는다.

plans/evidence_jobs/briefing_jobs는 각각 실제 concrete repository이고 engine identity가 모두 같아야 하며 모든 사전 검증은 분석 접수보다 먼저 끝난다. 전체 timeout은 정수1..600초, appversion은 기존 regex1..128, UUID4 workspace/request, token은 valid_session_token, question nonblank1..1500, model은 정확 gpt-6.1-sol, 예약 두 값은 실제 Decimal/finite/(0,10]/센트 단위다. 모두 어떤 SQL/분석/queue보다 먼저 검사한다. 입력은 server-owned 연결 계약이며 브라우저에 예약/모델/원문 선택을 맡기지 않는다. caller가 소유한 DBOS client를 생성/종료하지 않는다.

asyncio.timeout 하나가 분석/최종 접수/queue 전체를 감싼다. 같은 timeout으로 기존 run_question_plan을 실행한다. None이면 None, no_match/blocked면 briefingNone으로 반환하고 최종 접수/queue0이다. QuestionEvidenceRun exact type/vars·QuestionDispatch._dispatch·receipt tuple/type/count를 검증한다. evidence_complete의 ordered completed child IDs/planID로 submit_briefing_job을 호출하며 finalrequestID는 원래requestID다. SDK·현재 원문·작성자·중복/비용 검증은 기존 submit helper가 다시 수행한다. None이면 None. 반환 BriefingJob exacttype/rawfieldshape·UUID·workspace/request/plan/children/question/model 일치를 검사한 뒤 enqueue helper에 전달한다. ack exacttype/vars·jobID/workflowID·statusenum·queued bool관계를 검사한다. None이면 None. 이미 completed/terminal은 큐 재접수하지 않는 기존 helper 계약을 유지한다. token/workspace/source가 중간에 바뀌면 기존 권한 오류를 그대로 전파하며 최종 결과/부분 원문은 반환하지 않는다.

모든 SQL은 기존 helper의 to_thread 경로만 사용한다. 기존 run_question_plan/submit/enqueue의 알려진 안전 오류·TimeoutError·CancelledError는 보존한다. 새 raw/위조 반환 검증은 fixed QuestionBriefingRunError만 반환하며 raw exception/token/질문/DSN을 넣지 않는다. 기존 helper에서 임의 예외가 오면 고정 error로 정리하되 cause/context 원문을 남기지 않는다. 예외 종류는 기존 sanitized auth/storage/budget/queue/QuestionRunError/GuardedResponsesError만 보존한다. outer TimeoutError는 그대로다. 취소/timeout/SQL to_thread 중단 뒤에도 원래 접수/예약은 남으며 보이지 않는 enqueue·다음 child·자동 refund/retry를 만들지 않는다. 독립 parent workflow·token 저장·자동 프로세스 복구는 만들지 않는다.

## Task 1

- [x] 신규 runner와 apps/worker/tests/test_question_briefing_runner.py 두 파일만 TDD 구현한다. 기존 실행/테스트/fixture/exports/provider/모델/version/slot/실제 데이터는 수정하지 않는다.

단계 호출 순서/값/같은 requestID·현재 계획/child순서·no_match/blocked/None·위조rawtypes/status/receipt count·최종값 변조·동시 동일요청·완료 재접수/재열람·queue ACK 불명확·분석/최종예약거부·현재 권한/원문변경·timeout/cancel 각 경계/nohiddencontinuation·borrowedclient/원문예외정리·offloop를 검사한다. 전용 합성 SQL25605와 native DBOS/기존 registered evidence+briefing queue·MockSSE에서 한 run_question_briefing이 자료 분석→최종 생성 접수까지 진행하고, 완료 후 기존 read_completed_briefing_job으로 canonical receipt를 읽으며 같은 요청 재실행의 provider호출/예약 증가0을 확인한다. native고유 qbr_UUID schema를 쓰고 자신 client/runtime/provider를 종료한 후 자신의 schema만 삭제한다. 자기 테스트 module/packageattrs/sys.path를 복원한다. 기존 helper를 테스트용으로 약화/바꾸지 않는다. native path가 기존 fixture출력의 검색질문/관계상태와 다르면 합성fixture만 올바르게 구성한다.

Ruff/format/mypy 및 신규+기존 questionrunner/briefingworker/queue 집중 검사를 수행한다. 보고서는 .superpowers/sdd/question-briefing-runner/task-1-report.md에 RED/GREEN/명령/인터페이스/한계를 기록하고 신규2파일+체크박스만 커밋한다. 서브에이전트 생성 금지.

## Controller gates

- [ ] 독립 태스크/전체 검토·전체 검사·계약·oldbytes/이전증거·privacy.
- [ ] 진행문서·Draft PR·Sites·전용 QA 정리. HTTP 질문 버튼/서버 전환은 별도.
