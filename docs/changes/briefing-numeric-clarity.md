# 첫 브리핑의 수치 관계·조건 설명

2026-10-19 KST. PR48/181bee1 후속 M3 구현이다. 사용자 ‘이어서 진행’과 D022의 실제 부분 충족을 근거로, 자료 선택을 유지하며 첫 요약의 수치 표현을 개선한다. OpenSpec root=null 확인: init 없이 이 단일 Spec/Global Constraints/Task를 사용한다.

## Spec · 목적과 경계

첫 요약에서 목표·중간 실적·조건부 전망, 포함된 항목과 전체를 명확히 구분한다. 포함관계를 설명하면서 전체를 ‘독립적으로 더해지는’ 수치로 바꾸지 않는다. 숫자·단위·대상·기간·하한/열린 상한을 원문대로 보존하고 전망 조건을 첫 답변에 담는다. 여러 주제 비교에는 각각의 출처·기준을 분리하며 자료가 없는 여론 수치·정확 날짜·인과를 만들지 않는다. 자유 문장의 의미 정확성은 schema로 인증할 수 없으므로 실제 답변을 별도 판정한다.

기존 v9 유료 요청·결과를 새 지침으로 재생하지 않기 위해 새 final/profile/workflow v10만 적용한다. 새 화면·기술 체크포인트·가상 최근 이슈·새 데이터 자동 승인/게시는 없다. 모바일 브리핑 디자인·로그인·공개 읽기·기존 근거/인용과 데이터/수집기는 유지한다.

## Global Constraints

- 기준181bee1cfe9ddfc807d91cd6664b406a843e4fe1, branch feat/briefing-numeric-clarity, PR48 기반 Draft PR. 기존 linked worktree를 재사용하며 baseline4,655개/sourceCI39224270248를 반복 실행하지 않는다. controller의 최종 변경 전체 gate는 별도다. main/운영(D013)은 병합/게시하지 않는다.
- 새로운 private research-v10 / issuedigest-research-v10, final issuedigest_research_v10, workflow issuedigest_research_run_v10. v2~v9·planner7·selector SDK의 실제 지침/tool/schema/prompt bytes·이름/version/slot과 결과를 보존한다. v9 worker 전체를 byte-identical fixture로 보관하고 실제 PG/DBOS 역사 v9 checkpoint를 재생한다. 과거 v2~v8 fixture/재생은 유지한다.
- v10은 알고리즘이 같은 기존 relevance protocol을 그대로 재사용한다. 정확 슬롯은 planner7 paid1→issuedigest_research_search_v9 step2→issuedigest_research_select_v9__model.request paid3→issuedigest_research_apply_v9 step4→issuedigest_research_v10__model.request paid5다. v9의 앞 네 이름/selector receipt 두 key는 그대로다. workflow ID가 요청별 분리돼 다른 실행의 checkpoint를 재사용하지 않는다. v9은 원래 final9/slot5다. 새로운 search/select/apply 복제 함수나 step은 만들지 않는다.
- 기존 v9 orchestration은 명시 v9/v10 final strategy(Agent/prompt/run/build/recovery profile)만 받는 공통 body로 작게 일반화한다. 새 모델 계약을 제외한 의미는 동일하다. legacy execute/planned body는 손대지 않는다. recovery metadata·속성·usage·terminal reconciliation 공통 helper는 exact Literal v9/v10만 허용하고 기존 v9 기본 public-internal wrappers/signatures/반환을 보존한다. arbitrary profile/prefix slicing(-2 등)/substring dispatch를 사용하지 않는다. workflow/model namespace·정수 nonbool 슬롯·완료 count/order·원래 입력 hash를 raw deserialize 전에 검사한다.
- v10도 시작 표식+원래 prompt SHA를 전송 전에 public DBOSClient attributes에 원자 저장한다. prefix2+표식은 모호 실패/재호출0, prefix>=3은 원래 hash와 재구성 입력을 대조한다. marker 두 key의 이름은 기존 issuedigest_select_v9_started / issuedigest_select_v9_prompt_sha256 그대로다. 현재 workflow의 exact v9/v10 identity도 검사해 혼합을 거부한다. 기존 D022 두 보수적 Ruling과 전송 전 실패/예약 유지·적법한 제목 변경의 replay 거절 비용은 유지한다. 회계용 원래 hash 형식 검증과 모델 재생의 현재 입력 검증을 혼동하지 않는다.
- 현재 권한/부모/모든 원문·후보 원래 순서·같은 selected만 원자 고정/재생하고 cached apply 뒤 uncached 검증한다. uncertain 보존·exclude만 제외, 선택 자료만 final prompt/evidence/title에 남긴다. 전부 제외/검색0은 최종 모델0과 알려진 usage를 유지한다. token-only 단조 합산/취소·권한변경·잘못된 DTO·전송유실/terminal SIGKILL 복원은 새 v10에서도 유지하고 status/result/예약을 바꾸지 않는다. DB/schema/API/HTTP/OpenAPI/권한을 바꾸지 않는다.
- v10 최종 tool/canonical은 v8 날짜 제한/v6 변환/공통 builder를 재사용한다. 지침은 frozen v8을 기반으로 새 짧은 수치 설명 규칙만 덧붙인다. 합성 예시는 허용하되 실제 평가 질문/원문/수치·ID를 지침/fixture/공개 기록에 넣지 않는다. 첫 답변에 포함관계·계획/실적/조건부 전망·조건/상하한을 유지하고 출처별 비교 기준을 분리하도록 명시한다. 정확 인용을 새 진실 인증으로 승격하지 않으며 핵심 근거가 없으면 기존 빈 modules의 자료 부족을 사용한다. 의미를 판정하는 취약한 금칙어/정규식 차단·응답 자동 고쳐쓰기·추가 모델 검수/수리는 만들지 않는다.
- v9/v10 final 공통 실행·budget은 작은 helper로 추출해 긴 복제를 피할 수 있다. v9 actual instructions/tool/prompt/budget/default model ownership을 정확 보존하는 golden checks를 먼저 둔다. 새 v10 instructions 길이와 모든 날짜0/1/16·인용 최대100의 raw/normalized tool schema 중 큰 실제/static envelope를 반영한다. combined prior exact nonbool/nonnegative total≤20,000/output≤1,000, 전체24,000/output2,500, final cap min(2,000,2,500-prior_output),45초·1요청·repair/retry0·Responses/storeFalse·gpt-5.4-mini는 동일하다. planner8,000/500/15초·selector12,000/500/15초·월USD10/건0.25/40건·월10만원도 유지한다. 원래 질문/whole bounded quotes를 잘라 지침 예산을 메우지 않는다. 최대100인용/16날짜의 동시 적재는 보장하지 않고 초과는 유료 호출 전 거부한다.
- 새 v10 factory는 Model 필수이며 잘못된 None/object/string은 기본 client 생성 전에 거부한다. 기존 v8 base model을 빌려 DBOS config 후 launch 전에 등록하고 주입 모델을 새로 생성/닫지 않는다. 기본 client ownership은 기존 경로가 소유한다. domain/client/UI에 정확 private v10만 좁게 추가하고 core-first·귀속 prefix·Unicode·정확 인용/날짜·AI review·위조/누락/혼합/stripped/public v1/v2 거부를 유지한다. OpenAPI/공개 경계를 확대하지 않는다.
- 구현자는 합성 fixture/FunctionModel과 controller 지정 loopback PostgreSQL25497만 쓴다. 실제 키/원문/서버/network/provider/container 관리·자식agent·baseline/full gate·push/PR/배포는 금지한다. TDD 실제 RED→GREEN·관련 검사·명시 commit/report·Task1만 완료한다. controller 소유 기밀 파일/실제 평가와 계획 인수 체크는 건드리지 않는다.
- controller는 작업별/전체 독립 검토와 최종 전체 gate·기존 고정3질문/같은 원문/gold/미판정을 유지한 실제 앱3회+다중주제 비교 신규1회(합계4앱·최대12provider·각최대3·추가 성공 재시도0)를 수행한다. 각 실행 전에 private receipt를 저장하고 실패를 분모에 남긴다. 신규 비교는 기존 기검토 공개 텍스트의 서로 다른 두 주제를 함께 요구하고 controller가 필수 두 자료를 사전 명시한다. 실제 질문/원문/ID/keys·raw응답은 private만. 모든 계획/선택·최종 주장/AI평가/인용을 직접 읽고 원래3과 신규1의 의미 판정/분모를 구분한다. 이전 v9 3/9·selector3·v8/v7/v6/v5의 실패/부분 분모를 유지한다. 원문 날짜/uncertain 실제 양성은 나오지 않으면 미검증으로 남긴다. 일반 정치 이슈/중립성/상품 전체 완료를 주장하지 않는다.
- controller의 개인 개발 적용은 활성0/기존 source·asset 보존/외부 전후 백업·별도 복원/자료·세션·공개·수집기 보존 조건에서만 수행한다. actual/source/gate/runtime/CI·PR/Sites 인수를 구분한다. Sitesv70 archive·요약/사본/native 게시와 소유 QA/SDD만 정리하고 사용자 탭은 열거나 이동하지 않는다.

## Task 1: 첫 요약 설명 v10과 기존 relevance protocol의 호환 실행

- [x] 새 finalv10 SDK·짧은 수치/조건 설명 지침·실제/static 예산·필수 borrowed model을 구현하고 긴 v9 실행 복제 없이 공통 helper를 사용한다. 먼저 v9 지침/tool/prompt/예산/합성 canonical 결과·클라이언트 수명 golden regression을 RED→GREEN으로 잠근다. 합성 포함관계/열린 상하한·서로 다른 기준의 비교·조건·날짜0/정확 날짜·자료 부족 응답을 실제 builder 경로에서 검증하되 forced model 예시를 의미 품질 인증으로 부르지 않는다.
- [x] 기존 relevance body/recovery/accounting를 exact v9/v10 strategy로 좁게 공통화하고 v10 workflow/final만 추가한다. 앞4개 namespace/receipt는 그대로 유지하며 all9 workflows의 original version/slot·완료 checkpoint만 회복한다. v9 frozen 실제 fixture로 paid3/적용/paid5/validation 복구를 검증하고 v10의 ambiguous marker·원래 hash 변경·선택 원문 축소·취소/권한·malformed DTO/완료 raw usage·terminal finally SIGKILL·현재 권한 재검사를 실제 PG/DBOS로 TDD 검증한다. 새 모델/step retry0·등록 후 owned model 수명·한도초과 전 final0·v9별 동일 namespace bytes 증거를 남긴다.
- [x] exact private v10 domain/client/UI와 실제 Python builder→fullclient/app/CanvasView fixture를 추가해 첫 열린 요약·접힌상세/분류·정확 근거/Unicode/date/nonanswer와 위조/누락/혼합/stripped/public 거부를 잠근다. API/OpenAPI·레이아웃·저장 schema·기존공개 contract는 유지한다.
- [x] 관련 Python/JS/Ruff/format/mypy/types/contract/diff와 raw/static/date0/1/16 최대 schema·instructions SHA/기존 provider bytes 증거, RED/GREEN·관련 README/AGENTS를 기록하고 명시 commit/report한다. Task1만 체크하고 controller 실제4/12·전체 gate/독립 검토/개발/PR/CI/Sites/정리를 완료로 대신 표시하지 않는다.

## Controller 인수

최종 검토·전체 gate·실제 원래3+신규다중주제1/최대12와 직접 읽기, 개발 보존 인수·PR/CI·Sites·소유 QA 정리는 확인 뒤 진행 기록에 누적한다. 이 Spec의 자유 문장 지침이 환각/중립성을 보장하는 것으로 표시하지 않는다.

## Controller 실제 의미 인수 · 개발 적용 보류

v10 수치 설명 지침은 구현했으나 실제 의미 인수는 통과하지 못해 개인 개발 적용을 보류했다. 개발 앱은 기존 ab6654e/v9를 유지한다. 코드 검사/모델 실행 성공과 답변 품질을 구분한다.

고정한 기존3질문+새 다중주제1을 각각 한 번 실행했다. 실제4앱/12요청·재시도0·완료4(답변3/제공 자료 한정 부족1)·실행 실패0이다. 원래3은 부분1·미충족1·적절한 부족1이며, 새1은 두 필수 주제를 보존했지만 부분 충족이다. 완전 충족 답변으로 판정한 것은0이다. 하한을 진행률로 단순화·병렬 항목의 잘못된 포함 관계·첫 요약의 전망 조건 누락이 남았다. 같은 모델의 supported 평가는 독립 사실 검증이 아니다.

선택 전 후보1/3/3/3→선택 후1/1/1/2이고 최종 입력에는 선택한 원문 전체 인용만 남았다. 원래 셋째의 human 미판정3은 유지하며 제외에 정답 가점을 주지 않는다. 계획4·선택 결정10·서로 다른 제공 인용15종·답변 주장20/AI평가20을 직접 읽었다. 실제 입력17,657/출력3,622토큰, 지연8.18/8.45/4.86/8.95초다. 앱 사용량과 완료 raw12개의 합계가 일치하며 청구 금액은 미검증이다.

이전 v9 3앱/9요청(좁은 충족1·부분1·적절한 부족1), selector 단독3, v8/v7/v6/v5의 실패/부분 분모는 별개로 보존한다. 같은 정부 텍스트3건의 소표본이며 일반 정치 이슈·중립성·상품 전체 품질을 인증하지 않는다. 실제 uncertain 결정/정확 날짜 양성은0으로 미검증이다. 실제 사용자 세션0·원문/질문/ID/raw응답은 비공개로 보존한다. 다음은 수치 대상·기간·포함 관계·관측/조건부 전망을 근거에 연결하는 구조를 먼저 설계하고, 이번 실패를 유지한 별도 평가를 하는 것이다. 지침만 추가하거나 성공까지 재요청하는 방식으로 통과를 주장하지 않는다.

작업별 독립 검토는65ffb5c 기준 Spec/품질 PASS(C0/I0/M0)다. 전체 gate6c36cd6의4,887개와 전체 브랜치 독립 검토(구현 Spec/품질 PASS/C0I0M0), [Draft PR49](https://github.com/DigestWorks/IssueDigest/pull/49)를 확인했다. 실제 의미 FAIL과 CI/Sites/정리는 진행 기록에서 구분한다. 새 Ruling은 없으며 D022의 기존 복구 판단/비용을 유지한다. 개인 개발 적용의 전제인 실제 품질 인수를 통과하지 못했으므로 배포를 수행하지 않는다.
