# 질문별 근거 명제 순수 계약 구현

2026-10-23 한국 시간. 기반 PR98/03b341d. [질문별 명제 설계](question-evidence-propositions.md)가 binding spec다. OpenSpec root:null을 확인했으므로 init 없이 spec-driven-workflow 2단계를 적용한다. 순수 계약/합성 구조 검증이며 모델 의미·진실·앱 연결 인수가 아니다.

## Global Constraints

Freeze all462 existing non-Markdown tracked files and prior private evidence. Add only packages/agents/src/issuedigest_agents/question_evidence_propositions.py and packages/agents/tests/test_question_evidence_propositions.py; implementer may check only its Task1 checkbox. Existing APIs/runtime/provider instructions/DTO/source validators/dependencies/tests must remain byte-identical. Reuse helpers read-only. Synthetic fixtures only; no network/provider calls/private actual data/old runners/app/API/worker/DB/UI/server/main/deployment. Controller owns docs/private proofs/fullQA/QA resources/PR/Sites. No subagents from implementer/reviewers. TDD required; read test-driven-development skill. Use restore_introduced_modules/sync_model_loop fixtures where appropriate to avoid whole-suite pollution. No global mutable state, side effects or client lifecycle work. Sanitize whole-operation errors, no source/partial result/cause leakage. Structural success never certifies semantic correctness, completeness, truth, current access or human review.

## Public contract

Implement design exact root/proposition/facet/value/reference/coverage keys, enums, local IDs, required fields/no extras and limits. New public build_question_evidence_propositions(source: Source, question: str, data: QuestionEvidenceInput | dict[str, Any]) -> QuestionEvidencePropositions; validate_question_evidence_propositions(source: Source, question: str, result: QuestionEvidencePropositions | dict[str, Any]) -> QuestionEvidencePropositions. Pure input DTO contains exactly propositions/coverage; output contains exactly profile/status/question_sha256/source_sha256/propositions/coverage. New QuestionEvidenceError(ValueError) fixed sanitized messages and from None. Nested classes may be new module-public types; no package-root export edits. Required profile/status have no restoration defaults. No model/SDK calls, number candidate building dependency, hash of criterion/gold or field inventing.

Source is existing numeric_evidence.Source. Guard original Source actual/container/scalar types and full current provenance before any dump, then reuse existing _source_data for canonical bundle/source integrity and exact quote catalog. Source SHA is exact design canonical JSON of snapshot_id/bundle/presentation JSON-mode dumps; question is original nonblank valid UTF-8 exact str length1..2000 Unicode code points; do not strip/normalize/hash truncated question. Same text with changed identity/presentation/order must not silently reuse a receipt. All receipt raw/actual objects and nested fields must be revalidated fresh, including original unchecked model instances/subclasses/tuple/list/scalar/key anomalies before serialization/default restoration. Follow existing raw JSON list vs actual tuple conventions: raw dict accepts only exact JSON objects/lists/scalars; actual typed DTO uses declared canonical tuple fields. Do not accept raw tuple by normalizing it into JSON or actual list replacing a tuple. Missing nullable/empty fields must fail rather than restore defaults.

Validate original exact refs against cited quote using Unicode offsets, full slice match, nonblank valid UTF-8, integer exact (bool/float rejected). Supporting refs1..8; subject/predicate0..8 contained in support; facet refs1..8 contained in support and every value-nested ref exactly listed in facet.refs. Duplicate references within each list rejected; sharing refs across fields allowed. No extra implicit string length cap beyond existing valid source and design question limit. No source truncation/normalization or lexical/numeric/date inference.

Target IDs bound/distribution exactly one local quantity, others []; per_member/collective needs member_refs; missing metric/subject/predicate or relative time anchor implies uncertain. Enforce declared cardinalities, ID domains/unique ordered lists and acyclic inter-proposition dependencies; direction dependent→prerequisite. Dependencies may be empty even with prerequisite facet; do not manufacture edges. Uncertain/unknown remains explicit, never automatically upgraded. Empty no-numeric Source and empty result are valid with coverage reason. Coverage null only with ≥1link; no_linked_evidence only when links empty; ambiguous/insufficient allowed with0 or more. Reject unknown linked IDs and duplicates. A new fresh result, not mutated old DTO, is returned. A semantic mislabel with otherwise exact refs may be structurally valid and must not be advertised as correct.

## Task 1: Pure contract and adversarial boundary tests

- [x] Implement new pure module and tests using RED→GREEN TDD.

Own only the two new files above and this checkbox. Read binding design, existing pure-contract patterns and source guards. First demonstrate missing-module failing test with synthetic Source; then implement. Test all8facet variants and actual/raw successful roundtrip, exact question/source canonical hash independently computed, raw required markers, empty/zero-numeric/multiple citations, quote-relative Unicode repetition and preserving literal negative/relative/per-category/bound cues, partial/unknown state, dependencies empty/directed/cycle, no semantic certification. Include same number shared with differing metrics without inventing values.

Adversarial tests: invalid source identity/bundle/presentation/text hash/malformed Source, invalid question exact type/UTF-8/blank/limit, wrong/current source and question hash drift, missing root/nested nullable or empty keys/extra/enum/type; unsupported facet value keys; bool/int/float/string subclasses and nested raw/actual container/subclass/unchecked wrong type before dump, duplicate IDs and refs across per-list boundaries, target wrong owner/type/unknown/self, bounds cardinality, every facet/value/support containment, metric/per-member/relative uncertainty rules, all list caps plus exact boundaries without alternate invalidity masking the cap. No fragile implementation-mirroring gold or check that merely asserts class existence. Safe errors suppress private input/cause and do not mutate input. Revalidation should reject mutated or stale stored output and produce fresh canonical DTO.

Run targeted new tests + existing role_alias_contract/role_reference tests, scoped Ruff/format/mypy. Use existing .venv and repository conventions. No fullQA/provider/private source reads. Report commands/output/RED→GREEN/commit/self-review/concerns in own SDD report; commit owned files and checkbox. Controller runs whole-suite and preservation gates afterward.

## Controller gates

- [ ] Task review spec+quality; final whole-branch review and appropriate fullQA.
- [ ] Existing462 code/private evidence unchanged; actual stored source read-only roundtrip with explicit manual layout vs no semantic inference.
- [ ] Documentation/privacy/links, Draft PR basePR98, Sites previousv120 preserved, own QA cleanup. No app/worker/main deployment.


## 구현과 무호출 원문 대조

초기 구현bf14eeb·신규174개와 scoped Ruff/format/mypy를 확인하고, 검토 수정dde2931의 최종 신규198개와 scoped 검사를 다시 확인했다. 신규149시점에 기존 role alias/원문 참조96개를 더한245개가 통과했으며, 이후 새25검사를 더한174개 실행과 구분한다. 이전462실행 파일과 SDK/실제 평가 증거는 유지한다.

기존 원문과 앞선 수동 설계12행을 새 builder/저장 validator에 넣어 동일한 JSON으로 왕복했다. 원래 항목 유형은 기준을 아는 수동 배치이며 모든 명제를uncertain으로 두고 대상/서술/지표를 추론하지 않았다. 현재 source hash/offset bool/존재하지 않는 연결/질문 drift의4변조를 거부하고 원문 bytes를 유지했다.12/12 의미 성공·모델 추출·완전한 브리핑 경로를 뜻하지 않는다. 신규 모델 요청과 과거 runner 재실행은0이다. 최종 검토/전체QA/게시 결과는 최종 인계를 따른다.

태스크 검토 I1은 typed DTO/Source의 원래 __dict__ map·key subclass가 정규화되는 공백이었다. 새 모듈에만 재귀 exactdict/exactstr 검사를 추가했고 dump-forbidden24회귀 RED→GREEN을 확인했다. 기존 helper/SDK/원문·기준은 유지했다. 수정 전 bf14eeb의 전체QA는 필요한 변경 때문에 중단했고 성공에서 제외한다. 수정 후 dde2931에서 새전체QA를 실행한다.

수정 범위 재검토에서 I1해소·명세/품질 승인 C0I0M0을 확인했다. 전체 브랜치 검토·새전체QA와 게시 인계는 controller gate에 남긴다.
