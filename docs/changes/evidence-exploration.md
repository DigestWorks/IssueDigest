# 근거 탐색 확대·분류와 브리핑 디자인

2026-10-16. 사용자가 자료 탐색/근거 분류 개발과 기존에 논의한 앱 디자인의 선행 구현을 승인했다. R1~R6·D016~D020·제품 경험 인터뷰를 따른다. 기존 OpenSpec root=null이므로 init/승인 재요청 없이 SDD/TDD/독립 검토로 진행한다. 첫 구현은 승인된 공식 원천의 수집 연결과 명시 분류를 실제 질문 흐름에 붙이는 범위이며 전체 웹 탐색/서비스 출시가 아니다.

## Global Constraints

- B2C 질문→짧은 브리핑→필요한 비교/변화/근거 탐색이 제품이다. React Router/React/TS, Python/FastAPI, PostgreSQL/pgvector, PydanticAI/DBOS, Neo4j 선택과 기존 모노레포를 유지한다. 새 유료 서비스·월10만원 상한·초대/가입·세션14일/7일·현재 권한/예약/멱등성/취소/복구를 변경하지 않는다.
- 기존 자료·질문·실행·원문·계정/세션과 공개 브리핑 v1을 보존한다. 현재 공유 검증 이력을 개인 보관함으로 부르지 않는다. 승인된 두 개발 계정만 질문한다. 비회원 공개 읽기/원문/재열람은 모델·세션·비공개 조회를 만들지 않는다. main/운영 병합은 D013 유예, 개인 개발 HTTPS 반영과 feature Draft PR·Sites 갱신은 기존 승인 범위다. 사용자 탭을 열거나 이동하지 않는다.
- UI는 실제 기능·자료만 표시한다. 인기/주목/추천·여론·개인 저장·알림·공유·실시간 전체 웹 탐색을 꾸미지 않는다. 자료 선택/카탈로그/디버그 메뉴/ID 이름/자료 범위 진단/준비 중 체크포인트를 되살리지 않는다. 로그인 안내는 헤더 메뉴와 명시 질문 트리거로 집중한다. 이미지/샘플 모듈을 실제 생성 결과로 표시하지 않는다.
- 첫 수집 확대는 한국정책브리핑 정책뉴스 목록의 고정 HTTPS 주소와 정확한 policyNewsView 기사만 사용한다. RSS는 공식 중단 안내가 있어 사용하지 않는다. 목록은 발견용 메타데이터이며 근거/진실 판정/인기 순위가 아니다. article의 정확 공공누리1 텍스트 조건·출처·발행일·본문 SHA와 사진/외부 저작물 제외를 기존 policy_html parser로 개별 확인한다. 다른 도메인/동적 JS/인증/검색광고/사진/원격 지시/추적 query/redirect를 따라가지 않는다.
- 수집 SDK는 제한된 읽기 HTTP와 private capture만 수행한다. import/startup/공개 GET/로그인 복원에서 외부 수집·DB 쓰기·모델을 실행하지 않는다. operator가 capture/제한된 quote/ID/이용조건을 확인한 private job으로 기존 provisioning·presentation·index 경로에 명시 등록한다. 같은 artifact/job은 동일 준비·반복 등록, 재수집/내용 변경은 새 명시 버전이며 과거 원문/결과를 덮지 않는다. 수집이 공개 게시를 뜻하지 않으며 D020의 전체 내용/권리 검토·독립 게시 hash 계약을 바꾸지 않는다. 이번 단계는 수집 SDK/등록된 검색 자료 확대이지 질문 때 전체 웹 자동 탐색/정기 스케줄 완료가 아니다.
- 새 AI 분류는 기존 Claim.basis=inference를 유지하고 기존 SupportReview의 자동 검토로 별도 기록한다. '자료에 기록된 내용'(content/supported), '출처의 주장'(attribution/supported), '확인하기 어려움'(content/insufficient)만 허용한다. 이것은 현재 선택 근거에 대한 AI 평가이며 독립 사실 검증·진실/찬반 점수·국민 여론/정당한 주장 판정이 아니다. source_assertion/observation으로 AI 해석을 승격하거나 과거 결과에 새 분류를 추정해 붙이지 않는다. 모순/50:50 양측·추가 자료가 없는 분류를 채우지 않는다.
- 원문·인용 일치/UUID/참조·권한을 계속 검증한다. 분류는 각 claim의 실제 인용과 정확 대응하는 SupportReview 1개로 기록하며 자동 reviewer 식별자는 고정 기술 식별자다. 실제 인간 검토자를 위조하지 않는다. claim/기존 계약에 default 필드를 추가해 과거 canonical JSON/hash/공개 v1을 변경하지 않는다. 기존 v1/v2·공개 게시 payload는 그대로 읽는다. 새 v3 결과의 공개 게시 지원은 별도이며 기존 공개 경계를 완화하지 않는다.
- 새 classified agent/workflow는 v3 이름으로 분리하고 기존 v2 구조·agent 이름/지침/결과 재생을 보존한다. 기존 DBOS workflow ID가 있으면 등록된 원래 함수로 복구하고 새 요청만 v3를 시작한다. 불명확 유료 결과 재호출·자동 retry/모델 호출 증가는 없다. 현재 모델/24,000토큰 상한/2,500출력/단일 호출·no-store·프롬프트 byte 사전 한도를 유지하고 v3 schema 비용도 포함한다.
- 실제 키/계정/접속/개별 private ID/원문은 controller만 다루고 Git/PR/Sites에 넣지 않는다. 테스트는 합성 자료와 controller가 제공하는 소유 전용 PG만 사용하며 실제 서버/DB/25439 복원본을 fixture/reset하지 않는다. 운영자 도구는 기존 private-file/URL/중복 JSON/비유한 수/재검증/고정 오류·로그 원칙을 재사용한다. lower implementer는 subagent/reviewer를 만들지 않는다.

## Task 1: 먼저 읽히는 현대적 앱 디자인

- [ ] frontend-design을 적용해 홈/로그인/비공개 브리핑/공개 읽기/기록/근거 창의 한 가지 디자인 체계로 정리한다. 앱 사용을 위한 차분하고 정밀한 정보 인터페이스: 중립색 바탕·소량의 녹색 강조·선명한 한국어 산세리프·짧은 행간과 충분한 문단 여백·정돈된 목록/정확한 타이포 위계. 과한 마케팅 헤더/그라데이션/카드 대시보드/반복 배지·설명은 없다. 로고/아이콘 버튼 유지. 기존 겹친 스타일 override를 정리하고 필요한 실제 화면의 상태를 동일 토큰으로 맞춘다.
- [ ] 한국어 제목의 Batang/serif fallback을 제거하고 실제 제공되는 적법한 로컬 폰트 또는 합리적 기존 글꼴을 사용한다. 새 폰트이면 공식 원천·라이선스·작은 정적 자산으로 self-host하고 출처를 문서에 남긴다. 일반 사용자에게 기술 stack 설명을 추가하지 않는다. 질문을 중심에 두고 중복 heading/label/홍보 문구를 정리하되 접근성 label을 유지한다.
- [ ] 모바일에서 30초 요약→접을 수 있는 비교/변화→정확 근거→후속 질문이 자연스럽고, PC는 본문을 읽으면서 원문 창의 맥락을 확인한다. 기존 native dialog/보호 GET·공개 고정버전 재확인·Escape/초점 복원·route/race/권한 정리·질문 초안→로그인·명시 제출/후속/취소/재열람·header계정/테마 의미를 보존한다. 없는 자료·기능을 추가하지 않는다.
- [ ] 320/390/1440·밝은/어두운 테마·44px 조작·키보드/초점·reduced-motion·줄바꿈/긴 한국어/실패/진행/빈 상태를 고려한다. 변경 행동이 있으면 TDD, 순수 시각/문구 수정에는 구현을 흉내 내는 테스트를 새로 만들지 않는다. 의미 있는 기존 회귀를 유지해 JS lint/types/tests/build/contracts 후 commit/report. backend/domain/worker/generated 계약·실제 데이터/서버/Sites는 수정하지 않는다.

## Task 2: 공식 정책뉴스 발견·확보와 정확 근거 준비

- [ ] packages/connectors에 고정 `https://www.korea.kr/news/policyNewsList.do` 첫 페이지의 실제 결과 영역만 읽는 발견 SDK와 `https://www.korea.kr/news/policyNewsView.do?newsId=<9 ASCII digits>` 확보 SDK를 추가한다. 결과는 중복 없는 canonical article 후보이며 순위/지지/사실이 아니다. 목록의 추천/상위 배너/푸터 기사와 tracking query를 후보로 섞지 않는다. HTML을 실행하지 않는다. 목록 구조/빈 결과를 명확히 검증하고 변경 시 고정 오류로 실패한다.
- [ ] 요청별20초/2MiB·동일 동작 retry0·TLS검증·redirect/proxy/env인증/쿠키 금지·identity UTF-8 HTML과 제한된 고정 origin/path·최대2기사/한 batch를 지킨다. SDK import는 네트워크/DB/env를 읽지 않고 transport 주입 테스트를 지원한다. 기존 Assembly connector 로그/에러 안전 처리를 공유하거나 같은 계약을 지키며 원문·URL/query/keys를 예외/log/repr로 노출하지 않는다. artifact는 엄격 UTF8/중복key/비유한/추가field/model_construct 우회 재검증과 size limit을 지키는 private capture다.
- [ ] apps/worker의 작은 CLI/순수 준비 함수를 만든다. 발견 capture→명시 기사 capture→기존 parser의 본문/조건 확인→운영자가 선택한 정확 인용·UUID/원문저장 참조·이용조건 확인이 있는 private job→기존 ProvisioningPlan에 덮어쓰기 없는 append를 제공한다. 기존 raw/citation/document/version/evidence 계약과 대상/허용 초대/DB를 보존한다. 같은 capture/job의 준비는 동일하고 다른 artifact에 같은 IDs를 재사용하면 기존 등록에서 거부한다. verified SourcePresentation은 확보 기사에서 확인한 제목/출처만 사용한다. 검색 색인/실제 등록은 controller가 기존 명령으로 수행하며 SDK/prepare가 자동 DB 쓰기를 하지 않는다.
- [ ] meaningful TDD: 결과 영역 vs 배너/푸터/중복/다른URL, bounded status/bytes/encoding/redirect/log/timeout/transport, parser조건 불일치/다른article/사진 제외/정확quoteUnicode/누락·oversize·중복JSON·조작모델·job정체성·기존baseplan 보존/반복을 검사한다. 합성HTTP와 기존 pipeline 회귀, Ruff/mypy/필요 계약 검사 후 commit/report. 실제 기사/키/서버/Sites/active UI를 사용/변경하지 않는다. CLI추가 외 새 의존성/lock 변경은 피하고 필요한 generated lock만 근거를 기록한다.

## Task 3: 근거의 한계를 설명하는 AI 분류와 화면 연결

- [ ] 기존 AIOutput/create_agent/model_prompt/build_canvas/v2 DBOS 재생은 보존한다. 별도 v3 typed output으로 각 claim에 documented/attributed/uncertain 및 짧은 근거 설명을 필수 제공한다. 기존1..5자료/최대12claims/summary·comparison·timeline+마지막evidence·정확action/citation·timeline정확날짜/모델·토큰/예약 한도를 유지한다. 새 input schema/instructions도 사전 byte budget에 계산한다.
- [ ] v3 build는 각 inference claim에 기존 SupportReview를 정확1개 부여한다. fixed reviewer_kind=automated/reviewer_id=issuedigest-research-v3/method=pydantic-ai/method_version=research-v3, target/동일citation_ids/공통 UTC reviewed_at과 validated_at, rationale는 실제 모델의 bounded 설명이다. category→scope/assessment 매핑은 Global Constraints 그대로다. legacy/v3 섞임·누락·중복·unknown target/ref·과거 v2에 분류 주입을 거부하는 bounded 경계를 서버와 TS에 둔다. generic 도메인의 Claim 또는 과거 직렬화/hash를 바꾸지 않는다. v1/v2/publicv1의 실제 fixture/immutable 조회 회귀를 반드시 유지한다.
- [ ] v3 agent와 DBOS workflow를 등록하고 새 queued 요청만 v3로 시작한다. 같은 research-{run_id} workflow가 존재하면 status의 등록된 원래 v2/v3 이름으로 이어가되 unknown이면 안전하게 실패한다. 자동 recovery에도 두 이름이 등록된다. 원문·membership·취소·유료 결과 저장/재생·단일 호출/불명확 재호출 방지를 유지한다. 새 scheduler/공개 signup/유료provider/스키마 변경을 도입하지 않는다.
- [ ] TS 엄격 parser/renderer를 새 private v3에 연결한다. 자료에 기록됨/출처의 주장/확인하기 어려움을 작은 문구/tooltip으로 구분하고 근거 설명은 필요할 때 읽는다. AI 해석 label을 유지하며 독립 사실 검증 배지로 보이지 않게 한다. 구 결과는 현재 inference/원문 표시를 유지하고 분류를 추정하지 않는다. public D020 v1/v2-only·support_reviews=empty 정책은 완화하지 않는다. Task1 디자인·동작을 유지하고 생성/실패/취소는 실제 상태만 보인다. 아직 검증 안 된 AI token을 사실처럼 스트리밍하지 않는다.
- [ ] meaningful TDD: v3 outputshape/ref/mapping/unsupportedcategory/예산/날짜/주체·자료부족/프롬프트지시, v2과거출력/공개불변hash, 실제 PG/DBOS 기존workflow복구·queued멱등/취소/권한/저장·단일호출/unknownname, TSmalformed/mixed/ref/tooltip/legacy/private/public/원문·로그인·race 회귀. 관련 검사/Ruff/mypy/JSlint/types/build/contracts 후 commit/report. README/AGENTS·R2/R3/R4·D021·계획/작업/진행·실행 문서를 실제 완료/미완료로 정리한다.

## 최종 검증·개발 반영

컨트롤러가 전체 actual PostgreSQL/JS 검사·독립 작업/전체 검토·320/390/1440/테마/키보드/초점·공개v1불변·기존권한/로그인/생성·분류/원문을 검증한다. 공식 실제 목록/기사 최대2건을 SDK로 확보해 개별 조건/내용·인용을 확인하고 기존 operator 경로로 내부 자료에 명시 append/색인하며 현재 공개 게시1건은 바꾸지 않는다. 실제 DB 사전/사후 백업과 별도 복원·기존 rows 보존·새 기록 반복을 확인한다. 합성 신원/공개 자료 복원본으로 한 번의 제한된 실제 모델 검증이 필요하면 기존 키/상한 내에서만 수행하고 실제 사용자 세션을 대신 만들지 않는다. 기존 활성 workflow/유료 실행이 있으면 폐기하지 않고 유지/완료 후 안전하게 API/worker/static을 개인 개발 도메인에 반영한다. main/운영 변경 없이 Draft PR·저장소·Sites/이전 기록을 갱신하고 사용자 탭은 열지 않는다. 전체 웹 자동 탐색/최근인기이슈/정기수집/의미검색/검증된부분결과/개인화/전체 B2C 완료를 주장하지 않는다.
