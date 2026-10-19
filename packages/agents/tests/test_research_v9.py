"""Synthetic final9 combined budget and historical byte contracts."""

import importlib
import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_v6 import proposal


def profile():
    import issuedigest_agents

    assert (Path(issuedigest_agents.__file__).parent / "research_v9.py").exists(), (
        "missing final9 implementation"
    )
    return importlib.import_module("issuedigest_agents.research_v9")


@pytest.mark.parametrize("prior,cap", [(0, 2000), (500, 2000), (501, 1999), (1000, 1500)])
def test_combined_prior_drives_actual_final_output_cap(sync_model_loop, prior, cap):
    v9 = profile()
    selected, response = proposal()
    calls = []

    def respond(messages, info):
        calls.append(info)
        assert info.model_settings == dict(openai_store=False, max_tokens=cap, timeout=45)
        return ModelResponse(
            parts=[ToolCallPart("answer", response)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    agent = v9.create_agent_v9(FunctionModel(respond))
    prompt = v9.model_prompt_v9(
        "합성", (selected,), prior_input_tokens=600, prior_output_tokens=prior
    )
    output, inputs, outputs = v9.run_agent_v9(
        agent, prompt, prior_input_tokens=600, prior_output_tokens=prior
    )
    canvas = v9.build_canvas_v9(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.research.claims[0].derivation.method_version == "research-v9"
    assert canvas.research.support_reviews[0].reviewer_id == "issuedigest-research-v9"
    assert (inputs, outputs) == (100, 50) and len(calls) == 1


@pytest.mark.parametrize(
    "inputs,outputs", [(True, 0), (0, True), (-1, 0), (0, -1), (0, 1001), (20000, 1)]
)
def test_combined_invalid_prior_is_rejected_before_provider(inputs, outputs):
    v9 = profile()
    selected, _ = proposal()
    with pytest.raises(ValueError):
        v9.model_prompt_v9(
            "합성", (selected,), prior_input_tokens=inputs, prior_output_tokens=outputs
        )


def test_final9_does_not_drop_whole_quotes_to_fit_dynamic_budget():
    v9 = profile()
    selected, _ = proposal()
    with pytest.raises(ValueError, match="budget"):
        v9.model_prompt_v9("합성", (selected,), prior_input_tokens=19000, prior_output_tokens=1000)


def test_frozen_v8_worker_is_actual_baseline_bytes():
    path = Path(__file__).parents[3] / "apps/worker/tests/fixtures/research_worker_v8.py"
    assert path.exists(), "missing historical v8 fixture"
    assert (
        sha256(path.read_bytes()).hexdigest()
        == "f81ce73041e29a000738e9f5d2523799f35d6cff915c26ad22b574eebaff0f95"
    )


def test_v9_actual_builder_fixtures():
    from v9_fixture import (
        ASTRAL_FIXTURE,
        FIXTURE,
        NONANSWER_FIXTURE,
        TIMELINE_FIXTURE,
        build_astral_fixture,
        build_fixture,
    )

    assert build_fixture() == json.loads(FIXTURE.read_text())
    assert build_astral_fixture() == json.loads(ASTRAL_FIXTURE.read_text())
    assert build_fixture(quote="2026-10-19 합성 발표", timeline=True) == json.loads(
        TIMELINE_FIXTURE.read_text()
    )
    assert build_fixture(outcome="insufficient_evidence") == json.loads(
        NONANSWER_FIXTURE.read_text()
    )


@pytest.mark.parametrize(
    "mutation", ["stripped", "mixed", "reviewer", "core", "prefix", "unicode", "timestamp", "date"]
)
def test_v9_exact_profile_preserves_canonical_guards(mutation):
    from issuedigest_domain.research_journey import ResearchResult
    from pydantic import ValidationError
    from v9_fixture import build_fixture

    value = build_fixture()["result"]
    research = value["canvas"]["research"]
    if mutation == "stripped":
        research["support_reviews"] = []
    if mutation == "mixed":
        research["claims"][0]["derivation"]["method_version"] = "research-v8"
    if mutation == "reviewer":
        research["support_reviews"][0]["reviewer_id"] = "issuedigest-research-v8"
    if mutation == "core":
        research["support_reviews"][0].update(scope="content", assessment="insufficient")
    if mutation == "prefix":
        research["claims"][0]["text"] = "없는기관에 따르면, 합성"
    if mutation == "unicode":
        research["claims"][0]["text"] = "제공 자료에 따르면, \ufeff\u0085"
    if mutation == "timestamp":
        research["support_reviews"][0]["reviewed_at"] = "2026-10-15T09:00:00.123456+09:00"
    if mutation == "date":
        research["claims"][0]["valid_period"] = {
            "start_date": "2026-01-01",
            "end_date": "2026-01-01",
        }
    with pytest.raises(ValidationError):
        ResearchResult.model_validate_json(json.dumps(value))


@pytest.mark.parametrize("dates", [(), ("2026-10-19",)])
def test_v9_reuses_exact_v8_raw_normalized_tools_and_instruction_bytes(sync_model_loop, dates):
    from issuedigest_agents import research_v8 as v8
    from issuedigest_agents.research_v6 import _provider_schema_bytes_v6
    from pydantic_ai.profiles.openai import openai_model_profile

    selected, response = proposal()
    v9 = profile()
    payload = json.loads(
        v9.model_prompt_v9("질문", (selected,), prior_input_tokens=600, prior_output_tokens=900)
    )
    if dates:
        payload["sources"][0]["citations"][0]["quote"] = "2026-10-19 발표"
    prompt = json.dumps(payload, ensure_ascii=False)
    ids = v8._prompt_citation_ids_v5(prompt)
    expected = _provider_schema_bytes_v6(v8._provider_tools_v8(ids, dates))

    def respond(messages, info):
        assert info.instructions == v8.SYSTEM_INSTRUCTIONS_V8 == v9.SYSTEM_INSTRUCTIONS_V9
        envelopes = [
            dict(
                type="function",
                name=t.name,
                description=t.description,
                strict=t.strict,
                parameters=t.parameters_json_schema,
            )
            for t in info.output_tools
        ]
        assert len(json.dumps(envelopes, ensure_ascii=False).encode()) == expected[1]
        assert ('"timeline"' in json.dumps(envelopes)) == bool(dates)
        assert info.model_settings["max_tokens"] == 1600
        assert info.function_tools == [] and not info.allow_text_output
        return ModelResponse(
            parts=[ToolCallPart("answer", response)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    agent = v9.create_agent_v9(FunctionModel(respond, profile=openai_model_profile("gpt-5.4-mini")))
    v9.run_agent_v9(agent, prompt, prior_input_tokens=600, prior_output_tokens=900)
    assert v9.STATIC_INPUT_BYTES_V9 == v8.STATIC_INPUT_BYTES_V8


def test_v9_output_over_dynamic_cap_fails_with_one_response(sync_model_loop):
    from pydantic_ai.exceptions import UsageLimitExceeded

    v9 = profile()
    selected, response = proposal()
    calls = []

    def respond(messages, info):
        calls.append(True)
        return ModelResponse(
            parts=[ToolCallPart("answer", response)],
            usage=RequestUsage(input_tokens=100, output_tokens=1501),
        )

    agent = v9.create_agent_v9(FunctionModel(respond))
    prompt = v9.model_prompt_v9(
        "질문", (selected,), prior_input_tokens=600, prior_output_tokens=1000
    )
    with pytest.raises((ValueError, UsageLimitExceeded)):
        v9.run_agent_v9(agent, prompt, prior_input_tokens=600, prior_output_tokens=1000)
    assert calls == [True]


def test_standalone_selector_source_bytes_remain_frozen():
    import issuedigest_agents.relevance_selection as sdk

    assert (
        sha256(Path(sdk.__file__).read_bytes()).hexdigest()
        == "c194b9314ed4158976084b5e240160876c0c3ba6e23931ddf7fa1abd8b809212"
    )


@pytest.mark.parametrize("model", [None, object(), "openai:gpt-5.4-mini"])
def test_v9_factory_rejects_missing_or_unborrowed_model_before_client_creation(monkeypatch, model):
    v9 = profile()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("v9 factory cannot delegate an invalid borrowed model")

    monkeypatch.setattr(v9, "_create_classified_agent", forbidden)
    with pytest.raises(ValueError, match="model"):
        v9.create_agent_v9(model)
    assert calls == []


def test_v9_cannot_be_relabelled_as_public_v1_or_v2():
    from issuedigest_domain.public_briefings import PublicBriefingPlan
    from pydantic import ValidationError
    from v9_fixture import build_fixture

    from conftest import public_plan_data

    value = public_plan_data()
    value["canvas"] = build_fixture()["result"]["canvas"]
    value["canvas"]["research"]["evidence"][0]["document"]["canonical_url"] = value["sources"][0][
        "official_url"
    ]
    with pytest.raises(ValidationError, match="Unsupported public Canvas scope"):
        PublicBriefingPlan.model_validate(value)
