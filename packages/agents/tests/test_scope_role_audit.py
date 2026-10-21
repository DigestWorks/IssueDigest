"""Synthetic bounded audit SDK and mock wire; no paid calls or meaning certification."""

import importlib
import importlib.util
import json
from types import SimpleNamespace

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document
from test_scope_audit_contract import audit_input, generation, issue
from test_shared_measurement_context_v2 import binding, packet, scope
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


def api():
    name = "issuedigest_agents.scope_role_audit"
    assert importlib.util.find_spec(name) is not None, "Missing scope role audit SDK"
    return importlib.import_module(name)


def response(data=None, *, inputs=100, outputs=30, error=None, text=False):
    calls = []

    def respond(messages, info):
        calls.append((messages, info))
        if error:
            raise error
        return ModelResponse(
            parts=[TextPart("free text")]
            if text
            else [
                ToolCallPart(
                    "audit_scope_roles_v1", json.dumps(audit_input("n1") if data is None else data)
                )
            ],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src=None, original=None, data=None, **options):
    mod = api()
    src = src or document("동부 이용자 37명.")
    original = original or generation(src)
    model, calls = response(data, **options)
    result = mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
    assert len(calls) == 1
    return result


def test_audit_prompt_is_complete_local_source_packet_with_exact_ordered_projection():
    mod = api()
    src = document("설명.\n 동부 이용자 약 37여 명 내외.", "다른 항목 83개교.")
    original = generation(src)
    body = json.loads(mod.scope_role_audit_prompt(src, original))
    assert body["profile"] == "scope-role-audit-v1"
    assert ["".join(s["text"] for s in q["sentences"]) for q in body["quotes"]] == [
        "설명.\n 동부 이용자 약 37여 명 내외.",
        "다른 항목 83개교.",
    ]
    assert len(body["candidates"]) == 2
    assert [p["candidate_id"] for p in body["projection"]] == ["n1"]
    assert body["projection"][0]["target_scopes"] == []
    prompt = mod.scope_role_audit_prompt(src, original)
    assert str(src[0]) not in prompt and original.prompt_sha256 not in prompt
    with pytest.raises(mod.ScopeRoleAuditError):
        mod.scope_role_audit_prompt(src, original.model_dump(mode="json"))


def test_completed_audit_preserves_report_receipts_and_two_request_aggregate():
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src)
    result = run(src, original, audit_input("n1", issues=[issue()], status="issues_found"))
    assert result.profile == "scope-role-audit-v1"
    assert result.report.generation == original and result.report.status == "issues_flagged"
    assert result.audit_usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    assert result.combined_usage.model_dump() == dict(
        input_tokens=200, output_tokens=60, requests=2
    )
    assert mod.validate_scope_role_audit_generation(src, result) == result
    assert (
        mod.validate_scope_role_audit_generation(src, json.loads(result.model_dump_json()))
        == result
    )


def test_empty_selection_has_no_audit_usage_request_or_positive_review_even_at_full_budget():
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(
        src, dict(contexts=[], events=[], bindings=[], relations=[]), inputs=17500, outputs=2500
    )
    model, calls = response()
    result = mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
    assert calls == []
    assert result.report.status == "not_applicable" and result.audit_usage is None
    assert result.combined_usage == original.usage
    assert mod.validate_scope_role_audit_generation(src, result) == result


@pytest.mark.parametrize("inputs,outputs", [(18900, 970), (19870, 0)])
def test_runtime_aggregate_inclusive_total_and_output_limits(inputs, outputs):
    result = run(inputs=inputs, outputs=outputs)
    assert result.combined_usage.input_tokens + result.combined_usage.output_tokens == 20000
    assert result.combined_usage.output_tokens <= 2500


@pytest.mark.parametrize(
    "generation_output,audit_output,accepted",
    [(1500, 1000, True), (1501, 999, True), (1501, 1000, False), (0, 1001, False)],
)
def test_audit_dynamic_output_cap_is_smaller_of_thousand_and_remaining(
    generation_output, audit_output, accepted
):
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src, outputs=generation_output)
    model, calls = response(outputs=audit_output)
    if accepted:
        result = mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
        assert result.combined_usage.output_tokens == generation_output + audit_output
    else:
        with pytest.raises(mod.ScopeRoleAuditError) as caught:
            mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
        assert caught.value.generation_usage == original.usage
        assert caught.value.audit_may_have_started is True
    assert len(calls) == 1


@pytest.mark.parametrize("sizes", [(111, 999), (999, 111)])
def test_preflight_uses_utf8_actual_schema_remaining_inclusive_and_blocks_one_over(
    monkeypatch, sizes
):
    mod = api()
    src = document("🧪 동부 이용자 37명.")
    original = generation(src)
    monkeypatch.setattr(mod, "_provider_schema_bytes_v5", lambda tools: sizes)
    prompt, tools, remaining, cap = mod._preflight(src, original)
    envelope = (
        len(prompt.encode()) + len(mod.SCOPE_ROLE_AUDIT_INSTRUCTIONS.encode()) + 999 + 2048 + cap
    )
    # Only local stage budget constants change; frozen generation limits do not.
    monkeypatch.setattr(mod, "MAX_RUN_TOKENS", envelope + 130)
    assert mod.scope_role_audit_prompt(src, original) == prompt
    monkeypatch.setattr(mod, "MAX_RUN_TOKENS", envelope + 129)
    model, calls = response()
    with pytest.raises(mod.ScopeRoleAuditError) as caught:
        mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
    assert calls == [] and caught.value.audit_may_have_started is False
    assert caught.value.generation_usage == original.usage
    assert caught.value.audit_usage is None and caught.value.combined_usage == original.usage


@pytest.mark.parametrize("case", ["zero_output", "no_total", "bad_generation", "bad_model"])
def test_preflight_failures_send_zero_and_preserve_only_validated_generation_usage(case):
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(
        src,
        inputs=19969 if case == "no_total" else 100,
        outputs=2500 if case == "zero_output" else 30,
    )
    if case == "bad_generation":
        original = original.model_copy(update={"usage": original.usage.model_dump()})
    model, calls = response()
    handle = (
        mod.create_scope_role_auditor(model)
        if case != "bad_model"
        else SimpleNamespace(model=model)
    )
    with pytest.raises(mod.ScopeRoleAuditError) as caught:
        mod.run_scope_role_auditor(handle, src, original)
    assert calls == [] and caught.value.audit_may_have_started is False
    assert caught.value.audit_usage is None
    assert (caught.value.generation_usage is None) == (case == "bad_generation")


@pytest.mark.parametrize(
    "options,known",
    [
        ({"error": RuntimeError("private source")}, False),
        ({"text": True}, True),
        ({"inputs": 19900, "outputs": 1}, True),
    ],
)
def test_audit_failure_metadata_distinguishes_started_unknown_and_known_usage(options, known):
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src)
    model, calls = response(**options)
    with pytest.raises(mod.ScopeRoleAuditError) as caught:
        mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
    error = caught.value
    assert len(calls) == 1 and error.audit_may_have_started is True
    assert error.generation_usage == original.usage and (error.audit_usage is not None) == known
    assert (error.combined_usage is not None) == known
    assert str(error) == "Scope role audit failed" and error.__cause__ is None


@pytest.mark.parametrize(
    "change",
    [
        "unknown_candidate",
        "unknown_sentence",
        "bad_slot",
        "extra",
        "missing_check",
        "contradiction",
        "incomplete",
    ],
)
def test_dynamic_schema_and_report_guards_reject_entire_output_without_retry(change):
    mod = api()
    src = document("동부 이용자 37명과 서부 이용자 59명.")
    data = packet()
    data["contexts"][0]["target_scopes"] = [scope("동부")]
    raw = audit_input("n1", issues=[issue()], status="issues_found")
    if change == "unknown_candidate":
        raw["issues"][0]["candidate_id"] = "n2"
    elif change == "unknown_sentence":
        raw["issues"][0]["support_sentence_ids"] = ["s99"]
    elif change == "bad_slot":
        raw["issues"][0].update(kind="unsupported", scope_slot="r2")
    elif change == "extra":
        raw["approved"] = True
    elif change == "missing_check":
        raw["checks"] = []
    elif change == "contradiction":
        raw["checks"][0]["status"] = "no_issue_found"
    else:
        raw = audit_input("n1", incomplete=True)
    model, calls = response(raw)
    with pytest.raises(mod.ScopeRoleAuditError):
        mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, generation(src, data))
    assert len(calls) == 1


@pytest.mark.parametrize("change", ["checks_list", "issue_dict", "canonical_anchor", "subclass"])
def test_actual_dynamic_output_types_are_checked_before_narrowing(monkeypatch, change):
    from pydantic import Field, create_model

    mod = api()
    original_run = mod.Agent.run_sync

    def forged(self, *args, **kwargs):
        result = original_run(self, *args, **kwargs)
        output = result.output
        row = output.issues[0]
        if change == "checks_list":
            output = output.model_copy(update={"checks": list(output.checks)})
        elif change == "issue_dict":
            output = output.model_copy(update={"issues": (row.model_dump(),)})
        else:
            anchor = row.source_anchor
            if change == "canonical_anchor":
                anchor = (
                    type(anchor)
                    .__bases__[0]
                    .model_validate_json(anchor.model_dump_json(), strict=True)
                )
            else:
                cls = create_model(
                    "ExtraAuditAnchor",
                    __base__=type(anchor),
                    hidden=(str, Field(default="hidden", exclude=True)),
                )
                anchor = cls.model_validate(anchor.model_dump())
            output = output.model_copy(
                update={"issues": (row.model_copy(update={"source_anchor": anchor}),)}
            )
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(mod.Agent, "run_sync", forged)
    with pytest.raises(mod.ScopeRoleAuditError) as caught:
        run(data=audit_input("n1", issues=[issue()], status="issues_found"))
    assert caught.value.audit_usage.input_tokens == 100


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "prompt",
        "instructions",
        "audit_usage",
        "aggregate",
        "aggregate_requests",
        "report",
        "source",
        "nested_dict",
        "list",
        "subclass",
        "missing_profile",
    ],
)
def test_stored_runtime_generation_reconstructs_report_hashes_and_combined_budget(field):
    from pydantic import Field, create_model

    mod = api()
    src = document("동부 이용자 37명.")
    result = run(src)
    raw = json.loads(result.model_dump_json())
    if field == "missing_profile":
        raw.pop("profile")
    elif field == "profile":
        raw["profile"] = "shared-context-generation-v2"
    elif field in ("prompt", "instructions"):
        raw[f"{field}_sha256"] = "0" * 64
    elif field == "audit_usage":
        raw["audit_usage"]["output_tokens"] = 1001
    elif field == "aggregate":
        raw["combined_usage"]["input_tokens"] += 1
    elif field == "aggregate_requests":
        raw["combined_usage"]["requests"] = 1
    elif field == "report":
        raw["report"]["projection"][0]["candidate_id"] = "n99"
    elif field == "source":
        src = document("동부 이용자 38명.")
    elif field == "nested_dict":
        raw = result.model_copy(update={"audit_usage": result.audit_usage.model_dump()})
    elif field == "list":
        report = result.report.model_copy(update={"projection": list(result.report.projection)})
        raw = result.model_copy(update={"report": report})
    else:
        cls = create_model(
            "ExtraAuditGeneration",
            __base__=type(result),
            hidden=(str, Field(default="hidden", exclude=True)),
        )
        raw = cls.model_validate(result.model_dump())
    with pytest.raises(mod.ScopeRoleAuditError):
        mod.validate_scope_role_audit_generation(src, raw)


def test_dynamic_runtime_limits_identity_lifecycle_and_required_model(monkeypatch):
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src, inputs=300, outputs=1700)
    model, calls = response()
    original_init, original_run = mod.Agent.__init__, mod.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_scope_role_audit_v1" and kwargs["retries"] == 0
        return original_init(self, *args, **kwargs)

    def called(self, *args, **kwargs):
        limits = kwargs["usage_limits"]
        assert (limits.request_limit, limits.total_tokens_limit, limits.output_tokens_limit) == (
            1,
            18000,
            800,
        )
        assert kwargs["model_settings"] == dict(openai_store=False, max_tokens=800, timeout=30)
        assert kwargs["retries"] == 0
        return original_run(self, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Caller owns lifecycle")

    monkeypatch.setattr(mod.Agent, "__init__", initialized)
    monkeypatch.setattr(mod.Agent, "run_sync", called)
    monkeypatch.setattr(model, "__aenter__", forbidden)
    monkeypatch.setattr(model, "__aexit__", forbidden)
    handle = mod.create_scope_role_auditor(model)
    assert calls == []
    assert mod.run_scope_role_auditor(handle, src, original).combined_usage.requests == 2
    with pytest.raises(TypeError):
        mod.create_scope_role_auditor()
    with pytest.raises(mod.ScopeRoleAuditError):
        mod.create_scope_role_auditor(None)


def test_mock_responses_wire_is_one_strict_no_store_borrowed_request(sync_model_loop):
    import httpx2
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src, outputs=1700)
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
                        name="audit_scope_roles_v1",
                        arguments=json.dumps(audit_input("n1")),
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
        result = mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
        assert result.report.status == "no_issues_flagged" and len(requests) == 1
        body = json.loads(requests[0].content)
        assert (body["store"], body["max_output_tokens"], body["temperature"]) == (False, 800, 0.25)
        assert len(body["tools"]) == 1
        tool = body["tools"][0]
        assert tool["strict"] is True and tool["name"] == "audit_scope_roles_v1"
        assert tool["parameters"]["required"] == ["checks", "issues", "incomplete"]
        assert body["input"][0] == dict(
            role="user", content=mod.scope_role_audit_prompt(src, original)
        )
        assert not client.is_closed
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


def test_schema_uses_selected_candidate_sentence_and_present_slot_enums():
    mod = api()
    src = document("동부 서부 이용자 37명과 다른 이용자 59명. 설명.")
    data = packet()
    data["contexts"][0]["target_scopes"] = [scope("동부"), scope("서부")]
    original = generation(src, data)
    _, tools, _, _ = mod._preflight(src, original)
    schema = tools[0].output.model_json_schema()
    definitions = schema["$defs"]
    assert definitions["ScopeAuditCheckV1"]["properties"]["candidate_id"]["const"] == "n1"
    properties = definitions["ScopeAuditIssueV1"]["properties"]
    assert properties["support_sentence_ids"]["items"]["enum"] == ["s1", "s2"]
    assert properties["scope_slot"]["anyOf"][0]["enum"] == ["r1", "r2"]
    assert definitions["ScopeAuditAnchorV1"]["properties"]["sentence_id"]["enum"] == ["s1", "s2"]


def test_slot_present_on_another_selected_candidate_cannot_be_borrowed():
    mod = api()
    src = document("동부 서부 이용자 37명과 다른 이용자 59명.")
    data = packet()
    data["contexts"][0]["target_scopes"] = [scope("동부")]
    data["bindings"].append(binding("n2", target_scopes=[scope("서부")]))
    original = generation(src, data)
    raw = audit_input("n1", "n2", issues=[issue(kind="unsupported", slot="r2")])
    raw["checks"][0]["status"] = "issues_found"
    model, calls = response(raw)
    with pytest.raises(mod.ScopeRoleAuditError) as caught:
        mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
    assert len(calls) == 1 and caught.value.audit_usage.requests == 1


@pytest.mark.parametrize(
    "field,value",
    [("audit_usage", None), ("requests", 2), ("output_tokens", True), ("input_tokens", -1)],
)
def test_stored_audit_requires_actual_known_nonnegative_single_stage_usage(field, value):
    mod = api()
    src = document("동부 이용자 37명.")
    raw = json.loads(run(src).model_dump_json())
    if field == "audit_usage":
        raw[field] = value
    else:
        raw["audit_usage"][field] = value
    with pytest.raises(mod.ScopeRoleAuditError):
        mod.validate_scope_role_audit_generation(src, raw)


def test_agent_initialization_failure_did_not_start_audit_or_consume_unknown_usage(monkeypatch):
    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src)
    model, calls = response()

    def failed(*args, **kwargs):
        raise RuntimeError("private initialization details")

    monkeypatch.setattr(mod.Agent, "__init__", failed)
    with pytest.raises(mod.ScopeRoleAuditError) as caught:
        mod.run_scope_role_auditor(mod.create_scope_role_auditor(model), src, original)
    assert calls == [] and caught.value.audit_may_have_started is False
    assert caught.value.audit_usage is None and caught.value.combined_usage == original.usage
