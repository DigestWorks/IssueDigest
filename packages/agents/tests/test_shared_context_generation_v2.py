"""Synthetic v2 borrowed-model generation and strict stored-result boundaries."""

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
from test_shared_measurement_context_v2 import example, packet, scope


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_modules():
    package = importlib.import_module("issuedigest_agents")
    existing = set(sys.modules)
    attributes = vars(package).copy()
    yield
    for name in set(sys.modules) - existing:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)
    # A from-package import can reuse an unloaded module through this namespace.
    # Restore both caches so later frozen reload tests see the same class identities.
    for name in set(vars(package)) - attributes.keys():
        delattr(package, name)
    for name, value in attributes.items():
        setattr(package, name, value)


def sdk():
    name = "issuedigest_agents.shared_context_generation_v2"
    assert importlib.util.find_spec(name) is not None, "Missing v2 shared generation"
    return importlib.import_module(name)


def response(data, *, inputs=100, outputs=30, error=None, text=False, inspect=None):
    calls = []

    def respond(messages, info):
        calls.append(info)
        if inspect:
            inspect(messages, info)
        if error:
            raise error
        return ModelResponse(
            parts=[TextPart("free text")]
            if text
            else [ToolCallPart("fill_shared_context_v2", json.dumps(data))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src=None, data=None, **options):
    api = sdk()
    model, calls = response(packet() if data is None else data, **options)
    result = api.run_shared_context_framer_v2(
        api.create_shared_context_framer_v2(model), src or document("항목 37여 명 내외.")
    )
    assert len(calls) == 1
    return result


def test_nonempty_v2_generation_preserves_prompt_roles_full_index_and_receipts():
    api = sdk()
    src, data = example()
    result = run(src, data)
    assert (result.profile, result.status) == ("shared-context-generation-v2", "unreviewed")
    assert [c.expression.text for c in result.frame.candidate_index.candidates] == [
        "약\t37여 명 내외",
        "61~79명 내외",
        "83개교",
    ]
    assert result.frame.facts[0].purpose.span.text == "지원 목적으로"
    assert result.frame.facts[0].reporting_actor.span.text == "발표처"
    assert [s.anchor.span.text for s in result.frame.facts[0].target_scopes] == [
        "합성국",
        "동부",
        "청년",
    ]
    prompt = api.shared_context_prompt_v2(src)
    raw = json.loads(prompt)
    assert raw["profile"] == "shared-context-generation-v2"
    assert raw["source"]["citations"][0]["quote"] == src[1].citations[0].selector.quote
    assert raw["candidates"][0]["expression"] == "약\t37여 명 내외"
    assert raw["candidates"][0]["qualifiers"] == ["약", "여", "내외"]
    assert raw["candidates"][1]["atoms"] == [
        {"number": "61", "unit": None},
        {"number": "79", "unit": "명"},
    ]
    assert raw["candidates"][2]["atoms"] == [{"number": "83", "unit": "개교"}]
    assert raw["eligible_status_sentence_ids"] == ["s2", "s3"]
    assert raw["context_id_slots"] == [f"c{i}" for i in range(1, 13)]
    assert raw["reporting_event_id_slots"] == [f"e{i}" for i in range(1, 13)]
    assert result.prompt_sha256 == sha256(prompt.encode()).hexdigest()
    assert (
        result.instructions_sha256
        == sha256(api.SHARED_CONTEXT_INSTRUCTIONS_V2.encode()).hexdigest()
    )
    assert result.usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    assert api.validate_shared_context_generation_v2(src, result) == result
    assert (
        api.validate_shared_context_generation_v2(src, json.loads(result.model_dump_json()))
        == result
    )


@pytest.mark.parametrize(
    "change",
    [
        "slot",
        "event_slot",
        "candidate",
        "sentence",
        "status",
        "unused",
        "extra",
        "missing",
        "relation",
        "scopes",
        "contexts_cap",
        "events_cap",
        "bindings_cap",
        "relations_cap",
    ],
)
def test_invalid_provider_record_rejected_once_retaining_usage(change):
    api = sdk()
    src, data = example()
    if change == "slot":
        data["contexts"][0]["context_id"] = "c13"
    elif change == "event_slot":
        data["events"][0]["event_id"] = "e13"
    elif change == "candidate":
        data["bindings"][0]["candidate_id"] = "n4"
    elif change == "sentence":
        data["bindings"][0]["status_evidence_sentence_id"] = "s1"
    elif change == "status":
        data["bindings"][0]["status_evidence_sentence_id"] = None
    elif change == "unused":
        data["contexts"].append(deepcopy(data["contexts"][0]))
    elif change == "extra":
        data["certified"] = True
    elif change == "missing":
        data.pop("relations")
    elif change == "relation":
        data["relations"] *= 2
    elif change == "scopes":
        data["bindings"][0]["target_scopes"] = [scope("동부", "s2")] * 4
    else:
        key, cap = {
            "contexts_cap": ("contexts", 12),
            "events_cap": ("events", 12),
            "bindings_cap": ("bindings", 12),
            "relations_cap": ("relations", 16),
        }[change]
        data[key] = data[key] * (cap + 1)
    model, calls = response(data)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer_v2(api.create_shared_context_framer_v2(model), src)
    assert len(calls) == 1
    assert caught.value.known_usage.model_dump() == dict(
        input_tokens=100, output_tokens=30, requests=1
    )
    assert str(caught.value) == "Shared context v2 generation failed"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "change",
    [
        "profile",
        "frame_version",
        "prompt",
        "instructions",
        "usage",
        "missing",
        "extra",
        "slot",
        "source",
    ],
)
def test_stored_version_receipts_slots_usage_and_source_are_revalidated(change):
    api = sdk()
    src = document("항목 37여 명 내외.")
    raw = json.loads(run(src).model_dump_json())
    if change == "profile":
        raw["profile"] = "shared-context-generation-v1"
    elif change == "frame_version":
        raw["frame"]["profile"] = "shared-measurement-context-v1"
    elif change == "prompt":
        raw["prompt_sha256"] = "0" * 64
    elif change == "instructions":
        raw["instructions_sha256"] = "0" * 64
    elif change == "usage":
        raw["usage"]["requests"] = 2
    elif change == "missing":
        raw.pop("usage")
    elif change == "extra":
        raw["reviewed"] = True
    elif change == "source":
        src = document("항목 38여 명 내외.")
    else:
        data = packet()
        data["contexts"][0]["context_id"] = data["bindings"][0]["context_id"] = "c13"
        raw["frame"] = json.loads(
            api.build_shared_measurement_frame_v2(src, data).model_dump_json()
        )
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.validate_shared_context_generation_v2(src, raw)
    assert caught.value.known_usage is None


@pytest.mark.parametrize(
    "node", ["frame", "input", "usage", "index", "facts", "context", "purpose", "scope", "subclass"]
)
def test_stored_unchecked_nested_model_types_and_containers_cannot_be_laundered(node):
    api = sdk()
    src, data = example()
    result = run(src, data)
    frame = result.frame
    if node == "frame":
        forged = result.model_copy(update={"frame": frame.model_dump()})
    elif node == "usage":
        forged = result.model_copy(update={"usage": result.usage.model_dump()})
    else:
        if node == "input":
            frame = frame.model_copy(update={"input": frame.input.model_dump()})
        elif node == "index":
            frame = frame.model_copy(update={"candidate_index": frame.candidate_index.model_dump()})
        elif node == "facts":
            frame = frame.model_copy(update={"facts": list(frame.facts)})
        elif node == "context":
            frame = frame.model_copy(
                update={
                    "input": frame.input.model_copy(
                        update={"contexts": (frame.input.contexts[0].model_dump(),)}
                    )
                }
            )
        else:
            fact = frame.facts[0]
            if node == "purpose":
                fact = fact.model_copy(update={"purpose": fact.purpose.model_dump()})
            elif node == "scope":
                fact = fact.model_copy(
                    update={"target_scopes": (fact.target_scopes[0].model_dump(),)}
                )
            else:
                extra = create_model(
                    "ExtraFact",
                    __base__=type(fact),
                    secret=(str, Field(default="hidden", exclude=True)),
                )
                fact = extra.model_validate(fact.model_dump())
            frame = frame.model_copy(update={"facts": (fact, frame.facts[1])})
        forged = result.model_copy(update={"frame": frame})
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation_v2(src, forged)


@pytest.mark.parametrize(
    "node", ["context", "event", "binding", "scope", "anchor", "relation", "cue", "list", "dict"]
)
def test_actual_dynamic_nodes_checked_before_narrowing(monkeypatch, node):
    api = sdk()
    original = api._runtime.Agent.run_sync

    def forged(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        output = result.output
        row, ev, bind, rel = (
            output.contexts[0],
            output.events[0],
            output.bindings[0],
            output.relations[0],
        )
        if node == "list":
            output = output.model_copy(update={"bindings": list(output.bindings)})
        elif node == "dict":
            output = output.model_copy(update={"contexts": (row.model_dump(),)})
        else:
            target = {
                "context": row,
                "event": ev,
                "binding": bind,
                "scope": row.target_scopes[0],
                "anchor": row.measured_variable,
                "relation": rel,
                "cue": rel.cue,
            }[node]
            base = type(target).__bases__[0]
            replacement = base.model_validate_json(target.model_dump_json(), strict=True)
            if node == "context":
                output = output.model_copy(update={"contexts": (replacement,)})
            elif node == "event":
                output = output.model_copy(update={"events": (replacement,)})
            elif node == "binding":
                output = output.model_copy(update={"bindings": (replacement, output.bindings[1])})
            elif node in ("scope", "anchor"):
                row = row.model_copy(
                    update={"target_scopes": (replacement,)}
                    if node == "scope"
                    else {"measured_variable": replacement}
                )
                output = output.model_copy(update={"contexts": (row,)})
            else:
                output = output.model_copy(
                    update={
                        "relations": (
                            replacement
                            if node == "relation"
                            else rel.model_copy(update={"cue": replacement}),
                        )
                    }
                )
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api._runtime.Agent, "run_sync", forged)
    src, data = example()
    with pytest.raises(api.SharedContextGenerationError) as caught:
        run(src, data)
    assert caught.value.known_usage.input_tokens == 100


@pytest.mark.parametrize("schema_sizes", [(111, 999), (999, 111)])
def test_complete_utf8_envelope_inclusive_raw_normalized_boundary(monkeypatch, schema_sizes):
    api = sdk()
    src = document("🧪 항목 37여 명 내외.")
    result = run(src)
    monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: schema_sizes)
    prompt, tools = api._preflight(src)
    limit = (
        len(prompt.encode())
        + len(api.SHARED_CONTEXT_INSTRUCTIONS_V2.encode())
        + max(api._provider_schema_bytes_v5(tools))
        + 2048
        + 2500
    )
    assert len(prompt.encode()) > len(prompt)
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit)
    assert api.shared_context_prompt_v2(src) == prompt
    assert api.validate_shared_context_generation_v2(src, result) == result
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit - 1)
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError):
        api.shared_context_prompt_v2(src)
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation_v2(src, result)
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer_v2(api.create_shared_context_framer_v2(model), src)
    assert calls == []


@pytest.mark.parametrize("text", ["수치 없음.", "항목 37명 " + "가" * 6000])
def test_empty_or_over_budget_source_never_sends_or_truncates(text):
    api = sdk()
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer_v2(api.create_shared_context_framer_v2(model), document(text))
    assert calls == []


def test_long_numeric_sentence_narrows_known_status_and_empty_output_allowed():
    api = sdk()
    src = document("항목 37명 " + "x" * 1001)
    prompt, tools = api._preflight(src)
    assert json.loads(prompt)["eligible_status_sentence_ids"] == []
    data = packet()
    data["contexts"][0]["value_status"] = "observed"
    model, calls = response(data)
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer_v2(api.create_shared_context_framer_v2(model), src)
    assert len(calls) == 1
    assert run(src).frame.facts[0].value_status == "unknown"
    result = run(data=dict(contexts=[], events=[], bindings=[], relations=[]))
    assert result.frame.facts == result.frame.relations == ()
    assert tools[0].strict is True


@pytest.mark.parametrize(
    "options,known",
    [
        ({"text": True}, True),
        ({"error": RuntimeError("private source")}, False),
        ({"inputs": 20001}, False),
        ({"outputs": 2501}, False),
    ],
)
def test_failure_no_retry_repair_fallback_and_nullable_known_usage(options, known):
    api = sdk()
    model, calls = response(packet(), **options)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer_v2(
            api.create_shared_context_framer_v2(model), document("항목 37명.")
        )
    assert len(calls) == 1
    # At token overflow the frozen SDK may discard the captured response;
    # nullable usage stays unknown, never a free-call assertion.
    assert (caught.value.known_usage is not None) == known
    assert str(caught.value) == "Shared context v2 generation failed"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("inputs,outputs", [(17500, 2500), (20000, 0)])
def test_actual_usage_inclusive_limits(inputs, outputs):
    assert run(inputs=inputs, outputs=outputs).usage.model_dump() == dict(
        input_tokens=inputs, output_tokens=outputs, requests=1
    )


@pytest.mark.parametrize(
    "node", ["source_list", "bundle", "representation", "citations", "subclass"]
)
def test_source_actual_nested_types_checked_before_request(node):
    api = sdk()
    src = document("항목 37명.")
    bundle = src[1]
    if node == "source_list":
        src = list(src)
    elif node == "bundle":
        src = (src[0], bundle.model_dump(), src[2])
    else:
        if node == "representation":
            bundle = bundle.model_copy(
                update={"representation": bundle.representation.model_dump()}
            )
        elif node == "citations":
            bundle = bundle.model_copy(update={"citations": list(bundle.citations)})
        else:
            extra = create_model(
                "ExtraBundle",
                __base__=type(bundle),
                secret=(str, Field(default="hidden", exclude=True)),
            )
            bundle = extra.model_validate(bundle.model_dump())
        src = (src[0], bundle, src[2])
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer_v2(api.create_shared_context_framer_v2(model), src)
    assert calls == []


def test_borrowed_runtime_identity_limits_settings_and_v1_bytes_unchanged(monkeypatch):
    api = sdk()
    old = importlib.import_module("issuedigest_agents.shared_context_generation")
    roles = importlib.import_module("issuedigest_agents.role_guided_shared_context")
    src = document("학교 83개교, 이용자 37여 명 내외.")
    old_prompt, old_tools = old._preflight(src)
    old_schema = old_tools[0].output.model_json_schema()
    assert (
        api.SHARED_CONTEXT_INSTRUCTIONS_V2
        == roles.ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS.replace(
            "fill_role_guided_shared_context_v1", "fill_shared_context_v2"
        )
    )
    original_init, original_run = api._runtime.Agent.__init__, api._runtime.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_shared_context_v2"
        assert (
            kwargs["instructions"] == api.SHARED_CONTEXT_INSTRUCTIONS_V2 and kwargs["retries"] == 0
        )
        return original_init(self, *args, **kwargs)

    def called(self, *args, **kwargs):
        limits = kwargs["usage_limits"]
        assert (limits.request_limit, limits.output_tokens_limit, limits.total_tokens_limit) == (
            1,
            2500,
            20000,
        )
        assert kwargs["model_settings"] == dict(openai_store=False, max_tokens=2500, timeout=30)
        assert kwargs["retries"] == 0
        return original_run(self, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Caller owns lifecycle")

    monkeypatch.setattr(api._runtime.Agent, "__init__", initialized)
    monkeypatch.setattr(api._runtime.Agent, "run_sync", called)
    model, calls = response(packet())
    monkeypatch.setattr(model, "__aenter__", forbidden)
    monkeypatch.setattr(model, "__aexit__", forbidden)
    handle = api.create_shared_context_framer_v2(model)
    assert calls == []
    result = api.run_shared_context_framer_v2(handle, src)
    assert result.frame.candidate_index.candidates[0].expression.text == "83개교"
    assert old.shared_context_prompt(src) == old_prompt
    assert old._preflight(src)[1][0].output.model_json_schema() == old_schema
    with pytest.raises(old.SharedContextGenerationError):
        old.validate_shared_context_generation(src, result)
    with pytest.raises(TypeError):
        api.create_shared_context_framer_v2()
    with pytest.raises(api.SharedContextGenerationError):
        api.create_shared_context_framer_v2(None)
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer_v2(SimpleNamespace(model=model), src)


def test_actual_http_wire_strict_complete_v2_schema_preserves_caller_settings(sync_model_loop):
    import httpx2
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    api = sdk()
    src, data = example()
    requests = []

    def transport(request):
        requests.append(request)
        return httpx2.Response(
            200,
            json=dict(
                id="resp_synthetic",
                object="response",
                created_at=1,
                status="completed",
                model="synthetic-model",
                output=[
                    dict(
                        type="function_call",
                        id="fc_synthetic",
                        call_id="call_synthetic",
                        name="fill_shared_context_v2",
                        arguments=json.dumps(data),
                        status="completed",
                    )
                ],
                usage=dict(input_tokens=100, output_tokens=30, total_tokens=130),
            ),
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
        result = api.run_shared_context_framer_v2(api.create_shared_context_framer_v2(model), src)
        assert result.frame.facts[0].purpose.span.text == "지원 목적으로" and len(requests) == 1
        body = json.loads(requests[0].content)
        assert (
            body["store"] is False
            and body["max_output_tokens"] == 2500
            and body["temperature"] == 0.25
        )
        assert len(body["tools"]) == 1
        tool = body["tools"][0]
        assert tool["strict"] is True and tool["name"] == "fill_shared_context_v2"
        assert tool["parameters"]["required"] == ["contexts", "events", "bindings", "relations"]
        assert body["input"][0] == {"role": "user", "content": api.shared_context_prompt_v2(src)}
        assert not client.is_closed
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


def test_cold_import_prompt_validation_and_create_never_allocate_io_or_clients():
    code = """
import builtins, importlib, io, os, socket
from hashlib import sha256
import openai, pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
src = document("Item 37")
def forbidden(*args, **kwargs): raise AssertionError("Unexpected IO/client/key/request")
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
api = importlib.import_module("issuedigest_agents.shared_context_generation_v2")
api.create_shared_context_framer_v2(model)
prompt = api.shared_context_prompt_v2(src)
result = api.SharedContextGenerationV2(
    frame=api.build_shared_measurement_frame_v2(
        src, dict(contexts=[], events=[], bindings=[], relations=[])),
    prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.SHARED_CONTEXT_INSTRUCTIONS_V2.encode()).hexdigest(),
    usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1),
)
assert api.validate_shared_context_generation_v2(src, result) == result
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
