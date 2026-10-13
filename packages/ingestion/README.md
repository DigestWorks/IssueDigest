# IssueDigest 원문 후보 사전 검사

`issuedigest-ingestion`은 표준 라이브러리만 사용하는 독립 Python 패키지다.
명시한 data root의 `parsed/`와 `pdfs/`를 재귀적으로 읽고, 여론조사 JSON과 PDF의
**검증되지 않은 파일 연결 후보**를 보고한다. DB·네트워크·모델을 호출하지 않으며,
EvidenceBundle·인용·이관 데이터를 만들지 않는다. 기존 API/도메인 계약과 독립이다.

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
