# 원문·파싱·인용 계약 구현

상태: 코드·자동 검증·독립 리뷰 완료, Sites 게시 대기 · 2026-10-11. 기준 커밋 `92befb1`, 선행 PR #3. 사용자 승인: 다음 작업 진행 요청.

## 목표와 범위

[계약 조사](../research/product-contracts.md)의 첫 묶음을 실행 코드로 옮긴다. 자료의 원본 버전과 파서가 만든 표현을 분리하고, 인용이 그 표현의 실제 위치를 가리키는지 검증한다. 구조·위치 검증은 주장 지지 여부나 사실 정확성을 판정하지 않는다.

이번 작업은 저장·수집·AI 호출·화면 기능이 아니라 도메인 계약과 검증 함수다. DB·검색·실행기·인증 제안은 확정하지 않는다. 주장/관계, Run/Event, Canvas, 비용 계약은 후속 작업이다. 공개 API는 기존 상태 경로만 유지한다.

## Global Constraints

- Python/Pydantic 도메인이 계약 원본이며 실제 FastAPI OpenAPI → 생성 TypeScript로 연결한다. 계약 전용 가짜 HTTP 경로를 만들지 않는다.
- 새로운 모델은 `extra=forbid`, `frozen=True`; 중첩 모델도 frozen, 컬렉션은 tuple. 입력 JSON과 JSON round-trip을 지원한다. 임의 dict에 의미 있는 조건을 숨기지 않는다.
- 내부 ID와 저장 객체 참조는 UUID4, 해시는 소문자 SHA-256 64자리다. 저장 참조는 경로나 서명 URL이 아닌 불투명 객체 ID다. 수집 시각은 timezone-aware이며 UTC로 직렬화한다.
- 오프셋·페이지 번호는 strict integer로 bool/실수/숫자 문자열을 거부한다. 문자열 인용은 공백·NFC/NFD를 자동 변경하지 않는다.
- 원문 bytes를 받지 않는 이 계약은 원문 해시의 형식만 확인한다. 원문 보관·중복 제거·접근 권한·파싱 성공·의미 검증 완료를 주장하지 않는다.
- fixture는 명확한 합성 테스트 자료만 사용한다. 외부 호출·키·운영 자료·비공개 코드 복사는 없다. 종속성은 추가하지 않는다.
- 파일은 역할별로 나눈다: domain `sources.py`, `citations.py`, `evidence.py`; API `contracts.py`; TS `citations.ts`. 분할이 필요하면 controller에게 근거를 보고한다.

## 계약과 완료 기준

### B1. 원문과 파싱 표현

- `SourceDocument`: `document_id`, `workspace_id`, `provider`, `source_id`, `source_kind`, 선택 `canonical_url`. provider/source_id는 빈 문자열·공백만 거부하며 원래 값을 유지한다. source_kind는 `bill`, `legal_text`, `government_document`, `news`, `poll`, `statistics`, `petition`, `other`.
- URL은 http/https만 허용하며 사용자명/암호 포함 URL을 거부한다. URL 검증은 네트워크 접근 허가가 아니다.
- `DocumentVersion`: `version_id`, `document_id`, `raw_object_id`, `raw_sha256`, `media_type`, `collected_at`. 비교 정규화 해시나 출처 발행 시각은 이번 계약에 넣지 않는다. 출처의 연/월/일 정밀도를 임의 타임스탬프로 바꾸지 않도록 후속 계약에 남긴다.
- `ParsedRepresentation`: `representation_id`, `document_version_id`, `parser_name`, `parser_version`, `normalization_profile`, `text`, `text_sha256`, `pages`, `tables`. text_sha256는 전달된 text의 UTF-8 해시와 일치해야 한다. parser 이름/버전/정규화 profile은 명시하며 빈 값 거부.
- `PageSpan`: `page_number`(1부터), `start`, `end`(code point). 페이지 번호는 unique; span은 텍스트 안에서 비어 있지 않고 서로 겹치지 않으며 순서대로 온다. 페이지 사이 간격은 허용한다. PDF citation이 이 span 밖을 가리키면 거부한다.
- `TableCell`: `cell_id`, `text`, 선택 `unit`, `period`, `question`, `population`, `methodology`, `sample_size`, `weighting`. sample_size는 양의 strict integer 또는 null. 결측은 null로 유지하고 문항/표본 조건을 합산·보간하지 않는다.
- `ParsedTable`: `table_id`, `cells`. table/cell ID는 비어 있지 않은 문자열, 같은 표현에서 table_id unique, 같은 table에서 cell_id unique. 두 table의 같은 cell_id는 허용한다. 빈 표/빈 셀 text는 허용하며 부족한 원자료를 만들어 채우지 않는다.
- 원문이 동일하고 파서 버전만 바뀌면 별도 representation_id로 이전 표현/인용과 공존할 수 있다. 서로 다른 raw version의 인용을 재결합하지 않는다. 이 정책의 계약 테스트는 DB 중복 제거를 구현한 증거가 아니다.

### B2. 인용과 위치 검증

- `TextQuoteSelector`: `kind="text"`, `start`, `end`, `quote`, 선택 `prefix`, `suffix`. Python Unicode code point 기준 `[start,end)`; start>=0, end>start, quote 비어 있지 않음. context가 있으면 인접 텍스트와 정확히 일치해야 한다.
- `PdfQuoteSelector`: `kind="pdf"`, `page_number`, 동일 start/end/quote/prefix/suffix, `regions`(기본 빈 tuple). 인용 텍스트가 지정 페이지 span 안에 있어야 한다. 좌표가 없는 파싱 결과에 좌표를 만들지 않는다.
- `NormalizedBox`: `x0`, `y0`, `x1`, `y1`. 유한 int/float(단 bool/문자열 거부), [0,1], x0<x1, y0<y1. 좌표는 회전·crop 반영 후 표시 페이지의 좌상단 원점. 실제 PDF 렌더링/회전 변환은 이번 범위 밖이며 입력 좌표의 형태·범위만 확인한다.
- `TableCellSelector`: `kind="table_cell"`, `table_id`, `cell_id`, `quote`. 지정 셀이 존재하고 그 셀 text와 quote가 정확히 같아야 한다. 부분 셀 인용·통계 합산은 범위 밖이다.
- `Citation`: `citation_id`, `document_version_id`, `representation_id`, `selector` discriminated union. 각 locator는 모델로 표현한다.
- `EvidenceBundle`: `schema_version=1`, `document`, `version`, `representation`, `citations`. document→version→representation→citations의 ID 연결을 모두 확인한다. citation_id 중복을 거부하고 모든 selector의 위치/quote/context를 확인한다. 원문/파싱/인용은 변경을 자동 이동·덮어쓰지 않는다.
- 검증 함수 `validate_citation(citation, representation)`는 성공 시 `CitationAnchorValidation` (`citation_id`, `anchor_status="matched"`, `support_status="not_evaluated"`)를 반환하고 오류는 ValueError로 명확히 거부한다. 정확한 인용이 무관한 주장에 쓰였더라도 의미 지지 검증 성공으로 표시하지 않는다.
- JSON 입력 경로에서도 숫자 coercion, extra 필드, naive 시각, 비유한 좌표, 깨진 참조와 다른 버전 인용을 거부한다. Pydantic의 검증 생략 construction/model_copy(update=...)는 신뢰할 수 없는 입력 경로로 사용하지 않도록 문서화한다.

### B3. 웹 계약과 Unicode

- 앱의 OpenAPI components에 EvidenceBundle/인용 검증 결과 및 의존 스키마를 추가한다. 컴포넌트 이름 충돌을 조용히 덮어쓰지 않는다. `/openapi.json`과 export 스크립트가 같은 내용을 낸다. 기존 HTTP paths는 그대로다.
- 생성 `openapi.json`, `schema.d.ts`를 갱신하고 api-client에서 관련 생성 타입을 export한다. 별도 수기 TypeScript 계약을 복제하지 않는다.
- `getCitationUtf16Range(text, selector)`는 생성된 text/pdf selector 타입을 받아 `{start,end}` JS UTF-16 인덱스를 반환한다. code point 범위·quote·prefix/suffix를 확인하고 잘못된 입력은 throw한다. 분할은 code point이며 grapheme cluster는 아니다. table selector는 이 함수의 입력이 아니다.
- 한글, BMP 밖 이모지, 결합 문자, 선행/후행 공백을 Python과 TS에서 확인한다. 합성 UTF-8 JSON fixture를 공유해 두 언어의 offsets가 같은 인용을 선택하도록 검증한다.

### B4. 검증·기록

- pytest discovery에 domain tests를 포함하고 의미 있는 동작 테스트를 먼저 실패시킨 뒤 구현한다. RED/GREEN 명령·출력을 SDD 보고서에 보존한다.
- 테스트: 올바른 JSON round-trip, immutable nested collections, extra rejection, IDs/hash/time/strict scalar errors, parser-only revision 공존, quote/context/range/Unicode 오류, 페이지 span/box 오류, 존재하지 않는 table/cell·다른 버전 참조, 중복 IDs, 불완전 통계 조건 유지, 의미 지지 미판정.
- API/OpenAPI 테스트는 새 schema $ref가 모두 해석되며 HTTP paths가 늘지 않은 것을 확인한다. 기존 상태·요청 ID 회귀 유지. TS 실제 conversion 결과와 잘못된 input 거부 확인.
- 전체 `npm run check`, 생성 계약 drift check, 독립 task review와 전체 branch review 통과. 패키지 README, 작업 목록, 진행 기록, Sites 공개 요약에서 완료/미구현을 구분한다.

## Task 1: 원문·파싱·인용 계약과 타입 연결

- [ ] B1~B4를 하나의 변경 단위로 구현하고 검증한다.

읽을 원본: `docs/research/product-contracts.md`의 원문/인용 부분과 위 B1~B4. 기존 status 계약·API paths·웹 화면은 보존한다. `packages/domain/src/issuedigest_domain/`에 모델과 검증을, `packages/domain/tests/`에 테스트를 추가하고 domain의 공개 exports/README를 갱신한다. `apps/api/src/issuedigest_api/contracts.py`에 순수 OpenAPI 컴포넌트 등록을 분리하고 main에 연결한다. `apps/api/tests/`에 스키마 등록 검증을 추가한다. `packages/api-client/src/citations.ts`와 public exports/테스트/README를 갱신한다. 합성 공통 fixture는 `tests/fixtures/citation-unicode.json`. 생성 계약 파일과 pytest 설정을 갱신한다. `docs/planning/tasks.md`, `progress.md`, `docs/README.md`에 첫 계약 부분 완료와 후속 범위를 기록한다. Sites는 controller가 반영한다.

환경: Node 24.21.0/npm 11.19.0 (`PATH=/home/xinics/.nvm/versions/node/v24.21.0/bin:$PATH`), uv 0.11.4, 잠긴 Python 3.13.12. 새 종속성 없이 현재 설치를 사용한다. focused tests로 TDD 후 전체 check 한 번, self-review, 커밋. 한 번에 모든 테스트를 미리 만들고 import 오류만 RED로 삼지 말고 기능별 실패 동작을 확인한다.

## 후속 작업

출처 시간 정밀도·재수집 관측·내용 비교 fingerprint·실제 parser/원문 저장, 주장/관계 및 비교 조건, Run/Event/Canvas/Usage 계약과 저장·권한 검증. 다음 묶음 전까지 P1 전체를 완료로 표시하지 않는다.
