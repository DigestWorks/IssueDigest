# Worker

`issuedigest-worker`는 운영자가 이미 확보한 private HWPX 파일에서 정확 본문·셀 인용을 준비하고 기존 `ProvisioningPlan`에 snapshot을 추가한다. SDK와 CLI는 DB·네트워크·공급자·모델 호출 없이 실행한다. 같은 작업 함수는 후속 DBOS 실행에서 재사용한다. 현재 DBOS 스케줄·재시도·복구 런타임과 실제 공동 DB 연결·적용은 미완료다.

## 설치·검증

저장소 루트에서 고정 workspace 의존성을 설치한다. 새 외부 의존성은 없다.

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

공개 테스트는 합성 ZIP/XML·계정·자료만 사용한다. HTTP 크롤러·원문 객체 보관·정기 수집·검색·AI·공동 DB 실사용은 후속이다. 작업 범위는 [HWPX 수집 명세](../../docs/changes/hwpx-import.md)를 따른다.
