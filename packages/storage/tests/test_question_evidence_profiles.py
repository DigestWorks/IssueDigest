"""Private version selection remains frozen across server configuration changes."""

from decimal import Decimal
from uuid import uuid4

import pytest
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository, question_source_plans
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchConflict
from sqlalchemy import update
from test_evidence_jobs import seed

V2 = "guarded-question-evidence-v2"
V3 = "guarded-question-evidence-v3"


@pytest.fixture(autouse=True)
def clean_profile_rows(engine):
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs, briefing_jobs"))
    yield
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs, briefing_jobs"))


@pytest.fixture
def revision_0013(engine, database_url):
    """Historic 0013 contracts target their revision, independently of moving head."""
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory

    from conftest import migration_config

    current = (
        ScriptDirectory.from_config(migration_config(database_url))
        .get_revision("0014_question_scoped_profile")
        .module
    )
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            current.downgrade()
    try:
        yield
    finally:
        with engine.begin() as conn:
            with Operations.context(MigrationContext.configure(conn)):
                current.upgrade()


def test_plan_profile_frozen_and_private(engine):
    token, workspace, _ = seed(engine)
    request = uuid4()
    repo = QuestionPlanRepository(engine, evidence_profile=V3)
    plan = repo.submit(token, workspace, request, "?!")
    assert "evidence_profile" not in plan.model_dump()
    assert repo.get_evidence_profile(token, workspace, plan.plan_id) == V3
    old = QuestionPlanRepository(engine)
    assert old.submit(token, workspace, request, "?!") == plan
    assert old.get_evidence_profile(token, workspace, plan.plan_id) == V3
    from issuedigest_storage.sessions import AuthenticationDenied

    with pytest.raises(AuthenticationDenied):
        old.get_evidence_profile("a" * 42 + "A", workspace, plan.plan_id)
    with engine.begin() as conn:
        conn.execute(
            update(question_source_plans)
            .where(question_source_plans.c.plan_id == plan.plan_id)
            .values(evidence_profile=V2)
        )
    with pytest.raises(StorageCorruption):
        old.get(token, workspace, plan.plan_id)


@pytest.mark.parametrize("profile", ["unknown", 3, None])
def test_unknown_plan_profile_rejected(engine, profile):
    with pytest.raises(ValueError):
        QuestionPlanRepository(engine, evidence_profile=profile)


def test_evidence_profile_identity(engine):
    token, workspace, snapshot = seed(engine)
    repo = EvidenceJobRepository(engine)
    request = uuid4()
    job = repo.submit(
        token,
        workspace,
        request,
        snapshot,
        "질문",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".10"),
        profile=V3,
    )
    assert job.profile == V3
    assert repo.prepare(job.job_id)[0].profile == V3
    assert (
        repo.submit(
            token,
            workspace,
            request,
            snapshot,
            "질문",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".10"),
            profile=V3,
        )
        == job
    )
    with pytest.raises(ResearchConflict):
        repo.submit(
            token,
            workspace,
            request,
            snapshot,
            "질문",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".10"),
            profile=V2,
        )


@pytest.mark.parametrize("wrong", ["profile", "input_format", None])
def test_v3_finish_exact_labels(engine, wrong):
    from test_evidence_jobs import completion_receipt

    token, workspace, snapshot = seed(engine)
    repo = EvidenceJobRepository(engine)
    job = repo.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "질문",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".10"),
        profile=V3,
    )
    receipt = completion_receipt(repo, job)
    receipt.update(profile=V3, input_format="question-evidence-source-v3")
    repo.claim(
        job.job_id,
        prompt_sha256=receipt["prompt_sha256"],
        instructions_sha256=receipt["instructions_sha256"],
    )
    if wrong:
        receipt[wrong] = V2 if wrong == "profile" else "question-evidence-source-v2"
        with pytest.raises(StorageCorruption):
            repo.finish(
                job.job_id,
                receipt=receipt,
                known_usage=receipt["usage"],
                usage_complete=True,
                stream_closed=True,
            )
    else:
        assert (
            repo.finish(
                job.job_id,
                receipt=receipt,
                known_usage=receipt["usage"],
                usage_complete=True,
                stream_closed=True,
            ).profile
            == V3
        )


def test_migration_preserves_v2_refuses_v3_and_reupgrades(engine, database_url, revision_0013):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import text

    from conftest import migration_config

    rev = ScriptDirectory.from_config(migration_config(database_url)).get_revision(
        "0013_question_evidence_profiles"
    )
    token, workspace, _ = seed(engine)
    repo = QuestionPlanRepository(engine)
    plan = repo.submit(token, workspace, uuid4(), "?!")
    with engine.begin() as conn:
        before = conn.execute(text("SELECT payload, input_sha256 FROM question_source_plans")).all()
        with Operations.context(MigrationContext.configure(conn)):
            rev.module.downgrade()
            rev.module.upgrade()
            rev.module.upgrade()
        assert (
            conn.execute(text("SELECT payload, input_sha256 FROM question_source_plans")).all()
            == before
        )
    assert repo.get_evidence_profile(token, workspace, plan.plan_id) == V2
    QuestionPlanRepository(engine, evidence_profile=V3).submit(token, workspace, uuid4(), "?!")
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="v3"):
                rev.module.downgrade()


@pytest.mark.parametrize(
    "expression", ["profile <> 'custom'", "model <> 'other' OR profile <> 'custom'"]
)
@pytest.mark.parametrize("replace_known", [False, True])
def test_migration_refuses_unrecognized_profile_constraint(
    engine, database_url, expression, replace_known, revision_0013
):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text

    from conftest import migration_config

    rev = ScriptDirectory.from_config(migration_config(database_url)).get_revision(
        "0013_question_evidence_profiles"
    )
    with engine.begin() as conn:
        checkpoint = conn.begin_nested()
        if replace_known:
            conn.execute(
                text("ALTER TABLE evidence_jobs DROP CONSTRAINT evidence_jobs_model_profile_check")
            )
        conn.execute(
            text(
                "ALTER TABLE evidence_jobs ADD CONSTRAINT custom_profile_check CHECK ("
                + expression
                + ")"
            )
        )
        before = inspect(conn).get_check_constraints("evidence_jobs")
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="Unexpected evidence profile"):
                rev.module.upgrade()
        assert inspect(conn).get_check_constraints("evidence_jobs") == before
        checkpoint.rollback()


def test_briefing_rejects_mixed_children(engine):
    from issuedigest_storage.briefing_jobs import BriefingJobRepository
    from issuedigest_storage.evidence_jobs import digest, evidence_jobs
    from sqlalchemy import select
    from test_briefing_jobs import packet

    token, workspace, plan, children = packet(engine, count=2)
    with engine.begin() as conn:
        row = (
            conn.execute(select(evidence_jobs).where(evidence_jobs.c.job_id == children[1]))
            .mappings()
            .one()
        )
        receipt = dict(row["receipt"], profile=V3, input_format="question-evidence-source-v3")
        identity = dict(
            snapshot_id=str(row["snapshot_id"]),
            source_sha256=row["source_sha256"],
            question=row["question"],
            model=row["model"],
            reservation_usd=str(row["reservation_usd"]),
            profile=V3,
        )
        conn.execute(
            update(evidence_jobs)
            .where(evidence_jobs.c.job_id == children[1])
            .values(
                profile=V3,
                input_sha256=digest(identity),
                receipt=receipt,
                receipt_sha256=digest(receipt),
            )
        )
    with pytest.raises(ResearchConflict, match="child"):
        BriefingJobRepository(engine).inputs(token, workspace, plan, children)


@pytest.mark.parametrize("operation", ["upgrade", "downgrade"])
@pytest.mark.parametrize("change", ["unknown", "ambiguous", "nullable", "default"])
def test_migration_plan_schema_rejection_is_non_destructive(
    engine, database_url, operation, change, revision_0013
):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect, text

    from conftest import migration_config

    rev = ScriptDirectory.from_config(migration_config(database_url)).get_revision(
        "0013_question_evidence_profiles"
    )
    token, workspace, _ = seed(engine)
    QuestionPlanRepository(engine).submit(token, workspace, uuid4(), "?!")
    with engine.begin() as conn:
        checkpoint = conn.begin_nested()
        if change == "unknown":
            conn.execute(
                text(
                    "ALTER TABLE question_source_plans DROP CONSTRAINT "
                    "question_source_plans_evidence_profile_check"
                )
            )
            conn.execute(
                text(
                    "ALTER TABLE question_source_plans ADD CONSTRAINT "
                    "question_source_plans_evidence_profile_check "
                    "CHECK (length(evidence_profile)>0)"
                )
            )
        elif change == "ambiguous":
            conn.execute(
                text(
                    "ALTER TABLE question_source_plans ADD CONSTRAINT custom_plan_profile_check "
                    "CHECK (length(evidence_profile)>0)"
                )
            )
        elif change == "nullable":
            conn.execute(
                text(
                    "ALTER TABLE question_source_plans ALTER COLUMN evidence_profile DROP NOT NULL"
                )
            )
        else:
            conn.execute(
                text(
                    "ALTER TABLE question_source_plans ALTER COLUMN evidence_profile "
                    "SET DEFAULT 'custom'"
                )
            )
        before = {
            table: (
                inspect(conn).get_columns(table),
                inspect(conn).get_check_constraints(table),
                conn.execute(text("SELECT * FROM " + table)).all(),
            )
            for table in ("question_source_plans", "evidence_jobs")
        }
        with Operations.context(MigrationContext.configure(conn)):
            with pytest.raises(RuntimeError, match="Unexpected question plan"):
                getattr(rev.module, operation)()
        for table, (_, constraints, rows) in before.items():
            assert inspect(conn).get_check_constraints(table) == constraints
            assert conn.execute(text("SELECT * FROM " + table)).all() == rows
        assert [str(c) for c in inspect(conn).get_columns("question_source_plans")] == [
            str(c) for c in before["question_source_plans"][0]
        ]
        checkpoint.rollback()
