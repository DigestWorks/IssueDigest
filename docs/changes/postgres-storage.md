# PostgreSQL 원문·인용 저장 기반

2026-10-12. 사용자 선택 D011: PostgreSQL + pgvector + PydanticAI/DBOS. 이 작업은 R2의 **검증된 EvidenceBundle 스냅샷 저장·조회와 원자적 outbox**만 구현한다. R1 권한, R3 검색, R6 워커 복구 전체의 완료를 뜻하지 않는다.

## Global Constraints

- PoC·운영 모두 PostgreSQL을 사용한다. SQLite·메모리 대체 구현은 만들지 않는다. 첫 검증 엔진은 PostgreSQL 18.6이다.
- Python 3.13.12·uv 0.11.4, 기존 계약·HTTP 두 경로·웹은 유지한다. 재사용 저장 패키지는 API/worker 진입점과 분리한다.
- 원문 bytes·객체 저장소·파서·검색/pgvector 인덱스·Neo4j·인증·실제 DBOS/PydanticAI 실행·SSE·운영 배치는 후속이다. 원문 객체 ID와 해시는 참조이며 파일 존재·해시 대조를 보장하지 않는다.
- DB 접근은 서버 내부 구성 요소다. workspace 필터는 인증·멤버십 검증을 대체하지 않는다. 공개 HTTP 저장/조회 경로를 추가하지 않는다.
- 운영/공유 DB·원격 서버 설치를 변경하지 않는다. 테스트는 새 전용 로컬 DB 및 CI의 합성 자료만 사용한다. 비밀 설정은 기록하지 않는다.
- 기존 부분 계약은 변경하지 않는다. 제공 모델은 저장 입구와 읽기 출구에서 JSON으로 재검증해 model_construct/model_copy 검증 우회를 막는다.
- 독립 리뷰·검증 기록은 미병합 PR 검토가 끝날 때까지 해당 계획의 ignored SDD 디렉터리에 보존한다. 다른 계획의 기록을 읽거나 삭제하지 않는다.

## 저장 규칙

1. 호출자는 UUID v4 `snapshot_id`와 검증 가능한 EvidenceBundle을 제출한다. 저장소 `save(snapshot_id, bundle) -> bool`은 최초 생성에 True, 동일 ID·같은 정규화 내용의 재전송에 False를 반환한다. 다른 내용이나 다른 공간으로 같은 ID를 재사용하면 StorageConflict다. citation tuple 순서도 스냅샷 내용이며 보존한다.
2. `load(workspace_id, snapshot_id) -> EvidenceBundle | None`은 해당 공간의 자료만 읽고 모르는 ID/다른 공간은 None이다. 재검증 실패·저장 객체/관계/내용 해시 불일치는 StorageCorruption으로 거부하며 원문 내용·DB URL을 오류에 출력하지 않는다.
3. SourceDocument, DocumentVersion, ParsedRepresentation, Citation은 각각 ID 기준 불변 객체다. 동일 ID·동일 내용은 재사용하고 다른 내용은 충돌이다. 전역 ID와 workspace 및 부모 참조는 FK/unique로 묶는다. 같은 표현에서 새 citation을 추가할 때 새 snapshot_id로 저장할 수 있다. 기존 스냅샷의 citation 목록은 변하지 않는다.
4. `(workspace_id, provider, source_id)`는 문서 identity에 대해 유일하다. 원문 내용 해시의 같음만으로 버전을 합치지는 않는다. 외부 수집에서 ID·내용 fingerprint를 재사용하는 정규화/중복 제거 정책은 후속이다.
5. 정규화한 계약 JSON은 JSONB payload에 저장하고 ID/공간/부모 참조는 관계형 열로 둔다. payload와 열의 일치는 저장·읽기 양쪽에서 검사한다. UTC·UUID·Unicode 정규화는 기존 도메인 직렬화를 따른다. DB가 표현할 수 없는 문자열은 쓰기를 실패시키며 일부 행이 남지 않는다.
6. 한 트랜잭션이 문서·버전·표현·인용·스냅샷 및 `evidence.snapshot_saved.v1` outbox 행을 함께 저장한다. 스냅샷당 outbox 한 행만 남긴다. payload는 공간·snapshot/문서/버전/표현 ID를 참조하며 원문 내용은 넣지 않는다. 최초 event ID는 snapshot ID를 사용한다. outbox 조회/소비·재시도·그래프 투영은 이 작업에 포함하지 않는다.
7. 동시에 같은 스냅샷을 제출해도 하나만 생성한다. 호출자가 AUTOCOMMIT Engine을 전달해도 저장은 명시적인 트랜잭션으로 처리한다. commit 이전의 실패·충돌은 해당 쓰기 전체를 rollback한다. commit 응답 중 연결이 끊겨 완료 여부를 확인할 수 없으면 미저장으로 단정하지 않고 같은 snapshot ID로 조회·재시도해 확인한다. 동일 객체 ID의 서로 다른 내용이 동시 제출되어도 기존 객체를 덮어쓰지 않는다. DBOS를 도입하기 전 SQLAlchemy 트랜잭션이 앱 저장·outbox의 기준이다.
8. Alembic upgrade는 새 DB에 적용하고 재실행 가능하다. downgrade→upgrade도 합성 DB에서 검증한다. DB 초기화는 앱 import/startup에서 수행하지 않는다. 연결 URL은 명시적으로 전달하고 PostgreSQL+psycopg만 받으며 실제 엔진도 PostgreSQL인지 검사한다.

## Task 1 · 저장 패키지·마이그레이션·실제 DB 검증

- [x] 아래 전체 수용 조건을 구현하고 검증한다. 구현자가 완료 시 이 항목을 체크한다.

`packages/storage`의 uv 멤버와 `issuedigest_storage` typed Python 패키지를 만든다. SQLAlchemy 2.1.4, Alembic 1.20.0, psycopg[binary] 3.3.6을 정확히 고정하고 uv.lock을 갱신한다. 기존 domain을 workspace 의존성으로 사용한다. 최소 공개 API는 `create_storage_engine(database_url)`, `EvidenceRepository(engine)`와 위 save/load, `StorageConflict`, `StorageCorruption`이다. 불변 객체용 독립 테이블, 스냅샷의 정확한 인용 연결·순서, outbox, FK·unique·버전 메타데이터를 Alembic 최초 revision으로 구성한다. SQLAlchemy metadata.create_all을 앱/테스트의 마이그레이션 대용으로 사용하지 않는다.

TDD: 실행 가능한 실제 PostgreSQL 테스트를 먼저 쓰고 의미 있는 RED를 확인한 뒤 구현한다. 계약을 흉내내는 테스트 대신 다음 장애 경계와 결과를 검증한다.

- text/PDF/table citation·한국어/emoji·UTC 시각·tuple 순서 round trip, 새 repository/connection으로 재열람.
- 다른 workspace 조회 격리; 같은 source 문서의 새 version·새 representation·새 snapshot에서 추가 citation 허용, 과거 snapshot 보존.
- 같은 snapshot 재전송은 False 및 outbox/객체 행 수 동일; snapshot 또는 문서/버전/표현/인용 ID의 변경 충돌 및 전역 ID를 다른 공간에 재사용 거부.
- 모델 검증 우회 입력 거부, DB에 잘못 저장된 payload/hash/부모 참조 감지. 필요하면 합성 전용 DB에서 직접 SQL로 손상시키되 실행 테스트 범위 내에서만 수행한다.
- 쓰기 중간·outbox 삽입 실패 때 앞선 새 객체가 남지 않음. DB 실패를 일으키는 테스트는 테스트 hook을 제품 코드에 추가하지 않고 실제 제약/테스트 fixture로 발생시킨다.
- 독립 connection의 동시 동일 snapshot 쓰기에서 True 한 번·False 한 번, 정확한 객체·outbox 행 수. 동시 변경 충돌도 기존 자료 보존을 확인한다.
- 빈 DB upgrade·재upgrade·downgrade/재upgrade, PostgreSQL 이외 URL 거부 및 잘못된 연결 구성에서 URL/비밀번호 비노출.

테스트 DB는 `ISSUEDIGEST_TEST_DATABASE_URL`로 명시한다. 수동 로컬 전체 검사에서 미설정이면 DB 통합 테스트를 명확히 skip할 수 있지만 CI에서는 전용 PostgreSQL 18.6 service+URL을 제공하여 실제 통합 테스트를 반드시 실행한다. CI 전용 DB 외 reset/drop은 하지 않도록 테스트 fixture에 전용 DB 이름 검증을 둔다. Docker service는 localhost 전용이며 운영 비밀을 사용하지 않는다. 루트 pytest/mypy 검사 대상과 CI·README·storage README/마이그레이션 실행 안내를 갱신한다. 제품 API/웹 동작 변경 없음.

## 완료 증거

독립 작업 리뷰 + 전체 변경 리뷰, controller의 `npm run check` 및 실제 PostgreSQL 통합 테스트 통과, Draft PR 게시를 각각 기록한다. 운영 DB 연결·사용자 자료 수집·검색·실행 복구·월 운영비는 별도 미검증으로 남긴다.

## 구현 중 판단 기록

- 앱 도구가 저장소를 인식하지 못해 기존 sibling `.worktrees` 경로에 Git worktree를 만들었다. 판단이 틀리면 앱의 작업 공간 연결을 다시 정리해야 한다.
- 스냅샷 ID는 파싱 표현 ID와 분리했다. 같은 표현에 추가 인용을 선택해도 과거 선택을 보존하기 위한 경계이며, 잘못된 경계라면 저장 스키마 이관이 필요하다.
- 선택된 pgvector·PydanticAI·DBOS의 설치는 해당 검색/worker 구현에서 한다. 이번 저장에 쓰지 않는 의존성을 먼저 추가하지 않으며, 호환성 문제가 생기면 그 단계에서 버전을 조정한다.
- 미병합 PR 검토가 끝날 때까지 ignored 리뷰 기록을 보존한다. 불필요한 보존이면 로컬 scratch 정리만 필요하다.
- rollback 보장은 commit 전 실패에 적용한다. commit 응답을 잃으면 같은 ID로 결과를 확인한다. 이 판단이 달라지면 호출자의 오류·재확인 처리를 수정해야 한다.
