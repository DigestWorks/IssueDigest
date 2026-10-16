"""Cross-registry recovery uses only the dedicated synthetic PostgreSQL database."""

import json
import os
import signal
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from dbos import DBOS, DBOSClient
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchRequest
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from issuedigest_storage.research import ResearchRepository
from issuedigest_storage.research_schema import research_budget_months
from issuedigest_storage.search import rebuild_projection
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.models.test import TestModel
from sqlalchemy import select

from conftest import bundle_data


def seed(engine, database_url):
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
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(
            request_id=uuid4(),
            question="80% 의미는?",
        ),
    )
    DBOS.migrate(database_url, application_role=engine.url.username)
    return bundle, token, repo, run


def output(bundle, text="첫 모델의 해석", classified=False):
    claim = {
        "text": text,
        "citation_ids": [str(bundle.citations[0].citation_id)],
        "event_date": None,
    }
    if classified:
        claim.update(category="documented", rationale="선택 인용의 합성 설명")
    return {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "합성 요약",
                "claims": [claim],
            }
        ],
    }


CRASH_SCRIPT = """import importlib.util, json, os, signal
from issuedigest_storage.research import ResearchRepository
from pydantic_ai.models.test import TestModel
if os.environ.get('LEGACY_WORKER'):
    spec = importlib.util.spec_from_file_location('frozen_v2', os.environ['LEGACY_WORKER'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_worker = module.run_worker
else:
    from issuedigest_worker.research_worker import run_worker
class CountedModel(TestModel):
    async def request(self, *args, **kwargs):
        with open(os.environ['CALL_MARKER'], 'a') as marker: marker.write('called\\n')
        if os.environ.get('CRASH_INSIDE_MODEL') == '1': os.kill(os.getpid(), signal.SIGKILL)
        if os.environ.get('WAIT_RELEASE'):
            import asyncio
            from pathlib import Path
            while not Path(os.environ['WAIT_RELEASE']).exists(): await asyncio.sleep(0.05)
        return await super().request(*args, **kwargs)
original = ResearchRepository.worker_transition
def crash(self, run_id, status, **kwargs):
    if status == 'validating': os.kill(os.getpid(), signal.SIGKILL)
    return original(self, run_id, status, **kwargs)
if os.environ.get('CRASH_AFTER_MODEL') == '1': ResearchRepository.worker_transition = crash
run_worker(os.environ['ISSUEDIGEST_TEST_DATABASE_URL'],
    model=CountedModel(custom_output_args=json.loads(os.environ['SYNTHETIC_OUTPUT'])), once=True)
"""


def crash_worker(database_url, tmp_path, proposal, *, legacy=True, checkpoint=True):
    marker = tmp_path / "synthetic-provider-calls"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(proposal),
        "CALL_MARKER": str(marker),
        "PYDANTIC_AI_NO_BANNER": "1",
        "CRASH_AFTER_MODEL" if checkpoint else "CRASH_INSIDE_MODEL": "1",
    }
    if legacy:
        env["LEGACY_WORKER"] = str(Path(__file__).parent / "fixtures/research_worker_v2.py")
    proc = subprocess.run(
        [sys.executable, "-c", CRASH_SCRIPT], env=env, capture_output=True, timeout=20
    )
    assert proc.returncode == -signal.SIGKILL, proc.stderr.decode()[-1000:]
    assert marker.read_text() == "called\n"
    return marker


def client(database_url):
    return DBOSClient(system_database_url=database_url, application_name="issuedigest-research")


def test_real_legacy_v2_checkpoint_recovers_under_recorded_version_then_new_requests_use_v3(
    engine,
    database_url,
    tmp_path,
):
    bundle, token, repo, old = seed(engine, database_url)
    marker = crash_worker(database_url, tmp_path, output(bundle))
    inspector = client(database_url)
    try:
        before = inspector.list_workflows(
            workflow_ids=[f"research-{old.run_id}"], load_input=False, load_output=False
        )[0]
        checkpoints = inspector.list_workflow_steps(before.workflow_id, load_output=False)
        assert [(step["function_id"], step["function_name"]) for step in checkpoints] == [
            (1, "issuedigest_research_v2__model.request"),
        ]
        assert checkpoints[0]["completed_at_epoch_ms"] is not None
        assert repo.get_run(token, old.workspace_id, old.run_id).status == "generating"
        new_bundle, new_token, _, new = seed(engine, database_url)
        new_marker = tmp_path / "new-provider-calls"
        current_env = {
            **os.environ,
            "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
            "SYNTHETIC_OUTPUT": json.dumps(output(new_bundle, "새 해석", True)),
            "CALL_MARKER": str(new_marker),
            "DBOS__APPVERSION": "synthetic-current-worker-version",
            "PYDANTIC_AI_NO_BANNER": "1",
        }
        current_process = subprocess.run(
            [sys.executable, "-c", CRASH_SCRIPT], env=current_env, capture_output=True, timeout=15
        )
        assert current_process.returncode == 0, current_process.stderr.decode()[-1000:]
        assert new_marker.read_text() == "called\n"
        recovered = repo.get_run(token, old.workspace_id, old.run_id)
        assert recovered.status == "completed"
        assert recovered.result.canvas.research.claims[0].text == "첫 모델의 해석"
        assert recovered.result.canvas.research.claims[0].derivation.method_version == "research-v2"
        assert recovered.result.canvas.research.support_reviews == ()
        current = repo.get_run(new_token, new.workspace_id, new.run_id)
        assert current.status == "completed"
        assert current.result.canvas.research.claims[0].derivation.method_version == "research-v3"
        assert len(current.result.canvas.research.support_reviews) == 1
        after = inspector.list_workflows(
            workflow_ids=[before.workflow_id, f"research-{new.run_id}"],
            load_input=False,
            load_output=False,
        )
        by_name = {workflow.name: workflow for workflow in after}
        assert by_name["issuedigest_research_run_v2"].app_version == before.app_version
        assert by_name["issuedigest_research_run_v3"].app_version != before.app_version
        assert inspector.list_workflow_steps(before.workflow_id, load_output=False) == checkpoints
        assert marker.read_text() == "called\n"
        # Another full registry destroy/relaunch must only read completed application rows.
        run_worker(
            database_url,
            model=TestModel(custom_output_args=output(bundle, "재호출 금지", True)),
            once=True,
        )
        assert repo.get_run(token, old.workspace_id, old.run_id) == recovered
    finally:
        inspector.destroy()


@pytest.mark.parametrize("legacy", [True, False])
def test_inflight_model_crash_fails_without_recalling_and_keeps_reservation(
    engine,
    database_url,
    tmp_path,
    legacy,
):
    from pydantic_ai.models.function import FunctionModel

    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_worker(
        database_url,
        tmp_path,
        output(bundle, classified=not legacy),
        legacy=legacy,
        checkpoint=False,
    )
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("ambiguous model request must never be repeated")

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    failed = repo.get_run(token, run.workspace_id, run.run_id)
    assert failed.status == "failed" and failed.error_code == "generation_failed"
    assert failed.result is None and calls == [] and marker.read_text() == "called\n"
    with engine.connect() as conn:
        budget = conn.execute(select(research_budget_months)).one()
    assert budget.reservation_count == 1 and str(budget.reserved_usd) == "0.25"
    inspector = client(database_url)
    try:
        workflow = inspector.list_workflows(
            workflow_ids=[f"research-{run.run_id}"], load_input=False, load_output=False
        )[0]
        assert workflow.status == "CANCELLED"
        assert inspector.list_workflow_steps(workflow.workflow_id, load_output=False) == []
    finally:
        inspector.destroy()


@pytest.mark.parametrize("name", ["issuedigest_research_run_v2", "issuedigest_research_run_v3"])
def test_existing_queued_workflow_dispatches_registered_original_name(engine, database_url, name):
    bundle, token, repo, run = seed(engine, database_url)
    inspector = client(database_url)
    try:
        inspector.enqueue(
            {
                "workflow_name": name,
                "queue_name": "_dbos_internal_queue",
                "workflow_id": f"research-{run.run_id}",
                "app_version": "synthetic-queued-cohort",
            },
            str(run.run_id),
        )
        run_worker(
            database_url,
            model=TestModel(custom_output_args=output(bundle, classified=name.endswith("v3"))),
            once=True,
        )
        completed = repo.get_run(token, run.workspace_id, run.run_id)
        assert completed.status == "completed"
        assert completed.result.canvas.research.claims[0].derivation.method_version == name.replace(
            "issuedigest_research_run_", "research-"
        )
        assert inspector.retrieve_workflow(f"research-{run.run_id}").get_status().name == name
    finally:
        inspector.destroy()


@pytest.mark.parametrize(
    "case", ["unknown-name", "cancelled-workflow", "cancelled-run", "revoked-membership"]
)
def test_recovery_never_calls_model_for_unknown_cancelled_or_unauthorized_run(
    engine,
    database_url,
    tmp_path,
    case,
):
    from pydantic_ai.models.function import FunctionModel

    bundle, token, repo, run = seed(engine, database_url)
    inspector = client(database_url)
    try:
        if case == "revoked-membership":
            # A real paid checkpoint exists; reloading still checks current authorization.
            crash_worker(database_url, tmp_path, output(bundle))
            from issuedigest_storage.auth_schema import auth_workspace_memberships
            from sqlalchemy import delete

            with engine.begin() as conn:
                conn.execute(
                    delete(auth_workspace_memberships).where(
                        auth_workspace_memberships.c.workspace_id == run.workspace_id
                    )
                )
        else:
            name = (
                "unknown-synthetic-name"
                if case == "unknown-name"
                else "issuedigest_research_run_v2"
            )
            inspector.enqueue(
                {
                    "workflow_name": name,
                    "queue_name": "_dbos_internal_queue",
                    "workflow_id": f"research-{run.run_id}",
                    "app_version": "synthetic-denied-cohort",
                },
                str(run.run_id),
            )
            if case == "cancelled-workflow":
                inspector.cancel_workflow(f"research-{run.run_id}")
            if case == "cancelled-run":
                repo.cancel(token, run.workspace_id, run.run_id)
        calls = []

        def forbidden(messages, info):
            calls.append(True)
            raise AssertionError("forbidden recovery reached provider")

        run_worker(database_url, model=FunctionModel(forbidden), once=True)
        state = repo.worker_states((run.run_id,))[run.run_id]
        assert state == ("cancelled" if case == "cancelled-run" else "failed")
        assert calls == []
        status = inspector.retrieve_workflow(f"research-{run.run_id}").get_status()
        if case != "revoked-membership":
            assert status.status == "CANCELLED"
    finally:
        inspector.destroy()


def test_second_worker_is_rejected_before_touching_an_inflight_request(
    engine, database_url, tmp_path
):
    import time

    from pydantic_ai.models.function import FunctionModel

    bundle, token, repo, run = seed(engine, database_url)
    marker, release = tmp_path / "calls", tmp_path / "release"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(output(bundle, classified=True)),
        "CALL_MARKER": str(marker),
        "WAIT_RELEASE": str(release),
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    first = subprocess.Popen(
        [sys.executable, "-c", CRASH_SCRIPT],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 15
        while not marker.exists():
            assert time.monotonic() < deadline and first.poll() is None
            time.sleep(0.05)
        before = repo.get_run(token, run.workspace_id, run.run_id)
        assert before.status == "generating"
        calls = []

        def forbidden(messages, info):
            calls.append(True)
            raise AssertionError("second worker must not invoke model")

        with pytest.raises(ValueError, match="Research worker already running"):
            run_worker(database_url, model=FunctionModel(forbidden), once=True)
        assert repo.get_run(token, run.workspace_id, run.run_id) == before
        assert calls == [] and marker.read_text() == "called\n"
        release.touch()
        assert first.wait(timeout=15) == 0
        assert repo.get_run(token, run.workspace_id, run.run_id).status == "completed"
    finally:
        if first.poll() is None:
            first.kill()
            first.wait(timeout=5)


def test_worker_lock_connection_is_idle_and_loss_fails_closed(engine):
    from issuedigest_worker.research_recovery import WORKER_LOCK_KEYS, research_worker_lock
    from sqlalchemy import text

    with research_worker_lock(engine) as check:
        check()
        with engine.connect() as observer:
            pid, state = observer.execute(
                text(
                    "SELECT a.pid, a.state FROM pg_locks l JOIN pg_stat_activity a ON a.pid=l.pid "
                    "WHERE l.locktype='advisory' AND l.classid=:namespace AND l.objid=:worker "
                    "AND l.objsubid=2 AND l.granted"
                ),
                WORKER_LOCK_KEYS,
            ).one()
            assert state == "idle"
            assert observer.scalar(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
        with pytest.raises(ValueError, match="^Research worker ownership lost$"):
            check()
    with research_worker_lock(engine) as recovered:
        recovered()
