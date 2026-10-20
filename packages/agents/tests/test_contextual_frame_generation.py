"""Synthetic one-request frame generation; exact structure never certifies semantics."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from hashlib import sha256
from types import SimpleNamespace

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import Field, create_model
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_contextual_frame import anchor as contextual_anchor
from test_contextual_frame import relation
from test_numeric_evidence import document


def anchor(text, sentence_id="s1"):
    return contextual_anchor(text, sentence=sentence_id)


ROLES = (
    "measured_entity",
    "reporting_actor",
    "period",
    "logical_condition",
    "forecast_basis",
    "comparison_baseline",
    "status_text",
    "reporting_tense_text",
)


@pytest.fixture(autouse=True)
def own_model_loop(sync_model_loop):
    yield


@pytest.fixture(scope="module", autouse=True)
def restore_new_module_imports():
    names = (
        "issuedigest_agents.contextual_frame_generation",
        "issuedigest_agents.contextual_frame",
        "issuedigest_agents.contextual_anchor",
        "issuedigest_agents.numeric_frame",
        "issuedigest_agents.numeric_frame_generation",
        "issuedigest_agents.numeric_selection",
        "issuedigest_agents.numeric_selection_evaluation",
    )
    introduced = [name for name in names if name not in sys.modules]
    yield
    for name in introduced:
        sys.modules.pop(name, None)


def sdk():
    name = "issuedigest_agents.contextual_frame_generation"
    assert importlib.util.find_spec(name) is not None, "Missing contextual frame generation SDK"
    return importlib.import_module(name)


def fact(candidate="n1", **fields):
    return {
        "candidate_id": candidate,
        **dict.fromkeys(ROLES),
        "value_status": "unknown",
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
            else [ToolCallPart("fill_contextual_frame_v1", json.dumps(output))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def run(src, facts=(), relations=(), **options):
    api = sdk()
    model, calls = response({"facts": list(facts), "relations": list(relations)}, **options)
    result = api.run_contextual_framer(api.create_contextual_framer(model), src)
    assert len(calls) == 1
    return result


def rich():
    src = document(
        "🧪 기관은 수요 증가를 근거로 내년 조건 충족 시 취업자 전월비 10명 증가 전망을 발표했다."
    )
    row = fact(
        measured_entity=anchor("취업자"),
        reporting_actor=anchor("기관"),
        period=anchor("내년"),
        logical_condition=anchor("조건 충족 시"),
        forecast_basis=anchor("수요 증가를 근거로"),
        comparison_baseline=anchor("전월비"),
        value_status="forecast",
        status_text=anchor("전망"),
        reporting_tense="past",
        reporting_tense_text=anchor("발표했다"),
    )
    return src, row


def test_whole_prompt_reuses_candidate_representation_with_distinct_profile():
    api = sdk()
    from issuedigest_agents.numeric_candidates import build_numeric_candidates
    from issuedigest_agents.numeric_selection import _prompt

    src = document("🧪 A 9만 9000명 이상. B 1~2호. C 1호~2호.", "D 7")
    packet = json.loads(api.contextual_frame_prompt(src))
    expected = json.loads(_prompt(src, build_numeric_candidates(src)))
    expected["profile"] = "contextual-frame-generation-v1"
    assert packet == expected
    assert [c["expression"] for c in packet["candidates"]] == [
        "9만 9000명 이상",
        "1~2호",
        "1호~2호",
        "7",
    ]


def test_function_model_separates_all_roles_reconstructs_and_records_current_receipts():
    api = sdk()
    src, row = rich()

    def inspect(messages, info):
        assert len(info.output_tools) == 1
        tool = info.output_tools[0]
        assert tool.name == "fill_contextual_frame_v1" and tool.strict is True
        assert info.model_settings["openai_store"] is False
        assert info.model_settings["max_tokens"] == 2500
        assert info.model_settings["timeout"] == 30
        assert api.CONTEXTUAL_FRAME_INSTRUCTIONS in str(messages)
        assert api.contextual_frame_prompt(src) in str(messages)

    result = run(src, [row], inspect=inspect)
    assert (result.profile, result.status) == ("contextual-frame-generation-v1", "unreviewed")
    assert (result.frame.profile, result.frame.status) == (
        "numeric-contextual-frame-v1",
        "unreviewed",
    )
    resolved = result.frame.resolved.facts[0]
    assert {role: getattr(resolved, role).span.text for role in ROLES} == {
        "measured_entity": "취업자",
        "reporting_actor": "기관",
        "period": "내년",
        "logical_condition": "조건 충족 시",
        "forecast_basis": "수요 증가를 근거로",
        "comparison_baseline": "전월비",
        "status_text": "전망",
        "reporting_tense_text": "발표했다",
    }
    assert (resolved.value_status, resolved.reporting_tense) == ("forecast", "past")
    assert (resolved.reporting_actor.span.start, resolved.reporting_actor.span.end) == (2, 4)
    assert result.prompt_sha256 == sha256(api.contextual_frame_prompt(src).encode()).hexdigest()
    assert (
        result.instructions_sha256 == sha256(api.CONTEXTUAL_FRAME_INSTRUCTIONS.encode()).hexdigest()
    )
    assert result.usage.model_dump() == {"input_tokens": 100, "output_tokens": 30, "requests": 1}
    assert api.validate_contextual_frame_generation(src, result) == result
    assert api.validate_contextual_frame_generation(src, result.model_dump(mode="json")) == result


@pytest.mark.parametrize(
    "value_status,status_text", [("unknown", None), ("planned", "계획"), ("observed", "관측")]
)
@pytest.mark.parametrize("tense,tense_text", [("unknown", None), ("past", "발표했다")])
def test_known_and_unknown_status_tense_and_distinct_actor_positive(
    value_status, status_text, tense, tense_text
):
    row = fact(
        measured_entity=anchor("취업자"),
        reporting_actor=anchor("기관"),
        value_status=value_status,
        status_text=anchor(status_text) if status_text else None,
        reporting_tense=tense,
        reporting_tense_text=anchor(tense_text) if tense_text else None,
    )
    result = run(document("기관 취업자 10명 관측 및 계획을 발표했다."), [row])
    assert result.frame.resolved.facts[0].value_status == value_status
    assert result.frame.resolved.facts[0].reporting_tense == tense
    assert (
        result.frame.resolved.facts[0].measured_entity
        != result.frame.resolved.facts[0].reporting_actor
    )


def test_direct_subgroup_relation_and_empty_selection_are_preserved():
    src = document("전체 100명 중 소계 40명 중 하위 10명 포함.")
    rows = [
        fact("n1", measured_entity=anchor("전체")),
        fact("n2", measured_entity=anchor("소계")),
        fact("n3", measured_entity=anchor("하위")),
    ]
    result = run(src, rows, [relation("n3", "n2", cue=anchor("포함"))])
    assert [(r.from_id, r.to_id) for r in result.frame.resolved.relations] == [("n3", "n2")]
    assert (
        result.frame.resolved.relations[0].statement.text
        == "전체 100명 중 소계 40명 중 하위 10명 포함."
    )
    empty = run(src)
    assert (empty.frame.resolved.facts, empty.frame.resolved.relations) == ((), ())


def test_source_bound_schema_requires_anchors_for_known_status_and_tense():
    api = sdk()
    _, tools = api._preflight(document("A 10. B 20."))
    schema = tools[0].output.model_json_schema()
    defs = schema["$defs"]
    facts = [d for d in defs.values() if "value_status" in d.get("properties", {})]
    assert len(facts) == 4
    for variant in facts:
        props = variant["properties"]
        assert props["candidate_id"]["enum"] == ["n1", "n2"]
        assert set(variant["required"]) == {
            "candidate_id",
            "value_status",
            "reporting_tense",
            *ROLES,
        }
        status_unknown = props["value_status"].get("const") == "unknown"
        tense_unknown = props["reporting_tense"].get("const") == "unknown"
        assert ("anyOf" in props["status_text"]) == status_unknown
        assert ("anyOf" in props["reporting_tense_text"]) == tense_unknown
    anchor_def = next(d for d in defs.values() if "text" in d.get("properties", {}))
    assert anchor_def["properties"]["sentence_id"]["enum"] == ["s1", "s2"]
    assert anchor_def["properties"]["text"]["maxLength"] == 1000
    relation_def = next(d for d in defs.values() if "from_id" in d.get("properties", {}))
    assert relation_def["properties"]["from_id"]["enum"] == ["n1", "n2"]
    assert relation_def["properties"]["to_id"]["enum"] == ["n1", "n2"]
    assert relation_def["properties"]["statement_sentence_ids"]["items"]["enum"] == ["s1", "s2"]


@pytest.mark.parametrize(
    "mutation",
    [
        "known-status-null",
        "known-tense-null",
        "stale-id",
        "stale-sentence",
        "rewrite",
        "duplicate",
        "ambiguous",
        "different-quote",
        "cross-sentence",
        "nonexact",
        "long",
        "relation",
    ],
)
def test_invalid_output_rejected_once_without_repair_and_keeps_usage(mutation):
    api = sdk()
    src = document("A A 10. B 20.", "C 30.")
    row = fact()
    rels = []
    if mutation == "known-status-null":
        row["value_status"] = "observed"
    elif mutation == "known-tense-null":
        row["reporting_tense"] = "past"
    elif mutation == "stale-id":
        row["candidate_id"] = "n99"
    elif mutation == "stale-sentence":
        row["period"] = anchor("A", "s99")
    elif mutation == "rewrite":
        row["value"] = 10
    elif mutation in {"ambiguous", "different-quote", "cross-sentence", "nonexact", "long"}:
        row["measured_entity"] = {
            "ambiguous": anchor("A"),
            "different-quote": anchor("C", "s3"),
            "cross-sentence": anchor("10. B"),
            "nonexact": anchor("Z"),
            "long": anchor("x" * 1001),
        }[mutation]
    elif mutation == "relation":
        rels = [relation()]
    rows = [row, row] if mutation == "duplicate" else [row]
    model, calls = response({"facts": rows, "relations": rels})
    with pytest.raises(
        api.ContextualFrameGenerationError, match="^Contextual frame generation failed$"
    ) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    assert len(calls) == 1
    assert error.value.known_usage.model_dump() == {
        "input_tokens": 100,
        "output_tokens": 30,
        "requests": 1,
    }
    assert error.value.__cause__ is None


def test_exact_but_semantically_wrong_selection_remains_unreviewed():
    api = sdk()
    src, row = rich()
    row["measured_entity"] = anchor("기관")
    row["value_status"] = "planned"
    result = run(src, [row])
    assert result.frame.resolved.facts[0].measured_entity.span.text == "기관"
    assert api.validate_contextual_frame_generation(src, result).status == "unreviewed"


@pytest.mark.parametrize(
    "mutation",
    [
        "prompt",
        "instructions",
        "profile",
        "status",
        "frame",
        "usage",
        "hidden-result",
        "hidden-frame",
        "hidden-anchor",
        "extra",
        "source",
    ],
)
def test_validation_rebuilds_receipts_source_and_canonical_nested_models(mutation):
    api = sdk()
    src, row = rich()
    result = run(src, [row])
    raw = result.model_dump(mode="json")
    if mutation in {"prompt", "instructions"}:
        raw[f"{mutation}_sha256"] = "0" * 64
    elif mutation in {"profile", "status"}:
        raw[mutation] = "reviewed"
    elif mutation == "frame":
        raw["frame"]["resolved"]["facts"][0]["measured_entity"]["span"]["start"] += 1
    elif mutation == "usage":
        raw["usage"]["requests"] = 0
    elif mutation.startswith("hidden-"):
        target = {
            "hidden-result": result,
            "hidden-frame": result.frame,
            "hidden-anchor": result.frame.resolved.facts[0].measured_entity,
        }[mutation]
        widened_type = create_model(
            "HiddenGenerationField", __base__=type(target), secret=(str, Field(exclude=True))
        )
        widened = widened_type(**target.model_dump(), secret="must reject before dump")
        raw = (
            widened
            if mutation == "hidden-result"
            else result.model_copy(update={"frame": widened})
            if mutation == "hidden-frame"
            else result.model_copy(
                update={
                    "frame": result.frame.model_copy(
                        update={
                            "resolved": result.frame.resolved.model_copy(
                                update={
                                    "facts": (
                                        result.frame.resolved.facts[0].model_copy(
                                            update={"measured_entity": widened}
                                        ),
                                    )
                                }
                            )
                        }
                    )
                }
            )
        )
    elif mutation == "extra":
        raw = result.model_copy(update={"verified": True})
    elif mutation == "source":
        src = document("기관 취업자 10명.")
    with pytest.raises(
        api.ContextualFrameGenerationError, match="^Invalid contextual frame generation$"
    ):
        api.validate_contextual_frame_generation(src, raw)


def test_source_mutation_during_request_rejects_and_preserves_usage():
    api = sdk()
    src = document("A 10.")

    def mutate(messages, info):
        citation = src[1].citations[0]
        citation.selector.__dict__["quote"] = "B 10."

    model, calls = response({"facts": [fact()], "relations": []}, inspect=mutate)
    with pytest.raises(api.ContextualFrameGenerationError) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100


@pytest.mark.parametrize("inputs,outputs", [(20001, 0), (18000, 2500), (100, 2501)])
def test_actual_usage_overflow_is_preserved_in_failure(inputs, outputs):
    api = sdk()
    model, calls = response({"facts": [], "relations": []}, inputs=inputs, outputs=outputs)
    with pytest.raises(api.ContextualFrameGenerationError) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), document("A 10"))
    assert len(calls) == 1
    # The installed SDK checks limits before committing the response to public
    # captured history. No returned/captured response means usage remains unknown.
    assert error.value.known_usage is None


@pytest.mark.parametrize("inputs,outputs", [(17500, 2500), (20000, 0)])
def test_inclusive_usage_caps_are_not_replaced(inputs, outputs):
    result = run(document("A 10"), inputs=inputs, outputs=outputs)
    assert result.usage.model_dump() == {
        "input_tokens": inputs,
        "output_tokens": outputs,
        "requests": 1,
    }


def test_known_zero_receipt_validates_without_claiming_transport_authentication():
    api = sdk()
    src = document("A 10")
    result = run(src)
    # FunctionModel estimates all-zero usage itself. Exercise the SDK's canonical
    # receipt validation directly, without treating that estimate as a zero receipt.
    result = result.model_copy(
        update={"usage": api.KnownUsage(input_tokens=0, output_tokens=0, requests=1)}
    )
    assert api.validate_contextual_frame_generation(src, result).usage.model_dump() == {
        "input_tokens": 0,
        "output_tokens": 0,
        "requests": 1,
    }


@pytest.mark.parametrize(
    "mutation",
    [
        "overflow",
        "requests-zero",
        "requests-two",
        "requests-bool",
        "aggregate",
        "raw-bool",
        "missing-response",
        "hidden-output",
        "hidden-fact",
        "hidden-anchor",
        "canonical-fact",
        "construct-field",
        "known-null",
    ],
)
def test_unchecked_sdk_result_is_revalidated_before_dump_and_keeps_raw_usage(monkeypatch, mutation):
    api = sdk()
    original = api.Agent.run_sync
    src = document("A 10.")

    def changed(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        messages = result.new_messages()
        raw = next(m for m in messages if isinstance(m, ModelResponse))
        output = result.output
        if mutation == "overflow":
            raw.usage.input_tokens = result.usage.input_tokens = 21000
            raw.usage.output_tokens = result.usage.output_tokens = 2600
        elif mutation.startswith("requests-"):
            result.usage.requests = {"requests-zero": 0, "requests-two": 2, "requests-bool": True}[
                mutation
            ]
        elif mutation == "aggregate":
            result.usage.input_tokens += 1
        elif mutation == "raw-bool":
            raw.usage.input_tokens = True
        elif mutation == "missing-response":
            messages = []
        elif mutation.startswith("hidden-"):
            target = (
                output
                if mutation == "hidden-output"
                else output.facts[0]
                if mutation == "hidden-fact"
                else output.facts[0].measured_entity
            )
            widened_type = create_model(
                "HiddenDynamic", __base__=type(target), secret=(str, Field(exclude=True))
            )
            widened = widened_type(**target.model_dump(), secret="hidden")
            output = (
                widened
                if mutation == "hidden-output"
                else output.model_copy(update={"facts": (widened,)})
                if mutation == "hidden-fact"
                else output.model_copy(
                    update={
                        "facts": (output.facts[0].model_copy(update={"measured_entity": widened}),)
                    }
                )
            )
        elif mutation == "canonical-fact":
            from issuedigest_agents.contextual_frame import ContextualFrameFactInput

            output = output.model_copy(
                update={
                    "facts": (
                        ContextualFrameFactInput.model_validate_json(
                            output.facts[0].model_dump_json()
                        ),
                    )
                }
            )
        elif mutation == "construct-field":
            output.__dict__["verified"] = True
        elif mutation == "known-null":
            output = output.model_copy(
                update={
                    "facts": (
                        output.facts[0].model_copy(
                            update={"value_status": "observed", "status_text": None}
                        ),
                    )
                }
            )
        return SimpleNamespace(output=output, usage=result.usage, new_messages=lambda: messages)

    monkeypatch.setattr(api.Agent, "run_sync", changed)
    model, calls = response({"facts": [fact(measured_entity=anchor("A"))], "relations": []})
    with pytest.raises(
        api.ContextualFrameGenerationError, match="^Contextual frame generation failed$"
    ) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    assert len(calls) == 1
    if mutation in {"raw-bool", "missing-response"}:
        assert (
            error.value.known_usage is None
            if mutation == "raw-bool"
            else error.value.known_usage.input_tokens == 100
        )
    else:
        expected = (21000, 2600, 1) if mutation == "overflow" else (100, 30, 1)
        assert (
            error.value.known_usage.input_tokens,
            error.value.known_usage.output_tokens,
            error.value.known_usage.requests,
        ) == expected


@pytest.mark.parametrize("node", ["root", "fact", "anchor", "relation", "cue"])
def test_dictionary_sdk_nodes_are_rejected_before_reader_and_preserve_usage(monkeypatch, node):
    api = sdk()
    original_run = api.Agent.run_sync
    original_read = api._read
    dynamic_reads = []

    def read(model, value):
        if model.__name__ == "ContextualFrameOutputV1":
            dynamic_reads.append(value)
        return original_read(model, value)

    def changed(self, *args, **kwargs):
        result = original_run(self, *args, **kwargs)
        output = result.output
        facts, relations = output.facts, output.relations
        if node == "root":
            output = output.model_dump(mode="json")
        else:
            if node == "fact":
                facts = (facts[0].model_dump(mode="json"), facts[1])
            elif node == "anchor":
                fields = {
                    **facts[0].__dict__,
                    "measured_entity": facts[0].measured_entity.model_dump(),
                }
                facts = (type(facts[0]).model_construct(**fields), facts[1])
            elif node == "relation":
                relations = (relations[0].model_dump(mode="json"),)
            else:
                fields = {**relations[0].__dict__, "cue": relations[0].cue.model_dump()}
                relations = (type(relations[0]).model_construct(**fields),)
            output = type(output).model_construct(facts=facts, relations=relations)
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api, "_read", read)
    monkeypatch.setattr(api.Agent, "run_sync", changed)
    rows = [fact(measured_entity=anchor("A")), fact("n2", measured_entity=anchor("B"))]
    model, calls = response({"facts": rows, "relations": [relation()]})
    with pytest.raises(
        api.ContextualFrameGenerationError, match="^Contextual frame generation failed$"
    ) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), document("A 10명 중 B 2명."))
    assert len(calls) == 1
    assert error.value.known_usage.model_dump() == {
        "input_tokens": 100,
        "output_tokens": 30,
        "requests": 1,
    }
    assert dynamic_reads == []


def test_agent_identity_and_limits_and_no_retries_are_applied(monkeypatch):
    api = sdk()
    original_init = api.Agent.__init__
    original_run = api.Agent.run_sync

    def initialized(self, *args, **kwargs):
        assert kwargs["name"] == "issuedigest_contextual_frame_v1"
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
        return original_run(self, *args, **kwargs)

    monkeypatch.setattr(api.Agent, "__init__", initialized)
    monkeypatch.setattr(api.Agent, "run_sync", called)
    assert run(document("A 10")).usage.requests == 1


def test_instructions_changed_during_request_cannot_certify_new_hash(monkeypatch):
    api = sdk()

    def mutate(messages, info):
        monkeypatch.setattr(
            api, "CONTEXTUAL_FRAME_INSTRUCTIONS", api.CONTEXTUAL_FRAME_INSTRUCTIONS + " changed"
        )

    model, calls = response({"facts": [], "relations": []}, inspect=mutate)
    with pytest.raises(api.ContextualFrameGenerationError) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), document("A 10"))
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100


def test_timeout_has_unknown_usage_and_empty_output_keeps_observed_usage():
    api = sdk()
    for options, expected in [
        ({"error": TimeoutError("secret source")}, None),
        ({"text": True}, 100),
    ]:
        model, calls = response({}, **options)
        with pytest.raises(
            api.ContextualFrameGenerationError, match="^Contextual frame generation failed$"
        ) as error:
            api.run_contextual_framer(api.create_contextual_framer(model), document("A 10"))
        assert len(calls) == 1
        assert (
            error.value.known_usage.input_tokens if error.value.known_usage else None
        ) == expected


@pytest.mark.parametrize("text", ["No numbers.", " ".join("1명" for _ in range(256))])
def test_empty_or_oversized_catalog_rejected_before_request(text):
    api = sdk()
    model, calls = response({})
    src = document(text)
    with pytest.raises(
        api.ContextualFrameGenerationError, match="^Invalid contextual frame generation input$"
    ):
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    with pytest.raises(api.ContextualFrameGenerationError):
        api.contextual_frame_prompt(src)
    assert calls == []


@pytest.mark.parametrize("schema_sizes", [(111, 999), (999, 111)])
def test_actual_utf8_envelope_boundary_uses_larger_schema_in_prompt_run_and_validate(
    monkeypatch, schema_sizes
):
    api = sdk()
    src = document("🧪 A 10명")
    result = run(src)
    monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: schema_sizes)
    exact = (
        len(api.contextual_frame_prompt(src).encode())
        + len(api.CONTEXTUAL_FRAME_INSTRUCTIONS.encode())
        + 999
        + 2048
        + 2500
    )
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact)
    assert run(src).frame.resolved.facts == ()
    assert api.validate_contextual_frame_generation(src, result) == result
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact + 1)
    assert api.contextual_frame_prompt(src)
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact - 1)
    model, calls = response({})
    with pytest.raises(api.ContextualFrameGenerationError):
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    with pytest.raises(api.ContextualFrameGenerationError):
        api.validate_contextual_frame_generation(src, result)
    assert calls == []


def test_real_provider_schema_utf8_envelope_is_inclusive_at_exact_byte(monkeypatch):
    api = sdk()
    src = document("🧪 A 10명")
    prompt, tools = api._preflight(src)
    raw, normalized = api._provider_schema_bytes_v5(tools)
    exact = (
        len(prompt.encode("utf-8"))
        + len(api.CONTEXTUAL_FRAME_INSTRUCTIONS.encode("utf-8"))
        + max(raw, normalized)
        + 2048
        + 2500
    )
    assert len(prompt.encode("utf-8")) > len(prompt)
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact)
    result = run(src)
    assert api.validate_contextual_frame_generation(src, result) == result
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact + 1)
    assert api.contextual_frame_prompt(src) == prompt
    monkeypatch.setattr(api, "MAX_RUN_TOKENS", exact - 1)
    model, calls = response({})
    with pytest.raises(api.ContextualFrameGenerationError):
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    with pytest.raises(api.ContextualFrameGenerationError):
        api.validate_contextual_frame_generation(src, result)
    assert calls == []


def test_hidden_source_field_rejected_before_serialization_and_no_request():
    api = sdk()
    src = document("A 10.")
    widened_type = create_model(
        "HiddenRepresentation",
        __base__=type(src[1].representation),
        secret=(str, Field(exclude=True)),
    )
    widened = widened_type(**src[1].representation.model_dump(), secret="hidden")
    src = src[0], src[1].model_copy(update={"representation": widened}), src[2]
    model, calls = response({})
    with pytest.raises(api.ContextualFrameGenerationError):
        api.contextual_frame_prompt(src)
    with pytest.raises(api.ContextualFrameGenerationError):
        api.run_contextual_framer(api.create_contextual_framer(model), src)
    assert calls == []


def test_borrowed_model_required_and_lifecycle_is_never_owned(monkeypatch):
    api = sdk()
    model, calls = response({"facts": [], "relations": []})

    def forbidden(*args, **kwargs):
        raise AssertionError("Lifecycle is caller owned")

    monkeypatch.setattr(model, "__aenter__", forbidden)
    monkeypatch.setattr(model, "__aexit__", forbidden)
    framer = api.create_contextual_framer(model)
    assert calls == []
    assert api.run_contextual_framer(framer, document("A 10")).frame.resolved.facts == ()
    with pytest.raises(TypeError):
        api.create_contextual_framer()
    with pytest.raises(
        api.ContextualFrameGenerationError, match="^Invalid contextual frame generation model$"
    ):
        api.create_contextual_framer("openai:fake")
    with pytest.raises(api.ContextualFrameGenerationError):
        api.run_contextual_framer(SimpleNamespace(model=model), document("A 10"))


def test_cold_import_create_prompt_validate_are_key_free_and_do_not_allocate_or_use_io():
    sdk()
    code = """
import builtins, importlib, io, os, socket
from hashlib import sha256
import openai, pydantic_ai
from pydantic_ai.models.function import FunctionModel
from test_numeric_evidence import document
from test_contextual_frame import fact, anchor
src = document("A A 10")
row = fact(measured_entity=anchor("A", "A 10"))
def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected IO/client/key/request")
model = FunctionModel(forbidden)
openai.AsyncOpenAI.__init__ = forbidden
openai.OpenAI.__init__ = forbidden
pydantic_ai.Agent.__init__ = forbidden
original = type(os.environ).__getitem__
def no_env(self, key):
    if key != "PYDANTIC_DISABLE_PLUGINS":
        forbidden()
    return original(self, key)
type(os.environ).__getitem__ = no_env
builtins.open = io.open = forbidden
socket.socket = forbidden
api = importlib.import_module("issuedigest_agents.contextual_frame_generation")
api.create_contextual_framer(model)
prompt = api.contextual_frame_prompt(src)
result = api.ContextualFrameGeneration(
    frame=api.build_contextual_frame(src, {"facts": [row], "relations": []}),
    prompt_sha256=sha256(prompt.encode()).hexdigest(),
    instructions_sha256=sha256(api.CONTEXTUAL_FRAME_INSTRUCTIONS.encode()).hexdigest(),
    usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1),
)
assert api.validate_contextual_frame_generation(src, result) == result
assert result.frame.resolved.facts[0].measured_entity.span.start == 2
assert api.build_contextual_frame(src, result.frame.input) == result.frame
try:
    api.validate_contextual_frame_generation(src, {})
except api.ContextualFrameGenerationError as error:
    assert error.known_usage is None
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("node", ["fact", "anchor", "relation", "cue"])
@pytest.mark.parametrize("kind", ["canonical", "hidden", "extra"])
def test_actual_dynamic_types_are_rejected_before_dynamic_reader(monkeypatch, node, kind):
    """Narrowing must not erase canonical or excluded nested provider nodes."""
    api = sdk()
    from issuedigest_agents.contextual_anchor import ContextualAnchor
    from issuedigest_agents.contextual_frame import (
        ContextualFrameFactInput,
        ContextualFrameRelationInput,
    )

    original_run, original_read = api.Agent.run_sync, api._read
    dynamic_reads = []

    def checked_read(model, value):
        if model.__name__ == "ContextualFrameOutputV1":
            dynamic_reads.append(value)
        return original_read(model, value)

    def changed(self, *args, **kwargs):
        result = original_run(self, *args, **kwargs)
        output = result.output
        row, rel = output.facts[0], output.relations[0]
        target = {"fact": row, "anchor": row.measured_entity, "relation": rel, "cue": rel.cue}[node]
        if kind == "canonical":
            cls = {
                "fact": ContextualFrameFactInput,
                "anchor": ContextualAnchor,
                "relation": ContextualFrameRelationInput,
                "cue": ContextualAnchor,
            }[node]
            target = cls.model_validate_json(target.model_dump_json())
        elif kind == "hidden":
            cls = create_model(
                "HiddenProviderNode", __base__=type(target), secret=(str, Field(exclude=True))
            )
            target = cls(**target.model_dump(), secret="hidden")
        else:
            target = target.model_copy(update={"secret": "hidden"})
        if node == "fact":
            row = target
        elif node == "anchor":
            row = row.model_copy(update={"measured_entity": target})
        elif node == "relation":
            rel = target
        else:
            rel = rel.model_copy(update={"cue": target})
        output = output.model_copy(update={"facts": (row, output.facts[1]), "relations": (rel,)})
        return SimpleNamespace(output=output, usage=result.usage, new_messages=result.new_messages)

    monkeypatch.setattr(api.Agent, "run_sync", changed)
    monkeypatch.setattr(api, "_read", checked_read)
    rows = [fact(measured_entity=anchor("A")), fact("n2", measured_entity=anchor("B"))]
    model, calls = response({"facts": rows, "relations": [relation(cue=anchor("중"))]})
    with pytest.raises(api.ContextualFrameGenerationError) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), document("A 10명 중 B 2명."))
    assert len(calls) == 1 and error.value.known_usage.requests == 1
    assert dynamic_reads == []


def test_function_model_resolves_repeated_roles_and_cues_without_expanding_text():
    from test_contextual_frame import repeated

    src, data = repeated()
    result = run(src, data["facts"], data["relations"])
    assert [f.comparison_baseline.span.start for f in result.frame.resolved.facts[:2]] == [5, 21]
    assert [r.cue.span.start for r in result.frame.resolved.relations] == [40, 29]
    assert [r.cue.span.text for r in result.frame.resolved.relations] == ["포함", "포함"]
    assert result.frame.input.model_dump(mode="json") == data


def test_provider_context_is_required_nullable_and_bounded_in_real_dynamic_schema():
    api = sdk()
    _, tools = api._preflight(document("A 10명. B 20명."))
    definitions = tools[0].output.model_json_schema()["$defs"]
    definition = next(d for d in definitions.values() if "context_text" in d.get("properties", {}))
    assert set(definition["required"]) == {"sentence_id", "text", "context_text"}
    assert definition["properties"]["context_text"]["anyOf"] == [
        {"maxLength": 1000, "minLength": 1, "type": "string"},
        {"type": "null"},
    ]


@pytest.mark.parametrize(
    "selected",
    [
        {"sentence_id": "s1", "text": "A"},
        {"sentence_id": "s1", "text": "A", "context_text": "A A"},
        {"sentence_id": "s1", "text": "A", "context_text": "absent"},
        {"sentence_id": "s1", "text": "A", "context_text": "A A 10명"},
    ],
)
def test_invalid_context_output_fails_once_with_observed_usage(selected):
    api = sdk()
    model, calls = response({"facts": [fact(measured_entity=selected)], "relations": []})
    with pytest.raises(api.ContextualFrameGenerationError) as error:
        api.run_contextual_framer(api.create_contextual_framer(model), document("A A 10명."))
    assert len(calls) == 1 and error.value.known_usage.input_tokens == 100
