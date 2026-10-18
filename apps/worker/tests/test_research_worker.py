"""Real DBOS workflow with a synthetic model, no paid provider call."""

from uuid import uuid4

import pytest
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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repository = ResearchRepository(engine)
    run = repository.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role=engine.url.username)
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
                        "category": "documented",
                        "rationale": "선택한 인용의 합성 평가",
                    }
                ],
            }
        ],
    }
    run_worker(database_url, model=TestModel(custom_output_args=output), once=True)
    completed = repository.get_run(token, bundle.document.workspace_id, run.run_id)
    assert completed is not None and completed.status == "completed"
    assert completed.result is not None
    assert completed.result.canvas.research.claims[0].derivation.method_version == "research-v4"
    assert len(completed.result.canvas.research.support_reviews) == 1
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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role=engine.url.username)
    citation = str(bundle.citations[0].citation_id)
    first_output = {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "요약",
                "claims": [
                    {
                        "text": "첫 모델의 해석",
                        "citation_ids": [citation],
                        "event_date": None,
                        "category": "documented",
                        "rationale": "선택한 인용의 합성 평가",
                    }
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
                        "category": "documented",
                        "rationale": "선택한 인용의 합성 평가",
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
        assert midway.snapshot_ids == (snapshot,)
        added = bundle_data()
        added["document"]["workspace_id"] = str(bundle.document.workspace_id)
        new_snapshot = uuid4()
        EvidenceRepository(engine).save(new_snapshot, EvidenceBundle.model_validate(added))
        with engine.begin() as conn:
            from issuedigest_storage.search import rebuild_projection

            rebuild_projection(conn, bundle.document.workspace_id, new_snapshot)
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
            assert completed.snapshot_ids == (snapshot,)
            assert len(completed.result.canvas.research.evidence) == 1
            assert [event.status for event in completed.events] == [
                "queued",
                "retrieving",
                "generating",
                "validating",
                "completed",
            ]
        finally:
            second.terminate()
            second.wait(timeout=10)
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=5)


def test_terminal_storage_outage_recovers_without_recalling_model(engine, database_url, tmp_path):
    import json
    import os
    import signal
    import subprocess
    import sys
    import time

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role=engine.url.username)
    citation = str(bundle.citations[0].citation_id)

    def output(text):
        return {
            "outcome": "answer",
            "message": None,
            "modules": [
                {
                    "kind": "summary",
                    "title": "요약",
                    "claims": [
                        {
                            "text": text,
                            "citation_ids": [citation],
                            "event_date": None,
                            "category": "documented",
                            "rationale": "선택한 인용의 합성 평가",
                        }
                    ],
                }
            ],
        }

    script = """import json, os
from pathlib import Path
from issuedigest_storage.research import ResearchRepository
from issuedigest_storage import StorageError
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.models.test import TestModel
original = ResearchRepository.worker_transition
if os.environ.get('FAIL_TERMINAL') == '1':
    def fail(self, run_id, status, **kwargs):
        if status in {'completed', 'failed'}:
            Path(os.environ['FAULT_MARKER']).write_text('terminal write attempted')
            raise StorageError('synthetic private DB fault')
        return original(self, run_id, status, **kwargs)
    ResearchRepository.worker_transition = fail
run_worker(
    os.environ['ISSUEDIGEST_TEST_DATABASE_URL'],
    model=TestModel(custom_output_args=json.loads(os.environ['SYNTHETIC_OUTPUT'])),
    poll_seconds=0.1,
)
"""
    marker = tmp_path / "terminal-attempted"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(output("첫 모델의 해석")),
        "FAIL_TERMINAL": "1",
        "FAULT_MARKER": str(marker),
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    first = subprocess.Popen(
        [sys.executable, "-c", script],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 15
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists() and first.poll() is None
        active = repo.get_run(token, bundle.document.workspace_id, run.run_id)
        assert active is not None and active.status == "validating"
        first.send_signal(signal.SIGKILL)
        assert first.wait(timeout=10) == -signal.SIGKILL
        env.pop("FAIL_TERMINAL")
        env["SYNTHETIC_OUTPUT"] = json.dumps(output("재호출됐다면 보일 해석"))
        second = subprocess.Popen(
            [sys.executable, "-c", script],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
                if final is not None and final.status in {"completed", "failed"}:
                    break
                time.sleep(0.1)
            assert final is not None and final.status == "completed"
            assert final.result is not None
            assert final.result.canvas.research.claims[0].text == "첫 모델의 해석"
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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    assert run is not None
    DBOS.migrate(database_url, application_role=engine.url.username)
    run_worker(database_url, model=TestModel(), once=True)
    final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert final is not None and final.status == "failed"
    assert final.error_code == "insufficient_evidence" and final.result is None
    assert final.input_tokens == 0 and final.output_tokens == 0


def test_worker_redacts_invalid_source_and_finishes_run(engine, database_url):
    from issuedigest_storage.schema import evidence_snapshots
    from sqlalchemy import update

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    assert run is not None
    with engine.begin() as conn:
        conn.execute(
            update(evidence_snapshots)
            .where(evidence_snapshots.c.snapshot_id == snapshot)
            .values(payload={"bad": "private source"})
        )
    DBOS.migrate(database_url, application_role=engine.url.username)
    run_worker(database_url, model=TestModel(), once=True)
    final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert (
        final is not None and final.status == "failed" and final.error_code == "generation_failed"
    )


def test_validation_failure_retains_known_model_usage(monkeypatch):
    """A paid response is counted even when its canvas fails validation afterward."""
    from contextlib import nullcontext
    from types import SimpleNamespace

    import issuedigest_worker.research_worker as worker

    run_id, workspace_id, snapshot_id = uuid4(), uuid4(), uuid4()
    transitions = []

    class Repository:
        def __init__(self, _engine):
            pass

        def worker_states(self, _ids):
            return {}

        def worker_active_runs(self, _after):
            return ()

        def queued_ids(self):
            return (run_id,)

        def worker_load(self, _run_id):
            return (
                SimpleNamespace(
                    question="합성 질문",
                    status="queued",
                    workspace_id=workspace_id,
                    snapshot_ids=(snapshot_id,),
                ),
                (),
            )

        def worker_parent_context(self, _run_id):
            return None

        def worker_transition(self, _run_id, status, **kwargs):
            transitions.append((status, kwargs))
            return True

    class FakeDBOS:
        def __init__(self, *, config):
            pass

        @staticmethod
        def workflow(**kwargs):
            return lambda function: function

        @staticmethod
        def get_workflow_status(_workflow_id):
            return None

        @staticmethod
        def launch():
            pass

        @staticmethod
        def start_workflow(function, *args):
            function(*args)
            return SimpleNamespace(get_result=lambda: None)

        @staticmethod
        def destroy(**kwargs):
            pass

    def fail_validation(*args):
        raise ValueError("synthetic invalid citation")

    monkeypatch.setattr(worker, "research_worker_lock", lambda _engine: nullcontext(lambda: None))
    monkeypatch.setattr(worker, "ResearchRepository", Repository)
    monkeypatch.setattr(
        worker, "create_storage_engine", lambda _url: SimpleNamespace(dispose=lambda: None)
    )
    monkeypatch.setattr(worker, "create_agent", lambda _model: object())
    monkeypatch.setattr(worker, "create_agent_v3", lambda _model: object())
    monkeypatch.setattr(worker, "create_agent_v4", lambda _model: object())
    monkeypatch.setattr(
        worker,
        "DBOSClient",
        lambda **kwargs: SimpleNamespace(
            list_workflows=lambda **kwargs: [],
            destroy=lambda: None,
        ),
    )
    monkeypatch.setattr(worker, "DBOS", FakeDBOS)
    monkeypatch.setattr(worker, "SetWorkflowID", lambda _value: nullcontext())
    monkeypatch.setattr(worker, "model_prompt_v4", lambda *args, **kwargs: "{}")
    monkeypatch.setattr(
        worker,
        "run_agent_v4",
        lambda _agent, _prompt: (object(), 123, 45),
    )
    monkeypatch.setattr(worker, "build_canvas_v4", fail_validation)

    run_worker(
        "postgresql+psycopg://synthetic@127.0.0.1/issuedigest_test", model=object(), once=True
    )

    status, fields = transitions[-1]
    assert status == "failed"
    assert fields["error_code"] == "generation_failed"
    assert (fields["input_tokens"], fields["output_tokens"]) == (123, 45)


def test_worker_nohit_never_calls_model_and_keeps_conservative_reservation(engine, database_url):
    from issuedigest_storage.research_schema import research_budget_months
    from pydantic_ai.models.function import FunctionModel
    from sqlalchemy import select

    data = bundle_data()
    bundle = EvidenceBundle.model_validate(data)
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="양자컴퓨터는?"),
    )
    calls = []

    def forbidden_provider(messages, info):
        calls.append(messages)
        raise AssertionError("no evidence must never reach provider")

    DBOS.migrate(database_url, application_role=engine.url.username)
    run_worker(database_url, model=FunctionModel(forbidden_provider), once=True)
    final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert final.status == "failed" and final.error_code == "insufficient_evidence"
    assert final.snapshot_ids == () and final.result is None and calls == []
    assert final.input_tokens == 0 and final.output_tokens == 0
    assert (
        repo.submit(
            token,
            bundle.document.workspace_id,
            ResearchRequest(request_id=run.request_id, question=run.question),
        )
        == final
    )
    with engine.connect() as conn:
        budget = conn.execute(select(research_budget_months)).one()
    assert budget.reservation_count == 1 and str(budget.reserved_usd) == "0.25"


def test_corrupt_publication_is_terminal_and_never_retries_the_model(
    engine, database_url, monkeypatch
):
    from issuedigest_storage import StorageCorruption

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
    )
    original = ResearchRepository.worker_transition
    injected = False

    def corrupt_once(self, run_id, status, **fields):
        nonlocal injected
        if status == "completed" and not injected:
            injected = True
            raise StorageCorruption("synthetic immutable evidence integrity failure")
        return original(self, run_id, status, **fields)

    monkeypatch.setattr(ResearchRepository, "worker_transition", corrupt_once)
    output = {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "해석",
                "claims": [
                    {
                        "text": "합성 의미",
                        "citation_ids": [str(bundle.citations[0].citation_id)],
                        "event_date": None,
                        "category": "documented",
                        "rationale": "선택한 인용의 합성 평가",
                    }
                ],
            }
        ],
    }
    DBOS.migrate(database_url, application_role=engine.url.username)
    run_worker(database_url, model=TestModel(custom_output_args=output), once=True)
    final = repo.get_run(token, bundle.document.workspace_id, run.run_id)
    assert final.status == "failed" and final.error_code == "generation_failed"
    assert final.result is None and final.input_tokens > 0


@pytest.mark.parametrize(
    "question", ["日本について 설명해줘", "💰 설명해줘", "$ 설명해줘", "+ 설명해줘"]
)
def test_explicit_unknown_topic_with_parent_never_reaches_provider(engine, database_url, question):
    from issuedigest_agents.research import AIOutput, build_canvas
    from issuedigest_domain.research_journey import ResearchResult
    from issuedigest_storage.search import rebuild_projection
    from pydantic_ai.models.function import FunctionModel

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    workspace = bundle.document.workspace_id
    parent = repo.submit(
        token, workspace, ResearchRequest(request_id=uuid4(), question="80% 의미는?")
    )
    loaded = repo.worker_load(parent.run_id)
    output = AIOutput(outcome="insufficient_evidence", message="합성 불충분", modules=())
    result = ResearchResult(
        canvas=build_canvas(parent.run_id, workspace, loaded[1], output),
        source_titles={bundle.document.document_id: "합성 자료"},
    )
    repo.worker_transition(parent.run_id, "completed", result=result)
    child = repo.submit(
        token,
        workspace,
        ResearchRequest(request_id=uuid4(), question=question, parent_run_id=parent.run_id),
    )
    calls = []

    def forbidden_provider(messages, info):
        calls.append(messages)
        raise AssertionError("explicit unknown topic must not use parent's evidence")

    DBOS.migrate(database_url, application_role=engine.url.username)
    run_worker(database_url, model=FunctionModel(forbidden_provider), once=True)
    final = repo.get_run(token, workspace, child.run_id)
    assert final.status == "failed" and final.error_code == "insufficient_evidence"
    assert final.snapshot_ids == () and final.result is None
    assert final.input_tokens == 0 and final.output_tokens == 0 and calls == []
