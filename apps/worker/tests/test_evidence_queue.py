"""Explicit queue registration and native SSE durable execution."""

import asyncio
import importlib
import sys
import threading
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from sqlalchemy import text


@pytest.fixture(scope="module", autouse=True)
def isolate_queue_modules():
    paths = sys.path.copy()
    root = Path(__file__).resolve().parents[3]
    for path in ("packages/agents/tests", "packages/storage/tests"):
        sys.path.insert(0, str(root / path))
    packages = [importlib.import_module(n) for n in ("issuedigest_agents", "issuedigest_worker")]
    before = set(sys.modules)
    attrs = [vars(p).copy() for p in packages]
    yield
    for name in set(sys.modules) - before:
        if name.startswith(("issuedigest_agents.", "issuedigest_worker.evidence_")):
            sys.modules.pop(name, None)
    sys.path[:] = paths
    for package, original in zip(packages, attrs, strict=True):
        for key in set(vars(package)) - original.keys():
            delattr(package, key)
        for key, value in original.items():
            setattr(package, key, value)


@pytest.fixture
def queue_admission(engine):
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from test_evidence_jobs import seed

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE evidence_jobs"))
    token, workspace, snapshot = seed(engine)
    yield (
        EvidenceJobRepository(engine),
        dict(
            token=token,
            workspace_id=workspace,
            snapshot_id=snapshot,
            request_id=uuid4(),
            question="합성 질문?",
            model="gpt-6.1-sol",
            reservation_usd=Decimal(".50"),
        ),
    )
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE evidence_jobs"))


@pytest.mark.parametrize("ack_loss", [False, True])
def test_real_queue_duplicate_and_committed_ack_loss(
    queue_admission, engine, database_url, monkeypatch, ack_loss
):
    from dbos import DBOS, DBOSClient
    from test_evidence_worker import native_body

    jobs, inputs = queue_admission
    dispatch = importlib.import_module("issuedigest_agents.evidence_dispatch")
    requests = []
    entered, release = threading.Event(), threading.Event()
    worker = importlib.import_module("issuedigest_worker.evidence_worker")
    execute = worker.execute_evidence_job

    async def gated_execute(*args, **kwargs):
        entered.set()
        # Async waiting keeps both the DBOS and caller event loops available.
        assert await asyncio.to_thread(release.wait, 20), "Worker gate was not released"
        return await execute(*args, **kwargs)

    monkeypatch.setattr(worker, "execute_evidence_job", gated_execute)

    async def run():
        def serve(request):
            requests.append(request)
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=native_body()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            provider = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            DBOS.migrate(database_url, application_role=engine.url.username)
            DBOS(
                config=dict(
                    name="evidence-queue-synthetic",
                    system_database_url=database_url,
                    application_version="evidence-test-v1",
                    run_admin_server=False,
                )
            )
            client = DBOSClient(
                system_database_url=database_url, application_name="evidence-queue-synthetic"
            )
            try:
                DBOS.launch()
                registered = await asyncio.to_thread(
                    importlib.import_module(
                        "issuedigest_worker.evidence_queue"
                    ).register_evidence_queue,
                    jobs,
                    client=provider,
                    check_ownership=lambda _: True,
                )
                assert registered.queue.name == "issuedigest_guarded_evidence_v1"
                assert registered.queue._worker_concurrency == 1
                assert registered.queue._concurrency == 1
                original = client.enqueue_async
                acknowledged = []

                async def enqueue(options, *args, **kwargs):
                    handle = await original(options, *args, **kwargs)
                    acknowledged.append(options["workflow_id"])
                    return handle

                monkeypatch.setattr(client, "enqueue_async", enqueue)

                async def lost(*args, **kwargs):
                    await enqueue(*args, **kwargs)
                    raise RuntimeError("SECRET ACK question/token")

                if ack_loss:
                    monkeypatch.setattr(client, "enqueue_async", lost)
                    with pytest.raises(dispatch.EvidenceDispatchError) as caught:
                        await dispatch.submit_evidence_job(
                            jobs, client=client, app_version="evidence-test-v1", **inputs
                        )
                    assert caught.value.__context__ is None
                    assert "SECRET" not in str(caught.value)
                    monkeypatch.setattr(client, "enqueue_async", enqueue)
                first = await dispatch.submit_evidence_job(
                    jobs, client=client, app_version="evidence-test-v1", **inputs
                )
                assert await asyncio.to_thread(entered.wait, 10), "Worker did not reach gate"
                second = await dispatch.submit_evidence_job(
                    jobs, client=client, app_version="evidence-test-v1", **inputs
                )
                assert first == second and first.queued
                assert acknowledged == [first.workflow_id] * (3 if ack_loss else 2)
                assert jobs.prepare(first.job_id)[0].status == "pending"
                assert requests == []
                release.set()

                handle = await client.retrieve_workflow_async(first.workflow_id)
                await asyncio.wait_for(handle.get_result(), timeout=20)
                saved = jobs.prepare(first.job_id)[0]
                assert saved.status == "completed" and saved.receipt["status"] == "unreviewed"
                assert len(requests) == 1 and not provider.is_closed()

                async def forbidden(*args, **kwargs):
                    pytest.fail("Terminal dispatch must not enqueue")

                monkeypatch.setattr(client, "enqueue_async", forbidden)
                replay = await dispatch.submit_evidence_job(
                    jobs, client=client, app_version="evidence-test-v1", **inputs
                )
                assert replay.status == "completed" and not replay.queued
                with engine.connect() as conn:
                    assert (
                        conn.scalar(text("SELECT reservation_count FROM research_budget_months"))
                        == 1
                    )
            finally:
                release.set()
                client.destroy()
                DBOS.destroy(destroy_registry=True)

    asyncio.run(run())


def test_persisted_incompatible_limits_fail_closed(
    queue_admission, engine, database_url, monkeypatch
):
    from dbos import DBOS

    jobs, _ = queue_admission
    DBOS.migrate(database_url, application_role=engine.url.username)
    DBOS(
        config=dict(
            name="evidence-queue-synthetic",
            system_database_url=database_url,
            application_version="evidence-test-v1",
            run_admin_server=False,
        )
    )
    provider = AsyncOpenAI(api_key="synthetic", max_retries=0)
    try:
        DBOS.launch()
        original = DBOS.register_queue
        original(
            "issuedigest_guarded_evidence_v1",
            global_concurrency=2,
            worker_concurrency=2,
            on_conflict="always_update",
        )

        def retained(name, **kwargs):
            return original(name, **kwargs, on_conflict="never_update")

        monkeypatch.setattr(DBOS, "register_queue", retained)
        with pytest.raises(ValueError, match="Evidence queue limits unavailable"):
            importlib.import_module("issuedigest_worker.evidence_queue").register_evidence_queue(
                jobs, client=provider, check_ownership=lambda _: True
            )
        assert not provider.is_closed()
    finally:
        asyncio.run(provider.close())
        DBOS.destroy(destroy_registry=True)


def test_import_does_not_register_connect_or_read_environment():
    import subprocess

    script = """
from dbos import DBOS
import socket, os
import issuedigest_worker.evidence_worker
import issuedigest_storage.evidence_jobs

def forbidden(*a, **k):
    raise AssertionError("Import performed external action")
DBOS.register_queue = forbidden
DBOS.launch = forbidden
socket.create_connection = forbidden
os.getenv = forbidden
import issuedigest_agents.evidence_dispatch
import issuedigest_worker.evidence_queue
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_queue_module_available():
    assert importlib.util.find_spec("issuedigest_worker.evidence_queue") is not None
