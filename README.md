# IssueDigest

현재 구현 중: [역할 경계·출력 배분 v2 SDK](docs/changes/semantic-balanced-output-implementation.md). 별도 생성·검수와 실제 사용량에 따른 합산 한도를 구현하고 독립 검토·전체QA를 진행한다. 실제 의미 품질·앱 반영은 별도 인수한다.

다음 계약: [전체 역할 참조·증감 연결·출력 배분 설계](docs/changes/role-aware-generation-audit.md). 비교 기준/목적까지 읽는 검수, 명시 증감 근거와 짧은 항목명·진단 묶음을 설계했다. 원래 역할/경고의 오프라인 복원만 확인했으며 새 SDK·실제 토큰/의미 개선은 아직이다.

현재 인수: [compact 생성·역할 검수7회](docs/research/compact-scope-acceptance.md). 생성2반환/의미0/2, 검수5시도/4반환·출력 미완료 거부1이다. 기존 오류를 탐지했지만 정상/허용 기준과 충돌하는 진단도 있어 앱 적용을 보류한다. 원래 결과/기준·실패 사용량과 참고$0.0897140을 보존했다.


현재 구현: [원문 중복 축소·수치 역할 검수 SDK](docs/changes/compact-source-scope-audit.md). 원문을 그대로 복원하는 별도 생성 경로와, 원래 답을 고치지 않는 네 역할 진단·생성/검수 합산 한도를 구현했다. 차단 자료의 오프라인 요청은20,692→18,587이다. 독립 검토·전체7,366개 검사/빌드/계약 검증을 통과했으며 실제 의미 개선과 앱 적용은 후속이다.

현재 인수: [수치 후보 v2 생성의 제한 검증](docs/research/shared-context-v2-acceptance.md). 실제3회 모두 반환했지만 의미 기준은1/3이다. 필수 수치7개·단위/근사는 보존했으나 지역/사업 연도 누락과 운영 주체의 범위 오인이 남았다. 새 다문단 자료1건은 송신 전 용량 차단이다. 앱 적용을 보류하며 원래 결과·비용을 보존한다.

현재 구현: [수치 후보 v2의 생성 연결](docs/changes/shared-context-v2.md). 원문 단위·근사 표현을 새 단일 요청과 저장 결과 재구성까지 연결했다. 전체7,206개 검사와 기존421파일 보존을 확인했다. 실제 모델 의미 인수·앱 적용은 아직 없으며 이전 실패를 보존한다.

현재 구현: [복합 단위·근사 후보 v2](docs/changes/numeric-candidates-v2.md). 학교·사람 단위와 근사 표현을 원문 span으로 보존하는 순수 후보 계약을 추가했다. 전체7,099개 검사와 기존419파일 보존을 확인했다. 기존 자료의 두 후보 누락은 오프라인 재구성으로 확인했으며 새 AI 호출/앱 적용은0이다.

현재 인수: [새 자료 점검](docs/research/role-guidance-acceptance.md). 두 자료 중 하나는 수치 후보 단위·근사 표현 누락으로 모델 호출 전에 차단했고, 나머지 실제1회는 반환했으나 필수 하위 지역 누락으로 의미 미충족이다. 다음은 후보 계약 보완이며 앱 적용은 보류한다.

현재 구현: [측정 대상·계층적 범위 지침](docs/changes/shared-context-role-guidance.md). 별도 생성 경로와 합성 검증을 추가했다. 전체7,049개 검사 통과와 기존417파일 보존을 확인했다. 실제 AI 의미 개선·앱 적용은 아직 검증하지 않았다.

현재 비교: [동일 계약 모델4회](docs/research/shared-context-model-comparison.md). GPT-6.1 Sol은4건 모두 반환했으나 의미 기준은2/4 충족이다. 대상·필수 광역 범위 누락이 남아 앱/기본 모델은 바꾸지 않았다. 그룹 출력 즉시 구현을 보류하고 의미 품질을 우선 검토한다.

현재 인수: [공유 맥락 생성의 실제4회](docs/research/shared-context-acceptance.md). 반환1건은 필수 별도 범위를 누락해 의미 미충족이고3건은 구조 거부로 의미 미판정이다. 기존 결과·상한/비용을 보존하며 앱 적용은 보류한다. 다음은 [측정 그룹 출력 제안](docs/changes/measurement-group-output.md)이며 아직 구현하지 않았다.

현재 구현: [공유 맥락 생성 SDK](docs/changes/shared-context-generation.md). 새 순수 계약을 단일 borrowed-model 요청에 연결했다. 전체7,019개 검사·독립 검토와 기존4자료 원문 전체의 오프라인 요청 용량을 확인했다. 실제 AI 호출0이며 의미 품질·앱 적용은 후속이다.

현재 구현: [공유 측정 맥락](docs/changes/shared-measurement-context.md). 공통 항목/범위·보고 사건을 명시 연결하고 목적을 조건과 분리하는 순수 adapter를 추가했다. 독립 검토와 전체6,916개 검사를 통과했다. 이 순수 계약의 생성 연결은 위 SDK 기록을 따르며, 미관측 의미 품질·앱 적용은 후속이다. 기존 결과와 요청 설정은 보존한다.

현재 연구: [동일 계약 추론 비교](docs/research/measurement-reasoning-comparison.md). 네 시도 중 반환2개 모두 의미 미충족·다른2개 미판정으로 설정/앱을 바꾸지 않았다. 공유 맥락의 설계 후 순수 구현은 위 현재 기록을 따르며, 이 연구 당시 실행 코드는 보존했다.

현재 구현: [측정 범위 생성·문장 상태 근거](docs/changes/measurement-frame-generation.md). 새 범위 계약과 단일 요청을 연결하고 전체6,667개 검사를 통과했다. 실제4회는 수치17개를 보존했지만 의미 기준0/4로 앱 적용을 보류한다. [결과·남은 오류](docs/research/measurement-frame-generation-acceptance.md)를 보존한다.

현재 구현: [측정 대상·적용 범위 분리](docs/changes/measurement-scope-contract.md). 같은 대상의 지역·집단·기관 범위를 별도 원문으로 연결하는 순수 계약이다. 신규207/전체6,544개 구조 검사를 통과했지만 AI 선택/상태 근거·미관측 자료·앱 연결은 후속이다. 새 모델 호출과 앱 변경은 없다.

현재 구현: [범위·상태 근거 지침](docs/changes/scoped-contextual-generation.md). 기존 v1 요청을 공유하고 별도 선택 지침을 추가했다. 전체6,337개 검사와 v1 호환을 확인했지만 실제4회는 기존1/2·새합성1/2 충족으로 의미 오류가 남아 앱 적용은 보류한다.

이전 구현: [문맥 프레임 생성 SDK](docs/changes/contextual-frame-generation.md). 역할·관계 근거의 반복 표현을 명시 문맥으로 구분하는 별도 단일 요청 경로다. 전체6,240개 검사를 통과했지만 실제2회는 반환2/의미 기준0/2로 대상 범위·상태 근거 오류가 남아 기존 앱은 보존한다.

이전 구현: [문맥 기반 원문 참조](docs/changes/contextual-anchor.md). 같은 문장의 명시적 문맥으로 반복 표현의 짧은 원문 위치를 구분한다. 실제 AI 선택·프레임/앱 연결은 별도 인수하며 이전 모델의 실패 결과는 유지한다.

IssueDigest는 질문에서 시작해 이슈의 맥락·쟁점·변화를 이해하는 B2C 브리핑 서비스입니다. 궁금한 점을 묻고 짧은 브리핑에서 비교·변화·반응·원문 근거로 이어갑니다. [제품 경험 인터뷰](docs/research/product-experience-interview.md)와 D016·D017이 제품 방향의 원본입니다.

현재 앱은 비회원 질문→로그인→편집 상태 복원, 명시 생성, 질문에 따른 서버 근거 검색, 정확 원문과 검증된 완료 브리핑, 후속 질문·취소·재접속·자동 저장/재열람을 제공합니다. 기본 메뉴는 **브리핑·브리핑 기록**, 테마와 계정은 아이콘으로 엽니다. 질문만 제출하며 결과의 정확 인용에서 원문을 확인합니다. 현재 검색은 접근 가능한 저장 색인의 제한된 문자 검색입니다.

[모델 제한 비교](docs/research/frame-model-comparison.md)는 같은 계약의 신규2회에서 고정 의미 기준 수동충족1/2를 관측했다. 반복 anchor 전체 거부는 남아 앱 적용은 하지 않는다.

[수치 프레임 생성 SDK](docs/changes/numeric-frame-generation.md)는 새 역할 프레임을 단일 bounded borrowed-model 요청으로 채운다. 전체5,937개 검사를 통과했지만 실제2회는 부분1/거부1·의미 완전0/2다. 기존 앱/원래 생성기·자료/기준은 변경하지 않으며 [남은 오류](docs/research/numeric-frame-generation-acceptance.md)를 보존한다.

[수치 의미 역할 프레임](docs/changes/numeric-evidence-frame.md)을 구현했다. 측정 대상/발표자, 값의 상태/보고 시제, 논리 조건/전망 근거·비교 기준을 별도 원문으로 연결한다. 기존 생성기와 앱은 보존하며 구조 검사 통과를 실제 의미 품질로 해석하지 않는다.

[역할 지침 비교](docs/research/numeric-role-guidance-trial.md)에서 원문 기반 기준을 별도 보강하고 실제2회 호출했다. 반환2지만 대상 혼동·관계 누락이 남아 의미 완전0/2다. 지침만 적용하지 않고 측정 대상/발표자·상태/시제·논리 조건/전망 근거·비교 기준을 분리하는 다음 계약을 정리했다. 앱은 변경하지 않았다.

[수치 역할의 기준 평가기](docs/changes/numeric-selection-evaluation.md)를 추가해 기존 결과의 필드별 차이·미판정·전체 거부를 오프라인으로 재현한다. 기준 일치는 독립 의미·진실·최종 앱 인증이 아니며 새 모델 호출은 없다. 원래 두 건의 부분1/거부1·의미 완전0/2는 그대로다.

서버의 수치·문장 후보를 AI가 선택하는 내부 SDK를 추가했다. 같은 두 자료의 실제2회는 부분 반환1·거부1·의미 완전 충족0/2다. 반환 제안의 수치6개·단위/범위/포함 관계는 보존했지만 조건 누락·약한 상태 근거가 남았다. [현재 명세](docs/changes/numeric-candidate-selection.md)·[진행 기록](docs/planning/progress.md)·[평가 기록](tests/evaluation/README.md)을 따른다. 이전 후보11/11·지원37/37/미지원2건과 v3/v2/v1/앱 실패는 보존하며 앱 연결·최종 브리핑은 별도다. 개발ab6654e/v9/main·운영 유예를 유지한다.

초대 자료·질문·브리핑 기록은 기존 세션과 현재 멤버십으로 보호합니다. 이와 별도로 명시 검토한 공개 복사본만 질문 아래 목록과 `/briefings/:slug`에서 비회원에게 제공합니다. 고정 버전 링크·출처 표시·정확 인용 원문을 읽을 수 있으며, 이어갈 질문은 일반 홈의 편집 가능한 초안으로 전달합니다. 읽기·재열람은 모델을 호출하지 않고 질문의 명시 제출부터 기존 로그인/권한/비용 정책을 적용합니다.

첫 공개 출처는 문서별로 공공누리 제1유형 텍스트 재게시를 확인한 한국정책브리핑 공식 기사로 제한합니다. 사진·외부 저작물은 제외하며 기존 비공개 실행을 자동 공개하지 않습니다. 게시 저장소가 없으면 공개 API는503이고 실제 목록이 없으면 홈 영역을 생략합니다. [공개 브리핑 명세](docs/changes/public-briefings.md)와 [D020](docs/planning/decisions.md)을 따릅니다. 독립 검증·개별 내용/이용 조건 검토 후1건을 명시 게시하고 개인 개발 HTTPS에 반영했습니다. 사후 백업 복원도 확인했으며 main/운영 게시는 유예합니다. 최근 이슈/개인화·개인 관심 이슈·알림·사용자 공유·AI 부분 결과·전체 B2C 품질은 후속입니다. 현재 증거는 [진행 기록](docs/planning/progress.md), 다음 작업은 [작업 목록](docs/planning/tasks.md)을 확인합니다.

- [문서 안내·협업 방법](docs/README.md)
- [에이전트 지침](AGENTS.md)
- [구현 계획·마일스톤](docs/planning/implementation-plan.md#마일스톤)
- [요구사항·설계](docs/planning/requirements-design.md)
- [결정 기록](docs/planning/decisions.md)
- [작업 목록](docs/planning/tasks.md)
- [진행 기록](docs/planning/progress.md)
- [이전 기록·재사용 자산](docs/planning/archive.md)
- [개발 서버 안내·확인 기록](infra/development-server.md)
- [조사 실행·비용·검증 경계](infra/research-development.md)
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
  ingestion/              읽기 전용 원문 후보 검사·PDF 페이지 텍스트·정확 인용 준비
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
- 기본 포트가 이미 사용 중이면 해당 프로세스를 정리하거나 API의 별도 포트를 지정하고 웹의 개발용 `API_PROXY_TARGET`을 맞춥니다. 자세한 명령은 [웹 README](apps/web/README.md)에 있습니다.

원문 후보 검사와 제한된 PDF 텍스트 추출·인용 후보/정확 문맥 선택의 입력·명령·집계/상세 출력과 검증 경계는
[원문 검사 패키지 안내](packages/ingestion/README.md)에 있습니다.

## 검증과 계약

```sh
npm run check
```

재사용 생성 화면 렌더러 `@issuedigest/ui`의 사용법과 표시 검증 경계는
[UI 패키지 안내](packages/ui/README.md)에 있다. 이 패키지는 서버 검증 자료를
받아 여섯 모듈을 렌더링합니다. 브리핑 화면은 서버 검증 결과와 자료 제목을 전달하며, 현재 AI 생성 범위는 요약·비교·타임라인·근거입니다. 수치 없는 차트나 근거 없는 관계도는 만들지 않습니다.

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

웹은 Google 로그인·현재 권한에 따른 브리핑 기록·원문과 인용 읽기·로그아웃을 제공합니다. 실제 자료는 설정된 서버 세션과 승인 공간에 저장된 자료에서 읽으며, 기본 미설정 실행은 로그인/자료 연결이 준비되지 않았음을 표시합니다. D011에서 PostgreSQL + pgvector + PydanticAI/DBOS를 선택했습니다. 검증된 EvidenceBundle의 내부 PostgreSQL 저장·조회와 원자적 outbox를 구현했으며, 공동 개발 DB·승인 자료와 Google 로그인·보호 문자 검색을 연결했습니다. PydanticAI/DBOS 조사 워커와 저장·후속 질문·취소를 연결했습니다. 실제 모델 사용에는 별도의 서버 키와 명시 활성화가 필요합니다. 고정 기사 반복 확보와 저장/상태는 별도 개발 수집기에 연결했습니다. Neo4j·광범위한 최신 자료 수집·의미 검색·운영 연결은 후속입니다. 키·공급자 자격 증명은 웹에 넣지 않습니다. 다음 범위와 검증 상태는 [개발 기반 작업](docs/changes/development-foundation.md)과 [진행 기록](docs/planning/progress.md)을 확인합니다.


## 개발 앱·근거 검색

[HTTPS 개발 앱](https://dev.issuedigest.projects.ai.kr/)의 실제 적용 상태는 [진행 기록](docs/planning/progress.md)을 따릅니다. 질문만 제출하면 서버가 현재 접근 가능한 저장 색인에서 최대8개 검색어로 관련 근거를 최대5개 찾습니다. 관련 근거가 없으면 모델을 호출하지 않고 자료 부족으로 종료합니다. 저장된 본문·PDF 페이지·표 셀의 정확 인용은 브리핑에서 엽니다. 검색어/후보 한도가 있는 문자 검색이며 웹 전체 탐색·의미 검색·최신 자료 수집 완료를 뜻하지 않습니다. 운영 앱 배포는 유예 중입니다.

[검색 인터페이스 명세](docs/changes/evidence-search-interface.md)와 [개발 접속 기록](infra/development-https.md)에 검증·남은 조건을 기록합니다. main 자동 배포와 별개로 개인 개발 앱에서 검증하며 현재 검색 코드의 앱 갱신 상태는 [진행 기록](docs/planning/progress.md)을 따릅니다.

## Google 로그인·자료 진입

운영자가 초대한 Google 계정만 로그인할 수 있습니다. Google 서명·state/PKCE/nonce를 확인하고 서버 세션을 발급한 뒤 현재 작업 공간 권한으로 자료 목록·원문/인용을 읽습니다. 이메일·공급자 토큰을 웹 저장소에 보관하지 않습니다. 로그아웃하면 해당 서버 세션을 폐기합니다. 세션 정책은 최대14일·7일 미사용 만료이며 기존 세션의 만료일을 자동 연장하지 않습니다. 서버 반영 여부는 진행 기록을 따릅니다.

[설정·실행 안내](apps/api/README.md)와 [작업 명세](docs/changes/google-oauth-workspace.md)에 개발용 HTTPS callback, 명시 마이그레이션·초대/자료 등록과 필요한 환경변수를 기록했습니다. 공동 개발 DB·고정 HTTPS 개발 앱을 연결했고 실제 Google 로그인 바인딩과 세션 저장을 확인했습니다. 사용자의 자료 읽기·검색 최종 확인과 main 운영 앱은 별도로 남아 있습니다. 테스트의 합성 계정/자료는 실사용 계정/자료가 아닙니다. 공개 앱·main 병합은 D013에 따라 유예합니다.
