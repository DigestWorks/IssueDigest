"""Admission and acknowledgement boundaries, using real synthetic SQL."""

import asyncio
import importlib
import sys
import threading
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text


@pytest.fixture(scope="module", autouse=True)
def isolated_modules():
    paths = sys.path.copy()
    root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(root / "packages/storage/tests"))
    packages = [importlib.import_module(n) for n in ("issuedigest_agents",)]
    before = set(sys.modules)
    attrs = [vars(p).copy() for p in packages]
    yield
    for name in set(sys.modules) - before:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)
    sys.path[:] = paths
    for package, original in zip(packages, attrs, strict=True):
        for key in set(vars(package)) - original.keys():
            delattr(package, key)
        for key, value in original.items():
            setattr(package, key, value)


@pytest.fixture
def admission(engine):
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


class QueueClient:
    """Only external enqueue is replaced; SQL admission remains real."""

    def __init__(self, action=None):
        self.calls = []
        self.action = action

    async def enqueue_async(self, options, *args):
        self.calls.append((options, args))
        if self.action:
            self.action()


def module():
    assert importlib.util.find_spec("issuedigest_agents.evidence_dispatch") is not None
    return importlib.import_module("issuedigest_agents.evidence_dispatch")


def send(jobs, inputs, client, **changes):
    return module().submit_evidence_job(
        jobs, client=client, app_version="evidence-test-v1", **(inputs | changes)
    )


def test_pending_retry_payload_and_cancelled_skip(admission):
    jobs, inputs = admission
    client = QueueClient()
    first = asyncio.run(send(jobs, inputs, client))
    second = asyncio.run(send(jobs, inputs, client))
    assert first == second and first.status == "pending" and first.queued
    assert set(vars(first)) == {"job_id", "workflow_id", "status", "queued"}
    assert (
        client.calls
        == [
            (
                dict(
                    workflow_name="issuedigest_guarded_evidence_job_v1",
                    queue_name="issuedigest_guarded_evidence_v1",
                    workflow_id="guarded-evidence-" + str(first.job_id),
                    app_version="evidence-test-v1",
                    workflow_id_reuse_policy="return-existing",
                ),
                (str(first.job_id),),
            )
        ]
        * 2
    )
    jobs.cancel(inputs["token"], inputs["workspace_id"], first.job_id)
    terminal = asyncio.run(send(jobs, inputs, client))
    assert terminal.status == "cancelled" and not terminal.queued
    assert len(client.calls) == 2


@pytest.mark.parametrize("version", [None, "", " ", "a b", "한", "a" * 129, "v\n"])
def test_invalid_version_precedes_storage(admission, version):
    jobs, inputs = admission
    client = QueueClient()
    with pytest.raises(ValueError):
        asyncio.run(
            module().submit_evidence_job(jobs, client=client, app_version=version, **inputs)
        )
    assert client.calls == []
    with jobs.engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM evidence_jobs")) == 0


def test_none_and_source_failure_never_enqueue(admission):
    from issuedigest_storage.research import ResearchConflict

    jobs, inputs = admission
    client = QueueClient()
    from issuedigest_storage.sessions import AuthenticationDenied

    with pytest.raises(AuthenticationDenied):
        asyncio.run(send(jobs, inputs, client, token="invalid"))
    assert asyncio.run(send(jobs, inputs, client, workspace_id=uuid4())) is None
    with pytest.raises(ResearchConflict):
        asyncio.run(send(jobs, inputs, client, snapshot_id=uuid4()))
    assert client.calls == []


def test_enqueue_error_retains_pending_and_sanitizes(admission):
    jobs, inputs = admission

    def fail():
        raise RuntimeError("SECRET question token")

    client = QueueClient(fail)
    with pytest.raises(module().EvidenceDispatchError) as caught:
        asyncio.run(send(jobs, inputs, client))
    error = caught.value
    assert "SECRET" not in str(error) and error.__suppress_context__
    assert jobs.get(inputs["token"], inputs["workspace_id"], error.job_id).status == "pending"
    retry = asyncio.run(send(jobs, inputs, QueueClient()))
    assert retry.job_id == error.job_id
    with jobs.engine.connect() as conn:
        assert conn.scalar(text("SELECT reservation_count FROM research_budget_months")) == 1


def test_cancelled_enqueue_propagates_without_reset(admission):
    jobs, inputs = admission

    def cancel():
        raise asyncio.CancelledError()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(send(jobs, inputs, QueueClient(cancel)))
    retry = asyncio.run(send(jobs, inputs, QueueClient()))
    assert retry.status == "pending"


def test_cancel_during_thread_commit_has_no_hidden_enqueue(admission, monkeypatch):
    jobs, inputs = admission
    entered, release, committed = threading.Event(), threading.Event(), threading.Event()
    original = jobs.submit

    def delayed(*args, **kwargs):
        entered.set()
        release.wait(10)
        try:
            return original(*args, **kwargs)
        finally:
            committed.set()

    monkeypatch.setattr(jobs, "submit", delayed)
    client = QueueClient()

    async def run():
        task = asyncio.create_task(send(jobs, inputs, client))
        assert await asyncio.to_thread(entered.wait, 10)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        assert await asyncio.to_thread(committed.wait, 10)

    asyncio.run(run())
    assert client.calls == []
    retry = asyncio.run(send(jobs, inputs, client))
    assert retry.status == "pending" and len(client.calls) == 1


@pytest.mark.parametrize("mode", ["budget", "authority", "source-change"])
def test_current_rejections_do_not_enqueue(admission, mode):
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchBudgetExceeded, ResearchForbidden

    jobs, inputs = admission
    client = QueueClient()
    if mode == "budget":
        with jobs.engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO research_budget_months "
                    "(month, reserved_usd, reservation_count) "
                    "VALUES (to_char(clock_timestamp(),'YYYY-MM'),10,40)"
                )
            )
        expected = ResearchBudgetExceeded
    else:
        asyncio.run(send(jobs, inputs, client))
        client.calls.clear()
        with jobs.engine.begin() as conn:
            if mode == "authority":
                conn.execute(text("UPDATE auth_workspace_memberships SET role='viewer'"))
            else:
                conn.execute(
                    text(
                        "UPDATE parsed_representations SET payload = "
                        "jsonb_set(payload, '{text}', '\"changed\"'::jsonb)"
                    )
                )
        expected = ResearchForbidden if mode == "authority" else StorageCorruption
    with pytest.raises(expected):
        asyncio.run(send(jobs, inputs, client))
    assert client.calls == []


def test_permission_revoked_after_submit_blocks_queue(admission, monkeypatch):
    jobs, inputs = admission
    original = jobs.submit

    def revoke(*args, **kwargs):
        job = original(*args, **kwargs)
        with jobs.engine.begin() as conn:
            conn.execute(text("UPDATE auth_workspace_memberships SET active=false"))
        return job

    monkeypatch.setattr(jobs, "submit", revoke)
    client = QueueClient()
    assert asyncio.run(send(jobs, inputs, client)) is None
    assert client.calls == []


def test_storage_commit_ack_loss_retry_uses_saved_reservation(admission, monkeypatch):
    from issuedigest_storage.repository import StorageError

    jobs, inputs = admission
    original = jobs.submit

    def lost(*args, **kwargs):
        original(*args, **kwargs)
        raise StorageError("Synthetic SQL acknowledgement unavailable")

    monkeypatch.setattr(jobs, "submit", lost)
    client = QueueClient()
    with pytest.raises(StorageError):
        asyncio.run(send(jobs, inputs, client))
    assert client.calls == []
    monkeypatch.setattr(jobs, "submit", original)
    retry = asyncio.run(send(jobs, inputs, client))
    assert retry.status == "pending" and retry.queued
    with jobs.engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM evidence_jobs")) == 1
        assert conn.scalar(text("SELECT reservation_count FROM research_budget_months")) == 1


def test_recheck_observes_cancel_before_enqueue(admission, monkeypatch):
    jobs, inputs = admission
    original = jobs.submit

    def cancelled(*args, **kwargs):
        job = original(*args, **kwargs)
        jobs.cancel(inputs["token"], inputs["workspace_id"], job.job_id)
        return job

    monkeypatch.setattr(jobs, "submit", cancelled)
    client = QueueClient()
    dispatch = asyncio.run(send(jobs, inputs, client))
    assert dispatch.status == "cancelled" and not dispatch.queued
    assert client.calls == []
