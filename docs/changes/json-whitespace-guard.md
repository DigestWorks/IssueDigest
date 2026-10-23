# JSON 도구 인자 · 연속 공백 감지

2026-10-23 한국 시간. 기반 PR104/b0430b3 및 사전 진단935311d. [출력 정체 조사](../research/question-evidence-stall-investigation.md)에 이어 순수 증분 감지기를 구현한다. OpenSpec root:null이며 init 없이 spec-driven-workflow 2단계를 적용한다. 원인 해결·실제 취소/비용 절감·앱 인수와 구분한다.

## Global Constraints

Freeze all468 existing non-Markdown files and all prior source/question/criteria/provider results/usage/consumed namespaces. Implementer owns ONLY new packages/agents/src/issuedigest_agents/json_whitespace_guard.py, new packages/agents/tests/test_json_whitespace_guard.py and Task1 checkbox. No changes to existing runtime/SDK/pure contracts/tests/exports/deps/API/worker/UI/DB/server/settings/main. Synthetic TDD only, no private data/old runners/network/provider/resources/fullQA/subagents. Controller owns private recorded-argument replay, wholeQA/reviews/docs/PR/Sites/cleanup. No client creation, request cancellation, retry, output repair/truncation, semantic/access/completion approval, usage accounting or default free-cost assertion. No retained text/partial returned values/errors containing input/cause. Do not add hidden source/question/budget limits.

## Spec

New pure standard-library module: JSON_WHITESPACE_GUARD_PROFILE="json-whitespace-guard-v1", JSON_WHITESPACE_RUN_LIMIT=256, JsonWhitespaceGuardError(ValueError), JsonWhitespaceGuard. Constructor takes no arguments and starts in_stringFalse/escapeFalse/run0/characters0/failedFalse. Public read-only properties failed:bool, characters_consumed:int, outside_whitespace_run:int. No reset/resume API. No arbitrary-object tamper/deep immutability guarantee.

feed(delta:str)->str accepts ONLY exact type str (not subclasses), never coerces/stringifies. If already failed, raise fixed "JSON whitespace guard already failed" from None without reading delta or changing counters. Invalid original type latches failed=True, raises fixed "Invalid JSON argument chunk" from None with counters unchanged and no repr/stringification. For every inspected Python Unicode code point increment characters_consumed, including the point that breaches the limit. Empty delta returns the identical empty string and does not reset pending state/counters. Successful feed returns the exact original delta object, byte/text content unchanged. Never buffer or retain input chunks/text; retain only lexical flags/counters. A rejected multi-character chunk returns no accepted prefix; prior successful feeds are not revoked or certified.

Lexical state persists across arbitrary chunk boundaries. Within JSON string: backslash escapes the next code point, escaped quote must not end string, odd/even backslashes and literal backslash-u sequences behave lexically; no unescaping/Unicode normalization. Outside JSON string: ASCII space, TAB, CR and LF increment one continuous whitespace run; quote enters string and resets run, every other code point resets run. Whitespace inside strings is untouched and never contributes to outside run, even if very long or JSON-invalid. Never use str.isspace() to broaden policy to non-JSON Unicode whitespace. Valid run256 passes;257 latches failure and raises "JSON whitespace run limit exceeded" from None immediately, without inspecting remaining suffix. After failure, counters remain at that first offending point on every subsequent feed.

The guard is deliberately NOT a JSON parser/completion validator/schema/source/semantic validator. Non-JSON fragments, incomplete strings, non-ASCII whitespace, repeated punctuation and noncontinuous stalls are outside its detection guarantee. Legal formatting whitespace outside strings can exceed256 and be rejected; this is a fixed heuristic policy under its own profile. No higher/lower override in this version. Request/output token limits and normal final validation remain caller responsibility. Constant count of scalar state fields; no cumulative output storage. No assertion that characters_consumed means forwarded characters, tokens, latency or provider billing.

Caller must feed each exact tool-argument delta before buffering/using it, latch the same guard per argument stream, and handle its exception by deciding transport cancellation. This module performs no cancellation or streaming integration. A closed stream can miss final usage; preserve existing known usage plus may-have-started/unknown cost in the later runtime and never retry automatically. Existing SDK/source/paid paths remain unchanged.

## Task 1: Incremental whitespace guard

- [x] Implement only new module/tests+checkbox with RED→GREEN TDD.

Read test-driven-development skill. Meaningful tests: 0/256/257 boundary; whole vs1/2/mixed chunks across threshold and empty chunks; reset by legal non-whitespace; TAB/CR/LF combinations; long whitespace inside JSON strings preserved; opening/closing and escaped quotes/backslashes including boundaries/odd-even runs and literal backslash-u; Unicode/emoji/non-ASCII whitespace unchanged and not counted as outside JSON spaces. Invalid object/None/bytes/int/bool/str subclass rejects without calling malicious __str__/__repr__/iteration, failed latch and stable counts including rejection suffix not visited, no reset method/read-only public counters. Success same object identity/content; no partial return or input-bearing error/cause; no retained chunk/text state. Known valid json.dumps documents under different partitions as preservation cases; ordinary malformed/incomplete fragments demonstrate no JSON-validity claim. Use synthetic fixtures only. No real timing/network or provider API; no actual model/source data. Run focused suite/scoped Ruff/format/mypy/diff checks, not wholeQA. Do not mirror the implementation with a copied scanner oracle; test controlled cases and partition invariance. Commit owned3paths, write exact RED/GREEN/static/selfreview evidence in own SDD task report.

## Controller gates

- [x] Task spec/quality and whole-branch review C0I0M0; 새전체9,316개(Python8,496+JS820)·정적 검사/빌드/OpenAPI·실패/skip/warning0.
- [x] Read-only old actual v1/v2 argument replay under multiple synthetic partitions; preserve468/prior proof and current single native probe timeout/unknown usage. No new paid request.
- [x] Docs/privacy/links, Draft PR105 basePR104, Sitesv127/previousv126·7exact-doc snapshots, ownQA/SDD cleanup. No app/worker/main activation.

## 판단과 비용

1. 문자열 밖 ASCII JSON 연속 공백256을 감지 한도로 둔다. 관측6,619bytes를 조기에 식별하려는 휴리스틱이며 정상 formatting도 거부할 수 있고 다른 정체 형태는 놓칠 수 있다. 최적 한도/실제 절감은 미검증이다.
2. 문자 내용을 보존하는 순수 감지기만 추가하고 실제 streaming 취소/재시도·비용 처리를 연결하지 않는다. 기존 유료 경로를 지키는 대신 현재 앱의 지연/비용을 바로 줄이지 못하며 통합·사용량 미관측 인수가 추가로 필요하다.

## 검증 결과

실행63fc05b·합성155/새전체9,316개(Python8,496+JS820)·정적 검사/빌드/OpenAPI·실패/skip/warning0, 태스크/전체 검토 C0I0M0다. v2 기록 인자 네 합성 분할은 문자2,554/연속 공백257에서 거부되고 v1 미완료는 그대로 통과한다. 기존468실행/과거 증거·사전 고정14파일은 유지했다. [Draft PR105](https://github.com/DigestWorks/IssueDigest/pull/105), 실제 SDK/스트림 취소·앱 연결은 후속이다.
