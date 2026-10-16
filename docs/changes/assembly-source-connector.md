# 국회 법안 원문 연결기 · 첫 이관

2026-10-16 KST. 사용자가 기존 수집기의 선별 재사용과 법안 연결기 개발 진행을 승인했다. UI/UX는 별도 인터뷰 중이며 이번 구현에서 변경하지 않는다. OpenSpec root=null이므로 기존 명세+SDD/TDD/독립 검토를 따른다. 기준 feat/research-journey/2439385.

## 목표·범위

기존 LawDigest의 국회 원천 ID·공식 상세 페이지 조회 규칙을 선별 재사용한다. 과거 전체 runtime/MySQL/AI 요약 실행기를 복사하지 않는다. 첫 연결기는 운영자가 지정한 법안 **한 건의 공식 제안이유·주요내용**을 실제 조회하고 원본 capture→정확 추출→기존 ProvisioningPlan→명시 등록 도구로 넘긴다. 질문/생성 UI·기존 조사 워커는 변경하지 않는다.

이번 범위는 원문 한 건을 안전하게 연결하는 첫 단계다. 신규 법안 목록 증분 탐색·전체 처리 이력 해석·자동 변경 감지·정기 DBOS 수집·알림은 후속이며 완료로 표시하지 않는다. 실제 기존 수집 실행 상태는 미확인이다. 2026-10-16 읽기 집계의 Bill41,004건/제안일 상한2026-07-10은 최신 수집 성공을 의미하지 않는다.

## 수용 기준·경계

- `packages/connectors`를 Python workspace 패키지로 연결한다. httpx2==2.13.1 명시 고정(기존 dev 사용 버전), import/startup에서 네트워크/DB/환경키 조회 없음. 동기 bounded SDK와 합성 transport 주입을 지원한다.
- 공식 origin `https://likms.assembly.go.kr`만 요청. 입력은 URL이 아닌 bill_id(ASCII 영문숫자/밑줄, 최대80). 상세 GET `/bill/bi/billDetailPage.do?billId=...`와 그 페이지 form/meta의 CSRF를 이용한 읽기용 POST `/bill/bi/bill/detail/billInfo.do`만 허용한다. 원천의 공개 상세 HTML 요청을 재사용하며 임의 URL·redirect·TLS 우회·환경 proxy·쿠키/CSRF 로그를 허용하지 않는다.
- GET/POST 합계 최대2회, 자동 retry0, 요청 timeout20초, 응답당 최대2MiB/합계4MiB, UTF-8 HTML만 허용한다. redirect/status오류·과대 stream·비HTML·없는/중복form·없는/중복CSRF·입력ID와 form billId 불일치·중복/너무 큰 form field를 고정 오류로 거부한다. form action/외부URL을 따라가지 않는다. query/headers/response text/privateID를 예외/표준출력에 포함하지 않는다.
- 정확 raw 상세 응답 두 개를 private artifact에 보존하고 hash로 결합한다. 저장 capture 모델은 bill_id·canonical_url·명시 timezone collected_at·원본 HTML 두 개와 schema_version1. repr에 원문/CSRF/ID를 노출하지 않음. 저장 크기·duplicate JSON key/비유한 수·추가 필드·우회 construct/copy도 거부한다. SDK는 기본 저장을 하지 않는다.
- 표준 HTMLParser로 `id=prntSummary` 영역을 하나만 추출한다. script/style/숨겨진 콘텐츠를 근거로 넣지 않고, block/br 경계와 entity/한국어·Unicode를 명시 프로필로 정규화한다. 빈/중복/닫히지 않은 영역·비정상 중첩/깊이·과대 텍스트를 거부한다. 최대100,000 Unicode 문자. 반환 text는 실제 영역에서만 유래하며 다른 법안/메뉴/AI 요약을 fallback하지 않는다. 구조 변경은 실패로 표시한다.
- 준비 job은 운영자가 고정한 UUID4(document/version/raw_object/representation/snapshot/citation), bill_id, 공식 대조 title(1..300자), bill_number(숫자1..10자리), 명시 collected_at, operator_approved=true를 갖는다. source_kind=bill/provider·canonicalURL은 고정 규칙. title/number는 capture의 billId 일치와 표시 텍스트 존재를 확인하되 공식 메타데이터 자동 검증이라고 주장하지 않는다. 발의일/처리 단계/법적 효력은 추정하지 않는다.
- 준비는 capture+job+기존 private ProvisioningPlan으로 EvidenceBundle snapshot을 추가한다. document workspace/expected DB/승인 invites/기존 snapshot은 보존한다. raw bytes는 두 HTML을 담은 정확 capture artifact JSON bytes이며 raw_sha256으로 대조한다. text representation은 추출한 제안 내용만 담고 parser/profile/version 명시. citation은 전체 요약의 정확 start/end/prefix/suffix로 canonical 검증, support 판단 없음. 제목은 별도 operator metadata이며 source raw text로 합성하지 않는다.
- 같은 artifact+같은 IDs/job의 준비·등록 재실행은 같은 결과/신규0. 같은 ID에 다른 내용은 거부. 네트워크 재수집에서 HTML/CSRF/collected_at 변화가 새 버전을 뜻하는지 자동 판정하지 않는다. 운영자가 원문 대조하고 새 버전 IDs를 제공하며 기존 결과는 덮어쓰지 않는다. 이 한계를 README에 명시.
- worker CLI 두 단계: `issuedigest-capture-assembly PRIVATE_JOB PRIVATE_NEW_CAPTURE`, `issuedigest-prepare-assembly PRIVATE_JOB PRIVATE_CAPTURE PRIVATE_BASE_PLAN PRIVATE_NEW_PLAN`. 첫 단계만 네트워크2회, 둘째는 네트워크/DB/모델0. 기존 worker private file 보안 helpers(read_private/write_private) 재사용. 작업 파일 owned regular400/600·parents symlink 금지·output owned700/new600/원자배타 출력·고정 메시지·집계만 출력. 실패는 부분 output 없음, inputs 유지. output paths가 기존파일이면 요청 전에 거부 가능한 범위에서 확인하되 race는 배타 게시로 보호한다.
- 실제 등록은 기존 provision_cli의 --check-database/--apply만 사용하며 새 DB write path·초대 등록 로직·role·schema/API를 만들지 않는다. `SourcePresentation` 연결은 controller가 실제 제목 대조 후 기존 SDK로 명시한다. 앱은 라이브 조회가 아니라 마지막 저장한 capture이고 최신 상태/전문으로 표시하지 않는다.
- 기존 MySQL/수집 runtime/공용 checkout/system/main/운영 배포는 변경하지 않는다. 실제 사용자 session을 만들거나 대신 사용하지 않는다. 실제 raw/keys/ID/quote/hash는 private, 공개 테스트는 합성만 사용한다.

## Task 1 · 공식 원문 SDK·오프라인 등록 준비

- [x] 새 connector SDK, HTML 추출, strict capture/job 모델, workspace 설정과 worker CLI/순수 준비를 TDD로 구현한다. 기존 ProvisioningPlan 검증·불변ID alias 검사·private file helpers를 재사용/작게 공통화하되 HWPX 회귀를 유지한다. 새 package root/tests/mypy/pytest/uv lock을 등록한다.
- [x] 테스트: bounded fixed origin2요청·cookie/CSRF결합·redirect/HTTP/nonHTML/oversize stream/duplicateform/token/ID mismatch·script/숨김/중복/비정상HTML/Unicode, private file/invalid JSON/크기/실패부분파일·inputs보존, plan exactrepeat/IDconflict/기존승인불변/정확canonicalcitation. 기존 전용PG에서 준비 artifact의 기존 provision register→repeat0→보호read 연계를 합성 신원으로 확인한다. 실제 외부/운영 DB에 테스트하지 않는다.

구현 범위 packages/connectors, apps/worker, root workspace/lock·테스트 설정·관련README. 명세/진행·Sites/실제서버는 controller 소유. 새 UI/API/DB migration·네트워크 fixture·추정 날짜/이력은 추가하지 않는다.

## Task 2 · controller 실제 검증·인계

- [x] controller가 별도 private artifact로 실제 원천1건 capture·준비·offline검사·반복을 확인한다. 실제 개발 등록은 기존근거와 겹치지 않는 본문을 선별한 경우에만 전후백업/별도소유DB복원·기존인증보존 후 기존 앱 계정으로 명시 적용한다. 미확인·변경없음이면 추가0으로 기록한다.
- [ ] 독립 작업/전체 검토·적절한전체검사·Draft PR/진행기록/Sites 갱신. 개발본 적용 범위와 최신성/이력/자동수집 미구현을 구분한다. 사용자 UI 인터뷰는 제안·확정·미정으로 따로 보존한다. main/운영 게시 유예.
