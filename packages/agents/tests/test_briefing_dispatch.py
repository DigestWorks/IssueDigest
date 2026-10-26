"""Authenticated existing-job dispatch against dedicated synthetic PostgreSQL."""

import asyncio
import importlib
import sys
import threading
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from uuid import uuid1, uuid4

import pytest
from sqlalchemy import text


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
    for p, original in zip(packages, attrs, strict=True):
        for key in set(vars(p)) - original.keys():
            delattr(p, key)
        for key, value in original.items():
            setattr(p, key, value)


@pytest.fixture
def admission(engine):
    from issuedigest_storage.briefing_jobs import BriefingJobRepository
    from test_briefing_worker import admit, seed

    with engine.begin() as c:
        c.execute(text("TRUNCATE briefing_jobs,evidence_jobs,question_source_plans"))
    jobs = BriefingJobRepository(engine)
    p = seed(engine)
    job = admit(jobs, p)
    yield jobs, dict(token=p[0], workspace_id=p[1], job_id=job.job_id)
    with engine.begin() as c:
        c.execute(text("TRUNCATE briefing_jobs,evidence_jobs,question_source_plans"))


class QueueClient:
    def __init__(self, action=None):
        self.calls = []
        self.action = action

    async def enqueue_async(self, options, *args):
        self.calls.append((options, args))
        if self.action:
            self.action()


def api():
    assert importlib.util.find_spec("issuedigest_agents.briefing_dispatch") is not None
    return importlib.import_module("issuedigest_agents.briefing_dispatch")


def send(jobs, inputs, client, **changes):
    return api().enqueue_briefing_job(
        jobs, client=client, app_version="briefing-test-v1", **(inputs | changes)
    )


def test_pending_duplicate_terminal_and_offloop(admission, monkeypatch):
    jobs, inputs = admission
    original, thread = jobs.get, threading.get_ident()
    reads = []

    def checked(*args):
        assert threading.get_ident() != thread
        reads.append(args)
        return original(*args)

    monkeypatch.setattr(jobs, "get", checked)
    client = QueueClient()
    first = asyncio.run(send(jobs, inputs, client))
    assert asyncio.run(send(jobs, inputs, client)) == first
    assert len(reads) == 4 and first.queued
    assert (
        client.calls
        == [
            (
                dict(
                    workflow_name="issuedigest_question_briefing_job_v1",
                    queue_name="issuedigest_guarded_evidence_v1",
                    workflow_id="question-briefing-" + str(inputs["job_id"]),
                    app_version="briefing-test-v1",
                    workflow_id_reuse_policy="return-existing",
                ),
                (str(inputs["job_id"]),),
            )
        ]
        * 2
    )
    jobs.cancel(inputs["token"], inputs["workspace_id"], inputs["job_id"])
    terminal = asyncio.run(send(jobs, inputs, client))
    assert terminal.status == "cancelled" and not terminal.queued
    with pytest.raises(FrozenInstanceError):
        first.queued = False


@pytest.mark.parametrize(
    "field,value",
    [
        ("app_version", ""),
        ("app_version", "한"),
        ("app_version", "v\n"),
        ("app_version", "a" * 129),
        ("app_version", None),
        ("workspace_id", uuid1()),
        ("job_id", uuid1()),
        ("job_id", str(uuid4())),
    ],
)
def test_invalid_before_sql(admission, monkeypatch, field, value):
    jobs, inputs = admission

    def forbidden(*args):
        pytest.fail("Invalid input reached SQL")

    monkeypatch.setattr(jobs, "get", forbidden)
    options = dict(client=QueueClient(), app_version="v1", **inputs)
    options[field] = value
    with pytest.raises(ValueError):
        asyncio.run(api().enqueue_briefing_job(jobs, **options))


@pytest.mark.parametrize("mode", ["missing", "auth", "source", "second-none", "wrong-id"])
def test_current_read_rejections(admission, monkeypatch, mode):
    jobs, inputs = admission
    client = QueueClient()
    if mode == "missing":
        monkeypatch.setattr(jobs, "get", lambda *_: None)
        assert asyncio.run(send(jobs, inputs, client, job_id=uuid4())) is None
    elif mode in ("second-none", "wrong-id"):
        original, reads = jobs.get, []

        def changed(*args):
            reads.append(True)
            job = original(*args)
            if len(reads) == 2:
                return None if mode == "second-none" else replace(job, job_id=uuid4())
            return job

        monkeypatch.setattr(jobs, "get", changed)
        if mode == "second-none":
            assert asyncio.run(send(jobs, inputs, client)) is None
        else:
            with pytest.raises(ValueError):
                asyncio.run(send(jobs, inputs, client))
    else:
        from issuedigest_storage.repository import StorageCorruption
        from issuedigest_storage.research import ResearchConflict, ResearchForbidden

        with jobs.engine.begin() as c:
            c.execute(
                text(
                    "UPDATE auth_workspace_memberships SET role='viewer'"
                    if mode == "auth"
                    else "UPDATE source_presentations "
                    "SET payload=jsonb_set(payload,'{title}','\"changed\"')"
                )
            )
        with pytest.raises((ResearchConflict, ResearchForbidden, StorageCorruption)):
            asyncio.run(send(jobs, inputs, client))
    assert client.calls == []


def test_ambiguous_ack_and_native_cancellation(admission):
    jobs, inputs = admission

    def failed():
        raise RuntimeError("PRIVATE_TOKEN_123")

    with pytest.raises(api().BriefingDispatchError) as caught:
        asyncio.run(send(jobs, inputs, QueueClient(failed)))
    error = caught.value
    assert str(error) == "Briefing queue acknowledgement unavailable"
    assert error.__context__ is None and error.__cause__ is None
    assert error.job_id == inputs["job_id"]

    def cancelled():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(send(jobs, inputs, QueueClient(cancelled)))
    assert asyncio.run(send(jobs, inputs, QueueClient())).workflow_id == error.workflow_id
    with jobs.engine.connect() as c:
        assert c.scalar(text("SELECT reservation_count FROM research_budget_months")) == 2
