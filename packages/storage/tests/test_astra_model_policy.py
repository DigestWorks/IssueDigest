"""Astra storage admission and migration contracts, never external provider calls."""

import importlib
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from issuedigest_storage.briefing_jobs import BriefingJobRepository
from issuedigest_storage.evidence_jobs import EvidenceJobRepository, digest
from issuedigest_storage.question_plans import QuestionPlanRepository
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchConflict
from sqlalchemy import event, inspect, text
from test_briefing_jobs import admit, claim, packet
from test_evidence_jobs import seed

from conftest import migration_config

ASTRA = "gpt-6-astra"
SOL = "gpt-6.1-sol"
V5 = "guarded-question-evidence-v5"
REV = "0015_question_astra_models"
TABLES = ("evidence_jobs", "briefing_jobs")


def policy():
    return importlib.import_module("issuedigest_domain.question_model_policy")


@pytest.mark.parametrize(
    "model,profile,allowed",
    [(SOL, "guarded-question-evidence-v" + v, True) for v in ("2", "3", "5")]
    + [
        (ASTRA, V5, True),
        (ASTRA, "guarded-question-evidence-v2", False),
        (ASTRA, "guarded-question-evidence-v3", False),
        (ASTRA, "guarded-question-evidence-v4", False),
        ("other", V5, False),
        (True, V5, False),
    ],
)
def test_exact_model_profile_policy(model, profile, allowed):
    assert policy().evidence_model_allowed(model, profile) is allowed


@pytest.mark.parametrize(
    "model,amount,allowed",
    [
        (SOL, Decimal(".01"), True),
        (ASTRA, Decimal("1"), True),
        (ASTRA, Decimal("10"), True),
        (ASTRA, Decimal(".99"), False),
        (ASTRA, Decimal("NaN"), False),
        (ASTRA, Decimal("1.001"), False),
        (ASTRA, True, False),
        (ASTRA, 1, False),
        ("other", Decimal("1"), False),
    ],
)
def test_reservation_policy(model, amount, allowed):
    assert policy().reservation_allowed(model, amount) is allowed


@pytest.fixture(autouse=True)
def clean(engine):
    with engine.begin() as c:
        c.execute(text("TRUNCATE evidence_jobs,briefing_jobs,question_source_plans"))
    yield
    with engine.begin() as c:
        c.execute(text("TRUNCATE evidence_jobs,briefing_jobs,question_source_plans"))


def revision(database_url):
    return ScriptDirectory.from_config(migration_config(database_url)).get_revision(REV).module


def evidence(engine, model=ASTRA, profile=V5, reservation="1.00"):
    token, workspace, snapshot = seed(engine)
    jobs = EvidenceJobRepository(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "앞",
        model=model,
        profile=profile,
        reservation_usd=Decimal(reservation),
    )
    return jobs, job, (token, workspace, snapshot)


def test_astra_evidence_replay_and_hash_identity(engine):
    jobs, job, p = evidence(engine)
    request = uuid4()
    args = (p[0], p[1], request, p[2], "앞")
    kw = dict(model=ASTRA, profile=V5, reservation_usd=Decimal("1.00"))
    jobs.cancel(p[0], p[1], job.job_id)
    admitted = jobs.submit(*args, **kw)
    assert jobs.submit(*args, **kw) == admitted
    with pytest.raises(ResearchConflict):
        jobs.submit(*args, **dict(kw, model=SOL))
    assert jobs.prepare(admitted.job_id)[0].model == ASTRA
    with engine.connect() as c:
        row = (
            c.execute(
                text("SELECT * FROM evidence_jobs WHERE job_id=:id"), dict(id=admitted.job_id)
            )
            .mappings()
            .one()
        )
        expected = dict(
            snapshot_id=str(p[2]),
            source_sha256=row["source_sha256"],
            question="앞",
            model=ASTRA,
            reservation_usd="1.00",
            profile=V5,
        )
        assert row["input_sha256"] == digest(expected)


@pytest.mark.parametrize(
    "profile,reservation",
    [
        ("guarded-question-evidence-v2", "1.00"),
        ("guarded-question-evidence-v3", "1.00"),
        ("guarded-question-evidence-v4", "1.00"),
        (V5, ".99"),
    ],
)
def test_astra_invalid_evidence_before_budget(engine, profile, reservation):
    with pytest.raises(ValueError):
        evidence(engine, profile=profile, reservation=reservation)
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM evidence_jobs")) == 0
        assert c.scalar(text("SELECT count(*) FROM research_budget_months")) == 0


def native_packet(engine, models=(ASTRA,)):
    # Existing Sol fixture establishes native identity/receipt shape, then cancel and
    # readmit under the v5 plan contract with real repository completion.
    p = packet(engine, count=len(models))
    with engine.begin() as c:
        c.execute(text("DELETE FROM evidence_jobs"))
        c.execute(text("UPDATE question_source_plans SET evidence_profile=:p"), dict(p=V5))
        c.execute(text("DELETE FROM research_budget_months"))
    plans = QuestionPlanRepository(engine, evidence_profile=V5)
    plan = plans.submit(p[0], p[1], uuid4(), "앞")
    jobs = EvidenceJobRepository(engine)
    ids = []
    for choice, model in zip(plan.sources, models, strict=True):
        job = jobs.submit(
            p[0],
            p[1],
            uuid4(),
            choice.snapshot_id,
            "앞",
            model=model,
            profile=V5,
            reservation_usd=Decimal("1.00"),
        )
        jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
        usage = dict(input_tokens=10, output_tokens=5, requests=1)
        receipt = dict(
            profile=V5,
            status="unreviewed",
            transport_profile="guarded-responses-tool-v1",
            input_format="question-evidence-source-v5",
            prompt_sha256="a" * 64,
            instructions_sha256="b" * 64,
            usage=usage,
            evidence=dict(
                source_sha256=job.source_sha256, question_sha256=sha256("앞".encode()).hexdigest()
            ),
        )
        jobs.finish(
            job.job_id, receipt=receipt, known_usage=usage, usage_complete=True, stream_closed=True
        )
        ids.append(job.job_id)
    return p[0], p[1], plan.plan_id, tuple(ids)


def test_astra_final_completion_replay_and_model_binding(engine):
    jobs = BriefingJobRepository(engine)
    p = native_packet(engine)
    req = uuid4()
    job = admit(jobs, p, req, model=ASTRA, reservation_usd=Decimal("1.00"))
    assert admit(jobs, p, req, model=ASTRA, reservation_usd=Decimal("1.00")) == job
    assert claim(jobs, job)
    receipt = dict(
        profile="question-briefing-generation-v1",
        model=ASTRA,
        status="unreviewed",
        prompt_sha256=job.prompt_sha256,
        instructions_sha256=job.instructions_sha256,
        usage=dict(input_tokens=20, output_tokens=5, requests=1),
        briefing=dict(
            workspace_id=str(p[1]),
            sources=[dict(snapshot_id=str(s[0])) for s in jobs.prepare(job.job_id)[1].sources],
        ),
    )
    wrong = dict(receipt, model=SOL)
    with pytest.raises(StorageCorruption):
        jobs.finish(
            job.job_id,
            receipt=wrong,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        )
    done = jobs.finish(
        job.job_id,
        receipt=receipt,
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    assert done.model == ASTRA and done.receipt == receipt
    assert jobs.get(p[0], p[1], job.job_id) == done
    with engine.begin() as c:
        c.execute(
            text("UPDATE briefing_jobs SET receipt=:r,receipt_sha256=:h"),
            dict(r=__import__("json").dumps(wrong), h=digest(wrong)),
        )
    with pytest.raises(StorageCorruption):
        jobs.get(p[0], p[1], job.job_id)


@pytest.mark.parametrize(
    "models,final,reservation",
    [
        ((ASTRA,), ASTRA, ".99"),
        ((ASTRA,), SOL, "1.00"),
        ((SOL,), ASTRA, "1.00"),
        ((ASTRA, SOL), ASTRA, "1.00"),
    ],
)
def test_final_mismatch_or_underfunding_precedes_reservation(engine, models, final, reservation):
    jobs = BriefingJobRepository(engine)
    p = native_packet(engine, models)
    with engine.connect() as c:
        before = c.execute(text("SELECT * FROM research_budget_months")).all()
    with pytest.raises((ValueError, ResearchConflict, StorageCorruption)):
        admit(jobs, p, model=final, reservation_usd=Decimal(reservation))
    with engine.connect() as c:
        assert c.execute(text("SELECT * FROM research_budget_months")).all() == before
        assert c.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0


def test_migration_preserves_sol_rows_and_exact_14_roundtrip(engine, database_url):
    jobs, job, p = evidence(engine, model=SOL, reservation=".25")
    with engine.begin() as c:
        before = c.execute(text("SELECT * FROM evidence_jobs")).all()
        with Operations.context(MigrationContext.configure(c)):
            revision(database_url).downgrade()
            baseline = {t: inspect(c).get_check_constraints(t) for t in TABLES}
            revision(database_url).upgrade()
            assert c.execute(text("SELECT * FROM evidence_jobs")).all() == before
            revision(database_url).downgrade()
            assert {t: inspect(c).get_check_constraints(t) for t in TABLES} == baseline
            revision(database_url).upgrade()
    assert jobs.get(p[0], p[1], job.job_id) == job


@pytest.mark.parametrize("kind", ["evidence", "briefing"])
def test_downgrade_refuses_any_astra_rows(engine, database_url, kind):
    if kind == "evidence":
        evidence(engine)
    else:
        jobs = BriefingJobRepository(engine)
        admit(jobs, native_packet(engine), model=ASTRA, reservation_usd=Decimal("1.00"))
        with engine.begin() as c:
            c.execute(text("UPDATE evidence_jobs SET model='gpt-6.1-sol'"))
    with engine.begin() as c:
        before = {t: c.execute(text("SELECT * FROM " + t)).all() for t in TABLES}
        checks = {t: inspect(c).get_check_constraints(t) for t in TABLES}
        with Operations.context(MigrationContext.configure(c)):
            with pytest.raises(RuntimeError, match="Astra"):
                revision(database_url).downgrade()
        assert {t: c.execute(text("SELECT * FROM " + t)).all() for t in TABLES} == before
        assert {t: inspect(c).get_check_constraints(t) for t in TABLES} == checks


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize(
    "change",
    [
        "model_nullable",
        "model_default",
        "model_type",
        "model_text",
        "profile_nullable",
        "profile_default",
        "profile_text",
        "reservation_nullable",
        "reservation_scale",
        "profile_type",
        "reservation_type",
        "reservation_default",
        "unknown",
        "duplicate",
        "unvalidated",
        "literal",
    ],
)
@pytest.mark.parametrize("operation", ["upgrade", "downgrade"])
def test_migration_rejects_drift_before_any_ddl(engine, database_url, table, change, operation):
    module = revision(database_url)
    with engine.begin() as c:
        checkpoint = c.begin_nested()
        try:
            with Operations.context(MigrationContext.configure(c)):
                if operation == "upgrade":
                    module.downgrade()
            name = (
                "evidence_jobs_model_profile_check"
                if table == "evidence_jobs"
                else "briefing_jobs_check"
            )
            if change.endswith("_nullable"):
                column = change.removesuffix("_nullable")
                if column == "reservation":
                    column = "reservation_usd"
                c.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"))
            elif change in ("model_default", "profile_default"):
                column = change.removesuffix("_default")
                c.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT 'other'"))
            elif change in ("model_type", "model_text", "profile_text"):
                column = change.split("_", 1)[0]
                kind = "text" if change.endswith("_text") else "varchar(100)"
                c.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {kind}"))
            elif change == "reservation_scale":
                c.execute(
                    text(f"ALTER TABLE {table} ALTER COLUMN reservation_usd TYPE numeric(6,3)")
                )
            elif change == "profile_type":
                c.execute(text(f"ALTER TABLE {table} ALTER COLUMN profile TYPE varchar(200)"))
            elif change == "reservation_type":
                c.execute(
                    text(f"ALTER TABLE {table} ALTER COLUMN reservation_usd TYPE numeric(7,2)")
                )
            elif change == "reservation_default":
                c.execute(text(f"ALTER TABLE {table} ALTER COLUMN reservation_usd SET DEFAULT 1"))
            elif change == "duplicate":
                c.execute(
                    text(f"ALTER TABLE {table} ADD CONSTRAINT extra_model CHECK (length(model)>0)")
                )
            else:
                expr = next(
                    x["sqltext"]
                    for x in inspect(c).get_check_constraints(table)
                    if x["name"] == name
                )
                c.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {name}"))
                if change == "unknown":
                    name = "unknown_model"
                if change == "literal":
                    expr = expr.replace("gpt-6.1-sol", "gpt-6.1-sol::text")
                suffix = " NOT VALID" if change == "unvalidated" else ""
                c.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr}){suffix}"))
            before = {
                t: (str(inspect(c).get_columns(t)), inspect(c).get_check_constraints(t))
                for t in TABLES
            }
            mutations = []

            def observe(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith(("ALTER", "CREATE", "DROP")):
                    mutations.append(statement)

            event.listen(c, "before_cursor_execute", observe)
            try:
                with Operations.context(MigrationContext.configure(c)):
                    with pytest.raises(RuntimeError, match="Unexpected"):
                        getattr(module, operation)()
            finally:
                event.remove(c, "before_cursor_execute", observe)
            assert mutations == []
            assert {
                t: (str(inspect(c).get_columns(t)), inspect(c).get_check_constraints(t))
                for t in TABLES
            } == before
        finally:
            checkpoint.rollback()


def test_fresh_base_through_14_to_15(engine, database_url):
    scripts = ScriptDirectory.from_config(migration_config(database_url))
    with engine.begin() as c:
        checkpoint = c.begin_nested()
        try:
            schema = "astra_migration_" + uuid4().hex
            c.execute(text("CREATE SCHEMA " + schema))
            c.execute(text("SET LOCAL search_path TO " + schema))
            with Operations.context(MigrationContext.configure(c)):
                for step in reversed(list(scripts.iterate_revisions(REV, "base"))):
                    step.module.upgrade()
                    if step.revision == "0014_question_scoped_profile":
                        assert all(
                            ASTRA not in x["sqltext"]
                            for t in TABLES
                            for x in inspect(c).get_check_constraints(t)
                        )
                for t in TABLES:
                    assert any(ASTRA in x["sqltext"] for x in inspect(c).get_check_constraints(t))
        finally:
            checkpoint.rollback()


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize(
    "constraint,change",
    [
        ("reservation_usd_check", "weak"),
        ("reservation_usd_check", "unvalidated"),
        ("astra_reservation_check", "weak"),
        ("astra_reservation_check", "unvalidated"),
    ],
)
def test_all_reservation_checks_are_exact_before_ddl(
    engine, database_url, table, constraint, change
):
    module = revision(database_url)
    with engine.begin() as c:
        checkpoint = c.begin_nested()
        try:
            name = table + "_" + constraint
            expression = next(
                x["sqltext"] for x in inspect(c).get_check_constraints(table) if x["name"] == name
            )
            c.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {name}"))
            if change == "weak":
                expression = "reservation_usd >= 0"
            suffix = " NOT VALID" if change == "unvalidated" else ""
            c.execute(
                text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression}){suffix}")
            )
            checks = {t: inspect(c).get_check_constraints(t) for t in TABLES}
            with Operations.context(MigrationContext.configure(c)):
                with pytest.raises(RuntimeError, match="Unexpected"):
                    module.downgrade()
            assert {t: inspect(c).get_check_constraints(t) for t in TABLES} == checks
        finally:
            checkpoint.rollback()


@pytest.mark.parametrize("table", TABLES)
@pytest.mark.parametrize("value", [".99", "0"])
def test_database_itself_rejects_underfunded_astra(engine, table, value):
    from sqlalchemy.exc import IntegrityError

    if table == "evidence_jobs":
        _, job, _ = evidence(engine)
    else:
        jobs = BriefingJobRepository(engine)
        job = admit(jobs, native_packet(engine), model=ASTRA, reservation_usd=Decimal("1.00"))
    with engine.begin() as c:
        checkpoint = c.begin_nested()
        try:
            with pytest.raises(IntegrityError):
                c.execute(
                    text(f"UPDATE {table} SET reservation_usd=:value WHERE job_id=:id"),
                    dict(value=Decimal(value), id=job.job_id),
                )
        finally:
            checkpoint.rollback()


@pytest.mark.parametrize("table", TABLES)
def test_underfunded_astra_corruption_rejected_by_dto_and_current(engine, table):
    if table == "evidence_jobs":
        jobs, job, _ = evidence(engine)
    else:
        jobs = BriefingJobRepository(engine)
        job = admit(jobs, native_packet(engine), model=ASTRA, reservation_usd=Decimal("1.00"))
    with engine.begin() as c:
        checkpoint = c.begin_nested()
        try:
            c.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {table}_astra_reservation_check"))
            c.execute(
                text(f"UPDATE {table} SET reservation_usd=.99 WHERE job_id=:id"),
                dict(id=job.job_id),
            )
            row = (
                c.execute(text(f"SELECT * FROM {table} WHERE job_id=:id"), dict(id=job.job_id))
                .mappings()
                .one()
            )
            with pytest.raises(StorageCorruption):
                jobs._dto(row)
            with pytest.raises(StorageCorruption):
                jobs._current(c, row)
        finally:
            checkpoint.rollback()


def test_sol_native_completion_row_identity_survives_roundtrip(engine, database_url):
    from test_briefing_jobs import final_receipt

    jobs = BriefingJobRepository(engine)
    p = packet(engine)
    job = admit(jobs, p)
    assert claim(jobs, job)
    receipt = final_receipt(jobs, job)
    done = jobs.finish(
        job.job_id,
        receipt=receipt,
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    with engine.begin() as c:
        rows = {t: c.execute(text("SELECT * FROM " + t)).all() for t in TABLES}
        with Operations.context(MigrationContext.configure(c)):
            revision(database_url).downgrade()
            revision(database_url).upgrade()
        assert {t: c.execute(text("SELECT * FROM " + t)).all() for t in TABLES} == rows
    assert jobs.get(p[0], p[1], done.job_id) == done
    assert admit(jobs, p, request=done.request_id) == done


def test_completed_final_finish_rechecks_current_children(engine):
    from test_briefing_jobs import final_receipt

    jobs = BriefingJobRepository(engine)
    p = packet(engine)
    job = admit(jobs, p)
    assert claim(jobs, job)
    receipt = final_receipt(jobs, job)
    jobs.finish(
        job.job_id,
        receipt=receipt,
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    with engine.begin() as c:
        c.execute(text("UPDATE evidence_jobs SET question='changed'"))
    with pytest.raises((ResearchConflict, StorageCorruption)):
        jobs.finish(job.job_id)


@pytest.mark.parametrize(
    "profile", ["guarded-question-evidence-v2", "guarded-question-evidence-v3"]
)
def test_database_rejects_astra_legacy_evidence_profile(engine, profile):
    from sqlalchemy.exc import IntegrityError

    _, job, _ = evidence(engine, model=SOL, profile=profile)
    with engine.begin() as conn:
        checkpoint = conn.begin_nested()
        try:
            with pytest.raises(IntegrityError):
                conn.execute(
                    text("UPDATE evidence_jobs SET model=:model WHERE job_id=:id"),
                    dict(model=ASTRA, id=job.job_id),
                )
        finally:
            checkpoint.rollback()


def test_pending_final_current_read_binds_child_model(engine):
    jobs = BriefingJobRepository(engine)
    p = native_packet(engine)
    job = admit(jobs, p, model=ASTRA, reservation_usd=Decimal("1.00"))
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE briefing_jobs SET model=:model WHERE job_id=:id"),
            dict(model=SOL, id=job.job_id),
        )
    with pytest.raises(StorageCorruption):
        jobs.prepare(job.job_id)


@pytest.mark.parametrize("operation", ["submit", "completed_finish"])
@pytest.mark.parametrize("changed", ["model", "reservation", "both"])
def test_evidence_replay_revalidates_persisted_model_and_reservation_identity(
    engine, operation, changed
):
    jobs, job, p = evidence(engine)
    if operation == "completed_finish":
        assert jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
        usage = dict(input_tokens=10, output_tokens=5, requests=1)
        receipt = dict(
            profile=V5,
            status="unreviewed",
            transport_profile="guarded-responses-tool-v1",
            input_format="question-evidence-source-v5",
            prompt_sha256="a" * 64,
            instructions_sha256="b" * 64,
            usage=usage,
            evidence=dict(
                source_sha256=job.source_sha256,
                question_sha256=sha256("앞".encode()).hexdigest(),
            ),
        )
        jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=usage,
            usage_complete=True,
            stream_closed=True,
        )
    with engine.begin() as conn:
        row = conn.execute(text("SELECT * FROM evidence_jobs")).mappings().one()
        original_hash = row["input_sha256"]
        request_id = row["request_id"]
        model = SOL if changed in ("model", "both") else ASTRA
        amount = Decimal(".25") if changed == "both" else Decimal("2.00")
        if changed == "model":
            amount = Decimal("1.00")
        conn.execute(
            text("UPDATE evidence_jobs SET model=:model,reservation_usd=:amount"),
            dict(model=model, amount=amount),
        )
    with engine.connect() as conn:
        before_job = conn.execute(text("SELECT * FROM evidence_jobs")).all()
        before_budget = conn.execute(text("SELECT * FROM research_budget_months")).all()
        before_sessions = conn.execute(text("SELECT * FROM auth_sessions")).all()
        assert conn.scalar(text("SELECT input_sha256 FROM evidence_jobs")) == original_hash
    writes = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")):
            writes.append(statement)

    event.listen(engine, "before_cursor_execute", observe)
    try:
        with pytest.raises((StorageCorruption, ResearchConflict)):
            if operation == "submit":
                jobs.submit(
                    p[0],
                    p[1],
                    request_id,
                    p[2],
                    "앞",
                    model=ASTRA,
                    profile=V5,
                    reservation_usd=Decimal("1.00"),
                )
            else:
                jobs.finish(
                    job.job_id,
                    known_usage=dict(input_tokens=100, output_tokens=50, requests=1),
                    usage_complete=True,
                    stream_closed=True,
                )
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    # Authentication's existing transactional last-activity touch is rolled back;
    # the rejected replay must never attempt a job/budget/usage mutation.
    assert all(statement.startswith("UPDATE auth_sessions ") for statement in writes)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT * FROM evidence_jobs")).all() == before_job
        assert conn.execute(text("SELECT * FROM research_budget_months")).all() == before_budget
        assert conn.execute(text("SELECT * FROM auth_sessions")).all() == before_sessions
