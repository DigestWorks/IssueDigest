"""Synthetic contextual frames: exact structure remains unreviewed."""

import importlib
import importlib.util
import json
import sys
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import Field, create_model
from test_numeric_evidence import document

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


@pytest.fixture(scope="module", autouse=True)
def restore_new_module_imports():
    names = (
        "issuedigest_agents.contextual_frame",
        "issuedigest_agents.contextual_anchor",
        "issuedigest_agents.numeric_frame",
        "issuedigest_agents.numeric_selection_evaluation",
        "issuedigest_agents.numeric_selection",
    )
    introduced = [name for name in names if name not in sys.modules]
    yield
    for name in introduced:
        sys.modules.pop(name, None)


def api():
    name = "issuedigest_agents.contextual_frame"
    assert importlib.util.find_spec(name) is not None, "Missing contextual frame implementation"
    return importlib.import_module(name)


def anchor(text, context=None, sentence="s1"):
    return {"sentence_id": sentence, "text": text, "context_text": context}


def fact(candidate="n1", **fields):
    return {
        "candidate_id": candidate,
        **dict.fromkeys(ROLES),
        "value_status": "unknown",
        "reporting_tense": "unknown",
        **fields,
    }


def relation(from_id="n2", to_id="n1", cue=None, sentences=("s1",), kind="included_in"):
    return {
        "from_id": from_id,
        "to_id": to_id,
        "kind": kind,
        "statement_sentence_ids": list(sentences),
        "cue": cue or anchor("포함"),
    }


def repeated():
    src = document("🧪 전체 전월비 100명 포함, 소계 전월비 40명 포함, 하위 10명 포함.")
    rows = [
        fact(measured_entity=anchor("전체"), comparison_baseline=anchor("전월비", "전체 전월비")),
        fact(
            "n2",
            measured_entity=anchor("소계"),
            comparison_baseline=anchor("전월비", "소계 전월비"),
        ),
        fact("n3", measured_entity=anchor("하위")),
    ]
    rels = [
        relation("n3", "n2", anchor("포함", "하위 10명 포함")),
        relation("n2", "n1", anchor("포함", "소계 전월비 40명 포함")),
    ]
    return src, {"facts": rows, "relations": rels}


def test_repeated_roles_and_cues_keep_short_offsets_full_statements_and_input():
    mod = api()
    src, data = repeated()
    result = mod.build_contextual_frame(src, data)
    assert (result.profile, result.status) == ("numeric-contextual-frame-v1", "unreviewed")
    assert result.input.model_dump(mode="json") == data
    assert [
        (f.comparison_baseline.span.start, f.comparison_baseline.span.end)
        for f in result.resolved.facts[:2]
    ] == [(5, 8), (21, 24)]
    assert [r.cue.span.text for r in result.resolved.relations] == ["포함", "포함"]
    assert [(r.from_id, r.to_id) for r in result.resolved.relations] == [("n3", "n2"), ("n2", "n1")]
    assert [r.cue.span.start for r in result.resolved.relations] == [40, 29]
    assert all(
        r.statement.text == src[1].citations[0].selector.quote for r in result.resolved.relations
    )
    assert mod.validate_contextual_frame(src, result) == result
    assert mod.validate_contextual_frame(src, json.loads(result.model_dump_json())) == result
    assert mod.build_contextual_frame(src, result.input) == result


@pytest.mark.parametrize("role", ROLES)
def test_each_role_uses_context_and_requires_nullable_context_field(role):
    mod = api()
    src = document("A A 10명.")
    result = mod.build_contextual_frame(
        src, {"facts": [fact(**{role: anchor("A", "A 10명")})], "relations": []}
    )
    assert getattr(result.resolved.facts[0], role).span.start == 2
    for selected in [anchor("A"), {"sentence_id": "s1", "text": "A"}]:
        with pytest.raises(mod.ContextualFrameError):
            mod.build_contextual_frame(src, {"facts": [fact(**{role: selected})], "relations": []})


@pytest.mark.parametrize("status", ["observed", "planned", "forecast", "unknown"])
@pytest.mark.parametrize("tense", ["past", "present", "future", "unknown"])
def test_existing_status_tense_constraints_are_inherited(status, tense):
    mod = api()
    src = document("기관 10명 전망 발표했다.")
    row = fact(
        value_status=status,
        reporting_tense=tense,
        status_text=anchor("전망"),
        reporting_tense_text=anchor("발표했다"),
    )
    result = mod.build_contextual_frame(src, {"facts": [row], "relations": []})
    assert (result.resolved.facts[0].value_status, result.resolved.facts[0].reporting_tense) == (
        status,
        tense,
    )
    for name, known in [
        ("status_text", status != "unknown"),
        ("reporting_tense_text", tense != "unknown"),
    ]:
        if known:
            with pytest.raises(mod.ContextualFrameError):
                mod.build_contextual_frame(src, {"facts": [{**row, name: None}], "relations": []})


@pytest.mark.parametrize(
    "text,selected,start,end",
    [
        ("🧪 e\u0301 e\u0301 10명.", anchor("e\u0301", "e\u0301 10명"), 5, 7),
        ("ababa 10명.", anchor("aba", "baba"), 2, 5),
        ("A 10명.", anchor("A"), 0, 1),
    ],
)
def test_unicode_overlap_and_no_context_unique_compatibility(text, selected, start, end):
    result = api().build_contextual_frame(
        document(text), {"facts": [fact(measured_entity=selected)], "relations": []}
    )
    span = result.resolved.facts[0].measured_entity.span
    assert (span.start, span.end, span.text) == (start, end, selected["text"])


@pytest.mark.parametrize(
    "text,selected",
    [
        ("aaaa 10명.", anchor("a", "aa")),
        ("X aaaa 10명.", anchor("aa", "X aaaa")),
        ("A 10명. B 20명.", anchor("명", "명. B")),
        ("A A 10명.", anchor("A", "absent")),
        ("A A 10명.", anchor("A", "10명")),
        ("e\u0301 10명.", anchor("é", "e\u0301 10명")),
    ],
)
def test_invalid_context_never_falls_back_or_repairs(text, selected):
    with pytest.raises(api().ContextualFrameError):
        api().build_contextual_frame(
            document(text), {"facts": [fact(measured_entity=selected)], "relations": []}
        )


@pytest.mark.parametrize(
    "mutation",
    ["duplicate", "missing", "pair", "cycle", "noncontiguous", "outside", "quote", "extra", "cap"],
)
def test_existing_whole_frame_relation_and_quote_constraints_reject(mutation):
    mod = api()
    src, data = repeated()
    if mutation == "duplicate":
        data["facts"].append(deepcopy(data["facts"][0]))
    elif mutation == "missing":
        del data["facts"][0]["period"]
    elif mutation == "pair":
        data["relations"].append(
            relation("n1", "n2", anchor("포함", "하위 10명 포함"), kind="parallel")
        )
    elif mutation == "cycle":
        data["relations"].append(relation("n1", "n3", anchor("포함", "하위 10명 포함")))
    elif mutation in {"noncontiguous", "outside"}:
        src = document("전체 100명. 소계 40명 포함. 하위 10명 포함.")
        data = {
            "facts": [
                fact(measured_entity=anchor("전체")),
                fact("n2", measured_entity=anchor("소계", sentence="s2")),
            ],
            "relations": [
                relation(
                    cue=anchor("포함", sentence="s2"),
                    sentences=("s1", "s3") if mutation == "noncontiguous" else ("s2",),
                )
            ],
        }
    elif mutation == "quote":
        src = document("A 10명.", "B 20명.")
        data = {"facts": [fact(measured_entity=anchor("B", sentence="s2"))], "relations": []}
    elif mutation == "extra":
        data["facts"][0]["measured_entity"]["start"] = 2
    else:
        data["relations"] *= 9
    with pytest.raises(mod.ContextualFrameError, match="^Invalid contextual frame input$"):
        mod.build_contextual_frame(src, data)


@pytest.mark.parametrize(
    "path,value",
    [
        (("profile",), "reviewed"),
        (("status",), "reviewed"),
        (("input", "facts", 0, "comparison_baseline", "context_text"), "소계 전월비"),
        (("input", "facts", 0, "measured_entity", "text"), "소계"),
        (("resolved", "candidate_index", "source_sha256"), "0" * 64),
        (("resolved", "candidate_index", "snapshot_id"), str(uuid4())),
        (("resolved", "candidate_index", "workspace_id"), str(uuid4())),
        (("resolved", "candidate_index", "citations", 0, "quote"), "forged"),
        (("resolved", "facts", 0, "comparison_baseline", "span", "start"), 22),
        (("resolved", "facts", 0, "measured_entity", "span", "start"), False),
        (("resolved", "facts", 0, "value_status"), "planned"),
        (("resolved", "relations", 0, "cue", "span", "text"), "forged"),
        (("resolved", "relations", 0, "statement", "text"), "forged"),
        (("resolved", "relations", 0, "from_id"), "n1"),
        (("input", "secret"), "hidden"),
        (("resolved", "secret"), "hidden"),
    ],
)
def test_wrapper_reconstruction_rejects_mutation(path, value):
    mod = api()
    src, data = repeated()
    raw = mod.build_contextual_frame(src, data).model_dump(mode="json")
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(mod.ContextualFrameError, match="^Invalid contextual frame$"):
        mod.validate_contextual_frame(src, raw)


@pytest.mark.parametrize(
    "node",
    ["root", "input", "fact", "anchor", "relation", "cue", "resolved", "resolved_fact", "span"],
)
@pytest.mark.parametrize("kind", ["hidden", "extra", "pydantic_extra", "construct"])
def test_canonical_nodes_are_checked_before_dump(node, kind):
    mod = api()
    src, data = repeated()
    result = mod.build_contextual_frame(src, data)

    def forge(item):
        if kind == "hidden":
            cls = create_model("Hidden", __base__=type(item), secret=(str, Field(exclude=True)))
            return cls(**item.model_dump(), secret="hidden")
        copied = item.model_copy()
        if kind == "extra":
            copied.__dict__["secret"] = "hidden"
        elif kind == "pydantic_extra":
            object.__setattr__(copied, "__pydantic_extra__", {"secret": "hidden"})
        else:
            name = next(iter(type(item).model_fields))
            copied = type(item).model_construct(**{**item.__dict__, name: True})
        return copied

    if node == "root":
        result = forge(result)
    elif node == "resolved":
        result = result.model_copy(update={"resolved": forge(result.resolved)})
    elif node in {"resolved_fact", "span"}:
        row = result.resolved.facts[0]
        if node == "resolved_fact":
            row = forge(row)
        else:
            resolved = row.measured_entity.model_copy(
                update={"span": forge(row.measured_entity.span)}
            )
            row = row.model_copy(update={"measured_entity": resolved})
        result = result.model_copy(
            update={
                "resolved": result.resolved.model_copy(
                    update={"facts": (row, *result.resolved.facts[1:])}
                )
            }
        )
    else:
        data = result.input
        if node == "input":
            data = forge(data)
        elif node in {"fact", "anchor"}:
            row = data.facts[0]
            row = (
                forge(row)
                if node == "fact"
                else row.model_copy(update={"measured_entity": forge(row.measured_entity)})
            )
            data = data.model_copy(update={"facts": (row, *data.facts[1:])})
        else:
            rel = data.relations[0]
            rel = (
                forge(rel) if node == "relation" else rel.model_copy(update={"cue": forge(rel.cue)})
            )
            data = data.model_copy(update={"relations": (rel, *data.relations[1:])})
        result = result.model_copy(update={"input": data})
        with pytest.raises(mod.ContextualFrameError):
            mod.build_contextual_frame(src, data)
    with pytest.raises(mod.ContextualFrameError):
        mod.validate_contextual_frame(src, result)


def test_empty_frame_preserves_numeric_atoms_and_current_source():
    mod = api()
    src = document("A 9만 9000명 이상. B 1~2호.")
    result = mod.build_contextual_frame(src, {"facts": [], "relations": []})
    assert result.resolved.candidate_index.candidates[1].atoms[0].unit is None
    assert [c.expression.text for c in result.resolved.candidate_index.candidates] == [
        "9만 9000명 이상",
        "1~2호",
    ]
    with pytest.raises(mod.ContextualFrameError):
        mod.validate_contextual_frame(document("A 9만 9001명 이상. B 1~2호."), result)
