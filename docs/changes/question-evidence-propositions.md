# 질문별 근거 명제 · 조건·시간·비수치 정보

2026-10-23 한국 시간. **설계안이며 제품 코드·모델 SDK 구현은 아니다.** [실제 생성 인수](../research/columnar-generation-acceptance.md)의 각각/이내 부분 보존, 시간3·비수치4 미표현을 다룬다. 질문 중심 B2C 브리핑·현재 권한/불변 인용/합산 예산은 유지한다. 문서와 비공개 무호출 시제품만 변경하므로 spec-driven-workflow의 문서 예외를 적용한다. 기존 수치 생성기·원문·기준·응답·모든 점수·비용을 수정하거나 재실행하지 않는다.

## 문제와 선택

수치 역할 생성기는 수치 후보를 중심으로 출력한다. 기한·자격·승인·법적 지위·후속 절차는 수치를 담는 필드에 억지로 넣을 정보가 아니다. 넓은 인용에 ‘각각’이나 ‘수용’이 있어도 선택된 역할에 연결되지 않으면 의미 보존을 인증할 수 없다. 단어가 존재하는 것과 어떤 대상·행위에 적용되는지는 다르다.

새 경로는 **질문별 근거 명제**를 반환한다. 기본 단위는 출처가 표현한 하나의 주장·조건·절차이며, 수치는 그 명제의 한 요소다. 전체 원문을 재사용하되 기존 numeric frame을 필수 입력이나 정답으로 삼지 않는다. 같은 자료에서 별도 생성기를 무조건 모두 호출하는 설계도 하지 않는다. 최종 브리핑에는 확정 사실로 승격하지 않고 출처 귀속·근거 부족을 유지한다.

| 선택지 | 판단 | 비용·한계 |
| --- | --- | --- |
| 기존 수치 역할 필드에 모든 정보를 추가 | 채택하지 않음 | 수치 없는 명제와 상대 시점을 처리하기 어렵고 동결 SDK/기록을 바꾸게 됨 |
| 긴 인용·요약 문장만 추가 | 근거 표시에는 사용, 구조 계약 대안은 아님 | 각 조건의 대상/의존 관계와 빠진 질문을 기계적으로 구분하기 어려움 |
| 별도 질문별 명제 계약 | 다음 구현안 | 계약·저장 검증·생성 연결이 필요하며 의미 품질은 별도 실제 평가 필요 |

## 입력과 경계

먼저 한 개의 검증된 Source와 정확한 질문1개를 받는 순수 계약을 구현한다. Source 원래 타입·현재 snapshot/bundle/quote·원문 hash와 위치를 재구성하며 기존 source 검증을 재사용한다. Source 하나 안의 여러 인용은 지원하지만 서로 다른 snapshot의 원문을 합치지 않는다. 다음 생성 SDK의 입력 표현은 원문/문단/문장 전체 보존을 전제로 따로 측정한다. 현재 columnar packet의 수치 catalog가 비수치 명제의 필요조건은 아니다. 수치 후보0개도 유효해야 한다.

질문은 모델 출력으로 바꾸지 않고 정확 UTF-8 hash로 고정한다. 과거12개 개발 명제·정답/사람 판정은 provider 입력에 넣지 않는다. 모든 원문은 신뢰하지 않는 자료이며 원문 안 지시를 실행하지 않는다. 공개 조회 권한과 비공개 자료 경계를 넓히지 않는다. 순수 validator는 출처 일치만 확인하며 현재 접근 권한은 호출자가 별도로 확인한다.

## 제안 데이터 계약

아래 필드는 **제안**이다. 실제 Pydantic 클래스나 공개 API가 이미 존재한다는 뜻이 아니다. 모든 구조는 extra 금지·명시 필수 필드·원래 scalar/container 타입 검사 후 읽는다. 순서는 원래 제출 순서이며 ID는 결과 내부에서만 참조한다.

- 영수증: profile=`question-evidence-propositions-v1`, status=`unreviewed`, 정확 question/source hash, propositions, coverage. 모델 사용량/요청 식별·지침 hash는 순수 계약이 만들지 않으며 후속 SDK의 별도 영수증에 둔다.
- 원문 참조: Source의 citation ID(시제품에서는 q1 alias), 해당 citation.selector.quote 안 Unicode code point 기준 start/end, exact text. `0 <= start < end <= len(text)`와 slice 완전 일치를 재검증한다. byte/문서전체 offset·공백 정규화·유사 문자열 대체를 허용하지 않는다. 긴 인용과 짧은 요소 참조를 각각 보존한다. 모든 요소 ref는 같은 명제 supporting_refs 중 하나에 완전히 포함돼야 한다. 이는 provenance 보호이며 의미적 함의를 인증하지 않는다.
- 명제: local ID, source_statement 또는 uncertain, 정확 supporting_refs1개 이상, subject_refs, predicate_refs, facets, depends_on_ids. subject/predicate를 원문에서 특정하지 못하면 빈 목록을 명시하고 uncertain으로 둔다. AI 요약 자유 문장을 사실 필드로 저장하지 않는다.
- facet은 ID/kind/value/refs/target_ids를 가진다. kind별 value만 받으며 target_ids는 같은 명제의 다른 facet을 가리킨다. 대상이 없는 수식어를 모든 수치에 자동 적용하지 않는다. evidence refs는1개 이상이며 값의 의미가 옳다는 인증은 아니다.
- coverage는 원래 질문1개에 대해 linked_proposition_ids와 unresolved_reason(null 또는 no_linked_evidence/ambiguous/insufficient)을 둔다. 연결이0개면 이유가 필수다. 연결이 있어도 부족/모호를 표시할 수 있다. `complete`/`verified` 같은 완전성·진실 상태는 만들지 않는다. 질문을 사전 자동 분해하거나 모델이 required 목록을 정해서 성공 분모를 바꾸지 않는다.

| facet kind | value·연결 의미 | 보존할 경계 |
| --- | --- | --- |
| quantity | exact quantity expression ref와 metric_refs | 좌석/수용 인원처럼 지표를 구분, 수치 없는 명제도 허용 |
| bound | eq/gte/gt/lte/lt/unknown·quantity target | ‘이내’의 상한과 ‘미만’ 열린 경계의 cue ref. 무한대/환산/합계 계산 금지 |
| distribution | per_member/collective/unknown·quantity target·member_refs | ‘각/각각/씩’ cue와 대상 집합을 함께 보존. 분배 수를 총합으로 바꾸지 않음 |
| time | deadline/target/period/relative/unknown·literal ref·anchor_refs | 상대 시점을 실제 날짜로 추정하지 않음. 연도/월/일 보충 금지 |
| eligibility | literal ref | 기관 종류·법정 정의를 수치 대상과 혼합하지 않음 |
| prerequisite | literal ref·해당 명제 depends_on_ids | 승인 선행 조건과 후속 절차를 구분 |
| legal_effect | affirmed/negated/unknown·literal ref | ‘지위 부여 아님’의 부정을 제거하지 않음. 법률 해석 인증 아님 |
| procedure | planned/observed/conditional/unknown·literal ref | 계획/신청 허용/선정/준공/후속 검토를 구별 |

### 필드별 정확한 형태

후속 순수 구현의 필드 이름/타입은 다음으로 고정한다. `Ref`는 `{citation_id: str, start: int, end: int, text: str}`이며 exact 타입/비어 있지 않은 UTF-8 문자열·범위 규칙을 따른다. `Refs`는 순서 있는 Ref목록이고 최대8개다. `[]`와 null은 다르며 아래에서 허용한 빈 목록만 받는다. 명시 null은 coverage.unresolved_reason에만 허용한다. 각 object는 추가 키를 거부한다.

영수증의 정확한 키는 `profile, status, question_sha256, source_sha256, propositions, coverage`다. SHA는 소문자64-hex이고 question_sha256은 변형하지 않은 질문 UTF-8의 SHA256이다. source_sha256은 원래 타입을 검증한 Source를 `{snapshot_id, bundle, presentation}` JSON 값으로 직렬화한 뒤 `ensure_ascii=False, sort_keys=True, separators=(",", ":")`의 UTF-8 SHA256이다. bundle/presentation은 JSON-mode dump를 사용하고 UUID는 표준 소문자 하이픈 문자열이다. 원문 whitespace/값은 정규화하지 않는다.

명제의 정확한 키는 `id, epistemic_status, supporting_refs, subject_refs, predicate_refs, facets, depends_on_ids`다. id는 p1..p24, epistemic_status는 source_statement/uncertain이며 supporting_refs는1..8, subject_refs/predicate_refs는0..8, facets는0..16, depends_on_ids는0..8이다. facet ID는 명제 내부 f1..f16이며 같은 명제의 target_ids만 참조한다. 명제 ID·명제 내 facet ID·각 참조목록의 동일(citation_id,start,end,text)·각 ID목록의 중복을 거부한다. 다른 facet이 같은 Ref를 공유하는 것은 허용한다. subject/predicate 또는 quantity.metric_refs가 비었거나 time.relative의 anchor_refs가 비면 해당 명제 epistemic_status는 uncertain이어야 한다.

facet의 정확한 키는 `id, kind, value, refs, target_ids`다. refs는1..8, bound/distribution의 target_ids는 정확1개 quantity facet ID이며 그 밖의 kind는 target_ids=[]다. value의 중첩 Ref도 refs에 완전 일치 항목으로 포함돼야 하고 모든 refs/subject_refs/predicate_refs는 supporting_refs 중 하나에 같은 citation ID와 범위로 완전히 포함돼야 한다. 아래 키는 모두 필수이며 kind별 value에 다른 키를 허용하지 않는다.

| kind | value의 정확한 키/타입 |
| --- | --- |
| quantity | `{expression: Ref, metric_refs: Refs(0..8)}` |
| bound | `{operator: "eq" / "gte" / "gt" / "lte" / "lt" / "unknown"}` |
| distribution | `{mode: "per_member" / "collective" / "unknown", member_refs: Refs(0..8)}`; per_member/collective이면 member_refs1개 이상 |
| time | `{kind: "deadline" / "target" / "period" / "relative" / "unknown", literal_ref: Ref, anchor_refs: Refs(0..8)}` |
| eligibility | `{literal_ref: Ref}` |
| prerequisite | `{literal_ref: Ref}` |
| legal_effect | `{polarity: "affirmed" / "negated" / "unknown", literal_ref: Ref}` |
| procedure | `{state: "planned" / "observed" / "conditional" / "unknown", literal_ref: Ref}` |

coverage는 정확 `{linked_proposition_ids: list[p-ID](0..24), unresolved_reason: null / "no_linked_evidence" / "ambiguous" / "insufficient"}`다. ID는 존재·중복 검사를 하고 원래 순서를 유지한다. 연결0개면 null을 거부하고, 연결이 있는데 no_linked_evidence도 거부한다. null은 연결이 있다는 구조 상태일 뿐 질문 전체 완료를 뜻하지 않는다. 아무 명제도 못 찾은 빈 결과는 propositions=[]와 연결0개/명시 이유로 표현하며 원문을 몰래 자르거나 fabricated 명제를 만들지 않는다.

의존 방향은 **종속 명제 → 선행 조건 명제**다. 예를 들어 신청 허용 명제A가 상급기관 승인 명제B를 전제로 하면 A.depends_on_ids=[B]다. prerequisite facet은 조건을 설명하는 literal이지 반대 방향을 만드는 별도 edge가 아니다. 단일 명제에 조건/행위를 함께 인용했거나 선행 조건을 별도 명제로 추출하지 못한 경우 depends_on_ids=[]를 허용한다. 이 경우 조건 facet을 없애지 않으며 edge가 없다는 이유로 무조건 허용으로 해석하지 않는다. ID edge의 존재·acyclic 검사는 의미적 전제 관계의 진실 검증이 아니다.

quantity의 경계가 보이지 않아도 eq로 추정하지 않는다. 명시 bound가 없으면 그 부재를 유지하며, 변환기는 소비자가 이해할 수 없는 경계를 임의 보충하지 않는다. bound/distribution target은 quantity여야 한다. 다른 facet의 target_ids는 비어 있어야 하며 prerequisite의 명제 의존 관계만 depends_on_ids로 표현한다. 순환/자기참조/없는 ID·중복을 거부한다. depends_on_ids는 원문 선후·전제 관계에 대한 제안이고 원문 존재만으로 의미 관계가 맞다고 인증하지 않는다.

공통 제한은 최초 구현 전에 명시한다: 명제 최대24·명제당 facet 최대16·각 참조목록 최대8·명제 의존 최대8·질문 최대2,000 code point. 이는 저장/출력 구조의 보호 상한이며 원문을 줄이는 규칙이 아니다. 초과하면 전체 거부하고 부분 성공으로 수리하지 않는다. Source 자체의 기존 상한은 유지한다. 전송 크기/토큰/출력 예산은 실제 새 schema까지 측정하기 전 확정하지 않는다.

## 표시와 사용

이 계약은 내부 근거 표현이다. 최종 사용자에게 facet/ID·coverage 행렬을 노출하지 않는다. 브리핑은 짧은 요약을 중심으로 조건·기한·절차를 적절한 표/타임라인으로 표현하며 정확 인용으로 원문을 연다. 구조 검증 성공을 ‘확인된 사실’ 배지로 바꾸지 않는다. 날짜가 미확정이면 원문 상대 표현을 유지한다. 응답이 부족하면 기존 부족 안내를 유지하고 숨은 재호출로 채우지 않는다.

계약을 만들었다고 renderer/agent/그래프/검색이 연결된 것은 아니다. typed 명제 → 근거 선택 → 기존 브리핑 변환의 별도 adapter와 현재 권한·예산·취소/복구 인수를 거친 뒤 앱 적용을 판단한다. 기존 worker/version/checkpoint는 보존한다.

## 구현 순서와 수용 기준

1. 순수 계약/validator를 별도 모듈로 TDD 구현한다. 무수치·빈 결과/coverage 이유·명시 부정·상대 시간·분배/상한·전제/계획을 합성 fixtures로 검증한다. 원문/질문 hash, exact span, dangling/중복/cycle, field 누락/extra, 실제/저장 타입, scalar subclass/unchecked 모델·정규화 오인을 거부해야 한다.
2. 새 생성 SDK를 별도로 설계한다. 원문·질문·새 schema가 예산 안에 들어오는지 먼저 측정한다. 기존20,000/출력1,800을 자동 승계하거나 늘리지 않는다. 전체24,000 등 앱 한도도 기존 호출을 포함해 별도 검증한다. 요청1회·무재시도·no-store·현재 설정/known usage/송신 불확실성을 보존하며 SDK가 실제 모델 의미를 인증하지 않는다.
3. 실제 요청 전 원문·질문·사전 required 항목/분모·한도·실패 기준을 고정한다. 현재12명제는 같은 기준의 개발 회귀 관측으로 남기고 시간3/비수치4를 빼지 않는다. P2의 기존 이견도 유지한다. 별도 미관측 자료/실사용 질문·독립 사람 판정이 일반 품질 판단에 필요하다.
4. 앱 연결은 별도 인수다. 공개 읽기/권한·저장 재열람·현재 원문 hash·합산 비용·취소/재시작·출처 귀속/불충분 안내를 모두 확인한다. 설계/합성 구조 통과만으로 활성화하지 않는다.

## 이번 무호출 시제품에서 확인할 것

이전12개 기준의 원문 span을 수동으로 새 유형에 배치해 좌석/인원·분배/상한·시간·자격/승인/부정/절차가 표현될 자리가 있는지 확인한다. **기준을 아는 수동 구조 시제품**이며 모델이 찾은 결과나12/12 의미 성공이 아니다. 근거 없는 분류라도 exact 인용만 맞으면 구조 검사를 통과할 수 있는 한계도 예시로 남긴다. 기존 실험과 원래 점수는 수정하지 않는다.

- [ ] 순수 계약/합성 검증 구현.
- [ ] 실제 SDK·새 요청 예산/출력 용량 확인.
- [ ] 고정 개발 회귀와 별도 미관측 실제 의미/비용 인수.
- [ ] 기존 브리핑 변환/권한/예산/내구 경계와 앱 인수.


### 무호출 시제품 결과

기존 원문과12개 기준의 span을 그대로 읽어12행의 수동 설계 배치를 만들었다.12개 exact span이 현재 인용의 위치와 일치했고 hash/인용 소유/범위/원래 offset 타입/문자열/중복의10개 변조를 거부했다. 이는 제한된 위치·출처 시제품 검사이며 위의 전체 순수 계약을 구현·검증한 것은 아니다.

같은 인용을 유지한 채 법적 지위 문장의 유형을 quantity로 잘못 붙인 예시는 위치 검사를 통과했다. 따라서 구조 통과를 의미 성공으로 세지 않는다. 모델 추출·자동 후보 recall·12명제 정답률·SDK 요청/출력 용량·전체 제품 인수는 미검증이다. 기존 실제 평가58개 보존 증거는 hash가 같고 유료 호출0/과거 재실행0이다.


## 설계 검토

초기 독립 검토 C0/I1/M1은 facet value의 실제 필드·빈 값/필수성, 전제 의존 방향/빈 의존 목록의 의미를 지적했다. 위의 정확한 키·타입·ref 포함/quantity target·uncertain 조건과 종속→선행 조건 방향을 명시했다. 수동 시제품을 전체 계약 구현으로 바꾸어 부르지 않으며 원래 결과는 보존했다.

수정 범위 재검토는 잔여 C0/I0/M0이며 설계 문서로 인수했다. 순수 계약 구현·SDK·앱 인수는 위의 열린 항목으로 유지한다. 실행 파일462개가 같으므로 기존 전체8,696QA를 재사용하며 새 전체QA를 실행한 것으로 표시하지 않는다.
