# 문맥 참조를 사용하는 수치 프레임 생성

2026-10-20. [문맥 참조](contextual-anchor.md)를 역할/관계 프레임과 borrowed-model 생성 SDK에 연결한다. 반복 표현을 임의 첫 위치로 선택하지 않는다. 기존 생성/프레임과 실제 결과는 보존한다.

## 계약과 전역 제약

새 contextual_frame.py, contextual_frame_generation.py와 각각의 테스트만 실행 코드로 추가한다. 기존 모든 실행 코드/설정/의존성·candidate/anchor/frame/generation/evaluation/provider bytes·worker/API/DB/UI는 동결한다. 새 프레임은 순수, SDK는 명시 borrowed Model에 한 번 요청하는 별도 공개 경로다. 앱/월 예약/DBOS/운영·자동 게시·기존 응답/gold 수리·실제 의미 인증은 포함하지 않는다. source 권한은 caller 책임이다. 기존 source cap/문장 분할/Unicode codepoint·무정규화/canonical-before-dump 검사를 유지하고 fixed sanitized error만 노출한다.

순수 API: ContextualFrameFactInput(FrameFactInput 파생, 모든8개 anchor를 required nullable ContextualAnchor로 재선언), ContextualFrameRelationInput(FrameRelationInput 파생, cue는 required ContextualAnchor), ContextualFrameInput(facts≤12,relations≤16), ContextualNumericFrame, ContextualFrameError, build_contextual_frame(source,input), validate_contextual_frame(source,result). ContextualNumericFrame은 profile numeric-contextual-frame-v1/status unreviewed, 검증된 input:ContextualFrameInput과 resolved:NumericEvidenceFrame을 보존한다. nested resolved는 기존 프레임의 구조 DTO이며 기존 validate_numeric_frame과 호환된다고 주장하지 않는다. wrapper의 현재 Source+input 재구성만 전체 결과를 검증한다.

공통 구조 제약은 기존 build_numeric_frame을 읽기만 재사용한다. explicit context가 있으면 해당 context 자체를 기존 SentenceAnchor의 exact text로 전달해 넓은 문맥 위치에서 기존 후보/quote/중복/상태·시제/null/관계의 전체 문장·endpoint·directed pair·cycle 검사를 통과시킨 뒤, 새 resolver로 각 실제 역할/cue를 짧은 원문 span으로 좁힌다. context=None은 원래 text다. context는 같은 문장 안이므로 전체 문장 statement 포함 여부는 짧은 span과 동일한 경계를 갖는다. 원본 Source/index를 고치거나 불완전 index를 만들어 우회하지 않는다. 입력 dict 변환 전 canonical 검사, 모든 nonnull anchor는 resolve_contextual_anchor로 검증하며 candidate quote 일치를 보존한다. 넓은 문맥은 임시 검사용일 뿐 결과/의미 근거 span으로 남기지 않는다. 기존 resolved class를 strict 재검증해 결과를 만들며 numeric 값/상태/시제/관계 종류를 변환하지 않는다. 관계 결과 순서는 input과 동일하다. stored input·resolved·source identity/hash/원문/offset/role/context/status/profile 변조는 현재 Source에서 wrapper 전체를 재구성해 거부한다. 모든 입력 typed/dict 가능, hidden excluded subclass/extras/construct/copy 검사를 dump 전에 한다. 출력 input 보존은 재구성 근거이며 출처 서명·의미/진실/권한 인증이 아니다.

SDK API: ContextualFrameGenerationError(NumericEvidenceError 파생), ContextualFrameGeneration(profile contextual-frame-generation-v1/status unreviewed/frame:ContextualNumericFrame/prompt_sha256/instructions_sha256/usage:KnownUsage), contextual_frame_prompt(source), validate_contextual_frame_generation(source,result), create_contextual_framer(model), run_contextual_framer(framer,source). model필수·lazy/borrowed lifecycle(enter/exit/close/newclient 금지), agent identity issuedigest_contextual_frame_v1, tool fill_contextual_frame_v1/strictTrue, output는 source-specific candidate_id/sentence_id Literal과 context_text 필수nullable1..1000을 갖는다. 알려진 status/tense는 schema에도 nonnull text인4변형을 유지한다. root/nested actual dynamic model type·제외된숨은필드/dict/model_construct 우회도 canonical narrowing 전에 검사한다.

새 지침은 기존 NUMERIC_FRAME_INSTRUCTIONS를 읽어 역할/관계 의미 부분을 그대로 재사용하되 anchor 문법을 {sentence_id,text,context_text}로 대체한다. nullable context는 text가 문장내 unique일때, 반복 text는 명시 context가 문장내 unique이며 text도 그 context내 unique일때만 허용한다. context를 넓히더라도 반환 text는 필요한 짧은 역할/관계 표현이다. 자동 위치추정·문맥 생성수리/첫위치선택·인용수리·계산/숫자합산·도구검색/검수/재시도는 없다. 새 prompt는 기존 _prompt의 전체source/catalog를 보존하고 profile만 새값으로 바꾼다. UTF8 prompt+instructions+실제 raw/normalized provider schema 최대+기존 framing allowance+2500 ≤20000 preflight, 초과시 원문/지침/후보를 자르거나 요청하지 않는다. 후보0/문장0 거부.

요청은 retries0/agent+run, request_limit1/output≤2500/total≤20000, max_tokens2500/timeout30/openai_storeFalse. 성공 requests는 strict int1, raw usage known/유효 cap을 검사하고 결과를 pure wrapper로 resolve+현재 source/hash/instructions/prompt 재검증한다. 실패는 부분 프레임을 반환하지 않으며 known_usage를 기존 helper로 보존하고 unknown을0/무료로 바꾸지 않는다. create/prompt/validate는 explicit I/O/키/환경/모델생성 없이 동작한다(기존 Pydantic plugin lookup 예외). run만 명시 borrowed model을 통해 요청한다. 별도 actual 모델 평가가 없으면 합성 SDK 검증으로만 보고한다.

## 판단과 비용

Ruling: 기존 경로를 바꾸지 않는 새 프레임/SDK로 연결한다 — 과거 결과·복구/provider 계약을 보존한다 — 앱 적용과 두 경로 통합은 후속이며 중복 SDK 유지 비용이 생긴다.

Ruling: 전체 문장 구조 검사는 유일한 문맥으로 기존 builder를 재사용하고 결과만 정확한 짧은 span으로 재구성한다 — 숫자/관계 validator를 복제하지 않는다 — wrapper를 전용 validator로 검증해야 하며 내부 resolved DTO만 기존 validator에 넘길 수 없다.

## Task 1: 문맥 프레임과 생성 SDK 연결

- [x] 소유4파일 contextual_frame.py/contextual_frame_generation.py 및 test_contextual_frame.py/test_contextual_frame_generation.py만 TDD로 구현한다. 위 계약/정확 이름/한도/제약을 따른다. 기존 helper/model을 읽기만 재사용하고 source/index 위조·숫자/관계 validator 복제는 하지 않는다.
- 순수 회귀는 같은 문장에 반복된 role/cue를 서로 다른 context로 선택한 short 정확 span·전체 relation statement/direct pair·기존 status/tense validator·quote일치·누락/중복/cycle/비연속·context없음 unique호환/모호함거부·잘못된context·Unicode/겹침·모든wrapper/input/resolved/canonical숨은필드변조와dict roundtrip을 검사한다. 숫자/단위/경계와 의미unreviewed를 유지하고 old validator가 short repeated span을 수용한다고 주장하지 않는다.
- SDK 회귀는 실제 FunctionModel/동적tool schema와 root/fact/relation/anchor의 actual type guard, known status/tense4변형·IDenum·requirednullablecontext·원문/catalog 보존·exact envelope inclusive boundary/초과 no request·0후보·borrowed lifecycle·no-store/retry0/한도/실패usage/capturedusage unknown·prompt/source/instructions/usage변조·no partial/frame수리·순수 API explicit I/O금지를 검사한다. model_construct/copy/dict/hidden excluded subclass 우회도 거부한다. helper/class import/reload 간섭은 최소 재현해 신규 테스트가 도입한 모듈만 정리한다. 기존테스트/validator변경/skip 금지.
- 신규 pytest→agents 전체→Ruff/format/mypy를 실행하고 RED/GREEN/self-review/명령/output·실패진단을 소유 report에 보존한다. repo전체 QA는 controller가 담당한다. private 원문/키/서버/실제모델 접근·subagents생성 금지. 소유4파일+Task1checkbox만 commit한다.

## 검증 상태

구현7e8a4a9. 신규184개/agents1906개와 Ruff/format348파일·mypy138파일 통과. 태스크 독립 검토 C0/I0/M0, 별도 최종 검토 C0/I0/M0·source7e8a4a9의 전용QA 전체6,240개(Python5,420/JS820)·린트/타입/빌드/OpenAPI 계약을 실패/skip/warning0으로 통과했다. 초기 import/reload 충돌은 신규 테스트의 최초 도입 모듈만 정리해 해결했으며 기존 테스트/실행 코드401파일을 변경하지 않았다.

[실제 인수](../research/contextual-frame-generation-acceptance.md)의 기준/최대2회프로토콜·source/schema/prompt/지침을 호출 전에 고정했다. 신규2호출/retry0에서 반환2/거부0이지만 고정 의미 기준 수동충족0/2다. 반복 비교 위치2개는 구분했으나 측정 대상의 지역 범위 누락과 상태 근거 조사 선택이 남았다. 원래 결과/기준을 바꾸지 않고 앱 의미 개선으로 주장하지 않는다. 기존 앱 ab6654e/v9·main/운영 유예 유지. [Draft PR61](https://github.com/DigestWorks/IssueDigest/pull/61)·Sites v83 출판/이전v82 보존·소유QA1/SDD 정리를 확인했다. 최종 영수증은 [진행 기록](../planning/progress.md)을 따른다.
