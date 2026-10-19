"""Character anchors establish source consistency, never meaning or completeness."""

import importlib
import importlib.util
import json
from hashlib import sha256
from uuid import uuid4

import pytest
from model_loop import sync_model_loop as sync_model_loop
from test_numeric_evidence import document


def sdk():
    name = "issuedigest_agents.numeric_evidence_refs"
    assert importlib.util.find_spec(name) is not None, "Missing character-reference SDK"
    return importlib.import_module(name)


def ref(src, text, occurrence=0, citation=0):
    # Fixture locations are derived from synthetic source, never the production catalog/resolver.
    quote = src[1].citations[citation].selector.quote
    start = -1
    for _ in range(occurrence + 1):
        start = quote.index(text, start + 1)
    base = sum(len(c.selector.quote) for c in src[1].citations[:citation])
    return {"start_ref": base + start + 1, "end_ref": base + start + len(text)}


def fact(src, local_id="f1", value="10", kind="unknown", status=None, **fields):
    return {
        "local_id": local_id,
        "value": ref(src, value),
        "subject": None,
        "unit": None,
        "period": None,
        "qualifier": None,
        "condition": None,
        "status": {"kind": kind, "text": ref(src, status) if status else None},
        **fields,
    }


def relation(src, left="f1", right="f2", kind="included_in", statement=None, cue="중"):
    return {
        "kind": kind,
        "from_id": left,
        "to_id": right,
        "statement": ref(src, statement or src[1].citations[0].selector.quote),
        "cue": ref(src, cue),
    }


def pure(src, facts=(), relations=(), usage=None):
    api = sdk()
    return api._build_proposal(
        src,
        {"facts": list(facts), "relations": list(relations)},
        usage or api.KnownUsage(input_tokens=100, output_tokens=30, requests=1),
    )


def pair(src):
    return [
        fact(src, subject=ref(src, "A")),
        fact(src, "f2", value="2", subject=ref(src, "B")),
    ]


def test_catalog_preserves_every_codepoint_global_order_and_inclusive_offsets():
    # Dropping whitespace/control/combining code points or using UTF-8 offsets breaks this.
    api = sdk()
    text = " A\x00\t\n\u0085\ufeffe\u0301🧪 10 aa aa"
    src = document(text, "B 10")
    packet = json.loads(api.numeric_evidence_prompt_v3(src))
    assert packet["profile"] == "numeric-evidence-v3"
    assert [q["quote"] for q in packet["source"]["citations"]] == [text, "B 10"]
    assert packet["references"] == [
        {
            "citation_id": str(src[1].citations[0].citation_id),
            "characters": [
                [1, " "],
                [2, "A"],
                [3, "\x00"],
                [4, "\t"],
                [5, "\n"],
                [6, "\u0085"],
                [7, "\ufeff"],
                [8, "e"],
                [9, "\u0301"],
                [10, "🧪"],
                [11, " "],
                [12, "1"],
                [13, "0"],
                [14, " "],
                [15, "a"],
                [16, "a"],
                [17, " "],
                [18, "a"],
                [19, "a"],
            ],
        },
        {
            "citation_id": str(src[1].citations[1].citation_id),
            "characters": [
                [20, "B"],
                [21, " "],
                [22, "1"],
                [23, "0"],
            ],
        },
    ]
    result = pure(
        src,
        [
            fact(src),
            fact(src, "f2", value="aa", unit=ref(src, "e\u0301")),
            {**fact(src, "f3", value="aa"), "value": ref(src, "aa", 1)},
            {**fact(src, "f4"), "value": ref(src, "10", citation=1)},
        ],
    )
    assert [(f.value.start, f.value.end) for f in result.facts] == [
        (11, 13),
        (14, 16),
        (17, 19),
        (2, 4),
    ]
    assert result.facts[1].unit.text == "e\u0301"
    assert result.facts[0].value.start_ref == 12 and result.facts[0].value.end_ref == 13
    assert result.facts[3].value.citation_id == str(src[1].citations[1].citation_id)
    assert result.facts[0].context == str(src[1].citations[0].citation_id)
    assert api.validate_numeric_proposal_v3(src, result) == result
    assert result.profile == "numeric-evidence-v3" and result.status == "unreviewed"
    with pytest.raises(ValueError):
        result.status = "verified"


@pytest.mark.parametrize(
    "bad",
    [
        {"start_ref": 0, "end_ref": 1},
        {"start_ref": True, "end_ref": 4},
        {"start_ref": "3", "end_ref": 4},
        {"start_ref": 3.0, "end_ref": 4},
        {"start_ref": 4, "end_ref": 3},
        {"start_ref": 3, "end_ref": 12001},
        {"start_ref": 3},
        {"start_ref": 5, "end_ref": 6},
        {"start_ref": 1, "end_ref": 8},
        {"start_ref": 8, "end_ref": 8},
        {"start_ref": 3, "end_ref": 4, "text": "10"},
        {"start_ref": 3, "end_ref": 4, "occurrence": 0},
        {"start_ref": 3, "end_ref": 4, "citation_id": "x"},
    ],
)
def test_noninteger_missing_reverse_blank_cross_quote_and_extra_references_rejected(bad):
    src = document("A 10 \ufeff", "B")
    with pytest.raises(ValueError):
        pure(src, [{**fact(src), "value": bad}])


def test_span_1000_limit_and_full_source_12000_have_no_lower_catalog_cap():
    src = document("x" * 12000)
    result = pure(src, [fact(src, value="x" * 1000)])
    assert len(result.citations[0].quote) == 12000
    assert result.facts[0].value.end == 1000
    with pytest.raises(ValueError):
        pure(src, [fact(src, value="x" * 1001)])


@pytest.mark.parametrize("kind", ["observed", "planned", "forecast", "unknown"])
def test_status_taxonomy_exact_text_and_nullable_explicit_forecast_condition(kind):
    src = document("A 10명 이상 2025년 전망; B 2 조건 충족 시 전망")
    result = pure(
        src,
        [
            fact(
                src,
                kind=kind,
                status="전망",
                subject=ref(src, "A"),
                unit=ref(src, "명"),
                qualifier=ref(src, "이상"),
                period=ref(src, "2025년"),
            ),
            fact(
                src,
                "f2",
                value="2",
                kind="forecast",
                status="전망",
                condition=ref(src, "조건 충족 시"),
            ),
        ],
    )
    assert result.facts[0].kind == kind and result.facts[0].condition is None
    assert result.facts[1].kind == "forecast" and result.facts[1].condition.text == "조건 충족 시"
    assert pure(src, [fact(src)]).facts[0].status_text is None
    assert sdk().validate_numeric_proposal_v3(src, result) == result
    if kind != "unknown":
        with pytest.raises(ValueError):
            pure(src, [fact(src, kind=kind)])


@pytest.mark.parametrize("field", ["subject", "unit", "period", "qualifier", "condition", "status"])
def test_every_fact_field_must_share_value_citation(field):
    src = document("A 10", "B 2 계획")
    row = fact(src)
    row[field] = (
        {"kind": "planned", "text": ref(src, "계획", citation=1)}
        if field == "status"
        else ref(src, "B", citation=1)
    )
    with pytest.raises(ValueError):
        pure(src, [row])


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate-value",
        "duplicate-id",
        "bad-id",
        "13-facts",
        "17-relations",
        "null-value",
        "missing-value",
        "fact-extra",
        "status-extra",
        "old-kind",
        "old-context",
        "self",
        "missing-endpoint",
        "zero-with-relation",
        "no-subject",
        "cross-citation",
        "subject-outside",
        "value-outside",
        "cue-outside",
    ],
)
def test_invalid_fact_and_relation_is_whole_proposal_rejection(mutation):
    src = document("A 10 중 B 2; X", "C 3")
    facts, relations = pair(src), [relation(src, statement="A 10 중 B 2")]
    first, second = facts
    if mutation == "duplicate-value":
        second["value"] = first["value"]
    elif mutation == "duplicate-id":
        second["local_id"] = "f1"
    elif mutation == "bad-id":
        first["local_id"] = "f13"
    elif mutation == "13-facts":
        facts *= 7
    elif mutation == "17-relations":
        relations *= 17
    elif mutation == "null-value":
        first["value"] = None
    elif mutation == "missing-value":
        del first["value"]
    elif mutation == "fact-extra":
        first["citation_id"] = str(src[1].citations[0].citation_id)
    elif mutation == "status-extra":
        first["status"]["verified"] = True
    elif mutation == "old-kind":
        first["status"] = {"kind": "conditional_forecast", "text": ref(src, "중")}
    elif mutation == "old-context":
        first["context"] = ref(src, "A 10")
    elif mutation == "self":
        relations[0]["to_id"] = "f1"
    elif mutation == "missing-endpoint":
        relations[0]["to_id"] = "f3"
    elif mutation == "zero-with-relation":
        facts = []
    elif mutation == "no-subject":
        second["subject"] = None
    elif mutation == "cross-citation":
        second.update(value=ref(src, "3", citation=1), subject=ref(src, "C", citation=1))
    elif mutation == "subject-outside":
        second["subject"] = ref(src, "X")
    elif mutation == "value-outside":
        relations[0]["statement"] = ref(src, "중 B 2")
    elif mutation == "cue-outside":
        relations[0]["cue"] = ref(src, "X")
    with pytest.raises(ValueError):
        pure(src, facts, relations)


@pytest.mark.parametrize("kind", ["included_in", "parallel", "unknown"])
@pytest.mark.parametrize("reverse", [True, False])
def test_unordered_pairs_unique_across_kinds_and_directions(kind, reverse):
    src = document("A 10 중 B 2")
    extra = relation(src, *(("f2", "f1") if reverse else ("f1", "f2")), kind=kind)
    with pytest.raises(ValueError, match="Duplicate relation"):
        pure(src, pair(src), [relation(src), extra])


@pytest.mark.parametrize("size", [3, 4])
def test_three_plus_cycle_rejected_without_duplicate_pair(size):
    src = document("A 10 중 B 2 중 C 3 중 D 4")
    facts = [
        fact(src, f"f{i}", value=v, subject=ref(src, s))
        for i, (v, s) in enumerate(zip(["10", "2", "3", "4"], "ABCD", strict=True), 1)
    ][:size]
    chain = [relation(src, f"f{i}", f"f{i + 1}") for i in range(1, size)]
    assert len(pure(src, facts, chain).relations) == size - 1
    with pytest.raises(ValueError, match="Inclusion cycle"):
        pure(src, facts, [*chain, relation(src, f"f{size}", "f1")])


def test_twelve_facts_sixteen_relations_and_empty_candidates_are_supported():
    src = document(" ".join(f"S{i}:{i}中" for i in range(1, 13)))
    facts = [fact(src, f"f{i}", value=f":{i}", subject=ref(src, f"S{i}")) for i in range(1, 13)]
    edges = [(i, j) for i in range(1, 13) for j in range(i + 1, 13)][:16]
    relations = [relation(src, f"f{i}", f"f{j}", cue="中") for i, j in edges]
    result = pure(src, facts, relations)
    assert (len(result.facts), len(result.relations)) == (12, 16)
    assert pure(src).facts == () and pure(src).relations == ()


@pytest.mark.parametrize("field", ["subject", "value"])
def test_relation_requires_endpoint_physical_occurrence(field):
    src = document("A 10 중 B 2; A 10")
    facts = pair(src)
    facts[0][field] = ref(src, "A" if field == "subject" else "10", occurrence=1)
    with pytest.raises(ValueError):
        pure(src, facts, [relation(src, statement="A 10 중 B 2")])


def test_reference_validity_cannot_certify_status_unit_relation_semantics_or_coverage():
    src = document("A 10명 관측; B 2명 전망; C 99명 중 D 4명")
    facts = [
        fact(src, kind="planned", status="관측", unit=ref(src, "명 관측"), subject=ref(src, "A")),
        fact(src, "f2", value="2", subject=ref(src, "B")),
    ]
    result = pure(src, facts, [relation(src)])
    assert result.facts[0].kind == "planned" and result.facts[0].unit.text == "명 관측"
    assert len(result.facts) == 2  # 99 and 4 omitted; wrong cue association also passes.
    assert sdk().validate_numeric_proposal_v3(src, result).status == "unreviewed"


@pytest.mark.parametrize(
    "mutation",
    [
        "hash",
        "prompt",
        "quote",
        "context",
        "citation",
        "start",
        "end",
        "start_ref",
        "end_ref",
        "subject",
        "snapshot",
        "workspace",
        "status",
        "extra",
        "copied-extra",
        "nested-extra",
        "known-null",
        "usage-bool",
        "usage-negative",
        "usage-total",
        "usage-output",
        "requests",
        "source-order",
        "source-snapshot",
        "source-workspace",
        "relation-offset",
    ],
)
def test_current_source_validation_recomputes_hash_offsets_reference_ids_and_all_fields(mutation):
    api = sdk()
    src = document("A 10 중 B 2", "C 3")
    result = pure(src, pair(src), [relation(src)])
    raw = result.model_dump(mode="json")
    if mutation in ("hash", "prompt"):
        raw["source_sha256" if mutation == "hash" else "prompt_sha256"] = "0" * 64
    elif mutation == "quote":
        raw["citations"][0]["quote"] += "!"
    elif mutation in ("context", "citation"):
        raw["facts"][0]["context" if mutation == "context" else "citation_id"] = str(uuid4())
    elif mutation in ("start", "end", "start_ref", "end_ref"):
        raw["facts"][0]["value"][mutation] += 1
    elif mutation == "subject":
        raw["facts"][0]["subject"]["text"] = "Z"
    elif mutation in ("snapshot", "workspace"):
        raw[f"{mutation}_id"] = str(uuid4())
    elif mutation == "status":
        raw["status"] = "reviewed"
    elif mutation == "extra":
        raw["verified"] = True
    elif mutation == "copied-extra":
        raw = result.model_copy(update={"verified": True})
    elif mutation == "nested-extra":
        raw = result.model_copy(update={"facts": (result.facts[0].model_copy(update={"x": 1}),)})
    elif mutation == "known-null":
        raw["facts"][0]["kind"] = "observed"
    elif mutation.startswith("usage-"):
        key, value = {
            "usage-bool": ("input_tokens", True),
            "usage-negative": ("input_tokens", -1),
            "usage-total": ("input_tokens", 20000),
            "usage-output": ("output_tokens", 2501),
        }[mutation]
        raw["usage"][key] = value
    elif mutation == "requests":
        raw["usage"]["requests"] = 2
    elif mutation == "source-order":
        src = (
            src[0],
            src[1].model_copy(update={"citations": tuple(reversed(src[1].citations))}),
            src[2],
        )
    elif mutation == "source-snapshot":
        sid = uuid4()
        src = sid, src[1], src[2].model_copy(update={"snapshot_id": sid})
    elif mutation == "source-workspace":
        wid = uuid4()
        src = (
            src[0],
            src[1].model_copy(
                update={"document": src[1].document.model_copy(update={"workspace_id": wid})}
            ),
            src[2].model_copy(update={"workspace_id": wid}),
        )
    elif mutation == "relation-offset":
        raw["relations"][0]["statement"]["end"] -= 1
    with pytest.raises(api.NumericEvidenceError, match="^Invalid numeric evidence proposal$"):
        api.validate_numeric_proposal_v3(src, raw)


def model_response(output, *, inspect=None, inputs=100, outputs=30, error=None):
    from pydantic_ai.messages import ModelResponse, ToolCallPart
    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai.usage import RequestUsage

    calls = []

    def respond(messages, info):
        calls.append(info)
        if inspect:
            inspect(messages, info)
        if error:
            raise error
        return ModelResponse(
            parts=[ToolCallPart("propose_numeric_evidence_v3", json.dumps(output))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def test_real_agent_provider_boundary_has_only_current_integer_refs_and_enum_fields(
    sync_model_loop, monkeypatch
):
    api = sdk()
    src = document("A 10 중 B 2", "C 3 계획")
    original = api.Agent.run_sync
    captured = []

    def run(agent, *args, **kwargs):
        assert agent.name == "issuedigest_numeric_evidence_v3"
        assert kwargs["retries"] == 0
        limits = kwargs["usage_limits"]
        assert (limits.request_limit, limits.output_tokens_limit, limits.total_tokens_limit) == (
            1,
            2500,
            20000,
        )
        captured.append(args[0])
        return original(agent, *args, **kwargs)

    monkeypatch.setattr(api.Agent, "run_sync", run)

    def inspect(messages, info):
        assert info.function_tools == [] and info.allow_text_output is False
        assert info.model_settings == {"openai_store": False, "max_tokens": 2500, "timeout": 30}
        tool = info.output_tools[0]
        assert tool.name == "propose_numeric_evidence_v3" and tool.strict is True
        schema = tool.parameters_json_schema
        definitions = schema["$defs"]
        for definition in [schema, *definitions.values()]:
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])
            assert not {"citation_id", "occurrence", "context", "offset", "start", "end"} & set(
                definition["properties"]
            )
            for prop in definition["properties"].values():
                if prop.get("type") == "string":
                    assert "enum" in prop or "const" in prop
        spans = [v for v in definitions.values() if "start_ref" in v["properties"]]
        assert len(spans) == 1 and set(spans[0]["properties"]) == {"start_ref", "end_ref"}
        for prop in spans[0]["properties"].values():
            assert (prop["type"], prop["minimum"], prop["maximum"]) == ("integer", 1, 16)
        for row in definitions.values():
            props = row["properties"]
            if "kind" in props and "text" in props:
                if props["kind"].get("const") == "unknown":
                    assert {"type": "null"} in props["text"]["anyOf"]
                else:
                    assert props["kind"]["enum"] == ["observed", "planned", "forecast"]
                    assert "$ref" in props["text"] and "anyOf" not in props["text"]

    model, calls = model_response({"facts": [fact(src)], "relations": []}, inspect=inspect)
    result = api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), src)
    assert result.prompt_sha256 == sha256(captured[0].encode()).hexdigest()
    assert result.usage == api.KnownUsage(input_tokens=100, output_tokens=30, requests=1)
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["observed", "planned", "forecast", "unknown"])
def test_all_status_branches_succeed_through_actual_tool(sync_model_loop, kind):
    api = sdk()
    src = document("A 10 전망")
    model, calls = model_response({"facts": [fact(src, kind=kind, status="전망")], "relations": []})
    result = api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), src)
    assert result.facts[0].kind == kind and result.facts[0].status_text.text == "전망"
    assert result.facts[0].condition is None and len(calls) == 1


@pytest.mark.parametrize("bad", ["known-null", "bool", "string", "out-of-range", "extra"])
def test_provider_invalid_output_returns_no_result_unknown_usage_and_zero_retry(
    sync_model_loop, bad
):
    api = sdk()
    src = document("A 10")
    row = fact(src)
    if bad == "known-null":
        row["status"]["kind"] = "forecast"
    elif bad == "extra":
        row["value"]["text"] = "10"
    else:
        row["value"]["end_ref"] = {"bool": True, "string": "4", "out-of-range": 5}[bad]
    model, calls = model_response({"facts": [row], "relations": []})
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), src)
    assert caught.value.known_usage is None and len(calls) == 1


@pytest.mark.parametrize("mutation", ["duplicate", "relation", "live-source", "live-quote", "span"])
def test_post_result_failure_preserves_raw_usage_including_valid_live_mutation(
    sync_model_loop, mutation
):
    from issuedigest_domain import EvidenceBundle

    api = sdk()
    src = document("A 10 중 B 2")
    facts, relations = [fact(src)], []
    if mutation == "duplicate":
        facts.append(fact(src, "f2"))
    elif mutation == "relation":
        relations.append(relation(src))
    elif mutation == "span":
        facts[0]["value"] = ref(src, " ")

    def inspect(messages, info):
        if mutation == "live-source":
            object.__setattr__(src[2], "snapshot_id", uuid4())
        elif mutation == "live-quote":
            raw = src[1].model_dump(mode="json")
            quote = "A 10 중 B 2; C 3"
            raw["representation"].update(text=quote, text_sha256=sha256(quote.encode()).hexdigest())
            raw["citations"][0]["selector"].update(quote=quote, end=len(quote))
            changed = EvidenceBundle.model_validate(raw)
            object.__setattr__(src[1], "representation", changed.representation)
            object.__setattr__(src[1], "citations", changed.citations)
            assert api._source_data(src).citations[0].quote == quote

    model, calls = model_response(
        {"facts": facts, "relations": relations}, inspect=inspect, inputs=112, outputs=45
    )
    with pytest.raises(
        api.NumericEvidenceError, match="^Numeric evidence extraction failed$"
    ) as caught:
        api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), src)
    assert caught.value.known_usage == api.KnownUsage(
        input_tokens=112, output_tokens=45, requests=1
    )
    assert caught.value.__cause__ is None and len(calls) == 1


@pytest.mark.parametrize("error", [RuntimeError("private canary"), TimeoutError("private canary")])
def test_transport_failure_and_timeout_are_unknown_usage_and_one_request(sync_model_loop, error):
    api = sdk()
    model, calls = model_response(None, error=error)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), document("A 10"))
    assert caught.value.known_usage is None and caught.value.__cause__ is None
    assert "canary" not in str(caught.value) and len(calls) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "aggregate",
        "requests-bool",
        "requests-over",
        "raw-over",
        "raw-invalid",
        "unchecked-output",
        "output-extra",
        "no-raw",
        "two-raw",
    ],
)
def test_usage_and_unchecked_output_are_revalidated_with_known_raw_receipt(
    monkeypatch, sync_model_loop, mutation
):
    from copy import deepcopy
    from types import SimpleNamespace

    from pydantic_ai.messages import ModelResponse

    api = sdk()
    src = document("A 10")
    model, calls = model_response({"facts": [fact(src)], "relations": []})
    original = api.Agent.run_sync

    def changed(agent, *args, **kwargs):
        result = original(agent, *args, **kwargs)
        response = next(m for m in result.new_messages() if isinstance(m, ModelResponse))
        if mutation == "aggregate":
            result.usage.input_tokens += 1
        elif mutation == "requests-bool":
            result.usage.requests = True
        elif mutation == "requests-over":
            result.usage.requests = 2
        elif mutation == "raw-over":
            response.usage.input_tokens = result.usage.input_tokens = 21000
            response.usage.output_tokens = result.usage.output_tokens = 2600
        elif mutation == "raw-invalid":
            response.usage.input_tokens = True
        elif mutation in ("unchecked-output", "output-extra"):
            row = result.output.facts[0]
            updates = (
                {"value": row.value.model_copy(update={"start_ref": True})}
                if mutation == "unchecked-output"
                else {"verified": True}
            )
            result.output = result.output.model_copy(
                update={"facts": (row.model_copy(update=updates),)}
            )
        elif mutation in ("no-raw", "two-raw"):
            messages = [] if mutation == "no-raw" else [response, deepcopy(response)]
            return SimpleNamespace(
                output=result.output, usage=result.usage, new_messages=lambda: messages
            )
        return result

    monkeypatch.setattr(api.Agent, "run_sync", changed)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), src)
    usage = caught.value.known_usage
    if mutation in ("raw-invalid", "no-raw"):
        assert usage is None
    elif mutation == "raw-over":
        assert usage == api.KnownUsage(input_tokens=21000, output_tokens=2600, requests=1)
    elif mutation == "two-raw":
        assert usage == api.KnownUsage(input_tokens=200, output_tokens=60, requests=2)
    else:
        assert usage == api.KnownUsage(input_tokens=100, output_tokens=30, requests=1)
    assert len(calls) == 1


@pytest.mark.parametrize(
    "inputs,outputs", [(True, 0), (-1, 0), (0, True), (0, -1), (1.5, 0), (20000, 1), (0, 2501)]
)
def test_invalid_provider_usage_cannot_be_success_or_free_receipt(sync_model_loop, inputs, outputs):
    api = sdk()
    model, calls = model_response({"facts": [], "relations": []}, inputs=inputs, outputs=outputs)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), document("A 10"))
    assert caught.value.known_usage is None and len(calls) == 1


def test_inclusive_usage_caps_and_zero_raw_counters(sync_model_loop):
    api = sdk()
    for inputs, outputs in ((17500, 2500), (20000, 0)):
        model, calls = model_response(
            {"facts": [], "relations": []}, inputs=inputs, outputs=outputs
        )
        result = api.run_numeric_extractor_v3(
            api.create_numeric_extractor_v3(model), document("A 10")
        )
        assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.requests) == (
            inputs,
            outputs,
            1,
        )
        assert len(calls) == 1
    assert (
        pure(
            document("A 10"), usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1)
        ).usage.input_tokens
        == 0
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "list",
        "snapshot",
        "extra",
        "nested-extra",
        "selector",
        "empty",
        "21",
        "12001",
        "utf8",
        "blank",
        "hash",
        "workspace",
    ],
)
def test_source_preflight_rejects_before_agent_allocation(monkeypatch, mutation):
    api = sdk()
    src = document("A 10")
    if mutation == "list":
        src = list(src)
    elif mutation == "snapshot":
        src = uuid4(), src[1], src[2]
    elif mutation == "extra":
        src = src[0], src[1].model_copy(update={"verified": True}), src[2]
    elif mutation == "nested-extra":
        src = src[0], src[1], src[2].model_copy(update={"x": 1})
    elif mutation == "selector":
        citation = src[1].citations[0]
        src = (
            src[0],
            src[1].model_copy(
                update={
                    "citations": (
                        citation.model_copy(
                            update={
                                "selector": citation.selector.model_copy(update={"quote": "wrong"})
                            }
                        ),
                    )
                }
            ),
            src[2],
        )
    elif mutation == "empty":
        src = src[0], src[1].model_copy(update={"citations": ()}), src[2]
    elif mutation == "21":
        src = document(*(["A 10"] * 21))
    elif mutation == "12001":
        src = document("x" * 12001)
    elif mutation == "utf8":
        src = document("한" * 12000)
    elif mutation == "blank":
        src = document(" \ufeff\u0085")
    elif mutation == "hash":
        src = (
            src[0],
            src[1].model_copy(
                update={
                    "representation": src[1].representation.model_copy(
                        update={"text_sha256": "0" * 64}
                    )
                }
            ),
            src[2],
        )
    elif mutation == "workspace":
        src = src[0], src[1], src[2].model_copy(update={"workspace_id": uuid4()})
    model, calls = model_response({"facts": [], "relations": []})
    allocated = []
    monkeypatch.setattr(api, "Agent", lambda *a, **kw: allocated.append(True))
    with pytest.raises(api.NumericEvidenceError):
        api.run_numeric_extractor_v3(api.create_numeric_extractor_v3(model), src)
    assert allocated == [] and calls == []


def test_lazy_handle_borrows_model_without_allocating_or_closing(monkeypatch, sync_model_loop):
    from dataclasses import FrozenInstanceError

    api = sdk()
    real = api.Agent
    allocated, closed = [], []
    monkeypatch.setattr(api, "Agent", lambda *a, **kw: allocated.append(True))
    for invalid in (None, "openai:any", object()):
        with pytest.raises(api.NumericEvidenceError):
            api.create_numeric_extractor_v3(invalid)
    model, calls = model_response({"facts": [], "relations": []})
    handle = api.create_numeric_extractor_v3(model)
    assert handle.model is model and allocated == [] and calls == []
    with pytest.raises(FrozenInstanceError):
        handle.model = None
    monkeypatch.setattr(api, "Agent", real)
    monkeypatch.setattr(model, "__aexit__", lambda *a: closed.append(True))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert api.run_numeric_extractor_v3(handle, document("A 10")).facts == ()
    assert len(calls) == 1 and closed == []


def test_import_and_handle_do_not_read_credentials_or_allocate_client_agent():
    import os
    import subprocess
    import sys

    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    code = """
import os
import openai
import pydantic_ai
from pydantic_ai.models.function import FunctionModel
def forbidden(*args, **kwargs):
    raise AssertionError("Unexpected allocation")
openai.AsyncOpenAI.__init__ = forbidden
pydantic_ai.Agent.__init__ = forbidden
original = type(os.environ).__getitem__
def checked(self, key):
    if key == "OPENAI_API_KEY":
        raise AssertionError("Unexpected credential lookup")
    return original(self, key)
type(os.environ).__getitem__ = checked
from issuedigest_agents.numeric_evidence_refs import create_numeric_extractor_v3
create_numeric_extractor_v3(FunctionModel(lambda messages, info: None))
"""
    result = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_actual_raw_normalized_schema_decimal_boundaries_fit_static_and_reject_nonints():
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    api = sdk()
    for n in (1, 9, 10, 99, 100, 999, 1000, 9999, 10000, 12000):
        tools = api._numeric_tools(n)
        assert max(api._provider_schema_bytes_v5(tools)) <= max(api.NUMERIC_SCHEMA_BYTES)
        tool = tools[0]
        raw_schema = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
        normalized = OpenAIJsonSchemaTransformer(raw_schema, strict=True).walk()
        assert raw_schema["properties"]["facts"]["maxItems"] == 12
        assert raw_schema["properties"]["relations"]["maxItems"] == 16
        for schema in (raw_schema, normalized):
            spans = [v for v in schema["$defs"].values() if "start_ref" in v["properties"]]
            for prop in spans[0]["properties"].values():
                assert (prop["minimum"], prop["maximum"], prop["type"]) == (1, n, "integer")
            statuses = [
                v["properties"]
                for v in schema["$defs"].values()
                if "kind" in v["properties"] and "text" in v["properties"]
            ]
            for props in statuses:
                if props["kind"].get("const") == "unknown":
                    assert {"type": "null"} in props["text"]["anyOf"]
                else:
                    assert "$ref" in props["text"] and "anyOf" not in props["text"]
        envelope = {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "strict": True,
            "parameters": raw_schema,
        }
        raw_bytes = len(json.dumps([envelope], ensure_ascii=False).encode())
        envelope["parameters"] = normalized
        norm_bytes = len(json.dumps([envelope], ensure_ascii=False).encode())
        assert api._provider_schema_bytes_v5(tools) == (raw_bytes, norm_bytes)
        if n == 12000:
            assert api.NUMERIC_SCHEMA_BYTES == (raw_bytes, norm_bytes)
        for bad in (True, "1", 1.0, 0, n + 1):
            row = {**fact(document("10")), "value": {"start_ref": 1, "end_ref": bad}}
            with pytest.raises(ValueError):
                tool.output.model_validate_json(
                    json.dumps({"facts": [row], "relations": []}), strict=True
                )
        row = {**fact(document("10")), "value": {"start_ref": 1, "end_ref": n}}
        assert tool.output.model_validate_json(
            json.dumps({"facts": [row], "relations": []}), strict=True
        )


def test_static_and_actual_whole_table_envelope_reject_before_agent_without_truncation(
    monkeypatch, sync_model_loop
):
    api = sdk()
    assert api.NUMERIC_STATIC_BYTES == len(api.NUMERIC_EVIDENCE_INSTRUCTIONS.encode()) + max(
        api.NUMERIC_SCHEMA_BYTES
    )
    assert api.NUMERIC_PROMPT_BYTE_LIMIT == 20000 - 2500 - 2048 - api.NUMERIC_STATIC_BYTES
    assert (
        len(
            json.loads(api.numeric_evidence_prompt_v3(document(*["x"] * 20)))["source"]["citations"]
        )
        == 20
    )
    # Find the last whole ASCII quote fitting the byte envelope; table ID decimal widths matter.
    last, last_prompt = None, None
    for size in range(1, 12001):
        src = document("x" * size)
        try:
            prompt = api.numeric_evidence_prompt_v3(src)
        except api.NumericEvidenceError:
            break
        last, last_prompt = src, prompt
    assert last is not None and 1 < size < 12000
    assert len(last_prompt.encode()) <= api.NUMERIC_PROMPT_BYTE_LIMIT
    assert len(json.loads(last_prompt)["references"][0]["characters"]) == size - 1
    model, calls = model_response({"facts": [], "relations": []})
    handle = api.create_numeric_extractor_v3(model)
    assert api.run_numeric_extractor_v3(handle, last).citations[0].quote == "x" * (size - 1)
    allocated = []
    monkeypatch.setattr(api, "Agent", lambda *a, **kw: allocated.append(True))
    for src in (document("x" * size), document("한" * size), document("x" * 12000)):
        with pytest.raises(api.NumericEvidenceError):
            api.run_numeric_extractor_v3(handle, src)
    assert allocated == [] and len(calls) == 1
    monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: (20000, 20000))
    with pytest.raises(api.NumericEvidenceError):
        api.run_numeric_extractor_v3(handle, document("x"))
    assert allocated == [] and len(calls) == 1


def test_source_hash_is_exact_ordered_snapshot_workspace_whole_quotes_payload():
    src = document("🧪 A 10", "B 2")
    report = pure(src, [fact(src)])
    payload = {
        "snapshot_id": str(src[0]),
        "workspace_id": str(src[2].workspace_id),
        "citations": [
            {"citation_id": str(c.citation_id), "quote": c.selector.quote} for c in src[1].citations
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert report.source_sha256 == sha256(encoded.encode()).hexdigest()
