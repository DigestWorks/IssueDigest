# main 자동 배포

`main` 푸시와 수동 실행은 `.github/workflows/production.yml`에서 처리한다. 앱이 없는 초기 `main`은 대기로 종료하며 배포 작업은 건너뛴다. 앱이 병합되면 고정된 Node·npm·Python·uv와 lockfile을 사용해 `npm run check`를 실행한다. PostgreSQL 검사는 GitHub 러너의 합성 DB를 사용한다. 운영 DB를 초기화하거나 마이그레이션하지 않는다. 앱이 없는 상태에서 수동 실행하면 `host-check`가 GitHub 러너에서 서버까지의 SSH 연결과 도구를 확인한다. 앱 게시 성공을 뜻하지 않는다.

검사를 통과한 커밋만 SSH로 전달한다. 전용 키는 `deploy COMMIT_SHA`와 읽기 전용 `check`만 허용하며 대화형 셸·포트 전달·임의 명령을 허용하지 않는다. GitHub에는 `ISSUEDIGEST_DEPLOY_HOST`, `ISSUEDIGEST_DEPLOY_USER`, `ISSUEDIGEST_DEPLOY_KEY`, `ISSUEDIGEST_DEPLOY_KNOWN_HOSTS`를 비밀값으로 등록한다. 실제 접속 정보와 키는 공개 저장소에 기록하지 않는다.

## 서버 경로와 권한

- `/srv/issuedigest/repo`: 배포용 Git 저장소. 개발 그룹은 읽기·쓰기·탐색이 가능하며 실행 가능한 파일을 실행할 수 있다.
- `/srv/issuedigest/releases`: 커밋과 실행 시각으로 구분한 산출물. 개발 그룹에 읽기·쓰기·탐색 권한을 부여한다. 실패한 빌드도 진단을 위해 보존한다.
- `/srv/issuedigest/current`: 현재 릴리스 심볼릭 링크. 배포 계정만 전환한다.
- `/srv/issuedigest/shared`: 잠금·배포 커밋·운영 환경 설정. 개발 그룹에는 비밀 설정을 공개하지 않는다.

공용 checkout에서 수정·실행할 수 있다. 같은 checkout의 브랜치와 파일 변경은 다른 사용자에게도 적용되므로 개발 작업은 각자 홈의 clone 또는 별도 worktree 사용을 권장한다. 신규 개발 계정은 관리자가 기존 개발 그룹에 추가한다. 그룹 변경 후 새 로그인 세션에서 접근한다. 기존 `postgres`, `reference`, `access` 경로와 데이터는 배포 대상이 아니다.

## 배포와 복구

관리자가 `deploy.sh`와 `ssh-command.sh`를 root 소유 `/usr/local/libexec/issuedigest/`에 설치한다. 서비스·nginx 템플릿도 관리자 설치 대상이다. 저장소 파일을 바꿔도 관리자 설치 파일이 자동 교체되지는 않는다. 도구 버전을 바꾸면 서버 도구도 먼저 갱신한다.

배포 스크립트는 서버 잠금과 GitHub 동시 실행 제한을 적용한다. 전달된 SHA가 최신 `main`인지 확인하고 `git archive`로 새 릴리스를 만든다. `npm ci`, `uv sync --locked --all-packages --no-dev`, `npm run build`를 실행하고 후보 API를 별도 로컬 포트에서 검사한다. 빌드 중 `main`이 바뀌면 오래된 커밋을 게시하지 않는다.

후보가 통과하면 `current`를 원자적으로 전환하고 API 서비스를 재시작한다. 웹·API 공개 상태 확인이 실패하면 이전 링크를 복원하고 서비스를 재시작한다. 첫 배포 실패는 링크를 해제하고 서비스를 중지한다. API 재시작 중 짧은 요청 실패가 있을 수 있으며 무중단 배포를 보장하지 않는다.

웹은 `apps/web/build/client`를 nginx가 제공하고 앱 경로는 `index.html`로 연결한다. API·헬스 경로는 FastAPI에 전달하며 HTML로 대체하지 않는다. 앱 병합 전 웹은 HTTP503, API는 연결할 서비스가 없으므로 HTTP502를 반환한다. HTTPS 인증서는 기존 webroot·갱신 훅을 사용한다. 초기 인증서가 없으면 `issuedigest-tls.timer`가 시간마다 발급을 재시도한다. 성공하면 HTTPS 설정을 적용하고 초기 발급 타이머를 중지한다. 이후 갱신은 기존 certbot이 담당한다. 인증서 발급 전에는 HTTP503을 유지하며 앱 배포의 공개 HTTPS 검사는 실패한다.

기본 API는 외부 DB 없이 시작하고 보호된 자료 조회는 거부한다. `/health/live`는 프로세스 생존만 확인한다. DB·로그인·자료 수집·검색·에이전트 실행 완료를 뜻하지 않는다. 후속 앱 구성이 환경 설정을 요구하면 `shared/application.env`를 관리자와 배포 계정만 읽을 수 있게 작성하고 후보 실행에도 동일한 설정이 적용되는지 확인해야 한다.

## 검증 기준과 출처

기준은 개발 브랜치의 `README.md` 운영 정적 파일 계약, 기존 `verify.yml` 검사 명령, 실제 FastAPI의 `/health/live`와 `/api/v1/status`이다. 개발 브랜치를 병합하거나 내용을 변경하지 않았다.

[GitHub workflow 문법](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [배포 제어](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments)를 기준으로 main 필터·동시 실행 제한·production 환경을 구성했다. 운영 DB 마이그레이션, 인증, 자료 연결은 별도 검증 대상이다.

## 준비 검증 기록 (2026-10-13)

- 공용 저장소의 그룹 읽기 허용·쓰기 거부·shared 열람 거부를 실제 개발 계정에서 확인했다.
- `actionlint`·`bash -n`·`nginx -t`·systemd 설정 검사 통과. SSH 임의 명령 거부와 읽기 전용 `check`를 확인했다.
- 실제 개발 브랜치의 별도 사본으로 고정 도구·locked 설치·정적 빌드·offline API 실행을 확인했다. 로컬 nginx의 웹200·SPA 경로200·API/health JSON200·없는 API JSON404를 확인했다. 읽기 전용 파일 시스템 등 운영 서비스 제한을 적용한 임시 systemd 서비스에서도 health200을 확인한 뒤 중지했다. 사본은 공개 앱에 연결하지 않았다.
- `main` 준비 커밋의 push 워크플로에서 readiness 성공과 앱 검사·배포 건너뛰기를 확인했다. 수동 실행은 서버 SSH 연결 검증용이다.
- 권한 있는 DNS 서버4개와 Google·Cloudflare 조회는 서버 A 레코드를 반환했다. 인증기관은 발급 시 DNS NXDOMAIN을 반환해 초기 TLS가 대기 중이다. 타이머를 준비했으며 발급 성공을 미리 완료로 표시하지 않는다.
- 실제 앱 main 병합·공개 앱 배포·장애 후 이전 릴리스 복구는 아직 실행하지 않았다. DB·개발 브랜치·기존 수집/참조 서비스는 변경하지 않았다. Sites 요약은 반영 대기다.

## 개발 그룹 쓰기와 실행 권한 추가 (2026-10-13)

사용자 요청으로 `repo`와 `releases`의 기존·신규 파일에 그룹 쓰기 권한을 적용했다. 디렉터리 setgid와 기본 ACL로 그룹 소유권·쓰기 권한을 이어가며, 스크립트는 실행 권한을 유지한다. 일반 문서·데이터에 일괄 실행 권한을 부여하지 않는다. 현재 개발 계정과 관리자 계정에 공용 저장소 Git 신뢰 경로를 등록하고 `core.sharedRepository=group`을 설정했다. 새 개발 계정에도 해당 Git 설정이 필요하다.

실제 개발 계정에서 두 경로의 파일·디렉터리 생성, 파일 쓰기, 스크립트 실행, 그룹 권한 상속, Git 상태 조회를 확인했다. `shared`와 DB 비밀 디렉터리 접근 제한은 유지한다. 배포 계정은 상위 디렉터리에서 릴리스 링크를 전환할 수 있도록 별도 ACL을 부여했다. root 소유 서버 설치 스크립트·서비스·nginx 설정과 sudo/Docker 권한은 그대로다.
