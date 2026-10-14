# Infra

개발·배포·백업·복원·운영 설정 위치. 기존 서버 정보와 결정 기록을 기준으로 구성한다. 실제 비밀값은 저장소 밖에서 관리한다.

[개발 서버 안내·확인 기록](development-server.md)에 사용자 전용 환경·자원·실행 방법·지정 포트·검증·남은 확인을 기록한다. Docker·운영 배포 구성은 아직 없으며 개발 자동 검사는 저장소 GitHub Actions에서 실행한다.

[PostgreSQL 연결 준비](postgresql.md)에 선택 엔진·관리자 확인 사항·내부 연결·마이그레이션·백업의 후속 범위를 둔다. 실제 저장 패키지 실행과 합성 DB 검증은 packages/storage README를 따른다. 운영 설치 완료를 뜻하지 않는다.

Google OAuth의 명시 runtime 실행은 [API README](../apps/api/README.md)를 따릅니다. 개발·운영 Google 웹 앱에 각각 승인 HTTPS origin과 `{PUBLIC_ORIGIN}/api/v1/auth/google/callback`을 등록하고 client ID/secret과 앱 권한 PostgreSQL 연결을 저장소 밖에서 주입해야 합니다. 초대 이메일·identity·membership은 개인 DB의 승인된 trusted operator 경계에서만 등록합니다. runtime에는 스키마 변경 계정을 주지 않으며 마이그레이션은 별도 명시 작업입니다.

`ISSUEDIGEST_CONFIGURED_RUNTIME=1`일 때만 새 factory를 선택합니다. API 실행은 `--no-access-log`를 사용하며 개발 Vite `/api` proxy 실패 로그의 URL·error payload도 고정 메시지로 대체합니다. 지원하는 개발 launcher는 raw request URL을 기록하는 `vite:proxy`·`vite:time` DEBUG namespace만 제외하고 다른 진단은 유지합니다. 임의의 직접 Vite 실행은 이 보장 밖입니다. 다만 기존 운영 프록시/Nginx 로그는 이 변경으로 수정하지 않았습니다. 공개 OAuth 전에 callback query와 cookie의 프록시 기록 여부를 확인해야 합니다. 합성 OAuth/DB 검증은 실제 Google 앱 등록·계정 승인·외부 로그인 준비 완료를 뜻하지 않습니다.

실제 공동 공간의 자료·초대 예약 준비는 [저장 패키지의 비공개 등록 CLI](../packages/storage/README.md#비공개-작업-공간-등록-cli)를
따릅니다. 개인 계획은 현재 사용자 소유 mode 0600 정규 파일로 저장소 밖에 보관합니다.
기본 실행은 파일 검증만 하고 `--check-database`는 읽기 전용 대상·스키마 검사로 적용/runtime
권한 준비를 보장하지 않습니다. `--apply`는 자료·초대의 단일 트랜잭션 등록입니다.
DB 모드만 명시적 `ISSUEDIGEST_DATABASE_URL`을 읽으며 query 없는
PostgreSQL+psycopg URL의 database와 계획의 `expected_database`를 정확히 대조합니다.
지원 형식·고정 합성 JSON·명령·집계 출력과 제한은 위 안내에 둡니다.

실제 적용 전에 대상·백업/복원 조건·승인 계정·원문/인용/이용 조건과 기존 앱 역할의
SELECT/INSERT 권한과 초대의 `SELECT FOR UPDATE` 잠금을 위한 `auth_identity_invites`의
UPDATE 권한(테이블 전체 또는 최소 한 열)을 확인합니다. 이 잠금에 UPDATE 권한이 필요해도
CLI는 기존 초대·인증 상태를 바꾸지 않습니다. 필요한 Alembic migration은 별도 관리 계정으로
명시 실행하고 CLI/runtime에는 DDL 계정을 쓰지 않습니다. 오프라인 검증→읽기 검사→명시 적용 뒤
기존 앱 권한 GET·자료 목록/본문 조회와 사용자의 실제 Google 로그인을 확인합니다. 초대 예약은
실제 사용자/세션 생성이나 로그인 확인이 아니며, 합성 검증을 운영 적용 완료로 기록하지
않습니다. 실제 연결 설정·앱 권한·백업/복원 조건·사용자 Google 로그인 확인은 대기 중입니다.
연결·앱 계정·백업 조건이 준비되지 않으면 실제 migration/적용은 대기로 둡니다.
