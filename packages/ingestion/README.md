# IssueDigest 원문 후보 검사·PDF·공식 정책 HTML

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

## 공식 정책 HTML 추출과 정확 인용

`extract_policy_html`은 호출자가 확보한 대한민국 정책브리핑 정책뉴스 HTML `bytes`만
해석한다. 현재 관측한 템플릿과 정확히
`https://www.korea.kr/news/policyNewsView.do?newsId=<9자리 ASCII 숫자>` 형식만 지원한다.
자격증명·port·다른 호스트·추가 query·fragment·공백·역슬래시·인코딩 우회는 거부한다.
유일한 HTML head의 `og:url`은 지정 URL과 정확히 같아야 한다.

다음 예시는 기사 원문이 아닌 합성 데이터다. 저장소 루트에서
`uv run --package issuedigest-ingestion python`으로 실행할 수 있다.
UUID4는 예시 호출자가 지정한다. 함수는 파일을 읽거나 저장하지 않는다.

```python
from hashlib import sha256
from uuid import UUID

from issuedigest_domain.citations import Citation, validate_citation
from issuedigest_ingestion import (
    PolicyHtmlLimits,
    extract_policy_html,
    locate_policy_html_quote,
    to_policy_html_representation,
)

url = "https://www.korea.kr/news/policyNewsView.do?newsId=123456789"
notice = "이 자료는 텍스트에 한하여 공공누리 제1유형(출처표시)의 조건에 따라 이용할 수 있습니다."
raw = f"""<!doctype html><html><head>
<meta property="og:url" content="{url}"></head><body>
<div class="view_title"><h1>합성 정책</h1></div>
<div class="variety"><div class="info">2026.10.01
<a class="gotosite">합성부</a></div></div>
<div class="view_cont"><p>한글😀 <strong>합성 인용</strong></p></div>
<div class="kogl_wrap"><div class="type"><span>{notice}</span></div>
<div class="info">제3자 사진은 별도 허가가 필요합니다.</div></div>
</body></html>""".encode("utf-8")

# 합성 예시에서만 같은 bytes로 기대 해시를 계산한다.
# 실제 호출자는 별도로 확보·대조한 원문 해시를 전달한다.
extraction = extract_policy_html(
    raw,
    expected_sha256=sha256(raw).hexdigest(),
    canonical_url=url,
    limits=PolicyHtmlLimits(),
)
representation = to_policy_html_representation(
    extraction,
    representation_id=UUID("22222222-2222-4222-8222-222222222222"),
    document_version_id=UUID("11111111-1111-4111-8111-111111111111"),
)
selector = locate_policy_html_quote(representation, quote="😀 합성 인용")
citation = Citation(
    citation_id=UUID("33333333-3333-4333-8333-333333333333"),
    representation_id=representation.representation_id,
    document_version_id=representation.document_version_id,
    selector=selector,
)
anchor = validate_citation(citation, representation)
assert extraction.text == "한글😀 합성 인용"
assert (selector.start, selector.end) == (2, 9)
assert (anchor.anchor_status, anchor.support_status) == ("matched", "not_evaluated")
```

`raw`는 exact `bytes`이며 UTF-8 strict로 해석한다(BOM 허용). 기대 SHA-256은 소문자
hex64자여야 하고 원문 전체 bytes의 해시와 같아야 한다. 문자열·`bytearray`·빈 원문·
잘못된 UTF-8·한도 초과 입력은 거부한다. 줄바꿈이나 BOM은 해시 전에 바꾸지 않는다.

메타데이터는 유일한 `div.view_title h1` 제목, `div.variety div.info` 안의 실제
`YYYY.MM.DD` 날짜와 `a.gotosite` 부처명이다. 툴팁은 부처명에 포함하지 않는다.
발행일은 `date`이며 `og:published_time`에서 시각이나 시간대를 추정하지 않는다.
누락·중복·빈 제목/부처명·잘못된 날짜는 거부한다.

라이선스는 유일한 `div.kogl_wrap` 안의 `div.type` 직계 `span`에서 확인한다.
inline markup과 HTML 공백을 정규화한 뒤 아래 문장과 정확히 같아야 한다.
별도 `div.info`의 사진 권리 안내·정책 링크는 `license_notice`에 포함하지 않는다.
안내 중복이나 wrapper에 명시된 다른 공공누리 제2~4유형은 거부한다.
문구나 구조가 바뀌면 템플릿 대조와 명시적인 파서 버전 변경이 필요하다.

> 이 자료는 텍스트에 한하여 공공누리 제1유형(출처표시)의 조건에 따라 이용할 수 있습니다.

`license_url`은 `https://www.kogl.or.kr/info/license.do`다. URL을 방문하지 않는다.
안내는 텍스트 이용 조건이며 사진·외부 이미지·첨부물의 사용 권한으로 확대하지 않는다.
호출자는 부처명·대한민국 정책브리핑·제목·발행일·URL을 담은 `attribution`으로 출처를 표시한다.

## 정책 HTML 정규화·지원 구조·한도

유일한 `div.view_cont` 안의 `p`를 원래 순서로 추출한다.
inline 태그의 text/entity와 Unicode는 보존하며 NFC/NFD 정규화를 하지 않는다.
CRLF/CR을 LF로 해석하고 일반 HTML 연속 공백은 문단 안에서 한 space로 바꾼다.
`br`만 명시적인 newline을 만들며 각 줄의 양끝 공백을 제거한다.
빈 문단은 버리고 비어 있지 않은 문단은 `\n\n`으로 연결한다.
정규화 식별자는 `korea-policy-paragraphs-v1`이다.

본문의 `script/style/noscript/template/iframe`, `figure/figcaption`, `imageWrap`·`tooltip`
class subtree와 `img`의 alt는 제외한다. 제목·날짜·메뉴·본문 밖 AI 요약도 섞지 않는다.
URL·이미지를 가져오거나 JS·외부 본문 속 지시를 실행하지 않는다.
`p` 안에서는 일반 HTML inline 태그(a/span/strong/br/img와 문자 서식 태그)를 지원한다.
표·목록·중첩 문단·문단 안 블록/미지원 태그·`p` 밖의 의미 있는 텍스트는 거부한다.
공백과 문단만 담는 wrapper는 허용한다. 선택한 본문·메타데이터 subtree가 잘렸거나
모호하게 닫히면 거부한다. 페이지 밖 무관한 HTML 오류를 브라우저 보안 검증처럼 판정하지 않는다.

| `PolicyHtmlLimits` 필드 | 기본값 | 허용 최대 |
| --- | --- | --- |
| `max_raw_bytes` | 2MiB = 2,097,152 | 8MiB = 8,388,608 |
| `max_text_characters` | 100,000 Unicode code points | 1,000,000 |
| `max_depth` | HTML 중첩 128 | 256 |

한도는 bool·실수를 제외한 양의 exact `int`다. `None`은 기본 한도를 선택한다.
과대 원문·본문·깊이는 잘라 성공시키지 않는다. 추출 결과는 메모리에 있고 프로세스 격리는 없다.

`PolicyHtmlExtraction`과 `PolicyHtmlLimits`는 frozen dataclass다. 결과는 `source_id`(9자리 뉴스 ID),
`canonical_url`, `title`, `publisher`, `publication_date`, `attribution`, `license_notice`,
`license_url`, `text`, `raw_sha256`, `raw_bytes`(원문 byte 수), `text_sha256`을 담는다.
파서 식별자는 `parser_name="korea-policy-html"`이며 기존 앵커 metadata는 `parser_version="1"`,
두 plain span의 날짜·발행처는 `"2"`를 유지한다. 새 `"3"`은 unique `div.variety`의 직접
`div.info`(정확 class 속성만)에 두 무속성 span이 있는 관측 형태만 지원한다. 첫 span은
중첩 없는 정확 ASCII `YYYY.MM.DD` 달력 날짜, 둘째 span은 whitespace와 단일 앵커뿐이다.
앵커 속성은 정확 `class="gotosite"`와 상대
`href="/news/ministryNewsList.do?repCode=A12345"` 형태(ASCII 대문자1개·숫자5개)만 허용한다.
발행처 text와 선택적 단일 `<i class="tooltip">`의 plain text만 허용하며 tooltip은 발행처에서
제외한다. 빈 발행처·추가/중첩/숨김 metadata·중복·다른 링크는 거부한다. HTML parser version3은
AI workflow v3와 별개다. 기존1/2의 결과·직렬화·hash와 본문/정확 인용 알고리즘을 보존한다.
새 profile도 정확한 기사 URL·권리 문구 검증을 거치며 tooltip에서 이용권을 추정하지 않는다.
결과의 `limits`에는 적용한 불변 한도를 보존한다.
결과 생성과 어댑터 경계는 타입·URL/ID 대응·출처표시·라이선스·정규화·텍스트 해시·한도를 검증한다.
원문 bytes는 결과에 복제하지 않으므로, 직접 생성한 결과의 원문 해시는 형식만 검증할 수 있다.
원문 bytes와 해시의 일치는 `extract_policy_html` 호출에서 검증한다.

어댑터는 caller UUID4로 기존 `ParsedRepresentation`을 만들며 `pages=tables=()`다.
텍스트·해시·파서 식별자를 옮기고 새 ID·문서 버전·페이지·표는 만들지 않는다.
UUID4는 기존 domain이 검증한다. 어댑터는 그 `ValidationError`를 고정
`AuditError("policy_html_invalid_representation")`로 바꾸며 원래 오류의 표시를 숨긴다.
잘못된 caller ID를 오류·경고에 포함하지 않는다.

`locate_policy_html_quote`는 기존 domain과 해당 파서/정규화 계약을 다시 검증한다.
검증 우회로 만든 잘못된 객체도 거부한다. exact substring과 Unicode code-point 위치만 사용한다.
`start`가 없으면 유일한 일치에서만 성공한다. 겹치는 일치도 중복으로 센다.
명시한 `start`는 음수가 아닌 exact `int`이며 그 위치에 quote가 정확히 있어야 한다.
자동으로 위치나 문자열을 보정하지 않는다. 반환 `TextQuoteSelector.prefix/suffix`는 각 최대80
code points의 실제 인접 문자열이며, 인접 문맥이 없으면 `None`이다.
호출자는 기존 `validate_citation`을 사용한다. 위치의 `matched`와 주장의 `not_evaluated`를 구분한다.

## 정책 HTML 고정 오류와 사용 경계

`AuditError`는 다음 고정 코드만 담는다. 원문·URL·경로·quote·ID나 원본 예외를 공개 출력에 넣지 않는다.

| 고정 오류 | 의미 |
| --- | --- |
| `invalid_policy_html_raw`, `policy_html_empty_raw` | exact bytes가 아니거나 빈 원문 |
| `invalid_expected_sha256`, `policy_html_hash_mismatch` | 기대 해시 형식 또는 원문 해시 불일치 |
| `invalid_policy_html_url`, `policy_html_url_mismatch` | 지원 URL 형식 오류 또는 head og:url 불일치 |
| `invalid_policy_html_limits` | 잘못된 한도 타입·값·객체 |
| `policy_html_invalid_utf8` | strict UTF-8 디코딩 실패 |
| `policy_html_byte_limit_exceeded`, `policy_html_text_limit_exceeded`, `policy_html_depth_limit_exceeded` | 원문·본문·깊이 한도 초과 |
| `policy_html_invalid_structure`, `policy_html_empty_text` | 모호함·잘림·미지원 본문 또는 추출할 텍스트 없음 |
| `policy_html_invalid_metadata`, `policy_html_invalid_license` | 제목·날짜·부처명 또는 명시 라이선스 검증 실패 |
| `policy_html_invalid_result`, `policy_html_invalid_representation` | 결과·caller UUID4·표현 계약 검증 실패 |
| `invalid_quote`, `invalid_quote_start` | 빈/공백/잘못된 Unicode 인용 또는 잘못된 위치 |
| `quote_not_found`, `quote_ambiguous` | 정확 일치 없음 또는 여러 위치 |

URL·hash·HTML 메타데이터 검증은 출처 진위 인증이 아니다. 호출자는 수집 경로·수집 시각과
별도로 확보한 원문 해시를 대조하고 기록한다. 발행일을 수집 시각으로 취급하지 않는다.
원문 HTML은 개인 저장소의 mode600 파일로 별도 보관하고 파싱 텍스트와 구분한다.
실제 원문·상세 인용·해시·UUID를 Git·PR·Sites에 복제하지 않는다.
위치 일치는 정책 확정·인과관계·AI 주장 지지를 판정하지 않는다.

이 기능은 내부 Python 라이브러리다. HTML용 CLI·HTTP 경로·DB 저장·인증·AI 생성에는
연결하지 않았다. 기존 PDF/인용/CLI 동작은 유지한다. 한 공식 원문의 검증을 전체 코퍼스나
평가셋 완료로 표현하지 않는다. 합성 회귀 검증은 다음 명령으로 실행한다.

```sh
uv run pytest packages/ingestion/tests/test_policy_html.py
uv run pytest packages/ingestion/tests packages/domain/tests
```

## 기존 법안 기본 정보 어댑터

`parse_legacy_bill_metadata`는 호출자가 별도로 확보한 **단일 Bill 행의 JSON bytes**와
사전에 대조한 SHA-256을 받는다. 기존 수집 DB에 접속하거나 URL을 방문하지 않는다.
다음 값은 합성 예시이며 실제 수집 행을 포함하지 않는다.

```python
import json
from hashlib import sha256
from uuid import UUID

from issuedigest_ingestion import (
    locate_legacy_bill_quote,
    parse_legacy_bill_metadata,
    to_legacy_bill_representation,
)

source_id = "SYNTHETIC_42"
bill = {
    "bill_id": source_id,
    "assembly_number": 22,
    "bill_name": "합성 고등교육 법안",
    "bill_number": 2200001,
    "propose_date": "2026-03-30",
    "committee": "합성 위원회",
    "stage": None,
    "bill_result": None,
    "proposer_kind": "CONGRESSMAN",
    "bill_link": f"https://likms.assembly.go.kr/bill/billDetail.do?billId={source_id}",
}
raw = json.dumps(bill, ensure_ascii=False).encode("utf-8")
# 실제 호출자는 raw와 독립적으로 확보한 기대 해시를 전달한다.
metadata = parse_legacy_bill_metadata(raw, expected_sha256=sha256(raw).hexdigest())
representation = to_legacy_bill_representation(
    metadata,
    representation_id=UUID("22222222-2222-4222-8222-222222222222"),
    document_version_id=UUID("11111111-1111-4111-8111-111111111111"),
)
selector = locate_legacy_bill_quote(representation, quote="고등교육 법안")
```

입력은 최대 64KiB의 strict UTF-8 JSON 객체다. 위 열 개 key는 모두 필수이고 다른 key,
중복 key, 비표준 숫자, 잘못된 UTF-8, 빈 문자열, 제어문자와 줄바꿈을 거부한다.
`committee`, `stage`, `bill_result`, `proposer_kind`만 `null`을 허용한다.
ID는 ASCII 영숫자/underscore 1~255자, 법안명과 nullable 문구는 1~255자다.
대수는 1~99 정수, 의안번호는 대수와 앞 두 자리가 일치하는 7자리 양의 정수다.
제안일은 실제 `YYYY-MM-DD` 날짜이며 발의구분은 `CHAIRMAN`, `CONGRESSMAN`,
`GOVERNMENT` 중 하나다. 공식 링크는 정확히
`https://likms.assembly.go.kr/bill/billDetail.do?billId=<bill_id>` 형식이어야 한다.

결과는 원천 ID·공식 링크·대수·의안번호·제안일 등 검증된 메타데이터와 원본 bytes의
해시/길이, 렌더링 텍스트의 해시를 보존한다. 첫 줄은 법안명, 둘째 줄은 기본 정보이며
전문이나 현재 상태가 아니라는 안내다. 나머지 줄은 대수, 의안번호, 제안일, 위원회,
수집 당시 단계·처리결과, 발의구분 순이다. `null`은 “미수집”이며 발의구분 enum은
“위원장 제안”/“의원 발의”/“정부 제출”로 표시하되 결과 객체에는 원래 enum을 보존한다.
정규화 식별자는 `legacy-bill-metadata-v1`, 파서는 `legacy-bill-metadata` 버전 `1`이다.
표현에는 실제 페이지나 표를 만들지 않는다. quote 위치는 Python Unicode code-point
기준이며 중복 위치에는 명시 `start`가 필요하다. 기존 `Citation`과
`validate_citation`으로 exact anchor를 확인할 수 있다.

오류는 원본 값·경로·원래 예외를 담지 않는 고정 `AuditError` 코드다:
`legacy_bill_invalid_raw`, `invalid_expected_sha256`, `legacy_bill_hash_mismatch`,
`legacy_bill_byte_limit_exceeded`, `legacy_bill_invalid_json`,
`legacy_bill_invalid_metadata`, `legacy_bill_invalid_url`, `legacy_bill_invalid_result`,
`legacy_bill_invalid_representation`, `invalid_quote`, `invalid_quote_start`,
`quote_not_found`, `quote_ambiguous`.

이 텍스트는 기존 수집 DB의 **법안 기본 정보**를 내부 조사에 이용하기 위한 렌더링이다.
표시할 때 국회 의안정보시스템의 공식 링크, 원천 ID, 수집 시각을 함께 남기고 현재
처리 상태는 공식 출처에서 다시 확인한다. 원문 전문이나 AI 요약·현재 상태의 검증으로
해석하지 않는다. PDF와 민간 본문 이용 권한으로 확대하지 않는다. 원본 JSON과 실제
해시·ID는 개인 보관 영역에 두며 Git/PR/Sites에 넣지 않는다.

```sh
uv run pytest packages/ingestion/tests/test_legacy_bill.py
```

## 로컬 HWPX 본문·표·정확 인용

`extract_hwpx`는 별도로 획득한 exact `bytes`와 기대 SHA-256만 받는다. 파일·URL을
열거나 ZIP을 디스크에 풀지 않는다. 호출자는 원문 게시물의 출처·수집 시각·이용 조건과
원문 해시를 따로 확보해야 한다. HWPX 확장자·파싱 성공은 첨부 이용 권한의 증명이 아니다.
이 기능은 Python 라이브러리이며 CLI·worker·HTTP·DB·AI 생성에 연결하지 않았다.

```python
from issuedigest_ingestion import (
    HwpxLimits,
    extract_hwpx,
    to_hwpx_representation,
    locate_hwpx_quote,
    locate_hwpx_cell,
)

extraction = extract_hwpx(
    snapshot_bytes, expected_sha256=expected_sha256, limits=HwpxLimits(max_sections=32)
)
representation = to_hwpx_representation(
    extraction,
    representation_id=representation_id,
    document_version_id=document_version_id,
)
text_selector = locate_hwpx_quote(representation, quote=exact_quote)
first_table = representation.tables[0]
cell_selector = locate_hwpx_cell(
    representation,
    table_id=first_table.table_id,
    cell_id=first_table.cells[0].cell_id,
)
# 기존 Citation과 validate_citation을 사용한다.
# 정확 anchor는 matched, 주장 지지는 not_evaluated다.
```

위 변수는 호출자가 제공한다. UUID는 exact `UUID` 객체인 UUID4여야 한다. 인용 문자열은
원문과 정확히 같아야 하며, 반복·겹치는 매치에는 명시 `start`가 필요하다. `start/end`는
Python Unicode code-point 범위다. 셀 인용은 빈 셀을 포함한 완전한 셀 텍스트를 선택한다.
다른 파서 표현·변조된 해시·무효 ID·범위·추정 셀 메타데이터는 어댑터 경계에서 거부한다.

정규화는 `hwpx-flow-v1`, 파서는 `hwpx`, 버전은 `1`이다. XML 자체의 표준 줄바꿈 처리
외에는 Unicode NFC/NFD·trim·공백 정규화를 하지 않는다. 문단의 run/t 문자열과 inline
`lineBreak`, `tab`, `nbSpace`, `fwSpace`를 보존한다. 비어 있지 않은 본문 조각은 `\n`,
구역은 `\n\f\n`으로 연결한다. 문단 속 표 앞·뒤 텍스트는 각각 별도 조각으로 남긴다.
구역은 파일명 정렬이 아니라 `Contents/content.hpf`의 OPF manifest/spine 순서다.
manifest href는 패키지 루트 경로를 우선 사용하며, 정확한 루트 멤버가 없을 때만
`Contents/` 상대 경로를 사용한다. `linear="no"` 항목은 본문으로 읽지 않는다.
`linear`가 생략된 공식 `Contents/header.xml`과 `settings.xml`/`Contents/settings.xml`도
각각 정확한 head/app namespace·root를 확인해 제외한다. 본문 root는 section namespace의
`sec`만 지원하며, 문단·표 요소는 paragraph namespace를 요구한다.

`HwpxExtraction`은 frozen dataclass이며 `text`, `raw_sha256`, `raw_bytes`, `text_sha256`,
`sections`, `spans`, `tables`, 적용한 `limits`와 파서 식별자를 담는다. 모든 컨테이너는 tuple이다.
`HwpxSection(section_index, member_name, start, end)`는 spine의 실제 본문 구역이다.
`HwpxTextSpan(start, end, section_index, table_id, cell_id)`는 출력에 한 번만 기록된
문단/셀 조각이다. 본문 문단의 table/cell IDs는 `None`이다.

`HwpxTable`은 `table_id`, `section_index`, `row_count`, `column_count`,
`parent_cell_id`, `start/end`, `cells`를 담는다. table 범위는 내부의 중첩 표를 포함하며
첫 조각 앞 구분자도 포함할 수 있다. `HwpxCell`은 `cell_id`, 0-based `row/column`,
`row_span/column_span`, 원문 `text`, 소유한 `HwpxSpan(start, end)` tuple을 담는다.
ID는 구역/표 등장 순서와 셀 주소로 결정한다(`s0-t0`, `s0-t0-r0-c0`). 중첩 표는
별도 table ID와 `parent_cell_id`를 가진다. 바깥 셀 text/spans는 중첩 표의 셀 텍스트를
중복 포함하지 않는다. 단위·기간 문구는 셀 원문에 남기며 `TableCell.unit/period`를
추론해 채우지 않는다. 표 의미·수치 합산·수혜 대상 판정은 후속 검토다.

지원 본문은 `sec` 직계 문단/표, `p/run/t`, run 안의 표·ctrl, 표의 `tr/tc`, 셀의
유일한 `cellAddr/cellSpan/subList`와 subList 안의 문단/표다. 행의 XML 순서와 cellAddr의
행 번호가 같고 셀 주소가 행·열 순서여야 한다. 병합 셀은 격자 안에 있어야 하며 중복·빈
격자 위치를 거부한다. 합법적인 빈/그림 셀은 text `""`, spans `()`로 유지한다.
레이아웃 속성(sz/pos/margin/cellzone 등)은 텍스트로 읽지 않는다. 그림·도형·수식·차트·
비디오·각주/미주·shapeComment·머리/꼬리·secPr/colPr·페이지 번호/줄 레이아웃·
필드/책갈피 제어 subtree는 본문으로 승격하지 않는다. 그 안의 drawText/이미지 문자는
지원 대상이 아니다. 프리뷰·script·외부 참조를 실행하거나 가져오지 않는다.
본문의 다른 요소·누락된 필수 구조·다른 namespace는 고정 오류로 거부한다.
전체 KS X 6101 검증기·페이지 렌더러·OCR·HWP 바이너리 파서는 아니다.

| `HwpxLimits` | 기본값 | 허용 최대 |
| --- | --- | --- |
| `max_raw_bytes` | 16MiB | 64MiB |
| `max_member_bytes` | 8MiB | 16MiB |
| `max_total_bytes` | 32MiB | 64MiB |
| `max_members` | 512 | 2,048 |
| `max_sections` | 64 | 256 |
| `max_nodes` | 100,000 | 200,000 |
| `max_depth` | 128 | 256 |
| `max_text_characters` | 1,000,000 | 1,000,000 |
| `max_tables` | 1,000 | 2,000 |
| `max_cells` | 20,000 | 40,000 |
| `max_grid_slots` | 100,000 | 200,000 |

한도는 bool을 제외한 양의 exact int다. `None`은 기본 한도다. 원문 bytes를 먼저 제한하고
ZIP central-directory의 실제 항목 수를 확인한 뒤 ZipFile을 생성한다. 모든 멤버의
선언된 압축 해제 크기/합계와 경로·중복·암호화·압축 방식을 검사한다. CRC/stream 검사는
본문이 아닌 멤버도 64KiB 청크로 읽어 수행하며, 본문 XML만 한도 안에서 메모리에 보관한다.
저장/deflate만 지원하고 ZIP64 종료 디렉터리 형식·분할 ZIP·암호화 ZIP과 META-INF의
encryption-data/encrypted-key를 거부한다. ZIP64 로컬 멤버 헤더는 기존 원문/멤버/합계 크기와
항목 수 한도 및 CRC/stream 검사를 통과하면 허용한다. DTD·ENTITY·processing instruction·외부 XML 참조는 거부한다. XML 노드/깊이는
트리에 추가하기 전에, 텍스트는 결합하기 전에 검사한다. 격자 한도는 모든 표의
row_count × column_count 합계이며, 점유 좌표를 만들거나 병합 범위를 순회하기 전에 검사한다.
미완료·부분·잘린 결과는 성공으로 반환하지 않는다. 프로세스 격리는 제공하지 않는다.

추출 결과와 caller 표현을 다시 검증한다. 원문 bytes를 결과에 복제하지 않으므로 직접
생성한 결과의 raw hash는 형식만 검증한다. 원문 hash 일치는 `extract_hwpx`에서 확인한다.
기존 ParsedRepresentation에 pages `()`와 표/셀 ID·텍스트만 옮긴다. 실제 페이지 좌표와
새 문서/버전 ID를 만들지 않는다. 결과의 자체 일관성 검사는 원문 진위나 라이선스 판정이 아니다.

오류는 입력·경로·원문·인용·ID나 원본 예외를 포함하지 않는 고정 `AuditError`다.
코드는 `hwpx_invalid_raw`, `invalid_expected_sha256`, `hwpx_hash_mismatch`,
`hwpx_invalid_limits`, `hwpx_invalid_package`, `hwpx_invalid_xml`, `hwpx_invalid_structure`,
`hwpx_encrypted`, `hwpx_empty_text`, `hwpx_invalid_result`, `hwpx_invalid_representation`,
`hwpx_invalid_cell_selector`, `hwpx_cell_not_found`, `invalid_quote`, `invalid_quote_start`,
`quote_not_found`, `quote_ambiguous`와 `hwpx_{raw_byte/member_byte/total_byte/member/section/node/
 depth/text/table/cell/grid}_limit_exceeded`다. 공개 출력에는 고정 코드/집계만 사용하고
실제 원문·개별 hash·UUID·전체 인용은 개인 저장소에만 보관한다.

합성 ZIP/XML·Unicode·병합/중첩 표와 악성 입력 회귀 검증:

```sh
uv run pytest packages/ingestion/tests/test_hwpx.py
uv run pytest packages/ingestion/tests
uv run ruff check packages/ingestion/src packages/ingestion/tests/test_hwpx.py
uv run ruff format --check packages/ingestion/src packages/ingestion/tests/test_hwpx.py
uv run mypy packages/ingestion/src
```

## 공식 법령 HTML

`extract_legal_html(raw, canonical_url)`은 이미 확보한 국가법령정보센터 `lsInfoR.do` 본문을 오프라인으로 추출한다. URL의 법령 버전·시행일과 원문 메타데이터·표시 헤더를 대조하며, 조문과 부칙을 함께 보존한다. 숨겨진 법령 문단·시행일 예외가 있으면 불완전한 원문으로 처리하고 거부한다. 메뉴·연락처·스크립트·입력 컨트롤은 본문에 넣지 않는다.

```python
from issuedigest_ingestion import extract_legal_html

extracted = extract_legal_html(raw_bytes, canonical_url)
# extracted.text, raw_sha256, text_sha256, parser provenance
```

이 함수는 네트워크·DB·모델을 호출하지 않으며 최신 법령 조회나 개별 조항의 현재 효력을 판정하지 않는다. `LegalHtmlLimits`로 원본/텍스트 크기·깊이·노드 수를 제한한다. 반환된 전체 표현과 AI 입력에 선택한 정확 인용 범위는 별개다. 기존 EvidenceBundle·인용·등록 계약을 사용하며 공개 게시를 수행하지 않는다.
