"""Synthetic lossless compact source packets and bounded generation boundaries."""

import importlib
import importlib.util
import json
from hashlib import sha256

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document
from test_shared_measurement_context_v2 import example, packet
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


def sdk():
    name = "issuedigest_agents.compact_shared_context"
    assert importlib.util.find_spec(name) is not None, "Missing compact generation SDK"
    return importlib.import_module(name)


def response(data, *, inputs=100, outputs=30, error=None, text=False):
    calls = []

    def respond(messages, info):
        calls.append((messages, info))
        if error:
            raise error
        return ModelResponse(
            parts=[TextPart("free text")]
            if text
            else [ToolCallPart("fill_compact_shared_context_v1", json.dumps(data))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src=None, data=None, **options):
    api = sdk()
    model, calls = response(packet() if data is None else data, **options)
    result = api.run_compact_shared_context_framer(
        api.create_compact_shared_context_framer(model), src or document("항목 37여 명 내외.")
    )
    assert len(calls) == 1
    return result


def test_source_packet_preserves_all_quotes_sentences_and_complete_v2_quantities():
    api = sdk()
    quotes = ("🧪 e\u0301 설명.\n\n 약\t37여 명 내외. \t", "학교 83개교와 61~79명 내외.")
    src = document(*quotes)
    payload = json.loads(api.compact_shared_context_prompt(src))
    assert set(payload) == {
        "profile",
        "quotes",
        "candidates",
        "eligible_status_sentence_ids",
        "context_id_slots",
        "reporting_event_id_slots",
    }
    assert payload["profile"] == "compact-shared-context-v1"
    assert payload["quotes"][0] == {
        "quote_id": "q1",
        "sentences": [
            {"id": "s1", "text": "🧪 e\u0301 설명."},
            {"id": "s2", "text": "\n"},
            {"id": "s3", "text": "\n"},
            {"id": "s4", "text": " 약\t37여 명 내외."},
            {"id": "s5", "text": " \t"},
        ],
    }
    assert ["".join(s["text"] for s in q["sentences"]) for q in payload["quotes"]] == list(quotes)
    assert [q["quote_id"] for q in payload["quotes"]] == ["q1", "q2"]
    assert payload["candidates"] == [
        dict(
            id="n1",
            quote_id="q1",
            sentence_ids=["s4"],
            lexical_kind="number",
            expression="약\t37여 명 내외",
            atoms=[dict(number="37", unit="명")],
            separator=None,
            qualifiers=["약", "여", "내외"],
        ),
        dict(
            id="n2",
            quote_id="q2",
            sentence_ids=["s6"],
            lexical_kind="number",
            expression="83개교",
            atoms=[dict(number="83", unit="개교")],
            separator=None,
            qualifiers=[],
        ),
        dict(
            id="n3",
            quote_id="q2",
            sentence_ids=["s6"],
            lexical_kind="number",
            expression="61~79명 내외",
            atoms=[dict(number="61", unit=None), dict(number="79", unit="명")],
            separator="~",
            qualifiers=["내외"],
        ),
    ]
    prompt = api.compact_shared_context_prompt(src)
    for private_id in [
        str(src[0]),
        str(src[1].document.workspace_id),
        *[str(c.citation_id) for c in src[1].citations],
    ]:
        assert private_id not in prompt


def test_generation_reconstructs_v2_frame_receipts_and_rejects_other_profiles():
    api = sdk()
    src, data = example()
    result = run(src, data)
    assert (result.profile, result.status) == ("compact-shared-context-v1", "unreviewed")
    assert result.frame.profile == "shared-measurement-context-v2"
    assert result.frame.facts[0].purpose.span.text == "지원 목적으로"
    assert [c.expression.text for c in result.frame.candidate_index.candidates] == [
        "약\t37여 명 내외",
        "61~79명 내외",
        "83개교",
    ]
    assert (
        result.prompt_sha256 == sha256(api.compact_shared_context_prompt(src).encode()).hexdigest()
    )
    assert (
        result.instructions_sha256
        == sha256(api.COMPACT_SHARED_CONTEXT_INSTRUCTIONS.encode()).hexdigest()
    )
    assert result.usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    assert api.validate_compact_shared_context_generation(src, result) == result
    assert (
        api.validate_compact_shared_context_generation(src, json.loads(result.model_dump_json()))
        == result
    )
    old = importlib.import_module("issuedigest_agents.shared_context_generation_v2")
    with pytest.raises(old.SharedContextGenerationError):
        old.validate_shared_context_generation_v2(src, result)
    with pytest.raises(api.CompactSharedContextError):
        api.validate_compact_shared_context_generation(
            src,
            old.SharedContextGenerationV2(
                frame=result.frame,
                prompt_sha256=result.prompt_sha256,
                instructions_sha256=result.instructions_sha256,
                usage=result.usage,
            ),
        )


@pytest.mark.parametrize(
    "change", ["gap", "overlap", "text", "tail", "order", "citation", "duplicate", "unknown"]
)
def test_source_packet_rejects_lossy_or_unordered_sentence_partitions(change):
    api = sdk()
    index = api.build_numeric_candidates_v2(document("설명. 항목 37명.", "다른 항목 41명."))
    first, second, third = index.sentences
    if change in ("gap", "overlap", "text", "citation"):
        fields = {
            "gap": dict(start=1, text=first.span.text[1:]),
            "overlap": dict(start=0),
            "text": dict(text="위조."),
            "citation": dict(citation_id=third.span.citation_id),
        }[change]
        target = second if change == "overlap" else first
        forged = target.model_copy(update={"span": target.span.model_copy(update=fields)})
        sentences = (first, forged, third) if change == "overlap" else (forged, second, third)
    elif change == "tail":
        sentences = (first, third)
    elif change == "order":
        sentences = (third, first, second)
    elif change == "duplicate":
        sentences = (first, second.model_copy(update={"sentence_id": first.sentence_id}), third)
    else:
        sentences = (
            first,
            second,
            third.model_copy(
                update={"span": third.span.model_copy(update={"citation_id": "unknown"})}
            ),
        )
    with pytest.raises(ValueError):
        api._source_packet(index.model_copy(update={"sentences": sentences}))


@pytest.mark.parametrize(
    "change",
    [
        "profile",
        "prompt",
        "instructions",
        "requests",
        "overflow",
        "missing",
        "extra",
        "source",
        "slot",
        "omitted_candidate",
    ],
)
def test_stored_reconstruction_rejects_profile_receipt_catalog_and_source_drift(change):
    api = sdk()
    src = document("항목 37명, 학교 83개교.")
    raw = json.loads(run(src).model_dump_json())
    if change == "profile":
        raw["profile"] = "shared-context-generation-v2"
    elif change in ("prompt", "instructions"):
        raw[f"{change}_sha256"] = "0" * 64
    elif change == "requests":
        raw["usage"]["requests"] = 2
    elif change == "overflow":
        raw["usage"]["output_tokens"] = 2501
    elif change == "missing":
        raw.pop("usage")
    elif change == "extra":
        raw["certified"] = True
    elif change == "source":
        src = document("항목 38명, 학교 83개교.")
    elif change == "omitted_candidate":
        raw["frame"]["candidate_index"]["candidates"].pop()
    else:
        frame_api = importlib.import_module("issuedigest_agents.shared_measurement_context_v2")
        data = packet()
        data["contexts"][0]["context_id"] = data["bindings"][0]["context_id"] = "c13"
        raw["frame"] = json.loads(
            frame_api.build_shared_measurement_frame_v2(src, data).model_dump_json()
        )
    with pytest.raises(api.CompactSharedContextError) as caught:
        api.validate_compact_shared_context_generation(src, raw)
    assert caught.value.known_usage is None
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "node",
    [
        "source_list",
        "source_dict",
        "source_subclass",
        "frame_dict",
        "usage_dict",
        "facts_list",
        "input_dict",
        "anchor_dict",
        "nested_subclass",
        "generation_subclass",
    ],
)
def test_actual_models_and_tuples_rejected_before_serialization(node):
    from pydantic import Field, create_model

    api = sdk()
    src, data = example()
    result = run(src, data)
    if node == "source_list":
        src = list(src)
    elif node == "source_dict":
        src = (
            src[0],
            src[1].model_copy(update={"representation": src[1].representation.model_dump()}),
            src[2],
        )
    elif node == "source_subclass":
        extra = create_model(
            "ExtraBundle",
            __base__=type(src[1]),
            secret=(str, Field(default="hidden", exclude=True)),
        )
        src = (src[0], extra.model_validate(src[1].model_dump()), src[2])
    elif node == "frame_dict":
        result = result.model_copy(update={"frame": result.frame.model_dump()})
    elif node == "usage_dict":
        result = result.model_copy(update={"usage": result.usage.model_dump()})
    elif node == "generation_subclass":
        extra = create_model(
            "ExtraGeneration",
            __base__=type(result),
            secret=(str, Field(default="hidden", exclude=True)),
        )
        result = extra.model_validate(result.model_dump())
    else:
        frame = result.frame
        if node == "facts_list":
            frame = frame.model_copy(update={"facts": list(frame.facts)})
        elif node == "input_dict":
            frame = frame.model_copy(update={"input": frame.input.model_dump()})
        else:
            fact = frame.facts[0]
            if node == "anchor_dict":
                fact = fact.model_copy(update={"purpose": fact.purpose.model_dump()})
            else:
                extra = create_model(
                    "ExtraFact",
                    __base__=type(fact),
                    secret=(str, Field(default="hidden", exclude=True)),
                )
                fact = extra.model_validate(fact.model_dump())
            frame = frame.model_copy(update={"facts": (fact, frame.facts[1])})
        result = result.model_copy(update={"frame": frame})
    with pytest.raises(api.CompactSharedContextError):
        api.validate_compact_shared_context_generation(src, result)
    if node.startswith("source"):
        model, calls = response(data)
        with pytest.raises(api.CompactSharedContextError):
            api.run_compact_shared_context_framer(
                api.create_compact_shared_context_framer(model), src
            )
        assert calls == []


@pytest.mark.parametrize("sizes", [(111, 999), (999, 111)])
def test_utf8_actual_schema_envelope_boundary_is_inclusive_and_overflow_sends_zero(
    monkeypatch, sizes
):
    api = sdk()
    src = document("🧪 항목 37명.")
    result = run(src)
    monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: sizes)
    prompt, tools = api._preflight(src)
    limit = (
        len(prompt.encode())
        + len(api.COMPACT_SHARED_CONTEXT_INSTRUCTIONS.encode())
        + max(sizes)
        + 2048
        + 2500
    )
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit)
    assert api.compact_shared_context_prompt(src) == prompt
    assert api.validate_compact_shared_context_generation(src, result) == result
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit - 1)
    model, calls = response(packet())
    with pytest.raises(api.CompactSharedContextError):
        api.run_compact_shared_context_framer(api.create_compact_shared_context_framer(model), src)
    with pytest.raises(api.CompactSharedContextError):
        api.validate_compact_shared_context_generation(src, result)
    assert calls == []


@pytest.mark.parametrize(
    "data,options,known",
    [
        (None, {"text": True}, True),
        (None, {"error": RuntimeError("private")}, False),
        (None, {"inputs": 20001}, False),
        (None, {"outputs": 2501}, False),
        (dict(contexts=[], events=[], bindings=[], relations=[], extra=True), {}, True),
        (dict(contexts=[], events=[], bindings=[]), {}, True),
    ],
)
def test_failed_runtime_never_retries_and_preserves_nullable_observed_usage(data, options, known):
    api = sdk()
    model, calls = response(packet() if data is None else data, **options)
    with pytest.raises(api.CompactSharedContextError) as caught:
        api.run_compact_shared_context_framer(
            api.create_compact_shared_context_framer(model), document("항목 37명.")
        )
    assert len(calls) == 1
    assert (caught.value.known_usage is not None) == known
    assert str(caught.value) == "Compact shared context generation failed"
    assert caught.value.__cause__ is None


@pytest.mark.parametrize("inputs,outputs", [(17500, 2500), (20000, 0)])
def test_runtime_usage_accepts_inclusive_limits(inputs, outputs):
    assert run(inputs=inputs, outputs=outputs).usage.model_dump() == dict(
        input_tokens=inputs, output_tokens=outputs, requests=1
    )


@pytest.mark.parametrize("text", ["수치 없음.", "항목 37명 " + "가" * 6000])
def test_empty_and_over_budget_inputs_send_zero_without_truncation(text):
    api = sdk()
    model, calls = response(packet())
    with pytest.raises(api.CompactSharedContextError):
        api.run_compact_shared_context_framer(
            api.create_compact_shared_context_framer(model), document(text)
        )
    assert calls == []


@pytest.mark.parametrize("node", ["list", "dict", "canonical_anchor", "subclass"])
def test_actual_dynamic_output_nodes_cannot_be_narrowed_into_valid_input(monkeypatch, node):
    from types import SimpleNamespace

    from pydantic import Field, create_model

    api = sdk()
    original = api._runtime.Agent.run_sync

    def forged(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        output = result.output
        row = output.contexts[0]
        if node == "list":
            output = output.model_copy(update={"bindings": list(output.bindings)})
        elif node == "dict":
            output = output.model_copy(update={"contexts": (row.model_dump(),)})
        else:
            anchor = row.measured_variable
            if node == "canonical_anchor":
                anchor = (
                    type(anchor)
                    .__bases__[0]
                    .model_validate_json(anchor.model_dump_json(), strict=True)
                )
            else:
                extra = create_model(
                    "ExtraAnchor",
                    __base__=type(anchor),
                    secret=(str, Field(default="hidden", exclude=True)),
                )
                anchor = extra.model_validate(anchor.model_dump())
            output = output.model_copy(
                update={"contexts": (row.model_copy(update={"measured_variable": anchor}),)}
            )
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api._runtime.Agent, "run_sync", forged)
    src, data = example()
    with pytest.raises(api.CompactSharedContextError) as caught:
        run(src, data)
    assert caught.value.known_usage.input_tokens == 100


def test_borrowed_runtime_limits_identity_lifecycle_and_frozen_requests(monkeypatch):
    from types import SimpleNamespace

    api = sdk()
    old_names = [
        "shared_context_generation",
        "shared_context_generation_v2",
        "role_guided_shared_context",
    ]
    old = [importlib.import_module(f"issuedigest_agents.{name}") for name in old_names]
    src = document("학교 83개교, 이용자 37여 명 내외.")
    before = [
        (mod._preflight(src)[0], mod._preflight(src)[1][0].output.model_json_schema())
        for mod in old
    ]
    original_init, original_run = api._runtime.Agent.__init__, api._runtime.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_compact_shared_context_v1"
        assert kwargs["instructions"] == api.COMPACT_SHARED_CONTEXT_INSTRUCTIONS
        assert kwargs["retries"] == 0
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
    handle = api.create_compact_shared_context_framer(model)
    assert calls == []
    result = api.run_compact_shared_context_framer(handle, src)
    assert result.frame.candidate_index.candidates[0].expression.text == "83개교"
    after = [
        (mod._preflight(src)[0], mod._preflight(src)[1][0].output.model_json_schema())
        for mod in old
    ]
    assert after == before
    assert api.COMPACT_SHARED_CONTEXT_INSTRUCTIONS.startswith(
        old[1].SHARED_CONTEXT_INSTRUCTIONS_V2.replace(
            "fill_shared_context_v2", "fill_compact_shared_context_v1"
        )
    )
    with pytest.raises(TypeError):
        api.create_compact_shared_context_framer()
    with pytest.raises(api.CompactSharedContextError):
        api.create_compact_shared_context_framer(None)
    with pytest.raises(api.CompactSharedContextError):
        api.run_compact_shared_context_framer(SimpleNamespace(model=model), src)


def test_responses_wire_uses_compact_source_and_strict_current_schema(sync_model_loop):
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
                        name="fill_compact_shared_context_v1",
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
        result = api.run_compact_shared_context_framer(
            api.create_compact_shared_context_framer(model), src
        )
        assert result.frame.facts[0].purpose.span.text == "지원 목적으로"
        assert len(requests) == 1
        body = json.loads(requests[0].content)
        assert (body["store"], body["max_output_tokens"], body["temperature"]) == (
            False,
            2500,
            0.25,
        )
        assert len(body["tools"]) == 1
        tool = body["tools"][0]
        assert tool["strict"] is True and tool["name"] == "fill_compact_shared_context_v1"
        assert tool["parameters"]["required"] == ["contexts", "events", "bindings", "relations"]
        assert body["input"][0] == dict(role="user", content=api.compact_shared_context_prompt(src))
        assert not client.is_closed
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


def test_cold_import_prompt_and_validation_never_allocate_io_or_clients():
    import os
    import subprocess
    import sys

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
api = importlib.import_module("issuedigest_agents.compact_shared_context")
api.create_compact_shared_context_framer(model)
prompt = api.compact_shared_context_prompt(src)
frame_api = importlib.import_module("issuedigest_agents.shared_measurement_context_v2")
result = api.CompactSharedContextGeneration(
    frame=frame_api.build_shared_measurement_frame_v2(
        src, dict(contexts=[], events=[], bindings=[], relations=[])),
    prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.COMPACT_SHARED_CONTEXT_INSTRUCTIONS.encode()).hexdigest(),
    usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1),
)
assert api.validate_compact_shared_context_generation(src, result) == result
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("marker", ["profile", "status"])
def test_stored_compact_rejects_omitted_generation_markers_before_defaults(marker):
    api = sdk()
    src = document("동부 이용자 37명.")
    result = run(src)
    raw = json.loads(result.model_dump_json())
    assert api.validate_compact_shared_context_generation(src, result) == result
    assert api.validate_compact_shared_context_generation(src, raw) == result
    raw.pop(marker)
    with pytest.raises(api.CompactSharedContextError):
        api.validate_compact_shared_context_generation(src, raw)
