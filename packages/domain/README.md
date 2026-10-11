# 공통 Python 도메인·계약

Python 3.13.12·Pydantic 2.14.0의 `issuedigest-domain` 패키지입니다. 상태 응답 `Liveness`, `ServiceStatus`와 첫 원문·파싱·인용 계약을 정의합니다. Python 모델 → 실제 FastAPI OpenAPI components → 생성 TypeScript 타입이 하나의 계약을 사용합니다. 이 패키지는 앱 내부 구현이나 저장소에 의존하지 않습니다.

| 모델·공개 함수 | 검증 범위 |
| --- | --- |
| `SourceDocument` | UUID4 문서/작업 공간, 공급처·원천 ID·자료 종류, 자격 증명 없는 HTTP(S) URL |
| `DocumentVersion` | UUID4 원문 객체 참조, 소문자 SHA-256 형식, 시간대 있는 수집 시각의 UTC 직렬화 |
| `ParsedRepresentation`, `PageSpan` | 파서·정규화 버전, UTF-8 텍스트 해시 일치, code point 페이지 범위·순서·중복 |
| `ParsedTable`, `TableCell` | 표/셀 식별자 중복, strict 양의 표본 크기, 결측 조건의 null 유지 |
| `TextQuoteSelector`, `PdfQuoteSelector`, `NormalizedBox`, `TableCellSelector` | 정확한 텍스트/페이지/전체 셀 인용, 유한 0~1 PDF 사각형 |
| `Citation`, `EvidenceBundle` | 원문 버전·파싱 표현·인용의 ID 연결, 인용 ID 중복과 위치/문맥 |
| `validate_citation`, `CitationAnchorValidation` | 정확한 anchor 일치: `anchor_status="matched"`, 의미 지지: `support_status="not_evaluated"` |

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

`uv.lock`으로 의존성을 고정합니다. pytest는 API와 domain 테스트를 함께 발견하며 두 언어가 `tests/fixtures/citation-unicode.json`의 합성 UTF-8 자료를 공유합니다. 생성 파일은 직접 수정하지 않습니다. 후속 범위는 출처 시간의 연/월/일 정밀도, 재수집 관측, 내용 비교 fingerprint, 실제 parser·원문 저장, 주장/관계·비교 조건, Run/Event/Canvas/Usage와 권한 검증입니다. 기준 DB·Neo4j·검색·실행기·제품 자료 수집은 아직 구현하지 않았습니다.
