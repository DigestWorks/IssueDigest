# IssueDigest 서버·데이터 연결 계획

IssueDigest는 독립 프로젝트로 개발하며, 서버 자원과 비용을 추가 확보한 뒤 전용 DB와 데이터 접근을 구성한다.

- 결정일: 2026-10-12
- 저장소: https://github.com/DigestWorks/IssueDigest
- PostgreSQL 검증 기준: 18.6
- pgvector: 추후 검토
- 기존 수집 데이터: 읽기 접근 후 종류·건수·수집 상태 확인

## 전용 DB

프로젝트 전용 PostgreSQL 인스턴스와 DB·계정을 준비한다. 배포 위치와 접속 포트는 추가 확보할 서버 환경에 맞춰 정한다. 앱 실행 계정과 스키마 변경 계정의 권한을 구분한다. 설치·백업·확장 설정은 관리자가 수행한다. pgvector 채택 시 해당 PostgreSQL 버전에 맞는 확장을 설치한다.

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

확인 당시 `DigestWorks_Jaesin` 계정은 관련 프로젝트 디렉터리에 접근할 수 없었다. 읽기 권한 제공과 DB 계정 생성은 후속 작업이다.

## 자원과 비용

CPU·메모리·디스크·백업 공간은 IssueDigest용으로 추가 확보한다. 서버 또는 볼륨 증설 여부, 배포 위치, 월 예산과 분담 방식은 견적을 확인한 뒤 정한다. 모델 API 비용은 서버 비용과 별도로 집계한다.

현재 Oracle 서버의 `5432` 포트는 `happy-postgres` 컨테이너의 PostgreSQL 16.13이 사용 중이다. IssueDigest의 PostgreSQL 18.6 배포 위치와 포트는 별도로 정한다.

## 연결 완료 확인

1. 배포 위치·자원·월 비용 합의
2. 전용 DB·계정·백업 구성
3. 개발 계정의 코드·원문 열람과 기존 DB SELECT 확인
4. IssueDigest의 DB 접속과 마이그레이션 확인
5. 원문 하나를 저장·조회하고 출처가 유지되는지 확인
