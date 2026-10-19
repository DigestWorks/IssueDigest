# Source connectors

`issuedigest-connectors`는 공개 원천 한 건을 한정된 요청으로 확보하는 동기 SDK다. 첫 연결기는 국회의 **제안이유·주요내용**만 다룬다. 패키지 import는 네트워크·DB·환경 키를 조회하지 않으며 SDK는 파일을 자동 저장하지 않는다. 의존성은 `httpx2==2.13.1`, 기존 workspace와 같은 `pydantic==2.14.0`이다.

```sh
uv sync --locked --all-packages
uv run pytest packages/connectors/tests apps/worker/tests/test_assembly_import.py
uv run ruff check packages/connectors apps/worker
uv run mypy
```

```python
from datetime import UTC, datetime
from issuedigest_connectors import capture_assembly, serialize_capture

# bill_id와 collected_at은 운영자가 지정한 private job에서 가져온다.
capture = capture_assembly(bill_id, collected_at=datetime.now(UTC))
private_artifact_bytes = serialize_capture(capture)
```

공식 origin `https://likms.assembly.go.kr`에서만 상세 GET `/bill/bi/billDetailPage.do?billId=…`와 읽기용 POST `/bill/bi/bill/detail/billInfo.do`를 요청한다. 입력 ID는 ASCII 영문숫자·밑줄 1~80자다. 상세 페이지의 유일한 `form id="form"` 안의 input name/value와 유일한 `meta name="_csrf"`만 사용하며 form action은 따르지 않는다. 다른 검색·푸터 form은 무시한다. form billId는 입력과 정확히 일치해야 한다. 세션 cookie와 고정 `X-CSRF-TOKEN` 헤더는 해당 두 요청 사이에서만 유지한다.

요청 최대 두 회, 자동 재시도 0, 요청 timeout 20초, 응답당 2 MiB/합계 4 MiB다. TLS 검증을 유지하고 환경 proxy·환경 인증·redirect를 사용하지 않는다. HTTP 200, UTF-8 HTML만 허용한다. 압축 응답, 다른 charset 선언, 중복 token/form/field, 비정상 구조, field 64개 초과·field 값 4,096자 초과·전체 field 16,384바이트 초과를 거부한다. 원격 오류·경로·query·header·cookie·CSRF·본문을 SDK 오류나 HTTP 라이브러리 로그에 노출하지 않는다. 라이브러리 로그 필터는 capture 실행 context에만 적용하여 다른 스레드의 무관한 로그는 유지한다. 테스트 transport를 명시 주입할 수 있다.

`AssemblyCapture` schema_version 1은 `bill_id`, 고정 `canonical_url`, timezone을 명시한 `collected_at`, 정확한 UTF-8 응답 `detail_html`·`summary_html`을 담는다. `serialize_capture`와 `parse_capture`는 최대 8 MiB의 엄격한 UTF-8 JSON만 처리한다. duplicate key·비유한 수·추가 필드·잘못된 시간·ID·HTML을 거부하고 `model_construct`/`model_copy` 우회 모델도 저장 경계에서 재검증한다. 원문·CSRF·ID는 repr에 포함하지 않는다. 반환 객체와 JSON은 모두 private 자료다.

요약은 표준 `HTMLParser`로 유일한 `id=prntSummary` 영역만 추출한다. 프로필 `assembly-summary-visible-blocks-v1`은 block/br를 줄 경계로, `<pre>`의 CRLF/CR를 LF로 바꾼다. 각 줄의 Unicode 공백은 한 칸으로 합치고 빈 줄·양끝 공백을 제거한다. entity를 해석하되 한국어·이모지·조합 문자를 NFC로 변환하지 않는다. script/style/template/noscript/head/datalist·닫힌 dialog, hidden/inert/aria-hidden, 명시적인 display:none/visibility:hidden 콘텐츠는 제외한다. 메뉴·제목·다른 법안·AI 텍스트로 fallback하지 않는다.

브라우저 DOM 복구·JavaScript·외부 CSS를 실행하지 않는다. 요약 조상의 inline style도 검사하며 양의 pixel height·height:auto 외의 미지원 스타일은 거부한다. 일반 wrapper class는 외부 CSS를 실행해 가시성을 검증했다고 주장하지 않는다. 요약의 알려진 `theme_list_summary` class와 양의 pixel height 이외의 class/style, iframe/details 같은 동적 가시성, 비정상 중첩, 없는/중복/빈/미종결 영역은 실패 처리한다. 깊이 64, node 50,000, 요약 100,000 Unicode 문자 이내다. 상세 GET은 선택 form과 token을 확보하고 main 구조가 닫힌 뒤의 footer만 bounded opaque 영역으로 취급한다. 이 footer 텍스트는 메타데이터·근거에 쓰지 않으며, 전체 나머지 문서에서도 중복 form/token/summary selector와 node/depth/charset/attribute 한도를 계속 검사한다. 선택 form과 요약의 중첩·종결 검사는 유지한다. 구조 변경 시 검토 후 프로필을 명시적으로 변경해야 한다.

capture의 두 응답 전체와 지정 수집 시각을 private artifact로 보존한다. 정확 artifact JSON 바이트가 raw hash의 기준이므로 같은 의미의 JSON이라도 재직렬화하면 별개 raw가 될 수 있다. 같은 capture artifact와 같은 job/IDs의 준비·등록은 재실행해도 같은 결과·신규 0이다. **재수집의 HTML·CSRF·수집 시각 변경을 새 법안 버전으로 자동 판정하지 않는다.** 운영자가 원문을 대조하고 새 version/raw_object/representation/snapshot/citation UUID4를 지정한다. 기존 결과는 덮어쓰지 않는다.

[worker의 두 단계 비공개 명령](../../apps/worker/README.md)이 확보·준비를 담당하고 실제 등록은 기존 provision CLI만 사용한다. 발의일·처리 단계·법적 효력·최신 상태·법안 전문·전체 처리 이력·목록 증분 탐색·자동 변경 감지·정기 실행은 이번 연결기의 결과가 아니다. 앱에 연결하는 자료는 마지막 저장 capture이며 실제 제목 대조와 `SourcePresentation` 연결은 운영자가 별도로 수행한다.


## 고정 정책뉴스 발견·확보

`discover_policy`·`policy_candidates`와 `capture_policy`는 고정 정책뉴스 첫 목록과 명시한 기사1~2개의 private artifact를 반환한다. 후보 선택·기사별 공공누리1 텍스트 검토·PolicyJob/세 hash·정확 인용·오프라인 준비·기존 명시 등록/검색 투영/표시 제목 연결은 [worker의 정책뉴스 운영 절차](../../apps/worker/README.md#정책뉴스를-확인하고-비공개-등록-계획을-준비하기)를 따른다. import는 수집하지 않으며 SDK는 DB·파일 저장·정기 수집·공개 게시를 실행하지 않는다.


`policy_candidate_metadata(discovery) -> tuple[PolicyCandidateMetadata, ...]`는 기존 제목 전용 `PolicyCandidate`·`policy_candidates`에 추가된 공개 SDK다. 기존 bounded serializer/parser로 capture를 다시 검증한 뒤 같은 보이는 목록 영역·canonical 링크만 읽는다. 불변·strict·extra forbid 모델은 `news_id`, `canonical_url`, 공백 정돈한1~300자 `title`, 정확한 `date` 타입 `published_on`, 공백 정돈한1~200자 `publisher`를 담으며 모든 필드는 repr에서 제외한다. `source` 첫 span은 정확 `YYYY.MM.DD` 달력 날짜, 둘째 span은 발행처다. 숨김·누락·모호한 날짜/발행처나 같은 ID의 상충하는 제목·날짜·발행처는 고정 `PolicyError("Unable to validate policy discovery")`로 실패한다. 동일 메타데이터 중복은 합친다. 기존 제목 전용 SDK가 허용한 날짜 문자열과 capture 바이트 계약은 바꾸지 않는다.

목록 날짜·발행처는 발견 메타데이터다. 기사 본문 발행일과 다를 수 있으며 내용·권리 승인·진실·최근 주목도·순위가 아니다. [비공개 후보 비교 보고서](../../apps/worker/README.md#목록의-날짜-범위와-이전-관측을-비교하기)는 추가 HTTP·DB·모델 호출 없이 이 메타데이터를 비교한다.
