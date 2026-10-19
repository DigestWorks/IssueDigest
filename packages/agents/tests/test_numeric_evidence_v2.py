"""Compact source anchors prove structure, never semantics or complete extraction."""

import importlib
import importlib.util
import json
from hashlib import sha256
from uuid import uuid4

import pytest
from model_loop import sync_model_loop as sync_model_loop
from test_numeric_evidence import document


def sdk():
    name = "issuedigest_agents.numeric_evidence_v2"
    assert importlib.util.find_spec(name) is not None, "Missing compact numeric evidence SDK"
    return importlib.import_module(name)


def span(text, occurrence=0):
    return {"text": text, "occurrence": occurrence}


def fact(src, local_id="f1", value="10", citation=0, kind="unknown", status=None, **fields):
    return {
        "citation_id": str(src[1].citations[citation].citation_id),
        "local_id": local_id,
        "value": span(value),
        "subject": None,
        "unit": None,
        "period": None,
        "qualifier": None,
        "condition": None,
        "status": {"kind": kind, "text": span(status) if status is not None else None},
        **fields,
    }


def relation(src, left="f1", right="f2", kind="included_in", statement=None, cue="중"):
    return {
        "citation_id": str(src[1].citations[0].citation_id),
        "kind": kind,
        "from_id": left,
        "to_id": right,
        "statement": span(statement or src[1].citations[0].selector.quote),
        "cue": span(cue),
    }


def pure(src, facts, relations=(), usage=None):
    api = sdk()
    return api._build_proposal(
        src,
        {"facts": facts, "relations": list(relations)},
        usage or api.KnownUsage(input_tokens=100, output_tokens=30, requests=1),
    )


def test_whole_quote_context_preserves_long_unicode_quote_and_compact_fields():
    # Reintroducing a <=1000 context span, normalization, or byte offsets breaks this.
    api = sdk()
    text = "🧪 aaaa e\u0301 A 2025년 1.5  명 이상 계획; B 2~3명 조건 충족 시 전망." + "x" * 1100
    src = document(text)
    result = pure(
        src,
        [
            fact(
                src,
                value="1.5  ",
                kind="planned",
                status="계획",
                subject=span("A"),
                unit=span("명"),
                period=span("2025년"),
                qualifier=span("이상"),
            ),
            fact(
                src,
                "f2",
                value="2~3",
                kind="conditional_forecast",
                status="전망",
                subject=span("B"),
                condition=span("조건 충족 시"),
            ),
            {**fact(src, "f3", value="aa"), "value": span("aa", 2)},
        ],
    )
    assert result.profile == "numeric-evidence-v2" and result.status == "unreviewed"
    assert result.citations[0].quote == text
    assert result.facts[0].context == str(src[1].citations[0].citation_id)
    assert result.facts[0].value.text == "1.5  "
    assert result.facts[0].subject.start == 10
    assert result.facts[1].condition.text == "조건 충족 시"
    assert result.facts[1].kind == "conditional_forecast"
    assert result.facts[2].status_text is None
    assert (result.facts[2].value.start, result.facts[2].value.end) == (4, 6)
    assert api.validate_numeric_proposal_v2(src, result) == result
    with pytest.raises(ValueError):
        result.status = "verified"


@pytest.mark.parametrize(
    "text,occurrence",
    [
        ("AA", 0),
        ("é", 0),
        ("aa", 3),
        (" \ufeff\u0085", 0),
        ("aa", True),
        ("aa", "0"),
        ("aa", -1),
        ("aa", 32),
        ("x" * 1001, 0),
    ],
)
def test_nonexact_blank_or_unbounded_compact_span_rejected(text, occurrence):
    src = document("aaaa e\u0301 10 \ufeff\u0085")
    row = fact(src)
    row["value"] = span(text, occurrence)
    with pytest.raises(ValueError):
        pure(src, [row])


def test_same_value_distinct_occurrences_and_semantic_mistakes_remain_unreviewed():
    src = document("A 10명 관측; B 10명 계획; C 99명")
    first = fact(src, subject=span("B"), kind="observed", status="계획")
    second = fact(src, "f2", subject=span("A"))
    second["value"] = span("10", 1)
    result = pure(src, [first, second])
    assert [f.value.start for f in result.facts] == [2, 12]
    assert result.facts[0].subject.text == "B"  # Wrong association passes exact text checks.
    assert result.facts[0].kind == "observed"  # Wrong interpretation is not certified.
    assert len(result.facts) == 2  # C 99 was omitted; no complete-extraction guarantee.
    assert sdk().validate_numeric_proposal_v2(src, result).status == "unreviewed"
    assert pure(src, []).relations == ()


@pytest.mark.parametrize(
    "mutation",
    [
        "known-null",
        "status-extra",
        "span-extra",
        "field-extra",
        "old-context",
        "bad-citation",
        "missing",
        "duplicate-value",
        "duplicate-id",
        "bad-id",
        "13-facts",
        "17-relations",
        "null-value",
        "zero-with-relation",
        "self",
        "missing-endpoint",
        "no-subject",
        "cross-citation",
        "subject-outside",
        "value-outside",
        "cue-outside",
        "statement-too-long",
    ],
)
def test_invalid_fact_or_relation_is_whole_proposal_rejection(mutation):
    src = document("A 10 중 B 2; 외부 주체 X", "C 2")
    f1, f2 = fact(src, subject=span("A")), fact(src, "f2", value="2", subject=span("B"))
    facts, relations = [f1, f2], [relation(src, statement="A 10 중 B 2")]
    if mutation == "known-null":
        f1["status"]["kind"] = "planned"
    elif mutation == "status-extra":
        f1["status"]["verified"] = True
    elif mutation == "span-extra":
        f1["value"]["citation_id"] = f1["citation_id"]
    elif mutation == "field-extra":
        f1["numeric_value"] = 10
    elif mutation == "old-context":
        f1["context"] = span("A 10")
    elif mutation == "bad-citation":
        f1["citation_id"] = str(uuid4())
    elif mutation == "missing":
        f1["value"] = span("missing")
    elif mutation == "duplicate-value":
        f2["value"] = span("10")
    elif mutation == "duplicate-id":
        f2["local_id"] = "f1"
    elif mutation == "bad-id":
        f1["local_id"] = "f13"
    elif mutation == "13-facts":
        facts *= 7
    elif mutation == "17-relations":
        relations *= 17
    elif mutation == "null-value":
        f1["value"] = None
    elif mutation == "zero-with-relation":
        facts = []
    elif mutation == "self":
        relations[0]["to_id"] = "f1"
    elif mutation == "missing-endpoint":
        relations[0]["to_id"] = "f3"
    elif mutation == "no-subject":
        f2["subject"] = None
    elif mutation == "cross-citation":
        f2["citation_id"] = str(src[1].citations[1].citation_id)
        f2["subject"] = span("C")
    elif mutation == "subject-outside":
        f2["subject"] = span("X")
    elif mutation == "value-outside":
        relations[0]["statement"] = span("중 B 2")
    elif mutation == "cue-outside":
        relations[0]["cue"] = span("외부")
    elif mutation == "statement-too-long":
        relations[0]["statement"] = span("x" * 1001)
    with pytest.raises(ValueError):
        pure(src, facts, relations)


@pytest.mark.parametrize("kind", ["included_in", "parallel", "unknown"])
@pytest.mark.parametrize("reverse", [True, False])
def test_unordered_pair_unique_across_all_kinds_and_directions(kind, reverse):
    src = document("A 10 중 B 2")
    facts = [fact(src, subject=span("A")), fact(src, "f2", value="2", subject=span("B"))]
    second = relation(src, *(("f2", "f1") if reverse else ("f1", "f2")), kind=kind)
    with pytest.raises(ValueError, match="Duplicate relation"):
        pure(src, facts, [relation(src), second])


@pytest.mark.parametrize("size", [3, 4])
def test_inclusion_cycle_is_rejected_independently_of_pair_duplicates(size):
    src = document("A 10 중 B 2 중 C 3 중 D 4")
    facts = [
        fact(src, f"f{i}", value=v, subject=span(s))
        for i, (v, s) in enumerate(zip(["10", "2", "3", "4"], "ABCD", strict=True), 1)
    ][:size]
    chain = [relation(src, f"f{i}", f"f{i + 1}") for i in range(1, size)]
    assert len(pure(src, facts, chain).relations) == size - 1
    with pytest.raises(ValueError, match="Inclusion cycle"):
        pure(src, facts, [*chain, relation(src, f"f{size}", "f1")])


def test_relation_physical_occurrence_and_ambiguous_cue_semantic_boundary():
    src = document("A 10 중 B 2; C 3 중 D 4")
    facts = [fact(src, subject=span("A")), fact(src, "f2", value="2", subject=span("B"))]
    row = relation(src, statement="A 10 중 B 2")
    row["cue"] = span("중", 1)
    with pytest.raises(ValueError):
        pure(src, facts, [row])
    # The wider statement contains the wrong cue's position; structure cannot assess its referent.
    row["statement"] = span(src[1].citations[0].selector.quote)
    assert pure(src, facts, [row]).status == "unreviewed"


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
        "occurrence",
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
        "source-change",
        "relation-offset",
    ],
)
def test_validate_current_source_recomputes_provenance_offsets_and_structure(mutation):
    api = sdk()
    src = document("A 10 중 B 2", "C 3")
    result = pure(
        src,
        [fact(src, subject=span("A")), fact(src, "f2", value="2", subject=span("B"))],
        [relation(src)],
    )
    raw = result.model_dump(mode="json")
    if mutation in ("hash", "prompt"):
        raw["source_sha256" if mutation == "hash" else "prompt_sha256"] = "0" * 64
    elif mutation == "quote":
        raw["citations"][0]["quote"] += "!"
    elif mutation in ("context", "citation"):
        raw["facts"][0]["context" if mutation == "context" else "citation_id"] = str(uuid4())
    elif mutation in ("start", "end", "occurrence"):
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
    elif mutation == "source-change":
        changed = document("A 10 중 B 3", "C 3")
        src = src[0], changed[1], src[2]
    elif mutation == "relation-offset":
        raw["relations"][0]["statement"]["end"] -= 1
    with pytest.raises(api.NumericEvidenceError, match="^Invalid numeric evidence proposal$"):
        api.validate_numeric_proposal_v2(src, raw)


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
            parts=[ToolCallPart("propose_numeric_evidence_v2", json.dumps(output))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def test_provider_schema_status_union_and_settings_are_enforced_on_real_agent(
    sync_model_loop, monkeypatch
):
    api = sdk()
    src = document("A 10 중 B 2", "C 3 계획")
    captured = []
    original = api.Agent.run_sync

    def run(agent, *args, **kwargs):
        assert agent.name == "issuedigest_numeric_evidence_v2"
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
        assert tool.name == "propose_numeric_evidence_v2" and tool.strict is True
        schema = tool.parameters_json_schema
        definitions = schema["$defs"]
        for definition in [schema, *definitions.values()]:
            assert definition["additionalProperties"] is False
            assert set(definition["required"]) == set(definition["properties"])
        compact = [v for v in definitions.values() if "occurrence" in v["properties"]]
        assert len(compact) == 1 and set(compact[0]["properties"]) == {"text", "occurrence"}
        for row in definitions.values():
            props = row["properties"]
            if "citation_id" in props:
                assert props["citation_id"]["enum"] == [
                    str(c.citation_id) for c in src[1].citations
                ]
            if "kind" in props and "text" in props:
                if props["kind"].get("const") == "unknown":
                    assert {"type": "null"} in props["text"]["anyOf"]
                else:
                    assert "$ref" in props["text"] and "anyOf" not in props["text"]

    model, calls = model_response({"facts": [fact(src)], "relations": []}, inspect=inspect)
    result = api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), src)
    assert result.usage == api.KnownUsage(input_tokens=100, output_tokens=30, requests=1)
    assert result.prompt_sha256 == sha256(captured[0].encode()).hexdigest()
    prompt = json.loads(captured[0])
    assert prompt["profile"] == "numeric-evidence-v2"
    assert set(prompt["source"]) == {"snapshot_id", "workspace_id", "citations"}
    assert [q["quote"] for q in prompt["source"]["citations"]] == ["A 10 중 B 2", "C 3 계획"]
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["observed", "planned", "conditional_forecast"])
def test_known_null_text_is_rejected_before_agent_result_with_no_retry(sync_model_loop, kind):
    api = sdk()
    src = document("A 10 계획")
    model, calls = model_response({"facts": [fact(src, kind=kind)], "relations": []})
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), src)
    assert caught.value.known_usage is None and len(calls) == 1


@pytest.mark.parametrize(
    "mutation", ["substring", "duplicate", "relation", "live-source", "live-quote"]
)
def test_result_failure_preserves_known_raw_usage(sync_model_loop, mutation):
    api = sdk()
    src = document("A 10 중 B 2")
    row = fact(src)
    facts, relations = [row], []
    if mutation == "substring":
        row["value"] = span("private canary absent")
    elif mutation == "duplicate":
        facts.append(fact(src, "f2"))
    elif mutation == "relation":
        relations.append(relation(src))

    def inspect(messages, info):
        if mutation == "live-source":
            object.__setattr__(src[2], "snapshot_id", uuid4())
        elif mutation == "live-quote":
            from issuedigest_domain import EvidenceBundle

            # Keep canonical provenance valid, so only comparing with the sent packet detects this.
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
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), src)
    assert caught.value.known_usage == api.KnownUsage(
        input_tokens=112, output_tokens=45, requests=1
    )
    assert "canary" not in str(caught.value) and caught.value.__cause__ is None
    assert len(calls) == 1


def test_provider_error_is_unknown_usage_and_single_request(sync_model_loop):
    api = sdk()
    model, calls = model_response(None, error=RuntimeError("private canary"))
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), document("A 10"))
    assert caught.value.known_usage is None and caught.value.__cause__ is None
    assert len(calls) == 1 and "canary" not in str(caught.value)


def test_lazy_borrowed_handle_never_allocates_agent_or_closes_model(monkeypatch, sync_model_loop):
    from dataclasses import FrozenInstanceError

    api = sdk()
    real = api.Agent
    allocated, closed = [], []
    monkeypatch.setattr(api, "Agent", lambda *a, **kw: allocated.append(True))
    for invalid in (None, "openai:any", object()):
        with pytest.raises(api.NumericEvidenceError):
            api.create_numeric_extractor_v2(invalid)
    model, calls = model_response({"facts": [], "relations": []})
    handle = api.create_numeric_extractor_v2(model)
    assert handle.model is model and allocated == [] and calls == []
    with pytest.raises(FrozenInstanceError):
        handle.model = None
    monkeypatch.setattr(api, "Agent", real)
    monkeypatch.setattr(model, "__aexit__", lambda *a: closed.append(True))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert api.run_numeric_extractor_v2(handle, document("A 10")).facts == ()
    assert len(calls) == 1 and closed == []


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
    ],
)
def test_invalid_source_preflight_precedes_agent(monkeypatch, mutation):
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
        c = src[1].citations[0]
        src = (
            src[0],
            src[1].model_copy(
                update={
                    "citations": (
                        c.model_copy(
                            update={"selector": c.selector.model_copy(update={"quote": "wrong"})}
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
    model, calls = model_response({"facts": [], "relations": []})
    handle = api.create_numeric_extractor_v2(model)
    allocated = []
    monkeypatch.setattr(api, "Agent", lambda *a, **kw: allocated.append(True))
    with pytest.raises(api.NumericEvidenceError):
        api.run_numeric_extractor_v2(handle, src)
    assert allocated == [] and calls == []


def test_static_twenty_citation_raw_normalized_and_exact_actual_envelope(
    monkeypatch, sync_model_loop
):
    from uuid import UUID

    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    api = sdk()
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 21))
    tools = api._numeric_tools(ids)
    raw, normalized = api._provider_schema_bytes_v5(tools)
    tool = tools[0]
    schema = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    envelope = {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "strict": True,
        "parameters": schema,
    }
    assert raw == len(json.dumps([envelope], ensure_ascii=False).encode())
    envelope["parameters"] = OpenAIJsonSchemaTransformer(schema, strict=True).walk()
    assert normalized == len(json.dumps([envelope], ensure_ascii=False).encode())
    assert api.NUMERIC_STATIC_BYTES == len(api.NUMERIC_EVIDENCE_INSTRUCTIONS.encode()) + max(
        raw, normalized
    )
    assert api.NUMERIC_PROMPT_BYTE_LIMIT == 20000 - 2500 - 2048 - api.NUMERIC_STATIC_BYTES
    assert (
        len(
            json.loads(api.numeric_evidence_prompt_v2(document(*["x"] * 20)))["source"]["citations"]
        )
        == 20
    )
    initial = document("x")
    overhead = len(api.numeric_evidence_prompt_v2(initial).encode()) - 1
    quote = "x" * (api.NUMERIC_PROMPT_BYTE_LIMIT - overhead)
    src = document(quote)
    assert len(api.numeric_evidence_prompt_v2(src).encode()) == api.NUMERIC_PROMPT_BYTE_LIMIT
    model, calls = model_response({"facts": [], "relations": []})
    assert (
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), src).citations[0].quote
        == quote
    )
    for tail in ("x", "한"):
        with pytest.raises(api.NumericEvidenceError):
            api.numeric_evidence_prompt_v2(document(quote + tail))
    monkeypatch.setattr(api, "_provider_schema_bytes_v5", lambda tools: (20000, 20000))
    with pytest.raises(api.NumericEvidenceError):
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), initial)
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["included_in", "parallel", "unknown"])
@pytest.mark.parametrize("field", ["subject", "value"])
def test_relation_requires_endpoint_occurrence_not_merely_same_text(kind, field):
    src = document("A 10 중 B 2; A 10")
    first = fact(src, subject=span("A"))
    first[field] = span("A" if field == "subject" else "10", 1)
    second = fact(src, "f2", value="2", subject=span("B"))
    with pytest.raises(ValueError):
        pure(src, [first, second], [relation(src, kind=kind, statement="A 10 중 B 2")])


@pytest.mark.parametrize("kind", ["observed", "planned", "conditional_forecast", "unknown"])
def test_all_status_branches_have_actual_tool_success_without_normalizing(sync_model_loop, kind):
    api = sdk()
    src = document("A 10 계획")
    model, calls = model_response({"facts": [fact(src, kind=kind, status="계획")], "relations": []})
    result = api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), src)
    assert result.facts[0].kind == kind and result.facts[0].status_text.text == "계획"
    assert result.facts[0].condition is None and len(calls) == 1


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
def test_received_usage_and_unchecked_output_are_revalidated_with_raw_receipt(
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
                {"value": row.value.model_copy(update={"occurrence": True})}
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
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), src)
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
def test_provider_usage_failures_never_return_success_or_synthesize_zero(
    sync_model_loop, inputs, outputs
):
    api = sdk()
    model, calls = model_response({"facts": [], "relations": []}, inputs=inputs, outputs=outputs)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_extractor_v2(api.create_numeric_extractor_v2(model), document("A 10"))
    assert caught.value.known_usage is None and len(calls) == 1


def test_success_usage_inclusive_caps_and_zero_counters(sync_model_loop):
    api = sdk()
    for inputs, outputs in ((17500, 2500), (20000, 0)):
        model, calls = model_response(
            {"facts": [], "relations": []}, inputs=inputs, outputs=outputs
        )
        result = api.run_numeric_extractor_v2(
            api.create_numeric_extractor_v2(model), document("A 10")
        )
        assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.requests) == (
            inputs,
            outputs,
            1,
        )
        assert len(calls) == 1
    # FunctionModel estimates an all-zero response's usage; validate genuine zero counters directly.
    usage = api.KnownUsage(input_tokens=0, output_tokens=0, requests=1)
    assert pure(document("A 10"), [], usage=usage).usage == usage


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
from issuedigest_agents.numeric_evidence_v2 import create_numeric_extractor_v2
create_numeric_extractor_v2(FunctionModel(lambda messages, info: None))
"""
    result = subprocess.run([sys.executable, "-c", code], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_raw_and_normalized_known_text_schemas_exclude_null_and_all_sizes_fit_static():
    from uuid import UUID

    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    api = sdk()
    for count in range(1, 21):
        tools = api._numeric_tools(tuple(str(UUID(int=i, version=4)) for i in range(1, count + 1)))
        assert max(api._provider_schema_bytes_v5(tools)) <= max(api.NUMERIC_SCHEMA_BYTES)
        raw = tools[0].output.model_json_schema(schema_generator=GenerateToolJsonSchema)
        assert raw["properties"]["facts"]["maxItems"] == 12
        assert raw["properties"]["relations"]["maxItems"] == 16
        for schema in (raw, OpenAIJsonSchemaTransformer(raw, strict=True).walk()):
            statuses = [
                v["properties"]
                for v in schema["$defs"].values()
                if "text" in v["properties"] and "kind" in v["properties"]
            ]
            assert len(statuses) == 2
            for props in statuses:
                if props["kind"].get("const") == "unknown":
                    assert {"type": "null"} in props["text"]["anyOf"]
                else:
                    assert "$ref" in props["text"] and "anyOf" not in props["text"]


def test_exact_source_hash_is_ordered_snapshot_workspace_and_whole_quotes_only():
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


def test_inclusive_fact_relation_span_and_canonical_quote_limits():
    from itertools import combinations

    api = sdk()
    subjects = "ABCDEFGHIJKL"
    text = "; ".join(f"{s} {i * 111}" for i, s in enumerate(subjects, 1))
    src = document(text)
    facts = [
        fact(src, f"f{i}", value=str(i * 111), subject=span(s)) for i, s in enumerate(subjects, 1)
    ]
    pairs = list(combinations(range(1, 8), 2))
    relations = [
        relation(src, f"f{left}", f"f{right}", kind="parallel", cue=";")
        for left, right in pairs[:17]
    ]
    result = pure(src, facts, relations[:16])
    assert len(result.facts) == 12 and len(result.relations) == 16
    with pytest.raises(ValueError):
        pure(src, facts, relations)
    long_src = document("x" * 1000)
    assert len(pure(long_src, [fact(long_src, value="x" * 1000)]).facts[0].value.text) == 1000
    assert len(api._source_data(document("x" * 12000)).citations[0].quote) == 12000
