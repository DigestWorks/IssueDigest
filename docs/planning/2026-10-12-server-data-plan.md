# IssueDigest 서버·데이터 연결 계획

IssueDigest는 독립 프로젝트로 개발하며, 전용 DB를 구성하고 서버 자원·비용 추가 확보와 기존 데이터 접근을 이어서 진행한다.

- 결정일: 2026-10-12
- 저장소: https://github.com/DigestWorks/IssueDigest
- PostgreSQL 검증 기준: 18.6
- pgvector: 추후 검토
- 기존 수집 데이터: 읽기 접근 후 종류·건수·수집 상태 확인

## 전용 DB

2026-10-12 Oracle 서버에 전용 PostgreSQL 18.6 인스턴스와 `issuedigest` DB를 구성했다. 접속 주소는 서버 내부 `127.0.0.1:15432`이다. `DigestWorks_Jaesin`은 스키마와 데이터를 관리하며, 앱용 `issuedigest_app`은 데이터 읽기·쓰기 권한을 갖는다.

접속 정보는 개발 계정 전용 파일에 저장했다. 초기 백업·복원 검증을 완료했으며, 정기 백업과 외부 보관은 후속 구성 항목이다. [접속·운영 안내](../../infra/postgres/README.md)에 설정과 검증 결과를 기록했다. pgvector는 추후 검토한다.

## 기존 데이터 접근

LawDigest 코드·DB·원문은 재사용 가능성을 확인할 자료로 다룬다. 개발 계정에는 비밀 설정을 제외한 코드 열람본, 원문 파일 읽기 권한, 기존 DB의 SELECT 전용 계정을 제공한다. 데이터 종류·건수·수집 상태는 접근을 확보한 뒤 개발자가 직접 확인한다.

2026-10-12 Oracle 서버 `140.245.74.246`에서 확인한 위치는 다음과 같다. 파일 경로의 존재를 확인했으며, 운영 파이프라인과의 연결은 추가 확인이 필요하다.

| 대상 | 위치 |
| --- | --- |
| 기존 백엔드 | `/home/ubuntu/project/Lawdigest/services/backend` |
| 기존 AI 코드 | `/home/ubuntu/project/Lawdigest/services/ai` |
| 기존 수집 코드 | `/home/ubuntu/project/Lawdigest/services/data` |
| 기존 DB | `lawdigest-mysql` 컨테이너, 호스트 포트 `3306` |
| 원문·가공 파일 후보 | `/home/ubuntu/project/data_job/data` |
| 수집 산출물 후보 | `/home/ubuntu/project/Lawdigest/services/data/output` |

확인 당시 `DigestWorks_Jaesin` 계정은 관련 프로젝트 디렉터리에 접근할 수 없었다. 기존 코드·원문 읽기 권한과 LawDigest DB 조회 계정 제공은 후속 작업이다.

## 자원과 비용

CPU·메모리·디스크·백업 공간은 IssueDigest용으로 추가 확보한다. 서버 또는 볼륨 증설 여부, 배포 위치, 월 예산과 분담 방식은 견적을 확인한 뒤 정한다. 모델 API 비용은 서버 비용과 별도로 집계한다.

현재 Oracle 서버의 `5432` 포트는 `happy-postgres` 컨테이너의 PostgreSQL 16.13이 사용 중이다. IssueDigest의 PostgreSQL 18.6은 별도 컨테이너 `issuedigest-postgres`의 서버 내부 `15432` 포트로 운영한다. 현재 CPU 최대 0.5개·메모리 1GiB 한도를 적용했으며, 자원·비용 추가 확보 후 최종 배정을 정한다.

## 연결 완료 확인

1. 배포 위치·자원·월 비용 합의
2. 전용 DB·계정·백업 구성
3. 개발 계정의 코드·원문 열람과 기존 DB SELECT 확인
4. IssueDigest의 DB 접속과 마이그레이션 확인
5. 원문 하나를 저장·조회하고 출처가 유지되는지 확인
