# 질문별 근거 생성의 중단 가능한 스트림 연결

2026-10-25. [기존 transport](guarded-responses-stream.md)를 실제 source/질문별 근거 생성 SDK에 연결한다. 기존 v1/v2 SDK와 앱/worker의 기본 경로는 유지한다. 합성 연결 검증과 실제 모델 의미·앱 인수를 구분한다.

## Global Constraints

- Only new `packages/agents/src/issuedigest_agents/guarded_question_evidence.py` and its new test file may change execution code. Existing execution files, dependencies, exports, provider instructions/prompt bytes, old paid results and namespaces remain byte-identical. Documentation may change. No actual provider requests, database/server writes, app/worker activation or main merge.
- New async public `run_guarded_question_evidence(*, client: AsyncOpenAI, model: str, source: Source, question: str) -> GuardedQuestionEvidenceGeneration`. Borrow caller client; use existing `question_evidence_generation_v2._preflight` and exact `QUESTION_EVIDENCE_V2_INSTRUCTIONS`, plus one call to `run_guarded_responses_tool`. No retry/repair/fallback, no source shortening, no client creation/close, no sync loop bridge.
- New strict receipt `GuardedQuestionEvidenceGeneration`: profile Literal `guarded-question-evidence-v1`, transport_profile Literal `guarded-responses-tool-v1`, input_format Literal `question-evidence-source-v2`, status Literal `unreviewed`, evidence QuestionEvidencePropositions, prompt_sha256 Sha256, instructions_sha256 Sha256, usage KnownUsage. Receipt requires exact single request, output<=4000 and input+output<=20000. Different profile deliberately does not impersonate historical v2 receipts. It is structural consistency, not semantic/public/access approval.
- New `validate_guarded_question_evidence(source, question, result)` reconstructs and validates fresh evidence with existing proposition validator, original actual-type/raw-required guards, exact current prompt/instructions hashes and budget. Reject unchecked model_construct/coercion, extra/missing/type-corrupt fields, source metadata/text changes, question/hash changes and profile substitutions. Return validated receipt without changing input/source.
- Before dispatch check strict original source, exact question and v2 preflight; retain full source hash. On completed transport require exact expected output class, expected transport profile, usage_complete exactly True, actual valid KnownUsage, budgets, and immutable-source hash before/after evidence build plus saved validation. Build with existing build_question_evidence_propositions. Do not manufacture receipt from partial/incomplete/invalid output. Source mutation during await fails with observed final usage retained.
- Wrapper failures: `GuardedQuestionEvidenceError` subclass of `GuardedResponsesError`, fixed sanitized text inherited, same observations. Local/preflight invalid input reason input / known_usage None / may_have_started False / usage_complete False / stream_closed False. Native GuardedResponsesError copied to wrapper preserving all observations and reason, from None. Native GuardedResponsesCancelled re-raised unchanged as cancellation, never ordinary error. Post-transport structural/source failure reason output, known terminal usage retained, may_have_started True, usage_complete True, stream_closed True (transport success establishes closed body). Do not copy raw exception text/inputs/partial outputs/provider IDs to error fields. Unknown/unexpected ordinary failure conservatively has may_have_started True after dispatch but no invented usage/close confirmation. No exception handler catches BaseException broadly.
- Transport's 60s/1s/80k/10k and exact no-retry client requirements remain unchanged. Closing HTTP is not proof of provider compute cancellation/final cost. No claim of app quality or provider semantics from synthetic output.

## Task 1: Connect source-specific generation to native stream

- [x] Implement the two new execution files only plus this checkbox with TDD.

Read test-driven-development skill. RED tests before implementation, then GREEN and scoped lint/format/mypy. New synthetic tests must exercise real AsyncOpenAI with httpx2.MockTransport and close-observing SSE, exact question/full quotes/instructions/strict tool name/schema/wire options; one complete valid source-attributed proposition receipt + JSON save/revalidate roundtrip; valid empty insufficient response allowed but not semantic success. Assert native incomplete/invalid JSON/whitespace/transport/cancel observations survive wrapper; no partial receipt, no retries/client close; source quote/title/metadata mutation during await rejects retaining final usage; invalid source/question/budget/client/model preflight sends zero requests; tampered saved receipts/raw-required/constructed wrong types rejected. Use existing fixture module restoration pattern so imports do not poison frozen reload tests. Do not duplicate transport's entire event matrix: focus on integration boundaries and assertion of no app activation. Use deterministic events/deadline overrides, no private data/network/provider calls. Commit owned files; full report records RED/GREEN/static commands/results and self-review. Controller runs full QA once and independent task/final review. No subagent spawning by implementer.

## Controller gates

- [ ] Independent task and whole-branch review, full repository checks.
- [ ] Existing execution/private evidence integrity, documentation and privacy checks.
- [ ] Draft PR, plan summary/history update or explicit Sites pending, own QA cleanup. App/worker/provider acceptance remains separate.

## 判断・영향

1. 원문 검증과 native transport를 새 SDK로 연결하고 기존 v2는 유지한다. 기존 저장 결과·재생을 보존하지만 앱에 적용하려면 versioned worker·예산/권한/복구 인수가 추가로 필요하다.
2. 기존 정확한 지침·질문을 유지해 전달 경로의 효과만 분리한다. 이전의 출력 정체가 여전히 발생할 수 있으며 이번 합성 성공을 실제 모델 품질로 확대하지 않는다.
