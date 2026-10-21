"""Synthetic shared generation boundaries; exact linkage is not semantic review."""

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
from pydantic import Field, ValidationError, create_model
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document


@pytest.fixture(autouse=True)
def own_loop(sync_model_loop):
    yield


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_modules():
    names = (
        "shared_context_generation",
        "shared_measurement_context",
        "measurement_frame_generation",
        "contextual_frame_generation",
        "contextual_frame",
        "contextual_anchor",
        "measurement_scope",
        "numeric_frame",
        "numeric_frame_generation",
        "numeric_selection_evaluation",
        "numeric_selection",
    )
    introduced = [
        f"issuedigest_agents.{n}" for n in names if f"issuedigest_agents.{n}" not in sys.modules
    ]
    yield
    for name in introduced:
        sys.modules.pop(name, None)


def sdk():
    name = "issuedigest_agents.shared_context_generation"
    assert importlib.util.find_spec(name) is not None, "Missing shared context generation SDK"
    return importlib.import_module(name)


def anchor(text, sentence="s1", context=None):
    return dict(sentence_id=sentence, text=text, context_text=context)


def scope(text, kind="geographic"):
    return dict(kind=kind, anchor=anchor(text))


def context(context_id="c1", event_id="e1", **fields):
    return dict(
        context_id=context_id,
        reporting_event_id=event_id,
        measured_variable=None,
        target_scopes=[],
        period=None,
        value_status="unknown",
        logical_condition=None,
        purpose=None,
        forecast_basis=None,
        comparison_baseline=None,
        **fields,
    )


def event(event_id="e1", **fields):
    return {
        "event_id": event_id,
        "kind": "unknown",
        "reporting_actor": None,
        "predicate": None,
        "reporting_tense": "unknown",
        **fields,
    }


def binding(candidate="n1", context_id="c1", **fields):
    return {
        "candidate_id": candidate,
        "context_id": context_id,
        "target_scopes": [],
        "status_evidence_sentence_id": None,
        **fields,
    }


def packet():
    return dict(contexts=[context()], events=[event()], bindings=[binding()], relations=[])


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
            else [ToolCallPart("fill_shared_context_v1", json.dumps(data))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src=None, data=None, **options):
    api = sdk()
    model, calls = response(packet() if data is None else data, **options)
    result = api.run_shared_context_framer(
        api.create_shared_context_framer(model), src or document("항목 10명.")
    )
    assert len(calls) == 1
    return result


def test_shared_roles_purpose_whole_status_and_receipts():
    api = sdk()
    src = document(
        "🧪 발표처는 수요로 내년 조건 충족 시 동부 청년 이용자 "
        "전월비 10명 전망을 지원 목적으로 발표했다."
    )
    data = packet()
    data["contexts"][0].update(
        measured_variable=anchor("이용자"),
        target_scopes=[scope("동부")],
        period=anchor("내년"),
        value_status="forecast",
        logical_condition=anchor("조건 충족 시"),
        purpose=anchor("지원 목적으로"),
        forecast_basis=anchor("수요로"),
        comparison_baseline=anchor("전월비"),
    )
    data["events"][0] = event(
        kind="attributed_report",
        reporting_actor=anchor("발표처"),
        predicate=anchor("발표했다"),
        reporting_tense="past",
    )
    data["bindings"][0].update(
        target_scopes=[scope("청년", "population")], status_evidence_sentence_id="s1"
    )
    result = run(src, data)
    assert (result.profile, result.status) == ("shared-context-generation-v1", "unreviewed")
    got = result.frame.frame.frame.resolved.facts[0]
    assert got.measured_entity.span.text == "이용자"
    assert got.reporting_actor.span.text == "발표처"
    assert (got.value_status, got.reporting_tense) == ("forecast", "past")
    assert got.logical_condition.span.text == "조건 충족 시"
    assert result.frame.purposes[0].purpose.span.text == "지원 목적으로"
    assert got.status_text.span.text == src[1].citations[0].selector.quote
    assert [s.anchor.span.text for s in result.frame.frame.scopes[0].target_scopes] == [
        "동부",
        "청년",
    ]
    assert result.prompt_sha256 == sha256(api.shared_context_prompt(src).encode()).hexdigest()
    assert (
        result.instructions_sha256 == sha256(api.SHARED_CONTEXT_INSTRUCTIONS.encode()).hexdigest()
    )
    assert result.usage.model_dump() == dict(input_tokens=100, output_tokens=30, requests=1)
    assert api.validate_shared_context_generation(src, result) == result
    assert (
        api.validate_shared_context_generation(src, json.loads(result.model_dump_json())) == result
    )


@pytest.mark.parametrize("status", ["observed", "planned", "forecast", "unknown"])
@pytest.mark.parametrize("kind", ["attributed_report", "narration", "unknown"])
def test_status_independent_of_reporting_kind(status, kind):
    data = packet()
    data["contexts"][0]["value_status"] = status
    data["bindings"][0]["status_evidence_sentence_id"] = "s1"
    if kind != "unknown":
        data["events"][0] = event(
            kind=kind,
            reporting_actor=anchor("기관") if kind == "attributed_report" else None,
            predicate=anchor("발표했다"),
            reporting_tense="past",
        )
    result = run(document("기관 항목 10 발표했다."), data)
    assert result.frame.input.contexts[0].value_status == status
    assert result.frame.input.events[0].kind == kind


@pytest.mark.parametrize(
    "path,value",
    [
        (("contexts", 0, "context_id"), "c13"),
        (("contexts", 0, "reporting_event_id"), "e13"),
        (("bindings", 0, "context_id"), "c13"),
        (("events", 0, "event_id"), "e13"),
        (("bindings", 0, "candidate_id"), "n2"),
        (("bindings", 0, "status_evidence_sentence_id"), "s2"),
        (("contexts", 0, "purpose"), anchor("항목", "s2")),
        (("contexts", 0, "purpose"), anchor("없는말")),
        (("contexts", 0, "value_status"), "fabricated"),
        (("contexts", 0, "target_scopes"), [scope("항목")] * 5),
        (("bindings", 0, "target_scopes"), [scope("항목")] * 5),
        (("events", 0, "reporting_actor"), anchor("항목")),
        (("events", 0, "predicate"), anchor("항목")),
        (("events", 0, "reporting_tense"), "future"),
        (("events", 0, "kind"), "narration"),
        (("events", 0, "kind"), "attributed_report"),
    ],
)
def test_invalid_provider_records_rejected_once_with_usage(path, value):
    api = sdk()
    data = packet()
    data[path[0]][path[1]][path[2]] = value
    model, calls = response(data)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer(
            api.create_shared_context_framer(model), document("항목 10명.")
        )
    assert len(calls) == 1 and caught.value.known_usage.input_tokens == 100
    assert str(caught.value) == "Shared context generation failed"
    assert caught.value.__cause__ is None


def test_empty_output_and_non_numeric_source_policy():
    assert (
        run(data=dict(contexts=[], events=[], bindings=[], relations=[])).frame.input.bindings == ()
    )
    api = sdk()
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer(
            api.create_shared_context_framer(model), document("수치 없는 문장.")
        )
    assert calls == [] and caught.value.known_usage is None


@pytest.mark.parametrize(
    "status,evidence", [("observed", None), ("forecast", "s1"), ("unknown", "s1")]
)
def test_no_eligible_sentence_narrows_status_and_evidence(status, evidence):
    api = sdk()
    data = packet()
    data["contexts"][0]["value_status"] = status
    data["bindings"][0]["status_evidence_sentence_id"] = evidence
    model, calls = response(data)
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer(
            api.create_shared_context_framer(model), document("x" * 998 + " 10")
        )
    assert len(calls) == 1
    assert run(document("x" * 998 + " 10")).frame.input.contexts[0].value_status == "unknown"


@pytest.mark.parametrize(
    "key,cap", [("contexts", 12), ("events", 12), ("bindings", 12), ("relations", 16)]
)
def test_each_array_cap_independently_rejects_at_dynamic_boundary(key, cap):
    api = sdk()
    _, tools = api._preflight(document("항목 10명, 20명."))
    model = tools[0].output
    data = packet()
    data["relations"] = [
        dict(
            from_id="n1",
            to_id="n2",
            kind="parallel",
            statement_sentence_ids=["s1"],
            cue=anchor("항목"),
        )
    ]
    # Direct dynamic validation isolates cap errors from reference uniqueness and role builders.
    data[key] *= cap
    model.model_validate_json(json.dumps(data), strict=True)
    data[key].append(deepcopy(data[key][0]))
    with pytest.raises(ValidationError) as caught:
        model.model_validate_json(json.dumps(data), strict=True)
    assert any(e["type"] == "too_long" and e["loc"] == (key,) for e in caught.value.errors())


def test_full_source_prompt_and_actual_strict_schema():
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    api = sdk()
    src = document("🧪 항목 10명.", "다른 항목 20명.")
    prompt, tools = api._preflight(src)
    payload = json.loads(prompt)
    assert payload["profile"] == "shared-context-generation-v1"
    assert payload["eligible_status_sentence_ids"] == ["s1", "s2"]
    assert payload["context_id_slots"] == [f"c{i}" for i in range(1, 13)]
    assert payload["reporting_event_id_slots"] == [f"e{i}" for i in range(1, 13)]
    assert "🧪 항목 10명." in prompt and "다른 항목 20명." in prompt
    assert len(tools) == 1 and tools[0].strict and tools[0].name == "fill_shared_context_v1"
    raw = tools[0].output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    normalized = OpenAIJsonSchemaTransformer(raw, strict=True).walk()
    assert normalized["required"] == ["contexts", "events", "bindings", "relations"]
    for node in [normalized, *normalized.get("$defs", {}).values()]:
        if node.get("type") == "object":
            assert node["additionalProperties"] is False
            assert set(node["required"]) == set(node["properties"])
    serialized = json.dumps(normalized)
    assert "\\\\A[A-Za-z0-9_-]+\\\\z" not in serialized


@pytest.mark.parametrize(
    "field,value",
    [
        ("profile", "wrong"),
        ("status", "reviewed"),
        ("prompt_sha256", "0" * 64),
        ("instructions_sha256", "0" * 64),
        ("usage", dict(input_tokens=1, output_tokens=1, requests=2)),
    ],
)
def test_stored_receipt_and_usage_tampering(field, value):
    api = sdk()
    src = document("항목 10명.")
    result = run(src)
    for changed in [
        result.model_copy(update={field: value}),
        {**json.loads(result.model_dump_json()), field: value},
    ]:
        with pytest.raises(api.SharedContextGenerationError):
            api.validate_shared_context_generation(src, changed)


def test_stored_whole_frame_and_current_dynamic_slots_are_revalidated():
    api = sdk()
    src = document("항목 10명.")
    result = run(src)
    raw = json.loads(result.model_dump_json())
    raw["frame"]["purposes"][0]["context_id"] = "c2"
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation(src, raw)
    pure = importlib.import_module("issuedigest_agents.shared_measurement_context")
    data = packet()
    data["contexts"][0]["context_id"] = data["bindings"][0]["context_id"] = "valid_but_not_slot"
    frame = pure.build_shared_measurement_frame(src, data)
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation(src, result.model_copy(update={"frame": frame}))
    title_only = (src[0], src[1], src[2].model_copy(update={"title": "Changed title"}))
    assert api.validate_shared_context_generation(title_only, result) == result
    changed_source = document("항목 11명.")
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation(changed_source, result)


@pytest.mark.parametrize(
    "change",
    [
        "root-dict",
        "list",
        "row-dict",
        "anchor-dict",
        "scope-dict",
        "subclass",
        "extra",
        "unchecked-id",
    ],
)
def test_actual_dynamic_nested_types_checked_before_narrowing(monkeypatch, change):
    api = sdk()
    original = api._runtime.Agent.run_sync

    def forged(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        output = result.output
        row = output.contexts[0]
        if change == "root-dict":
            output = output.model_dump(mode="json")
        elif change == "list":
            output = output.model_copy(update={"contexts": list(output.contexts)})
        elif change == "row-dict":
            output = output.model_copy(update={"contexts": (row.model_dump(mode="json"),)})
        else:
            if change == "anchor-dict":
                row = row.model_copy(update={"measured_variable": anchor("항목")})
            elif change == "scope-dict":
                row = row.model_copy(update={"target_scopes": (scope("항목"),)})
            elif change == "subclass":
                subclass = create_model(
                    "HiddenContext",
                    __base__=type(row),
                    hidden=(str, Field(default="secret", exclude=True)),
                )
                row = subclass.model_validate(row.model_dump(mode="python"))
            elif change == "extra":
                row = row.model_copy()
                row.__dict__["hidden"] = "secret"
            else:
                row = row.model_copy(update={"context_id": "c13"})
            output = output.model_copy(update={"contexts": (row,)})
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api._runtime.Agent, "run_sync", forged)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        run()
    assert caught.value.known_usage.input_tokens == 100


@pytest.mark.parametrize(
    "text,error,inputs,outputs",
    [
        (True, None, 100, 30),
        (False, RuntimeError("private source secret"), 100, 30),
        (False, None, 19000, 1100),
        (False, None, 100, 2501),
    ],
)
def test_failures_sanitized_without_retry(text, error, inputs, outputs):
    api = sdk()
    model, calls = response(packet(), text=text, error=error, inputs=inputs, outputs=outputs)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer(
            api.create_shared_context_framer(model), document("항목 10명.")
        )
    assert len(calls) == 1
    assert "secret" not in str(caught.value) and caught.value.__cause__ is None
    if text:
        assert caught.value.known_usage.input_tokens == inputs
    else:
        # Existing SDK may discard capture when it raises at actual token overflow.
        assert caught.value.known_usage is None


def test_full_preflight_budget_rejects_before_model_and_never_clips():
    api = sdk()
    src = document("큰" * 6000 + " 10명.")
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError):
        api.shared_context_prompt(src)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer(api.create_shared_context_framer(model), src)
    assert calls == [] and caught.value.known_usage is None


@pytest.mark.parametrize("invalid", [None, "openai:test", object()])
def test_model_is_required_and_borrowed(invalid):
    api = sdk()
    with pytest.raises(api.SharedContextGenerationError):
        api.create_shared_context_framer(invalid)


def relational():
    src = document("동부 이용자 100명 중 서부 이용자 20명 포함.")
    data = packet()
    data["contexts"] = [
        {**context(), "measured_variable": anchor("이용자", context="동부 이용자")},
        {**context("c2"), "measured_variable": anchor("이용자", context="서부 이용자")},
    ]
    data["bindings"] = [binding(), binding("n2", "c2")]
    data["relations"] = [
        dict(
            from_id="n2",
            to_id="n1",
            kind="included_in",
            statement_sentence_ids=["s1"],
            cue=anchor("중"),
        )
    ]
    return src, data


def test_shared_reporting_event_and_repeated_context_direct_relation():
    src, data = relational()
    result = run(src, data)
    assert len(result.frame.input.events) == 1
    facts = result.frame.frame.frame.resolved.facts
    assert [(f.measured_entity.span.start, f.measured_entity.span.text) for f in facts] == [
        (3, "이용자"),
        (17, "이용자"),
    ]
    assert [(r.kind, r.from_id, r.to_id) for r in result.frame.frame.frame.resolved.relations] == [
        ("included_in", "n2", "n1")
    ]


@pytest.mark.parametrize(
    "change",
    [
        "known-null",
        "wrong-candidate-sentence",
        "cross-quote",
        "duplicate-binding",
        "unused-context",
        "unused-event",
        "missing-context",
        "missing-event",
        "bad-relation",
        "partial-statement",
        "ambiguous-anchor",
        "combined-scope-cap",
    ],
)
def test_whole_operation_rejects_invalid_shared_links_and_relations(change):
    api = sdk()
    src, data = relational()
    if change == "known-null":
        data["contexts"][0]["value_status"] = "planned"
    elif change in ("wrong-candidate-sentence", "cross-quote"):
        src = (
            document("항목 10명. 다른 항목 20명.")
            if change == "wrong-candidate-sentence"
            else document("항목 10명.", "다른 항목 20명.")
        )
        data = packet()
        data["bindings"][0]["status_evidence_sentence_id"] = "s2"
    elif change == "duplicate-binding":
        data["bindings"].append(binding())
    elif change == "unused-context":
        data["contexts"].append(context("c3"))
    elif change == "unused-event":
        data["events"].append(event("e2"))
    elif change == "missing-context":
        data["bindings"][0]["context_id"] = "c3"
    elif change == "missing-event":
        data["contexts"][0]["reporting_event_id"] = "e2"
    elif change == "bad-relation":
        data["relations"][0]["to_id"] = "n3"
    elif change == "partial-statement":
        src = document("동부 100명. 서부 20명 포함.")
        data = packet()
        data["contexts"][0]["measured_variable"] = anchor("동부")
        data["contexts"].append({**context("c2"), "measured_variable": anchor("서부", "s2")})
        data["bindings"].append(binding("n2", "c2"))
        data["relations"] = [
            dict(
                from_id="n2",
                to_id="n1",
                kind="included_in",
                statement_sentence_ids=["s2"],
                cue=anchor("포함", "s2"),
            )
        ]
    elif change == "ambiguous-anchor":
        data["contexts"][0]["measured_variable"]["context_text"] = None
    else:
        src = document("가 나 다 라 마 항목 10명.")
        data = packet()
        data["contexts"][0]["target_scopes"] = [scope(t) for t in ["가", "나", "다", "라"]]
        data["bindings"][0]["target_scopes"] = [scope("마")]
    model, calls = response(data)
    with pytest.raises(api.SharedContextGenerationError) as caught:
        api.run_shared_context_framer(api.create_shared_context_framer(model), src)
    assert len(calls) == 1 and caught.value.known_usage.input_tokens == 100


@pytest.mark.parametrize("schema_sizes", [None, (111, 999), (999, 111)])
def test_utf8_envelope_inclusive_maximum_raw_or_normalized(monkeypatch, schema_sizes):
    api = sdk()
    src = document("🧪 항목 10명.")
    result = run(src)
    if schema_sizes:
        monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: schema_sizes)
    prompt, tools = api._preflight(src)
    limit = (
        len(prompt.encode())
        + len(api.SHARED_CONTEXT_INSTRUCTIONS.encode())
        + max(api._provider_schema_bytes_v5(tools))
        + 2048
        + 2500
    )
    assert len(prompt.encode()) > len(prompt)
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit)
    assert api.shared_context_prompt(src) == prompt
    assert api.validate_shared_context_generation(src, result) == result
    assert run(src).frame.input.bindings[0].candidate_id == "n1"
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", limit - 1)
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError):
        api.shared_context_prompt(src)
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation(src, result)
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer(api.create_shared_context_framer(model), src)
    assert calls == []


@pytest.mark.parametrize("inputs,outputs", [(17500, 2500), (20000, 0)])
def test_actual_inclusive_usage_bounds(inputs, outputs):
    result = run(inputs=inputs, outputs=outputs)
    assert result.usage.model_dump() == dict(input_tokens=inputs, output_tokens=outputs, requests=1)


@pytest.mark.parametrize(
    "node", ["frame", "input", "usage", "context", "event", "binding", "purposes", "derived"]
)
def test_stored_unchecked_model_containers_rejected(node):
    api = sdk()
    src = document("항목 10명.")
    result = run(src)
    frame = result.frame
    if node == "frame":
        forged = result.model_copy(update={"frame": frame.model_dump(mode="json")})
    elif node == "usage":
        forged = result.model_copy(update={"usage": result.usage.model_dump()})
    else:
        if node == "input":
            frame = frame.model_copy(update={"input": frame.input.model_dump(mode="json")})
        elif node == "purposes":
            frame = frame.model_copy(update={"purposes": list(frame.purposes)})
        elif node == "derived":
            frame = frame.model_copy(update={"frame": frame.frame.model_dump(mode="json")})
        else:
            key = {"context": "contexts", "event": "events", "binding": "bindings"}[node]
            row = getattr(frame.input, key)[0]
            frame = frame.model_copy(
                update={
                    "input": frame.input.model_copy(update={key: (row.model_dump(mode="json"),)})
                }
            )
        forged = result.model_copy(update={"frame": frame})
    with pytest.raises(api.SharedContextGenerationError):
        api.validate_shared_context_generation(src, forged)


@pytest.mark.parametrize(
    "node", ["context", "event", "binding", "scope", "anchor", "relation", "cue"]
)
def test_exact_dynamic_node_types_cannot_be_replaced_with_canonical_base(monkeypatch, node):
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
            output = output.model_copy(update={"contexts": (replacement, output.contexts[1])})
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
            output = output.model_copy(update={"contexts": (row, output.contexts[1])})
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
    src, data = relational()
    data["contexts"][0]["target_scopes"] = [scope("동부")]
    with pytest.raises(api.SharedContextGenerationError) as caught:
        run(src, data)
    assert caught.value.known_usage.input_tokens == 100


def test_shared_runtime_request_identity_settings_and_borrowed_lifecycle(monkeypatch):
    from dataclasses import FrozenInstanceError

    api = sdk()
    original_init, original_run = api._runtime.Agent.__init__, api._runtime.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_shared_context_v1"
        assert kwargs["instructions"] == api.SHARED_CONTEXT_INSTRUCTIONS
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
        raise AssertionError("Caller owns model lifecycle")

    monkeypatch.setattr(api._runtime.Agent, "__init__", initialized)
    monkeypatch.setattr(api._runtime.Agent, "run_sync", called)
    model, calls = response(packet())
    monkeypatch.setattr(model, "__aenter__", forbidden)
    monkeypatch.setattr(model, "__aexit__", forbidden)
    handle = api.create_shared_context_framer(model)
    assert calls == []
    with pytest.raises(FrozenInstanceError):
        handle.model = model
    assert api.run_shared_context_framer(handle, document("항목 10명.")).status == "unreviewed"
    with pytest.raises(TypeError):
        api.create_shared_context_framer()
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer(SimpleNamespace(model=model), document("항목 10명."))


def test_actual_responses_wire_is_strict_bounded_and_preserves_caller_settings(sync_model_loop):
    import httpx2
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.providers.openai import OpenAIProvider

    api = sdk()
    src = document("항목 10명.")
    requests = []

    def transport(request):
        requests.append(request)
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
                        "name": "fill_shared_context_v1",
                        "arguments": json.dumps(packet()),
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
        result = api.run_shared_context_framer(api.create_shared_context_framer(model), src)
        assert result.usage.input_tokens == 100 and len(requests) == 1
        body = json.loads(requests[0].content)
        assert body["store"] is False and body["max_output_tokens"] == 2500
        assert body["temperature"] == 0.25
        assert len(body["tools"]) == 1
        assert body["tools"][0]["strict"] is True
        assert body["tools"][0]["name"] == "fill_shared_context_v1"
        assert body["tools"][0]["parameters"]["required"] == [
            "contexts",
            "events",
            "bindings",
            "relations",
        ]
        assert body["input"][0] == {"role": "user", "content": api.shared_context_prompt(src)}
        assert body["instructions"] == api.SHARED_CONTEXT_INSTRUCTIONS
        assert not client.is_closed
    finally:
        sync_model_loop.run_until_complete(provider_client.close())


@pytest.mark.parametrize("node", ["bundle", "presentation", "representation", "citations"])
def test_source_actual_models_and_tuples_rejected_before_request(node):
    api = sdk()
    src = document("항목 10명.")
    if node == "bundle":
        src = src[0], src[1].model_dump(mode="json"), src[2]
    elif node == "presentation":
        src = src[0], src[1], src[2].model_dump(mode="json")
    elif node == "representation":
        original = src[1].representation
        hidden = create_model(
            "HiddenSource", __base__=type(original), secret=(str, Field(exclude=True))
        )
        widened = hidden(**original.model_dump(), secret="private source")
        src = src[0], src[1].model_copy(update={"representation": widened}), src[2]
    else:
        src = src[0], src[1].model_copy(update={"citations": list(src[1].citations)}), src[2]
    model, calls = response(packet())
    with pytest.raises(api.SharedContextGenerationError):
        api.shared_context_prompt(src)
    with pytest.raises(api.SharedContextGenerationError):
        api.run_shared_context_framer(api.create_shared_context_framer(model), src)
    assert calls == []


def test_cold_import_create_prompt_validate_do_not_allocate_clients_or_use_io():
    code = """
import builtins, importlib, io, os, socket
from hashlib import sha256
import openai, pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
src = document("Item 10")
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
api = importlib.import_module("issuedigest_agents.shared_context_generation")
api.create_shared_context_framer(model)
prompt = api.shared_context_prompt(src)
data = dict(contexts=[], events=[], bindings=[], relations=[])
result = api.SharedContextGeneration(
    frame=api.build_shared_measurement_frame(src, data),
    prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.SHARED_CONTEXT_INSTRUCTIONS.encode()).hexdigest(),
    usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1),
)
assert api.validate_shared_context_generation(src, result) == result
try: api.validate_shared_context_generation(src, {})
except api.SharedContextGenerationError as error: assert error.known_usage is None
else: raise AssertionError("Invalid stored result accepted")
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_dynamic_schema_exact_current_catalogs_and_event_variants():
    from pydantic_ai.tools import GenerateToolJsonSchema

    api = sdk()
    _, tools = api._preflight(document("항목 10명. 두번째 항목 20명."))
    schema = tools[0].output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    defs = schema["$defs"]
    assert defs["SharedCandidateIdV1"]["enum"] == ["n1", "n2"]
    assert defs["SharedSentenceIdV1"]["enum"] == ["s1", "s2"]
    assert defs["SharedStatusSentenceIdV1"]["enum"] == ["s1", "s2"]
    assert defs["SharedContextIdV1"]["enum"] == [f"c{i}" for i in range(1, 13)]
    assert defs["SharedEventIdV1"]["enum"] == [f"e{i}" for i in range(1, 13)]
    for name in ("SharedContextV1", "SharedBindingV1"):
        props = defs[name]["properties"]
        assert props["context_id"] == {"$ref": "#/$defs/SharedContextIdV1"}
        assert props["target_scopes"]["maxItems"] == 4
    unknown = defs["SharedEventUnknownV1"]["properties"]
    assert unknown["reporting_actor"]["type"] == unknown["predicate"]["type"] == "null"
    assert unknown["reporting_tense"]["const"] == "unknown"
    narration = defs["SharedEventNarrationV1"]["properties"]
    assert narration["reporting_actor"]["type"] == "null"
    assert narration["predicate"] == {"$ref": "#/$defs/SharedAnchorV1"}
    attributed = defs["SharedEventAttributedReportV1"]["properties"]
    assert (
        attributed["reporting_actor"]
        == attributed["predicate"]
        == {"$ref": "#/$defs/SharedAnchorV1"}
    )
    _, tools = api._preflight(document("x" * 998 + " 10"))
    no_eligible = tools[0].output.model_json_schema()["$defs"]
    assert no_eligible["SharedContextV1"]["properties"]["value_status"]["const"] == "unknown"
    assert (
        no_eligible["SharedBindingV1"]["properties"]["status_evidence_sentence_id"]["type"]
        == "null"
    )


@pytest.mark.parametrize("section", ["contexts", "bindings"])
def test_scope_cap_independent_of_pure_resolver(section):
    api = sdk()
    _, tools = api._preflight(document("가 나 다 라 마 항목 10명."))
    model = tools[0].output
    data = packet()
    data[section][0]["target_scopes"] = [scope(t) for t in ["가", "나", "다", "라"]]
    model.model_validate_json(json.dumps(data), strict=True)
    data[section][0]["target_scopes"].append(scope("마"))
    with pytest.raises(ValidationError) as caught:
        model.model_validate_json(json.dumps(data), strict=True)
    assert any(
        e["type"] == "too_long" and e["loc"] == (section, 0, "target_scopes")
        for e in caught.value.errors()
    )
