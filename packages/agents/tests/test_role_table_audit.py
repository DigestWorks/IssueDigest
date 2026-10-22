"""Synthetic table audits retain independent receipts, unchanged roles and observed costs."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import Field, create_model
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document
from test_role_alias_contract import anchor, packet, source
from test_semantic_role_audit_contract import audit_input, generation
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


def api():
    name = "issuedigest_agents.role_table_audit"
    assert importlib.util.find_spec(name) is not None, "Missing table audit SDK"
    return importlib.import_module(name)


def decode_prompt(src, original):
    codec = importlib.import_module("issuedigest_agents.role_table_packet")
    return codec.decode_role_table_packet(
        src, original, json.loads(api().role_table_audit_prompt(src, original))
    )


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
                    "audit_role_table_v1", json.dumps(audit_input("n1") if data is None else data)
                )
            ],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
            **(completion or {}),
        )

    return FunctionModel(respond), calls


def run(original=None, src=None, **options):
    mod = api()
    src = source() if src is None else src
    original = generation(src) if original is None else original
    model, calls = response(**options)
    result = mod.run_role_table_auditor(mod.create_role_table_auditor(model), src, original)
    assert len(calls) == 1
    return result


@pytest.mark.parametrize("profile", ["new"])
def test_full_proposal_prompt_coverage_and_own_receipts(profile):
    mod = api()
    original = generation(profile=profile)
    result = run(original)
    assert result.profile == "role-table-audit-v1" and result.report.generation == original
    assert result.combined_usage.model_dump() == dict(
        input_tokens=200, output_tokens=60, requests=2
    )
    assert mod.validate_role_table_audit_generation(source(), result) == result
    assert (
        mod.validate_role_table_audit_generation(source(), json.loads(result.model_dump_json()))
        == result
    )
    body = decode_prompt(source(), original)
    assert body["proposal"] == result.report.proposal.model_dump(mode="json")
    assert body["roles"] == list(result.report.roles)
    assert body["change_coverage"] == result.report.change_coverage
    assert (
        "".join(s["text"] for s in body["quotes"][0]["sentences"])
        == source()[1].citations[0].selector.quote
    )
    assert str(source()[0]) not in mod.role_table_audit_prompt(source(), original)
    prompt, tools, remaining, cap = mod._preflight(source(), original)
    assert remaining == 19870 and cap == 1100 and len(tools) == 1
    schema = json.dumps(tools[0].output.model_json_schema())
    assert ("change_direction" in schema) == (profile == "new")
    assert tools[0].name == "audit_role_table_v1" and tools[0].strict is True


def test_empty_selection_zero_requests_no_audit_usage():
    mod = api()
    data = dict(contexts=[], events=[], bindings=[], relations=[])
    original = generation(data=data)
    model, calls = response()
    got = mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    assert calls == [] and got.audit_usage is None and got.combined_usage == original.usage
    assert got.report.status == "not_applicable" and got.combined_usage.requests == 1
    assert (
        mod.validate_role_table_audit_generation(source(), json.loads(got.model_dump_json())) == got
    )


@pytest.mark.parametrize("outputs,accepted", [(700, True), (701, False)])
def test_new_audit_cap_observed_usage_preserved(outputs, accepted):
    mod = api()
    model, calls = response(outputs=outputs)
    original = generation(outputs=1800)
    if accepted:
        got = mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
        assert got.combined_usage.output_tokens == 2500
    else:
        with pytest.raises(mod.RoleTableAuditError) as caught:
            mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
        err = caught.value
        assert err.generation_usage == original.usage and err.audit_usage.output_tokens == outputs
        assert err.combined_usage.output_tokens == 2501 and err.audit_may_have_started
    assert len(calls) == 1


def test_actual_envelope_remaining_budget_boundary_and_observed_total(monkeypatch):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    prompt, tools, _, cap = mod._preflight(source(), generation())
    envelope = runtime._request_envelope(prompt, tools, mod.ROLE_TABLE_AUDIT_INSTRUCTIONS, cap)
    original = generation(inputs=20000 - envelope - 30)
    assert mod._preflight(source(), original)[2] == envelope
    assert (
        run(original, inputs=envelope - 1100, outputs=1100).combined_usage.input_tokens
        + run(original, inputs=envelope - 1100, outputs=1100).combined_usage.output_tokens
        == 20000
    )
    model, calls = response(inputs=envelope - 1099, outputs=1100)
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    assert caught.value.audit_usage.input_tokens == envelope - 1099 and len(calls) == 1
    original = generation(inputs=20000 - envelope - 29)
    model, calls = response()
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    assert (
        calls == [] and caught.value.audit_usage is None and not caught.value.audit_may_have_started
    )


@pytest.mark.parametrize("mode", ["unknown", "text", "wrong_catalog", "incomplete", "length"])
def test_single_failed_request_preserves_known_unknown_and_completion(mode):
    mod = api()
    options = {}
    if mode == "unknown":
        options["error"] = RuntimeError("private detail")
    elif mode == "text":
        options["text"] = True
    elif mode == "wrong_catalog":
        options["data"] = audit_input("n2")
    elif mode == "incomplete":
        options["completion"] = {"provider_details": {"finish_reason": "incomplete"}}
    else:
        options["completion"] = {"finish_reason": "length"}
    model, calls = response(**options)
    original = generation()
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    error = caught.value
    assert (
        len(calls) == 1
        and error.audit_may_have_started
        and error.generation_usage == original.usage
    )
    assert "private detail" not in str(error)
    if mode == "unknown":
        assert error.audit_usage is None and error.combined_usage is None
    else:
        assert error.audit_usage.output_tokens == 30 and error.combined_usage.requests == 2


def test_invalid_original_usage_never_trusted_and_large_source_zero_calls():
    mod = api()
    original = generation()
    model, calls = response()
    bad = original.model_copy(update={"instructions_sha256": "0" * 64})
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), bad)
    assert (
        calls == []
        and caught.value.generation_usage is None
        and caught.value.combined_usage is None
    )
    # A valid legacy generation can leave insufficient input budget for an audit.
    original = generation(inputs=18000, outputs=1800)
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    assert calls == [] and caught.value.generation_usage == original.usage


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "input_format",
        "report",
        "prompt_sha256",
        "instructions_sha256",
        "audit_usage",
        "combined_usage",
        "original_profile",
        "original_status",
        "report_coverage",
        "missing_nullable",
        "actual_report",
        "actual_usage",
    ],
)
def test_stored_generation_required_markers_receipts_and_usage(field):
    mod = api()
    got = run()
    raw = json.loads(got.model_dump_json())
    if field in ("profile", "input_format", "report"):
        raw.pop(field)
    elif field.endswith("sha256"):
        raw[field] = "0" * 64
    elif field == "audit_usage":
        raw[field]["output_tokens"] = 1101
    elif field == "combined_usage":
        raw[field]["requests"] = 1
    elif field.startswith("original_"):
        raw["report"]["generation"].pop(field.removeprefix("original_"))
    elif field == "report_coverage":
        raw["report"]["roles"].pop()
    elif field == "missing_nullable":
        raw.pop("audit_usage")
    elif field == "actual_report":
        raw = got.model_copy(update={"report": got.report.model_dump(mode="json")})
    else:
        raw = got.model_copy(update={"audit_usage": got.audit_usage.model_dump()})
    with pytest.raises(mod.RoleTableAuditError):
        mod.validate_role_table_audit_generation(source(), raw)


def test_actual_dynamic_output_nested_guards_before_dump(monkeypatch):
    mod = api()
    original = generation()
    _, tools, _, _ = mod._preflight(source(), original)
    cls = tools[0].output
    good = cls.model_validate_json(json.dumps(audit_input("n1")), strict=True)
    for bad in (
        good.model_dump(mode="json"),
        good.model_copy(update={"checks": list(good.checks)}),
    ):
        with pytest.raises(ValueError):
            mod._build_output(source(), original, bad, cls)
    extended = create_model(
        "ExtraAudit", __base__=cls, secret=(str, Field(default="hidden", exclude=True))
    )
    with pytest.raises(ValueError):
        mod._build_output(source(), original, extended.model_validate(good.model_dump()), cls)


@pytest.mark.parametrize("status", ["completed", "incomplete"])
def test_mock_http_wire_dynamic_schema_cap_no_store_borrowed_lifecycle(sync_model_loop, status):
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
                "incomplete_details": None,
                "model": "synthetic-model",
                "output": [
                    {
                        "type": "function_call",
                        "id": "fc_synthetic",
                        "call_id": "call_synthetic",
                        "name": "audit_role_table_v1",
                        "arguments": json.dumps(audit_input("n1")),
                        "status": "completed",
                    }
                ],
                "usage": {"input_tokens": 100, "output_tokens": 700, "total_tokens": 800},
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
        auditor = mod.create_role_table_auditor(model)
        if status == "completed":
            assert (
                mod.run_role_table_auditor(
                    auditor, source(), generation(outputs=1800)
                ).audit_usage.output_tokens
                == 700
            )
        else:
            with pytest.raises(mod.RoleTableAuditError) as caught:
                mod.run_role_table_auditor(auditor, source(), generation(outputs=1800))
            assert (
                caught.value.audit_usage.output_tokens == 700
                and caught.value.audit_may_have_started
            )
        assert not client.is_closed and len(requests) == 1
        wire = requests[0]
        assert (
            wire["store"] is False
            and wire["max_output_tokens"] == 700
            and wire["temperature"] == 0.25
        )
        assert wire["reasoning"]["effort"] == "low"
        assert timeouts == [dict(connect=30, read=30, write=30, pool=30)]
        assert wire["instructions"] == mod.ROLE_TABLE_AUDIT_INSTRUCTIONS
        assert len(wire["instructions"].encode("utf-8")) == 3134
        tool = wire["tools"][0]
        assert tool["name"] == "audit_role_table_v1" and tool["strict"] is True
        assert tool["parameters"]["required"] == ["checks", "issues", "incomplete"]
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


def test_cold_import_create_prompt_validation_no_io():
    code = """
import builtins,importlib,io,os,socket
import openai,pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
from test_role_alias_contract import anchor, packet, source
from test_semantic_role_audit_contract import generation,audit_input
src=source();original=generation()
def forbidden(*args,**kwargs): raise AssertionError("Unexpected I/O/client/key/request")
model=FunctionModel(forbidden)
openai.AsyncOpenAI.__init__=openai.OpenAI.__init__=forbidden
pydantic_ai.Agent.__init__=forbidden
old=type(os.environ).__getitem__
def no_env(self,key):
    if key!="PYDANTIC_DISABLE_PLUGINS": forbidden()
    return old(self,key)
type(os.environ).__getitem__=no_env
builtins.open=io.open=socket.socket=forbidden
mod=importlib.import_module("issuedigest_agents.role_table_audit")
contract=importlib.import_module("issuedigest_agents.semantic_role_audit_contract")
mod.create_role_table_auditor(model)
mod.role_table_audit_prompt(src,original)
report=contract.build_semantic_role_audit_report(src,original,audit_input("n1"))
assert contract.validate_semantic_role_audit_report(src,report)==report
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_prompt_slot_labels_losslessly_reconstruct_full_scope_catalog():
    src = document("합성국 동부 이용자 37명 증가.")
    data = packet()
    data["contexts"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("합성국"))]
    data["bindings"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("동부"))]
    original = generation(src, data)
    body = decode_prompt(src, original)
    assert body["scope_slots"] == [dict(number="n1", slots=["r1", "r2"])]
    contexts = {c["id"]: c for c in body["proposal"]["contexts"]}
    bindings = {b["number"]: b for b in body["proposal"]["bindings"]}
    restored = []
    for row in body["scope_slots"]:
        binding = bindings[row["number"]]
        scopes = contexts[binding["context"]]["scopes"] + binding["scopes"]
        restored.append(
            dict(
                number=row["number"],
                scopes=[
                    dict(slot=slot, **scope)
                    for slot, scope in zip(row["slots"], scopes, strict=True)
                ],
            )
        )
    contract = importlib.import_module("issuedigest_agents.semantic_role_audit_contract")
    report = contract.build_semantic_role_audit_report(src, original, audit_input("n1"))
    assert restored == [row.model_dump(mode="json") for row in report.scope_slots]


def test_rejected_stored_report_retains_valid_original_and_observed_stage_usage():
    mod = api()
    got = run()
    bad = got.model_dump(mode="json")
    bad["report"]["proposal_sha256"] = "0" * 64
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.validate_role_table_audit_generation(source(), bad)
    assert caught.value.generation_usage == got.report.generation.usage
    assert caught.value.audit_usage == got.audit_usage
    assert caught.value.audit_may_have_started
    assert caught.value.combined_usage == got.combined_usage


def test_final_revalidation_failure_keeps_successfully_observed_cost(monkeypatch):
    mod = api()
    original_preflight = mod._preflight
    count = 0

    def drift(src, original):
        nonlocal count
        count += 1
        prompt, tools, remaining, cap = original_preflight(src, original)
        return prompt + (" " if count > 1 else ""), tools, remaining, cap

    monkeypatch.setattr(mod, "_preflight", drift)
    original = generation(outputs=1800)
    model, calls = response(outputs=700)
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    error = caught.value
    assert len(calls) == 1 and count == 2 and error.audit_may_have_started
    assert error.generation_usage == original.usage
    assert error.audit_usage.model_dump() == dict(input_tokens=100, output_tokens=700, requests=1)
    assert error.combined_usage.model_dump() == dict(
        input_tokens=200, output_tokens=2500, requests=2
    )


@pytest.mark.parametrize(
    "generation_output,cap", [(30, 1100), (1400, 1100), (1597, 903), (1800, 700)]
)
def test_actual_generation_usage_determines_request_output_cap(generation_output, cap):
    mod = api()
    original = generation(outputs=generation_output)
    _, _, remaining, actual_cap = mod._preflight(source(), original)
    assert remaining == 20000 - 100 - generation_output and actual_cap == cap
    result = run(original, outputs=cap)
    assert result.combined_usage.output_tokens == generation_output + cap


@pytest.mark.parametrize("profile", ["new", "v2", "compact"])
def test_historical_generations_fail_before_send(profile):
    from test_role_aware_audit_contract import generation as historical_generation

    mod = api()
    model, calls = response()
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(
            mod.create_role_table_auditor(model),
            source(),
            historical_generation(profile=profile),
        )
    assert calls == [] and not caught.value.audit_may_have_started
    assert caught.value.combined_usage is None and caught.value.generation_usage is None


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "input_format",
        "report",
        "prompt_sha256",
        "instructions_sha256",
        "audit_usage",
        "combined_usage",
    ],
)
def test_all_audit_receipt_fields_required_before_dump(field, actual):
    mod = api()
    result = run()
    altered = result.model_copy(deep=True) if actual else result.model_dump(mode="json")
    del (altered.__dict__ if actual else altered)[field]
    with pytest.raises(mod.RoleTableAuditError):
        mod.validate_role_table_audit_generation(source(), altered)


@pytest.mark.parametrize(
    "case",
    [
        "composition_in_entity",
        "material_entity_loss",
        "ambiguous_materiality",
        "purpose_does_not_restrict_population",
        "population_restriction",
    ],
)
def test_supplied_synthetic_diagnoses_cross_sdk_with_unchanged_proposal(case):
    from test_semantic_role_audit_contract import semantic_case

    src, proposal, raw, expected = semantic_case(case)
    original = generation(src, proposal)
    result = run(original, src, data=raw)
    assert result.report.status == expected
    assert result.report.input.model_dump(mode="json") == raw
    assert result.report.proposal.model_dump(mode="json") == proposal
    assert result.report.generation == original


def test_postresponse_runtime_base_failure_does_not_overwrite_observed_usage(monkeypatch):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    original = generation(outputs=1800)
    model, calls = response(outputs=700)

    def fail_after_response(*args, **kwargs):
        raise runtime.RoleRequestError("synthetic late failure")

    monkeypatch.setattr(mod, "_build_output", fail_after_response)
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    assert len(calls) == 1 and caught.value.audit_may_have_started
    assert caught.value.generation_usage == original.usage
    assert caught.value.audit_usage.model_dump() == dict(
        input_tokens=100, output_tokens=700, requests=1
    )
    assert caught.value.combined_usage.output_tokens == 2500


@pytest.mark.parametrize("requests", [0, 2])
def test_audit_stage_requires_one_observed_request(requests):
    mod = api()
    got = run()
    altered = got.model_dump(mode="json")
    altered["audit_usage"]["requests"] = requests
    altered["combined_usage"]["requests"] = requests + 1
    with pytest.raises(mod.RoleTableAuditError):
        mod.validate_role_table_audit_generation(source(), altered)


def test_exhausted_generation_total_blocks_send_and_keeps_known_generation_usage():
    mod = api()
    original = generation(inputs=18200, outputs=1800)
    model, calls = response()
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    assert calls == [] and not caught.value.audit_may_have_started
    assert caught.value.audit_usage is None
    assert caught.value.combined_usage == original.usage


def test_table_own_markers_hashes_and_no_old_receipt_validation(monkeypatch):
    from hashlib import sha256

    mod = api()
    old = importlib.import_module("issuedigest_agents.semantic_role_audit")

    def forbidden(*args, **kwargs):
        raise AssertionError("Old receipt validator must not be called")

    monkeypatch.setattr(old, "validate_semantic_role_audit_generation", forbidden)
    got = run()
    prompt = mod.role_table_audit_prompt(source(), got.report.generation)
    body = json.loads(prompt)
    assert body["profile"] == got.profile == "role-table-audit-v1"
    assert body["input_format"] == got.input_format == "named-columns-v1"
    assert body["proposal"]["bindings"]["columns"] == [
        "number",
        "context",
        "scopes",
        "status_sentence",
        "change",
    ]
    assert got.prompt_sha256 == sha256(prompt.encode()).hexdigest()
    assert got.instructions_sha256 == sha256(mod.ROLE_TABLE_AUDIT_INSTRUCTIONS.encode()).hexdigest()
    assert mod.PROVIDER_IDENTITY == "issuedigest_role_table_audit_v1"
    decoder = (
        "Tables {columns,rows} carry complete original objects: map each row cell to its exact "
        "named column, in order. All cells exist, including null and empty lists. Nested "
        "anchors/scopes/change stay named objects. Read candidates and scope slots the same "
        "way; concatenate each quote sentence table text column in row order with no "
        "separators, preserving blanks and whitespace. Never infer missing cells or merge rows. "
    )
    assert (
        mod.ROLE_TABLE_AUDIT_INSTRUCTIONS
        == decoder
        + old.SEMANTIC_ROLE_AUDIT_INSTRUCTIONS.replace("audit_role_aware_v2", "audit_role_table_v1")
    )
    assert mod.validate_role_table_audit_generation(source(), got) == got


@pytest.mark.parametrize("stage", ["_build_output", "validate_role_table_audit_generation"])
@pytest.mark.parametrize("kind", ["request", "own", "plain"])
def test_late_error_with_empty_inner_usage_retains_observed_outer_cost(monkeypatch, stage, kind):
    mod = api()
    runtime = importlib.import_module("issuedigest_agents.role_bounded_runtime")
    error_type = {
        "request": runtime.RoleRequestError,
        "own": mod.RoleTableAuditError,
        "plain": ValueError,
    }[kind]

    def fail(*args, **kwargs):
        raise error_type("private late detail")

    monkeypatch.setattr(mod, stage, fail)
    original = generation(outputs=1800)
    model, calls = response(outputs=700)
    with pytest.raises(mod.RoleTableAuditError) as caught:
        mod.run_role_table_auditor(mod.create_role_table_auditor(model), source(), original)
    err = caught.value
    assert len(calls) == 1 and err.audit_may_have_started
    assert err.generation_usage == original.usage
    assert err.audit_usage.model_dump() == dict(input_tokens=100, output_tokens=700, requests=1)
    assert err.combined_usage.model_dump() == dict(input_tokens=200, output_tokens=2500, requests=2)
    assert "private late detail" not in str(err)


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "mutation", ["nested_nullable", "input_format", "source", "scalar", "rows"]
)
def test_stored_raw_actual_nested_source_and_container_tampering(actual, mutation):
    from test_role_table_packet import ListSubclass, StringSubclass

    mod = api()
    got = run()
    src = deepcopy(source())
    bad = got.model_copy(deep=True) if actual else got.model_dump(mode="json")
    fields = bad.__dict__ if actual else bad
    if mutation == "input_format":
        fields["input_format"] = "other"
    elif mutation == "source":
        src[1].representation.__dict__["text"] += " changed"
    elif mutation == "scalar":
        fields["profile"] = StringSubclass(fields["profile"])
    elif mutation == "rows":
        if actual:
            bad.report.input.__dict__["checks"] = ListSubclass(bad.report.input.checks)
        else:
            bad["report"]["input"]["checks"] = tuple(bad["report"]["input"]["checks"])
    elif actual:
        del bad.report.generation.frame.input.contexts[0].entity.__dict__["c"]
    else:
        del bad["report"]["generation"]["frame"]["input"]["contexts"][0]["entity"]["c"]
    with pytest.raises(mod.RoleTableAuditError):
        mod.validate_role_table_audit_generation(src, bad)


def test_maximum_explicit_144_diagnostics_cross_table_sdk_unchanged():
    from test_semantic_role_audit_contract import issue

    src = document(" ".join(f"대상 {i}명" for i in range(31, 43)) + ".")
    data = packet()
    data["contexts"][0]["entity"] = None
    data["bindings"] = [
        dict(number=f"n{i}", context="c1", scopes=[], status_sentence=None, change=None)
        for i in range(1, 13)
    ]
    numbers = [f"n{i}" for i in range(1, 13)]
    groups = [issue(*numbers, evidence=anchor(f"{i}명")) for i in range(31, 43)]
    original = generation(src, data)
    got = run(original, src, data=audit_input(*numbers, issues=groups, status="issues_found"))
    assert len(got.report.issues) == 144 and got.report.status == "issues_flagged"
    assert got.report.proposal.model_dump(mode="json") == data
    assert api().validate_role_table_audit_generation(src, got.model_dump(mode="json")) == got


def test_current_scope_targets_validate_through_table_sdk():
    from test_semantic_role_audit_contract import issue

    mod = api()
    src = document("합성국 동부 이용자 37명 증가.")
    data = packet()
    data["contexts"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("합성국"))]
    data["bindings"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("동부"))]
    original = generation(src, data)
    raw = audit_input(
        "n1",
        status="issues_found",
        issues=[issue("n1", kind="unsupported", slots=["r2"], evidence=anchor("동부"))],
    )
    got = run(original, src, data=raw)
    assert got.report.issues[0].scope_slot == "r2"
    assert got.report.proposal.model_dump(mode="json") == data
    raw["issues"][0]["targets"][0]["slot"] = "r3"
    with pytest.raises(mod.RoleTableAuditError) as caught:
        run(original, src, data=raw)
    assert caught.value.audit_usage.output_tokens == 30


@pytest.mark.parametrize("mutation", ["scalar", "missing", "nested"])
def test_dynamic_original_values_are_checked_before_serialization(mutation):
    from test_role_table_packet import StringSubclass

    mod = api()
    original = generation()
    _, tools, _, _ = mod._preflight(source(), original)
    cls = tools[0].output
    good = cls.model_validate_json(json.dumps(audit_input("n1")), strict=True)
    if mutation == "scalar":
        good.checks[0].__dict__["number"] = StringSubclass("n1")
    elif mutation == "missing":
        del good.checks[0].__dict__["status"]
    else:
        good.__dict__["incomplete"] = 0
    with pytest.raises(ValueError):
        mod._build_output(source(), original, good, cls)
