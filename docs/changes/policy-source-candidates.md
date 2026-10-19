# 공식 목록 후보 선별·출처 확대

2026-10-19 KST. M2의 승인 출처 확대를 이어간다. 고정 정책뉴스 목록의 실제 날짜·발행처를 정리하고, 이전 목록과 비교해 원문 검토 후보를 만든다. 선택한 후보의 원문·이용 조건·정확 인용을 별도로 검토한 뒤 기존 명시 등록으로 검색에 추가한다. OpenSpec root=null, 초기화하지 않는다. PR40 기반이며 D019~D022·R2/R3/R6·main/운영 유예를 유지한다.

## Global Constraints

- 고정 `https://www.korea.kr/news/policyNewsList.do`와 기존 정확9자리 policyNewsView 링크만 다룬다. 기존 discover/capture/PolicyDiscovery v1/PolicyCandidate/serializer와 HTTP(TLS/redirect/retry/bytes/cookie/log) 계약을 보존한다. import/후보 보고서는 HTTP·DB·환경 키·모델·DBOS를 호출하지 않는다. 새 의존성·DB migration·웹/API·생성 계약·AI 지침/유료 checkpoint·session/공개 게시를 변경하지 않는다. Task2의 관측된 metadata profile3 및 intake의 parser-version allowlist3만 추가하며 기존1/2 bytes·본문 알고리즘은 보존한다.
- 목록의 제목·날짜·발행처는 발견 메타데이터다. 기사 본문·권리·진실·최근 주목도·여론·순위가 아니며 목록 누락도 철회/삭제가 아니다. 기존 파서의 보이는 단일 article_body/list_type/ul과 canonical URL guards를 재사용한다. 새 메타데이터 API는 source의 첫 span을 정확 YYYY.MM.DD 달력 날짜, 둘째 span을 공백 정돈한1~200자 발행처로 읽는다. 목록 날짜는 목록에 표시된 값이며 원문 발행일과 다를 수 있으므로 실제 등록의 발행일은 원문에서 다시 확인한다. 제목은 기존 정돈/300자 한도, 날짜/발행처의 숨김/누락/모호함은 고정 오류다. 동일 ID의 날짜/발행처/제목이 다르면 새 API는 거부한다. 기존 title-only SDK가 허용한 입력까지 새로 거부하도록 바꾸지 않는다.
- `PolicyCandidateMetadata`와 `policy_candidate_metadata(capture)`는 connectors의 additive 공개 SDK다. 정확 news_id/canonical_url/title/published_on(date)/publisher를 불변·strict·extra forbid·민감 repr 제외 모델로 반환하며 기존 bounded discovery serializer/parser로 capture를 재검증한다. worker는 connectors의 private 모듈을 import하지 않는다.
- 순수 `build_policy_candidate_report(current_raw, *, since:date, through:date, previous_raw:bytes|None=None)`는 정수 schema_version1, 정확 discovery bytes SHA256/collected_at, optional 이전 SHA/collected_at, inclusive since/through와 entries를 반환한다. 날짜 인수는 정확 date 타입이고 since<=through다. 이전본은 현재보다 엄격히 이른 aware instant여야 한다. 현재/이전 모두 기존 파서와 새 metadata로 재검증한다. 원본은 각각 기존 최대4MiB+8192이며 출력은512KiB 이하다.
- entries는 현재 날짜 범위 안 후보를 new(이전 ID 없음)/unchanged(모든 metadata 같음)/metadata_changed(제목·날짜·발행처 중 변화)로 분류한다. 이전본이 없으면 new는 첫 관측일 뿐 전역 신규 기사라고 부르지 않는다. 이전 날짜 범위 안 ID가 **현재 전체 목록에 없을 때만** not_observed로 이전 metadata를 담는다. 현재에 있으나 범위 밖으로 이동한 ID를 누락으로 분류하지 않는다. 각 entry는 metadata와 status만 가지며 current-first 같은 순위를 만들지 않고 news_id 오름차순으로 정렬한다. 최대 현재100+이전100행이다. 권리 승인/본문 변경·전역 최신성·완전성·자동 후보 선택을 추론하지 않는다.
- `issuedigest-policy candidates PRIVATE_DISCOVERY YYYY-MM-DD YYYY-MM-DD PRIVATE_NEW_REPORT [--previous PRIVATE_DISCOVERY]`를 추가한다. CLI 날짜는 canonical ASCII YYYY-MM-DD만 허용한다. private input400/600·소유 regular·절대 경로·symlink/중간 경로 방어와 새700부모/600파일 배타 원자 저장을 재사용한다. 기존 명령/오류 exit를 유지한다. stdout은 schema_version/status="candidates_reported"/candidates(현재 범위 내)/new/unchanged/metadata_changed/not_observed만 출력하고 원문·표제·발행처·ID·URL·경로·개별 날짜/DSN은 출력하지 않는다. 상세는 private 보고서에만 둔다.
- 기존 실사용 자료·버전·인용·검색·기록·계정/세션·공개v1·개발 화면/API/worker·시간당 collector source/config/주기는 보존한다. 후보 발견을 검색/공개 승인으로 자동 승격하지 않는다. controller의 실제 공식 목록1회와 서로 다른 기사 최대2건 확보 후 개별 원문/공공누리1텍스트·사진/외부 저작물 제외·정확 인용을 검토한 경우만 기존 명시 provision 경로로 개인 개발 자료를 추가한다. 추가 전 백업·별도 복원 검증, 적용/재적용·권한/역사 인용·보존·사후 복원 증거를 남긴다. 수집 범위 확대나 새 cron·공개 게시·유료 생성은 없다.
- 구현자는 합성 fixtures/TDD만 사용하고 subagent/실제 서버/키/자료/HTTP를 사용하지 않는다. controller가 독립 검토·전체 gate·실제 bounded 확보/내용 검토·개인 개발 적용·Draft PR·Sites/이전판 보존을 맡는다. 사용자 탭을 열거나 이동하지 않는다.

## Task 1: 목록 메타데이터·후보 비교 보고서와 CLI

- [x] connectors의 additive metadata 타입/SDK와 파서 최소 공유 helper를 구현한다. 기존 result_entries/PolicyCandidate와 capture bytes 계약은 보존한다. 한 ID의 conflicting metadata와 날짜/발행처 불명확을 새 API에서 검증한다.
- [x] worker의 순수 후보 비교 보고서와 candidates CLI를 구현한다. 정확 SHA/시각·inclusive 날짜·이전 chronology·분류·정렬·현재 밖으로 이동한 ID 처리·한도·private 파일/집계 stdout을 검증한다. 기존 명령·고정 오류/예외와 no-IO 경계를 유지한다.
- [x] TDD로 날짜/윤년·공백·숨김·중복/충돌·비canonical 링크·forged capture·extra/중복 JSON·이전/현재/범위/모든 상태·boundaries·파일/출력/원자성·0HTTP/DB/모델·비밀 로그를 검증한다. 기존 connectors/worker 관련 회귀·Ruff/format/mypy와 README/체크박스/commit/report를 완료한다. 스타일/구현을 그대로 복제하는 테스트는 만들지 않는다.

Task1 구현 검증(2026-10-19): 새 합성 계약 검사111개를 포함해 connectors/worker602개 통과, 전용 PostgreSQL 필요 검사102개는 DB URL을 비운 상태로 건너뛰었다. 두 패키지 Ruff/format과 전체 mypy114개 소스가 통과했다. 전체 DB 포함 gate·독립 검토·실제 확보·개인 개발 적용은 controller 인수 범위다. 기존700 부모/새600 파일 보호와 명시 등록 경로를 보존하며 후보 보고서 자체는 자료 등록·선정·권리 승인이 아니다. 상세 SDK/보고서 필드와 CLI는 각 패키지 README에 기록했다. Task2는 별도다.

## Task 2: 관측된 원문의 발행처 링크 metadata profile

실제 확보한 기사 한 건은 info의 두 span 중 두 번째에 부처 링크가 있는 관측 형태여서 기존 parser가 거부했다. 첫 기사(plain v2)는 추출되지만 batch 전체를 임의 분할/재확보하지 않으며 정확 원본은 유지한다. 아래 구조만 합성 fixture로 재현한다. 실제 원문/ID는 구현자에게 전달하지 않는다.

- [x] 기존 v1/v2 분기는 그대로 보존하고, `info`가 unique `variety`의 직접 자식·attrs가 class=info이며 whitespace 이외 직접 text/추가 tag 없이 정확 두 plain span인 구조를 새 parser_version="3"로 지원한다. 첫 span은 attrs/중첩 없는 정확 ASCII YYYY.MM.DD 달력 날짜다. 둘째 span도 attrs 없고 whitespace 이외 직접 text 없이 정확1 anchor를 가진다. anchor attrs는 정확 class="gotosite", href="/news/ministryNewsList.do?repCode=<ASCII uppercase letter +5digits>"만이며, 자식은 발행처 text와 선택적 단일 `<i class="tooltip">`의 plain text뿐이다. tooltip은 발행처에서 제외하며 빈 발행처·추가/nested/hidden/다른 링크·scope/중복은 거부한다. tooltip을 이용한 출처/권리 추정을 하지 않는다. 기존 parser 분기가 원래 지원한 모양을 version3로 재분류하지 않는다.
- [x] ingestion의 extraction/representation/locator version allowlist에3을 추가하고, 저장 intake의 고정 parser-version allowlist도3만 추가한다. 본문 정규화 profile·text/hash/정확 인용·권리 문구/URL·새 버전 의미 fingerprint·PolicyJob/변경 비교·기존 v1/v2 직렬화/hash를 보존한다. 다른 버전은 계속 거부한다. storage 테스트에서 합성 profile3의 check/apply/재사용과 과거 인용을 실제 전용 PG로 확인하며 다른 intake guards를 약화하지 않는다. v3 AI workflow와 별개인 HTML parser_version3임을 문서에서 구별한다.
- [x] TDD로 관측 형태의 성공·같은본문/quote/hash·엄격한 부정 구조/날짜/링크·권리/원문 URL·이전1/2 호환·새3/미지원 버전/forged models 경계를 검증한다. 관련 ingestion/worker/storage 회귀·Ruff/format/mypy와 README/체크박스/report/commit을 완료한다. 실제 서버/원문/HTTP/모델 없이 합성 PG만 사용한다.

Task2 구현 검증(2026-10-19): 합성 HTML의 관측된 두 span·상대 부처 링크만 HTML parser_version3으로 추가했고 기존1/2 분기·직렬화/hash·본문/인용·권리/URL guards를 보존했다. 저장 intake의 고정 allowlist에는3만 추가했다. 새 성공/엄격 거부 검사와 기존 회귀를 포함해 ingestion/worker/storage 전용 합성 PostgreSQL 검사1,797개가 통과했다. 이후 추가한 윤년/권리 info scope/숨김/날짜0년4개를 포함한 최종 ingestion257개도 통과했다. 세 패키지 Ruff/format·전체 mypy114개 소스와 diff 검사가 통과했다. 원본1/2의 representation hash는 각각 기존 golden과 이전d29871f 코드 실행으로 대조했다. v3 check/apply/정확 재시도·재수집 재사용·과거v1/v3 인용을 실제 합성 PostgreSQL에서 확인했으며 HTML parser version3과 AI workflow v3는 별개다. 실제 HTTP/원문/키/모델/서버·개인 개발 적용·독립 검토/전체 gate·Sites는 controller 인수 범위다.

Task2 독립 검토 보완(2026-10-19): 새 profile의 숨김 조상 판정 누락1건을 수정했다. details/dialog는 open 상태와 무관하게, iframe/object/svg는 지원하지 않는 metadata 조상으로 거부하며 ARIA 대소문자·CSS visibility:collapse도 판정한다. v1/v2 경로는 유지했다. 먼저8개 거부 검사의 실패와16개 이전 호환 검사의 통과를 확인한 뒤 수정했으며 최종 HTML281개·전체 Ruff/format·mypy114개 소스·diff 검사를 통과했다. 재검토·수정 후 전체 gate는 controller 인수 범위다.

## Controller 인수·공유

작업별/전체 독립 검토·전용 합성 PostgreSQL 전체 검사를 통과한다. 실제 확보는 기존 SDK로 목록1회+기사2건을 bounded GET하고, 원래 DB에 있는 기사와 새 기사를 분리한 뒤 기존 CLI의 정확 batch 계약을 유지하기 위해 새 기사1건만 한 번 더 확보할 수 있다. HTTP 총4회 이하이며 보고서와 개별 원문/권리/인용은 private에 보존한다. 목록의 후보를 무검토 최신 이슈나 공개 브리핑으로 노출하지 않는다. 가능하면 검토한 새 자료를 기존 명시 등록·표시/검색 경로로 개인 개발에 추가하고 DB/앱/수집기·과거 인용을 보존한다. 실제 적용/복원·질문 검색 확인과 코드 완료를 구분하고 Draft PR·마일스톤·Sites를 갱신한다. 도메인 전체·언론/여론/최근 인기·자율 조사 완료로 확대하지 않는다.


Controller 인수(2026-10-19): 최종 제품93ab7c8에서 전용 PostgreSQL18.6 전체 Python3,035+JS568=3,603개·Ruff/format258·mypy114·JS lint/types·SPA build·API 계약과 [CI39187839563](https://github.com/DigestWorks/IssueDigest/actions/runs/39187839563)가 통과했다. 경고/skip/실패0. Task2 숨김 조상1건을 수정하고 작업별/보완/전체 독립 검토 C0/I0/M0, 미해결/보류 지적0이다.

실제 기존 SDK GET은 목록1+기사3=4회(서로 다른 기사2건)다. 원래2건 capture는 유지하고 이미 있던 자료는 중복 등록하지 않았다. 기존 exact-batch 계약에 맞게 새 기사만1회 재확보했다. 실제 후보10/이전 대비신규1/동일9/미관측1/metadata변경0이며 첫 관측·목록 날짜·본문 발행일·DB신규는 구분한다. 개별 원문/공공누리1 텍스트/사진·외부 저작물 제외·발행일·본문 SHA·8개 정확 인용을 controller가 검토하고 기존 명시 등록·표시/검색으로 새1건을 개발 DB에 추가했다. 같은 계획 재실행은0신규/0초대이며 앱 계정 read-only로3질문 검색/원문·모든15canonical을 확인했다. 출처의 정부 평가는 독립 사실 검증으로 승격하지 않는다.

기존23테이블의 모든 행·schema0009/공개1/receipt1을 보존하고 자료 버전15/인용49/검색36을 확인했다. 서버 밖 사전·직전·사후 full/app archive·별도 사후PG18.6 app 복원의23테이블 rowhash/count가 실제 사후 DB와 일치했다. vector/역할 포함 완전 재해복구는 아니다. 도구 전용 소스/venv만 분리 준비했고 정적웹4cd8f62·API/worker b63c7fa/PID·수집기a908083/config/주기는 변경하지 않았다. HTTPS/비회원 경계와 화면/공개본 hash도 동일하다. 모델/OAuth/새 cron/공개 게시0, main/운영 유예. [Draft PR41](https://github.com/DigestWorks/IssueDigest/pull/41)은 PR40 기반으로 미병합이며 Sites 출판 상태는 진행 기록을 따른다.
