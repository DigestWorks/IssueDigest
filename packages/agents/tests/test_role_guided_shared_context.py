"""Synthetic contract checks, never evidence of a model's semantic judgment."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from types import SimpleNamespace

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import Field, create_model
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


def sdk():
    name = "issuedigest_agents.role_guided_shared_context"
    assert importlib.util.find_spec(name) is not None, "Missing role-guided shared context SDK"
    return importlib.import_module(name)


def anchor(text):
    return dict(sentence_id="s1", text=text, context_text=None)


def fixture():
    # Explicit country/city scopes apply to both quantities. The reporter is not a location.
    src = document(
        "발표처는 수요를 근거로 내년 조건 충족 시 전국 동부시 청년 이용자 "
        "전월 대비 100명 중 신규 이용자 20명을 지원 목적으로 전망했다고 밝혔다."
    )
    shared = dict(
        reporting_event_id="e1",
        target_scopes=[dict(kind="geographic", anchor=anchor("전국"))],
        period=anchor("내년"),
        value_status="forecast",
        logical_condition=anchor("조건 충족 시"),
        purpose=anchor("지원 목적으로"),
        forecast_basis=anchor("수요를 근거로"),
        comparison_baseline=anchor("전월 대비"),
    )
    data = dict(
        contexts=[
            dict(
                context_id="c1",
                measured_variable=dict(sentence_id="s1", text="이용자", context_text="청년 이용자"),
                **deepcopy(shared),
            ),
            dict(context_id="c2", measured_variable=anchor("신규 이용자"), **deepcopy(shared)),
        ],
        events=[
            dict(
                event_id="e1",
                kind="attributed_report",
                reporting_actor=anchor("발표처"),
                predicate=anchor("밝혔다"),
                reporting_tense="past",
            )
        ],
        bindings=[
            dict(
                candidate_id=candidate,
                context_id=context,
                target_scopes=[
                    dict(kind="geographic", anchor=anchor("동부시")),
                    dict(kind="population", anchor=anchor("청년")),
                ],
                status_evidence_sentence_id="s1",
            )
            for candidate, context in [("n1", "c1"), ("n2", "c2")]
        ],
        relations=[
            dict(
                from_id="n2",
                to_id="n1",
                kind="included_in",
                statement_sentence_ids=["s1"],
                cue=anchor("중"),
            )
        ],
    )
    return src, data


def response(
    data, *, inputs=100, outputs=30, tool="fill_role_guided_shared_context_v1", text=False
):
    calls = []

    def respond(messages, info):
        calls.append((messages, info))
        return ModelResponse(
            parts=[TextPart("unstructured")] if text else [ToolCallPart(tool, json.dumps(data))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src=None, data=None, **options):
    api = sdk()
    default_src, default_data = fixture()
    model, calls = response(default_data if data is None else data, **options)
    result = api.run_role_guided_shared_context_framer(
        api.create_role_guided_shared_context_framer(model), default_src if src is None else src
    )
    assert len(calls) == 1
    return result


def test_complete_roles_and_both_geographic_levels_reconstruct_with_separate_reporter():
    api = sdk()
    src, data = fixture()
    result = run(src, data)
    assert (result.profile, result.status) == ("role-guided-shared-context-v1", "unreviewed")
    facts = result.frame.frame.frame.resolved.facts
    assert [f.measured_entity.span.text for f in facts] == ["이용자", "신규 이용자"]
    assert [f.reporting_actor.span.text for f in facts] == ["발표처", "발표처"]
    assert [(f.value_status, f.reporting_tense) for f in facts] == [("forecast", "past")] * 2
    for fact in facts:
        assert fact.period.span.text == "내년"
        assert fact.logical_condition.span.text == "조건 충족 시"
        assert fact.forecast_basis.span.text == "수요를 근거로"
        assert fact.comparison_baseline.span.text == "전월 대비"
        assert fact.status_text.span.text == src[1].citations[0].selector.quote
    assert [[s.anchor.span.text for s in f.target_scopes] for f in result.frame.frame.scopes] == [
        ["전국", "동부시", "청년"],
        ["전국", "동부시", "청년"],
    ]
    assert [p.purpose.span.text for p in result.frame.purposes] == ["지원 목적으로"] * 2
    assert [(r.from_id, r.to_id, r.kind) for r in result.frame.frame.frame.resolved.relations] == [
        ("n2", "n1", "included_in")
    ]
    assert result.usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    assert api.validate_role_guided_shared_context(src, result) == result
    assert (
        api.validate_role_guided_shared_context(src, json.loads(result.model_dump_json())) == result
    )


def test_only_profile_tool_and_appended_guidance_change_v1_request():
    from issuedigest_agents import shared_context_generation as v1

    api = sdk()
    src, _ = fixture()
    original = v1.shared_context_prompt(src)
    original_instructions = v1.SHARED_CONTEXT_INSTRUCTIONS
    prompt, tools = api._preflight(src)
    expected = json.loads(original)
    expected["profile"] = "role-guided-shared-context-v1"
    assert json.loads(prompt) == expected
    assert tools[0].strict is True
    assert (
        tools[0].output.model_json_schema() == v1._preflight(src)[1][0].output.model_json_schema()
    )
    assert api.ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS == (
        original_instructions.replace(
            "fill_shared_context_v1", "fill_role_guided_shared_context_v1"
        )
        + " "
        + api.ROLE_GUIDANCE
    )
    assert v1.shared_context_prompt(src) == original
    assert v1.SHARED_CONTEXT_INSTRUCTIONS == original_instructions
    assert tools[0].name == "fill_role_guided_shared_context_v1"


@pytest.mark.parametrize(
    "change", ["prompt", "instructions", "profile", "source", "derived", "slot"]
)
def test_new_receipts_never_approve_stale_cross_profile_or_tampered_results(change):
    from issuedigest_agents import shared_context_generation as v1

    api = sdk()
    src, data = fixture()
    result = run(src, data)
    stored = json.loads(result.model_dump_json())
    if change == "prompt":
        stored["prompt_sha256"] = "0" * 64
    elif change == "instructions":
        stored["instructions_sha256"] = sha256(v1.SHARED_CONTEXT_INSTRUCTIONS.encode()).hexdigest()
    elif change == "profile":
        stored["profile"] = "shared-context-generation-v1"
    elif change == "source":
        src = document(src[1].citations[0].selector.quote + " 바뀐 원문.")
        # Refresh receipts alone cannot legitimize the old source reconstruction.
        stored["prompt_sha256"] = sha256(
            api.role_guided_shared_context_prompt(src).encode()
        ).hexdigest()
    elif change == "derived":
        stored["frame"]["purposes"][0]["purpose"] = None
    else:
        from issuedigest_agents.shared_measurement_context import build_shared_measurement_frame

        data["contexts"][0]["context_id"] = "outside-slot"
        data["bindings"][0]["context_id"] = "outside-slot"
        stored["frame"] = build_shared_measurement_frame(src, data).model_dump(mode="json")
    with pytest.raises(api.RoleGuidedSharedContextError) as caught:
        api.validate_role_guided_shared_context(src, stored)
    assert caught.value.known_usage is None
    assert caught.value.__cause__ is None
    assert src[1].citations[0].selector.quote not in str(caught.value)
    with pytest.raises(v1.SharedContextGenerationError):
        v1.validate_shared_context_generation(src, result)


@pytest.mark.parametrize("node", ["frame-dict", "scope-dict", "list", "subclass"])
def test_unchecked_actual_structure_is_rejected_before_receipt_translation(node):
    api = sdk()
    src, data = fixture()
    result = run(src, data)
    if node == "frame-dict":
        forged = result.model_copy(update={"frame": result.frame.model_dump(mode="json")})
    elif node == "list":
        forged = result.model_copy(
            update={
                "frame": result.frame.model_copy(update={"purposes": list(result.frame.purposes)})
            }
        )
    else:
        context = result.frame.input.contexts[0]
        if node == "scope-dict":
            context = context.model_copy(
                update={"target_scopes": (context.target_scopes[0].model_dump(mode="json"),)}
            )
        else:
            hidden = create_model(
                "HiddenRoleContext", __base__=type(context), secret=(str, Field(exclude=True))
            )
            context = hidden(**context.model_dump(), secret="hidden synthetic detail")
        forged = result.model_copy(
            update={
                "frame": result.frame.model_copy(
                    update={
                        "input": result.frame.input.model_copy(
                            update={"contexts": (context, result.frame.input.contexts[1])}
                        )
                    }
                )
            }
        )
    with pytest.raises(api.RoleGuidedSharedContextError):
        api.validate_role_guided_shared_context(src, forged)


@pytest.mark.parametrize("node", ["context", "scope", "anchor"])
def test_runtime_rejects_base_models_in_place_of_actual_dynamic_nodes(monkeypatch, node):
    from issuedigest_agents import contextual_frame_generation as runtime

    api = sdk()
    original = runtime.Agent.run_sync

    def forged(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        row = result.output.contexts[0]
        target = {"context": row, "scope": row.target_scopes[0], "anchor": row.measured_variable}[
            node
        ]
        replacement = (
            type(target).__bases__[0].model_validate_json(target.model_dump_json(), strict=True)
        )
        if node == "context":
            row = replacement
        else:
            row = row.model_copy(
                update={"target_scopes": (replacement,)}
                if node == "scope"
                else {"measured_variable": replacement}
            )
        output = result.output.model_copy(update={"contexts": (row, result.output.contexts[1])})
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(runtime.Agent, "run_sync", forged)
    with pytest.raises(api.RoleGuidedSharedContextError) as caught:
        run()
    assert caught.value.known_usage.input_tokens == 100


@pytest.mark.parametrize(
    "change", ["missing-scope", "unknown-candidate", "combined-cap", "ambiguous"]
)
def test_invalid_dynamic_or_linkage_output_fails_whole_request_without_repair(change):
    api = sdk()
    src, data = fixture()
    if change == "missing-scope":
        data["contexts"][0]["target_scopes"][0].pop("anchor")
    elif change == "unknown-candidate":
        data["bindings"][0]["candidate_id"] = "n3"
    elif change == "combined-cap":
        data["bindings"][0]["target_scopes"] += [
            dict(kind="other", anchor=anchor("내년")),
            dict(kind="other", anchor=anchor("발표처")),
        ]
    else:
        data["contexts"][0]["measured_variable"]["context_text"] = None
    model, calls = response(data)
    with pytest.raises(api.RoleGuidedSharedContextError) as caught:
        api.run_role_guided_shared_context_framer(
            api.create_role_guided_shared_context_framer(model), src
        )
    assert len(calls) == 1
    assert caught.value.known_usage.model_dump() == dict(
        input_tokens=100, output_tokens=30, requests=1
    )
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("schema_sizes", [None, (111, 999), (999, 111)])
def test_new_utf8_envelope_checks_larger_schema_and_inclusive_cap_before_request(
    monkeypatch, schema_sizes
):
    api = sdk()
    src, data = fixture()
    result = run(src, data)
    if schema_sizes:
        monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: schema_sizes)
    prompt, tools = api._preflight(src)
    limit = (
        len(prompt.encode())
        + len(api.ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS.encode())
        + max(api._provider_schema_bytes_v5(tools))
        + 2048
        + 2500
    )
    assert len(prompt.encode()) > len(prompt)
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit)
    assert api.role_guided_shared_context_prompt(src) == prompt
    assert api.validate_role_guided_shared_context(src, result) == result
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit - 1)
    model, calls = response(data)
    for action in (
        lambda: api.role_guided_shared_context_prompt(src),
        lambda: api.validate_role_guided_shared_context(src, result),
        lambda: api.run_role_guided_shared_context_framer(
            api.create_role_guided_shared_context_framer(model), src
        ),
    ):
        with pytest.raises(api.RoleGuidedSharedContextError):
            action()
    assert calls == []


@pytest.mark.parametrize(
    "inputs,outputs,valid", [(17500, 2500, True), (17501, 2500, False), (1, 2501, False)]
)
def test_actual_usage_limits_accept_inclusive_cap_and_reject_overflow(inputs, outputs, valid):
    api = sdk()
    if valid:
        assert run(inputs=inputs, outputs=outputs).usage.output_tokens == 2500
    else:
        with pytest.raises(api.RoleGuidedSharedContextError) as caught:
            run(inputs=inputs, outputs=outputs)
        # The SDK rejects before publishing a response to its capture context.
        # Unknown usage is preserved, never represented as a free request.
        assert caught.value.known_usage is None


def test_runtime_identity_bounds_no_store_and_borrowed_lifecycle(monkeypatch):
    from dataclasses import FrozenInstanceError

    from issuedigest_agents import contextual_frame_generation as runtime

    api = sdk()
    original_init, original_run = runtime.Agent.__init__, runtime.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_role_guided_shared_context_v1"
        assert kwargs["instructions"] == api.ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS
        assert kwargs["retries"] == 0
        return original_init(self, *args, **kwargs)

    def called(self, *args, **kwargs):
        limits = kwargs["usage_limits"]
        assert (limits.request_limit, limits.output_tokens_limit, limits.total_tokens_limit) == (
            1,
            2500,
            20000,
        )
        assert kwargs["retries"] == 0
        assert kwargs["model_settings"] == dict(openai_store=False, max_tokens=2500, timeout=30)
        return original_run(self, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Caller owns lifecycle")

    monkeypatch.setattr(runtime.Agent, "__init__", initialized)
    monkeypatch.setattr(runtime.Agent, "run_sync", called)
    src, data = fixture()
    model, calls = response(data)
    monkeypatch.setattr(model, "__aenter__", forbidden)
    monkeypatch.setattr(model, "__aexit__", forbidden)
    handle = api.create_role_guided_shared_context_framer(model)
    assert calls == []
    with pytest.raises(FrozenInstanceError):
        handle.model = model
    assert api.run_role_guided_shared_context_framer(handle, src).status == "unreviewed"
    for invalid in (None, "model-name"):
        with pytest.raises(api.RoleGuidedSharedContextError):
            api.create_role_guided_shared_context_framer(invalid)
    with pytest.raises(api.RoleGuidedSharedContextError):
        api.run_role_guided_shared_context_framer(SimpleNamespace(model=model), src)


def test_old_tool_or_free_text_are_not_repaired():
    api = sdk()
    src, data = fixture()
    for options in ({"tool": "fill_shared_context_v1"}, {"text": True}):
        model, calls = response(data, **options)
        with pytest.raises(api.RoleGuidedSharedContextError) as caught:
            api.run_role_guided_shared_context_framer(
                api.create_role_guided_shared_context_framer(model), src
            )
        assert len(calls) == 1
        assert caught.value.known_usage.input_tokens == 100


def test_actual_responses_wire_preserves_v1_body_and_caller_settings(sync_model_loop):
    import httpx2
    from issuedigest_agents import shared_context_generation as v1
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    api = sdk()
    src, data = fixture()
    requests = []

    def transport(request):
        body = json.loads(request.content)
        requests.append(body)
        return httpx2.Response(
            200,
            json={
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 1,
                "status": "completed",
                "model": "synthetic-model",
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc_synthetic",
                        "call_id": "call_synthetic",
                        "name": body["tools"][0]["name"],
                        "arguments": json.dumps(data),
                        "status": "completed",
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 30, "total_tokens": 130},
            },
        )

    client = httpx2.AsyncClient(transport=httpx2.MockTransport(transport))
    provider_client = AsyncOpenAI(
        api_key="synthetic-not-a-secret",
        base_url="https://synthetic.invalid/v1",
        http_client=client,
        max_retries=0,
    )
    model = OpenAIResponsesModel(
        "synthetic-model",
        provider=OpenAIProvider(openai_client=provider_client),
        settings={"temperature": 0.25},
    )
    try:
        before = v1.run_shared_context_framer(v1.create_shared_context_framer(model), src)
        new = api.run_role_guided_shared_context_framer(
            api.create_role_guided_shared_context_framer(model), src
        )
        after = v1.run_shared_context_framer(v1.create_shared_context_framer(model), src)
        assert before == after
        assert len(requests) == 3 and requests[0] == requests[2]
        original, changed = deepcopy(requests[0]), requests[1]
        original["instructions"] = api.ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS
        original["input"][0]["content"] = api.role_guided_shared_context_prompt(src)
        original["tools"][0]["name"] = "fill_role_guided_shared_context_v1"
        assert changed == original
        assert changed["store"] is False and changed["max_output_tokens"] == 2500
        assert changed["temperature"] == 0.25 and len(changed["tools"]) == 1
        assert changed["tools"][0]["strict"] is True
        assert changed["tools"][0]["parameters"]["required"] == [
            "contexts",
            "events",
            "bindings",
            "relations",
        ]
        assert new.frame == before.frame and not client.is_closed
        with pytest.raises(api.RoleGuidedSharedContextError):
            api.validate_role_guided_shared_context(src, before.model_dump(mode="json"))
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


def test_unchecked_source_fails_before_request():
    api = sdk()
    src, data = fixture()
    forged = src[0], src[1].model_copy(update={"citations": list(src[1].citations)}), src[2]
    model, calls = response(data)
    with pytest.raises(api.RoleGuidedSharedContextError):
        api.role_guided_shared_context_prompt(forged)
    with pytest.raises(api.RoleGuidedSharedContextError):
        api.run_role_guided_shared_context_framer(
            api.create_role_guided_shared_context_framer(model), forged
        )
    assert calls == []


def test_cold_import_prompt_create_and_validation_allocate_no_clients_or_io():
    code = """
import builtins, importlib, io, os, socket
from hashlib import sha256
import openai, pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
from issuedigest_agents.shared_measurement_context import build_shared_measurement_frame
from issuedigest_agents.numeric_evidence import KnownUsage
src = document("항목 10명.")
def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected IO/client/key/request")
model = FunctionModel(forbidden)
openai.AsyncOpenAI.__init__ = openai.OpenAI.__init__ = forbidden
pydantic_ai.Agent.__init__ = forbidden
original = type(os.environ).__getitem__
def no_env(self, key):
    if key != "PYDANTIC_DISABLE_PLUGINS": forbidden()
    return original(self, key)
type(os.environ).__getitem__ = no_env
builtins.open = io.open = forbidden
socket.socket = forbidden
api = importlib.import_module("issuedigest_agents.role_guided_shared_context")
api.create_role_guided_shared_context_framer(model)
prompt = api.role_guided_shared_context_prompt(src)
result = api.RoleGuidedSharedContextGeneration(
    frame=build_shared_measurement_frame(
        src, dict(contexts=[], events=[], bindings=[], relations=[])
    ),
    prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS.encode()).hexdigest(),
    usage=KnownUsage(input_tokens=0, output_tokens=0, requests=1),
)
assert api.validate_role_guided_shared_context(src, result) == result
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
