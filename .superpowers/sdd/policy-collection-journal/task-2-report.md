# Task2 implementation report

Scope: worker private collection job parser/coordinator, `issuedigest-policy poll/status`, synthetic tests, worker README and Task2 checkboxes. Storage, migration, existing capture/compare/preparation SDKs, dependencies/lockfile, research worker, public/API/web contracts were not changed. No subagents, real server/data/keys/source HTTP or controller restore DB were used. Only the dedicated synthetic PostgreSQL18.6 on25457 was used.

## API and behavior

`issuedigest_worker.policy_collection` exposes:

- `parse_policy_collection_job(raw: str | bytes) -> PolicyCollectionConfig`: maximum8192 UTF-8 bytes; duplicate JSON keys, nonfinite numbers, extra fields and boolean integers rejected. JSON UUID4/string and array are converted explicitly before strict storage config validation; IDs normalize to a sorted distinct ASCII9-digit set of1–2. Fixed failure is `ValueError("Unable to validate policy collection job")`. Files are read through the existing descriptor-anchored private-file helper; the CLI requires an owned400/600 absolute regular file and rejects symlinks/replacements/oversize files.
- `poll_policy_collection(engine, config, *, clock=UTC_now, transport=None) -> PolicyCollectionPoll`: a single leased, admitted attempt. `busy/not_due/attempt_limit` return typed aggregates with no source HTTP/new attempt. `running` is committed and observable from a separate DB connection before the existing capture SDK is called. Baseline storage/hash read failures propagate as storage errors, leaving the admitted attempt running; they never become a false capture/validation terminal.
- Baseline semantic validation precedes HTTP: exact capture parser and immutable article scope; captured timestamp within baseline start/completion; existing comparison re-extracts identity/body/eligibility. Stored report is strict JSON/model with exact after capture hash/time, ordered scope, recomputed after fingerprints, coherent before hash/time pairing/order and source status/fingerprint/changed-field shape. Invalid baseline semantics/report produces only `validation_failed`, with zero fresh HTTP and previous success untouched. The previous report's before-side cannot be independently recomputed from the single baseline API; the observable after-side is recomputed and before-side structural consistency is verified.
- Fresh HTTP uses only existing fixed `capture_policy`, preserving TLS/timeout/size/no redirect/proxy/env-auth/cookie/retry policy. Exact `serialize_policy_capture` bytes and `compare_policy_captures` report bytes are atomically stored by the journal API. First success is `new`, a repeated body is `unchanged`, semantic changes are `changed`; scope is exact so no deletion/withdrawal is inferred. SDK capture failure produces `capture_failed`; body/license/parser/semantic failures produce `validation_failed`. Storage failures and start/success commit-unknown exceptions escape without retry or failure overwrite.
- Request `collected_at` is the actual request-start clock after baseline verification; terminal `finished_at` is a fresh completion clock after capture/comparison, never backdated to collection start. A request clock earlier than the committed start is rejected before HTTP. A completion clock earlier than capture request fails validation instead of storing inconsistent success. Invalid journal completion clocks remain subject to storage's strict time checks.
- `policy_collection_status(engine, config, *, now=None) -> PolicyCollectionStatusSummary`: delegates to the existing consistent read-only storage operation, then explicitly maps only safe aggregate/time/state fields. `latest` is independent of `last_success`; private attempt/channel/article IDs never enter returned summaries. No source/model call or row creation. Age/stale uses actual last successful journal completion, not SDK request start, publication/content freshness or collection coverage.

`issuedigest-policy poll PRIVATE_JOB` and `status PRIVATE_JOB` are explicit opt-in DB commands. Only that branch reads `ISSUEDIGEST_DATABASE_URL`; existing operator URL guards prohibit query overrides and compare expected DB before engine creation, then storage checks the actual DB. Engine uses hide_parameters/no echo/no pre-ping, and existing `private_engine_lifecycle` provides private log sinking and disposal before output. CLI JSON uses explicit field allowlists including nested status metadata. Successful poll and normal denials exit0; actual failed poll prints only the safe failure aggregate and exits1. Storage/commit/cleanup/input failures print the existing fixed error, no aggregate, exit1. Arguments retain fixed exit2. Existing discover/capture/compare/prepare file/output behavior remains covered by regression tests.

## TDD and verification

Tests name observable behavior: journal rows/exact bytes/history/status and source-request admission, with real PostgreSQL and synthetic `httpx2.MockTransport`. No mock repository is used. Synthetic failure injection acknowledges real DB commits before raising, terminates an actual leased backend during capture and SIGKILLs a child after a committed running row.

RED commands/results:

1. `ISSUEDIGEST_TEST_DATABASE_URL=<dedicated synthetic URL> uv run pytest apps/worker/tests/test_policy_collection.py -q` ->32 expected failures: collection coordinator missing; no production code existed.
2. After coordinator implementation the same32 tests passed. Added CLI/storage-boundary tests -> expected CLI missing-command failures; commit-unknown injection initially targeted lease setup commits rather than journal commits, so the test hook was corrected to the documented third/fourth commits. Then47 tests passed.
3. Request clock reversal and forged equal before-time RED ->2 failures reaching forbidden HTTP. Added pre-HTTP time guard and strict prior report time order ->49 passed.
4. Completion clock reversal RED (`-k completion_clock`) ->1 failed/1 passed: inconsistent success was observed. Completion/capture time validation added ->53 passed.

Final checks, all exit0:

- Sequential covering regression: `ISSUEDIGEST_TEST_DATABASE_URL=<dedicated synthetic URL> uv run pytest apps/worker/tests packages/connectors/tests/test_policy_sdk.py packages/ingestion/tests/test_policy_html.py -q` ->**645 passed in43.88s**, including52 collection tests, existing private discover/capture/compare/prepare and paid execution/recovery checkpoints. This covering run preceded the final isolated completion-clock guard.
- Final collection suite after that guard: same environment + `uv run pytest apps/worker/tests/test_policy_collection.py -q` ->**53 passed in1.30s**.
- `uv run ruff check apps/worker/src/issuedigest_worker/policy_collection.py apps/worker/src/issuedigest_worker/policy_cli.py apps/worker/tests/test_policy_collection.py` ->all checks passed.
- `uv run ruff format --check` on the same three paths ->3 files already formatted.
- Project-configured `uv run mypy` ->success,109 source files. An earlier worker-only invocation reported9 existing cross-package untyped-import/unused-ignore errors; configured project invocation resolves the workspace packages correctly and passed without changing them.
- `git diff --check` ->clean.

One earlier covering run was639 passed/1 failed: `test_recovery_never_calls_model_for_unknown_cancelled_or_unauthorized_run[revoked-membership-v2]` raised KeyError because its run disappeared. Systematic-debugging investigation traced worker_states' absent row back to the common fixture's TRUNCATE of research_runs. I had launched collection PG tests while that covering run was still active, and both used the same synthetic DB/reset fixture. This was test orchestration interference. The isolated failing recovery test passed (1 passed in3.83s), then the complete covering regression rerun sequentially passed645. No research product/test behavior was changed. All fixture-resetting PG commands after diagnosis were sequential.

## Limits and handoff

Full repository suite and independent review remain controller gates; targeted worker/source/parser regression is recorded above. Real migration/source acceptance/backup/permissions/scheduler were not attempted. README documents the one-shot commands, interval/attempt limits, separate scheduler environment and stop/rerun behavior, retention of successful originals, safe output and absence of automatic discovery/research/evidence registration/publication/deletion/limit reset. Database owners can still bypass repository immutability; this change does not add a tamper-proof trigger/privilege system. No storage API additions or edits were needed.


## Mechanical full-suite collection fix

Controller integration found a pytest default basename-import collision between the worker and storage `test_policy_collection.py` modules. Historical commands above retain the then-current path. The worker module is now `apps/worker/tests/test_policy_collection_worker.py`; contents are identical (100% Git rename), and storage/runtime/global pytest configuration were not changed.

RED: `PATH=/home/xinics/.local/bin:$PATH uv run pytest --collect-only -q` exited2, with2699 tests collected and one import-file-mismatch error collecting `packages/storage/tests/test_policy_collection.py`: imported `test_policy_collection` pointed to the worker module. Log: `/tmp/policy-test-module-red.log`.

GREEN after the rename, executed sequentially:

- Same whole-repository collect-only command: exit0, **2724 tests collected in1.07s**. Log: `/tmp/policy-test-module-collect-green.log`.
- `ISSUEDIGEST_TEST_DATABASE_URL=postgresql+psycopg://issuedigest_test@127.0.0.1:25457/issuedigest_test uv run pytest apps/worker/tests/test_policy_collection_worker.py -q` with the same PATH: exit0, **53 passed in1.36s**, warnings/skips/failures0. Only the leased synthetic DB was used. Log: `/tmp/policy-test-module-tests-green.log`.
- `git diff --check`: clean; staged diff is one100% rename with zero content additions/deletions.

No subagents, real data/server/keys, external source HTTP, runtime changes or parallel DB fixture runs. Full actual suite remains controller's integration gate. Commit is recorded in `test-module-fix-report.md`.
