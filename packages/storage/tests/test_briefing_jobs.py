"""Isolated final briefing storage contracts on dedicated synthetic PostgreSQL."""

import importlib
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository
from issuedigest_storage.research import ResearchForbidden
from sqlalchemy import text

from conftest import bundle_data


def api():
    name = "issuedigest_storage.briefing_jobs"
    assert importlib.util.find_spec(name) is not None, "Missing final briefing repository"
    return importlib.import_module(name)


def test_repository_exists():
    assert api().BriefingJobRepository


@pytest.fixture
def jobs(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs, question_source_plans, evidence_jobs"))
    yield api().BriefingJobRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs, question_source_plans, evidence_jobs"))


def packet(engine, count=1):
    data = bundle_data()
    bundle = EvidenceBundle.model_validate(data)
    sid, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(sid, bundle)
    EvidenceRepository(engine).rebuild_projection(bundle.document.workspace_id, sid)
    for _ in range(count - 1):
        extra = uuid4()
        EvidenceRepository(engine).save(extra, bundle)
        EvidenceRepository(engine).rebuild_projection(bundle.document.workspace_id, extra)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    workspace = bundle.document.workspace_id
    plan = QuestionPlanRepository(engine).submit(token, workspace, uuid4(), "앞")
    assert plan is not None and len(plan.sources) == count
    children = EvidenceJobRepository(engine)
    child_ids = []
    for choice in plan.sources:
        child = children.submit(
            token,
            workspace,
            uuid4(),
            choice.snapshot_id,
            plan.question,
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
        assert child is not None
        children.claim(child.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
        usage = dict(input_tokens=10, output_tokens=5, requests=1)
        receipt = dict(
            profile="guarded-question-evidence-v2",
            status="unreviewed",
            transport_profile="guarded-responses-tool-v1",
            input_format="question-evidence-source-v2",
            prompt_sha256="a" * 64,
            instructions_sha256="b" * 64,
            usage=usage,
            evidence=dict(
                source_sha256=child.source_sha256,
                question_sha256=sha256(plan.question.encode()).hexdigest(),
            ),
        )
        children.finish(
            child.job_id,
            receipt=receipt,
            known_usage=usage,
            usage_complete=True,
            stream_closed=True,
        )
        child_ids.append(child.job_id)
    return token, workspace, plan.plan_id, tuple(child_ids)


def admit(jobs, p, request=None, **changes):
    inputs = jobs.inputs(*p)
    options = dict(
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
        expected_inputs_sha256=inputs.inputs_sha256,
        prompt_sha256="c" * 64,
        instructions_sha256="d" * 64,
    )
    options.update(changes)
    return jobs.submit(p[0], p[1], request or uuid4(), p[2], p[3], **options)


def final_receipt(jobs, job):
    _, inputs = jobs.prepare(job.job_id)
    return dict(
        profile="question-briefing-generation-v1",
        model="gpt-6.1-sol",
        status="unreviewed",
        prompt_sha256=job.prompt_sha256,
        instructions_sha256=job.instructions_sha256,
        usage=dict(input_tokens=20, output_tokens=5, requests=1),
        briefing=dict(
            workspace_id=str(job.workspace_id),
            sources=[
                dict(snapshot_id=str(s[0]), source_sha256=c.source_sha256, receipt=c.receipt)
                for s, c in zip(inputs.sources, inputs.children, strict=True)
            ],
        ),
    )


def claim(jobs, job):
    return jobs.claim(
        job.job_id,
        expected_inputs_sha256=job.inputs_sha256,
        prompt_sha256=job.prompt_sha256,
        instructions_sha256=job.instructions_sha256,
    )


def test_admission_idempotency_shared_budget_and_claim(jobs, engine):
    p = packet(engine)
    request = uuid4()
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: admit(jobs, p, request), range(2)))
    assert results[0] == results[1]
    job = results[0]
    assert jobs.get(p[0], p[1], job.job_id) == job
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT reserved_usd,reservation_count FROM research_budget_months")
        ).one() == (Decimal(".50"), 2)
    with pytest.raises(api().ResearchConflict):
        admit(jobs, p, request, reservation_usd=Decimal(".26"))
    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(lambda _: claim(jobs, job), range(2))) == [False, True]
    assert jobs.recover(job.job_id).status == "indeterminate"
    assert not claim(jobs, job)


def test_completion_immutable_and_late_observations(jobs, engine):
    p = packet(engine)
    job = admit(jobs, p)
    assert claim(jobs, job)
    receipt = final_receipt(jobs, job)
    got = jobs.finish(
        job.job_id,
        receipt=receipt,
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    assert got.status == "completed" and got.receipt == receipt
    assert jobs.finish(job.job_id) == got
    assert jobs.cancel(p[0], p[1], job.job_id) == got
    job2 = admit(jobs, p)
    assert claim(jobs, job2)
    jobs.cancel(p[0], p[1], job2.job_id)
    late = jobs.finish(
        job2.job_id,
        receipt=final_receipt(jobs, job2),
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    assert (
        late.status == "cancelled" and late.receipt is None and late.known_usage == receipt["usage"]
    )


def test_cross_active_exclusion_and_old_replay(jobs, engine):
    p = packet(engine)
    children = EvidenceJobRepository(engine)
    _, inputs = jobs.prepare(admit(jobs, p).job_id)
    old = inputs.children[0]
    with pytest.raises(api().ResearchConflict):
        children.submit(
            p[0],
            p[1],
            uuid4(),
            old.snapshot_id,
            old.question,
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
    with engine.connect() as conn:
        old_request = conn.scalar(
            text("SELECT request_id FROM evidence_jobs WHERE job_id=:id"), {"id": old.job_id}
        )
    assert (
        children.submit(
            p[0],
            p[1],
            old_request,
            old.snapshot_id,
            old.question,
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".25"),
        )
        == old
    )
    with engine.begin() as conn:
        conn.execute(text("UPDATE briefing_jobs SET status='cancelled'"))
    active = children.submit(
        p[0],
        p[1],
        uuid4(),
        old.snapshot_id,
        old.question,
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    assert active.status == "pending"
    with pytest.raises(api().ResearchConflict):
        admit(jobs, p)


@pytest.mark.parametrize("change", ["receipt", "usage", "flags", "question", "source"])
def test_current_children_tamper_rejected(jobs, engine, change):
    p = packet(engine)
    job = admit(jobs, p)
    sql = {
        "receipt": "receipt='{}'::jsonb",
        "usage": "known_usage='{}'::jsonb",
        "flags": "usage_complete=false",
        "question": "question='changed'",
        "source": "source_sha256='changed'",
    }[change]
    with engine.begin() as conn:
        conn.execute(text("UPDATE evidence_jobs SET " + sql))
    with pytest.raises((api().StorageCorruption, api().ResearchConflict)):
        jobs.prepare(job.job_id)


def test_migration_only_owned_table(jobs, engine, database_url):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from sqlalchemy import inspect

    from conftest import migration_config

    rev = ScriptDirectory.from_config(migration_config(database_url)).get_revision(
        "0012_briefing_jobs"
    )
    with engine.begin() as conn:
        before = set(inspect(conn).get_table_names())
        stamp = conn.execute(text("SELECT version_num FROM alembic_version")).all()
        with Operations.context(MigrationContext.configure(conn)):
            rev.module.downgrade()
            try:
                assert set(inspect(conn).get_table_names()) == before - {"briefing_jobs"}
                assert conn.execute(text("SELECT version_num FROM alembic_version")).all() == stamp
            finally:
                rev.module.upgrade()
        assert set(inspect(conn).get_table_names()) == before


@pytest.mark.parametrize(
    "value",
    [
        1,
        1.0,
        True,
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("0"),
        Decimal("10.01"),
        Decimal(".001"),
    ],
)
def test_bad_reservation_before_sql(jobs, engine, value):
    from sqlalchemy import event

    def forbidden(*args):
        pytest.fail("invalid reservation issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            jobs.submit(
                "invalid",
                uuid4(),
                uuid4(),
                uuid4(),
                (uuid4(),),
                model="gpt-6.1-sol",
                reservation_usd=value,
                expected_inputs_sha256="a" * 64,
                prompt_sha256="b" * 64,
                instructions_sha256="c" * 64,
            )
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


@pytest.mark.parametrize("value", [True, 1, "", "A" * 64, "a" * 63, "a" * 64 + "\n"])
def test_bad_hash_before_sql(jobs, engine, value):
    from sqlalchemy import event

    def forbidden(*args):
        pytest.fail("invalid hash issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            jobs.submit(
                "invalid",
                uuid4(),
                uuid4(),
                uuid4(),
                (uuid4(),),
                model="gpt-6.1-sol",
                reservation_usd=Decimal(".25"),
                expected_inputs_sha256=value,
                prompt_sha256="b" * 64,
                instructions_sha256="c" * 64,
            )
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


@pytest.mark.parametrize("children", [(), [], (uuid4(),) * 2, (str(uuid4()),), (uuid4(),) * 6])
def test_invalid_children_before_sql(jobs, engine, children):
    from sqlalchemy import event

    def forbidden(*args):
        pytest.fail("invalid child identity issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            jobs.inputs("invalid", uuid4(), uuid4(), children)
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


@pytest.mark.parametrize(
    "field", ["expected_inputs_sha256", "prompt_sha256", "instructions_sha256"]
)
def test_changed_request_identity_no_budget_mutation(jobs, engine, field):
    p = packet(engine)
    request = uuid4()
    admit(jobs, p, request)
    with pytest.raises(api().ResearchConflict):
        admit(jobs, p, request, **{field: "e" * 64})
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT reserved_usd,reservation_count FROM research_budget_months")
        ).one() == (Decimal(".50"), 2)


@pytest.mark.parametrize("cap", ["money", "count"])
def test_shared_budget_limit_no_job(jobs, engine, cap):
    p = packet(engine)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE research_budget_months SET reserved_usd=:money,reservation_count=:count"),
            {
                "money": Decimal("9.90") if cap == "money" else Decimal(".25"),
                "count": 1 if cap == "money" else 40,
            },
        )
    with pytest.raises(api().ResearchBudgetExceeded):
        admit(jobs, p)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0


def member(engine, workspace, role):
    identity = IdentityRepository(engine)
    actor = uuid4()
    identity.register_identity(actor, "synthetic", str(actor))
    identity.set_membership(actor, workspace, role)
    return actor, SessionRepository(engine).issue_session(actor).token


def test_reader_shared_writer_and_original_actor_binding(jobs, engine):
    p = packet(engine)
    job = admit(jobs, p)
    _, viewer = member(engine, p[1], "viewer")
    _, editor = member(engine, p[1], "editor")
    assert jobs.get(viewer, p[1], job.job_id) == job
    with pytest.raises(ResearchForbidden):
        jobs.inputs(viewer, *p[1:])
    with pytest.raises(api().ResearchConflict):
        jobs.inputs(editor, *p[1:])
    assert jobs.cancel(editor, p[1], job.job_id).status == "cancelled"
    assert jobs.get(p[0], uuid4(), job.job_id) is None


@pytest.mark.parametrize("operation", ["prepare", "get", "claim", "completed_cancel"])
def test_original_writer_revocation_blocks_current_reads(jobs, engine, operation):
    p = packet(engine)
    job = admit(jobs, p)
    _, editor = member(engine, p[1], "editor")
    if operation == "completed_cancel":
        assert claim(jobs, job)
        receipt = final_receipt(jobs, job)
        jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        )
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE auth_workspace_memberships SET active=false WHERE user_id=:id"),
            {"id": job.actor_id},
        )
    with pytest.raises(ResearchForbidden):
        if operation == "prepare":
            jobs.prepare(job.job_id)
        elif operation == "get":
            jobs.get(editor, p[1], job.job_id)
        elif operation == "claim":
            claim(jobs, job)
        else:
            jobs.cancel(editor, p[1], job.job_id)


def test_revoked_writer_accounting_survives_and_is_monotone(jobs, engine):
    p = packet(engine)
    job = admit(jobs, p)
    assert claim(jobs, job)
    with engine.begin() as conn:
        conn.execute(text("UPDATE auth_workspace_memberships SET active=false"))
    usage = dict(input_tokens=100, output_tokens=5, requests=1)
    failed = jobs.finish(
        job.job_id, known_usage=usage, usage_complete=True, stream_closed=True, reason="input"
    )
    assert failed.status == "failed" and failed.known_usage == usage and failed.receipt is None
    later = jobs.finish(job.job_id, known_usage=dict(input_tokens=2, output_tokens=10, requests=1))
    assert later.known_usage == dict(input_tokens=100, output_tokens=10, requests=1)
    assert later.usage_complete and later.stream_closed


@pytest.mark.parametrize(
    "field",
    [
        "prompt_sha256",
        "instructions_sha256",
        "profile",
        "model",
        "status",
        "workspace",
        "source",
        "usage",
    ],
)
def test_bad_final_receipt_rolls_back(jobs, engine, field):
    p = packet(engine)
    job = admit(jobs, p)
    assert claim(jobs, job)
    receipt = final_receipt(jobs, job)
    if field == "workspace":
        receipt["briefing"]["workspace_id"] = str(uuid4())
    elif field == "source":
        receipt["briefing"]["sources"][0]["snapshot_id"] = str(uuid4())
    elif field == "usage":
        receipt["usage"] = dict(input_tokens=1, output_tokens=1, requests=1)
    else:
        receipt[field] = "changed"
    with pytest.raises(api().StorageCorruption):
        jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=dict(input_tokens=20, output_tokens=5, requests=1),
            usage_complete=True,
            stream_closed=True,
        )
    assert jobs.prepare(job.job_id)[0].status == "running"
    assert jobs.prepare(job.job_id)[0].known_usage is None


@pytest.mark.parametrize("state", ["pending", "failed", "cancelled", "indeterminate"])
def test_nonrunning_never_completed_by_late_receipt(jobs, engine, state):
    p = packet(engine)
    job = admit(jobs, p)
    receipt = final_receipt(jobs, job)
    if state != "pending":
        assert claim(jobs, job)
        if state == "cancelled":
            jobs.cancel(p[0], p[1], job.job_id)
        elif state == "indeterminate":
            jobs.recover(job.job_id)
        else:
            jobs.finish(job.job_id, reason="output")
    got = jobs.finish(
        job.job_id,
        receipt=receipt,
        known_usage=receipt["usage"],
        usage_complete=True,
        stream_closed=True,
    )
    assert got.status == state and got.receipt is None
    assert got.known_usage == receipt["usage"]


@pytest.mark.parametrize(
    "value",
    [
        {},
        {"input_tokens": True, "output_tokens": 0, "requests": 1},
        {"input_tokens": 0, "output_tokens": 0, "requests": 2},
        {"input_tokens": -1, "output_tokens": 0, "requests": 1},
    ],
)
def test_invalid_usage_before_sql(jobs, engine, value):
    from sqlalchemy import event

    def forbidden(*args):
        pytest.fail("invalid usage issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            jobs.finish(uuid4(), known_usage=value)
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


def test_ordered_children_and_same_own_completed_reuse(jobs, engine):
    p = packet(engine, 2)
    inputs = jobs.inputs(*p)
    assert tuple(c.snapshot_id for c in inputs.children) == tuple(
        s.snapshot_id for s in inputs.plan.sources
    )
    with pytest.raises(api().ResearchConflict):
        jobs.inputs(*p[:3], tuple(reversed(p[3])))
    job = admit(jobs, p)
    assert claim(jobs, job)
    receipt = final_receipt(jobs, job)
    receipt["briefing"]["sources"].reverse()
    with pytest.raises(api().StorageCorruption):
        jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        )
    jobs.cancel(p[0], p[1], job.job_id)
    # A separate own completed analysis of the exact same question/source is allowed.
    old = inputs.children[0]
    repo = EvidenceJobRepository(engine)
    replacement = repo.submit(
        p[0],
        p[1],
        uuid4(),
        old.snapshot_id,
        old.question,
        model=old.model,
        reservation_usd=Decimal(".25"),
    )
    repo.claim(
        replacement.job_id,
        prompt_sha256=old.prompt_sha256,
        instructions_sha256=old.instructions_sha256,
    )
    repo.finish(
        replacement.job_id,
        receipt=old.receipt,
        known_usage=old.known_usage,
        usage_complete=True,
        stream_closed=True,
    )
    reused = jobs.inputs(*p[:3], (replacement.job_id, p[3][1]))
    assert reused.children[0].job_id == replacement.job_id
    assert reused.inputs_sha256 != inputs.inputs_sha256


@pytest.mark.parametrize("change", ["incomplete", "missing", "actor", "workspace", "no_match"])
def test_unavailable_plan_or_child_no_reservation(jobs, engine, change):
    p = packet(engine)
    if change == "no_match":
        plan = QuestionPlanRepository(engine).submit(p[0], p[1], uuid4(), "?!")
        p = (*p[:2], plan.plan_id, p[3])
    else:
        assignment = {
            "incomplete": "status='failed'",
            "actor": "actor_id=:id",
            "workspace": "workspace_id=:id",
        }.get(change)
        with engine.begin() as conn:
            if change == "missing":
                conn.execute(text("DELETE FROM evidence_jobs"))
            else:
                conn.execute(text("UPDATE evidence_jobs SET " + assignment), {"id": uuid4()})
    with pytest.raises(api().ResearchConflict):
        jobs.inputs(*p)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0
        assert conn.scalar(text("SELECT reservation_count FROM research_budget_months")) == 1


@pytest.mark.parametrize("operation", ["inputs", "prepare", "get", "claim"])
def test_current_source_metadata_change_blocks_all(jobs, engine, operation):
    from issuedigest_storage.research import ResearchRepository

    p = packet(engine)
    job = admit(jobs, p)
    _, inputs = jobs.prepare(job.job_id)
    ResearchRepository(engine).upsert_presentation(
        inputs.sources[0][2].model_copy(update={"title": "changed"})
    )
    with pytest.raises(api().StorageCorruption):
        if operation == "inputs":
            jobs.inputs(*p)
        elif operation == "prepare":
            jobs.prepare(job.job_id)
        elif operation == "get":
            jobs.get(p[0], p[1], job.job_id)
        else:
            claim(jobs, job)


def test_old_new_admission_race_one_winner_and_no_double_charge(jobs, engine):
    p = packet(engine)
    child = jobs.inputs(*p).children[0]
    repo = EvidenceJobRepository(engine)

    def new():
        try:
            return admit(jobs, p).status
        except api().ResearchConflict:
            return "blocked"

    def old():
        try:
            return repo.submit(
                p[0],
                p[1],
                uuid4(),
                child.snapshot_id,
                child.question,
                model=child.model,
                reservation_usd=Decimal(".25"),
            ).status
        except api().ResearchConflict:
            return "blocked"

    with ThreadPoolExecutor(2) as pool:
        first, second = pool.submit(new), pool.submit(old)
        assert sorted((first.result(), second.result())) == ["blocked", "pending"]
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT reservation_count FROM research_budget_months")) == 2


def test_shared_budget_final_race_across_workspaces(jobs, engine):
    first, second = packet(engine), packet(engine)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE research_budget_months SET reserved_usd=9.75,reservation_count=39")
        )

    def submit(p):
        try:
            return admit(jobs, p).status
        except api().ResearchBudgetExceeded:
            return "budget"

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(submit, [first, second])) == ["budget", "pending"]
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT reserved_usd,reservation_count FROM research_budget_months")
        ).one() == (Decimal("10"), 40)


def test_plan_and_final_record_hash_tamper(jobs, engine):
    p = packet(engine)
    job = admit(jobs, p)
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE question_source_plans SET payload_sha256=:hash"), {"hash": "f" * 64}
        )
    with pytest.raises(api().StorageCorruption):
        jobs.prepare(job.job_id)


def test_completed_receipt_hash_tamper(jobs, engine):
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
    with engine.begin() as conn:
        conn.execute(text("UPDATE briefing_jobs SET receipt='{}'::jsonb"))
    with pytest.raises(api().StorageCorruption):
        jobs.get(p[0], p[1], job.job_id)


def test_schema_constraints(jobs, engine):
    from sqlalchemy.exc import IntegrityError

    p = packet(engine)
    job = admit(jobs, p)
    for assignment in (
        "model='other'",
        "profile='other'",
        "reservation_usd=0",
        "reservation_usd=10.01",
        "status='other'",
    ):
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text("UPDATE briefing_jobs SET " + assignment))
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO briefing_jobs SELECT :id,workspace_id,actor_id,:request,plan_id,"
                "question,model,profile,inputs_sha256,prompt_sha256,instructions_sha256,status,"
                "child_job_ids,reservation_usd,receipt,receipt_sha256,known_usage,reason,"
                "usage_complete,stream_closed FROM briefing_jobs WHERE job_id=:old"
            ),
            {"id": uuid4(), "request": uuid4(), "old": job.job_id},
        )


def test_corrupt_child_prompt_hash_is_storage_corruption(jobs, engine):
    p = packet(engine)
    job = admit(jobs, p)
    with engine.begin() as conn:
        conn.execute(text("UPDATE evidence_jobs SET prompt_sha256='changed'"))
    with pytest.raises(api().StorageCorruption):
        jobs.prepare(job.job_id)


def test_commit_ack_loss_completed_receipt_wins(jobs, engine, monkeypatch):
    p = packet(engine)
    job = admit(jobs, p)
    assert claim(jobs, job)
    receipt = final_receipt(jobs, job)
    transaction = jobs._base._transaction

    def lost_ack(operation):
        transaction(operation)
        raise OSError("synthetic ack loss")

    monkeypatch.setattr(jobs._base, "_transaction", lost_ack)
    with pytest.raises(OSError):
        jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        )
    monkeypatch.setattr(jobs._base, "_transaction", transaction)
    got = jobs.get(p[0], p[1], job.job_id)
    assert got.status == "completed" and got.receipt == receipt
    assert jobs.finish(job.job_id, reason="output") == got


def test_submit_failure_rolls_back_budget_and_insert(jobs, engine, monkeypatch):
    p = packet(engine)

    def broken(row):
        raise api().StorageCorruption("synthetic post-insert failure")

    monkeypatch.setattr(jobs, "_dto", broken)
    with pytest.raises(api().StorageCorruption):
        admit(jobs, p)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM briefing_jobs")) == 0
        assert conn.scalar(text("SELECT reservation_count FROM research_budget_months")) == 1


def test_equivalent_cent_decimal_retry(jobs, engine):
    p = packet(engine)
    request = uuid4()
    job = admit(jobs, p, request, reservation_usd=Decimal(".2500"))
    assert admit(jobs, p, request, reservation_usd=Decimal(".25")) == job


@pytest.mark.parametrize("value", [None, True, 1, str(uuid4())])
def test_exact_uuid4_before_sql(jobs, engine, value):
    from sqlalchemy import event

    def forbidden(*args):
        pytest.fail("invalid UUID issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            jobs.inputs("invalid", value, uuid4(), (uuid4(),))
        with pytest.raises(ValueError):
            jobs.prepare(value)
        with pytest.raises(ValueError):
            jobs.recover(value)
        with pytest.raises(ValueError):
            jobs.get("invalid", uuid4(), value)
        with pytest.raises(ValueError):
            jobs.cancel("invalid", uuid4(), value)
        with pytest.raises(ValueError):
            jobs.finish(value)
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)
