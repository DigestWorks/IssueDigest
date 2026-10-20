# 문맥으로 구분하는 정확 원문 참조

2026-10-20. [모델 비교](../research/frame-model-comparison.md)에서 남은 반복 표현의 모호함을 표현할 순수 계약이다. 기존 SDK/프레임/원문/실제 응답은 바꾸지 않는다.

## 계약과 전역 제약

새 contextual_anchor.py와 테스트만 실행 코드로 추가한다. 기존 numeric_frame/selection/generation/candidates/evaluation·provider bytes/worker·API/DB/UI·의존성은 동결한다. 파일/환경/네트워크·모델/키 접근은 없고 기존 Pydantic plugin 설정 조회 예외만 남는다. caller 권한과 실제 생성 의미 품질은 별도다. 기존 source cap/문장 분할/Unicode codepoint 경계와 무정규화를 유지한다.

공개 API: ContextualAnchor(SentenceAnchor 파생), ContextualAnchorResolution, ContextualAnchorError, resolve_contextual_anchor(source,anchor), validate_contextual_anchor(source,resolution). Input은 sentence_id,text와 필수 nullable context_text다. text/context_text는 비어 있지 않은 exact 원문 문자열1..1000codepoint이고 whitespace/Unicode를 정규화하지 않는다. context_text=None이면 기존 unique sentence anchor 규칙이다.

context가 있으면 먼저 같은 지정 문장 안에서 context_text가 정확히 한 번만 나와야 한다(겹치는 발생도 계산). 그 context 안에서 text 역시 정확히 한 번만 존재해야 한다(겹침 포함). 서버는 문맥의 시작+표현의 문맥 내부 시작으로 정확한 원문 위치를 계산하고, resolved.span.text는 짧은 text 그대로이며 context 전체로 확대하지 않는다. 다른 문장/quote를 넘는 context, 존재하지 않는/반복 context, context 안에서도 반복/누락인 text는 모두 거부한다. 첫 위치/가장 가까운 위치 선택·자동 context 생성·여러 문맥의 의미 추정은 없다. 서로 다른 두 context로 같은 반복 표현의 양쪽 위치를 명시 선택할 수 있어야 한다.

출력은 profile contextual-anchor-v1, status unreviewed, snapshot_id/workspace_id/source_sha256(현재 NumericCandidateIndex에서), anchor(검증한 input), resolved(기존 ResolvedAnchor)다. 현재 Source를 canonical 검사 후 기존 후보 index를 만들고 고정 문장/인용에 묶어 해결한다. index/전체 Source를 output에 중복 저장하지 않는다. 재검증은 input을 현재 Source에서 다시 resolve해 전체 결과와 정확 비교한다. 같은 표현을 가진 다른 source/snapshot/workspace도 identity/hash 차이를 거부한다. hash/위치는 실행 서명·독립 사실/의미·권한/인간 검토 인증이 아니다. 의미가 틀린 문맥을 명시해도 원문 연결만 맞으면 unreviewed로 남는다.

Input/Source/output은 _read/_canonical_models 기존 helper로 실제 모델 종류/숨겨진 excluded subclass 필드/extra를 dump 전에 검사하고 strict 재검증한다. public API는 JSON-compatible dict도 지원하되 이미 타입화된 model의 숨은 필드를 없애서 수리하지 않는다. 입력/출력 construct/copy 위조·다른 context와 stale resolved 조합·문자 위치/원문/identity/profile/status 변조를 거부한다. sanitized fixed error만 반환하며 부분 결과·모델 호출·수리·legacy 자동 변환은 없다.

## 판단과 비용

Ruling: 새로운 위치 표현은 먼저 독립 순수 resolver로 구현한다 — 기존의 거부/실제 응답을 바꾸지 않고 정확한 내부 span을 보존한다 — 생성 프레임/SDK 연결과 실제 AI 선택 품질은 다음 인수가 필요하다.

Ruling: context도 한 문장·1000codepoint 안에서 유일해야 한다 — 넓은 원문에서 임의 위치를 추정하지 않고 기존 bounded exact 규칙을 유지한다 — 긴 문맥·문장 횡단/해당 길이 안에서 구분 불가능한 표현은 계속 거부된다.

## Task 1: 순수 context resolver와 회귀

- [ ] packages/agents/src/issuedigest_agents/contextual_anchor.py와 packages/agents/tests/test_contextual_anchor.py를 TDD로 구현한다. 기존 source/candidate index/canonical helper·unique sentence resolver를 읽기만 재사용하고 의미/숫자/관계 validator를 복제하지 않는다. Context 내부의 유일한 substring 위치 계산은 새 계약에 필요한 작은 로컬 연산이다. 불완전/위조 index를 만들어 기존 resolver에 넘기는 우회는 하지 않는다.
- 합성 문장에 같은 비교 표현2개와 각각 다른 숫자/주어를 두고 두 위치를 명시 context로 선택해 정확한 짧은 span/offset을 확인한다. context없음 거부/unique문구 호환·중첩/겹친반복·context반복·경계/CRLF/emoji/decomposed Unicode·다른quote/sentence·길이/공백·겹침context와부분표현을 검사한다.
- 실제 canonical Source/input/output·중첩 모델의 excluded subclass fields/extra/unchecked model_construct/model_copy·bool/타입/누락/잘못된profile/status/hash/원문/위치·source변경·dict roundtrip과 의미가 틀려도 exact 위치만 맞으면unreviewed임을 검증한다. lazy/import/resolve/validate explicit I/O 금지를 검사하되 Pydantic plugin switch 예외를 명시한다.
- 신규 pytest→agents 전체→Ruff/format/mypy만 실행하고 RED/GREEN·self-review·명령/output·한계를 소유 report에 남긴다. repo 전체 검사는 컨트롤러의 전용QA DB에서 수행한다. import/reload 간섭은 최소 재현 후 신규 테스트의 최초 도입 모듈만 격리한다. 기존 test/production을 수정/skip하지 않는다.
- private 원문/키/서버/실제 모델 접근·subagent 생성은 하지 않는다. 소유2파일+이 task checkbox만 commit한다.

## 검증 상태

구현·독립 검토·전체 검사 진행 중. 새 모델 호출0·원래 결과/기준·앱/서버/main/운영 변경0. Sites 요약 반영 대기.
