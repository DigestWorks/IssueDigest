"""Additional v10 budget/current-authority integration beyond the shared relevance suite."""

import json

import pytest
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_recovery_v3 import output, seed
from test_research_worker_v9 import crash_relevance


def crash_v10(database_url, tmp_path, proposal, point):
    return crash_relevance(database_url, tmp_path, proposal, point, profile="v10")


def test_combined_actual_usage_exhausts_budget_before_final_request(engine, database_url):
    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        if name == "search_evidence":
            payload = {"queries": ["80%"]}
            incoming = 7000
        else:
            assert name == "classify_relevance"
            prompt = json.loads(messages[-1].parts[0].content)
            payload = {
                "decisions": [
                    {"snapshot_id": s["snapshot_id"], "decision": "retain"}
                    for s in prompt["sources"]
                ]
            }
            incoming = 11000
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=incoming, output_tokens=500),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "failed" and after.error_code == "insufficient_evidence"
    assert (after.input_tokens, after.output_tokens) == (18000, 1000)
    assert calls == ["search_evidence", "classify_relevance"]


@pytest.mark.parametrize("point", ["apply-checkpoint", "final-checkpoint"])
@pytest.mark.parametrize("mutation", ["cancel", "membership", "corrupt-source"])
def test_cached_apply_and_final_recheck_present_authority_and_all_originals(
    engine, database_url, tmp_path, point, mutation
):
    from issuedigest_storage.auth_schema import auth_workspace_memberships
    from issuedigest_storage.research_schema import research_runs
    from issuedigest_storage.schema import evidence_snapshots
    from sqlalchemy import delete, select, update

    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_v10(database_url, tmp_path, output(bundle, classified=True, core=True), point)
    before_calls = marker.read_text()
    if mutation == "cancel":
        repo.cancel(token, run.workspace_id, run.run_id)
    else:
        with engine.begin() as conn:
            if mutation == "membership":
                conn.execute(
                    delete(auth_workspace_memberships).where(
                        auth_workspace_memberships.c.workspace_id == run.workspace_id
                    )
                )
            else:
                conn.execute(
                    update(evidence_snapshots)
                    .where(evidence_snapshots.c.workspace_id == run.workspace_id)
                    .values(payload={"bad": "synthetic"})
                )
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError(
            "Current authority/originals failure cannot send another model request"
        )

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    with engine.connect() as conn:
        after = (
            conn.execute(select(research_runs).where(research_runs.c.run_id == run.run_id))
            .mappings()
            .one()
        )
    assert after["status"] == ("cancelled" if mutation == "cancel" else "failed")
    assert after["result"] is None and calls == [] and marker.read_text() == before_calls
    assert (after["input_tokens"], after["output_tokens"]) == (
        (369, 135) if point == "final-checkpoint" else (246, 90)
    )


@pytest.mark.parametrize(
    "profile,workflow_profile,final_profile",
    [
        ("v9", "v10", "v9"),
        ("v9", "v9", "v10"),
        ("v10", "v9", "v10"),
        ("v10", "v10", "v9"),
    ],
)
def test_cross_profile_workflow_or_final_is_rejected_before_raw_usage_read(
    profile, workflow_profile, final_profile
):
    from types import SimpleNamespace

    from issuedigest_worker import research_recovery
    from test_research_worker_v9 import EXPECTED

    class Metadata:
        def list_workflow_steps(self, workflow_id, *, load_output, limit):
            assert load_output is False, "Mixed profile cannot deserialize raw output"
            expected = EXPECTED[:4] + [
                (
                    5,
                    {
                        "v9": "issuedigest_research_v9__model.request",
                        "v10": "issuedigest_research_v10__model.request",
                    }[final_profile],
                )
            ]
            return [
                dict(function_id=i, function_name=n, completed_at_epoch_ms=1) for i, n in expected
            ]

        def list_workflows(self, **kwargs):
            return [
                SimpleNamespace(
                    workflow_id="synthetic",
                    name={
                        "v9": "issuedigest_research_run_v9",
                        "v10": "issuedigest_research_run_v10",
                    }[workflow_profile],
                    attributes={
                        "issuedigest_select_v9_started": True,
                        "issuedigest_select_v9_prompt_sha256": "a" * 64,
                    },
                )
            ]

    assert not research_recovery._recoverable_relevance_checkpoint(
        Metadata(), "synthetic", "generating", profile=profile
    )
    assert research_recovery._known_relevance_usage(Metadata(), "synthetic", profile=profile) == (
        0,
        0,
    )


@pytest.mark.parametrize("profile", ["v010", "v11", "prefix-v10", "v9extra", "", None, True])
def test_relevance_helpers_refuse_arbitrary_profile_before_db_access(profile):
    from issuedigest_worker import research_recovery

    with pytest.raises(ValueError, match="profile"):
        research_recovery._completed_relevance_checkpoint(
            object(), "synthetic", "queued", profile=profile
        )
    with pytest.raises(ValueError, match="profile"):
        research_recovery._known_relevance_usage(object(), "synthetic", profile=profile)


def test_borrowed_final10_registers_after_config_before_launch_without_new_client_or_close(
    engine, database_url, monkeypatch
):
    from dbos import DBOS
    from issuedigest_agents import research_v3
    from issuedigest_worker import research_worker as worker

    bundle, token, repo, run = seed(engine, database_url)
    lifecycle, events = [], []

    def respond(messages, info):
        name = info.output_tools[0].name
        if name == "search_evidence":
            payload = {"queries": ["80%"]}
        elif name == "classify_relevance":
            prompt = json.loads(messages[-1].parts[0].content)
            payload = {
                "decisions": [
                    {"snapshot_id": s["snapshot_id"], "decision": "retain"}
                    for s in prompt["sources"]
                ]
            }
        else:
            payload = output(bundle, classified=True, core=True)
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    class BorrowedModel(FunctionModel):
        async def __aenter__(self):
            lifecycle.append("enter")
            return self

        async def __aexit__(self, *args):
            lifecycle.append("close")

    borrowed = BorrowedModel(respond)
    initialize, launch, factory = DBOS.__init__, DBOS.launch, worker.create_agent_v10

    def configuring(self, *args, **kwargs):
        result = initialize(self, *args, **kwargs)
        events.append("configured")
        return result

    def registering(model):
        assert model is borrowed and "configured" in events and "launched" not in events
        result = factory(model)
        events.append("registered10")
        return result

    def launching(*args, **kwargs):
        assert "configured" in events and events[-1] == "registered10"
        events.append("launched")
        return launch(*args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Injected model must not create a default provider client")

    monkeypatch.setattr(DBOS, "__init__", configuring)
    monkeypatch.setattr(DBOS, "launch", launching)
    monkeypatch.setattr(worker, "create_agent_v10", registering)
    monkeypatch.setattr(research_v3, "AsyncOpenAI", forbidden)
    run_worker(database_url, model=borrowed, once=True)
    assert repo.get_run(token, run.workspace_id, run.run_id).status == "completed"
    assert events.index("configured") < events.index("registered10") < events.index("launched")
    assert lifecycle == []
