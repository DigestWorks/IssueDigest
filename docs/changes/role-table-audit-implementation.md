# Lossless table audit implementation

2026-10-22 KST. Binding spec: [reviewed table design](role-application-table-audit.md). OpenSpec root is absent; use SDD without initializing OpenSpec.

## Global Constraints

Preserve all 446 existing non-Markdown tracked files, 480 actual-trial evidence files and 45 reviewed design evidence files. Only two new production modules and two new synthetic test modules. No actual provider calls, old runner executions, private sources in public files, application/API/UI/DB/worker/default-model changes, deployment or main merge. Do not transform new audit receipts into old v2 audit receipts. Read-only reuse of pure helpers and current exact original generation/report contracts is permitted. Caller owns borrowed Model. Single bounded request, 30 seconds, no-store, no retry/repair/fallback. Generation output1800 unchanged; audit min(1100,2500-generation.output), combined total20000/output2500. Validate exact runtime containers/types/required markers before dumps; no default restoration or normalization. Use TDD. Explicitly import test_shared_measurement_context_v2.restore_introduced_modules for fixture identity restoration. Implementers run focused and meaningful adjacent tests/static checks only; controller runs full QA/preservation/privacy/offline actual-source checks. Workers must not spawn subagents, push, deploy, run real providers or read private actual evidence.

## Task 1: Pure named-column packet codec

- [x] Implement and test strict codec.

Own packages/agents/src/issuedigest_agents/role_table_packet.py and packages/agents/tests/test_role_table_packet.py plus this checkbox. Read binding spec. Public interfaces: build_role_table_packet(source: Source, generation: RoleAliasGenerationV2) -> dict[str, Any]; decode_role_table_packet(source: Source, generation: RoleAliasGenerationV2, packet: Any) -> dict[str, Any]. Both are pure, sanitized RoleTablePacketError(ValueError). Build from exact current validated source/generation, _source_packet(_frame(generation).candidate_index), unchanged proposal/coverage/roles/slots. Canonical decoded packet has profile role-table-audit-v1 and input_format named-columns-v1 plus quotes/candidates/proposal/change_coverage/roles/scope_slots. Compare incoming decoded packet against freshly reconstructed canonical packet, not caller-asserted canonical input. Table packet has same own markers; candidates, quote sentences, scope_slots and each proposal collection are exact {columns,rows}, lists only, with complete explicit cells. Exact headers: contexts id,event,entity,scopes,period,status,condition,purpose,basis,baseline; events id,kind,actor,predicate,tense; bindings number,context,scopes,status_sentence,change; relations kind,from,to,support,cue; candidates id,quote_id,expression,atoms,separator,qualifiers,lexical_kind,sentence_ids; sentences id,text; scope_slots number,slots. Nested named objects unchanged. Other top-level keys preserved. Reject wrong keys/order/arity/types, tuple rows/list subclasses, bool-as-int, nested key/default/type drift, source/catalog/proposal tampering, missing original generation/frame/index markers and subclasses/unchecked copies before serialization. Strict recursive JSON tree comparison to canonical must distinguish scalar types and prohibit non-exact containers. Never merge, strip, infer, cut or repair. Preserve all source text/sentence order, blank sentences/whitespace/numeric atoms/units/qualifiers/ranges. Empty selection remains valid explicit empty tables with full source. Tests demonstrate red then green, roundtrip, each table boundary and nested/raw/actual tampering; synthetic only. Commit owned files and checkbox. Report exact API, TDD commands/results/static checks and concerns to supplied report path.

## Task 2: Borrowed-model table audit SDK

- [ ] Implement and test separate SDK and receipts.

Own packages/agents/src/issuedigest_agents/role_table_audit.py and packages/agents/tests/test_role_table_audit.py plus this checkbox. Consume Task1 APIs unchanged. Read binding spec. Expose RoleTableAuditGeneration, RoleTableAuditError, ROLE_TABLE_AUDIT_INSTRUCTIONS, role_table_audit_prompt(source,generation), create_role_table_auditor(model), run_role_table_auditor(auditor,source,generation), validate_role_table_audit_generation(source,result). Wrapper explicit required profile role-table-audit-v1, input_format named-columns-v1, report SemanticRoleAuditReport, prompt_sha256, instructions_sha256, audit_usage nullable, combined_usage. Tool audit_role_table_v1, identity issuedigest_role_table_audit_v1. Instructions exactly DECODER+SEMANTIC_ROLE_AUDIT_INSTRUCTIONS.replace('audit_role_aware_v2','audit_role_table_v1'), 3134 UTF8 bytes. DECODER exact (including final space): 'Tables {columns,rows} carry complete original objects: map each row cell to its exact named column, in order. All cells exist, including null and empty lists. Nested anchors/scopes/change stay named objects. Read candidates and scope slots the same way; concatenate each quote sentence table text column in row order with no separators, preserving blanks and whitespace. Never infer missing cells or merge rows. '. Reuse pure dynamic output/report helpers read-only, rename ToolOutput without oldreceipt fabrication. Reconstruct packet/current source/generation, schema, original report, own instruction/prompt hashes and stage/aggregate usage on stored raw and actual boundaries. Complete prompt+instructions+max(raw/normalizedschema)+2048+cap envelope <= actual remaining. Empty selection zero audit requests/aggregate1; normal audit1/aggregate2. Borrowed model exact lifecycle/settings, no-store/30sec and no retries. Unknown possibly-started failures combined null; known incomplete/token-limit/overflow failures retain raw usage. Late report/final validator errors, including RoleRequestError and own errors with default empty usage, must retain already observed outer usage and started status. Tests current role/slot diagnostics/unchanged proposal, own markers/hashes/no oldvalidator delegation, source/nested/container tampering, inclusive budgets/overflow, empty, request wire and raw incomplete response, unknown errors, late validation regression, max144 report diagnostics using existing synthetic fixtures. No new generation call. Focused/static/adjacent tests; commit/report as Task1.

## Controller gates

- [x] Independent task and whole-branch review, fresh full QA, offline actual-source reconstruction/envelopes, immutable manifest and privacy checks.
- [x] Canonical progress/tasks/README, Draft PR and Sites summary with previous version preserved; no merge/deployment of application.

## 구현·검증 범위 · 2026-10-22 한국 시간

별도 `role_table_packet`은 검증된 현재 원문과 exact `RoleAliasGenerationV2`로 표 입력을 만들고, 역변환 값을 새로 재구성한 canonical 데이터와 실제 타입까지 비교한다. 열 순서·행 길이·필수 null/빈 배열·중첩 값/표식과 원문의 문장 순서·공백·단위·범위 표현을 보존한다. 기존 원문/추출을 합치거나 의미를 고치지 않는다. 신규 합성208개·인접 포함376개 검사와 태스크 독립 검토 C0/I0/M0를 통과했다.

별도 `role_table_audit`은 자기 profile/input_format·prompt/지침 hash·사용량 영수증을 가진다. 기존 pure report/동적 출력 schema만 재사용하며 예전 audit 영수증으로 바꾸지 않는다. caller 소유 Model·1회/30초/no-store와 생성 실제 사용량 차감·합산total20,000/output2,500을 유지한다. 빈 선택은 검수0회, 검수 시작 가능/사용량 불명확은 합산null이다. 미완료·한도초과·최종 검증 실패에도 알려진 실제 사용량과 시작 상태를 보존한다. 신규 합성83개·인접373개가 통과했으며 전체QA와 독립 검토의 최종 상태는 진행 기록을 따른다.

### 기존 실제 자료의 오프라인 SDK 확인

| 자료 | 구현된 검수 envelope | 실제 생성 잔여total | output cap | 여유 |
| --- | ---: | ---: | ---: | ---: |
| G | 11,117 | 16,460 | 1,100 | 5,343 |
| H | 10,613 | 16,789 | 1,100 | 6,176 |
| I | 10,509 | 16,843 | 1,100 | 6,334 |
| J | 13,809 | 14,904 | 890 | 1,095 |
| K | 11,714 | 16,140 | 1,100 | 4,426 |

과거 실제 generation5개를 읽기 전용 재사용한 SDK의 결과이며, 원문/proposal을 정확히 복원하고 검토된 시제품 packet/3,134byte 지침과 일치했다. 실제 raw/normalized schema와 framing2,048·출력reserve를 포함한 UTF8 기반 예약량이다. mock HTTP5회와 저장 결과 재검증을 확인했고 실제 provider 요청0이다. 합성 검수 usage100/30은 기존 실제 generation usage를 바꾸지 않으며 의미/토큰/실제 비용 개선 증거가 아니다. 짧은 H/I의 지침/header overhead 증가는 그대로 남는다.

다음은 새 사전 기준/상한을 고정한 실제 table 검수 평가다. 실제 읽기 정확도·장문 완료·오탐/미탐·비용은 별도로 확인하고, 원래 H의 미탐·I의 역할 오인·J의 누락/오선택·G의 독립 사람 재판정 과제를 보존한다. 역할 후보 전체 grid는 이번에 추가하지 않는다. 전체 앱 예산/권한/내구 인수·앱 연결은 후속이며 이 SDK는 아직 개발 사이트 실행 경로를 바꾸지 않는다.

## 최종 구현 인수 · 2026-10-22 한국 시간

태스크별/전체 변경 독립 검토 C0/I0/M0, 새 전체8,099개 검사(Python7,279+JS820)와 린트/형식/타입/빌드/OpenAPI 계약 검증을 통과했다. 실패/skip/warning0이다. 코드가 같은 `1dcaa12`에서 전체QA를 실행했으며 이후 변경은 Markdown/정적 계획 요약뿐이다. 기존446실행/설정/테스트·480실제 평가 증거·45설계 증거가 불변임을 확인했고 공개 변경의 비공개 실제ID/질문/긴인용60종 부재 검사와 문서 링크 검사를 통과했다. 소유한 격리QA DB 한 개만 제거하고 포트 닫힘을 확인했다. 별도 검토 지적/유보 판단은 없다.

실제 모델 호출0·과거 runner 재실행0·앱/API/UI/DB/worker/기본 모델/서버/main 변경0이다. 구현 인수는 구조/저장/예산/회계의 범위이며 실제 의미 품질·비용 개선·앱 적용을 인증하지 않는다. PR/Sites 최종 게시 영수증은 진행 기록을 따른다.
