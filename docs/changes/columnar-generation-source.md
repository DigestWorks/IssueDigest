# 전체 원문을 보존하는 columnar generation source

2026-10-23 한국 시간. 기반 [신규 원문 차단 진단](../research/new-source-recall-acceptance.md). OpenSpec root:null 확인, init 없이 spec-driven의 구현 절차를 적용한다. 이번 산출물은 별도 순수 입력 codec이며 provider SDK·출력 schema·앱 연결은 후속이다. 기존 원문/후보/조건을 줄이거나 예산을 늘리지 않는다.

## Global Constraints

Freeze458 existing non-Markdown tracked files and all prior actual642/design121/implementation12/research10/new-source33 evidence. Add only new packages/agents/src/issuedigest_agents/generation_source_packet.py and new packages/agents/tests/test_generation_source_packet.py; implementation task may update its own checkbox. No existing code/tests/config/dependency/instructions/SDK/model/profile/runtime edits, provider calls, private actual evidence, old runner execution, server/app/API/DB/UI changes or deployment. Controller owns reviews/fullQA/offline private sources/preservation/privacy/docs/PR/Sites. TDD first; use restore_introduced_modules fixture. Implementer never dispatches subagents or fullQA/push/deploy. No semantic approval, candidate filtering, source truncation, normalization, hidden lower caps or automatic repair. Source and untrusted packet exact original types must be guarded before dumping. Output JSON mutable but each call independent; never claim deeply frozen DTOs. Keep existing balanced generation failure/receipts and source bytes unchanged.

## Spec

`build_generation_source_packet(source: Source) -> dict[str, Any]`, `validate_generation_source_packet(source: Source, packet: Any) -> dict[str, Any]`, `decode_generation_source_packet(source: Source, packet: Any) -> dict[str, Any]`, `generation_source_packet_prompt(source: Source) -> str`. Fixed sanitized GenerationSourcePacketError("Invalid generation source packet") suppresses chained cause/source/partial result. No I/O/client/model on import or any operation.

Guard Source via existing exact raw/actual Source guard before any serialization. Rebuild current numeric-candidates-v2 index and frozen `_source_packet`, `_eligible`, context/event slots read-only, projecting the same complete JSON payload that balanced v2 would construct before its envelope check: profile shared-role-aliases-v2, quotes/candidates, eligible_status_sentence_ids, context_id_slots,reporting_event_id_slots. Convert trusted internal tuples to JSON lists through existing `_json`/json.loads. Do not call balanced `_preflight` because its full-source rejection must remain unchanged. No provenance UUID/metadata leaked into this projection; q/s/n/c/e IDs remain same.

Root packet exact fields: input_format=columnar-generation-source-v1, profile=shared-role-aliases-v2, atom_columns=[number,unit], candidate_count=int, candidate_columns=dict, quotes=list, eligible_status_sentence_ids=column,context_id_slots=column,reporting_event_id_slots=column. candidate_columns exact fields id,quote_id,sentence_ids,expression,atoms,lexical_kind,qualifiers,separator. Atom values encode each original atom dict as [number,unit] in original order. Each quote exact fields quote_id,sentence_count,sentence_columns; sentence_columns exact id,text. Keep quote order, every sentence including whitespace/empty partitions, all candidates/atoms/qualifiers/separators/unknown/unit-null values and original orders. Counts are exact lengths. No arbitrary candidate/quote/sentence cap beyond existing validated Source/index.

A column is one canonical shortest representation among options, comparing byte length of existing canonical `_json(option).encode('utf-8')`, tie by option order below. Every option and nested value is JSON list/string/int/null/dict as produced, no coercion:
1. [values, vector] always, including empty vector.
2. [constant, value] only nonempty and all values JSON type+value equal.
3. [dictionary, pool, indices] only nonempty, pool unique in first-occurrence exact JSON type+value order and indices zero-based ints; preserve duplicate rows through indices.
4. [indexed, prefix, suffixes] only for ID-bearing columns defined below and nonempty vector of strings matching full `([qsnec])([1-9][0-9]*)`, same prefix; suffixes exact base10 ints and decoding prefix+str(int) restores every original string. This is explicit prefix coding, not renumbering.
5. [indexed_lists, prefix, suffix_lists] only for ID-bearing columns defined below and nonempty vector of lists of such strings, flattened values nonempty and same prefix; preserve empty sublists and all nested order. Each suffix exact int.
ID-bearing columns are candidate id, quote_id, sentence_ids; quote sentence id; and top-level eligible_status_sentence_ids, context_id_slots, reporting_event_id_slots. Other columns (including sentence text and candidate expression/atoms/lexical_kind/qualifiers/separator) use only values/constant/dictionary even if literal text resembles an ID. This semantic eligibility prevents original content from being interpreted as machine identifiers, preserves all valid Source text without decimal conversion limits, and does not change the interpreter safety limit.

Constants/dictionaries must not treat true/1, null/empty string or list/tuple as same; source-derived values trusted JSON, public untrusted input still exact guard. Small columns may remain values if other modes are longer; no assumed compression success on every input. Return fresh independent structures, no exposed shared mutable tables.

Validation: copy/guard original raw JSON via existing strict `_copy_json` before any dump (reject subclasses, non-string keys, tuples, BaseModels, unchecked values); compare every scalar/type/field/list order to a freshly rebuilt canonical current-source packet with `_same_json` before interpreting modes/indices. Thus alternate semantically equivalent encodings, re-ordered dictionary pools, extra fields, same-size substitutions, wrong counts, prefix/indices changes, reference/quote/source drift and noncanonical ties reject. Decode only after full canonical match, expand every column/count/atom/quote, compare full reconstructed original JSON payload to current-source original, then return that fresh complete payload. No partial output on error. Do not just return the original without exercising decoding. Source identity/provenance validation is inherited from current builders, not authorization or provider authenticity.

Export `GENERATION_SOURCE_PACKET_INSTRUCTIONS` verbatim: `Columns align by zero-based row. values stores a vector; constant repeats one value; dictionary stores pool,indices; indexed stores prefix,suffixes; indexed_lists stores prefix,suffix-lists. Atoms use atom_columns.` This is future input-format guidance, not an active SDK instruction replacement. Prompt returns canonical JSON of current packet after construction, no provider envelope acceptance claim. Controller measures full current schema/instructions/framing/output plus this actual guidance on6frozen sources; no capacity/quality guarantee is inferred from pure codec roundtrip.

## Task 1: Pure canonical codec and boundary tests

- [x] Implement source-aware columnar codec and TDD tests.

Own only2newfiles and checkbox above. Read Spec/Global Constraints as requirements. Tests first record missing-module RED, implement then focused checks. Synthetic literal expected projections/column encodings (all5modes including ties/empty/null/duplicate/indices/IDs); independent public dense/short/multiquote/zero-candidate/whitespace/Unicode/range/qualifier/atom-null-unit fixtures. Source reconstructed JSON must equal frozen existing source projection and whole quote text exactly; full candidates/slots/eligible IDs retained. Guard original Source nested model/container/scalar/required-marker subclass/unchecked changes before dump; packet raw tuple/subclass/key/float/true/index model/new fields/count/mode/pool/order/duplicate/reference/span/source mutations reject. Every new field and mode kind should have meaningful tamper coverage without exhaustively repeating old SDK leaves. Freshness mutation cannot alter next result, validate/decode raw actual object is plain JSONdict only; no BaseModel acceptance. Test complete index with256candidates if valid fixture permits,20quotes, repeated sentences/large lists without new hidden limits. Import +operations network/client purity. Synthetic only, no private saved trials or outside fixture reads. Scoped newtests+compact shared context+balanced generation and ruff/format/mypy; do not run fullQA. Detailed report via controller path, commit owned files/checkbox and report stable code before handoff.

## Controller gates

- [x] Task +fresh whole-branch review (I1 fixed, scoped C0/I0/M0); fresh fullQA on stable code.
- [x] Frozen G~K+new fullsource canonical roundtrip, actual size incl guidance/schema/framing/output; preserve old rejections/criteria/usage/no paid calls;458code/642actual/121design/previous12+10+33evidence/privacy/link checks.
- [x] Draft PR95/Sites v117 previousv116 archive; ownSDD archived/ownQA removed, branch/worktree retained. No app/main deployment.

## 구현·오프라인 대조

구현source ead688d, 최종 수정26db0d1. 새121개를 포함한 관련233개 검사·scoped ruff/format/mypy를 통과했다. 모든5표현/정확 scalar·key/container/model 경계·canonical tie와 사전 순서·실제 decode·빈 후보/20quote/256candidate/공백·중복·Unicode를 확인했다. 이 검증은 의미 정확도/권한/공급자 진위 인증이 아니다. 전체 검사는 최종 영수증을 따른다.

기존G~K와 신규L의6자료를 현재 원문에서 다시 구성해 모든 JSON 값·순서/타입·문장/빈 문장·후보/atom/qualifier/단위·슬롯/eligible ID를 복원했다. 원문 문장을 결합한 전체 quote도 같다. 기존 SDK·지침·원래 결과/사용량·차단은 그대로다. 무호출 대조는 이미 본 자료의 개발 검사이지 새로운 holdout·모델 품질 평가가 아니다.

| 자료 | 기존 보수 envelope | 새 packet + 추가 형식 설명의 비교 envelope |
| --- | ---: | ---: |
| G | 15,398 | 15,435 |
| H | 15,075 | 15,240 |
| I | 15,113 | 15,278 |
| J | 17,437 | 16,546 |
| K | 15,611 | 15,332 |
| L | 23,618 | 19,820 |

비교 envelope는 기존 지침·같은 동적 출력 tool/schema·framing2,048/output1,800을 유지하고 새 형식 설명(앞 newline 포함215UTF-8bytes)을 **추가**한 계산이다. 실제 새 SDK `_preflight`/provider wire를 구성·검증한 결과가 아니다. 작은G/H/I는 설명/형식 비용으로 오히려 증가하며 모든 입력이 줄어든다고 주장하지 않는다. L prompt는9,041→5,028bytes이며 추가 설명까지 더한 순감소는3,798이다.20,000 대비 여유가180뿐이라 실제 새 지침/출력 도구 이름/형식·지원 자료군·모델 읽기·미완료/비용 인수 전에는 요청 수용 해결로 부르지 않는다. 이 수치는 tokenizer의 실제 토큰 수/청구 usage가 아니다.

현재 balanced v2 `_preflight`의 L차단23,618은 여전히 남아 있다. 순수 codec을 기존 SDK에 끼우거나 같은 SDK 영수증/profile로 위장하지 않았다. 별도 versioned generation SDK의 입력 형식 지침·profile/prompt/instruction hash·실제 잔여 예산·오류/known usage/송신 불확실성·무재시도 계약을 검토/구현한 뒤 실제 수용·의미를 인수해야 한다. 앱/API/DB/UI/worker·main/서버/실제 모델 호출0이다.

## 최종 검토에서 확인한 경계

초기 전체 검토에서 유효한4,302문자 본문이 `q`와 긴 숫자로만 구성되면 ID 압축 후보를 평가하다 정수 변환 한도에 걸리는 Important1건을 재현했다. 초기 전체 검사는 수정 전에 중단하고 해당 로그를 보존했으며 최종 통과 증거에 합산하지 않는다.

판단: ID prefix 압축은 실제 ID 열에만 적용하고 본문·표현·조건 같은 원문 값에는 값/상수/사전 표현을 사용한다. 현재 원문을 그대로 복원하고 전역 정수 안전 한도나 Source 허용 범위를 바꾸지 않는다. 잘못 판단했을 때의 비용은 일부 ID처럼 생긴 원문이 더 길게 인코딩될 수 있다는 점이며 내용 손실은 없다. 수정 회귀·수정 범위 재검토·최종 전체 검사는 최종 영수증을 따른다.

수정26db0d1에서 신규 회귀9개·관련233개와 scoped 정적 검사를 통과했고 독립 수정 재검토는 I1해결/새C0I0M0다. 기존6자료 packet/전체복원/비교결과도 초기 구현과 byte동일하다. 본문은 실제 ID로 해석하지 않으며 위 비교 수치와 기존 실패·점수는 변하지 않았다. 최종 전체 검사는 아래 영수증과 같다.

## 최종 전체 검증

수정 구현26db0d1의 신규121개를 포함한 전체8,573개(Python7,753+JS820)·Ruff/format438/mypy·ESLint/TS/생산빌드/OpenAPI drift를 통과했다. 실패/skip/warning0이며 검사 전후 실행 코드 해시가 같다. 초기 중단 검사는 이 결과에 포함하지 않는다. 태스크 검토·초기 전체I1수정·scoped재검토 C0/I0/M0, 보류/미해결 지적0이다. 기존458실행파일·실제642/설계121/이전구현12/연구10/신규원문33증거와 원래 실패/비용을 보존한다. 새 모델/서버/앱 변경0이다. PR/Sites/소유 임시 자원 정리는 최종 게시 인계를 따른다.
