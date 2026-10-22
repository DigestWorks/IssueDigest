# Semantic balanced output implementation

2026-10-22 KST. Binding spec: [reviewed design](semantic-boundary-balanced-output.md). Implementation remains separate from real semantic acceptance and app integration.

## Global Constraints

Add only three production modules and their three synthetic test modules. Preserve all 440 existing non-Markdown tracked files and all 361 historical actual-trial evidence files. No real provider calls, old trial reruns, private source in public files, app/API/UI/DB/worker/default-model changes, server deployment or main merge. Borrowed model, no store, single request/30 seconds, no retry/repair/fallback. Total 20000 and combined output 2500 unchanged. Validate actual exact types, required nullable markers before serialization, full source/catalog/schema/hash/usage reconstruction. Do not translate v2 receipts to v1 to reuse a validator. Synthetic tests explicitly reuse test_shared_measurement_context_v2.restore_introduced_modules to restore import identity. Follow TDD; focused tests only for implementers. Controller owns full QA, immutable manifests, offline real-source checks, review, PR and Sites. No subagents from workers.

## Task 1: Balanced generation

- [x] Implement and test new balanced generation.

Own only packages/agents/src/issuedigest_agents/balanced_role_generation.py and packages/agents/tests/test_balanced_role_generation.py plus this checkbox. Read binding design. Add RoleAliasGenerationV2, BalancedRoleGenerationError, balanced_role_prompt(source), create_balanced_role_framer(*, model), run_balanced_role_framer(source, *, model), validate_balanced_role_generation(source,result). Match old callable/run signatures if signatures here conflict with existing established callable convention; report exact final signatures. Profile shared-role-aliases-v2, tool fill_shared_role_aliases_v2, identity issuedigest_shared_role_aliases_v2. Exact old ROLE_ALIAS_INSTRUCTIONS with tool v1 replaced by v2 only; expose BALANCED_ROLE_INSTRUCTIONS. Generation output 1800 inclusive, total 20000. Reuse pure RoleAliasFrame/Input/resolver and bounded runtime; never create old generation receipts. Full stored dictionary and actual __dict__ frame/index marker validation before dump. Hash own prompt and instructions; reconstruct source, dynamic schema, frame and observed usage. Preserve known overflow usage, unknown/may-have-started failure semantics and explicit provider incomplete rejection. Tests: red then green; inclusive1800/overflow1801, total20000, schema envelope, all required markers raw/actual and nested/container/subclass tampering, source drift, own profiles/hashes, one/no-store borrowed model wire and incomplete valid-JSON raw usage. Reuse existing synthetic fixtures where suitable, no private actual evidence. Run focused tests/static checks and meaningful adjacent regressions, not full npm check. Commit only owned files and report exact commands/counts/TDD/concerns in report path supplied by controller.

## Task 2: Semantic audit contract and SDK

- [x] Implement and test semantic v2 audit.

Own only packages/agents/src/issuedigest_agents/semantic_role_audit_contract.py, semantic_role_audit.py and matching packages/agents/tests/test_semantic_role_audit_contract.py, test_semantic_role_audit.py plus this checkbox. Accept exact new RoleAliasGenerationV2 only; legacy/v1 rejected. Public APIs use semantic_role_* names analogous to role_aware_* existing contracts. Report role-aware-audit-report-v2; generation role-aware-audit-v2; tool audit_role_aware_v2; identity issuedigest_role_aware_v2. Copy exact final English instructions fenced in binding design, 2722 UTF8 bytes. Preserve unchanged full source/proposal and original hashes, five roles/current scope slots, explicit12 groups*12 targets=144, per-target full quantity/evidence/support/quote/order/slot/nonnull checks, duplicate and check contradictions, conservative empty/not_applicable/incomplete/uncertain/hard statuses. Reuse pure DTO/span helpers but no fake v1 generation or old coupled _build. Audit output min(1100,2500-generation.output_tokens); remaining total20000-generation.input_tokens-generation.output_tokens. Actual combined usage/request bounds including failure and nullable unknown started failures. Strict required markers/raw/actual/nested/container before dumps. TDD synthetic positive/negative/ambiguous role rules, complete/incomplete/empty,144 boundary/overflow, budgets700/dynamic remaining, raw provider incomplete/usage and source drift/tampering. Use synthetic role-case fixtures to verify unchanged proposals, exact evidence and hard/uncertain diagnostic representations under the instructions; do not claim a mock proves the model chooses the right diagnosis. Structural tests cannot claim semantic accuracy. Existing coupled audit loop cannot be reused by forging v1 receipts; avoid verbatim duplication by decomposing the new pure boundary into focused support/target/status helpers while reusing unchanged DTO/span utilities. No old code changes. Focused tests/static and ordered adjacent regressions only; commit/report as Task1.

## Controller gate

- [x] Independent task and whole-branch review, fresh full QA, preservation/privacy and offline actual-source envelope checks.
- [ ] Update canonical progress/tasks and Sites; publish Draft PR without merge or deployment.

## 구현과 확인 결과 · 2026-10-22 한국 시간

새 실행 경로는 생성 `shared-role-aliases-v2`와 검수 `role-aware-audit-v2`다. 기존 경로/영수증/실제 평가를 바꾸거나 변환하지 않는다. 원문·현재 후보와 frame/index 필수 표식·정확한 실제 타입/튜플을 직렬화 전에 확인하고, 자기 prompt/지침·schema·해시/usage를 재구성한다. 검수 report는 새 concrete generation만 받으며 다섯 역할·현재 scope 순서와 전체 proposal을 유지한다. 최대12묶음의 각 명시 대상12개를 개별 검증해 최대144진단을 만든다. 누락/근거 없음과 불확실/미완료를 구분하며 원래 결과를 수리하지 않는다.

생성 출력은1,800, 검수는 `min(1,100,2,500-generation.output)`이며 실제 생성의 input/output을 total20,000에서 차감한다. 생성1,800 사용 시 검수700이다. borrowed Model·한 번/30초/no-store·retry/repair/fallback0을 유지한다. 실패해도 알려진 사용량과 요청 발생 여부를 남기고, 시작 가능하지만 사용량이 불명확한 검수는 합산0으로 만들지 않는다. 태스크 검토에서 발견한 생성 최종 검증 실패 시 사용량 소실을 수정했고, 검수에도 같은 경계의 회귀를 추가했다.

신규 생성61·검수165(계약107/SDK58)는 합성 입력·FunctionModel·mock HTTP 검증이다. 태스크별 인접 검사는323/551개이며 실제 모델 정확도 증거가 아니다. 독립 태스크/전체 검토 최종 C0/I0/M0·새 전체7,808개 검사(Python6,988+JS820)·린트/형식/타입/빌드/OpenAPI 계약 검증을 통과했다. 실패/skip/warning0이다. 전체QA는 코드가 같은 `759add7`에서 검증했고 기존440실행/설정/테스트·361실제 증거 보존과 공개 비공개값 부재 검사를 확인했다. 실제 의미 품질/앱 적용 완료와는 구분한다.

### 실제 자료의 오프라인 전송 구조

| 참조 자료 | 생성 envelope / cap1,800 | 검수 envelope / cap700 | 가정한 잔여total | 여유 |
| --- | ---: | ---: | ---: | ---: |
| G | 15,398 | 10,487 | 15,228 | 4,741 |
| H | 15,075 | 9,879 | 15,353 | 5,474 |
| I | 15,113 | 9,867 | 15,350 | 5,483 |
| J | 17,437 | 14,600 | 14,714 | 114 |
| K | 15,611 | 11,662 | 15,324 | 3,662 |

새 SDK의 실제 raw/normalized 동적 schema·정확2,722byte 지침·완전한 원문/참조 proposal을 사용한 UTF8 envelope다. 설계 mock보다 새 schema 명칭으로 검수39byte가 늘었으며 설계 기록은 그대로 남긴다. 가정한 잔여total은 과거 input이 같고 새 생성이1,800을 모두 쓴다는 반사실 계산이다. reference generation usage100/30은 FunctionModel 합성값으로 실제 새 생성 사용량이 아니다. J는 완전한 과거 proposal 참조이며 잘린 실제 응답을 복구하거나 기존 의미 오류를 고친 결과가 아니다. K는 최신 완전한 과거 v1 방향을 포함한다. 최종10개 wire body를 mock HTTP에서 확인했고(준비/최종 두 실행 총20개), provider 요청은0이다. J여유114는 향후 출력 완료·token/비용/의미 정확도 보장이 아니다.

### 남은 인수

새 실제 평가에는 사전 고정 자료/판정 기준·비용 상한이 필요하다. 생성 완료, 정보 누락, 검수 오탐/미탐, 장문 출력 충분성을 각각 확인한다. 기존 소진 runner·실패 비용·gold/점수는 변경하거나 재실행하지 않는다. 알려진 G의 분쟁 경계는 독립 사람 재판정이 남아 있고 새 AI 검토를 사람 정답으로 쓰지 않는다. 앱 전체24,000/output2,500 회계·권한·내구 인수를 마친 뒤 연결한다. 현재 앱/API/UI/DB/worker·기본 모델·서버/main은 변경하지 않는다.
