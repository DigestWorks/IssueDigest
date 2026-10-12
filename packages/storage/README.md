# PostgreSQL 근거 스냅샷 저장

`issuedigest_storage`는 API·worker 진입점과 분리된 내부 Python 패키지입니다.
검증된 `EvidenceBundle`을 불변 스냅샷으로 저장하고 해당 workspace에서 다시 읽습니다.
SQLAlchemy **2.1.4**, Alembic **1.20.0**, psycopg[binary] **3.3.6**을 고정하며,
Python **3.13.12**·uv **0.11.4**·PostgreSQL **18.6**에서 합성 자료로 검증합니다.

## 연결과 마이그레이션

저장소 루트에서 `npm run setup`으로 workspace를 설치합니다.
연결 URL은 `postgresql+psycopg://...`만 받으며 실제 PostgreSQL 서버인지 확인합니다.
DB URL은 호출자가 명시적으로 전달합니다. 제품 앱의 import/startup은 DB를 만들거나
연결하지 않습니다. 아래 명령은 이미 준비한 개발용 DB에 명시적으로 적용합니다.
운영·공유 DB 또는 사용자 자료를 테스트 대상으로 사용하지 않습니다.

```sh
# ISSUEDIGEST_DATABASE_URL을 해당 개발 환경의 비밀 설정에서 지정한 뒤 실행
uv run --package issuedigest-storage alembic -c packages/storage/alembic.ini upgrade head
uv run --package issuedigest-storage alembic -c packages/storage/alembic.ini current
```

최초 revision은 `0001_evidence_snapshots`입니다. `alembic_version`으로 적용 상태를
관리하며 재실행해도 테이블을 다시 생성하지 않습니다. 데이터가 있는 DB에서 downgrade는
저장 테이블을 삭제하므로 아래 테스트의 전용 합성 DB에서만 검증합니다.
SQLAlchemy `metadata.create_all`은 마이그레이션 대용으로 사용하지 않습니다.
오프라인 SQL 생성은 지원하지 않으며 마이그레이션도 실제 PostgreSQL 연결을 확인합니다.

## 사용법과 불변성

```python
from uuid import uuid4
from issuedigest_storage import EvidenceRepository, create_storage_engine

# database_url: 서버 내부 설정, bundle: 호출자가 제공한 EvidenceBundle
engine = create_storage_engine(database_url)
try:
    repository = EvidenceRepository(engine)
    snapshot_id = uuid4()
    created = repository.save(snapshot_id, bundle)  # 최초 True, 동일 정규화 내용 재전송 False
    loaded = repository.load(bundle.document.workspace_id, snapshot_id)
finally:
    engine.dispose()
```

문서·버전·파싱 표현·인용은 각각 전역 UUID 기준 독립 불변 행입니다.
문서는 `(workspace_id, provider, source_id)` identity도 유일합니다.
같은 ID에 다른 내용 또는 workspace를 제출하면 `StorageConflict`가 발생합니다.
같은 원문 해시의 새 version ID는 별도 버전이며 파서 변경 표현도 별도로 보존합니다.
동일 표현에 새 인용을 추가하려면 새 snapshot ID를 사용합니다. 과거 스냅샷의 인용
목록·tuple 순서는 바뀌지 않습니다.

계약 JSON을 입구·출구에서 재검증하고 JSONB payload·내용 SHA-256·관계형 ID/공간/부모
참조를 대조합니다. 복합 FK와 unique 제약은 workspace·문서·버전·표현·인용 사슬과
스냅샷의 인용 연결을 묶습니다. `StorageCorruption`은 잘못된 payload·해시·관계를
거부합니다. `load`는 다른 workspace와 모르는 ID에 `None`을 반환합니다.
workspace 필터는 인증 또는 멤버십 검증을 대신하지 않습니다.

한 트랜잭션이 모든 객체, 스냅샷, 정확한 순서의 인용 연결,
`evidence.snapshot_saved.v1` outbox 한 행을 저장합니다. 최초 event ID는 snapshot ID이며
payload에는 workspace·snapshot·문서·버전·표현 ID만 포함합니다. 동일 재전송은 추가
outbox를 만들지 않습니다. 동시 같은 ID 제출은 하나만 생성하고 다른 내용은 충돌합니다.
DB 쓰기 실패는 전체를 rollback하고 원문·DB URL을 담지 않은 `StorageError`를 반환합니다.
연결 구성·연결 확인 실패는 비밀 설정을 담지 않은 `ValueError`입니다.

원문 bytes·객체 저장소·파서·검색/pgvector 인덱스·Neo4j·인증·DBOS/PydanticAI 실행·SSE는
후속입니다. 원문 객체 ID·해시는 참조이며 파일 존재나 원문 해시 대조를 보장하지 않습니다.
공개 HTTP 저장/조회, outbox 조회/소비·재시도·투영 API는 제공하지 않습니다.

## 합성 PostgreSQL 테스트

새 전용 로컬 컨테이너만 생성합니다. 아래 계정은 합성 테스트 전용 공개 값입니다.
컨테이너는 localhost에만 바인딩되며 기존 DB·컨테이너를 변경하지 않습니다.

```sh
docker run --name issuedigest-storage-test --rm -d \
  -e POSTGRES_USER=issuedigest_test -e POSTGRES_PASSWORD=issuedigest_test \
  -e POSTGRES_DB=issuedigest_test -p 127.0.0.1:55432:5432 postgres:18.6
export ISSUEDIGEST_TEST_DATABASE_URL='postgresql+psycopg://issuedigest_test:issuedigest_test@127.0.0.1:55432/issuedigest_test'
# pg_isready가 성공한 뒤 실행
uv run pytest packages/storage/tests
npm run check
# 이 명령으로 만든 전용 컨테이너만 종료
docker stop issuedigest-storage-test
```

fixture는 localhost/127.0.0.1·DB 이름 `issuedigest_test`·psycopg와 URL query override 없음으로
대상을 제한한 뒤 Alembic upgrade와 테스트 행 truncate를 수행합니다.
마이그레이션 테스트는 이 DB에서 downgrade→upgrade도 실행합니다. 손상 검출 테스트는
실행 범위 안에서 합성 행·제약·trigger만 변경하며 다음 테스트 전에 행을 초기화합니다.
DB 소유자 권한이 필요합니다. DB URL이 없는 로컬 전체 검사는 통합 테스트를 명시적으로
skip합니다. CI는 PostgreSQL **18.6** service와 URL을 제공하고 URL 누락을 실패로 처리합니다.

실제 DB round trip(text/PDF/table·한국어/emoji·UTC·인용 순서), workspace 격리,
버전/표현 추가, 불변 ID/identity 충돌, 모델 검증 우회, 저장 손상, FK 제약,
중간/outbox 실패 rollback, 독립 connection 동시 쓰기, 마이그레이션 재실행을 검사합니다.
