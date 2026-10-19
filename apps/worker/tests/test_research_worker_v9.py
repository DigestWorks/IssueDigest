"""v9 ordered metadata and real PG/DBOS synthetic three-call integration."""

import json

import pytest
from issuedigest_worker import research_recovery
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_recovery_v3 import client, output, seed

EXPECTED = [
    (1, "issuedigest_research_plan_v7__model.request"),
    (2, "issuedigest_research_search_v9"),
    (3, "issuedigest_research_select_v9__model.request"),
    (4, "issuedigest_research_apply_v9"),
    (5, "issuedigest_research_v9__model.request"),
]


@pytest.mark.parametrize(
    "stage,count,valid",
    [
        ("queued", 0, True),
        *[
            (s, n, n == 5 if s != "retrieving" else 1 <= n <= 4)
            for s in ["retrieving", "generating", "validating"]
            for n in range(6)
        ],
    ],
)
def test_exact_v9_metadata_prefix_before_deserialization(stage, count, valid):
    assert hasattr(research_recovery, "completed_v9_checkpoint"), "missing recovery9 guard"

    class Metadata:
        def list_workflow_steps(self, *args, **kwargs):
            assert kwargs == dict(load_output=False, limit=21)
            return [
                dict(function_id=i, function_name=n, completed_at_epoch_ms=1)
                for i, n in EXPECTED[:count]
            ]

    assert research_recovery.completed_v9_checkpoint(Metadata(), "synthetic", stage) == valid


@pytest.mark.parametrize("decision", ["retain", "uncertain", "exclude"])
def test_default_v9_selector_and_known_combined_usage(engine, database_url, decision):
    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        if name == "search_evidence":
            payload = {"queries": ["80%"]}
        elif name == "classify_relevance":
            prompt = json.loads(messages[-1].parts[0].content)
            payload = {
                "decisions": [
                    {"snapshot_id": s["snapshot_id"], "decision": decision}
                    for s in prompt["sources"]
                ]
            }
        else:
            payload = output(bundle, classified=True, core=True)
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == ("failed" if decision == "exclude" else "completed")
    assert calls == ["search_evidence", "classify_relevance"] + (
        [] if decision == "exclude" else ["answer"]
    )
    assert (after.input_tokens, after.output_tokens) == (
        (200, 100) if decision == "exclude" else (300, 150)
    )
    inspector = client(database_url)
    try:
        steps = inspector.list_workflow_steps(f"research-{run.run_id}", load_output=False)
        assert [(s["function_id"], s["function_name"]) for s in steps] == EXPECTED[
            : 4 if decision == "exclude" else 5
        ]
    finally:
        inspector.destroy()


@pytest.mark.parametrize(
    "stage,expected", [("classify_relevance", (200, 100)), ("answer", (300, 150))]
)
def test_malformed_paid_response_keeps_known_usage(engine, database_url, stage, expected):
    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
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
        if name == stage:
            payload = {}
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "failed" and after.error_code == "generation_failed"
    assert (after.input_tokens, after.output_tokens) == expected
    assert calls.count(stage) == 1


@pytest.mark.parametrize("mutation", ["cancel", "revoke"])
def test_cancel_or_revoke_after_selector_retains_known_usage_and_blocks_final(
    engine, database_url, mutation
):
    from issuedigest_storage.auth_schema import auth_workspace_memberships
    from issuedigest_storage.research_schema import research_budget_months, research_runs
    from sqlalchemy import delete, select

    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        if name == "search_evidence":
            payload = {"queries": ["80%"]}
        else:
            assert name == "classify_relevance"
            prompt = json.loads(messages[-1].parts[0].content)
            payload = {
                "decisions": [
                    {"snapshot_id": s["snapshot_id"], "decision": "retain"}
                    for s in prompt["sources"]
                ]
            }
            if mutation == "cancel":
                repo.cancel(token, run.workspace_id, run.run_id)
            else:
                with engine.begin() as conn:
                    conn.execute(
                        delete(auth_workspace_memberships).where(
                            auth_workspace_memberships.c.workspace_id == run.workspace_id
                        )
                    )
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    with engine.connect() as conn:
        after = (
            conn.execute(select(research_runs).where(research_runs.c.run_id == run.run_id))
            .mappings()
            .one()
        )
        assert after["status"] == ("cancelled" if mutation == "cancel" else "failed")
        assert (after["input_tokens"], after["output_tokens"]) == (200, 100)
        assert conn.execute(select(research_budget_months.c.reserved_usd)).scalar_one() > 0
    assert calls == ["search_evidence", "classify_relevance"]


CRASH_V9 = r"""
import json,os,signal
from issuedigest_storage.research import ResearchRepository
from issuedigest_worker.research_worker import run_worker
from pydantic_ai.messages import ModelResponse,ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
point=os.environ['CRASH_POINT']
def kill(): os.kill(os.getpid(),signal.SIGKILL)
from dbos import DBOSClient
claim=DBOSClient.update_workflow_attributes
def claiming(self,*args,**kwargs):
    if point=='selector-preclaim': kill()
    result=claim(self,*args,**kwargs)
    if point=='selector-claim': kill()
    return result
DBOSClient.update_workflow_attributes=claiming

def respond(messages,info):
    name=info.output_tools[0].name
    with open(os.environ['CALL_MARKER'],'a') as marker: marker.write(name+'\n')
    if point=='inside-'+name: kill()
    if point=='cached-selector-error' and name=='classify_relevance':
        raise ValueError('synthetic selector error')
    if name=='search_evidence': payload={'queries':['80%']}
    elif name=='classify_relevance':
        prompt=json.loads(messages[-1].parts[0].content)
        payload={'decisions':[{'snapshot_id':s['snapshot_id'],'decision':'retain'}
                              for s in prompt['sources']]}
    else: payload=json.loads(os.environ['SYNTHETIC_OUTPUT'])
    return ModelResponse(parts=[ToolCallPart(name,payload)],
                         usage=RequestUsage(input_tokens=123,output_tokens=45))
search=ResearchRepository.worker_search_and_fix
def searching(self,*args,**kwargs):
    if point=='before-search': kill()
    result=search(self,*args,**kwargs)
    if point=='search-commit': kill()
    return result
ResearchRepository.worker_search_and_fix=searching
apply=ResearchRepository.worker_apply_relevance_selection
def applying(self,*args,**kwargs):
    if point=='selector-checkpoint': kill()
    result=apply(self,*args,**kwargs)
    if point=='apply-commit': kill()
    return result
ResearchRepository.worker_apply_relevance_selection=applying
load=ResearchRepository.worker_load_relevance_candidates
loads=0
def loading(self,*args,**kwargs):
    global loads
    loads+=1
    if point=='search-checkpoint' or (point=='apply-checkpoint' and loads==2): kill()
    return load(self,*args,**kwargs)
ResearchRepository.worker_load_relevance_candidates=loading
transition=ResearchRepository.worker_transition
def transitioning(self,run_id,status,**kwargs):
    if ((point=='final-checkpoint' and status=='validating')
        or (point=='validating' and status=='completed')
        or (point=='cached-selector-error' and status=='failed')): kill()
    result=transition(self,run_id,status,**kwargs)
    if point=='before-final' and status=='generating': kill()
    return result
ResearchRepository.worker_transition=transitioning
run_worker(os.environ['ISSUEDIGEST_TEST_DATABASE_URL'],model=FunctionModel(respond),once=True)
"""


def crash_v9(database_url, tmp_path, proposal, point):
    import os
    import signal
    import subprocess
    import sys

    marker = tmp_path / "v9-model-calls"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(proposal),
        "CALL_MARKER": str(marker),
        "CRASH_POINT": point,
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    process = subprocess.run(
        [sys.executable, "-c", CRASH_V9], env=env, capture_output=True, timeout=20
    )
    assert process.returncode == -signal.SIGKILL, process.stderr.decode()[-2000:]
    return marker


@pytest.mark.parametrize(
    "point,new_calls,success",
    [
        ("inside-search_evidence", [], False),
        ("before-search", ["classify_relevance", "answer"], True),
        ("search-commit", ["classify_relevance", "answer"], True),
        ("search-checkpoint", ["classify_relevance", "answer"], True),
        ("inside-classify_relevance", [], False),
        ("selector-preclaim", ["classify_relevance", "answer"], True),
        ("selector-claim", [], False),
        ("cached-selector-error", [], False),
        ("selector-checkpoint", ["answer"], True),
        ("apply-commit", ["answer"], True),
        ("apply-checkpoint", ["answer"], True),
        ("before-final", [], False),
        ("inside-answer", [], False),
        ("final-checkpoint", [], True),
        ("validating", [], True),
    ],
)
def test_real_v9_crash_replays_only_completed_responses(
    engine, database_url, tmp_path, point, new_calls, success
):
    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_v9(database_url, tmp_path, output(bundle, classified=True, core=True), point)
    before = marker.read_text()
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        if name == "classify_relevance":
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
            usage=RequestUsage(input_tokens=123, output_tokens=45),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert calls == new_calls and marker.read_text() == before
    assert after.status == ("completed" if success else "failed")
    if success:
        assert (after.input_tokens, after.output_tokens) == (369, 135)
        assert after.result.canvas.research.claims[0].derivation.method_version == "research-v9"
    else:
        assert after.error_code == "generation_failed" and after.result is None


@pytest.mark.parametrize("count", range(1, 6))
@pytest.mark.parametrize(
    "mutation",
    ["name", "slot", "bool", "incomplete", "duplicate", "stream", "extra", "missing-name"],
)
def test_recovery_metadata_rejects_every_namespace_slot_and_incomplete_boundary(count, mutation):
    items = [
        dict(function_id=i, function_name=n, completed_at_epoch_ms=1) for i, n in EXPECTED[:count]
    ]
    if mutation == "name":
        items[-1]["function_name"] = "issuedigest_research_v8__model.request"
    if mutation == "slot":
        items[-1]["function_id"] = 7
    if mutation == "bool":
        items[0]["function_id"] = True
    if mutation == "incomplete":
        items[-1]["completed_at_epoch_ms"] = None
    if mutation == "duplicate":
        items.append(items[-1].copy())
    if mutation == "stream":
        items[-1]["function_name"] += "_stream"
    if mutation == "extra":
        items.append(dict(function_id=6, function_name="other", completed_at_epoch_ms=1))
    if mutation == "missing-name":
        items[-1].pop("function_name")

    class Metadata:
        def list_workflow_steps(self, *args, **kwargs):
            assert kwargs["load_output"] is False
            return items

    assert not research_recovery.completed_v9_checkpoint(
        Metadata(), "synthetic", "generating" if count == 5 else "retrieving"
    )


@pytest.mark.parametrize(
    "mutation", ["candidate", "prompt-hash", "question-hash", "selected", "coverage", "bool-usage"]
)
def test_forged_selector_report_is_revalidated_before_apply_or_final(
    engine, database_url, monkeypatch, mutation
):
    from uuid import uuid4

    import issuedigest_worker.research_worker as worker

    original = worker.run_selector
    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def forged(*args):
        report = original(*args)
        fields = {
            "candidate": {"candidate_snapshot_ids": (uuid4(),)},
            "prompt-hash": {"prompt_sha256": "a" * 64},
            "question-hash": {"question_sha256": "a" * 64},
            "selected": {"selected_snapshot_ids": (uuid4(),)},
            "coverage": {"decisions": ()},
            "bool-usage": {"input_tokens": True},
        }
        return report.model_copy(update=fields[mutation])

    monkeypatch.setattr(worker, "run_selector", forged)

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        if name == "search_evidence":
            payload = {"queries": ["80%"]}
        else:
            assert name == "classify_relevance"
            prompt = json.loads(messages[-1].parts[0].content)
            payload = {
                "decisions": [
                    {"snapshot_id": s["snapshot_id"], "decision": "retain"}
                    for s in prompt["sources"]
                ]
            }
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "failed" and after.error_code == "generation_failed"
    assert (after.input_tokens, after.output_tokens) == (200, 100)
    assert calls == ["search_evidence", "classify_relevance"]


@pytest.mark.parametrize(
    "count,attributes,valid",
    [
        (0, None, True),
        (1, None, True),
        (2, {}, True),
        (
            2,
            {
                "issuedigest_select_v9_started": True,
                "issuedigest_select_v9_prompt_sha256": "a" * 64,
            },
            False,
        ),
        (3, None, False),
        (
            3,
            {
                "issuedigest_select_v9_started": True,
                "issuedigest_select_v9_prompt_sha256": "a" * 64,
            },
            True,
        ),
        (
            4,
            {
                "issuedigest_select_v9_started": True,
                "issuedigest_select_v9_prompt_sha256": "a" * 64,
            },
            True,
        ),
        (
            5,
            {
                "issuedigest_select_v9_started": True,
                "issuedigest_select_v9_prompt_sha256": "a" * 64,
            },
            True,
        ),
        (3, {"issuedigest_select_v9_started": 1}, False),
        (2, {"other": "unrelated"}, False),
        (3, {"issuedigest_select_v9_started": True, "other": 1}, False),
        (3, {"issuedigest_select_v9_started": False}, False),
    ],
)
def test_exact_selector_started_marker_disambiguates_paid3(count, attributes, valid):
    from types import SimpleNamespace

    class Metadata:
        def list_workflow_steps(self, *args, **kwargs):
            assert kwargs["load_output"] is False
            return [
                dict(function_id=i, function_name=n, completed_at_epoch_ms=1)
                for i, n in EXPECTED[:count]
            ]

        def list_workflows(self, **kwargs):
            assert kwargs == dict(
                workflow_ids=["synthetic"],
                application_name="issuedigest-research",
                load_input=False,
                load_output=False,
            )
            return [
                SimpleNamespace(
                    workflow_id="synthetic",
                    name="issuedigest_research_run_v9",
                    attributes=attributes,
                )
            ]

    stage = "queued" if count == 0 else "generating" if count == 5 else "retrieving"
    assert research_recovery.recoverable_v9_checkpoint(Metadata(), "synthetic", stage) == valid


def test_failed_selector_claim_never_sends_paid_request_or_overwrites_attributes(
    engine, database_url, monkeypatch
):
    from dbos import DBOSClient

    bundle, token, repo, run = seed(engine, database_url)
    calls = []

    def fail(*args, **kwargs):
        raise ValueError("synthetic claim write unavailable")

    monkeypatch.setattr(DBOSClient, "update_workflow_attributes", fail)

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        assert name == "search_evidence"
        return ModelResponse(
            parts=[ToolCallPart(name, {"queries": ["80%"]})],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "failed" and after.error_code == "generation_failed"
    assert (after.input_tokens, after.output_tokens) == (100, 50)
    assert calls == ["search_evidence"]


def test_startup_repairs_terminal_cancel_usage_after_real_kill_without_paid_call(
    engine, database_url, tmp_path
):
    import os
    import signal
    import subprocess
    import sys

    from issuedigest_storage.research_schema import research_budget_months, research_runs
    from sqlalchemy import select

    bundle, token, repo, run = seed(engine, database_url)
    script = CRASH_V9.replace(
        "if point=='selector-checkpoint': kill()",
        "if point=='cancel-reset':\n"
        "        from uuid import UUID\n"
        "        self.cancel(os.environ['SYNTHETIC_TOKEN'],"
        "UUID(os.environ['SYNTHETIC_WORKSPACE']),UUID(os.environ['SYNTHETIC_RUN']))\n"
        "        kill()",
    )
    marker = tmp_path / "terminal-model-calls"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(output(bundle, classified=True, core=True)),
        "CALL_MARKER": str(marker),
        "CRASH_POINT": "cancel-reset",
        "SYNTHETIC_TOKEN": token,
        "SYNTHETIC_WORKSPACE": str(run.workspace_id),
        "SYNTHETIC_RUN": str(run.run_id),
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, timeout=20
    )
    assert result.returncode == -signal.SIGKILL, result.stderr.decode()[-1000:]
    before = repo.get_run(token, run.workspace_id, run.run_id)
    assert before.status == "cancelled" and (before.input_tokens, before.output_tokens) == (0, 0)
    called_before = marker.read_text()
    calls = []

    def forbidden(messages, info):
        calls.append(True)
        raise AssertionError("terminal reconciliation cannot call a model")

    run_worker(database_url, model=FunctionModel(forbidden), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "cancelled" and (after.input_tokens, after.output_tokens) == (246, 90)
    assert after.result is None and after.events == before.events
    assert calls == [] and marker.read_text() == called_before
    with engine.connect() as conn:
        assert conn.execute(select(research_budget_months.c.reserved_usd)).scalar_one() > 0
        assert conn.execute(
            select(research_runs.c.snapshot_ids).where(research_runs.c.run_id == run.run_id)
        ).scalar_one() == list(map(str, before.snapshot_ids))


@pytest.mark.parametrize(
    "mutation",
    ["none", "unowned", "noncanonical", "app", "name", "active", "metadata", "attributes", "usage"],
)
def test_terminal_reconciliation_only_reads_exact_owned_validated_v9_journals(mutation):
    from types import SimpleNamespace
    from uuid import UUID

    run_id = UUID("00000000-0000-4000-8000-000000000001")
    workflow = SimpleNamespace(
        workflow_id=f"research-{run_id}",
        name="issuedigest_research_run_v9",
        application_name="issuedigest-research",
        attributes={
            "issuedigest_select_v9_started": True,
            "issuedigest_select_v9_prompt_sha256": "a" * 64,
        },
    )
    if mutation == "unowned":
        workflow.workflow_id = "someone-else"
    if mutation == "noncanonical":
        workflow.workflow_id = f"research-{str(run_id).upper()}" + " "
    if mutation == "app":
        workflow.application_name = "other-app"
    if mutation == "name":
        workflow.name = "issuedigest_research_run_v8"
    if mutation == "attributes":
        workflow.attributes = {"unrelated": True}
    updates = []
    raw_reads = []
    pages = []

    class Metadata:
        def list_workflows(self, **kwargs):
            assert kwargs["load_input"] is False and kwargs["load_output"] is False
            if "workflow_ids" in kwargs:
                return [workflow]
            assert kwargs["name"] == "issuedigest_research_run_v9" and kwargs["limit"] == 20
            pages.append(kwargs["offset"])
            return [workflow] if kwargs["offset"] == 0 else []

        def list_workflow_steps(self, *args, **kwargs):
            result = [
                dict(function_id=i, function_name=n, completed_at_epoch_ms=1)
                for i, n in EXPECTED[:3]
            ]
            if mutation == "metadata":
                result[0]["function_id"] = True
            if kwargs["load_output"]:
                raw_reads.append(True)
                assert mutation not in {"metadata", "attributes"}
                for step in result:
                    if step["function_id"] in {1, 3}:
                        step["output"] = ModelResponse(
                            parts=[],
                            usage=RequestUsage(
                                input_tokens=True if mutation == "usage" else 100, output_tokens=50
                            ),
                        )
            return result

    class Repository:
        def worker_states(self, ids):
            return {
                identity: "generating" if mutation == "active" else "cancelled" for identity in ids
            }

        def worker_record_relevance_usage(self, *args, **kwargs):
            updates.append((args, kwargs))

    research_recovery.reconcile_v9_accounting(Metadata(), Repository())
    assert pages == [0, 1]
    assert bool(updates) == (mutation == "none")
    if mutation == "none":
        assert updates == [((run_id,), dict(input_tokens=200, output_tokens=100))]


@pytest.mark.parametrize("mutation", ["question", "presentation"])
def test_completed_selector_is_bound_to_original_prompt_on_recovery(
    engine, database_url, tmp_path, mutation
):
    from issuedigest_storage.research_schema import research_runs, source_presentations
    from sqlalchemy import select, update

    bundle, token, repo, run = seed(engine, database_url)
    marker = crash_v9(
        database_url, tmp_path, output(bundle, classified=True, core=True), "selector-checkpoint"
    )
    with engine.begin() as conn:
        if mutation == "question":
            conn.execute(
                update(research_runs)
                .where(research_runs.c.run_id == run.run_id)
                .values(question="바뀐 80% 질문")
            )
        else:
            row = (
                conn.execute(
                    select(source_presentations).where(
                        source_presentations.c.workspace_id == run.workspace_id
                    )
                )
                .mappings()
                .one()
            )
            payload = {**row["payload"], "title": "바뀐 합성 제목"}
            conn.execute(
                update(source_presentations)
                .where(source_presentations.c.snapshot_id == row["snapshot_id"])
                .values(payload=payload)
            )
    called_before = marker.read_text()
    calls = []

    def respond(messages, info):
        calls.append(info.output_tools[0].name)
        return ModelResponse(
            parts=[ToolCallPart("answer", output(bundle, classified=True, core=True))],
            usage=RequestUsage(input_tokens=123, output_tokens=45),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "failed" and after.error_code == "generation_failed"
    assert calls == [] and marker.read_text() == called_before
    assert (after.input_tokens, after.output_tokens) == (246, 90)


def test_exclusion_narrows_actual_final_prompt_dates_evidence_and_titles(engine, database_url):
    from hashlib import sha256

    from packages.storage.tests.test_research_repository import add_topic

    bundle, token, repo, run = seed(engine, database_url)
    excluded, excluded_bundle = add_topic(engine, run.workspace_id, "80% 2026-10-19 제외 합성 자료")
    selector_prompts = []
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        if name == "search_evidence":
            payload = {"queries": ["80%"]}
        elif name == "classify_relevance":
            prompt = messages[-1].parts[0].content
            selector_prompts.append(prompt)
            parsed = json.loads(prompt)
            assert len(parsed["sources"]) == 2
            payload = {
                "decisions": list(
                    reversed(
                        [
                            {
                                "snapshot_id": s["snapshot_id"],
                                "decision": "exclude"
                                if s["snapshot_id"] == str(excluded)
                                else "uncertain",
                            }
                            for s in parsed["sources"]
                        ]
                    )
                )
            }
        else:
            parsed = json.loads(messages[-1].parts[0].content)
            assert len(parsed["sources"]) == 1 and parsed["sources"][0]["snapshot_id"] != str(
                excluded
            )
            schema = json.dumps(info.output_tools[0].parameters_json_schema)
            assert "2026-10-19" not in schema and "timeline" not in schema
            payload = output(bundle, classified=True, core=True)
        return ModelResponse(
            parts=[ToolCallPart(name, payload)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert (
        after.status == "completed"
        and excluded not in after.snapshot_ids
        and len(after.snapshot_ids) == 1
    )
    assert after.result.canvas.research.evidence == (bundle,)
    assert set(after.result.source_titles) == {bundle.document.document_id}
    assert excluded_bundle.document.document_id not in after.result.source_titles
    inspector = client(database_url)
    try:
        metadata = inspector.list_workflow_steps(f"research-{run.run_id}", load_output=False)
        assert [(s["function_id"], s["function_name"]) for s in metadata] == EXPECTED
        workflow = inspector.list_workflows(
            workflow_ids=[f"research-{run.run_id}"], load_input=False, load_output=False
        )[0]
        assert workflow.attributes == {
            "issuedigest_select_v9_started": True,
            "issuedigest_select_v9_prompt_sha256": sha256(selector_prompts[0].encode()).hexdigest(),
        }
    finally:
        inspector.destroy()
    assert calls == ["search_evidence", "classify_relevance", "answer"]


def test_apply_commit_crash_reopens_original_candidates_after_real_narrowing(
    engine, database_url, tmp_path
):
    import os
    import signal
    import subprocess
    import sys

    from packages.storage.tests.test_research_repository import add_topic

    bundle, token, repo, run = seed(engine, database_url)
    excluded, _ = add_topic(engine, run.workspace_id, "80% 제외 자료 2026-10-19")
    script = CRASH_V9.replace(
        "'decision':'retain'",
        "'decision':('exclude' if s['snapshot_id']==os.environ['EXCLUDED'] else 'retain')",
    )
    marker = tmp_path / "narrowed-model-calls"
    env = {
        **os.environ,
        "ISSUEDIGEST_TEST_DATABASE_URL": database_url,
        "SYNTHETIC_OUTPUT": json.dumps(output(bundle, classified=True, core=True)),
        "CALL_MARKER": str(marker),
        "CRASH_POINT": "apply-commit",
        "EXCLUDED": str(excluded),
        "PYDANTIC_AI_NO_BANNER": "1",
    }
    result = subprocess.run(
        [sys.executable, "-c", script], env=env, capture_output=True, timeout=20
    )
    assert result.returncode == -signal.SIGKILL, result.stderr.decode()[-1000:]
    before = repo.get_run(token, run.workspace_id, run.run_id)
    assert len(before.snapshot_ids) == 1 and excluded not in before.snapshot_ids
    called_before = marker.read_text()
    calls = []

    def respond(messages, info):
        name = info.output_tools[0].name
        calls.append(name)
        assert name == "answer"
        assert len(json.loads(messages[-1].parts[0].content)["sources"]) == 1
        return ModelResponse(
            parts=[ToolCallPart(name, output(bundle, classified=True, core=True))],
            usage=RequestUsage(input_tokens=123, output_tokens=45),
        )

    run_worker(database_url, model=FunctionModel(respond), once=True)
    after = repo.get_run(token, run.workspace_id, run.run_id)
    assert after.status == "completed" and after.snapshot_ids == before.snapshot_ids
    assert after.result.canvas.research.evidence == (bundle,)
    assert (after.input_tokens, after.output_tokens) == (369, 135)
    assert calls == ["answer"] and marker.read_text() == called_before
