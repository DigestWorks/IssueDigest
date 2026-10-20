# 수치 의미 연결의 고정 기준 평가

2026-10-20 KST. 현재 후보 선택 SDK의 실제2건은 부분1·거부1·사전 의미 기준 완전 충족0/2다. 숫자6개 보존은 상태 근거와 전망 전제 연결의 정확성을 보장하지 않았다. 생성 계약을 다시 늘리기 전에, 사람이 지정한 기준과 반환 제안의 차이를 반복 측정한다. OpenSpec root=null이므로 기존 명세/SDD 방식으로 구현한다.

## 범위와 판단

순수 오프라인 평가기 하나를 추가한다. 대상은 선택된 fact와 대상·시점·조건·상태 분류/근거뿐이다. 관계 의미·완전한 문서 coverage·중립성·사실의 진위·최종 브리핑 품질은 평가하지 않는다. 기존 SDK/원문/평가 기준을 고쳐 통과시키지 않으며 새 모델 호출은0이다. 실제2건은 기존 결과를 재생하며 추가 평가 형식으로 변환한 기준은 사후 변환임을 명시한다.

판단1: 기준 anchor는 원문의 정확한 위치·텍스트 대안 중 완전 일치로 비교한다. 문구 포함만으로 역할 의미를 통과시키지 않는다. 더 넓지만 적절한 표현이나 사전에 열거하지 않은 동등 표현이 불일치할 수 있어, 불일치는 독립적인 의미 오류 확정이 아니라 기준과의 차이다. 원래 gold의 조건/수단 해석도 평가자의 해석이며 사실 인증이 아니다.

## Global Constraints

- 새 `packages/agents/src/issuedigest_agents/numeric_selection_evaluation.py`와 새 테스트 파일, agents README의 사실적 설명만 실행 범위다. 기존 모든 Python/TS/테스트/provider 지침·모델·lock·AGENTS·API/DB/UI/worker/collector 파일은 수정하지 않는다. 기존 numeric_selection.py의 실제 호출과 모든 역사 결과는 동결한다. private 원문/질문/ID/키/gold는 커밋하거나 출력하지 않는다.
- `evaluate_numeric_selection(source, reference, proposal, *, rejected_usage=None)`는 I/O/모델/client/DB/파일/환경 읽기 없는 순수 함수다. reference/proposal은 해당 strict 모델 또는 JSON 대응 dict를 받는다. source는 기존 Source다. 모듈 import도 네트워크/키 조회를 하지 않는다. 공개 오류는 `NumericSelectionEvaluationError(ValueError)`의 일반 메시지로 정리하고 내부 원문/검증 오류/ID를 노출하지 않는다. 기존 모델을 쓰되 unchecked construct/copy·subclass extra·bool 정수·stale source/index·원문/위치 변조를 누락 없이 재검증한다.
- `AnchorRule`은 mode `one_of|absent|unassessed`, alternatives는 정확 ExactSpan tuple0..4다. one_of는1..4개, 나머지는0개다. 중복 대안 금지. `ReferenceFact`는 candidate_id와 subject/period/condition/status_text AnchorRule, kind는 observed/planned/forecast/unknown 또는 null(미판정)이며 모든 필드는 필수다. 기준 anchor는 현재 후보 expression과 같은 quote의 정확 위치/텍스트여야 한다. 반복 텍스트를 서로 다른 위치로 지정할 수 있으며 모델용 unique 문구 제약으로 기준을 축소하지 않는다. 공백/Unicode/코드포인트를 정규화하지 않는다.
- `NumericSelectionReference`는 profile `numeric-selection-reference-v1`, candidate_index 전체, candidate_set `complete|partial`, facts tuple0..12다. 후보ID 중복/없음·유효하지 않은 anchor 대안은 평가 전에 거부한다. current Source 전체와 index를 `validate_numeric_candidates`로 재검증한다. reference는 평가자가 작성한 기준이며 truth/review/학습 라벨의 자동 생성이 아니다.
- proposal이 있으면 기존 `validate_numeric_selection`으로 현재 Source 전체에 대해 재검증한 뒤 비교한다. rejected_usage를 같이 주면 입력 모순으로 거부한다. proposal=None은 결과 전체 거부를 나타내며 raw facts를 수용하거나 성공으로 세지 않는다. rejected_usage는 strict KnownUsage 또는 dict 또는 None으로 받아 알려진 실패 사용량을 보존한다. 상한 초과 usage도 알려진 실제 비용이면 줄이거나0으로 바꾸지 않는다. proposal 없음만으로 무료/호출0을 추정하지 않는다.
- report는 profile `numeric-selection-evaluation-v1`, scope `fact_fields_only`, outcome `reference_match|reference_mismatch|inconclusive|rejected`, reference_sha256, proposal_sha256 또는 null, expected_facts 정수, received_facts 정수 또는 null, checks, usage KnownUsage 또는 null이다. hash는 strict 재검증된 모델의 canonical `_json(_plain(model))` UTF8 SHA256이며 동일 입력에 결정적이다. report는 원문/anchor/질문을 복사하지 않고 candidate_id/field/result만 기록한다. ID도 민감할 수 있으므로 호출자가 보고서 보관 경계를 지킨다.
- checks는 ReferenceFact 순서로 presence와 실제 존재하는 fact의 subject/period/condition/kind/status_text를 각각 비교한다. result는 match/mismatch/unassessed다. presence 없는 fact는 presence mismatch만 기록한다. mode absent는 실제 null만 match, one_of는 실제 span이 대안과 정확히 같을 때만 match, unassessed는 실제 값과 무관하게 unassessed다. kind null도 unassessed다. 마지막으로 예상 밖 fact를 proposal 순서로 presence mismatch(complete) 또는 unassessed(partial)로 기록한다. 누락·잘못된 역할·부수 날짜 선택을 분리해 볼 수 있어야 한다.
- outcome은 proposal None이면 rejected/checks빈/received_facts null/proposal_sha null이다. 그 외 mismatch 하나라도 있으면 reference_mismatch다. mismatch가 없어도 candidate_set partial 또는 unassessed 하나라도 있으면 inconclusive다. complete이고 모든 기준이 판정됐으며 모든 check가 match일 때만 reference_match다. 빈 complete 기준+빈 제안은 제한 범위의 reference_match다. report의 reference_match를 semantic correctness/독립 사실 검증/최종 제품 통과로 표현하지 않는다. 관계는 보고서 scope 밖이며 비교하지 않는다.
- 구현자는 합성 자료로만 TDD를 수행하고 신규 회귀 RED→GREEN, agents suite/Ruff/format/mypy, 기존 tracked apps/packages/AGENTS/locks SHA manifest를 보고한다. private 실제 packet/gold/키·네트워크/컨테이너/push/PR/Sites/full gate/child agent는 쓰지 않는다. source2개와 agents README만 commit하고 controller Markdown을 stage하지 않는다.
- controller가 기존2개 source/gold/hash/실패 응답을 유지해 오프라인 재생한다. 사람이 사후 변환한 reference와 원래 gold를 구분하고 예상 결과를 보고 수정하지 않는다. 실제 모델 추가 호출0/앱0, 이전 provider2의 usage4053/1166·부분1/거부1/완전0/2를 유지한다. 반환 원문 위치/유효 구조가 의미 인증은 아니다. 최종 전체 gate/작업·전체 리뷰/Draft PR54 기반 PR/CI와 기록을 완료한다. 새 소유QA만 정리하며 main·운영/개발ab6654e/v9·사용자 탭은 유지한다. Sites 미갱신 시 진행 기록에 반영 대기를 명시한다.

## Task 1: 순수 고정 기준 평가기

Read adjacent global-constraints.md first; its verbatim constraints bind the implementation.

- [ ] 위 모델·현재 Source/기준/proposal 재검증·필드별 결정적 비교·오류 정리·알려진 실패 usage 보존의 단일 평가 API를 새 모듈에 구현한다. 기존 helper/검증기를 재사용하며 생성 경로와 지침을 고치지 않는다.
- [ ] 새 테스트에서 대상/기간/조건/상태와 종류의 각각 오류·누락/부수 날짜·complete/partial/미판정·모든 outcome·빈 기준·정확 대안/큰 문구 차이/다른 반복 위치·서로 다른 quote/CRLF/Unicode·중복/없는ID/위조/unchecked/subclass extra/stale source·거부 raw 미수용/known unknown 초과 usage·결정적 hash/순서·import/run 무I/O를 회귀로 잠근다. 정상 assertion RED→GREEN을 보존한다.
- [ ] README에 사실적 API와 평가 범위·exact 대안의 불일치 비용·미판정/거부/known usage·독립 의미 인증과의 차이를 적는다. agents suite/Ruff/format/mypy 및 기존 파일 SHA manifest를 task-1-report.md에 남기고 해당 task 체크를 완료한다.

## Controller 인수

기존2건의 원문·원래 gold·raw/수용 결과/known usage를 변경하지 않는다. 사후 변환 reference는 별도 파일로 기록하고 원래 의미 인수 결과를 재판정하지 않는다. 반환 건의 상태/전망 전제 누락과 거부 건의 수용0을 재현하는지 확인한다. 신규 모델0·앱0을 실패분 비용0으로 표현하지 않는다. 코드 검사와 실제 소비자 품질은 구분한다.
