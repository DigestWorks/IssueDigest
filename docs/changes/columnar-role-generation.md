# 전체 원문 columnar 생성 SDK

2026-10-23 한국 시간. 기반 [무손실 입력 codec](columnar-generation-source.md), PR95/e46eec3. 별도 생성기로 새 입력 형식의 실제 SDK 경계를 구현한다. OpenSpec root:null이므로 init 없이 spec-driven 구현 절차를 적용한다. 합성 wire·오프라인 수용과 실제 유료 모델 의미/앱 인수는 구분한다.

## Global Constraints

Freeze all 460 existing non-Markdown tracked files, prior actual642/design121/implementation12/research10/new-source33 evidence and previous codec75 evidence. Add only packages/agents/src/issuedigest_agents/columnar_role_generation.py and packages/agents/tests/test_columnar_role_generation.py; implementer may update its own checkbox only. Never edit the codec, balanced generator, shared runtime, output DTO/schema, instructions/constants in existing modules, provider versions/settings/dependencies or old tests. Reuse existing helpers read-only. No provider/network/private actual source reads, old runners, app/API/worker/DB/UI/server/main changes or deployment, retry/repair/fallback/client construction/closure. Controller owns frozen/private/offline evidence, QA DB/fullQA/reviews/docs/PR/Sites. TDD with synthetic fixtures only, restore_introduced_modules and sync_model_loop fixtures. Exact original Source/model/container/scalar validation before dump; no source/candidate filtering/truncation/normalization or hidden lower caps. Explicit unreviewed results do not certify semantics, truth, neutrality, completeness, authority or access. No subagents from implementer/reviewers.

## Spec

Public API in the new module only:
- `ColumnarRoleGenerationError(RoleRequestError)` with sanitized fixed messages, observed `known_usage` and `may_have_started` retained, no chained cause/source/partial result.
- `ColumnarRoleGeneration(_StrictModel)` with all fields required: `profile: Literal["columnar-role-generation-v1"]`, `input_format: Literal["columnar-generation-source-v1"]`, `status: Literal["unreviewed"]`, `frame: RoleAliasFrame`, `prompt_sha256: Sha256`, `instructions_sha256: Sha256`, `usage: KnownUsage`. Its validator requires requests==1, output_tokens<=1800, input+output<=20000. No default restoration of missing root/nested required markers.
- `columnar_role_prompt(source: Source) -> str`; `validate_columnar_role_generation(source: Source, result: ColumnarRoleGeneration | dict[str, Any]) -> ColumnarRoleGeneration`; `create_columnar_role_framer(model: Model)`; `run_columnar_role_framer(framer, source: Source) -> ColumnarRoleGeneration`. Borrow required actual Model lazily; frozen handle does not claim deep immutability. Caller owns model/client lifecycle.

`PROVIDER_IDENTITY = "issuedigest_columnar_role_generation_v1"`; output tool name `fill_columnar_roles_v1`, strict=True. Output is the unchanged current-source dynamic `_input_model(index)` and `_build_output` RoleAliasFrame, preserving all existing selected quantity/roles/scopes/change/relation limits and unknown/null/unreviewed semantics. No new semantic acceptance, output budget or allowed tools.

`COLUMNAR_ROLE_INSTRUCTIONS` is exactly this pure expression over frozen constants (no other append/rewrite):
```
BALANCED_ROLE_INSTRUCTIONS.replace(
    "fill_shared_role_aliases_v2", "fill_columnar_roles_v1"
).replace(
    "Each quote contains complete ordered sentences {id,text}; concatenate without separators, preserving whitespace and blank sentences. ",
    "Input format is columnar-generation-source-v1. "
    + GENERATION_SOURCE_PACKET_INSTRUCTIONS
    + " Concatenate decoded quote sentences without separators, preserving whitespace and blanks. ",
)
```
All original role/bounds/quote injection safety instructions remain verbatim except those two substitutions. This is a new generation instruction/profile/hash, not an old receipt reused with a different prompt. Codec packet root profile remains shared-role-aliases-v2, describing the unchanged source projection; new generation receipt profile/input_format identify this SDK distinctly.

`_preflight(source)` obtains the exact canonical JSON prompt from `generation_source_packet_prompt(source)` (which guards live Source before dump), builds the same full numeric-candidates-v2 index and strict dynamic output tool above, then checks `_request_envelope(prompt, tools, COLUMNAR_ROLE_INSTRUCTIONS, 1800) <= 20000`. That calculation includes actual UTF-8 prompt+new instructions+max(raw,normalized new-name schema)+framing2048+output1800. Do not call the balanced generator's old rejecting preflight, alter limits, skip schema cost or shorten source. Exactly at limit accepts, +1 rejects before dispatch. Empty candidate catalogs still use the same explicit one-request API, no invented special behavior.

Run validates exact framer type/model and input before dispatch, then reuses `_run_role_request` with total20000/output1800/instructions/identity/new tool. One request only, 30-second runtime timeout, store=False, runtime retries0 and request_limit1. No separate model/client or wrapper ownership. Runtime handles actual dynamic output type/structure, raw usage overflow, completion state/provider incomplete, text/malformed/refusal/extra tools/network errors and transmission uncertainty. Do not weaken those guards or silently retry; borrowed client transport-retry policy remains caller responsibility.

Build frame with existing `_build_output`; own prompt/instruction SHA over exact UTF-8 and observed KnownUsage. Revalidate before returning. Stored validator performs fresh `_preflight`, guards original result raw/actual types with existing `_guard` before conversion, requires every root field and existing nested frame/index markers via `_require_frame_markers`, strict `_read` of own DTO, full `validate_role_alias_frame`, dynamic catalog reconstruction and equality of `_build_output` with stored frame, exact current prompt/new instruction hashes. Reject old generation profiles/class/hash, input-format/source/catalog/value drift, type subclasses/extras/unchecked nested types and missing markers. Source guard inherits codec raw/actual protection. Return a fresh validated DTO, not semantic approval. Preflight errors use `Invalid columnar role generation input`; validator uses `Invalid columnar role generation`; constructor bad model uses `Invalid columnar role generation model`; dispatched/post-response failure uses `Columnar role generation failed`. Preserve known usage on post-response validation failure; distinguish zero-send from started-unknown and started-known, suppress cause.

## Task 1: Standalone columnar generation SDK and boundaries

- [x] Implement the standalone SDK with TDD synthetic boundary and mock-wire tests.

Own only two new files and checkbox. Requirements are Spec/Global Constraints above; report missing-module RED before implementing. Use existing synthetic source/alias packet fixtures with independent literal receipt/tool/input expectations, not only implementation-mirroring assertions. Confirm public prompt exactly codec packet, complete quote roundtrip via codec, all candidate IDs/slots maintained and no source metadata IDs leaked. Genuine new profile/input_format/hash, unchanged underlying output semantics, every root required marker/raw+actual before default restoration, frame/index markers, subclasses/unchecked nested tuple/list/model/key/container/scalar variants, source/instruction/prompt/catalog drift and old-receipt rejection.

Test complete/empty output, current dynamic enum/alias-only schema, inclusive usage total/output limits, negative/bool/noninteger raw usage as existing runtime permits/rejects, raw completion vs SDK completion and incomplete/length/provider-details, malformed/unknown/multiple tool/text output; zero-send invalid model/source/envelope versus started unknown network and started-known malformed/overflow. Post-response final revalidation failure must retain known cost and dispatch uncertainty. No retries/client ownership. Mock HTTP via caller-owned OpenAI Responses SDK/MockTransport: exact columnar JSON prompt and exact new instructions, strict single new-name tool/raw normalized schema, store=False, max_output1800, timeout30, retries0 at Agent/runtime, caller model settings preserved; valid completed vs raw incomplete JSON body. Check import/constructor purity and existing helper/interface preservation; full old-code hashes are controller gate.

New SDK preflight boundary uses max raw/normalized schema exact20000/+1; full otherwise-valid long Source envelope rejection (no truncation/paid send). Retain legal 4,302-char ID-like literal public prompt/decode case when within budget or independently assert exact preflight reason. No private sources/providers/network or fullQA. Focused new tests+existing balanced generation+codec; scoped ruff/format/mypy. Report full commands/output/RED→GREEN, commit owned files+checkbox, return stable commit.

## Controller gates

- [ ] Task spec/quality and fresh whole-branch review; fullQA on final stable code.
- [ ] Six frozen source preflight/packet roundtrip/new-name raw+normalized SDK mock wire and exact instruction/schema envelope with original source/failure/usage/score preservation; no actual model call.
- [ ] 460 code/642actual/121design/prior12+10+33/codec75 preservation, privacy/docs; Draft PR base PR95, Sites previousv117 archive/publication; own QA/SDD cleanup. No app/main deployment.

Actual provider/model completion, semantics on the predeclared source questions, relation quality, and app/worker activation remain a separate next acceptance stage. Passing SDK checks must not be described as those outcomes.
