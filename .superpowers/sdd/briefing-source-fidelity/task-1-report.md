# Task 1 implementation report

Base `2b2699c` (PR44/source baseline `379720f` + approved plan). Branch `feat/briefing-source-fidelity`. One integrated task; no child agents, real keys/materials/provider/network/server/container operations, push or deployment. All PostgreSQL mutation tests ran sequentially and only against the assigned synthetic loopback database on port25488. Controller owns independent reviews, whole gate, actual semantic evaluation, personal-development application, PR and Sites publication.

## Implemented contract

- New private final `research_v8`: original v7 final signatures with mandatory validated prior input/output usage. Reuses frozen v6 provider DTOs/three strict tools/canonical projection and v7 usage/remaining helpers. `ToolOutput.output` and `typing.get_args`/`model_fields` derive actual Pydantic classes; no schema-only date filtering or copied v6 DTO builder. Unexpected frozen shapes fail before a model request.
- Candidates come only from strict validated prompt source citation quotes, preserving source/citation/appearance order, calendar validity and exact ASCII spelling; deduplicated first16. No candidate means runtime/schema details permit comparison only. Otherwise timeline date is a literal enum. A globally valid date attached to another quote still fails the existing canonical builder. Question, parent, title, collection metadata and malformed dates do not add candidates. No original quote/question normalization or slicing is added.
- Own v8 instructions preserve inclusion/subset/component relations, target/observed-result/conditional-forecast status, units, period, bounds and missing evidence. They request exact-quote explanations and forbid adding included quantities. These instructions and synthetic DTO success are not semantic-quality evidence.
- New default workflow `issuedigest_research_run_v8`, paid planner7 slot1 → search8 slot2 → paid final8 slot3. Shared planned body only selects v7/v8 functions; all original v7 inputs, operations, durable names and slots remain. All seven workflows plus planner7 register in each original-version cohort. Existing current-authority/parent/fixed-source checks, search0 accounting, usage validation, reservation, cancellation, orphan handling and single-worker rules remain.
- Frozen v7 worker fixture is byte-identical to the base actual worker. Historical v7 crash subprocesses use it; the new current worker recovers its planner/final checkpoints under original version/name, completed paid0 additional calls. Existing v2~v6 actual worker fixtures and paid slot1 replay remain.
- Exact private v8 is added to Python/client/UI guards. Actual Python DTO→builder fixtures cover comparison without dates, exact-date timeline, astral text and nonanswer; full client and original UI show open first summary, collapsed detail and exact quotation. Public intact/stripped v8 is rejected. No API/OpenAPI/layout/schema/data/permission/collector changes.

## RED → GREEN and initial failures

1. `uv run pytest packages/agents/tests/test_research_v8.py -q`: initial22 failed because v8 module was absent. This established the missing feature. One editing invocation accidentally used the environment's bare `python`, which failed to import `pathlib` before editing; switched to `uv run python`, and its accompanying repeated test run also had22 absent-module failures. No production edits occurred in that failed script.
2. First minimal implementation:20 passed,2 failed. `test_worst_case_static_includes_raw_normalized_100_ids_16_dates` exposed static12338 leaving no final prompt allowance at planner8000; duplicate wording in the new appendix was reduced, retaining the frozen v6 base. `test_invalid_raw_usage_never_retries[16000-1]` incorrectly expected a valid response under remaining23400 to fail; corrected the test to overbudget24000, then22 passed.
3. `uv run pytest apps/worker/tests/test_research_worker_v8.py -q -k 'recovery_requires or checkpoint_missing'`:28 failed because v8 recovery function did not yet exist; after adding exact planned metadata and worker selection,28 passed within the successful PG suite.
4. Initial client/UI v8 run:10 failed/31 passed, proving missing version recognition and UI validation. Added exact v8 branches; initial fixture timeline generation also exposed the domain distinction between Python dates and JSON date strings, so fixture roundtrip uses `model_validate_json`, preserving production validation. Subsequent client/UI/full-web/public scoped run passed100; final timeline/nonanswer/date guards increased it to106 passing tests.
5. Initial static checks found formatting/import/style issues and3 mypy errors for dynamic `create_model` type forms; format/import fixes and the same narrow dynamic-type annotations used in frozen builders resolved them. No runtime contract was loosened.

## Final scoped verification

Commands below were executed from the worktree. `uv` was `/home/xinics/.local/bin/uv`; Node/npm used `/home/xinics/.nvm/versions/node/v24.21.0/bin` at the front of PATH. These are scoped evidence, not a claim of a whole-gate run.

```sh
uv run pytest packages/agents/tests/test_research_v8.py packages/agents/tests/test_research_v7.py packages/agents/tests/test_research_v6.py packages/agents/tests/test_research_v6_simplified.py packages/agents/tests/test_research_profile_compatibility.py packages/domain/tests/test_public_briefings.py -q
# 269 passed in3.70s (v8 had40 at this point)
uv run pytest packages/agents/tests/test_research_v8.py -q
# final42 passed in1.90s after explicit100/16 preflight and v6/v7 goldens
ISSUEDIGEST_TEST_DATABASE_URL=postgresql+psycopg://issuedigest_test@127.0.0.1:25488/issuedigest_test uv run pytest apps/worker/tests/test_research_worker_v8.py apps/worker/tests/test_research_worker_v7.py -q
# 100 passed in114.71s
ISSUEDIGEST_TEST_DATABASE_URL=postgresql+psycopg://issuedigest_test@127.0.0.1:25488/issuedigest_test uv run pytest apps/worker/tests/test_research_worker.py apps/worker/tests/test_research_recovery_v3.py apps/worker/tests/test_research_worker_v7.py -q
# 179 passed in149.98s; historical v7 now frozen-worker→current-worker replay
ISSUEDIGEST_TEST_DATABASE_URL=postgresql+psycopg://issuedigest_test@127.0.0.1:25488/issuedigest_test uv run pytest apps/worker/tests/test_research_worker_v7.py -q -k 'real_crash and (final-checkpoint or validating)'
# 2 passed/48 deselected in8.98s after adding explicit original-version/name/unchanged-journal assertions
npm test -- packages/api-client/tests/v8-generated.test.ts packages/ui/tests/v8-briefing.test.tsx packages/api-client/tests/briefings.test.ts apps/web/tests/research-briefing.test.tsx
# final106 passed across4 files in8.42s
uv run mypy
# no issues in120 source files
npm run typecheck
# web/client/ui all passed
npm run contract:check
# materialized OpenAPI/TypeScript up to date; no generated contract diff
```

Ruff check/format-check passed over all13 changed/new Python source/test/helper files (the frozen original worker fixture is preserved unchanged). ESLint passed the7 changed/new TS/TSX source/test files. `git diff --check` passed. Exact scoped static command file lists:

```sh
uv run ruff check packages/agents/src/issuedigest_agents/research_v8.py packages/agents/src/issuedigest_agents/research_v3.py packages/agents/tests/test_research_v8.py packages/agents/tests/v8_fixture.py apps/worker/src/issuedigest_worker/research_worker.py apps/worker/src/issuedigest_worker/research_recovery.py apps/worker/tests/frozen_v7.py apps/worker/tests/test_research_worker_v7.py apps/worker/tests/test_research_worker_v8.py apps/worker/tests/test_research_worker.py apps/worker/tests/test_research_recovery_v3.py packages/domain/src/issuedigest_domain/research_classification.py packages/domain/tests/test_public_briefings.py
# identical file list with `ruff format --check`:13 files already formatted
npx eslint packages/api-client/src/research-classification.ts packages/api-client/src/research-validation.ts packages/ui/src/prepare.ts packages/api-client/tests/v8-generated.test.ts packages/ui/tests/v8-briefing.test.tsx packages/api-client/tests/briefings.test.ts apps/web/tests/research-briefing.test.tsx
git diff --check
```

## Envelopes and goldens

Measured actual all-three-tool envelopes with public `GenerateToolJsonSchema` and `OpenAIJsonSchemaTransformer(strict=True)`, JSON `ensure_ascii=False`, UTF-8.100 fixed UUID4s and16 distinct valid ten-character dates:

| Profile | Instructions | Raw tools | Normalized tools | Static |
| --- | ---: | ---: | ---: | ---: |
| frozen final6/7 | 3009 | 8092 | 7952 | 11101 |
| new final8 | 3599 | 8308 | 8168 | 11907 |
| frozen planner7 | 709 | 382 | 368 | 1091 |

SHA256:

- v8 instructions: `91df818c434cedf73ba3602bcf4f8a77c5ca47e500580e80238dbfd443e9c47a`
- v8 raw: `0d48f187332ca92431a0d49f02f16a9fb8bdd824f3707f62ef12be2958e7b360`
- v8 normalized: `c9b475e1ad58963e173603775cead3de06194a2230ff5c26cdb1a9b71874f784`
- frozen6/7 instructions: `b6ae1e1905a8fc0a9199012b1eff06eb70b5606871ebed5ed7d038c5d9334eae`
- frozen6/7 raw: `1c8fa45e1c415e4c395d08c9953703ff83e1ffd2d50ee51f1d566fa73237b700`
- frozen6/7 normalized: `15adddacdb4e91553d9f34ec567f32d963f77ee9eede267d8d180cc80f42f6e6`
- frozen6/7 prompt3124 bytes (`prompt_sources(5)`, question `목표와 실적 및 전망을 비교해 주세요.`, parent `이전 해석`, planner500/100 for7): `3acb7825a1083226885c4e0f7ee07d7bb887a34278cba1f7dd687dd7d21a44c8`
- planner7 instructions: `1dd7994efca29ed43c915e51f0df1dd66bcbb00dabcb5ed05826cbfe0b01a5b3`
- planner7 raw: `90a8316a96e1a784ba9adc54a587d20b8f91e0ab060d3d4bc4c32cc7d615416e`
- planner7 normalized: `4a6f23cbbe85489ab73e59aab69ee323f8ff287e7ed655be98dc1e1ac9bc326b`
- planner7 actual Korean truncation prompt4359 bytes, limit4361 (`합성 정책의 2026년 목표는?`, parent `가`×1500): `082f2a5a3ba20f22efd386ac4b6e68e5d1c412974a830c36266747e01be2d831`
- frozen v7 worker file and `git show 2b2699c:apps/worker/src/issuedigest_worker/research_worker.py` both: `fe9e76bb414eedd5de3ca246e2ebf39fc7dea709a08b3ff98940bcd96529ae8e`.

v2~v5 existing instruction/schema/prompt golden tests remain passing; v6/v7 raw/normalized/instruction/prompt goldens are added. Frozen v6/v7 agent source files are unchanged. The shared classified factory/builder only adds literalv8 to annotations. A FunctionModel using the OpenAI model profile verifies actual normalized provider envelopes, all tool fields/required/extraforbid/strict, date enum order and existing citation enums. Date0/1/2/15/16 static envelopes remain bounded by100/16.

## Practical limits and handoff

The fixed conservative final allowance is `24000 - validated_planner_input - validated_planner_output -11907 -2048 -2000`. At planner total8000 this leaves45 prompt bytes; at600 it leaves7445. A synthetic actual100-citation/16-date prompt is8480 bytes and is correctly rejected with provider calls0 (even planner0 would allow8045). Maxima are bounds, not a promise every maximal input fits. Ordinary selected whole-quote inputs pass. No original question/evidence is cropped; no limit, model count or retry is increased. Controller explicitly accepted retaining this safe preflight limit.

Candidate dates certify spelling and quote availability only, not event meaning or truth. Hierarchy/status meaning still requires the controller's fixed actual3-question evaluation; no prompt-keyword tests claim semantic quality. Known usage is retained where available, while usage0 on failure/cancel/response-loss does not mean free; reservations remain unchanged. Task1 implementation checks are complete; whole gate, independent review, actual model/manual browser/runtime/backup/PR/Sites remain controller-owned and unmarked.
