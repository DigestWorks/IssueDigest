# 실제 작업 공간의 자료·Google 초대 등록 준비

2026-10-14 한국 시간. 사용자는 실제 DB 연결→공동 공간/원문 등록→Google 로그인 검증 순서의 진행을 승인했다. 현재 SSH와 GitHub HTTPS가 시간초과여서 서버 설정·원격 최신 상태를 확인하지 못했다. 실제 연결 조건을 우회하지 않고 로컬에서 사용할 등록 도구와 개인 입력을 준비한다. OpenSpec root=null이므로 기존 문서형 명세와 SDD/TDD/독립 리뷰를 적용한다.

## Global Constraints

- 기존 Google OAuth·서버 세션·현재 권한·불변 EvidenceBundle·인용/원문 의미는 유지한다. 실제 Google 계정은 사용자 승인 첫 계정만이며 두 번째는 미정이다. 실제 이메일·클라이언트/DB/SSH 비밀·자료 본문/인용·개별 ID/hash는 Git/PR/Sites/로그에 게시하지 않는다. 구현자/리뷰어는 실제 개인 설정·원문 파일을 읽지 않고 합성 입력만 쓴다.
- 실제 서버/공동 DB는 테스트/reset/downgrade 대상이 아니다. 테스트는 controller가 만든 소유 loopback PostgreSQL18.6/issuedigest_test만 사용한다. 실제 적용은 접속·대상·백업 조건·기존 앱 계정/권한·승인 입력을 확인한 후에만 별도로 수행한다. 기본 실행은 로컬 파일 검증만 하고 DB/네트워크/파일 쓰기를 하지 않는다.
- 운영자 전용 CLI이다. HTTP 등록/초대/권한 API·자동 가입·provider subject 바인딩·세션/토큰 발급·Google 호출·자동 마이그레이션·계정 생성/권한 부여·자료 삭제/덮어쓰기·스키마 변경은 추가하지 않는다. 실제 runtime에는 DDL 계정을 쓰지 않는다. main·공용/운영 서비스·공개 앱 배포는 D013에 따라 유예한다.
- 자료와 초대의 등록은 하나의 실제 DB 트랜잭션으로 처리한다. 오류/충돌이면 이번 변경 전체가 rollback되고 기존 자료/권한은 보존된다. 재실행은 같은 예약 ID·정규화 내용으로 중복을 만들지 않는다. 초대의 기존 비활성/바인딩 상태와 사용자·멤버십·세션을 재활성화하거나 수정하지 않는다. commit 응답 유실은 성공으로 표시하지 않는다.
- stdout/stderr/errors/repr는 고정 메시지와 집계만 제공한다. 이메일/본문/DB URL·비밀·UUID/개별hash·입력 경로/값/예외 객체를 오류에 반사하지 않는다. CLI JSON 입력은 UTF-8·중복 key/비유한 숫자 거부·최대8MiB의 현재 사용자 소유 정규 파일, symlink/특수 파일/그룹·타인 읽기/쓰기 권한 거부. 한 번 열어 읽은 입력을 사용하며 오류는 입력 없는 고정 오류로 감싼다. 환경에서는 명시적 ISSUEDIGEST_DATABASE_URL만 읽는다. dotenv/쉘/URL/원문 다운로드/재귀 디렉터리 탐색을 하지 않는다.

## Task 1: 호출자 트랜잭션에서 재사용하는 자료·초대 저장

- [x] 저장 내부 helper·회귀 구현/검토.

`packages/storage/src/issuedigest_storage/repository.py`의 기존 save SQL과 `oauth.py`의 register_invite SQL을 작은 Connection 기반 내부 helper로 추출한다. 새 operator가 기존 저장 규칙을 복제하지 않고 호출자 트랜잭션에 참여시키기 위한 변경이다. helper는 스스로 engine 연결/commit/rollback을 하지 않는다. 기존 공개 메서드 서명·반환 bool·검증/오류·READ COMMITTED·불변 무결성/재전송·outbox·초대 정규화/충돌/기존 상태 보존은 그대로 유지한다. 공개 메서드의 invalid 입력은 기존처럼 DB 연결 전에 거부한다. helper의 입력 검증/전제와 정확한 typed signature를 보고서에 기록해 Task2가 안전하게 사용하도록 한다. 광범위 리팩터나 스키마/export/새 public API 변경은 없다.

TDD는 새 `packages/storage/tests/test_provision_transactions.py`에서 소유 PostgreSQL의 같은 Connection으로 자료+초대 생성/조회 후 명시 예외→전부 rollback, 정상 commit 후 기존 공개 로더/초대 경로와 동일, 같은 내용 재실행 미생성, 기존 내용 충돌·중간 실패/outbox 실패 rollback, 비활성/바인딩 초대 보존을 확인한다. 기존 `test_repository.py`/`test_oauth_workspace.py` 회귀를 포함한다. 기존 테스트를 지우거나 약화하지 않는다. focused Python+Ruff/format/mypy를 실행하고 exact RED/GREEN/commands/output와 helper 인터페이스를 보고한다. 전체 결합 검사는 controller가 Task2 뒤에 한 번 수행한다.

## Task 2: 비공개 등록 계획·읽기 검사·명시 적용 CLI

- [x] 계획/등록/CLI·테스트·사용 안내 구현/검토.

`packages/storage/src/issuedigest_storage/provisioning.py`에 운영 내부 모델/함수를 추가한다. 공개 domain/OpenAPI에 이메일 모델을 추가하지 않는다. strict/frozen/extra-forbid schema_version=1의 `ProvisioningPlan`은 `expected_database`(ASCII identifier1~63, 정확 비교), `workspace_id:UUID4`, `invites`(1~2), `snapshots`(1~50)를 가진다. invite는 예약 user_id:UUID4·ASCII 이메일(기존 _email과 같은 lowercase, dot/plus 병합 없음)·role(viewer/editor/owner), snapshot은 snapshot_id:UUID4·기존 EvidenceBundle이다. invite email/user와 snapshot ID 중복을 금지하고 모든 bundle workspace가 계획과 같아야 한다. 이메일과 ID/내용은 repr에 숨기고 불변 입력의 우회 생성은 저장 경계에서 JSON으로 재검증한다. 실제 계정 승인은 controller의 개인 파일에서 수행하며 모델 검증만으로 사용자 승인을 주장하지 않는다.

기본 순수 검증 결과는 schema_version/상태/초대 수/자료 수 집계만 제공한다. DB 읽기 검사는 manifest의 expected_database와 URL database/current_database의 정확 일치, PostgreSQL와 필요한 기존 근거/초대 테이블·열 준비를 확인한다. 전용 read-only transaction에서 SELECT만 하며 auth activity/흐름/세션을 만들지 않는다. 예상 대상이 다르면 가능한 한 연결 전에, 서버 대상/스키마 불일치는 쓰기 전에 고정 오류로 거부한다. inspector는 마이그레이션/DDL을 하지 않는다.

명시 apply는 같은 연결의 READ COMMITTED transaction에서 대상/스키마를 재확인하고 Task1 helper를 사용한다. 모든 자료·초대를 일관된 순서로 등록하며 성공 commit 후 created/unchanged 집계만 반환한다. 변경된 source identity·예약 ID/role/email/본문이나 DB 오류·입력 우회·권한 부족은 전부 rollback/fixed error, 동일 재실행은 기존 snapshot/outbox/초대만 유지한다. 기존 비활성 초대 또는 이미 바인딩된 초대를 같은 계획으로 다시 처리해도 권한/상태를 바꾸지 않는다. 이 도구는 실제 Google 로그인이나 접근 준비 완료를 판정하지 않는다.

`provision_cli.py`는 `uv run --package issuedigest-storage python -m issuedigest_storage.provision_cli /absolute/private/plan.json` 형식이다. 기본은 offline 검증, `--check-database`는 읽기 검사, `--apply`는 명시 등록이며 두 flag는 동시에 사용할 수 없다. CLI 인자 오류도 입력 없이 고정 메시지/exit2, 입력·연결·등록 실패는 고정 메시지/exit1, 성공은 집계 JSON/exit0이다. env/config 값을 출력하지 않는다. engine은 해당 모드에만 생성하고 성공/실패 모두 dispose한다. CLI 파일 경로·실제 plan/메일은 controller만 다룬다.

새 테스트는 otherwise-valid 경계1/2invites·1/50snapshots, 한도/중복/잘못된 UUID/역할/email/다른 공간/우회 모델, repr·비밀/경로 오류 미노출, 기본 모드 DB/네트워크/쓰기0, 파일 소유/0600/symlink/특수/size/UTF8/중복key/비유한숫자·인자/환경 검증, 읽기 검사가 DB 변경0·잘못된 대상/스키마 거부, 실제 PG 원자 생성·반복·두 번째 충돌 rollback·기존 상태 보존·권한 부족/commit 실패·dispose를 확인한다. `packages/storage/README.md`와 `infra/README.md`에 고정 합성 예시(개인 실제 파일 없음), 제한/명시 migration·대상/백업/승인·앱 역할/실제 로그인 확인 순서를 기록한다. focused/정적 검사 후 controller 전체 검사·review를 따른다. 의존성/스키마·앱 UI/HTTP 변경은 없다.

## Controller 결합·실제 연결

- [x] 작업/전체 독립 리뷰·전체 Python/JS/lint/타입/SPA/계약 검사와 합성 운영자 CLI→기존 실제 Google SDK/권한 API→자료 목록/원문 조회 결합 검증.
- [x] 기존 private 실제 정부 원문과 승인 계정 기록을 확인하고, 새 공유 공간/자료/인용/초대 예약 ID의 개인 등록 계획을 mode600으로 준비. 기존 검증 namespace를 실사용 계정으로 간주하지 않는다. 원문/인용 위치와 이용조건은 다시 대조하며 모델 입력 처리의 완료를 주장하지 않는다.
- [ ] 외부 연결 복구 후 기존 앱 DB 계정의 개인 설정·대상·필요 권한·백업 조건 확인, explicit migration/plan 검사/적용과 실제 Google 로그인(사용자) 검증. 서버·외부 연결이 없으면 이 항목을 대기로 남기고 실제 적용 완료로 표시하지 않는다.
- [ ] 코드·진행/작업/필요 입력 문서·Draft PR(basefeat/google-oauth-workspace)·Sites 이전 기록 보존/요약 갱신·소유 자원 정리/개발 인계. 외부 게시/동기화 실패는 미게시로 기록하고 코드/검토 증거를 보존한다.

## 검증 결과 · 2026-10-14

- helper87a9210: 새 실제 트랜잭션 검사11개·저장 회귀108개 및 독립 작업 리뷰 승인.
- CLI767bf9d: 초기79개·입력/대상/커밋 등 보완91개, 전체 저장235개. 작업 리뷰에서 실제 pool 정리 오류의 비밀 로그/성공 오판과 잡히는 예외만으로 무호출을 검사한 테스트2종 지적을 받았다.
- 수정22ede20: 실제 드라이버 연결 종료/반납 오류4개 RED→GREEN, 무호출 카운터 독립 확인, 엔진 자체 pool logger만 한시적으로 대체/복원. 전체 저장239개·정적 검사 통과. 커밋 후 정리 실패는 기존 커밋을 취소하지 못하며 실패 집계와 동일 입력 재실행으로 처리한다.
- controller 최종 전체 Python1,597+JS322=1,919개·Ruff/format/mypy56/TS/SPA/계약, 별도 CLI→실제 서명 검증 SDK의 고정 MockTransport→두 합성 사용자/보호 API·자료/인용·차단·로그아웃 결합1개 통과. skip/warning 없음. 실제 Google 네트워크/브라우저 로그인 검증과 다르다. 합성 QA의 초기 미정규화 기대값 오류는 QA만 수정했고 로그를 보존했다.
- 개인 실제 캐시 원문/출처표시 조건/정확 인용3개를 대조하고 새 공유 공간 예약 ID·승인 계정1개·자료1건의 비공개 계획을600으로 보관했다. 새 CLI 오프라인 검증 통과. 계정 승인 기록은 미등록 상태로 유지하며 실제 이관 완료로 표시하지 않는다.
- SSH/GitHub 연결 복구 후 전용 PG18.6/vector0.8.7·앱 테이블0개·앱 접속 설정 부재를 읽기 확인했다. 기존 앱 설정과 백업 조건을 받기 전 실제 DB 적용은 대기한다. 공동 DB/운영·권한·main은 변경하지 않았다. 작업 수정 재검토/전체 리뷰·PR/Sites/인계 상태는 진행 기록을 따른다.

- 독립 작업/수정·전체/최종 문서 수정 검토 승인. 전체 리뷰의 초대 잠금 UPDATE 권한 누락은1eea1e3에서 두 안내에 명시했고 scoped 재검토에서 해결·새 지적 없음. 실제 앱 권한/적용 준비를 승인한 것으로 해석하지 않는다.
