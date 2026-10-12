# IssueDigest PostgreSQL

IssueDigest 전용 PostgreSQL 18.6과 개발·앱 계정을 Oracle 서버에 구성했다.

- 서버 접속 주소: `127.0.0.1:15432`
- DB: `issuedigest`
- 개발 로그인: `DigestWorks_Jaesin`
- 스키마 소유 역할: `issuedigest_owner`
- 앱 로그인: `issuedigest_app`
- 서버 설정 위치: `/srv/issuedigest/postgres`
- 데이터 볼륨: `issuedigest_postgres_data`

## 개발 계정에서 접속

SSH로 서버에 로그인한 뒤 실행한다.

```sh
~/.local/bin/issuedigest-db
```

개발 역할은 접속 시 `issuedigest_owner`로 전환된다. `public` 스키마에 테이블을 만들고 데이터를 읽고 쓸 수 있다. 앱 역할은 테이블의 SELECT·INSERT·UPDATE·DELETE와 시퀀스 사용 권한을 갖는다. 개발 역할로 생성하는 `public` 테이블과 시퀀스에는 앱 권한이 자동으로 적용된다. 다른 스키마를 사용하면 해당 스키마의 앱 권한과 기본 권한도 지정해야 한다.

개발자 접속 정보는 `~/.config/issuedigest/database.env`와 `~/.config/issuedigest/pgpass`에 저장했다. 두 파일은 해당 Linux 계정 소유이며 권한은 `600`이다. 환경 변수가 필요한 도구에서는 다음을 실행한다.

```sh
source ~/.config/issuedigest/database.env
```

앱 비밀번호는 관리자 전용 디렉터리 `/srv/issuedigest/postgres/secrets/app_password`에 있다. 앱을 배포할 때 관리자에게 서비스용 비밀 설정을 요청한다.

## 로컬 개발 도구 연결

Mac에서 기존 SSH 키 경로를 지정해 터널을 연다.

```sh
ssh -i <개인키-경로> -N -L 15432:127.0.0.1:15432 DigestWorks_Jaesin@140.245.74.246
```

DB 도구에는 호스트 `127.0.0.1`, 포트 `15432`, DB `issuedigest`, 사용자 `DigestWorks_Jaesin`을 입력한다. 비밀번호는 서버의 개발자 접속 설정에서 확인한다.

## 관리자 운영

```sh
sudo docker compose -f /srv/issuedigest/postgres/compose.yaml ps
sudo docker compose -f /srv/issuedigest/postgres/compose.yaml up -d
sudo bash /srv/issuedigest/postgres/backup.sh
```

백업 스크립트는 DB 덤프와 역할 정의를 관리자 전용 `backups/`에 저장한다. 초기 백업을 만들고 DB 덤프의 임시 DB 복원을 검증했다. 정기 백업과 외부 보관은 자원·비용 확보 단계에서 구성한다. 백업·복원에는 컨테이너의 PostgreSQL 18 도구를 사용한다. 호스트에 설치한 접속용 `psql`은 Ubuntu 제공 14.24이다.

초기화 스크립트는 빈 데이터 볼륨에서만 실행된다. 기존 볼륨의 계정·비밀번호 변경은 관리자가 SQL로 수행한다. 비밀번호 파일만 바꿔도 DB 비밀번호가 바뀌지는 않는다.

현재 DB에는 CPU 최대 0.5개와 메모리 1GiB 한도를 적용했다. 프로젝트 자원·월 비용의 최종 배정은 추가 확보 후 정한다. pgvector는 추후 검토한다.

## 검증 기록

2026-10-12 서버에서 PostgreSQL 18.6, 개발 계정의 TCP 접속·테이블 생성·읽기·쓰기, 앱 계정의 CRUD·시퀀스 사용, 앱 DDL 거부와 관리 DB 접속 거부를 확인했다. 테스트 테이블은 삭제했다. 포트는 `127.0.0.1`에만 바인딩되며, 비밀번호는 Git에 저장하지 않는다.

공식 설정 근거: [PostgreSQL Docker 이미지](https://hub.docker.com/_/postgres), [PostgreSQL 역할 설정](https://www.postgresql.org/docs/18/sql-createrole.html).
