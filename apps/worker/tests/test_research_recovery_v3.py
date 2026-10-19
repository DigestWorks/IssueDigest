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


def output(bundle, text="첫 모델의 해석", classified=False, core=False):
    claim = {
        "text": text,
        "citation_ids": [str(bundle.citations[0].citation_id)],
        "event_date": None,
    }
    if classified:
        claim.update(category="documented", rationale="선택 인용의 합성 설명")
    if core:
        return {
            "outcome": "answer",
            "summary_title": "합성 요약",
            "core_answer": {k: v for k, v in claim.items() if k not in {"category", "event_date"}},
            "additional_summary_claims": [],
            "details": [],
        }
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
    spec = importlib.util.spec_from_file_location(
        'issuedigest_worker.frozen_historical', os.environ['LEGACY_WORKER'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run_worker = module.run_worker
else:
    from issuedigest_worker.research_worker import run_worker
class CountedModel(TestModel):
    async def request(self, *args, **kwargs):
        if args[2].output_tools[0].name == 'search_evidence':
            from pydantic_ai.messages import ModelResponse, ToolCallPart
            from pydantic_ai.usage import RequestUsage
            return ModelResponse(
                parts=[ToolCallPart('search_evidence', {'queries':['80%']})],
                usage=RequestUsage(input_tokens=10, output_tokens=5))
        with open(os.environ['CALL_MARKER'], 'a') as marker: marker.write('called\\n')
        if os.environ.get('CRASH_INSIDE_MODEL') == '1': os.kill(os.getpid(), signal.SIGKILL)
        if os.environ.get('ERROR_MODEL') == '1': raise ValueError('synthetic paid request error')
        if os.environ.get('WAIT_RELEASE'):
            import asyncio
            from pathlib import Path
            while not Path(os.environ['WAIT_RELEASE']).exists(): await asyncio.sleep(0.05)
        return await super().request(*args, **kwargs)
original = ResearchRepository.worker_transition
def crash(self, run_id, status, **kwargs):
    if status == 'validating' or (os.environ.get('ERROR_MODEL') == '1' and status == 'failed'):
        os.kill(os.getpid(), signal.SIGKILL)
    return original(self, run_id, status, **kwargs)
if os.environ.get('CRASH_AFTER_MODEL') == '1': ResearchRepository.worker_transition = crash
run_worker(os.environ['ISSUEDIGEST_TEST_DATABASE_URL'],
    model=CountedModel(custom_output_args=json.loads(os.environ['SYNTHETIC_OUTPUT'])), once=True)
"""


def crash_worker(database_url, tmp_path, proposal, *, legacy="v2", checkpoint=True, error=False):
    marker = tmp_path / "synthetic-provider-calls"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(proposal),
        "CALL_MARKER": str(marker),
        "PYDANTIC_AI_NO_BANNER": "1",
        "CRASH_AFTER_MODEL" if checkpoint else "CRASH_INSIDE_MODEL": "1",
    }
    if error:
        env["ERROR_MODEL"] = "1"
    if legacy:
        env["LEGACY_WORKER"] = str(Path(__file__).parent / f"fixtures/research_worker_{legacy}.py")
    proc = subprocess.run(
        [sys.executable, "-c", CRASH_SCRIPT], env=env, capture_output=True, timeout=20
    )
    assert proc.returncode == -signal.SIGKILL, proc.stderr.decode()[-1000:]
    assert marker.read_text() == "called\n"
    return marker


def client(database_url):
    return DBOSClient(system_database_url=database_url, application_name="issuedigest-research")


@pytest.mark.parametrize("legacy", ["v2", "v3", "v4", "v5", "v6"])
def test_real_historical_checkpoint_recovers_under_recorded_version_then_new_requests_use_v8(
    engine,
    database_url,
    tmp_path,
    legacy,
):
    version = legacy or "v6"
    bundle, token, repo, old = seed(engine, database_url)
    marker = crash_worker(
        database_url,
        tmp_path,
        output(bundle, classified=version != "v2", core=version == "v6"),
        legacy=legacy,
    )
    inspector = client(database_url)
    try:
        before = inspector.list_workflows(
            workflow_ids=[f"research-{old.run_id}"], load_input=False, load_output=False
        )[0]
        checkpoints = inspector.list_workflow_steps(before.workflow_id, load_output=False)
        assert [(step["function_id"], step["function_name"]) for step in checkpoints] == [
            (1, f"issuedigest_research_{version}__model.request"),
        ]
        assert checkpoints[0]["completed_at_epoch_ms"] is not None
        assert repo.get_run(token, old.workspace_id, old.run_id).status == "generating"
        new_bundle, new_token, _, new = seed(engine, database_url)
        new_marker = tmp_path / "new-provider-calls"
        current_env = {
            **os.environ,
            "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
            "SYNTHETIC_OUTPUT": json.dumps(output(new_bundle, "새 해석", True, core=True)),
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
        assert recovered.result.canvas.research.claims[0].text == (
            "제공 자료에 따르면, 첫 모델의 해석" if version == "v6" else "첫 모델의 해석"
        )
        assert (
            recovered.result.canvas.research.claims[0].derivation.method_version
            == f"research-{version}"
        )
        assert len(recovered.result.canvas.research.support_reviews) == (version != "v2")
        current = repo.get_run(new_token, new.workspace_id, new.run_id)
        assert current.status == "completed"
        assert current.result.canvas.research.claims[0].derivation.method_version == "research-v8"
        assert len(current.result.canvas.research.support_reviews) == 1
        after = inspector.list_workflows(
            workflow_ids=[before.workflow_id, f"research-{new.run_id}"],
            load_input=False,
            load_output=False,
        )
        by_id = {workflow.workflow_id: workflow for workflow in after}
        assert by_id[before.workflow_id].app_version == before.app_version
        assert by_id[before.workflow_id].name == f"issuedigest_research_run_{version}"
        assert by_id[f"research-{new.run_id}"].name == "issuedigest_research_run_v8"
        assert by_id[f"research-{new.run_id}"].app_version != before.app_version
        assert inspector.list_workflow_steps(before.workflow_id, load_output=False) == checkpoints
        assert marker.read_text() == "called\n"
        # Another full registry destroy/relaunch must only read completed application rows.
        run_worker(
            database_url,
            model=TestModel(custom_output_args=output(bundle, "재호출 금지", True, core=True)),
            once=True,
        )
        assert repo.get_run(token, old.workspace_id, old.run_id) == recovered
    finally:
        inspector.destroy()


@pytest.mark.parametrize("legacy", ["v2", "v3", "v4", "v5", "v6"])
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
        output(bundle, classified=legacy != "v2", core=legacy == "v6"),
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


@pytest.mark.parametrize(
    "name",
    [
        "issuedigest_research_run_v2",
        "issuedigest_research_run_v3",
        "issuedigest_research_run_v4",
        "issuedigest_research_run_v5",
        "issuedigest_research_run_v6",
    ],
)
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
            model=TestModel(
                custom_output_args=output(
                    bundle, classified=not name.endswith("v2"), core=name.endswith("v6")
                )
            ),
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


@pytest.mark.parametrize("profile", ["v2", "v3", "v4", "v5", "v6"])
@pytest.mark.parametrize(
    "case", ["unknown-name", "cancelled-workflow", "cancelled-run", "revoked-membership"]
)
def test_recovery_never_calls_model_for_unknown_cancelled_or_unauthorized_run(
    engine,
    database_url,
    tmp_path,
    case,
    profile,
):
    from pydantic_ai.models.function import FunctionModel

    bundle, token, repo, run = seed(engine, database_url)
    inspector = client(database_url)
    try:
        if case == "revoked-membership":
            # A real paid checkpoint exists; reloading still checks current authorization.
            crash_worker(
                database_url,
                tmp_path,
                output(bundle, classified=profile != "v2", core=profile == "v6"),
                legacy=profile,
            )
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
                else f"issuedigest_research_run_{profile}"
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
        "SYNTHETIC_OUTPUT": json.dumps(output(bundle, classified=True, core=True)),
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


@pytest.mark.parametrize("version", ["v2", "v3", "v4", "v5", "v6"])
@pytest.mark.parametrize("slot", [0, 2, -1, True, False, 1.0, "1", None, "missing"])
def test_model_checkpoint_rejects_wrong_or_malformed_durable_slot(version, slot):
    from issuedigest_worker.research_recovery import completed_model_checkpoint

    class MetadataClient:
        def list_workflow_steps(self, workflow_id, *, load_output, limit):
            assert workflow_id == "research-synthetic"
            assert load_output is False and limit == 21
            step = {
                "function_name": f"issuedigest_research_{version}__model.request",
                "completed_at_epoch_ms": 1,
            }
            if slot != "missing":
                step["function_id"] = slot
            return [step]

    assert not completed_model_checkpoint(
        MetadataClient(), "research-synthetic", f"issuedigest_research_run_{version}"
    )


@pytest.mark.parametrize("version", ["v2", "v3", "v4", "v5", "v6"])
def test_model_checkpoint_accepts_canonical_integer_slot_one(version):
    from issuedigest_worker.research_recovery import completed_model_checkpoint

    class MetadataClient:
        def list_workflow_steps(self, workflow_id, *, load_output, limit):
            assert workflow_id == "research-synthetic"
            assert load_output is False and limit == 21
            return [
                {
                    "function_id": 1,
                    "function_name": f"issuedigest_research_{version}__model.request",
                    "completed_at_epoch_ms": 1,
                }
            ]

    assert completed_model_checkpoint(
        MetadataClient(), "research-synthetic", f"issuedigest_research_run_{version}"
    )


@pytest.mark.parametrize("version", ["v2", "v3", "v4", "v5", "v6"])
def test_cached_paid_error_replays_without_a_second_request(
    engine, database_url, tmp_path, version
):
    from pydantic_ai.models.function import FunctionModel

    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_worker(
        database_url,
        tmp_path,
        output(bundle, classified=version != "v2", core=version == "v6"),
        legacy=version,
        error=True,
    )
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("cached paid error must never repeat the request")

    inspector = client(database_url)
    try:
        before = inspector.list_workflows(
            workflow_ids=[f"research-{run.run_id}"],
            load_input=False,
            load_output=False,
        )[0]
        steps = inspector.list_workflow_steps(before.workflow_id, load_output=False)
        assert [(s["function_id"], s["function_name"]) for s in steps] == [
            (1, f"issuedigest_research_{version}__model.request")
        ]
        assert steps[0]["completed_at_epoch_ms"] is not None
        assert repo.get_run(token, run.workspace_id, run.run_id).status == "generating"
        run_worker(database_url, model=FunctionModel(forbidden), once=True)
        failed = repo.get_run(token, run.workspace_id, run.run_id)
        assert failed.status == "failed" and failed.error_code == "generation_failed"
        assert failed.result is None and calls == [] and marker.read_text() == "called\n"
        after = inspector.retrieve_workflow(before.workflow_id).get_status()
        assert after.app_version == before.app_version
        assert after.name == before.name == f"issuedigest_research_run_{version}"
        assert inspector.list_workflow_steps(before.workflow_id, load_output=False) == steps
    finally:
        inspector.destroy()


@pytest.mark.parametrize("version", ["v2", "v3", "v4", "v5", "v6"])
@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "other-name", "incomplete", "too-many"]
)
def test_checkpoint_rejects_missing_duplicate_wrong_or_incomplete_model_step(version, mutation):
    from issuedigest_worker.research_recovery import completed_model_checkpoint

    step = {
        "function_id": 1,
        "function_name": f"issuedigest_research_{version}__model.request",
        "completed_at_epoch_ms": 1,
    }
    steps = [step]
    if mutation == "missing":
        steps.clear()
    elif mutation == "duplicate":
        steps.append({**step, "function_id": 2})
    elif mutation == "other-name":
        step["function_name"] = "other__model.request"
    elif mutation == "incomplete":
        step["completed_at_epoch_ms"] = None
    elif mutation == "too-many":
        steps.extend({**step, "function_id": i, "function_name": "unrelated"} for i in range(2, 22))

    class MetadataClient:
        def list_workflow_steps(self, workflow_id, *, load_output, limit):
            assert load_output is False and limit == 21
            return steps

    assert not completed_model_checkpoint(
        MetadataClient(), "research-synthetic", f"issuedigest_research_run_{version}"
    )
