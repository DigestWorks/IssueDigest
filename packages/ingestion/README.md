# IssueDigest 원문 후보 검사·PDF 페이지 텍스트

`issuedigest-ingestion`은 읽기 전용 Python 도구다. 후보 검사는 표준 라이브러리를,
PDF 추출은 고정 `pypdf==6.20.1`과 기존 workspace domain 계약을 사용한다.
명시한 data root의 `parsed/`와 `pdfs/`를 재귀적으로 읽고, 여론조사 JSON과 PDF의
**검증되지 않은 파일 연결 후보**를 보고한다. DB·네트워크·모델을 호출하지 않으며,
`audit-polls`는 EvidenceBundle·인용·이관 데이터를 만들지 않는다.
`inspect-pdf`의 추출과 아래 인용 어댑터는 기존 API/도메인 계약을 변경하지 않는다.

## 실행

저장소 루트에서 고정 Python/uv 도구를 설치한 뒤 실행한다.

```sh
uv sync --locked --all-packages
uv run --package issuedigest-ingestion issuedigest-ingestion audit-polls --data-root "$DATA_ROOT"
```

`DATA_ROOT`는 사용자가 직접 지정한다. root와 `parsed/`, `pdfs/`가 모두 실제 디렉터리여야
한다. 원문을 검사할 때는 전용 읽기 전용 mount를 사용한다. 과거 수집 경로·SSH·DB·URL에
자동 연결하지 않는다. 디렉터리 경로의 모든 구성 요소에서 symlink를 거부하며, 트리 내부의
symlink·특수 파일·지원하지 않는 확장자는 읽지 않고 별도 집계한다. Linux의
`dir_fd`, `O_NOFOLLOW`, `O_DIRECTORY`를 사용하며 Linux에서 검증했다.

기본 stdout에는 JSON 집계 한 개만 출력한다. 상세 정보가 필요하면 source root 밖의
개인 디렉터리에 **새 파일 이름**을 지정한다. 상위 디렉터리는 먼저 준비해야 한다.

```sh
uv run --package issuedigest-ingestion issuedigest-ingestion audit-polls \
  --data-root "$DATA_ROOT" --private-manifest "$PRIVATE_DIRECTORY/new-audit.json"
```

상세 파일은 mode `600`으로 exclusive 생성한다. 기존 파일·symlink를 덮어쓰지 않고,
출력 경로의 symlink 상위 디렉터리도 거부한다. root 내부 경로와 실제 디렉터리의 조상이
root인 경로를 거부하며, 저장 실패 시 자신이 생성한 부분 파일을 제거한다. 상세 manifest는
공개 Git·PR·Sites 대상이 아니다. 저장소 `output/`은 검증 산출물 제외 경로지만,
개인 manifest는 저장소 밖에 보관하는 것이 기본이다.

```python
from issuedigest_ingestion import AuditError, Limits, audit_poll_files

result = audit_poll_files(data_root, limits=Limits(max_files=10_000))
public_counts = result.summary
private_details = result.manifest
```

라이브러리는 파일을 저장하지 않는다. `AuditError`의 문자열은 아래 고정 오류 코드이며,
원본 OS 예외·파일 경로·JSON 본문을 포함하지 않는다. 공개 용도에는 `summary`만 사용한다.

## 검사 기준과 반환 경계

`parsed/`의 `.json`과 `pdfs/`의 `.pdf` 확장자를 대소문자 구분 없이 검사한다.
모든 비디렉터리 항목은 스캔 수·파일 수 한도에 포함된다. `registration_number` 키가 있는
JSON 객체를 여론조사로 인식한다. 다른 JSON 구조는 `unsupported`로 분류한다.

여론조사는 정확한 세 필드를 요구한다. 다른 필드를 추측하거나 자동 변환하지 않는다.

- `registration_number`: ASCII 숫자만 포함한 문자열, 1~32자. 공백·숫자·bool을 거부한다.
- `source_url`: `https://www.nesdc.go.kr/` 또는 `https://nesdc.go.kr/` 출처 URL.
  정확한 소문자 host와 생략된 포트 또는 `:443`만 허용한다. 자격 증명·공백·제어문자·
  역슬래시·다른 host/포트를 거부한다. URL을 요청하지 않는다.
- `pdf_path`: 비어 있지 않은 상대 POSIX 경로. 절대 경로·`..` 구성 요소·NUL·역슬래시·
  colon·빈 basename을 거부한다. JSON 경로는 파일 열기 지시가 아니며 basename만 비교한다.

동일 basename이 정확히 한 일반 PDF 파일과 연결되고 PDF 검사를 통과해야 `candidate`다.
없으면 `pdf_missing`, 여러 파일이면 `pdf_ambiguous`로 격리한다. 첫 파일을 고르지 않는다.
PDF는 첫 1,024바이트 안에 완전히 포함된 `%PDF-`가 있어야 한다. 전체 bytes의 크기와
SHA-256을 최대 64KiB 청크로 읽어 계산한다. 전체 PDF를 메모리에 적재하지 않는다.
JSON은 한도 안에서 메모리로 읽는다. 중복 JSON 키·비표준 NaN/Infinity도 잘못된 JSON이다.

파일을 발견했을 때와 열었을 때, 읽은 후의 device/inode·파일 종류·크기·mtime·ctime을
대조한다. 바뀐 JSON/PDF는 `json_changed`/`pdf_changed`로 격리한다. PDF를 한 번 읽고
여러 조사에서 참조할 수 있으므로 전체 읽기 집계는 실제 읽은 bytes 기준이다.
동일 SHA-256인 정상 PDF 그룹과 유효한 중복 등록번호 그룹을 보고하되 기록을 병합하지 않는다.
유효한 등록번호의 중복은 다른 metadata가 잘못된 조사도 포함한다.

파일명 대조는 원문 동일성의 증명이 아니다. PDF 헤더·해시는 PDF 파싱 성공·원문의 진위·
인용 정확성·보관/사용 권한을 검증하지 않는다. `candidate`는 후속 원문 대조의 입력이다.
이후 별도 작업에서 공급처의 원문·정확한 조사 대응·문서 버전·페이지/위치·인용 내용을
검증한 뒤 기존 EvidenceBundle 계약에 맞게 구성해야 한다.

## v1 공개 summary와 상세 manifest

완료 summary의 `format_version`은 `issuedigest-ingestion-summary-v1`,
`status`는 `completed`다. 공개 필드는 다음 집계와 UTC ISO 8601 관측 시각뿐이다.

| 필드 | 의미 |
| --- | --- |
| `started_at`, `completed_at` | 검사 시작·완료 시각 |
| `scanned_files` | `parsed`, `pdfs`별 비디렉터리 항목 수 |
| `candidate`, `quarantined`, `unsupported` | 읽기 대상으로 발견된 JSON별 분류 수 |
| `reasons` | JSON 분류의 고정 사유별 건수 |
| `pdf_reasons` | 참조 여부와 무관한 PDF 자체 검사 실패 건수 |
| `skipped_files`, `skipped_reasons` | 읽지 않은 입력 항목 수와 사유별 건수 |
| `duplicate_hash_groups` | 정상 PDF 파일 둘 이상이 같은 해시인 그룹 수 |
| `duplicate_registration_groups` | JSON 둘 이상이 같은 유효 등록번호인 그룹 수 |
| `bytes_read` | PDF·JSON에서 실제 읽은 총 bytes |

기본 출력에는 원문 텍스트·경로·등록번호·URL·해시가 없다.
`candidate`의 사유는 `null`; 다른 고정 사유는 다음과 같다.

| 구분 | 고정 코드 |
| --- | --- |
| JSON/metadata | `invalid_json`, `json_too_large`, `json_changed`, `invalid_registration_number`, `invalid_source_url`, `invalid_pdf_reference` |
| 원문 연결/PDF | `pdf_missing`, `pdf_ambiguous`, `pdf_too_large`, `pdf_changed`, `pdf_invalid_header` |
| 미지원 JSON | `unsupported_json` |
| 읽지 않은 항목 | `symlink`, `special_file`, `unsupported_extension` |

상세 manifest의 `format_version`은 `issuedigest-ingestion-manifest-v1`이다.
`summary`, `polls`, `pdfs`, `skipped`, `duplicate_hashes`, `duplicate_registrations`를 담는다.
`polls`에는 root 상대 JSON 경로·status·reason이 있고, metadata 검사를 통과한 경우
등록번호·출처 URL·JSON의 PDF 참조가 추가된다. candidate에는 연결한 PDF 상대 경로·
`pdf_size_bytes`·`pdf_sha256`이 추가된다. `pdfs`에는 상대 경로·검사 reason·관측 크기와
정상 파일의 해시를 담는다. `skipped`는 상대 경로와 사유, 중복 그룹은 해시/등록번호와
해당 상대 경로 목록을 담는다. 원문 텍스트와 질문 본문은 manifest에도 복제하지 않는다.

## 한도·실패·관측 시각

| 옵션 / `Limits` 필드 | 기본값 |
| --- | --- |
| `--max-files` / `max_files` | 10,000 |
| `--max-json-bytes` / `max_json_bytes` | 8MiB = 8,388,608 |
| `--max-pdf-bytes` / `max_pdf_bytes` | 128MiB = 134,217,728 |
| `--max-total-bytes` / `max_total_bytes` | 2GiB = 2,147,483,648 |

명시적으로 바꿀 수 있으며 양의 정수만 허용한다. 라이브러리의 bool·0·음수·문자열·실수는
`invalid_limits`다. 개별 파일 크기 초과는 해당 파일 격리다. 파일 수나 전체 읽기 한도
초과는 검사를 중단하며 manifest를 생성하지 않는다. 디렉터리 탐색·OS 읽기 실패도
검사 전체를 실패시킨다. 입력 교체/삭제가 확인되면 변경 사유로 격리한다.

완료 검사의 CLI exit code는 `0`이다. 잘못된 인자·root·읽기 실패·전체 한도 초과·상세
저장 실패는 exit `2`와 `{"format_version":"issuedigest-ingestion-summary-v1",
"status":"failed","error":"고정_코드"}`를 stdout에 출력한다. 오류 코드는
`invalid_arguments`, `invalid_limits`, `invalid_data_root`, `read_failed`,
`file_limit_exceeded`, `total_bytes_exceeded`, `manifest_failed`다.
실제 경로·원본 예외·본문은 stdout/stderr에 넣지 않는다.

exit `0`은 검사가 완료됐다는 뜻이며 이관 가능 판정이 아니다. 관측 시각은 운영 DB의
고정 시점 스냅샷이나 수집 최신성을 보장하지 않는다. 서로 다른 파일은 다른 순간에
읽으므로 지속적으로 변하는 원문 트리 전체의 일관된 스냅샷도 보장하지 않는다.

## 합성 검증

```sh
uv run pytest packages/ingestion/tests
npm run check
```

테스트는 임시 디렉터리의 합성 JSON/PDF·symlink·FIFO만 사용한다. 실제 원문을 Git에
추가하지 않는다. 전체 PostgreSQL 통합 검증의 전용 합성 DB 설정은 루트/저장 패키지
README를 따른다. 이 패키지의 검사 자체는 DB에 연결하지 않는다.

## 명시 PDF 추출과 정확 인용 준비

```sh
uv run --package issuedigest-ingestion issuedigest-ingestion inspect-pdf \
  --data-root "$DATA_ROOT" --pdf-path "pdfs/relative.pdf" --expected-sha256 "$EXPECTED_SHA256"
```

이 명령은 `parsed/`를 요구하지 않는다. 명시한 root의 `pdfs/` 아래 일반 파일만 읽는다.
root를 포함한 경로 구성 요소를 descriptor로 열어 symlink를 거부한다. `pdf_path`는 상대
POSIX 경로여야 하며 절대 경로·빈 구성 요소·`.`·`..`·NUL·역슬래시·특수 파일을 거부한다.
`expected_sha256`은 정확한 소문자 hex64자이며 필수다. 64KiB 이하 청크로 전체 해시와
크기를 확인하고 익명 임시 파일에 복사한다. 읽기 전후 device/inode·파일 종류·크기·mtime·ctime과
현재 경로를 대조한다. 해시 불일치·변경·첫1,024바이트 내 헤더 없음은 파싱 전에 실패한다.
부모는 전체 원문 PDF를 메모리에 적재하지 않고 파서는 확인한 snapshot만 읽는다.
읽기 완료 후 원본이 변경되어도 결과는 확인한 snapshot에 대응하며 최신 원본 상태를 보장하지 않는다.

Linux의 별도 Python 자식에서 자원 한도를 적용한 뒤 pypdf를 import한다. shell 없이 명시 FD만
전달하고 stdout/stderr·로그·경고는 버린다. wall timeout에서는 자신이 시작한 자식만 kill·회수한다.
성공·실패에 FD와 익명 임시 파일을 정리하고 자동 재시도하지 않는다. 자원 한도는 프로세스의
비용을 제한한다. OS sandbox나 파서의 모든 취약점에 대한 격리 보장은 아니다.

`strict=True`, `extraction_mode="plain"`으로 페이지 순서대로 추출한다. pypdf6.20.1의
생성자는 `password=None`이어도 빈 비밀번호를 시도하므로, 고정 버전의 암호화 처리 hook을
덮어쓴 reader로 비밀번호 검증 전에 거부한다. 빈 비밀번호로 열리는 PDF도 거부한다.
Unicode 정규화·trim·OCR·표 구조·좌표를 적용하지 않는다. 페이지 구분자는 정확히 `\n\f\n`이다.
빈/공백뿐인 페이지의 실제1-based 번호를 `empty_pages`에 남기고 그 텍스트도 보존한다.
비어 있지 않은 페이지의 `PageSpan.start/end`는 최종 텍스트의 Python code-point 범위다.
부모는 자식 JSON의 키·타입·parser 메타데이터·페이지별 텍스트 재결합·해시·페이지 번호와 구간을
다시 검증한다. 실패하거나 한도를 넘은 부분 텍스트는 완료 결과로 반환하지 않는다.

```python
from issuedigest_ingestion import (
    PdfLimits,
    extract_pdf_text,
    locate_pdf_quote,
    to_pdf_representation,
)

extraction = extract_pdf_text(
    data_root, "pdfs/relative.pdf", expected_sha256, limits=PdfLimits(max_pages=200)
)
representation = to_pdf_representation(
    extraction,
    document_version_id=document_version_id,
    representation_id=representation_id,
)
selector = locate_pdf_quote(representation, quote, page_number=page_number)
```

`PdfExtraction`과 `PdfLimits`는 frozen dataclass다. 추출 결과는 `text`, `pages`(불변 PageSpan
모델 tuple), `empty_pages`(정수 tuple), `page_count`, `raw_sha256`, `raw_bytes`, `text_sha256`,
`parser_name="pypdf"`, `parser_version="6.20.1"`, `normalization_profile="pypdf-plain-v1"`를 담는다.
어댑터는 호출자가 지정한 UUID4로 기존 `ParsedRepresentation`을 만들고 `tables=()`를 사용한다.
새 SourceDocument·DocumentVersion·EvidenceBundle·위치 좌표는 만들지 않는다.
UUID/representation 검증 실패는 기존 domain의 `ValidationError`를 따른다.

인용은 정확한 문자열이 지정한 페이지 또는 전체 텍스트에서 유일할 때만 허용한다.
겹치는 반복 매치도 중복이다. 전체 범위에서는 페이지 경계를 걸친 두 번째 매치도 중복으로 거부한다.
유일한 매치가 한 PageSpan 안에 있어야 `PdfQuoteSelector`를 반환하며 `regions=()`다.
`page_number`를 지정하면 해당 비어 있지 않은 PageSpan 안에서만 찾는다. 존재하지 않는 PageSpan
번호(빈 페이지 포함)는 거부한다. 문자열을 NFC/NFD로 바꾸거나 공백을 제거하지 않는다.
기존 `validate_citation`은 정확한 anchor `matched`를 검증하고 support는 `not_evaluated`로 남긴다.
정확한 텍스트 매치는 원문 진위·조사 대응·AI 수치/주장의 지지·표 의미를 증명하지 않는다.

## PDF 출력·한도·고정 오류

`inspect-pdf` 완료 stdout에는 다음 JSON 한 개만 출력한다(exit0).

```json
{"format_version":"issuedigest-pdf-text-summary-v1","status":"completed","page_count":3,"empty_page_count":1,"text_characters":31,"raw_bytes":2500,"source_verification":"not_evaluated"}
```

숫자는 예시다. 해시·텍스트·경로·원문 URL·등록번호·UUID는 공개 출력에 없다.
실패는 exit2와 같은 format_version의 `status="failed"`, `error="고정코드"`만 출력한다.

상세는 `--private-manifest "$PRIVATE_DIRECTORY/new-pdf-text.json"`으로만 저장한다.
기존 안전한 저장기를 사용해 root 밖 새 mode600 파일을 exclusive 생성한다. 덮어쓰기·symlink·
root 내부를 거부하고 저장 실패에서는 completed를 출력하지 않는다. 상세 형식은
`issuedigest-pdf-text-manifest-v1`이며 `summary`와 위 `extraction` 필드를 담는다.
페이지는 `page_number/start/end` 객체 목록으로 직렬화한다. 원문 bytes는 복제하지 않는다.
상세 텍스트·해시·경로는 Git·PR·Sites에 게시하지 않는다.

| CLI 옵션 / PdfLimits 필드 | 기본값 |
| --- | --- |
| `--max-pdf-bytes` / `max_pdf_bytes` | 134,217,728 (128MiB) |
| `--max-pages` / `max_pages` | 200 |
| `--max-text-characters` / `max_text_characters` | 1,000,000 code points (페이지 구분자 포함) |
| `--timeout-seconds` / `timeout_seconds` | wall30초 |
| 라이브러리만: `cpu_seconds` | CPU30초 |
| 라이브러리만: `max_address_space_bytes` | 536,870,912 (512MiB) |
| 라이브러리만: `max_output_bytes` | 16,777,216 (16MiB, 내부 자식 JSON) |

모든 한도는 양의 정수만 허용한다. bool·0·음수·문자열·실수는 거부한다.
자식 JSON에는 검증을 위한 페이지별 텍스트와 결합 텍스트가 있어 텍스트 자체보다 크다.
출력 한도도 별도로 적용하며 큰 Unicode 결과는 텍스트 한도 이전에 출력 한도를 넘을 수 있다.

| 고정 오류 | 의미 |
| --- | --- |
| `invalid_arguments`, `invalid_limits` | CLI 인자 또는 양의 정수 한도 오류 |
| `unsupported_platform` | Linux 이외 플랫폼 |
| `invalid_data_root` | root를 안전하게 열 수 없음 |
| `invalid_pdf_path`, `invalid_expected_sha256` | 입력 경로/기대 해시 형식 오류 |
| `pdf_read_failed` | 파일·디렉터리·symlink·특수 파일·임시 파일 읽기/쓰기 실패 |
| `pdf_changed`, `pdf_hash_mismatch`, `pdf_invalid_header` | snapshot 변경·기대 해시 불일치·헤더 없음 |
| `pdf_byte_limit_exceeded`, `pdf_page_limit_exceeded`, `pdf_text_limit_exceeded`, `pdf_output_limit_exceeded` | 해당 한도 초과 |
| `pdf_encrypted`, `no_extractable_text` | 암호화 또는 모든 페이지가 빈/공백 텍스트 |
| `pdf_parse_failed`, `pdf_invalid_unicode` | 손상/파서 실패 또는 유효 UTF-8로 인코딩 불가 |
| `pdf_timeout`, `pdf_worker_failed` | wall timeout 또는 자식 실행/종료 실패 (CPU/메모리 종료 포함) |
| `pdf_invalid_result` | 자식 프로토콜·타입·해시·페이지·메타데이터 검증 실패 |
| `manifest_failed` | 개인 상세 저장 실패 |
| `invalid_quote`, `invalid_page_number` | 빈/공백/유효 UTF-8이 아닌 인용 또는 대상 PageSpan 번호 오류 |
| `quote_not_found`, `quote_ambiguous`, `quote_crosses_page` | 정확 매치 없음·여러 매치·한 페이지 밖 매치 |

원본 예외·경로·PDF 내용은 고정 오류에 포함하지 않는다. 메모리 부족이 파서 내부 예외로
처리되면 `pdf_parse_failed`, import/OS 종료로 처리되면 `pdf_worker_failed`일 수 있다.

새 합성 검증은 실제 최소 PDF의 다중/빈 페이지·한글·BMP 밖 emoji·결합 문자·공백과
실제 subprocess·hash/경로/변경·암호화·페이지/텍스트/출력 한도·CPU/메모리·timeout·회수·
프로토콜 위조·공개 출력 프라이버시·개인 파일 저장·기존 audit-polls 회귀를 검사한다.
PDF fixture 생성에는 새 의존성을 추가하지 않는다. 실제 자료의 품질·OCR·표·좌표는 미검증이다.

## 제한된 인용 후보 검색·정확 문맥 선택

이미 검증한 caller-owned `ParsedRepresentation`에 `find_pdf_quote_candidates`를 호출하면
정확히 겹치는 모든 일치를 원문 code-point offset 순으로 집계한다. 자동으로 첫 후보를
선택하거나 문자열을 정규화·trim·유사 검색·순위화하지 않는다. 없는 문자열은 빈 성공 결과다.
`page_number`를 지정하면 해당 `PageSpan` 안의 quote만 조사하며 실제 페이지 번호를 유지한다.
빈 페이지 등 존재하지 않는 PageSpan 번호는 `invalid_page_number`다.

```python
from issuedigest_domain.citations import Citation, validate_citation
from issuedigest_ingestion import (
    PdfQuoteSearchLimits,
    find_pdf_quote_candidates,
    resolve_pdf_quote,
)

# representation과 quote는 호출자가 준비한 검증된 모델과 정확한 문자열이다.
result = find_pdf_quote_candidates(
    representation, quote, limits=PdfQuoteSearchLimits(max_candidates=20)
)
# 후보를 대조한 호출자가 페이지와 인접 문맥을 명시한다. 자동 선택은 제공하지 않는다.
selector = resolve_pdf_quote(
    representation,
    quote,
    page_number=selected_page_number,
    prefix=selected_prefix,
    suffix=selected_suffix,
)
citation = Citation(
    citation_id=citation_id,
    document_version_id=representation.document_version_id,
    representation_id=representation.representation_id,
    selector=selector,
)
anchor = validate_citation(citation, representation)
```

`PdfQuoteSearchResult`는 frozen dataclass다. 원본 `representation_id`, `document_version_id`,
`text_sha256`, 불변 selector tuple인 `candidates`, `occurrence_count`, `candidate_count`,
`cross_page_match_count`, `has_more`를 제공한다. `occurrence_count`는 지정 페이지 또는 전체
범위의 정확 일치 총수다. `candidate_count`는 한 PageSpan 안의 quote 총수이고,
`cross_page_match_count`는 어떤 PageSpan에도 완전히 들어가지 않는 일치 수다. 페이지 밖 gap의
일치도 이 수에 포함된다. `has_more`는 반환 수가 `candidate_count`보다 작을 때만 참이다.
반환 한도에 도달해도 끝까지 집계하며, 한도 실패는 완료된 부분 결과를 반환하지 않는다.
각 후보의 `prefix`/`suffix`는 페이지 안에서만 자른 앞뒤 최대 문맥이고 공백도 그대로 남긴다.
빈 문맥·0자 설정은 `None`, `regions=()`이며 좌표를 추측하지 않는다.

`resolve_pdf_quote`는 지정 페이지와 supplied `prefix`/`suffix`의 정확 인접 일치로 유일성을
검사한다. 문맥은 각각 `None` 또는 비어 있지 않은 유효 UTF-8 문자열이며 최대200 code points다.
공백 문맥도 유효하다. 반환 selector에는 제공한 문맥만 그대로 넣으며 미제공 문맥은 `None`이다.
조건 일치가 없으면 `quote_not_found`, 여러 개면 `quote_ambiguous`, 단일 일치의 quote 또는
제공 문맥이 한 PageSpan 밖이면 `quote_crosses_page`다. quote가 페이지를 가로지르거나,
문맥이 다른 페이지·gap을 침범해도 정확 인접 일치가 있으면 유일성 수에서 제외하지 않는다.
지정 페이지에서도 인접 문맥의 최대200자 대조는 페이지 밖 텍스트를 확인할 수 있지만,
그 경우 selector를 생성하지 않는다. 후보 반환 한도로 유일성을 추론하지 않는다.

| `PdfQuoteSearchLimits` 필드 | 기본값 | 허용 범위 |
| --- | --- | --- |
| `max_text_characters` | 1,000,000 | 양의 정수; 전체 검색은 전체 text, 페이지 지정은 해당 PageSpan 길이 |
| `max_occurrences` | 10,000 | 양의 정수; 지정 범위의 문맥 필터 적용 전 raw quote 일치 수 |
| `max_candidates` | 100 | 1..1000; 후보 검색 반환 수만 제한 |
| `context_characters` | 80 | 0..200; 후보 preview의 각 앞뒤 길이 |

한도 객체도 frozen dataclass이며 모든 값은 exact `int`다. bool·문자열·실수·범위 밖 값이나
잘못된 한도 인자는 `invalid_quote_search_limits`다. text 범위 초과는
`quote_search_text_limit_exceeded`, raw 일치 수 초과는 `quote_search_occurrence_limit_exceeded`다.
resolver는 `max_candidates`와 preview 길이로 선택을 제한하지 않으며 scan/occurrence 한도를
끝까지 적용한다. 잘못된 문맥은 `invalid_quote_context`, 인용·페이지 오류는 기존
`invalid_quote`/`invalid_page_number` 의미를 유지한다. 오류는 고정 코드만 담으며
text·quote·context·경로·ID를 포함하지 않는다. 기존 `locate_pdf_quote`와 CLI는 그대로다.

이 API는 기존 domain 검증을 통과한 caller-owned 모델을 소비한다. `model_construct`나
`model_copy(update=...)` 등 검증 우회로 만든 모델을 검증된 입력으로 취급하지 않는다.
이 모듈이 representation의 해시·페이지 계약을 새로 검증하는 신뢰 경계는 아니다.
선택 후 소비자는 위 예시처럼 기존 `validate_citation`을 호출해야 한다. `matched`는 정확한
위치 확인이고 support는 `not_evaluated`다. 검색·선택은 SourceDocument·DocumentVersion·
EvidenceBundle을 만들지 않으며 원문 진위·조사/표 대응·수치/주장 지지·geometry·OCR·제품 권한을
평가하지 않는다. 실제 후보의 quote·문맥·해시·UUID와 상세 결과는 개인 환경에만 보관하며
Git·PR·Sites에 게시하지 않는다. DB·네트워크·모델 호출이나 자동 원문 가져오기는 없다.
