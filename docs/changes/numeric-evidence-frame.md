# 수치 의미 역할 프레임

2026-10-20. 원문 후보 선택 이후의 내부 순수 계약이다. [역할 실험](../research/numeric-role-guidance-trial.md)의 대상/발표자 혼동·조건 과적재·직접 포함 누락을 표현할 수 있게 한다. 기존 결과를 자동 변환하거나 의미 오류를 해결했다고 주장하지 않는다.

## 계약과 전역 제약

새 numeric_frame.py와 그 테스트만 실행 코드를 추가한다. 기존 후보/선택/평가/생성기·provider bytes·worker·API·DB·UI·의존성은 변경하지 않는다. 명시 I/O, 모델 호출, 자동 보정, legacy 변환은 없다. 현재 Source에 묶인 후보 index와 역할별 exact anchor를 재구성하며 결과는 항상 unreviewed다. 현재 권한은 호출자가 별도 검사한다. 구조 유효성은 의미·완전성·진실 인증이 아니다.

공개 Python 계약: FrameFactInput, FrameRelationInput, NumericFrameInput, NumericEvidenceFrame, NumericFrameError, build_numeric_frame(source,input), validate_numeric_frame(source,frame). 내부 helper/model 이름은 구현자가 정한다.

각 fact는 candidate_id와 다음 필수 nullable anchor 필드를 가진다: measured_entity, reporting_actor, period, logical_condition, forecast_basis, comparison_baseline, reporting_tense_text. value_status는 observed/planned/forecast/unknown이며 status_text는 알려진 상태에 필수, unknown에는 nullable이다. reporting_tense는 past/present/future/unknown이며 reporting_tense_text도 같은 규칙이다. unknown은 모르는 의미이지 무료 판정/빈 문자열이 아니다. 모두 기존 SentenceAnchor를 사용한다. 역할은 같은 anchor를 공유할 수 있고 측정 대상에 발표자가 되는 문서를 배제하지 않는다. 숫자·단위·범위/수식어는 후보 index만 소유한다.

입력 facts 최대12, relations 최대16, 중복 candidate 금지. 관계는 included_in/parallel/unknown, from_id/to_id, 연속한 statement_sentence_ids(1..20), cue로 명시 선택한다. endpoint는 선택된 서로 다른 fact이며 두 measured_entity는 nonnull이어야 한다. statement는 같은 quote의 연속 문장이고 두 수치·측정 대상·cue를 포함해야 한다. unordered pair 중복/포함 cycle을 거부한다. subgroup→subtotal 직접 edge를 보존하고 aggregate edge를 추론/대체하지 않는다. 실제 의미에 맞는 endpoint인지는 별도 평가다.

출력은 profile numeric-evidence-frame-v1, status unreviewed, 현재 candidate_index, 해석된 facts/relations를 갖는다. 모든 anchor는 정확 ResolvedAnchor이고 같은 후보 quote에 있어야 한다. build는 현재 원문에서 해결하고 validate는 전체를 다시 build해 정확 비교한다. input/output/Source의 숨겨진 subclass 필드·extra·model_construct 위조도 dump 전에 canonical 검사하고 strict 재검증한다. JSON dict 직렬화 경로도 지원한다. schema 초과/잘못된 anchor/변경 source/위조 offsets·원문·profile·status는 전체 거부하고 부분 결과를 반환하지 않는다. 에러는 원문/비밀값을 노출하지 않는 고정 메시지다. Pydantic 자체 plugin 설정 조회 예외는 기존 평가기와 동일하다.

## 판단과 비용

Ruling: 첫 단계는 유료 생성기를 추가하지 않고 순수 프레임만 구현한다 — 역할 분리·원문 재검증을 먼저 고정한다 — 실제 모델 의미 개선과 앱 연결은 아직 얻지 못하며 별도 인수가 필요하다.

## Task 1: 순수 프레임 구현과 회귀

- [x] 위 계약대로 packages/agents/src/issuedigest_agents/numeric_frame.py와 packages/agents/tests/test_numeric_frame.py를 TDD로 추가한다. 기존 모듈은 읽기만 하고 기존 canonical guard/_read·후보/anchor/관계 resolver를 안전하게 재사용할 수 있다. 복제 validator보다 기존 relation resolver에 일시 adapter를 쓰는 것이 가능하나 역할을 output에서 합치거나 기존 provider를 호출하지 않는다.
- 실측값/발표자 분리, 미래 전망+과거 보고, 조건/전망 근거/전월비 분리, unknown/planned 양성, subgroup→subtotal edge 보존을 합성 회귀로 검사한다. 같은 원문에 잘못된 의미 anchor도 구조상 통과할 수 있음을 명시 테스트해 진실 인증 오해를 막는다.
- strict extra/숨겨진 excluded subclass 필드(입력·Source·출력 중첩), bool/nonliteral/caps, 반복/겹침/다른 quote/변조 위치/source, 관계 duplicate/cycle/noncontiguous/누락 대상·cue 범위 거부와 dict roundtrip을 검증한다. 기존 모듈/파일은 byte-identical이어야 한다.
- task 관련 테스트와 agents 전체, Ruff/format/mypy를 실행해 원문 출력 없이 RED→GREEN 증거와 한계를 보고한다. private 실제 자료/키/서버에는 접근하지 않는다. 구현자는 subagent를 만들지 않는다. 자기 diff를 검토하고 소유 두 파일만 commit한다. 완료 후 이 task 체크박스를 갱신한다.

## 검증 기록

구현/독립 검토/전체 검사는 진행 중이다. 모델 호출0, 앱/개발 서버/main/운영 변경 없음. Sites 요약 반영 대기.
