# 원문 중복 축소·역할 검수 SDK 구현

2026-10-21. 상태: 진행. [확정 설계](compact-source-scope-audit.md)의 구현1~3단계를 수행한다. 새 실제 의미/보안 인수·앱 연결은 별도다.

## Global Constraints

- 기존425개 실행/설정 파일과173개 실제 증거·요청/지침/결과/fixture는 불변이다. 새 SDK/테스트만 추가하고 API/DB/worker/UI·기본 모델·서버/main은 바꾸지 않는다. 실제 모델 호출0, 소진 runner 재실행0이다. 테스트/문서에 실제 원문·UUID·긴 인용/키를 넣지 않는다. controller만 이전 G/H/I/J를 오프라인으로 확인한다.
- 확정 설계의 profile/tool/identity·완전한 문장 분할/원문 복원·전체 v2 index/현재 source 재구성·동적 enum/slot·무수리·단일 bounded borrowed Model/30초/no-store·caller lifecycle을 그대로 구현한다. 기존 validator/profile로 번역해 새 요청을 통과시키거나 monkey patch/전역 교체를 하지 않는다.
- 실제 canonical/nested model·tuple 검사는 직렬화 전에 수행한다. 저장 결과는 현재 source·해당 concrete generation부터 전체 재구성한다. 서브클래스/unchecked dict/list·추가/누락/위조/다른 profile·source drift/receipt 불일치를 전체 거부하고 정리된 오류/알려진 stage usage만 보존한다. unknown을0/무료로 세지 않는다.
- 별도 검수는 선택된 네 역할만 진단하고 원래 generation을 변경하지 않는다. 구조/원문 일치는 의미/진실/중립/권한/완전성·사람 검토 인증이 아니다. 기관명이 같은 경우를 일괄 금지하지 않는다. no_issues_flagged·not_applicable·uncertain/incomplete·issues_flagged를 구분하고 검수 미실행/실패를 정상 검수로 세지 않는다.
- 생성+검수 합산total20,000/output2,500, 검수 추가1요청/retry/repair/fallback0이다. remaining_total=20,000-generation(input+output), audit_output_limit=min(1,000,2,500-generation.output)이며 UTF8(prompt+instructions)+max(raw,normalized schema)+2,048+audit_output_limit이 잔여를 초과하거나 출력 잔여0이면 송신0이다. runtime·stored usage 합산도 같은 잔여를 지킨다. 입력 generation의 usage가 검증되지 않으면 검수를 호출하지 않는다.
- 기존 model runtime/schema/anchor helper는 공통 구조의 읽기 전용 사용에 한정해 재사용할 수 있다. 새 module import/reload 테스트는 `test_shared_measurement_context_v2.restore_introduced_modules` fixture를 명시 import해 sys.modules와 package attribute를 모두 복원한다. 동일 fixture를 복제하거나 기존 테스트/strict guard를 수정하지 않는다. 새 테스트→selection reload→legacy/shared/compact/audit 순서도 검사한다. 테스트 수 늘리기 대신 변경 경계와 실제 mock wire에 집중한다.

## Task 1 — 무손실 compact 생성 SDK

- [x] 새 `packages/agents/src/issuedigest_agents/compact_shared_context.py`와 `packages/agents/tests/test_compact_shared_context.py`를 TDD로 구현한다. `CompactSharedContextGeneration`, `compact_shared_context_prompt`, `create_compact_shared_context_framer`, `run_compact_shared_context_framer`, `validate_compact_shared_context_generation`을 제공한다. 오류는 별도 `CompactSharedContextError`로 정리한다. profile `compact-shared-context-v1`, tool `fill_compact_shared_context_v1`, identity `issuedigest_compact_shared_context_v1`이다.
- [x] 현재 source→v2 index→각 인용의 완전한 문장 목록/로컬 q1..q20·전체 후보를 만드는 private `_source_packet(index)`를 역할 검수에서도 재사용할 수 있게 둔다. source canonical preflight 후에만 이 helper를 사용한다. 문장 start/end의0..len 연속 분할/동일 인용·원래 순서/정확 substring·연결 원문 일치를 검사한다. 검수 대상이 아닌 문장/빈 문장/공백도 모두 보존한다. 모델에 snapshot/workspace/citation UUID를 보내지 않지만 서버의 원래 index/provenance와 source 검증을 유지한다. 공개 helper를 추가할 필요는 없다.
- [x] 기존 SharedMeasurementFrameV2·v2의 `_build_shared_output_v2`와 동적 schema/enum·known usage·bounded request runtime을 재사용하고 새 prompt/instructions 해시와 현행 동적 입력을 별도로 검증한다. 지침은 v2 지침의 tool 이름을 바꾸고 문장 목록 형식 설명만 추가한다. `_preflight(source)` 및 `COMPACT_SHARED_CONTEXT_INSTRUCTIONS`를 controller 오프라인 점검에 제공한다. 시제품 수치와 똑같이 맞추기 위해 의미 지침을 삭제하지 않는다.
- [x] 합성 여러 인용/Unicode·공백·빈 문장/quote 매핑·수치/단위·근사·strict nested 타입/서브클래스·예산 inclusive 경계/초과 송신0·단일 runtime usage/실패·mock Responses wire·stored/source/receipt drift·무I/O·이전 요청 불변을 확인한다. focused lint/format/mypy·필요한 순서 회귀를 실행하고 커밋/보고한다. 전체QA·유료 호출/서버·PR/Sites는 controller가 맡는다.

## Task 2 — 무수리 역할 검수 계약·bounded SDK

- [x] 새 `scope_audit_contract.py`, `scope_role_audit.py`와 각각의 합성 테스트를 추가한다. 확정 설계의 projection/입력 체크/원문 위치·지원 statement/파생 상태/usage·영수증 재구성을 구현한다. Task1의 private `_source_packet`과 generation validator, 기존 v2 concrete generation validator를 재사용한다. canonical 입력 generation은 정확한 SharedContextGenerationV2 또는 CompactSharedContextGeneration만 받는다. source에서 직접 생성하지 않으며 어떤 생성기도 다시 호출하지 않는다.
- [x] 계약에는 `ScopeAuditInput`(ordered checks/max12, issues/max12, incomplete), 원래 generation·canonical 입력·해석된 위치/파생 상태를 보존하는 `ScopeAuditReport`를 두고 pure `build_scope_audit_report`, `validate_scope_audit_report`를 제공한다. 진단의 role/kind/slot/anchor/support_sentence_ids, 중복·서로 다른 source/수치·check와 진단의 일치·empty/incomplete 규칙은 확정 설계를 따른다. 수치 후보 선택의 전체 누락을 검수했다고 주장하지 않는다.
- [x] `ScopeRoleAuditGeneration`, `scope_role_audit_prompt`, `create_scope_role_auditor`, `run_scope_role_auditor`, `validate_scope_role_audit_generation`, 정리된 `ScopeRoleAuditError`를 제공한다. profile `scope-role-audit-v1`, tool `audit_scope_roles_v1`, identity `issuedigest_scope_role_audit_v1`이다. 검수 모델은 필수 borrowed Model이다. stored 결과에 원래 generation·source/projection/prompt/instructions 해시·canonical 진단·해석된 span/파생 상태·audit usage/합산 usage를 기록해 전체 재검증한다. 순수 report와 runtime wrapper가 같은 정보를 중복 보관할 필요는 없다.
- [x] 선택0이면 모델0회·audit usage없음/not_applicable로 구분한다. 정상 비어 있는 진단은 모든 선택 수치에 no_issue_found check가 있고 incomplete=false일 때만 no_issues_flagged다. incomplete=true에서 진단 없는 수치는 uncertain이어야 한다. hard issue가 있으면 issues_flagged가 우선이지만 incomplete는 보존하며 정상 승인으로 표시하지 않는다.
- [x] stage별 known usage의 requests는 각각1이며 검수 완료의 합산 requests는2(빈 선택은 검수0회·합산1)로 검증한다. 기존 `_bounded_usage`의 단일 요청 규칙을 합산 객체에 적용하거나 느슨하게 바꾸지 않는다.
- [x] known generation usage에서 잔여 total/output을 유도하고 preflight/schema·실제 runtime·stored 합산 한도를 검사한다. 검수 송신 전 실패와 송신했을 수 있으나 usage를 모르는 실패를 구분하는 오류 metadata로 원래 known generation usage·known audit usage를 각각 보존한다. 알려지지 않은 audit usage를0으로 합산한 완전한 total을 만들지 않는다. 자동 재요청·수정·fallback은0이다.
- [x] TDD로 순수 검수·동적 output actual 타입·source/field/slot/statement/anchor·중복/모순·incomplete·stored drift·합산 budget의 inclusive/초과/출력0·unknown usage·무호출/단일 mock wire/borrowed lifecycle을 검증한다. 서로 다른 지역 누락·사업 연도 누락/운영 주체 오인·정당한 기관 소속·연결 불명은 독립 합성 사례로 표현하되 AI 의미 성공으로 세지 않는다. 기존 fixture import를 재사용한다. focused lint/format/mypy·순서 회귀·커밋/보고까지만 맡는다.

## Controller verification

- [x] 태스크별 독립 검토와 전체 branch 검토·적절한 전체QA를 완료한다. 기존425파일/173증거 보존, G/H/I/J 원문 전체 compact 요청 용량·기존 generation의 검수 요청/잔여 예산을 오프라인 확인한다. 이는 새 compact usage/의미 개선 관측이 아니다.
- [ ] 소유 QA/SDD 정리·문서/마일스톤·Draft PR/Sites를 갱신한다. 새 실제 의미/보안·충분한 출력·내구 회계/권한·전체 앱 인수는 후속으로 표시한다. 앱·main/운영을 배포하지 않는다.
