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

최초 revision은 `0001_evidence_snapshots`이며 다음 `0002_auth_sessions`가 내부 사용자·멤버십·해시 세션 테이블을,
`0003_oauth_identity`가 단기 OAuth 상태·명시 초대 테이블을 추가합니다. `alembic_version`으로 적용 상태를
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
참조를 대조합니다. JSONB가 숫자 0의 부호를 보존하지 않으므로 저장 payload와 해시 입력에서
수치상 같은 `-0.0`·`0.0`을 `0.0`으로 정규화합니다. PDF 좌표의 같은 ID 재전송에도 같은
규칙을 적용하며 문자열·실제 좌표값·인용 순서는 그대로 보존합니다. 도메인 계약은 바꾸지 않습니다.
복합 FK와 unique 제약은 workspace·문서·버전·표현·인용 사슬과
스냅샷의 인용 연결을 묶습니다. `StorageCorruption`은 잘못된 payload·해시·관계를
거부합니다. `load`는 다른 workspace와 모르는 ID에 `None`을 반환합니다.
workspace 필터는 인증 또는 멤버십 검증을 대신하지 않습니다.

한 트랜잭션이 모든 객체, 스냅샷, 정확한 순서의 인용 연결,
`evidence.snapshot_saved.v1` outbox 한 행을 저장합니다. 최초 event ID는 snapshot ID이며
payload에는 workspace·snapshot·문서·버전·표현 ID만 포함합니다. 동일 재전송은 추가
outbox를 만들지 않습니다. 동시 같은 ID 제출은 하나만 생성하고 다른 내용은 충돌합니다.
호출자가 AUTOCOMMIT 엔진을 전달해도 저장 연결은 READ COMMITTED를 명시한 뒤 트랜잭션을
시작합니다. commit 이전의 실패·충돌은 해당 쓰기 전체를 rollback합니다.
DB 오류는 원문·DB URL을 담지 않은 `StorageError`를 반환합니다. commit 응답 중 연결이
끊기면 서버의 저장 완료 여부가 불확실할 수 있습니다. 이 경우 미저장으로 단정하지 않고
같은 snapshot ID와 같은 내용으로 재시도하거나 해당 workspace에서 `load`해 확인합니다.
재시도 결과 False는 동일 스냅샷이 이미 저장되어 있음을 뜻하며 추가 outbox는 만들지 않습니다.
연결 구성·연결 확인 실패는 비밀 설정을 담지 않은 `ValueError`입니다.

원문 bytes·객체 저장소·파서·pgvector 인덱스·Neo4j·로그인 공급자·DBOS/PydanticAI 실행·SSE는
후속입니다. 원문 객체 ID·해시는 참조이며 파일 존재나 원문 해시 대조를 보장하지 않습니다.
공개 HTTP 저장, outbox 조회/소비·재시도·투영 API는 제공하지 않습니다. API 앱의 보호 GET은 이 패키지의 내부 접근 경계를 사용합니다.

## 합성 PostgreSQL 테스트

기존 공유 DB와 분리된 PostgreSQL 18.6 전용 loopback 합성 DB를 준비하고,
DB 이름은 `issuedigest_test`로 지정합니다. 인증값과 연결 URL은 로컬 비밀 설정에서
`ISSUEDIGEST_TEST_DATABASE_URL` 환경 변수로 공급하며 문서·로그·버전 관리에 기록하지 않습니다.
기존 DB·계정·자료를 테스트 대상으로 사용하지 않습니다.

```sh
# 전용 합성 DB가 준비되고 ISSUEDIGEST_TEST_DATABASE_URL이 설정된 뒤 실행
uv run pytest packages/storage/tests apps/api/tests
npm run check
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


## 공급자와 독립된 내부 세션/접근

`IdentityRepository.register_identity(user_id, issuer, subject)`는 UUID4와 정확한 외부
issuer/subject pair를 원자적으로 등록합니다. 동일 pair/UUID 재등록만 idempotent하며
서로 다른 issuer의 같은 subject는 별개입니다. 이메일로 병합하거나 공백을 정규화하지 않습니다.
issuer와 subject는 각각 1~256 문자, NUL 없음이며 원문을 보존합니다. 이 한도는 PostgreSQL의
유일 pair 인덱스에 최대 UTF-8 문자열도 저장하도록 선택했습니다.
`set_enabled(user_id, enabled)`와 `set_membership(user_id, workspace_id, role, active=True)`로
사용자 활성과 viewer/editor/owner 멤버십을 내부에서 관리합니다. workspace UUID는 기존 근거
namespace이며 전체 workspace 생성/초대 관리가 아닙니다. 존재하지 않는 사용자 참조,
미지원 역할·잘못된 UUID·boolean 이외 상태값은 거부합니다.

이 메서드를 호출하는 코드가 신뢰된 OIDC 연결기/관리자 경계여야 합니다. 이 패키지는
공급자 토큰 검증과 사용자 비밀번호 처리를 수행하지 않습니다.
초대 승인은 아래 운영자 전용 메서드를 명시적으로 호출해야 합니다. 공개 HTTP 등록/발급/
멤버십 수정·테스트 로그인 경로는 없습니다. 외부 요청의 사용자 ID·이메일은 신뢰 증거가 아닙니다.

`SessionRepository.issue_session(user_id, lifetime_seconds=1209600)`는 활성 사용자에게만
`secrets.token_urlsafe(32)`의 256bit 임의 토큰을 발급합니다. DB에는 SHA-256 해시만 저장하며
원문은 `IssuedSession.token` 발급 결과에서만 반환합니다. repr에는 원문이 없고 로깅하지 않습니다.
재발급은 별도 토큰이며 `revoke_session(token)`은 idempotent입니다. 수명은 정수 1~1,209,600초
(bool 거부), 기본/최대 14일입니다. DB의 timezone-aware 서버 시각으로 발급하며 반환 만료는 UTC입니다.

`EvidenceAccessRepository.load_evidence(token, workspace_id, snapshot_id)`는 매 요청마다
DB에서 세션·사용자 활성·해당 공간의 active 멤버십을 확인하고 같은 Connection/transaction으로
기존 근거 integrity 로더를 호출합니다. 허용되지 않은 호출은 payload를 읽지 않습니다.
없는/만료/폐기/비활성 세션은 `AuthenticationDenied`, 미가입/다른 공간/없는 자료는 `None`,
DB 장애/저장 훼손은 원문·토큰·DB 설정을 포함하지 않는 `StorageError`입니다.
권한을 메모리에 캐시하지 않습니다. 성공한 허용 조회만 마지막 활동을 갱신하며 절대 만료를
연장하지 않습니다. 절대 만료 시각 또는 마지막 성공 조회 후 604,800초(7일)와 같은 시각도 거부합니다.
폐기/비활성/멤버십 회수는 다음 요청에서 확인합니다. 이미 시작한 응답을 소급 회수하지 않습니다.

인증 테이블은 기존 근거에 FK를 소급 추가하지 않습니다. `0001`→head와 `0002`→`0001`에서
기존 근거·스냅샷·인용 순서를 보존하며 `0002` downgrade는 인증 테이블만 삭제합니다.
`0006_persistent_sessions` upgrade는 기존 세션의 만료일을 변경하지 않고 절대 수명 제약만
14일로 변경합니다. downgrade는 8시간보다 긴 세션을 삭제한 뒤 8시간 제약을 복구합니다.
따라서 긴 세션 사용자는 다시 로그인해야 하며 기존 8시간 이하 세션의 만료일은 유지됩니다.
공통 정책은 `session_policy.py`에서 발급·검증·API 쿠키가 함께 사용합니다.
테스트 fixture는 루트 `conftest.py`를 공유하여 migration/reset을 충돌 없이 수행합니다.
실제 DB identity 충돌/동시 등록·hash-only 저장·수명/idle·활동 갱신·폐기/비활성/멤버십 회수,
두 회원의 동일 스냅샷 조회·workspace 격리·역할/FK·AUTOCOMMIT 경계·HTTP 오류 비노출을 검사합니다.
로그인 공급자, 운영 DB, 앱 로그인/자료 화면은 후속이며 이 단계만으로 운영 로그인이 완료되지 않습니다.


## OAuth 상태·명시 초대·작업 공간 목록

`OAuthRepository`는 서버 내부의 검증된 제공자 결과와 운영자가 명시적으로 승인한
초대만 처리합니다. HTTP 입력의 issuer/subject/email/권한을 그대로 전달하면 안 됩니다.
이 계층은 Google 서명이나 이메일 권위를 검증하지 않습니다. 제공자 연결기가 먼저
서명·issuer·audience·유효기간·nonce와 이메일 권위를 확인해야 합니다.

운영자는 `register_invite(issuer, email, user_id, workspace_id, role)`로 승인 이메일과
예약 UUID4, 승인한 공간·역할을 개인 DB에 등록합니다. 같은 내용은 최초 True/재호출 False,
내용 변경은 `StorageConflict`입니다. ASCII 이메일은 소문자로 비교하지만 dot/plus 별칭을
합치지 않습니다. 실제 계정·공간·세션·DB 비밀은 문서나 버전 관리에 기록하지 않습니다.
공개 가입/초대 등록 API는 없으며 실제 사용자나 공동 자료의 등록은 별도 준비 작업입니다.

`resolve_invited_identity(issuer, subject, email, authoritative_email)`는 미등록 subject의
최초 로그인에서만 권위 있는 검증 이메일과 활성·미사용 초대를 확인합니다. 사용자·승인
멤버십·고정 subject 바인딩은 한 트랜잭션으로 생성하며 동시 동일 로그인도 하나로 수렴합니다.
다른 subject는 같은 초대를 재사용할 수 없습니다. 이후 로그인은 정확한 issuer/subject와
활성 사용자만 사용하고 이메일 변경으로 사용자 ID나 권한을 바꾸지 않습니다. 폐기된 사용자와
멤버십을 재활성화하지 않습니다. `set_invite_enabled`는 미사용 초대의 이후 바인딩을 막으며
이미 발급한 사용자·멤버십·세션을 소급 폐기하지 않습니다. 기존 `set_enabled`,
`set_membership(..., active=False)`, `revoke_session`으로 각각 관리합니다.

`begin_login()`은 브라우저별 state/token 해시와 단기 PKCE verifier/nonce를 서버 DB에
10분 동안 저장합니다. PKCE는 S256이며 활성 흐름은 트랜잭션 잠금으로 최대 200개입니다.
`consume_login(state, browser_token)`은 양쪽 해시·만료를 확인한 뒤 한 번만 소비합니다.
다른 브라우저의 잘못된 요청은 유효 흐름을 삭제하지 않습니다. 제공자 호출 전에 소비하므로
실패 후 새 로그인 시작이 필요합니다. 반환 객체의 비밀은 repr에서 숨기고 로그에 기록하지 않습니다.
Google ID/access/refresh 토큰은 이 저장 계층에 전달하거나 저장하지 않습니다.

`issue_authorized_session(issuer, subject, previous_token=None)`은 등록된 활성 사용자와
활성 멤버십이 있는 경우에만 최대 14일/idle 7일의 해시 세션을 발급합니다. 이전 보유 쿠키의
세션 잠금 → 사용자 → 멤버십 순서로 확인하며 새 세션 저장과 이전 세션 폐기를 함께 commit합니다.
실패하면 둘 다 rollback합니다. 등록·권한 생성은 이 메서드가 수행하지 않습니다.

`WorkspaceAccessRepository.get_session(token)`은 세션·사용자·활성 멤버십을 같은
REPEATABLE READ 트랜잭션에서 잠그고 공간 UUID 문자열순으로 반환합니다. 멤버십은 최대 100개이며
넘치거나 훼손된 값은 응답 전체를 거부합니다. 멤버십이 없어도 유효 세션은 빈 목록을 반환합니다.
`list_evidence(token, workspace_id, limit=20)`은 해당 활성 멤버에게만 최신 생성 시각순,
같은 시각이면 snapshot UUID순으로 최대 50개와 `has_more`를 반환합니다. 비회원은 None,
자료가 없는 회원은 빈 catalog입니다. 각 반환 스냅샷의 기존 불변 로더를 같은 트랜잭션에서
재검증하고 실제 metadata·본문 첫 160 Unicode codepoint·인용 수만 요약합니다. 제목·주장·사진을
추정하지 않으며 원문 이용 권리나 주장 지지를 보장하지 않습니다. 부모·참조·payload가 훼손되면
부분 응답 없이 전체를 거부합니다. 유효 session/허용 catalog 조회만 activity를 갱신합니다.
동시 갱신의 SQLSTATE 40001은 트랜잭션 전체를 최대 두 번 재시도하여 권한을 다시 확인합니다.

`0003` downgrade는 신규 OAuth/초대 테이블만 제거하고 기존 사용자·세션·근거를 보존합니다.
테스트는 새 전용 loopback 합성 PostgreSQL에 한정합니다. 실제 공동 DB의 downgrade/reset,
운영 설정 변경, Google 계정 승인이나 외부 로그인은 이 구현의 검증 범위가 아닙니다.

## 비공개 작업 공간 등록 CLI

운영자가 승인한 자료·초대 예약을 준비하는 내부 도구입니다. 승인 이메일·예약 UUID4·역할과
검증된 `EvidenceBundle`을 하나의 개인 JSON 파일에 둡니다. 실제 이메일·원문·ID·연결 설정은
Git, PR, 공유 문서나 로그에 넣지 않습니다. 아래 예시는 실제 원문이나 계정과 관계없는 고정 합성
입력이며, `raw_object_id`와 raw hash는 합성 참조입니다. 이 예시의 빈 인용 목록은 실제 자료의
인용 확인을 대신하지 않습니다.

```json
{
  "schema_version": 1,
  "expected_database": "issuedigest_test",
  "workspace_id": "00000001-0000-4000-8000-000000000000",
  "invites": [
    {
      "user_id": "00000002-0000-4000-8000-000000000000",
      "email": "operator@example.test",
      "role": "viewer"
    }
  ],
  "snapshots": [
    {
      "snapshot_id": "00000003-0000-4000-8000-000000000000",
      "bundle": {
        "schema_version": 1,
        "document": {
          "document_id": "00000004-0000-4000-8000-000000000000",
          "workspace_id": "00000001-0000-4000-8000-000000000000",
          "provider": "synthetic",
          "source_id": "example-1",
          "source_kind": "other"
        },
        "version": {
          "version_id": "00000005-0000-4000-8000-000000000000",
          "document_id": "00000004-0000-4000-8000-000000000000",
          "raw_object_id": "00000006-0000-4000-8000-000000000000",
          "raw_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
          "media_type": "text/plain",
          "collected_at": "2026-10-14T00:00:00Z"
        },
        "representation": {
          "representation_id": "00000007-0000-4000-8000-000000000000",
          "document_version_id": "00000005-0000-4000-8000-000000000000",
          "parser_name": "synthetic",
          "parser_version": "1",
          "normalization_profile": "identity",
          "text": "Synthetic source.",
          "text_sha256": "043e71c9fd6621a93a8141ade39c265e7e6cc7bcfa0a3778a7d67826fe416586",
          "pages": [],
          "tables": []
        },
        "citations": []
      }
    }
  ]
}
```

파일은 현재 사용자 소유의 절대 경로 정규 파일로 준비하고 `chmod 600`으로 제한합니다.
읽기 전용 `0400`도 허용합니다. 부모 디렉터리·파일 symlink, 특수 파일, 다른 소유자,
그룹·타인 권한, 최대 8MiB 초과, 잘못된 UTF-8, 중복 JSON key와 비유한 숫자는 거부합니다.
열어 둔 파일 descriptor에서 한 번 읽으며 기본 실행은 DB·네트워크 연결이나 파일 쓰기가 없습니다.
`.env`나 다른 설정 파일을 읽지 않으며 URL·쉘 명령·원문 다운로드를 수행하지 않습니다.

```sh
# 절대 경로는 실행자가 준비한 개인 파일을 가리키는 자리표시자입니다.
uv run --package issuedigest-storage python -m issuedigest_storage.provision_cli /absolute/private/plan.json
# DB 모드에서만 명시적 ISSUEDIGEST_DATABASE_URL을 사용합니다.
uv run --package issuedigest-storage python -m issuedigest_storage.provision_cli /absolute/private/plan.json --check-database
uv run --package issuedigest-storage python -m issuedigest_storage.provision_cli /absolute/private/plan.json --apply
```

두 flag는 함께 사용할 수 없으며 축약 flag도 거부합니다. 성공은 집계 JSON과 exit 0,
인자 오류는 `Invalid provisioning arguments`와 exit 2, 입력·DB·등록 오류는
`Unable to provision workspace`와 exit 1입니다. 입력 경로·값·예외·이메일·DB URL은 출력하지
않습니다. 기본 결과는 `schema_version`, `status: validated`, `invites`, `snapshots`만 담습니다.
DB 검사 결과는 같은 집계와 `status: database_checked`, 적용 결과는 `status: applied`와
`invites_created`, `invites_unchanged`, `snapshots_created`, `snapshots_unchanged`를 담습니다.

v1 계획은 strict/frozen/extra-forbid이며 초대 1~2명·스냅샷 1~50개를 받습니다.
`expected_database`는 ASCII 식별자 `[A-Za-z_][A-Za-z0-9_]{0,62}`이고 대소문자까지 정확히
일치해야 합니다. 모든 예약 ID는 UUID4이며 이메일·사용자·스냅샷 중복과 다른 공간의 bundle을
거부합니다. ASCII 이메일은 기존 초대 규칙처럼 소문자로만 정규화하고 dot/plus 별칭은 합치지
않습니다. 역할은 `viewer`, `editor`, `owner`입니다. issuer는 기존 Google 공급자와 같은
`https://accounts.google.com`으로 고정합니다. 순수 모델 검증은 계정 승인을 판정하지 않습니다.

DB URL은 query 없는 `postgresql+psycopg://.../DATABASE`만 지원합니다. URL database가
계획과 다르면 연결 전에 거부하고, 실제 `current_database()`·PostgreSQL·트랜잭션 설정과
기존 public 근거/초대 테이블·필수 열을 연결 안에서 확인합니다. 다른 search_path의 shadow
테이블도 거부합니다. `--check-database`는 별도 READ COMMITTED read-only 트랜잭션의 SELECT만
실행하는 대상·스키마 검사이며, 적용이나 runtime에 필요한 권한이 준비되었음을 보장하지
않습니다. 검사·적용 모두 스키마를 만들거나 마이그레이션하지 않습니다.

`--apply`는 같은 연결의 READ COMMITTED 트랜잭션에서 대상·스키마를 다시 검사하고, 계획의
스냅샷 순서 다음 초대 순서로 기존 저장 helper를 호출합니다. 성공 commit 후에만 집계를
반환하며 충돌·DB 오류·권한 부족은 이번 쓰기 전체를 rollback합니다. 동일 계획 재실행은
스냅샷·outbox·초대를 늘리지 않습니다. 기존 비활성/바인딩 초대·사용자·멤버십·세션 상태를
바꾸지 않습니다. commit 응답 유실은 실패로 표시하며 저장 여부는 불확실할 수 있습니다.
새 ID로 다시 만들지 말고 동일 계획으로 재검사·재실행합니다. DB 모드 engine은 성공/실패
모두 dispose합니다. 엔진 단위 pool 로그 경계가 연결 reset·invalidation·close 오류의
원문/traceback 출력을 막고, SQLAlchemy가 오류를 내부에서 삼켜도 고정 실패를 반환합니다.
commit 이후 연결 정리에 실패하면 이미 등록되었을 수 있으므로 같은 계획으로 재확인합니다.

실제 적용 순서는 대상·기존 앱 계정 권한·백업/복원 조건·승인 계정·원문/인용/이용 조건 확인,
필요한 명시 Alembic migration, 오프라인 검증, 읽기 DB 검사, 명시 적용, 기존 앱 권한 GET과
사용자 실제 Google 로그인 확인입니다. migration에는 별도 관리 계정을 사용하고 CLI에는
기존 앱 역할의 필요한 SELECT/INSERT 권한과 초대의 `SELECT FOR UPDATE` 잠금을 위한
`auth_identity_invites`의 UPDATE 권한(테이블 전체 또는 최소 한 열)을 확인합니다. 이 잠금에
UPDATE 권한이 필요해도 CLI는 기존 초대·인증 상태를 바꾸지 않습니다. runtime의 기존 인증
읽기/쓰기 권한은 별도로 유지하며 CLI/runtime에 DDL 권한을 추가하지 않습니다. 등록 CLI는
사용자·권한·세션을 만들거나 Google을 호출하지 않으며 로그인/자료 접근 준비 완료를 판단하지
않습니다. 실제 앱 연결 설정·권한·백업/복원 조건·사용자 Google 로그인 확인은 대기 중입니다.

## 명시적 문자 검색 투영·보호 SDK

`0004_evidence_search`는 원 근거와 분리된 재생성 가능한 manifest·검색 단위 테이블을
추가합니다. native `varchar(3)[]` ngram 집합의 GIN 인덱스와 `@>`로 후보를 제한하며 새
extension·서비스·종속성은 설치하지 않습니다. migration은 위의 명시 Alembic 명령으로 실행합니다.
import/startup/기존 `save`는 migration이나 검색 투영을 수행하지 않습니다.

```python
from datetime import UTC, datetime
from issuedigest_domain import EvidenceSearchQuery
from issuedigest_storage import EvidenceRepository, WorkspaceAccessRepository

# engine, workspace_id, snapshot_id, session_token은 서버 내부에서 준비합니다.
rebuilt = EvidenceRepository(engine).rebuild_projection(workspace_id, snapshot_id)
query = EvidenceSearchQuery(
    terms=("등록금", "ABC-123"),
    limit=10,
    collected_from=datetime(2026, 10, 1, tzinfo=UTC),
    collected_to=datetime(2026, 11, 1, tzinfo=UTC),
)
result = WorkspaceAccessRepository(engine).search_evidence(session_token, workspace_id, query)
if result is not None:
    hits = result.hits
    coverage = result.coverage  # total/indexed/missing_snapshots, skipped_empty/large_cells
    incomplete = result.truncated or coverage.missing_snapshots > 0
```

`rebuild_projection`는 canonical `EvidenceRepository._load`를 재사용하고 하나의 READ COMMITTED
트랜잭션에서 manifest·단위를 교체합니다. 없는/다른 공간의 snapshot은 None, 동일 투영은
`RebuildProjectionResult.status="unchanged"`, 신규·달라진 투영은 `"rebuilt"`입니다. snapshot UUID의
결정적인 64-bit digest를 transaction advisory lock 키로 사용해 같은 snapshot 병렬 재생성을
직렬화합니다. 해시 충돌은 별개 snapshot을 직렬화할 뿐 내용이나 공간을 합치지 않습니다.
불변 원문 행에는 UPDATE 잠금을 요구하지 않습니다. 실패 시 이전 투영·근거·인용·outbox가
보존되며, 손상된 검색 단위는 명시 rebuild로 복구할 수 있습니다.

재생성 역할에는 기존 canonical 테이블 SELECT, 두 검색 테이블 SELECT/INSERT/DELETE 및
`pg_advisory_xact_lock` 실행 권한이 필요합니다. 보호 검색 역할은 기존 auth 세션·사용자·현재
membership의 SELECT/잠금 UPDATE 권한과 session 활동 UPDATE, canonical·검색 테이블 SELECT를
사용합니다. SDK가 DDL이나 권한 부여를 실행하지 않습니다. migration/재생성은 내부 관리 경계이며
공개 HTTP 쓰기·검색 경로는 추가하지 않습니다.

검색은 기존 REPEATABLE READ `_transaction`·`_authorize`·membership 잠금·`_refresh`와 40001
최대2회 재시도 경계를 사용합니다. 만료/idle/폐기/disabled는 `AuthenticationDenied`, 비회원·다른
공간은 None입니다. 허용된 빈 검색도 활동을 갱신하고 거부·오류는 갱신하지 않습니다.
workspace 필터를 SQL 후보·coverage·canonical reload에 모두 적용합니다. provider/source ID/kind와
수집 시각 필터는 원 문서/버전에서 얻습니다. 각 조사 후보는 canonical bundle, profile,
manifest checksum, unit text/checksum/ngrams, 원문 selector와 대조하며 훼손은 고정
`StorageCorruption`으로 전체 실패합니다. SQL 순서에서 같은 snapshot의 후보는 연속하므로
현재 snapshot의 canonical bundle·projection만 보존하고 다음 snapshot 전에 이전 전체 객체를
해제합니다. 이미 반환할 hit의 정확한 selector는 보존합니다. 반환 provider/source_id는 canonical
SourceDocument 문자열 전체를 보존하고 query 필터 한도(1,024자)로 자르거나 거부하지 않습니다. DB 오류는 설정·원문을 담지 않는 `StorageError`입니다.

수집 시각 desc·snapshot ID·unit ordinal 순으로 최대200개 후보(+1로 잘림 확인)를 조사하고,
실제 문자열 AND로 순서·반복 ngram 오탐을 제거합니다. 최대20개 hit를 반환하고 결과 한도나
후보 한도로 더 조사할 자료가 있으면 `truncated=True`입니다. `scanned_candidates`는 실제 검사한
후보 수(최대200)입니다. 저장 PostgreSQL text에는 NUL이 들어갈 수 없으므로 NUL term은
coverage와 빈 후보 결과를 반환합니다. 의미 검색·형태소 분석·정규화·관련성 점수는 제공하지
않으며 미투영/제외 셀/잘림이 있는 빈 결과를 모든 자료에 답이 없다는 근거로 쓰면 안 됩니다.

이 단계는 typed SDK와 합성 QA 검증이며 HTTP/UI·자동 outbox 소비·pgvector·AI 답변·전체 검색
평가20문항은 후속입니다. 실제 공동 DB 적용·설정·백업 확인과 사용자 운영 연결은 별도로 준비합니다.

## 조사 저장

`0005_research_journey`는 원본 evidence JSON이나 해시를 고치지 않고 표시 제목 sidecar, 조사 run/event, 월 예약 테이블을 추가합니다. `ResearchRepository`는 현재 쿠키 세션·enabled user·활성 membership을 조회/제출/취소 때 확인하고 worker는 actor 역할을 실행 전·완료 전 다시 확인합니다. 동일 actor/workspace/request_id와 동일 입력은 같은 run을 반환하며 입력이 달라지면 409입니다. 월 USD 10·건당 USD 0.25·40건, 공간별 active 1개를 PostgreSQL 잠금과 인덱스로 제한합니다. 실패·취소 예약은 자동 환급하지 않습니다. 모든 완료 결과는 JSONB에 저장되어 동료 멤버가 다시 읽을 수 있습니다.

운영자가 검증한 외부 제목은 `ResearchRepository.upsert_presentation(SourcePresentation(..., profile="operator-verified-v1"))`로 snapshot/workspace별 저장합니다. 자료 종류 기본 제목 외의 임의 본문 첫 줄을 제목으로 추정하지 않습니다. 기존 `legacy-bill-metadata-v1`만 정해진 첫 줄·의안번호·제안일을 검증해 자동으로 표시합니다.

새 요청은 질문/부모 맥락의 멱등 해시와queued/빈 근거를 저장합니다. `research_retrieval`은 기존 `search_evidence`의 실제 색인을 최대8개 검색어로 조회해 일치도/결정적 동률 순서로 최대5개 snapshot을 찾습니다. `worker_load`는 현재 권한·run잠금 아래 검색/정확 원문 로드·근거 기록·retrieving 전환을 한 트랜잭션으로 고정합니다. 복구에서는 고정된 근거만 읽으며 무근거는0모델호출/insufficient_evidence로 종료합니다. 부모 근거 재사용은 완료된 부모와 유효 검색어 없는 일반 후속 질문으로 제한하며 명시 새 주제의 실패에 임의 적용하지 않습니다. 과거 저장 결과를 다시 쓰지 않습니다.

## 검토한 공개 브리핑

`0007_public_briefings`는 기존 자료·세션·조사 행과 분리된 `public_briefing_heads`,
`public_briefings`를 추가합니다. 소유자만 명시 migration을 실행합니다. 기본 API import는
연결하거나 migration·게시를 실행하지 않습니다. 설정된 서버 factory는 기존 엔진을
`PublicBriefingRepository(engine)`에 명시 주입합니다. 서비스 역할에는 두 공개 테이블의
`SELECT`만 부여합니다. 게시 운영자에는 `SELECT/INSERT/UPDATE`와 transaction advisory lock
실행 권한이 필요하며 DDL·DELETE 권한은 필요하지 않습니다. 실제 역할 이름·권한 적용은
운영자가 별도로 확인하며 CLI가 권한을 바꾸지 않습니다.

게시 입력 `issuedigest_domain.public_briefings.PublicBriefingPlan`은 명시 공개 표제·설명·기준시각,
UUID4 공개 식별자, 순차 버전, 검토할 전체 Canvas와 각 문서의 `PublicSourceReview`를 받습니다.
출처 검토에는 정확한 `document_id`, `official_url`, `title`, `publisher`, `published_on`,
`checked_at`, `reviewer`, `license="kogl-type-1"`, `attribution`, `text_sha256`,
`photos_excluded=true`, `third_party_material_excluded=true`가 모두 필요합니다.
첫 지원 URL은 `https://www.korea.kr/news/policyNewsView.do?newsId=` 뒤 ASCII 숫자뿐이며
다른 호스트·경로·query·fragment·자격정보·명시 포트는 허용하지 않습니다. 같은 사이트의
다른 문서에 이용권을 추정하지 않습니다. 검토자는 해당 문서의 공공누리1유형 조건과
사진·외부 저작물 제외를 개별 확인하고, 자유 텍스트 전체의 공개 적합성도 검토해야 합니다.
이는 자동 개인정보 제거·사실 판정이 아닙니다.

Canvas는 기존 연구 v1/v2의 요약·비교·타임라인과 마지막 근거 모듈, 정확 인용,
`open_evidence` 액션으로 제한합니다. 최대5개 자료·12개 주장·4개 모듈을 받으며
생성/변환 문구의 inference provenance를 보존합니다. `as_of`는 내용 기준시각이므로
수집보다 이를 수 있지만 모든 출처 발행일 이후여야 합니다. 개별 권리 검토는 기준시각·수집
이후, 발행은 검토 이후여야 합니다. 원문 text/pages/tables/selector/인용·수집시각을 보존하고
내부 식별자는 공개 ID·버전별 독립 UUID4로 일관 변환합니다. parser는
`public-reviewed-copy` / `1` / `public-reviewed-copy-v1`로 표시합니다.

절대 경로·현재 사용자 소유·0400/0600 일반 파일만 읽습니다. symlink·FIFO·중복 JSON 키·
비유한 수치·추가 필드와8MiB 초과 입력은 거부합니다. 다음 명령의 경로와 해시는 운영자가
검토한 비공개 파일과 출력값으로 대체합니다. 기본 명령은 네트워크·DB 없이 검증합니다.

```sh
uv run --package issuedigest-storage python -m issuedigest_storage.public_briefing_cli /absolute/private-plan.json
uv run --package issuedigest-storage python -m issuedigest_storage.public_briefing_cli /absolute/private-plan.json --check-database
uv run --package issuedigest-storage python -m issuedigest_storage.public_briefing_cli /absolute/private-plan.json --apply --reviewed-sha256 FULL_PLAN_SHA256
uv run --package issuedigest-storage python -m issuedigest_storage.public_briefing_cli /absolute/private-plan.json --withdraw --reviewed-sha256 FULL_PLAN_SHA256
```

DB 명령은 `ISSUEDIGEST_DATABASE_URL`의 명시 PostgreSQL+psycopg URL을 사용하며 query override를
거부합니다. `plan_sha256`는 전체 검증 모델의 기본값·UTC 정규화값을 포함한 JSON을
`sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False`로 직렬화한
UTF-8 SHA256입니다. 공백이나 키 순서 자체의 서명은 아닙니다. 전체 내용을 검토한 이 해시가
정확히 일치해야 쓰며 검토자·본문·비밀 URL을 오류/로그에 출력하지 않습니다.

같은 slug/version/계획 재시도는 같은 시각·공개 데이터·해시를 반환합니다. 다른 내용의 덮어쓰기,
버전 건너뛰기, 공개 ID 재사용, 철회된 버전 재활성화는 충돌입니다. 동일 slug는 실제 PostgreSQL
transaction advisory lock과 latest CAS로 직렬화합니다. 최신 철회 뒤 과거 버전을 최신으로
되살리지 않으며 특정 과거 버전은 자체 철회 전까지 읽을 수 있습니다. `content_sha256`는
자기 hash 필드만 제외한 전체 `PublicBriefingDetail`의 동일 canonical JSON SHA256입니다.
DB의 payload/hash/행 참조·검토 기록·최대 버전/연속 이력/latest hash를 다시 검증하고 손상은
고정 오류로 처리합니다. 클라이언트가 이미 받은 데이터를 원격 삭제하는 기능은 아닙니다.

익명 읽기는 `/api/v1/briefings`, `/api/v1/briefings/{slug}`,
`/api/v1/briefings/{slug}/versions/{version}`의 GET뿐입니다. 최신 공개 목록은20개 이하입니다.
모두 `Cache-Control: no-store`, `X-Request-ID`와 검증된 JSON을 반환하며 미설정503,
없음/철회404, 잘못된 입력422에는 입력을 되돌리지 않습니다. 공개 읽기는 두 공개 테이블만
SELECT하고 세션·모델·DBOS·예산·비공개 저장소를 호출하지 않습니다. 공개 게시 HTTP API는 없습니다.

## Private retrieval evaluation

`issuedigest_storage.retrieval_evaluation.evaluate(engine, raw_job_bytes)` validates a bounded
strict JSON job again at the SDK boundary and returns an `EvaluationReport`. It accepts raw
bytes only, so forged Pydantic models cannot cause an unbounded dump before validation.
The existing retrieval algorithm is unchanged (`question-terms-v1`). Evaluation verifies the
exact workspace corpus, every canonical bundle and projection/unit, then runs all cases in
one read-only PostgreSQL `REPEATABLE READ` transaction. It never writes projections, sessions,
research runs, budgets or DBOS state. Failures use fixed messages and return no partial report.

`parse_job(raw_bytes)` validates offline; `EvaluationJob.model_json_schema()` and
`EvaluationReport.model_json_schema()` expose the strict job/report schemas. IDs, questions,
terms and ranks belong only in private report files, never ordinary logs. The caller owns the
engine and its logging/lifecycle configuration; the worker CLI supplies silent pool lifecycle
handling and publishes only after successful disposal. Do not enable SQL parameter logging.
See [evaluation instructions](../../tests/evaluation/README.md) for the full job example,
command, fingerprints, metric denominators and baseline/candidate comparison conditions.
