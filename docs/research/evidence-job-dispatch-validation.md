# 근거 작업 접수·DBOS queue 연결 검증

2026-10-26 KST. [명세](../changes/evidence-job-dispatch.md)의 신뢰 서버용 저장→queue 연결이다. 실제 브라우저/API 활성화나 모델 의미 품질의 인수가 아니다. 실제 제공자 호출·운영 서버/DB 변경은 0회다.

## 구현

`submit_evidence_job`은 기존 repository에 작업을 먼저 커밋한다. pending은 현재 세션·권한·원문을 다시 검사한 뒤 명시한 app_version과 고정 queue/workflow ID로 전달한다. queue payload는 작업 UUID 문자열 하나이며 질문·token·원문·receipt는 포함하지 않는다. 접수 응답에는 작업 ID/상태/queue ack만 포함하며 AI 완료를 뜻하지 않는다.

같은 요청을 다시 접수하면 저장된 작업과 workflow ID를 재사용한다. SQL 저장 뒤 enqueue 응답을 받지 못해도 원래 예약을 반환하거나 새 요청으로 바꾸지 않는다. 고정 오류에 작업 ID를 남기므로 caller가 같은 request로 재접수할 수 있다. SQL thread가 caller 취소 뒤 커밋해도 몰래 enqueue하지 않는다. 실제 실행 시 권한·source·작업 상태 검증은 기존 worker가 다시 수행한다.

설치된 DBOS3.2.0은 Queue 직접 생성을 거부한다. caller가 DBOS를 구성·migrate·명시 버전으로 launch한 뒤 동기 `register_evidence_queue`를 event loop 밖에서 호출한다. 이 명시 호출은 전용 queue 설정을 저장하고 반환된 실효 동시성1/1을 확인하며, 설정 불일치는 workflow 등록 전에 실패한다. import는 queue 등록이나 엔진 시작을 하지 않는다. client lifecycle은 caller 소유다.

## 검증

전용 합성 PostgreSQL과 실제 DBOSClient/queue·native AsyncOpenAI/모의 SSE를 사용했다. 모듈 부재 RED13건과 실효 queue 설정 불일치의 미차단 RED를 확인한 뒤 구현했다. 신규 집중 검사23개·Ruff/format4파일·mypy2소스가 통과했다. 전체 검사와 독립 검토 결과는 완료 후 반영한다.

- app_version 형식 검사는 SQL/queue보다 앞선다. 원래 repository의 UUID/질문/모델/Decimal·권한·source·합산 예산 계약을 유지한다.
- None/권한·source·예산 실패, 현재 pending 재조회 거부, terminal 상태는 enqueue하지 않는다.
- 실제 DBOS enqueue 커밋 후 응답 유실을 재현해 같은 요청을 재접수했다. 모의 HTTP1회·예약1회·동일 workflow ID와 완료 unreviewed receipt를 확인했다.
- enqueue 오류/취소와 SQL thread 중 취소 후 늦은 커밋에서도 예약/작업을 유지하고 숨은 enqueue·자동 재시도는 없다. 오류에 원래 예외·질문·token을 담지 않는다.
- 신규 fixture가 전용 작업 테이블을 정리하고 SDK/Pydantic module과 package 속성을 복원한다. 기존 실행 파일은 바꾸지 않는다.

## 한계·후속

질문 전용 검색에서 자료를 찾는 경로·다자료 실행·브리핑 변환/표시·개발 서버 적용은 아직 연결하지 않았다. 이 함수의 snapshot은 신뢰 서버에서 결정한 값이며 브라우저가 직접 고르는 API를 만들지 않는다. queue ack는 모델 송신/완료·실제 제공자 비용이나 의미 품질을 보장하지 않는다. caller는 queue와 일치하는 엔진/버전을 준비해야 한다.

## 선택과 영향

1. 기존 API/UI를 바꾸기 전에 신뢰 서버 저장→queue 경계를 연결한다. 이전 계약을 보존하지만 질문 전용 검색·브리핑 표시는 후속이다.
2. ack가 불분명하면 같은 ID 재접수만 허용한다. 중복 예약/AI 실행을 막지만 아직 송신되지 않은 pending도 예약을 유지할 수 있다.
3. 명시 버전과 별도 단일 동시 queue를 사용한다. 암묵적 최신 버전 routing을 피하지만 일치하는 worker 준비와 처리량 인수가 필요하다.
