# 기존 수집 데이터 접근

`DigestWorks_Jaesin` 계정에서 기존 수집 데이터와 코드·수집 상태를 읽을 수 있도록 구성했다.

- 서버: `140.245.74.246`
- 열람 루트: `/srv/issuedigest/reference`
- DB: MySQL `lawDB`, 서버 내부 `127.0.0.1:2835`
- DB 로그인: `issuedigest_jaesin_ro`
- 권한: 지정한 수집 데이터 테이블의 SELECT

## 시작

서버에 로그인한 뒤 다음을 실행한다.

```sh
ls /srv/issuedigest/reference/data
cat /srv/issuedigest/reference/manifest.json
~/.local/bin/issuedigest-legacy-db
```

DB에서 확인할 수 있는 테이블 목록과 법안 데이터 예시는 다음과 같다.

```sql
SHOW TABLES;
DESCRIBE Bill;
SELECT * FROM Bill LIMIT 5;
```

데이터 종류·건수·최근 수집 상태는 개발자가 직접 확인한다. DB 접속 파일은 `~/.config/issuedigest/legacy-mysql.cnf`이며, 해당 Linux 계정 소유·권한 `600`으로 저장했다. 환경 변수 안내는 `~/.config/issuedigest/legacy-data.env`에 있다. SQL 로그인은 서버 내부 TCP 접속에 사용되는 Docker 브리지 주소로 제한했다. 로컬 DB 도구에서는 기존 SSH 접속을 사용해 서버 `127.0.0.1:2835`로 터널을 연결한다.

## 파일 경로

| 열람 경로 (`/srv/issuedigest/reference/` 기준) | 내용 | 제공 방식 |
| --- | --- | --- |
| `code/services/backend` | 기존 백엔드 코드 | 열람용 스냅샷 |
| `code/services/ai` | 기존 AI 처리 코드 | 열람용 스냅샷 |
| `code/services/data` | 기존 수집 코드 | 열람용 스냅샷 |
| `code/docs`, `code/almanac` | 파이프라인·AI 운영 문서 | 열람용 스냅샷 |
| `data/bills`, `data/elections`, `data/polls` | 법안·선거·여론조사 산출물 | 현재 파일의 읽기 전용 마운트 |
| `data/parsed`, `data/pdfs` | 파싱 결과·원문 PDF | 현재 파일의 읽기 전용 마운트 |
| `data/ai-output` | AI 처리 산출물 | 현재 파일의 읽기 전용 마운트 |
| `data/legacy-data`, `data/legacy-output` | 기존 `data_job`의 자료·가공 결과 | 현재 파일의 읽기 전용 마운트 |
| `status/pipeline-runs.jsonl` | 실행 이벤트·실행 ID·시각 | 파라미터를 제외한 스냅샷 |

스냅샷은 2026-10-12에 만들었다. 실제 경로·원본 커밋·DB 조회 테이블 목록은 `manifest.json`에 있다. 코드의 비밀 설정과 하드코딩된 인증정보를 제거했으므로 코드는 열람용으로 사용한다. 원본 체크아웃과 기존 미커밋 문서는 보존했다.

## DB 범위

수집 런타임의 설정과 실제 연결로 `mysql` 컨테이너의 `lawDB:2835`를 확인했다. 이전에 확인한 `lawdigest-mysql:3306`의 `cloneOfLaw`는 테이블이 없는 상태였다.

조회 범위는 법안·발의·의원·정당·표결·검색 문서·수집 체크포인트·법령 용어·여론조사·선거 테이블이다. 사용자·토큰·인증·알림·사용자 반응 기록과 관리자 테이블은 제외했다. 새 테이블이 필요하면 관리자가 조회 권한을 추가한다.

## 관리자 설정과 검증

`provision.py`는 Oracle 서버에서 root로 실행하는 초기 설정 스크립트다. 기존 열람 경로나 접속 설정이 있으면 중단한다. 파일 경로·테이블 목록을 확인하고 사용한다.

- 코드와 상태 로그는 비밀 설정을 제거한 스냅샷으로 제공
- 원문 디렉터리는 계정 읽기 ACL과 읽기 전용 bind mount 적용
- 마운트 정의는 `/etc/fstab`에 기록, 변경 전 백업은 `/srv/issuedigest/fstab-before-reference`
- 수집 DB는 개별 테이블 SELECT와 동시 접속 3개 제한
- SQL 접속 도구는 세션 조회 시간 한도 30초 적용

실제 Linux 개발 계정에서 코드·원문·상태 열람과 TCP DB 조회를 확인했다. 원문 파일 쓰기, DB INSERT·DELETE·DDL, 사용자·관리자 테이블 조회 거부를 확인했다. 기존 `/home/ubuntu`와 PostgreSQL 비밀 디렉터리의 접근 제한도 유지했다. 시스템 재부팅은 수행하지 않았다.

원문 파일은 계속 갱신될 수 있으며, 코드·상태 스냅샷 갱신은 관리자가 수행한다. 원본의 새 파일 권한이 읽기를 막으면 해당 경로의 계정 ACL을 확인한다.

공식 권한 설정 근거: [MySQL CREATE USER](https://dev.mysql.com/doc/refman/8.0/en/create-user.html), [MySQL GRANT](https://dev.mysql.com/doc/refman/8.0/en/grant.html).
