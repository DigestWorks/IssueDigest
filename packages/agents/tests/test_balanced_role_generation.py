"""Synthetic v2 output allocation, reconstructed receipts and borrowed mock wire."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from hashlib import sha256

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document
from test_role_alias_contract import packet, source, without_frame_marker
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


def api():
    name = "issuedigest_agents.balanced_role_generation"
    assert importlib.util.find_spec(name) is not None, "Missing balanced role generation"
    return importlib.import_module(name)


def response(data=None, *, inputs=100, outputs=30, error=None, text=False, completion=None):
    calls = []

    def respond(messages, info):
        calls.append((messages, info))
        if error:
            raise error
        return ModelResponse(
            parts=[TextPart("unstructured")]
            if text
            else [
                ToolCallPart(
                    "fill_shared_role_aliases_v2", json.dumps(packet() if data is None else data)
                )
            ],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
            **(completion or {}),
        )

    return FunctionModel(respond), calls


def run(**options):
    mod = api()
    model, calls = response(**options)
    result = mod.run_balanced_role_framer(mod.create_balanced_role_framer(model), source())
    assert len(calls) == 1
    return result


def test_complete_source_alias_generation_own_profile_and_stored_receipts():
    mod = api()
    got = run()
    assert (got.profile, got.status) == ("shared-role-aliases-v2", "unreviewed")
    assert got.frame.input.model_dump(mode="json") == packet()
    assert got.usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    assert mod.validate_balanced_role_generation(source(), got) == got
    assert mod.validate_balanced_role_generation(source(), json.loads(got.model_dump_json())) == got
    body = json.loads(mod.balanced_role_prompt(source()))
    assert body["profile"] == "shared-role-aliases-v2"
    assert (
        "".join(s["text"] for s in body["quotes"][0]["sentences"])
        == source()[1].citations[0].selector.quote
    )
    assert [c["expression"] for c in body["candidates"]] == ["약\t37여 명 내외", "83개교"]
    assert str(source()[0]) not in mod.balanced_role_prompt(source())
    old = importlib.import_module("issuedigest_agents.role_alias_generation")
    assert type(got) is mod.RoleAliasGenerationV2
    assert not isinstance(got, old.RoleAliasGeneration)
    assert mod.BALANCED_ROLE_INSTRUCTIONS == old.ROLE_ALIAS_INSTRUCTIONS.replace(
        "fill_shared_role_aliases_v1", "fill_shared_role_aliases_v2"
    )
    assert got.prompt_sha256 == sha256(mod.balanced_role_prompt(source()).encode()).hexdigest()
    assert got.instructions_sha256 == sha256(mod.BALANCED_ROLE_INSTRUCTIONS.encode()).hexdigest()
    for key in ("prompt_sha256", "instructions_sha256"):
        old_hash = sha256(
            (
                old.role_alias_prompt(source())
                if key == "prompt_sha256"
                else old.ROLE_ALIAS_INSTRUCTIONS
            ).encode()
        ).hexdigest()
        bad = got.model_dump(mode="json")
        bad[key] = old_hash
        with pytest.raises(mod.BalancedRoleGenerationError):
            mod.validate_balanced_role_generation(source(), bad)


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "field", ["profile", "status", "frame", "prompt_sha256", "instructions_sha256", "usage"]
)
def test_all_generation_markers_required_before_dump(field, actual):
    mod = api()
    got = run()
    altered = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    del (altered.__dict__ if actual else altered)[field]
    with pytest.raises(mod.BalancedRoleGenerationError):
        mod.validate_balanced_role_generation(source(), altered)


@pytest.mark.parametrize(
    "mutation",
    ["subclass", "nested_subclass", "extra", "frame_dict", "bindings_list", "input_dict"],
)
def test_actual_receipts_reject_subclasses_extras_and_unchecked_containers(mutation):
    mod = api()
    got = run()
    if mutation == "subclass":

        class Derived(mod.RoleAliasGenerationV2):
            pass

        altered = Derived(**got.__dict__)
    elif mutation == "nested_subclass":

        class DerivedFrame(type(got.frame)):
            pass

        altered = got.model_copy(update={"frame": DerivedFrame(**got.frame.__dict__)})
    elif mutation == "extra":
        altered = got.model_copy()
        altered.__dict__["hidden"] = "unexpected"
    elif mutation == "frame_dict":
        altered = got.model_copy(update={"frame": got.frame.model_dump(mode="json")})
    elif mutation == "bindings_list":
        frame = got.frame.model_copy(
            update={
                "input": got.frame.input.model_copy(
                    update={"bindings": list(got.frame.input.bindings)}
                )
            }
        )
        altered = got.model_copy(update={"frame": frame})
    else:
        frame = got.frame.model_copy(update={"input": got.frame.input.model_dump(mode="json")})
        altered = got.model_copy(update={"frame": frame})
    with pytest.raises(mod.BalancedRoleGenerationError):
        mod.validate_balanced_role_generation(source(), altered)


@pytest.mark.parametrize(
    "inputs,outputs,accepted", [(18200, 1800, True), (18201, 1800, False), (100, 1801, False)]
)
def test_new_generation_inclusive_total_and_output_cap_retains_raw_overflow(
    inputs, outputs, accepted
):
    mod = api()
    if accepted:
        assert run(inputs=inputs, outputs=outputs).usage.output_tokens == outputs
    else:
        model, calls = response(inputs=inputs, outputs=outputs)
        with pytest.raises(mod.BalancedRoleGenerationError) as caught:
            mod.run_balanced_role_framer(mod.create_balanced_role_framer(model), source())
        assert len(calls) == 1
        assert caught.value.may_have_started is True
        assert caught.value.known_usage.model_dump() == dict(
            input_tokens=inputs, output_tokens=outputs, requests=1
        )


@pytest.mark.parametrize(
    "completion,accepted",
    [
        ({}, True),
        ({"finish_reason": "tool_call", "state": "complete"}, True),
        ({"state": "incomplete"}, False),
        ({"finish_reason": "length"}, False),
        ({"provider_details": {"finish_reason": "max_output_tokens"}}, False),
        ({"provider_details": {"finish_reason": "incomplete"}}, False),
    ],
)
def test_valid_tool_json_respects_explicit_incompletion_and_preserves_cap_usage(
    completion, accepted
):
    mod = api()
    model, calls = response(outputs=1800, completion=completion)
    framer = mod.create_balanced_role_framer(model)
    if accepted:
        assert mod.run_balanced_role_framer(framer, source()).usage.output_tokens == 1800
    else:
        with pytest.raises(mod.BalancedRoleGenerationError) as caught:
            mod.run_balanced_role_framer(framer, source())
        assert caught.value.may_have_started is True
        assert caught.value.known_usage.model_dump() == dict(
            input_tokens=100, output_tokens=1800, requests=1
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "kind", ["network", "text", "invalid", "oversize_source", "bad_model", "unchecked_source"]
)
def test_failures_distinguish_preflight_zero_send_started_unknown_and_known(kind):
    mod = api()
    kwargs = {}
    if kind == "network":
        kwargs["error"] = RuntimeError("sensitive-provider-detail")
    elif kind == "text":
        kwargs["text"] = True
    elif kind == "invalid":
        bad = packet()
        del bad["bindings"][0]["change"]
        kwargs["data"] = bad
    model, calls = response(**kwargs)
    src = source()
    framer = mod.create_balanced_role_framer(model)
    if kind == "oversize_source":
        src = document("설명 " * 8000 + "37명.")
    elif kind == "bad_model":
        framer = object()
    elif kind == "unchecked_source":
        src = src[0], src[1].model_copy(update={"citations": list(src[1].citations)}), src[2]
    with pytest.raises(mod.BalancedRoleGenerationError) as caught:
        mod.run_balanced_role_framer(framer, src)
    sent = kind in ("network", "text", "invalid")
    assert len(calls) == int(sent)
    assert caught.value.may_have_started is sent
    assert (caught.value.known_usage is not None) == (kind in ("text", "invalid"))
    assert "sensitive" not in str(caught.value) and caught.value.__cause__ is None


def test_final_revalidation_failure_preserves_already_observed_usage(monkeypatch):
    mod = api()
    original = mod._preflight
    preflight_calls = 0

    def changed_revalidation_prompt(src):
        nonlocal preflight_calls
        preflight_calls += 1
        prompt, tools = original(src)
        return (prompt if preflight_calls == 1 else prompt + " "), tools

    monkeypatch.setattr(mod, "_preflight", changed_revalidation_prompt)
    model, calls = response(inputs=100, outputs=30)
    with pytest.raises(mod.BalancedRoleGenerationError) as caught:
        mod.run_balanced_role_framer(mod.create_balanced_role_framer(model), source())
    assert preflight_calls == 2 and len(calls) == 1
    assert caught.value.may_have_started is True
    assert caught.value.known_usage.model_dump() == dict(
        input_tokens=100, output_tokens=30, requests=1
    )
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "mutation",
    ["profile", "status", "hash", "instruction", "usage", "requests", "nested", "source"],
)
def test_stored_generation_rejects_markers_receipt_source_and_actual_type_drift(mutation):
    mod = api()
    got = run()
    raw = got.model_dump(mode="json")
    src = source()
    if mutation in ("profile", "status"):
        del raw[mutation]
    elif mutation == "hash":
        raw["prompt_sha256"] = "0" * 64
    elif mutation == "instruction":
        raw["instructions_sha256"] = "0" * 64
    elif mutation == "usage":
        raw["usage"]["output_tokens"] = 1801
    elif mutation == "requests":
        raw["usage"]["requests"] = 2
    elif mutation == "nested":
        raw = got.model_copy(update={"frame": raw["frame"]})
    else:
        src = document("이용자 약\t37여 명 내외 증가, 학교 83개교 감소. 추가.")
    with pytest.raises(mod.BalancedRoleGenerationError):
        mod.validate_balanced_role_generation(src, raw)


@pytest.mark.parametrize("path", [(), ("frame",), ("frame", "candidate_index")])
@pytest.mark.parametrize("marker", ["profile", "status"])
@pytest.mark.parametrize("actual", [False, True])
def test_generation_missing_nested_markers_rejected_before_raw_or_actual_default_restoration(
    path, marker, actual
):
    mod = api()
    got = run()
    altered_frame = without_frame_marker(got.frame, path, marker, actual)
    if actual:
        altered = got.model_copy(update={"frame": altered_frame})
    else:
        altered = got.model_dump(mode="json")
        altered["frame"] = altered_frame
    with pytest.raises(mod.BalancedRoleGenerationError):
        mod.validate_balanced_role_generation(source(), altered)


def test_actual_dynamic_output_and_nested_types_are_checked_before_conversion(monkeypatch):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    prompt, tools = mod._preflight(source())
    dynamic_type = tools[0].output
    good = dynamic_type.model_validate_json(json.dumps(packet()), strict=True)
    for malformed in (
        good.model_dump(mode="json"),
        good.model_copy(update={"bindings": list(good.bindings)}),
    ):
        original = runtime.Agent

        class ForgedAgent:
            def __init__(self, *args, _original=original, **kwargs):
                self.inner = _original(*args, **kwargs)

            def run_sync(self, *args, _malformed=malformed, **kwargs):
                real = self.inner.run_sync(*args, **kwargs)
                return type(
                    "Result",
                    (),
                    dict(output=_malformed, usage=real.usage, all_messages=real.all_messages),
                )()

        with monkeypatch.context() as patch:
            patch.setattr(runtime, "Agent", ForgedAgent)
            model, _ = response()
            with pytest.raises(runtime.RoleRequestError):
                runtime._run_role_request(
                    model=model,
                    prompt=prompt,
                    tools=tools,
                    instructions=mod.BALANCED_ROLE_INSTRUCTIONS,
                    identity=mod.PROVIDER_IDENTITY,
                    total_limit=20000,
                    output_limit=1800,
                )


def test_preflight_measures_actual_normalized_schema_and_exact_boundary(monkeypatch):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    schema = importlib.import_module("issuedigest_agents.research_v5")
    prompt, tools = mod._preflight(source())
    envelope = (
        len(prompt.encode())
        + len(mod.BALANCED_ROLE_INSTRUCTIONS.encode())
        + max(schema._provider_schema_bytes_v5(tools))
        + 2048
        + 1800
    )
    assert envelope <= 20000
    model, calls = response()
    # The reusable runtime honors arbitrary remaining limits, including the exact envelope.
    with pytest.raises(runtime.RoleRequestError) as caught:
        runtime._run_role_request(
            model=model,
            prompt=prompt,
            tools=tools,
            instructions=mod.BALANCED_ROLE_INSTRUCTIONS,
            identity=mod.PROVIDER_IDENTITY,
            total_limit=envelope - 1,
            output_limit=1800,
        )
    assert calls == [] and caught.value.may_have_started is False
    runtime._run_role_request(
        model=model,
        prompt=prompt,
        tools=tools,
        instructions=mod.BALANCED_ROLE_INSTRUCTIONS,
        identity=mod.PROVIDER_IDENTITY,
        total_limit=envelope,
        output_limit=1800,
    )
    assert len(calls) == 1
    model, calls = response(outputs=18)
    output, usage = runtime._run_role_request(
        model=model,
        prompt=prompt,
        tools=tools,
        instructions=mod.BALANCED_ROLE_INSTRUCTIONS,
        identity=mod.PROVIDER_IDENTITY,
        total_limit=20000,
        output_limit=18,
    )
    assert type(output) is tools[0].output and usage.output_tokens == 18

    # The v2 preflight itself must reserve the actual normalized schema and output.
    other_bytes = len(prompt.encode()) + len(mod.BALANCED_ROLE_INSTRUCTIONS.encode()) + 2048 + 1800
    normalized_boundary = 20000 - other_bytes
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "_provider_schema_bytes_v5", lambda tools: (1, normalized_boundary))
        assert mod.balanced_role_prompt(source()) == prompt
        patch.setattr(
            runtime, "_provider_schema_bytes_v5", lambda tools: (1, normalized_boundary + 1)
        )
        model, calls = response()
        with pytest.raises(mod.BalancedRoleGenerationError) as caught:
            mod.run_balanced_role_framer(mod.create_balanced_role_framer(model), source())
        assert calls == [] and caught.value.may_have_started is False


@pytest.mark.parametrize(
    "status,incomplete_details",
    [
        ("completed", None),
        ("incomplete", {"reason": "max_output_tokens"}),
        ("incomplete", None),
    ],
)
def test_mock_http_wire_has_alias_only_schema_cap_no_store_and_borrowed_lifecycle(
    sync_model_loop, status, incomplete_details
):
    import httpx2 as httpx
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    mod = api()
    requests = []
    timeouts = []

    def handler(request):
        requests.append(json.loads(request.content))
        timeouts.append(request.extensions["timeout"])
        return httpx.Response(
            200,
            json={
                "id": "resp_synthetic",
                "object": "response",
                "created_at": 0,
                "status": status,
                "incomplete_details": incomplete_details,
                "model": "synthetic-model",
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc_synthetic",
                        "call_id": "call_synthetic",
                        "name": "fill_shared_role_aliases_v2",
                        "arguments": json.dumps(packet()),
                        "status": "completed",
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 1800, "total_tokens": 1900},
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider_client = AsyncOpenAI(api_key="synthetic", http_client=client, max_retries=0)
    try:
        model = OpenAIResponsesModel(
            "synthetic-model",
            provider=OpenAIProvider(openai_client=provider_client),
            settings={"temperature": 0.25, "openai_reasoning_effort": "low"},
        )
        framer = mod.create_balanced_role_framer(model)
        if status == "completed":
            assert mod.run_balanced_role_framer(framer, source()).usage.output_tokens == 1800
        else:
            with pytest.raises(mod.BalancedRoleGenerationError) as caught:
                mod.run_balanced_role_framer(framer, source())
            assert caught.value.may_have_started is True
            assert caught.value.known_usage.model_dump() == dict(
                input_tokens=100, output_tokens=1800, requests=1
            )
        assert not client.is_closed
        assert len(requests) == 1
        assert all(value == 30 for value in timeouts[0].values())
        wire = requests[0]
        assert (
            wire["store"] is False
            and wire["max_output_tokens"] == 1800
            and wire["temperature"] == 0.25
        )
        assert len(wire["tools"]) == 1 and wire["tools"][0]["strict"] is True
        assert wire["tools"][0]["name"] == "fill_shared_role_aliases_v2"
        assert wire["reasoning"]["effort"] == "low"
        assert wire["instructions"] == mod.BALANCED_ROLE_INSTRUCTIONS
        params = wire["tools"][0]["parameters"]
        assert params["required"] == ["contexts", "events", "bindings", "relations"]
        definitions = params["$defs"]
        relation = definitions["RoleRelationV1"]
        assert set(relation["properties"]) == {"kind", "from", "to", "support", "cue"}
        binding = definitions["RoleBindingV1"]
        assert set(binding["properties"]) == {
            "number",
            "context",
            "scopes",
            "status_sentence",
            "change",
        }
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


def test_cold_import_prompt_create_and_stored_validation_have_no_io():
    code = """
import builtins, importlib, io, os, socket
from hashlib import sha256
import openai, pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
from test_role_alias_contract import packet
src=document("이용자 약\\t37여 명 내외 증가, 학교 83개교 감소.")
def forbidden(*args, **kwargs): raise AssertionError("Unexpected IO/client/key/request")
model=FunctionModel(forbidden)
openai.AsyncOpenAI.__init__=openai.OpenAI.__init__=forbidden
pydantic_ai.Agent.__init__=forbidden
original=type(os.environ).__getitem__
def no_env(self,key):
    if key != "PYDANTIC_DISABLE_PLUGINS": forbidden()
    return original(self,key)
type(os.environ).__getitem__=no_env
builtins.open=io.open=forbidden
socket.socket=forbidden
api=importlib.import_module("issuedigest_agents.balanced_role_generation")
contract=importlib.import_module("issuedigest_agents.role_alias_contract")
from issuedigest_agents.numeric_evidence import KnownUsage
api.create_balanced_role_framer(model)
prompt=api.balanced_role_prompt(src)
result=api.RoleAliasGenerationV2(profile="shared-role-aliases-v2",status="unreviewed",
    frame=contract.build_role_alias_frame(src,packet()),prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.BALANCED_ROLE_INSTRUCTIONS.encode()).hexdigest(),
    usage=KnownUsage(input_tokens=0,output_tokens=0,requests=1))
assert api.validate_balanced_role_generation(src,result)==result
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
