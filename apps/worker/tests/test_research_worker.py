"""Real DBOS workflow with a synthetic model, no paid provider call."""

from uuid import uuid4

from dbos import DBOS
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchRequest
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from issuedigest_storage.research import ResearchRepository
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.models.test import TestModel

from conftest import bundle_data


def test_dbos_worker_persists_result_and_repeat_dispatch_does_not_rebill(engine, database_url):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repository = ResearchRepository(engine)
    run = repository.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="무슨 의미인가?", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role="issuedigest")
    output = {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "요약",
                "claims": [
                    {
                        "text": "합성 의미",
                        "citation_ids": [str(bundle.citations[0].citation_id)],
                        "event_date": None,
                    }
                ],
            }
        ],
    }
    run_worker(database_url, model=TestModel(custom_output_args=output), once=True)
    completed = repository.get_run(token, bundle.document.workspace_id, run.run_id)
    assert completed is not None and completed.status == "completed"
    assert completed.result is not None
    run_worker(database_url, model=TestModel(custom_output_args=output), once=True)
    reopened = repository.get_run(token, bundle.document.workspace_id, run.run_id)
    assert reopened == completed


def test_dbos_recovers_model_checkpoint_after_worker_crash(engine, database_url, tmp_path):
    """Kill the process after the durable model step and resume with a different model output."""
    import os
    import signal
    import subprocess
    import sys
    import time

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="해석?", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role="issuedigest")
    citation = str(bundle.citations[0].citation_id)
    first_output = {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "요약",
                "claims": [
                    {"text": "첫 모델의 해석", "citation_ids": [citation], "event_date": None}
                ],
            }
        ],
    }
    second_output = {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "요약",
                "claims": [
                    {
                        "text": "재호출됐다면 보일 해석",
                        "citation_ids": [citation],
                        "event_date": None,
                    }
                ],
            }
        ],
    }
    script = """import json, os, signal, sys
from issuedigest_storage.research import ResearchRepository
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.models.test import TestModel
original = ResearchRepository.worker_transition
if os.environ.get('CRASH_AFTER_MODEL') == '1':
    def crash(self, run_id, status, **kwargs):
        if status == 'validating': os.kill(os.getpid(), signal.SIGKILL)
        return original(self, run_id, status, **kwargs)
    ResearchRepository.worker_transition = crash
run_worker(
    os.environ['ISSUEDIGEST_TEST_DATABASE_URL'],
    model=TestModel(custom_output_args=json.loads(os.environ['SYNTHETIC_OUTPUT'])),
)
"""
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": __import__("json").dumps(first_output),
        "CRASH_AFTER_MODEL": "1",
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    first = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert first.wait(timeout=15) == -signal.SIGKILL
        midway = repo.get_run(token, bundle.document.workspace_id, run.run_id)
        assert midway is not None and midway.status == "generating"
        env["SYNTHETIC_OUTPUT"] = __import__("json").dumps(second_output)
        env.pop("CRASH_AFTER_MODEL")
        second = subprocess.Popen(
            [sys.executable, "-c", script],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                completed = repo.get_run(token, bundle.document.workspace_id, run.run_id)
                if completed is not None and completed.status in {"completed", "failed"}:
                    break
                time.sleep(0.1)
            assert completed is not None and completed.status == "completed"
            assert completed.result is not None
            assert completed.result.canvas.research.claims[0].text == "첫 모델의 해석"
        finally:
            second.terminate()
            second.wait(timeout=10)
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=5)


def test_worker_marks_uncitable_source_insufficient_without_model_request(engine, database_url):
    data = bundle_data()
    data["citations"] = []
    bundle = EvidenceBundle.model_validate(data)
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="질문?", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role="issuedigest")
    run_worker(database_url, model=TestModel(), once=True)
    final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert final is not None and final.status == "completed"
    assert (
        final.result is not None
        and final.result.canvas.revision.draft.outcome == "insufficient_evidence"
    )
    assert final.input_tokens == 0 and final.output_tokens == 0


def test_worker_redacts_invalid_source_and_finishes_run(engine, database_url):
    from issuedigest_storage.schema import evidence_snapshots
    from sqlalchemy import update

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    with engine.begin() as conn:
        conn.execute(
            update(evidence_snapshots)
            .where(evidence_snapshots.c.snapshot_id == snapshot)
            .values(payload={"bad": "private source"})
        )
    DBOS.migrate(database_url, application_role="issuedigest")
    run_worker(database_url, model=TestModel(), once=True)
    final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert (
        final is not None and final.status == "failed" and final.error_code == "generation_failed"
    )
