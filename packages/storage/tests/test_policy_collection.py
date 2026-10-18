"""Synthetic PostgreSQL collection journal boundaries; no source network."""

import importlib
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, select, text, update

NOW = datetime(2026, 10, 18, 12, tzinfo=UTC)


def api():
    try:
        return importlib.import_module("issuedigest_storage.policy_collection")
    except ModuleNotFoundError:
        pytest.fail("Policy collection journal is not implemented")


def config(**changes):
    return api().PolicyCollectionConfig(
        **dict(
            schema_version=1,
            expected_database="issuedigest_test",
            collection_id=uuid4(),
            news_ids=("123456789", "123456788"),
            minimum_interval_seconds=60,
            max_age_seconds=120,
            max_attempts=3,
        )
        | changes
    )


def tables():
    module = importlib.import_module("issuedigest_storage.policy_collection_schema")
    return module.policy_collection_channels, module.policy_collection_attempts


def test_config_normalizes_and_revalidates_forged_inputs(engine):
    a = api()
    cfg = config()
    assert cfg.news_ids == ("123456788", "123456789")
    with pytest.raises(ValidationError):
        cfg.max_attempts = 5
    repo = a.PolicyCollectionRepository(engine)
    for updates in (
        {"max_attempts": True},
        {"news_ids": ("１２３４５６７８９",)},
        {"news_ids": ("123456789", "123456789")},
        {"minimum_interval_seconds": 59},
        {"max_age_seconds": 59},
        {"collection_id": uuid4().hex},
        {"expected_database": "other"},
    ):
        with pytest.raises(a.PolicyCollectionError):
            with repo.lease(cfg.model_copy(update=updates)):
                pass
    assert repo.status(cfg, now=NOW).attempt_count == 0


def test_success_failure_and_baseline_are_separate_and_immutable(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        first = session.start(now=NOW)
        assert first.outcome == "started" and first.attempt.sequence == 1
        assert session.baseline() is None
        session.succeed(first.attempt.attempt_id, b"capture", b"report", finished_at=NOW)
        with pytest.raises(a.PolicyCollectionError):
            session.fail(first.attempt.attempt_id, "capture_failed", finished_at=NOW)
    with repo.lease(cfg) as session:
        assert session.start(now=NOW + timedelta(seconds=59)).outcome == "not_due"
        baseline = session.baseline()
        assert baseline.capture_bytes == b"capture" and baseline.report_bytes == b"report"
        assert baseline.capture_sha256 == sha256(b"capture").hexdigest()
        second = session.start(now=NOW + timedelta(seconds=60))
        session.fail(
            second.attempt.attempt_id, "capture_failed", finished_at=NOW + timedelta(seconds=61)
        )
    state = repo.status(cfg, now=NOW + timedelta(seconds=121))
    assert state.attempt_count == 2 and state.latest.state == "failed"
    assert state.last_success.state == "succeeded" and state.last_success.sequence == 1
    assert state.age_seconds == 121 and state.stale is True
    assert "capture_bytes" not in state.model_dump_json()


def test_interrupted_is_marked_before_not_due_or_limit_and_success_survives(engine):
    a, cfg = api(), config(max_attempts=2)
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        first = session.start(now=NOW)
        session.succeed(first.attempt.attempt_id, b"old", b"report", finished_at=NOW)
    with repo.lease(cfg) as session:
        session.start(now=NOW + timedelta(seconds=60))
    with repo.lease(cfg) as session:
        assert session.start(now=NOW + timedelta(seconds=61)).outcome == "not_due"
    state = repo.status(cfg, now=NOW + timedelta(seconds=61))
    assert state.latest.failure_code == "interrupted"
    assert state.last_success.sequence == 1
    with repo.lease(cfg) as session:
        assert session.start(now=NOW + timedelta(seconds=120)).outcome == "attempt_limit"


def test_busy_lock_and_ownership_loss_cannot_write(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        with repo.lease(cfg) as other:
            assert other is None
        # Same dedicated backend but lock was released outside the repository.
        session._connection.execute(text("SELECT pg_advisory_unlock(104704, 2)"))
        session._connection.commit()
        with pytest.raises(a.PolicyCollectionError):
            session.start(now=NOW)
    assert repo.status(cfg, now=NOW).attempt_count == 0
    with repo.lease(cfg) as session:
        assert session is not None


def test_config_binding_corruption_and_exact_baseline_hash(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
        session.succeed(attempt.attempt_id, b"original", b"report", finished_at=NOW)
    with pytest.raises(a.PolicyCollectionError):
        repo.status(cfg.model_copy(update={"max_attempts": 4}), now=NOW)
    channels, attempts = tables()
    with engine.begin() as conn:
        conn.execute(update(attempts).values(capture_bytes=b"modified"))
    with repo.lease(cfg) as session:
        with pytest.raises(a.PolicyCollectionError):
            session.baseline()
    with engine.begin() as conn:
        conn.execute(update(channels).values(config_sha256="0" * 64))
    with pytest.raises(a.PolicyCollectionError):
        repo.status(cfg, now=NOW)


def test_status_uses_read_only_snapshot_without_writes_or_private_bytes(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    statements = []

    def observe(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
        if "FROM policy_collection" in statement:
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar() == "on"
            assert conn.exec_driver_sql("SHOW transaction_isolation").scalar() == "repeatable read"

    event.listen(engine, "before_cursor_execute", observe)
    try:
        state = repo.status(cfg, now=NOW)
        assert state.latest is None and state.last_success is None and state.stale is True
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert not any(
        s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE", "CREATE")) for s in statements
    )
    assert not any("capture_bytes" in s or "report_bytes" in s for s in statements)
    channels, _ = tables()
    with engine.connect() as conn:
        assert conn.execute(select(channels)).all() == []


def test_terminal_validation_bounds_time_and_ambiguous_commit(engine, monkeypatch):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
        for capture, report, when in (
            (bytearray(b"x"), b"r", NOW),
            (b"", b"r", NOW),
            (b"x" * (8 * 1024 * 1024 + 16385), b"r", NOW),
            (b"x", b"r" * 65537, NOW),
            (b"x", b"r", NOW - timedelta(seconds=1)),
            (b"x", b"r", NOW.replace(tzinfo=None)),
        ):
            with pytest.raises(a.PolicyCollectionError):
                session.succeed(attempt.attempt_id, capture, report, finished_at=when)
        with pytest.raises(a.PolicyCollectionError):
            session.fail(attempt.attempt_id, "secret error", finished_at=NOW)
        original = session._connection.commit

        def uncertain():
            original()
            raise __import__("sqlalchemy").exc.OperationalError("private", {}, Exception("private"))

        monkeypatch.setattr(session._connection, "commit", uncertain)
        with pytest.raises(
            a.PolicyCollectionCommitUnknown, match="^Policy collection commit unknown$"
        ):
            session.succeed(attempt.attempt_id, b"x", b"r", finished_at=NOW)
        monkeypatch.setattr(session._connection, "commit", original)
        with pytest.raises(a.PolicyCollectionError):
            session.fail(attempt.attempt_id, "validation_failed", finished_at=NOW)
    assert repo.status(cfg, now=NOW).latest.state == "succeeded"


def test_reversed_clock_does_not_interrupt_or_write(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        session.start(now=NOW)
    with repo.lease(cfg) as session:
        with pytest.raises(a.PolicyCollectionError):
            session.start(now=NOW - timedelta(seconds=1))
    assert repo.status(cfg, now=NOW).latest.state == "running"


def test_forged_config_rejection_does_not_emit_private_warnings(engine, recwarn):
    a, cfg = api(), config()
    forged = cfg.model_copy(update={"collection_id": "private-invalid-id"})
    with pytest.raises(a.PolicyCollectionError):
        with a.PolicyCollectionRepository(engine).lease(forged):
            pass
    assert list(recwarn) == []


def test_baseline_rejects_nonmonotonic_stored_history(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        first = session.start(now=NOW).attempt
        session.succeed(first.attempt_id, b"valid", b"r", finished_at=NOW)
    _, attempts = tables()
    with engine.begin() as conn:
        conn.execute(update(attempts).values(sequence=2))
    with repo.lease(cfg) as session:
        with pytest.raises(a.PolicyCollectionError):
            session.baseline()


def test_invalidated_lease_does_not_reconnect_and_cleanup_failure_is_fixed(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        session._connection.invalidate()
        with pytest.raises(a.PolicyCollectionError):
            session.start(now=NOW)

    def fail_unlock(conn, cursor, statement, parameters, context, many):
        if "pg_advisory_unlock" in statement:
            raise RuntimeError("private cleanup failure")

    event.listen(engine, "before_cursor_execute", fail_unlock)
    try:
        with pytest.raises(a.PolicyCollectionError):
            with repo.lease(cfg) as session:
                pass
    finally:
        event.remove(engine, "before_cursor_execute", fail_unlock)
    with repo.lease(cfg) as session:
        assert session is not None


def test_invalid_failure_types_are_fixed_errors(engine):
    a, cfg = api(), config()
    with a.PolicyCollectionRepository(engine).lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
        for code in ([], {}, True, None):
            with pytest.raises(a.PolicyCollectionError):
                session.fail(attempt.attempt_id, code, finished_at=NOW)


def test_different_backend_and_terminated_connection_cannot_complete(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
        original = session._connection
        with engine.connect() as other:
            session._connection = other
            try:
                with pytest.raises(a.PolicyCollectionError):
                    session.succeed(attempt.attempt_id, b"x", b"r", finished_at=NOW)
            finally:
                session._connection = original
    assert repo.status(cfg, now=NOW).latest.state == "running"
    with repo.lease(cfg) as session:
        attempt = session.start(now=NOW + timedelta(seconds=60)).attempt
        with engine.begin() as observer:
            assert observer.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": session._pid})
        with pytest.raises(a.PolicyCollectionError):
            session.succeed(attempt.attempt_id, b"x", b"r", finished_at=NOW + timedelta(seconds=60))
    state = repo.status(cfg, now=NOW + timedelta(seconds=60))
    assert state.latest.state == "running" and state.attempt_count == 2


@pytest.mark.parametrize(
    "changes",
    [
        {"sequence": 0},
        {"sequence": 4097},
        {"state": "unknown"},
        {"finished_at": NOW},
        {"failure_code": "interrupted"},
        {"capture_bytes": b"private"},
    ],
)
def test_migration_rejects_invalid_attempt_shapes(engine, changes):
    from sqlalchemy.exc import IntegrityError

    a, cfg = api(), config()
    with a.PolicyCollectionRepository(engine).lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
    _, attempts = tables()
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                update(attempts)
                .where(attempts.c.attempt_id == attempt.attempt_id)
                .values(**changes)
            )


def test_uuid4_is_enforced_by_schema(engine):
    from uuid import UUID

    from sqlalchemy.exc import IntegrityError

    a, cfg = api(), config()
    with a.PolicyCollectionRepository(engine).lease(cfg) as session:
        session.start(now=NOW)
    _, attempts = tables()
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(
                update(attempts).values(attempt_id=UUID("00000000-0000-1000-8000-000000000000"))
            )


def test_stored_configuration_json_type_corruption_is_rejected(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        session.start(now=NOW)
    channels, _ = tables()
    # Python's True == 1 must not bypass the stored JSON hash/type boundary.
    altered = cfg.model_dump(mode="json")
    altered["schema_version"] = True
    with engine.begin() as conn:
        conn.execute(update(channels).values(config=altered))
    with pytest.raises(a.PolicyCollectionError):
        repo.status(cfg, now=NOW)


def test_lease_exit_detects_silent_lock_loss(engine):
    a, cfg = api(), config()
    with pytest.raises(a.PolicyCollectionError):
        with a.PolicyCollectionRepository(engine).lease(cfg) as session:
            session._connection.execute(text("SELECT pg_advisory_unlock(104704, 2)"))
            session._connection.commit()


def test_collection_poll_and_migration_preserve_existing_private_and_public_rows(
    engine, database_url
):
    from alembic import command
    from issuedigest_domain import EvidenceBundle
    from issuedigest_domain.public_briefings import PublicBriefingPlan, plan_hash
    from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
    from issuedigest_storage.public_briefings import PublicBriefingRepository

    from conftest import bundle_data, migration_config, public_plan_data

    bundle = EvidenceBundle.model_validate(bundle_data())
    EvidenceRepository(engine).save(uuid4(), bundle)
    actor = uuid4()
    IdentityRepository(engine).register_identity(actor, "synthetic", str(actor))
    SessionRepository(engine).issue_session(actor)
    plan = PublicBriefingPlan.model_validate(public_plan_data())
    PublicBriefingRepository(engine).publish(plan, reviewed_sha256=plan_hash(plan))
    names = (
        "source_documents",
        "document_versions",
        "parsed_representations",
        "citations",
        "evidence_snapshots",
        "snapshot_citations",
        "auth_users",
        "auth_sessions",
        "public_briefings",
        "public_briefing_heads",
    )

    def originals():
        with engine.connect() as conn:
            return {
                name: conn.execute(text(f"SELECT * FROM {name}")).mappings().all() for name in names
            }

    before = originals()
    migration = migration_config(database_url)
    command.downgrade(migration, "0007_public_briefings")
    command.upgrade(migration, "head")
    command.upgrade(migration, "head")
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine)
    with repo.lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
        session.succeed(attempt.attempt_id, b"raw", b"report", finished_at=NOW)
    repo.status(cfg, now=NOW)
    assert originals() == before


def test_extreme_timezone_overflow_is_a_fixed_error(engine):
    from datetime import timezone

    a, cfg = api(), config()
    with a.PolicyCollectionRepository(engine).lease(cfg) as session:
        invalid = datetime.min.replace(tzinfo=timezone(timedelta(hours=1)))
        with pytest.raises(a.PolicyCollectionError):
            session.start(now=invalid)


def test_autocommit_engine_cannot_persist_terminal_when_precommit_guard_fails(engine):
    a, cfg = api(), config()
    repo = a.PolicyCollectionRepository(engine.execution_options(isolation_level="AUTOCOMMIT"))
    with repo.lease(cfg) as session:
        attempt = session.start(now=NOW).attempt
        terminal_written = False

        def after(conn, cursor, statement, parameters, context, many):
            nonlocal terminal_written
            if statement.startswith("UPDATE policy_collection_attempts"):
                terminal_written = True

        def before(conn, cursor, statement, parameters, context, many):
            if terminal_written and statement == "SELECT current_database()":
                raise RuntimeError("private precommit failure")

        event.listen(engine, "after_cursor_execute", after)
        event.listen(engine, "before_cursor_execute", before)
        try:
            with pytest.raises(a.PolicyCollectionError):
                session.succeed(attempt.attempt_id, b"x", b"r", finished_at=NOW)
        finally:
            event.remove(engine, "after_cursor_execute", after)
            event.remove(engine, "before_cursor_execute", before)
    assert a.PolicyCollectionRepository(engine).status(cfg, now=NOW).latest.state == "running"
