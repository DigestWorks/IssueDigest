"""Scoped v5 profiles preserve durable identities and guarded schema boundaries."""

from decimal import Decimal
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository, validate_evidence_profile
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchConflict
from sqlalchemy import inspect, text
from test_evidence_jobs import completion_receipt, seed

from conftest import migration_config

V5 = "guarded-question-evidence-v5"
REVISION = "0014_question_scoped_profile"
TABLES = ("question_source_plans", "evidence_jobs")


@pytest.fixture(autouse=True)
def clean_jobs(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs, briefing_jobs"))
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs, briefing_jobs"))


def revision(database_url):
    return ScriptDirectory.from_config(migration_config(database_url)).get_revision(REVISION).module


def test_v5_plan_frozen_and_job_replay_identity(engine):
    token, workspace, snapshot = seed(engine)
    plans = QuestionPlanRepository(engine, evidence_profile=V5)
    request = uuid4()
    plan = plans.submit(token, workspace, request, "?!")
    assert QuestionPlanRepository(engine).submit(token, workspace, request, "?!") == plan
    assert plans.get_evidence_profile(token, workspace, plan.plan_id) == V5
    jobs = EvidenceJobRepository(engine)
    request = uuid4()
    args = (token, workspace, request, snapshot, "질문")
    kwargs = dict(model="gpt-6.1-sol", reservation_usd=Decimal(".10"), profile=V5)
    job = jobs.submit(*args, **kwargs)
    assert jobs.submit(*args, **kwargs) == job
    assert jobs.prepare(job.job_id)[0].profile == V5
    with pytest.raises(ResearchConflict):
        jobs.submit(*args, **dict(kwargs, profile="guarded-question-evidence-v3"))
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT reservation_count FROM research_budget_months")).scalar() == 1
        )


@pytest.mark.parametrize("wrong", [None, "profile", "input_format", "instructions_sha256"])
def test_v5_receipt_exact_identity(engine, wrong):
    token, workspace, snapshot = seed(engine)
    jobs = EvidenceJobRepository(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "질문",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".10"),
        profile=V5,
    )
    receipt = completion_receipt(jobs, job)
    receipt.update(profile=V5, input_format="question-evidence-source-v5")
    jobs.claim(
        job.job_id,
        prompt_sha256=receipt["prompt_sha256"],
        instructions_sha256=receipt["instructions_sha256"],
    )
    if wrong:
        receipt[wrong] = "wrong"
        with pytest.raises(StorageCorruption):
            jobs.finish(
                job.job_id,
                receipt=receipt,
                known_usage=receipt["usage"],
                usage_complete=True,
                stream_closed=True,
            )
    else:
        done = jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        )
        assert done.profile == V5
        assert jobs.get(token, workspace, job.job_id) == done


def test_v4_remains_rejected(engine):
    with pytest.raises(ValueError):
        validate_evidence_profile("guarded-question-evidence-v4")


@pytest.mark.parametrize("kind", ["plan", "job"])
def test_downgrade_refuses_any_v5_rows_without_deleting(engine, database_url, kind):
    token, workspace, snapshot = seed(engine)
    if kind == "plan":
        QuestionPlanRepository(engine, evidence_profile=V5).submit(token, workspace, uuid4(), "?!")
    else:
        EvidenceJobRepository(engine).submit(
            token,
            workspace,
            uuid4(),
            snapshot,
            "질문",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".10"),
            profile=V5,
        )
    with engine.begin() as conn:
        before = {table: conn.execute(text("SELECT * FROM " + table)).all() for table in TABLES}
        checks = {table: inspect(conn).get_check_constraints(table) for table in TABLES}
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="v5"):
                revision(database_url).downgrade()
        for table in TABLES:
            assert conn.execute(text("SELECT * FROM " + table)).all() == before[table]
            assert inspect(conn).get_check_constraints(table) == checks[table]


@pytest.mark.parametrize(
    "profile", ["guarded-question-evidence-v2", "guarded-question-evidence-v3"]
)
def test_migration_roundtrip_preserves_legacy_rows(engine, database_url, profile):
    token, workspace, snapshot = seed(engine)
    QuestionPlanRepository(engine, evidence_profile=profile).submit(token, workspace, uuid4(), "?!")
    EvidenceJobRepository(engine).submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "질문",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".10"),
        profile=profile,
    )
    with engine.begin() as conn:
        before = {table: conn.execute(text("SELECT * FROM " + table)).all() for table in TABLES}
        with Operations.context(MigrationContext.configure(conn)):
            revision(database_url).downgrade()
            revision(database_url).upgrade()
        for table in TABLES:
            assert conn.execute(text("SELECT * FROM " + table)).all() == before[table]


@pytest.mark.parametrize(
    "table,column,name",
    [
        (
            "question_source_plans",
            "evidence_profile",
            "question_source_plans_evidence_profile_check",
        ),
        ("evidence_jobs", "profile", "evidence_jobs_model_profile_check"),
    ],
)
@pytest.mark.parametrize(
    "change",
    [
        "weak",
        "extra",
        "nullable",
        "default",
        "type",
        "text_type",
        "unknown_name",
        "unvalidated",
        "literal_drift",
    ],
)
def test_upgrade_rejects_schema_drift_before_any_ddl(
    engine, database_url, table, column, name, change
):
    module = revision(database_url)
    with engine.begin() as conn:
        checkpoint = conn.begin_nested()
        with Operations.context(MigrationContext.configure(conn)):
            module.downgrade()
        if change in ("weak", "unknown_name"):
            conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {name}"))
            new_name = name if change == "weak" else "unknown_profile_check"
            conn.execute(
                text(f"ALTER TABLE {table} ADD CONSTRAINT {new_name} CHECK (length({column}) > 0)")
            )
        elif change == "extra":
            conn.execute(
                text(
                    f"ALTER TABLE {table} ADD CONSTRAINT extra_profile_check "
                    f"CHECK (length({column}) > 0)"
                )
            )
        elif change == "nullable":
            conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP NOT NULL"))
        elif change == "default":
            conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT 'custom'"))
        elif change == "literal_drift":
            expression = next(
                c["sqltext"]
                for c in inspect(conn).get_check_constraints(table)
                if c["name"] == name
            )
            conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {name}"))
            expression = expression.replace(
                "guarded-question-evidence-v3", "guarded-question-evidence- v3"
            )
            conn.execute(text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})"))
        elif change == "unvalidated":
            expression = next(
                c["sqltext"]
                for c in inspect(conn).get_check_constraints(table)
                if c["name"] == name
            )
            conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {name}"))
            conn.execute(
                text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression}) NOT VALID")
            )
        else:
            target_type = "text" if change == "text_type" else "varchar(100)"
            conn.execute(text(f"ALTER TABLE {table} ALTER COLUMN {column} TYPE {target_type}"))
        before = {
            t: (str(inspect(conn).get_columns(t)), inspect(conn).get_check_constraints(t))
            for t in TABLES
        }
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="Unexpected"):
                module.upgrade()
        for t in TABLES:
            assert (
                str(inspect(conn).get_columns(t)),
                inspect(conn).get_check_constraints(t),
            ) == before[t]
        checkpoint.rollback()


def test_fresh_base_to_head_and_explicit_0013_upgrade(engine, database_url):
    scripts = ScriptDirectory.from_config(migration_config(database_url))
    with engine.begin() as conn:
        checkpoint = conn.begin_nested()
        schema = "scoped_migration_" + uuid4().hex
        conn.execute(text("CREATE SCHEMA " + schema))
        conn.execute(text("SET LOCAL search_path TO " + schema))
        with Operations.context(MigrationContext.configure(conn)):
            for step in reversed(list(scripts.iterate_revisions(REVISION, "base"))):
                step.module.upgrade()
                if step.revision == "0013_question_evidence_profiles":
                    for table in TABLES:
                        checks = inspect(conn).get_check_constraints(table)
                        assert all(
                            "guarded-question-evidence-v5" not in c["sqltext"] for c in checks
                        )
            for table in TABLES:
                checks = inspect(conn).get_check_constraints(table)
                assert any("guarded-question-evidence-v5" in c["sqltext"] for c in checks)
        checkpoint.rollback()


@pytest.mark.parametrize("operation", ["upgrade", "downgrade"])
@pytest.mark.parametrize("target", ["plan_check", "job_check", "plan_default"])
def test_cast_looking_literals_rejected_without_mutation(engine, database_url, operation, target):
    module = revision(database_url)
    token, workspace, snapshot = seed(engine)
    QuestionPlanRepository(engine).submit(token, workspace, uuid4(), "?!")
    EvidenceJobRepository(engine).submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "질문",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".10"),
    )
    with engine.begin() as conn:
        checkpoint = conn.begin_nested()
        try:
            with Operations.context(MigrationContext.configure(conn)):
                if operation == "upgrade":
                    module.downgrade()
            if target == "plan_default":
                conn.execute(
                    text(
                        "ALTER TABLE question_source_plans ALTER COLUMN evidence_profile "
                        "SET DEFAULT 'guarded-question-evidence-v2::text'::character varying"
                    )
                )
            else:
                table = "question_source_plans" if target == "plan_check" else "evidence_jobs"
                name = (
                    "question_source_plans_evidence_profile_check"
                    if target == "plan_check"
                    else "evidence_jobs_model_profile_check"
                )
                expression = next(
                    c["sqltext"]
                    for c in inspect(conn).get_check_constraints(table)
                    if c["name"] == name
                )
                expression = expression.replace(
                    "guarded-question-evidence-v3", "guarded-question-evidence-v3::text"
                )
                conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT {name}"))
                conn.execute(
                    text(f"ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expression})")
                )
            before = {
                t: (
                    str(inspect(conn).get_columns(t)),
                    inspect(conn).get_check_constraints(t),
                    conn.execute(text("SELECT * FROM " + t)).all(),
                )
                for t in TABLES
            }
            with Operations.context(MigrationContext.configure(conn)):
                with pytest.raises(RuntimeError, match="Unexpected"):
                    getattr(module, operation)()
            for t in TABLES:
                assert (
                    str(inspect(conn).get_columns(t)),
                    inspect(conn).get_check_constraints(t),
                    conn.execute(text("SELECT * FROM " + t)).all(),
                ) == before[t]
        finally:
            checkpoint.rollback()


def test_normalization_preserves_cast_text_and_escaped_quotes(database_url):
    normalize = revision(database_url)._normalized
    assert normalize("('a''::text ( b)'::text)") == "'a''::text ( b)'"
    assert normalize("'guarded-question-evidence-v2::text'::character varying") == (
        "'guarded-question-evidence-v2::text'"
    )
