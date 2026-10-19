# 개발 서버 실행·확인 기록

공개 브리핑 개발 변경(D020)은 독립 검증/명시1건 게시 후 개인 개발 도메인에 적용했다. 제품 소스와 실제 검사·사후 백업 복원 증거는 [진행 기록](../docs/planning/progress.md)을 따른다. 기존 private 자료·계정/세션·실행을 보존하며 main/운영은 유예한다. 공개0007 테이블의 사전 백업·소유자 migration/최소 권한·별도 복원과 웹/API 경계 검증 절차는 [실행 개발 계약](research-development.md)을 따른다. 아래 초기 서버 기록을 새 게시/적용 완료 증거로 사용하지 않는다.


2026-10-12 한국 시간. 사용자 전용 환경에서 최신 실행 코드를 설치하고 웹/API와 SSH 터널을 검증했다. **IssueDigest 저장소는 공개**다. 접속 주소·SSH 계정·개인 키 경로는 이 문서와 Sites에 기록하지 않는다.

접속 세부정보는 이 작업 컴퓨터의 `~/.local/state/issuedigest/connection.json`(권한 600)과 서버 계정의 `~/ISSUEDIGEST-SETUP.md`에서 확인한다. 개인 키는 저장소 밖 SSH 경로에 보관한다. 최초 접속 때 받은 호스트 키를 전용 known_hosts에 기록했으며 별도 경로의 fingerprint 대조는 수행하지 않았다.

이전 서버 안내에서 저장소를 비공개라고 잘못 표기했다. 후속 문서에서 접속 주소·계정·키 경로를 제거했지만 이전 커밋/PR의 메타데이터는 남아 있다. 개인 키 본문·인증값은 Git에 올리지 않았다. 저장소 가시성이나 Git 이력은 변경하지 않았다.

## 설치·실행 위치

| 항목 | 준비 상태 |
| --- | --- |
| 기준 코드 | `806e22e684714ee547b6e3d1247ca9fe33c83664` · 원문/연구/실행 계약까지 포함한 서버 안내 브랜치 |
| 서버 작업 공간 | `~/IssueDigest/worktree/jaesin-development` · `codex/jaesin-development` |
| 환경 선택 | `~/.config/issuedigest/development-env.sh` · PATH만 설정 |
| 도구 설치 | `~/.local/share/issuedigest/tools/` · 기존 공유 시스템 도구 보존 |
| Python | uv 사용자 관리 Python 3.13.12, worktree의 `.venv` |
| 실행 세션 | `issuedigest-jaesin-dev` · `api`, `web` 두 tmux 창 |
| 개발 웹 / API | `127.0.0.1:15173` / `127.0.0.1:18090` |

서버 main은 초기 커밋의 깨끗한 상태로 보존한다. remote fetch 후 현재 실행 코드가 포함된 브랜치로 작업 worktree를 만들었다. 서버 저장소의 로컬 `.git/info/exclude`에 `/worktree/`를 추가해 main 작업 폴더에 중첩 worktree가 미추적 변경으로 나타나지 않도록 했다. GitHub PR 병합·서버의 main checkout 변경은 수행하지 않았다.

## 자원·권한

초기 읽기 확인: Ubuntu 22.04.5 LTS · ARM64(aarch64) · 논리 CPU 4개. 메모리 총 약 23.4GiB/가용 12.9GiB, 홈 파일시스템 총 약 193.6GiB/여유 약 39GiB, swap 총16GiB/여유 약4GiB. 공유 서버의 순간 관측값이며 전용 할당량이나 비용이 아니다. 공존 서비스·현재 부하·swap 사용 원인은 미조사다.

안내상 sudo 권한이 없으며 Docker 설치는 있으나 소켓 관리 권한은 없다. 사용자 전용 도구·작업 환경은 구성했지만 DB·컨테이너·리버스 프록시·외부 포트 개방·운영 서비스는 구성하지 않았다. 관리자와 자원 배정·월 분담 비용·DB/백업 운영 방법을 협의해야 한다.

## 도구 버전

| 도구 | 기존 설치 | 검증한 프로젝트 환경 |
| --- | --- | --- |
| Node | 공유 24.19.0 | 사용자 전용 24.21.0 |
| npm | 공유 11.17.0 | 사용자 전용 11.19.0 |
| pnpm | 공유 11.16.0 | 사용하지 않음, npm lockfile 유지 |
| Python | 시스템3.10.12 · 사용자3.12.15 | 사용자 관리3.13.12 |
| uv | 기존 사용자 설치0.13.0 | 프로젝트 전용0.11.4 |
| tmux | 3.2a | 기존 도구 사용 |

Node ARM64 공식 아카이브를 공식 SHASUMS256과 대조했고 uv는 공식 GitHub release의 지정 버전 ARM64 아카이브로 설치했다. `npm ci --no-audit --no-fund`와 `npm run setup`으로 lockfile에 따라 설치했다. 고정 버전·lockfile·제품 코드 변경이나 peer 의존성 우회는 없다. 기존 시스템 Node/npm 및 기존 사용자 uv 버전은 준비 후 다시 확인했다.

## 실행·다시 접속

서버에 SSH로 로그인한 다음 기존 세션으로 돌아간다:

```sh
tmux attach -t issuedigest-jaesin-dev
```

새 터미널에서 작업할 때는 환경을 선택하고 작업 공간으로 이동한다:

```sh
source ~/.config/issuedigest/development-env.sh
cd ~/IssueDigest/worktree/jaesin-development
node --version
npm --version
python3 --version
uv --version
```

세션을 새로 구성하거나 앱을 별도로 실행할 때 각 터미널에서 다음 명령을 사용한다. 이미 실행 중인 포트를 중복 실행하지 않는다.

```sh
# API 터미널
uv run --package issuedigest-api uvicorn issuedigest_api.main:app \
  --reload --host 127.0.0.1 --port 18090 --no-access-log

# 웹 터미널
API_PROXY_TARGET=http://127.0.0.1:18090 \
  npm run dev --workspace @issuedigest/web -- --port 15173
```

루트 `npm run dev`의 기본 로컬 포트는 5173/8000이다. 공유 서버에서는 위 명령으로 지정 포트를 전달한다. 두 서버는 loopback에만 바인딩하며 포트는 OS 독점 예약이 아니다.

로컬 컴퓨터에서 개인 접속 안내에 따라 SSH 터널을 연다. 아래 접속 대상/키 경로는 개인 설정으로 바꾸는 예시다:

```sh
ssh -N -i /path/to/private-key \
  -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:15173:127.0.0.1:15173 \
  -L 127.0.0.1:18090:127.0.0.1:18090 \
  SSH_ACCOUNT@SSH_HOST
```

개인 접속 안내의 known_hosts 설정도 적용한다. **터널이 열린 컴퓨터**에서 `http://127.0.0.1:15173`로 웹을 확인한다. 다른 컴퓨터에서는 자신의 터널이 필요하다. 이 작업 컴퓨터의 개발용 터널은 실행 상태로 유지했다.

앱 세션 종료는 `tmux kill-session -t =issuedigest-jaesin-dev`다. 직접 종료 후 두 포트가 해제되는 것을 확인하고 같은 구성으로 재시작했다. tmux는 SSH 연결 종료 후 앱을 유지하지만 호스트 재부팅 후 자동 시작하는 운영 서비스가 아니다.

## 검증 결과

- ARM64 worktree에서 `npm run check` 전체 성공: Python672개 + JS60개, Ruff/format·mypy·ESLint·TypeScript·SPA 빌드·생성 계약 drift 통과. 추적 파일 변경 없음.
- 서버 직접 API 및 웹 프록시, 로컬 SSH 터널 직접 API 및 웹 프록시에서 `/health/live`, `/api/v1/status` HTTP200·정확한 JSON·UUID v4 요청 ID 확인.
- 실제 API `/openapi.json`이 커밋된 계약과 일치하며 기존 두 HTTP 경로만 제공.
- SSH 터널의 브라우저에서 화면 hydration과 연결 버튼의 실제 성공 확인. 1366×900, 390×844에서 가로 넘침 없음; 콘솔 오류·경고 각0건.
- tmux 세션 종료 후 15173/18090 해제, 재시작 후 직접 API와 웹 프록시 정상 응답. 세션·터널은 인계 시 실행 상태.
- 화면 산출물은 로컬 `output/playwright/issuedigest-server-ready/`에 보존하며 커밋하지 않는다.

현재 제품은 빈 자료 화면과 API 상태 확인까지 제공한다. 실제 데이터·DB·AI·생성 화면·앱 인증은 아직 미연결이다. 이 검증을 전체 P1·운영 배포 완료로 간주하지 않는다. GitHub 읽기는 확인했고 이 서버의 개인 push 인증/쓰기 권한은 검증하지 않았다. 현재 PR 게시에는 기존 작업 컴퓨터의 GitHub 인증을 사용한다.

## 다음 확인

1. 관리자와 전용 자원·공존 서비스·월 분담 비용·외부 백업·런타임 계정 분리 확인.
2. 전용 PostgreSQL18.6·기존 28테이블·원문 경로·기간·스냅샷은 [실측](../docs/research/server-data-inventory.md)에서 확인했다. 현재 수집 성공·누락·운영 실행 커밋·원문의 정확한 대응은 후속이다.
3. D011의 PostgreSQL·pgvector·PydanticAI/DBOS를 사용한다. pgvector 패키지는 미준비다. A005~A006의 배치·인증과 D012 도메인 연결은 대기하며 [PostgreSQL 연결 준비](postgresql.md)의 남은 조건을 확인한다.

최신 상태는 [진행 기록](../docs/planning/progress.md), 선택은 [결정 기록](../docs/planning/decisions.md)을 따른다.


## Google OAuth 개발 연결 · 2026-10-13

코드는 Google 로그인·명시 초대·서버 세션·공동 자료 목록/읽기를 지원한다. 이 서버의 기본 개인 개발 세션은 미설정 앱으로 유지하며 실제 OAuth·공동 DB를 연결했다고 표시하지 않는다. 기존 앱 계정의 비밀 설정이 아직 읽히지 않으므로 개발자의 DDL 계정으로 앱을 실행하지 않는다. 필요한 환경변수·HTTPS·등록된 callback·명시 마이그레이션/초대 준비는 [API 안내](../apps/api/README.md)를 따른다.

실제 callback의 code/state가 개발 로그에 남지 않도록 API 실행에는 `--no-access-log`를 사용하고 웹은 지원되는 npm 개발 실행 경로를 쓴다. 설정된 OAuth runtime은 별도 opt-in이다. 운영 Nginx 로그·HTTPS/라우팅은 공개 OAuth 전에 별도 확인해야 하며, 개발 프록시 검증으로 운영 설정을 인증하지 않는다. main·공용 checkout·운영 서비스 변경이나 첫 앱 게시를 수행하지 않는다.


## 최신 인계 검증 · Google 로그인 코드

`29a152d`의 Google 로그인·자료 목록 코드를 개인 worktree로 fast-forward하고 upstream을 `origin/feat/google-oauth-workspace`로 연결했다. 고정 의존성 설치와 ARM Google 서명/설정/runtime103개·개발 launcher13개, 타입·SPA·계약을 확인했다. 실제 공동 DB를 테스트하지 않아 조건부 PostgreSQL1개는 skip이다. controller와 코드 CI의 별도 합성 PostgreSQL 전체 검증과 구분한다.

기존 API reloader의 자식이 종료된 상태에서 포트만 유지해 응답하지 않았으며, UID·개인 cwd·명령·그룹을 확인한 해당 개발 프로세스만 재시작했다. 웹 wrapper의 CLI 인수 누락은 TDD와 독립 리뷰로 보완했다. 실제 15173/18090의 헬스·상태와 로그인 화면200, API OpenAPI의 저장 계약 일치를 확인했다. API는 access log 없이 실행하고 웹은 지원 wrapper를 사용한다. 기본 미설정 runtime을 유지하며 실제 Google 계정·공동 DB·운영 서비스는 연결하지 않았다. 공유 checkout·main·공개 앱은 변경하지 않았다.

## 2026-10-14 · 실제 Google 개발 runtime 연결

기존 개인 tmux API를 `issuedigest_api.runtime:create_configured_app --factory --no-access-log`로 구성했다. 기존 앱 역할과 개인 Google 설정만 사용하며 스키마/권한을 바꾸지 않는다. 개인 웹은 기존15173, API18090의 loopback binding이다. Google용 HTTPS origin은 기존 등록된 `https://localhost:16173`이다. 서버 개인 파일의 명시 loader가 접속 URI를 메모리에서 psycopg 형식으로 정규화한다. 비밀 파일을 제품 코드에서 자동 탐색하지 않는다.

개인 SSH 터널과 개발용 자체 서명 HTTPS bridge에서 인증 전 상태/Origin 방어·start/취소flow를 확인했다. 사용자 앱 내 미리보기에서는 인증서 신뢰가 거부되고 포트가 바뀌므로 실제 Google 로그인에 사용할 수 없었다. 사용자 SSH/인증서 설정 요구는 중단하고 고정 HTTPS 개발 주소와 Google callback을 준비해야 한다. 설치된 Nginx 설정은 읽기 가능하나 개발 계정 쓰기 권한이 없다. 사용자 로그인과 공개 앱 연결은 미완료다. [현재 결과·경계](../docs/changes/google-login-runtime.md)를 따른다.


## 정책뉴스 반복 확보 · 개인 수집기 · 2026-10-18

소스`a908083`의 별도 collector worktree/가상환경과0008 수집 journal을 개인 개발에 적용했다. 기존 개발 앱/API/연구 worker는 유지한다. 승인한 고정 기사1건을 매시17분에 다시 확보하며 최소 간격3,300초·마지막 성공 완료 기준age 한도7,200초·총720시도·프로세스timeout120초/종료 유예10초다. 첫 실제 수동 실행·원본/보고서 해시·상태·즉시 not_due를 확인했다. 첫 cron tick은 기본 Python3.10으로 시작하며 import 실패했고, 실행기 shebang을 전용 Python3.13 절대 경로로 고정했다. 이후 cron의 최소 HOME/PATH·비로그인 shell에서도 exit0/not_due·외부 요청0을 확인했다. 실패 로그는 보존하고, 수정 후 미래 tick의 확보 성공은 별도 관측 사항이다.

원문/실행 로그·job·기존 소유자 DB 설정은 서버의 private 파일에만 둔다. 실행은 별도 `~/.local/bin/issuedigest-policy-collection`, job은 `~/.config/issuedigest/policy-collection/collection-job.json`, 집계 로그는 `~/.local/state/issuedigest/policy-collection/poll.log`다. source HEAD를 고정 검증하므로 collector 소스 갱신 시 실행기도 함께 검토해야 한다. 키/DSN/기사·collection 식별자를 Git·공개 로그에 복사하지 않는다. 기존 앱 자격/권한을 확대하지 않고 기존 개발자 DB 권한을 사용했다.

상태는 기존 명시 `issuedigest-policy status PRIVATE_JOB`로 읽는다. DB URL은 서버 설정을 메모리에서 psycopg 형식으로 정규화해 전달하며 값을 출력/명령 인수로 노출하지 않는다. status는 row·HTTP·모델 호출을 만들지 않는다. 매 실행을 추가 확보로 오인하지 않고 busy/not_due/attempt_limit와 실제 실패를 구분한다. 운영자 SDK/설정 형식은 [worker 문서](../apps/worker/README.md)와 [변경 명세](../docs/changes/policy-collection-journal.md)를 따른다.

중지하려면 개인 `crontab -e`에서 `# issuedigest-policy-collection` 표시가 붙은 해당 줄만 제거하고 다른 줄을 보존한다. 재개할 때도 같은 불변 job/원본/시도 한도를 유지하며 자동 초기화·원본 삭제를 하지 않는다. 실패 이력·마지막 성공·DB 용량/720회 상한을 확인해 후속 정책을 검토한다. 원본 확보는 검색 색인 편입/브리핑/공개 게시가 아니다. 실제 전후 백업·별도 복원·기존20앱 테이블/추가 journal 포함22테이블 일치와 외부 HTTPS 결과는 [진행 기록](../docs/planning/progress.md)에 남긴다. 역할/vector를 포함한 완전 재해 복구나 main/운영 출시 완료를 뜻하지 않는다.


## 2026-10-18 · 승인 편입·최신 검색 개인 개발 적용

제품b63c7fa의 API/조사 worker를 별도 소스·Python3.13 가상환경으로 갱신했다.0009와 기존 앱의 새 receipt SELECT만 적용하고, default grants로 자동 붙은 쓰기는 해당 새 테이블에서만 제거했다. 활성 작업0 확인·정상 종료/기동·단일 worker 잠금·한 건 기준 버전 편입/같은 승인 재실행·앱 계정 최신 검색과 과거 인용·사후23테이블 일치 복원을 확인했다. 원래 정적 웹·collector a908083/config/일정·이전 앱 worktree와 계정/세션·공개v1·main/운영 유예는 보존했다. 수집기 수정 후 실제 예약 성공도 확인했고0009 이후 read-only status가 정상이다. 실행 접속·개별 승인·키는 비공개 보관하며 상세 증거는 진행 기록을 따른다.


## 2026-10-19 · 소비자 브리핑 정적 디자인

[명세/인수](../docs/changes/consumer-briefing-design.md)의 정적 웹4cd8f62만 별도 고정 소스에서 빌드해 개인 개발 Nginx root에 반영했다. 이전asset83개와 원래root/설정은 롤백용으로 유지한다. reload 신호 직후에는 기존 worker가 잠시 응답할 수 있으므로 새 index 제공을 bounded 확인한다. 설정 교체는 원자적이며 실패하면 이전 설정으로 복귀한다. 실제 HTTPS·새 CSS/문구·두 테마·모바일/PC·비회원 읽기/정확 원문/로그인 초안을 검증했다. 오래 켜 둔 화면은 일반 새로고침으로 새 빌드를 읽는다.

API/조사 worker는b63c7fa 그대로이며 PID·명령/cwd가 전후 같다. 수집기a908083·설정/실행기/주기도 유지한다. DB·세션·공개 자료·OAuth·외부TLS·main/운영을 변경하지 않았다. 실제 유료 생성/사용자 로그인을 대신 수행하지 않았고 사용자 탭도 이동하지 않았다. 이전 절의 초기 서버 준비 상태는 해당 시점의 기록이며 현재 인수/출판 상태는 진행 기록을 따른다.


## 2026-10-19 · 공식 목록 후보·검토한 자료 추가

[명세/인수](../docs/changes/policy-source-candidates.md)의 도구 소스93ab7c8을 기존 앱과 분리한 전용 worktree/가상환경에서 실행했다. 목록 날짜/발행처·이전 관측 보고서는 오프라인이며, 실제 원본은 private에 보존한다. 개별 공공누리1 텍스트·발행일·본문/정확 인용을 검토한 새 공식 자료1건을 기존 provision·표시/검색 경로로 명시 추가했다. 같은 계획 재실행은 신규0이며 초대2개는 변경하지 않았다. schema0009/권한 변경은 없다.

정적 웹4cd8f62·API/조사worker b63c7fa의 PID/명령/cwd·수집기a908083의 source/config/실행기/주기는 전후 동일하다. HTTPS home/login/health/status/공개v1은200, 비회원session401/no-store/noCookie와 화면/공개본 hash를 보존했다. 서버 밖 사전·직전·사후 full/app 백업과 사후 별도PG18.6 복원의23테이블 row hash/count 일치, 기존 전체 행 보존·자료 버전15/인용49/검색36/receipt1/공개1·앱 계정 read-only 검색3문항을 확인했다. vector/역할까지의 완전 재해복구 검증은 아니다. 모델·OAuth·자동 게시·새 cron·main/운영 변경은 없다. 개인 승인 원문/ID/계정/접속/키·백업은 저장소 밖에 보존한다.


## 브리핑 답변 품질 개발 적용 · 2026-10-19 KST

제품f90839e의 정적 웹/API/조사 worker를 별도 고정 소스·locked runtime에서 함께 갱신했다. 활성run/workflow0 후 정상 종료/시작·단일 worker 잠금1·외부 HTTPS·새 웹 자산6개 hash·공개/보호 경계를 확인했다. 새 정적 파일19개와 이전asset82개·소스/환경은 롤백용으로 남겼다. 테마/읽기 디자인은 유지하고 새 privatev5 검증/표시만 추가했다. 실제 사용자 로그인/질문을 대신하지 않았다.

schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·수집기a908083/source/config/실행기/주기는 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도 PG18.6 app 복원을 수행해23개 public 테이블 rowhash/count 일치를 확인했다. DBOS registry는 public 감사 밖이며 vector/역할의 완전 재해복구 검증은 아니다. main/운영·DNS/TLS·권한은 변경하지 않았다. 실제 모델 초기4+별도 구조2의 의미 한계와 Sites 최종 상태는 [진행 기록](../docs/planning/progress.md)을 따른다.
