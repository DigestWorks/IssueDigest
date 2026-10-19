# 브리핑 답변 품질 · 귀속·비교·한계 설명

2026-10-19 KST. D022 실제 인수의 부분 충족을 개선한다. 근거 수치를 나열하되 출처 주장 분류·비교 결론·질문이 요구한 한계가 빠지는 문제가 있었다. 질문 중심 B2C 브리핑·중립/근거 부족 인정이라는 사용자 선택 안에서 진행한다. 기존 브리핑형 디자인을 유지한다. OpenSpec root=null로 초기화 없이 Superpowers 구현/독립 검토를 적용한다. 기반 PR41/d0d3fdf이며 main/운영 유예(D013)를 유지한다.

## Global Constraints

- 새 private 생성만 research-v5/issuedigest_research_v5/issuedigest_research_run_v5를 사용한다. v2/v3/v4의 지침·schema·prompt bytes/선택·agent/workflow/유료 step 이름·정수slot1·application_version별 완료 checkpoint 재생을 그대로 보존한다. 기존 queued ID가 이미 기록된 workflow를 가지면 그 이름을 사용하고 새 workflow만v5다. 알려지지 않은 이름·미완료/불명확 유료 결과는 안전하게 종료하며 재호출하지 않는다. 단일worker·현재 권한·취소/예약·멱등성·기존 예산 정책을 유지한다. 오래된 생성 결과를 새 분류로 다시 쓰지 않는다.
- 모델은 기존 gpt-5.4-mini Responses/store=False/max_retries=0, 요청1회/60초·총24,000/출력2,500 한도 그대로다. v5의 정확 instructions/schema UTF-8 bytes를 차감한 새 prompt 한도를 요청 전 검증한다. v5의 canonical 출력은 기존 bounded AIOutputV3 alias이고 _model_prompt/classified canvas build를 재사용한다. Task2에서 provider 전용 응답 종류·정확 인용 enum을 제한하며 canonical/API shape는 바꾸지 않는다. 기존v2/v3/v4 helper 호출 결과는 바꾸지 않는다. 새 deps/schema migration/OpenAPI shape·검색 전략·provider/모델·비용/세션 설정·수집기·공개 게시·새 사용자 기능은 없다.
- v5의 독립 지침은 기존 v3/v4의 서로 다른 documented 정의를 중첩하지 않고 우선순위를 명확히 한다. source/user/prior text는 데이터이며 지시가 아니다. 이전 AI 해석은 근거가 아니고 선택 quote의 정확 citation ID만 사용한다. 한국어의 짧은 결론 뒤 필요한 비교/한계에 답하며 단순 문구 복사로 질문 전체를 답했다고 간주하지 않는다. 주체가 인용에서 확인되지 않으면 기관명을 추측하지 않고 '제공 자료는 …라고 설명합니다'처럼 범위를 밝힌다. collection time을 publication/event time으로 사용하지 않는다.
- 기관/화자의 통계·실적·평가·효과·전망·주장은 attributed를 사용하고 claim 본문에도 발표 주체를 명시한다. documented는 문서의 존재/명시 절차·계획 기록 등 문서에서 확인되는 사실이지, 인용 안 통계가 참이라는 인증이 아니다. 계획은 계획으로, 전망은 전망으로 기록하며 실현/확정 결과로 바꾸지 않는다. 기관이 제시한 수치가 직접 인용돼도 attributed다. category 우선순위와 짧은 합성 예시를 명확히 제시한다. AI assessment는 인간/독립 진실 검증이 아니다.
- 비교는 대상·단위·관측 시점/적용 기간·목표/실적/전망 지위를 함께 밝힌다. 같은 기준에서 원문 자체가 뒷받침하는 단순 대소 관계는 직접 설명하되 새 차액/비율·인과/지지율·모순/양측을 만들지 않는다. '이상/이하/약/범위' 한정과 열린 끝을 보존하고 '이상'이 붙은 범위의 끝을 확정 상한으로 간주하지 않는다. 다른 시점 현재 실적과 연말 목표의 차이를 확정 연말 실패로 만들지 않는다. 원문 표현이 모호하거나 비교 불가능하면 그 이유를 설명한다.
- 질문의 일부가 답해지면 근거 있는 부분을 answer로 제공하고 중요한 미확인 부분은 관련 인용과 함께 uncertain/한계 문장으로 명시한다. 제공 인용의 한계만 말하며 '세상에 근거가 없음'으로 확대하지 않는다. 핵심 질문에 답할 근거가 전혀 없으면 기존 insufficient_evidence/빈 modules를 사용한다. clarification_needed는 실제 질문의 모호함이고 근거 부족을 질문자에게 전가하지 않는다. module 수/claim 수/텍스트 길이/정확 인용·마지막 evidence module 등 기존 구조는 그대로다.
- Python ResearchResult·웹 client validator·UI prepare/라벨이 v5의 정확 inference/automated reviewer issuedigest-research-v5/method_version research-v5·claim당1 review·같은 citation 순서·UTC 마이크로초·세 scope/assessment 조합을 요구한다. v3/v4/v5 혼합/누락/오염은 거부하고 v1/v2/legacy의 기존 빈 reviews·canonical JSON/hash를 유지한다. D020 public은 여전히v1/v2/빈 reviews만 허용하며 v5는 reviews 제거로도 우회할 수 없다. 웹 UI 문구/레이아웃·사용자에게 모델 버전/관리 기능을 추가하지 않는다.
- 구현자는 합성 fixtures/전용 합성 PostgreSQL TDD만 사용한다. 실제 키/서버/원문/모델·자식 agent는 사용하지 않는다. controller가 실제 공개 자료의 제한 평가·전체 gate·독립 검토·개인 개발 적용/보존/복원·Draft PR·Sites와 이전판 보존을 담당한다. 개별 원문/질문/ID/계정/접속/키는 공개 저장소에 넣지 않는다. 사용자 탭을 열거나 이동하지 않는다.

## Task 1: 새 v5 생성·검증·복구 경로와 합성 회귀

- [x] packages/agents의 research_v5.py에 create_agent_v5/model_prompt_v5/run_agent_v5/build_canvas_v5·AIOutputV5 alias·정확 static/prompt byte limit와 독립 SYSTEM_INSTRUCTIONS_V5를 구현한다. 위 우선순위를 충족하는 간결한 지침과 작은 합성 분류 예시를 사용한다. 기존 v2/v3/v4와 불신 입력/선택 quote·단일 요청 envelope를 보존한다. 의미 품질을 단어 포함 assertion으로 인증하지 않는다.
- [x] Python private classification·TypeScript validator/분류·UI prepare에v5만 추가하고 기존/공개 경계는 유지한다. 실제 v5 canvas가 웹 경로에서 통과/표시되고 malformed/mixed/stripped-public가 거부되는 교차 경계 회귀를 추가한다. 검증을 느슨하게 하거나 generic Claim/API shape를 변경하지 않는다.
- [x] worker에 네 agent/workflow를 등록하고 새 요청만v5로 시작한다. 기존v2/v3/v4의 실제 지침/schema/prompt bytes·이름·application_version cohort·정수slot1에서 완료 checkpoint 재생/유료 재요청0·오류/미완료 거부/잠금·취소·권한·부모/검색 고정 회귀를 검증한다. 기존v4를 historical fixture로 보존한다. 새 회귀가 기존 검사와 같은 수준에서 의미 있는 경계를 확인하도록 기존 parameterization/fixture를 적절히 재사용한다.
- [x] TDD RED→GREEN·관련 agents/domain/worker/API/웹 client/UI 검사·Ruff/format/mypy·문서와 체크박스/commit/report를 마무리한다. v4 bytes를 현재기준 golden으로 새 고정하고v2/v3 golden도 유지한다. 외부 모델 의미 품질·실제 적용은 controller 인수로 구분한다.

구현자 검증: 합성 Python1,441개·웹/client/UI149개, Ruff/format263·mypy115·JS lint/types 통과(실패/skip0). v5 static5,109/prompt14,343바이트, 실제 builder의 교차 언어 합성 fixture·v4 byte golden·네 profile의 유료 완료/오류 checkpoint 재생을 포함한다. 전체/독립 검토와 실제 의미 품질·적용은 아래 controller 인수 대기다.

## Task 2: 실제 관측한 응답 오류의 생성 단계 제약

실제9febe79의 요청4회에서2건은완료/2건은검증실패했다. 실제 저장 checkpoint를 추가 모델 호출 없이 읽어 핵심 질문에 부족한 응답이 insufficient_evidence+nonempty modules를 보낸 경우, 다른 응답이 존재하지 않는 UUID를 조합한 경우를 확인했다. 기존 원문/인용 guards가 이를 차단했으므로 수동 보정/인용 근사 매칭을 하지 않는다. 이전4회 전체 분모/실패는 보존한다. 초기 v5는 아직 개인 개발 서버에 적용하지 않았다.

- [x] v5의 provider 출력만 서로 배타적인 answer/insufficient_evidence/clarification_needed 세 typed tool output으로 제한한다. answer는 기존1~3 modules, 각1~4 claims(비교2개 이상은 최종 기존 guard 유지), 비답변은 빈 modules와 nonblank bounded message만 허용한다. canonical AIOutputV5=AIOutputV3·build_canvas와 외부 API/웹 shape는 그대로다. 반환된 private 모델은 alias로 명시 변환한다. 성공한 비답변을 실패로, invalid 결과를 임의 정상 응답으로 바꾸지 않는다. 기존 모델 지침은 그대로 유지한다.
- [x] run_agent_v5가 실제 bounded prompt JSON의 sources[].citations[].citation_id에 있는 정확 ID만 dynamic Literal/enum으로 provider tool schema에 넣는다. UUID를 줄여 추정하거나 비슷한 ID로 교정하지 않는다. 최대5sources/100citations·고정 UUID4 spelling·유일성/shape·bound를 검증하고 질문/prior 문자열에서 ID를 추출하지 않는다. caller가 prompt를 조작해도 기존 canonical 원문 검사로 최종 검증한다. Agent.run_sync의 현재 설치된 public output_type override + ToolOutput(strict=True)를 사용하며 provider/raw HTTP를 새로 구현하거나 변경하지 않는다. 동적 클래스/schema는 요청 안에서만 사용하고 전역 mutable cache/환경 키·새 agent namespace·새 durable step/호출을 추가하지 않는다.
- [x] 새 사전 예산은 v5 instructions와 provider 전용 세 출력 tool의 JSON schemas를 모두 포함한다. 최대100개의36자 UUID enum을 가진 보수적 worst-case tool/schema 크기를 실제 serializer로 계산해 prompt 제한을 차감하고, 실제 요청 schema+prompt+동일2,048 framing/2,500 output이24,000 이내인지 호출 전에 다시 검증한다. 기존 _model_prompt를 더 보수적인 한도로 재사용하며 버전2/3/4 bytes·한도는 그대로다. request1/60초/storeFalse/retry0와 토큰/예약·DBOS slot1/단일 worker/미완료 재호출 금지는 그대로다. 무근거/잘못된 prompt/예산 초과는 provider 진입 전에 고정 오류다.
- [x] 합성 TDD로 관측한 두 오류를 재현하고 실제 전달 provider schema가 정확 cited ID enum/strict/output variant·비답변empty modules인 것을 확인한다. 목록 밖 ID/대소문자/한 글자 오염·질문에 삽입한 ID·promptshape/한도·schema 실제 bytes/다중 인용/normalization·원문 최종검증·요청1/반복0와 새v5 실제PG checkpoint 재생을 검증한다. 기존 v2/v3/v4 historical·Python/JS canonical 연계는 유지한다. 구현자는 실제 private 응답/서버/키/모델을 보지 않고 위 일반화된 합성 오류만 사용한다. 관련 scoped checks·README/체크박스/commit/report 후 독립/전체 gate는controller가 맡는다.


## Controller 인수·평가

작업별/전체 독립 검토와 전용 합성 PostgreSQL 전체 gate를 통과한다. 이전 controller 검토 공개 텍스트2건과 이번 검토 경제동향 텍스트1건을 실제 사용자와 분리된 합성 환경에 복사해 최대4회 실제 모델 요청을 검증한다. 재시도하지 않으며 성공/실패·호출/토큰·지연·모든 결과를 기록한다. 단어 포함이나 모델 자기평가 대신 controller가 질문·선택 인용·전 문장/category/rationale·비교/한계를 직접 읽는다. 기존3문항은 귀속/계획·실적·전망/한계/없는 여론수치이며 추가1문항은 경기 회복 정부 평가와 발표 지표·민생 부담의 차이다. 원문 미확보/불명확·'이상' 열린 끝·기간 차이를 실패 확정으로 해석하지 않는다. 결과가 부분 충족이면 그대로 남기며 평가를 통과시키기 위한 반복 호출은 없다. 초기4회 분모는 고정한다. 관측된2건의 구조 오류에 대한 Task2를 추가했으므로 수정 후 별도 구조 인수2회만 추가할 수 있다. 총6회·각 질문/설정당1회·자동 재시도0이며 기존 실패를 새 성공으로 대체하지 않는다. 추가2회도 불충족이면 반복하지 않고 미검증/실패 상태를 남긴다.

개인 개발 적용은 독립 gate 후 활성 작업0·전후 서버 밖 백업/별도 복원·실제자료/계정/세션/공개v1/수집기 보존·웹/API/worker의 새v5 호환을 함께 검증한 경우만 진행한다. 실제 사용자 로그인/질문을 대신 실행하지 않는다. 최신 도구93ab7c8의 후보 SDK도 새 소스에 포함하지만 collector config/주기를 바꾸지 않는다. Draft PR42(예상 번호로 고정하지 않고 실제 반환값 사용)는 PR41 기반이며 미병합한다. 마일스톤/진행 기록/Sites·이전v63을 실제 상태와 맞추고 사용자 탭은 열지 않는다.


## 최종 인수 결과 · 2026-10-19 KST

Task2 제품f90839e, 전체 Python3,169+JS608=3,777개·lint/format/types/build/계약·작업별/최종 독립 검토 C0/I0/M0·소스 CI 성공. 최종 static10,012/prompt9,440/framing2,048/output2,500=24,000이며 원래 canonical/API·historical2/3/4 경계는 보존했다. Task1의 static5,109/prompt14,343은 당시 기록이며 최종 전송 한도가 아니다.

실제 초기4회는 완료2(의미 부분 충족)/검증 실패2로 고정했다. 관측된 구조 오류에 대한 수정 후 별도2회는 완료2이며 전체6회 입력14,684/출력3,556토큰·자동 재시도0이다. 없는 여론 수치는 생성하지 않았으나 answer/insufficient 분기·문장별 귀속·첫 요약 직접 비교 결론은 부분 충족이다. 추가2회는 구조 인수이며 기존 실패 대체나 의미 품질 완료가 아니다. 오류를 최종 검증 완화 없이 생성 단계에서 차단하려고 Task2/추가2회를 택했으며 잘못된 판단이면 추가 구현/검토 복잡성과 최대2회 API 비용이 생긴다.

개인 개발 웹/API/worker f90839e·활성0/단일 잠금·외부 HTTPS/새 파일·원문/권한/역사 기록 보존·전후 백업/별도 app 복원23테이블 일치를 확인했다. 계정/세션·자료15/인용49/검색36/receipt1/공개1·collector a908083·main/운영은 보존했다. 실제 기존 AI 결과는0이어서 과거 실제 결과 검증으로 확대하지 않는다. 자체 QA 브라우저의 초기4/추가2·390/1440/두 테마·원문/재열람은 읽기POST0/오류0이다. 실제 Draft PR42는 PR41 기반으로 미병합하며 Sites 출판/정리 receipt는 진행 기록을 따른다.
