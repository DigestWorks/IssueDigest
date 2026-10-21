# 측정 대상 범위·상태 근거 선택 지침

2026-10-21 KST. [이전 실제 인수](../research/contextual-frame-generation-acceptance.md)의 원문 일치/의미0/2를 개선하기 위한 별도 지침 버전이다. 두 실패의 값·지역명·문구를 하드코딩하지 않는다.

## 계약과 전역 제약

실행 변경은 contextual_frame_generation.py의 요청 공통 실행 추출, 새 scoped_contextual_generation.py, 새 test_scoped_contextual_generation.py 및 새 합성 v1 호환 fixture만 허용한다. 기존 v1 공개 API·모델종류·profile·지침/prompt/raw+normalized tool schema·identity/settings/limits/retry/lifecycle/실패usage·결과·검증 의미는 그대로다. 다른 모든 기존 실행/테스트/설정/의존성·pure frame/anchor/candidate·worker/API/DB/UI는 동결한다. 앱/운영 변경·추가 검수/수리/재시도/새client/권한 확대는 없다. Source 권한과 의미/진실/중립성·전체 제품 인수는 별도다. 모든 결과는 unreviewed다.

기존 run_contextual_framer는 정확 framer/model 검사와 기존 _preflight를 유지한 뒤 private 공통 요청 helper를 호출하도록 refactor한다. 공통 helper는 동일 모듈 안에 두고 기존 Agent/capture/_known_usage/_captured_usage/_read/_canonical_models 및 실제 동적 모델 검사를 읽기만 재사용한다. Model/source/prompt/tools/instructions/identity/result model/validator/error class와 고정 실패 문구 등 trusted 내부 인자를 받아, 요청·strict root/nested 실제타입·원문 frame 재구성·receipt·실패 known/unknown usage 로직을 한 번만 소유한다. v1에는 현재 모듈의 원래 class/validator/constants를 호출 시 전달해 기존 monkeypatch·검사 지점을 우회하지 않는다. 외부 사용자에게 자유 policy/callback/검증 생략 설정을 노출하지 않는다. 타입 안전한 TypeVar/generic 등으로 result subclass를 유지하고 새 경로를 v1 validator로 검증하지 않는다. v1 입력 오류/요청 실패의 기존 error class/고정 문자열과 사용량 기록을 보존한다. 공통 helper가 따로 client 생성/enter/exit/close하지 않는다.

새 API는 ScopedContextualFrameGeneration(ContextualFrameGeneration 파생, profile Literal scoped-contextual-frame-generation-v1), ScopedContextualGenerationError(ContextualFrameGenerationError 파생), scoped_contextual_frame_prompt(source), validate_scoped_contextual_frame_generation(source,result), create_scoped_contextual_framer(model), run_scoped_contextual_framer(framer,source). 새 framer는 독립 frozen dataclass+필수 borrowed Model이며 exact framer type과 모델을 검사한다. 새 agent identity issuedigest_scoped_contextual_frame_v1, tool fill_scoped_contextual_frame_v1/strictTrue다. 성공/입력/실패는 각 새 profile/validator/error type으로 구분하며 공개 dict 입력과 canonical-before-dump/hidden excluded subtype/construct/copy 가드는 유지한다.

새 _preflight(source)는 기존 v1 _preflight를 읽기 재사용해 source/catalog/candidate/동적모델/schema를 얻고, tool의 실제 output class는 유지한 채 ToolOutput metadata name만 새 이름으로 구성한다. prompt JSON은 전체 source/catalog를 보존하고 profile만 scoped-contextual-frame-generation-v1로 바꾼다. 새 지침은 CONTEXTUAL_FRAME_INSTRUCTIONS의 tool 이름만 바꾸고 아래 SCOPE_STATUS_GUIDANCE를 한 번 추가한 SCOPED_CONTEXTUAL_INSTRUCTIONS다. 기존 본문/의미 제약은 보존한다. 새 prompt+새 지침+실제 raw/normalized schema 최대+기존 framing allowance+2500 ≤20000을 다시 계산해 초과시 truncate/호출 없이 거부한다. v1 preflight가 먼저 거부한 source를 새 경로로 우회 수용하지 않는다. 선택형 hook을 v1 공개 API에 추가하지 않는다.

SCOPE_STATUS_GUIDANCE는 다음 exact ASCII 문자열이다(줄은 하나의 공백으로 이어짐):

Measured_entity must identify the measured object and its explicit geographic, population, institutional or subgroup scope. Preserve necessary scope in a sufficient contiguous source phrase; an event or action predicate alone drops scope. A broader context_text locates text but does not restore scope omitted from measured_entity.text. For known value_status, status_text.text itself must contain explicit predicate or status evidence attached to that quantity. Topic or case particles, connectives, punctuation or numbers alone do not supply that evidence, even if context_text or reporting_tense_text contains it. Prefer sufficient evidence over maximum brevity. If support is absent, use unknown/null; never infer missing scope or status.

이는 모델에 선택을 요구하는 지침이며 서버의 의미 인증/어휘 금지 목록·최소길이 정규식으로 만들지 않는다. source-exact한 잘못된 선택은 구조검사만 통과할 수 있으므로 합성 검사와 실제 의미 평가를 구분한다. 새 모델 출력문법/8개역할/관계는 기존 ContextualFrameInput 그대로이며 숫자/단위/경계/관계 validator를 복제하지 않는다. 성공 결과는 기존 contextual wrapper를 source에서 재구성하고 새 prompt/instructions SHA를 검증한다. v1/새 profile 상호오용과 source/prompt/instructions/usage/status/profile 변조는 거부한다.

공통 실행은 기존과 동일한 agent/run retries0, request_limit1, max_tokens/output2500,total20000,timeout30,openai_storeFalse다. strict int requests1·실제 raw/aggregate usage·실패 known/unknown/captured usage·no partial frame·borrowed lifecycle을 보존한다. create/prompt/validate는 explicit I/O/키/환경/모델 생성이 없고 기존 Pydantic plugin lookup 예외만 둔다. 실제 모델의 client retry는 caller 책임이며 controller 실제 평가에서는 client max_retries0/capture 호출 상한을 강제한다.

## 판단과 비용

Ruling: 요청 실행을 공유하고 선택 지침만 새 버전으로 분리한다 — 세 번째 SDK 복제와 기존 결과의 의미 변경을 피한다 — 기존 v1 실행 모듈을 좁게 refactor하는 회귀 위험이 있어 수정 전 wire/result fixture와 전체 검증이 필요하다.

Ruling: 단어/문자 길이 차단 대신 의미 선택 지침을 평가한다 — 조사 한 글자와 대상 범위 누락을 일반적인 근거 선택 문제로 다룬다 — 지침만으로 의미 오류를 차단할 수 없어 실제/미관측 평가와 앱 인수가 남는다.

Ruling: 실제 호출 전 새 합성C를 미지원 차량단위 대에서 지원 방문진료 건수로 수정한다 — 선택 지침과 기존 유한 단위 파서의 제한을 분리하고 초기 source/reference를 보존한다 — 차량 단위 인식은 미구현/미검증으로 남고 지원 단위의 개발 평가로 제한된다. A/B/gold/D unchanged, calls0, revision1 frozen.

## Task 1: 실행 공유·새 범위 지침 경로

- [x] 위 허용4파일을 TDD로 구현한다. 합성 사전 동결 fixture는 controller가 제공한 /home/xinics/.local/state/issuedigest/scoped-contextual-generation-20261021/v1-compatibility.json을 bytes 그대로 packages/agents/tests/fixtures/contextual-frame-v1-wire.json에 복사한다. private 실제 자료/키는 아니다. 원래 v1 module/test/기준과 다른 기존파일을 변경하지 않는다(허용한 요청 helper 추출만 예외).
- 기존 fixture의 고정 source를 복원해 v1 instruction/identity/prompt/raw+normalized tool JSON/schema/result/settings/limits/agent+run retry가 동일함을 FunctionModel로 검증한다. fixture의 empty facts는 wire/result 호환용이며 새 경로의 의미 검증을 대체하지 않는다. 원래 v1 테스트는 그대로 전체 실행한다.
- 새 경로의 실제 FunctionModel 양성은 다양한 지역/기관/집단·수량·관측/전망/unknown·반복 문맥/관계가 있는 합성 source로 검사한다. 지침의 generic scope/status 요구와 exact 본문 재사용을 확인하되 특정 이전 실제값/문구를 복사하지 않는다. 구조적으로 exact인 의미 오선택이 unreviewed로 남는 한계도 검사한다.
- 새 profile/tool/identity와 v1교차거부·source/prompt/instructions/usage변조·strict actual dynamic root/nested type/hidden excluded fields/dict/construct/copy·원문 정확짧은span/전체catalog·실제 schema envelope inclusive boundary/초과 no request·0후보·borrowed lifecycle/no-store/한도/retry0·실패raw/captured/unknownusage/부분결과금지·순수API explicitI/O를 검사한다. 기존 타입 가드를 공통 helper로 옮기면서 누락/완화하지 않는다.
- 신규 pytest→agents 전체→Ruff/format/mypy를 실행하고 RED/GREEN·self-review·명령/output·실패진단을 소유 report에 남긴다. 원인불명 실패는 수정 전에 최소재현한다. import/reload 격리는 새 테스트가 처음 도입한 모듈만 대상으로 한다. 기존테스트변경/skip 금지. repo 전체QA는 controller 담당. private 실제source/키/서버/네트워크/실제모델/subagent 접근금지. 소유4파일+Task1checkbox만 commit한다.

## 검증 상태

구현 sourceb3e1e46. 신규97개+원래v1 88개=focused185·agents2003·Ruff/format352파일·mypy139파일 통과. 수정 전 v1 wire/result 합성 fixture bytes와 지침/prompt/raw+normalized schema/설정/한도/결과 호환을 확인했다. 태스크 독립 검토 C0/I0/M0, 최종 독립 검토 C0/I0/M0·전용QA9589526의 전체6,337개(Python5517/JS820)·린트/타입/빌드/OpenAPI 계약을 실패/skip/warning0으로 통과했다. 다른 기존404파일은 동일하다. sourcebb8bce6/전체6240 baseline·OpenSpec rootnull로 SDD만 적용했다. [실제 인수](../research/scoped-contextual-generation-acceptance.md)는 사전 기준과 총4회 상한(기존 실제인용2+다른분야 새 합성2)을 고정하고 독립검토·전체QA 후 실행했다. 반환4/거부0·기존1/2/새합성1/2 충족이며 조사 상태 근거와 범위/발표자 혼동 실패를 보존한다. 원래v1실제결과2개도 오프라인 재검증했다. 새 합성 자료도 개발자가 만든 검증으로 독립 holdout/실제 뉴스 표본이라 부르지 않는다. 앱/서버/main/운영 유예. [Draft PR62](https://github.com/DigestWorks/IssueDigest/pull/62)·Sites v84 출판/이전v83 보존·소유QA1/SDD 정리를 확인했다. 최종 영수증은 [진행 기록](../planning/progress.md)을 따른다.
