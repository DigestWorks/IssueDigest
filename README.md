# IssueDigest

DigestWorks의 이슈 조사·근거 비교 서비스 풀스택 모노레포입니다. 현재 React Router 웹·FastAPI API·상태 계약·개발 검증 기반을 구성했습니다. 내부 PostgreSQL 근거 스냅샷 저장 기반과 생성 화면 React 렌더러를 구현했으며, 제품의 자료 수집·조사·운영 연결과 전체 P1은 아직 미완료입니다.

첫 사용자는 우리 둘이며, 실제 원자료에서 근거·관계·변화를 찾아 질문에 맞는 화면으로 탐색합니다. 프론트는 React Router, 백엔드는 Python/FastAPI, 그래프는 Neo4j를 사용합니다. 기준 저장소는 PostgreSQL이며, 검색·AI 실행 도구는 D011에 따라 단계적으로 연결합니다. 운영 배치는 검토 중입니다.

- [문서 안내·협업 방법](docs/README.md)
- [에이전트 지침](AGENTS.md)
- [구현 계획](docs/planning/implementation-plan.md)
- [요구사항·설계](docs/planning/requirements-design.md)
- [결정 기록](docs/planning/decisions.md)
- [작업 목록](docs/planning/tasks.md)
- [진행 기록](docs/planning/progress.md)
- [이전 기록·재사용 자산](docs/planning/archive.md)
- [개발 서버 안내·확인 기록](infra/development-server.md)
- [공유 계획 사이트](https://lawdigest-rebuild-plan.ijaesinii.chatgpt.site/)

이전 와이어프레임은 별도 비공개 저장소의 코드로 보존하며 배포를 종료했습니다. 계획 문서는 서비스 기능의 구현 완료를 뜻하지 않습니다.

## 저장소 구조

```text
apps/
  web/                    React Router · React · TypeScript
  api/                    Python · FastAPI
  worker/                 수집·가공·투영·에이전트 작업
packages/
  domain/                 Python 응답 모델·계약 원본
  storage/                PostgreSQL 불변 EvidenceBundle 스냅샷·outbox
  ingestion/              읽기 전용 여론조사 JSON·PDF 원문 후보 사전 검사
  api-client/             생성 OpenAPI·TypeScript 타입·HTTP 클라이언트
  connectors/             데이터 수집 연결기
  agents/                 에이전트·도구·결과 검증
  ui/                     생성 화면 명세·허용 컴포넌트
infra/                    배포·백업·운영 설정
tests/evaluation/         실제 근거와 평가 질문
docs/                     계획·결정·작업·진행 기록
AGENTS.md                 사람과 에이전트의 작업 기준
```

각 개발 폴더에는 책임과 현재 상태를 적은 README가 있습니다. Python·TypeScript 워크스페이스와 고정 의존성은 아래 개발 기반 명령으로 설치·검증합니다.

## 협업 기준

Linear 대신 이 저장소의 문서와 PR로 논의합니다. 결정·작업 상태의 원본은 `docs/`이며, Sites에는 이를 요약해 공유합니다. 작업을 시작할 때 [문서 안내](docs/README.md)를 읽고 관련 요구사항·결정·작업을 확인하세요.

## 설치와 실행

Node **24.21.0** (npm **11.19.0**), Python **3.13.12**, uv **0.11.4**를 사용합니다. `.nvmrc`·`.python-version`·프로젝트 설정에 버전을 기록하고 `package-lock.json`·`uv.lock`을 커밋합니다. Node 버전 관리 도구를 사용한다면 `.nvmrc`의 버전을 선택한 뒤 아래 명령을 저장소 루트에서 실행합니다.

```sh
node --version
npm --version
uv --version
npm ci
npm run setup
npm run dev
```

`setup`은 `uv sync --locked --all-packages`로 API·도메인·저장·원문 후보 검사 패키지·검증 도구를 설치합니다. uv가 지정 Python을 찾지 못하면 `uv python install 3.13.12`로 설치합니다. `npm run dev` 통합 실행기는 Linux에서 지원·검증했으며 두 앱을 실행하고 종료 신호를 받으면 함께 중지합니다. Windows에서는 `npm run dev:api`와 `npm run dev:web`을 별도 터미널에서 실행하고 각 터미널에서 직접 종료합니다.

- 웹: [http://127.0.0.1:5173](http://127.0.0.1:5173) · API: [http://127.0.0.1:8000](http://127.0.0.1:8000).
- 별도 터미널 실행: `npm run dev:api`, `npm run dev:web`.
- 웹의 **연결 확인**은 실제 `/api/v1/status` 응답을 검사합니다. API 프로세스의 응답 여부만 확인하며 DB·작업 엔진의 준비 상태를 뜻하지 않습니다.
- 기본 포트가 이미 사용 중이면 해당 프로세스를 정리하거나 API의 별도 포트를 지정하고 웹의 개발용 `API_PROXY_TARGET`을 맞춥니다. 자세한 명령은 [웹 README](apps/web/README.md)에 있습니다.

원문 후보를 검사하는 독립 도구의 입력·명령·집계/상세 출력과 검증 경계는
[원문 후보 검사 패키지 안내](packages/ingestion/README.md)에 있습니다.

## 검증과 계약

```sh
npm run check
```

재사용 생성 화면 렌더러 `@issuedigest/ui`의 사용법과 표시 검증 경계는
[UI 패키지 안내](packages/ui/README.md)에 있다. 이 패키지는 서버 검증 자료를
받아 여섯 모듈을 렌더링하며 개발 앱의 빈 자료 화면에는 연결하지 않는다.

이 명령은 Python lint·format·타입·테스트, TypeScript lint·타입·테스트, SPA 생산 빌드, 계약 변경 검사를 순서대로 실행합니다. 각 단계도 루트에서 `npm run lint:python`, `npm run typecheck:python`, `npm run test:python`, `npm run lint`, `npm run typecheck`, `npm test`, `npm run build`, `npm run contract:check`로 실행할 수 있습니다. Python 도구 직접 실행은 `uv run ruff check .`, `uv run mypy`, `uv run pytest`입니다.

실제 PostgreSQL 18.6 저장 통합 테스트는 전용 로컬 `issuedigest_test` 데이터베이스의
`ISSUEDIGEST_TEST_DATABASE_URL`을 명시하면 위 검사에 함께 실행됩니다. 미설정 로컬 실행은
저장 통합 테스트를 명시적으로 skip하며, CI는 합성 PostgreSQL service와 URL을 제공해
반드시 실행합니다. fixture는 로컬 전용 DB 이름과 연결 설정을 확인한 뒤 해당 DB의
테스트 행·스키마를 초기화합니다. [저장 패키지 안내](packages/storage/README.md)에
합성 DB 생성, 명시적 Alembic 마이그레이션, 저장·조회 사용법을 기록했습니다.
앱 import/startup은 DB 연결이나 초기화를 수행하지 않습니다.

Python 도메인 모델과 FastAPI OpenAPI가 계약 원본입니다. 응답 모델이나 API 경로를 바꾸면 `npm run contract:generate`를 실행하고 `packages/api-client/openapi.json`과 `src/schema.d.ts`를 함께 검토·커밋합니다. `contract:check`는 임시 폴더에서 다시 생성해 두 파일을 비교하며 차이가 있으면 실패합니다. 생성 파일은 직접 수정하지 않습니다. GitHub Actions는 같은 설치·검증 절차를 수행합니다.

원문·파싱·인용과 개체·주장·제한된 관계·관측·비교 조건에 이어 Run/Event/Canvas/Usage의 세 번째 부분 계약을 구현했습니다. 제공된 이력 재생·화면 근거·호출 및 월 예산 참조를 순수 함수와 불변 모델로 검사합니다. 검증과 게시 이력은 진행 기록에서 확인합니다. 실제 OpenAPI components와 생성 웹 타입으로 연결하며 제품 HTTP 경로는 추가하지 않습니다. [도메인 README](packages/domain/README.md)에 참조·수치·검토·비교의 검증 경계를 기록합니다. 인용 존재나 조건 일치는 주장 진실·합산 가능성·저장·권한 구현을 보장하지 않습니다.

React Router **8.4.0**, React **19.3.0**, Vite **8.3.4**, FastAPI **0.143.0**, Pydantic **2.14.0**를 고정했습니다. TypeScript **5.9.3**은 현재 OpenAPI 생성기의 `^5.x`와 린트 도구의 `<6.1.0` 지원 범위를 함께 만족하는 최신 5.x 안정 버전입니다. 강제 peer 의존성 우회는 사용하지 않습니다. [프레임워크 SPA 안내](https://reactrouter.com/how-to/spa), [OpenAPI 생성기](https://openapi-ts.dev/introduction)를 기준으로 구성하고 패키지 메타데이터로 호환성을 확인했습니다.

## 생산 연결과 현재 제한

`npm run build`의 정적 산출물은 `apps/web/build/client`입니다. 운영에서는 웹 정적 파일을 제공하고 `/api/*`와 `/health/*`를 FastAPI로 전달하는 같은 출처의 리버스 프록시가 필요합니다. 앱 경로는 `index.html`로 연결하되 API·헬스 요청을 HTML로 바꾸면 안 됩니다. Vite 프록시는 개발 서버 설정입니다. 개발 서버나 `vite preview`를 운영 서버로 사용하지 않습니다. 개발 서버의 사용자 전용 환경·웹/API·SSH 터널은 검증했습니다. [서버 안내](infra/development-server.md)에 실행·재접속 방법을 기록하며 운영 배포는 아직 수행하지 않았습니다.

현재 화면에는 자료가 없으며 실제 서비스 연결 확인만 실행할 수 있습니다. D011에서 PostgreSQL + pgvector + PydanticAI/DBOS를 선택했습니다. 검증된 EvidenceBundle의 내부 PostgreSQL 저장·조회와 원자적 outbox를 구현했으며, 워커·Neo4j·자료 수집·검색 인덱스·AI 실행·권한·운영 연결은 아직 없습니다. 키·공급자 자격 증명은 웹에 넣지 않습니다. 다음 범위와 검증 상태는 [개발 기반 작업](docs/changes/development-foundation.md)과 [진행 기록](docs/planning/progress.md)을 확인합니다.
