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

새 요청은 질문/부모 맥락의 멱등 해시와queued/빈 근거를 저장합니다. `research_retrieval`의 `question-topics-ko-v2`는 기존 canonical 투영에서 최대8개 질문 원형과 원형별 최대1개 조사 변형을 조회합니다. 변형별 실제 문자열 일치 문단을 snapshot별로 번갈아 최대200개 검증하고201번째로 잘림을 감지하며, 변형별20개 snapshot·전체 상위20개·최종5개를 제한합니다. 주제별 중복 가산 없이 일치 주제 수, 원형 직접 일치 수, 안정된 snapshot ID 순으로 정렬합니다. 길이4 이상 문자열은 명시한 ASCII 공백6종만 제거한 전체 문자열 실제 포함도 확인하며 원문 위치로 사용하지 않습니다. 기존 공개 문자 검색 API와 `literal-ngrams-v1` 투영은 유지합니다. `worker_load`는 현재 권한·run잠금 아래 검색/정확 원문 로드·근거 기록·retrieving 전환을 한 트랜잭션으로 고정합니다. 복구에서는 고정된 근거만 읽으며 무근거는0모델호출/insufficient_evidence로 종료합니다. 부모 근거 재사용은 완료된 부모와 유효 검색어 없는 일반 후속 질문으로 제한하며 명시 새 주제의 실패에 임의 적용하지 않습니다. 과거 저장 결과를 다시 쓰지 않습니다.

새 v7 검색 경계는 두 메서드로 나뉩니다. `worker_prepare_search(run_id)`는 현재 작성 권한과
완료 부모의 원문 provenance를 검증해 현재 run을 반환합니다. 검색·근거 고정·정상 상태 전이는
수행하지 않으므로 원래 질문에 문자 일치가 없어도 planner를 실행할 수 있습니다. 신규 worker가
먼저 `retrieving`으로 전이한 뒤 `worker_search_and_fix(run_id, queries, *, input_tokens=0,
output_tokens=0)`를 호출합니다. 첫 고정은 `retrieving` 상태에서만 허용합니다.

storage는 tuple 형태의1~3개 query(각1~64자, 공백만/Unicode 제어 문자 불가)와 실제 planner
사용량(음수/bool 불가, 출력500 이하, 입력+출력8,000 이하)을 다시 검증합니다. 현재 권한과
run 잠금 아래 기존 최신 승인 검색을 원래 질문부터 실행하고 각 계획 query의
`question_terms` 검색을 더합니다. 각 결과 최대5개를 원래 질문 우선 라운드로빈으로 합쳐
중복 없는 최대5개 원문·표시를 검증한 뒤 같은 transaction에서 snapshot IDs를 고정합니다.
검색 성공은 새 상태 이벤트를 만들지 않습니다. 검색0은 알려진 planner input/output usage와
`failed/insufficient_evidence`를 원자 저장하며 재실행으로 새 자료를 선택하지 않습니다.
취소·현재 권한 상실은 추가 색인 조회 전에 종료합니다.

이미 고정된 active run은 현재 색인·새 승인본을 조회하지 않고 고정 원문·표시·부모를 다시
검증해 같은 IDs를 반환합니다. 유효 검색어 없는 일반 후속 질문은 계획 query에 관계없이
완료 부모의 정확한 전체 근거를 재사용하며, 고정 후에도 같은 부모 IDs인지 확인합니다.
새 주제는 기존 부모 근거로 자동 대체하지 않습니다. 과거 workflow용 `worker_load`의
queued 검색·고정·retrieving 전이와 고정 근거 재생 의미는 유지합니다.

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
The retrieval profile is `question-topics-ko-v2`; pre-change baseline reports identify
`question-terms-v1`. The literal projection profile remains unchanged. Evaluation verifies the
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

`issuedigest_storage.planned_retrieval_evaluation.evaluate(engine, raw_job_bytes)` adds a
separate strict comparison SDK (`PlannedEvaluationJob` / `PlannedEvaluationReport`). It reuses
v1 scope/fingerprint/transaction/family metrics and calls the actual planned search with no
parent or model calls. Reports distinguish recorded planner output from operator-authored
queries and count relevant, explicitly irrelevant and unjudged returns. `judged_precision`
excludes unjudged returns and is null with no judged returns; it is not overall precision or
answer quality. See the [planned comparison job and denominators](../../tests/evaluation/README.md#기록된-계획-검색과-원래-검색-비교).

## 명시 정책뉴스 collection journal

`0008_policy_collection`은 기존 근거·공개 게시·세션과 FK를 공유하지 않는
`policy_collection_channels`와 `policy_collection_attempts`만 추가합니다.
`issuedigest_storage.policy_collection`의 `PolicyCollectionConfig`는 정렬한9자리 ASCII
기사 ID1~2개·UUID4 collection·DB명·간격·보존 기준·실행 상한을 불변 결합합니다.
같은 collection에 설정을 바꾸면 고정 오류로 거부합니다. 새 collection은 별도 운영자 결정입니다.

`PolicyCollectionRepository(engine).lease(config)`의 context에서만 poll을 기록합니다.
전용 연결의 nonblocking session advisory lock `(104704, 2)`가 사용 중이면 `None`을
반환합니다. 실제 DB명·backend·lock 소유를 매 쓰기 전에 확인하며 AUTOCOMMIT 엔진도
READ COMMITTED transaction으로 바꿉니다. `session.start(now=aware_datetime)`은 이전
running을 interrupted로 마감한 뒤 간격·상한을 확인하고, 허용된 새 running을 HTTP 전에
commit합니다. 거부 결과는 `not_due`·`attempt_limit`이며 새 attempt가 없습니다.

`session.baseline()`만 마지막 성공의 정확 capture/report bytes를 읽습니다.
타입·상한·SHA256와 실행 순서를 재검증합니다. capture는 최대8MiB+16,384bytes,
report는 최대64KiB입니다. 둘 다 비어 있지 않은 bytes만 받습니다. storage는 report를
해석하지 않으며 SDK의 원본 형식·동일 기사집합·비교 결과 검증은 호출 worker의 책임입니다.
`session.succeed(attempt_id, capture_bytes, report_bytes, finished_at=...)`는 두 원본과
SHA를 원자적으로 저장합니다. `session.fail(..., "capture_failed" | "validation_failed",
finished_at=...)`은 실패 코드만 남기고 마지막 성공을 유지합니다. 완료 행과 원본을
수정·삭제하는 repository API는 없습니다. 자동 보존 삭제도 없습니다.

`repository.status(config, now=None)`는 REPEATABLE READ·READ ONLY transaction에서
attempt_count·latest·last_success·age_seconds·stale를 구분하며 raw bytes를 조회하지
않습니다. 기본 관측 시각은 일관된 snapshot을 확보한 뒤에 읽습니다. 명시한 `now`는
관측된 시작·완료보다 과거이면 거부합니다. 알려지지 않은 collection도 행을 만들지
않습니다. age/stale의 기준은 마지막 성공의 `finished_at`이며 SDK 발행일·본문 최신성·전체
기사 수집 완전성을 뜻하지 않습니다.
이는 마지막 성공 확보 완료 시각 기준입니다. 상태 모델의 내부 식별자는 CLI 출력 대상이 아닙니다.

모든 시각은 timezone을 가진 datetime이며 저장 경계에서 UTC로 정규화합니다.
이전 시작·완료보다 과거인 시각, forged Pydantic 모델, 상태/설정/hash 손상,
연결/lock 상실은 `PolicyCollectionError`의 고정 메시지로 닫습니다. commit 응답이
불명확하면 `PolicyCollectionCommitUnknown`이 발생하고 해당 lease를 더 사용할 수
없습니다. HTTP·commit 재시도 또는 `fail` 덮어쓰기를 하지 않고 context를 종료합니다.
다음 명시 실행에서 실제 저장 상태를 읽고 남은 running만 interrupted로 마감합니다.
context 종료는 정확 lock을 풀고 연결을 닫으며, 해제 실패 연결은 pool로 반환하지 않습니다.

## 검토한 고정 collection attempt의 private 편입

`0009_policy_intake`는 `policy_intake_receipts`만 추가합니다. 기존 journal·canonical·인용·공개
브리핑·세션을 변경하는 migration은 없습니다. `issuedigest_storage.policy_intake`의 생성자는
IO 없이 engine만 보관합니다. HTTP·모델·collector·worker 의존성도 없습니다.

- `PolicyIntakeEntry(snapshot_id, bundle, presentation, fingerprint_sha256)`
- `PolicyIntakePlan(collection, attempt_id, workspace_id, approval_sha256, entries)`
- `PolicyIntakeRepository(engine).load_capture(collection, attempt_id)`
- `repository.check(plan)` / `repository.apply(plan)`

`collection`은 기존 `PolicyCollectionConfig`, `attempt_id`는 운영자가 고정한 UUID4입니다.
`load_capture`는 REPEATABLE READ·READ ONLY에서 정확한 성공 attempt의 원본 bytes·SHA를
다시 검증해 기존 `PolicyCollectionBaseline`을 반환합니다. latest를 대신 선택하지 않습니다.
`check`도 READ ONLY이며 advisory lock·자료·표시·투영·receipt를 만들지 않습니다.

`check/apply`는 같은 검증·결정 경로를 사용합니다. bounded strict UTF-8 JSON envelope,
설정 결합·capture/report SHA·기사집합·시각·성공 상태, 후보와 기존 자료의 graph·정확 인용·
source/URL·원본 provenance, 마지막 승인·재시도 receipt와 원래 생성된 canonical을 확인합니다.
HTML 본문·권리·metadata 재추출과 report 의미 재계산은 기존 worker parser/compare의 책임입니다.
고정 intake는 `korea-policy-html` parser version `"1"`, `"2"`, `"3"`만 허용합니다. `"3"`은
관측된 두 span·상대 부처 링크 metadata 형식이며 AI workflow v3와 별개입니다. 본문 정규화는
기존 `korea-policy-paragraphs-v1`을 유지하고 다른 parser version은 계속 거부합니다.
parser version도 기존 의미 fingerprint에 포함하므로 같은 본문이라도 version2→3은 새 승인
버전이며 이후 같은 metadata/인용의 version3 수집은 기존 버전을 재사용합니다. 과거 인용은
기존 canonical reader로 계속 검증합니다.
`approval_sha256`도 검증된 worker 승인의 attestation이며 storage가 원래 PolicyJob을 재구성해
검증하는 서명이 아닙니다. `fingerprint_sha256`은 report의 기존 `after_fingerprint` digest를
그대로 사용합니다. 이를 JSON 문자열로 다시 hash하지 않습니다.

첫 추적은 새 기준 버전을 만듭니다. 마지막 승인 fingerprint와 인용 selector 배열이 순서까지
같을 때만 기존 snapshot·인용·표시를 재사용합니다. 인용 선택 변경도 새 승인 버전입니다.
A→B→A는 새 버전이며 과거/동일 수집 시각의 뒤늦은 편입은 거부합니다. 기존 source는 원래
문서 ID와 payload를 유지하고 새 버전의 나머지 ID는 새 UUID4여야 합니다. 같은 attempt
재실행은 전체 검증 plan의 canonical JSON SHA256 request hash가 같을 때만 허용합니다.
`json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`의
UTF-8 SHA256이며 entries·인용 순서와 후보 ID·기본값을 포함합니다.

`apply`는 READ COMMITTED에서 nonblocking transaction advisory lock `(104704, 3)`을 얻고
원래 backend·실제 DB·lock 소유와 현재 scope를 쓰기 전 및 commit 전에 확인합니다.
기존 `EvidenceRepository._save`, 표시 저장 body와 `rebuild_projection`을 호출해 원문·인용·
outbox·표시·투영·receipt 전체를 한 번 commit합니다. 실패는 전체 rollback합니다. 재시도도
원본·canonical 관계·outbox·표시를 다시 확인하며 derived 투영만 재생성할 수 있습니다.
commit 응답 유실은 `PolicyIntakeCommitUnknown("Policy intake commit unknown")`으로
구분하고 자동 재시도하지 않습니다. 다른 실패는 `PolicyIntakeError("Policy intake unavailable")`
고정 오류입니다. 다음 명시적 같은 요청은 실제 commit 여부를 다시 읽습니다.

결과는 `schema_version/outcome/sources/new_versions/reused_versions/receipts_created` 집계만
포함합니다. outcome은 `checked/applied/already_applied/busy`입니다. check와 기존 적용 재시도는
`receipts_created=0`, 이미 적용된 요청은 `new_versions=0`입니다. 민감한 입력은 모델 repr에서
숨기며 engine logging·수명·정리는 호출자가 책임집니다.

receipt PK는 `(workspace_id, attempt_id, news_id)`이고 실제 선택된
`document_id/version_id/representation_id/snapshot_id`의 기존 복합 관계를 참조합니다.
`(workspace_id, document_id, capture_collected_at)`도 unique이며 `ix_policy_intake_latest`는
해당 workspace/문서의 수집 시각 내림차순 조회를 지원합니다. 쿼리 소비자는 journal 권한 없이
`policy_intake_schema.PolicyIntakeReceipt.model_validate(dict(row), strict=True)`로 구조만
검증할 수 있습니다. 이는 원본/보고서 검증을 수행하지 않습니다. receipt를 덮어쓰거나 삭제하는
repository API는 없지만 DB 소유자의 직접 변조를 막는 trigger·권한 시스템은 아닙니다.

새 질문의 `research_retrieval.variant_candidates(conn, workspace_id, term,
original_terms=...)`는 workspace/문서별 `capture_collected_at`이 가장 큰 receipt의 snapshot만
후보로 사용합니다. `created`와 `reused` receipt를 모두 포함하며 본문 버전의 수집 시각으로
대신 선택하지 않습니다. 이 조건은 검색어·round-robin·200개 후보 제한·점수 계산 전에
적용됩니다. 최신 승인본에 검색어가 없거나 투영이 없어도 구판으로 돌아가지 않습니다.
receipt가 없는 legacy 문서는 기존 검색을 유지합니다. 정규화·프로필·순위·한도는 같습니다.

반환 후보는 receipt 구조와 canonical의 workspace/문서/버전/representation/snapshot 관계,
source ID·생성/재사용 시각을 확인하고 기존 canonical·투영 검증을 거칩니다. 생성 receipt는
원본 hash도 canonical과 비교합니다. 이는 조회된 후보의 구조·관계 검사이며 journal 원본·
보고서·승인 provenance를 다시 검증하거나 DB 소유자의 일관된 직접 변조를 탐지하는 보장은
아닙니다. 조회는 자료·receipt·표시·투영을 쓰거나 원본 artifact를 읽지 않습니다.

적용 전 실제 DB에 `0009_policy_intake` migration과 **실제 app 역할의
`policy_intake_receipts` SELECT 권한**이 필요합니다. 기존 canonical/검색 투영 SELECT 권한에
이 테이블 SELECT만 추가하며 channel·attempt journal 권한은 필요하지 않습니다. migration만
실행해서 기존 app 역할에 SELECT가 자동 부여되지는 않습니다. 실제 권한 적용·안전 재시작은
운영 절차에서 별도로 수행합니다.

일반 literal 검색과 정확 원문 reader는 역사 버전을 계속 읽습니다. 이미 snapshot을 고정한
run의 재실행, 일반 후속 질문의 검증된 부모 근거 재사용과 과거 유료 checkpoint 복구도
기존 근거를 유지합니다. 새 주제를 검색하는 질문에만 최신 승인본 선택이 적용됩니다.


운영자 권한 확인: 기존 default privileges가 새 테이블에 앱 쓰기를 자동 부여할 수도 있다. 개인 개발 적용에서 이를 확인해 `policy_intake_receipts`에만 비조회 권한을 제거하고 기존 앱의 SELECT 성공·INSERT/UPDATE/DELETE/TRUNCATE/REFERENCES/TRIGGER/MAINTAIN 거부를 실측했다. 기존 테이블이나 default grants를 일괄 변경하지 않는다. migration 완료와 최소 권한 검증은 별도 단계다.


## Private v9 내부 관련성 선택

신뢰 worker만 `worker_load_relevance_candidates(run_id, candidate_ids)`와 `worker_apply_relevance_selection(run_id, candidate_ids, selected_ids, input_tokens=..., output_tokens=...)`를 사용한다. DBOS search2의 원래 canonical UUID4 고유1..5 후보를 근거로 현재 사용자/멤버십→run 잠금 순서·부모·모든 원문을 검사한다. 후보 또는 정확 selected인 현재 고정값만 한 번의 ordered subset 축소/동일 replay로 허용한다. unknown/중복/재정렬/다른 row 원문/terminal은 허용하지 않는다. 모두 제외는 snapshot_ids를 비우고 알려진 합계 usage와 insufficient_evidence를 같은 트랜잭션에 기록한다.

새 `worker_record_relevance_usage`는 v9 worker의 검증된 실제 subtotal만 단조 증가로 기록한다. 취소·권한 변경 이후에도 알려진 비용을 보존하며 status/result/원문·권한/예약을 수정하지 않는다. 후보/전체 결정/hash는 DBOS journal 내부에만 남기고 DB schema/HTTP에는 추가하지 않는다. 기존 worker_search_and_fix/worker_load/worker_transition 및 완료 provenance 계약은 바꾸지 않는다.
