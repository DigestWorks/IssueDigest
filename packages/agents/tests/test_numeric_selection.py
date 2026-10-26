"""Synthetic source consistency tests, deliberately including semantically wrong selections."""

import importlib
import importlib.util
import json
from copy import deepcopy
from dataclasses import FrozenInstanceError
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_numeric_evidence import document


def sdk():
    name = "issuedigest_agents.numeric_selection"
    assert importlib.util.find_spec(name) is not None, "Missing numeric selection SDK"
    return importlib.import_module(name)


def anchor(text, sentence="s1"):
    return {"sentence_id": sentence, "text": text}


def fact(candidate="n1", *, kind="unknown", status=None, **fields):
    return {
        "candidate_id": candidate,
        "subject": None,
        "period": None,
        "condition": None,
        "status": {"kind": kind, "text": status},
        **fields,
    }


def relation(left="n2", right="n1", *, kind="included_in", sentences=("s1",), cue=None):
    return {
        "kind": kind,
        "from_id": left,
        "to_id": right,
        "statement_sentence_ids": sentences,
        "cue": cue or anchor("중"),
    }


def pure(src, facts=(), relations=(), usage=None):
    api = sdk()
    return api._build_proposal(
        src,
        {"facts": list(facts), "relations": list(relations)},
        usage or api.KnownUsage(input_tokens=100, output_tokens=30, requests=1),
    )


def pair():
    return [fact(subject=anchor("A")), fact("n2", subject=anchor("B"))]


def model_response(output, *, inspect=None, inputs=100, outputs=30, error=None):
    calls = []

    def respond(messages, info):
        calls.append(info)
        if inspect:
            inspect(messages, info)
        if error:
            raise error
        return ModelResponse(
            parts=[ToolCallPart("select_numeric_candidates_v1", json.dumps(output))],
            usage=RequestUsage(input_tokens=inputs, output_tokens=outputs),
        )

    return FunctionModel(respond), calls


def test_compact_prompt_preserves_whole_source_and_exact_numeric_atoms():
    api = sdk()
    src = document("🧪 A 9만 9000명 이상. B 1~2호. C 1호~2호. D 3억 5천만 원.", "E 7")
    packet = json.loads(api.numeric_selection_prompt(src))
    assert packet["profile"] == "numeric-selection-v1"
    assert [q["quote"] for q in packet["source"]["citations"]] == [
        "🧪 A 9만 9000명 이상. B 1~2호. C 1호~2호. D 3억 5천만 원.",
        "E 7",
    ]
    assert packet["sentences"][0] == {
        "id": "s1",
        "citation_id": str(src[1].citations[0].citation_id),
        "text": "🧪 A 9만 9000명 이상.",
    }
    rows = packet["candidates"]
    assert [c["id"] for c in rows] == ["n1", "n2", "n3", "n4", "n5"]
    assert [(c["expression"], c["atoms"], c["separator"], c["qualifiers"]) for c in rows] == [
        ("9만 9000명 이상", [{"number": "9만 9000", "unit": "명"}], None, ["이상"]),
        ("1~2호", [{"number": "1", "unit": None}, {"number": "2", "unit": "호"}], "~", []),
        ("1호~2호", [{"number": "1", "unit": "호"}, {"number": "2", "unit": "호"}], "~", []),
        ("3억 5천만 원", [{"number": "3억 5천만", "unit": "원"}], None, []),
        ("7", [{"number": "7", "unit": None}], None, []),
    ]
    assert rows[1]["sentence_ids"] == ["s2"] and rows[0]["lexical_kind"] == "number"
    assert not {"start", "end", "source_sha256", "workspace_id"} & set(rows[0])
    proposal = pure(src, [fact("n2"), fact("n1"), fact("n5")])
    assert [f.candidate_id for f in proposal.facts] == ["n2", "n1", "n5"]
    assert proposal.candidate_index.candidates[1].atoms[0].unit is None
    assert proposal.profile == "numeric-selection-v1" and proposal.status == "unreviewed"
    assert proposal.prompt_sha256 == sha256(api.numeric_selection_prompt(src).encode()).hexdigest()
    assert api.validate_numeric_selection(src, proposal) == proposal
    assert api.validate_numeric_selection(src, proposal.model_dump(mode="json")) == proposal
    assert set(type(proposal.facts[0]).model_fields) == {
        "candidate_id",
        "subject",
        "period",
        "condition",
        "kind",
        "status_text",
    }
    with pytest.raises(ValueError):
        proposal.status = "reviewed"


@pytest.mark.parametrize("kind", ["observed", "planned", "forecast", "unknown"])
def test_status_and_nullable_semantics_resolve_from_same_quote_other_sentence(kind):
    src = document("A 10명. 올해 조건 충족 시 전망.")
    result = pure(
        src,
        [
            fact(
                kind=kind,
                subject=anchor("A"),
                period=anchor("올해", "s2"),
                condition=anchor("조건 충족 시", "s2"),
                status=anchor("전망", "s2"),
            )
        ],
    )
    row = result.facts[0]
    assert row.kind == kind and row.subject.span.text == "A"
    assert row.period.span.text == "올해" and row.condition.span.text == "조건 충족 시"
    assert row.status_text.span.text == "전망"
    assert pure(src, [fact()]).facts[0].status_text is None
    if kind != "unknown":
        with pytest.raises(ValueError):
            pure(src, [fact(kind=kind)])


def test_sentence_local_unique_unicode_and_same_phrase_at_other_physical_positions():
    src = document("🧪 e\u0301\x00 A 10.\r\n A 20. A 30.")
    result = pure(
        src,
        [
            fact(subject=anchor("e\u0301\x00 A")),
            fact("n2", subject=anchor("A", "s3")),
            fact("n3", subject=anchor("A", "s4")),
        ],
    )
    assert [(f.subject.span.start, f.subject.span.end) for f in result.facts] == [
        (2, 7),
        (14, 15),
        (20, 21),
    ]
    packet = json.loads(sdk().numeric_selection_prompt(src))
    assert [s["text"] for s in packet["sentences"]] == [
        "🧪 e\u0301\x00 A 10.",
        "\r\n",
        " A 20.",
        " A 30.",
    ]
    assert sdk().validate_numeric_selection(src, result) == result


@pytest.mark.parametrize(
    "text,sentence",
    [
        ("aa", "s1"),
        ("A A", "s1"),
        ("", "s1"),
        (" \t\ufeff", "s1"),
        ("é", "s1"),
        ("B", "s1"),
        ("10. B", "s1"),
        ("A", "s99"),
        ("x" * 1001, "s1"),
        ("\ud800", "s1"),
    ],
)
def test_anchor_repeated_overlapping_absent_cross_sentence_blank_and_invalid_utf8(text, sentence):
    src = document("aaaa A A A e\u0301 10. B 2.")
    with pytest.raises(ValueError):
        pure(src, [fact(subject=anchor(text, sentence))])


@pytest.mark.parametrize("field", ["subject", "period", "condition", "status"])
def test_semantic_anchors_reject_different_quote(field):
    src = document("A 10.", "B 전망.")
    row = fact()
    row[field] = (
        {"kind": "forecast", "text": anchor("전망", "s2")}
        if field == "status"
        else anchor("B", "s2")
    )
    with pytest.raises(ValueError):
        pure(src, [row])


@pytest.mark.parametrize(
    "extra", ["value", "unit", "qualifier", "range", "occurrence", "citation_id"]
)
def test_provider_cannot_rewrite_server_owned_numbers_or_anchor_occurrences(extra):
    src = document("A 10명")
    row = fact()
    row[extra] = "wrong"
    with pytest.raises(ValueError):
        pure(src, [row])
    row = fact(subject={**anchor("A"), extra: "wrong"})
    with pytest.raises(ValueError):
        pure(src, [row])


def test_contiguous_whole_statement_keeps_whitespace_and_two_endpoint_physical_spans():
    src = document(" A 10.\r\n 중 B 2. 꼬리 C 3.")
    facts = [fact(subject=anchor("A")), fact("n2", subject=anchor("B", "s3"))]
    result = pure(src, facts, [relation(sentences=("s1", "s2", "s3"), cue=anchor("중", "s3"))])
    row = result.relations[0]
    assert row.statement.text == " A 10.\r\n 중 B 2."
    assert (row.statement.start, row.statement.end) == (0, 15)
    assert (row.from_id, row.to_id) == ("n2", "n1")
    assert sdk().validate_numeric_selection(src, result) == result


@pytest.mark.parametrize(
    "mutation",
    [
        "reverse",
        "gap",
        "duplicate",
        "missing",
        "empty",
        "over20",
        "other-quote",
        "self",
        "endpoint",
        "subject-null",
        "subject-outside",
        "value-outside",
        "cue-outside",
        "cue-quote",
        "duplicate-pair",
        "reverse-pair",
        "other-kind-pair",
        "zero-facts",
        "candidate-duplicate",
        "candidate-absent",
        "candidate-null",
        "status-extra",
    ],
)
def test_relations_and_selections_reject_whole_output_for_structural_violation(mutation):
    src = document("A 10.\n 중 B 2. X. C 3.", "D 4.")
    facts = [fact(subject=anchor("A")), fact("n2", subject=anchor("B", "s3"))]
    rels = [relation(sentences=("s1", "s2", "s3"), cue=anchor("중", "s3"))]
    rel = rels[0]
    if mutation in {"reverse", "gap", "duplicate", "missing", "empty", "over20", "other-quote"}:
        rel["statement_sentence_ids"] = {
            "reverse": ("s3", "s2", "s1"),
            "gap": ("s1", "s3"),
            "duplicate": ("s1", "s2", "s2", "s3"),
            "missing": ("s1", "s99"),
            "empty": (),
            "over20": ("s1",) * 21,
            "other-quote": ("s1", "s6"),
        }[mutation]
    elif mutation == "self":
        rel["to_id"] = rel["from_id"]
    elif mutation == "endpoint":
        rel["to_id"] = "n3"
    elif mutation == "subject-null":
        facts[0]["subject"] = None
    elif mutation == "subject-outside":
        facts[0]["subject"] = anchor("X", "s4")
    elif mutation == "value-outside":
        facts[1] = fact("n3", subject=anchor("C", "s5"))
        rel["from_id"] = "n3"
    elif mutation.startswith("cue-"):
        rel["cue"] = anchor("D", "s6") if mutation == "cue-quote" else anchor("X", "s4")
    elif mutation.endswith("pair"):
        rels.append(
            {
                **rel,
                **(
                    {"from_id": "n1", "to_id": "n2"}
                    if mutation == "reverse-pair"
                    else {"kind": "parallel"}
                    if mutation == "other-kind-pair"
                    else {}
                ),
            }
        )
    elif mutation == "zero-facts":
        facts = []
    elif mutation == "candidate-duplicate":
        facts[1]["candidate_id"] = "n1"
    elif mutation == "candidate-absent":
        facts[0]["candidate_id"] = "n99"
    elif mutation == "candidate-null":
        facts[0]["candidate_id"] = None
    elif mutation == "status-extra":
        facts[0]["status"]["verified"] = True
    with pytest.raises(ValueError):
        pure(src, facts, rels)


@pytest.mark.parametrize("kind", ["included_in", "parallel", "unknown"])
def test_relation_kinds_and_cycle(kind):
    src = document("A 10 중 B 2 및 C 3")
    facts = [*pair(), fact("n3", subject=anchor("C"))]
    chain = [relation("n3", "n2", kind=kind), relation("n2", "n1", kind=kind)]
    assert len(pure(src, facts, chain).relations) == 2
    if kind == "included_in":
        with pytest.raises(ValueError):
            pure(src, facts, [*chain, relation("n1", "n3")])


def test_fact_relation_caps_empty_and_all_256_current_candidate_ids():
    src = document(" ".join(f"{chr(65 + i)} {i + 1}명" for i in range(13)) + " 중")
    facts = [fact(f"n{i + 1}", subject=anchor(chr(65 + i))) for i in range(13)]
    rels = [
        relation(f"n{i}", f"n{j}", kind="parallel") for i in range(1, 13) for j in range(i + 1, 13)
    ][:17]
    result = pure(src, facts[:12], rels[:16])
    assert (len(result.facts), len(result.relations)) == (12, 16)
    assert pure(src).facts == () and pure(src).relations == ()
    with pytest.raises(ValueError):
        pure(src, facts)
    with pytest.raises(ValueError):
        pure(src, facts[:12], rels)
    many = document(" ".join("1명" for _ in range(256)))
    tools = sdk()._selection_tools(sdk().build_numeric_candidates(many))
    schema = tools[0].output.model_json_schema()
    enums = [
        v["properties"]["candidate_id"]["enum"]
        for v in schema["$defs"].values()
        if "candidate_id" in v.get("properties", {})
    ]
    assert enums == [[f"n{i}" for i in range(1, 257)]]
    index = sdk().build_numeric_candidates(many)
    output = sdk()._ProviderOutput.model_validate_json(
        json.dumps({"facts": [fact("n256")], "relations": []})
    )
    assert sdk()._resolve_facts(index, output)[0].candidate_id == "n256"
    with pytest.raises(ValueError):
        pure(many, [fact("n256")])  # Whole catalog exceeds the independent 20,000 envelope.


def test_structural_consistency_does_not_certify_semantics_direction_or_completeness():
    src = document("A 10명 관측; B 2명 전망; C 99명 중 D 4명")
    rows = [
        fact(subject=anchor("B"), kind="planned", status=anchor("관측")),
        fact("n2", subject=anchor("A")),
    ]
    # Wrong subjects, planned vs observed, unrelated cue and reverse inclusion all pass.
    result = pure(src, rows, [relation("n1", "n2")])
    assert result.facts[0].kind == "planned" and result.facts[0].subject.span.text == "B"
    assert (result.relations[0].from_id, result.relations[0].to_id) == ("n1", "n2")
    assert len(result.facts) == 2 and len(result.candidate_index.candidates) == 4
    assert sdk().validate_numeric_selection(src, result).status == "unreviewed"


@pytest.mark.parametrize(
    "mutation",
    [
        "prompt",
        "profile",
        "status",
        "extra",
        "copied-extra",
        "construct-extra",
        "hidden-extra",
        "nested-extra",
        "anchor-text",
        "anchor-position",
        "sentence-id",
        "candidate-id",
        "kind-null",
        "statement",
        "statement-ids",
        "cue",
        "index-source",
        "index-quote",
        "index-unit",
        "index-number",
        "index-range",
        "index-order",
        "index-missing",
        "index-snapshot",
        "usage-bool",
        "usage-negative",
        "usage-output",
        "usage-total",
        "usage-requests",
        "source-order",
        "source-snapshot",
        "source-workspace",
        "source-extra",
        "source-hash",
    ],
)
def test_validate_reconstructs_current_source_index_all_spans_hashes_and_unchecked_models(mutation):
    api = sdk()
    src = document("A 10명 중 B 1~2호", "C 3명")
    result = pure(src, pair(), [relation()])
    raw = result.model_dump(mode="json")
    if mutation == "prompt":
        raw["prompt_sha256"] = "0" * 64
    elif mutation in {"profile", "status"}:
        raw[mutation] = "reviewed"
    elif mutation == "extra":
        raw["verified"] = True
    elif mutation in {"copied-extra", "construct-extra", "hidden-extra"}:
        if mutation == "copied-extra":
            raw = result.model_copy(update={"verified": True})
        elif mutation == "construct-extra":
            raw = api.NumericSelectionProposal.model_construct(**result.model_dump())
            raw.__dict__["verified"] = True
        else:
            raw = result.model_copy()
            object.__setattr__(raw, "__pydantic_extra__", {"verified": True})
    elif mutation == "nested-extra":
        raw = result.model_copy(
            update={
                "facts": (result.facts[0].model_copy(update={"verified": True}), result.facts[1])
            }
        )
    elif mutation == "anchor-text":
        raw["facts"][0]["subject"]["span"]["text"] = "Z"
    elif mutation == "anchor-position":
        raw["facts"][0]["subject"]["span"].update(start=1, end=2)
    elif mutation == "sentence-id":
        raw["facts"][0]["subject"]["sentence_id"] = "s2"
    elif mutation == "candidate-id":
        raw["facts"][0]["candidate_id"] = "n99"
    elif mutation == "kind-null":
        raw["facts"][0]["kind"] = "observed"
    elif mutation == "statement":
        raw["relations"][0]["statement"]["text"] = "Z" * len(
            raw["relations"][0]["statement"]["text"]
        )
    elif mutation == "statement-ids":
        raw["relations"][0]["statement_sentence_ids"] = ["s2"]
    elif mutation == "cue":
        raw["relations"][0]["cue"]["span"]["start"] += 1
    elif mutation.startswith("index-"):
        idx = raw["candidate_index"]
        if mutation == "index-source":
            idx["source_sha256"] = "0" * 64
        elif mutation == "index-quote":
            idx["citations"][0]["quote"] += "!"
        elif mutation in {"index-unit", "index-number"}:
            idx["candidates"][0]["atoms"][0]["unit" if mutation == "index-unit" else "number"][
                "text"
            ] = "X"
        elif mutation == "index-range":
            idx["candidates"][1]["atoms"].reverse()
        elif mutation == "index-order":
            idx["sentences"].reverse()
        elif mutation == "index-missing":
            idx["candidates"].pop()
        elif mutation == "index-snapshot":
            idx["snapshot_id"] = str(uuid4())
    elif mutation.startswith("usage-"):
        key, value = {
            "usage-bool": ("input_tokens", True),
            "usage-negative": ("input_tokens", -1),
            "usage-output": ("output_tokens", 2501),
            "usage-total": ("input_tokens", 20000),
            "usage-requests": ("requests", 2),
        }[mutation]
        raw["usage"][key] = value
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
    elif mutation == "source-extra":
        src = src[0], src[1].model_copy(update={"extra": True}), src[2]
    elif mutation == "source-hash":
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
    with pytest.raises(api.NumericEvidenceError, match="^Invalid numeric selection proposal$"):
        api.validate_numeric_selection(src, raw)


def test_actual_agent_schema_has_only_current_ids_strict_fields_and_bounded_borrowed_call(
    sync_model_loop, monkeypatch
):
    api = sdk()
    src = document("A 10 중 B 2", "C 3 계획")
    original = api.Agent.run_sync
    captured = []

    def run(agent, *args, **kwargs):
        assert agent.name == "issuedigest_numeric_selection_v1"
        assert agent.model is model
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
        assert tool.name == "select_numeric_candidates_v1" and tool.strict is True
        schema = tool.parameters_json_schema
        for row in [schema, *schema["$defs"].values()]:
            props = row["properties"]
            assert row["additionalProperties"] is False and set(row["required"]) == set(props)
            assert not {
                "value",
                "unit",
                "qualifier",
                "start",
                "end",
                "occurrence",
                "citation_id",
            } & set(props)
            for key in ("candidate_id", "from_id", "to_id"):
                if key in props:
                    assert props[key]["enum"] == ["n1", "n2", "n3"]
            if "sentence_id" in props:
                assert props["sentence_id"]["enum"] == ["s1", "s2"]
                assert props["text"]["minLength"] == 1 and props["text"]["maxLength"] == 1000
            if "statement_sentence_ids" in props:
                assert props["statement_sentence_ids"]["items"]["enum"] == ["s1", "s2"]
                assert (
                    props["statement_sentence_ids"]["minItems"],
                    props["statement_sentence_ids"]["maxItems"],
                ) == (1, 20)
            if "kind" in props and "text" in props:
                if props["kind"].get("const") == "unknown":
                    assert {"type": "null"} in props["text"]["anyOf"]
                else:
                    assert props["kind"]["enum"] == ["observed", "planned", "forecast"]
                    assert "$ref" in props["text"] and "anyOf" not in props["text"]

    model, calls = model_response({"facts": [fact()], "relations": []}, inspect=inspect)
    handle = api.create_numeric_selector(model)
    with pytest.raises(FrozenInstanceError):
        handle.model = model
    result = api.run_numeric_selector(handle, src)
    assert result.usage == api.KnownUsage(input_tokens=100, output_tokens=30, requests=1)
    assert result.prompt_sha256 == sha256(captured[0].encode()).hexdigest()
    assert len(calls) == 1


@pytest.mark.parametrize("kind", ["observed", "planned", "forecast", "unknown"])
def test_actual_tool_status_branches(sync_model_loop, kind):
    api = sdk()
    model, calls = model_response(
        {"facts": [fact(kind=kind, status=anchor("전망"))], "relations": []}
    )
    result = api.run_numeric_selector(api.create_numeric_selector(model), document("A 10 전망"))
    assert result.facts[0].kind == kind and result.facts[0].status_text.span.text == "전망"
    assert len(calls) == 1


@pytest.mark.parametrize(
    "bad", ["known-null", "candidate", "sentence", "extra", "anchor-extra", "bool"]
)
def test_invalid_tool_schema_preserves_cached_response_usage_without_retry(sync_model_loop, bad):
    api = sdk()
    row = fact(subject=anchor("A"))
    if bad == "known-null":
        row["status"]["kind"] = "observed"
    elif bad == "candidate":
        row["candidate_id"] = "n99"
    elif bad == "sentence":
        row["subject"]["sentence_id"] = "s99"
    elif bad == "extra":
        row["value"] = "10"
    elif bad == "anchor-extra":
        row["subject"]["occurrence"] = 0
    elif bad == "bool":
        row["candidate_id"] = True
    model, calls = model_response({"facts": [row], "relations": []})
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_selector(api.create_numeric_selector(model), document("A 10"))
    assert caught.value.known_usage == api.KnownUsage(
        input_tokens=100, output_tokens=30, requests=1
    )
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mutation", ["duplicate", "ambiguous", "relation", "live-source", "live-quote"]
)
def test_post_result_rejections_preserve_known_usage_and_sanitize(sync_model_loop, mutation):
    api = sdk()
    src = document("A A 10 중 B 2")
    facts, rels = [fact()], []
    if mutation == "duplicate":
        facts.append(fact())
    elif mutation == "ambiguous":
        facts[0]["subject"] = anchor("A")
    elif mutation == "relation":
        rels.append(relation())

    def inspect(messages, info):
        if mutation == "live-source":
            object.__setattr__(src[2], "snapshot_id", uuid4())
        elif mutation == "live-quote":
            data = src[1].model_dump(mode="json")
            quote = "A A 10 중 B 2; C 3"
            data["representation"].update(
                text=quote, text_sha256=sha256(quote.encode()).hexdigest()
            )
            data["citations"][0]["selector"].update(quote=quote, end=len(quote))
            changed = EvidenceBundle.model_validate(data)
            object.__setattr__(src[1], "representation", changed.representation)
            object.__setattr__(src[1], "citations", changed.citations)

    model, calls = model_response(
        {"facts": facts, "relations": rels}, inspect=inspect, inputs=112, outputs=45
    )
    with pytest.raises(api.NumericEvidenceError, match="^Numeric selection failed$") as caught:
        api.run_numeric_selector(api.create_numeric_selector(model), src)
    assert caught.value.known_usage == api.KnownUsage(
        input_tokens=112, output_tokens=45, requests=1
    )
    assert caught.value.__cause__ is None and len(calls) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "aggregate",
        "requests-bool",
        "requests-over",
        "raw-over",
        "raw-invalid",
        "unchecked",
        "hidden-extra",
        "no-raw",
        "two-raw",
    ],
)
def test_raw_usage_and_unchecked_sdk_result_revalidated(monkeypatch, sync_model_loop, mutation):
    api = sdk()
    model, calls = model_response({"facts": [fact()], "relations": []})
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
        elif mutation in {"unchecked", "hidden-extra"}:
            row = result.output.facts[0].model_copy(
                update={"candidate_id": "n99"} if mutation == "unchecked" else {"verified": True}
            )
            result.output = result.output.model_copy(update={"facts": (row,)})
        elif mutation in {"no-raw", "two-raw"}:
            messages = [] if mutation == "no-raw" else [response, deepcopy(response)]
            return SimpleNamespace(
                output=result.output, usage=result.usage, new_messages=lambda: messages
            )
        return result

    monkeypatch.setattr(api.Agent, "run_sync", changed)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_selector(api.create_numeric_selector(model), document("A 10"))
    expected = (
        None
        if mutation == "raw-invalid"
        else api.KnownUsage(
            input_tokens=21000 if mutation == "raw-over" else 200 if mutation == "two-raw" else 100,
            output_tokens=2600 if mutation == "raw-over" else 60 if mutation == "two-raw" else 30,
            requests=2 if mutation == "two-raw" else 1,
        )
    )
    assert caught.value.known_usage == expected and len(calls) == 1


@pytest.mark.parametrize(
    "inputs,outputs", [(True, 0), (-1, 0), (0, True), (0, -1), (1.5, 0), (20000, 1), (0, 2501)]
)
def test_invalid_real_provider_usage_is_not_a_success(sync_model_loop, inputs, outputs):
    api = sdk()
    model, calls = model_response({"facts": [], "relations": []}, inputs=inputs, outputs=outputs)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_selector(api.create_numeric_selector(model), document("A 10"))
    # Installed SDK checks token limits before committing the response to captured history.
    # With no returned result/captured response, even an over-limit receipt is unavailable.
    assert caught.value.known_usage is None and len(calls) == 1


@pytest.mark.parametrize("inputs,outputs", [(17500, 2500), (20000, 0)])
def test_inclusive_success_usage_caps(sync_model_loop, inputs, outputs):
    api = sdk()
    model, calls = model_response({"facts": [], "relations": []}, inputs=inputs, outputs=outputs)
    result = api.run_numeric_selector(api.create_numeric_selector(model), document("A 10"))
    assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.requests) == (
        inputs,
        outputs,
        1,
    )
    assert len(calls) == 1


@pytest.mark.parametrize("error", [RuntimeError("private canary"), TimeoutError("private canary")])
def test_transport_and_timeout_are_sanitized_unknown_usage(sync_model_loop, error):
    api = sdk()
    model, calls = model_response(None, error=error)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_selector(api.create_numeric_selector(model), document("A 10"))
    assert caught.value.known_usage is None and caught.value.__cause__ is None
    assert "canary" not in str(caught.value) and len(calls) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "list",
        "snapshot",
        "workspace",
        "extra",
        "nested-extra",
        "selector",
        "hash",
        "empty",
        "21",
        "12001",
        "utf8",
        "blank",
        "no-candidates",
        "257",
        "huge-sentences",
    ],
)
def test_canonical_source_and_dynamic_envelope_reject_before_agent_allocation(
    monkeypatch, mutation
):
    api = sdk()
    src = document("A 10")
    if mutation == "list":
        src = list(src)
    elif mutation == "snapshot":
        src = uuid4(), src[1], src[2]
    elif mutation == "workspace":
        src = src[0], src[1], src[2].model_copy(update={"workspace_id": uuid4()})
    elif mutation == "extra":
        src = src[0], src[1].model_copy(update={"verified": True}), src[2]
    elif mutation == "nested-extra":
        src = (
            src[0],
            src[1].model_copy(
                update={"representation": src[1].representation.model_copy(update={"x": 1})}
            ),
            src[2],
        )
    elif mutation in {"selector", "hash"}:
        bundle = src[1]
        if mutation == "selector":
            citation = bundle.citations[0].model_copy(
                update={
                    "selector": bundle.citations[0].selector.model_copy(update={"quote": "Z 10"})
                }
            )
            bundle = bundle.model_copy(update={"citations": (citation,)})
        else:
            bundle = bundle.model_copy(
                update={
                    "representation": bundle.representation.model_copy(
                        update={"text_sha256": "0" * 64}
                    )
                }
            )
        src = src[0], bundle, src[2]
    elif mutation == "empty":
        src = src[0], src[1].model_copy(update={"citations": ()}), src[2]
    else:
        quotes = {
            "21": ["1"] * 21,
            "12001": ["1" + "x" * 12000],
            "utf8": ["\ud800 1"],
            "blank": [" \ufeff"],
            "no-candidates": ["다섯 명"],
            "257": ["1 " * 257],
            "huge-sentences": ["1" + "." * 11000],
        }[mutation]
        if mutation == "utf8":
            src = (
                src[0],
                src[1].model_copy(
                    update={
                        "citations": (
                            src[1]
                            .citations[0]
                            .model_copy(
                                update={
                                    "selector": src[1]
                                    .citations[0]
                                    .selector.model_copy(update={"quote": quotes[0]})
                                }
                            ),
                        )
                    }
                ),
                src[2],
            )
        else:
            src = document(*quotes)

    def forbidden(*args, **kwargs):
        pytest.fail("Agent allocated before valid source/envelope")

    monkeypatch.setattr(api, "Agent", forbidden)
    model, calls = model_response({"facts": [], "relations": []})
    with pytest.raises(api.NumericEvidenceError):
        api.numeric_selection_prompt(src)
    with pytest.raises(api.NumericEvidenceError) as caught:
        api.run_numeric_selector(api.create_numeric_selector(model), src)
    assert calls == [] and caught.value.known_usage is None


def test_dynamic_raw_normalized_envelope_counts_all_sections_and_utf8(monkeypatch):
    api = sdk()
    src = document("🧪 10명. B 2호.")
    prompt, tools = api._preflight(src)
    raw, normalized = api._provider_schema_bytes_v5(tools)
    envelope = (
        len(prompt.encode())
        + len(api.NUMERIC_SELECTION_INSTRUCTIONS.encode())
        + max(raw, normalized)
        + 2048
        + 2500
    )
    assert raw > 0 and normalized > 0 and envelope <= 20000
    assert len(prompt.encode()) > len(prompt)
    # Both raw and normalized maxima independently govern admission, inclusive at cap.
    spare = 20000 - envelope
    original = api._provider_schema_bytes_v5
    for side in (0, 1):
        sizes = [0, 0]
        sizes[side] = max(raw, normalized) + spare
        monkeypatch.setattr(
            api, "_provider_schema_bytes_v5", lambda tools, sizes=sizes: tuple(sizes)
        )
        assert api.numeric_selection_prompt(src) == prompt
        sizes[side] += 1
        with pytest.raises(api.NumericEvidenceError):
            api.numeric_selection_prompt(src)
    monkeypatch.setattr(api, "_provider_schema_bytes_v5", original)
    old = api.NUMERIC_SELECTION_INSTRUCTIONS
    monkeypatch.setattr(api, "NUMERIC_SELECTION_INSTRUCTIONS", old + "a" * spare)
    assert api.numeric_selection_prompt(src) == prompt
    monkeypatch.setattr(api, "NUMERIC_SELECTION_INSTRUCTIONS", old + "a" * (spare + 1))
    with pytest.raises(api.NumericEvidenceError):
        api.numeric_selection_prompt(src)


def test_import_create_prompt_validate_are_lazy_no_key_request_write_or_model_lifecycle(
    monkeypatch,
):
    api = sdk()
    original_namespace = vars(api).copy()
    try:
        src = document("A 10")
        proposal = pure(src, [fact()])
        model, calls = model_response({"facts": [], "relations": []})

        def forbidden(*args, **kwargs):
            pytest.fail("Unexpected client/key/file/model lifecycle")

        import builtins
        import os

        import openai

        monkeypatch.setattr(openai.AsyncOpenAI, "__init__", forbidden)
        monkeypatch.setattr(openai.OpenAI, "__init__", forbidden)
        monkeypatch.setattr(api.Agent, "__init__", forbidden)
        monkeypatch.setattr(builtins, "open", forbidden)
        original_getenv = os.getenv

        def no_credentials(key, *args):
            if "KEY" in key or "TOKEN" in key:
                forbidden()
            return original_getenv(key, *args)

        monkeypatch.setattr(os, "getenv", no_credentials)
        original_getitem = type(os.environ).__getitem__

        def no_environ_credentials(environ, key):
            if "KEY" in key or "TOKEN" in key:
                forbidden()
            return original_getitem(environ, key)

        monkeypatch.setattr(type(os.environ), "__getitem__", no_environ_credentials)
        monkeypatch.setattr(api, "Agent", forbidden)
        monkeypatch.setattr(FunctionModel, "__aenter__", forbidden)
        monkeypatch.setattr(FunctionModel, "__aexit__", forbidden)
        importlib.reload(api)
        monkeypatch.setattr(api, "Agent", forbidden)
        selector = api.create_numeric_selector(model)
        assert selector.model is model
        assert api.numeric_selection_prompt(src)
        assert (
            api.validate_numeric_selection(src, proposal.model_dump(mode="json")).status
            == "unreviewed"
        )
        assert calls == []
        with pytest.raises(api.NumericEvidenceError):
            api.create_numeric_selector(None)

    finally:
        # Cached evaluators may retain these exact proposal model classes.
        vars(api).clear()
        vars(api).update(original_namespace)


def test_run_borrows_without_enter_exit_or_closing(sync_model_loop, monkeypatch):
    api = sdk()

    def forbidden(*args, **kwargs):
        pytest.fail("Borrowed Model lifecycle called")

    monkeypatch.setattr(FunctionModel, "__aenter__", forbidden)
    monkeypatch.setattr(FunctionModel, "__aexit__", forbidden)
    model, calls = model_response({"facts": [], "relations": []})
    assert (
        api.run_numeric_selector(api.create_numeric_selector(model), document("A 10")).facts == ()
    )
    assert len(calls) == 1


def test_subclass_declared_extra_is_not_silently_dropped_by_typed_serialization():
    api = sdk()
    src = document("A 10")
    result = pure(src, [fact(subject=anchor("A"))])

    class ExtraAnchor(api.ResolvedAnchor):
        verified: bool

    widened = ExtraAnchor(**result.facts[0].subject.model_dump(), verified=True)
    unchecked = result.model_copy(
        update={"facts": (result.facts[0].model_copy(update={"subject": widened}),)}
    )
    with pytest.raises(api.NumericEvidenceError):
        api.validate_numeric_selection(src, unchecked)

    class ExtraProviderAnchor(api.SentenceAnchor):
        verified: bool

    provider = api._ProviderOutput.model_validate_json(
        json.dumps({"facts": [fact(subject=anchor("A"))], "relations": []})
    )
    widened_provider = ExtraProviderAnchor(sentence_id="s1", text="A", verified=True)
    unchecked_provider = provider.model_copy(
        update={"facts": (provider.facts[0].model_copy(update={"subject": widened_provider}),)}
    )
    with pytest.raises(ValueError):
        api._build_proposal(src, unchecked_provider, result.usage)


def test_thousand_character_anchor_and_twenty_sentence_statement_are_supported():
    src = document("A" * 1000 + " 10. " + "빈문장. " * 18 + "중 B 2.")
    result = pure(
        src,
        [fact(subject=anchor("A" * 1000)), fact("n2", subject=anchor("B", "s20"))],
        [relation(sentences=tuple(f"s{i}" for i in range(1, 21)), cue=anchor("중", "s20"))],
    )
    assert len(result.facts[0].subject.span.text) == 1000
    assert len(result.relations[0].statement_sentence_ids) == 20
    assert result.relations[0].statement.text == src[1].citations[0].selector.quote


def test_null_units_signed_two_atom_open_bounds_and_lexical_hints_remain_exact():
    src = document("A 1호~2. B 최소 -2~-1명 이상. 날짜 2026-10-20. 제12조.")
    result = pure(src, [fact(), fact("n2"), fact("n3"), fact("n4")])
    candidates = result.candidate_index.candidates
    assert [(a.number.text, a.unit.text if a.unit else None) for a in candidates[0].atoms] == [
        ("1", "호"),
        ("2", None),
    ]
    assert [(a.number.text, a.unit.text if a.unit else None) for a in candidates[1].atoms] == [
        ("-2", None),
        ("-1", "명"),
    ]
    assert [q.text for q in candidates[1].qualifiers] == ["최소", "이상"]
    assert candidates[2].lexical_kind == "temporal" and candidates[3].lexical_kind == "identifier"
    # Lexical hints do not claim to certify which source quantities matter semantically.
    assert sdk().validate_numeric_selection(src, result).status == "unreviewed"


def test_statement_must_contain_selected_subject_physical_occurrence_not_same_text_elsewhere():
    src = document("A 10 중 B 2. A 3.")
    facts = [fact(subject=anchor("A", "s2")), fact("n2", subject=anchor("B"))]
    with pytest.raises(ValueError):
        pure(src, facts, [relation()])
    assert len(pure(src, facts, [relation(sentences=("s1", "s2"))]).relations) == 1


def test_prompt_actual_byte_boundary_and_framing_output_reserves(monkeypatch):
    api = sdk()
    short = document("1 " + "x" * 100)
    prompt, tools = api._preflight(short)
    overhead = (
        len(api.NUMERIC_SELECTION_INSTRUCTIONS.encode())
        + max(api._provider_schema_bytes_v5(tools))
        + 2048
        + 2500
    )
    # Increasing the single ASCII tail by one adds one byte to source and sentence catalog.
    spare = 20000 - overhead - len(prompt.encode())
    count = 100 + spare // 2
    accepted = document("1 " + "x" * count)
    accepted_prompt = api.numeric_selection_prompt(accepted)
    accepted_envelope = overhead + len(accepted_prompt.encode())
    assert accepted_envelope in {19999, 20000}
    with pytest.raises(api.NumericEvidenceError):
        api.numeric_selection_prompt(document("1 " + "x" * (count + 1)))
    reserve_extra = 20001 - accepted_envelope
    monkeypatch.setattr(api, "PROVIDER_FRAMING_ALLOWANCE", 2048 + reserve_extra)
    with pytest.raises(api.NumericEvidenceError):
        api.numeric_selection_prompt(accepted)
    monkeypatch.setattr(api, "PROVIDER_FRAMING_ALLOWANCE", 2048)
    monkeypatch.setattr(api, "MAX_OUTPUT_TOKENS", 2500 + reserve_extra)
    with pytest.raises(api.NumericEvidenceError):
        api.numeric_selection_prompt(accepted)


def test_real_raw_and_openai_normalized_schema_both_keep_current_enums_and_known_nonnull():
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    api = sdk()
    src = document("A 1. B 2.")
    _, tools = api._preflight(src)
    raw = tools[0].output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    normalized = OpenAIJsonSchemaTransformer(raw, strict=True).walk()
    for schema in (raw, normalized):
        for row in schema["$defs"].values():
            props = row["properties"]
            if "candidate_id" in props:
                assert props["candidate_id"]["enum"] == ["n1", "n2"]
            if "sentence_id" in props:
                assert props["sentence_id"]["enum"] == ["s1", "s2"]
            if "kind" in props and "text" in props and "enum" in props["kind"]:
                assert "$ref" in props["text"] and "anyOf" not in props["text"]


def test_zero_known_usage_is_accepted_without_fabricating_transport_receipt():
    api = sdk()
    result = pure(
        document("A 10"), usage=api.KnownUsage(input_tokens=0, output_tokens=0, requests=1)
    )
    assert (result.usage.input_tokens, result.usage.output_tokens, result.usage.requests) == (
        0,
        0,
        1,
    )


def test_source_subclass_extra_cannot_disappear_during_canonical_revalidation():
    api = sdk()
    src = document("A 10")

    class ExtraRepresentation(type(src[1].representation)):
        verified: bool

    widened = ExtraRepresentation(**src[1].representation.model_dump(), verified=True)
    src = src[0], src[1].model_copy(update={"representation": widened}), src[2]
    with pytest.raises(api.NumericEvidenceError):
        api.numeric_selection_prompt(src)


def test_cold_sdk_import_and_create_do_not_lookup_keys_or_allocate_clients():
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
openai.OpenAI.__init__ = forbidden
pydantic_ai.Agent.__init__ = forbidden
original = type(os.environ).__getitem__
def no_key(self, key):
    if key == "OPENAI_API_KEY":
        raise AssertionError("Unexpected key lookup")
    return original(self, key)
type(os.environ).__getitem__ = no_key
from issuedigest_agents.numeric_selection import create_numeric_selector
create_numeric_selector(FunctionModel(lambda messages, info: None))
"""
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
