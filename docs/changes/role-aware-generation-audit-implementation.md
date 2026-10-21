# 전체 역할 생성·검수 SDK 구현

기준 설계: [역할 전체 참조·증감 연결·출력 배분](role-aware-generation-audit.md). 사용자 이어서 진행 지시에 따른 두 SDK 구현이며 실제 모델/앱 적용은 별도다. OpenSpec root=null을 확인했고 기존 격리 worktree의 새 feature branch에서 실행한다.

## Global Constraints

- 기존431개 실행/설정/테스트 파일·279개 실제 증거는 불변이다. 제품 코드는 아래 새 모듈/합성 테스트만 추가한다. 실제 모델 요청0·소진 runner 재실행0, 앱/API/DB/worker/UI·기본 모델·서버/main 변경0이다. 실제 원문·ID·긴 인용/키는 저장소/테스트에 넣지 않는다.
- 모든 새 모델/필드는 required이며 nullable과 누락을 구분한다. 정확한 concrete/actual nested 모델·tuple 검사를 직렬화 전에 수행한다. 동적 후보/문장/context/event/role/slot의 현재 catalog와 source를 다시 검증한다. canonical과 wire 이름 혼합/추가/누락/서브클래스/unchecked dict/list는 거부한다. 원래 generation의 저장 profile/status도 파싱/default 전에 검사한다.
- 원문/수량/단위·근사/공백/빈 문장을 줄이거나 context를 합치고 잘못된 역할을 수리하지 않는다. 현재 full v2 index와 원래 Source 재구성·정확 anchor/연속 지원 statement를 유지한다. 기존 generation profile로 번역해 영수증을 통과시키지 않는다. 새 지침/실제 schema/prompt·모든 저장/파생 값을 자신의 profile에서 재구성한다.
- 각 단계는 caller가 명시한 borrowed Model, 단일1요청/30초/no-store·retry/repair/fallback0이며 caller의 설정/클라이언트 lifecycle을 소유하지 않는다. total20,000, 합산output2,500, 새 generation output1,400·audit min(1,100,2,500-generation.output)이다. legacy output1,400을 소급하지 않는다. preflight는 UTF8(prompt+instructions)+max(raw,normalized schema)+framing2,048+해당output을 남은total과 비교한다. runtime/stored도 같은 usage 한도를 검사한다. aggregate requests2(빈검수면1)는 stage requests1과 구분한다.
- 전송 전 실패/전송 가능/usage불명·관측 초과/출력 미완료를 구분해 known usage와 may_have_started를 보존한다. unknown을0으로 합산하지 않는다. raw response usage는 SDK가 버리기 전에 narrow observer로 보존한다. observer는 Model.request를 추가 호출/재시도하거나 caller client를 열고 닫지 않는다.
- 검수는 원래 결과를 변경하지 않고 coverage/not_applicable/incomplete/uncertain/issues/no-issues를 구분한다. source/구조 일치나 no-issues는 의미/진실/중립/권한·전체 수치 추출·사람 검토 인증이 아니다. 전체 proposal의 전달도 오탐 해소 보장이 아니다.
- 새 테스트는 `test_shared_measurement_context_v2.restore_introduced_modules`를 명시 import해 modules+package attributes를 복원하고 fixture를 복제/기존 strict guard를 바꾸지 않는다. 중복 모듈/임의의 광범위 reload를 피하고 Task별 focused 후 새 tests→numeric_selection reload→numeric/contextual/measurement generation→role_guided→shared/v2→compact/scope audit의 관련 순서만 검사한다. 최종 전체QA는 controller가 맡는다.

## Task 1 — 명시 alias·방향 순수 계약과 bounded 생성 SDK

- [x] 새 `role_alias_contract.py`, `role_bounded_runtime.py`, `role_alias_generation.py`와 합성 `test_role_alias_contract.py`, `test_role_alias_generation.py`만 추가한다. 원래 공유 frame을 정확히 재구성하는 순수 계약과 새 방향 연결/해석·validator, caller 모델 단일 생성 경로를 구현한다. 생성 profile/tool/identity는 shared-role-aliases-v1 / fill_shared_role_aliases_v1 / issuedigest_shared_role_aliases_v1이다.
- [x] RoleAliasInput/RoleAliasFrame, build_role_alias_frame/validate_role_alias_frame과 RoleAliasGeneration/RoleAliasGenerationError, role_alias_prompt/create_role_alias_framer/run_role_alias_framer/validate_role_alias_generation을 제공한다. 구체 모델 내부 구조는 구현자가 간결하게 정하되 alias input·framev2·binding별 change 명시성/해석·source·새 영수증/known usage를 모두 재구성한다. 원래 frame input에 change를 몰래 추가하지 않는다.
- [x] 설계의 객체별 전송 이름만 받으며 canonical 필드를 끼워 넣거나 field alias의 populate_by_name으로 우회하지 않는다. root12/12/12/16·합산scope4·동적 slots/catalog·보고 사건 규칙을 유지한다. 각 binding의 change는 required nullable이다. 확정 direction은 exact evidence, uncertain은 nullable evidence·지원 statement, null은 미제안이며 자동으로 채우지 않는다. support는1..20연속/같은 인용·완전 수량/anchor 포함을 검사한다. enum 의미 연결은 자동 인증하지 않는다.
- [x] Task2 공유를 위해 pure `role_alias_contract._encode_shared_input(input: SharedMeasurementInput) -> dict`를 제공한다. 실제 canonical/nested 입력부터 객체별 alias로 정확 encode하며 change 필드는 추가하지 않는다. legacy full proposal은 이 helper 뒤 unavailable을 명시하고, 새 proposal은 실제 alias input의 required change를 보존한다.
- [x] 새 private 공통 `_run_role_request`를 role_bounded_runtime.py에 둬 Task2가 재사용할 수 있게 한다. 명시 model/prompt/tools/instructions/identity/total_limit/output_limit로 단일 bounded 요청을 수행하고 actual dynamic output/검증된 stage usage를 반환한다. sanitized error에는 nullable known_usage/may_have_started를 둔다. source/프레임 생성/credential ownership은 넣지 않는다. 기존 frozen observer/usage/schema/helper는 구조적으로 read-only 재사용할 수 있다.
- [x] 실제 동적 DTO/schema 정규화·prompt/instructions·1,400 reserve의 envelope를 무호출/mock로 확인한다. synthetic accepted/overflow/boundary·cold no-I/O·null/uncertain/반대방향 연결·다른 수치/인용/중복문맥·raw dict/missing markers/source/receipt drift·실제 mock wire/사용량/borrowed lifecycle을 TDD로 검사한다. controller가 private G/H/I/J/K 전체 용량을 확인하며 넘으면 원문/예산을 바꾸지 않고 알려진 거부로 기록해 형식 재검토한다. 실제 토큰/의미 개선이라고 표시하지 않는다.
- [x] focused lint/format/mypy·관련 순서 회귀·self review·범위 커밋/보고까지만 수행한다. 전체QA/다른 에이전트/PR/push/배포/실제 자료·모델 접근은 하지 않는다.

## Task 2 — 전체 원래 역할·coverage·명시 묶음 검수 SDK

- [x] 새 `role_aware_audit_contract.py`, `role_aware_audit.py`와 합성 `test_role_aware_audit_contract.py`, `test_role_aware_audit.py`만 추가한다. Task1 pure alias encoder/모델·source 검증·공통 runtime을 read-only 재사용한다. exact 새 RoleAliasGeneration/기존 SharedContextGenerationV2/CompactSharedContextGeneration만 각각 자신의 validator로 검증한다. Task1 파일은 수정하지 않는다.
- [x] RoleAwareAuditInput/RoleAwareAuditReport, build_role_aware_audit_report/validate_role_aware_audit_report와 RoleAwareAuditGeneration/RoleAwareAuditError, role_aware_audit_prompt/create_role_aware_auditor/run_role_aware_auditor/validate_role_aware_audit_generation을 제공한다. profile/tool/identity는 role-aware-audit-v1 / audit_role_aware_v1 / issuedigest_role_aware_audit_v1이다.
- [x] 전체 contexts/events/bindings/relations(목적·조건·비교 기준 포함)를 같은 객체별 alias로 정확 전달하고 hash를 보존한다. legacy에 change를 null로 채우지 않고 unavailable/네 역할을 명시하며 동적 enum에서 change_direction을 제외한다. 새 generation은 available/다섯 역할이다. 현재 수치별 scope 슬롯은 context+binding 순서이며 r1..r4를 넘지 않는다. 원래 generation과 proposal/coverage/source/hash를 저장부터 다시 재구성한다.
- [x] checks는 원래 선택 순서·number/status 정확1개이다. issues 최대12묶음/targets1..12·총확장144를 명시적으로 허용하는 새 계약이다. 같은 role/kind/evidence/support를 명시 열거 targets에만 확장하며 대상마다 source/수량/anchor/지원statement·현재 슬롯/non-null필드를 검사한다. missing exact evidence/슬롯null, unsupported scope 현재슬롯·다른role슬롯null, direction unsupported 새 nonnullchange를 요구한다. 빈/중복 targets·동일 진단/상충 check/무관 슬롯을 거부한다. 진단 내용/개수는 보존하며 새 확장 순서는 group/targets 순서다.
- [x] empty/no-issue/uncertain/hard/incomplete 규칙과 coverage 차이를 보수적으로 파생한다. 선택0은 Model0회/not_applicable·audit usage없음이다. baseline/period·목적/범위·운영/발표·정당한 소속과 direction을 구분하는 지침을 쓴다. 기존 실제 G gold를 고치거나 새 기준과 같은 것으로 덮지 않는다.
- [x] 검증된 원래 generation 사용량에서 잔여total과 min(1,100,2,500-generation.output)을 유도하고 실제 schema/envelope·runtime/stored 합산 한도를 검사한다. 공통 runtime 오류의 known/may_started를 받아 원래 known generation usage와 nullable audit usage를 보존한다. invalid 원래 generation의 usage를 신뢰하지 않는다. unknown을0으로 합산하지 않는다. 새로운 output1,400을 legacy에 소급하지 않는다.
- [x] TDD로 두 legacy/새 concrete·alias/full proposal/coverage·묶음의 교차 수치/인용/슬롯/중복·확장144/초과·incomplete·nullchange·증감 explicit/legacy거부·모든 stored marker/type/receipt/source drift·예산 inclusive/초과/0·unknown/관측 초과·0/1실제 mock wire/borrowed lifecycle을 검사한다. focused lint/format/mypy·관련 순서 회귀·self review·범위 커밋/보고까지만 한다. controller 자료/전체QA/다른 에이전트/실제 모델/PR/push/배포는 하지 않는다.

## Controller verification

- [x] Task별 독립 검토와 전체 branch 검토·필요 수정/재검토·최종 전체QA를 마친다. 기존431코드/279증거 SHA·G/H/I/J/K full source/원래 역할·실제 동적schema+지침+한도의 무호출 용량을 확인한다. legacy 관측 usage는 예시일 뿐 새 생성 사용량/의미 성공으로 해석하지 않는다.
- [ ] SDK/실제 인수/앱 적용 상태를 분리해 문서·마일스톤·Draft PR·Sites를 갱신한다. 소유 QA/current SDD만 private 보존 후 정리한다. 실제 provider 호출/앱·서버/main 배포는0으로 둔다. actual 요청/출력 충분성·의미/오탐·전체 앱 예산/권한/내구 실행은 후속이다.
