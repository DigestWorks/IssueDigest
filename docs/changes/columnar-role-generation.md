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

`_preflight(source)` obtains the exact canonical JSON prompt from `generation_source_packet_prompt(source)` (which guards live Source before dump), builds the same full numeric-candidates-v2 index and strict dynamic output tool above, then checks `_request_envelope(prompt, tools, COLUMNAR_ROLE_INSTRUCTIONS, 1800) <= 20000`. That calculation includes actual UTF-8 prompt+new instructions+max(raw,normalized new-name schema)+framing2048+output1800. Do not call the balanced generator's old rejecting preflight, alter limits, skip schema cost or shorten source. Exactly at limit accepts, +1 rejects before dispatch. Empty candidate or sentence catalogs are rejected before dispatch by the unchanged dynamic output model builder. The codec still supports empty catalogs; this standalone numeric generation API does not fabricate a numeric-output schema or send a paid request without numeric candidates.

Run validates exact framer type/model and input before dispatch, then reuses `_run_role_request` with total20000/output1800/instructions/identity/new tool. One request only, 30-second runtime timeout, store=False, runtime retries0 and request_limit1. No client construction/closure or lifecycle ownership. Runtime handles actual dynamic output type/structure, raw usage overflow, completion state/provider incomplete, text-only/malformed/network errors and transmission uncertainty. The new SDK additionally wraps the borrowed model in the existing read-only `_ObservedAuditModel` before passing it to the runtime. After runtime success but before constructing a receipt, inspect its captured original response: exactly one ModelResponse with exactly one ToolCallPart named fill_columnar_roles_v1 and otherwise only optional ThinkingPart parts is allowed. Reject extra/unknown tool calls, text (including mixed text+tool), file/builtin/other parts; preserve already-known usage on rejection. The observer forwards one nonstreaming request and never constructs/closes a client. Existing runtime is unchanged. Do not weaken those guards or silently retry; borrowed client transport-retry policy remains caller responsibility.

Build frame with existing `_build_output`; own prompt/instruction SHA over exact UTF-8 and observed KnownUsage. Revalidate before returning. Stored validator performs fresh `_preflight`, guards original result raw/actual types with existing `_guard` before conversion. For actual BaseModel also call existing `_original_values(result, ColumnarRoleGeneration)` to reject original scalar/container subclasses. For raw input use existing `_copy_json` plus `_required_raw(result, ColumnarRoleGeneration)` before `_read` so every raw model field/key/container/scalar is checked before serialization/default restoration; requires every root field and existing nested frame/index markers via `_require_frame_markers`, strict `_read` of own DTO, full `validate_role_alias_frame`, dynamic catalog reconstruction and equality of `_build_output` with stored frame, exact current prompt/new instruction hashes. Reject old generation profiles/class/hash, input-format/source/catalog/value drift, type subclasses/extras/unchecked nested types and missing markers. Source guard inherits codec raw/actual protection. Return a fresh validated DTO, not semantic approval. Preflight errors use `Invalid columnar role generation input`; validator uses `Invalid columnar role generation`; constructor bad model uses `Invalid columnar role generation model`; dispatched/post-response failure uses `Columnar role generation failed`. Preserve known usage on post-response validation failure; distinguish zero-send from started-unknown and started-known, suppress cause.

## Task 1: Standalone columnar generation SDK and boundaries

- [x] Implement the standalone SDK with TDD synthetic boundary and mock-wire tests.

Own only two new files and checkbox. Requirements are Spec/Global Constraints above; report missing-module RED before implementing. Use existing synthetic source/alias packet fixtures with independent literal receipt/tool/input expectations, not only implementation-mirroring assertions. Confirm public prompt exactly codec packet, complete quote roundtrip via codec, all candidate IDs/slots maintained and no source metadata IDs leaked. Genuine new profile/input_format/hash, unchanged underlying output semantics, every root required marker/raw+actual before default restoration, frame/index markers, subclasses/unchecked nested tuple/list/model/key/container/scalar variants, source/instruction/prompt/catalog drift and old-receipt rejection.

Test complete and empty-array output on a source with numeric candidates; empty candidate/sentence catalogs reject before dispatch. Cover current dynamic enum/alias-only schema, inclusive usage total/output limits, negative/bool/noninteger raw usage as existing runtime permits/rejects, raw completion vs SDK completion and incomplete/length/provider-details, malformed/unknown/multiple tool/text output; zero-send invalid model/source/envelope versus started unknown network and started-known malformed/overflow. Post-response final revalidation failure must retain known cost and dispatch uncertainty. No retries/client ownership. Mock HTTP via caller-owned OpenAI Responses SDK/MockTransport: exact columnar JSON prompt and exact new instructions, strict single new-name tool/raw normalized schema, store=False, max_output1800, timeout30, retries0 at Agent/runtime, caller model settings preserved; valid completed vs raw incomplete JSON body. Check import/constructor purity and existing helper/interface preservation; full old-code hashes are controller gate.

New SDK preflight boundary uses max raw/normalized schema exact20000/+1; full otherwise-valid long Source envelope rejection (no truncation/paid send). Retain codec roundtrip for legal 4,302-char ID-like literal; if its actual SDK envelope exceeds20000 assert exact preflight reason with no dispatch. Use valid existing-size sources for envelope tests, not a source already rejected by existing quote/candidate caps. No private sources/providers/network or fullQA. Focused new tests+existing balanced generation+codec; scoped ruff/format/mypy. Report full commands/output/RED→GREEN, commit owned files+checkbox, return stable commit.

## Controller gates

- [x] Task spec/quality and fresh whole-branch review C0/I0/M0; fullQA8696 on stablee580e17/executable87e2746.
- [x] Six frozen source preflight/packet roundtrip/new-name raw+normalized SDK mock wire and exact instruction/schema envelope with original source/failure/usage/score preservation; no actual model call.
- [x] 460 code/642actual/121design/prior12+10+33/codec75 preservation, privacy/docs; Draft PR96 base PR95, Sitesv118 previousv117 archived; own QA/SDD archived/cleaned. No app/main deployment.

Actual provider/model completion, semantics on the predeclared source questions, relation quality, and app/worker activation remain a separate next acceptance stage. Passing SDK checks must not be described as those outcomes.

## 구현 중 보조 코드 확인과 판단

1. 기존 동적 출력 모델이 수치 후보0개를 거부하므로 새 SDK도 송신 전에 거부한다. codec의 빈 후보 보존은 유지하며 임의 출력 schema를 만들지 않는다. 비용: 수치가 없는 자료에는 이 수치 역할 생성기를 실행할 수 없다. 일반 비수치 브리핑 경로와는 별개다.
2. 기존 runtime은 여러 정상 도구 호출 중 하나를 선택할 수 있어 새 SDK에서 원래 응답을 관측해 정확 한 도구 호출/선택적 thinking만 허용한다. 섞인 설명문/추가 도구 등은 known usage를 남기고 거부한다. 비용: 사용할 수 있는 답이 포함돼 있어도 혼합 응답은 보수적으로 실패하며 재시도하지 않는다. 과거 runtime은 바꾸지 않는다.
3. 기존 guard가 일부 scalar subclass/JSON 아닌 tuple을 그대로 허용할 수 있으므로 새 SDK에만 재사용 가능한 exact 원래 값/JSON/필수 필드 검사를 추가한다. 비용: 축약하거나 느슨하게 구성한 저장 기록은 거부되고 전체 canonical JSON을 제공해야 한다. 기존 버전 기록은 변경하지 않는다.

## 구현·보존 원문 SDK 대조

구현87e2746·신규123개/관련305개 및 scoped Ruff/format/mypy 통과. 새 generation profile/input_format·정확 prompt/instruction hash·단일 도구/선택적 thinking·실패 known usage·raw/actual 원래 타입/필수 필드를 검증한다. 기존 codec/SDK/runtime/출력 DTO를 수정하지 않았다. 전체 검토/QA와 게시 결과는 최종 인계를 따른다.

기존G~K와 신규L의 원문을 바꾸지 않고 새 SDK `_preflight`와 caller-owned OpenAIResponsesModel/MockTransport를 각1회 실행했다. **합성 응답은 빈 contexts/events/bindings/relations**이며 실제 provider 요청·모델이 선택한 근거·의미 점수는0/미평가다. source packet 전체 JSON·quote 복원은 기존 보존 결과와 동일하며 새 SDK raw/JSON 영수증 재검증을 확인했다.

| 자료 | 기존 balanced v2 envelope | 실제 새 SDK preflight envelope | 20,000 대비 여유 |
| --- | ---: | ---: | ---: |
| G | 15,398 | 15,429 | 4,571 |
| H | 15,075 | 15,234 | 4,766 |
| I | 15,113 | 15,272 | 4,728 |
| J | 17,437 | 16,540 | 3,460 |
| K | 15,611 | 15,326 | 4,674 |
| L | 23,618 | 19,814 | 186 |

전송할 실제 새 지침4,857UTF-8bytes와 새 도구 이름의 raw/normalized 출력 schema 중 큰 값(L6,081/5,821), prompt(L5,028), framing2,048/output1,800을 포함했다. 이전 codec의 기존 지침+추가 설명 비교19,820과 별개로 실제 새 SDK 지침/도구로 계산한 값이다. 실제 tokenizer 토큰 수·청구 usage나 OpenAI 서버의 수용 보장은 아니다. wire의 정확 canonical prompt·새 지침/strict 도구/schema·store=False/maxOutput1,800/timeout30·borrowed settings와 client 수명·자체 영수증을 확인했다.

원래 balancedL의 차단23,618과 기존 결과/질문/기준·모든 사용량/부분 점수는 그대로다. 작은G/H/I는 기존보다 입력 비용이 증가하므로 보편적 압축 성공을 주장하지 않는다. 임의의 긴 Source는 여전히 한도 초과로 거부될 수 있으며 축약/한도 상향으로 우회하지 않는다. 초기 parent 합성 helper가 SDK의 문자열 content를 배열형으로 가정해 실패한 기록을 보존했고 실제 serializer 형식과 일치하도록 helper만 수정했다. 실제 provider 재호출이나 제품 코드 변경은 없다.

다음은 이 새 SDK의 한 번씩 고정된 실제 모델 응답·미완료/known usage·사전12명제 의미/역할/관계 평가다. 합성 completed나 빈 결과를 실제 추출 성공으로 세지 않으며 앱/worker 활성화도 그 인수 후 별도로 판단한다.

## 최종 전체 검증

실행 구현87e2746/검증 head e580e17에서 신규123개 포함 전체8,696개(Python7,876+JS820)와 Ruff/format440/mypy·ESLint/TypeScript/생산빌드/OpenAPI drift가 통과했다. 실패/skip/warning0, 검사 전후 실행 코드 해시가 같다. 태스크·새 전체 독립 검토 C0/I0/M0·미해결/보류0이며 세 판단/비용은 위 기록과 같다. 기존460non-Markdown파일·실제642/설계121/이전구현12/연구10/신규원문33/직전codec75증거를 보존했다. 실제 provider 요청0/앱 변경0이다. 최종 PR/Sites/소유 임시 자원 인계는 진행 기록을 따른다.
