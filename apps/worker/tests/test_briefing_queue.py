"""Native DBOS briefing queue against dedicated synthetic PostgreSQL."""

import asyncio
import importlib
import sys
import threading
from pathlib import Path
from uuid import uuid1, uuid4

import httpx2 as httpx
import pytest
from dbos import DBOS, DBOSClient, SetWorkflowID
from openai import AsyncOpenAI
from sqlalchemy import text
from sqlalchemy.schema import DropSchema
from sqlalchemy.sql import quoted_name


@pytest.fixture(scope="module", autouse=True)
def isolated_modules():
    paths, before = sys.path.copy(), set(sys.modules)
    packages = [importlib.import_module(n) for n in ("issuedigest_agents", "issuedigest_worker")]
    attrs = [vars(p).copy() for p in packages]
    root = Path(__file__).resolve().parents[3]
    for path in ("apps/worker/tests", "packages/agents/tests"):
        sys.path.insert(0, str(root / path))
    yield
    for name in set(sys.modules) - before:
        if name.startswith(("issuedigest_agents.", "issuedigest_worker.", "test_")):
            sys.modules.pop(name, None)
    sys.path[:] = paths
    for package, original in zip(packages, attrs, strict=True):
        for name in set(vars(package)) - original.keys():
            delattr(package, name)
        for name, value in original.items():
            setattr(package, name, value)


@pytest.fixture
def admitted(engine):
    from issuedigest_storage.briefing_jobs import BriefingJobRepository
    from test_briefing_worker import admit, seed

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs,evidence_jobs,question_source_plans"))
    jobs = BriefingJobRepository(engine)
    inputs = seed(engine)
    job = admit(jobs, inputs)
    yield jobs, inputs, job
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE briefing_jobs,evidence_jobs,question_source_plans"))


def queue_api():
    assert importlib.util.find_spec("issuedigest_worker.briefing_queue") is not None
    return importlib.import_module("issuedigest_worker.briefing_queue")


def test_registration_conflict_precedes_workflow(admitted, monkeypatch):
    jobs, _, _ = admitted
    from types import SimpleNamespace

    called = []

    def conflict(*args, **kwargs):
        called.append((args, kwargs))
        return SimpleNamespace(global_concurrency=2, worker_concurrency=1)

    monkeypatch.setattr(DBOS, "register_queue", conflict)
    with pytest.raises(ValueError, match="queue limits"):
        queue_api().register_briefing_queue(jobs, client=object(), check_ownership=lambda _: True)
    assert called == [
        (
            ("issuedigest_guarded_evidence_v1",),
            dict(global_concurrency=1, worker_concurrency=1, on_conflict="never_update"),
        )
    ]


def test_native_queue_identity_replay_and_completion(admitted, engine, database_url, monkeypatch):
    from test_guarded_responses_stream import Body
    from test_question_briefing_generation import rows

    jobs, inputs, job = admitted
    schema = "qbf_" + uuid4().hex
    requests = []
    allow = True
    entered, release = threading.Event(), threading.Event()

    def owned(_):
        return allow

    def serve(request):
        requests.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            stream=Body(
                rows(dict(outcome="insufficient_evidence", message="합성 근거 부족", modules=[]))
            ),
        )

    async def run():
        nonlocal allow
        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            provider = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            remote = None
            try:
                DBOS.migrate(database_url, schema=schema, application_role=engine.url.username)
                DBOS(
                    config=dict(
                        name="briefing-queue-synthetic",
                        system_database_url=database_url,
                        dbos_system_schema=schema,
                        application_version="briefing-test-v1",
                        run_admin_server=False,
                    )
                )
                remote = DBOSClient(
                    system_database_url=database_url,
                    application_name="briefing-queue-synthetic",
                    dbos_system_schema=schema,
                )
                DBOS.launch()
                module = queue_api()
                execute = module.execute_briefing_job

                async def gated(*args, **kwargs):
                    entered.set()
                    assert await asyncio.to_thread(release.wait, 20)
                    return await execute(*args, **kwargs)

                monkeypatch.setattr(module, "execute_briefing_job", gated)
                registered = await asyncio.to_thread(
                    module.register_briefing_queue,
                    jobs,
                    client=provider,
                    check_ownership=owned,
                )
                assert await registered.queue.get_global_concurrency_async() == 1
                assert await registered.queue.get_worker_concurrency_async() == 1
                workflow = registered.workflow
                for bad in (str(uuid1()), str(job.job_id).upper(), "not-a-uuid", 42):
                    with pytest.raises((ValueError, TypeError)):
                        await workflow(bad)
                with SetWorkflowID("wrong-" + str(job.job_id)):
                    with pytest.raises(ValueError):
                        await workflow(str(job.job_id))
                allow = False
                denied_id = uuid4()
                from issuedigest_storage.research import ResearchForbidden

                with SetWorkflowID("question-briefing-" + str(denied_id)):
                    with pytest.raises(ResearchForbidden):
                        await workflow(str(denied_id))
                allow = True
                from issuedigest_agents.briefing_dispatch import enqueue_briefing_job

                async def send():
                    return await enqueue_briefing_job(
                        jobs,
                        client=remote,
                        app_version="briefing-test-v1",
                        token=inputs[0],
                        workspace_id=inputs[1],
                        job_id=job.job_id,
                    )

                original_enqueue = remote.enqueue_async

                async def lost_ack(*args, **kwargs):
                    await original_enqueue(*args, **kwargs)
                    raise RuntimeError("PRIVATE_QUEUE_ACK")

                monkeypatch.setattr(remote, "enqueue_async", lost_ack)
                from issuedigest_agents.briefing_dispatch import BriefingDispatchError

                with pytest.raises(BriefingDispatchError) as caught:
                    await send()
                assert caught.value.__context__ is None and caught.value.__cause__ is None
                assert "PRIVATE_QUEUE_ACK" not in str(caught.value)
                assert await asyncio.to_thread(entered.wait, 10)
                monkeypatch.setattr(remote, "enqueue_async", original_enqueue)
                first = await send()
                assert first.queued
                assert (await send()).workflow_id == first.workflow_id
                assert requests == []
                release.set()
                handle = await remote.retrieve_workflow_async(first.workflow_id)
                assert await asyncio.wait_for(handle.get_result(), 30) is None
                final = await send()
                assert final.status == "completed" and not final.queued
                assert len(requests) == 1 and not provider.is_closed()
                with engine.connect() as conn:
                    assert (
                        conn.scalar(text("SELECT reservation_count FROM research_budget_months"))
                        == 2
                    )
                from issuedigest_worker.briefing_worker import read_completed_briefing_job

                assert (
                    await read_completed_briefing_job(
                        jobs, job.job_id, check_ownership=lambda _: True
                    )
                    is not None
                )
            finally:
                release.set()
                if remote is not None:
                    remote.destroy()
                DBOS.destroy(destroy_registry=True)
                await provider.close()

    try:
        asyncio.run(run())
    finally:
        with engine.begin() as conn:
            conn.execute(DropSchema(quoted_name(schema, True), cascade=True, if_exists=True))
