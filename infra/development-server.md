# 개발 서버 안내·확인 기록

2026-10-12 한국 시간. 사용자가 전달한 안내와 SSH 읽기 전용 확인을 구분한다. 이 문서는 비공개 저장소용이며 접속 주소·계정은 공개 Sites에 복사하지 않는다. 키·인증값은 포함하지 않는다.

## 접속과 작업 위치

| 항목 | 값 |
| --- | --- |
| SSH | `DigestWorks_Jaesin@140.245.74.246:22` |
| 서버 저장소 | `/home/DigestWorks_Jaesin/IssueDigest` |
| 서버 안내 | `~/ISSUEDIGEST-SETUP.md` |
| 계정별 작업 공간 | `~/IssueDigest/worktree/` 아래 Git worktree, 작업별 브랜치 |
| 개발 웹 / API | `127.0.0.1:15173` / `127.0.0.1:18090` |
| 관리자 작업 | 민재님에게 설치·서비스·호스트 Docker 설정 요청 |

전달된 키는 사용자 요청에 따라 저장소 밖 `/home/xinics/.ssh/issuedigest-jaesin.pkcs8.pem`으로 옮기고 권한을 `600`으로 설정했다. 키는 이 컴퓨터의 로컬 접속용이며 서버나 Git에 복사하지 않는다. 첫 SSH 접속에서 받은 호스트 키는 전용 `known_hosts_issuedigest` 파일에 기록했다. 별도 경로로 fingerprint를 대조한 것은 아니다.

이 컴퓨터에서의 접속:

```sh
ssh -i /home/xinics/.ssh/issuedigest-jaesin.pkcs8.pem \
  -o UserKnownHostsFile=/home/xinics/.ssh/known_hosts_issuedigest \
  -o StrictHostKeyChecking=yes \
  DigestWorks_Jaesin@140.245.74.246
```

## 직접 확인한 상태

| 항목 | 2026-10-12 확인 결과 |
| --- | --- |
| SSH 계정 | 안내 계정으로 로그인 성공 |
| OS / CPU | Ubuntu 22.04.5 LTS · ARM64(aarch64) · 논리 CPU 4개 |
| 메모리 | 총 약 23.4GiB · 가용 약 12.9GiB |
| Swap | 총 16GiB · 여유 약 4GiB. 사용 원인·현재 부하는 미조사 |
| 홈 파일시스템 | 총 약 193.6GiB · 남은 약 39.0GiB |
| 지정 포트 | 확인 시점에 15173 / 18090 TCP listener 없음. OS 독점 예약은 아님 |
| 권한 | 안내상 sudo 없음. Docker 설치는 있으나 소켓 접근 권한 없음 |
| 서버 Git | 깨끗한 `main`, `ba47f3aa8fbf2996abd3edc1c5f05588d5093942`; 추적 파일 `.gitignore`, `README.md` |
| GitHub 읽기 | 서버에서 `git ls-remote` 성공. 쓰기 권한·개인 push 인증은 미검증 |

가용 자원은 공유 서버의 순간 관측값이다. IssueDigest 전용 할당량·공존 서비스·월 비용·백업 공간이 확정된 것은 아니다. 서버 커널 이름만으로 클라우드 요금이나 무료 사용 여부를 추정하지 않는다. ARM에서 사용할 의존성·컨테이너 이미지의 호환성도 설치 단계에서 검증해야 한다.

## 개발 도구 차이

| 도구 | 서버 확인 | 저장소 고정 기준 | 다음 조치 |
| --- | --- | --- | --- |
| Node | 24.19.0 | 24.21.0 | 사용자 전용 설치/버전 선택 |
| npm | 11.17.0 | 11.19.0 | 저장소 기준으로 맞춤 |
| pnpm | 11.16.0 | 사용하지 않음 | `package-lock.json`과 npm 유지 |
| Python | 시스템 3.10.12 · uv 관리 3.12.15 | 3.13.12 | 사용자 전용 설치, 저장소 uv 환경 사용 |
| uv | `~/.local/bin/uv` 0.13.0 | 0.11.4 | 프로젝트용 버전 선택. SSH 비대화 세션의 PATH에는 현재 없음 |
| tmux | 3.2a | 고정 기준 없음 | 세션 유지에 사용 가능 |
| Docker | 27.2.1, 소켓 접근 불가 | 배치 미확정 | DB·운영 배치안 마련 후 관리자와 협의 |

서버의 임시 `~/.venvs/issuedigest`를 프로젝트 환경으로 채택하지 않는다. 고정 버전과 lockfile을 기준으로 맞추며 공유 시스템 도구는 교체하지 않는다. 이번 확인에서는 도구·의존성 설치와 서버 설정을 변경하지 않았다.

## 사용할 코드와 포트

계획은 `docs/issuedigest-implementation-plan`, 현재까지의 실행 코드·제품 계약은 `feat/execution-contracts`에 있다. 읽기 확인 당시 실행 코드 기준은 `baf80d80e43edf6b871bd8332b9e9bb6e5b38bd4`다. PR #1~#6이 Draft·미병합이므로 `main`에 실행 코드가 없는 상태는 로컬 구현과 모순되지 않는다. 서버의 원격 참조는 초기 계획까지만 가져온 상태였으며 GitHub 읽기 요청에서는 최신 실행 브랜치가 확인됐다.

다음 준비 시 저장소 상태를 다시 확인하고 원격을 fetch한 뒤, 최신 실행 브랜치를 바탕으로 별도 작업 브랜치/worktree를 만든다. `main` 변경·PR 병합은 이번 범위에 포함하지 않는다.

아래는 코드 checkout과 고정 도구·의존성 설치 **후** 사용할 명령안이다. 원격 실행은 아직 검증하지 않았다. 루트 `npm run dev`는 기본 로컬 포트 5173/8000을 사용하므로 이 공유 서버에서는 두 앱에 지정 포트를 각각 전달한다.

```sh
# 서버의 작업 worktree 루트, API 터미널
uv run --package issuedigest-api uvicorn issuedigest_api.main:app \
  --reload --host 127.0.0.1 --port 18090

# 같은 worktree 루트, 웹 터미널
API_PROXY_TARGET=http://127.0.0.1:18090 \
  npm run dev --workspace @issuedigest/web -- --port 15173
```

로컬 컴퓨터에서 SSH 터널을 열면 개발 서버 포트를 외부에 공개하지 않고 확인할 수 있다:

```sh
ssh -i /home/xinics/.ssh/issuedigest-jaesin.pkcs8.pem \
  -o UserKnownHostsFile=/home/xinics/.ssh/known_hosts_issuedigest \
  -o StrictHostKeyChecking=yes -o ExitOnForwardFailure=yes \
  -N -L 15173:127.0.0.1:15173 -L 18090:127.0.0.1:18090 \
  DigestWorks_Jaesin@140.245.74.246
```

앱 실행 뒤 `http://127.0.0.1:15173`에서 접속한다. 터널·앱 기동은 후속 검증이며 개발 서버를 운영 배포로 간주하지 않는다. 현재 앱은 상태 확인만 제공하고 DB·자료 수집·AI·생성 UI는 아직 연결 전이다.

## 남은 확인과 다음 순서

1. 사용자 전용 도구 버전을 맞추고 최신 실행 코드의 작업 worktree 준비.
2. lockfile 설치·전체 검사와 지정 포트의 웹/API·SSH 터널 연결 검증.
3. 관리자와 자원 배정·공존 서비스·월 분담 비용·외부 백업·DB 운영 권한 확인. 기존 수집/AI 서버와 이 개발 서버가 같은 대상인지도 확인 필요.
4. 기존 데이터 위치·건수·기간·최근 수집 성공·실행 커밋 확인. 다른 계정·서비스·운영 데이터는 이번에 탐색하지 않았다.
5. 확인된 자원과 월 10만 원 한도를 기준으로 A001~A003, A005~A006의 DB·검색·실행기·배치·인증을 판단.

접속 확인으로 B001의 개발 계정·기초 자원은 일부 해소했지만 B002의 데이터 현황과 운영 배치 결정은 여전히 대기다. 최신 작업 상태는 [진행 기록](../docs/planning/progress.md), 선택은 [결정 기록](../docs/planning/decisions.md)을 따른다.
