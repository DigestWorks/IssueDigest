"""Synthetic exact role frames; structural validity never certifies semantic truth."""

import builtins
import importlib
import importlib.util
import io
import json
import os
import socket
import sys
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import pytest
from issuedigest_agents.numeric_candidates import build_numeric_candidates
from pydantic import Field, create_model
from test_numeric_evidence import document
from test_numeric_selection import anchor, relation

ROLES = (
    "measured_entity",
    "reporting_actor",
    "period",
    "logical_condition",
    "forecast_basis",
    "comparison_baseline",
    "reporting_tense_text",
    "status_text",
)


@pytest.fixture(scope="module", autouse=True)
def restore_new_module_imports():
    # Frozen selection tests intentionally reload their module. Do not leave a newly
    # imported evaluator caching the old proposal class for the later evaluator tests.
    names = (
        "issuedigest_agents.numeric_frame",
        "issuedigest_agents.numeric_selection_evaluation",
    )
    introduced = [name for name in names if name not in sys.modules]
    yield
    for name in introduced:
        sys.modules.pop(name, None)


def api():
    name = "issuedigest_agents.numeric_frame"
    assert importlib.util.find_spec(name) is not None, "Missing pure numeric evidence frame"
    return importlib.import_module(name)


def fact(candidate="n1", **fields):
    return {
        "candidate_id": candidate,
        **dict.fromkeys(ROLES),
        "value_status": "unknown",
        "reporting_tense": "unknown",
        **fields,
    }


def build(src, facts=(), relations=()):
    return api().build_numeric_frame(src, {"facts": list(facts), "relations": list(relations)})


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


def trio():
    src = document("전체 100명 중 소계 40명 중 하위 10명 포함.")
    rows = [
        fact("n1", measured_entity=anchor("전체")),
        fact("n2", measured_entity=anchor("소계")),
        fact("n3", measured_entity=anchor("하위")),
    ]
    return src, rows


def test_roles_preserve_measured_entity_forecast_and_past_reporting_separately():
    src, row = rich()
    result = build(src, [row])
    assert (result.profile, result.status) == ("numeric-evidence-frame-v1", "unreviewed")
    assert result.candidate_index == build_numeric_candidates(src)
    resolved = result.facts[0]
    assert {role: getattr(resolved, role).span.text for role in ROLES} == {
        "measured_entity": "취업자",
        "reporting_actor": "기관",
        "period": "내년",
        "logical_condition": "조건 충족 시",
        "forecast_basis": "수요 증가를 근거로",
        "comparison_baseline": "전월비",
        "reporting_tense_text": "발표했다",
        "status_text": "전망",
    }
    assert (resolved.value_status, resolved.reporting_tense) == ("forecast", "past")
    assert (resolved.reporting_actor.span.start, resolved.reporting_actor.span.end) == (2, 4)
    assert set(resolved.model_dump()) == {"candidate_id", "value_status", "reporting_tense", *ROLES}
    assert not {"value", "unit", "number", "qualifier", "usage"} & set(resolved.model_dump())
    assert api().validate_numeric_frame(src, result) == result


@pytest.mark.parametrize("value_status", ["observed", "planned", "forecast", "unknown"])
@pytest.mark.parametrize("reporting_tense", ["past", "present", "future", "unknown"])
def test_explicit_value_status_and_reporting_tense_are_independent(value_status, reporting_tense):
    src = document("기관 10명 계획을 발표했다.")
    result = build(
        src,
        [
            fact(
                measured_entity=anchor("기관"),
                reporting_actor=anchor("기관"),
                value_status=value_status,
                status_text=anchor("계획"),
                reporting_tense=reporting_tense,
                reporting_tense_text=anchor("발표했다"),
            )
        ],
    )
    row = result.facts[0]
    assert (row.value_status, row.reporting_tense) == (value_status, reporting_tense)
    assert row.measured_entity == row.reporting_actor


def test_nullable_unknown_empty_selection_and_cross_sentence_roles_are_valid():
    src = document("A 10명. 내년 전망.")
    result = build(src, [fact(period=anchor("내년", "s2"))])
    assert result.facts[0].period.span.text == "내년"
    assert result.facts[0].value_status == result.facts[0].reporting_tense == "unknown"
    assert all(getattr(result.facts[0], role) is None for role in ROLES if role != "period")
    assert (build(src).facts, build(src).relations) == ((), ())
    no_numbers = document("수치 없음.")
    assert build(no_numbers).candidate_index.candidates == ()


def test_structurally_valid_wrong_semantic_entity_stays_unreviewed():
    src, row = rich()
    row["measured_entity"] = anchor("기관")
    result = build(src, [row])
    assert result.facts[0].measured_entity.span.text == "기관"
    assert result.status == "unreviewed"
    assert api().validate_numeric_frame(src, result) == result


def test_candidate_index_alone_owns_ranges_units_open_bounds_and_selection_order():
    src = document("A 9만 9000명 이상. B 1~2호. C 1호~2호.")
    result = build(src, [fact("n3"), fact("n1"), fact("n2")])
    assert [f.candidate_id for f in result.facts] == ["n3", "n1", "n2"]
    assert [c.expression.text for c in result.candidate_index.candidates] == [
        "9만 9000명 이상",
        "1~2호",
        "1호~2호",
    ]
    assert result.candidate_index.candidates[1].atoms[0].unit is None


@pytest.mark.parametrize("kind", ["included_in", "parallel", "unknown"])
def test_direct_subgroup_to_subtotal_edges_are_preserved_without_aggregate_inference(kind):
    src, rows = trio()
    result = build(src, rows, [relation("n3", "n2", kind=kind, cue=anchor("포함"))])
    assert [(r.kind, r.from_id, r.to_id) for r in result.relations] == [(kind, "n3", "n2")]
    assert result.relations[0].statement.text == "전체 100명 중 소계 40명 중 하위 10명 포함."
    assert api().validate_numeric_frame(src, result) == result


def test_contiguous_multisentence_statement_keeps_intervening_whitespace():
    src = document("전체 100명.\n 소계 40명 포함.")
    result = build(
        src,
        [fact(measured_entity=anchor("전체")), fact("n2", measured_entity=anchor("소계", "s3"))],
        [relation(sentences=("s1", "s2", "s3"), cue=anchor("포함", "s3"))],
    )
    assert result.relations[0].statement.text == "전체 100명.\n 소계 40명 포함."


def test_public_models_and_json_dict_roundtrip_preserve_every_field():
    mod = api()
    src, row = rich()
    checked = mod.FrameFactInput.model_validate_json(json.dumps(row), strict=True)
    data = mod.NumericFrameInput(facts=(checked,), relations=())
    result = mod.build_numeric_frame(src, data)
    assert mod.build_numeric_frame(src, json.loads(data.model_dump_json())) == result
    assert mod.validate_numeric_frame(src, json.loads(result.model_dump_json())) == result
    assert (
        mod.NumericEvidenceFrame.model_validate_json(result.model_dump_json(), strict=True)
        == result
    )
    assert mod.FrameRelationInput.model_validate_json(json.dumps(relation()), strict=True).kind == (
        "included_in"
    )
    with pytest.raises(ValueError):
        result.status = "reviewed"


@pytest.mark.parametrize("field", [*ROLES, "value_status", "reporting_tense", "candidate_id"])
def test_every_fact_field_is_required_even_when_nullable(field):
    src = document("A 10명.")
    row = fact()
    del row[field]
    with pytest.raises(api().NumericFrameError):
        build(src, [row])


@pytest.mark.parametrize(
    "field,value",
    [
        ("candidate_id", True),
        ("candidate_id", "n99"),
        ("value_status", True),
        ("value_status", "actual"),
        ("reporting_tense", "yesterday"),
        ("reporting_tense", 1),
        ("value_status", None),
        ("reporting_tense", None),
    ],
)
def test_candidate_ids_and_status_literals_are_strict(field, value):
    with pytest.raises(api().NumericFrameError):
        build(document("A 10명."), [fact(**{field: value})])


@pytest.mark.parametrize(
    "field,value",
    [
        ("value_status", "observed"),
        ("value_status", "planned"),
        ("value_status", "forecast"),
        ("reporting_tense", "past"),
        ("reporting_tense", "present"),
        ("reporting_tense", "future"),
    ],
)
def test_known_status_or_tense_requires_its_own_explicit_text(field, value):
    with pytest.raises(api().NumericFrameError):
        build(document("A 10명."), [fact(**{field: value})])


@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize(
    "bad_anchor",
    [
        anchor(""),
        anchor("  "),
        anchor("x" * 1001),
        anchor("absent"),
        anchor("A", "s99"),
        anchor("A", True),
        anchor(True),
        {**anchor("A"), "start": 0},
    ],
)
def test_every_role_rejects_invalid_or_extended_anchor(role, bad_anchor):
    with pytest.raises(api().NumericFrameError):
        build(document("A 10명."), [fact(**{role: bad_anchor})])


@pytest.mark.parametrize("role", ROLES)
def test_every_role_rejects_another_quote(role):
    with pytest.raises(api().NumericFrameError):
        build(document("A 10명.", "B 20명."), [fact(**{role: anchor("B", "s2")})])


@pytest.mark.parametrize(
    "text,selected",
    [
        ("A A 10명.", anchor("A")),
        ("aaaa 10명.", anchor("aa")),
        ("A 10명. B 전망.", anchor("명. B")),
        ("e\u0301 10명.", anchor("é")),
    ],
)
def test_repeated_overlapping_cross_sentence_and_normalized_anchor_are_rejected(text, selected):
    with pytest.raises(api().NumericFrameError):
        build(document(text), [fact(measured_entity=selected)])


@pytest.mark.parametrize("level", ["input", "fact", "anchor", "relation"])
def test_extra_fields_are_rejected_at_every_input_level(level):
    raw = {"facts": [fact(measured_entity=anchor("A"))], "relations": []}
    target = raw
    if level == "fact":
        target = raw["facts"][0]
    elif level == "anchor":
        target = raw["facts"][0]["measured_entity"]
    elif level == "relation":
        raw["relations"] = [relation()]
        target = raw["relations"][0]
    target["synthetic-secret"] = "synthetic-private-text"
    with pytest.raises(api().NumericFrameError) as error:
        api().build_numeric_frame(document("A 10명."), raw)
    assert str(error.value) == "Invalid numeric frame input"
    assert error.value.__suppress_context__


def test_fact_and_relation_caps_and_duplicate_candidate_reject_whole_input():
    src = document(" ".join(f"A{i} {i}명." for i in range(14)))
    rows = [fact(f"n{i}") for i in range(1, 13)]
    assert len(build(src, rows).facts) == 12
    for bad in [rows + [fact("n13")], [fact(), fact()]]:
        with pytest.raises(api().NumericFrameError):
            build(src, bad)
    src, rows = trio()
    with pytest.raises(api().NumericFrameError):
        build(src, rows, [relation()] * 17)


@pytest.mark.parametrize(
    "mutation",
    [
        "self",
        "unselected",
        "duplicate_pair",
        "cycle",
        "noncontiguous",
        "reversed",
        "repeated_sentence",
        "unknown_sentence",
        "empty_statement",
        "too_long_statement",
        "no_entity",
        "entity_outside",
        "number_outside",
        "cue_outside",
        "unknown_cue",
        "different_quote",
        "bad_kind",
        "bool_endpoint",
        "missing_cue",
        "extra_cue",
    ],
)
def test_invalid_relations_reject_entire_frame(mutation):
    src = document("전체 100명. 소계 40명 포함. 하위 10명 설명.", "다른 20명.")
    rows = [
        fact(measured_entity=anchor("전체")),
        fact("n2", measured_entity=anchor("소계", "s2")),
        fact("n3", measured_entity=anchor("하위", "s3")),
        fact("n4", measured_entity=anchor("다른", "s4")),
    ]
    rel = relation(sentences=("s1", "s2", "s3"), cue=anchor("포함", "s2"))
    relations = [rel]
    if mutation == "self":
        rel["to_id"] = "n2"
    elif mutation == "unselected":
        rows.pop(0)
    elif mutation == "duplicate_pair":
        relations.append({**rel, "from_id": "n1", "to_id": "n2", "kind": "parallel"})
    elif mutation == "cycle":
        relations += [
            {**rel, "from_id": "n1", "to_id": "n3"},
            {**rel, "from_id": "n3", "to_id": "n2"},
        ]
    elif mutation == "noncontiguous":
        rel["statement_sentence_ids"] = ["s1", "s3"]
    elif mutation == "reversed":
        rel["statement_sentence_ids"] = ["s2", "s1"]
    elif mutation == "repeated_sentence":
        rel["statement_sentence_ids"] = ["s1", "s1"]
    elif mutation == "unknown_sentence":
        rel["statement_sentence_ids"] = ["s99"]
    elif mutation == "empty_statement":
        rel["statement_sentence_ids"] = []
    elif mutation == "too_long_statement":
        rel["statement_sentence_ids"] = ["s1"] * 21
    elif mutation == "no_entity":
        rows[0]["measured_entity"] = None
    elif mutation == "entity_outside":
        rows[0]["measured_entity"] = anchor("하위", "s3")
        rel["statement_sentence_ids"] = ["s1", "s2"]
    elif mutation == "number_outside":
        rel["statement_sentence_ids"] = ["s2", "s3"]
    elif mutation == "cue_outside":
        rel["statement_sentence_ids"] = ["s1", "s2"]
        rel["cue"] = anchor("설명", "s3")
    elif mutation == "unknown_cue":
        rel["cue"] = anchor("secret-not-found")
    elif mutation == "different_quote":
        rel["statement_sentence_ids"] = ["s1", "s2", "s3", "s4"]
    elif mutation == "bad_kind":
        rel["kind"] = "sum"
    elif mutation == "bool_endpoint":
        rel["from_id"] = True
    elif mutation == "missing_cue":
        del rel["cue"]
    else:
        rel["cue"]["start"] = 0
    with pytest.raises(api().NumericFrameError):
        build(src, rows, relations)


def test_limits_accept_exactly_sixteen_explicit_unique_relation_pairs():
    src = document("A 1명 B 2명 C 3명 D 4명 E 5명 F 6명 G 7명 병렬.")
    rows = [fact(f"n{i}", measured_entity=anchor(name)) for i, name in enumerate("ABCDEFG", 1)]
    relations = [
        relation(f"n{i}", f"n{j}", kind="parallel", cue=anchor("병렬"))
        for i in range(1, 8)
        for j in range(i + 1, 8)
    ][:16]
    assert len(build(src, rows, relations).relations) == 16
    relations.append(relation("n6", "n7", kind="parallel", cue=anchor("병렬")))
    with pytest.raises(api().NumericFrameError):
        build(src, rows, relations)


@pytest.mark.parametrize(
    "mutation",
    [
        "offset",
        "bool_offset",
        "text",
        "profile",
        "status",
        "source_hash",
        "index_text",
        "index_omission",
        "index_extra",
        "fact_extra",
        "anchor_extra",
        "status_literal",
        "missing_text",
        "duplicate",
        "too_many",
        "statement",
        "cue_offset",
        "relation_extra",
    ],
)
def test_validation_reconstructs_and_rejects_forged_output(mutation):
    src, rows = trio()
    result = build(src, rows, [relation("n3", "n2", cue=anchor("포함"))])
    raw = result.model_dump(mode="json")
    span = raw["facts"][0]["measured_entity"]["span"]
    if mutation == "offset":
        span.update(start=1, end=3)
    elif mutation == "bool_offset":
        span["start"] = False
    elif mutation == "text":
        span["text"] = "변조"
    elif mutation == "profile":
        raw["profile"] = "numeric-selection-v1"
    elif mutation == "status":
        raw["status"] = "reviewed"
    elif mutation == "source_hash":
        raw["candidate_index"]["source_sha256"] = "0" * 64
    elif mutation == "index_text":
        raw["candidate_index"]["citations"][0]["quote"] = "forged"
    elif mutation == "index_omission":
        raw["candidate_index"]["candidates"].pop()
    elif mutation == "index_extra":
        raw["candidate_index"]["secret"] = "private"
    elif mutation == "fact_extra":
        raw["facts"][0]["value"] = "100"
    elif mutation == "anchor_extra":
        span["occurrence"] = 0
    elif mutation == "status_literal":
        raw["facts"][0]["value_status"] = "actual"
    elif mutation == "missing_text":
        raw["facts"][0]["reporting_tense"] = "past"
    elif mutation == "duplicate":
        raw["facts"].append(deepcopy(raw["facts"][0]))
    elif mutation == "too_many":
        raw["facts"] *= 5
    elif mutation == "statement":
        raw["relations"][0]["statement"]["text"] = "X"
    elif mutation == "cue_offset":
        raw["relations"][0]["cue"]["span"].update(start=0, end=1)
    else:
        raw["relations"][0]["secret"] = "private"
    with pytest.raises(api().NumericFrameError) as error:
        api().validate_numeric_frame(src, raw)
    assert str(error.value) == "Invalid numeric frame"
    assert error.value.__suppress_context__


@pytest.mark.parametrize("mutation", ["snapshot", "quote", "metadata", "unchecked_extra"])
def test_current_source_is_revalidated_for_build_and_validation(mutation):
    src, row = rich()
    result = build(src, [row])
    sid, bundle, presentation = src
    if mutation == "snapshot":
        sid = uuid4()
        presentation = presentation.model_copy(update={"snapshot_id": sid})
    elif mutation == "quote":
        item = bundle.citations[0]
        bundle = bundle.model_copy(
            update={
                "citations": (
                    item.model_copy(
                        update={"selector": item.selector.model_copy(update={"quote": "X"})}
                    ),
                )
            }
        )
    elif mutation == "metadata":
        presentation = presentation.model_copy(update={"title": ""})
    else:
        bundle = bundle.model_copy(update={"secret": "private"})
    changed = sid, bundle, presentation
    with pytest.raises(api().NumericFrameError):
        api().validate_numeric_frame(changed, result)
    if mutation != "snapshot":
        with pytest.raises(api().NumericFrameError):
            build(changed, [row])


def hidden(item):
    subclass = create_model(
        "SyntheticHidden", __base__=type(item), private_field=(str, Field(exclude=True))
    )
    return subclass(**item.model_dump(), private_field="synthetic-private-text")


@pytest.mark.parametrize(
    "target",
    [
        "input",
        "input_fact",
        "input_anchor",
        "input_relation",
        "source_citation",
        "source_selector",
        "output",
        "output_fact",
        "output_anchor",
        "output_span",
        "output_index",
        "output_candidate",
        "output_relation",
        "output_cue",
    ],
)
def test_hidden_excluded_subclasses_are_rejected_before_dump(target):
    mod = api()
    src, rows = trio()
    data = mod.NumericFrameInput.model_validate_json(
        json.dumps({"facts": rows, "relations": [relation("n3", "n2", cue=anchor("포함"))]}),
        strict=True,
    )
    result = mod.build_numeric_frame(src, data)
    if target == "input":
        data = hidden(data)
    elif target == "input_fact":
        data = data.model_copy(update={"facts": (hidden(data.facts[0]), *data.facts[1:])})
    elif target == "input_anchor":
        first = data.facts[0].model_copy(
            update={"measured_entity": hidden(data.facts[0].measured_entity)}
        )
        data = data.model_copy(update={"facts": (first, *data.facts[1:])})
    elif target == "input_relation":
        data = data.model_copy(update={"relations": (hidden(data.relations[0]),)})
    elif target.startswith("source"):
        sid, bundle, presentation = src
        item = bundle.citations[0]
        item = (
            hidden(item)
            if target == "source_citation"
            else item.model_copy(update={"selector": hidden(item.selector)})
        )
        src = sid, bundle.model_copy(update={"citations": (item,)}), presentation
    elif target == "output":
        result = hidden(result)
    elif target in {"output_fact", "output_anchor", "output_span"}:
        first = result.facts[0]
        if target == "output_fact":
            first = hidden(first)
        else:
            selected = first.measured_entity
            selected = (
                hidden(selected)
                if target == "output_anchor"
                else selected.model_copy(update={"span": hidden(selected.span)})
            )
            first = first.model_copy(update={"measured_entity": selected})
        result = result.model_copy(update={"facts": (first, *result.facts[1:])})
    elif target in {"output_index", "output_candidate"}:
        index = result.candidate_index
        index = (
            hidden(index)
            if target == "output_index"
            else index.model_copy(
                update={"candidates": (hidden(index.candidates[0]), *index.candidates[1:])}
            )
        )
        result = result.model_copy(update={"candidate_index": index})
    else:
        rel = result.relations[0]
        rel = (
            hidden(rel)
            if target == "output_relation"
            else rel.model_copy(update={"cue": hidden(rel.cue)})
        )
        result = result.model_copy(update={"relations": (rel,)})
    if target.startswith("input") or target.startswith("source"):
        with pytest.raises(mod.NumericFrameError):
            mod.build_numeric_frame(src, data)
    if not target.startswith("input"):
        with pytest.raises(mod.NumericFrameError):
            mod.validate_numeric_frame(src, result)


@pytest.mark.parametrize("target", ["input", "input_fact", "output_fact", "output_span"])
def test_unchecked_constructs_and_model_copy_do_not_bypass_validation(target):
    mod = api()
    src, row = rich()
    data = mod.NumericFrameInput.model_validate_json(json.dumps({"facts": [row], "relations": []}))
    result = mod.build_numeric_frame(src, data)
    if target == "input":
        data = mod.NumericFrameInput.model_construct(
            facts=data.facts, relations=(), secret="hidden"
        )
        # Pydantic construct can drop extras; an unchecked required invalid value must still fail.
        data.__dict__["secret"] = "hidden"
    elif target == "input_fact":
        first = data.facts[0].model_copy(update={"reporting_tense": True})
        data = data.model_copy(update={"facts": (first,)})
    elif target == "output_fact":
        first = result.facts[0].model_copy(update={"value_status": "secret"})
        result = result.model_copy(update={"facts": (first,)})
    else:
        selected = result.facts[0].measured_entity
        selected = selected.model_copy(
            update={"span": selected.span.model_copy(update={"start": True})}
        )
        result = result.model_copy(
            update={"facts": (result.facts[0].model_copy(update={"measured_entity": selected}),)}
        )
    with pytest.raises(mod.NumericFrameError):
        if target.startswith("input"):
            mod.build_numeric_frame(src, data)
        else:
            mod.validate_numeric_frame(src, result)


def test_import_and_run_have_no_external_io_except_pydantic_plugin_configuration(monkeypatch):
    src, row = rich()
    name = "issuedigest_agents.numeric_frame"
    spec = importlib.util.find_spec(name)
    assert spec is not None, "Missing pure numeric evidence frame"
    module = importlib.util.module_from_spec(spec)

    def forbidden(*args, **kwargs):
        raise AssertionError("Frame attempted external I/O")

    def plugin_configuration(name, default=None):
        if name != "PYDANTIC_DISABLE_PLUGINS":
            forbidden()
        return None

    with monkeypatch.context() as patch:
        for obj, attr in [
            (builtins, "open"),
            (io, "open"),
            (Path, "open"),
            (os, "getenv"),
            (type(os.environ), "__getitem__"),
            (socket, "socket"),
            (socket, "create_connection"),
        ]:
            patch.setattr(obj, attr, forbidden)
        patch.setattr(os, "getenv", plugin_configuration)
        spec.loader.exec_module(module)
        result = module.build_numeric_frame(src, {"facts": [row], "relations": []})
        assert module.validate_numeric_frame(src, result).status == "unreviewed"
