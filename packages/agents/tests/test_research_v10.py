"""Synthetic final10 combined budget and historical byte contracts."""

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

    assert (Path(issuedigest_agents.__file__).parent / "research_v10.py").exists(), (
        "missing final10 implementation"
    )
    return importlib.import_module("issuedigest_agents.research_v10")


@pytest.mark.parametrize("prior,cap", [(0, 2000), (500, 2000), (501, 1999), (1000, 1500)])
def test_combined_prior_drives_actual_final_output_cap(sync_model_loop, prior, cap):
    v10 = profile()
    selected, response = proposal()
    calls = []

    def respond(messages, info):
        calls.append(info)
        assert info.model_settings == dict(openai_store=False, max_tokens=cap, timeout=45)
        return ModelResponse(
            parts=[ToolCallPart("answer", response)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    agent = v10.create_agent_v10(FunctionModel(respond))
    prompt = v10.model_prompt_v10(
        "합성", (selected,), prior_input_tokens=600, prior_output_tokens=prior
    )
    output, inputs, outputs = v10.run_agent_v10(
        agent, prompt, prior_input_tokens=600, prior_output_tokens=prior
    )
    canvas = v10.build_canvas_v10(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.research.claims[0].derivation.method_version == "research-v10"
    assert canvas.research.support_reviews[0].reviewer_id == "issuedigest-research-v10"
    assert (inputs, outputs) == (100, 50) and len(calls) == 1


@pytest.mark.parametrize(
    "inputs,outputs", [(True, 0), (0, True), (-1, 0), (0, -1), (0, 1001), (20000, 1)]
)
def test_combined_invalid_prior_is_rejected_before_provider(inputs, outputs):
    v10 = profile()
    selected, _ = proposal()
    with pytest.raises(ValueError):
        v10.model_prompt_v10(
            "합성", (selected,), prior_input_tokens=inputs, prior_output_tokens=outputs
        )


def test_final10_does_not_drop_whole_quotes_to_fit_dynamic_budget():
    v10 = profile()
    selected, _ = proposal()
    with pytest.raises(ValueError, match="budget"):
        v10.model_prompt_v10(
            "합성", (selected,), prior_input_tokens=19000, prior_output_tokens=1000
        )


def test_frozen_v9_worker_is_actual_baseline_bytes():
    path = Path(__file__).parents[3] / "apps/worker/tests/fixtures/research_worker_v9.py"
    assert path.exists(), "missing historical v9 fixture"
    assert (
        sha256(path.read_bytes()).hexdigest()
        == "4cb64e39c754ac4e08f4ae347bedd74ea08b7d3346dc5cdf0087cf0ace860d77"
    )


def test_v10_actual_builder_fixtures():
    from v10_fixture import (
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
def test_v10_exact_profile_preserves_canonical_guards(mutation):
    from issuedigest_domain.research_journey import ResearchResult
    from pydantic import ValidationError
    from v10_fixture import build_fixture

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
def test_v10_reuses_exact_v8_tools_and_extends_frozen_instructions(sync_model_loop, dates):
    from issuedigest_agents import research_v8 as v8
    from issuedigest_agents.research_v6 import _provider_schema_bytes_v6
    from pydantic_ai.profiles.openai import openai_model_profile

    selected, response = proposal()
    v10 = profile()
    payload = json.loads(
        v10.model_prompt_v10("질문", (selected,), prior_input_tokens=600, prior_output_tokens=900)
    )
    if dates:
        payload["sources"][0]["citations"][0]["quote"] = "2026-10-19 발표"
    prompt = json.dumps(payload, ensure_ascii=False)
    ids = v8._prompt_citation_ids_v5(prompt)
    expected = _provider_schema_bytes_v6(v8._provider_tools_v8(ids, dates))

    def respond(messages, info):
        assert info.instructions == v10.SYSTEM_INSTRUCTIONS_V10
        assert info.instructions.startswith(v8.SYSTEM_INSTRUCTIONS_V8)
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

    agent = v10.create_agent_v10(
        FunctionModel(respond, profile=openai_model_profile("gpt-5.4-mini"))
    )
    v10.run_agent_v10(agent, prompt, prior_input_tokens=600, prior_output_tokens=900)
    assert v10.STATIC_INPUT_BYTES_V10 > v8.STATIC_INPUT_BYTES_V8


def test_v10_output_over_dynamic_cap_fails_with_one_response(sync_model_loop):
    from pydantic_ai.exceptions import UsageLimitExceeded

    v10 = profile()
    selected, response = proposal()
    calls = []

    def respond(messages, info):
        calls.append(True)
        return ModelResponse(
            parts=[ToolCallPart("answer", response)],
            usage=RequestUsage(input_tokens=100, output_tokens=1501),
        )

    agent = v10.create_agent_v10(FunctionModel(respond))
    prompt = v10.model_prompt_v10(
        "질문", (selected,), prior_input_tokens=600, prior_output_tokens=1000
    )
    with pytest.raises((ValueError, UsageLimitExceeded)):
        v10.run_agent_v10(agent, prompt, prior_input_tokens=600, prior_output_tokens=1000)
    assert calls == [True]


def test_standalone_selector_source_bytes_remain_frozen():
    import issuedigest_agents.relevance_selection as sdk

    assert (
        sha256(Path(sdk.__file__).read_bytes()).hexdigest()
        == "c194b9314ed4158976084b5e240160876c0c3ba6e23931ddf7fa1abd8b809212"
    )


@pytest.mark.parametrize("model", [None, object(), "openai:gpt-5.4-mini"])
def test_v10_factory_rejects_missing_or_unborrowed_model_before_client_creation(monkeypatch, model):
    v10 = profile()
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("v10 factory cannot delegate an invalid borrowed model")

    monkeypatch.setattr(v10, "_create_classified_agent", forbidden)
    with pytest.raises(ValueError, match="model"):
        v10.create_agent_v10(model)
    assert calls == []


def test_v10_cannot_be_relabelled_as_public_v1_or_v2():
    from issuedigest_domain.public_briefings import PublicBriefingPlan
    from pydantic import ValidationError
    from v10_fixture import build_fixture

    from conftest import public_plan_data

    value = public_plan_data()
    value["canvas"] = build_fixture()["result"]["canvas"]
    value["canvas"]["research"]["evidence"][0]["document"]["canonical_url"] = value["sources"][0][
        "official_url"
    ]
    with pytest.raises(ValidationError, match="Unsupported public Canvas scope"):
        PublicBriefingPlan.model_validate(value)


@pytest.mark.parametrize(
    "quote,body",
    [
        (
            "합성 장비 계획 90대 중 교체 25대가 포함된다.",
            "장비 계획 90대에 교체 25대가 포함되므로 별도 합산하지 않습니다.",
        ),
        (
            "합성 중간 실적 18대이며 부품 공급 시 연말 60대 이상을 전망한다.",
            "중간 실적은 18대이고 부품 공급을 전제로 연말 60대 이상을 전망하며 "
            "상한은 제시되지 않았습니다.",
        ),
        (
            "합성 지표 A는 동부의 연간 장비 목표 90대, B는 서부의 분기 설문 37%다.",
            "A는 동부 연간 장비 목표 90대이고 B는 서부 분기 설문 37%로 대상·기간·단위가 다릅니다.",
        ),
        (
            "합성 재고는 최대 45상자이며 출고는 12상자다.",
            "재고는 최대 45상자로 정확히 45상자라는 뜻이 아니며 출고는 12상자입니다.",
        ),
    ],
)
def test_synthetic_numeric_prose_survives_actual_conversion_and_builder(quote, body):
    """Forced examples verify transport/guards, never certify generated semantic quality."""
    from v10_fixture import build_fixture

    value = build_fixture(quote=quote, body=body)
    research = value["result"]["canvas"]["research"]
    assert research["claims"][0]["text"] == "제공 자료에 따르면, " + body
    assert research["evidence"][0]["citations"][0]["selector"]["quote"] == quote
    assert research["support_reviews"][0]["reviewer_id"] == "issuedigest-research-v10"
    assert value["result"]["canvas"]["revision"]["draft"]["modules"][0]["kind"] == "summary"


@pytest.mark.parametrize("count", [0, 1, 16])
def test_final10_static_envelope_covers_maximum_raw_and_normalized_schemas(count):
    from uuid import UUID

    from issuedigest_agents.research_v6 import _provider_schema_bytes_v6
    from issuedigest_agents.research_v8 import _provider_tools_v8

    v10 = profile()
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    dates = tuple(f"2026-10-{i:02}" for i in range(1, count + 1))
    assert (
        _provider_schema_bytes_v6(_provider_tools_v8(ids, dates))
        == {0: (7070, 6964), 1: (8097, 7957), 16: (8308, 8168)}[count]
    )
    assert (
        len(v10.SYSTEM_INSTRUCTIONS_V10.encode())
        + max(_provider_schema_bytes_v6(_provider_tools_v8(ids, dates)))
        <= v10.STATIC_INPUT_BYTES_V10
    )
