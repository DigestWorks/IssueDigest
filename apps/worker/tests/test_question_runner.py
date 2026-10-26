"""Automatic private question progression, using only synthetic evidence and native I/O."""

import asyncio
import importlib
import sys
import threading
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event, text


def module():
    assert importlib.util.find_spec("issuedigest_worker.question_runner"), "Missing question runner"
    return importlib.import_module("issuedigest_worker.question_runner")


def test_runner_available():
    assert module().run_question_plan


@pytest.fixture(scope="module", autouse=True)
def isolated_runner_modules():
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
            question="앞",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".50"),
        ),
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE question_source_plans, evidence_jobs"))


def run(admission, client, **changes):
    plans, jobs, inputs = admission
    return module().run_question_plan(
        plans, jobs, client=client, app_version="question-runner-test-v1", **(inputs | changes)
    )


def complete(jobs, job):
    from test_evidence_jobs import completion_receipt

    receipt = completion_receipt(jobs, job)
    assert jobs.claim(
        job.job_id,
        prompt_sha256=receipt["prompt_sha256"],
        instructions_sha256=receipt["instructions_sha256"],
    )
    assert (
        jobs.finish(
            job.job_id,
            receipt=receipt,
            known_usage=receipt["usage"],
            usage_complete=True,
            stream_closed=True,
        ).status
        == "completed"
    )


def counts(engine):
    with engine.connect() as conn:
        return (
            conn.scalar(text("SELECT count(*) FROM evidence_jobs")),
            conn.scalar(
                text("SELECT coalesce(sum(reservation_count),0) FROM research_budget_months")
            ),
        )


class CompletingClient:
    def __init__(self, admission, action=None):
        self.admission = admission
        self.action = action
        self.queued = []
        self.waited = []

    async def enqueue_async(self, options, *args):
        self.queued.append(options["workflow_id"])

    async def retrieve_workflow_async(self, workflow_id):
        self.waited.append(workflow_id)

        async def result():
            _, jobs, inputs = self.admission
            job = await asyncio.to_thread(
                jobs.get, inputs["token"], inputs["workspace_id"], UUID(workflow_id[17:])
            )
            if job.status != "completed":
                await asyncio.to_thread(complete, jobs, job)
            if self.action:
                await self.action()
            return {"untrusted": "workflow output must never become a receipt"}

        return SimpleNamespace(get_result=result)


def test_one_call_collects_ordered_receipts_and_replay_is_free(admission, engine):
    client = CompletingClient(admission)
    result = asyncio.run(run(admission, client))
    assert result.dispatch.status == "evidence_complete"
    assert result.dispatch.completed_count == result.dispatch.total_sources == 2
    assert len(result.receipts) == 2 and all(r.status == "unreviewed" for r in result.receipts)
    assert counts(engine) == (2, 2) and len(client.queued) == len(client.waited) == 2
    assert set(vars(result)) == {"dispatch", "receipts"}
    with pytest.raises(FrozenInstanceError):
        result.receipts = ()
    assert asyncio.run(run(admission, client)) == result
    assert counts(engine) == (2, 2) and len(client.queued) == len(client.waited) == 2


def test_no_match_none_and_blocked_return_no_receipts(admission, engine, monkeypatch):
    client = CompletingClient(admission)
    result = asyncio.run(run(admission, client, question="?!"))
    assert result.dispatch.status == "no_match" and result.receipts == ()
    assert counts(engine) == (0, 0) and client.waited == []
    plans, jobs, inputs = admission
    inputs["request_id"] = uuid4()
    dispatch = importlib.import_module("issuedigest_agents.question_dispatch")
    first = asyncio.run(
        dispatch.advance_question_plan(plans, jobs, client=client, app_version="test", **inputs)
    )
    jobs.cancel(inputs["token"], inputs["workspace_id"], first.dispatches[0].job_id)
    result = asyncio.run(run(admission, client))
    assert result.dispatch.status == "blocked" and result.receipts == () and client.waited == []
    monkeypatch.setattr(plans, "submit", lambda *args: None)
    assert asyncio.run(run(admission, client)) is None


@pytest.mark.parametrize("value", [True, False, 0, 601, -1, 1.0, "1", None])
def test_timeout_exact_int_before_sql(admission, engine, value):
    def forbidden(*args):
        pytest.fail("Invalid timeout issued SQL")

    event.listen(engine, "before_cursor_execute", forbidden)
    try:
        with pytest.raises(ValueError):
            asyncio.run(run(admission, CompletingClient(admission), total_timeout_seconds=value))
    finally:
        event.remove(engine, "before_cursor_execute", forbidden)


@pytest.mark.parametrize("stage", ["retrieve", "result"])
@pytest.mark.parametrize("error", [RuntimeError("SECRET question/token"), TimeoutError("SECRET")])
def test_native_errors_are_sanitized_outside_handler(admission, stage, error):
    client = CompletingClient(admission)

    async def fail(*args):
        raise error

    async def handle(*args):
        return SimpleNamespace(get_result=fail)

    client.retrieve_workflow_async = fail if stage == "retrieve" else handle
    with pytest.raises(module().QuestionRunError) as caught:
        asyncio.run(run(admission, client))
    assert caught.value.reason == "workflow"
    assert caught.value.__context__ is caught.value.__cause__ is None
    assert "SECRET" not in str(caught.value)


@pytest.mark.parametrize("cancel", [False, True])
def test_wait_timeout_or_cancel_has_no_hidden_next_child(admission, engine, cancel):
    client = CompletingClient(admission)
    entered = asyncio.Event()

    async def handle(*args):
        async def pending():
            entered.set()
            await asyncio.Event().wait()

        return SimpleNamespace(get_result=pending)

    client.retrieve_workflow_async = handle

    async def exercise():
        task = asyncio.create_task(run(admission, client, total_timeout_seconds=1))
        await entered.wait()
        assert counts(engine) == (1, 1)
        if cancel:
            task.cancel()
        with pytest.raises(asyncio.CancelledError if cancel else TimeoutError):
            await task
        await asyncio.sleep(0)

    asyncio.run(exercise())
    assert counts(engine) == (1, 1) and len(client.queued) == 1


def ack(status="pending", queued=True, job_id=None):
    from issuedigest_agents.evidence_dispatch import EvidenceDispatch

    job_id = job_id or uuid4()
    return EvidenceDispatch(job_id, "guarded-evidence-" + str(job_id), status, queued)


def progress(status="in_progress", completed=0, total=2, dispatches=None, plan=None):
    from issuedigest_agents.question_dispatch import QuestionDispatch

    return QuestionDispatch(
        plan or uuid4(), status, completed, total, (ack(),) if dispatches is None else dispatches
    )


@pytest.mark.parametrize(
    "change",
    [
        {"plan_id": "bad"},
        {"plan_id": UUID(int=1)},
        {"total_sources": True},
        {"total_sources": 6},
        {"completed_count": False},
        {"completed_count": -1},
        {"status": "secret"},
        {"dispatches": []},
        {"dispatches": (object(),)},
        {"dispatches": ()},
        {"completed_count": 1},
        {"status": "evidence_complete"},
        {"status": "no_match"},
        {"status": "blocked"},
    ],
)
def test_invalid_progress_rejected_before_workflow_lookup(monkeypatch, change):
    runner = module()
    bad = replace(progress(), **change)

    async def advance(*args, **kwargs):
        return bad

    monkeypatch.setattr(runner, "advance_question_plan", advance)
    with pytest.raises(runner.QuestionRunError) as caught:
        asyncio.run(
            runner.run_question_plan(
                None,
                None,
                client=object(),
                app_version="test",
                token="synthetic",
                workspace_id=uuid4(),
                request_id=uuid4(),
                question="앞",
                model="gpt-6.1-sol",
                reservation_usd=Decimal(".50"),
            )
        )
    assert caught.value.reason == "progress" and caught.value.__context__ is None


@pytest.mark.parametrize(
    "change",
    [
        {"job_id": "bad"},
        {"workflow_id": "other"},
        {"status": "other"},
        {"queued": 1},
        {"status": "running", "queued": True},
        {"status": "failed"},
    ],
)
def test_invalid_ack_rejected_before_workflow_lookup(monkeypatch, change):
    runner = module()
    state = progress(dispatches=(replace(ack(), **change),))

    async def advance(*args, **kwargs):
        return state

    monkeypatch.setattr(runner, "advance_question_plan", advance)
    with pytest.raises(runner.QuestionRunError, match="progress"):
        asyncio.run(
            runner.run_question_plan(
                None,
                None,
                client=object(),
                app_version="test",
                token="synthetic",
                workspace_id=uuid4(),
                request_id=uuid4(),
                question="앞",
                model="gpt-6.1-sol",
                reservation_usd=Decimal(".50"),
            )
        )


@pytest.mark.parametrize("change", ["no_progress", "plan", "total", "same_child", "prefix"])
def test_progress_must_be_monotone_and_stable(admission, monkeypatch, change):
    runner = module()
    first_ack = ack("completed", False)
    first = progress(completed=1, total=3, dispatches=(first_ack, ack()))
    next_ack = ack()
    second = progress(
        completed=2,
        total=3,
        dispatches=(
            first_ack,
            replace(first.dispatches[1], status="completed", queued=False),
            next_ack,
        ),
        plan=first.plan_id,
    )
    if change == "no_progress":
        second = first
    elif change == "plan":
        second = replace(second, plan_id=uuid4())
    elif change == "total":
        second = replace(second, total_sources=4)
    elif change == "same_child":
        second = replace(second, dispatches=(first_ack, next_ack, first.dispatches[1]))
    else:
        second = replace(
            second, dispatches=(ack("completed", False), second.dispatches[1], next_ack)
        )
    states = iter((first, second))

    async def advance(*args, **kwargs):
        return next(states)

    async def handle(*args):
        async def result():
            return None

        return SimpleNamespace(get_result=result)

    monkeypatch.setattr(runner, "advance_question_plan", advance)
    monkeypatch.setattr(runner, "_wait_authorized", lambda *a: True)
    client = SimpleNamespace(retrieve_workflow_async=handle)
    with pytest.raises(runner.QuestionRunError, match="progress"):
        asyncio.run(run(admission, client))


@pytest.mark.parametrize("change", ["authority", "source", "metadata", "session"])
def test_current_guards_rechecked_after_wait(admission, engine, change):
    async def mutate():
        with engine.begin() as conn:
            conn.execute(
                text(
                    {
                        "authority": "UPDATE auth_workspace_memberships SET role='viewer'",
                        "session": "DELETE FROM auth_sessions",
                        "source": (
                            "UPDATE parsed_representations SET "
                            "payload=jsonb_set(payload,'{text}','\"changed\"')"
                        ),
                        "metadata": (
                            "UPDATE source_presentations SET "
                            "payload=jsonb_set(payload,'{title}','\"changed\"')"
                        ),
                    }[change]
                )
            )

    client = CompletingClient(admission, mutate)
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchForbidden
    from issuedigest_storage.sessions import AuthenticationDenied

    with pytest.raises((StorageCorruption, ResearchForbidden, AuthenticationDenied)):
        asyncio.run(run(admission, client))
    assert counts(engine) == (1, 1) and len(client.queued) == 1


@pytest.mark.parametrize("change", ["receipt", "usage", "missing", "status", "source", "extra"])
def test_completed_replay_refuses_tampered_receipts(admission, engine, monkeypatch, change):
    client = CompletingClient(admission)
    result = asyncio.run(run(admission, client))
    job_id = result.dispatch.dispatches[0].job_id
    if change == "extra":
        worker = importlib.import_module("issuedigest_worker.evidence_worker")
        original = worker.read_completed_evidence_job
        monkeypatch.setattr(
            worker,
            "read_completed_evidence_job",
            lambda *a, **kw: original(*a, **kw).model_copy(update={"status": "approved"}),
        )
    else:
        with engine.begin() as conn:
            conn.execute(
                text(
                    {
                        "receipt": (
                            "UPDATE evidence_jobs SET receipt_sha256=:value WHERE job_id=:job"
                        ),
                        "usage": (
                            "UPDATE evidence_jobs SET known_usage='{}'::jsonb WHERE job_id=:job"
                        ),
                        "missing": "UPDATE evidence_jobs SET receipt=NULL WHERE job_id=:job",
                        "status": "UPDATE evidence_jobs SET usage_complete=false WHERE job_id=:job",
                        "source": "UPDATE evidence_jobs SET source_sha256=:value WHERE job_id=:job",
                    }[change]
                ),
                {"value": "f" * 64, "job": job_id},
            )
    from issuedigest_storage.repository import StorageCorruption

    with pytest.raises((module().QuestionRunError, StorageCorruption)):
        asyncio.run(run(admission, client))
    assert counts(engine) == (2, 2) and len(client.queued) == len(client.waited) == 2


@pytest.mark.parametrize("change", ["source", "authority", "other_id"])
def test_collection_revalidates_after_last_read_and_denies_other_id(
    admission, engine, monkeypatch, change
):
    client = CompletingClient(admission)
    asyncio.run(run(admission, client))
    worker = importlib.import_module("issuedigest_worker.evidence_worker")
    original = worker.read_completed_evidence_job
    reads = []

    def altered(*args, **kwargs):
        assert kwargs["check_ownership"](uuid4()) is False
        receipt = original(*args, **kwargs)
        reads.append(args[1])
        if len(reads) == 2:
            if change == "other_id":
                assert kwargs["check_ownership"](reads[0]) is False
                return None
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE auth_workspace_memberships SET role='viewer'"
                        if change == "authority"
                        else (
                            "UPDATE parsed_representations SET "
                            "payload=jsonb_set(payload,'{text}','\"late\"')"
                        )
                    )
                )
        return receipt

    monkeypatch.setattr(worker, "read_completed_evidence_job", altered)
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchForbidden

    with pytest.raises((module().QuestionRunError, StorageCorruption, ResearchForbidden)) as caught:
        asyncio.run(run(admission, client))
    if change == "other_id":
        assert type(caught.value) is module().QuestionRunError
        assert caught.value.reason == "receipt" and caught.value.__context__ is None
    else:
        from issuedigest_storage.repository import StorageCorruption
        from issuedigest_storage.research import ResearchForbidden

        assert isinstance(caught.value, (StorageCorruption, ResearchForbidden))
    assert counts(engine) == (2, 2) and len(client.queued) == 2


def test_unknown_advance_errors_are_not_caught(admission, monkeypatch):
    runner = module()

    async def broken(*args, **kwargs):
        raise RuntimeError("synthetic existing advance exception")

    monkeypatch.setattr(runner, "advance_question_plan", broken)
    with pytest.raises(RuntimeError, match="synthetic existing"):
        asyncio.run(run(admission, object()))


@pytest.mark.parametrize("change", ["expired", "job_id", "snapshot", "plan", "raw_plan"])
def test_current_authority_and_fixed_source_checked_before_native_wait(
    admission, engine, monkeypatch, change
):
    runner = module()
    plans, jobs, inputs = admission
    original = runner.advance_question_plan
    get = jobs.get

    async def altered(*args, **kwargs):
        result = await original(*args, **kwargs)
        if change == "expired":
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM auth_sessions"))
        elif change in ("job_id", "snapshot"):
            monkeypatch.setattr(
                jobs,
                "get",
                lambda *a: replace(
                    get(*a), **{"job_id" if change == "job_id" else "snapshot_id": uuid4()}
                ),
            )
        else:
            saved = plans.submit(
                inputs["token"], inputs["workspace_id"], inputs["request_id"], inputs["question"]
            )
            updates = {"plan_id": uuid4()} if change == "plan" else {"sources": list(saved.sources)}
            monkeypatch.setattr(plans, "submit", lambda *a: saved.model_copy(update=updates))
        return result

    monkeypatch.setattr(runner, "advance_question_plan", altered)
    client = CompletingClient(admission)
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.sessions import AuthenticationDenied

    with pytest.raises((runner.QuestionRunError, StorageCorruption, AuthenticationDenied)):
        asyncio.run(run(admission, client))
    assert counts(engine) == (1, 1) and client.waited == [] and len(client.queued) == 1


def test_native_two_source_single_call_concurrent_replay_owned_schema(
    admission, engine, database_url, monkeypatch
):
    import httpx2 as httpx
    from dbos import DBOS, DBOSClient
    from openai import AsyncOpenAI
    from sqlalchemy.schema import DropSchema
    from sqlalchemy.sql import quoted_name
    from test_evidence_worker import native_body

    _, jobs, _ = admission
    worker = importlib.import_module("issuedigest_worker.evidence_worker")
    execute = worker.execute_evidence_job
    entered, release = threading.Event(), threading.Event()
    requests = []
    schema = "qpr_" + uuid4().hex

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

    before = default_state()

    async def gated(*args, **kwargs):
        entered.set()
        assert await asyncio.to_thread(release.wait, 20), "Native gate not released"
        return await execute(*args, **kwargs)

    monkeypatch.setattr(worker, "execute_evidence_job", gated)

    async def exercise():
        def serve(request):
            requests.append(request)
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=native_body()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            provider = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            client = None
            active = []
            try:
                DBOS.migrate(database_url, schema=schema, application_role=engine.url.username)
                DBOS(
                    config=dict(
                        name="question-runner-synthetic",
                        system_database_url=database_url,
                        dbos_system_schema=schema,
                        application_version="question-runner-test-v1",
                        run_admin_server=False,
                    )
                )
                client = DBOSClient(
                    system_database_url=database_url,
                    application_name="question-runner-synthetic",
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
                waits = []
                original = client.retrieve_workflow_async

                async def retrieve(workflow_id):
                    waits.append(workflow_id)
                    return await original(workflow_id)

                monkeypatch.setattr(client, "retrieve_workflow_async", retrieve)
                active.append(asyncio.create_task(run(admission, client)))
                assert await asyncio.to_thread(entered.wait, 10)
                active.append(asyncio.create_task(run(admission, client)))
                # Both callers observe the same durable first workflow before it can run.
                async with asyncio.timeout(10):
                    while len(waits) < 2:
                        await asyncio.sleep(0.01)
                assert counts(engine) == (1, 1) and requests == []
                assert waits[0] == waits[1]
                release.set()
                first, second = await asyncio.gather(*active)
                assert first == second and first.dispatch.status == "evidence_complete"
                assert len(first.receipts) == 2 and all(
                    r.status == "unreviewed" for r in first.receipts
                )
                assert counts(engine) == (2, 2) and len(requests) == 2
                assert len(set(waits)) == 2 and len(waits) <= 4

                async def forbidden(*args, **kwargs):
                    pytest.fail("Completed replay attempted native queue/wait")

                monkeypatch.setattr(client, "enqueue_async", forbidden)
                monkeypatch.setattr(client, "retrieve_workflow_async", forbidden)
                assert await run(admission, client) == first
                assert counts(engine) == (2, 2) and len(requests) == 2
                assert not provider.is_closed()
            finally:
                release.set()
                for task in active:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*active, return_exceptions=True)
                try:
                    if client is not None:
                        client.destroy()
                finally:
                    try:
                        DBOS.destroy(destroy_registry=True)
                    finally:
                        await provider.close()

    try:
        asyncio.run(exercise())
    finally:
        with engine.begin() as conn:
            conn.execute(DropSchema(quoted_name(schema, True), cascade=True, if_exists=True))
    with engine.connect() as conn:
        assert not conn.scalar(
            text("SELECT EXISTS (SELECT FROM pg_namespace WHERE nspname=:schema)"),
            {"schema": schema},
        )
    assert default_state() == before


def test_five_sources_bounded_to_five_waits_six_advances_offloop_sql(
    admission, engine, monkeypatch
):
    from issuedigest_domain import EvidenceBundle
    from issuedigest_storage import EvidenceRepository

    from conftest import bundle_data

    plans, _, inputs = admission
    for _ in range(3):
        data = bundle_data()
        data["document"]["workspace_id"] = str(inputs["workspace_id"])
        snapshot = uuid4()
        EvidenceRepository(engine).save(snapshot, EvidenceBundle.model_validate(data))
        EvidenceRepository(engine).rebuild_projection(inputs["workspace_id"], snapshot)
    client = CompletingClient(admission)
    runner = module()
    advance = runner.advance_question_plan
    calls = []
    main_thread = threading.get_ident()

    async def recorded(*args, **kwargs):
        calls.append(kwargs.copy())
        return await advance(*args, **kwargs)

    def offloop(*args):
        assert threading.get_ident() != main_thread, "Runner blocked event loop with SQL"

    monkeypatch.setattr(runner, "advance_question_plan", recorded)
    event.listen(engine, "before_cursor_execute", offloop)
    try:
        result = asyncio.run(run(admission, client))
    finally:
        event.remove(engine, "before_cursor_execute", offloop)
    assert (
        result.dispatch.completed_count
        == result.dispatch.total_sources
        == len(result.receipts)
        == 5
    )
    assert len(calls) == 6 and all(call == calls[0] for call in calls)
    assert len(client.waited) == len(client.queued) == 5 and counts(engine) == (5, 5)
    assert (
        plans.submit(
            inputs["token"], inputs["workspace_id"], inputs["request_id"], inputs["question"]
        ).plan_id
        == result.dispatch.plan_id
    )


def test_completed_acknowledgement_race_advances_without_repeat_job(admission, engine, monkeypatch):
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
    client = CompletingClient(admission)
    result = asyncio.run(run(admission, client))
    assert len(result.receipts) == 2 and counts(engine) == (2, 2)
    assert len(client.waited) == 2 and len(client.queued) == 1


@pytest.mark.parametrize(
    "change", ["duplicate", "prefix_queue", "prefix_status", "extra", "subclass"]
)
def test_raw_progress_and_prefix_shape_checks(admission, monkeypatch, change):
    from issuedigest_agents.question_dispatch import QuestionDispatch

    runner = module()
    first = ack("completed", False)
    state = progress(completed=1, dispatches=(first, ack()))
    if change == "duplicate":
        state = replace(state, dispatches=(first, replace(first, status="pending", queued=True)))
    elif change == "prefix_queue":
        state = replace(state, dispatches=(replace(first, queued=True), state.dispatches[1]))
    elif change == "prefix_status":
        state = replace(state, dispatches=(replace(first, status="running"), state.dispatches[1]))
    elif change == "extra":
        object.__setattr__(state, "receipt", {"untrusted": True})
    else:

        class UntrustedDispatch(QuestionDispatch):
            pass

        state = UntrustedDispatch(**vars(state))

    async def advance(*args, **kwargs):
        return state

    monkeypatch.setattr(runner, "advance_question_plan", advance)
    client = CompletingClient(admission)
    with pytest.raises(runner.QuestionRunError, match="progress"):
        asyncio.run(run(admission, client))
    assert client.waited == client.queued == []


@pytest.mark.parametrize("change", ["missing_plan", "raw_plan", "unknown", "expired"])
def test_collection_boundary_preserves_current_access_and_sanitizes_unknown(
    admission, engine, monkeypatch, change
):
    runner = module()
    client = CompletingClient(admission)
    asyncio.run(run(admission, client))
    plans, _, inputs = admission
    original = runner.advance_question_plan

    async def completed(*args, **kwargs):
        result = await original(*args, **kwargs)
        if change == "expired":
            with engine.begin() as conn:
                conn.execute(text("DELETE FROM auth_sessions"))
        elif change == "unknown":

            def broken(*args):
                raise RuntimeError("SECRET token/receipt")

            monkeypatch.setattr(plans, "submit", broken)
        elif change == "missing_plan":
            monkeypatch.setattr(plans, "submit", lambda *a: None)
        else:
            plan = plans.submit(
                inputs["token"], inputs["workspace_id"], inputs["request_id"], inputs["question"]
            )
            monkeypatch.setattr(plans, "submit", lambda *a: plan.model_copy(update={"receipt": {}}))
        return result

    monkeypatch.setattr(runner, "advance_question_plan", completed)
    if change == "missing_plan":
        assert asyncio.run(run(admission, client)) is None
    else:
        from issuedigest_storage.repository import StorageCorruption
        from issuedigest_storage.sessions import AuthenticationDenied

        expected = {
            "raw_plan": StorageCorruption,
            "expired": AuthenticationDenied,
            "unknown": runner.QuestionRunError,
        }[change]
        with pytest.raises(expected) as caught:
            asyncio.run(run(admission, client))
        if change == "unknown":
            assert caught.value.__context__ is caught.value.__cause__ is None
            assert caught.value.reason == "receipt" and "SECRET" not in str(caught.value)
    assert counts(engine) == (2, 2) and len(client.waited) == 2
