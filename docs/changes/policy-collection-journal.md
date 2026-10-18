# 정책뉴스 반복 확보·실행 이력

2026-10-18. M2의 다음 구현으로, 명시된 공식 기사1~2개를 다시 확보하고 PostgreSQL에 실행·성공 원본·변경 비교·실패를 남긴다. 기존 D021/R2/R6·[변경 비교](policy-change-detection.md)를 재사용한다. OpenSpec root=null, 초기화하지 않는다. 최종 제품의 내부 수집 기반이며 사용자에게 운영/자료 관리 화면을 추가하지 않는다.

## Global Constraints

- 고정 공식 `capture_policy`·`serialize_policy_capture`·`compare_policy_captures`를 재사용한다. private job에 명시된9자리 ASCII news_id1~2개만 확보하며 다른 URL/도메인·목록 추적·자동 후보 선택을 추가하지 않는다. 기존 HTTP20초/2MiB·TLS검증·redirect/proxy/env인증/cookie/retry 금지와 로그 비노출을 유지한다. 소수 고정 기사의 재확보를 최신 이슈 전면 수집으로 부르지 않는다.
- 기록은 기존 PostgreSQL에 분리된 내부 두 테이블로 저장한다. raw capture는 검증된 원본일 뿐 EvidenceBundle/검색 색인/브리핑/공개 게시가 아니다. 기존 원문·인용·사용자/세션·공개v1·v2/v3/v4 유료 실행/복구·DBOS metadata·웹/API/OpenAPI와 모델/의존성은 보존한다. startup/import/공개GET/로그인 복원은 네트워크·DB 초기화·수집을 실행하지 않는다.
- 운영자 job은 소유400/600 절대 경로 private 파일·최대8KiB·엄격 UTF8/중복JSON/비유한/추가필드/불리언 정수 거부를 지킨다. 필드는 schema_version=1, expected_database, collection_id(UUID4), news_ids, minimum_interval_seconds(60..86400), max_age_seconds(최소 interval..604800), max_attempts(1..4096)다. news_ids는 중복 없이 정렬해 collection_id에 불변 결합한다. DB명을 URL과 실제 current_database 모두에서 대조한다. 같은 ID에 다른 설정을 덮지 않는다.
- 각 poll은 nonblocking PostgreSQL session advisory lock `(104704, 2)`를 전용 연결에서 보유하며 DB/동일backend/잠금 소유를 쓰기 전에 확인한다. 잠금은 연구 worker와 별도다. 중복·최소 간격·횟수 상한 거부는 HTTP/새 attempt를 만들지 않는다. 상태 조회는 read-only 일관된 transaction으로 최신 attempt와 마지막 성공을 분리하고 행/모델/HTTP를 만들지 않는다.
- poll은 running을 먼저 commit한 뒤 HTTP를 호출한다. 성공은 정확 capture/report bytes·SHA256·시각·비교 요약과 함께 원자적으로 terminal 저장한다. 실패는 고정 stage enum만 기록하고 마지막 성공은 보존한다. 강제 종료의 running은 다음 잠금 획득 시 interrupted로 마감한다. 불명확한 commit은 재시도/실패 덮어쓰기를 하지 않으며 다음 명시 실행에서 실제 상태를 읽는다. 완료 행·원본을 덮거나 지우지 않는다.
- 원본 최대8MiB+16,384, 비교 보고서 최대64KiB이며 출력/예외/log에 원문·URL/query·기사/collection/attempt ID·계정·경로·DSN을 노출하지 않는다. CLI stdout은 집계·상태·시각·stale만, 실패는 고정 오류다. 직전 실패/미완료를 성공으로 표시하거나 미관측을 삭제/철회로 판정하지 않는다. stale은 마지막 성공 확보 완료 시각(finished_at) 기준이며 SDK의 요청 시작 수집 시각(collected_at)은 정확 원본에 별도로 보존한다. 실제 완료 시각을 앞당겨 기록하지 않는다. stale은 발행일/내용 최신성·수집 범위 완전성과 구분한다.
- 하위 구현자는 subagent/reviewer를 만들지 않고 실제 서버·키·DB·네트워크를 다루지 않는다. 전용 합성 PostgreSQL만 사용한다. main/운영 병합은 D013 유예다. controller가 실제 인수·권한 범위 내 개인 개발 적용·기록·Draft PR·Sites를 맡으며 사용자 탭을 열거나 이동하지 않는다.

## Task 1: PostgreSQL 수집 journal·잠금·불변 실행 저장

- [x] `0008_policy_collection` migration·schema를 추가한다. `policy_collection_channels`에는 collection_id·정규화 설정/해시·생성 시각, `policy_collection_attempts`에는 attempt UUID4·channel FK·단조 sequence·running/succeeded/failed·시작/완료 시각·고정 failure_code와 성공 capture/report bytes/SHA를 저장한다. 관계·상태/nullable·양의 sequence/크기/완료시각 제약을 schema와 migration에 함께 둔다. 원본/완료행은 repository에서 append-only이며 기존 테이블은 변경하지 않는다. 합성 fixture reset에 두 테이블을 추가한다.
- [x] 새 storage 모듈에 불변 scope/config 모델과 repository/session API를 만든다. DB 검증→명시 lease→설정 결합/검증→현재 상태/마지막 성공 확인→이전 running interrupted 마감→간격/상한 확인→새 running 시작→성공/실패 terminal 저장→unlock/close를 제공한다. 상태 조회는 생성/DDL·네트워크 없이 일관된 read-only transaction, baseline은 저장 SHA와 byte 길이/타입을 재검증한다. 모든 입력은 재검증하며 forged model_construct/model_copy 우회·시각 역전·unknown state·상태 충돌·stored hash/설정 변조·DB/잠금 연결 상실은 고정 오류로 닫는다. 완료 불명확 응답은 자동 재시도하지 않는다.
- [x] worker가 다음 Task에서 쓸 최소 API·타입을 정하고 사용 예·transaction 경계·잠금 해제/connection-loss 의미를 report에 적는다. storage에는 connector/worker 의존성을 추가하지 않는다. report는 opaque exact bytes로 저장하고 SDK 비교/semantic 검증 책임은 worker가 맡는다. status에 private raw를 출력하지 않으며 worker가 필요한 때만 검증된 baseline을 읽는다.
- [x] TDD RED→GREEN으로 실제 전용 PG의 migration/반복·설정 불변·DB명·최소 간격/상한·성공뒤실패/중단·현재 상태/마지막 성공·hash corruption·동시 lease/다른backend/잠금상실·terminal 불명확 commit·읽기-only/no-write·크기/타입·기존 원문/공개/세션 보존을 검증한다. Ruff/format/mypy와 관련 PG 회귀 후 storage README·체크박스·report·커밋. 전체 suite는 controller가 실행한다.

## Task 2: bounded poll·상태 CLI와 수집 SDK 연결

- [x] Task1 API를 이용해 worker에 엄격 job parser와 `poll_policy_collection`/`policy_collection_status`를 구현한다. 명시 scope/간격/상한 확인과 running commit 이후에만 기존 capture SDK를 호출한다. 저장 baseline을 기존 parser/동일 기사집합으로 검증하고 compare로 현재 본문/조건을 검증한 뒤 정확 두 artifact를 저장한다. baseline의 첫 성공은 new다. HTTP/조건·파싱 실패는 각각 capture_failed/validation_failed로 남기며 기존 성공은 보존한다. DB오류/불명확 성공 commit은 추가 HTTP/실패 덮어쓰기 없이 고정 오류로 종료한다. 반환은 typed 집계/시각·상태만이다.
- [x] 기존 `issuedigest-policy poll PRIVATE_JOB` 및 `issuedigest-policy status PRIVATE_JOB`를 추가한다. 명시 CLI에서만 ISSUEDIGEST_DATABASE_URL을 읽고 기존 private engine lifecycle/log sink를 재사용한다. 다른 CLI 명령/파일 출력 계약을 보존한다. busy·not_due·attempt_limit는 집계된 정상 거부로 구분하고 실패한 실제 poll은 nonzero, status는 성공/실패/미완료·last_success와 age/stale를 정확히 분리한다. 상태 확인은 row/모델/HTTP를 만들지 않는다.
- [x] 실제 전용 PG+합성 MockTransport TDD: 첫 확보/동일 본문 재확보/본문 변경/성공뒤 HTTP오류·허용조건 오류·SIGKILL/running 복구·old/forged baseline·DB상실·동시/간격/상한 거부의0HTTP·상태조회0HTTP/0write·입력파일/중복JSON/불리언/크기·비밀 로그 비노출·기존 discover/capture/compare/prepare와 유료 실행 회귀를 검증한다. 실제 기사/신원은 사용하지 않는다. Ruff/format/mypy·관련 테스트 후 worker README에 한 번 실행/최소 간격/서버 scheduler 연결·중지/반복실행·원본 보존/한도와 미구현 범위를 적는다. lock/dependency/웹/API 계약은 바꾸지 않는다. commit/report·체크박스를 남긴다.

## Controller 인수와 반영

전체 검사·작업별/전체 독립 검토를 확인한다. 개인 개발 서버에서는 기존 권한·현재 schema/backup·활성 작업·공존 자원을 먼저 읽고, 사전 백업/별도 복원본에서 migration·고정 공식 기사 한 건의 실제 poll·원본/시각·상태와 무HTTP 간격 거부를 확인한다. 안전한 범위에서 별도 collector 실행 환경/개인 scheduler만 연결하며 기존 API/연구 worker/main/공개 게시/자료 권한은 바꾸지 않는다. 실제 연결을 못 했다면 이유와 다음 행동을 기록하며 코드 완료와 운영 실행을 구분한다. 실제 접속/키/기사 ID/원문/상세 receipt는 비공개로 보관한다. 마일스톤M2·tasks/progress·Draft PR·Sites와 이전 계획판 보존을 갱신한다. 자동 편입/최근 이슈 발견·자율 조사·전체 출시 완료로 표시하지 않는다.
