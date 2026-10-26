# 질문별 순차 AI 작업 연결 검증

2026-10-26 KST. [명세](../changes/question-plan-dispatch.md). 고정한 질문별 선택을 기존 영속 분석 작업으로 접수하는 신뢰 서버용 경계다. 자동 부모 workflow·브리핑 변환·API/UI·개발 적용은 이번 범위가 아니다. 실제 제공자 호출·운영 서버/DB 변경·main/앱/기본 worker 활성화0이다.

## 구현 계약

`advance_question_plan`은 기존 질문 계획을 현재 작성자의 동일 요청으로 재검증한다. 선택한 자료마다 고정 namespace/plan/source/order로 자식 UUID4를 유도하고 예약 전에 기대 원문 hash를 DB transaction 안에서 비교한다. 현재 원문이 다르면 예약·작업 저장 없이 거부한다. 기존 자료별 작업과 현재 권한·원문 검증을 재사용한다.

완료한 자식은 재사용하고 첫 미완료에 도달하면 반환한다. pending은 기존 queue dispatch를 사용하고 running은 기다리는 상태만 반환하며 failed/cancelled/indeterminate는 이후 자료를 접수하지 않는다. 응답은 ID/상태/개수/queue ack만 담는다. `evidence_complete`는 분석 작업 완료이며 브리핑 완성·사실 인증이 아니다. no_match는 모델·예약·queue를 만들지 않는다.

상위 caller가 완료 후 같은 요청을 다시 호출해야 진행한다. 일부 자료만 접수한 상태에서 중단될 수 있으며 이미 예약·접수한 작업을 되돌리거나 몰래 재실행하지 않는다. 동시 요청은 같은 자식과 기존 활성1개/합산 예산 제약을 사용한다. 원문이 바뀌었을 때 새 자료로 자동 대체하지 않는다.

자식 요청 ID 유도 profile은 고정한다: UTF-8 `issuedigest:question-plan-child:v1|{소문자 하이픈 plan UUID}|{소문자 하이픈 snapshot UUID}|{0부터 시작하는 십진수 순서}`의 SHA256 첫16바이트에 UUID version4/표준 variant bit를 설정한다. 이는 비밀값/인증 token이 아닌 멱등성 키다. 이후 변경은 원래 요청의 복구를 깨므로 새 profile과 명시 이행이 필요하다.

## 검증

집중 검사91개와 Ruff/format/mypy가 통과했다. 실제 DBOSClient·등록한 합성 queue·기존 worker·native 모의 SSE로 두 자료의 완료/재접수와 예약2개/모의 HTTP2회를 확인했다. 실제 호출 횟수가 아닌 차단된 모의 요청 수다. 실행df8cd6f/테스트 격리 보완6c6f65b·새 전체9,716개(Python8,896+JS820)·Ruff/format/mypy·타입/빌드/OpenAPI 통과, 실패/skip/warning0이다. 태스크/전체 검토 C0I0M0 후 자체QA에서 발견한 테스트 격리 문제1개를 고쳤고 수정 재검토도 C0I0M0다. 새 테스트→기존 queue검사6개 및 역순1개가 통과했으며 최종 전체 검사는 새 전용 DB에서 다시 실행했다. 처음 실패한 전체 실행은 통과로 세지 않았다. 합성 원문과 전용 PostgreSQL/native DBOS/모의 SSE만 사용하며 실제 제공자 응답·비용·의미 품질을 추정하지 않는다.

## 판단과 비용

1. 자료별 순차 진행으로 기존 활성 작업1개 계약을 유지한다. 자동 연속 실행은 상위 orchestration 후속이며 실패한 자료를 건너뛰지 않는다.
2. 결정적인 자식 UUID4를 사용한다. 새batchtable은 필요 없지만 이 유도 알고리즘/namespace를 바꾸면 복구 계약이 깨진다.
3. 기존 예약 저장에 선택적 expected-source guard를 넣는다. 원문 변경 경쟁을 막지만 저장 코드/검사 각1파일을 수정한다. 나머지 기존488실행파일과 이전43증거는 보존한다.

첫 전체 실행은 기존 queue 검사3개 실패/8,893개 통과로 종료해 통과로 세지 않았다. 원인은 새 native 테스트가 기본 dbos.queues에 다른 앱 이름으로 같은 고정 queue를 남긴 테스트 간섭이었다. 새 테스트만 고유 qpd_<UUID> schema를 사용하고 종료 후 정리하며, 기본 schema/queue 불변을 검사하도록 보완했다. 앱 실행 코드는 변경하지 않았다. 신선한 전용 DB에서 전체 검사를 다시 수행한다.

4. 테스트 전용 DBOS schema를 격리했다. 기존 queue와의 충돌을 막는 대신 테스트 준비/정리와 전체 재검사 비용이 늘었다.
