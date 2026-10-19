# 질문별 조사 계획·승인 자료 검색

2026-10-19. D011·D019·D022/M3·PR43/7ed6730의 다음 구현이다. 질문→AI 검색 계획→승인된 저장 자료 검색→근거 고정→브리핑을 연결한다. 기존 소비자 브리핑 디자인을 유지한다. OpenSpec root=null로 초기화하지 않고 이 명세와 Superpowers 구현/검토를 사용한다. main/운영 유예(D013)를 유지한다.

## Global Constraints

- 새 private workflow/최종 agent는 issuedigest_research_run_v7/issuedigest_research_v7, planning agent는 issuedigest_research_plan_v7다. v2/v3/v4/v5/v6의 실제 provider schema·지침·prompt bytes/한도·이름·원래 application_version·유료 namespace/정수slot1·기존 결과는 동결한다. 여섯 workflow와 별도 planner를 등록하고 새 요청만v7이다. 기존 workflow는 원래 cohort/이름으로 회복한다. v6 실제 worker를 historical fixture로 보존해 유료 재요청0을 검증한다.
- v7의 모델 호출은 planner1회+최종1회까지, 자동 재시도/출력 수리0이다. gpt-5.4-mini·Responses storeFalse/max_retries0·PydanticAI/DBOS 고정·월 예약USD10/건USD0.25/40건·사용자 월10만 원 조건은 그대로다. 전체 입력+출력24,000토큰, planner 출력500/최종2,000으로 전체 최대출력2,500을 유지한다. planner timeout15초/최종45초다. planner 지침/strict tool raw+normalized schema와 framing2,048·prompt를 포함한 사전 envelope는8,000이하이고 실제 사용량을 확인한다. 최종 prompt bound는24,000에서 cached planner input+output 실제 사용량, 재사용v6 static/alltool schema, framing2,048과 최종2,000을 차감한다. 보고된 planner 사용량은 음수/bool/한도초과를 거부한다. 두 요청의 사용량을 합산 기록하고 실패/유실의 앱 usage0을 무료로 해석하지 않는다.
- planner는 strict search_evidence 출력의 queries 1~3개(각1~64자·공백만/제어문자 불가)만 제안한다. 질문과 기존 bounded parent context를 불신 데이터로 전달하며 원문·웹·비밀·임의URL/SQL/셸 도구를 제공하지 않는다. provider planner schema도 extra forbid·모든 필드 required·실제 raw/normalized bytes로 사전 검증한다. 한글 저장 색인을 전제로 질문의 주제/기간을 보존하는 짧은 literal 검색어를 만들고 필요한 경우 한글로 표현을 바꾸되 인명/기관/수치/날짜/정치 주장을 새로 추정하지 않는다. planner는 원래 질문을 그대로 보존한다. 선택적 이전 AI 맥락만 실제 UTF-8 byte budget 안으로 code-point 경계에서 짧게 하고 잘렸음을 prompt에 명시한다. 질문과 기본 prompt envelope 자체가 큰 경우에는 질문을 자르거나 모델에 보내지 않고 안전하게 실패한다. 최종 브리핑에는 기존 bounded parent context를 그대로 사용하고 실제 원문/인용은 자르거나 정규화하지 않는다. 계획은 사실/근거가 아니며 최종 모델에는 고정 원문과 질문/부모 맥락만 전달한다.
- 실제 도구는 현재 권한의 workspace 저장 색인만 조회한다. 기존 최신 승인/원문/인용·manifest·receipt 검증을 재사용한다. 원래 질문의 terms 검색을 항상 포함하고 planner 각 query의 question_terms 검색을 더한다. 원래 검색+최대3개 계획 검색을 실행하고, 각 결과 최대5개를 라운드로빈(원래 검색 첫 순서)·중복 제거해 최대5개를 고정한다. 출처 폭·기간·주목도·여론을 추측하지 않는다. 이 작업은 외부 웹 탐색·새 수집/등록/공개 게시가 아니다. generic followup은 기존 정확 parent 전체 근거 재사용 규칙을 유지하며 planner query로 바꾸지 않는다.
- 준비 단계는 현재 actor 권한/parent를 검사하되 원문 검색·조기 no-match를 하지 않는다. 신규 v7 worker가 queued→retrieving로 전이한 후 planner를 호출한다. 실제 검색은 별도 DBOS.step issuedigest_research_search_v7(slot2)이며, 이미 고정한 snapshot_ids는 현재 검색/새 승인본으로 바꾸지 않는다. actor 재검사와 자료 선택·고정은 한 transaction이다. 검색0이면 planner의 알려진 usage와 insufficient_evidence 실패를 원자적으로 기록해 재시작 후 검색 결과를 바꾸지 않는다. 취소·권한 변경·부모/원문 불일치 뒤 최종 모델 호출/게시를 하지 않는다. 기존 worker_load의 historical queued 검색/복구 동작은 보존한다.
- v7 durable paid slots는 planner model.request1 → search step2 → final model.request3다. 각 정확 function명/정수slot/완료를 metadata-only로 확인한다. queued 새 시작 외, retrieving 회복은 완료 planner1(추가 paid step 없음)만 재생 가능하며 미완료/불명확 planner는 실패·예약 유지다. generating/validating 회복은 planner1/search2/final3이 모두 정확 완료여야 하며 불명확 final은 재호출하지 않는다. 정의되지 않은/중복/위조 namespace·slot·extra paid step을 거부한다. DBOS journal/원래 ID/version을 재작성하지 않는다. single worker advisory lock·기존 멱등성/취소/권한/예산 계약을 유지한다.
- 최종 v7 provider/첫 요약·보수적 제공 자료 귀속/uncertain/typed timeline은 현재v6 경로를 재사용하고 canonical AIOutputV7=AIOutputV3다. documented canonical/정확 prefix/날짜/인용·공통v6 Unicode 검사를v7에도 적용한다. v6 자체 schema/지침/prompt bytes는 바꾸지 않는다. private 정확 issuedigest-research-v7/research-v7 review만 확장하고 과거 결과/공개v1/v2·빈 reviews/stripped-public 거부·API/OpenAPI shape·인증·UI 레이아웃·DB schema/권한·수집기는 그대로다. 새 생성도 독립 사실 검증으로 표시하지 않는다.
- 구현자는 합성 fixtures/전용 합성 PostgreSQL만 사용한다. 실제 키/원문/서버/네트워크/모델/자식 agent를 사용하지 않는다. controller가 독립/전체 gate·실제 작은 고정3질문(앱3실행/공급자최대6요청·자동재시도0)·개인 개발 보존/반영·Draft PR·Sites v65 기록 보존과 소유 QA 정리를 담당한다. 실제 사용자 로그인/질문을 대신하지 않고 키/접속/실제 원문/질문/ID를 커밋하지 않는다. 사용자 브라우저 탭을 열거나 이동하지 않는다.

## Task 1: 권한을 재확인하는 검색 도구·원자 근거 고정

- [x] ResearchRepository에 worker_prepare_search(run_id)->ResearchRun|None와 worker_search_and_fix(run_id, queries:tuple[str,...], *, input_tokens:int=0, output_tokens:int=0)->tuple[UUID,...]|None를 추가한다. 로직이 커지면 storage 내부 research_search.py로 분리한다. prepare는 read/현재 권한/부모 검증만 하며 worker가 retrieving 전이 후 사용할 수 있다. 검색을 먼저 하거나 no-match로 조기 실패하지 않는다. terminal/권한 거부는 기존 안전 경계로 끝낸다.
- [x] search_and_fix는 queries 형식/한도·사용량 한도를 검증하고 권한/row lock 재검사 후 원래 질문+계획의 bounded retrieval을 실행한다. 현재 search 최신 승인 검증을 재사용하고 deterministic round-robin/max5로 선택·정확 원문/presentation 검증·snapshot_ids를 같은 transaction에 고정한다. generic parent 재사용/새 주제 분리는 기존 계약대로다. 이미 고정된 실행은 새 검색0·새 상태 전이0·원래 근거를 검증해 같은 IDs를 반환한다. 검색0은 알려진 planner usage와 failed/insufficient_evidence를 원자 저장하고 None으로 끝낸다. 현재 권한 변경/취소 뒤 추가 조회/모델 작업을 진행하지 않는다.
- [x] 실제 전용 합성 PG TDD RED→GREEN: 원래검색0/계획검색성공·원래후보유지/중복/5개/3쿼리한도·다른 workspace 미유출·최신승인/오래된fallback차단·parent generic/새주제·허용후권한회수·검색0 usage/terminal재실행·row고정뒤색인/승인변경·동시fix·오염/transactionrollback을 검증한다. 기존 repository/retrieval/권한 회귀·Ruff/format/mypy를 통과하고 관련 README·Task1 체크박스·commit/report를 남긴다. 실제 모델/전체 gate/배포를 완료라고 표시하지 않는다.

## Task 2: v7 계획→검색→생성·비용/복구/읽기 결합

내부 함수 경계는 create_planner_v7/planning_prompt_v7(question,parent=None)/run_planner_v7(agent,prompt), create_agent_v7/model_prompt_v7(question,sources,parent=None,*,prior_input_tokens,prior_output_tokens)/run_agent_v7(agent,prompt,*,prior_input_tokens,prior_output_tokens)/build_canvas_v7다. 두 runner는 해당 요청의 output/input_tokens/output_tokens를 반환하며 합산은 worker 책임이다. SYSTEM_INSTRUCTIONS_V7=SYSTEM_INSTRUCTIONS_V6, AIOutputV7=AIOutputV3를 내보낸다. 기존 _create_classified_agent의 name version Literal을 v7/plan_v7로 좁게 확장해 모델 선택·DBOSDurability를 재사용할 수 있다. planner도 run_sync output_type을 실제 strict SearchPlanV7 tool로 override해 기본 canonical 출력 schema를 전송하지 않는다.

- [x] agents에 strict planner와v7 최종 경로를 TDD로 추가한다. provider 선택/DBOSDurability/PydanticAI one-request 경계를 재사용하되 과거 provider bytes는 바꾸지 않는다. planner queries만 받으며 실제 tool schema와 strict OpenAI normalized envelope/8,000 bound·prompt·1request/0retry를 검증한다. 최종은 v6 provider helpers/지침·변환을 재사용하고 planner 실제 usage를 차감한 dynamic prompt/remaining-token/max2,000/45초를 호출 전에 검사한다. 전체24,000/출력2,500·음수/가짜usage/형식실패/과대prompt/인용오염을 안전하게 거부한다.
- [x] worker에 여섯 profile과 planner·v7 workflow를 등록하고 기존v2~v6 execute 경로를 유지한다. v7은 prepare/current-state metadata guard→retrieving→planner1→검색 durablestep2→고정 원문 재검사→generating→최종3→검증/저장 순서다. 알려진 양쪽 usage를 합산하고 검색0은 최종 호출0, 취소/권한/검색오염·부모 불일치/불명확 유료 step 뒤 추가 모델0을 보장한다. recovery metadata guard는 v7 stage별 정확 순서와 모든 과거slot1을 구분한다. registry/cohort/orphan/single-worker 계약을 유지한다.
- [x] Python private validation·웹 client·UI classification에 정확v7 profile을 추가하되 canonical/API/public/기존v6 의미 guards·디자인은 보존한다. 실제 Python v7 builder 생성 합성 fixture→전체 client→열린 첫 요약/접힌 상세/정확 원문·nonanswer 경로를 검증한다. public v7 stripped reviews·혼합/누락/위조와 Unicode·prefix·날짜 경계를 거부한다.
- [x] 실제 합성PG에서 planner 완료/검색 기록 전 재생, 검색 commit뒤 checkpoint 유실의 멱등fix, final 완료 전후 재시작·두 유료 checkpoint 재생/추가 model0, incomplete/extra/가짜slot·취소/권한·누적usage·v2~v6 역사golden/checkpoint를 검증한다. 모든 관련 scoped Python/JS와 static/contract를 통과하고 README/AGENTS·Task2 체크박스·commit/report를 남긴다. 독립/전체 gate·실제 의미 인수·개인 개발/PR/Sites는 controller에 남긴다.

## Controller 인수

기반7ed6730·CI39197598861 success/이전 실행7566 전체3,967개를 재사용하며 무변경 baseline을 반복하지 않는다. 작업별/전체 독립 source 검토 뒤 소유 합성PG에서 전체lint/format/types/tests/build/contract를 실행한다. 기존 승인 공개 텍스트3건·합성 신원에 고정3질문(직접 질문·다른 표현의 같은 주제·없는 전국 여론)을 사용한다. 앱실행3/공급자최대6요청·실패 포함 분모 유지/추가 성공 재시도0, 실제 검색 선택/원문/문장/사용량/첫 요약을 직접 대조한다. 계획검색 회복은 합성 식별 corpus로도 구분 검증한다. 실제 표본이 질문/계획 연결을 잘못하면 그대로 한계로 기록한다.

개인 개발 적용은 활성0·새 소스/웹/API/단일worker·서버 밖 전후 full/app백업과 별도 복원23public 행 일치·기존 자료/로그인/공개/수집기/권한 보존·HTTPS를 확인해 수행한다. app 신규schema/권한/외부수집·main/운영 변경은 없다. PR43 기반 Draft PR을 생성/첨부하고 실제 번호를 쓴다. 마일스톤·현재/역사경계·실제 비용/한계·Sites 이전v65/문서 사본/게시와 소유 QA 정리를 기록한다. 기존v6 초기4+별도2/실패3·실제 자료 부족 분기 성공과 소표본 한계를 지우지 않는다.


## 구현·인수 결과 · 2026-10-19 KST

현재 개인 개발 웹/API/조사 worker는 `57c71ec`이며 [Draft PR44](https://github.com/DigestWorks/IssueDigest/pull/44)(PR43 기반)다. 새 private v7은 질문→검색어 계획1회→현재 권한의 승인 저장 색인 검색→최대5근거 원자 고정→최종 생성1회다. 원래 질문 검색을 항상 포함하고 계획 검색과 원래 질문 우선 라운드로빈으로 합친다. 계획은 근거가 아니며 외부 웹 탐색·자동 등록/공개 게시를 추가하지 않는다. 첫 요약·보수적 제공 자료 귀속·정확 인용·부족 응답과 기존 소비자 디자인을 유지한다.

전체 Python3,459+JS694=4,153개·lint/format/types/build/contract와 작업별/전체 독립 검토를 통과했다. raw boolean 사용량 검증 지적은 실제 응답/합산·cached 재생 경계에서 보완·재검토했다. 자체 합성 신원의 실제3상태·390/1440·두 테마·첫 열린 요약/접힌 상세·정확 원문/초점·재열람(읽기POST0/페이지오류0)을 확인했다. 기존v2~v6 provider bytes/지침/한도/유료slot1·결과와 공개 계약을 보존하며 새v7은 exact paid1/search2/paid3을 회복한다.

실제 고정3앱실행/공급자6요청·자동재시도0은 브리핑 완료1(의미 부분 충족)·자료 부족 완료1·검증 실패1이다. 원래 문자 검색0이던 영어 표현의 주택 질문은 계획 검색으로 정확 자료1건을 찾았으나, 최종 timeline이 원문에 없는 정확 날짜2개를 추정해 표시를 차단했다. 성공까지 다시 호출하지 않았다. 완료 답변의9문장/평가·선택 인용3개와 실패 checkpoint의6문장/인용을 직접 대조했다. 목표·실적·조건부 전망의 첫 결론은 읽히지만 세부 항목의 포함 관계 누락과 목표/확정 결과의 모호한 표현은 남았다. 자료에 없는 전국 찬성률·인지도는 생성하지 않고 근거 부족으로 끝났다. 검색 개선·구조 통과를 전체 의미 품질 완료로 해석하지 않는다. cached 실제 사용량은 입력9,413/출력2,087토큰이며3실행 지연은8.39/5.76/3.96초다. 모든 유료 응답6개를 확인했고 실제 청구 금액은 미검증이다. 실패/취소·권한 변경·응답 유실의 앱 usage0은 무료를 뜻하지 않으며 기존 보수적 예약을 유지한다. 이전v6 초기4(부족1/실패3)+별도2와v5 초기4+별도2의 실패·부분 충족 분모를 보존한다.

개발 웹/API/worker를 활성 작업0에서 정상 중지·재기동하고 단일 worker lock1·새 source/cwd·정적19파일/외부6assets 일치를 확인했다. 이전90assets/원래 source/복귀 경로와 수집기a908083/config/runner/cron을 보존했다. schema0009·자료15/인용49/검색36/receipt1/공개1·계정/세션·HTTPS/비회원401 경계를 유지했다. 서버 밖 사전·직전·사후 full/app 백업과 별도PG18.6 복원에서 직전/사후/백업 직후/복원의23public테이블 rowhash/count 전체 일치·15canonical을 확인했다. 실제 기존 AI 결과는0개이므로 역사 실제 결과 재생을 주장하지 않는다. DBOS registry·vector/역할까지 포함한 완전 DR은 아니다. main/운영 유예(D013)는 유지한다.

판단 기록: 원래 질문을 보존하고 선택적 이전 AI 맥락만 planner의 실제 JSON UTF-8 잔여 예산/code-point 경계로 줄이며 잘림을 명시한다. 최종 생성의 기존 bounded 맥락·원문/인용은 보존한다. 잘못되면 검색 계획의 관련성이 낮아질 수 있어 맥락 선택/예산 정책·테스트를 조정해야 하며, 과거 데이터 재작성이나 추가 모델 호출은 필요하지 않다. [D022 후속 판단](../planning/decisions.md)을 따른다.

다음 우선순위는 검색 잡음·날짜와 포함 관계의 의미 보존·다양한 실제 질문 평가 및 검증된 모듈 점진 전달이다. 다매체 발견·관심/변화/공유·개인화·pgvector/Neo4j 서비스 연결·외부 자율 탐색과 일반 B2C 품질/운영 출시는 후속이다. Sites 최종 게시/QA 정리 receipt는 [진행 기록](../planning/progress.md)이 원본이다.
