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

선택기 자체는 독립 SDK다. 검색·외부 도구·DBOS·HTTP·UI·공개 API·자동 SupportReview를 소유하지 않는다. 앱 통합은 아래 v9 worker가 caller-injected model로 제공한다. 기본 모델의 생성/폐기 계약과 SDK bytes는 그대로이며 기존 v2~v8/planner7의 지침·schema·한도·결과를 변경하지 않는다. 실제3질문 인수와 전체 gate는 controller가 별도로 수행한다.


## Private v9 관련성 선택 통합

`research_v9`는 `create_agent_v9(model)`의 필수 caller model을 빌리고 별도 client를 생성하거나 닫지 않는다. `model_prompt_v9`/`run_agent_v9`는 planner+selector의 정확한 비음수 정수(nonbool) 합계≤20,000/출력≤1,000을 받는다. 전체24,000에서 이를 차감하고 `min(2,000, 2,500-prior_output_tokens)`의 동적 출력1,500..2,000을 prompt/static/actual envelope·요청 설정·usage 검사에 동일하게 사용한다. frozen v8 지침·exact date 도구·v6 canonical 변환을 재사용한다.

기존 공통 helper가 선택한 whole quote들을 dynamic 예산 때문에 다시 버리지 않는다. 그 prompt 전체·최악 raw/normalized schema·지침·framing2,048·출력이 남은 UTF-8 예산을 넘으면 유료 호출 전에 거부한다. 최대5자료/100인용/16날짜는 동시 적재 보장이 아니다. 정확 private reviewer `issuedigest-research-v9`/`research-v9`만 추가하며 실제 builder 기반 `v9_fixture.py`의 비교/날짜/astral/비답변을 클라이언트와 UI에서 검증한다. 실제 의미·중립성·모델·개발 배포 인수를 의미하지 않는다.


## Private v10 첫 답변의 수치 설명

`research_v10`의 필수 borrowed `Model` factory·prompt/run/build는 v9와 같은 작은 `_relevance_final` 실행 helper를 사용한다. v9 지침·도구·prompt·설정·canonical 결과는 유지하며, v10은 frozen v8 지침에 741 UTF-8 bytes만 더한다. 첫 core answer에 포함 관계와 합산 금지, 계획·중간 실적·조건부 전망의 조건, 열린 상하한, 출처별 대상·기간·단위를 명시하도록 지시한다. 핵심 근거가 없으면 기존 빈 modules 자료 부족을 사용한다. 의미 blacklist·자동 수정·추가 모델 검수는 없다.

v10 instructions는4,340바이트, 최악 static12,648바이트다. 최대100인용의 raw/normalized 도구 envelope는 날짜0에서7,070/6,964, 날짜1에서8,097/7,957, 날짜16에서8,308/8,168바이트이며 더 큰 값을 반영한다. combined prior와 동적 출력·전체 예산·45초/요청1/repair·retry0는 v9와 같다. 원래 질문과 선택된 whole quotes를 잘라 예산을 메우지 않으며 넘으면 유료 호출 전에 거부한다. 새 client를 만들거나 빌린 model을 닫지 않는다.

정확 reviewer는 `issuedigest-research-v10`/`research-v10`이다. `tests/v10_fixture.py`의 실제 builder JSON을 full client·앱·CanvasView가 소비한다. 합성 수치 관계·날짜·Unicode·비답변은 전달과 검증 경계 검사이며 실제 생성 문장 의미 품질 인증이 아니다. 실제 모델/개발 적용 인수는 controller 소유 명세에 별도로 기록한다.


## 독립 수치 근거 후보 SDK

`numeric_evidence`는 질문 필터 없이 한 `(snapshot_id, EvidenceBundle, SourcePresentation)`의
전체 인용에서 수치 근거 후보를 제안한다. 현재 권한을 가진 원문을 제공하는 책임은 호출자에게
있다. `create_numeric_extractor(model: Model)`은 필수 borrowed 모델을 검사하는 frozen lazy
handle이며 None/모델명 문자열/일반 객체를 거부한다. import/handle 생성/실패한 preflight는
Agent·client·키 조회·요청을 만들지 않는다. 호출자는 Responses 모델(예: gpt-5.4-mini)과
transport `max_retries=0`을 구성하고 모델·client 수명을 소유한다. SDK는 이를 생성하거나 닫지
않는다. 기존 조사·관련성 SDK/worker·DBOS·HTTP·공개 게시에는 연결하지 않았다.

```python
from issuedigest_agents.numeric_evidence import (
    create_numeric_extractor,
    numeric_evidence_prompt,
    run_numeric_extractor,
    validate_numeric_proposal,
)

extractor = create_numeric_extractor(model)  # 호출자가 소유한 PydanticAI Model
prompt = numeric_evidence_prompt(source)  # 요청 없이 원문·예산 검사
proposal = run_numeric_extractor(extractor, source)
checked = validate_numeric_proposal(source, proposal)  # 현재 Source로 재계산
```

canonical bundle/presentation을 재검증해 unchecked model_copy/model_construct의 잘못된
version/hash/selector·다른 snapshot/workspace·중복 citation을 거부한다. 1..20개 인용·전체
quote≤12,000 Unicode code points를 허용하며 별도 UTF-8 envelope를 적용한다. 원문을 잘라
예산을 맞추지 않는다. 제목/metadata는 prompt에 넣지 않는다. NEL/BOM을 포함한 기존
Python+ECMAScript 공백 합집합으로 비공백을 검사하며 앞뒤 공백·NFC·대소문자·수치·단위를
정규화하지 않는다.

정확 provider identity는 `issuedigest_numeric_evidence_v1`, 유일한 strict output tool은
`propose_numeric_evidence`다. 인용 ID enum을 요청마다 제한하고 facts0..12/relations0..16을
받는다. 각 field는 citation_id/exact text≤1,000자/엄격 occurrence0..31이며 겹치는 문자열도
왼쪽부터 센다. 서버가 quote 기준 Python code-point 반열린 start/end를 계산한다. fact의
context/value는 필수이고 subject/unit/period/qualifier/status_text/condition은 nullable이다.
known kind(observed/planned/conditional_forecast)는 status_text가 필요하며 unknown은 nullable이다.
모든 field는 같은 citation/context 안에 있어야 한다. qualifier 부재는 정확값/닫힌 상한을
뜻하지 않는다. 값은 원문 문자열이며 숫자 여부·산술·대상/기간/상태 의미를 인증하지 않는다.

관계는 included_in(child→parent)/parallel/unknown과 context/cue다. context는 같은 citation의
두 endpoint value와 cue를 포함해야 한다. 모든 종류에 걸쳐 unordered fact pair당 한 관계만
허용한다. 중복 value 구간/local ID·자기참조/없는 endpoint·교차 citation·포함 cycle은 제안
전체를 거부한다. cue 존재와 cycle 없는 graph는 관계 의미 인증이 아니다. 0facts는0relations를
요구하며 빈 후보/unknown/null은 누락·자료 부족일 수 있고 포괄적 추출 성공 표시가 아니다.

frozen strict extra-forbid `NumericEvidenceProposal`은 profile=`numeric-evidence-v1`,
status=`unreviewed`, 원래 순서의 facts/relations·snapshot/workspace·전체 인용과 서버 계산
source/prompt SHA256·typed `KnownUsage`를 보존한다. source hash는 snapshot/workspace와 순서 있는
citation ID/정확 quote의 UTF-8 deterministic JSON이다. 공개 validate는 현재 Source로
hash/인용/위치/구조를 재계산·대조하며 변경/위조 provenance를 거부한다. 해시는 인증 서명이
아니며 원문에 존재하는 다른 의미 해석·kind/관계의 진실·누락을 판정하지 못한다. 자동 승인·
새 진실 인증·공개 게시 결과로 소비할 수 없다.

독립 한도는 input+output20,000/output2,500·30초·요청1/retry/repair0·Responses/storeFalse다.
최악20IDs의 실제 tool envelope는 raw3,160/normalized3,061 UTF-8바이트, 지침1,650바이트,
static4,810바이트다. framing2,048·출력2,500을 예약해 prompt10,642바이트를 허용하고 실제
schema envelope도 매 요청 다시 검사한다. 최대 인용/후보 수를 동시에 채울 수 있다는
보장은 없다. 기존 앱24,000/월10만원 예약 정책과 통합한 예산이 아니며 앱 연결은 별도 설계다.

실패는 원문·공급자 오류를 노출하지 않는 `NumericEvidenceError`다. 실제 SDK result를 받은
후 후처리/usage 검증에 실패하면 valid nonnegative raw `known_usage`를 그대로 보존하며
상한을 넘은 값도 자르지 않는다. SDK/전송이 result를 반환하지 않거나 raw usage가 잘못되면
`known_usage=None`(미상)이다. 이는 무료나 예약 반환이 아니며 transport 비용 완전 회복·
DBOS journal/정산은 SDK 밖이다. 오류/빈 후보를 자동 수리·재요청하지 않는다.

합성 경계 검사는 `uv run pytest packages/agents/tests/test_numeric_evidence.py -q`로 실행한다.
기존 agents 회귀 검사는 `uv run pytest packages/agents/tests -q`, 정적 검사는
`uv run ruff check packages/agents`, `uv run ruff format --check packages/agents`,
`uv run mypy packages/agents/src`다. 합성 성공은 실제 모델 의미 품질이나 최종 브리핑 인수가 아니다.


## 반복 원문 없는 수치 근거 v2

새 `numeric_evidence_v2`는 기존 v1과 별도인 private SDK다.
`create_numeric_extractor_v2(model: Model)`, `numeric_evidence_prompt_v2(source)`,
`run_numeric_extractor_v2(extractor, source)`, `validate_numeric_proposal_v2(source, proposal)`를
제공한다. source는 위와 같은 정확한 tuple이며 canonical source 검증·정확 resolver·원래 순서의
whole quote와 `KnownUsage`/`NumericEvidenceError`를 v1에서 재사용한다. 필수 borrowed Model만
받는 lazy handle이며 키/default client를 읽거나 모델·client를 생성/폐기하지 않는다.
호출자는 transport의 `max_retries=0`과 현재 원문 접근 권한·client 수명을 책임진다.

provider identity는 `issuedigest_numeric_evidence_v2`, 유일한 strict output tool은
`propose_numeric_evidence_v2`다. fact/relation의 `citation_id`는 현재 인용 enum이며 각 span에는
정확 `text`(비공백1..1,000 code points)/엄격한 `occurrence`(0..31)만 있다. fact의 value는
필수이고 subject/unit/period/qualifier/condition은 nullable이다. status는
`{kind: observed|planned|conditional_forecast, text: span}` 또는
`{kind: unknown, text: span|null}`의 nested strict union이다. known text의 null은 실제
raw/normalized provider JSON Schema에서 허용하지 않는다. 부수적 날짜/식별자를 측정값으로
만들지 않고 명시된 실질 수치·작은 하위 항목·증감도 후보화하도록 지시한다. 상한 때문에
전체 추출을 보장하지 않는다.

서버는 겹침을 포함한 occurrence를 whole quote에서 계산한다. resolved fact는 citation_id와
같은 문자열인 `context`로 `proposal.citations`의 전체 인용을 참조한다. 인용 자체는1,000자를
넘어도 된다. 각 nullable field와 flattened kind/status_text는 정확한 원문 위치를 보존한다.
관계 statement/cue는 exact span이며 statement가 두 endpoint의 실제 value·nonnull subject와
cue 위치를 모두 포함해야 한다. 서로 다른 endpoint는 같은 인용을 참조해야 하며 주체가 불명확하거나
statement가1,000자를 넘으면 관계를 제안하지 않는다. 모든 kind/방향에 걸친 unordered pair 중복과
included_in child→parent의 cycle을 각각 거부한다. 사실/관계 상한은12/16이며0facts는0relations다.

frozen strict extra-forbid `NumericEvidenceProposalV2`는 `numeric-evidence-v2`/`unreviewed`만
허용한다. 현재 Source로 모든 위치/인용·snapshot/workspace·prompt/source SHA256·구조를
재계산하고 unchecked extra나 stale source를 거부한다. hash는 서명·권한·인간 검토·진실 또는
외부 usage 인증이 아니다. 원문에 있는 잘못된 subject 연결·상태/조건 해석·cue 지시 대상과 수치
누락은 구조 검사를 통과할 수 있다. 단위/숫자를 계산·합산·정규화하거나 qualifier 부재를
정확값으로 해석하지 않는다. 자동 승인·완전 추출·의미 인증·최종 브리핑 품질 보장으로 쓰지 않는다.

독립 한도는 total20,000/output2,500·timeout30초·요청1/retry/repair0·Responses/storeFalse다.
20UUID schema의 실측 raw4,518/normalized4,363바이트와 지침2,268바이트로 static6,786바이트다.
framing2,048·출력2,500을 예약해 prompt8,666 UTF-8바이트를 허용한다. 매 요청의 실제
raw/normalized schema envelope도 Agent 생성 전에 검사하며 인용을 자르거나 정규화하지 않는다.
canonical1..20인용/총12,000 code points와 후보 최대 수의 동시 수용 보장은 없다.
성공 usage는 nonbool 비음수 정수·요청정확1·상한을 검사한다. 결과 후 실패는 알려진 raw usage를
보존하고 결과가 없는 실패는 `known_usage=None`으로 둔다. 이는 무료/예약 반환이 아니다.
기존 앱24,000/월10만원·DBOS/예산 예약·worker/UI/API/공개와 통합하지 않은 독립 비용이다.

합성 검사는 `uv run pytest packages/agents/tests/test_numeric_evidence_v2.py -q`다. agents 전체와
Ruff/format/mypy 명령은 위와 같다. 합성 성공과 실제 두 고정 packet의 의미 평가·전체 gate·앱 통합은
별도로 기록한다. 출력 구조가 짧아졌다는 것만으로 실제 품질이나 누락 원인 해결을 증명하지 않는다.


## 서버 문자 참조 수치 근거 v3

`numeric_evidence_refs`는 원문을 다시 쓰지 않고 서버가 만든 문자 ID를 선택하는 독립 private
SDK다. 기존 v1/v2와 조사 worker·DBOS·API·공개·UI는 그대로 유지한다.

```python
from issuedigest_agents.numeric_evidence_refs import (
    create_numeric_extractor_v3,
    numeric_evidence_prompt_v3,
    run_numeric_extractor_v3,
    validate_numeric_proposal_v3,
)

extractor = create_numeric_extractor_v3(model)  # 필수 borrowed PydanticAI Model
prompt = numeric_evidence_prompt_v3(source)  # 요청 없이 전체 원문·문자표·예산 검사
proposal = run_numeric_extractor_v3(extractor, source)
checked = validate_numeric_proposal_v3(source, proposal)  # 현재 Source로 재계산
```

Source는 v1과 같은 정확한 `(UUID4 snapshot, EvidenceBundle, SourcePresentation)` tuple이다.
canonical 원문·hash·selector·snapshot/workspace·unchecked extra를 다시 검증한다. 원래 순서의
1..20개 whole quote·합계12,000 code points를 유지하며 별도의 작은 문자 수 상한은 없다.
제목/metadata는 근거에 포함하지 않는다. 호출자가 현재 접근 권한, transport `max_retries=0`,
model/client 수명을 관리한다. SDK import·handle 생성·실패한 preflight는 키를 읽거나
Agent/client를 만들지 않으며 빌린 model/client를 닫지 않는다.

prompt는 `profile="numeric-evidence-v3"`, 원래 `source`, 인용별 `references`를 포함한다.
각 references 항목의 `characters`는 `[id, exact_one_codepoint_character]` 행이다. 인용 순서와
Python code-point 순서로 모든 글자에 전역 연속 정수1..N을 부여한다. 내부 공백·control·NEL·BOM·
결합문자·astral을 생략하거나 정규화하지 않는다. ID는 현재 Source/prompt에서만 의미가 있다.
원문과 표 전체를 함께 전송하며 자르거나 일부 인용을 버려 예산을 맞추지 않는다.

provider identity는 `issuedigest_numeric_evidence_v3`, 유일한 strict output tool은
`propose_numeric_evidence_v3`다. 각 ReferenceSpan은 `start_ref/end_ref` 양 끝 포함 정수만 받으며
실제 schema가 두 값의 최소1/최대현재N을 제한한다. bool/string/float·추가 text/occurrence/offset/
citation UUID는 거부한다. 서버는 실제 catalog로 재검증해 같은 인용의 연속 비공백1..1,000자만
해결하고 citation_id/text/반열린 code-point start/end를 확정한다. 근처 문자열로 이동하거나
합성·보정하지 않는다.

fact0..12의 value는 필수이고 subject/unit/period/qualifier/condition은 nullable reference다.
status는 `{kind: observed|planned|forecast, text: reference}` 또는
`{kind: unknown, text: reference|null}`이다. known text의 null은 raw/OpenAI-normalized schema와
runtime 모두 거부한다. forecast는 조건이 없는 전망도 포함하며 명시 조건만 condition에 따로
보존한다. 소비자는 condition도 읽어야 하며 향후 v1/v2와 결합하려면 명시 mapping·재검증이
필요하다. 기존 conditional_forecast 분류/결과를 자동 변환하지 않는다. 명시 실질 수치·작은
하위 항목·증감을 후보화하고 부수적 날짜/식별자를 측정값으로 만들지 않으며 조사/어미를 단위로
선택하지 않도록 지시한다. 원문 단위가 없으면 null이다. 이 의미를 regex로 인증하지 않는다.

모든 fact field는 value와 같은 인용이어야 하며 중복 local_id/물리 value 구간을 거부한다.
kind/status_text를 서버가 flatten하고 citation_id/context를 value의 whole quote 참조로 정한다.
relation0..16은 kind(included_in/parallel/unknown), from_id/to_id, statement/cue reference다.
연속 statement는 같은 인용의 두 다른 endpoint value와 nonnull subject·cue의 실제 위치를
모두 포함해야 한다. 모든 kind/방향을 합쳐 unordered pair당 하나만 허용하며 included_in의
child→parent cycle을 거부한다. facts0이면 relations0이다. 시점이 다른 관측/전망·근접·같은 단위·
산술로 포함을 추론하지 말고 직접 관계 근거가 없으면 생략하도록 지시한다.

strict/frozen/extra-forbid `NumericEvidenceProposalV3`는 profile=`numeric-evidence-v3`,
status=`unreviewed`, 서버 prompt/source SHA256·snapshot/workspace·원래 전체 인용·resolved facts/
relations·KnownUsage를 보존한다. validate는 현재 Source/catalog의 ID부터 모든 text/offset/
provenance/context/구조를 재계산하고 stale/tamper/unchecked extra를 거부한다. hash는 서명·권한·
진실·인간 검토나 외부 usage/모델 이력 인증이 아니다. 유효 참조를 선택해도 잘못된 주체·단위·
kind/조건·cue/관계 의미와 후보 누락은 통과할 수 있다. 빈 후보도 완전 추출이나 의미 품질 통과를
뜻하지 않는다.

독립 한도는 total20,000/output2,500·30초·요청1/retry/repair0·Responses/storeFalse다.
최대N=12,000 schema는 raw2,867/normalized2,674 UTF-8바이트이며 지침2,561·static5,428바이트다.
framing2,048·출력2,500을 예약해 prompt는10,024 UTF-8바이트를 허용하고 실제 N의 schema+
whole quote+문자표 envelope도 Agent 생성 전에 다시 검사한다. 정수 최대값의 decimal 길이
경계1/9/10/99/100/999/1000/9999/10000/12000을 검증한다. 단일 반복 ASCII quote는892자
prompt10,020바이트까지 들어가고893자는10,031바이트로 사전 거부된다. 이 예시는 별도 문자 cap이
아니며 인용 수·문자 종류·escape·ID 자릿수에 따라 달라진다. 같은12,000자 Source도 전체 표
때문에 거부될 수 있으므로 source/candidate 상한의 동시 수용을 보장하지 않는다. 기존
앱24,000/월10만원·예약·DBOS journal은 변경하지 않는다.

성공 usage는 strict nonbool 비음수 정수·요청정확1·total/output 상한을 검사한다. 결과를 받은
뒤 구조/usage/source 변경 검사가 실패하면 알려진 raw usage를 상한 초과도 포함해 보존한다.
AgentRunResult가 없는 실패/timeout·잘못된 raw usage는 `known_usage=None`이며 무료/예약 반환이
아니다. 오류는 기존 sanitized `NumericEvidenceError`를 사용하고 수리·추가 모델 검수·검색·
embedding·재시도를 하지 않는다.

합성 검사는 `uv run pytest packages/agents/tests/test_numeric_evidence_refs.py -q`다.
패키지 검사는 `uv run pytest packages/agents/tests -q`, `uv run ruff check packages/agents`,
`uv run ruff format --check packages/agents`, `uv run mypy packages/agents/src`다.
합성 통과와 고정 실제2회 전 field 의미 평가·전체 gate·독립 검토·앱/최종 브리핑 인수는 별도다.
입출력 구조·taxonomy·지침이 함께 달라졌으므로 실제 평가에서도 단일 변경의 인과 효과로
해석하지 않는다.


## 순수 수치 표기 후보 색인

`numeric_candidates`는 B2C 브리핑을 위한 내부 근거 기반이며 현재 앱·worker·provider에
연결하지 않은 순수 API다. 원래 순서의 whole quote를 검사하고 유한 문법에 맞는 표기와
모든 문자 위치를 반환한다. 모델/client 생성, 키 조회, 요청, DB 접근, 파일 쓰기는 없다.

```python
from issuedigest_agents.numeric_candidates import (
    build_numeric_candidates,
    numeric_candidates_packet,
    validate_numeric_candidates,
)

index = build_numeric_candidates(source)
checked = validate_numeric_candidates(source, index)
packet = numeric_candidates_packet(source, checked)
```

Source는 기존과 같은 정확한 `(UUID4 snapshot, EvidenceBundle, SourcePresentation)` tuple이다.
기존 순수 canonical 검증으로 hash·selector·snapshot/workspace·unchecked extra를 다시 검사한다.
1..20개 whole quote와 합계12,000 Python Unicode code points를 허용하며 제목/metadata는
수치 근거가 아니다. 호출자가 현재 접근 권한을 책임진다. 인용을 자르거나 공백/NFC/숫자/단위를
정규화하지 않는다.

모델은 모두 strict/frozen/extra-forbid다. `ExactSpan(citation_id,text,start,end)`은 원래 인용의
code-point 반열린 구간이며 text는 그 위치의 정확한 slice다. `SentenceCandidate(sentence_id,
span)`는 `s1,s2,...` 전역 순서이며 각 인용을 LF 또는 `.?!。！？` 직후에서 분할한다. 양옆이
ASCII 숫자인 소수점은 경계가 아니다. 경계 문자는 앞 구간에 포함하며 CRLF·공백만인 구간·
마지막 tail·control/NEL/BOM·결합문자/astral까지 모든 code point를 원래 위치에 보존한다.
URL/약어와 실제 언어적 문장 경계는 인증하지 않는다.

`NumericAtom(number,unit)`의 number와 nullable unit은 exact span이다.
`NumericCandidate(candidate_id,sentence_ids,expression,atoms,separator,qualifiers,lexical_kind)`는
전역 `n1,n2,...`, 실제 겹치는 모든 문장 ID, 연속 원문 expression, atom1..2개, nullable
separator, qualifier0..2개를 담는다. 범위는 두 atom과 정확한 separator를 보존하며 단위를
서로 복사하지 않는다. 후보는 인용/원문 순서이며 겹치는 숫자 영역을 중복 출력하지 않는다.

지원 문법과 우선순위는 다음과 같다.

- 법령 `제`+ASCII digits+`조/항/호`는 배율/단위보다 먼저 identifier로 보존한다. expression은
  `제12조` 전체, number는 `12`, unit은 null이다. 온전한 `YYYY-MM-DD` 또는 `YYYY/MM/DD`는
  다음 우선순위의 temporal 단일 atom이며 전체 날짜가 number다. 달력 유효성을 판정하지
  않는다. 날짜를 범위의 한쪽 숫자로 잘라 합치지 않는다. 바로 앞의 `+,-,−`는 날짜 atom에
  넣지 않고 whole quote/문장 구간에 남긴다. 음수 연도나 식별자의 실제 의미는 인증하지 않는다.
- 숫자는 ASCII digits, 정상 3자리 comma 그룹, 소수, 선행 `+,-,−`, 한국어 배율
  `십/백/천/만/억/조`를 지원한다. `9만 9000`, `3억 5천만`, `-2.5`, `1,200.5`를 계산하지
  않고 spelling 그대로 보존한다. 배율이 있어야 다음 가로 공백의 부호 없는 숫자 그룹을
  이어 붙이며, 온전한 날짜 앞에서는 연결을 멈춘다. hyphen은 범위 판정을 위해 남긴다.
- 범위 separator는 `~,∼,～,–,—,-`다. 수·배율·단위와 범위 양끝 사이에는 space/tab만
  연결하며 LF를 넘지 않는다. `1~2호`, `1호~2호`, `-2~-1`의 각 끝을 그대로 남긴다.
  단위가 다르거나 한쪽에 없어도 보정하지 않는다. 여러 종류가 섞인 범위의 lexical_kind는
  ambiguous, temporal, identifier, number 순서로 결정한다.
- 명시 측정 단위 사전은 `%p, %, bp, p, 호, 명, 원, 건, 개, 배, 점, 석, 곳, km², km2,
  ㎢, km, m², m2, ㎡, m, kg, g, t`다. temporal 단위는 `개월, 년, 월, 일, 시, 분, 초`다.
  긴 표기부터 고르며 조사/어미를 unit에 넣지 않는다. 정상 숫자의 명시 단위는 일반 이름
  hint보다 우선한다. 지수나 다른 atom의 단위를 추정하지 않고 없으면 null이다.
- 인접 prefix `약/최대/최소`와 suffix `이상/이하/초과/미만`을 별도 exact qualifier span으로
  expression에 포함한다. 완전한 suffix는 단위 prefix/이름 hint보다 먼저 확인하므로
  `1초과`는 unit=null·qualifier=`초과`이며 `1초`의 temporal 단위는 유지한다. 그 밖의
  문장으로 조건이나 열린 하한을 추론하지 않는다.
- digit로 시작하고 digit로 끝나는 연속 digit/dot/comma run의 malformed comma·다중 소수점은
  쪼개지 않고 ambiguous atom으로 보존한다. 문장 구간을 넘으면 모든 겹치는 문장을 참조한다.
  terminal dot/comma는 숫자 밖의 구두점이다.
- 단위가 없는 정상 숫자는 number다. 바로 붙은 alphabetic/Hangul 이름은 identifier hint지만,
  숫자 부분만 expression/number에 담는다. 유한 grammatical ending 예외는 `으로, 로, 이다,
  이었다, 입니다, 이고, 이며, 에서, 에, 은, 는, 이, 가, 을, 를, 와, 과, 의, 도, 만, 부터,
  까지, 보다`이며 `106.6으로` 같은 표기를 identifier로 바꾸지 않는다. 조사/이름 구별은
  형태소 분석이 아니므로 이 예외와 단위 prefix가 우연히 맞는 이름은 오분류될 수 있다.

지원 밖 한글 수사·분수·지수 표기·선행점 소수·새 단위의 완전 포괄을 주장하지 않는다.
예를 들어 `다섯 명`은 빈 후보가 될 수 있고 `1e3`과 `1/2`는 별도 숫자 후보로 남는다.
임의 이름이나 단위의 의미, 대상·기간·관계·조건·사실의 진실을 판정하지 않는다. 거짓 문장의
수치도 후보가 된다. 빈 후보는 완전 추출 인증이 아니다. 사전 밖 표기의 누락/잡음을 숨기지
않으며 날짜/identifier/ambiguous도 후보 상한256개에 포함한다. 257개면 전체를 거부한다.

`NumericCandidateIndex`는 profile=`numeric-candidates-v1`, status=`unreviewed`, snapshot/workspace,
서버 canonical source JSON UTF-8 SHA256, 원래 순서의 전체 citations, sentences, candidates를
담는다. `validate_numeric_candidates`는 exact index type과 중첩 unchecked extra/strictness를
검사한 뒤 현재 canonical Source에서 전체 색인을 재생성하여 모든 field·ID·순서·구간·text·
분류·단위·수식어·누락/추가를 비교한다. 일관된 offset/text 변조나 model_copy/model_construct도
원래 결과와 다르면 거부한다. 같은 원문/인용의 유효 metadata 변경은 새 의미 인증이 아니다.
SHA256은 서명·인증·권한·인간 검토·진실을 뜻하지 않는다.

실패는 원문·비공개 ID를 노출하지 않는 `NumericCandidateError(ValueError)`다. 수리·부분 성공·
추가 모델 호출은 없다. packet은 validate 후 전체 인용을 포함한 색인의 canonical JSON이며
사용량 영수증·모델 지침·토큰 예산을 만들지 않는다. 향후 provider에 넘길 때 전체 schema/
instructions/prompt budget을 별도로 검사해야 하므로 provider-ready packet으로 부르지 않는다.
후보 선택과 의미·관계 검증, 실제 앱 연결/최종 브리핑 인수는 후속이다.

합성 검사는 `uv run --offline pytest packages/agents/tests/test_numeric_candidates.py -q`다.
agents suite/Ruff/format/mypy는 위의 패키지 검사 명령을 따른다. 실제 private packet 평가와
전체 저장소 gate·독립 검토는 별도다.


## 수치 후보 선택과 문장 의미 anchor

`numeric_selection`은 위 순수 후보 색인을 그대로 사용하는 독립 내부 SDK다. 기존 수치
v1/v2/v3·역사 provider/worker·앱과 연결하지 않는다.

```python
from issuedigest_agents.numeric_selection import (
    create_numeric_selector,
    numeric_selection_prompt,
    run_numeric_selector,
    validate_numeric_selection,
)

selector = create_numeric_selector(model)  # 필수 borrowed PydanticAI Model
prompt = numeric_selection_prompt(source)  # 전체 원문과 실제 dynamic schema 예산 검사
proposal = run_numeric_selector(selector, source)
checked = validate_numeric_selection(source, proposal)
```

Source는 정확한 `(UUID4 snapshot, EvidenceBundle, SourcePresentation)` tuple이다. 기존 순수
검증으로 원문 hash/selector·snapshot/workspace·1..20개 인용·합계12,000 code points와 unchecked
extra를 다시 검사한다. 중첩 하위 클래스의 추가 필드도 직렬화 중 숨기지 않는다. 제목/metadata는
근거가 아니며 호출자가 현재 권한·transport `max_retries=0`·model/client 수명을 책임진다.
import/create/prompt/validate는 키 조회·모델 요청·client/Agent 생성·폐기·network/DB/파일 쓰기가
없다. create는 frozen lazy handle이며 run만 빌린 Model로 요청하고 enter/exit/close하지 않는다.

prompt profile은 `numeric-selection-v1`이다. 전체 ordered source와 문장 catalog의
`id/citation_id/text`, 수치 catalog의 `id/citation_id/sentence_ids/lexical_kind/expression/atoms/
separator/qualifiers`를 전달한다. atom의 number와 각 nullable unit, 범위 양끝·separator·열린
qualifier는 원문 그대로이며 단위 복사·수치 계산/합산·정규화가 없다. 전체 색인 JSON이나 숫자
offset 표를 provider prompt로 쓰지 않는다. lexical hint는 측정값·날짜·식별자의 의미 인증이 아니다.

agent identity는 `issuedigest_numeric_selection_v1`, 유일한 strict tool은
`select_numeric_candidates_v1`이다. source별 실제 schema는 모든 현재 후보 ID와 문장 ID만
허용하는 Literal enum(하나일 때 const)을 사용한다. provider fact는 `candidate_id`, nullable
`subject/period/condition`, nested `status`만 받는다. status는
`{kind: observed|planned|forecast, text: SentenceAnchor}` 또는
`{kind: unknown, text: SentenceAnchor|null}`이며 known text는 null을 허용하지 않는다.
forecast는 조건 없는 전망도 포함하며 condition에는 명시 조건만 둔다. 숫자 value/unit/range/
qualifier 필드는 provider에 없다. 숫자 자체는 서버 소유 `NumericCandidate`를 선택한다.

`SentenceAnchor`는 `sentence_id/text`만 받는다. text는 비공백1..1,000 code points의 exact
phrase로, 선택한 한 문장에서 겹치는 발생까지 포함해 정확히 한 번 있어야 한다. 서버가 원래
인용의 `ExactSpan(citation_id,text,start,end)`을 계산한다. Unicode·CRLF·공백·control·결합문자·
astral을 변경하지 않는다. 같은 문장의 반복 문구나 문장을 넘는 anchor는 표현하지 못하며 전체
거부/누락이 생길 수 있다. 서로 다른 문장의 동일 문구는 각 실제 위치로 해결한다. fact의 모든
의미 anchor는 expression과 같은 인용이어야 하며 같은 문장일 필요는 없다. 없는 근거는
unknown/null로 두며 문자열을 보정하거나 추정하지 않는다.

fact는0..12개이며 후보 중복 선택을 거부한다. relation은0..16개의
`kind(included_in/parallel/unknown)/from_id/to_id/statement_sentence_ids/cue`다. statement는
동일 인용의 원래 순서로 연속한1..20개 전체 문장을 선택한다. 중간의 빈 문장·앞뒤 공백·구두점도
보존하며 역순/누락/중복/다른 인용을 거부한다. 서버 statement span 안에 두 다른 선택 후보의
expression, 두 nonnull subject의 실제 위치, cue가 모두 있어야 하며 cue 문장도 포함해야 한다.
included_in은 child→parent이며 cycle을 거부한다. 모든 kind/방향을 합쳐 unordered pair당
하나만 허용한다. 직접 단서·명시 주체 없는 관계는 생략하도록 지시하고 근접·같은 단위·산술로
관계를 만들지 않는다. facts0이면 relations0이다.

strict/frozen/extra-forbid `NumericSelectionProposal`은 profile=`numeric-selection-v1`,
status=`unreviewed`, 전체 `candidate_index`, 실제 prompt UTF-8 `prompt_sha256`, facts,
relations, `KnownUsage`를 담는다. ResolvedFact는 candidate_id·nullable subject/period/condition·
flattened kind/status_text이며 ResolvedAnchor는 sentence_id/span이다. ResolvedRelation은 provider
필드와 서버 statement/span 및 resolved cue를 보존한다. validate는 현재 Source에서 index·모든
수치/단위/범위·문장 anchor·관계·provenance·source/prompt hash를 전부 재생성해 비교한다.

매 요청은 실제 dynamic raw/Responses-normalized schema 중 큰 UTF-8 bytes + 전체 지침 + 전체
prompt + framing2,048 + 출력2,500 ≤ total20,000을 Agent 생성 전에 검사한다. 고정 prompt cap으로
enum 비용을 대신하지 않으며 어느 부분도 잘라 맞추지 않는다. source/candidate 최대256과 전체
요청 예산의 동시 수용을 보장하지 않는다. 문장이 많으면 enum만으로도 거부될 수 있다. 후보0이면
prompt/run은 호출 전에 실패하며 가짜 usage0 proposal을 만들지 않는다. 후보가 있는 source에서
선택 facts0은 허용하지만 완전 추출 인증은 아니다. Responses/storeFalse·timeout30초·요청1·
retry/repair/추가 도구0, 출력2,500/total20,000과 strict 정수 usage를 검사한다.

오류는 원문/ID/raw 응답 없는 `NumericEvidenceError`다. 결과를 받으면 raw usage를 먼저 확보해
구조 거부·source 변경·상한 초과를 포함한 후처리 실패에도 보존한다. SDK가 output schema를
거부해 결과를 반환하지 않아도 공개 `capture_run_messages`에 실제 ModelResponse가 남으면
그 유효 raw usage를 보존한다. 잘못된 raw usage나 결과/캡처된 response 없는 transport/timeout은
`known_usage=None`(미상)이다. 현재 SDK는 usage 한도 검사 후 response를 history에 추가하므로,
SDK 자체의 상한 거부는 캡처 영수증이 남지 않아 미상일 수 있다. 미상은 무료/예약 반환이 아니며
원문·응답을 로깅하거나 자동 재호출해 복구하지 않는다. 외부 모델 이력/비용 전체 인증은 아니다.

정확 anchor와 구조는 잘못된 주체 연결·상태/조건 해석·관계 단서의 지시 대상·포함 방향·누락을
막는 의미 인증이 아니다. 그런 반례도 테스트에서 unreviewed로 유지한다. hash는 서명·작성자·
인간 검토·진실·권한·완전 추출 인증이 아니다. 순수 후보 검사, 이 SDK의 합성 검사, controller의
고정 실제 두 packet/원래 의미 gold 평가, 전체 gate와 최종 브리핑/앱 통합 인수는 각각 별도다.
앱24,000/월10만원·예산 예약·DBOS/복구·API/공개/UI/수집기는 변경하지 않는다.

합성 검사는 `uv run --offline pytest packages/agents/tests/test_numeric_selection.py -q`다.
agents 전체 검사는 `uv run --offline pytest packages/agents/tests -q`, 정적 검사는
`uv run --offline ruff check packages/agents`,
`uv run --offline ruff format --check packages/agents`,
`uv run --offline mypy packages/agents/src`다.
