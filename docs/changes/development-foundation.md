# 개발 실행 기반

상태: Task 1 구현·자동 검증·실제 스모크 통과 · 2026-10-11. 상위 범위는 P1 기반 작업이다. 사용자 지시: 모노레포 구현 준비 다음 단계로 진행. 제품의 기능·엔진 결정은 기존 결정 기록을 따른다.

## Task 1 · 웹·API·공유 계약·개발 검증 구성

### 목표·수용 조건

첫 개발자가 저장소를 받은 뒤 고정된 의존성으로 웹과 API를 실행하고, 실제 연결 상태와 실패를 확인할 수 있어야 한다. 이후 제품 코드에서도 같은 React Router·FastAPI 실행 구조와 계약 생성 방식을 유지한다.

- B1: 루트에서 Python·TypeScript 의존성 설치, 개발 실행, 검증 명령을 제공한다. Node 24 LTS·Python 3.13을 사용하고 정확한 버전·잠금 파일을 기록한다. 현재 사용 가능한 Node 24.21.0, Python 3.13.12, uv 0.11.4 기준으로 검증한다.
- B2: FastAPI가 `GET /health/live`와 `GET /api/v1/status`를 제공한다. 전자는 `{ "status": "ok" }`, 후자는 `{ "service": "issuedigest-api", "api_version": "v1", "status": "ok" }`를 반환한다. 모든 응답에 서버가 생성한 UUID `X-Request-ID`를 제공한다. 건강 상태는 API 프로세스 응답 여부이며 DB·작업 엔진 준비 완료를 뜻하지 않는다.
- B3: Python 도메인 패키지의 응답 모델과 FastAPI OpenAPI를 계약의 원본으로 사용한다. 생성한 OpenAPI·TypeScript 타입을 버전 관리하며 재생성 후 차이가 없는지 CI에서 검사한다. 웹에서 같은 버전의 계약과 타입을 사용한다. 런타임 응답 검증으로 잘못된 JSON·HTTP 실패·네트워크 실패·시간 초과를 연결 실패로 처리한다.
- B4: React Router Framework mode의 SPA 빌드로 시작한다. API가 인증·도메인·도구 호출을 담당한다. 앱 기본 화면은 한국어로 IssueDigest의 이슈 조사·근거 비교 목적과 아직 자료가 없는 상태를 간결하게 표시한다. 실제 API 연결 확인 동작은 접수/확인 중·성공·실패·재시도를 보여준다. 구현하지 않은 조사·저장·AI 작업은 실행 버튼이나 가상 결과로 표시하지 않는다.
- B5: 개발 중 웹은 같은 출처의 `/api`·`/health` 경로를 Vite 프록시로 API에 전달한다. 서버 주소는 개발용 서버 설정이며 키·공급자 자격 증명을 웹에 넣지 않는다. 생산 빌드는 정적 파일로 생성하고 생산 연결은 동일 경로의 리버스 프록시가 담당하도록 문서화한다. 실제 운영 배포는 수행하지 않는다.
- B6: API 응답·요청 ID·API 계약, 클라이언트의 성공/실패/응답 검증, 화면의 로딩/실패/재시도를 의미 있는 테스트로 검증한다. 변경 전에 실패 테스트를 확인하고 구현 후 통과시킨다. Python lint·타입·테스트, TypeScript lint·타입·테스트·생산 빌드와 계약 변경 검사를 GitHub Actions로 구성한다. 스모크 검증은 실제 API·웹을 기동하여 데스크톱·모바일과 API 중단 상태를 확인한다.
- B7: 루트·각 앱·공유 패키지 README에 확인된 설치·실행·검증 명령과 현재 제한을 기록한다. 진행·작업 기록에서 이번 기반 완료와 전체 P1 미완료를 구분한다.

## Global Constraints

- 확정 기술은 React Router·React·TypeScript, Python·FastAPI, Neo4j다. 기준 DB·검색·실행기·인증은 이번 변경에서 결정하거나 임시 구현하지 않는다.
- 초기 실행 기반은 유료 API·클라우드·운영 데이터 없이 동작한다. 기존 운영 서버에는 설치하지 않는다.
- 가상 이슈·근거·AI 결과를 채우지 않는다. 아직 없는 제품 기능을 실행 가능하게 표현하지 않는다.
- 사람·에이전트의 협업 원본은 저장소 문서다. Linear는 사용하지 않는다. Sites 반영 여부를 진행 기록에 남긴다.
- API 응답 계약은 Python 모델/FastAPI OpenAPI가 원본이고 웹 타입은 생성 결과다. 앱 내부 코드를 다른 앱에서 직접 가져오지 않는다.
- 잠금 파일은 커밋하고 비밀값·로컬 빌드·브라우저 산출물은 커밋하지 않는다.

## 설계

루트 npm workspaces는 `apps/web`과 새 `packages/api-client`를 관리한다. 클라이언트 패키지는 생성 타입과 상태 조회를 제공한다. 루트 uv workspace는 `apps/api`와 `packages/domain`을 관리한다. API와 웹은 HTTP 계약만 공유하며 패키지 구현 언어를 억지로 통합하지 않는다.

`apps/worker`, 연결기, 에이전트, 생성 UI 폴더는 기존 계획대로 보존한다. 실행기 결정 전에는 큐·저장소·워커 실행을 흉내 내는 코드를 추가하지 않는다. 초기 계약은 시스템 상태만 버전 고정하며 문서·실행·화면 계약은 실제 기능 작업에서 이어서 정의한다.

화면은 차분한 조사 도구 스타일로 구성한다. 제목·짧은 설명·빈 자료 상태를 우선하고, 연결 확인은 작은 보조 영역으로 둔다. 긴 기술 설명·장식 카드·여러 탭·비활성 제품 버튼을 추가하지 않는다.

### 작업

- [x] 위 B1~B7과 Global Constraints를 모두 구현·검증한다.
- 작업 파일: 루트 Node/Python 워크스페이스·잠금·런타임 버전·개발/검증 스크립트, `apps/web`, `apps/api`, `packages/domain`, `packages/api-client`, `.github/workflows`, 해당 README와 진행·작업 기록.
- 정확한 API 경로·응답·요청 ID·기술 경계·화면 상태·검증 요건은 위 수용 조건을 그대로 사용한다.
- 개발 의존성을 설치하고 실패 테스트부터 실행한다. 셸에서 시스템 기본 Python 3.8이나 Node 22를 쓰지 않고 지정한 런타임으로 실행한다.
- root `npm run` 명령과 `uv` 명령으로 테스트·타입·lint·빌드·계약 검사 결과를 남긴다. 실험용 레포·파일을 새 앱에 복사하지 않는다.
- 자체 검토 후 변경을 커밋한다. 사람의 검토 전 PR 병합이나 운영 배포를 수행하지 않는다.

## 참고

- [React Router 설치](https://reactrouter.com/start/framework/installation)
- [React Router SPA](https://reactrouter.com/how-to/spa)
- [FastAPI 시작·OpenAPI](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [uv workspaces](https://docs.astral.sh/uv/concepts/projects/workspaces/)
- [uv GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)
- [OpenAPI TypeScript](https://openapi-ts.dev/introduction)
- [상위 작업 목록](../planning/tasks.md)

## 구현·검증 기록

- 런타임: Node 24.21.0·npm 11.19.0·Python 3.13.12·uv 0.11.4. 직접 의존성은 정확한 버전, 전체 해석 결과는 npm/uv 잠금 파일로 고정했다.
- TDD 실패 증거: `uv run pytest`에서 엔드포인트·서버 요청 ID·OpenAPI 계약에 대해 7개 assertion 실패. `npm test`에서 클라이언트 16개·화면 4개 assertion 실패. 구현 후 각각 7개·20개 모두 통과했다.
- 전체 자동 검증: `npm run check` 통과. Python lint/format·타입·테스트, TypeScript lint·타입·테스트, Framework SPA 빌드, OpenAPI/TypeScript 재생성 비교를 포함한다.
- 같은 고정 설치·검증의 [GitHub Actions 실행 #38133178226](https://github.com/DigestWorks/IssueDigest/actions/runs/38133178226)이 기반 코드 커밋 `d132583`에서 성공했다. [PR #2](https://github.com/DigestWorks/IssueDigest/pull/2)에서 변경을 검토한다.
- 실제 API·프록시 HTTP와 데스크톱 1366×900·모바일 390×844 hydration, 응답 지연·확인 중, API 중단·실패, 복구·재시도를 컨트롤러가 확인했다. 가로 넘침 없음, 새 브라우저 콘솔 오류·경고 각 0건, 개발 서버 함께 기동·종료 통과. 결과는 [진행 기록](../planning/progress.md)에 기록했다. Task 1만 완료 표시하며 전체 P1은 미완료다.
- TypeScript는 생성기 `^5.x`와 린트 도구 `<6.1.0` 범위의 공통 안정 버전 5.9.3이다. `isbot` 5.2.2는 React Router 기본 진입점의 빌드 의존성이므로 명시 고정했다. 의존성 충돌을 강제로 무시하지 않는다.
- 생산은 정적 `apps/web/build/client`와 같은 출처의 `/api`·`/health` 리버스 프록시 경계를 유지한다. API 프로세스 응답을 DB·작업 엔진 준비 상태로 표현하지 않는다.
- 전체 P1·워커·제품 계약·기준 DB·검색·실행기·인증은 미완료다. Sites 요약 반영 대기, 운영 배포·기존 서버 설치·유료 호출 없음.
