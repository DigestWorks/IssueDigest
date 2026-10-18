# Worker

`issuedigest-worker`는 운영자가 이미 확보한 private HWPX 파일에서 정확 본문·셀 인용을 준비하고 기존 `ProvisioningPlan`에 snapshot을 추가한다. 이 준비 SDK와 CLI는 DB·네트워크·공급자·모델 호출 없이 실행한다. 별도 `issuedigest-research-worker`는 아래의 명시적 DBOS 조사 실행을 담당한다.

## 설치·검증

저장소 루트에서 고정 workspace 의존성을 설치한다. HWPX 준비 경로 자체에는 새 외부 의존성이 없다.

```sh
uv sync --locked --all-packages
uv run pytest apps/worker/tests
uv run ruff check apps/worker
uv run ruff format --check apps/worker
uv run mypy
```

## Private job 입력

유한 UTF-8 JSON 객체에 `schema_version: 1`, `sources`(1~10개)를 명시한다. job/base JSON 각각 최대 8 MiB다. 중복 JSON key·비유한 수·추가 필드·형식 변환을 거부한다. 각 source의 필드는 다음과 같다.

| 필드 | 값 |
| --- | --- |
| `raw_path` | 이미 확보한 HWPX 원문 파일의 절대 경로 |
| `document` | 기존 `SourceDocument`: document/workspace UUID4, provider, source_id, source_kind=`government_document`, canonical HTTPS URL |
| `version` | 기존 `DocumentVersion`: version/document/raw_object UUID4, raw SHA-256, media_type=`application/hwp+zip`, 명시한 timezone 포함 collected_at |
| `representation_id`, `snapshot_id` | 호출자가 고정한 UUID4. 출력 준비에서 ID를 생성하지 않는다. |
| `license` | `license_type: "public_nuri_type_1"`, `text_only: true`, `operator_approved: true`, `evidence_url`: canonical URL의 정규화된 문자열과 정확히 같은 HTTPS URL |
| `citations` | 1~100개. 텍스트는 `{kind:"text", citation_id:UUID4, quote:정확문자열, start?:Unicode문자위치}`. 셀은 `{kind:"table_cell", citation_id:UUID4, table_id, cell_id}` |

job 전체 인용은 최대 200개, quote는 최대 100,000 Unicode 문자다. 반복 텍스트는 정확한 `start`가 필요하다. `table_id`/`cell_id`는 기존 HWPX 파서의 안정 위치 ID를 명시한다. 실제 원문의 ID·인용·해시·경로·계정은 저장소 밖 private 파일에만 둔다. 원문에서 발행처·게시 시각·페이지·단위·이용권을 추정하지 않는다. 이용 확인은 운영자 형식·동의 확인이며 홈페이지 진위나 라이선스 자동 검증이 아니다. anchor 검증의 주장 지지 상태는 `not_evaluated`다.

원문은 사용자 소유 regular file, 권한 400/600만 읽는다. 계획 입력도 같은 원칙을 따른다. 경로의 모든 부모·파일 symlink, FIFO·디렉터리·다른 소유자·공개 모드·크기/해시 불일치·읽기 중 변경/교체를 거부한다. 원문당 16 MiB, job 전체 raw 32 MiB·텍스트 1,000,000 문자·셀 20,000개를 제한한다. XML 해제 크기 예산 32 MiB는 source 수로 균등 분배하며 기존 파서의 ZIP/XML/node/depth/grid 한도를 유지한다. 결과는 기존 계획의 최대 50 snapshot·8 MiB 범위 내에서 재검증한다.

## 준비·기존 등록 도구 연결

출력은 기존 파일을 덮어쓰지 않는 새 절대 경로를 사용한다. 출력 부모 디렉터리는 사용자 소유 700이어야 한다. 완성된 600 artifact를 같은 디렉터리에서 원자적·배타적으로 게시한다. 실패하면 부분 출력·임시 파일을 정리하며 입력·기존 출력은 보존한다. 성공은 집계 JSON, 실패/잘못된 인수는 고정 메시지만 출력한다. exit code는 0=준비 성공, 1=준비 실패, 2=인수 오류다.

아래 경로는 모두 운영자가 지정한 개인 파일 경로다.

```sh
uv run issuedigest-prepare-hwpx PRIVATE_JOB_PLAN PRIVATE_BASE_PLAN PRIVATE_OUTPUT_PLAN
uv run python -m issuedigest_storage.provision_cli PRIVATE_OUTPUT_PLAN
```

첫 명령은 artifact를 준비하고 두 번째 명령은 기존 도구의 오프라인 검사를 수행한다. 기존 `expected_database`·workspace·승인 invites와 snapshot 순서·내용은 보존한다. 동일 snapshot은 중복 추가하지 않는다. 기존/신규 문서·버전·표현·인용 ID가 다른 내용에 재사용되면 거부한다. 별개 snapshot의 동일한 문서/버전/표현 참조 공유는 허용한다.

전용 DB 설정·백업·적용 권한이 별도로 준비된 뒤 기존 도구에서 명시적으로 검사/등록한다. 아래 명령은 실제 DB에 접근하며 이번 worker 준비 경로는 실행하지 않는다.

```sh
uv run python -m issuedigest_storage.provision_cli PRIVATE_OUTPUT_PLAN --check-database
uv run python -m issuedigest_storage.provision_cli PRIVATE_OUTPUT_PLAN --apply
```

DB URL 검증·초대 상태·원자 등록·outbox·반복 등록 계약은 [저장 패키지](../../packages/storage/README.md)의 기존 도구가 맡는다. worker가 SQL·권한 검사·마이그레이션을 복제하지 않는다.

## Typed SDK

`parse_job(raw: str | bytes) -> HwpxJob`과 `prepare_hwpx_plan(job: HwpxJob, base: ProvisioningPlan) -> ProvisioningPlan`을 제공한다. SDK는 전체 직렬화와 파일 읽기 전에 두 입력 모델의 개수·깊이(최대 32)·순환 참조·문자열과 전체 escaped UTF-8 JSON 8 MiB 예산을 검사한다. 공유 객체도 출현마다 바이트를 계산하고, 숫자 필드는 유한 float 또는 64-bit 범위의 int만 직렬화한다. 이어서 불변 모델도 매 호출 JSON으로 재검증하므로 `model_construct`/`model_copy` 우회 입력은 거부한다. 오류는 `PreparationError`의 고정 안전 메시지다. 반환 모델은 private 자료이므로 내용·repr·traceback을 공개 로그에 기록하지 않는다.

```python
from issuedigest_storage.provisioning import ProvisioningPlan
from issuedigest_worker import HwpxJob, prepare_hwpx_plan


def prepare(job: HwpxJob, approved_base: ProvisioningPlan) -> ProvisioningPlan:
    return prepare_hwpx_plan(job, approved_base)
```

공개 테스트는 합성 ZIP/XML·계정·자료만 사용한다. HWPX 경로의 HTTP 수집·원문 객체 보관·정기 수집·검색·AI·공동 DB 실사용은 후속이다. 작업 범위는 [HWPX 수집 명세](../../docs/changes/hwpx-import.md)를 따른다.


## 정책뉴스를 확인하고 비공개 등록 계획을 준비하기

`issuedigest-policy`는 운영자가 명시 실행하는 `discover` → `capture` → `compare`/`prepare` 명령이다. 발견은 고정 HTTPS 주소 `https://www.korea.kr/news/policyNewsList.do`의 첫 페이지 결과 영역만 읽는다. 확보는 정확한 `https://www.korea.kr/news/policyNewsView.do?newsId=<9자리 ASCII 숫자>` 기사1~2개만 읽는다. 목록의 제목·날짜·순서는 발견 메타데이터이며 근거·인기·사실 판정에 쓰지 않는다. RSS·다른 도메인·redirect·추적 query·인증·JavaScript를 따라가지 않는다.

### 발견하고 기사1~2개를 명시 확보하기

입력은 현재 사용자 소유의 절대 경로 정규 파일이며 권한은 `0400` 또는 `0600`이어야 한다. 모든 부모와 파일의 symlink를 거부한다. 출력 부모는 현재 사용자 소유 `0700` 디렉터리여야 하며 미리 준비한다. 각 출력에는 아직 없는 새 절대 경로를 지정한다. CLI는 요청 전에 출력 경로를 확인하고 완성된 `0600` 파일을 배타적으로 게시한다. 기존 파일을 덮어쓰지 않으며 실패 시 입력·기존 출력을 보존한다.

다음 경로·시각·기사 ID `123456789`는 합성 구문 예시다. 운영할 때는 개인 경로와 명시한 실제 수집 시각, discovery에서 직접 선택한 ID로 바꾼다. 예시 ID가 discovery에 없으면 capture는 요청 전에 실패한다.

```sh
uv run issuedigest-policy discover 2026-10-18T00:00:00Z /absolute/private/policy/discovery.json
uv run issuedigest-policy capture /absolute/private/policy/discovery.json 2026-10-18T00:01:00Z /absolute/private/policy/capture.json 123456789
```

1. `discover`가 저장한 `PolicyDiscovery`를 비공개로 확인한다. SDK에서는 `parse_policy_discovery(raw)`와 `policy_candidates(discovery)`로 후보의 `news_id`, `canonical_url`, `title`을 읽는다.
2. 선택한 서로 다른 ID1~2개를 `capture`의 마지막 인수로 직접 지정한다. 두 기사는 ID 인수를 하나 더 붙인다. URL이나 중복 ID, 후보에 없는 ID,3개 이상을 지정하면 거부한다. 수집 시각은 timezone이 있는 ISO datetime이어야 한다.
3. `PolicyCapture`의 `articles`에 저장된 기사별 HTML과 정확 canonical URL을 확인한다. HTTP 응답은 요청당20초·2MiB, 재시도0이며 TLS 검증·UTF-8 HTML·identity encoding만 허용한다. 발견은 GET1회, 확보는 선택 기사 수만큼 GET한다. 환경 proxy·인증·cookie를 전달하지 않는다.

Discovery artifact는 최대 `MAX_POLICY_DISCOVERY_BYTES = 4 * 1024 * 1024 + 8192`, capture는 `MAX_POLICY_CAPTURE_BYTES = 8 * 1024 * 1024 + 16384`바이트다. 각각 `schema_version=1`, aware `collected_at`과 `list_html` 또는 `articles[{news_id, canonical_url, html}]`을 담는다. `serialize_policy_discovery`·`serialize_policy_capture`가 만든 정확한 UTF-8 JSON bytes를 보관한다. SDK의 `discover_policy(*, collected_at, transport=None)`·`capture_policy(news_ids: tuple[str, ...], *, collected_at, transport=None)`는 파일을 쓰지 않는다. CLI와 달리 `capture_policy` 자체에는 discovery 대조 인수가 없으므로 SDK 호출자는 후보 선택을 직접 확인해야 한다.

### 기사별 텍스트 이용 조건을 검토하고 PolicyJob 작성하기

모든 확보 기사의 정확한 공공누리 제1유형 텍스트 조건, 출처/발행처·제목·발행일·본문과 사진/외부 저작물 제외를 사람이 확인한다. 파서 통과는 사람의 권리 검토를 대신하지 않는다. 사진·이미지·외부 저작물을 인용하지 않는다. 준비는 기존 `extract_policy_html`로 조건과 본문을 다시 검증하며 다른 공공누리 유형이나 본문/해시 불일치를 거부한다.

승인한 `PolicyJob`을 별도 private UTF-8 JSON 파일에 작성한다. job은 최대 `131072`바이트이며 중복 key·비유한 수·추가 필드·타입 변환을 거부한다. 다음 필드를 모두 제공한다.

| 위치·필드 | 형식과 확인 기준 |
| --- | --- |
| `schema_version` | 정수 `1`. boolean이나 문자열은 허용하지 않는다. |
| `capture_sha256` | **capture 파일 전체의 원래 bytes**에 대한 SHA-256. 공백·키 순서를 바꿔 재직렬화한 JSON의 hash로 대체하지 않는다. |
| `collected_at` | capture의 수집 시각과 일치하는 aware ISO datetime. 기사 발행일을 넣지 않는다. |
| `sources` |1~2개 `PolicySource`. capture의 `articles`와 정확히 같은 `news_id` 집합이어야 한다. |
| `sources[].news_id` |9자리 ASCII 숫자 문자열. canonical URL은 `policy_url(news_id)`로 고정된다. |
| `sources[].article_sha256` | 해당 `article.html.encode("utf-8")` bytes의 SHA-256. capture 전체 hash와 구분한다. |
| `sources[].text_sha256` | 위 기사 bytes를 `extract_policy_html(raw, expected_sha256=article_sha256, canonical_url=policy_url(news_id))`로 추출한 `text_sha256`. 제목·목록·원시 HTML hash로 대신하지 않는다. 세 hash는 모두 소문자16진수64자리다. |
| `sources[].photos_and_external_works_excluded` | 검토를 마친 경우에만 `true`. |
| `sources[].license` | `{ "license_type": "public_nuri_type_1", "text_only": true, "operator_approved": true, "evidence_url": "https://www.korea.kr/news/policyNewsView.do?newsId=123456789" }`. URL의 합성 ID를 해당 기사 ID로 바꾸며 정확히 일치해야 한다. |
| `sources[].document_id`, `version_id`, `raw_object_id`, `representation_id`, `snapshot_id` | 운영자가 고정한 UUID4. 각 ID 필드의 값은 job의 source 사이에서 중복되지 않아야 한다. 준비가 새 ID를 생성하지 않는다. |
| `sources[].citations` | 기사당1~10개 `PolicyQuote`: `{ "citation_id": "00000000-0000-4000-8000-000000000001", "quote": "합성 검토 문구", "start": 0 }`. 예시 UUID/문구를 검토한 값으로 바꾼다. `citation_id`는 job 전체에서 고유한 UUID4다. `quote`는 비어 있지 않은 정확한 추출 본문1~2000 Unicode 문자다. `start`는 생략/null 또는0~100000 정수이며 UTF-16/UTF-8 위치가 아닌 Unicode code point 위치다. 반복 문구는 정확한 `start`를 지정한다. |

capture에 승인하지 않은 기사가 있으면 `sources`에서 그 기사만 빼서 준비할 수 없다. 승인할 기사만 새 capture로 명시 확보하고 새 artifact·수집 시각·세 hash를 다시 확인한다. 본문·수집 내용이 바뀌면 새 명시 버전으로 검토한다. 같은 기사 문서 ID를 유지할 수 있지만 version/raw/representation/snapshot/citation ID를 새로 고정하며 과거 자료·결과는 덮어쓰지 않는다.

### 계획과 표시 제목을 오프라인으로 준비하고 명시 등록하기

기존 승인 base plan과 job·capture를 지정한다. 다음 두 명령은 네트워크·DB·모델을 호출하지 않으며 서로 다른 새 출력 파일을 만든다.

```sh
uv run issuedigest-policy prepare /absolute/private/policy/job.json /absolute/private/policy/capture.json /absolute/private/policy/base.json /absolute/private/policy/prepared-plan.json
uv run issuedigest-policy prepare /absolute/private/policy/job.json /absolute/private/policy/capture.json /absolute/private/policy/base.json /absolute/private/policy/presentations.json --output-kind presentations
```

기본 `--output-kind plan`은 기존 `ProvisioningPlan`에 snapshot을 append한 JSON이다. base의 `expected_database`, workspace, 승인 invites와 기존 snapshot을 보존한다. 동일 artifact/job/IDs로 재준비하면 같은 계획이며 내용이 다른 ID 재사용은 거부한다. 다만 CLI 출력 경로는 재실행 때도 새 이름이어야 한다. 결과는 기존 plan의 최대50 snapshots·8MiB 한도로 재검증한다.

`--output-kind presentations`는 추가 기사의 `SourcePresentation` JSON 배열이다. 제목은 목록/job이 아닌 각 기사의 검증한 본문 메타데이터에서 가져오며 profile은 `policy-html-v1`이다. `bill_number`·`proposed_on`은 null이고 기사 발행일을 법안 제안일로 넣지 않는다. `DocumentVersion.raw_sha256`는 capture 전체 hash, media type은 `application/vnd.issuedigest.policy-capture+json`이다. 정확한 quote 위치 검증의 support는 `not_evaluated`이며 사실 검증이 아니다.

동일한 오프라인 준비를 SDK에서 호출할 수 있다.

```python
from issuedigest_storage.provisioning import parse_plan
from issuedigest_worker import PreparedPolicy, parse_policy_job, prepare_policy_plan


def prepare_approved_policy(
    approved_job_raw: bytes, capture_raw: bytes, approved_base_raw: bytes
) -> PreparedPolicy:
    return prepare_policy_plan(
        parse_policy_job(approved_job_raw), capture_raw, parse_plan(approved_base_raw)
    )
```

반환값의 `plan`과 `presentations`는 private 자료다. CLI는 성공 때 집계 JSON만 출력하고 exit0으로 끝난다. 실패는 `Unable to complete policy operation`/exit1, 인수 오류는 `Invalid policy arguments`/exit2다. 경로·기사 ID·HTML·인용·job·hash·원시 예외를 공개 로그나 Git/PR/Sites에 기록하지 않는다.

준비 후에는 기존 [비공개 등록 CLI](../../packages/storage/README.md#비공개-작업-공간-등록-cli)의 오프라인 검증 → 대상 DB 검사 → 명시 `--apply` → 같은 계획 반복 확인을 따른다. 필요한 DB/백업/권한은 그 절차에서 따로 확인한다. 등록 뒤 새 snapshot마다 기존 [`EvidenceRepository.rebuild_projection`](../../packages/storage/README.md#명시적-문자-검색-투영보호-sdk)을 명시 호출하고, 준비한 제목은 기존 [`ResearchRepository.upsert_presentation`](../../packages/storage/README.md#조사-저장)으로 저장한다. 새 DB write CLI나 자동 outbox 소비를 추가하지 않는다.

수집·준비·등록은 공개 게시가 아니다. D020의 별도 [전체 내용/권리·계획 hash 검토와 공개 게시](../../packages/storage/README.md#검토한-공개-브리핑)를 그대로 거쳐야 한다. 이 경로를 import/startup·공개 GET·로그인 복원·질문 시 자동 수집에 연결하지 않는다. 전체 웹 탐색·정기 수집·최신/인기 선정이나 자동 게시를 제공하지 않는다.

### 확보한 capture의 변경 비교

`compare`는 이미 확보한 정확 capture bytes만 읽는 오프라인 명령이다. 네트워크·모델·DB를 호출하지 않는다. 첫 비교에서는 `--previous`를 생략하고, 다음 비교에서는 운영자가 이전 capture를 명시한다. 아래 모든 경로는 새 출력이 있는 개인 절대 경로의 구문 예시다.

```sh
uv run issuedigest-policy compare /absolute/private/policy/current.json /absolute/private/policy/first-report.json
uv run issuedigest-policy compare /absolute/private/policy/current.json /absolute/private/policy/change-report.json --previous /absolute/private/policy/previous.json
```

SDK는 `issuedigest_worker.policy_changes.compare_policy_captures(current_raw: bytes, *, previous_raw: bytes | None = None) -> PolicyChangeReport`다. 두 capture의 기존 JSON·개수·식별자·URL·시각 검증과 모든 기사의 HTML SHA·본문·이용 조건 검증을 다시 수행한다. 이전보다 오래된 수집 시각은 거부한다. 같은 instant의 서로 다른 bytes도 거부하며, 정확 동일 bytes는 허용한다. 어느 쪽 기사라도 검증이 실패하면 비교 전체가 실패한다.

| 상태 | 판단 |
| --- | --- |
| `new` | 이전 capture가 없거나 해당 기사가 이전에 없음 |
| `unchanged` | 같은 source ID의 검증된 의미 필드가 모두 같음 |
| `changed` | 같은 source ID의 검증된 의미 필드가 달라짐 |
| `not_observed` | 이전 capture에만 있음. 삭제·철회로 해석하지 않음 |

의미 필드는 `text_sha256`, `title`, `publisher`, `publication_date`, `license_notice`, `license_url`, `parser_name`, `parser_version`, `normalization_profile`이다. 날짜는 ISO 날짜 문자열로 만든 뒤 정렬 key·공백 없는 UTF-8 JSON의 SHA-256을 fingerprint로 사용한다. 수집 시각·HTML 장식·사진·추적 token·기사 배열 순서는 의미 변경에 포함하지 않는다. 허용되지 않는 이용 조건은 `changed`로 통과시키지 않고 실패한다. 이 비교는 사실·중요도·정정·철회·최신 전체 수집 여부를 판정하지 않는다.

최대64KiB의 불변·엄격 typed private 보고서는 `schema_version=1`, `profile="policy-change-v1"`, 정확 before/after capture SHA-256·수집 시각과 ID순의 source별 상태·before/after fingerprint·정렬된 `changed_fields`를 담는다. 첫 비교의 before capture 정보와 `new`/`not_observed`의 없는 쪽 fingerprint는 null이다. `changed_fields`는 `changed`에서만 달라진 의미 필드 이름을 담는다. 보고서에 원문 HTML·본문·제목·발행 주체를 복제하지 않는다.

출력 사전 검사·입력400/600·출력 부모700·symlink 거부·새600 파일의 배타적 원자 저장은 기존 private-file helper와 같다. 성공 stdout은 `schema_version`, `status="compared"`, `new`/`changed`/`unchanged`/`not_observed` 개수만 담는다. 작업 실패는 기존 `Unable to complete policy operation`/exit1, 인수 오류는 `Invalid policy arguments`/exit2이며 SDK 실패는 `PreparationError("Unable to compare policy captures")`다.

최초/이전/현재 capture bytes와 각 보고서는 Git·PR·Sites·공개 로그 밖의 private 보관 정책에 따라 함께 보존한다. 공백·재직렬화도 capture hash를 바꾸므로 비교 뒤 기존 capture나 보고서를 덮어쓰지 않는다. 새 비교는 새 파일로 저장하고 이전 원문·인용·승인 계획은 그대로 보존한다. 자동 수집·정기 실행·보존 기간/자동 삭제·새 버전 ID 생성·등록/공개 게시·질문 중 자율 탐색은 추가하지 않는다. `changed`/`new`도 운영자의 내용·이용 조건 검토와 기존 명시 승인/등록·게시 절차를 거쳐야 한다.

합성 회귀는 저장소 루트에서 실행한다.

```sh
uv run pytest apps/worker/tests/test_policy_changes.py apps/worker/tests/test_policy_import.py packages/connectors/tests/test_policy_sdk.py packages/ingestion/tests/test_policy_html.py
uv run ruff check apps/worker
uv run ruff format --check apps/worker
uv run mypy
```

### 고정 기사 반복 확보와 PostgreSQL 이력

`poll`은 명시한 공식 기사1~2개를 한 번 확보하고 원본과 비교 보고서를 내부 journal에 남긴다. 서버 scheduler는 아래의 한 번 실행 명령을 주기적으로 호출할 수 있다. 명령 자체는 반복 loop나 scheduler를 만들지 않는다. 기존 연구 worker와 별도 실행 환경에서 실행하고 `ISSUEDIGEST_DATABASE_URL`을 그 환경에만 제공한다. 해당 DB에는 운영자가 검토한 `0008_policy_collection` migration이 먼저 적용되어 있어야 한다. import/startup/status는 migration을 실행하지 않는다.

소유자가 현재 실행 계정인 절대 경로의400/600 private UTF-8 JSON 파일을 준비한다. 최대8KiB이며 중복 key·비유한 수·추가 필드·불리언 정수·타입 변환을 거부한다. 다음은 합성 예시이며 scope와 한도를 운영자가 명시해야 한다.

```json
{
  "schema_version": 1,
  "expected_database": "issuedigest_test",
  "collection_id": "00000000-0000-4000-8000-000000000001",
  "news_ids": ["123456789"],
  "minimum_interval_seconds": 3600,
  "max_age_seconds": 7200,
  "max_attempts": 24
}
```

`collection_id`는 UUID4다. `news_ids`는 중복 없는9자리 ASCII 숫자 문자열1~2개로 정렬해 저장한다. 최소 간격은60~86400초, age 한도는 최소 간격 이상604800초 이하, 총 시도 상한은1~4096이다. DB URL의 DB명과 실제 `current_database()`가 모두 `expected_database`와 일치해야 한다. 같은 ID의 scope·간격·한도는 최초 결합 이후 변경할 수 없다.

```sh
uv run issuedigest-policy poll /absolute/private/policy/collection-job.json
uv run issuedigest-policy status /absolute/private/policy/collection-job.json
```

매 poll은 전용 연결의 nonblocking advisory lock `(104704, 2)`를 잡고 `running`을 commit한 뒤 기존 고정 capture SDK를 호출한다. 중복 실행은 `busy`, 최소 간격 전에는 `not_due`, 총 시도 한도 도달 시에는 `attempt_limit` 집계/exit0으로 끝나며 HTTP나 새 attempt를 만들지 않는다. scheduler 주기를 최소 간격 이상으로 설정한다. 중지하려면 연결한 scheduler를 비활성화한다. 다음 명시 poll에서 남은 `running`을 `failed/interrupted`로 마감하며, 재실행도 간격·상한을 따른다. 기존 연구 worker scheduler/잠금은 변경하지 않는다.

성공은 `succeeded`와 `new`/`changed`/`unchanged` 개수/시각만 stdout에 출력한다. 첫 성공은 `new`다. HTTP 실패는 `capture_failed`, 본문·이용 조건·저장 baseline의 의미 검증 실패는 `validation_failed`이며 `failed` 집계/exit1로 끝난다. DB 실패/commit 응답 불명확/cleanup 실패는 집계 출력 없이 고정 오류/exit1이다. 불명확한 commit은 HTTP/commit 재시도나 실패 덮어쓰기를 하지 않는다. 다음 명시 status/poll에서 저장된 실제 상태를 확인한다. 인수 오류는 기존 exit2다.

`status`는 read-only transaction에서 최신 attempt와 마지막 성공을 분리한다. 최초 미실행은 둘 다 null이고 stale이다. 최신 실패/미완료를 과거 성공으로 표시하지 않는다. 마지막 성공이 없으면 `age_seconds=null, stale=true`이며, 있으면 마지막 성공의 실제 확보 완료 시각 `finished_at` 이후 경과 시간이 `max_age_seconds`를 초과할 때 stale이다. SDK 요청 시작의 `collected_at`은 정확 capture bytes에 별도로 보존하며 완료 시각을 대신하지 않는다. 이 age는 확보 작업의 상태이며 발행일/내용 최신성이나 전체 수집 범위의 완전성을 뜻하지 않는다. status는 source HTTP·모델 호출·새 행을 만들지 않는다.

정확 capture bytes(최대8MiB+16384)와 비교 report bytes(최대64KiB), 각 SHA256은 성공 terminal과 함께 원자 저장한다. 기존 성공 원본/완료행은 repository에서 덮거나 지우지 않으며 실패 뒤에도 마지막 성공을 보존한다. 상태 출력은 집계·상태·시각만 담고 기사/collection/attempt ID·URL·경로·DSN·원문을 출력하지 않는다. 입력 파일·DB 원본·상세 receipt는 Git/PR/Sites/공개 로그 밖에 보관한다. DB 소유자의 직접 변경을 방지하는 감사 trigger/권한 정책은 추가하지 않았다.

자동 기사 발견·후보 선정·전체 최신 이슈 수집·자율 조사·EvidenceBundle/검색 자동 편입·공개 게시·자동 삭제/보존 기간·한도 reset·scheduler 설치는 포함하지 않는다. 내용 변경 뒤의 검토/등록/게시에는 기존 명시 승인 절차가 필요하다. scheduler 연결은 운영 인수 단계에서 별도로 기록하며 코드 구현만으로 운영 실행을 완료했다고 표시하지 않는다.

SDK는 `issuedigest_worker.policy_collection`의 `parse_policy_collection_job(raw)`, `poll_policy_collection(engine, config)`와 `policy_collection_status(engine, config)`다. poll/status 반환값은 private ID 없는 불변 typed 집계이며, engine lifecycle은 호출자가 `private_engine_lifecycle`로 감싼다. CLI는 engine/pool 정리가 성공한 뒤에만 결과를 출력한다. 합성 검사는 실제 PostgreSQL과 MockTransport를 사용한다.

```sh
uv run pytest apps/worker/tests/test_policy_collection.py
```

## 내구 조사 작업자

`issuedigest-research-worker`는 `ISSUEDIGEST_DATABASE_URL`과 서버 전용 `OPENAI_API_KEY`가 필요합니다. DBOS와 PydanticAI를 시작 전에 등록하고, queued run을 폴링하여 `research-{run_id}` 안정 workflow ID로 새 요청을v4 실행합니다. v2/v3/v4 이름과 agent를 모두 등록하고 기존 ID는 원래 등록 이름·application_version을 사용합니다. 모델은 OpenAI Responses `gpt-5.4-mini`로 고정하며 `store=False`, 공급자 재시도 0, 최대 한 요청·요청당 출력 2,500토큰·총 24,000토큰·요청 timeout 60초입니다. source 인용을 최대 다섯 자료·12,000자까지 전달합니다. 실제 모델 키가 없는 환경에서 작업자는 시작하지 않습니다.

스키마는 소유자 자격으로 Alembic `0005_research_journey`를 먼저 적용합니다. DBOS 시스템 스키마는 기존 앱 역할명을 `ISSUEDIGEST_DBOS_APPLICATION_ROLE`에 설정한 뒤 소유자 자격으로 `issuedigest-research-migrate-dbos`를 **별도** 실행합니다. 그 뒤 앱 역할로 worker를 실행합니다. Worker의 DBOS `run_migrations=False`, OTLP off, 시스템 풀 3이며 DBOS HTTP/admin 서비스를 등록하지 않습니다. 운영 자료/키로 테스트하지 않습니다. 모델 호출 결과 수신 실패와 실제 과금 사이의 불확실성은 예약액을 돌려주지 않는 방식으로 보수적으로 다룹니다.

## 국회 원문 capture·오프라인 준비

`issuedigest-capture-assembly`는 공개 국회 상세 페이지를 최대 두 요청으로 확보하고, `issuedigest-prepare-assembly`는 이미 저장된 capture에서 **제안이유·주요내용**만 추출하여 기존 등록 계획에 추가한다. 첫 명령만 네트워크를 사용한다. 두 번째 명령은 네트워크·DB·모델·공급자 호출 없이 실행한다. 수집 경계와 HTML 정규화 프로필은 [connectors](../../packages/connectors/README.md)에 있다.

private job은 최대 16 KiB의 엄격한 UTF-8 JSON 객체이며 다음 필드를 모두 명시한다. 추가 필드·중복 key·비유한 수·형식 변환을 거부한다.

| 필드 | 값 |
| --- | --- |
| `schema_version` | 정수 `1` |
| `bill_id` | ASCII 영문숫자·밑줄 1~80자 |
| `title` | 운영자가 공식 페이지와 대조한 제목 1~300자 |
| `bill_number` | 운영자가 대조한 ASCII 숫자 1~10자리 |
| `collected_at` | timezone을 명시한 수집 시각. capture와 같은 instant |
| `operator_approved` | boolean `true` |
| `document_id`, `version_id`, `raw_object_id`, `representation_id`, `snapshot_id`, `citation_id` | 운영자가 고정한 UUID4. 준비 중 생성하지 않음 |

제목·번호는 capture의 표시 텍스트 존재, form billId 일치 및 billNo가 있을 때 번호 일치를 검사한다. 이는 운영자 대조를 보조하는 확인이며 공식 메타데이터 자동 검증이 아니다. 제목·번호는 private job의 별도 운영자 메타데이터로 유지하며 추출 원문에 합성하지 않는다. `SourcePresentation` 자동 생성은 하지 않는다.

```sh
uv run issuedigest-capture-assembly PRIVATE_JOB PRIVATE_NEW_CAPTURE
uv run issuedigest-prepare-assembly PRIVATE_JOB PRIVATE_CAPTURE PRIVATE_BASE_PLAN PRIVATE_NEW_PLAN
uv run python -m issuedigest_storage.provision_cli PRIVATE_NEW_PLAN
```

입력은 owned regular 400/600, 모든 부모 경로 symlink 금지, 출력은 owned 700 부모 안의 새 600 파일이어야 한다. 기존 출력은 요청 전에 확인하고 최종 배타 게시로 경합을 방어한다. 실패 시 부분 파일을 정리하고 입력·기존 출력은 보존한다. 성공은 집계 JSON, 오류는 고정 문구만 출력한다. exit code는 0=성공, 1=작업 실패, 2=인수 오류다.

`parse_assembly_job(raw) -> AssemblyJob`, `prepare_assembly_plan(job, capture_raw: bytes, base: ProvisioningPlan) -> ProvisioningPlan` SDK를 제공한다. capture 파일의 **정확 JSON bytes**를 raw_sha256으로 결합하고 `application/vnd.issuedigest.assembly-capture+json`으로 기록한다. 표현은 파서 `assembly-prntSummary-htmlparser`, 버전 `1`, 프로필 `assembly-summary-visible-blocks-v1`과 추출 text/hash만 담는다. 인용은 전체 요약의 start=0/end=Unicode 문자 길이와 빈 prefix/suffix를 canonical 검증하고 support는 `not_evaluated`다. 발의일·처리 단계·법적 효력은 추정하지 않는다.

base의 workspace·expected_database·승인 invites·기존 snapshot을 보존한다. 기존/신규 문서·버전·raw object·표현·snapshot·인용 ID의 다른 내용 재사용을 거부하고, 동일 artifact+job+IDs 재실행은 같은 결과다. 새 네트워크 capture의 HTML·CSRF·collected_at 변화를 버전으로 자동 판정하지 않으며 운영자가 원문을 대조하고 새 버전 IDs를 제공해야 한다. 같은 JSON의 공백을 바꿔도 raw bytes/hash가 달라질 수 있으므로 최초 capture 파일을 그대로 보관한다.

실제 DB 등록은 위 HWPX 절차와 같은 기존 provision CLI의 `--check-database`/`--apply`만 사용한다. 새 DB write path·초대/role·스키마·API를 만들지 않는다. 앱의 제목 연결은 운영자가 공식 제목 대조 후 기존 `SourcePresentation` SDK로 수행한다. 앱은 마지막 저장 capture를 보여주며 최신 상태·전문·전체 이력이나 자동 수집 완료를 뜻하지 않는다. 공개 테스트는 합성 HTML·신원·자료만 사용한다.

질문 전용 실행은 현재 권한과run잠금 아래 기존 색인을 검색해 최대5개 근거를 고정한 뒤retrieving으로 전환합니다. 고정된 근거는 복구 때 다시 검색하지 않습니다. 무근거는 모델 호출 없이insufficient_evidence로 종료하며 기존 월 예약/요청 한도는 유지합니다. 버전 갱신 전 기존 worker를 중지하고 활성run/workflow를 완료·정리한 상태를 확인합니다. 진행 중 작업을 임의 폐기하지 않습니다.


### v2/v3/v4 checkpoint 호환과 단일 worker

PostgreSQL session advisory lock을 전용 AUTOCOMMIT 연결에서 획득한 뒤에만 상태/DBOS metadata를 읽습니다. 중복 기동은 고정 오류로 거부하며 첫 worker의 작업·예약·모델 호출을 바꾸지 않습니다. 소유 확인은 모델 전 단계/저장·poll/cohort에 적용하고 잠금 연결 오류는 고정 실패로 닫습니다. 정상 종료는 unlock/close, 프로세스 중단은 PostgreSQL 세션 종료로 잠금을 해제합니다. 최초v2 worker는 이 잠금을 모르므로 최초 업그레이드는 quiescent 상태가 필요합니다. 이후에도 worker는 하나만 운용합니다.

DBOS3.2의 공용 `DBOSClient.list_workflows/list_workflow_steps`를 input/output 비로딩으로 조회하고 실제 활성 application row와 정확한 ID로 대응합니다. 최대20개씩 읽어 원래 application_version의 cohort를 순차 launch/회복하고 registry를 destroy한 뒤 현재 버전으로 새 queued 요청을 처리합니다. `DBOS.resume_workflow`만 호출하면 원래 version이 남아 현재 큐가 처리하지 않으므로 같은 기록 version으로 기동합니다. 원래 checkpoint·workflow ID·step 순서를 삭제/수정하지 않습니다. terminal/cancelled/unknown workflow는 resume하지 않고, 실제 application row로 소유를 확인한 불명확/terminal orphan의 PENDING/ENQUEUED만 취소합니다.

generating/validating 재진입은 정확한 원래 `issuedigest_research_v2__model.request` 또는v3/v4의 완료 journal 정수slot1 step1개가 있을 때만 재생합니다. metadata 확인은 DBOSClient의 직접 읽기로 수행해 유료 step 앞에 새 durable step를 넣지 않습니다. 요청 중 프로세스가 중단되어 완료 checkpoint가 없으면 generation_failed와 예약 유지로 끝내며 유료 요청을 다시 보내지 않습니다. 이것은 제공자의 실제 접수/과금 여부를 알아낸다는 뜻이 아닙니다. 모델 오류 뒤 자동 retry·새 유료 호출을 추가하지 않습니다.

## Operator-only stored retrieval evaluation

Run `uv run --package issuedigest-worker issuedigest-evaluate-retrieval
/absolute/private/job.json --output /absolute/private/report.json` from the repository root
(as one shell command). Alternatively use `uv run --package issuedigest-worker python -m
issuedigest_worker.retrieval_evaluation_cli ...`. Both require an externally supplied
`ISSUEDIGEST_DATABASE_URL`, matching the job's `expected_database` exactly. No server, worker
startup, login, provider or browser is involved. This is an explicit read-only operator action.

Use an owned 600 job file and an owned 700 report parent. The report must be a new file; it is
published atomically as 600 after the complete evaluation and database pool disposal succeed.
stdout contains only aggregate retrieval metrics; failures emit a fixed message and no report.
The job is strict UTF-8 JSON capped at 256KiB with an exact whole-workspace corpus (1..50
snapshots), 1..40 questions and explicit positive families or negative no-match cases.
See [the complete job schema, commands and metric limits](../../tests/evaluation/README.md).
Keep jobs/gold/reports outside Git/PR/Sites. Synthetic regression success does not execute the
existing 20-question real-material evaluation or establish answer/citation quality.

새 v4는 기관의 발표 수치·평가를 귀속하고 목표·실적·전망을 구분하도록 지침만 개선한다. 같은 대상·기간·단위가 확인되는 단순 대소 관계는 설명하되 계산·인과·양측을 생성/강제하지 않는다. v3와 같은 bounded output schema/build·validation을 공유하며 reviewer만 issuedigest-research-v4/research-v4로 엄격히 구분한다. v2/v3 지침/schema/prompt bytes는 보존하고 새 v4 prompt14,813+static4,639+framing2,048+output2,500으로24,000 한도를 지킨다. 합성 모델/PG 검사는 실제 모델 품질 판정이 아니다. 실제 검증·적용 상태는 진행 기록을 따른다.
