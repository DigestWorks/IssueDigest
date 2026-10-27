"""Dedicated synthetic durable job integration."""

import importlib
from decimal import Decimal
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from sqlalchemy import text

from conftest import bundle_data


def api():
    name = "issuedigest_storage.evidence_jobs"
    assert importlib.util.find_spec(name) is not None, "Missing durable job repository"
    return importlib.import_module(name)


@pytest.fixture
def jobs(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE evidence_jobs"))
    yield api().EvidenceJobRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE evidence_jobs"))


def seed(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identity = IdentityRepository(engine)
    identity.register_identity(actor, "synthetic", str(actor))
    identity.set_membership(actor, bundle.document.workspace_id, "owner")
    return (
        SessionRepository(engine).issue_session(actor).token,
        bundle.document.workspace_id,
        snapshot,
    )


def test_repository_exists():
    assert api().EvidenceJobRepository


def test_idempotency_claim_recovery_and_budget(jobs, engine):
    token, workspace, snapshot = seed(engine)
    request = uuid4()
    job = jobs.submit(
        token,
        workspace,
        request,
        snapshot,
        " exact ",
        model="gpt-6.1-sol",
        reservation_usd=Decimal("1.00"),
    )
    again = jobs.submit(
        token,
        workspace,
        request,
        snapshot,
        " exact ",
        model="gpt-6.1-sol",
        reservation_usd=Decimal("1.00"),
    )
    assert again.job_id == job.job_id
    with pytest.raises(api().ResearchConflict):
        jobs.submit(
            token,
            workspace,
            request,
            snapshot,
            "changed",
            model="gpt-6.1-sol",
            reservation_usd=Decimal("1.00"),
        )
    assert jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
    assert not jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
    assert jobs.recover(job.job_id).status == "indeterminate"
    assert jobs.get(token, workspace, job.job_id).receipt is None
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT reserved_usd,reservation_count FROM research_budget_months")
        ).one()
        assert row == (Decimal("1.00"), 1)


@pytest.mark.parametrize(
    "reservation", [1, 1.0, True, Decimal("NaN"), Decimal("0"), Decimal("10.01"), Decimal(".001")]
)
def test_exact_reservation(jobs, engine, reservation):
    token, workspace, snapshot = seed(engine)
    with pytest.raises(ValueError):
        jobs.submit(
            token,
            workspace,
            uuid4(),
            snapshot,
            "q",
            model="gpt-6.1-sol",
            reservation_usd=reservation,
        )


def test_source_hash_matches_agents(jobs, engine):
    from issuedigest_agents.question_evidence_propositions import _source

    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    _, source = jobs.prepare(job.job_id)
    assert job.source_sha256 == _source(source)[0]


def test_observations_over_cap_and_unknown_are_not_free(jobs, engine):
    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    assert jobs.recover(job.job_id).known_usage is None
    jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
    huge = dict(input_tokens=2**70, output_tokens=9000, requests=1)
    failed = jobs.finish(
        job.job_id, known_usage=huge, usage_complete=True, stream_closed=True, reason="output"
    )
    assert failed.known_usage == huge and failed.receipt is None and failed.status == "failed"
    assert (
        jobs.finish(
            job.job_id, known_usage=dict(input_tokens=1, output_tokens=1, requests=1)
        ).known_usage
        == huge
    )


def test_budget_combines_old_pool_and_new(jobs, engine):
    token, workspace, snapshot = seed(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO research_budget_months VALUES "
                "(to_char(clock_timestamp(),'YYYY-MM'),9.75,39)"
            )
        )
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    assert job.status == "pending"
    jobs.cancel(token, workspace, job.job_id)
    with pytest.raises(api().ResearchBudgetExceeded):
        jobs.submit(
            token,
            workspace,
            uuid4(),
            snapshot,
            "q",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".01"),
        )


def test_viewer_can_read_current_job(jobs, engine):
    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    viewer = uuid4()
    identity = IdentityRepository(engine)
    identity.register_identity(viewer, "synthetic", str(viewer))
    identity.set_membership(viewer, workspace, "viewer")
    viewer_token = SessionRepository(engine).issue_session(viewer).token
    assert jobs.get(viewer_token, workspace, job.job_id).job_id == job.job_id
    with pytest.raises(api().ResearchForbidden):
        jobs.cancel(viewer_token, workspace, job.job_id)


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_agent_modules():
    import sys

    package = importlib.import_module("issuedigest_agents")
    existing, attributes = set(sys.modules), vars(package).copy()
    yield
    for name in set(sys.modules) - existing:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)
    for name in set(vars(package)) - attributes.keys():
        delattr(package, name)
    for name, value in attributes.items():
        setattr(package, name, value)


def test_atomic_duplicate_claims(jobs, engine):
    from concurrent.futures import ThreadPoolExecutor

    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: jobs.claim(
                    job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64
                ),
                range(2),
            )
        )
    assert sorted(results) == [False, True]


def test_migration_only_new_table_and_old_rows(jobs, engine, database_url):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect

    from conftest import migration_config

    token, workspace, snapshot = seed(engine)
    config = migration_config(database_url)
    revision = ScriptDirectory.from_config(config).get_revision("0010_evidence_jobs")
    with engine.begin() as conn:
        # Historical table recreation must not leak its baseline CHECKs into moving head.
        checkpoint = conn.begin_nested()
        try:
            old = conn.execute(
                text("SELECT snapshot_id,workspace_id FROM evidence_snapshots")
            ).all()
            version = conn.execute(text("SELECT version_num FROM alembic_version")).all()
            before = set(inspect(conn).get_table_names())
            with Operations.context(MigrationContext.configure(conn)):
                revision.module.downgrade()
                try:
                    assert set(inspect(conn).get_table_names()) == before - {"evidence_jobs"}
                    assert (
                        conn.execute(
                            text("SELECT snapshot_id,workspace_id FROM evidence_snapshots")
                        ).all()
                        == old
                    )
                    assert (
                        conn.execute(text("SELECT version_num FROM alembic_version")).all()
                        == version
                    )
                finally:
                    revision.module.upgrade()
            assert set(inspect(conn).get_table_names()) == before
            assert conn.execute(text("SELECT version_num FROM alembic_version")).all() == version
        finally:
            checkpoint.rollback()
        for table in ("question_source_plans", "evidence_jobs"):
            assert any(
                "guarded-question-evidence-v5" in check["sqltext"]
                for check in inspect(conn).get_check_constraints(table)
            )


def test_source_metadata_change_rejects_same_request(jobs, engine):
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchRepository

    token, workspace, snapshot = seed(engine)
    request = uuid4()
    job = jobs.submit(
        token,
        workspace,
        request,
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    _, source = jobs.prepare(job.job_id)
    ResearchRepository(engine).upsert_presentation(
        source[2].model_copy(update={"title": "changed"})
    )
    with pytest.raises(api().ResearchConflict):
        jobs.submit(
            token,
            workspace,
            request,
            snapshot,
            "q",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
    with pytest.raises(StorageCorruption):
        jobs.prepare(job.job_id)


@pytest.mark.parametrize(
    "question,model",
    [
        ("", "gpt-6.1-sol"),
        ("  ", "gpt-6.1-sol"),
        ("q" * 1501, "gpt-6.1-sol"),
        ("q", "gpt-5.4-mini"),
        ("q", True),
    ],
)
def test_exact_question_and_model(jobs, engine, question, model):
    token, workspace, snapshot = seed(engine)
    with pytest.raises(ValueError):
        jobs.submit(
            token,
            workspace,
            uuid4(),
            snapshot,
            question,
            model=model,
            reservation_usd=Decimal(".25"),
        )


def test_invalid_session_other_workspace_and_missing_source(jobs, engine):
    from issuedigest_storage.sessions import AuthenticationDenied

    token, workspace, snapshot = seed(engine)
    with pytest.raises(AuthenticationDenied):
        jobs.submit(
            "invalid",
            workspace,
            uuid4(),
            snapshot,
            "q",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
    assert (
        jobs.submit(
            token,
            uuid4(),
            uuid4(),
            snapshot,
            "q",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
        is None
    )
    with pytest.raises(api().ResearchConflict):
        jobs.submit(
            token,
            workspace,
            uuid4(),
            uuid4(),
            "q",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )


def test_concurrent_shared_budget_last_reservation(jobs, engine):
    from concurrent.futures import ThreadPoolExecutor

    one = seed(engine)
    two = seed(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO research_budget_months VALUES "
                "(to_char(clock_timestamp(),'YYYY-MM'),9.75,39)"
            )
        )

    def submit_one(seed_data):
        token, workspace, snapshot = seed_data
        try:
            return jobs.submit(
                token,
                workspace,
                uuid4(),
                snapshot,
                "q",
                model="gpt-6.1-sol",
                reservation_usd=Decimal(".25"),
            ).status
        except api().ResearchBudgetExceeded:
            return "budget"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit_one, [one, two])) == ["budget", "pending"]


def test_finish_storage_rejects_mismatched_source_identity(jobs, engine):
    from issuedigest_storage.repository import StorageCorruption

    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
    usage = dict(input_tokens=10, output_tokens=5, requests=1)
    fake = dict(
        profile="guarded-question-evidence-v2",
        status="unreviewed",
        prompt_sha256="a" * 64,
        instructions_sha256="b" * 64,
        usage=usage,
        evidence={"source_sha256": "f" * 64},
    )
    with pytest.raises(StorageCorruption):
        jobs.finish(
            job.job_id, receipt=fake, known_usage=usage, usage_complete=True, stream_closed=True
        )
    assert jobs.prepare(job.job_id)[0].status == "running"


def test_actual_old_run_and_new_job_share_pool(jobs, engine):
    from issuedigest_domain.research_journey import ResearchRequest
    from issuedigest_storage.research import ResearchRepository

    token, workspace, snapshot = seed(engine)
    old = ResearchRepository(engine).submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="old")
    )
    assert old is not None
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "new",
        model="gpt-6.1-sol",
        reservation_usd=Decimal("9.75"),
    )
    assert job.status == "pending"
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT reserved_usd,reservation_count FROM research_budget_months")
        ).one() == (Decimal("10"), 2)


@pytest.mark.parametrize("change", ["revoke", "title", "delete"])
def test_completed_cancel_revalidates_original_authority_and_source(jobs, engine, change):
    from issuedigest_storage.auth_schema import auth_workspace_memberships
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchConflict, ResearchForbidden, ResearchRepository
    from sqlalchemy import update

    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    receipt = completion_receipt(jobs, job)
    jobs.claim(
        job.job_id,
        prompt_sha256=receipt["prompt_sha256"],
        instructions_sha256=receipt["instructions_sha256"],
    )
    jobs.finish(
        job.job_id,
        receipt=receipt,
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    editor = uuid4()
    identity = IdentityRepository(engine)
    identity.register_identity(editor, "synthetic", str(editor))
    identity.set_membership(editor, workspace, "editor")
    editor_token = SessionRepository(engine).issue_session(editor).token
    if change == "revoke":
        with engine.begin() as conn:
            conn.execute(
                update(auth_workspace_memberships)
                .where(auth_workspace_memberships.c.user_id != editor)
                .values(active=False)
            )
    elif change == "title":
        _, source = jobs.prepare(job.job_id)
        ResearchRepository(engine).upsert_presentation(
            source[2].model_copy(update={"title": "changed"})
        )
    else:
        with engine.begin() as conn:
            for table in ("snapshot_citations", "outbox"):
                conn.execute(
                    text("DELETE FROM " + table + " WHERE snapshot_id=:sid"), {"sid": snapshot}
                )
            conn.execute(
                text("DELETE FROM evidence_snapshots WHERE snapshot_id=:sid"), {"sid": snapshot}
            )
    with pytest.raises((ResearchForbidden, ResearchConflict, StorageCorruption)):
        jobs.cancel(editor_token, workspace, job.job_id)


def completion_receipt(jobs, job):
    from hashlib import sha256

    from issuedigest_agents.guarded_question_evidence_v2 import (
        GUARDED_QUESTION_V2_INSTRUCTIONS,
        GuardedQuestionEvidenceGenerationV2,
        _preflight,
    )
    from issuedigest_agents.question_evidence_propositions import (
        build_question_evidence_propositions,
    )

    _, source = jobs.prepare(job.job_id)
    prompt, _ = _preflight(source, job.question)
    evidence = build_question_evidence_propositions(
        source,
        job.question,
        dict(
            propositions=[],
            coverage=dict(linked_proposition_ids=[], unresolved_reason="insufficient"),
        ),
    )
    return GuardedQuestionEvidenceGenerationV2(
        profile="guarded-question-evidence-v2",
        transport_profile="guarded-responses-tool-v1",
        input_format="question-evidence-source-v2",
        status="unreviewed",
        evidence=evidence,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        instructions_sha256=sha256(GUARDED_QUESTION_V2_INSTRUCTIONS.encode()).hexdigest(),
        usage=dict(input_tokens=10, output_tokens=5, requests=1),
    ).model_dump(mode="json")


@pytest.mark.parametrize("public_operation", ["get", "cancel"])
@pytest.mark.parametrize("worker_operation", ["claim", "finish"])
def test_authenticated_worker_lock_order_race(jobs, engine, public_operation, worker_operation):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, get_ident
    from time import monotonic

    from sqlalchemy import event

    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    receipt = completion_receipt(jobs, job)
    if worker_operation == "finish":
        assert jobs.claim(
            job.job_id,
            prompt_sha256=receipt["prompt_sha256"],
            instructions_sha256=receipt["instructions_sha256"],
        )
    public_locked, release_public, worker_started = Event(), Event(), Event()
    ids = {}

    def before(conn, cursor, statement, parameters, context, executemany):
        if get_ident() == ids.get("worker_thread"):
            ids.setdefault("worker_pid", conn.connection.driver_connection.info.backend_pid)
            worker_started.set()

    def after(conn, cursor, statement, parameters, context, executemany):
        if (
            get_ident() == ids.get("public_thread")
            and "auth_workspace_memberships" in statement
            and "FOR UPDATE" in statement
            and not public_locked.is_set()
        ):
            ids["public_pid"] = conn.connection.driver_connection.info.backend_pid
            public_locked.set()
            assert release_public.wait(10)

    def public():
        ids["public_thread"] = get_ident()
        return getattr(jobs, public_operation)(token, workspace, job.job_id)

    def worker():
        ids["worker_thread"] = get_ident()
        if worker_operation == "claim":
            return jobs.claim(
                job.job_id,
                prompt_sha256=receipt["prompt_sha256"],
                instructions_sha256=receipt["instructions_sha256"],
            )
        return jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        )

    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(public)
            try:
                assert public_locked.wait(5)
                second = pool.submit(worker)
                assert worker_started.wait(5)
                with engine.connect() as observer:
                    deadline = monotonic() + 5
                    while ids["public_pid"] not in observer.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": ids["worker_pid"]}
                    ):
                        assert monotonic() < deadline, (
                            "worker did not block behind public transaction"
                        )
                        Event().wait(0.01)
                release_public.set()
                assert first.result(timeout=10) is not None
                second.result(timeout=10)
            finally:
                release_public.set()
    finally:
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "after_cursor_execute", after)
    state = jobs.prepare(job.job_id)[0].status
    assert state == (
        "cancelled"
        if public_operation == "cancel"
        else "running"
        if worker_operation == "claim"
        else "completed"
    )


@pytest.mark.parametrize("expected", [True, 1, "", "A" * 64, "a" * 63, "a" * 64 + "\n"])
def test_expected_source_hash_invalid_before_sql(jobs, engine, expected):
    from sqlalchemy import event

    def forbidden(*args):
        pytest.fail("invalid expected hash issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            jobs.submit(
                "invalid",
                uuid4(),
                uuid4(),
                uuid4(),
                "q",
                model="gpt-6.1-sol",
                reservation_usd=Decimal(".25"),
                expected_source_sha256=expected,
            )
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


def test_expected_source_mismatch_precedes_budget_and_retry_lookup(jobs, engine):
    token, workspace, snapshot = seed(engine)
    request = uuid4()
    args = (token, workspace, request, snapshot, "q")
    options = dict(model="gpt-6.1-sol", reservation_usd=Decimal(".25"))
    with pytest.raises(api().ResearchConflict):
        jobs.submit(*args, **options, expected_source_sha256="f" * 64)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM evidence_jobs")) == 0
        assert conn.scalar(text("SELECT count(*) FROM research_budget_months")) == 0
    job = jobs.submit(*args, **options)
    assert jobs.submit(*args, **options, expected_source_sha256=job.source_sha256) == job
    with engine.begin() as conn:
        conn.execute(text("UPDATE research_budget_months SET reserved_usd=10,reservation_count=40"))
    with pytest.raises(api().ResearchConflict):
        jobs.submit(*args, **options, expected_source_sha256="f" * 64)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM evidence_jobs")) == 1
        assert conn.execute(
            text("SELECT reserved_usd,reservation_count FROM research_budget_months")
        ).one() == (Decimal("10"), 40)
