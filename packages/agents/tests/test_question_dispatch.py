"""Sequential plan admission uses synthetic SQL; only external queue I/O is replaced."""

import asyncio
import importlib
import sys
import threading
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import event, text


@pytest.fixture(scope="module", autouse=True)
def isolated_modules():
    paths = sys.path.copy()
    root = Path(__file__).resolve().parents[3]
    for path in ("packages/storage/tests", "packages/agents/tests", "apps/worker/tests"):
        sys.path.insert(0, str(root / path))
    packages = [importlib.import_module(n) for n in ("issuedigest_agents", "issuedigest_worker")]
    before, attrs = set(sys.modules), [vars(p).copy() for p in packages]
    yield
    for name in set(sys.modules) - before:
        if name.startswith(("issuedigest_agents.", "issuedigest_worker.")):
            sys.modules.pop(name, None)
    sys.path[:] = paths
    for package, original in zip(packages, attrs, strict=True):
        for key in set(vars(package)) - original.keys():
            delattr(package, key)
        for key, value in original.items():
            setattr(package, key, value)


@pytest.fixture
def admission(engine):
    from issuedigest_domain import EvidenceBundle
    from issuedigest_storage import EvidenceRepository
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from issuedigest_storage.question_plans import QuestionPlanRepository
    from test_evidence_jobs import seed

    from conftest import bundle_data

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs"))
    token, workspace, snapshot = seed(engine)
    EvidenceRepository(engine).rebuild_projection(workspace, snapshot)
    data = bundle_data()
    data["document"]["workspace_id"] = str(workspace)
    other = uuid4()
    EvidenceRepository(engine).save(other, EvidenceBundle.model_validate(data))
    EvidenceRepository(engine).rebuild_projection(workspace, other)
    yield (
        QuestionPlanRepository(engine),
        EvidenceJobRepository(engine),
        dict(
            token=token,
            workspace_id=workspace,
            request_id=uuid4(),
            question=" 앞 ",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".50"),
        ),
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs"))


class QueueClient:
    def __init__(self, action=None):
        self.calls = []
        self.action = action

    async def enqueue_async(self, options, *args):
        self.calls.append((options, args))
        if self.action:
            self.action()


def module():
    assert importlib.util.find_spec("issuedigest_agents.question_dispatch"), "Missing plan dispatch"
    return importlib.import_module("issuedigest_agents.question_dispatch")


def advance(admission, client, **changes):
    plans, jobs, inputs = admission
    return module().advance_question_plan(
        plans, jobs, client=client, app_version="question-test-v1", **(inputs | changes)
    )


def counts(engine):
    with engine.connect() as conn:
        return (
            conn.scalar(text("SELECT count(*) FROM evidence_jobs")),
            conn.scalar(
                text("SELECT coalesce(sum(reservation_count),0) FROM research_budget_months")
            ),
        )


def complete(jobs, job):
    from test_evidence_jobs import completion_receipt

    receipt = completion_receipt(jobs, job)
    assert jobs.claim(
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


def test_no_match_has_no_jobs_reservations_or_queue(admission, engine):
    client = QueueClient()
    result = asyncio.run(advance(admission, client, question="?!"))
    assert result.status == "no_match" and result.completed_count == result.total_sources == 0
    assert result.dispatches == () and client.calls == [] and counts(engine) == (0, 0)
    assert set(vars(result)) == {
        "plan_id",
        "status",
        "completed_count",
        "total_sources",
        "dispatches",
    }


def test_first_unfinished_stops_retry_reuses_and_complete_prefix_advances(admission, engine):
    plans, jobs, inputs = admission
    client = QueueClient()
    first = asyncio.run(advance(admission, client))
    assert first.status == "in_progress" and first.total_sources == 2 and first.completed_count == 0
    assert len(first.dispatches) == 1 and first.dispatches[0].queued
    assert counts(engine) == (1, 1)
    again = asyncio.run(advance(admission, client))
    assert again == first and counts(engine) == (1, 1)
    job = jobs.get(inputs["token"], inputs["workspace_id"], first.dispatches[0].job_id)
    complete(jobs, job)
    second = asyncio.run(advance(admission, client))
    assert second.completed_count == 1 and len(second.dispatches) == 2
    assert not second.dispatches[0].queued and second.dispatches[1].queued
    assert second.dispatches[0].job_id != second.dispatches[1].job_id
    assert counts(engine) == (2, 2)
    complete(jobs, jobs.get(inputs["token"], inputs["workspace_id"], second.dispatches[1].job_id))
    before = len(client.calls)
    final = asyncio.run(advance(admission, client))
    assert final.status == "evidence_complete" and final.completed_count == 2
    assert all(not ack.queued for ack in final.dispatches)
    assert counts(engine) == (2, 2) and len(client.calls) == before
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT request_id,snapshot_id FROM evidence_jobs ORDER BY snapshot_id")
        ).all()
    assert all(request.version == 4 for request, _ in rows)
    assert len({request for request, _ in rows}) == 2
    assert asyncio.run(advance(admission, client)) == final


@pytest.mark.parametrize("status", ["running", "failed", "cancelled", "indeterminate"])
def test_running_or_blocked_never_admits_later_children(admission, engine, status):
    _, jobs, inputs = admission
    client = QueueClient()
    first = asyncio.run(advance(admission, client))
    job_id = first.dispatches[0].job_id
    if status == "running":
        jobs.claim(job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
    elif status == "cancelled":
        jobs.cancel(inputs["token"], inputs["workspace_id"], job_id)
    else:
        jobs.finish(job_id, reason="unknown" if status == "indeterminate" else "output")
    client.calls.clear()
    result = asyncio.run(advance(admission, client))
    assert result.status == ("in_progress" if status == "running" else "blocked")
    assert result.completed_count == 0 and len(result.dispatches) == 1
    assert result.dispatches[0].status == status and not result.dispatches[0].queued
    assert client.calls == [] and counts(engine) == (1, 1)


@pytest.mark.parametrize(
    "field,value",
    [
        ("workspace_id", True),
        ("request_id", "bad"),
        ("question", False),
        ("question", " "),
        ("question", "x" * 1501),
        ("model", "other"),
        ("model", True),
        ("reservation_usd", 1),
        ("reservation_usd", Decimal("NaN")),
        ("reservation_usd", Decimal(".001")),
        ("reservation_usd", Decimal("0")),
        ("reservation_usd", Decimal("10.01")),
    ],
)
def test_invalid_inputs_before_any_sql_including_no_match(admission, engine, field, value):
    client = QueueClient()

    def forbidden(*args):
        pytest.fail("invalid input issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            asyncio.run(advance(admission, client, **({"question": "?!"} | {field: value})))
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)
    assert client.calls == []


@pytest.mark.parametrize("version", [None, "", "a b", "한", "a" * 129, "v\n"])
def test_bad_version_before_sql(admission, engine, version):
    plans, jobs, inputs = admission

    def forbidden(*args):
        pytest.fail("bad version issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            asyncio.run(
                module().advance_question_plan(
                    plans, jobs, client=QueueClient(), app_version=version, **inputs
                )
            )
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


def test_same_engine_and_exact_repositories_required_before_sql(admission, engine):
    from issuedigest_storage import create_storage_engine
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository

    plans, jobs, inputs = admission
    other = create_storage_engine(engine.url.render_as_string(hide_password=False))

    def forbidden(*args):
        pytest.fail("repository mismatch issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        for p, j in ((plans, EvidenceJobRepository(other)), (object(), jobs), (plans, object())):
            with pytest.raises(ValueError):
                asyncio.run(
                    module().advance_question_plan(
                        p, j, client=QueueClient(), app_version="test", **inputs
                    )
                )
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)
        other.dispose()


@pytest.mark.parametrize(
    "change",
    ["workspace", "request", "question", "source_type", "source_hash", "extra", "nested_extra"],
)
def test_model_copy_tamper_is_reconstructed_strictly(admission, engine, monkeypatch, change):
    from issuedigest_storage.repository import StorageCorruption

    plans, _, inputs = admission
    plan = plans.submit(
        inputs["token"], inputs["workspace_id"], inputs["request_id"], inputs["question"]
    )
    updates = {
        "workspace": {"workspace_id": uuid4()},
        "request": {"request_id": uuid4()},
        "question": {"question": False},
        "source_type": {"sources": list(plan.sources)},
        "source_hash": {"sources": (plan.sources[0].model_copy(update={"source_sha256": True}),)},
        "extra": {"receipt": {}},
        "nested_extra": {"sources": (plan.sources[0].model_copy(update={"receipt": {}}),)},
    }
    monkeypatch.setattr(plans, "submit", lambda *args: plan.model_copy(update=updates[change]))
    client = QueueClient()
    with pytest.raises(StorageCorruption):
        asyncio.run(advance(admission, client))
    assert client.calls == [] and counts(engine) == (0, 0)


@pytest.mark.parametrize("change", ["authority", "title", "source"])
def test_current_plan_access_and_source_guard(admission, engine, change):
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchForbidden

    asyncio.run(advance(admission, QueueClient()))
    with engine.begin() as conn:
        sql = {
            "authority": "UPDATE auth_workspace_memberships SET role='viewer'",
            "title": (
                "UPDATE source_presentations SET payload=jsonb_set(payload,'{title}','\"changed\"')"
            ),
            "source": (
                "UPDATE parsed_representations SET "
                "payload=jsonb_set(payload,'{text}','\"changed\"')"
            ),
        }[change]
        conn.execute(text(sql))
    client = QueueClient()
    with pytest.raises((StorageCorruption, ResearchForbidden)):
        asyncio.run(advance(admission, client))
    assert client.calls == [] and counts(engine) == (1, 1)


@pytest.mark.parametrize("completed_prefix", [False, True])
def test_source_race_after_plan_before_admission_rolls_back(
    admission, engine, monkeypatch, completed_prefix
):
    from issuedigest_storage import EvidenceRepository
    from issuedigest_storage.research import ResearchConflict, ResearchRepository

    plans, jobs, inputs = admission
    if completed_prefix:
        first = asyncio.run(advance(admission, QueueClient()))
        complete(
            jobs, jobs.get(inputs["token"], inputs["workspace_id"], first.dispatches[0].job_id)
        )
    original = plans.submit

    def changed(*args):
        plan = original(*args)
        with engine.begin() as conn:
            sid = plan.sources[int(completed_prefix)].snapshot_id
            bundle = EvidenceRepository._load(conn, inputs["workspace_id"], sid)
            presentation = ResearchRepository._presentation(
                conn, inputs["workspace_id"], sid, bundle
            )
            ResearchRepository._upsert_presentation(
                conn, presentation.model_copy(update={"title": "raced"})
            )
        return plan

    monkeypatch.setattr(plans, "submit", changed)
    client = QueueClient()
    from issuedigest_storage.repository import StorageCorruption

    with pytest.raises((ResearchConflict, StorageCorruption)):
        asyncio.run(advance(admission, client))
    expected = (1, 1) if completed_prefix else (0, 0)
    assert client.calls == [] and counts(engine) == expected


def test_ambiguous_queue_and_cancel_preserve_first_pending_without_next(admission, engine):
    def lost():
        raise RuntimeError("SECRET")

    with pytest.raises(
        importlib.import_module("issuedigest_agents.evidence_dispatch").EvidenceDispatchError
    ):
        asyncio.run(advance(admission, QueueClient(lost)))
    assert counts(engine) == (1, 1)

    def cancel():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(advance(admission, QueueClient(cancel)))
    assert counts(engine) == (1, 1)
    assert asyncio.run(advance(admission, QueueClient())).dispatches[0].queued


def test_cancelled_sql_waiter_never_hidden_enqueues(admission, engine, monkeypatch):
    _, jobs, _ = admission
    entered, release, committed = threading.Event(), threading.Event(), threading.Event()
    original = jobs.submit

    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        try:
            return original(*args, **kwargs)
        finally:
            committed.set()

    monkeypatch.setattr(jobs, "submit", delayed)
    client = QueueClient()

    async def run():
        task = asyncio.create_task(advance(admission, client))
        assert await asyncio.to_thread(entered.wait, 10)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        assert await asyncio.to_thread(committed.wait, 10)

    asyncio.run(run())
    assert client.calls == [] and counts(engine) == (1, 1)


def test_revoked_after_admission_and_unknown_error_never_enqueue(admission, engine, monkeypatch):
    _, jobs, _ = admission
    original = jobs.submit

    def revoke(*args, **kwargs):
        job = original(*args, **kwargs)
        with engine.begin() as conn:
            conn.execute(text("UPDATE auth_workspace_memberships SET active=false"))
        return job

    monkeypatch.setattr(jobs, "submit", revoke)
    client = QueueClient()
    assert asyncio.run(advance(admission, client)) is None
    assert client.calls == [] and counts(engine) == (1, 1)


def test_real_dbos_mock_sse_two_source_complete_resume(
    admission, engine, database_url, monkeypatch
):
    import httpx2 as httpx
    from dbos import DBOS, DBOSClient
    from openai import AsyncOpenAI
    from sqlalchemy.schema import DropSchema
    from sqlalchemy.sql import quoted_name
    from test_evidence_worker import native_body

    _, jobs, inputs = admission
    worker = importlib.import_module("issuedigest_worker.evidence_worker")
    execute = worker.execute_evidence_job
    entered, release = threading.Event(), threading.Event()
    requests = []
    schema = "qpd_" + uuid4().hex

    def default_state():
        with engine.connect() as conn:
            metadata = conn.execute(
                text(
                    "SELECT c.oid,c.relname,c.relkind FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid=c.relnamespace "
                    "WHERE n.nspname='dbos' ORDER BY c.relname"
                )
            ).all()
            queues = (
                conn.execute(text("SELECT * FROM dbos.queues ORDER BY name")).all()
                if conn.scalar(text("SELECT to_regclass('dbos.queues')")) is not None
                else None
            )
            exists = conn.scalar(
                text("SELECT EXISTS (SELECT FROM pg_namespace WHERE nspname='dbos')")
            )
        return exists, metadata, queues

    before_default = default_state()

    async def gated(*args, **kwargs):
        entered.set()
        assert await asyncio.to_thread(release.wait, 20)
        return await execute(*args, **kwargs)

    monkeypatch.setattr(worker, "execute_evidence_job", gated)

    async def run():
        def serve(request):
            requests.append(request)
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=native_body()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            provider = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            client = None
            try:
                DBOS.migrate(database_url, schema=schema, application_role=engine.url.username)
                with engine.connect() as conn:
                    assert conn.scalar(
                        text("SELECT EXISTS (SELECT FROM pg_namespace WHERE nspname=:schema)"),
                        {"schema": schema},
                    )
                DBOS(
                    config=dict(
                        name="question-dispatch-synthetic",
                        system_database_url=database_url,
                        dbos_system_schema=schema,
                        application_version="question-test-v1",
                        run_admin_server=False,
                    )
                )
                client = DBOSClient(
                    system_database_url=database_url,
                    application_name="question-dispatch-synthetic",
                    dbos_system_schema=schema,
                )
                DBOS.launch()
                await asyncio.to_thread(
                    importlib.import_module(
                        "issuedigest_worker.evidence_queue"
                    ).register_evidence_queue,
                    jobs,
                    client=provider,
                    check_ownership=lambda _: True,
                )
                first = await advance(admission, client)
                assert await asyncio.to_thread(entered.wait, 10)
                again = await advance(admission, client)
                assert again == first and counts(engine) == (1, 1) and requests == []
                release.set()
                handle = await client.retrieve_workflow_async(first.dispatches[0].workflow_id)
                await asyncio.wait_for(handle.get_result(), 20)
                second = await advance(admission, client)
                assert second.completed_count == 1 and len(second.dispatches) == 2
                assert not second.dispatches[0].queued and second.dispatches[1].queued
                assert second.dispatches[0].job_id == first.dispatches[0].job_id
                handle = await client.retrieve_workflow_async(second.dispatches[1].workflow_id)
                await asyncio.wait_for(handle.get_result(), 20)

                async def forbidden(*args, **kwargs):
                    pytest.fail("completed plan enqueued")

                monkeypatch.setattr(client, "enqueue_async", forbidden)
                final = await advance(admission, client)
                assert (
                    final.status == "evidence_complete"
                    and final.completed_count == final.total_sources == 2
                )
                assert all(not ack.queued for ack in final.dispatches)
                assert counts(engine) == (2, 2) and len(requests) == 2
                assert all(
                    jobs.get(inputs["token"], inputs["workspace_id"], ack.job_id).status
                    == "completed"
                    for ack in final.dispatches
                )
                assert not provider.is_closed()
            finally:
                release.set()
                try:
                    if client is not None:
                        client.destroy()
                finally:
                    try:
                        DBOS.destroy(destroy_registry=True)
                    finally:
                        await provider.close()

    try:
        asyncio.run(run())
    finally:
        # Only this test's freshly generated schema is owned; default dbos is untouched.
        with engine.begin() as conn:
            conn.execute(DropSchema(quoted_name(schema, True), cascade=True, if_exists=True))
    with engine.connect() as conn:
        assert not conn.scalar(
            text("SELECT EXISTS (SELECT FROM pg_namespace WHERE nspname=:schema)"),
            {"schema": schema},
        )
    assert default_state() == before_default


def test_changed_reservation_is_conflict_not_silent_partial(admission, engine):
    from issuedigest_storage.research import ResearchConflict

    first = asyncio.run(advance(admission, QueueClient()))
    with pytest.raises(ResearchConflict):
        asyncio.run(advance(admission, QueueClient(), reservation_usd=Decimal(".75")))
    assert counts(engine) == (1, 1)
    assert asyncio.run(advance(admission, QueueClient())) == first


def test_unknown_storage_error_and_none_plan_do_not_enqueue(admission, engine, monkeypatch):
    plans, _, _ = admission
    client = QueueClient()

    def fail(*args):
        raise RuntimeError("synthetic unknown")

    monkeypatch.setattr(plans, "submit", fail)
    with pytest.raises(RuntimeError, match="synthetic unknown"):
        asyncio.run(advance(admission, client))
    monkeypatch.setattr(plans, "submit", lambda *args: None)
    assert asyncio.run(advance(admission, client)) is None
    assert client.calls == [] and counts(engine) == (0, 0)


def test_stable_child_profile_and_new_plan_identity():
    from uuid import UUID

    dispatch = module()
    plan = UUID("00000000-0000-4000-8000-000000000001")
    snapshot = UUID("00000000-0000-4000-8000-000000000002")
    child = dispatch._child(plan, snapshot, 0)
    assert str(child) == "5b2fe480-679c-4517-ad39-a3e788d893dc"
    assert child.version == 4
    assert dispatch._child(plan, snapshot, 1) != child
    assert dispatch._child(snapshot, snapshot, 0) != child


@pytest.mark.parametrize(
    "field,value",
    [
        ("job_id", uuid4()),
        ("workspace_id", uuid4()),
        ("snapshot_id", uuid4()),
        ("question", "changed"),
        ("model", "other"),
        ("source_sha256", "f" * 64),
        ("status", "unknown"),
    ],
)
def test_current_job_identity_checked_before_paid_dispatch(
    admission, engine, monkeypatch, field, value
):
    from dataclasses import replace

    from issuedigest_storage.repository import StorageCorruption

    _, jobs, _ = admission
    original = jobs.get
    monkeypatch.setattr(jobs, "get", lambda *args: replace(original(*args), **{field: value}))
    client = QueueClient()
    with pytest.raises(StorageCorruption):
        asyncio.run(advance(admission, client))
    assert client.calls == [] and counts(engine) == (1, 1)


def test_completed_acknowledgement_race_still_stops_at_first_pending(
    admission, engine, monkeypatch
):
    _, jobs, _ = admission
    original = jobs.submit
    calls = 0

    def raced(*args, **kwargs):
        nonlocal calls
        calls += 1
        job = original(*args, **kwargs)
        if calls == 2:
            complete(jobs, job)
            return jobs.get(args[0], args[1], job.job_id)
        return job

    monkeypatch.setattr(jobs, "submit", raced)
    client = QueueClient()
    result = asyncio.run(advance(admission, client))
    assert result.status == "in_progress" and len(result.dispatches) == 1
    assert result.dispatches[0].status == "completed" and not result.dispatches[0].queued
    assert client.calls == [] and counts(engine) == (1, 1)


@pytest.mark.parametrize(
    "profile", ["guarded-question-evidence-v2", "guarded-question-evidence-v3"]
)
def test_stored_profile_survives_config_change_and_partial_resume(admission, engine, profile):
    import json

    import httpx2 as httpx
    from issuedigest_agents.question_dispatch import advance_question_plan
    from issuedigest_storage.question_plans import QuestionPlanRepository
    from issuedigest_worker.evidence_worker import execute_evidence_job
    from issuedigest_worker.question_runner import run_question_plan
    from openai import AsyncOpenAI
    from test_guarded_responses_stream import Body, events

    original, jobs, args = admission
    plans = QuestionPlanRepository(original.engine, evidence_profile=profile)
    queue, requests = QueueClient(), []
    other_profile = (
        "guarded-question-evidence-v3" if profile.endswith("v2") else "guarded-question-evidence-v2"
    )

    def serve(request):
        requests.append(request)
        rows = events(
            json.dumps(
                dict(
                    propositions=[],
                    coverage=dict(linked_proposition_ids=[], unresolved_reason="insufficient"),
                )
            )
        )
        tool = (
            "fill_question_evidence_v2" if profile.endswith("v2") else "fill_question_evidence_v3"
        )
        for row in rows:
            for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
                if item is not None:
                    item["name"] = tool
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=Body(rows))

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            async with AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0) as client:
                first = await advance_question_plan(
                    plans, jobs, client=queue, app_version="test-v1", **args
                )
                assert first.completed_count == 0 and first.total_sources == 2
                receipt = await execute_evidence_job(
                    jobs,
                    first.dispatches[0].job_id,
                    client=client,
                    check_ownership=lambda _: True,
                    expected_profile=profile,
                )
                assert receipt.profile == profile
                resumed_plans = QuestionPlanRepository(engine, evidence_profile=other_profile)
                second = await advance_question_plan(
                    resumed_plans, jobs, client=queue, app_version="test-v1", **args
                )
                assert second.plan_id == first.plan_id and second.completed_count == 1
                assert counts(engine) == (2, 2)
                await execute_evidence_job(
                    jobs,
                    second.dispatches[-1].job_id,
                    client=client,
                    check_ownership=lambda _: True,
                    expected_profile=profile,
                )
                result = await run_question_plan(
                    resumed_plans, jobs, client=queue, app_version="test-v1", **args
                )
                assert result.dispatch.status == "evidence_complete"
                assert [r.profile for r in result.receipts] == [profile, profile]
                assert (
                    await run_question_plan(
                        resumed_plans, jobs, client=queue, app_version="test-v1", **args
                    )
                    == result
                )
                assert len(requests) == 2 and counts(engine) == (2, 2)
                expected = (
                    "issuedigest_guarded_evidence_job_v1"
                    if profile.endswith("v2")
                    else "issuedigest_guarded_evidence_job_v2"
                )
                assert len(queue.calls) == 2
                assert all(call[0]["workflow_name"] == expected for call in queue.calls)
                assert all(
                    call[0]["queue_name"] == "issuedigest_guarded_evidence_v1"
                    for call in queue.calls
                )

    asyncio.run(exercise())
