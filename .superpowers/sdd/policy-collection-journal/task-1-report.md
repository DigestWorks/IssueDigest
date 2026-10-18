# Task1 implementation report

Scope: independent PostgreSQL journal/schema/migration, guarded leased storage API, synthetic reset/tests and storage README. No connector/worker imports, dependencies, public/API/web changes or real operational access. Authoritative requirements: current Task1 in `docs/changes/policy-collection-journal.md` (interrupted marking precedes interval/limit denial).

## Worker API

Import from `issuedigest_storage.policy_collection`:

- `PolicyCollectionConfig(schema_version=1, expected_database: str, collection_id: UUID4, news_ids: tuple[str, ...], minimum_interval_seconds: int, max_age_seconds: int, max_attempts: int)`: strict/frozen/extra-forbid. UUID must be a Python UUID4; news IDs must be a tuple of 1–2 distinct9-digit ASCII strings, normalized by sorting. Integer booleans are rejected. interval60..86400, age interval..604800, attempts1..4096. Private JSON parser remains Task2 responsibility; convert JSON UUID/list to UUID/tuple after strict input validation. Every repository input revalidates actual fields, including model_copy/model_construct bypasses; no serializer warnings with private forged values.
- `PolicyCollectionRepository(engine)`: construction has no connection or DDL side effects. URL must be postgresql+psycopg and name must equal expected_database. Actual current_database is checked on each operation.
- `repo.lease(config)`: context manager yielding `PolicyCollectionSession | None`. None means busy. Dedicated connection retains nonblocking session lock `(104704, 2)` through all method transactions/HTTP. Session has no public replacement/reconnect capability. It verifies original driver object/backend PID and pg_locks ownership before operation and again before write commit. Caller must use context manager even after errors. Every lease is read-write READ COMMITTED, overriding inherited AUTOCOMMIT/read-only engine options.
- `session.start(*, now: datetime) -> PolicyCollectionStart`: outcome started/not_due/attempt_limit. Only started has `.attempt`. Creates/binds immutable channel if absent; verifies metadata sequence/state/time; marks previous running failed/interrupted **before** interval/limit decision; then inserts next sequence if allowed. All changes commit before returning. not_due/attempt_limit insert no new attempt; they may commit interrupted recovery. Same lease cannot start again while its attempt remains active.
- `session.baseline() -> PolicyCollectionBaseline | None`: explicit no-write read of last succeeded attempt, verified history, exact capture_bytes/capture_sha256/report_bytes/report_sha256 and `.attempt`. Can run before/after start. Raw bytes are excluded from repr. Both hashes, byte types/lengths and configuration hash are checked; report semantic/content parsing belongs to worker. No automatic artifact repair or previous-baseline fallback.
- `session.succeed(attempt_id: UUID, capture_bytes: bytes, report_bytes: bytes, *, finished_at: datetime) -> None`: exact, nonempty bytes; capture<=8MiB+16384, report<=65536. Computes both SHA256 values and atomically stores succeeded terminal. Only active UUID returned by this same session's successful start is accepted. Previous terminal/originals never updated.
- `session.fail(attempt_id: UUID, failure_code: Literal['capture_failed','validation_failed'], *, finished_at: datetime) -> None`: failed terminal without raw or exception text. interrupted is repository-only recovery code. Last successful original survives failures.
- `repo.status(config, *, now: datetime) -> PolicyCollectionStatus`: REPEATABLE READ READ ONLY consistent metadata read, no row/DDL/HTTP/model-provider creation. Fields: attempt_count; latest and last_success as distinct `PolicyCollectionAttempt | None`; age_seconds float|None; stale bool. Attempt fields: internal UUID4 attempt_id, sequence, state running/succeeded/failed, started_at, finished_at|None, failure_code|None. Do not print identifiers/config/model repr from CLI. Raw columns are not selected by status.

```python
# cfg has already passed private job validation; engine is under private_engine_lifecycle.
repository = PolicyCollectionRepository(engine)
with repository.lease(cfg) as session:
    if session is None:
        # busy aggregate; no HTTP
        ...
    else:
        started = session.start(now=started_at)
        if started.outcome == "started":
            baseline = session.baseline()  # verify/parse it before source HTTP
            # Task2: fixed SDK capture/compare/serialization, no storage exception retry.
            session.succeed(started.attempt.attempt_id, exact_capture, exact_report,
                            finished_at=finished_at)
# A subsequent status read is explicit; render only aggregate/status/time/stale fields.
state = repository.status(cfg, now=status_time)
```

All supplied datetimes must be exact aware datetime instances; UTC normalization rejects overflow/naive/reversed times. Completion must be >= start; each later start must be >= previous completion. Status now must not precede observed start/completion. **Storage age/stale uses last_success.finished_at (journal completion), not the opaque SDK collected_at field.** stale is True when no success or age_seconds > max_age_seconds. This is 마지막 성공 확보 완료 시각 기준. Worker supplies actual journal completion time and retains SDK collected_at in exact capture bytes; it must not fake finished_at to match capture start. No collected_at metadata column is added. Storage cannot infer semantic capture time from opaque bytes. No claim of publication/content freshness or source coverage completeness follows from stale=False. This completion-clock interpretation was explicitly confirmed by controller.

## Transaction and failure boundaries

Channel binding + interrupted recovery + admission + running insertion are one committed transaction. HTTP begins only after start returns started. Baseline reads roll back their read transaction without ending the session advisory lease. Terminal update+both artifacts+hashes are one transaction, restricted by WHERE state=running and same channel/attempt. No external network is called here.

`PolicyCollectionError` string is exactly `Policy collection storage unavailable`. Input, stored-config/type/hash/state/history/time/ownership/DB errors are sanitized and never contain private values. Failed statements roll back. SQLAlchemy connection failures poison the session. Unlock/close failures are sanitized and failing connections invalidated. No replacement backend is opened after invalidation. Context exit verifies exact lock release; lock already lost is an error unless a previous method already surfaced that poisoned lease.

`PolicyCollectionCommitUnknown` subclasses PolicyCollectionError; string exactly `Policy collection commit unknown`. Any exception acknowledging start/terminal commit poisons the session. **Do not retry the commit or HTTP, do not call fail or succeed again, and do not overwrite with a failure.** Exit the context. Actual commit may have succeeded; the next explicit status/poll reads stored reality. A remaining running row becomes interrupted on next start; a committed terminal remains immutable. This holds when the database committed but client acknowledgment was lost, tested by raising after a real commit. CLI engine/pool lifecycle sink remains caller responsibility.

`0008_policy_collection` is an explicit Alembic migration with standalone frozen table definitions matching runtime schema. UUID4, channel FK, unique channel sequence, positive bounded sequence, one running/channel, nullable state shape, allowed failure enums, bounded success bytes/hashes and completion>=start are DB constraints. Repository provides append-only terminal/original behavior; database owners can bypass repository and alter data, which read boundaries detect where covered. This is not a DB trigger/privilege-based tamper-proof audit system and adds no deletion/retention/scheduler policy.

## TDD and verification

Dedicated owned PostgreSQL18.6 only; environment supplied ISSUEDIGEST_TEST_DATABASE_URL. No real server/data/keys/source HTTP used.

RED: `uv run pytest packages/storage/tests/test_policy_collection.py -q` ->8 failed with `Policy collection journal is not implemented` before production code. Follow-up RED cycles exposed private serializer warnings, baseline sequence gaps, hidden unlock failure, unhashable failure code, UUID4 schema gap, stored JSON True==1 hash bypass, silent lease-exit lock loss, timezone overflow, and inherited AUTOCOMMIT persisting a terminal before failed precommit guard. Each was corrected before its GREEN check.

Final GREEN verification (all exit0):

- `ISSUEDIGEST_TEST_DATABASE_URL=<dedicated synthetic URL> uv run pytest packages/storage/tests -q` -> **519 passed in14.61s**, including25 new collection tests; no warnings/failures. Existing migration base downgrade/head upgrade/repeat regression and seeded0007→0008 preservation regression both passed.
- `uv run ruff check packages/storage/src/issuedigest_storage/policy_collection* packages/storage/migrations packages/storage/tests/test_policy_collection.py conftest.py` -> All checks passed.
- `uv run ruff format --check packages/storage/src/issuedigest_storage/policy_collection* packages/storage/migrations packages/storage/tests/test_policy_collection.py conftest.py` ->13 files already formatted.
- `uv run mypy packages/storage/src packages/storage/migrations` -> Success: no issues found in34 source files.
- `git diff --check` -> clean.

Known limits: full project suite, CLI/SDK coordination, actual source capture, operational migration/scheduler/backup are controller/Task2 responsibilities and were not performed by this implementer. Session `_connection`/`_pid` are internal and only used by synthetic failure-injection tests. Database schema owners can deliberately bypass repository append-only semantics; no new DB role/trigger policy was authorized. There is no automatic retention deletion, attempt-limit reset or HTTP retry.
