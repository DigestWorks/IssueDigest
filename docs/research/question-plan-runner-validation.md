# 질문별 자동 분석·검증 결과 수집

2026-10-26 KST. [명세](../changes/question-plan-runner.md). 기존 순차 접수에서 첫 미완료 작업의 native 완료를 기다린 뒤 같은 요청으로 다음 자료를 진행하는 내부 실행기다. 독립 부모 workflow·브리핑 합성/저장/API/UI·개발 적용은 이번 범위가 아니다. 실제 제공자 호출·운영 서버/DB 변경·main/앱/기본 worker 활성화0이다.

## 구현 계약

`run_question_plan`은 기존 `advance_question_plan`과 DBOS handle을 사용한다. 원래 요청과 자식 ID·모델/예약 정책을 그대로 사용하고 완료 상태는 DBOS 응답 본문이 아닌 현재 저장소에서 다시 검증한다. 첫 실패를 건너뛰거나 유료 재시도하지 않는다. 진행 상태/개수/ID가 맞지 않거나 완료 prefix가 늘지 않으면 중단한다.

전체 대기는 최대600초, 기다릴 작업 수는 선택한 자료 수 이하다. caller 취소/timeout은 이미 접수한 원격 작업을 취소하거나 예약을 환불하지 않는다. coroutine/process가 중단되면 같은 명시 요청으로 재개하며, 토큰을 영속화하거나 독립 부모 복구를 주장하지 않는다.

모든 자료가 완료된 경우 현재 writer 계획과 원문, 각 완료 job과 canonical 영수증·prompt/instructions/usage를 다시 검증한다. 모든 검증이 성공한 뒤 순서대로 수집하며 중간 실패·권한 상실 때 부분 영수증을 반환하지 않는다. AI status는 unreviewed이며 브리핑·확인된 사실·사람 검토로 승격하지 않는다. 수집 callback은 현재 사용자의 읽기 권한 확인이며 worker lease를 부여하지 않는다.

## 검증

모듈 부재 RED 후 신규73개와 기존 queue5개를 합친 집중78개·Ruff/format/strict mypy가 통과했다. 실제 DBOSClient/기존 worker/모의 SSE로 한 실행의 두 자료 완료·동시 동일 요청·완료 재열람과 예약2개/차단된 native요청2회를 확인했다. 다섯 자료에서는 정확5대기/6진행이며 SQL의 eventloop 밖 실행을 확인했다. 실행dca3341·새 전체9,789개(Python8,969+JS820)·Ruff/format/mypy·타입/빌드/OpenAPI 통과, 실패/skip/warning0이다. 태스크/전체 독립 검토 C0I0M0이며 미해결 지적은 없다. 신선한 전용 DB의 전체 실행에서 테스트 격리/metadata 보존도 통과했고 실행 파일은 시작 이후 바꾸지 않았다. 전용 합성 PostgreSQL·nativeDBOS·모의 SSE만 사용한다. 새 통합 검사는 고유 qpr_<UUID> schema를 사용하고 종료 후 정리하며 기본 DBOS metadata/queue를 유지한다.

## 판단과 비용

1. 하나의 coroutine에서 자동 진행한다. 토큰 영속화는 없지만 프로세스 중단 뒤에는 같은 요청으로 재실행해야 한다.
2. 전체600초/자료 수 이하 대기로 제한한다. 정체 루프를 막지만 timeout 뒤 이미 접수한 작업을 다시 확인해야 한다.
3. 모든 완료 영수증을 현재 권한/원문으로 재검증한다. 추가 AI 비용은 없지만 SQL 검사 비용이 있고 브리핑 합성·의미 인수는 별도다.
