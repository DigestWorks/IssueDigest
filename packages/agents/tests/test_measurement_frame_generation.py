"""Synthetic measurement provider boundaries; linkage never certifies meaning."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import BaseModel, Field, create_model
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_measurement_scope import anchor, scope
from test_numeric_evidence import document

ROLES = (
    "measured_entity",
    "reporting_actor",
    "period",
    "logical_condition",
    "forecast_basis",
    "comparison_baseline",
    "reporting_tense_text",
)


@pytest.fixture(autouse=True)
def own_model_loop(sync_model_loop):
    yield


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_modules():
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)


def sdk():
    name = "issuedigest_agents.measurement_frame_generation"
    assert importlib.util.find_spec(name) is not None, "Missing measurement generation SDK"
    return importlib.import_module(name)


def fact(candidate="n1", **fields):
    return {
        "candidate_id": candidate,
        **dict.fromkeys(ROLES),
        "target_scopes": [],
        "value_status": "unknown",
        "status_evidence_sentence_id": None,
        "reporting_tense": "unknown",
        **fields,
    }


def response(output, *, inspect=None, inputs=100, outputs=30, error=None, text=False):
    calls = []

    def respond(messages, info):
        calls.append(info)
        if inspect:
            inspect(messages, info)
        if error:
            raise error
        return ModelResponse(
            parts=[TextPart("")]
            if text
            else [ToolCallPart("fill_measurement_frame_v1", json.dumps(output))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src, facts=(), relations=(), **options):
    api = sdk()
    model, calls = response({"facts": list(facts), "relations": list(relations)}, **options)
    result = api.run_measurement_framer(api.create_measurement_framer(model), src)
    assert len(calls) == 1
    return result


def rich():
    src = document(
        "🧪 발표처는 수요를 근거로 내년 조건 충족 시 동부 청년 이용자 전월비 10명 전망을 발표했다."
    )
    row = fact(
        measured_entity=anchor("이용자"),
        reporting_actor=anchor("발표처"),
        period=anchor("내년"),
        logical_condition=anchor("조건 충족 시"),
        forecast_basis=anchor("수요를 근거로"),
        comparison_baseline=anchor("전월비"),
        target_scopes=[scope("동부"), scope("청년", "population")],
        value_status="forecast",
        status_evidence_sentence_id="s1",
        reporting_tense="past",
        reporting_tense_text=anchor("발표했다"),
    )
    return src, row


def test_separate_roles_scopes_whole_status_and_receipts():
    api = sdk()
    src, row = rich()
    result = run(src, [row])
    assert (result.profile, result.status) == ("measurement-frame-generation-v1", "unreviewed")
    assert (result.frame.profile, result.frame.status) == (
        "measurement-scope-frame-v1",
        "unreviewed",
    )
    got = result.frame.frame.resolved.facts[0]
    assert [getattr(got, r).span.text for r in ROLES] == [
        "이용자",
        "발표처",
        "내년",
        "조건 충족 시",
        "수요를 근거로",
        "전월비",
        "발표했다",
    ]
    assert got.status_text.span.text == src[1].citations[0].selector.quote
    assert result.frame.input.facts[0].status_text.model_dump() == {
        "sentence_id": "s1",
        "text": src[1].citations[0].selector.quote,
        "context_text": None,
    }
    assert [(s.kind, s.anchor.span.text) for s in result.frame.scopes[0].target_scopes] == [
        ("geographic", "동부"),
        ("population", "청년"),
    ]
    assert result.prompt_sha256 == sha256(api.measurement_frame_prompt(src).encode()).hexdigest()
    assert (
        result.instructions_sha256
        == sha256(api.MEASUREMENT_FRAME_INSTRUCTIONS.encode()).hexdigest()
    )
    assert result.usage.model_dump() == {"input_tokens": 100, "output_tokens": 30, "requests": 1}
    assert api.validate_measurement_frame_generation(src, result) == result
    assert (
        api.validate_measurement_frame_generation(src, json.loads(result.model_dump_json()))
        == result
    )


@pytest.mark.parametrize("status", ["observed", "planned", "forecast", "unknown"])
@pytest.mark.parametrize("tense", ["past", "present", "future", "unknown"])
def test_known_and_unknown_combinations_and_nullable_reporter(status, tense):
    row = fact(
        value_status=status,
        status_evidence_sentence_id="s1",
        reporting_tense=tense,
        reporting_tense_text=anchor("발표") if tense != "unknown" else None,
    )
    result = run(document("운영기관 방문 10건 발표."), [row])
    got = result.frame.frame.resolved.facts[0]
    assert (
        got.reporting_actor is None and got.value_status == status and got.reporting_tense == tense
    )
    assert got.status_text.span.text == "운영기관 방문 10건 발표."
    assert run(document("A 10"), [fact()]).frame.input.facts[0].status_text is None


def test_repeated_contexts_and_direct_relation():
    src = document("동부 이용자 100명 중 서부 이용자 20명 포함.")
    rows = [
        fact(measured_entity=anchor("이용자", "동부 이용자"), target_scopes=[scope("동부")]),
        fact("n2", measured_entity=anchor("이용자", "서부 이용자"), target_scopes=[scope("서부")]),
    ]
    rel = dict(
        from_id="n2",
        to_id="n1",
        kind="included_in",
        statement_sentence_ids=["s1"],
        cue=anchor("포함"),
    )
    result = run(src, rows, [rel])
    assert [f.measured_entity.span.start for f in result.frame.frame.resolved.facts] == [3, 17]
    assert result.frame.frame.resolved.relations[0].from_id == "n2"
    assert run(src).frame.scopes == ()


def test_prompt_preserves_whole_source_catalogues_and_only_eligible_numeric_sentences():
    api = sdk()
    src = document("발표했다. 🧪 A 10명. B 20명.", "C 30명.")
    packet = json.loads(api.measurement_frame_prompt(src))
    assert packet["profile"] == "measurement-frame-generation-v1"
    assert [s["text"] for s in packet["sentences"]] == [
        "발표했다.",
        " 🧪 A 10명.",
        " B 20명.",
        "C 30명.",
    ]
    assert packet["eligible_status_sentence_ids"] == ["s2", "s3", "s4"]
    assert [c["quote"] for c in packet["source"]["citations"]] == [
        "발표했다. 🧪 A 10명. B 20명.",
        "C 30명.",
    ]
    assert [c["id"] for c in packet["candidates"]] == ["n1", "n2", "n3"]


def test_dynamic_schema_required_roles_scopes_status_and_tense():
    api = sdk()
    _, tools = api._preflight(document("A 10. B 20."))
    assert len(tools) == 1 and tools[0].name == "fill_measurement_frame_v1" and tools[0].strict
    schema = tools[0].output.model_json_schema()
    defs = schema["$defs"]
    variants = [d for d in defs.values() if "value_status" in d.get("properties", {})]
    assert len(variants) == 4
    for v in variants:
        p = v["properties"]
        assert set(v["required"]) == {
            "candidate_id",
            *ROLES,
            "target_scopes",
            "value_status",
            "reporting_tense",
            "status_evidence_sentence_id",
        }
        assert "status_text" not in p
        assert p["target_scopes"]["maxItems"] == 4
        assert p["candidate_id"]["enum"] == ["n1", "n2"]
        status = p["status_evidence_sentence_id"]
        unknown = p["value_status"].get("const") == "unknown"
        assert ("anyOf" in status) == unknown
        assert (status["anyOf"][0] if unknown else status)["enum"] == ["s1", "s2"]
        assert ("anyOf" in p["reporting_tense_text"]) == (
            p["reporting_tense"].get("const") == "unknown"
        )
    assert schema["properties"]["facts"]["maxItems"] == 12
    assert schema["properties"]["relations"]["maxItems"] == 16
    rel = next(v for v in defs.values() if "from_id" in v.get("properties", {}))
    statement = rel["properties"]["statement_sentence_ids"]
    assert statement["maxItems"] == 20 and statement["minItems"] == 1
    assert statement["items"]["enum"] == ["s1", "s2"]
    anchor_def = defs["MeasurementAnchorV1"]["properties"]
    assert anchor_def["sentence_id"]["enum"] == ["s1", "s2"]
    assert anchor_def["text"]["maxLength"] == 1000
    assert schema["additionalProperties"] is False
    assert all(v["additionalProperties"] is False for v in variants)
    scope_def = next(
        v
        for v in defs.values()
        if "kind" in v.get("properties", {}) and "anchor" in v["properties"]
    )
    assert scope_def["properties"]["kind"] == {"$ref": "#/$defs/ScopeKind"}
    assert defs["ScopeKind"]["enum"] == ["geographic", "population", "institutional", "other"]


@pytest.mark.parametrize("length", [1000, 1001])
def test_status_sentence_codepoint_boundary_and_empty_eligible_schema(length):
    api = sdk()
    src = document("🧪" + "x" * (length - 4) + " 10")
    packet = json.loads(api.measurement_frame_prompt(src))
    assert packet["eligible_status_sentence_ids"] == (["s1"] if length == 1000 else [])
    _, tools = api._preflight(src)
    schema = tools[0].output.model_json_schema()
    assert '"enum": []' not in json.dumps(schema)
    if length == 1000:
        assert (
            len(
                run(src, [fact(value_status="observed", status_evidence_sentence_id="s1")])
                .frame.input.facts[0]
                .status_text.text
            )
            == 1000
        )
    else:
        assert run(src, [fact()]).frame.input.facts[0].status_text is None
        variants = [
            v for v in schema["$defs"].values() if "value_status" in v.get("properties", {})
        ]
        assert len(variants) == 2
        assert all(v["properties"]["value_status"]["const"] == "unknown" for v in variants)
        assert all(
            v["properties"]["status_evidence_sentence_id"]["type"] == "null" for v in variants
        )


@pytest.mark.parametrize(
    "change",
    [
        "same-quote",
        "cross-quote",
        "nonnumeric",
        "stale",
        "known-null",
        "known-tense-null",
        "status_text",
        "scope-cap",
        "facts-cap",
        "relations-cap",
        "missing-scope",
        "missing-role",
        "extra",
    ],
)
def test_bad_provider_selection_rejects_once_with_usage(change):
    api = sdk()
    src = document("A 10. B 20. 발표했다.", "C 30.")
    row = fact(value_status="observed", status_evidence_sentence_id="s1")
    rows, rels = [row], []
    if change in {"same-quote", "cross-quote", "nonnumeric", "stale"}:
        row["status_evidence_sentence_id"] = {
            "same-quote": "s2",
            "cross-quote": "s4",
            "nonnumeric": "s3",
            "stale": "s99",
        }[change]
    elif change == "known-null":
        row["status_evidence_sentence_id"] = None
    elif change == "known-tense-null":
        row["reporting_tense"] = "past"
    elif change == "status_text":
        row["status_text"] = anchor("발표했다", sentence="s3")
    elif change == "scope-cap":
        row["target_scopes"] = [scope("A")] * 5
    elif change == "facts-cap":
        rows *= 13
    elif change == "relations-cap":
        rels = [
            dict(
                from_id="n1",
                to_id="n2",
                kind="parallel",
                statement_sentence_ids=["s1"],
                cue=anchor("A"),
            )
        ] * 17
    elif change == "missing-scope":
        del row["target_scopes"]
    elif change == "missing-role":
        del row["reporting_actor"]
    else:
        row["verified"] = True
    model, calls = response({"facts": rows, "relations": rels})
    with pytest.raises(
        api.MeasurementFrameGenerationError, match="^Measurement frame generation failed$"
    ) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), src)
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100
    assert error.value.__cause__ is None


@pytest.mark.parametrize(
    "node", ["root", "fact", "scope", "scope-anchor", "anchor", "relation", "cue"]
)
@pytest.mark.parametrize("attack", ["dict", "hidden", "extra", "construct"])
def test_actual_dynamic_nodes_checked_before_serialization(monkeypatch, node, attack):
    api = sdk()
    original = api._runtime.Agent.run_sync
    serialized = []

    def changed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        output = result.output
        row, rel = output.facts[0], output.relations[0]
        target = {
            "root": output,
            "fact": row,
            "scope": row.target_scopes[0],
            "scope-anchor": row.target_scopes[0].anchor,
            "anchor": row.measured_entity,
            "relation": rel,
            "cue": rel.cue,
        }[node]
        if attack == "dict":
            altered = target.model_dump(mode="json")
        elif attack == "hidden":
            cls = create_model(
                "HiddenMeasurementNode", __base__=type(target), secret=(str, Field(exclude=True))
            )
            altered = cls(**target.model_dump(), secret="hidden")
        elif attack == "extra":
            altered = target.model_copy(update={"verified": True})
        else:
            fields = {**target.__dict__, "verified": True}
            altered = type(target).model_construct(**fields)
            # model_construct(extra=forbid) drops unknown args; a forged live field must reject.
            altered.__dict__["verified"] = True
        if node == "root":
            output = altered
        else:
            if node == "fact":
                row = altered
            elif node == "scope":
                row = row.model_copy(update={"target_scopes": (altered,)})
            elif node == "scope-anchor":
                row = row.model_copy(
                    update={
                        "target_scopes": (
                            row.target_scopes[0].model_copy(update={"anchor": altered}),
                        )
                    }
                )
            elif node == "anchor":
                row = row.model_copy(update={"measured_entity": altered})
            elif node == "relation":
                rel = altered
            else:
                rel = rel.model_copy(update={"cue": altered})
            output = output.model_copy(
                update={"facts": (row, output.facts[1]), "relations": (rel,)}
            )
        # A canonical-type gate must reject without invoking a malicious serializer.
        if isinstance(output, BaseModel):

            def forbidden(*args, **kwargs):
                serialized.append(True)
                raise AssertionError("Serialization preceded canonical node checks")

            monkeypatch.setattr(type(output), "model_dump_json", forbidden)
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api._runtime.Agent, "run_sync", changed)
    rows = [
        fact(measured_entity=anchor("A"), target_scopes=[scope("A", "other")]),
        fact("n2", measured_entity=anchor("B")),
    ]
    rel = dict(
        from_id="n2",
        to_id="n1",
        kind="included_in",
        statement_sentence_ids=["s1"],
        cue=anchor("중"),
    )
    model, calls = response({"facts": rows, "relations": [rel]})
    with pytest.raises(api.MeasurementFrameGenerationError) as error:
        api.run_measurement_framer(
            api.create_measurement_framer(model), document("A 10명 중 B 2명.")
        )
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100
    assert serialized == []


@pytest.mark.parametrize("node", ["anchor", "scope", "scope-anchor", "relation", "cue"])
def test_canonical_base_node_cannot_replace_exact_dynamic_type(monkeypatch, node):
    api = sdk()
    from issuedigest_agents.contextual_anchor import ContextualAnchor
    from issuedigest_agents.contextual_frame import ContextualFrameRelationInput
    from issuedigest_agents.measurement_scope import MeasurementScopeInput

    original = api._runtime.Agent.run_sync

    def changed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        output = result.output
        row, rel = output.facts[0], output.relations[0]
        target = {
            "anchor": row.measured_entity,
            "scope": row.target_scopes[0],
            "scope-anchor": row.target_scopes[0].anchor,
            "relation": rel,
            "cue": rel.cue,
        }[node]
        cls = (
            MeasurementScopeInput
            if node == "scope"
            else ContextualFrameRelationInput
            if node == "relation"
            else ContextualAnchor
        )
        target = cls.model_validate_json(target.model_dump_json())
        if node == "anchor":
            row = row.model_copy(update={"measured_entity": target})
        elif node == "scope":
            row = row.model_copy(update={"target_scopes": (target,)})
        elif node == "scope-anchor":
            row = row.model_copy(
                update={
                    "target_scopes": (row.target_scopes[0].model_copy(update={"anchor": target}),)
                }
            )
        elif node == "relation":
            rel = target
        else:
            rel = rel.model_copy(update={"cue": target})
        return SimpleNamespace(
            output=output.model_copy(update={"facts": (row, output.facts[1]), "relations": (rel,)}),
            usage=result.usage,
            new_messages=result.new_messages,
        )

    monkeypatch.setattr(api._runtime.Agent, "run_sync", changed)
    rows = [
        fact(measured_entity=anchor("A"), target_scopes=[scope("A", "other")]),
        fact("n2", measured_entity=anchor("B")),
    ]
    model, calls = response(
        {
            "facts": rows,
            "relations": [
                dict(
                    from_id="n2",
                    to_id="n1",
                    kind="included_in",
                    statement_sentence_ids=["s1"],
                    cue=anchor("중"),
                )
            ],
        }
    )
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.run_measurement_framer(
            api.create_measurement_framer(model), document("A 10명 중 B 2명.")
        )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "prompt",
        "instructions",
        "profile",
        "status",
        "usage-requests",
        "usage-total",
        "usage-output",
        "extra",
        "hidden",
        "frame-profile",
        "frame-status",
        "input",
        "scopes",
        "resolved",
        "source",
        "whole-status",
    ],
)
def test_validator_rebuilds_all_receipts_and_wrapper_fields(mutation):
    api = sdk()
    src, row = rich()
    result = run(src, [row])
    raw = result.model_dump(mode="json")
    if mutation in {"prompt", "instructions"}:
        raw[mutation + "_sha256"] = "0" * 64
    elif mutation in {"profile", "status"}:
        raw[mutation] = "other"
    elif mutation == "usage-requests":
        raw["usage"]["requests"] = 2
    elif mutation == "usage-total":
        raw["usage"]["input_tokens"] = 20000
    elif mutation == "usage-output":
        raw["usage"]["output_tokens"] = 2501
    elif mutation == "extra":
        raw = result.model_copy(update={"verified": True})
    elif mutation == "hidden":
        cls = create_model(
            "HiddenReceipt",
            __base__=type(result.frame.input.facts[0]),
            secret=(str, Field(exclude=True)),
        )
        widened = cls(**result.frame.input.facts[0].model_dump(), secret="hidden")
        raw = result.model_copy(
            update={
                "frame": result.frame.model_copy(
                    update={"input": result.frame.input.model_copy(update={"facts": (widened,)})}
                )
            }
        )
    elif mutation == "frame-profile":
        raw["frame"]["profile"] = "other"
    elif mutation == "frame-status":
        raw["frame"]["status"] = "reviewed"
    elif mutation == "input":
        raw["frame"]["input"]["facts"][0]["target_scopes"] = []
    elif mutation == "scopes":
        raw["frame"]["scopes"][0]["target_scopes"][0]["kind"] = "other"
    elif mutation == "resolved":
        raw["frame"]["frame"]["resolved"]["facts"][0]["measured_entity"]["span"]["start"] += 1
    elif mutation == "source":
        src = document("수정된 대상 10명.")
    else:
        # Even a fully self-consistent pure wrapper cannot smuggle substring status evidence.
        data = result.frame.input.model_dump(mode="json")
        data["facts"][0]["status_text"] = anchor("전망")
        raw = result.model_copy(update={"frame": api.build_measurement_scope_frame(src, data)})
    with pytest.raises(
        api.MeasurementFrameGenerationError, match="^Invalid measurement frame generation$"
    ):
        api.validate_measurement_frame_generation(src, raw)


@pytest.mark.parametrize(
    "mutation",
    [
        "requests-zero",
        "requests-two",
        "requests-bool",
        "aggregate",
        "raw-bool",
        "missing-response",
        "overflow",
    ],
)
def test_runtime_usage_forgeries_fail_and_preserve_observed_usage(monkeypatch, mutation):
    api = sdk()
    original = api._runtime.Agent.run_sync

    def changed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        messages = result.new_messages()
        raw = next(m for m in messages if isinstance(m, ModelResponse))
        if mutation.startswith("requests-"):
            result.usage.requests = {"requests-zero": 0, "requests-two": 2, "requests-bool": True}[
                mutation
            ]
        elif mutation == "aggregate":
            result.usage.input_tokens += 1
        elif mutation == "raw-bool":
            raw.usage.input_tokens = True
        elif mutation == "missing-response":
            messages = []
        else:
            raw.usage.input_tokens = result.usage.input_tokens = 21000
            raw.usage.output_tokens = result.usage.output_tokens = 2600
        return SimpleNamespace(
            output=result.output, usage=result.usage, new_messages=lambda: messages
        )

    monkeypatch.setattr(api._runtime.Agent, "run_sync", changed)
    model, calls = response({"facts": [], "relations": []})
    with pytest.raises(api.MeasurementFrameGenerationError) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), document("A 10"))
    assert len(calls) == 1
    if mutation == "raw-bool":
        assert error.value.known_usage is None
    else:
        assert error.value.known_usage.model_dump() == {
            "input_tokens": 21000 if mutation == "overflow" else 100,
            "output_tokens": 2600 if mutation == "overflow" else 30,
            "requests": 1,
        }


@pytest.mark.parametrize("inputs,outputs", [(17500, 2500), (20000, 0)])
def test_actual_inclusive_usage_caps(inputs, outputs):
    assert run(document("A 10"), inputs=inputs, outputs=outputs).usage.input_tokens == inputs


@pytest.mark.parametrize("inputs,outputs", [(17501, 2500), (100, 2501), (20001, 0)])
def test_actual_overflow_not_free_when_sdk_discards_capture(inputs, outputs):
    api = sdk()
    model, calls = response({"facts": [], "relations": []}, inputs=inputs, outputs=outputs)
    with pytest.raises(api.MeasurementFrameGenerationError) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), document("A 10"))
    assert len(calls) == 1 and error.value.known_usage is None


@pytest.mark.parametrize(
    "options,known", [({"error": TimeoutError("secret")}, False), ({"text": True}, True)]
)
def test_timeout_and_freeform_failure_no_retry(options, known):
    api = sdk()
    model, calls = response({}, **options)
    with pytest.raises(
        api.MeasurementFrameGenerationError, match="^Measurement frame generation failed$"
    ) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), document("A 10"))
    assert len(calls) == 1 and (error.value.known_usage is not None) == known


def test_shared_runtime_identity_limits_settings_and_caller_lifecycle(monkeypatch):
    api = sdk()
    original_init, original_run = api._runtime.Agent.__init__, api._runtime.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_measurement_frame_v1"
        assert kwargs["instructions"] == api.MEASUREMENT_FRAME_INSTRUCTIONS
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
        assert kwargs["model_settings"] == {
            "openai_store": False,
            "max_tokens": 2500,
            "timeout": 30,
        }
        return original_run(self, *args, **kwargs)

    def forbidden(*args, **kwargs):
        raise AssertionError("Caller owns lifecycle")

    monkeypatch.setattr(api._runtime.Agent, "__init__", initialized)
    monkeypatch.setattr(api._runtime.Agent, "run_sync", called)
    model, calls = response({"facts": [], "relations": []})
    monkeypatch.setattr(model, "__aenter__", forbidden)
    monkeypatch.setattr(model, "__aexit__", forbidden)
    framer = api.create_measurement_framer(model)
    with pytest.raises(FrozenInstanceError):
        framer.model = model
    assert calls == []
    assert api.run_measurement_framer(framer, document("A 10")).frame.scopes == ()
    with pytest.raises(TypeError):
        api.create_measurement_framer()
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.create_measurement_framer("openai:fake")
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.run_measurement_framer(SimpleNamespace(model=model), document("A 10"))


@pytest.mark.parametrize("schema_sizes", [None, (111, 999), (999, 111)])
def test_actual_utf8_envelope_inclusive_max_raw_normalized(monkeypatch, schema_sizes):
    api = sdk()
    src = document("🧪 A 10명")
    result = run(src)
    if schema_sizes:
        monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: schema_sizes)
    prompt, tools = api._preflight(src)
    exact = (
        len(prompt.encode())
        + len(api.MEASUREMENT_FRAME_INSTRUCTIONS.encode())
        + max(api._provider_schema_bytes_v5(tools))
        + 2048
        + 2500
    )
    assert len(prompt.encode()) > len(prompt)
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact)
    assert run(src).frame.scopes == ()
    assert api.validate_measurement_frame_generation(src, result) == result
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact - 1)
    model, calls = response({})
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.measurement_frame_prompt(src)
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.validate_measurement_frame_generation(src, result)
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.run_measurement_framer(api.create_measurement_framer(model), src)
    assert calls == []


@pytest.mark.parametrize("bad", ["empty", "large", "hidden-source"])
def test_bad_source_preflight_never_calls_model(bad):
    api = sdk()
    src = document("A 10")
    if bad == "empty":
        src = document("No numbers.")
    elif bad == "large":
        src = document(" ".join("1명" for _ in range(256)))
    else:
        original = src[1].representation
        cls = create_model(
            "HiddenSource", __base__=type(original), secret=(str, Field(exclude=True))
        )
        src = (
            src[0],
            src[1].model_copy(
                update={"representation": cls(**original.model_dump(), secret="secret")}
            ),
            src[2],
        )
    model, calls = response({})
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.measurement_frame_prompt(src)
    with pytest.raises(api.MeasurementFrameGenerationError):
        api.run_measurement_framer(api.create_measurement_framer(model), src)
    assert calls == []


@pytest.mark.parametrize("changed", ["source", "instructions"])
def test_request_drift_cannot_certify_current_input(monkeypatch, changed):
    api = sdk()
    src = document("A 10")

    def mutate(messages, info):
        if changed == "source":
            src[1].citations[0].selector.__dict__["quote"] = "B 10"
        else:
            monkeypatch.setattr(
                api,
                "MEASUREMENT_FRAME_INSTRUCTIONS",
                api.MEASUREMENT_FRAME_INSTRUCTIONS + " changed",
            )

    model, calls = response({"facts": [], "relations": []}, inspect=mutate)
    with pytest.raises(api.MeasurementFrameGenerationError) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), src)
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100


def test_cold_import_prompt_create_validate_without_keys_clients_files_or_network():
    sdk()
    code = """
import builtins, importlib, io, os, socket
from hashlib import sha256
import openai, pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
src = document("A A 10")
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
api = importlib.import_module("issuedigest_agents.measurement_frame_generation")
api.create_measurement_framer(model)
prompt = api.measurement_frame_prompt(src)
data = {"facts": [], "relations": []}
result = api.MeasurementFrameGeneration(
    frame=api.build_measurement_scope_frame(src, data),
    prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.MEASUREMENT_FRAME_INSTRUCTIONS.encode()).hexdigest(),
    usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1),
)
assert api.validate_measurement_frame_generation(src, result) == result
try: api.validate_measurement_frame_generation(src, {})
except api.MeasurementFrameGenerationError as error: assert error.known_usage is None
else: raise AssertionError("Invalid result accepted")
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("profile", ["contextual", "scoped_contextual"])
def test_both_frozen_pre_refactor_wires_and_results_stay_identical(monkeypatch, profile):
    from uuid import UUID

    from issuedigest_domain import EvidenceBundle
    from issuedigest_domain.research_journey import SourcePresentation
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    sdk()
    api = importlib.import_module(
        "issuedigest_agents."
        + (
            "contextual_frame_generation"
            if profile == "contextual"
            else "scoped_contextual_generation"
        )
    )
    frozen = json.loads(
        (
            Path(__file__).parent
            / "fixtures"
            / (
                "contextual-frame-v1-wire.json"
                if profile == "contextual"
                else "scoped-contextual-v1-wire.json"
            )
        ).read_bytes()
    )
    raw = frozen["source"]
    src = (
        UUID(raw["snapshot_id"]),
        EvidenceBundle.model_validate_json(json.dumps(raw["bundle"])),
        SourcePresentation.model_validate_json(json.dumps(raw["presentation"])),
    )
    instructions = (
        api.CONTEXTUAL_FRAME_INSTRUCTIONS
        if profile == "contextual"
        else api.SCOPED_CONTEXTUAL_INSTRUCTIONS
    )
    prompt = (
        api.contextual_frame_prompt
        if profile == "contextual"
        else api.scoped_contextual_frame_prompt
    )
    create = (
        api.create_contextual_framer
        if profile == "contextual"
        else api.create_scoped_contextual_framer
    )
    execute = (
        api.run_contextual_framer if profile == "contextual" else api.run_scoped_contextual_framer
    )
    runtime = api if profile == "contextual" else api._v1
    assert instructions == frozen["instructions"]
    assert api.PROVIDER_IDENTITY == frozen["provider_identity"]
    assert prompt(src) == frozen["prompt"]
    _, tools = api._preflight(src)
    raw_tools, normalized_tools = [], []
    for tool in tools:
        schema = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
        envelope = dict(
            type="function",
            name=tool.name,
            description=tool.description,
            strict=tool.strict,
            parameters=schema,
        )
        raw_tools.append(envelope)
        normalized_tools.append(
            {**envelope, "parameters": OpenAIJsonSchemaTransformer(schema, strict=True).walk()}
        )
    assert raw_tools == frozen["raw_tools"] and normalized_tools == frozen["normalized_tools"]
    original_init, original_run = runtime.Agent.__init__, runtime.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == frozen["provider_identity"]
        assert kwargs["instructions"] == frozen["instructions"]
        assert kwargs["retries"] == frozen["agent_retries"]
        return original_init(self, *args, **kwargs)

    def called(self, request_prompt, **kwargs):
        assert request_prompt == frozen["prompt"]
        assert kwargs["model_settings"] == frozen["settings"]
        assert {k: getattr(kwargs["usage_limits"], k) for k in frozen["limits"]} == frozen["limits"]
        assert kwargs["retries"] == frozen["run_retries"]
        return original_run(self, request_prompt, **kwargs)

    def respond(messages, info):
        return ModelResponse(
            parts=[ToolCallPart(tools[0].name, '{"facts":[],"relations":[]}')],
            usage=RequestUsage(input_tokens=111, output_tokens=22),
        )

    monkeypatch.setattr(runtime.Agent, "__init__", initialized)
    monkeypatch.setattr(runtime.Agent, "run_sync", called)
    assert execute(create(FunctionModel(respond)), src).model_dump(mode="json") == frozen["result"]


def test_all_four_scope_kinds_and_structurally_wrong_meaning_remain_unreviewed():
    result = run(
        document("운영처 동부 청년 기관군 기타 이용자 10명."),
        [
            fact(
                measured_entity=anchor("이용자"),
                target_scopes=[
                    scope("동부"),
                    scope("청년", "population"),
                    scope("기관군", "institutional"),
                    scope("기타", "other"),
                ],
                value_status="planned",
                status_evidence_sentence_id="s1",
            )
        ],
    )
    assert [s.kind for s in result.frame.scopes[0].target_scopes] == [
        "geographic",
        "population",
        "institutional",
        "other",
    ]
    assert result.frame.frame.resolved.facts[0].reporting_actor is None
    # A sentence with a number but no asserted planned predicate is still exact context.
    assert result.frame.frame.resolved.facts[0].value_status == "planned"
    assert result.status == result.frame.status == result.frame.frame.status == "unreviewed"


@pytest.mark.parametrize(
    "change",
    ["known-null", "wrong-candidate", "extra-status", "scope-kind", "missing-role", "bool-id"],
)
def test_constructed_exact_dynamic_models_still_require_strict_revalidation(monkeypatch, change):
    api = sdk()
    original = api._runtime.Agent.run_sync

    def changed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        row = result.output.facts[0]
        fields = dict(row.__dict__)
        if change == "known-null":
            fields.update(value_status="observed")
        elif change == "wrong-candidate":
            fields.update(status_evidence_sentence_id="s2")
        elif change == "extra-status":
            fields["status_text"] = anchor("A")
        elif change == "scope-kind":
            fields["target_scopes"] = (
                row.target_scopes[0].model_copy(update={"kind": "fabricated"}),
            )
        elif change == "missing-role":
            del fields["reporting_actor"]
        else:
            fields["candidate_id"] = True
        forged = type(row).model_construct(**fields)
        if change == "extra-status":
            forged.__dict__["status_text"] = anchor("A")
        output = result.output.model_copy(update={"facts": (forged,)})
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api._runtime.Agent, "run_sync", changed)
    model, calls = response({"facts": [fact(target_scopes=[scope("A", "other")])], "relations": []})
    with pytest.raises(api.MeasurementFrameGenerationError) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), document("A 10. B 20."))
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100


@pytest.mark.parametrize(
    "status,selected", [("observed", None), ("forecast", "s1"), ("unknown", "s1")]
)
def test_empty_eligibility_rejects_any_known_status_or_nonnull_evidence(status, selected):
    api = sdk()
    src = document("x" * 998 + " 10")
    row = fact(value_status=status, status_evidence_sentence_id=selected)
    model, calls = response({"facts": [row], "relations": []})
    with pytest.raises(api.MeasurementFrameGenerationError) as error:
        api.run_measurement_framer(api.create_measurement_framer(model), src)
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100
