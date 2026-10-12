# 저장·검색·실행 엔진 선택

2026-10-12 확인. **선택: PostgreSQL + pgvector + PydanticAI/DBOS(D011).** 두 사용자의 조사·근거 비교, 월 합계 10만 원, PoC/운영 동일 엔진 조건으로 사용자가 채택했다. 검색 품질·복구·운영비 실측은 후속이며 보편적으로 가장 우수한 스택이라는 결론은 아니다.

## 선택 이유와 비교 이력

| 영역 | 채택 이유 | 기존 대안과의 비교 | 아직 검증할 것 |
| --- | --- | --- | --- |
| 기준 DB: PostgreSQL | 문서·인용·버전·실행·예산·outbox를 관계·제약·트랜잭션으로 묶고 같은 DB에서 벡터 투영 가능 | MySQL도 관계/트랜잭션과 CJK ngram 검색을 지원한다. 선택 이유는 MySQL의 불가능성이 아니라 pgvector·DBOS 조합과 운영 구성의 수 | 마이그레이션·동시 쓰기·이관·백업 복원·전용 자원 |
| 벡터: pgvector | 기준 데이터와 벡터 색인을 같은 PostgreSQL에 두어 별도 검색 서비스 운영 부담을 줄임 | OpenSearch/Nori의 전문 검색 장점은 있었으나 첫 규모에서 별도 운영 서비스로 채택하지 않음. 한국어 형태소 품질은 pgvector가 제공하지 않음 | 정확 ID·어휘·의미 검색 결합, 기간/출처 필터 후 기대 근거·지연·메모리 |
| 에이전트: PydanticAI | Python 도메인·검증 모델·도구 계약을 공유하고 DBOS 내구 실행 연결 가능 | 도구 호출/구조화 결과를 직접 구현하는 것보다 framework 경계를 사용. UI renderer·권한·비용 원장을 대신하지 않음 | 도구 선택·명세 검증·MCP 호출·생성 결과 유용성 |
| 내구 실행: DBOS | PostgreSQL에 실행 이력을 두며 별도 실행 서비스 운영 구성을 줄일 수 있음 | Temporal의 실행 서비스·장기 작업 운영 장점보다 현재 규모의 구성 단순화를 우선. 고가용성·운영 경험이 자동 확보되지는 않음 | 중단/재시작·진행 작업 버전·도구 중복·취소·재접속·월 비용 |

공식 근거: [PostgreSQL JSONB](https://www.postgresql.org/docs/18/datatype-json.html), [MySQL CJK ngram](https://dev.mysql.com/doc/refman/8.4/en/fulltext-search-ngram.html), [pgvector](https://github.com/pgvector/pgvector), [DBOS workflow](https://docs.dbos.dev/python/tutorials/workflow-tutorial), [PydanticAI DBOS 통합](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/). 운영 구성이 줄어든다는 판단은 이 제품 규모·선택 조합에 대한 설계 추론이며 비용 견적은 아니다.

## 현재 버전과 첫 구현 경계

[PostgreSQL 지원표](https://www.postgresql.org/support/versioning/)에서 최신 안정 18 계열 minor는 **18.6**, 지원 종료는 2030-11-14다. 19 beta는 첫 기준으로 쓰지 않는다. 전용 로컬 합성 DB에서 PostgreSQL18.6 실제 서버 버전을 확인했다. Docker `postgres:18.6-bookworm` manifest의 amd64/arm64 지원을 확인했으며 이는 개발 서버의 설치·자원 배정 완료를 뜻하지 않는다.

첫 저장 구현은 SQLAlchemy **2.1.4**·Alembic **1.20.0**·psycopg **3.3.6**을 고정한다. 2026-10-12 공식 PyPI 메타데이터의 안정 버전·Python 요구 범위를 확인했고 실제 Python3.13 설치/검사는 변경의 검증 결과로 기록한다. [SQLAlchemy2.1 문서](https://docs.sqlalchemy.org/en/21/), [SQLAlchemy 배포](https://pypi.org/project/SQLAlchemy/2.1.4/), [Alembic 배포](https://pypi.org/project/alembic/1.20.0/), [psycopg 배포](https://pypi.org/project/psycopg/3.3.6/).

pgvector 공식 README는 **0.8.7**을 안내한다. 해당 extension·embedding 차원·인덱스·ARM 이미지의 실제 조합은 검색 구현 때 고정·검증한다. 이번 저장 패키지는 벡터 열/검색을 구현하지 않는다. PydanticAI/DBOS도 실행 연결 때 필요한 배포 버전·호환성·운영 메타데이터를 고정한다. 선택된 엔진과 아직 설치하지 않은 기능을 구분한다.

## 검색에서 빠뜨리지 않을 조건

한국어 형태소 분석이 PostgreSQL 기본 설정이나 벡터 검색에서 자동 해결된다고 가정하지 않는다. 정확 번호·이름과 한국어 어휘 검색을 별도 경로로 만들고 의미 검색과 합친다. `pg_trgm`은 문자열 유사도·부분 일치 도구이며 형태소 분석기의 대체라는 근거는 없다. [PostgreSQL 사전](https://www.postgresql.org/docs/18/textsearch-dictionaries.html), [pg_trgm](https://www.postgresql.org/docs/18/pgtrgm.html).

pgvector 근사 인덱스는 필터 적용 뒤 반환 후보가 부족할 수 있다. workspace·기간·출처 필터를 포함해 exact 검색과 비교하고 인덱스/iterative scan 설정을 검증한다. 점수가 높은 결과만으로 인용 정확성이나 주장 지지를 판정하지 않는다. [pgvector filtering/iterative scans](https://github.com/pgvector/pgvector#filtering).

평가는 실제 질문 20개와 이용 가능한 원문 30~50건으로 시작한다. 법안 번호·이름·동명이인·시점·출처, 여론조사의 문항/표본 조건, 근거 없음 질문을 포함한다. 결과별 원문 anchor 일치·기대 근거·필터 준수·지연·사용 비용을 기록한다. 현재 합성 계약/저장 테스트는 이 검색 평가의 대체가 아니다.

## 실행 연결의 필수 경계

현행 통합은 `DBOSDurability` capability를 붙이고 자신의 `@DBOS.workflow` 안에서 agent를 실행한다. deprecated `DBOSAgent` wrapper를 새 기본 구현으로 사용하지 않는다. agent/toolset은 DBOS launch 전에 등록하고 안정된 이름/ID를 유지한다. 예제의 SQLite URL을 복사하지 않고 PostgreSQL URL을 명시한다. 스트리밍·observer event·취소는 workflow/step 경계를 따라 전달·재생 방식이 달라지므로 앱의 저장 이벤트 순번을 전달 기준으로 삼는다. SDK·transport·workflow 재시도가 겹치지 않게 정책을 정한다. [현행 PydanticAI 통합](https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/).

DBOS의 step은 완료 checkpoint 전에는 재시도될 수 있다. 외부 유료 호출이 공급자에 접수된 뒤 저장 전에 중단되면 외부 부작용의 단 한 번 실행을 보장할 수 없다. 확인 불가 상태·재조회·명시적 재실행 정책과 앱 UsageLedger가 필요하다. [DBOS 내구성 보장](https://docs.dbos.dev/python/tutorials/workflow-tutorial#durability-guarantees).

앱 기준 데이터와 outbox는 같은 PostgreSQL 트랜잭션으로 저장한다. DBOS system DB를 별도 DB로 배치하면 자동으로 앱 데이터와 원자적인 것이 아니다. 실행 연결 시 datasource/transaction 경계를 명시한다. 이번 저장은 일반 SQLAlchemy transaction이며 DBOS 복구가 구현된 것으로 표시하지 않는다. [DBOS transaction/datasource](https://docs.dbos.dev/python/tutorials/transaction-tutorial).

## 다음 연결 순서

1. 검증된 EvidenceBundle 저장·조회·불변 스냅샷·원자적 outbox·마이그레이션 (이번 작업).
2. 서버 자원·월 비용·DB/외부 백업 배치 확인 후 개발 서버의 전용 PostgreSQL 연결. 인증·공간 권한을 갖춘 등록/조회 API.
3. 실제 원문 객체·파싱·수집 ID 재사용, 읽기 스냅샷 점검과 실제 평가셋.
4. pgvector/한국어 검색·Neo4j 투영, 그 뒤 PydanticAI/DBOS worker·저장 이벤트·예산/유료 호출·복구 검증.

서버 접근 세부정보·키·실제 비공개 데이터는 이 문서와 Sites에 넣지 않는다. 월 비용 10만 원은 상한이며 현재 실측 달성으로 기록하지 않는다.
