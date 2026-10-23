"""Synthetic columnar receipts, exact source boundaries and borrowed Responses wire."""

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
    name = "issuedigest_agents.columnar_role_generation"
    assert importlib.util.find_spec(name) is not None, "Missing columnar role generation SDK"
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
                    "fill_columnar_roles_v1", json.dumps(packet() if data is None else data)
                )
            ],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
            **(completion or {}),
        )

    return FunctionModel(respond), calls


def run(**options):
    mod = api()
    model, calls = response(**options)
    result = mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
    assert len(calls) == 1
    return result


def test_complete_source_receipt_has_distinct_identity_and_lossless_codec_prompt():
    mod = api()
    got = run()
    assert (got.profile, got.input_format, got.status) == (
        "columnar-role-generation-v1",
        "columnar-generation-source-v1",
        "unreviewed",
    )
    assert mod.PROVIDER_IDENTITY == "issuedigest_columnar_role_generation_v1"
    assert got.frame.input.model_dump(mode="json") == packet()
    assert got.frame.status == got.frame.frame.status == "unreviewed"
    assert got.usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    checked = mod.validate_columnar_role_generation(source(), got)
    assert checked == got and checked is not got
    assert mod.validate_columnar_role_generation(source(), json.loads(got.model_dump_json())) == got
    codec = importlib.import_module("issuedigest_agents.generation_source_packet")
    prompt = mod.columnar_role_prompt(source())
    assert prompt == codec.generation_source_packet_prompt(source())
    encoded = json.loads(prompt)
    assert encoded["profile"] == "shared-role-aliases-v2"
    assert encoded["input_format"] == "columnar-generation-source-v1"
    decoded = codec.decode_generation_source_packet(source(), encoded)
    assert "".join(s["text"] for s in decoded["quotes"][0]["sentences"]) == (
        "이용자 약\t37여 명 내외 증가, 학교 83개교 감소."
    )
    assert [c["id"] for c in decoded["candidates"]] == ["n1", "n2"]
    assert [c["expression"] for c in decoded["candidates"]] == ["약\t37여 명 내외", "83개교"]
    assert decoded["context_id_slots"] == [f"c{i}" for i in range(1, 13)]
    assert decoded["reporting_event_id_slots"] == [f"e{i}" for i in range(1, 13)]
    assert str(source()[0]) not in prompt
    assert str(source()[1].citations[0].citation_id) not in prompt
    old = importlib.import_module("issuedigest_agents.balanced_role_generation")
    assert type(got) is mod.ColumnarRoleGeneration
    assert not isinstance(got, old.RoleAliasGenerationV2)
    expected = old.BALANCED_ROLE_INSTRUCTIONS.replace(
        "fill_shared_role_aliases_v2", "fill_columnar_roles_v1"
    ).replace(
        "Each quote contains complete ordered sentences {id,text}; concatenate without separators, "
        "preserving whitespace and blank sentences. ",
        "Input format is columnar-generation-source-v1. "
        "Columns align by zero-based row. values stores a vector; constant repeats one value; "
        "dictionary stores pool,indices; indexed stores prefix,suffixes; indexed_lists stores "
        "prefix,suffix-lists. Atoms use atom_columns. "
        "Concatenate decoded quote sentences without separators, "
        "preserving whitespace and blanks. ",
    )
    assert mod.COLUMNAR_ROLE_INSTRUCTIONS == expected
    assert got.prompt_sha256 == sha256(prompt.encode()).hexdigest()
    assert got.instructions_sha256 == sha256(expected.encode()).hexdigest()
    for key in ("prompt_sha256", "instructions_sha256"):
        old_hash = sha256(
            (
                old.balanced_role_prompt(source())
                if key == "prompt_sha256"
                else old.BALANCED_ROLE_INSTRUCTIONS
            ).encode()
        ).hexdigest()
        bad = got.model_dump(mode="json")
        bad[key] = old_hash
        with pytest.raises(mod.ColumnarRoleGenerationError):
            mod.validate_columnar_role_generation(source(), bad)


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "field",
    ["profile", "input_format", "status", "frame", "prompt_sha256", "instructions_sha256", "usage"],
)
def test_all_generation_markers_required_before_dump(field, actual):
    mod = api()
    got = run()
    altered = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    del (altered.__dict__ if actual else altered)[field]
    with pytest.raises(mod.ColumnarRoleGenerationError):
        mod.validate_columnar_role_generation(source(), altered)


@pytest.mark.parametrize(
    "mutation",
    ["subclass", "nested_subclass", "extra", "frame_dict", "bindings_list", "input_dict"],
)
def test_actual_receipts_reject_subclasses_extras_and_unchecked_containers(mutation):
    mod = api()
    got = run()
    if mutation == "subclass":

        class Derived(mod.ColumnarRoleGeneration):
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
    with pytest.raises(mod.ColumnarRoleGenerationError):
        mod.validate_columnar_role_generation(source(), altered)


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
        with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
            mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
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
    framer = mod.create_columnar_role_framer(model)
    if accepted:
        assert mod.run_columnar_role_framer(framer, source()).usage.output_tokens == 1800
    else:
        with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
            mod.run_columnar_role_framer(framer, source())
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
    framer = mod.create_columnar_role_framer(model)
    if kind == "oversize_source":
        src = document("설명 " * 8000 + "37명.")
    elif kind == "bad_model":
        framer = object()
    elif kind == "unchecked_source":
        src = src[0], src[1].model_copy(update={"citations": list(src[1].citations)}), src[2]
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(framer, src)
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
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
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
    with pytest.raises(mod.ColumnarRoleGenerationError):
        mod.validate_columnar_role_generation(src, raw)


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
    with pytest.raises(mod.ColumnarRoleGenerationError):
        mod.validate_columnar_role_generation(source(), altered)


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
                    instructions=mod.COLUMNAR_ROLE_INSTRUCTIONS,
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
        + len(mod.COLUMNAR_ROLE_INSTRUCTIONS.encode())
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
            instructions=mod.COLUMNAR_ROLE_INSTRUCTIONS,
            identity=mod.PROVIDER_IDENTITY,
            total_limit=envelope - 1,
            output_limit=1800,
        )
    assert calls == [] and caught.value.may_have_started is False
    runtime._run_role_request(
        model=model,
        prompt=prompt,
        tools=tools,
        instructions=mod.COLUMNAR_ROLE_INSTRUCTIONS,
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
        instructions=mod.COLUMNAR_ROLE_INSTRUCTIONS,
        identity=mod.PROVIDER_IDENTITY,
        total_limit=20000,
        output_limit=18,
    )
    assert type(output) is tools[0].output and usage.output_tokens == 18

    # The v2 preflight itself must reserve the actual normalized schema and output.
    other_bytes = len(prompt.encode()) + len(mod.COLUMNAR_ROLE_INSTRUCTIONS.encode()) + 2048 + 1800
    normalized_boundary = 20000 - other_bytes
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "_provider_schema_bytes_v5", lambda tools: (1, normalized_boundary))
        assert mod.columnar_role_prompt(source()) == prompt
        patch.setattr(
            runtime, "_provider_schema_bytes_v5", lambda tools: (1, normalized_boundary + 1)
        )
        model, calls = response()
        with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
            mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
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
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.providers.openai import OpenAIProvider
    from pydantic_ai.tools import GenerateToolJsonSchema

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
                        "name": "fill_columnar_roles_v1",
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
        framer = mod.create_columnar_role_framer(model)
        if status == "completed":
            assert mod.run_columnar_role_framer(framer, source()).usage.output_tokens == 1800
        else:
            with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
                mod.run_columnar_role_framer(framer, source())
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
        assert wire["tools"][0]["name"] == "fill_columnar_roles_v1"
        assert wire["reasoning"]["effort"] == "low"
        assert wire["instructions"] == mod.COLUMNAR_ROLE_INSTRUCTIONS
        assert wire["input"] == [dict(role="user", content=mod.columnar_role_prompt(source()))]
        params = wire["tools"][0]["parameters"]
        output_type = mod._preflight(source())[1][0].output
        raw_schema = output_type.model_json_schema(schema_generator=GenerateToolJsonSchema)
        assert params == OpenAIJsonSchemaTransformer(raw_schema, strict=True).walk()
        assert params["required"] == ["contexts", "events", "bindings", "relations"]
        definitions = params["$defs"]
        assert definitions["RoleNumberV1"]["enum"] == ["n1", "n2"]
        assert definitions["RoleSentenceV1"]["const"] == "s1"
        assert definitions["RoleContextIdV1"]["enum"] == [f"c{i}" for i in range(1, 13)]
        assert definitions["RoleEventIdV1"]["enum"] == [f"e{i}" for i in range(1, 13)]
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
api=importlib.import_module("issuedigest_agents.columnar_role_generation")
contract=importlib.import_module("issuedigest_agents.role_alias_contract")
from issuedigest_agents.numeric_evidence import KnownUsage
api.create_columnar_role_framer(model)
prompt=api.columnar_role_prompt(src)
result=api.ColumnarRoleGeneration(profile="columnar-role-generation-v1",input_format="columnar-generation-source-v1",status="unreviewed",
    frame=contract.build_role_alias_frame(src,packet()),prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.COLUMNAR_ROLE_INSTRUCTIONS.encode()).hexdigest(),
    usage=KnownUsage(input_tokens=0,output_tokens=0,requests=1))
assert api.validate_columnar_role_generation(src,result)==result
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_empty_candidate_catalog_codec_preserved_but_generation_rejects_without_dispatch():
    mod = api()
    codec = importlib.import_module("issuedigest_agents.generation_source_packet")
    text = "설명만 있는 원문."
    src = document(text)
    prompt = codec.generation_source_packet_prompt(src)
    decoded = codec.decode_generation_source_packet(src, json.loads(prompt))
    assert decoded["quotes"] == [dict(quote_id="q1", sentences=[dict(id="s1", text=text)])]
    assert decoded["candidates"] == []
    model, calls = response(data=dict(contexts=[], events=[], bindings=[], relations=[]))
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), src)
    assert calls == [] and caught.value.may_have_started is False
    assert caught.value.known_usage is None
    assert str(caught.value) == "Invalid columnar role generation input"


def test_legal_long_id_like_literal_codec_roundtrip_and_exact_envelope_rejection():
    mod = api()
    codec = importlib.import_module("issuedigest_agents.generation_source_packet")
    candidates = importlib.import_module("issuedigest_agents.numeric_candidates_v2")
    contract = importlib.import_module("issuedigest_agents.role_alias_contract")
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    from pydantic_ai import ToolOutput

    text = "q" + "1" * 4301
    src = document(text)
    prompt = codec.generation_source_packet_prompt(src)
    decoded = codec.decode_generation_source_packet(src, json.loads(prompt))
    assert decoded["quotes"] == [dict(quote_id="q1", sentences=[dict(id="s1", text=text)])]
    index = candidates.build_numeric_candidates_v2(src)
    tools = [ToolOutput(contract._input_model(index), name="fill_columnar_roles_v1", strict=True)]
    assert runtime._request_envelope(prompt, tools, mod.COLUMNAR_ROLE_INSTRUCTIONS, 1800) == 27621
    model, calls = response()
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), src)
    assert calls == [] and caught.value.may_have_started is False
    assert caught.value.known_usage is None
    assert str(caught.value) == "Invalid columnar role generation input"


def test_complete_multiquote_whitespace_and_all_candidates_preserved_without_lower_cap():
    mod = api()
    codec = importlib.import_module("issuedigest_agents.generation_source_packet")
    src = document("  첫째 7명.\n\n 둘째 8명. ", "셋째 9명.\n ")
    decoded = codec.decode_generation_source_packet(src, json.loads(mod.columnar_role_prompt(src)))
    assert ["".join(s["text"] for s in q["sentences"]) for q in decoded["quotes"]] == [
        "  첫째 7명.\n\n 둘째 8명. ",
        "셋째 9명.\n ",
    ]
    assert [c["id"] for c in decoded["candidates"]] == ["n1", "n2", "n3"]
    assert [c["expression"] for c in decoded["candidates"]] == ["7명", "8명", "9명"]


@pytest.mark.parametrize("side", ["input", "output"])
@pytest.mark.parametrize("value", [-1, True, 1.5, "2"])
def test_raw_noninteger_bool_negative_usage_rejected_without_invented_known_cost(side, value):
    mod = api()
    options = {"inputs" if side == "input" else "outputs": value}
    model, calls = response(**options)
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
    assert len(calls) == 1 and caught.value.may_have_started is True
    assert caught.value.known_usage is None
    assert str(caught.value) == "Columnar role generation failed"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "kind", ["malformed", "unknown", "multiple", "text", "mixed", "mixed_text"]
)
def test_runtime_rejects_bad_response_shapes_once_with_observed_usage(kind):
    mod = api()
    parts = [ToolCallPart("fill_columnar_roles_v1", json.dumps(packet()))]
    if kind == "malformed":
        parts = [ToolCallPart("fill_columnar_roles_v1", "{private-malformed")]
    elif kind == "unknown":
        parts = [ToolCallPart("fill_shared_role_aliases_v2", json.dumps(packet()))]
    elif kind == "multiple":
        parts *= 2
    elif kind == "text":
        parts = [TextPart("private refusal")]
    elif kind == "mixed":
        parts += [ToolCallPart("unregistered_tool", "{}")]
    else:
        parts += [TextPart("private unstructured surplus")]
    calls = []

    def respond(messages, info):
        calls.append(info)
        return ModelResponse(parts=parts, usage=RequestUsage(input_tokens=100, output_tokens=30))

    model = FunctionModel(respond)
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
    assert len(calls) == 1 and caught.value.may_have_started is True
    assert caught.value.known_usage.model_dump() == dict(
        input_tokens=100, output_tokens=30, requests=1
    )
    assert str(caught.value) == "Columnar role generation failed"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("dominant", ["raw", "normalized"])
def test_sdk_preflight_accepts_exact_schema_envelope_and_rejects_one_byte_more(
    monkeypatch, dominant
):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    prompt = mod.columnar_role_prompt(source())
    remaining = (
        20000 - len(prompt.encode()) - len(mod.COLUMNAR_ROLE_INSTRUCTIONS.encode()) - 2048 - 1800
    )
    sizes = (remaining, 1) if dominant == "raw" else (1, remaining)
    monkeypatch.setattr(runtime, "_provider_schema_bytes_v5", lambda tools: sizes)
    assert mod.columnar_role_prompt(source()) == prompt
    assert run().profile == "columnar-role-generation-v1"
    sizes = (remaining + 1, 1) if dominant == "raw" else (1, remaining + 1)
    model, calls = response()
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), source())
    assert calls == [] and caught.value.may_have_started is False
    assert caught.value.known_usage is None
    assert str(caught.value) == "Invalid columnar role generation input"


def test_valid_long_source_remains_whole_and_fails_only_full_envelope_before_send():
    mod = api()
    codec = importlib.import_module("issuedigest_agents.generation_source_packet")
    contract = importlib.import_module("issuedigest_agents.role_alias_contract")
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    candidates = importlib.import_module("issuedigest_agents.numeric_candidates_v2")
    from pydantic_ai import ToolOutput

    text = "설명 " * 1000 + "37명."
    src = document(text)
    prompt = codec.generation_source_packet_prompt(src)
    decoded = codec.decode_generation_source_packet(src, json.loads(prompt))
    assert "".join(s["text"] for s in decoded["quotes"][0]["sentences"]) == text
    index = candidates.build_numeric_candidates_v2(src)
    tools = [ToolOutput(contract._input_model(index), name="fill_columnar_roles_v1", strict=True)]
    assert runtime._request_envelope(prompt, tools, mod.COLUMNAR_ROLE_INSTRUCTIONS, 1800) > 20000
    model, calls = response()
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), src)
    assert calls == [] and caught.value.may_have_started is False
    assert caught.value.known_usage is None
    assert str(caught.value) == "Invalid columnar role generation input"


@pytest.mark.parametrize(
    "mutation",
    [
        "root_list",
        "source_list",
        "source_subclass",
        "citation_list",
        "quote_subclass",
        "source_key",
    ],
)
def test_original_source_types_rejected_before_conversion_and_without_dispatch(mutation):
    mod = api()
    src = source()
    if mutation == "root_list":
        src = list(src)
    elif mutation == "source_list":
        src = src[0], src[1].model_dump(mode="json"), src[2]
    elif mutation == "source_subclass":

        class Derived(type(src[1])):
            pass

        src = src[0], Derived(**src[1].__dict__), src[2]
    elif mutation == "citation_list":
        src = src[0], src[1].model_copy(update={"citations": list(src[1].citations)}), src[2]
    elif mutation == "quote_subclass":

        class Derived(str):
            pass

        citation = src[1].citations[0]
        citation = citation.model_copy(
            update={
                "selector": citation.selector.model_copy(
                    update={"quote": Derived(citation.selector.quote)}
                )
            }
        )
        src = src[0], src[1].model_copy(update={"citations": (citation,)}), src[2]
    else:
        bundle = src[1].model_copy()
        bundle.__dict__["unexpected"] = "private"
        src = src[0], bundle, src[2]
    model, calls = response()
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.run_columnar_role_framer(mod.create_columnar_role_framer(model), src)
    assert calls == [] and caught.value.may_have_started is False
    assert caught.value.known_usage is None


@pytest.mark.parametrize(
    "mutation",
    [
        "old_profile",
        "format",
        "old_class",
        "catalog",
        "input_number",
        "raw_tuple",
        "raw_key",
        "raw_scalar",
        "actual_usage_dict",
        "actual_usage_bool",
        "actual_change_dict",
    ],
)
def test_stored_receipts_reject_old_catalog_and_exact_raw_actual_type_drift(mutation):
    mod = api()
    got = run()
    bad = got.model_dump(mode="json")
    if mutation == "old_profile":
        bad["profile"] = "shared-role-aliases-v2"
    elif mutation == "format":
        bad["input_format"] = "numeric-candidates-v2"
    elif mutation == "old_class":
        old = importlib.import_module("issuedigest_agents.balanced_role_generation")
        fields = dict(got.__dict__)
        fields.pop("input_format")
        fields["profile"] = "shared-role-aliases-v2"
        bad = old.RoleAliasGenerationV2(**fields)
    elif mutation == "catalog":
        bad["frame"]["frame"]["candidate_index"]["candidates"][0]["candidate_id"] = "n99"
    elif mutation == "input_number":
        bad["frame"]["input"]["bindings"][0]["number"] = "n99"
    elif mutation == "raw_tuple":
        bad["frame"]["input"]["bindings"] = tuple(bad["frame"]["input"]["bindings"])
    elif mutation == "raw_key":
        bad[1] = bad.pop("usage")
    elif mutation == "raw_scalar":

        class Derived(str):
            pass

        bad["profile"] = Derived(bad["profile"])
    elif mutation == "actual_usage_dict":
        bad = got.model_copy(update={"usage": got.usage.model_dump()})
    elif mutation == "actual_usage_bool":
        bad = got.model_copy(update={"usage": got.usage.model_copy(update={"requests": True})})
    else:
        binding = got.frame.input.bindings[0]
        binding = binding.model_copy(update={"change": binding.change.model_dump()})
        frame = got.frame.model_copy(
            update={"input": got.frame.input.model_copy(update={"bindings": (binding,)})}
        )
        bad = got.model_copy(update={"frame": frame})
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.validate_columnar_role_generation(source(), bad)
    assert str(caught.value) == "Invalid columnar role generation"
    assert caught.value.known_usage is None and caught.value.may_have_started is False
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("bad_model", [None, "openai:synthetic", object()])
def test_constructor_requires_actual_borrowed_model_and_fixed_failure(bad_model):
    mod = api()
    with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
        mod.create_columnar_role_framer(bad_model)
    assert str(caught.value) == "Invalid columnar role generation model"
    assert caught.value.known_usage is None and caught.value.may_have_started is False
    assert caught.value.__cause__ is None


def test_empty_selected_output_uses_one_request_with_complete_catalog_retained():
    got = run(data=dict(contexts=[], events=[], bindings=[], relations=[]))
    assert got.frame.input.model_dump(mode="json") == dict(
        contexts=[], events=[], bindings=[], relations=[]
    )
    assert len(got.frame.frame.candidate_index.candidates) == 2
    assert got.usage.requests == 1 and got.status == "unreviewed"


@pytest.mark.parametrize("direction", [None, "uncertain", "decrease"])
def test_role_unknown_null_and_unreviewed_semantics_are_preserved(direction):
    data = packet()
    if direction is None:
        data["bindings"][0]["change"] = None
    elif direction == "uncertain":
        data["bindings"][0]["change"].update(direction="uncertain", evidence=None)
    else:
        data["bindings"][0]["change"]["direction"] = "decrease"
    got = run(data=data)
    assert got.frame.input.model_dump(mode="json") == data
    assert got.status == got.frame.status == "unreviewed"
    assert got.frame.input.contexts[0].status == "unknown"
    assert got.frame.input.events[0].tense == "unknown"


@pytest.mark.parametrize("field", ["input_tokens", "output_tokens", "requests"])
@pytest.mark.parametrize("actual", [False, True])
def test_usage_fields_required_before_stored_read(field, actual):
    mod = api()
    got = run()
    altered = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    usage = altered.usage.__dict__ if actual else altered["usage"]
    del usage[field]
    with pytest.raises(mod.ColumnarRoleGenerationError):
        mod.validate_columnar_role_generation(source(), altered)


@pytest.mark.parametrize(
    "field,value",
    [("requests", 0), ("requests", 2), ("input_tokens", 19971), ("output_tokens", 1801)],
)
def test_receipt_dto_usage_limits_apply_independently_of_runtime(field, value):
    mod = api()
    raw = run().model_dump(mode="json")
    raw["usage"][field] = value
    with pytest.raises(ValueError):
        mod.ColumnarRoleGeneration.model_validate_json(json.dumps(raw), strict=True)


def test_actual_receipt_scalar_subclasses_rejected_before_dump():
    mod = api()
    got = run()

    class Derived(str):
        pass

    bad = got.model_copy(update={"profile": Derived(got.profile)})
    with pytest.raises(mod.ColumnarRoleGenerationError):
        mod.validate_columnar_role_generation(source(), bad)


def test_agent_runtime_keeps_identity_zero_retries_and_single_request_limits(monkeypatch):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    original = runtime.Agent
    constructor = []
    dispatch = []

    class ObservedAgent:
        def __init__(self, *args, **kwargs):
            constructor.append(kwargs)
            self.inner = original(*args, **kwargs)

        def run_sync(self, *args, **kwargs):
            dispatch.append(kwargs)
            return self.inner.run_sync(*args, **kwargs)

    monkeypatch.setattr(runtime, "Agent", ObservedAgent)
    assert run().usage.requests == 1
    assert len(constructor) == len(dispatch) == 1
    assert constructor[0]["name"] == "issuedigest_columnar_role_generation_v1"
    assert constructor[0]["retries"] == dispatch[0]["retries"] == 0
    assert constructor[0]["instructions"] == mod.COLUMNAR_ROLE_INSTRUCTIONS
    tool = constructor[0]["output_type"][0]
    assert tool.name == "fill_columnar_roles_v1" and tool.strict is True
    limits = dispatch[0]["usage_limits"]
    assert (limits.request_limit, limits.output_tokens_limit, limits.total_tokens_limit) == (
        1,
        1800,
        20000,
    )


@pytest.mark.parametrize("kind", ["thinking", "file", "builtin_call", "builtin_return"])
def test_original_response_permits_only_optional_thinking_beside_single_tool(kind):
    from pydantic_ai.messages import (
        BinaryContent,
        FilePart,
        NativeToolCallPart,
        NativeToolReturnPart,
        ThinkingPart,
    )

    mod = api()
    extra = {
        "thinking": ThinkingPart("private synthetic reasoning"),
        "file": FilePart(BinaryContent(b"synthetic", media_type="application/pdf")),
        "builtin_call": NativeToolCallPart("web_search", "{}"),
        "builtin_return": NativeToolReturnPart("web_search", "synthetic"),
    }[kind]
    calls = []

    def respond(messages, info):
        calls.append(info)
        return ModelResponse(
            parts=[extra, ToolCallPart("fill_columnar_roles_v1", json.dumps(packet()))],
            usage=RequestUsage(input_tokens=100, output_tokens=30),
        )

    model = FunctionModel(respond)
    framer = mod.create_columnar_role_framer(model)
    if kind == "thinking":
        assert mod.run_columnar_role_framer(framer, source()).usage.requests == 1
    else:
        with pytest.raises(mod.ColumnarRoleGenerationError) as caught:
            mod.run_columnar_role_framer(framer, source())
        assert caught.value.may_have_started is True
        assert caught.value.known_usage.model_dump() == dict(
            input_tokens=100, output_tokens=30, requests=1
        )
    assert len(calls) == 1
