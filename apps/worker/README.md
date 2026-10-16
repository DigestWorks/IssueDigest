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

## 내구 조사 작업자

`issuedigest-research-worker`는 `ISSUEDIGEST_DATABASE_URL`과 서버 전용 `OPENAI_API_KEY`가 필요합니다. DBOS와 PydanticAI를 시작 전에 등록하고, queued run을 폴링하여 `research-{run_id}` 안정 workflow ID로 새 요청을v3 실행합니다. 기존v2/v3 이름과 agent를 모두 등록하고 기존 ID는 원래 등록 이름·application_version을 사용합니다. 모델은 OpenAI Responses `gpt-5.4-mini`로 고정하며 `store=False`, 공급자 재시도 0, 최대 한 요청·요청당 출력 2,500토큰·총 24,000토큰·요청 timeout 60초입니다. source 인용을 최대 다섯 자료·12,000자까지 전달합니다. 실제 모델 키가 없는 환경에서 작업자는 시작하지 않습니다.

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

질문 전용 실행은 현재 권한과run잠금 아래 기존 색인을 검색해 최대5개 근거를 고정한 뒤retrieving으로 전환합니다. 고정된 근거는 복구 때 다시 검색하지 않습니다. 무근거는 모델 호출 없이insufficient_evidence로 종료하며 기존 월 예약/요청 한도는 유지합니다. 최초v2→v3 적용 전 기존 worker를 중지하고 활성run/workflow를 완료·정리한 상태를 확인합니다. 진행 중 작업을 임의 폐기하지 않습니다.


### v2 checkpoint 호환과 단일 worker

PostgreSQL session advisory lock을 전용 AUTOCOMMIT 연결에서 획득한 뒤에만 상태/DBOS metadata를 읽습니다. 중복 기동은 고정 오류로 거부하며 첫 worker의 작업·예약·모델 호출을 바꾸지 않습니다. 소유 확인은 모델 전 단계/저장·poll/cohort에 적용하고 잠금 연결 오류는 고정 실패로 닫습니다. 정상 종료는 unlock/close, 프로세스 중단은 PostgreSQL 세션 종료로 잠금을 해제합니다. 최초v2 worker는 이 잠금을 모르므로 최초 업그레이드는 quiescent 상태가 필요합니다. 이후에도 worker는 하나만 운용합니다.

DBOS3.2의 공용 `DBOSClient.list_workflows/list_workflow_steps`를 input/output 비로딩으로 조회하고 실제 활성 application row와 정확한 ID로 대응합니다. 최대20개씩 읽어 원래 application_version의 cohort를 순차 launch/회복하고 registry를 destroy한 뒤 현재 버전으로 새 queued 요청을 처리합니다. `DBOS.resume_workflow`만 호출하면 원래 version이 남아 현재 큐가 처리하지 않으므로 같은 기록 version으로 기동합니다. 원래 checkpoint·workflow ID·step 순서를 삭제/수정하지 않습니다. terminal/cancelled/unknown workflow는 resume하지 않고, 실제 application row로 소유를 확인한 불명확/terminal orphan의 PENDING/ENQUEUED만 취소합니다.

generating/validating 재진입은 정확한 원래 `issuedigest_research_v2__model.request` 또는v3의 완료 journal step1개가 있을 때만 재생합니다. metadata 확인은 DBOSClient의 직접 읽기로 수행해 유료 step 앞에 새 durable step를 넣지 않습니다. 요청 중 프로세스가 중단되어 완료 checkpoint가 없으면 generation_failed와 예약 유지로 끝내며 유료 요청을 다시 보내지 않습니다. 이것은 제공자의 실제 접수/과금 여부를 알아낸다는 뜻이 아닙니다. 모델 오류 뒤 자동 retry·새 유료 호출을 추가하지 않습니다.
