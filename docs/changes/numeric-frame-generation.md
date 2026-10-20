# 수치 역할 프레임 생성 SDK

2026-10-20. [순수 프레임](numeric-evidence-frame.md)을 모델이 채우는 내부 생성 계약이다. 기존 실제2자료의 실패/부분/의미0/2와 모든 gold/원문/사용량은 보존한다. SDK 구조 인수와 실제 의미 인수를 구분한다.

## 전역 제약과 계약

새 numeric_frame_generation.py와 테스트만 실행 코드를 추가한다. 기존 후보/프레임/생성/평가/worker/provider bytes·API·DB·UI·의존성은 동결한다. 승인된 범위의 내부 SDK이며 앱 연결/서버 배포·사용자 UI는 이번 범위가 아니다. Model은 반드시 호출자가 빌려주며 기본 key/client 탐색·Model 생성/진입/종료/close를 하지 않는다. import/create/prompt/validate는 명시 파일·환경·네트워크 I/O나 모델 요청을 하지 않는다(Pydantic plugin 설정 조회는 기존 예외). 실제 source 접근 권한/캐시·월 예산/DBOS·취소/복구는 향후 호출자 인수다.

공개 API: numeric_frame_prompt(source), create_numeric_framer(model), run_numeric_framer(framer,source), validate_numeric_frame_generation(source,result), NumericFrameGeneration, NumericFrameGenerationError. 에러는 고정 메시지와 nullable known_usage를 제공하며 원문/키/내부 validation detail을 노출하지 않는다.

모델은 현재 NumericFrameInput 계약의 모든 필수 nullable 역할과 status/tense를 채운다. current candidate/sentence ID는 dynamic Literal enum이고 relation도 current IDs를 사용한다. dynamic classes는 기존 class를 파생/재사용하며 모델 숫자/offset/단위 재작성은 받지 않는다. provider strict 도구명 fill_numeric_frame_v1·identity issuedigest_numeric_frame_v1·profile numeric-frame-generation-v1. 역할마다 1..1000 codepoint의 한 문장 내 unique exact anchor다. known 상태/시제는 nonnull 근거를 요구하고 unknown에는 null을 허용한다. source별 enum과 full prompt를 사전 검사해 잘라내지 않고 전체 거부한다.

지침은 원문을 untrusted data로 취급하고 embedded instructions를 무시한다. 모든 측정 수치·하위 항목/증감/전망/열린 한도를 보존하되 날짜/ID는 측정값에서 제외한다. measured_entity는 측정 대상, reporting_actor는 발표자이며 섞지 않는다(둘이 같은 경우를 금지하지 않는다). forecast와 과거 보고 시제를 분리한다. status_text는 숫자 자체 대신 상태를 지지하는 서술을 고른다. logical_condition은 조건, forecast_basis는 전망 근거/운영 계획, comparison_baseline은 전월비 등의 기준이며 서로 대체하지 않는다. 원문에 없으면 unknown/null이다. 직접 subgroup→subtotal edge를 aggregate edge로 대체/추론하지 않으며 명시 근거 없는 관계는 생략한다. 유효 anchor/구조는 의미·완전성/진실 인증이 아니다.

요청1회·retries0·no-store·timeout30초·출력2500/총20000 상한. envelope는 실제 instructions/prompt UTF8 + max(raw/normalized actual provider schema bytes) + framing2048 + output2500이며20000 초과/후보나 문장0은 요청 전 거부한다. 요청의 입력 prompt는 기존 whole source/candidate/sentence 표현을 재사용할 수 있으나 새 profile로 구별한다. 숫자/원문을 재출력하는 새 prompt 중복 구현을 피한다. source/input/output의 숨겨진 excluded subclass fields도 dump 전에 canonical 검사한다. dynamic output은 정확 해당 dynamic type/중첩 타입을 검사한 후 canonical NumericFrameInput으로 변환해 순수 build_numeric_frame을 호출한다. 미상 usage는 무료/0으로 추정하지 않는다.

결과는 profile/status(unreviewed), frame, prompt_sha256, instructions_sha256, usage(KnownUsage)다. 현재 source로 prompt·프레임을 재생성해 원문/역할/관계를 검사하고 현재 지침 hash도 비교한다. source가 요청 중 변하면 거부한다. hash는 현재 표현/지침의 일치 영수증이며 실행 사실·서명·독립 의미 인증이 아니다. 실제 schema를 비롯한 전체 preflight를 validate에서도 확인한다. 성공·후처리 실패·limit/invalid structured output 거부에서 관측된 raw usage를 최대한 보존하며 known 없는 실패는 None이다. 추가 검수/repair/retry/검색/legacy 변환은 없다.

## 판단과 비용

Ruling: 새로운 프레임 생성은 독립 SDK에서 먼저 인수한다 — 현재 앱의 예산/내구 실행을 바꾸지 않고 의미 실패를 관찰한다 — 의미가 개선되어도 앱 연결·운영 품질은 별도로 남는다.

Ruling: SDK가 응답 기록 전에 한도로 거부하면 known_usage=None을 유지한다 — 관측하지 못한 비용을 만들거나 borrowed Model 구조를 바꾸지 않는다 — SDK만으로 실제 비용을 알 수 없는 경우가 남아 실제 인수에서는 별도 raw 영수증을 보존한다.

## Task 1: 프레임 생성과 합성 회귀

- [x] 위 계약대로 packages/agents/src/issuedigest_agents/numeric_frame_generation.py와 packages/agents/tests/test_numeric_frame_generation.py를 TDD로 구현한다. 기존 pure frame·canonical helpers·candidate prompt·usage/schema helpers를 읽기만 재사용한다. 공통 resolver·usage validator를 복제하지 않는다. 기존 tests/production/의존성은 byte-identical이다.
- borrowed Model의 no lifecycle·lazy/key-free import/create/prompt/validate, source-bound enum과 current instructions/profile/tool, schema/runtime nonnull 상태/시제, 실제 envelope 경계±1/Unicode/raw-normalized max/초과시0요청, request1/retries0/settings와 usage성공/거부/미상 보존을 검증한다.
- numeric_frame의 역할 분리/원문 재구성·직접 포함 관계를 SDK 실제 FunctionModel 경로에서 검증한다. 이전 Minor인 observed 값+서로 다른 대상/발표자 합성 양성도 새 테스트에서 보강한다. unknown/planned 양성, stale source/hash/hidden subclass/dynamic construct 위조/semantic wrong but exact의 unreviewed 경계, invalid request count/overflow/timeout/empty output 거부와 fixed error를 포함한다.
- 신규 테스트→agents 전체→Ruff/format/mypy만 실행한다. repo 전체 검사는 컨트롤러가 전용QA DB로 수행한다. 테스트 import/reload 간섭이 있으면 원인을 재현해 신규 테스트가 최초 도입한 모듈만 격리하며 기존 tests를 변경/skip하지 않는다.
- private raw/키/실제 서버·유료 모델에 접근하지 않고 subagent를 만들지 않는다. RED/GREEN·self-review·실제 명령/output을 소유 report에 남기고 소유2파일+task 체크박스만 commit한다.

## 실제 의미 인수 · 컨트롤러

기존 고정 개발 자료2건을 같은 모델 gpt-5.4-mini Responses로 각각1회, 신규 총2회 상한·SDK/client retry0으로 실행한다. 호출 전 새 역할별 기대 기준·직접 관계·부수 날짜 제외·instruction/source hash를 private에 고정하며 원래 gold를 바꾸지 않는다. 신규 기준은 새 frame을 위한 단일 annotator의 개발 표본이며 holdout/독립 검증이 아니다. 상태 표현의 유효한 다른 철자는 exact 차이와 의미 오류를 구분해 수동 판정한다. 전체 raw/거부·known usage를 private에 보존하고 성공까지 재호출·출력 수정/기준 사후 변경을 하지 않는다. 보지 않은 자료·정치 중립성·최종 앱 품질은 별도다. 추가 API 비용은 관측 토큰만 기록하며 청구액 검증 전 추정하지 않는다.

구현·전체 검증·독립 검토·실제 인수 진행 중. Sites 요약 반영 대기.
