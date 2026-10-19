"""Strict planning and cumulative budget boundaries, with synthetic model requests only."""

import importlib
import json
from uuid import uuid4

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from test_research_v6 import proposal


def profile():
    return importlib.import_module("issuedigest_agents.research_v7")


def synthetic(output, inspect=None):
    calls = []

    def respond(messages, info):
        calls.append(info.output_tools[0].name)
        if inspect:
            inspect(info)
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    return FunctionModel(respond), calls


def test_planner_sends_only_strict_queries_tool_and_untrusted_question_context(sync_model_loop):
    v7 = profile()

    def inspect(info):
        assert len(info.output_tools) == 1
        tool = info.output_tools[0]
        assert tool.name == "search_evidence" and tool.strict is True
        assert set(tool.parameters_json_schema["properties"]) == {"queries"}
        assert tool.parameters_json_schema["required"] == ["queries"]
        assert tool.parameters_json_schema["additionalProperties"] is False

    model, calls = synthetic({"queries": ["합성 정책", "2026 목표"]}, inspect)
    prompt = v7.planning_prompt_v7("원문 질문 <instruction>", "이전 해석 " * 500)
    assert json.loads(prompt) == {
        "question": "원문 질문 <instruction>",
        "prior_interpretation_context": ("이전 해석 " * 500)[:1500],
        "prior_interpretation_context_truncated": True,
    }
    result, inputs, outputs = v7.run_planner_v7(v7.create_planner_v7(model), prompt)
    assert result.queries == ("합성 정책", "2026 목표")
    assert inputs >= 0 and outputs >= 0 and calls == ["search_evidence"]


@pytest.mark.parametrize(
    "queries", [[], ["가"] * 4, [""], [" "], ["가" * 65], ["a\n"], ["\ufeff"], [123]]
)
def test_strict_plan_rejects_invalid_literal_queries(queries):
    with pytest.raises(ValidationError):
        profile().SearchPlanV7.model_validate({"queries": queries})


def test_planner_does_not_repair_invalid_output(sync_model_loop):
    v7 = profile()
    model, calls = synthetic({"queries": [" "]})
    with pytest.raises(UnexpectedModelBehavior):
        v7.run_planner_v7(v7.create_planner_v7(model), v7.planning_prompt_v7("합성"))
    assert calls == ["search_evidence"]


def test_planner_rejects_oversize_without_request(sync_model_loop):
    v7 = profile()
    model, calls = synthetic({"queries": ["합성"]})
    with pytest.raises(ValueError):
        v7.planning_prompt_v7("가" * 8000)
    with pytest.raises(ValueError):
        v7.run_planner_v7(v7.create_planner_v7(model), "가" * 8000)
    assert calls == []


@pytest.mark.parametrize(
    "inputs,outputs", [(-1, 0), (True, 0), (1.5, 0), (0, -1), (0, True), (0, 501), (8000, 1)]
)
def test_final_rejects_fake_or_overbudget_planner_usage_before_request(
    sync_model_loop, inputs, outputs
):
    v7 = profile()
    selected, response = proposal()
    model, calls = synthetic(response)
    with pytest.raises(ValueError):
        v7.model_prompt_v7(
            "합성", (selected,), prior_input_tokens=inputs, prior_output_tokens=outputs
        )
    with pytest.raises(ValueError):
        v7.run_agent_v7(
            v7.create_agent_v7(model), "{}", prior_input_tokens=inputs, prior_output_tokens=outputs
        )
    assert calls == []


def test_final_reuses_v6_provider_and_builds_exact_v7_classification(sync_model_loop):
    v7 = profile()
    selected, response = proposal()
    model, calls = synthetic(response)
    prompt = v7.model_prompt_v7(
        "합성", (selected,), prior_input_tokens=500, prior_output_tokens=100
    )
    result, inputs, outputs = v7.run_agent_v7(
        v7.create_agent_v7(model), prompt, prior_input_tokens=500, prior_output_tokens=100
    )
    assert inputs + outputs + 600 <= 24000 and outputs <= 2000
    canvas = v7.build_canvas_v7(uuid4(), selected[1].document.workspace_id, (selected,), result)
    assert canvas.research.claims[0].text == "제공 자료에 따르면, 같은 방향입니다."
    assert canvas.research.claims[0].derivation.method_version == "research-v7"
    assert canvas.research.support_reviews[0].reviewer_id == "issuedigest-research-v7"
    assert calls == ["answer"]


def test_final_rejects_prompt_above_dynamic_remaining_budget_without_request(sync_model_loop):
    v7 = profile()
    selected, response = proposal()
    model, calls = synthetic(response)
    with pytest.raises(ValueError):
        v7.run_agent_v7(
            v7.create_agent_v7(model), "x" * 9000, prior_input_tokens=7000, prior_output_tokens=500
        )
    assert calls == []


def test_planner_raw_normalized_envelopes_and_actual_request_settings(sync_model_loop):
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    v7 = profile()
    tool = v7._planner_tools_v7()[0]
    raw = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    normalized = OpenAIJsonSchemaTransformer(raw, strict=True).walk()
    for schema in (raw, normalized):
        assert set(schema["properties"]) == {"queries"}
        assert schema["required"] == ["queries"] and schema["additionalProperties"] is False
        assert schema["properties"]["queries"]["minItems"] == 1
        assert schema["properties"]["queries"]["maxItems"] == 3
    # OpenAI normalizes away string length keywords; runtime validation retains them.
    assert raw["properties"]["queries"]["items"]["minLength"] == 1
    assert raw["properties"]["queries"]["items"]["maxLength"] == 64

    def inspect(info):
        assert info.instructions == v7.PLANNER_INSTRUCTIONS_V7
        assert info.function_tools == [] and info.allow_text_output is False
        assert info.model_settings == {"openai_store": False, "max_tokens": 500, "timeout": 15}

    model, _ = synthetic({"queries": ["합성"]}, inspect)
    prompt = v7.planning_prompt_v7("합성")
    assert len(prompt.encode()) + v7.PLANNER_STATIC_BYTES_V7 + 2048 + 500 <= 8000
    v7.run_planner_v7(v7.create_planner_v7(model), prompt)


@pytest.mark.parametrize("planner", [True, False])
@pytest.mark.parametrize("inputs,outputs", [(-1, 0), (0, -1), (16000, 1), (100, 2501)])
def test_invalid_reported_usage_stops_after_one_request(sync_model_loop, planner, inputs, outputs):
    from pydantic_ai.exceptions import UsageLimitExceeded
    from pydantic_ai.usage import RequestUsage

    v7 = profile()
    selected, response = proposal()
    calls = []

    def respond(messages, info):
        calls.append(True)
        data = {"queries": ["합성"]} if planner else response
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, data)],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    agent = (v7.create_planner_v7 if planner else v7.create_agent_v7)(FunctionModel(respond))
    if planner:
        with pytest.raises((ValueError, UsageLimitExceeded)):
            v7.run_planner_v7(agent, v7.planning_prompt_v7("합성"))
    else:
        prompt = v7.model_prompt_v7(
            "합성", (selected,), prior_input_tokens=7500, prior_output_tokens=500
        )
        with pytest.raises((ValueError, UsageLimitExceeded)):
            v7.run_agent_v7(agent, prompt, prior_input_tokens=7500, prior_output_tokens=500)
    assert calls == [True]


def test_final_request_uses_remaining_budget_and_45_second_2000_output_limit(sync_model_loop):
    v7 = profile()
    selected, response = proposal()

    def inspect(info):
        assert info.model_settings == {"openai_store": False, "max_tokens": 2000, "timeout": 45}
        assert info.instructions == v7.SYSTEM_INSTRUCTIONS_V7
        assert info.function_tools == [] and info.allow_text_output is False

    model, calls = synthetic(response, inspect)
    prompt = v7.model_prompt_v7(
        "합성", (selected,), prior_input_tokens=500, prior_output_tokens=100
    )
    v7.run_agent_v7(
        v7.create_agent_v7(model), prompt, prior_input_tokens=500, prior_output_tokens=100
    )
    assert calls == ["answer"]


@pytest.mark.parametrize("mutation", ["unknown-id", "date", "old-category", "blank"])
def test_final_malformed_provider_output_never_repairs(sync_model_loop, mutation):
    v7 = profile()
    selected, response = proposal()
    if mutation == "unknown-id":
        response["core_answer"]["citation_ids"] = [str(uuid4())]
    if mutation == "date":
        response["core_answer"]["event_date"] = "2026-01-01"
    if mutation == "old-category":
        response["core_answer"]["category"] = "documented"
    if mutation == "blank":
        response["core_answer"]["text"] = "\ufeff\u0085"
    model, calls = synthetic(response)
    prompt = v7.model_prompt_v7(
        "합성", (selected,), prior_input_tokens=500, prior_output_tokens=100
    )
    with pytest.raises(UnexpectedModelBehavior):
        v7.run_agent_v7(
            v7.create_agent_v7(model), prompt, prior_input_tokens=500, prior_output_tokens=100
        )
    assert calls == ["answer"]


@pytest.mark.parametrize("outcome", ["insufficient_evidence", "clarification_needed"])
def test_nonanswer_uses_same_private_canvas_contract(sync_model_loop, outcome):
    v7 = profile()
    selected, _ = proposal()

    def respond(messages, info):
        return ModelResponse(
            parts=[
                ToolCallPart(
                    outcome, {"outcome": outcome, "message": "제공 자료의 한계", "modules": []}
                )
            ]
        )

    prompt = v7.model_prompt_v7(
        "합성", (selected,), prior_input_tokens=500, prior_output_tokens=100
    )
    result, _, _ = v7.run_agent_v7(
        v7.create_agent_v7(FunctionModel(respond)),
        prompt,
        prior_input_tokens=500,
        prior_output_tokens=100,
    )
    canvas = v7.build_canvas_v7(uuid4(), selected[1].document.workspace_id, (selected,), result)
    assert canvas.revision.draft.outcome == outcome
    assert canvas.research.claims == () and canvas.research.support_reviews == ()


def test_actual_python_v7_fixtures_match_stored_client_inputs():
    from v7_fixture import ASTRAL_FIXTURE, FIXTURE, build_astral_fixture, build_fixture

    assert build_fixture() == json.loads(FIXTURE.read_text())
    assert build_astral_fixture() == json.loads(ASTRAL_FIXTURE.read_text())


@pytest.mark.parametrize(
    "mutation", ["missing", "mixed", "reviewer", "core", "prefix", "unicode", "timestamp", "date"]
)
def test_v7_canonical_rejects_missing_mixed_forged_prefix_unicode_and_dates(mutation):
    from issuedigest_domain.research_journey import ResearchResult
    from v7_fixture import build_fixture

    value = build_fixture()["result"]
    research = value["canvas"]["research"]
    if mutation == "missing":
        research["support_reviews"] = []
    if mutation == "mixed":
        research["claims"][0]["derivation"]["method_version"] = "research-v6"
    if mutation == "reviewer":
        research["support_reviews"][0]["reviewer_id"] = "issuedigest-research-v6"
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
        ResearchResult.model_validate(value)


def test_planner_preserves_question_and_marks_only_optional_korean_parent_truncation():
    v7 = profile()
    question = "합성 정책의 2026년 목표는?"
    payload = json.loads(v7.planning_prompt_v7(question, "가" * 1500))
    assert payload["question"] == question
    assert payload["prior_interpretation_context_truncated"] is True
    assert 0 < len(payload["prior_interpretation_context"]) < 1500
    assert payload["prior_interpretation_context"] == "가" * len(
        payload["prior_interpretation_context"]
    )
    assert (
        len(v7.planning_prompt_v7(question, "가" * 1500).encode())
        <= v7.PLANNER_PROMPT_BYTE_LIMIT_V7
    )


def test_planner_counts_actual_tool_envelope_before_request(sync_model_loop, monkeypatch):
    from pydantic_ai import ToolOutput

    v7 = profile()
    tools = v7._planner_tools_v7()
    monkeypatch.setattr(
        v7,
        "_planner_tools_v7",
        lambda: [
            ToolOutput(tools[0].output, name="search_evidence", description="x" * 8000, strict=True)
        ],
    )
    model, calls = synthetic({"queries": ["합성"]})
    with pytest.raises(ValueError):
        v7.run_planner_v7(v7.create_planner_v7(model), v7.planning_prompt_v7("합성"))
    assert calls == []
