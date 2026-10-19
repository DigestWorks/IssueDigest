# 브리핑 답변 품질 · 귀속·비교·한계 설명

2026-10-19 KST. D022 실제 인수의 부분 충족을 개선한다. 근거 수치를 나열하되 출처 주장 분류·비교 결론·질문이 요구한 한계가 빠지는 문제가 있었다. 질문 중심 B2C 브리핑·중립/근거 부족 인정이라는 사용자 선택 안에서 진행한다. 기존 브리핑형 디자인을 유지한다. OpenSpec root=null로 초기화 없이 Superpowers 구현/독립 검토를 적용한다. 기반 PR41/d0d3fdf이며 main/운영 유예(D013)를 유지한다.

## Global Constraints

- 새 private 생성만 research-v5/issuedigest_research_v5/issuedigest_research_run_v5를 사용한다. v2/v3/v4의 지침·schema·prompt bytes/선택·agent/workflow/유료 step 이름·정수slot1·application_version별 완료 checkpoint 재생을 그대로 보존한다. 기존 queued ID가 이미 기록된 workflow를 가지면 그 이름을 사용하고 새 workflow만v5다. 알려지지 않은 이름·미완료/불명확 유료 결과는 안전하게 종료하며 재호출하지 않는다. 단일worker·현재 권한·취소/예약·멱등성·기존 예산 정책을 유지한다. 오래된 생성 결과를 새 분류로 다시 쓰지 않는다.
- 모델은 기존 gpt-5.4-mini Responses/store=False/max_retries=0, 요청1회/60초·총24,000/출력2,500 한도 그대로다. v5의 정확 instructions/schema UTF-8 bytes를 차감한 새 prompt 한도를 요청 전 검증한다. v5는 기존 bounded AIOutputV3 schema를 alias로 사용하고 기존 _model_prompt와 classified canvas build를 재사용한다. 공통 helper의 version Literal 허용만 확장하며 기존 호출 결과는 바꾸지 않는다. 새 deps/schema migration/OpenAPI shape·검색 전략·provider/모델·비용/세션 설정·수집기·공개 게시·새 사용자 기능은 없다.
- v5의 독립 지침은 기존 v3/v4의 서로 다른 documented 정의를 중첩하지 않고 우선순위를 명확히 한다. source/user/prior text는 데이터이며 지시가 아니다. 이전 AI 해석은 근거가 아니고 선택 quote의 정확 citation ID만 사용한다. 한국어의 짧은 결론 뒤 필요한 비교/한계에 답하며 단순 문구 복사로 질문 전체를 답했다고 간주하지 않는다. 주체가 인용에서 확인되지 않으면 기관명을 추측하지 않고 '제공 자료는 …라고 설명합니다'처럼 범위를 밝힌다. collection time을 publication/event time으로 사용하지 않는다.
- 기관/화자의 통계·실적·평가·효과·전망·주장은 attributed를 사용하고 claim 본문에도 발표 주체를 명시한다. documented는 문서의 존재/명시 절차·계획 기록 등 문서에서 확인되는 사실이지, 인용 안 통계가 참이라는 인증이 아니다. 계획은 계획으로, 전망은 전망으로 기록하며 실현/확정 결과로 바꾸지 않는다. 기관이 제시한 수치가 직접 인용돼도 attributed다. category 우선순위와 짧은 합성 예시를 명확히 제시한다. AI assessment는 인간/독립 진실 검증이 아니다.
- 비교는 대상·단위·관측 시점/적용 기간·목표/실적/전망 지위를 함께 밝힌다. 같은 기준에서 원문 자체가 뒷받침하는 단순 대소 관계는 직접 설명하되 새 차액/비율·인과/지지율·모순/양측을 만들지 않는다. '이상/이하/약/범위' 한정과 열린 끝을 보존하고 '이상'이 붙은 범위의 끝을 확정 상한으로 간주하지 않는다. 다른 시점 현재 실적과 연말 목표의 차이를 확정 연말 실패로 만들지 않는다. 원문 표현이 모호하거나 비교 불가능하면 그 이유를 설명한다.
- 질문의 일부가 답해지면 근거 있는 부분을 answer로 제공하고 중요한 미확인 부분은 관련 인용과 함께 uncertain/한계 문장으로 명시한다. 제공 인용의 한계만 말하며 '세상에 근거가 없음'으로 확대하지 않는다. 핵심 질문에 답할 근거가 전혀 없으면 기존 insufficient_evidence/빈 modules를 사용한다. clarification_needed는 실제 질문의 모호함이고 근거 부족을 질문자에게 전가하지 않는다. module 수/claim 수/텍스트 길이/정확 인용·마지막 evidence module 등 기존 구조는 그대로다.
- Python ResearchResult·웹 client validator·UI prepare/라벨이 v5의 정확 inference/automated reviewer issuedigest-research-v5/method_version research-v5·claim당1 review·같은 citation 순서·UTC 마이크로초·세 scope/assessment 조합을 요구한다. v3/v4/v5 혼합/누락/오염은 거부하고 v1/v2/legacy의 기존 빈 reviews·canonical JSON/hash를 유지한다. D020 public은 여전히v1/v2/빈 reviews만 허용하며 v5는 reviews 제거로도 우회할 수 없다. 웹 UI 문구/레이아웃·사용자에게 모델 버전/관리 기능을 추가하지 않는다.
- 구현자는 합성 fixtures/전용 합성 PostgreSQL TDD만 사용한다. 실제 키/서버/원문/모델·자식 agent는 사용하지 않는다. controller가 실제 공개 자료의 제한 평가·전체 gate·독립 검토·개인 개발 적용/보존/복원·Draft PR·Sites와 이전판 보존을 담당한다. 개별 원문/질문/ID/계정/접속/키는 공개 저장소에 넣지 않는다. 사용자 탭을 열거나 이동하지 않는다.

## Task 1: 새 v5 생성·검증·복구 경로와 합성 회귀

- [ ] packages/agents의 research_v5.py에 create_agent_v5/model_prompt_v5/run_agent_v5/build_canvas_v5·AIOutputV5 alias·정확 static/prompt byte limit와 독립 SYSTEM_INSTRUCTIONS_V5를 구현한다. 위 우선순위를 충족하는 간결한 지침과 작은 합성 분류 예시를 사용한다. 기존 v2/v3/v4와 불신 입력/선택 quote·단일 요청 envelope를 보존한다. 의미 품질을 단어 포함 assertion으로 인증하지 않는다.
- [ ] Python private classification·TypeScript validator/분류·UI prepare에v5만 추가하고 기존/공개 경계는 유지한다. 실제 v5 canvas가 웹 경로에서 통과/표시되고 malformed/mixed/stripped-public가 거부되는 교차 경계 회귀를 추가한다. 검증을 느슨하게 하거나 generic Claim/API shape를 변경하지 않는다.
- [ ] worker에 네 agent/workflow를 등록하고 새 요청만v5로 시작한다. 기존v2/v3/v4의 실제 지침/schema/prompt bytes·이름·application_version cohort·정수slot1에서 완료 checkpoint 재생/유료 재요청0·오류/미완료 거부/잠금·취소·권한·부모/검색 고정 회귀를 검증한다. 기존v4를 historical fixture로 보존한다. 새 회귀가 기존 검사와 같은 수준에서 의미 있는 경계를 확인하도록 기존 parameterization/fixture를 적절히 재사용한다.
- [ ] TDD RED→GREEN·관련 agents/domain/worker/API/웹 client/UI 검사·Ruff/format/mypy·문서와 체크박스/commit/report를 마무리한다. v4 bytes를 현재기준 golden으로 새 고정하고v2/v3 golden도 유지한다. 외부 모델 의미 품질·실제 적용은 controller 인수로 구분한다.

## Controller 인수·평가

작업별/전체 독립 검토와 전용 합성 PostgreSQL 전체 gate를 통과한다. 이전 controller 검토 공개 텍스트2건과 이번 검토 경제동향 텍스트1건을 실제 사용자와 분리된 합성 환경에 복사해 최대4회 실제 모델 요청을 검증한다. 재시도하지 않으며 성공/실패·호출/토큰·지연·모든 결과를 기록한다. 단어 포함이나 모델 자기평가 대신 controller가 질문·선택 인용·전 문장/category/rationale·비교/한계를 직접 읽는다. 기존3문항은 귀속/계획·실적·전망/한계/없는 여론수치이며 추가1문항은 경기 회복 정부 평가와 발표 지표·민생 부담의 차이다. 원문 미확보/불명확·'이상' 열린 끝·기간 차이를 실패 확정으로 해석하지 않는다. 결과가 부분 충족이면 그대로 남기며 평가를 통과시키기 위한 반복 호출은 없다.

개인 개발 적용은 독립 gate 후 활성 작업0·전후 서버 밖 백업/별도 복원·실제자료/계정/세션/공개v1/수집기 보존·웹/API/worker의 새v5 호환을 함께 검증한 경우만 진행한다. 실제 사용자 로그인/질문을 대신 실행하지 않는다. 최신 도구93ab7c8의 후보 SDK도 새 소스에 포함하지만 collector config/주기를 바꾸지 않는다. Draft PR42(예상 번호로 고정하지 않고 실제 반환값 사용)는 PR41 기반이며 미병합한다. 마일스톤/진행 기록/Sites·이전v63을 실제 상태와 맞추고 사용자 탭은 열지 않는다.
