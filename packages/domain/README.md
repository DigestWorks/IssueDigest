# 공통 Python 도메인·계약

Python 3.13.12·Pydantic 2.14.0의 `issuedigest-domain` 패키지입니다. 상태 응답 `Liveness`, `ServiceStatus`, 첫 원문·파싱·인용 계약과 두 번째 개체·주장·관계·비교 조건과 세 번째 실행·화면·사용량 부분 계약을 정의합니다. Python 모델 → 실제 FastAPI OpenAPI components → 생성 TypeScript 타입이 하나의 계약을 사용합니다. 이 패키지는 앱 내부 구현이나 저장소에 의존하지 않습니다.

| 모델·공개 함수 | 검증 범위 |
| --- | --- |
| `SourceDocument` | UUID4 문서/작업 공간, 공급처·원천 ID·자료 종류, 자격 증명 없는 HTTP(S) URL |
| `DocumentVersion` | UUID4 원문 객체 참조, 소문자 SHA-256 형식, 시간대 있는 수집 시각의 UTC 직렬화 |
| `ParsedRepresentation`, `PageSpan` | 파서·정규화 버전, UTF-8 텍스트 해시 일치, code point 페이지 범위·순서·중복 |
| `ParsedTable`, `TableCell` | 표/셀 식별자 중복, strict 양의 표본 크기, 결측 조건의 null 유지 |
| `TextQuoteSelector`, `PdfQuoteSelector`, `NormalizedBox`, `TableCellSelector` | 정확한 텍스트/페이지/전체 셀 인용, 유한 0~1 PDF 사각형 |
| `Citation`, `EvidenceBundle` | 원문 버전·파싱 표현·인용의 ID 연결, 인용 ID 중복과 위치/문맥 |
| `validate_citation`, `CitationAnchorValidation` | 정확한 anchor 일치: `anchor_status="matched"`, 의미 지지: `support_status="not_evaluated"` |
| `SourceIdentity`, `Entity`, `IdentityReview` | 외부 식별 3항 키·별칭 중복, 독립 ID·미검토 상태, 인용 있는 검토 메타데이터 |
| `EntityReference`, `ClaimReference`, `DocumentReference`, `RelationReference` | kind 태그와 UUID4 대상 참조 |
| `Claim`, `DerivationRecord`, `SupportReview` | 원문 주장/관측/추론 구분, 추론에만 가공 근거 필수, 귀속/내용/관계 검토 범위 |
| `Relation` | `issuedigest-relations-v1` 제한 어휘·방향·자기 관계 거부·근거 참조 |
| `DateInterval`, `Dimension`, `ComparisonContext`, `Observation` | 정확한 날짜·기간·조건, strict 표본 크기, 정밀 수치 문자열·결측 보존 |
| `assess_comparison`, `ComparisonAssessment`, `ComparisonReason` | 조건 일치/차이/부족·관련 ID와 판정 일관성, 합산 `not_evaluated` |
| `ResearchBundle` | 같은 공간의 실제 제공 객체 참조, 문서/버전 충돌·전역 인용/검토 ID·외부 식별 충돌, 검토 인용 subset |

새 모델은 `extra=forbid`, `frozen=True`이며 중첩 모델도 불변이고 컬렉션은 tuple입니다. JSON 배열 입력과 JSON round-trip을 지원합니다. 신뢰할 수 없는 입력은 `model_validate` 또는 `model_validate_json`으로 검사해야 합니다. Pydantic의 `model_construct` 및 `model_copy(update=...)`는 검증을 생략하므로 입력 경로로 사용하지 않습니다. `validate_citation`은 이미 검증된 `Citation`/`ParsedRepresentation`을 받습니다. 불변 계약은 실제 저장·중복 제거·동시 변경 처리의 구현 증거가 아닙니다.

인용 오프셋은 Python Unicode code point의 `[start,end)`이며 bool·실수·숫자 문자열을 거부합니다. 공백·NFC/NFD를 자동 변경하지 않고 prefix/suffix는 바로 인접한 텍스트와 일치해야 합니다. PDF 인용은 지정 페이지 span 안에 있어야 하며 regions 기본값은 빈 tuple입니다. 좌표는 회전·crop을 반영한 표시 페이지 좌상단 원점입니다. 입력 형식·범위만 검사하며 실제 PDF 렌더링이나 회전 변환을 하지 않습니다. 빈 표·빈 셀과 정확한 빈 셀 인용도 보존합니다. 부족한 통계 조건을 채우거나 합산·보간하지 않습니다.

원문 해시는 bytes를 받지 않으므로 형식만 검사합니다. `raw_object_id`는 경로나 서명 URL이 아닌 불투명 UUID4 객체 ID입니다. URL 검증은 네트워크 접근 허가가 아닙니다. 파서 버전이 바뀌면 별도 representation ID로 과거 표현·인용과 공존할 수 있고, 다른 원문/표현 버전 인용을 재결합하지 않습니다. 원문 보관·접근 권한·파싱 성공·주장 의미 지지는 아직 구현하지 않았습니다.

저장소 루트에서 설치·검증합니다.

```sh
uv sync --locked --all-packages
uv run ruff check .
uv run mypy
uv run pytest
npm run contract:generate
npm run contract:check
```

`uv.lock`으로 의존성을 고정합니다. pytest는 API와 domain 테스트를 함께 발견하며 두 언어가 `tests/fixtures/citation-unicode.json`의 합성 UTF-8 자료를 공유합니다. 생성 파일은 직접 수정하지 않습니다. 후속 범위는 출처 시간의 연/월/일 정밀도, 재수집 관측, 내용 비교 fingerprint, 실제 parser·원문 저장, 실행 이벤트 저장·SSE·권한·공급자 호출·화면 렌더러와 동시 예산 처리입니다. 기준 DB·Neo4j·검색·실행기·제품 자료 수집은 아직 구현하지 않았습니다.


`ResearchBundle.schema_version=1`은 strict int입니다. 동일 이름의 개체는 다른 ID로 유지하며 외부 identity 없는 개체와 `identity_review=None`을 허용합니다. 검토의 `reviewed_at`은 시간대 있는 datetime 또는 ISO datetime 문자열만 받아 UTC로 직렬화하고 epoch 숫자/숫자 문자열을 거부합니다. 검토 입력은 인증된 사용자 행위 기록이 아닙니다. `SupportReview`는 claim 귀속(`attribution`)/내용(`content`) 또는 관계(`relation`)를 구분하며 인용은 target 인용의 부분집합이어야 합니다. 인용 존재와 입력된 `supported` 검토는 주장 내용의 진실을 자동 판정한 결과가 아닙니다.

관계는 법안→사람/조직 `introduced_by`, 법안→조직 `reviewed_by`, 법안→법안 `alternative_to`, 주장→주장 `supports`/`contradicts`, 문서→개체 `mentions`만 허용합니다. 인과 predicate나 자동 역방향을 만들지 않습니다. `mentions` 인용은 source 문서 버전에 속해야 합니다. 같은 문서/버전을 여러 파싱 표현에서 재사용할 수 있지만 해당 ID의 객체가 서로 다르면 거부합니다. ID/identity 유일성은 제공된 묶음 내부 규칙이며 저장소 전체 unique enforcement가 아닙니다.

`DateInterval`은 양 끝을 포함하며 Python date만 받고 datetime은 거부합니다. JSON은 정확한 ASCII `YYYY-MM-DD`만 허용합니다. 날짜를 모르면 null과 `raw_period`/`raw_validity_text`로 보존합니다. 수치 `value`는 최대 128자의 ASCII 소수 문자열이며 부동소수점 변환·반올림·음의 0 정규화를 하지 않습니다. 값이 있으면 `raw_value`가 필요하고, 값이 없으면 `missing_reason`이 필요합니다. 원문 값과 해석 값의 의미 일치는 인증하지 않습니다.

`assess_comparison`은 검증된 Observation tuple을 최소 두 개 받아 입력 순서와 객체를 보존합니다. metric부터 value 결측까지 고정된 순서로 확인합니다. 알려진 조건이 다르면 `different_context`, 차이 없이 결측이 있으면 `insufficient_context`, 모두 알려져 같으면 `same_context`입니다. dimensions는 순서를 제외한 key/value로 비교하며 빈 차원은 유효합니다. 수치 자체가 달라도 같은 조건이면 `same_context`이고 sample_size까지 같아야 합니다. 이 판정은 조사 동등성·합산·완전 분포를 증명하지 않으며 `aggregation_status`는 항상 `not_evaluated`입니다. 결과 모델은 사유 ID·중복·status 일관성도 검증합니다. 같은 필드의 missing/different 사유 ID는 겹칠 수 없으며, 항상 알려진 metric/dimensions에는 missing 사유를 허용하지 않습니다. 세 개 이상 관측에서 결측 항목과 다른 알려진 항목이 분리된 사유, 서로 다른 필드의 독립 사유는 허용합니다.


## 실행·화면·사용량의 제공 객체 계약

| 파일·공개 모델/함수 | 검증 범위 |
| --- | --- |
| `contract_values.py` / `MoneyMicrowon` | 새 계약의 strict 문자열·0..2**53-1 정수·UTC 시각·정밀 정수 금액 공유 값 |
| `canvas_modules.py` / `CanvasModule`, `CanvasAction` 및 종류별 모델 | evidence/summary/comparison/timeline/graph/bar chart, 인용/기록 ID와 네 종류의 제안 액션 |
| `execution.py` / `ExecutionVersions`, `RunInput`, `RunSubmission`, `Run`, `SubmissionAssessment` | 자료 버전 순서·원문 질문 고정, 정확한 JSON SHA-256 재계산, 제출 범위별 create/reuse/conflict |
| `execution.py` / `RunEvent`, `RunEventPayload`, `RunHistory`, `RunSnapshot`, `ReplayBatch`, `CallAttempt` | 단일 kind 태그, 연속 seq·공간/실행·취소·미확인 상태와 호출 시각/결과 기록 |
| `hash_run_input`, `assess_submission`, `replay_run`, `events_after`, `may_start_paid_step` | 입력 해시·제공 중복 제출 판정·결정적 fold·정확한 cursor tail·유료 시작 적격성 |
| `canvas.py` / `CanvasDraft`, `CanvasRevision`, `CanvasBundle`, `promote_revision` | 정상 제안과 실패 안내 분리, 선택 자료·인용 합집합·기록 존재, 같은 조건의 알려진 차트 값, 부모/번호/expected ID 충돌 |
| `usage.py` / `PricingSnapshot`, `BudgetWindow`, `UsageReservation`, `UsageEntry`, `UsageBook`, `BudgetAssessment`, `assess_budget` | 서울 완전한 월·전체 운영비 한도, 가격/예약/entry 참조와 정산, 정밀 합계·unknown 예약 유지·실제 초과비용 |
| `execution_bundle.py` / `RunExecutionBundle` | 전체 제공 객체 연결, 동일 revision 모듈 발표 후 성공, prefix별 유료 권한과 중복 재시도 거부, 미확인/해소 및 사용량 참조 |

새 계약에만 strict 문자열과 JS 안전 정수를 적용합니다. `schema_version=1`은 bool/숫자 문자열을 거부합니다. 새 시각은 aware datetime 또는 ISO datetime 문자열만 받고 UTC로 정규화하며 epoch·date-only·naive·UTC 범위 초과를 거부합니다. 기존 원문/연구 계약의 값 정책은 그대로입니다. 모든 새 모델은 frozen/extra-forbid, 중첩 컬렉션은 tuple입니다. 검증 생략 construction/copy는 입력 경로가 아닙니다.

Run의 세 ID는 실행·요청·추적을 구분하고 설정/엔진 버전은 기록입니다. 자료 tuple 순서와 질문 공백을 해시에 보존합니다. 제공된 입력 객체의 실제 동등성으로 재전송을 판정하며 해시만으로 reuse하지 않습니다. 실제 중복 제출 unique·트랜잭션은 후속입니다.

이력은 저장 순번으로 처리하고 시각은 run 생성 이후이면 허용합니다. 벽시계의 단조 증가나 가상 진행률을 요구하지 않습니다. 정상 화면은 성공만 승격하고 실패·취소는 base를 보존합니다. 취소된 작업의 늦은 비용 확인은 unresolved 목록만 해소하며 화면/최종 상태를 되돌리지 않습니다. 유료 시작은 accepted/running·취소 의도와 unresolved 없음일 때만 적격입니다. cursor tail과 latest snapshot은 제공된 전체 이력을 검사한 결과이며 저장·SSE·실시간 합류·복구·보존 만료를 구현하지 않습니다.

Canvas의 네 액션은 원문 열기·자료 선택·질문 제안·정렬입니다. 임의 HTML/CSS/URL/도구/쓰기 필드는 없습니다. 표시는 기존 인용·주장·관측에서 가져올 참조이고 안전 렌더링·권한·실제 행위는 후속입니다. `promote_revision`은 후보 근거/부모 충돌만 검사하여 후보를 반환합니다. 실행 성공/취소 적격성은 이력이 검사하고 저장 CAS나 동시 변경은 구현하지 않습니다.

Money는 최대128자의 strict ASCII 정수 문자열이며 1원=1,000,000 microwon입니다. Python int로 합산하여 float/Decimal context 반올림을 사용하지 않습니다. `BudgetAssessment`의 `limit_microwon`, `used_microwon`, `requested_microwon`, `remaining_microwon`, `overrun_microwon`은 모두 같은 단위입니다. 월 상한은 전체 운영비 10만 원이며 `committed_other_cost_microwon`에 서버·DB·저장·세금·같은 키의 외부 비용을 입력합니다. held는 예약과 entry 비용 합의 최댓값, settled는 알려진 실제 비용을 사용합니다. 취소/실패·예약 초과는 비용을 없애지 않습니다. 가격·환율·사용량의 입력은 공급자 확인이나 완전한 청구 내역을 증명하지 않습니다. 실제 요금 변환·외부 지출 집계·동시 예약·원자성은 후속입니다.

`RunExecutionBundle`은 현재 run의 base·revision·module.ready·attempt·usage를 연결합니다. 제공된 같은 공간의 다른 run revision도 부모/번호/근거를 모두 검사하며 ancestor만 포함하는 최소 이력을 선택하지 않습니다. 현재 run의 first revision은 base(없으면 None)를 부모로 하는 한 개까지이며 이후 후보는 현재 run revision을 부모로 합니다. 같은 부모의 후속 후보를 unique 번호로 제한하지 않고 저장 CAS도 구현하지 않습니다. 유료 dispatch는 제공된 `authorized_after_seq` prefix와 시각 부등식으로 검증합니다. 이 적격 cursor는 실제 dispatch 시점에 새 권한 확인을 했다는 증거가 아니며, 단조 증가하지 않는 이벤트 시각에서 물리적 취소 경합 순서를 추정하지 않습니다. 실제 worker/DB가 dispatch 직전 취소·예산 권한을 강제하는 작업은 후속입니다. UsageBook에는 다른 run의 예약도 담을 수 있지만 해당 run의 실행 이력을 인증하지 않습니다. 합성 fixture 검증은 제품 화면·AI 출력·운영 복구 구현의 증거가 아닙니다.

## 저장 근거 문자 검색 SDK 계약

`EvidenceSearchQuery`는 literal term 1~8개(각 1~64 Unicode code points),
strict 정수 `limit` 1~20을 받습니다. 비공백 term의 앞뒤 공백과 ASCII 비교상 중복은
거부합니다. `provider`·`source_id`는 정확한 문자열 필터(1~1,024자), `source_kind`는
기존 출처 종류입니다. 선택적 `collected_from`·`collected_to`는 UTC-aware `datetime`이며
시작 포함·끝 제외의 증가하는 수집 시각 구간입니다. 발행·시행 시각을 뜻하지 않습니다.
모델은 frozen/extra-forbid이며 `validate_search_query`가 SDK 진입점에서 construct/copy 입력을
다시 검사합니다. 새 모델은 HTTP/OpenAPI·웹 계약에 연결하지 않습니다.

```python
from issuedigest_domain import EvidenceSearchQuery, build_search_projection

query = EvidenceSearchQuery(terms=("등록금", "ABC-123"), limit=10)
projection = build_search_projection(bundle)  # 검증된 불변 EvidenceBundle
```

`literal-ngrams-v1`은 512자 본문 단위와 63자 중첩을 사용합니다. PDF는 기존 실제 `PageSpan`
안에서만 분할하고 page 번호를 보존하며 좌표를 추정하지 않습니다. PDF 판정은 정확한
`application/pdf` media type을 사용합니다. 일반 본문은 PageSpan metadata가 있어도 전체 본문을
TextQuoteSelector로 분할하며 span 사이의 텍스트도 포함합니다. `application/pdf`의
비어 있지 않은 본문에 PageSpan이 없으면 고정 입력 오류로 거부합니다. 빈 PDF 본문의 온전한
셀은 페이지를 주장하지 않고 투영할 수 있습니다. 실제 페이지가 없는 PDF 텍스트는 PageSpan을
제공하는 재파싱 후 투영합니다. 1~2,048자 표 셀은 전체
`TableCellSelector`로 추가하고, 빈 셀과 큰 셀의 제외 수를 각각 기록합니다. 큰 셀이 본문에도
있다면 본문 단위에서 검색될 수 있습니다. `validate_selector`는 기존 인용 검증과 검색 단위가
공유하는 정확한 텍스트·페이지·셀 anchor 검사입니다.

투영은 전체 직렬화 전에 본문 1,000,000자·표 1,000개·셀 20,000개·단위 6,000개·단위 텍스트
총 2,000,000자를 검사합니다. 위조 모델 그래프도 500,000노드·깊이32·전체 문자열 12,000,000자와
컬렉션 한도로 먼저 검사하고 고정 `ValueError`를 반환합니다. 결정적인 단위 순서, selector,
원문 SHA-256, ASCII 비교용 1·2·3-gram 집합을 만듭니다. 원문 offset은 Unicode code points이며
ASCII A~Z만 소문자로 비교합니다. Unicode 정규화·형태소 분석·와일드카드 해석은 없습니다.
모든 term은 같은 검색 단위 안에 있어야 합니다.

`EvidenceSearchResult`는 `hits`, 필터 범위의 `SearchCoverage`, `scanned_candidates`, `truncated`를
반환합니다. hit는 원 workspace/snapshot/document/version/representation과 출처 metadata,
정확한 selector, `matched_terms`, `anchor_status="matched"`, `support_status="not_evaluated"`를
갖습니다. hit의 provider/source_id는 canonical SourceDocument의 NonBlank 계약을 그대로
보존하며 1,024자를 넘는 값도 자르지 않습니다. query 필터 한도는 반환 metadata 한도가 아닙니다.
Citation ID를 만들거나 등록된 인용으로 표시하지 않습니다. 빈 결과에서도 전체·투영·
미투영 snapshot 수와 제외 셀 수를 확인해야 하며, 문자 일치는 주장 지지·관련성·의미 검색 품질을
뜻하지 않습니다.

## 조사 화면 계약

`research_journey.py`는 자료 표시 sidecar, 질문/선택적 부모 요청, 서버가 찾은0~5개 snapshot의 실행 기록, 증가하는 상태 이벤트, 자동 저장된 `CanvasBundle` 결과를 정의합니다. 완료 결과는1개 이상의 유효 근거를 요구하며 queued/무근거실패는 빈 근거를 허용합니다. 요청의 snapshot_ids/임의 필드는 거부합니다. 기존 불변 SourceDocument/EvidenceBundle 필드는 바꾸지 않습니다. 표시 제목에는 UUID를 허용하지 않으며 알 수 없는 원본에는 자료 종류의 중립적 이름을 사용합니다.


private research-v3/v4/v5의 분류는 generic Claim에 필드를 추가하지 않고 기존 SupportReview로만 기록합니다. ResearchResult의 조건부 경계는 inference·동일 method_version research-v3 또는 research-v4 또는 research-v5 통일·review1개/claim·고정 automated 식별자·동일한 인용 순서·UTC 마이크로초 일치·300자 설명과 세 scope/assessment 조합만 허용합니다. 기존v1/v2는 빈 review로 그대로 읽으며 분류를 소급하지 않습니다. 공개 D020는v1/v2/빈 review만 허용하고 v3/v4/v5 게시는 지원하지 않습니다. 기존 canonical JSON/hash와 OpenAPI shape를 유지합니다.

private v4도 기존 세 분류/300자 설명/동일 인용 순서/UTC 마이크로초 검증과 UI를 사용한다. reviewer_id issuedigest-research-v4와 method_version research-v4가 같은 버전의 모든 claim에 정확히 일치해야 하며 v3/v4/v5 혼합·누락·다른 인용/시각은 거부한다. 공개는 계속 v1/v2/빈 reviews만 허용하고 v3/v4/v5는 review를 제거해도 거부한다. generic Claim/default·OpenAPI·과거 canonical JSON/hash는 변경하지 않는다.


새 private v5의 고정 reviewer_id는 `issuedigest-research-v5`, method_version은 `research-v5`다. 같은 엄격 분류·UTC 마이크로초·인용 순서·claim당1개 규칙을 적용한다. v3/v4/v5를 서로 섞지 않고 public v1/v2/빈 reviews 경계를 유지한다. 과거 결과를 새 분류로 다시 쓰지 않는다.


private v10은 정확 `research-v10`/`issuedigest-research-v10`만 추가한다. 기존 첫 supported summary·귀속 접두어·Unicode·인용별 정확 날짜·AI 평가 metadata와 누락/혼합/위조 거부를 유지한다. 실제 Python builder의 comparison/timeline/astral/비답변 fixture를 기존 full client·첫 열린 요약/접힌 상세·정확 근거 화면으로 전달한다. public v1/v2·API/OpenAPI·저장 schema와 화면 레이아웃은 확장하지 않는다. 합성 출력은 실제 의미 정확성 인증이 아니다.
