# Infra

개발·배포·백업·복원·운영 설정 위치. 기존 서버 정보와 결정 기록을 기준으로 구성한다. 실제 비밀값은 저장소 밖에서 관리한다.

[개발 서버 안내·확인 기록](development-server.md)에 사용자 전용 환경·자원·실행 방법·지정 포트·검증·남은 확인을 기록한다. Docker·운영 배포 구성은 아직 없으며 개발 자동 검사는 저장소 GitHub Actions에서 실행한다.

[PostgreSQL 연결 준비](postgresql.md)에 선택 엔진·관리자 확인 사항·내부 연결·마이그레이션·백업의 후속 범위를 둔다. 실제 저장 패키지 실행과 합성 DB 검증은 packages/storage README를 따른다. 운영 설치 완료를 뜻하지 않는다.

Google OAuth의 명시 runtime 실행은 [API README](../apps/api/README.md)를 따릅니다. 개발·운영 Google 웹 앱에 각각 승인 HTTPS origin과 `{PUBLIC_ORIGIN}/api/v1/auth/google/callback`을 등록하고 client ID/secret과 앱 권한 PostgreSQL 연결을 저장소 밖에서 주입해야 합니다. 초대 이메일·identity·membership은 개인 DB의 승인된 trusted operator 경계에서만 등록합니다. runtime에는 스키마 변경 계정을 주지 않으며 마이그레이션은 별도 명시 작업입니다.

`ISSUEDIGEST_CONFIGURED_RUNTIME=1`일 때만 새 factory를 선택합니다. API 실행은 `--no-access-log`를 사용하지만 기존 운영 프록시/Nginx 로그는 이 변경으로 수정하지 않았습니다. 공개 OAuth 전에 callback query와 cookie의 프록시 기록 여부를 확인해야 합니다. 합성 OAuth/DB 검증은 실제 Google 앱 등록·계정 승인·외부 로그인 준비 완료를 뜻하지 않습니다.
