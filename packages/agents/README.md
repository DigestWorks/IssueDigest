# Agents

에이전트 조율·근거 검증 위치. 모델 호출과 UI 렌더링을 분리한다. 조사 실행은 별도 DBOS worker가 명시적으로 시작하며 import나 기본 API 시작 때 유료 호출을 하지 않는다.

## 조사 제안과 캔버스 검증

`issuedigest_agents.research`는 PydanticAI의 명명된 agent와 DBOSDurability capability를 사용합니다. 모델은 summary/comparison/timeline 제안·문장·기존 citation ID만 반환합니다. 서버가 질문에 맞춰 찾고 고정한 immutable EvidenceBundle 인용을 검증한 뒤 `CanvasBundle`을 새로 구성하며 모든 AI 문장은 `basis=inference` 및 derivation으로 기록합니다. 독립 사실 검증이나 인간 검토로 표시하지 않습니다. timeline 날짜는 인용된 정확한 `YYYY-MM-DD` 문자열이 없으면 거부하고 수치 chart/graph는 생성하지 않습니다. 본문·질문은 지시가 아닌 불신 입력으로 제한하고 외부 도구를 등록하지 않습니다.

역사 v5 질문은 `issuedigest_agents.research_v5`의 `AIOutputV5`·`create_agent_v5`·`model_prompt_v5`·`build_canvas_v5`를 사용합니다. 각 claim은 documented/attributed/uncertain과300자 이하 설명을 필수 제공하며 기존 inference claim과 같은 인용 순서의 자동 SupportReview1개로 투영합니다. content/supported·attribution/supported·content/insufficient만 허용합니다. 고정 reviewer_id는 `issuedigest-research-v5`이며 실제 인간을 뜻하지 않습니다. 공통 UTC reviewed_at/validated_at을 마이크로초까지 대조하고 혼합/누락/중복/잘못된 참조를 거부합니다.

v3 prompt는16,049 UTF-8바이트, 고정 지시/스키마3,403바이트·framing2,048·출력2,500을 포함한24,000 한도입니다. 기존v2는 원래 출력 schema·agent/DBOSDurability 이름·지침·prompt17,309바이트/고정2,143바이트를 보존해 기존 유료 checkpoint를 재생합니다. 원래 public 함수와 저장된v1/v2 결과를 유지하고 과거 분류를 추정하지 않습니다. 역사 v2~v6는 gpt-5.4-mini/Responses no-store·요청1회·retry0·출력2,500을 유지합니다. collected_at은 수집 시각이며 발행일/이벤트가 아니고 proposed_on은 법안 제안일만 뜻합니다.

역사 v4의 schema는 v3의 bounded schema를 그대로 재사용하며 지침·agent/workflow/review 식별자로 분리한다. v4는 기관 통계·효과·평가·주장을 귀속하고 목표·실적·전망·확정 결과를 구분한다. 동일 대상·기간·단위에서 검증 가능한 단순 대소 관계를 설명하고 새 계산·인과·양측을 강제하지 않는다. v4 static schema/instructions4,639바이트, prompt14,813바이트이며 총 한도는 동일하다. v2/v3 지침/schema/prompt bytes와 유료 namespace/slot1은 그대로 보존한다. 합성 모델의 고정 출력은 전달·계약 회귀이며 실제 의미 품질은 controller의 별도 원문 평가가 필요하다.


v5는 기존 bounded AIOutputV3 schema의 alias이며 v3/v4 지침을 이어 붙이지 않는 독립 지침이다. 수치/평가/실적·전망의 귀속을 우선하고 문서 기록·계획과 구분한다. 질문 전체의 짧은 결론·가능한 비교·미확인 한계를 인용한 표시 claim에 담으며 answer.message는 표시하지 않는다. '이상' 열린 끝·서로 다른 기간·목표/실적을 보존하고 부분 답변과 핵심 근거 부족을 구분한다. v5 canonical `AIOutputV5`는 alias를 유지하며 provider에만 answer/insufficient_evidence/clarification_needed 세 typed strict output tool을 요청마다 지정한다. answer는1~3 modules·각1~4 claims, 비답변은 빈 modules·공백이 아닌500자 이하 메시지만 허용한다. 실제 bounded prompt의 sources 인용에서만 UUID4의 정확한36자 표기를 enum으로 만들며 최대5 sources·각32/총100개의 유일한 인용 ID를 검증한다. 질문/이전 해석의 ID는 후보가 아니며 잘못된 철자·목록 밖 ID를 교정하지 않는다. 반환값을 기존 canonical alias로 명시 변환하고 기존 원문/비교 검증을 그대로 통과시킨다.

최대100 UUID를 가진 세 tool의 메타데이터/스키마는 실제 JSON serializer로 정규화 전6,514/후6,417바이트이며 더 큰 값을 예약한다. 독립 지침3,498바이트를 더한 고정 예산10,012바이트·prompt9,440바이트이며 실제 요청의 스키마+prompt+framing2,048+출력2,500이24,000 이내인지 다시 확인한다. `Agent.run_sync(output_type=...)`와 `ToolOutput(strict=True)` 공개 API만 사용하고 요청/시간/토큰 한도는 동일하다. v2/v3/v4의 지침/schema/prompt 선택은 고정 SHA-256 회귀로 보존하고 각 namespace/slot1을 재생한다. `packages/agents/tests/v5_fixture.py`의 합성 생성 자료를 웹 client→UI→정확 원문 흐름에서 검사한다. 이는 실제 모델 의미 품질 평가가 아니다.


역사 private v6 생성은 `research_v6`다. canonical `AIOutputV6`는 기존 `AIOutputV3` alias이며 documented/attributed/uncertain과 기존 domain/client guards를 그대로 허용한다. provider 전용 answer는 summary_title(1~100), core_answer1개, additional_summary_claims0~3개, details0~2개(comparison/timeline)다. core가 첫 summary의 첫 claim이 되고 상세와 최종 evidence가 뒤따른다. answer에는 message가 없고 핵심에 직접 근거가 없으면 insufficient_evidence의 빈 modules와 자료 범위의 nonblank message를 쓴다. 주제 관련 문서 존재만으로 전국 찬성률/인지도에 답하지 않으며 비교 질문은 첫 core의 직접 결론을 요구한다. 이는 실제 의미의 정확성을 증명하지 않는다.

Task2 provider DTO는 category/source_subject를 요구하지 않는다. core는 text/rationale/citation_ids만 받고 항상 attributed로 변환한다. 추가 요약과 상세 claim은 assessment: source_statement 또는 uncertain을 받으며 각각 attributed/uncertain으로 변환한다. 긍정 해석의 주체는 서버가 고정 `제공 자료`로 조합한 `제공 자료에 따르면, {text}`다. uncertain에는 접두어를 붙이지 않는다. 모델 본문의 기관명을 추측하지 말라는 지침을 유지하지만 source_statement가 참이거나 주체가 맞다는 인증은 아니다. 새 생성에서 documented로 승격하지 않으며 기존 canonical documented/정확 custom-subject 검증·공개 경계는 유지한다. 구 DTO의 필드나 모순 조합을 수동 수리하지 않는다.

provider 본문은1~400자, rationale은1~300자이며 공통 Unicode nonblank 검사를 한다. core/summary/comparison에는 event_date 키 자체가 없고 timeline의 별도 typed DTO만 exact YYYY-MM-DD 필수 날짜를 받는다. datetime/epoch/월 단위를 날짜로 보정하지 않으며 최종 원문 인용의 exact 날짜도 다시 검증한다. 기존 canonical500자·원문·날짜·비교 guards와 issuedigest-research-v6/research-v6 reviewer, 혼합·누락·불확실 첫 core 거부를 유지한다. nonblank는 Python Unicode whitespace와 ECMAScript WhiteSpace/LineTerminator 합집합으로 통일하며 NEL(U+0085)·BOM(U+FEFF) 단독/혼합 공백을 거부한다. 유효한 앞뒤 공백과 원문은 보정하지 않는다.

동적 UUID enum은 요청마다 native TypeAliasType 공유 참조로 한 번 정의하며 질문/prior ID를 합치지 않는다. 최대100개 인용의 실제 세 tool 직렬화는 raw8,092/normalized7,952바이트, 독립 지침3,009바이트, 예약 static11,101바이트·prompt8,351바이트다. 두 detail 타입의 스키마를 모두 예약하므로 기존 Task1보다 prompt 공간이 줄었다. 실제 요청도 총24,000(출력2,500·framing2,048 포함)을 사전 검증하며 gpt-5.4-mini Responses/storeFalse/max_retries0·요청1회/60초를 유지한다. historical v2/v3/v4/v5의 실제 지침/schema/raw·normalized provider schemas/prompt 선택과 유료 namespace/slot1은 동결한다.

`tests/v6_fixture.py`가 새 provider DTO 변환과 builder를 실제 실행해 합성 JSON을 재생성한다. 웹 client→열린 첫 요약/접힌 상세→정확 원문을 검사하며 astral 본문400자도 서버 고정 접두어로 만든다. 기존 canonical custom-subject/80자·documented 검증은 별도 호환 검사다. Python과 v6 웹 길이 검사는 Unicode code-point 기준을 쓰고 과거 raw-client UTF-16 동작·profile 없는 비답변 경계는 유지한다. 합성 모델 통과를 실제 모델 의미 품질 통과로 표시하지 않는다. 전체 gate·독립 review·실제 모델/자료·개인 개발 반영은 controller 인수다.


## Private v7 계획과 최종 생성

`research_v7`는 `create_planner_v7`/`planning_prompt_v7`/`run_planner_v7`, `create_agent_v7`/`model_prompt_v7`/`run_agent_v7`/`build_canvas_v7`를 제공한다. 두 runner는 해당 요청의 output/input_tokens/output_tokens만 반환하며 worker가 합산한다. planner는 실제 `SearchPlanV7` strict `search_evidence` tool로 run_sync output_type을 override한다. queries1~3개·각1~64자·공백/제어/format문자 거부·extra forbid이며 사실/원문/웹 도구를 제공하지 않는다. 한글 저장 색인에 맞는 짧은 검색어를 제안하되 주제/기간·인명/수치 등을 만들어내지 않도록 지시한다.

planner 지침709바이트, 실제 tool raw382/normalized368바이트 중 큰 값과 framing2,048·출력500을 예약해 prompt4,361바이트를 허용한다. 실제 요청 tool bytes도 다시 검사하며 전체8,000·출력500·15초·요청1회/retry0이다. 질문을 그대로 보존하고 선택적인 이전 AI 맥락만 최대1,500자·실제 UTF-8/JSON 예산의 code-point 경계에서 줄인다. `prior_interpretation_context_truncated`가 잘림을 명시하며 질문과 기본 envelope 자체가 크면 호출 전에 실패한다.

최종은 `SYSTEM_INSTRUCTIONS_V7=SYSTEM_INSTRUCTIONS_V6`, `AIOutputV7=AIOutputV3`이며 실제 v6 provider tools/변환을 재사용한다. final prompt는24,000에서 실제 planner input+output, v6 static11,101, framing2,048, 최종 출력2,000을 차감한 동적 한도를 사용한다. final은45초·요청1회/retry0이다. 음수/bool/가짜/초과 usage를 거부하며 두 출력은 합계2,500이하다. 최종에는 계획을 근거로 전달하지 않고 질문·기존 bounded parent·고정 원문만 전달한다. 원문/인용/날짜·Unicode guards와 첫 summary·attributed/uncertain 의미를 보존하고 reviewer만 정확 issuedigest-research-v7/research-v7로 구분한다. 실제 builder가 만든 `tests/v7_fixture.py`의 JSON을 client/UI가 함께 검증한다. v6와 그 이전 provider bytes·단일 유료 slot1은 그대로 동결한다.


## Private v8 원문 날짜와 수치 관계

새 최종 agent는 `research_v8`의 `create_agent_v8`/`model_prompt_v8`/`run_agent_v8`/`build_canvas_v8`다. planner는 원래 `research_v7`을 그대로 사용한다. 최종 함수는 v7과 동일한 필수 `prior_input_tokens`/`prior_output_tokens`를 받으며 검증된 실제 planner 사용량을 전체24,000에서 차감한다. frozen v6의 세 strict tool·DTO·canonical 변환을 재사용하고 실제 Pydantic class를 파생해 details/event_date만 좁힌다. 날짜0이면 comparison만, 날짜가 있으면 source→citation→quote 순서의 처음16개 고유·유효 YYYY-MM-DD literal만 timeline enum으로 허용한다. 질문·이전 AI·제목·공급자/시각 metadata는 날짜 후보가 아니다. 월/주/연말/상대 시점을 날짜로 보정하지 않으며 최종 canonical 검사는 해당 claim의 선택 인용에 날짜가 있는지 다시 확인한다.

지침은 수치의 포함/부분/하위 항목을 독립 총량처럼 더하지 않고 정확 인용으로 포함 관계를 설명하도록 한다. 목표/중간실적/조건부 전망과 단위·시점·열린 상한을 보존한다. 이는 사실 인증이나 의미 자동 수정이 아니며 추가 모델·self-review·재시도는 없다. static과 실제 raw/OpenAI strict normalized envelope를 모두 검사하고 예산을 넘으면 질문/원문을 자르지 않고 요청 전에 실패한다. planner8,000/출력500/15초와 final출력2,000/45초·provider retry0/storeFalse는 유지한다.

정확 reviewer는 `issuedigest-research-v8`/`research-v8`이며 기존 canonical alias·API·OpenAPI·공개v1/v2·빈 reviews 경계는 그대로다. `tests/v8_fixture.py`는 실제 DTO와 builder로 비교/정확 날짜 timeline/astral/비답변 합성 JSON을 만들고 client/UI가 소비한다. 합성 성공은 실제 모델의 문장 의미 품질 인수가 아니다.

## 독립 관련성 선택 SDK

`relevance_selection`의 `create_selector(model=None)`는 frozen lazy handle만 만든다. import·handle 생성·실패한 preflight는 Agent/기본 모델/client/key를 초기화하지 않는다. `selection_prompt(question, sources)`는 strict 비공백1..1500자 질문과 현재 권한으로 호출자가 공급한1..5개 `(snapshot_id, EvidenceBundle, SourcePresentation)`를 받는다. UUID4·고유 snapshot·단일 workspace·presentation 연결과 기존 bundle의 version/hash/정확 인용 provenance를 재검증한다. 이 SDK는 권한을 부여하거나 현재 권한을 조회하지 않는다.

기존 whole-quote prompt builder와 `_PromptV5`를 재사용한다. 질문·인용을 그대로 보존하고 부모 AI 맥락은 받지 않는다. 최대5자료·자료별32/총100인용·본문12,000자 이내에서 전체 인용 단위로 구성하며, 한 후보라도 비어 있거나 예산 때문에 빠지면 요청 전체를 거부한다. 제목/metadata는 안내이며 질문/원문/제목은 비신뢰 데이터다. 직접 답변 통계가 없더라도 주제·다중 비교 중 일부에 관련된 자료를 보존하도록 지시한다. 지침·합성 출력·schema 통과는 실제 관련성 품질이나 중립성 인증이 아니다.

`run_selector(handle, prompt)`는 strict JSON·후보 coverage·UTF-8 byte 예산과 실제 요청 envelope를 검사한 다음에만 Agent를 만든다. 주입된 `FunctionModel`도 같은 경로를 사용하며 기본 client/key는 만들지 않는다. 기본 모델은 gpt-5.4-mini Responses/store=False·client max_retries0이며 요청1회·PydanticAI retry0·최대 입력+출력12,000/출력500/timeout15초다. 최악5UUID의 실제 tool raw842/normalized789바이트 중 큰 값과 지침1,019바이트, framing2,048·출력500을 예약해 prompt는7,591 UTF-8바이트다. 매 요청의 실제 raw/normalized envelope도 다시 검사한다.

기본 호출에서 SDK가 만든 클라이언트는 성공·실패·provider/model/Agent 생성 오류 후 같은 호환 event loop에서 await close한다. 주입한 모델/클라이언트와 호출자의 event loop는 닫지 않는다. 이 함수는 동기 API이며 이미 실행 중인 event loop에서는 기본 클라이언트를 할당하기 전에 고정 실행 오류로 실패한다.

유일한 strict tool `classify_relevance`는 prompt 후보 UUID 문자열 Literal enum과 `retain|exclude|uncertain`만 받는다. 모든 후보를 정확1회 분류해야 하며 unknown/duplicate/missing/extra/잘못된 결정을 수리하지 않는다. 서버는 응답 순서를 원래 후보 순서로 투영하며 uncertain을 포함해 retain+uncertain만 선택하고 exclude만 제외한다. frozen `RelevanceSelection`은 `evidence-relevance-v1`, 정확 prompt/질문 UTF-8 SHA256, 원래 후보 IDs·전체 결정·선택/제외 IDs와 검증된 input/output tokens를 보존한다. raw 응답과 aggregate의 exact-int/nonbool/nonnegative 사용량·한도·일치를 기존 helper로 검사하며, 불확실 사용량을0으로 치환하지 않는다. 입력 오류는 고정 `Invalid relevance selection input`, 실행/결정/usage/network 오류는 고정 `Relevance selection failed`로 실패한다.

선택기는 독립 SDK다. 검색·외부 도구·DBOS·worker/HTTP·UI·공개 API·자동 SupportReview와 연결하지 않는다. 현재 앱 전체24,000/출력2,500 예산이나 내구 복구를 구현한 것이 아니며 기존 v2~v8/planner7의 지침·schema·한도·결과를 변경하지 않는다. 실제3질문 인수와 전체 gate는 controller가 별도로 수행한다.
