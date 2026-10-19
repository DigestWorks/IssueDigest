"""Synthetic v8 source-date opportunity boundaries; no semantic model evaluation."""

import importlib
import json
from datetime import date
from uuid import UUID, uuid4

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_v6 import proposal


def profile():
    return importlib.import_module("issuedigest_agents.research_v8")


def setup(quote=None):
    from issuedigest_agents.research_v7 import model_prompt_v7

    selected, response = proposal()
    payload = json.loads(
        model_prompt_v7(
            "2026-01-01 질문",
            (selected,),
            "2026-02-02 부모",
            prior_input_tokens=500,
            prior_output_tokens=100,
        )
    )
    if quote is not None:
        payload["sources"][0]["citations"][0]["quote"] = quote
    return selected, response, payload


def execute(response, payload, inspect=None, usage=None):
    v8 = profile()
    calls = []

    def respond(messages, info):
        calls.append(info.output_tools[0].name)
        if inspect:
            inspect(info)
        return ModelResponse(
            parts=[ToolCallPart(response["outcome"], response)],
            usage=usage or RequestUsage(input_tokens=100, output_tokens=50),
        )

    agent = v8.create_agent_v8(FunctionModel(respond))

    def result():
        return v8.run_agent_v8(
            agent,
            json.dumps(payload, ensure_ascii=False),
            prior_input_tokens=500,
            prior_output_tokens=100,
        )

    return result, calls


def timeline(response, event_date):
    response["details"] = [
        {
            "kind": "timeline",
            "title": "정확 날짜",
            "claims": [
                {
                    **response["core_answer"],
                    "assessment": "source_statement",
                    "event_date": event_date,
                }
            ],
        }
    ]


def test_zero_quote_dates_removes_timeline_from_schema_and_runtime(sync_model_loop):
    _, response, payload = setup("10월 둘째 주와 연말 예정. 2026-02-30 ２０２６-01-01")
    payload["sources"][0]["title"] = "2026-03-03 제목"
    timeline(response, "2026-01-01")

    def inspect(info):
        schema = json.dumps(info.output_tools[0].parameters_json_schema)
        assert '"timeline"' not in schema and '"event_date"' not in schema
        assert len(info.output_tools) == 3 and all(t.strict for t in info.output_tools)

    run, calls = execute(response, payload, inspect)
    with pytest.raises(UnexpectedModelBehavior):
        run()
    assert calls == ["answer"]


@pytest.mark.parametrize(
    "value,valid",
    [
        ("2026-10-19", True),
        ("2026-10-20", False),
        ("2026-02-30", False),
        ("2026-10-19T00:00:00Z", False),
        (20261019, False),
    ],
)
def test_exact_date_enum_validates_actual_runtime_without_retry(sync_model_loop, value, valid):
    _, response, payload = setup("2026-10-19 발표, 2026-02-30 잘못된 날짜")
    timeline(response, value)
    run, calls = execute(response, payload)
    if valid:
        output, _, _ = run()
        assert output.modules[1].claims[0].event_date == date(2026, 10, 19)
    else:
        with pytest.raises(UnexpectedModelBehavior):
            run()
    assert calls == ["answer"]


def test_candidates_follow_source_citation_literal_order_dedupe_cap_and_calendar():
    _, _, payload = setup("2026-02-30 2024-02-29 2026-01-02 2024-02-29")
    payload["sources"][0]["citations"].append(
        {"citation_id": str(uuid4()), "quote": " ".join(f"2026-03-{i:02}" for i in range(1, 20))}
    )
    expected = ("2024-02-29", "2026-01-02", *(f"2026-03-{i:02}" for i in range(1, 15)))
    assert profile()._prompt_dates_v8(json.dumps(payload)) == expected


def test_global_date_attached_to_different_citation_is_rejected_by_canvas(sync_model_loop):
    selected, response, payload = setup()
    payload["sources"][0]["citations"].append({"citation_id": str(uuid4()), "quote": "2026-10-19"})
    timeline(response, "2026-10-19")
    output, _, _ = execute(response, payload)[0]()
    with pytest.raises(ValueError, match="Timeline date absent"):
        profile().build_canvas_v8(uuid4(), selected[1].document.workspace_id, (selected,), output)


def test_derived_schema_and_runtime_keep_core_details_nonanswer_strict_bounds(sync_model_loop):
    v8 = profile()
    _, response, payload = setup("2026-10-19")
    ids = tuple(c["citation_id"] for c in payload["sources"][0]["citations"])
    tools = v8._provider_tools_v8(ids, ("2026-10-19",))
    for mutation in (
        "extra-core",
        "extra-answer",
        "assessment",
        "wrong-id",
        "too-many-details",
        "empty-comparison",
    ):
        value = json.loads(json.dumps(response))
        if mutation == "extra-core":
            value["core_answer"]["event_date"] = "2026-10-19"
        if mutation == "extra-answer":
            value["modules"] = []
        if mutation == "assessment":
            value["core_answer"]["assessment"] = "source_statement"
        if mutation == "wrong-id":
            value["core_answer"]["citation_ids"] = [str(uuid4())]
        if mutation == "too-many-details":
            value["details"] = [{"kind": "comparison", "title": "합성", "claims": []}] * 3
        if mutation == "empty-comparison":
            value["details"] = [{"kind": "comparison", "title": "합성", "claims": []}]
        with pytest.raises(ValidationError):
            tools[0].output.model_validate(value)
    for tool in tools[1:]:
        good = {"outcome": tool.name, "message": "자료 부족", "modules": []}
        assert tool.output.model_validate(good)
        with pytest.raises(ValidationError):
            tool.output.model_validate({**good, "core_answer": response["core_answer"]})


def test_worst_case_static_includes_raw_normalized_100_ids_16_dates():
    v8 = profile()
    from issuedigest_agents.research_v6 import _provider_schema_bytes_v6

    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    dates = tuple(f"2026-10-{i:02}" for i in range(1, 17))
    sizes = _provider_schema_bytes_v6(v8._provider_tools_v8(ids, dates))
    assert v8.STATIC_INPUT_BYTES_V8 == len(v8.SYSTEM_INSTRUCTIONS_V8.encode()) + max(sizes)
    for count in (0, 1, 2, 15, 16):
        assert max(_provider_schema_bytes_v6(v8._provider_tools_v8(ids, dates[:count]))) <= max(
            sizes
        )
    assert 24000 - 8000 - v8.STATIC_INPUT_BYTES_V8 - 2048 - 2000 > 0


@pytest.mark.parametrize("inputs,outputs", [(-1, 0), (True, 0), (0, True), (0, 501), (8000, 1)])
def test_invalid_planner_usage_prevents_prompt_and_provider(inputs, outputs):
    v8 = profile()
    selected, _, _ = setup()
    with pytest.raises(ValueError):
        v8.model_prompt_v8(
            "합성", (selected,), prior_input_tokens=inputs, prior_output_tokens=outputs
        )
    with pytest.raises(ValueError):
        v8.run_agent_v8(
            v8.create_agent_v8(FunctionModel(lambda messages, info: None)),
            "{}",
            prior_input_tokens=inputs,
            prior_output_tokens=outputs,
        )


@pytest.mark.parametrize(
    "inputs,outputs", [(True, 45), (100, False), (-1, 0), (0, -1), (24000, 1), (100, 2001)]
)
def test_invalid_raw_usage_never_retries(sync_model_loop, inputs, outputs):
    from pydantic_ai.exceptions import UsageLimitExceeded

    _, response, payload = setup()
    run, calls = execute(
        response, payload, usage=RequestUsage(input_tokens=inputs, output_tokens=outputs)
    )
    with pytest.raises((ValueError, UsageLimitExceeded)):
        run()
    assert calls == ["answer"]


def test_v8_canonical_metadata_is_exact(sync_model_loop):
    selected, response, payload = setup()

    def inspect(info):
        assert info.model_settings == {"openai_store": False, "max_tokens": 2000, "timeout": 45}
        assert info.instructions == profile().SYSTEM_INSTRUCTIONS_V8
        assert info.function_tools == [] and info.allow_text_output is False

    output, _, _ = execute(response, payload, inspect)[0]()
    canvas = profile().build_canvas_v8(
        uuid4(), selected[1].document.workspace_id, (selected,), output
    )
    assert canvas.research.claims[0].derivation.method_version == "research-v8"
    assert canvas.research.support_reviews[0].reviewer_id == "issuedigest-research-v8"


def test_actual_normalized_envelope_matches_preflight_and_enum_order(sync_model_loop):
    from issuedigest_agents.research_v6 import _provider_schema_bytes_v6
    from pydantic_ai.profiles.openai import openai_model_profile

    v8 = profile()
    _, response, payload = setup("2026-10-19 2024-02-29 2026-10-19")
    prompt = json.dumps(payload, ensure_ascii=False)
    ids = tuple(c["citation_id"] for s in payload["sources"] for c in s["citations"])
    tools = v8._provider_tools_v8(ids, v8._prompt_dates_v8(prompt))
    expected = _provider_schema_bytes_v6(tools)
    calls = []

    def respond(messages, info):
        calls.append(True)
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
        answer = info.output_tools[0].parameters_json_schema
        assert answer["additionalProperties"] is False
        assert set(answer["required"]) == {
            "outcome",
            "summary_title",
            "core_answer",
            "additional_summary_claims",
            "details",
        }
        event = answer["$defs"]["ProviderTimelineClaimV8"]["properties"]["event_date"]
        assert event["enum"] == ["2026-10-19", "2024-02-29"]
        assert answer["$defs"]["ProviderCitationIdV6"]["enum"] == list(ids)
        assert (
            len(prompt.encode())
            + len(v8.SYSTEM_INSTRUCTIONS_V8.encode())
            + max(expected)
            + 2048
            + 2000
            + 600
            <= 24000
        )
        return ModelResponse(parts=[ToolCallPart("answer", response)])

    agent = v8.create_agent_v8(FunctionModel(respond, profile=openai_model_profile("gpt-5.4-mini")))
    v8.run_agent_v8(agent, prompt, prior_input_tokens=500, prior_output_tokens=100)
    assert calls == [True]


def test_dynamic_and_actual_envelope_overflow_never_calls_provider(sync_model_loop, monkeypatch):
    from pydantic_ai import ToolOutput

    v8 = profile()
    selected, response, payload = setup()
    run, calls = execute(response, payload)
    with pytest.raises(ValueError):
        v8.model_prompt_v8(
            "가" * 24000, (selected,), prior_input_tokens=7500, prior_output_tokens=500
        )
    with pytest.raises(ValueError):
        v8.run_agent_v8(
            v8.create_agent_v8(FunctionModel(lambda messages, info: None)),
            "x" * 9000,
            prior_input_tokens=7500,
            prior_output_tokens=500,
        )
    original = v8._provider_tools_v8
    monkeypatch.setattr(
        v8,
        "_provider_tools_v8",
        lambda ids, dates: [
            ToolOutput(t.output, name=t.name, description="x" * 24000, strict=True)
            for t in original(ids, dates)
        ],
    )
    with pytest.raises(ValueError, match="provider input"):
        run()
    assert calls == []


@pytest.mark.parametrize("mutation", ["extra", "duplicate", "unknown-id", "invalid-json"])
def test_bad_prompt_cannot_expand_date_or_citation_candidates(sync_model_loop, mutation):
    _, response, payload = setup("2026-10-19")
    if mutation == "extra":
        payload["sources"][0]["proposed_on"] = "2026-10-20"
    if mutation == "duplicate":
        payload["sources"][0]["citations"].append(payload["sources"][0]["citations"][0].copy())
    if mutation == "unknown-id":
        payload["sources"][0]["citations"][0]["citation_id"] = "unknown"
    if mutation == "invalid-json":
        with pytest.raises(ValueError):
            profile()._prompt_dates_v8("{")
        return
    run, calls = execute(response, payload)
    with pytest.raises(ValueError):
        run()
    assert calls == []


@pytest.mark.parametrize("outcome", ["insufficient_evidence", "clarification_needed"])
def test_nonanswer_function_model_builds_unchanged_empty_canvas(sync_model_loop, outcome):
    selected, _, payload = setup()
    response = {"outcome": outcome, "message": "제공 자료의 한계", "modules": []}
    output, _, _ = execute(response, payload)[0]()
    canvas = profile().build_canvas_v8(
        uuid4(), selected[1].document.workspace_id, (selected,), output
    )
    assert canvas.revision.draft.outcome == outcome
    assert canvas.research.claims == canvas.research.support_reviews == ()


def test_shared_python_v8_fixtures_reproduce_actual_builder():
    from v8_fixture import (
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
    "mutation", ["missing", "mixed", "reviewer", "core", "prefix", "unicode", "timestamp", "date"]
)
def test_v8_canonical_rejects_forged_mixed_missing_prefix_unicode_dates(mutation):
    from issuedigest_domain.research_journey import ResearchResult
    from v8_fixture import build_fixture

    value = build_fixture()["result"]
    research = value["canvas"]["research"]
    if mutation == "missing":
        research["support_reviews"] = []
    if mutation == "mixed":
        research["claims"][0]["derivation"]["method_version"] = "research-v7"
    if mutation == "reviewer":
        research["support_reviews"][0]["reviewer_id"] = "issuedigest-research-v7"
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


def test_historical_v7_worker_fixture_is_exact_deployed_source():
    import hashlib
    from pathlib import Path

    path = Path(__file__).parents[3] / "apps/worker/tests/fixtures/research_worker_v7.py"
    assert (
        hashlib.sha256(path.read_bytes()).hexdigest()
        == "fe9e76bb414eedd5de3ca246e2ebf39fc7dea709a08b3ff98940bcd96529ae8e"
    )


def test_actual_100_citations_16_dates_overflow_stops_before_provider(sync_model_loop):
    v8 = profile()
    _, response, payload = setup()
    ids = [str(UUID(int=i, version=4)) for i in range(1, 101)]
    payload["sources"] = [
        {
            **payload["sources"][0],
            "title": "합성",
            "citations": [{"citation_id": cid, "quote": "합성"} for cid in ids[start : start + 25]],
        }
        for start in range(0, 100, 25)
    ]
    payload["sources"][0]["citations"][0]["quote"] = " ".join(
        f"2026-10-{i:02}" for i in range(1, 17)
    )
    prompt = json.dumps(payload, ensure_ascii=False)
    assert len(v8._prompt_dates_v8(prompt)) == 16
    assert len(v8._prompt_citation_ids_v5(prompt)) == 100
    assert len(prompt.encode()) == 8480
    run, calls = execute(response, payload)
    with pytest.raises(ValueError, match="provider input"):
        run()
    assert calls == []


def test_frozen_v6_v7_provider_prompt_instruction_goldens():
    import hashlib

    from issuedigest_agents import research_v6 as v6
    from issuedigest_agents import research_v7 as v7
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema
    from test_research_profile_compatibility import prompt_sources

    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    raw, normalized = [], []
    for tool in v6._provider_tools_v6(ids):
        schema = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
        envelope = dict(
            type="function",
            name=tool.name,
            description=tool.description,
            strict=True,
            parameters=schema,
        )
        raw.append(envelope)
        normalized.append(
            {**envelope, "parameters": OpenAIJsonSchemaTransformer(schema, strict=True).walk()}
        )
    assert v6._provider_schema_bytes_v6(v6._provider_tools_v6(ids)) == (8092, 7952)
    for value, digest in [
        (raw, "1c8fa45e1c415e4c395d08c9953703ff83e1ffd2d50ee51f1d566fa73237b700"),
        (normalized, "15adddacdb4e91553d9f34ec567f32d963f77ee9eede267d8d180cc80f42f6e6"),
    ]:
        assert hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest() == digest
    for instructions in (v6.SYSTEM_INSTRUCTIONS_V6, v7.SYSTEM_INSTRUCTIONS_V7):
        assert (
            hashlib.sha256(instructions.encode()).hexdigest()
            == "b6ae1e1905a8fc0a9199012b1eff06eb70b5606871ebed5ed7d038c5d9334eae"
        )
    args = ("목표와 실적 및 전망을 비교해 주세요.", prompt_sources(5), "이전 해석")
    prompts = [
        v6.model_prompt_v6(*args),
        v7.model_prompt_v7(*args, prior_input_tokens=500, prior_output_tokens=100),
    ]
    for prompt in prompts:
        assert len(prompt.encode()) == 3124
        assert (
            hashlib.sha256(prompt.encode()).hexdigest()
            == "3acb7825a1083226885c4e0f7ee07d7bb887a34278cba1f7dd687dd7d21a44c8"
        )
