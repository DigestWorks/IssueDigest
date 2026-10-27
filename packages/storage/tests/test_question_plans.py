"""Synthetic PostgreSQL selection durability, authorization and corruption guards."""

import importlib
from uuid import uuid4

import pytest
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from sqlalchemy import select, text, update
from test_evidence_jobs import seed
from test_research_retrieval import save


def api():
    name = "issuedigest_storage.question_plans"
    assert importlib.util.find_spec(name), "Missing question selection repository"
    return importlib.import_module(name)


@pytest.fixture
def plans(engine):
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans"))
    yield api().QuestionPlanRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans"))


def test_repository_exists():
    assert api().QuestionPlanRepository


def test_index_selection_is_ordered_fixed_and_has_no_paid_side_effects(plans, engine, monkeypatch):
    token, workspace, snapshot = seed(engine)
    repo = EvidenceRepository(engine)
    repo.rebuild_projection(workspace, snapshot)
    other = save(engine, workspace, "앞 앞 앞")
    with engine.connect() as conn:
        unchanged = {
            table: conn.execute(text("SELECT * FROM " + table)).all()
            for table in ("evidence_jobs", "research_runs", "research_budget_months")
        }
    request = uuid4()
    plan = plans.submit(token, workspace, request, " 앞 ")
    assert plan.question == " 앞 " and plan.status == "selected"
    assert tuple(s.snapshot_id for s in plan.sources) == tuple(sorted((snapshot, other), key=str))
    save(engine, workspace, "앞")

    def forbidden(*args):
        pytest.fail("saved plan searched again")

    monkeypatch.setattr(api().research_retrieval, "retrieve_snapshot_ids", forbidden)
    assert plans.submit(token, workspace, request, " 앞 ") == plan
    assert plans.get(token, workspace, plan.plan_id) == plan
    with pytest.raises(api().ResearchConflict):
        plans.submit(token, workspace, request, "앞")
    with engine.connect() as conn:
        for table, rows in unchanged.items():
            assert conn.execute(text("SELECT * FROM " + table)).all() == rows
        assert conn.scalar(text("SELECT count(*) FROM question_source_plans")) == 1


@pytest.mark.parametrize("question,reason", [("?!", "no_terms"), ("희귀주제", "no_candidates")])
def test_no_match_is_durable_after_new_corpus(plans, engine, monkeypatch, question, reason):
    token, workspace, _ = seed(engine)
    request = uuid4()
    if reason == "no_terms":
        monkeypatch.setattr(
            api().research_retrieval,
            "retrieve_snapshot_ids",
            lambda *args: pytest.fail("empty terms searched"),
        )
    plan = plans.submit(token, workspace, request, question)
    assert plan.status == "no_match" and plan.reason == reason and plan.sources == ()
    save(engine, workspace, "희귀주제")
    assert plans.submit(token, workspace, request, question) == plan
    if reason == "no_candidates":
        assert plans.submit(token, workspace, uuid4(), question).status == "selected"


@pytest.mark.parametrize(
    "column,value",
    [
        ("question", "changed"),
        ("actor_id", uuid4()),
        ("input_sha256", "f" * 64),
        ("payload_sha256", "f" * 64),
        ("request_id", uuid4()),
    ],
)
def test_row_tampering_rejects(plans, engine, column, value):
    token, workspace, _ = seed(engine)
    plan = plans.submit(token, workspace, uuid4(), "?!")
    with engine.begin() as conn:
        conn.execute(update(api().question_source_plans).values(**{column: value}))
    with pytest.raises(api().StorageCorruption):
        plans.get(token, workspace, plan.plan_id)


@pytest.mark.parametrize("change", ["extra", "missing", "bool", "profile", "state", "source", "id"])
def test_rehashed_invalid_payload_rejects(plans, engine, change):
    token, workspace, _ = seed(engine)
    plan = plans.submit(token, workspace, uuid4(), "?!")
    payload = plan.model_dump(mode="json")
    if change == "extra":
        payload["receipt"] = {}
    elif change == "missing":
        del payload["reason"]
    elif change == "bool":
        payload["question"] = True
    elif change == "profile":
        payload["profile"] = "changed"
    elif change == "state":
        payload["status"] = "selected"
    elif change == "source":
        payload["sources"] = [dict(snapshot_id=str(uuid4()), source_sha256="a" * 64)]
    else:
        payload["plan_id"] = str(uuid4())
    with engine.begin() as conn:
        actor = conn.scalar(select(api().question_source_plans.c.actor_id))
        conn.execute(
            update(api().question_source_plans).values(
                payload=payload,
                payload_sha256=api().digest(dict(actor_id=str(actor), payload=payload)),
            )
        )
    with pytest.raises(api().StorageCorruption):
        plans.get(token, workspace, plan.plan_id)


def test_current_reader_writer_and_workspace_rules(plans, engine):
    from issuedigest_storage.auth_schema import auth_workspace_memberships
    from issuedigest_storage.sessions import AuthenticationDenied

    token, workspace, _ = seed(engine)
    plan = plans.submit(token, workspace, uuid4(), "?!")
    viewer = uuid4()
    identity = IdentityRepository(engine)
    identity.register_identity(viewer, "synthetic", str(viewer))
    identity.set_membership(viewer, workspace, "viewer")
    vt = SessionRepository(engine).issue_session(viewer).token
    assert plans.get(vt, workspace, plan.plan_id) == plan
    assert plans.get(vt, uuid4(), plan.plan_id) is None
    with pytest.raises(api().ResearchForbidden):
        plans.submit(vt, workspace, uuid4(), "q")
    with pytest.raises(AuthenticationDenied):
        plans.get("invalid", workspace, plan.plan_id)
    with engine.begin() as conn:
        conn.execute(
            update(auth_workspace_memberships)
            .where(auth_workspace_memberships.c.user_id != viewer)
            .values(role="viewer")
        )
    with pytest.raises(api().ResearchForbidden):
        plans.get(vt, workspace, plan.plan_id)


@pytest.mark.parametrize("damage", ["title", "bundle", "delete"])
def test_original_source_revalidated_on_get_and_retry(plans, engine, damage):
    from issuedigest_storage.research import ResearchRepository

    token, workspace, snapshot = seed(engine)
    EvidenceRepository(engine).rebuild_projection(workspace, snapshot)
    request = uuid4()
    plan = plans.submit(token, workspace, request, "앞")
    with engine.begin() as conn:
        if damage == "title":
            bundle = EvidenceRepository._load(conn, workspace, snapshot)
            presentation = ResearchRepository._presentation(conn, workspace, snapshot, bundle)
            ResearchRepository._upsert_presentation(
                conn, presentation.model_copy(update={"title": "changed"})
            )
        elif damage == "bundle":
            conn.execute(
                text(
                    "UPDATE parsed_representations SET "
                    "payload=jsonb_set(payload,'{text}', '\"changed\"')"
                )
            )
        else:
            for table in (
                "evidence_search_units",
                "evidence_search_projections",
                "source_presentations",
            ):
                conn.execute(
                    text("DELETE FROM " + table + " WHERE snapshot_id=:s"), {"s": snapshot}
                )
            conn.execute(
                text("DELETE FROM snapshot_citations WHERE snapshot_id=:s"), {"s": snapshot}
            )
            conn.execute(text("DELETE FROM outbox WHERE snapshot_id=:s"), {"s": snapshot})
            conn.execute(
                text("DELETE FROM evidence_snapshots WHERE snapshot_id=:s"), {"s": snapshot}
            )
    for call in (
        lambda: plans.get(token, workspace, plan.plan_id),
        lambda: plans.submit(token, workspace, request, "앞"),
    ):
        with pytest.raises((api().StorageCorruption, api().ResearchConflict)):
            call()


@pytest.mark.parametrize(
    "result",
    [(True,), (str(uuid4()),), (uuid4(),) * 2, tuple(uuid4() for _ in range(6)), [uuid4()]],
)
def test_malformed_retrieval_fails_closed(plans, engine, monkeypatch, result):
    token, workspace, _ = seed(engine)
    monkeypatch.setattr(api().research_retrieval, "retrieve_snapshot_ids", lambda *args: result)
    with pytest.raises(api().StorageCorruption):
        plans.submit(token, workspace, uuid4(), "topic")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM question_source_plans")) == 0


def test_migration_and_import_leave_old_rows_and_registry_untouched(plans, engine, database_url):
    from decimal import Decimal

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from issuedigest_storage.schema import metadata as old_metadata
    from sqlalchemy import inspect

    from conftest import migration_config

    token, workspace, snapshot = seed(engine)
    job = EvidenceJobRepository(engine).submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    plans.submit(token, workspace, uuid4(), "?!")
    old_registry = set(old_metadata.tables)
    assert "question_source_plans" not in old_registry
    importlib.reload(api())
    assert set(old_metadata.tables) == old_registry
    config = migration_config(database_url)
    revision = ScriptDirectory.from_config(config).get_revision("0011_question_source_plans")
    with engine.begin() as conn:
        # Historical table recreation must not leak its baseline CHECKs into moving head.
        checkpoint = conn.begin_nested()
        try:
            old = {
                table: conn.execute(text("SELECT * FROM " + table)).all()
                for table in ("evidence_jobs", "research_budget_months", "evidence_snapshots")
            }
            before = set(inspect(conn).get_table_names())
            version = conn.execute(text("SELECT version_num FROM alembic_version")).all()
            with Operations.context(MigrationContext.configure(conn)):
                revision.module.downgrade()
                try:
                    assert set(inspect(conn).get_table_names()) == before - {
                        "question_source_plans"
                    }
                    for table, rows in old.items():
                        assert conn.execute(text("SELECT * FROM " + table)).all() == rows
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
    assert EvidenceJobRepository(engine).get(token, workspace, job.job_id).status == "pending"
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM evidence_jobs WHERE job_id=:j"), {"j": job.job_id})


@pytest.mark.parametrize("operation", ["submit", "get"])
def test_shared_job_gate_precedes_auth_and_serializes_duplicate_submission(
    plans, engine, operation
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, get_ident
    from time import monotonic

    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from sqlalchemy import event

    token, workspace, _ = seed(engine)
    request = uuid4()
    existing = plans.submit(token, workspace, request, "?!") if operation == "get" else None
    held, release, started = Event(), Event(), Event()
    ids = {}

    def before(conn, cursor, statement, parameters, context, executemany):
        thread = get_ident()
        if thread == ids.get("second"):
            ids.setdefault("second_pid", conn.connection.driver_connection.info.backend_pid)
            started.set()
        if thread in (ids.get("first"), ids.get("second")):
            first_statement = ids.setdefault((thread, "first_sql"), statement)
            assert "pg_advisory_xact_lock" in first_statement

    def after(conn, cursor, statement, parameters, context, executemany):
        if (
            get_ident() == ids.get("first")
            and "auth_workspace_memberships" in statement
            and not held.is_set()
        ):
            ids["first_pid"] = conn.connection.driver_connection.info.backend_pid
            held.set()
            assert release.wait(10)

    def first():
        ids["first"] = get_ident()
        return (
            plans.get(token, workspace, existing.plan_id)
            if existing
            else plans.submit(token, workspace, request, "?!")
        )

    def second():
        ids["second"] = get_ident()
        if existing:

            def check(conn):
                EvidenceJobRepository._lock_jobs(conn)
                return plans._base._actor(conn, token, workspace)

            return plans._base._transaction(check)
        return plans.submit(token, workspace, request, "?!")

    event.listen(engine, "before_cursor_execute", before)
    event.listen(engine, "after_cursor_execute", after)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            one = pool.submit(first)
            try:
                assert held.wait(5)
                two = pool.submit(second)
                assert started.wait(5)
                with engine.connect() as observer:
                    deadline = monotonic() + 5
                    while ids["first_pid"] not in observer.scalar(
                        text("SELECT pg_blocking_pids(:p)"), {"p": ids["second_pid"]}
                    ):
                        assert monotonic() < deadline
                        Event().wait(0.01)
                release.set()
                result, duplicate = one.result(10), two.result(10)
                assert result is not None and duplicate is not None
                if not existing:
                    assert result == duplicate
            finally:
                release.set()
    finally:
        event.remove(engine, "before_cursor_execute", before)
        event.remove(engine, "after_cursor_execute", after)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM question_source_plans")) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", True),
        ("request_id", "not-a-uuid"),
        ("question", True),
        ("question", " "),
        ("question", "x" * 1501),
    ],
)
def test_invalid_inputs_fail_before_sql(plans, engine, field, value):
    from sqlalchemy import event

    data = dict(token="invalid", workspace_id=uuid4(), request_id=uuid4(), question="q")
    data[field] = value

    def forbidden(*args):
        pytest.fail("invalid input issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            plans.submit(**data)
        with pytest.raises(ValueError):
            plans.get("invalid", uuid4(), True)
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


def test_different_actors_are_separate_but_current_members_can_read(plans, engine):
    token, workspace, _ = seed(engine)
    actor = uuid4()
    identity = IdentityRepository(engine)
    identity.register_identity(actor, "synthetic", str(actor))
    identity.set_membership(actor, workspace, "editor")
    second_token = SessionRepository(engine).issue_session(actor).token
    request = uuid4()
    one = plans.submit(token, workspace, request, "?!")
    two = plans.submit(second_token, workspace, request, "?!")
    assert one.plan_id != two.plan_id
    assert plans.get(second_token, workspace, one.plan_id) == one
    assert plans.get(token, workspace, two.plan_id) == two
    assert plans.get(token, workspace, uuid4()) is None


@pytest.mark.parametrize(
    "damage",
    ["duplicate", "oversized", "source_bool", "source_extra", "source_hash", "reason_bool"],
)
def test_rehashed_selected_shapes_and_hashes_are_checked(plans, engine, damage):
    token, workspace, snapshot = seed(engine)
    EvidenceRepository(engine).rebuild_projection(workspace, snapshot)
    plan = plans.submit(token, workspace, uuid4(), "앞")
    raw = plan.model_dump(mode="json")
    if damage == "duplicate":
        raw["sources"] *= 2
    elif damage == "oversized":
        raw["sources"] = [dict(snapshot_id=str(uuid4()), source_sha256="a" * 64) for _ in range(6)]
    elif damage == "source_bool":
        raw["sources"][0]["snapshot_id"] = True
    elif damage == "source_extra":
        raw["sources"][0]["quote"] = "forbidden"
    elif damage == "source_hash":
        raw["sources"][0]["source_sha256"] = "f" * 64
    else:
        raw["reason"] = False
    with engine.begin() as conn:
        actor = conn.scalar(select(api().question_source_plans.c.actor_id))
        conn.execute(
            update(api().question_source_plans).values(
                payload=raw, payload_sha256=api().digest(dict(actor_id=str(actor), payload=raw))
            )
        )
    with pytest.raises(api().StorageCorruption):
        plans.get(token, workspace, plan.plan_id)


@pytest.mark.parametrize(
    "change", ["revoke_session", "expire_session", "idle_session", "disable_user", "remove_member"]
)
def test_current_session_and_membership_are_required(plans, engine, change):
    from issuedigest_storage.sessions import AuthenticationDenied

    token, workspace, _ = seed(engine)
    request = uuid4()
    plan = plans.submit(token, workspace, request, "?!")
    with engine.begin() as conn:
        statement = {
            "revoke_session": "UPDATE auth_sessions SET revoked=true",
            "expire_session": (
                "UPDATE auth_sessions SET issued_at=clock_timestamp()-interval '3 days', "
                "last_activity_at=clock_timestamp()-interval '2 days', "
                "expires_at=clock_timestamp()-interval '1 day'"
            ),
            "idle_session": (
                "UPDATE auth_sessions SET issued_at=clock_timestamp()-interval '9 days', "
                "expires_at=clock_timestamp()+interval '4 days', "
                "last_activity_at=clock_timestamp()-interval '8 days'"
            ),
            "disable_user": "UPDATE auth_users SET enabled=false",
            "remove_member": "UPDATE auth_workspace_memberships SET active=false",
        }[change]
        conn.execute(text(statement))
    for call in (
        lambda: plans.get(token, workspace, plan.plan_id),
        lambda: plans.submit(token, workspace, request, "?!"),
    ):
        if "session" in change:
            with pytest.raises(AuthenticationDenied):
                call()
        else:
            assert call() is None


def test_saved_originals_do_not_follow_new_index_or_other_workspace(plans, engine):
    token, workspace, snapshot = seed(engine)
    EvidenceRepository(engine).rebuild_projection(workspace, snapshot)
    alien = save(engine, uuid4(), "앞")
    request = uuid4()
    plan = plans.submit(token, workspace, request, "앞")
    assert tuple(s.snapshot_id for s in plan.sources) == (snapshot,)
    assert alien not in tuple(s.snapshot_id for s in plan.sources)
    newer = save(engine, workspace, "앞")
    assert plans.submit(token, workspace, request, "앞") == plan
    assert set(s.snapshot_id for s in plans.submit(token, workspace, uuid4(), "앞").sources) == {
        snapshot,
        newer,
    }


def test_real_index_caps_selection_at_five_in_stable_order(plans, engine):
    token, workspace, _ = seed(engine)
    ids = tuple(save(engine, workspace, "공통주제") for _ in range(7))
    plan = plans.submit(token, workspace, uuid4(), "공통주제")
    assert tuple(source.snapshot_id for source in plan.sources) == tuple(sorted(ids, key=str)[:5])


def test_shallow_model_copy_cannot_smuggle_unknown_fields(plans, engine):
    token, workspace, _ = seed(engine)
    plan = plans.submit(token, workspace, uuid4(), "?!")
    copied = plan.model_copy(update={"question": False})
    raw = copied.model_dump(mode="json", warnings=False)
    with engine.begin() as conn:
        actor = conn.scalar(select(api().question_source_plans.c.actor_id))
        conn.execute(
            update(api().question_source_plans).values(
                payload=raw, payload_sha256=api().digest(dict(actor_id=str(actor), payload=raw))
            )
        )
    with pytest.raises(api().StorageCorruption):
        plans.submit(token, workspace, plan.request_id, "?!")


def test_same_actor_request_in_two_workspaces_is_separate(plans, engine):
    token, workspace, _ = seed(engine)
    from issuedigest_storage.auth_schema import auth_sessions
    from issuedigest_storage.sessions import token_digest

    with engine.connect() as conn:
        actor = conn.scalar(
            select(auth_sessions.c.user_id).where(
                auth_sessions.c.token_sha256 == token_digest(token)
            )
        )
    other = uuid4()
    IdentityRepository(engine).set_membership(actor, other, "owner")
    request = uuid4()
    first = plans.submit(token, workspace, request, "?!")
    second = plans.submit(token, other, request, "?!")
    assert first.plan_id != second.plan_id
    assert plans.get(token, other, first.plan_id) is None
    assert plans.get(token, workspace, second.plan_id) is None
