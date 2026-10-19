"""Actual DBOS/PostgreSQL v8 planning, fixation, cumulative accounting and replay."""

import json

import pytest
from issuedigest_worker import research_recovery
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_recovery_v3 import client, output, seed


def steps(stage):
    items = [(1, "issuedigest_research_plan_v7__model.request")]
    if stage in {"generating", "validating"}:
        items += [
            (2, "issuedigest_research_search_v8"),
            (3, "issuedigest_research_v8__model.request"),
        ]
    return [dict(function_id=i, function_name=n, completed_at_epoch_ms=1) for i, n in items]


@pytest.mark.parametrize("stage", ["retrieving", "generating", "validating"])
@pytest.mark.parametrize(
    "mutation",
    [
        None,
        "missing",
        "extra",
        "wrong-name",
        "bool-slot",
        "incomplete",
        "duplicate",
        "wrong-slot",
        "search-extra",
    ],
)
def test_v8_recovery_requires_exact_stage_slots_and_completed_names(stage, mutation):
    values = steps(stage)
    if mutation == "missing":
        values.pop()
    if mutation == "extra":
        values.append(
            dict(function_id=4, function_name="other__model.request", completed_at_epoch_ms=1)
        )
    if mutation == "wrong-name":
        values[0]["function_name"] = "issuedigest_research_v6__model.request"
    if mutation == "bool-slot":
        values[0]["function_id"] = True
    if mutation == "incomplete":
        values[-1]["completed_at_epoch_ms"] = None
    if mutation == "duplicate":
        values.append(values[0].copy())
    if mutation == "wrong-slot":
        values[0]["function_id"] = 0
    if mutation == "search-extra":
        values.append(
            dict(
                function_id=4,
                function_name="issuedigest_research_search_v8",
                completed_at_epoch_ms=1,
            )
        )

    class Metadata:
        def list_workflow_steps(self, workflow_id, *, load_output, limit):
            assert load_output is False and limit == 21
            return values

    assert research_recovery.completed_v8_checkpoint(Metadata(), "synthetic", stage) is (
        mutation is None
    )


def test_v8_worker_plans_then_searches_and_sums_actual_usage(engine, database_url):
    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        payload = (
            {"queries": ["합성"]}
            if name == "search_evidence"
            else output(bundle, classified=True, core=True)
        )
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    completed = repo.get_run(token, run.workspace_id, run.run_id)
    assert completed.status == "completed" and completed.result
    assert (completed.input_tokens, completed.output_tokens) == (200, 100)
    assert completed.result.canvas.research.claims[0].derivation.method_version == "research-v8"
    assert [e.status for e in completed.events] == [
        "queued",
        "retrieving",
        "generating",
        "validating",
        "completed",
    ]
    assert calls == ["search_evidence", "answer"]
    inspector = client(database_url)
    try:
        actual = inspector.list_workflow_steps(f"research-{run.run_id}", load_output=False)
        assert [(s["function_id"], s["function_name"]) for s in actual] == [
            (s["function_id"], s["function_name"]) for s in steps("generating")
        ]
    finally:
        inspector.destroy()


def test_v8_no_match_records_planner_usage_and_never_calls_final(engine, database_url):
    from issuedigest_storage.research_schema import research_runs
    from sqlalchemy import update

    bundle, token, repo, run = seed(engine, database_url)
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == run.run_id)
            .values(question="존재하지않는질문")
        )
    calls = []

    def respond(messages, info):
        calls.append(info.output_tools[0].name)
        return ModelResponse(
            parts=[ToolCallPart("search_evidence", {"queries": ["없는자료"]})],
            usage=RequestUsage(input_tokens=123, output_tokens=45),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    failed = repo.get_run(token, run.workspace_id, run.run_id)
    assert failed.status == "failed" and failed.error_code == "insufficient_evidence"
    assert (failed.input_tokens, failed.output_tokens) == (123, 45)
    assert calls == ["search_evidence"]


CRASH_V8 = r"""
import json, os, signal
from issuedigest_storage.research import ResearchRepository
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
point = os.environ.get("CRASH_POINT")
def kill(): os.kill(os.getpid(), signal.SIGKILL)
def respond(messages, info):
    name = info.output_tools[0].name
    with open(os.environ["CALL_MARKER"], "a") as marker: marker.write(name + "\n")
    if point == "inside-" + name: kill()
    if point == "cached-final-error" and name == "answer":
        raise ValueError("synthetic paid final error")
    payload = ({"queries": ["80%"]} if name == "search_evidence"
               else json.loads(os.environ["SYNTHETIC_OUTPUT"]))
    return ModelResponse(parts=[ToolCallPart(name, payload)],
                         usage=RequestUsage(input_tokens=123, output_tokens=45))
fix = ResearchRepository.worker_search_and_fix
def search(self, *args, **kwargs):
    if point == "before-search": kill()
    result = fix(self, *args, **kwargs)
    if point == "search-commit": kill()
    return result
ResearchRepository.worker_search_and_fix = search
load = ResearchRepository.worker_load
def loading(self, *args, **kwargs):
    if point == "search-checkpoint": kill()
    return load(self, *args, **kwargs)
ResearchRepository.worker_load = loading
transition = ResearchRepository.worker_transition
def transitioning(self, run_id, status, **kwargs):
    if ((point == "final-checkpoint" and status == "validating")
        or (point == "validating" and status == "completed")): kill()
    if point == "cached-final-error" and status == "failed": kill()
    result = transition(self, run_id, status, **kwargs)
    if point == "before-final" and status == "generating": kill()
    return result
ResearchRepository.worker_transition = transitioning
run_worker(os.environ["ISSUEDIGEST_TEST_DATABASE_URL"], model=FunctionModel(respond), once=True)
"""


def crash_v8(database_url, tmp_path, proposal, point):
    import os
    import signal
    import subprocess
    import sys

    marker = tmp_path / "v8-model-calls"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(proposal),
        "CALL_MARKER": str(marker),
        "CRASH_POINT": point,
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    result = subprocess.run(
        [sys.executable, "-c", CRASH_V8], env=env, capture_output=True, timeout=20
    )
    assert result.returncode == -signal.SIGKILL, result.stderr.decode()[-2000:]
    return marker


@pytest.mark.parametrize(
    "point,expected_calls,success",
    [
        ("inside-search_evidence", [], False),
        ("before-search", ["answer"], True),
        ("search-commit", ["answer"], True),
        ("search-checkpoint", ["answer"], True),
        ("before-final", [], False),
        ("inside-answer", [], False),
        ("cached-final-error", [], False),
        ("final-checkpoint", [], True),
        ("validating", [], True),
    ],
)
def test_v8_real_crash_replays_only_completed_paid_steps(
    engine, database_url, tmp_path, point, expected_calls, success
):
    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_v8(database_url, tmp_path, output(bundle, classified=True, core=True), point)
    before = repo.get_run(token, run.workspace_id, run.run_id)
    fixed = before.snapshot_ids
    called_before = marker.read_text()
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        assert name == "answer"
        return ModelResponse(
            parts=[ToolCallPart(name, output(bundle, classified=True, core=True))],
            usage=RequestUsage(input_tokens=123, output_tokens=45),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == ("completed" if success else "failed")
    assert calls == expected_calls and marker.read_text() == called_before
    if fixed:
        assert after.snapshot_ids == fixed
    if success:
        assert (after.input_tokens, after.output_tokens) == (246, 90)
        assert after.result.canvas.research.claims[0].derivation.method_version == "research-v8"
    else:
        assert after.error_code == "generation_failed" and after.result is None


@pytest.mark.parametrize("mutation", ["cancel", "membership", "corrupt-source"])
def test_v8_current_authority_and_originals_block_final_after_planner_checkpoint(
    engine, database_url, tmp_path, mutation
):
    from issuedigest_storage.auth_schema import auth_workspace_memberships
    from issuedigest_storage.schema import evidence_snapshots
    from sqlalchemy import delete, update

    bundle, token, repo, run = seed(engine, database_url)
    crash_v8(database_url, tmp_path, output(bundle, classified=True, core=True), "search-commit")
    if mutation == "cancel":
        repo.cancel(token, run.workspace_id, run.run_id)
    elif mutation == "membership":
        with engine.begin() as conn:
            conn.execute(
                delete(auth_workspace_memberships).where(
                    auth_workspace_memberships.c.workspace_id == run.workspace_id
                )
            )
    else:
        with engine.begin() as conn:
            conn.execute(
                update(evidence_snapshots)
                .where(evidence_snapshots.c.workspace_id == run.workspace_id)
                .values(payload={})
            )
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("current authority or invalid original must stop final")

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    assert calls == []
    state = repo.worker_states((run.run_id,))[run.run_id]
    assert state == ("cancelled" if mutation == "cancel" else "failed")


def test_v8_checkpoint_missing_function_metadata_is_not_recoverable():
    class Metadata:
        def list_workflow_steps(self, *args, **kwargs):
            return [{"function_id": 1, "completed_at_epoch_ms": 1}]

    assert not research_recovery.completed_v8_checkpoint(Metadata(), "synthetic", "retrieving")


@pytest.mark.parametrize("mutation", ["incomplete", "extra", "fake-slot"])
def test_v8_real_checkpoint_with_invalid_metadata_fails_without_model(
    engine, database_url, tmp_path, monkeypatch, mutation
):
    from dbos import DBOSClient

    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_v8(
        database_url, tmp_path, output(bundle, classified=True, core=True), "final-checkpoint"
    )
    original = DBOSClient.list_workflow_steps

    def invalid_metadata(self, workflow_id, **kwargs):
        values = original(self, workflow_id, **kwargs)
        if workflow_id == f"research-{run.run_id}":
            if mutation == "incomplete":
                values[-1]["completed_at_epoch_ms"] = None
            if mutation == "extra":
                values.append({**values[-1], "function_id": 4})
            if mutation == "fake-slot":
                values[0]["function_id"] = True
        return values

    monkeypatch.setattr(DBOSClient, "list_workflow_steps", invalid_metadata)
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("invalid metadata must stop before model replay")

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    failed = repo.get_run(token, run.workspace_id, run.run_id)
    assert failed.status == "failed" and failed.error_code == "generation_failed"
    assert calls == [] and marker.read_text() == "search_evidence\nanswer\n"


def test_v8_cached_search_provenance_mismatch_is_terminal(
    engine, database_url, tmp_path, monkeypatch
):
    from uuid import uuid4

    from issuedigest_storage.research import ResearchRepository

    bundle, token, repo, run = seed(engine, database_url)
    crash_v8(
        database_url, tmp_path, output(bundle, classified=True, core=True), "search-checkpoint"
    )
    monkeypatch.setattr(
        ResearchRepository, "worker_search_and_fix", lambda *args, **kwargs: (uuid4(),)
    )
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("fixed result mismatch must never call final")

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    failed = repo.get_run(token, run.workspace_id, run.run_id)
    assert failed.status == "failed" and failed.error_code == "generation_failed"
    assert (failed.input_tokens, failed.output_tokens) == (123, 45)
    assert calls == []


def test_v8_parent_mismatch_after_planner_checkpoint_stops_before_final(
    engine, database_url, tmp_path
):
    from uuid import uuid4

    from issuedigest_storage.research_schema import research_runs
    from sqlalchemy import update

    bundle, token, repo, run = seed(engine, database_url)
    crash_v8(database_url, tmp_path, output(bundle, classified=True, core=True), "before-search")
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == run.run_id)
            .values(parent_run_id=uuid4())
        )
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("invalid canonical parent must stop final")

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    failed = repo.get_run(token, run.workspace_id, run.run_id)
    assert failed.status == "failed" and failed.error_code == "generation_failed"
    assert calls == []


def test_v8_planned_search_can_supply_evidence_after_original_question_has_no_hit(
    engine, database_url
):
    from issuedigest_storage.research_schema import research_runs
    from sqlalchemy import update

    bundle, token, repo, run = seed(engine, database_url)
    with engine.begin() as conn:
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == run.run_id)
            .values(question="different wording")
        )
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        payload = (
            {"queries": ["80%"]}
            if name == "search_evidence"
            else output(bundle, classified=True, core=True)
        )
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    completed = repo.get_run(token, run.workspace_id, run.run_id)
    assert completed.status == "completed" and len(completed.snapshot_ids) == 1
    assert completed.question == "different wording"
    assert (completed.input_tokens, completed.output_tokens) == (200, 100)
    assert calls == ["search_evidence", "answer"]


@pytest.mark.parametrize("malformed_stage", ["search_evidence", "answer"])
def test_v8_raw_boolean_cached_usage_fails_without_new_model(
    engine, database_url, tmp_path, malformed_stage
):
    import os
    import signal
    import subprocess
    import sys

    bundle, token, repo, run = seed(engine, database_url)
    marker = tmp_path / "malformed-usage-model-calls"
    # Seed the pre-fix accepted response through the real durable provider boundary,
    # bypassing only validation in this isolated child; never edit the DBOS journal.
    script = CRASH_V8.replace(
        'point = os.environ.get("CRASH_POINT")',
        "import issuedigest_agents.research_v7 as v8\n"
        "v8._validate_usage = lambda *args, **kwargs: None\n"
        'point = os.environ.get("CRASH_POINT")',
    ).replace(
        "usage=RequestUsage(input_tokens=123, output_tokens=45)",
        "usage=(RequestUsage(input_tokens=True, output_tokens=45) "
        'if name == os.environ["MALFORMED_STAGE"] else '
        "RequestUsage(input_tokens=123, output_tokens=45))",
    )
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(output(bundle, classified=True, core=True)),
        "CALL_MARKER": str(marker),
        "MALFORMED_STAGE": malformed_stage,
        "CRASH_POINT": "before-search"
        if malformed_stage == "search_evidence"
        else "final-checkpoint",
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    crashed = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, timeout=20
    )
    assert crashed.returncode == -signal.SIGKILL, crashed.stderr.decode()[-2000:]
    inspector = client(database_url)
    try:
        before = inspector.list_workflow_steps(f"research-{run.run_id}", load_output=False)
        assert len(before) == (1 if malformed_stage == "search_evidence" else 3)
        assert all(step["completed_at_epoch_ms"] is not None for step in before)
        calls = []

        def forbidden(messages, info):
            calls.append(info.output_tools[0].name)
            raise AssertionError("malformed cached paid usage must not cause another model request")

        run_worker(database_url, model=FunctionModel(forbidden), once=True)
        failed = repo.get_run(token, run.workspace_id, run.run_id)
        assert failed.status == "failed" and failed.error_code == "generation_failed"
        assert failed.result is None and calls == []
        assert (failed.input_tokens, failed.output_tokens) == (
            (0, 0) if malformed_stage == "search_evidence" else (123, 45)
        )
        assert inspector.list_workflow_steps(f"research-{run.run_id}", load_output=False) == before
        assert marker.read_text() == (
            "search_evidence\n"
            if malformed_stage == "search_evidence"
            else "search_evidence\nanswer\n"
        )
    finally:
        inspector.destroy()
