# 공통 Python 도메인·계약

Python 3.13.12·Pydantic 2.14.0의 `issuedigest-domain` 패키지입니다. 상태 응답 `Liveness`, `ServiceStatus`, 첫 원문·파싱·인용 계약과 두 번째 개체·주장·관계·비교 조건 부분 계약을 정의합니다. Python 모델 → 실제 FastAPI OpenAPI components → 생성 TypeScript 타입이 하나의 계약을 사용합니다. 이 패키지는 앱 내부 구현이나 저장소에 의존하지 않습니다.

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

`uv.lock`으로 의존성을 고정합니다. pytest는 API와 domain 테스트를 함께 발견하며 두 언어가 `tests/fixtures/citation-unicode.json`의 합성 UTF-8 자료를 공유합니다. 생성 파일은 직접 수정하지 않습니다. 후속 범위는 출처 시간의 연/월/일 정밀도, 재수집 관측, 내용 비교 fingerprint, 실제 parser·원문 저장, Run/Event/Canvas/Usage와 권한 검증입니다. 기준 DB·Neo4j·검색·실행기·제품 자료 수집은 아직 구현하지 않았습니다.


`ResearchBundle.schema_version=1`은 strict int입니다. 동일 이름의 개체는 다른 ID로 유지하며 외부 identity 없는 개체와 `identity_review=None`을 허용합니다. 검토의 `reviewed_at`은 시간대 있는 datetime 또는 ISO datetime 문자열만 받아 UTC로 직렬화하고 epoch 숫자/숫자 문자열을 거부합니다. 검토 입력은 인증된 사용자 행위 기록이 아닙니다. `SupportReview`는 claim 귀속(`attribution`)/내용(`content`) 또는 관계(`relation`)를 구분하며 인용은 target 인용의 부분집합이어야 합니다. 인용 존재와 입력된 `supported` 검토는 주장 내용의 진실을 자동 판정한 결과가 아닙니다.

관계는 법안→사람/조직 `introduced_by`, 법안→조직 `reviewed_by`, 법안→법안 `alternative_to`, 주장→주장 `supports`/`contradicts`, 문서→개체 `mentions`만 허용합니다. 인과 predicate나 자동 역방향을 만들지 않습니다. `mentions` 인용은 source 문서 버전에 속해야 합니다. 같은 문서/버전을 여러 파싱 표현에서 재사용할 수 있지만 해당 ID의 객체가 서로 다르면 거부합니다. ID/identity 유일성은 제공된 묶음 내부 규칙이며 저장소 전체 unique enforcement가 아닙니다.

`DateInterval`은 양 끝을 포함하며 Python date만 받고 datetime은 거부합니다. JSON은 정확한 ASCII `YYYY-MM-DD`만 허용합니다. 날짜를 모르면 null과 `raw_period`/`raw_validity_text`로 보존합니다. 수치 `value`는 최대 128자의 ASCII 소수 문자열이며 부동소수점 변환·반올림·음의 0 정규화를 하지 않습니다. 값이 있으면 `raw_value`가 필요하고, 값이 없으면 `missing_reason`이 필요합니다. 원문 값과 해석 값의 의미 일치는 인증하지 않습니다.

`assess_comparison`은 검증된 Observation tuple을 최소 두 개 받아 입력 순서와 객체를 보존합니다. metric부터 value 결측까지 고정된 순서로 확인합니다. 알려진 조건이 다르면 `different_context`, 차이 없이 결측이 있으면 `insufficient_context`, 모두 알려져 같으면 `same_context`입니다. dimensions는 순서를 제외한 key/value로 비교하며 빈 차원은 유효합니다. 수치 자체가 달라도 같은 조건이면 `same_context`이고 sample_size까지 같아야 합니다. 이 판정은 조사 동등성·합산·완전 분포를 증명하지 않으며 `aggregation_status`는 항상 `not_evaluated`입니다. 결과 모델은 사유 ID·중복·status 일관성도 검증합니다.
