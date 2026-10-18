# 공식 자료 변경 감지

2026-10-18. 사용자의 내부 AI 파이프라인 개발 계속 요청에 따라, 기존 승인된 정책뉴스 capture를 비교해 중복 가공과 변경 누락을 줄이는 내부 연결기를 구현한다. D021/D022·R2/R6를 따른다. OpenSpec root=null이며 초기화하지 않는다. 운영자용 비교 도구는 최종 수집 파이프라인에서도 재사용하며 사용자 화면·임시 진단 메뉴를 추가하지 않는다.

## Global Constraints

- 기존 고정 공식 출처·1~2기사 capture와 policy-html parser를 재사용한다. 다른 출처·원격 탐색·정기 실행·모델 호출·자동 DB 등록·공개 게시를 도입하지 않는다. 발견/확보와 변경 비교, 승인 등록, 공개 게시를 구분한다.
- 입력은 기존 크기 제한/중복 JSON/비유한 값/타입/URL/시각 검증을 통과한 정확 capture bytes다. 기존 결과·계정/세션·private/public 경계·DB 스키마·OpenAPI·v2/v3/v4 유료 실행/호환·의존성·예산을 변경하지 않는다.
- 비교는 검증된 본문·제목·발행 주체·발행일·이용 조건·parser profile의 동일성만 판단한다. 사실·중요도·정정/철회 여부·최신 전체 수집을 추론하지 않는다. 이전 capture에만 있는 기사는 not_observed이며 삭제/철회로 판정하지 않는다. 이전보다 오래된 collection time은 거부한다. 같은 시각의 서로 다른 capture는 순서를 확정할 수 없어 거부하되 정확 동일 bytes는 허용한다.
- capture의 시각/페이지 장식/추적 token만 달라졌다면 본문 변경으로 표시하지 않는다. 새로운 capture의 조건/본문 검증이 실패하면 작업 전체를 고정 오류로 종료하고 unchanged나 승인 가능으로 표시하지 않는다.
- 모든 파일은 기존 private-file helper의 절대 경로·소유/권한·symlink 거부·한도·exclusive atomic write를 재사용한다. stdout/stderr는 집계/고정 오류만 출력하며 제목·URL·본문·ID·입력 경로를 노출하지 않는다. 네트워크/DB/model/import side effect가 없다.
- 구현자는 하위 에이전트를 생성하지 않는다. 실제 계정/서버/자료/키를 읽거나 변경하지 않는다. main/운영은 D013 유예다. 컨트롤러가 독립 검토·검증·feature Draft PR·계획표/Sites 갱신을 수행하며 사용자 탭을 열지 않는다.

## Task 1: 정확 capture의 변경 비교 SDK·CLI

- [ ] `apps/worker/src/issuedigest_worker/policy_changes.py`에 순수 `compare_policy_captures(current_raw: bytes, *, previous_raw: bytes | None = None)`를 구현한다. 두 입력 모두 기존 parse_policy_capture를 통과시키고 기사마다 기존 extract_policy_html에 실제 HTML SHA/canonical URL을 전달한다. 첫 실행은 new, 동일 source_id의 비교는 unchanged/changed, 이전에만 있으면 not_observed다. 결과 순서는 news_id로 고정하며 HTML 순서 변경이 결과 판단을 바꾸지 않는다.
- [ ] frozen/strict/extra-forbid typed report에 schema_version=1, 명시 profile `policy-change-v1`, 정확 before/after capture SHA256·수집 시각, source별 status와 before/after 의미 fingerprint 및 변경 필드 목록을 보존한다. fingerprint는 정렬 key의 UTF-8 canonical JSON으로 본문 text_sha256·title·publisher·publication_date·license_notice/license_url·parser_name/version/normalization_profile을 포함한다. 원문 HTML/본문을 보고서에 복제하지 않는다. new/not_observed의 없는 쪽 fingerprint는 null이며 changed 필드는 기존 의미 필드 이름의 정렬 목록이다. source ID는 private report에만 둔다. 보고서는 최대64KiB이며 불명확/잘못된 입력은 고정 PreparationError로 실패한다.
- [ ] 기존 `issuedigest-policy compare PRIVATE_CAPTURE PRIVATE_NEW_OUTPUT [--previous PRIVATE_CAPTURE]` 분기를 추가한다. compare는 네트워크·모델·DB를 호출하지 않으며 기존 discover/capture/prepare 동작을 보존한다. 성공 stdout은 schema_version/status 및 new/changed/unchanged/not_observed 집계만, 실패는 기존 고정 메시지다. output 사전 검사와 exclusive atomic write·600 권한을 보존한다.
- [ ] TDD로 누락 API/CLI RED를 먼저 확인하고 구현한다. 의미 있는 회귀: 초기 new, 수집 시각/장식·사진만 변경은 unchanged, 본문/제목/주체/날짜 변경은 changed·필드, 기사 추가/목록에서 빠짐 not_observed, 기사 순서 독립, 오래된 시각/같은시각다른bytes·잘못된 조건·invalid JSON/duplicate/oversize/nonbytes 거부, 오류/로그 원문 비노출, 기존 private helper·네트워크 미호출·기존 CLI 회귀를 포함한다. 테스트 fixture는 합성만 사용한다.
- [ ] 관련 Python 테스트·Ruff format/check·mypy를 실행하고 worker README에 실제 명령·판단/자동화 경계·보존 정책을 기록한다. 위 체크박스는 증거가 있을 때만 완료 표시한다. 커밋과 report에 RED/GREEN 명령·결과/파일·한계를 기록한다. 문서의 상위 마일스톤·Sites는 컨트롤러가 맡는다.

## 완료 판정

독립 Task/전체 검토와 관련 회귀, 저장소 계획표/진행 기록·Sites 갱신을 확인한다. 이번 완료는 내부 변경 비교 도구의 구현이다. 정기 수집·질문 중 자율 탐색·Neo4j·벡터 검색·에이전트 다중 호출·서비스 출시 완료로 표시하지 않는다. 앱 실행 경로 변경이 없으면 불필요한 API/worker 재시작·실제 데이터 변경을 수행하지 않는다.
