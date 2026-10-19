"""Synthetic provider boundaries: no key, network, or actual model responses."""

import copy
import json
from uuid import UUID, uuid4

import pytest
from issuedigest_agents import research_v5 as v5
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from test_generation import source
from test_research_v5 import proposal


def run_synthetic(prompt, response, inspect=None):
    calls = []

    def respond(messages, info):
        calls.append(True)
        if inspect:
            inspect(info)
        tool = next(
            (
                tool
                for tool in info.output_tools
                if tool.parameters_json_schema["properties"]["outcome"].get("const")
                == response["outcome"]
            ),
            info.output_tools[0],
        )
        return ModelResponse(parts=[ToolCallPart(tool.name, response)])

    agent = v5.create_agent_v5(FunctionModel(respond))
    return agent, calls


def test_provider_schema_has_three_exclusive_strict_variants_and_exact_ids(sync_model_loop):
    selected, output = proposal()
    outsider = str(uuid4())
    prompt = v5.model_prompt_v5(outsider, (selected,), outsider)
    ids = [c["citation_id"] for c in json.loads(prompt)["sources"][0]["citations"]]

    def inspect(info):
        assert len(info.output_tools) == 3
        assert all(t.strict is True for t in info.output_tools)
        by_outcome = {
            t.parameters_json_schema["properties"]["outcome"]["const"]: t for t in info.output_tools
        }
        assert set(by_outcome) == {"answer", "insufficient_evidence", "clarification_needed"}
        answer = by_outcome["answer"].parameters_json_schema
        assert answer["properties"]["modules"]["minItems"] == 1
        assert answer["properties"]["modules"]["maxItems"] == 3
        claim = answer["$defs"]["ProviderClaimV5"]
        assert claim["properties"]["citation_ids"]["items"]["enum"] == ids
        assert outsider not in json.dumps(answer)
        assert claim["properties"]["citation_ids"]["minItems"] == 1
        assert claim["properties"]["citation_ids"]["maxItems"] == 3
        for outcome in ("insufficient_evidence", "clarification_needed"):
            schema = by_outcome[outcome].parameters_json_schema
            assert schema["properties"]["modules"]["maxItems"] == 0
            assert schema["properties"]["message"]["minLength"] == 1
            assert schema["properties"]["message"]["pattern"] == r"\S"
            assert schema["properties"]["message"]["maxLength"] == 500

    agent, calls = run_synthetic(prompt, output.model_dump(mode="json"), inspect)
    result, _, _ = v5.run_agent_v5(agent, prompt)
    assert type(result) is v5.AIOutputV5
    assert result == output
    assert calls == [True]


@pytest.mark.parametrize("mutation", ["nonanswer-modules", "unknown", "case", "one-char"])
def test_observed_protocol_errors_are_rejected_without_retry(sync_model_loop, mutation):
    selected, output = proposal()
    payload = json.loads(v5.model_prompt_v5("합성 질문", (selected,)))
    # Include letters so case corruption is observable, and retain UUID4 spelling.
    cid = "abcdefab-cdef-4abc-8def-abcdefabcdef"
    payload["sources"][0]["citations"][0]["citation_id"] = cid
    response = output.model_dump(mode="json")
    response["modules"][0]["claims"][0]["citation_ids"] = [cid]
    if mutation == "nonanswer-modules":
        response.update(outcome="insufficient_evidence", message="합성 근거 부족")
    else:
        response["modules"][0]["claims"][0]["citation_ids"] = [
            {
                "unknown": str(uuid4()),
                "case": cid.upper(),
                "one-char": cid[:-1] + "0",
            }[mutation]
        ]
    agent, calls = run_synthetic(json.dumps(payload), response)
    with pytest.raises(UnexpectedModelBehavior):
        v5.run_agent_v5(agent, json.dumps(payload))
    assert calls == [True]


@pytest.mark.parametrize("outcome", ["insufficient_evidence", "clarification_needed"])
@pytest.mark.parametrize("message", ["합성 자료의 한계", "", "  \t ", "가" * 501])
def test_provider_nonanswer_keeps_success_and_rejects_invalid_messages(
    sync_model_loop, outcome, message
):
    selected = source()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    agent, calls = run_synthetic(prompt, dict(outcome=outcome, message=message, modules=[]))
    if not message.strip() or len(message) > 500:
        with pytest.raises(UnexpectedModelBehavior):
            v5.run_agent_v5(agent, prompt)
    else:
        result, _, _ = v5.run_agent_v5(agent, prompt)
        assert type(result) is v5.AIOutputV5
        canvas = v5.build_canvas_v5(uuid4(), selected[1].document.workspace_id, (selected,), result)
        assert canvas.revision.draft.outcome == outcome
        assert canvas.revision.draft.message == message
    assert calls == [True]


@pytest.mark.parametrize(
    "mutation",
    [
        "json",
        "root",
        "question",
        "prior",
        "empty",
        "sources-type",
        "source-shape",
        "citation-shape",
        "empty-quote",
        "nonstring-quote",
        "id-type",
        "id-case",
        "id-short",
        "id-not-v4",
        "duplicate",
        "source-duplicate",
        "six-sources",
        "33-citations",
        "101-citations",
        "extra-root",
        "extra-source",
        "extra-citation",
    ],
)
def test_invalid_prompt_fails_before_any_provider_request(mutation):
    selected = source()
    payload = json.loads(v5.model_prompt_v5("합성 질문", (selected,)))
    citation = payload["sources"][0]["citations"][0]
    if mutation == "json":
        prompt = "{"
    elif mutation == "root":
        prompt = "[]"
    else:
        match mutation:
            case "question":
                payload["question"] = []
            case "prior":
                payload["prior_interpretation_context"] = []
            case "empty":
                payload["sources"] = []
            case "sources-type":
                payload["sources"] = {}
            case "source-shape":
                payload["sources"][0].pop("citations")
            case "citation-shape":
                citation.pop("quote")
            case "empty-quote":
                citation["quote"] = " \t "
            case "nonstring-quote":
                citation["quote"] = 1
            case "id-type":
                citation["citation_id"] = 1
            case "id-case":
                citation["citation_id"] = "ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF"
            case "id-short":
                citation["citation_id"] = UUID(citation["citation_id"]).hex
            case "id-not-v4":
                citation["citation_id"] = str(UUID(int=1))
            case "duplicate":
                payload["sources"][0]["citations"].append(copy.deepcopy(citation))
            case "source-duplicate":
                payload["sources"].append(copy.deepcopy(payload["sources"][0]))
            case "six-sources":
                payload["sources"] *= 6
            case "33-citations":
                payload["sources"][0]["citations"] = [
                    dict(citation_id=str(uuid4()), quote="합성") for _ in range(33)
                ]
            case "101-citations":
                payload["sources"] = [
                    {
                        **payload["sources"][0],
                        "citations": [
                            dict(citation_id=str(uuid4()), quote="합성") for _ in range(n)
                        ],
                    }
                    for n in (26, 25, 25, 25)
                ]
            case "extra-root":
                payload["injected"] = "data"
            case "extra-source":
                payload["sources"][0]["injected"] = "data"
            case "extra-citation":
                citation["injected"] = "data"
        prompt = json.dumps(payload)

    def forbidden(messages, info):
        raise AssertionError("invalid prompt reached provider")

    with pytest.raises(ValueError, match="provider (prompt|input)"):
        v5.run_agent_v5(v5.create_agent_v5(FunctionModel(forbidden)), prompt)


def test_caller_cannot_expand_the_original_canonical_citation_set(sync_model_loop):
    selected, output = proposal()
    payload = json.loads(v5.model_prompt_v5("합성 질문", (selected,)))
    outsider = str(uuid4())
    payload["sources"][0]["citations"][0]["citation_id"] = outsider
    response = output.model_dump(mode="json")
    response["modules"][0]["claims"][0]["citation_ids"] = [outsider]
    prompt = json.dumps(payload)
    agent, calls = run_synthetic(prompt, response)
    result, _, _ = v5.run_agent_v5(agent, prompt)
    with pytest.raises(ValueError, match="Unknown or duplicate citation"):
        v5.build_canvas_v5(uuid4(), selected[1].document.workspace_id, (selected,), result)
    assert calls == [True]


def test_budget_includes_all_serialized_tools_and_the_100_uuid_worst_case():
    # Prevent a canonical-only or one-tool budget from silently reducing provider headroom.
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    tools = v5._provider_tools_v5(ids)
    raw_bytes, normalized_bytes = v5._provider_schema_bytes_v5(tools)
    assert raw_bytes >= 4000 and normalized_bytes >= 4000
    assert v5.STATIC_INPUT_BYTES_V5 == (
        len(v5.SYSTEM_INSTRUCTIONS_V5.encode()) + max(raw_bytes, normalized_bytes)
    )
    assert v5.INPUT_PROMPT_BYTE_LIMIT_V5 == 24_000 - 2_500 - 2_048 - v5.STATIC_INPUT_BYTES_V5
    for count in (1, 2, 32, 99, 100):
        actual = v5._provider_schema_bytes_v5(v5._provider_tools_v5(ids[:count]))
        assert max(actual) <= max(raw_bytes, normalized_bytes)


def test_actual_schema_budget_is_rechecked_before_the_request(monkeypatch):
    from pydantic_ai import ToolOutput

    selected, output = proposal()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    original = v5._provider_tools_v5

    def oversize(ids):
        return [
            ToolOutput(tool.output, name=tool.name, description="x" * 24_000, strict=True)
            for tool in original(ids)
        ]

    monkeypatch.setattr(v5, "_provider_tools_v5", oversize)
    agent, calls = run_synthetic(prompt, output.model_dump(mode="json"))
    with pytest.raises(ValueError, match="provider input"):
        v5.run_agent_v5(agent, prompt)
    assert calls == []


def test_provider_multi_citation_conversion_retains_order_and_duplicate_guard(sync_model_loop):
    selected, output = proposal()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    ids = [c.citation_id for c in selected[1].citations]
    response = output.model_dump(mode="json")
    response["modules"][0]["claims"][0]["citation_ids"] = [str(ids[1]), str(ids[0])]
    agent, calls = run_synthetic(prompt, response)
    result, _, _ = v5.run_agent_v5(agent, prompt)
    assert result.modules[0].claims[0].citation_ids == (ids[1], ids[0])
    canvas = v5.build_canvas_v5(uuid4(), selected[1].document.workspace_id, (selected,), result)
    assert canvas.research.support_reviews[0].citation_ids == (ids[1], ids[0])
    response["modules"][0]["claims"][0]["citation_ids"] = [str(ids[0]), str(ids[0])]
    agent, calls = run_synthetic(prompt, response)
    duplicated, _, _ = v5.run_agent_v5(agent, prompt)
    with pytest.raises(ValueError, match="Unknown or duplicate citation"):
        v5.build_canvas_v5(uuid4(), selected[1].document.workspace_id, (selected,), duplicated)
    assert calls == [True]


def test_normalized_provider_schemas_match_the_preflight_serializer(sync_model_loop):
    from pydantic_ai.profiles.openai import openai_model_profile

    selected, output = proposal()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    ids = tuple(c["citation_id"] for s in json.loads(prompt)["sources"] for c in s["citations"])
    expected = v5._provider_schema_bytes_v5(v5._provider_tools_v5(ids))
    seen = []

    def respond(messages, info):
        payloads = [
            dict(
                type="function",
                name=t.name,
                description=t.description,
                strict=t.strict,
                parameters=t.parameters_json_schema,
            )
            for t in info.output_tools
        ]
        actual_bytes = len(json.dumps(payloads, ensure_ascii=False).encode())
        assert actual_bytes == expected[1]
        assert (
            len(prompt.encode())
            + len(v5.SYSTEM_INSTRUCTIONS_V5.encode())
            + actual_bytes
            + 2048
            + 2500
        ) <= 24000
        answer = info.output_tools[0].parameters_json_schema
        assert "default" not in json.dumps(answer)
        assert answer["required"] == ["outcome", "message", "modules"]
        claim = answer["$defs"]["ProviderClaimV5"]
        assert set(claim["required"]) == {
            "text",
            "citation_ids",
            "event_date",
            "category",
            "rationale",
        }
        assert claim["properties"]["citation_ids"]["items"]["enum"] == list(ids)
        assert all(t.strict is True for t in info.output_tools)
        seen.append(True)
        return ModelResponse(parts=[ToolCallPart("answer", output.model_dump(mode="json"))])

    agent = v5.create_agent_v5(FunctionModel(respond, profile=openai_model_profile("gpt-5.4-mini")))
    actual, _, _ = v5.run_agent_v5(agent, prompt)
    assert actual == output and seen == [True]


@pytest.mark.parametrize(
    "mutation",
    ["no-modules", "four-modules", "no-claims", "five-claims", "no-citations", "four-citations"],
)
def test_provider_rejects_answer_shape_overflows_without_retry(sync_model_loop, mutation):
    selected, output = proposal()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    response = output.model_dump(mode="json")
    match mutation:
        case "no-modules":
            response["modules"] = []
        case "four-modules":
            response["modules"] *= 4
        case "no-claims":
            response["modules"][0]["claims"] = []
        case "five-claims":
            response["modules"][0]["claims"] *= 5
        case "no-citations":
            response["modules"][0]["claims"][0]["citation_ids"] = []
        case "four-citations":
            response["modules"][0]["claims"][0]["citation_ids"] *= 4
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises(UnexpectedModelBehavior):
        v5.run_agent_v5(agent, prompt)
    assert calls == [True]


def test_comparison_still_requires_two_claims_in_the_final_canonical_guard(sync_model_loop):
    selected, output = proposal()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    response = output.model_dump(mode="json")
    response["modules"][0]["kind"] = "comparison"
    agent, calls = run_synthetic(prompt, response)
    result, _, _ = v5.run_agent_v5(agent, prompt)
    with pytest.raises(ValueError, match="Comparison needs two claims"):
        v5.build_canvas_v5(uuid4(), selected[1].document.workspace_id, (selected,), result)
    assert calls == [True]


@pytest.mark.parametrize("question", ["", " \t "])
def test_blank_prompt_question_is_rejected_before_provider(question):
    selected = source()
    prompt = v5.model_prompt_v5(question, (selected,))

    def forbidden(messages, info):
        raise AssertionError("blank question reached provider")

    with pytest.raises(ValueError, match="provider prompt"):
        v5.run_agent_v5(v5.create_agent_v5(FunctionModel(forbidden)), prompt)


def test_exact_prompt_limit_is_accepted_and_one_byte_over_is_rejected(sync_model_loop):
    selected, output = proposal()
    payload = json.loads(v5.model_prompt_v5("x", (selected,)))
    base_length = len(json.dumps(payload, ensure_ascii=False).encode())
    payload["question"] += "x" * (v5.INPUT_PROMPT_BYTE_LIMIT_V5 - base_length)
    prompt = json.dumps(payload, ensure_ascii=False)
    assert len(prompt.encode()) == v5.INPUT_PROMPT_BYTE_LIMIT_V5
    agent, calls = run_synthetic(prompt, output.model_dump(mode="json"))
    result, _, _ = v5.run_agent_v5(agent, prompt)
    assert result == output and calls == [True]
    payload["question"] += "x"
    with pytest.raises(ValueError, match="provider input"):
        v5.run_agent_v5(agent, json.dumps(payload, ensure_ascii=False))
    assert calls == [True]


def test_maximum_100_ids_and_five_sources_remain_accepted(sync_model_loop):
    ids = [str(UUID(int=i, version=4)) for i in range(1, 101)]
    payload = dict(
        question="합성 질문",
        prior_interpretation_context=None,
        sources=[
            dict(
                snapshot_id=str(uuid4()),
                title="합성",
                kind="other",
                collected_at="2026-10-19T00:00:00Z",
                citations=[dict(citation_id=c, quote="합성") for c in ids[offset : offset + 20]],
            )
            for offset in range(0, 100, 20)
        ],
    )
    _, output = proposal()
    response = output.model_dump(mode="json")
    response["modules"][0]["claims"][0]["citation_ids"] = [ids[99], ids[0]]
    seen = []

    def inspect(info):
        enum = info.output_tools[0].parameters_json_schema["$defs"]["ProviderClaimV5"][
            "properties"
        ]["citation_ids"]["items"]["enum"]
        assert enum == ids
        seen.append(True)

    prompt = json.dumps(payload, ensure_ascii=False)
    agent, calls = run_synthetic(prompt, response, inspect)
    result, _, _ = v5.run_agent_v5(agent, prompt)
    assert result.modules[0].claims[0].citation_ids == (UUID(ids[99]), UUID(ids[0]))
    assert calls == seen == [True]


def test_schema_ids_follow_trimmed_prompt_instead_of_the_original_source(sync_model_loop):
    from test_research_profile_compatibility import prompt_sources

    selected = prompt_sources(30)
    prompt = v5.model_prompt_v5("합성 질문", selected, "이전 해석 " * 400)
    actual_ids = [c["citation_id"] for s in json.loads(prompt)["sources"] for c in s["citations"]]
    assert 1 < len(actual_ids) < len(selected[0][1].citations)
    _, output = proposal()
    response = output.model_dump(mode="json")
    response["modules"][0]["claims"][0]["citation_ids"] = [actual_ids[0]]

    def inspect(info):
        assert (
            info.output_tools[0].parameters_json_schema["$defs"]["ProviderClaimV5"]["properties"][
                "citation_ids"
            ]["items"]["enum"]
            == actual_ids
        )

    agent, calls = run_synthetic(prompt, response, inspect)
    v5.run_agent_v5(agent, prompt)
    assert calls == [True]


@pytest.mark.parametrize("input_tokens,output_tokens", [(24001, 1), (1, 2501)])
def test_v5_enforces_usage_limits_on_the_only_request(sync_model_loop, input_tokens, output_tokens):
    from pydantic_ai.exceptions import UsageLimitExceeded
    from pydantic_ai.usage import RequestUsage

    selected, output = proposal()
    prompt = v5.model_prompt_v5("합성 질문", (selected,))
    calls = []

    def respond(messages, info):
        calls.append(True)
        return ModelResponse(
            parts=[ToolCallPart("answer", output.model_dump(mode="json"))],
            usage=RequestUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        )

    agent = v5.create_agent_v5(FunctionModel(respond))
    with pytest.raises(UsageLimitExceeded):
        v5.run_agent_v5(agent, prompt)
    assert calls == [True]
