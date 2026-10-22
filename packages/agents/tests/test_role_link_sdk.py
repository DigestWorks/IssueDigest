"""Synthetic SDK receipts and bounded mock requests; no semantic acceptance claims."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import BaseModel, create_model
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_role_link_catalog import original
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


def api():
    name = "issuedigest_agents.role_link_sdk"
    assert importlib.util.find_spec(name) is not None, "Missing bounded role link SDK"
    return importlib.import_module(name)


def response(data=None, *, inputs=100, outputs=30, completion=None, kind="tool", error=None):
    calls = []

    def respond(messages, info):
        calls.append((messages, info))
        if error is not None:
            raise error
        parts = [
            ToolCallPart(
                "review_role_links_v1",
                json.dumps(dict(rows=["SO"], incomplete=False) if data is None else data),
            )
        ]
        if kind == "text":
            parts = [TextPart("private unstructured")]
        elif kind == "multiple":
            parts = parts * 2
        return ModelResponse(
            parts=parts,
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
            **(completion or {}),
        )

    return FunctionModel(respond), calls


def run(src=None, gen=None, **options):
    mod = api()
    if src is None:
        src, default = original("현재 3명.", numbers=("n1",))
        gen = default if gen is None else gen
    model, calls = response(**options)
    result = mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    assert len(calls) == int(result.report.coverage.candidate_pairs > 0)
    return result


def usage(gen, *, inputs=100, outputs=30):
    return gen.model_copy(
        update={
            "usage": gen.usage.model_copy(update={"input_tokens": inputs, "output_tokens": outputs})
        }
    )


def test_success_full_prompt_and_independent_roundtrip_receipts():
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    before = deepcopy(src), gen.model_dump(mode="json")
    result = run(src, gen)
    assert result.profile == "role-link-generation-v1"
    assert result.input_format == "named-columns-matrix-v1"
    assert result.report.catalog.generation == gen
    assert result.report.input.model_dump(mode="json") == dict(rows=["SO"], incomplete=False)
    assert result.report.decisions[0].roles == ("measurement_scope", "operator")
    assert result.combined_usage.model_dump() == dict(
        input_tokens=200, output_tokens=60, requests=2
    )
    prompt = mod.role_link_prompt(src, gen)
    packet = json.loads(prompt)
    assert packet["role_order"] == "STOREIBP"
    assert packet["hint_table"]["rows"] == [["m1", "q1", "s1", "현재", None]]
    assert packet["domains"] == [dict(quote_id="q1", numbers=["n1"], hints=["m1"])]
    codec = importlib.import_module("issuedigest_agents.role_table_packet")
    restored = codec.decode_role_table_packet(src, gen, packet["source_packet"])
    assert restored["proposal"] == gen.frame.input.model_dump(mode="json")
    assert result.prompt_sha256 == sha256(prompt.encode()).hexdigest()
    assert result.instructions_sha256 == sha256(mod.ROLE_LINK_INSTRUCTIONS.encode()).hexdigest()
    assert mod.validate_role_link_generation(src, result) == result
    assert mod.validate_role_link_generation(src, result.model_dump(mode="json")) == result
    assert (src, gen.model_dump(mode="json")) == before
    _, tools, remaining, cap = mod._preflight(src, gen)
    assert remaining == 19870 and cap == 1100
    assert len(tools) == 1 and tools[0].name == "review_role_links_v1" and tools[0].strict
    schema = tools[0].output.model_json_schema()
    assert set(schema["properties"]) == set(schema["required"]) == {"rows", "incomplete"}
    assert schema["properties"]["rows"]["minItems"] == 1
    assert schema["properties"]["rows"]["maxItems"] == 1
    assert schema["properties"]["rows"]["items"] == {"type": "string"}


@pytest.mark.parametrize(
    "quotes,numbers,rows,status",
    [
        (("현재 3명.",), (), [""], "not_applicable"),
        (("3명.",), ("n1",), [], "candidate_inventory_empty"),
        (("현재 설명.", "3명."), ("n1",), [""], "candidate_inventory_empty"),
    ],
)
def test_zero_pairs_skip_request_even_when_output_cap_is_zero(
    monkeypatch, quotes, numbers, rows, status
):
    mod = api()
    src, gen = original(*quotes, numbers=numbers)
    monkeypatch.setattr(mod, "_remaining", lambda observed: (0, 0))
    model, calls = response(error=AssertionError("No request allowed"))
    got = mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    assert calls == [] and got.link_usage is None and got.combined_usage == gen.usage
    assert got.report.input.rows == tuple(rows) and got.report.status == status
    assert mod.validate_role_link_generation(src, got.model_dump(mode="json")) == got
    assert mod._preflight(src, gen)[1] == []
    with pytest.raises(mod.RoleLinkSDKError):
        mod.run_role_link_reviewer(object(), src, gen)


@pytest.mark.parametrize(
    "rows,incomplete,status",
    [
        (["?"], False, "candidate_review_uncertain"),
        (["_"], True, "candidate_review_incomplete"),
        (["STOREIBP"], False, "reviewed_candidates"),
    ],
)
def test_explicit_relation_uncertainty_and_incomplete_are_not_provider_failure(
    rows, incomplete, status
):
    got = run(data=dict(rows=rows, incomplete=incomplete))
    assert got.report.status == status
    assert got.link_usage.requests == 1


@pytest.mark.parametrize(
    "data",
    [
        dict(rows=[], incomplete=False),
        dict(rows=["S", "S"], incomplete=False),
        dict(rows=["OS"], incomplete=False),
        dict(rows=["SS"], incomplete=False),
        dict(rows=["S;T"], incomplete=False),
        dict(rows=["_"], incomplete=False),
        dict(rows=[1], incomplete=False),
        dict(rows=["S"], incomplete=0),
        dict(rows=["S"]),
        dict(rows=["S"], incomplete=False, extra=1),
    ],
)
def test_bad_dynamic_or_canonical_output_rejected_wholly_with_cost(data):
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    model, calls = response(data=data)
    with pytest.raises(mod.RoleLinkSDKError) as caught:
        mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    err = caught.value
    assert len(calls) == 1 and err.link_may_have_started
    assert err.generation_usage == gen.usage and err.link_usage.output_tokens == 30
    assert err.combined_usage.requests == 2 and err.__cause__ is None
    assert "현재" not in str(err)


@pytest.mark.parametrize(
    "options",
    [
        dict(completion=dict(state="incomplete")),
        dict(completion=dict(finish_reason="length")),
        dict(completion=dict(provider_details=dict(finish_reason="incomplete"))),
        dict(kind="text"),
        dict(kind="multiple"),
        dict(outputs=1101),
    ],
)
def test_provider_failure_never_repeats_and_preserves_known_usage(options):
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    model, calls = response(**options)
    with pytest.raises(mod.RoleLinkSDKError) as caught:
        mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    assert len(calls) == 1 and caught.value.link_may_have_started
    assert caught.value.link_usage is not None
    assert caught.value.combined_usage.requests == 2


@pytest.mark.parametrize("started", [False, True])
def test_unknown_request_failure_preserves_dispatch_uncertainty(monkeypatch, started):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")

    def fail(**kwargs):
        raise runtime.RoleRequestError("private detail", may_have_started=started)

    monkeypatch.setattr(mod, "_run_role_request", fail)
    src, gen = original("현재 3명.", numbers=("n1",))
    model, _ = response()
    with pytest.raises(mod.RoleLinkSDKError) as caught:
        mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    err = caught.value
    assert err.link_may_have_started is started and err.link_usage is None
    assert err.combined_usage == (None if started else gen.usage)
    assert "private" not in str(err) and err.__cause__ is None


@pytest.mark.parametrize("stage", ["_build_output", "validate_role_link_generation"])
@pytest.mark.parametrize("kind", ["plain", "request", "sdk"])
def test_late_failures_never_overwrite_observed_cost(monkeypatch, stage, kind):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    error = {"plain": ValueError, "request": runtime.RoleRequestError, "sdk": mod.RoleLinkSDKError}[
        kind
    ]

    def fail(*args, **kwargs):
        raise error("private late detail")

    monkeypatch.setattr(mod, stage, fail)
    src, gen = original("현재 3명.", numbers=("n1",))
    gen = usage(gen, outputs=1800)
    model, calls = response(outputs=700)
    with pytest.raises(mod.RoleLinkSDKError) as caught:
        mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    err = caught.value
    assert len(calls) == 1 and err.link_may_have_started
    assert err.link_usage.model_dump() == dict(input_tokens=100, output_tokens=700, requests=1)
    assert err.combined_usage.output_tokens == 2500


def test_budget_full_envelope_inclusive_boundary_and_one_over():
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    prompt, tools, _, cap = mod._preflight(src, gen)
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    envelope = runtime._request_envelope(prompt, tools, mod.ROLE_LINK_INSTRUCTIONS, cap)
    boundary = usage(gen, inputs=20000 - envelope - 30)
    assert mod._preflight(src, boundary)[2] == envelope
    assert run(src, boundary, inputs=envelope - 1100, outputs=1100).combined_usage.requests == 2
    model, calls = response()
    with pytest.raises(mod.RoleLinkSDKError) as caught:
        mod.run_role_link_reviewer(
            mod.create_role_link_reviewer(model),
            src,
            usage(boundary, inputs=boundary.usage.input_tokens + 1),
        )
    assert calls == [] and not caught.value.link_may_have_started
    assert caught.value.link_usage is None


@pytest.mark.parametrize("outputs,cap", [(1610, 890), (1800, 700), (2500, 0)])
def test_remaining_output_cap_never_increases(outputs, cap):
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    gen = usage(gen, outputs=outputs)
    model, calls = response(outputs=cap)
    if cap:
        assert mod._preflight(src, gen)[3] == cap
        assert run(src, gen, outputs=cap).combined_usage.output_tokens == 2500
    else:
        with pytest.raises(mod.RoleLinkSDKError):
            mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
        assert calls == []


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "input_format",
        "report",
        "prompt_sha256",
        "instructions_sha256",
        "link_usage",
        "combined_usage",
    ],
)
def test_every_receipt_field_required_before_dump(actual, field):
    mod = api()
    got = run()
    altered = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    del (altered.__dict__ if actual else altered)[field]
    src, _ = original("현재 3명.", numbers=("n1",))
    with pytest.raises(mod.RoleLinkSDKError):
        mod.validate_role_link_generation(src, altered)


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "mutation",
    [
        "profile",
        "format",
        "prompt",
        "instructions",
        "input",
        "span",
        "coverage",
        "domain",
        "encoding",
        "usage",
        "requests",
        "nested_missing",
        "scalar",
        "source",
    ],
)
def test_current_source_and_every_report_receipt_drift_rejects(actual, mutation):
    from test_role_table_packet import StringSubclass

    mod = api()
    got = run()
    bad = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    src, _ = original("현재 3명.", numbers=("n1",))
    changes = {
        "profile": (("profile",), "role-table-audit-v1"),
        "format": (("input_format",), "named-columns-v1"),
        "prompt": (("prompt_sha256",), "0" * 64),
        "instructions": (("instructions_sha256",), "0" * 64),
        "input": (("report", "input", "rows"), ("-",) if actual else ["-"]),
        "span": (("report", "decisions", 0, "hint", "start"), 1),
        "coverage": (("report", "coverage", "unreviewed_pairs"), 1),
        "domain": (("report", "catalog", "domains", 0, "numbers"), () if actual else []),
        "encoding": (("report", "role_order"), "STORIEBP"),
        "usage": (("combined_usage", "output_tokens"), 61),
        "requests": (("link_usage", "requests"), 2),
        "scalar": (("profile",), StringSubclass("role-link-generation-v1")),
    }

    def fields(node):
        return node.__dict__ if isinstance(node, BaseModel) else node

    if mutation == "source":
        src[1].representation.__dict__["text"] += "changed"
    elif mutation == "nested_missing":
        node = bad
        for key in ("report", "catalog", "generation", "frame", "input", "contexts", 0):
            node = fields(node)[key]
        context = fields(node)
        del context["baseline"]
    else:
        path, value = changes[mutation]
        node = bad
        for key in path[:-1]:
            node = fields(node)[key]
        fields(node)[path[-1]] = value
    with pytest.raises(mod.RoleLinkSDKError):
        mod.validate_role_link_generation(src, bad)


@pytest.mark.parametrize("mutation", ["missing", "scalar", "tuple", "bool", "subclass"])
def test_dynamic_actual_identity_types_and_fields_checked_before_serialization(mutation):
    from test_role_table_packet import StringSubclass

    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    cls = mod._preflight(src, gen)[1][0].output
    out = cls.model_validate_json('{"rows":["S"],"incomplete":false}', strict=True)
    if mutation == "missing":
        del out.__dict__["incomplete"]
    elif mutation == "scalar":
        out.__dict__["rows"] = (StringSubclass("S"),)
    elif mutation == "tuple":
        out.__dict__["rows"] = ["S"]
    elif mutation == "bool":
        out.__dict__["incomplete"] = 0
    else:
        out = create_model("OutputSubclass", __base__=cls)(rows=("S",), incomplete=False)
    with pytest.raises(ValueError):
        mod._build_output(src, gen, out, cls)


def test_wrapper_lazy_borrowed_and_runtime_settings():
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    model, calls = response()
    reviewer = mod.create_role_link_reviewer(model)
    assert reviewer.model is model and calls == []
    with pytest.raises(FrozenInstanceError):
        reviewer.model = object()
    with pytest.raises(mod.RoleLinkSDKError):
        mod.create_role_link_reviewer(object())
    mod.run_role_link_reviewer(reviewer, src, gen)
    messages, info = calls[0]
    assert info.model_settings["openai_store"] is False
    assert info.model_settings["timeout"] == 30 and info.model_settings["max_tokens"] == 1100
    assert messages[0].instructions == mod.ROLE_LINK_INSTRUCTIONS


def test_repeated_hints_multiquote_empty_columns_and_order_are_preserved():
    src, gen = original("현재현재 설명.", "올해 3명.", "4명.", numbers=("n2", "n1"))
    got = run(src, gen, data=dict(rows=["", "", "?"], incomplete=False))
    assert got.report.coverage.candidate_pairs == 1
    assert got.report.input.rows == ("", "", "?")
    assert got.report.decisions[0].number == "n1"
    assert got.report.catalog.domains[2].numbers == ("n2",)


def test_maximum_288_pairs_via_low_cost_mock_runtime_keeps_real_preflight(monkeypatch):
    mod = api()
    text = (
        " ".join(f"'item{chr(65 + i)}'" for i in range(24))
        + " "
        + " ".join(f"{i}명." for i in range(1, 13))
    )
    src, gen = original(text, numbers=tuple(f"n{i}" for i in range(1, 13)))
    rows = [";".join(["?"] * 12)] * 24
    calls = []

    def request(**kwargs):
        calls.append(kwargs)
        assert kwargs["identity"] == "issuedigest_role_links_v1"
        assert kwargs["output_limit"] == 1100
        assert kwargs["total_limit"] == 19870
        tool = kwargs["tools"][0]
        data = dict(rows=rows, incomplete=False)
        kwargs["model"].responses.append(
            ModelResponse(parts=[ToolCallPart("review_role_links_v1", json.dumps(data))])
        )
        known = importlib.import_module("issuedigest_agents.numeric_evidence").KnownUsage
        return tool.output.model_validate_json(json.dumps(data), strict=True), known(
            input_tokens=100, output_tokens=30, requests=1
        )

    # Replace only I/O; canonical preflight/envelope stays active.
    monkeypatch.setattr(mod, "_run_role_request", request)
    model, _ = response(error=AssertionError("No provider call"))
    got = mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
    assert len(calls) == 1
    assert got.report.coverage.candidate_pairs == got.report.coverage.uncertain_pairs == 288
    assert got.report.decisions[-1].hint_id == "m24"
    assert got.report.decisions[-1].number == "n12"
    assert mod.validate_role_link_generation(src, got.model_dump(mode="json")) == got


def test_instruction_literal_and_import_perform_no_client_or_network_work():
    mod = api()
    with open("docs/changes/role-link-sdk.md") as file:
        design = file.read()
    literal = design.split("Call review_role_links_v1 once.", 1)[1].split("```", 1)[0].rstrip()
    assert mod.ROLE_LINK_INSTRUCTIONS == "Call review_role_links_v1 once." + literal
    code = """
import socket
import openai

def forbidden(*args, **kwargs):
    raise AssertionError('unexpected client or network')
socket.socket.connect = forbidden
openai.OpenAI.__init__ = forbidden
openai.AsyncOpenAI.__init__ = forbidden
import issuedigest_agents.role_link_sdk
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize("mutation", ["bool_count", "missing", "container", "subclass"])
def test_stage_usage_originals_reject_coercion_and_default_restoration(actual, mutation):
    mod = api()
    got = run()
    bad = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    fields = bad.__dict__ if actual else bad
    stage = fields["link_usage"]
    fields_stage = stage.__dict__ if actual else stage
    if mutation == "bool_count":
        fields_stage["requests"] = True
    elif mutation == "missing":
        del fields_stage["requests"]
    elif mutation == "container":
        fields["link_usage"] = stage.model_dump() if actual else tuple(stage.items())
    else:
        from test_role_table_packet import StringSubclass

        fields_stage["output_tokens"] = StringSubclass("30")
    src, _ = original("현재 3명.", numbers=("n1",))
    with pytest.raises(mod.RoleLinkSDKError):
        mod.validate_role_link_generation(src, bad)


@pytest.mark.parametrize("metadata", ["encrypted", "summary", "multiple"])
@pytest.mark.parametrize("position", ["before", "after", "around"])
def test_thinking_metadata_does_not_count_as_an_output_tool(metadata, position):
    from pydantic_ai.messages import ThinkingPart

    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    thoughts = [
        ThinkingPart(
            content="" if metadata == "encrypted" else "synthetic summary",
            signature="synthetic encrypted metadata",
        )
    ]
    if metadata == "multiple":
        thoughts.append(ThinkingPart(content="second synthetic summary"))
    tool = ToolCallPart("review_role_links_v1", '{"rows":["SO"],"incomplete":false}')
    parts = thoughts + [tool] if position == "before" else [tool] + thoughts
    if position == "around":
        parts = [thoughts[0], tool, *thoughts]
    calls = []

    def respond(messages, info):
        calls.append(messages)
        return ModelResponse(parts=parts, usage=RequestUsage(input_tokens=111, output_tokens=22))

    got = mod.run_role_link_reviewer(
        mod.create_role_link_reviewer(FunctionModel(respond)), src, gen
    )
    assert len(calls) == 1 and got.report.input.rows == ("SO",)
    assert got.link_usage.model_dump() == dict(input_tokens=111, output_tokens=22, requests=1)
    assert mod.validate_role_link_generation(src, got.model_dump(mode="json")) == got


@pytest.mark.parametrize("extra", ["text", "duplicate", "wrong_tool", "native_tool"])
def test_thinking_metadata_does_not_hide_unexpected_output_parts(extra):
    from pydantic_ai.messages import NativeToolCallPart, ThinkingPart

    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    tool = ToolCallPart("review_role_links_v1", '{"rows":["SO"],"incomplete":false}')
    unexpected = {
        "text": TextPart("unexpected output"),
        "duplicate": tool,
        "wrong_tool": ToolCallPart("unrequested_tool", "{}"),
        "native_tool": NativeToolCallPart("unexpected_native_tool", {}),
    }[extra]
    calls = []

    def respond(messages, info):
        calls.append(messages)
        return ModelResponse(
            parts=[ThinkingPart(content="synthetic summary"), tool, unexpected],
            usage=RequestUsage(input_tokens=111, output_tokens=22),
        )

    with pytest.raises(mod.RoleLinkSDKError) as caught:
        mod.run_role_link_reviewer(mod.create_role_link_reviewer(FunctionModel(respond)), src, gen)
    assert len(calls) == 1 and caught.value.link_may_have_started
    assert caught.value.link_usage.model_dump() == dict(
        input_tokens=111, output_tokens=22, requests=1
    )
    assert caught.value.combined_usage.requests == 2


@pytest.mark.parametrize("summary", [[], [{"type": "summary_text", "text": "synthetic summary"}]])
def test_openai_adapter_reasoning_metadata_and_single_tool_roundtrip(sync_model_loop, summary):
    import httpx2 as httpx
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        return httpx.Response(
            200,
            json=dict(
                id="resp_synthetic",
                object="response",
                created_at=0,
                status="completed",
                incomplete_details=None,
                model="synthetic-model",
                output=[
                    dict(
                        type="reasoning",
                        id="rs_synthetic",
                        summary=summary,
                        encrypted_content="synthetic encrypted metadata",
                    ),
                    dict(
                        type="function_call",
                        id="fc_synthetic",
                        call_id="call_synthetic",
                        name="review_role_links_v1",
                        status="completed",
                        arguments='{"rows":["SO"],"incomplete":false}',
                    ),
                ],
                usage=dict(input_tokens=111, output_tokens=22, total_tokens=133),
            ),
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider_client = AsyncOpenAI(api_key="synthetic", http_client=client, max_retries=0)
    try:
        model = OpenAIResponsesModel(
            "synthetic-model",
            provider=OpenAIProvider(openai_client=provider_client),
            settings={"openai_reasoning_effort": "low"},
        )
        got = mod.run_role_link_reviewer(mod.create_role_link_reviewer(model), src, gen)
        assert len(calls) == 1 and got.report.input.rows == ("SO",)
        assert got.link_usage.model_dump() == dict(input_tokens=111, output_tokens=22, requests=1)
        assert mod.validate_role_link_generation(src, got) == got
        assert not client.is_closed
        assert calls[0]["store"] is False and calls[0]["max_output_tokens"] == 1100
    finally:
        sync_model_loop.run_until_complete(provider_client.close())
