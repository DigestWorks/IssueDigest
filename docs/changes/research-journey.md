# 첫 실제 조사 흐름

2026-10-15. 사용자 승인: 법안을 선택하고 질문하여 실제 자료 기반 AI 결과를 얻고 근거를 확인·저장/재열람하는 흐름으로 개선한다. 기반 구현만 제품 진척처럼 보고하지 않는다. OpenSpec root=null, 기존 명세 + SDD/TDD/독립 검토를 사용한다. R1~R6/D011/D013/D015 유지. main/운영 배포 유예, 개인 개발 HTTPS 반영은 승인됨.

## 제품·수용 기준

첫 화면은 “이슈 조사”, “자료”, “저장한 조사”로 이해할 수 있어야 한다. 내부 작업 공간/UUID/원천ID는 이름·제목으로 표시하지 않는다. 실제 법안명/자료 제목·의안번호·제안일을 표시한다. 법안 카드에서 선택/질문·AI 핵심 정리를 시작하며 선택 자료와 질문을 유지한다. 첫 질문 전 가짜 결과/AI 예시는 표시하지 않는다. AI 요청 중 접수→자료 찾기→분석→근거 확인 상태를 보고, 실패/자료 부족/예산 한도와 취소를 구분한다. 성공 결과는 질문에 맞는 요약/비교/타임라인/근거 모듈을 구성한다. 인용 클릭으로 검증된 본문·저장 인용 위치를 열고 후속 질문/자동 저장/동료의 같은 결과 재열람이 가능해야 한다. 새로고침은 재과금 없이 진행 또는 저장 결과를 복구한다.

자료9건/기존 계정·초대·권한을 보존한다. 기존 법안8건은 기본 정보이고 현재 처리 상태/법안 조문/영향을 검증한 자료가 아님을 구분한다. 선택8건에 수집 처리 이력이0건인 것을 확인했다. 미수집을 실제 처리 이벤트 없음으로 주장하지 않는다. 기존 법안 처리 이력/제안 내용은 대응되는 원자료가 확인될 때 추가한다. AI는 자료에 없는 효과/찬반/사실을 만들어내지 않으며, 부족하면 부족한 내용을 알려 준다.

## 기술·안전·범위

- PydanticAI + DBOS/PostgreSQL 실제 연결, React Router/FastAPI/기존 CanvasBundle/CanvasView 재사용. 새로운 임시 실행 엔진·메모리 결과 저장·예제 응답 fallback 없음. 기능은 수동 질문 트리거부터 완성한다. 정기 수집·자동 변경 감지는 별도 후속이며 이번 완료로 표시하지 않는다.
- 새로운 source presentation sidecar는 snapshot/workspace별 검증된 표시 제목·법안번호/제안일 등 표시 메타데이터를 저장한다. 기존 SourceDocument/EvidenceBundle 필드를 바꿔 불변 hash/과거 스냅샷을 깨지 않는다. 알려진 법안 메타데이터 profile의 첫줄은 실제 법안명으로 쓸 수 있고, 기타는 안전한 종류별 기본명으로 fallback한다. source_id/UUID fallback은 금지한다.
- 보호 `/api/v1/workspaces/{workspace_id}/research/sources`, `/research` GET/POST, `/research/{run_id}` GET, `/research/{run_id}/cancel` POST. 기존 cookie 세션/현재 membership 재확인·same-origin POST·query 금지/JSON 중복key/크기/고정오류/no-store/X-Request-ID를 유지한다. 읽기는 현재 member, 생성/취소는 owner/editor. 첫 실제 계정은 owner임을 읽기 확인했다. 다른 공간/비회원/폐기·만료는 거부한다. 실제 사용자 세션을 임의 발급/대신 사용하지 않는다.
- POST: request_id UUID4 idempotency, question1..1500자, snapshot_ids1..3개 중복 없음, parent_run_id optional. 같은 키/동일 입력은 같은 결과, 다른 입력은409. actor/workspace별 DB 권한 확인 후 저장한다. parent는 같은 workspace의 완료 조사이고 그 결과/질문과 현재 선택을 제한된 후속 맥락으로 사용한다. 질문·결과는 로그/URL에 넣지 않는다.
- PostgreSQL 새 revision0005: source 표시 메타데이터와 조사 run/result/event/예산 예약 저장(필요한 최소 테이블). queued/retrieving/generating/validating/completed/failed/cancelled 상태·증분 이벤트·결과/선택 버전/질문/모델/토큰 사용량 보존. 새 질문만 과금, 새로고침/GET은 모델 호출0. 최종 결과 불변. 현재 membership을 생성/조회/완료 때 재검사한다. 취소 후 결과를 게시하지 않는다. 모든 완료 조사는 자동 저장되며 별도의 가짜 저장 버튼을 만들지 않는다.
- 글로벌 월 AI 예약 한도 USD10, 건당 보수적 USD0.25 예약·월 최대40건, 공간별 동시 active1. 트랜잭션/잠금으로 경쟁·중복 요청에서도 초과하지 않는다. 실패/취소/접수불명도 예약을 자동 반환하지 않아 보수적 상한을 유지한다. configured model은 우선 기존 wireframe과 같은 gpt-5.4-mini만 허용한다. request limit2·최대출력2500/request·합계 토큰24000·timeout60초·provider 자동 재시도0/출력 수정 재시도0, 명시 수동 재요청만 새run. 가격상 무리한 모델을 operator가 넣어 예약액을 우회하지 못하게 한다.
- PydanticAI-slim[openai,dbos]2.56.0, DBOS3.2.0을 공식 PyPI metadata로 확인했다. 기존 fixed 의존성과 uv로 호환성 확인/lock. Responses API `store=False`, server-only key. 키 미설정은 기능 연결 대기로 표시하며 모델 응답을 꾸미지 않는다. API startup/import에서 DB/network/migration/model 호출 금지. 선택 기존 방식에 따라 명시 configured runtime만 연구 저장소를 연결한다.
- 별도 worker는 queued run을 poll하고 안정된 run UUID 기반 DBOS workflow ID로 실행한다. DBOSDurability capability와 명명된 PydanticAI agent는 DBOS.launch 전 등록한다. queued→workflow 시작의 틈에서도 job이 유실되지 않도록 별도 비내구 claim을 먼저 확정하지 않는다. launch run_migrations=False, admin server/telemetry/원문 로그 off, loopback/로컬 프로세스만 사용한다. DBOS.migrate는 별도 owner 단계(application_role 기존앱역할)이며 runtime에 DDL을 주지 않는다. 프로세스 재시작·checkpoint/replay·중복 dispatch를 실제 전용 PG에서 검증한다. 유료 요청 접수 후 응답 유실의 재과금 불확실성은 자동 provider 재시도를 끄고 보수적 예약·실패 분류로 제한하며 exactly-once 과금을 주장하지 않는다.
- worker는 actor의 현재 enabled membership을 조회하고 최대5개 source/총12000자 근거만 얻는다. seed 자료를 포함하고 질문 단어 기반 기존 검색을 재사용하여 관련 자료를 찾는다. 현재9건을 전부 정답이라고 취급하지 않는다. 읽기 전용 source 조회 도구를 PydanticAI에 등록할 수 있으나 외부 웹/셸/임의URL/사용자 자격 증명 도구는 없다. untrusted source/question의 지시를 실행하지 않는다.
- AI는 제한된 구조화 결과에서 모듈 종류·제목·주장과 citation IDs를 선택한다. 서버는 현재 선택의 canonical citation/버전/출처로 대조하고 기존 CanvasBundle을 구성/검증한다. AI 해석은 inference + derivation으로 표시하고 support 확인을 가장하지 않는다. 날짜는 인용의 실제 날짜만 timeline에 사용하고, 표/차트 수치를 만들어내지 않는다. 초기 모듈은 summary/comparison/timeline/evidence이며 chart/graph는 실제 수치/관계 근거 없으면 생성하지 않는다. 요약/비교/시간질문에 서로 다른 모듈 조합이 가능한지 검증한다. 인용/후속 질문 액션을 실제 앱에 연결한다.
- 웹은 새 연구 API의 원시 응답/identity·상태·Canvas 참조·날짜·금액·개수 한도를 검증한다. 모델이 만든 HTML/JS 실행 없음. 기존 렌더러에 title map을 전달하여 출처ID를 사용자 이름으로 보여주지 않는다. reader의 실제 자료 제목도 표시한다. 원문 링크·인용 선택·기존 인증을 보존한다. UI는 차분한 편집 화면, 큰 소개문/마케팅 배너/그라데이션/개발 진단 반복 없음. 390px/키보드/로딩·실패·취소·빈 목록과 모바일 사용을 확인한다.
- 실제 데이터/키/이메일/UUID/서버 접속값은 private에만 보존. 실제 DB를 test/reset/restore하지 않는다. 운영 원본·MySQL은 읽기 전용이며 새 역할/전체 권한 확대 없음. 실제 앱 적용 전후 백업·별도 소유DB 복원·기존9건/인증 보존·보호 조회를 확인한다. Sites는 기존 탭을 열지 않고 요약·과거 기록 보존.

## 공식 근거

- https://pydantic.dev/docs/ai/capabilities/durable_execution/dbos/ (DBOSDurability/사전 등록/사용자 workflow)
- https://pydantic.dev/docs/ai/models/openai/ (OpenAIResponsesModel/settings/provider)
- https://docs.dbos.dev/python/reference/configuration (run_migrations=False)
- https://docs.dbos.dev/python/reference/dbos-class (명시 DBOS.migrate/application_role)
- https://developers.openai.com/api/docs/models/gpt-5.4-mini (Responses/구조화 출력·함수 호출)

## Task 1 · 실제 조사 backend·내구 실행·typed client

- [x] 위 보호 source catalog/run 생성·진행/결과 목록/재열람·취소/예산/idempotency/authority·표시 제목 계약과 PostgreSQL migration/repository를 TDD로 구현한다.
- [x] PydanticAI/DBOS 워커·구조화 결과→검증 CanvasBundle·usage/fixederrors·재시작/중복 dispatch/명시 runtime·READMEs를 구현하고 필요한 종속성/계약/typed client를 고정한다.

수정 범위 packages/domain·storage·agents·api-client, apps/api·worker, root Python workspace 설정/lock/테스트, 관련 READMEs. 기존web UI는 Task2 담당. 하위 구현자는 전체 spec을 읽고 명시한 경계 안에서 단순한 계약을 결정해 문서화한다. DBOS/AI 공식 SDK 소스·문서를 확인하며 기억으로 API를 추측하지 않는다. 실제 외부 유료 호출/서버/비밀값은 controller만 다룬다. 단위/권한/트랜잭션/예산경쟁/정확 참조/직접 CLI/API/실제 DBOS 재시작은 합성 전용PG로 검증한다.

## Task 2 · 사용 가능한 조사 화면

- [ ] 기존 와이어프레임 질문/결과 상호작용을 참고하고 새 typed client/CanvasView로 법안 선택→AI 질문/진행→생성 모듈/근거 액션→후속 질문→자동 저장 목록/새로고침·재열람을 연결한다.
- [x] 실제 이름/제목 중심 카드·내부 공간/ID 제거·빈 상태·실패·취소·모바일/키보드/인용 선택·새로고침 중복 호출0을 검증한다. 이전 원문 검색/reader는 보조 자료보기 경로로 보존한다.

수정 범위 apps/web·packages/ui와 합성 UI 테스트/README. 새 backend 계약을 먼저 읽고 model payload·schema를 새로 만들지 않는다. 실제 동작 없는 도구·AI 전 결과·예시/추정 최신 이벤트/가짜차트는 추가하지 않는다.

## Task 3 · controller 실제 적용·검증·인계

- [ ] 기존 수집 법안/내용/처리 이력과 공식 자료를 대조해 실제 근거를 확장한다. 이름·출처·기본 정보/과거 이력·전문·AI 해석을 구분한다. 불확실한 자료는 보류한다.
- [ ] 작업/전체 독립 리뷰·전용PG 포함 전체 검사·실제 HTTP/DB 브라우저 여정 후, 백업·명시 migration/DBOS 설정·기존 앱 역할·worker/API·개발 HTTPS에 반영한다. 승인 키가 준비되면 실제 AI 요청과 저장/재열람·다른 질문 모듈·부족/실패를 확인한다.
- [ ] PR·레포 문서·Sites 요약/이전 기록 보존·정리. main/운영 배포 유예 유지. 실제 AI가 막히면 그 상태와 사용자 입력을 정확히 남기며 완료를 가장하지 않는다.
