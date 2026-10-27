"""Borrowed native transport and real SQL call-intent integration."""

import asyncio
import importlib
import sys
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from sqlalchemy import text


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_modules():
    original_paths = sys.path.copy()
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages/agents/tests"))
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "packages/storage/tests"))
    packages = [
        importlib.import_module(name) for name in ("issuedigest_agents", "issuedigest_worker")
    ]
    existing = set(sys.modules)
    attributes = [vars(package).copy() for package in packages]
    yield
    for name in set(sys.modules) - existing:
        if name.startswith(("issuedigest_agents.", "issuedigest_worker.evidence_worker")):
            sys.modules.pop(name, None)
    sys.path[:] = original_paths
    for package, original in zip(packages, attributes, strict=True):
        for name in set(vars(package)) - original.keys():
            delattr(package, name)
        for name, value in original.items():
            setattr(package, name, value)


def native_body():
    import json

    from test_guarded_responses_stream import Body, events

    data = dict(
        propositions=[], coverage=dict(linked_proposition_ids=[], unresolved_reason="insufficient")
    )
    stream = events(json.dumps(data))
    for row in stream:
        for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if item is not None:
                item["name"] = "fill_question_evidence_v2"
    return Body(stream)


async def exercise(jobs, job, *, mutate=None, body=None, ownership=None):
    requests = []

    def serve(request):
        requests.append(request)
        if mutate:
            mutate()
        return httpx.Response(
            200, headers={"content-type": "text/event-stream"}, stream=body or native_body()
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
        client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
        worker = importlib.import_module("issuedigest_worker.evidence_worker")
        result = await worker.execute_evidence_job(
            jobs, job.job_id, client=client, check_ownership=ownership or (lambda _: True)
        )
        assert not client.is_closed()
        return result, requests


def submit(jobs, engine):
    token, workspace, snapshot = seed(engine)
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "합성 질문?",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".50"),
    )
    return job, token, workspace


def test_native_complete_and_replay(jobs, engine):
    job, token, workspace = submit(jobs, engine)
    result, requests = asyncio.run(exercise(jobs, job))
    assert result.status == "unreviewed"
    assert result.evidence.status == "unreviewed"
    assert len(requests) == 1
    replay, calls = asyncio.run(exercise(jobs, job))
    assert replay == result and calls == []
    assert jobs.get(token, workspace, job.job_id).status == "completed"


def test_committed_intent_never_reissues(jobs, engine):
    job, _, _ = submit(jobs, engine)
    jobs.claim(job.job_id, prompt_sha256="a" * 64, instructions_sha256="b" * 64)
    result, requests = asyncio.run(exercise(jobs, job))
    assert result is None and requests == []
    assert jobs.recover(job.job_id).status == "indeterminate"


def test_cancel_during_call_retains_usage(jobs, engine):
    job, token, workspace = submit(jobs, engine)
    result, requests = asyncio.run(
        exercise(jobs, job, mutate=lambda: jobs.cancel(token, workspace, job.job_id))
    )
    assert result is None and len(requests) == 1
    saved = jobs.get(token, workspace, job.job_id)
    assert saved.status == "cancelled" and saved.receipt is None
    assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)


def test_cached_receipt_rechecks_ownership(jobs, engine):
    job, _, _ = submit(jobs, engine)
    asyncio.run(exercise(jobs, job))
    with pytest.raises(importlib.import_module("issuedigest_storage.research").ResearchForbidden):
        asyncio.run(exercise(jobs, job, ownership=lambda _: False))


def test_actual_dbos_registration_and_checkpoint(jobs, engine, database_url):
    from dbos import DBOS, SetWorkflowID

    job, _, _ = submit(jobs, engine)
    requests = []
    owned = []

    def ownership(job_id):
        owned.append(job_id)
        return True

    async def run():
        def serve(request):
            requests.append(request)
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=native_body()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            DBOS.migrate(database_url, application_role=engine.url.username)
            DBOS(
                config={
                    "name": "durable-evidence-synthetic",
                    "system_database_url": database_url,
                    "application_version": "guarded-evidence-v1",
                    "run_admin_server": False,
                }
            )
            try:
                workflow = importlib.import_module(
                    "issuedigest_worker.evidence_worker"
                ).register_evidence_workflow(jobs, client=client, check_ownership=ownership)
                DBOS.launch()
                identifier = "guarded-evidence-" + str(job.job_id)
                with SetWorkflowID(identifier):
                    handle = await DBOS.start_workflow_async(workflow, str(job.job_id))
                assert await handle.get_result() is None
                with SetWorkflowID(identifier):
                    replay = await DBOS.start_workflow_async(workflow, str(job.job_id))
                assert await replay.get_result() is None
                assert len(requests) == 1 and len(owned) >= 4
                assert jobs.prepare(job.job_id)[0].status == "completed"
            finally:
                DBOS.destroy(destroy_registry=True)

    asyncio.run(run())


@pytest.mark.parametrize(
    "field,value",
    [
        ("known_usage", {"input_tokens": True, "output_tokens": 5, "requests": 1}),
        ("usage_complete", False),
        ("receipt_sha256", "f" * 64),
    ],
)
def test_corrupt_completion_rejected(jobs, engine, field, value):
    from issuedigest_storage.evidence_jobs import evidence_jobs
    from sqlalchemy import update

    job, _, _ = submit(jobs, engine)
    asyncio.run(exercise(jobs, job))
    with engine.begin() as conn:
        conn.execute(
            update(evidence_jobs)
            .where(evidence_jobs.c.job_id == job.job_id)
            .values(**{field: value})
        )
    from issuedigest_storage.repository import StorageCorruption

    with pytest.raises((ValueError, StorageCorruption)):
        asyncio.run(exercise(jobs, job))


@pytest.mark.parametrize("mutation", ["revoke", "title", "delete", "source"])
def test_mutation_during_native_call_blocks_result_preserves_usage(jobs, engine, mutation):
    from issuedigest_storage.repository import StorageCorruption
    from issuedigest_storage.research import ResearchConflict, ResearchForbidden, ResearchRepository
    from issuedigest_storage.schema import evidence_snapshots
    from sqlalchemy import delete

    job, _, workspace = submit(jobs, engine)
    _, source = jobs.prepare(job.job_id)

    def mutate():
        if mutation == "revoke":
            with engine.begin() as conn:
                conn.execute(text("UPDATE auth_workspace_memberships SET active=false"))
        elif mutation == "source":
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE parsed_representations SET payload = "
                        "jsonb_set(payload, '{text}', '\"changed\"'::jsonb)"
                    )
                )
        elif mutation == "title":
            ResearchRepository(engine).upsert_presentation(
                source[2].model_copy(update={"title": "changed"})
            )
        else:
            with engine.begin() as conn:
                conn.execute(
                    text("DELETE FROM outbox WHERE snapshot_id=:sid"), {"sid": job.snapshot_id}
                )
                conn.execute(
                    text("DELETE FROM snapshot_citations WHERE snapshot_id=:sid"),
                    {"sid": job.snapshot_id},
                )
                conn.execute(
                    delete(evidence_snapshots).where(
                        evidence_snapshots.c.snapshot_id == job.snapshot_id
                    )
                )

    with pytest.raises((ResearchForbidden, ResearchConflict, StorageCorruption)):
        asyncio.run(exercise(jobs, job, mutate=mutate))
    with engine.connect() as conn:
        saved = conn.execute(text("SELECT status,receipt,known_usage FROM evidence_jobs")).one()
        assert saved.status == "failed" and saved.receipt is None
        assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)


def test_completion_commit_ack_loss_keeps_winning_result(jobs, engine, monkeypatch):
    job, _, _ = submit(jobs, engine)
    finish = jobs.finish
    lost = False

    def commit_then_raise(*args, **kwargs):
        nonlocal lost
        result = finish(*args, **kwargs)
        if kwargs.get("receipt") is not None and not lost:
            lost = True
            raise RuntimeError("synthetic lost commit acknowledgement")
        return result

    monkeypatch.setattr(jobs, "finish", commit_then_raise)
    result, requests = asyncio.run(exercise(jobs, job))
    assert result.status == "unreviewed" and len(requests) == 1
    assert jobs.prepare(job.job_id)[0].status == "completed"


def test_native_cancellation_persists_observations(jobs, engine):
    from test_guarded_responses_stream import Body

    job, _, _ = submit(jobs, engine)

    async def run():
        body = Body([], wait=True)
        task = asyncio.create_task(exercise(jobs, job, body=body))
        await body.blocked.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return body

    body = asyncio.run(run())
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "cancelled" and saved.known_usage is None
    assert saved.stream_closed is True and body.closed


@pytest.fixture
def jobs(engine):
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE evidence_jobs"))
    yield EvidenceJobRepository(engine)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE evidence_jobs"))


def seed(engine):
    from test_evidence_jobs import seed as make_seed

    return make_seed(engine)


def test_worker_exists():
    name = "issuedigest_worker.evidence_worker"
    assert importlib.util.find_spec(name) is not None, "Missing durable evidence worker"
    assert importlib.import_module(name).execute_evidence_job


@pytest.mark.parametrize(
    "mode,reason,known,complete",
    [
        ("invalid", "output", True, True),
        ("overcap", "usage", True, True),
        ("transport", "transport", False, False),
        ("whitespace", "whitespace", False, False),
    ],
)
def test_native_terminal_observations(jobs, engine, mode, reason, known, complete):
    from issuedigest_agents.guarded_responses_stream import GuardedResponsesError
    from test_guarded_responses_stream import Body, events

    job, _, _ = submit(jobs, engine)
    body = native_body()
    if mode == "invalid":
        body = native_body()
        # A terminal syntactically valid call with an invalid schema cannot become evidence.
        for row in body.rows:
            if "arguments" in row:
                row["arguments"] = "{}"
            if row.get("item", {}).get("status") == "completed":
                row["item"]["arguments"] = "{}"
            for item in row.get("response", {}).get("output", []):
                item["arguments"] = "{}"
            if "delta" in row:
                row["delta"] = "{}"
    elif mode == "overcap":
        body.rows[-1]["response"]["usage"] = dict(
            input_tokens=20001, output_tokens=5, total_tokens=20006
        )
    elif mode == "transport":
        body = Body([], read_error=True)
    elif mode == "whitespace":
        body = Body(events(" " * 100000))
        for row in body.rows:
            if row.get("item"):
                row["item"]["name"] = "fill_question_evidence_v2"
            for item in row.get("response", {}).get("output", []):
                item["name"] = "fill_question_evidence_v2"
    with pytest.raises(GuardedResponsesError) as got:
        asyncio.run(exercise(jobs, job, body=body))
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "failed" and saved.receipt is None
    assert saved.reason == got.value.reason == reason
    assert (saved.known_usage is not None) == known
    assert saved.usage_complete == complete and saved.stream_closed is True
    if mode == "overcap":
        assert saved.known_usage["input_tokens"] == 20001


def test_imports_do_no_database_network_or_model_work():
    import subprocess

    script = """
import socket, sqlalchemy, openai
from dbos import DBOS
def forbidden(*args,**kwargs):
    raise AssertionError('Import performed work')
socket.socket.connect=forbidden
sqlalchemy.create_engine=forbidden
openai.AsyncOpenAI.__init__=forbidden
DBOS.__init__=forbidden
import issuedigest_storage.evidence_jobs
import issuedigest_worker.evidence_worker
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_receipt_semantics_rechecked_even_with_recomputed_hash(jobs, engine):
    from issuedigest_agents.guarded_responses_stream import GuardedResponsesError
    from issuedigest_storage.evidence_jobs import digest, evidence_jobs
    from sqlalchemy import select, update

    job, _, _ = submit(jobs, engine)
    asyncio.run(exercise(jobs, job))
    with engine.begin() as conn:
        receipt = conn.scalar(
            select(evidence_jobs.c.receipt).where(evidence_jobs.c.job_id == job.job_id)
        )
        receipt["evidence"]["question_sha256"] = "f" * 64
        conn.execute(
            update(evidence_jobs)
            .where(evidence_jobs.c.job_id == job.job_id)
            .values(receipt=receipt, receipt_sha256=digest(receipt))
        )
    with pytest.raises(GuardedResponsesError):
        asyncio.run(exercise(jobs, job))


def test_actual_dbos_cached_step_rechecks_current_authority(
    jobs, engine, database_url, monkeypatch
):
    from dbos import DBOS, SetWorkflowID
    from issuedigest_storage.research import ResearchForbidden

    worker = importlib.import_module("issuedigest_worker.evidence_worker")
    job, _, _ = submit(jobs, engine)
    requests = []
    reads = 0
    original = worker.read_completed_evidence_job

    def crash_after_checkpoint(*args, **kwargs):
        nonlocal reads
        reads += 1
        if reads == 2:
            raise asyncio.CancelledError("synthetic workflow interruption after committed step")
        return original(*args, **kwargs)

    monkeypatch.setattr(worker, "read_completed_evidence_job", crash_after_checkpoint)

    async def run():
        def serve(request):
            requests.append(request)
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, stream=native_body()
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            DBOS.migrate(database_url, application_role=engine.url.username)
            DBOS(
                config={
                    "name": "durable-evidence-synthetic",
                    "system_database_url": database_url,
                    "application_version": "guarded-evidence-v1",
                    "run_admin_server": False,
                }
            )
            try:
                workflow = worker.register_evidence_workflow(
                    jobs, client=client, check_ownership=lambda _: True
                )
                DBOS.launch()
                identifier = "guarded-evidence-" + str(job.job_id)
                with SetWorkflowID(identifier):
                    handle = await DBOS.start_workflow_async(workflow, str(job.job_id))
                with pytest.raises(asyncio.CancelledError):
                    await handle.get_result()
                steps = await DBOS.list_workflow_steps_async(identifier)
                assert (
                    len(steps) == 1
                    and steps[0]["function_name"] == "issuedigest_guarded_evidence_call_v1"
                )
                assert steps[0]["output"] is None
                monkeypatch.setattr(worker, "read_completed_evidence_job", original)
                with engine.begin() as conn:
                    conn.execute(text("UPDATE auth_workspace_memberships SET active=false"))
                replay = await DBOS.resume_workflow_async(identifier)
                with pytest.raises(ResearchForbidden):
                    await replay.get_result()
                assert len(requests) == 1
            finally:
                DBOS.destroy(destroy_registry=True)

    asyncio.run(run())


def test_lost_claim_acknowledgement_blocks_all_native_calls(jobs, engine, monkeypatch):
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository

    job, _, _ = submit(jobs, engine)
    claim = jobs.claim

    def commit_then_raise(*args, **kwargs):
        assert claim(*args, **kwargs)
        raise RuntimeError("synthetic claim acknowledgement loss")

    monkeypatch.setattr(jobs, "claim", commit_then_raise)
    with pytest.raises(RuntimeError, match="acknowledgement loss"):
        asyncio.run(exercise(jobs, job))
    restarted = EvidenceJobRepository(engine)
    result, requests = asyncio.run(exercise(restarted, job))
    assert result is None and requests == []
    assert restarted.prepare(job.job_id)[0].status == "indeterminate"


def test_observation_storage_failure_surfaces_without_reissuing(jobs, engine, monkeypatch):
    from issuedigest_storage.evidence_jobs import EvidenceJobRepository
    from issuedigest_storage.repository import StorageError

    job, _, _ = submit(jobs, engine)
    body = native_body()

    def unavailable(*args, **kwargs):
        raise StorageError("Synthetic observation storage unavailable")

    monkeypatch.setattr(jobs, "finish", unavailable)
    with pytest.raises(StorageError):
        asyncio.run(exercise(jobs, job, body=body))
    assert body.closed
    restarted = EvidenceJobRepository(engine)
    assert restarted.prepare(job.job_id)[0].status == "running"
    result, requests = asyncio.run(exercise(restarted, job))
    assert result is None and requests == []
    assert restarted.prepare(job.job_id)[0].status == "indeterminate"


def test_preflight_failure_is_terminal_without_a_native_call(jobs, engine):
    from hashlib import sha256

    from issuedigest_domain import EvidenceBundle
    from issuedigest_storage import EvidenceRepository

    from conftest import bundle_data

    token, workspace, _ = seed(engine)
    data = bundle_data()
    data["document"]["workspace_id"] = str(workspace)
    data["representation"]["text"] = "x" * 100000
    data["representation"]["text_sha256"] = sha256(
        data["representation"]["text"].encode()
    ).hexdigest()
    data["citations"] = data["citations"][:1]
    data["citations"][0]["selector"] = dict(
        kind="text", start=0, end=100000, quote=data["representation"]["text"]
    )
    snapshot = uuid4()
    EvidenceRepository(engine).save(snapshot, EvidenceBundle.model_validate(data))
    job = jobs.submit(
        token,
        workspace,
        uuid4(),
        snapshot,
        "q",
        model="gpt-6.1-sol",
        reservation_usd=Decimal(".25"),
    )
    with pytest.raises(ValueError):
        asyncio.run(exercise(jobs, job))
    saved = jobs.prepare(job.job_id)[0]
    assert saved.status == "failed" and saved.known_usage is None and saved.reason == "input"


@pytest.mark.parametrize(
    "stage,want",
    [
        ("dto_schema", "dto_schema"),
        (None, "unavailable"),
        ("private secret body", "unavailable"),
        ([], "unavailable"),
    ],
)
@pytest.mark.parametrize("broken_handler", [False, True])
def test_rejection_logs_only_stage_and_handler_failure_preserves_sql(
    jobs, engine, monkeypatch, caplog, stage, want, broken_handler
):
    import logging

    from issuedigest_agents.guarded_responses_stream import GuardedResponsesError
    from issuedigest_agents.numeric_evidence import KnownUsage

    worker = importlib.import_module("issuedigest_worker.evidence_worker")
    job, _, _ = submit(jobs, engine)
    error = GuardedResponsesError(
        reason="output",
        known_usage=KnownUsage(input_tokens=10, output_tokens=5, requests=1),
        may_have_started=True,
        usage_complete=True,
        stream_closed=True,
    )
    error._diagnostic_stage = stage

    async def reject(**kwargs):
        raise error from ValueError("private secret body api-key question source output")

    class Broken(logging.Handler):
        def emit(self, record):
            raise RuntimeError("private secret handler detail")

    monkeypatch.setattr(worker, "run_guarded_question_evidence_v2", reject)
    logger = logging.getLogger(worker.__name__)
    handler = Broken()
    if broken_handler:
        logger.addHandler(handler)
    try:
        with caplog.at_level(logging.WARNING, logger=worker.__name__):
            with pytest.raises(GuardedResponsesError) as got:
                asyncio.run(exercise(jobs, job))
        assert got.value is error
        saved = jobs.prepare(job.job_id)[0]
        assert saved.status == "failed" and saved.reason == "output" and saved.receipt is None
        assert saved.known_usage == dict(input_tokens=10, output_tokens=5, requests=1)
        assert saved.usage_complete is True and saved.stream_closed is True
        assert "private" not in caplog.text and str(job.job_id) not in caplog.text
        if not broken_handler:
            (record,) = [r for r in caplog.records if r.name == worker.__name__]
            assert record.getMessage() == f"evidence_generation_rejected stage={want}"
            assert f"stage={want}" in caplog.text
            assert record.diagnostic_stage == want
            assert record.exc_info is None and record.exc_text is None and record.args == (want,)
    finally:
        if broken_handler:
            logger.removeHandler(handler)
