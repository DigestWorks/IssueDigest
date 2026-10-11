# 개체·주장·관계·비교 조건 계약

상태: 구현·검증·독립 리뷰·Draft PR #5·Sites v20 완료 · 2026-10-11 한국 시간. 기준 `ef62666`, 선행 PR #4. 다음 작업 진행 요청으로 승인된 계약 구현의 두 번째 묶음이다.

## 목표와 경계

[계약 조사](../research/product-contracts.md)의 개체·주장·관계와 조건 있는 수치를 실행 가능한 계약으로 옮긴다. 동명이인을 이름만으로 합치지 않고, 근거 없는 관계·잘못된 양 끝·다른 공간 참조를 거부한다. 원문 위치 일치와 의미 검토 결과는 구분한다. 수치 비교는 알려진 조건의 일치/차이/부족을 보고하며 통계적 비교 가능성이나 합산 가능성을 인증하지 않는다.

주체·가공 방법·검토 기록을 분리하는 설계는 [W3C PROV 개요](https://www.w3.org/TR/prov-overview/)를 참고한다. RDF/JSON-LD 호환 구현을 뜻하지 않는다. [Pydantic 수치 타입](https://pydantic.dev/docs/validation/latest/api/pydantic/standard_library_types/)의 입력 변환에 의존하지 않고 정밀 수치는 문자열로 제한한다.

## Global Constraints

- 기존 원문/파싱/인용 계약·상태 API·웹 UI를 보존한다. Python 모델 → 실제 OpenAPI components → 생성 TypeScript가 원본 경로다. 새 제품 HTTP 경로·UI·DB·Neo4j 쓰기·AI 호출·수집 기능을 만들지 않는다.
- 새 모델은 frozen/extra-forbid, 중첩 모델과 tuple까지 불변이다. UUID4 내부 ID, 공백만 있는 식별자/내용 거부, JSON 왕복, strict integer 표본 크기를 적용한다. 숫자·bool을 식별자/수치 문자열로 변환하지 않는다.
- 검증 대상은 제공된 객체/참조/조건이다. 근거가 존재해도 주장이 사실임을 보장하지 않는다. 사람이 검토했다는 입력도 인증된 행위 기록이 아니며 실제 인증·저장·추출·Neo4j 투영은 후속이다.
- `schema_version=1`은 int만 허용한다. 기존 source-evidence 계약 버전을 변경하지 않는다. 온톨로지/비교 정책은 아래 제한된 v1으로 버전 관리하며 알 수 없는 종류/버전을 거부한다.
- 새 종속성·외부/유료 호출·비공개 코드·운영 자료 없이 합성 fixture로 검증한다. DB/검색/실행기/인증 제안을 확정하지 않는다.
- 역할별 파일: `knowledge.py`(개체/참조/주장/검토), `relations.py`(온톨로지/관계), `observations.py`(기간/조건/수치/비교), `research.py`(묶음 참조 검증). 날짜 타입은 observations에서 공유하며 import cycle을 만들지 않는다. API의 기존 contracts 등록 경로와 api-client 공개 생성 타입을 확장한다.

## 완료 기준

### C1. 개체·주장·검토 기록

- `SourceIdentity`: provider, namespace, value (각 NonBlank 문자열). URL/이름은 동일성 키가 아니다.
- `Entity`: entity_id, workspace_id, kind (`person`, `organization`, `bill`, `policy`, `issue`, `place`), name, aliases(tuple NonBlank, 정확히 같은 별칭 중복 거부), source_identities(tuple SourceIdentity, 같은 3항 키 중복 거부), optional valid_period(DateInterval), optional raw_validity_text(NonBlank), optional identity_review(IdentityReview).
- 같은 이름·다른 ID는 허용한다. source identity 없이 미해결 개체를 기록할 수 있다. identity_review=None은 미검토이며 이름 비교로 자동 생성하지 않는다.
- 공통 검토 메타데이터: review_id(UUID4), reviewer_kind(`human`/`automated`), reviewer_id(NonBlank), method, method_version, reviewed_at(aware UTC), rationale(NonBlank), citation_ids(비어 있지 않은 unique UUID4 tuple). reviewed_at 입력은 datetime 또는 ISO datetime 문자열이며 epoch 숫자/bool/naive 날짜를 거부한다. 새 공통 검토 타입 내부 base class는 공개 API에 노출하지 않아도 된다.
- `IdentityReview`: 위 메타데이터 + assessment(`confirmed`, `ambiguous`). 지정 인용이 존재해야 한다. 두 개체의 같은 외부 identity 충돌을 review 입력으로 덮어쓰지 않는다.
- `EntityReference(kind="entity", entity_id)`, `ClaimReference(kind="claim", claim_id)`, `DocumentReference(kind="document", document_id)`는 태그 있는 frozen 모델이다. Relation 양 끝은 kind discriminator union이다. SupportReview target은 claim/relation 참조만 허용하므로 `RelationReference(kind="relation", relation_id)`도 정의한다.
- `DerivationRecord`: method, method_version, rationale(모두 NonBlank). 자동 의미 검증이 아닌 입력된 가공/추론 근거 기록이다.
- `Claim`: claim_id, workspace_id, text(NonBlank), basis(`source_assertion`, `observation`, `inference`), speaker_entity_id(nullable UUID4), subject_entity_ids(unique UUID4 tuple), citation_ids(nonempty unique UUID4 tuple), optional valid_period, optional raw_event_time_text(NonBlank), optional derivation.
- basis=inference이면 derivation 필수; 다른 basis이면 derivation을 거부한다. 원문 주장의 화자가 불명이면 null을 유지한다. speaker/subject가 있으면 같은 bundle의 개체를 가리켜야 한다. 인용과 text는 제공된 해석이며 내용 지지를 자동 판정하지 않는다.
- `SupportReview`: 공통 검토 메타데이터 + target(ClaimReference/RelationReference discriminated union), scope(`attribution`, `content`, `relation`), assessment(`supported`, `contradicted`, `insufficient`). claim은 attribution/content만, relation은 relation만 허용한다. review citation_ids는 해당 target의 citation_ids 부분집합이어야 한다. 기록된 의미 검토와 실제 실행 검증을 혼동하지 않는다.

### C2. 제한된 관계 어휘

- `Relation`: relation_id, workspace_id, ontology_version=`issuedigest-relations-v1`, predicate, source/target(위 3종 참조), basis(Claim과 같음), citation_ids(nonempty unique tuple), optional valid_period, optional derivation. basis/derivation 조건은 Claim과 같다. 같은 typed endpoint 자기 관계는 거부한다.
- 허용 방향/개체 종류:

| predicate | source | target |
|---|---|---|
| introduced_by | entity:bill | entity:person 또는 organization |
| reviewed_by | entity:bill | entity:organization |
| alternative_to | entity:bill | entity:bill |
| supports | claim | claim |
| contradicts | claim | claim |
| mentions | document | entity:모든 허용 종류 |

- endpoint 태그/존재/개체 종류를 검사한다. causes 등 미등록 predicate는 inference라도 거부한다. mentions 인용은 모두 source document의 버전에 속해야 한다. 시간 선후·동시 등장으로 다른 predicate를 만들거나 역방향 자동 추가하지 않는다.
- 이 어휘는 구조적 v1 경계다. predicate에 인용이 있다고 내용상 관계가 입증됐다는 뜻이 아니다. 그래프 투영이나 온톨로지 추론 엔진을 도입하지 않는다.

### C3. 수치·기간·조건 판정

- `DateInterval`: start_date, end_date (필수 date, inclusive, end>=start). JSON은 정확한 YYYY-MM-DD, Python은 date만(date subclass datetime 제외), datetime/epoch/bool/짧은 월/잘못된 날짜 거부. 불명·연/월만 아는 기간은 null + raw_period/raw_validity_text로 보존하며 날짜를 만들어 채우지 않는다.
- `Dimension`: key, value(NonBlank). `ComparisonContext`: metric(NonBlank), unit/population/geography/question/methodology/weighting/denominator/series_id(각 nullable NonBlank), period(nullable DateInterval), sample_size(nullable strict positive int), dimensions(tuple Dimension, duplicate key 거부).
- `Observation`: observation_id, workspace_id, subject_entity_id(nullable UUID4), raw_value(nullable str, 공백만 있으면 거부하되 원본 보존), value(nullable strict 문자열), missing_reason(nullable `not_reported`, `unreadable`, `not_applicable`, `withheld`), raw_period(nullable NonBlank), context(ComparisonContext), citation_ids(nonempty unique UUID4 tuple).
- value 문자열은 최대128자, ASCII `-?(0|[1-9][0-9]*)(\.[0-9]+)?` 형식(whole-string). 숫자 입력/NaN/Infinity/지수/콤마/공백/선행0 거부. 큰 정밀 값을 float로 바꾸지 않으며 소수점 자리·음의0을 자동 변경하지 않는다. value가 있으면 raw_value 필수·missing_reason은 null; value가 없으면 missing_reason 필수. 결측을 0으로 변경하지 않는다. 원문 값과 해석 값의 의미 일치를 인증하지 않는다.
- `assess_comparison(observations: tuple[Observation,...]) -> ComparisonAssessment`: 입력은 검증된 모델, 최소2개, observation_id unique, 같은 workspace(위반 ValueError). 순서를 보존한다. 입력을 바꾸거나 합산/비율 계산을 하지 않는다.
- `ComparisonAssessment`: policy_version=`issuedigest-comparison-v1`, observation_ids(tuple), status(`same_context`, `different_context`, `insufficient_context`), reasons(tuple ComparisonReason), aggregation_status=`not_evaluated`. `ComparisonReason`: field(아래 목록), kind(`different`, `missing`), observation_ids(관련 unique ID tuple).
- 비교할 필드 순서는 metric, unit, period, population, geography, question, methodology, sample_size, weighting, denominator, series_id, dimensions, value. value는 수치 자체를 비교하지 않고 결측만 확인한다. nullable 조건 하나라도 null이면 해당 field missing 사유, 알려진 값이 서로 다르면 different 사유도 함께 남긴다. missing이 없어도 값이 다르면 different_context, 하나라도 different가 있으면 missing과 같이 있더라도 different_context, different 없이 missing이면 insufficient_context, 사유가 없으면 same_context.
- dimensions는 key/value 맵으로 비교하여 순서만 다른 동일 조건은 같게 취급한다. 빈 dimensions는 차원 없음으로 유효하다. 비교 대상 observation_ids는 모든 입력 ID, 사유의 observation_ids는 missing인 항목만 또는 서로 다른 알려진 값이 있는 항목들을 입력 순서대로 기록한다.
- 결과 모델 자체도 observation_ids 최소2개/중복 거부, 사유 ID nonempty/unique 및 전체 ID의 부분집합, (field,kind) 사유 중복 거부, different 사유 최소2개 ID를 검사한다. value 필드는 missing 사유만 허용한다. 같은 field의 missing/different 사유 ID는 서로 겹치면 안 되며 non-nullable metric/dimensions의 missing 사유를 거부한다. 같은 field에서 결측 항목과 알려진 차이 항목이 분리된 사유 및 다른 field의 독립 사유는 허용한다. reasons로부터 위 우선순위로 정해진 status와 전달 status가 같아야 한다. 완성 결과 JSON의 모순도 거부하되 원래 observation 내용의 의미를 재판정하지 않는다.
- `same_context`는 메타데이터가 모두 알려져 일치한다는 뜻이며 조사 동등성·합산 가능성·분포 완전성을 증명하지 않는다. sample_size까지 엄격히 비교하는 보수적 정책이다. 다른 조건도 화면에서 나란히 읽을 수 있지만 하나의 동등 집단/합산/완전 분포로 인증하지 않는다. 합산/분포 엔진은 구현하지 않는다.

### C4. 묶음 참조·타입·검증

- `ResearchBundle`: schema_version=1(strict), workspace_id, evidence(tuple EvidenceBundle), entities, claims, relations, observations, support_reviews(각 tuple). 빈 작업 묶음 허용. 모든 문서와 기록의 workspace_id는 루트와 일치해야 한다.
- entity/claim/relation/observation/review ID는 각 컬렉션에서 unique. IdentityReview와 SupportReview의 review_id는 전체 묶음에서 unique. citation ID도 evidence 전체에서 unique. 같은 원문 doc/version이 여러 파싱 표현에 들어가는 것은 허용하되 같은 ID의 document/version 객체는 같아야 한다. representation_id는 evidence에서 unique. 외부 identity 3항 키가 서로 다른 Entity에 중복되면 거부한다. 이 규칙은 저장소 전체 unique enforcement가 아니다.
- 모든 인용 참조·speaker/subject·relation endpoint·review target을 실제 bundle 객체에 대조한다. 중첩 EvidenceBundle의 위치 검증은 기존 검증을 따른다. unknown/다른 workspace/참조 충돌을 거부한다. 문서/개체/주장 tag를 혼동하지 않는다. review 인용 subset/scope와 mentions source document 규칙을 적용한다.
- 기존 models_json_schema 등록을 한 번에 확장해 공유 $defs 충돌을 만들지 않는다. ResearchBundle/ComparisonAssessment와 의존 모델을 실제 OpenAPI와 생성 TS에 추가하고 공개 타입 aliases를 export한다. 모든 $refs/discriminator mapping 해석, HTTP paths 그대로, export=실제 OpenAPI, collision 거부, drift 통과.
- 테스트는 먼저 동작 실패를 확인한 후 구현한다. 동일 이름의 분리 개체, 외부 ID 충돌, 근거 없는/역방향/없는 endpoint/자기 관계/미등록 인과 predicate, inference 누락, 다른 workspace·자료 버전·review 참조, statement attribution vs truth, 서로 다른 문항/표본/기간/모집단/단위/분모/가중치/방법, null/불완전 분포, 숫자 정밀도·JSON coercion, 날짜 shape, tuple 불변을 검증한다. 조건만 같고 값이 달라도 same_context이며 aggregation은 not_evaluated여야 한다.
- 전체 npm run check, 독립 task/전체 변경 리뷰, Draft PR, Sites 공개 요약. package README/작업/진행/문서 안내를 갱신하고 나머지 P1·실제 자료/추출/권한/저장/AI/그래프는 미완료로 둔다. 연구 문서는 당시 조사 제안 기록이며 지우거나 구현 완료로 전체를 바꾸지 않는다.

## Task 1: 연구 계약과 조건 비교·생성 타입

- [x] C1~C4의 실행 코드·자동 검증·기록·독립 리뷰와 보완 재검토, Draft PR #5·Sites v20 공개 게시·사용자 폴더 연결을 완료했다.

관련 원본은 위 Global Constraints와 C1~C4, `docs/research/product-contracts.md`의 개체·주장·관계 부분이다. 기존 공개 EvidenceBundle 타입/Unicode helper/상태 API는 보존한다. `packages/domain/src/issuedigest_domain/`에 역할별 파일과 공개 exports, `packages/domain/tests/`에 의미 있는 동작 테스트를 추가한다. API contracts/테스트와 api-client 생성 파일/public exports/README를 확장한다. 새 TS 런타임 기능은 없다. docs/README, planning/tasks/progress에서 두 번째 부분 계약과 미완료 경계를 기록한다. controller가 Sites·GitHub·사용자 폴더 연결을 담당한다.

환경: Node24.21.0/npm11.19.0 (`PATH=/home/xinics/.nvm/versions/node/v24.21.0/bin:$PATH`), uv0.11.4/잠긴 Python3.13.12. 설치된 의존성을 사용한다. test-driven-development를 따른다. 기능별 실제 RED→GREEN, focused tests, 전체 check는 커밋 전1회, self-review/커밋/상세 보고서. 리뷰/게시 gate 전에 결합 checkbox를 무리하게 완료 처리하지 않는다.


## 구현 인계

역할별 Python 불변 모델·참조 검사와 비교 함수, 실제 OpenAPI components·생성 TypeScript/public aliases를 구현했다. 기존 HTTP paths·원문/인용·상태·웹 기능과 선행 계약 버전은 유지했다. 합성 자료만 사용했고 종속성·DB·추출·AI·그래프·UI를 추가하지 않았다. C1~C4 결합 체크박스는 controller의 독립 리뷰·PR·Sites 게시 전까지 대기로 유지한다. 실행 검증 결과·남은 단계는 [진행 기록](../planning/progress.md)에 기록한다. 제품 계약 조사·과거 제안은 보존한다.

최종 리뷰 P2 수정: 제공된 비교 결과 JSON에서 같은 필드의 결측/차이 ID 중복과 metric/dimensions 결측을 거부한다. 비교 알고리즘·정책 버전·생성 스키마 형태는 유지한다. 수정 회귀 검증과 재검토 상태는 진행 기록에 남긴다.
