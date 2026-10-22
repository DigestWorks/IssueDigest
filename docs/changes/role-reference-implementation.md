# Role reference coverage implementation

2026-10-22 KST. Binding [reviewed design](role-reference-coverage.md). Existing linked worktree clean, base6fa6a1488ccee7c3ace24a84b8e7363a8f0d02d3, openspec root:null (no init). One pure contract task; no model requests or app wiring.

## Global Constraints

Freeze456 existing non-Markdown tracked files,642 actual evidence (previous562+80),45+59+17 prior design files. Own only new packages/agents/src/issuedigest_agents/role_reference_coverage.py and matching packages/agents/tests/test_role_reference_coverage.py plus own task checkbox. No existing module/test/config/dependency edits, providers/network/private actual sources/gold/old runners, subagents/fullQA/push/deploy. Controller handles independent reviews, fullQA, offline actual sources, preservation/privacy, docs/PR/Sites and own QA/SDD cleanup. Reuse strict original/raw/actual validators/locators read-only. TDD first, restore_introduced_modules fixture, meaningful focused/adjacent/static only. No role conversion, old score changes, semantic truth/materiality/approval/hardmissing/repair or extra usage receipts.

## Task 1: Canonical carrier inventory and strict report

- [x] Implement and test pure source reference report.

APIs build_role_reference_coverage(source:Source,link:RoleLinkGeneration|dict[str,Any])->RoleReferenceCoverage; validate_role_reference_coverage(source:Source,result:RoleReferenceCoverage|dict[str,Any])->RoleReferenceCoverage. RoleReferenceCoverageError is sanitized fixed message/no cause/source/partialoutput. Validate exact original Source and original link with original strict raw/actual guards BEFORE dumps; then validate_role_link_generation. Validators also guard entire original new report and recursively required markers/scalar/container/model identity before any serialization/default restoration, not just its copied original_link. No unchecked copies/subclasses/raw tuples or int/bool coercion. Full current source/link/catalog/domain/carriers/rows/counts/hash/rules reconstruction; compare every field. Return canonical immutable-value DTOs in existing _StrictModel style (do not change base class).

All DTO fields required/no defaults:
- ReferenceCarrier: carrier_id:str,number:str,path:str,field Literal entity/period/condition/purpose/basis/baseline/context_scope/binding_scope/reporting_actor/reporting_predicate/change_evidence/relation_cue/quantity/status_context,category Literal primary/auxiliary,span:ExactSpan.
- ReferenceWitness: carrier_id:str,overlap Literal exact/contains/partial.
- ReferenceRow: hint_id:str,number:str,link_state:LinkState,roles:tuple[LinkRole,...],hint:ExactSpan,lexical_status Literal exact_reference/containing_reference/partial_reference/no_reference_in_selected_fields,matches:tuple[ReferenceWitness,...],auxiliary:tuple[ReferenceWitness,...],other_facts:tuple[ReferenceWitness,...],semantic_equivalence Literal not_assessed,materiality Literal not_assessed.
- ReferenceCoverageCounts: selected_numbers,total_hints,candidate_pairs,exact_reference,containing_reference,partial_reference,no_reference_in_selected_fields,primary_carriers,auxiliary_carriers (all strict nonnegative ints).
- RoleReferenceCoverage: profile Literal role-reference-coverage-v1,rules_version Literal selected-anchor-overlap-v1,status Literal unreviewed,source_inventory_exhaustive Literal False,semantic_approval Literal False,semantic_equivalence Literal not_assessed,materiality Literal not_assessed,original_link:RoleLinkGeneration,original_link_sha256:Sha256,rules_sha256:Sha256,carriers:tuple[ReferenceCarrier,...],rows:tuple[ReferenceRow,...],coverage:ReferenceCoverageCounts.

Carrier generation EXACT deterministic order per original proposal binding order, then fields below; skip only null anchor. c1.. globally over appended carriers (IDs never depend on provider input). Context/event lookup by that binding.context then context.event; no implicit sharing or transitive inheritance. Preserve duplicate same span/path across different binding numbers and duplicate positions in different fields. IDs unique by inventory position; same path alone never merges owners. Scope kind remains in original_link, not new role correctness claim.
Primary order/paths/field names:
1 context fields entity,period,condition,purpose,basis,baseline in that order, path contexts/{context.id}/{key}, field=key.
2 context scopes original order: contexts/{context.id}/scopes/{zeroindex}/anchor,field=context_scope.
3 binding scopes original order: bindings/{number}/scopes/{zeroindex}/anchor,field=binding_scope.
4 selected event.actor: events/{event.id}/actor,field=reporting_actor.
Auxiliary order/paths:
1 event.predicate: events/{event.id}/predicate,field=reporting_predicate.
2 binding.change.evidence if change and anchor nonnull: bindings/{number}/change/evidence,field=change_evidence.
3 EVERY original relation in proposal order where number equals from_ OR to, no extra inheritance: relations/{zeroindex}/cue,field=relation_cue. Both direct endpoints get own carrier; preserve unknown/parallel/included_in metadata in original_link, not a new classification.
4 current full numeric candidate.expression: quantities/{number}/expression,field=quantity.
5 if status_sentence nonnull, full current sentence.span: bindings/{number}/status_sentence,field=status_context.
Alias anchor uses existing strict _resolve with ContextualAnchor(s,t,c); only resolved narrow t span becomes carrier. c disambiguates but is not selected info. Quantity and status sentence come only from current validated generation's candidate index. No auto support/statement/title/metadata, reporter predicate in primary, unrelated context/event, relation-chain propagation, string search/normalization/paraphrase.

For each original link.report.decisions row IN ORIGINAL ORDER (all states, no filtering), compare its current hint span with ALL carriers in original inventory order. Same citation_id required. Exact start/end => exact; else carrier.start<=hint.start and carrier.end>=hint.end => contains; else max(starts)<min(ends) => partial; touching endpoints or different citation => no witness. Retain all overlapping witnesses, not only best. Same number+primary => matches; same number+auxiliary => auxiliary; different number => other_facts regardless category (category/owner stay in inventory). Lexical status only from matches, priority exact then contains then partial then no-reference. Other/aux witnesses never fill current primary coverage. Incoming roles/link_state/hint/number copied exactly, semantics/materiality remain not_assessed. No group completion from a partial member, no matching different occurrences just because text equal. No missing or semantic_preserved verdict. Coverage sums rows exactly and carrier categories; selected_numbers/total_hints from current original link.report.coverage. Empty selection or0pairs still validates original_link and creates complete valid inventory (if selected numbers but0hints carriers may nonempty), rows0 counts0; no synthetic request. Full288pairs preserved; witnesses never arbitrarily capped. Own report is not legacy144diagnostic/20support report.

Rules hash: export pure role_reference_rules()->fresh JSON dictionary (do not expose mutable shared state), covering rules_version, exact primary/aux field order and path templates, routing(binding.context/context.event/direct relation endpoints), narrow resolution/c exclusion and skipped null policy, binding-major/globalc order/no dedup, overlap samecitation/exact/containment/strictintersect/priority, witness routing incl other-fact auxiliary, all-state row order, forbidden semantic inference and metadata exclusions. Use existing canonical _hash on this descriptor and full canonical original_link JSON. No ad hoc supplied inventory accepted as canonical.

Synthetic TDD tests before module: literal positive carrier order/path/owner/IDs/all categories; shared context/event owner retained, binding-specific scope not leaked, direct relation cues both endpoints but no primary/chain inheritance; null/nochange/status absent; exact/contains/partial/group fragment/both best and allwitnesses, c-only/support-only/otherfact/repeated text/differentquote/touch boundaries; wrong actor placement still textual reference not semantic certification, roles S/E unchanged; related/unrelated/?/_ rows retained; empty selection, selected but nohint, multiquote and0rows; source/gen/link/hash/usage drift and every report marker/rule/path/span/owner/id/witness/roles/state/priority/count tamper; raw+actual roundtrip, missing required fields/defaulted nested markers, exact scalar/container/model/subclass/uncheckedcopy before serialization, no normalization. 288pairs without hidden legacy cap and worst allowed carrier/witness path inventory with no truncation; no quote/sentence support limit invented. Import/client/network purity. Use synthetic public fixtures only, no private actuals. Run newtests+role_link_catalog/contract/SDK and meaningful scoped ruff/format/mypy; do not fullQA. Commit owned2files/checkbox; detailed TDD report path provided by controller.

## Controller gates

- [x] Task and fresh whole-branch review, fresh full QA.
- [x] Real5sources/271rows vs frozen prototype, K6/J4 and all original scores preserved;456code/642actual/45+59+17design/privacy/link checks.
- [ ] Docs/Draft PR/Sites previousv113 archived; archive own SDD/remove own QA only, retain worktree. No app/main deployment/providers.

## 구현과 오프라인 대조 · 2026-10-22 한국 시간

구현 source는 db1876d다. 별도 순수 모듈에서 carrier inventory·모든 관계/witness·원래 SDK/hash·규칙/hash를 보존하고, 저장 결과의 전체 필드를 현재 원문에서 재구성한다. raw/actual 필수 marker·모델/컨테이너/스칼라 타입을 dump 전에 검사한다. 넓은 문맥·지원 문장·다른 수치의 참조는 해당 수치의 primary 참조를 대신하지 않는다. 역할과 의미 동등성/중요도를 자동 판정하거나 수정하지 않는다.

신규43개를 포함한 관련353개 검사와 scoped lint/format/mypy가 통과했다. 최대 유효 합성 입력은212carrier(132primary/80auxiliary),288행,57,600witness를 유지한다. 원문 locator·event종류·합산scope·SDK envelope 제약에 맞도록 합성 fixture를 수정했으며 기존 SDK는 바꾸지 않았다. 반복된 원래 SDK leaf 전부를 다시 변조하는 대신 새 schema-field 종류와 원래 source/generation/hash/usage의 대표 변조를 검사한다. 전체 검사는 최종 영수증으로 별도 기록한다.

추가 모델 호출 없이 기존 실제5자료를 현재 구현으로 재구성해 raw/actual roundtrip·carrier 전체·모든 행/witness를 검토된 시제품과 대조했다. 전체271행은 exact23/containing31/partial2/해당primary참조없음215로 일치했다. 직전10역할 불일치의 K6은 entity내 containing, J4는 해당primary참조없음으로 유지된다.215를 의미상 누락 수로 세지 않는다. 기존 부분 점수 주요6/8·대조7/9, 원래 generation 비분쟁1/4·G사람 재판정 유보·이전 검수2탐지/6미탐/추가3유보·실패/비용은 바꾸지 않는다.

기존456실행파일/642실제평가/121설계증거는 불변이다. 앱/API/DB/UI/worker·공급자 지침/기본 모델·main/서버 배포는 변경하지 않았다. 의미 동등성·중요도·잘못된 역할 배정·미관측 자료의 후보 recall·앱 전체 비용/권한/복구 인수가 다음 단계다.

태스크 독립 검토와 새 전체 브랜치 검토 모두 C0/I0/M0로 승인했다. 구현 수정 없이 확정 source db1876d의 새 전체8,452개(Python7,632+JS820), lint/format/types/build/OpenAPI 검사를 통과했다. 실패/skip/warning0이다. 의미/중요도·provider 진위·제품 전체 인수는 본 문자 참조 계약의 판단 대상이 아니며 별도 열린 과제로 유지한다.

[Draft PR92](https://github.com/DigestWorks/IssueDigest/pull/92)은 설계 PR91 브랜치를 대상으로 한다. main/앱 배포는 하지 않는다. 소유 QA컨테이너1개 제거·포트 닫힘을 확인했고 다른 자원은 유지했다. Sites에는 기존v113을 보존해 현재 구현과 남은 인수를 반영한다.
