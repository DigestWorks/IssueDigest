"""Synthetic exact aliases/directions; source linkage never certifies semantic direction."""

import importlib
import importlib.util
import json
from copy import deepcopy
from functools import cache

import pytest
from pydantic import Field, create_model
from test_numeric_evidence import document
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.role_alias_contract"
    assert importlib.util.find_spec(name) is not None, "Missing role alias contract"
    return importlib.import_module(name)


def anchor(text, sentence="s1", context=None):
    return dict(s=sentence, t=text, c=context)


def packet():
    return dict(
        contexts=[
            dict(
                id="c1",
                event="e1",
                entity=anchor("이용자"),
                scopes=[],
                period=None,
                status="unknown",
                condition=None,
                purpose=None,
                basis=None,
                baseline=None,
            )
        ],
        events=[dict(id="e1", kind="unknown", actor=None, predicate=None, tense="unknown")],
        bindings=[
            dict(
                number="n1",
                context="c1",
                scopes=[],
                status_sentence=None,
                change=dict(direction="increase", evidence=anchor("증가"), support=["s1"]),
            )
        ],
        relations=[],
    )


@cache
def source():
    return document("이용자 약\t37여 명 내외 증가, 학교 83개교 감소.")


def test_exact_aliases_reconstruct_full_v2_and_explicit_direction_without_repair():
    mod = api()
    src, data = source(), packet()
    result = mod.build_role_alias_frame(src, data)
    assert result.profile == "role-alias-frame-v1" and result.status == "unreviewed"
    assert result.input.model_dump(mode="json") == data
    assert result.frame.input.contexts[0].measured_variable.text == "이용자"
    assert [c.expression.text for c in result.frame.candidate_index.candidates] == [
        "약\t37여 명 내외",
        "83개교",
    ]
    change = result.changes[0]
    assert change.candidate_id == "n1" and change.change.direction == "increase"
    assert change.change.evidence.span.text == "증가"
    assert change.change.statement.text == src[1].citations[0].selector.quote
    assert mod.validate_role_alias_frame(src, result) == result
    assert mod.validate_role_alias_frame(src, json.loads(result.model_dump_json())) == result
    # An exact but semantically opposite enum remains explicitly unreviewed.
    data["bindings"][0]["change"]["direction"] = "decrease"
    assert mod.build_role_alias_frame(src, data).changes[0].change.direction == "decrease"


def test_null_and_uncertain_are_distinct_and_never_implicitly_filled():
    mod = api()
    data = packet()
    data["bindings"][0]["change"] = None
    null = mod.build_role_alias_frame(source(), data)
    assert null.changes[0].change is None
    data["bindings"][0]["change"] = dict(direction="uncertain", evidence=None, support=["s1"])
    uncertain = mod.build_role_alias_frame(source(), data)
    assert uncertain.changes[0].change.direction == "uncertain"
    assert uncertain.changes[0].change.evidence is None
    assert null != uncertain


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_change",
        "canonical_context",
        "mixed_anchor",
        "canonical_event",
        "extra",
        "slot",
        "candidate",
        "sentence",
        "missing_context",
        "duplicate_context",
        "duplicate_binding",
        "known_status",
        "known_tense",
        "combined_scopes",
        "empty_support",
        "support_duplicate",
        "support_gap",
        "support_reverse",
        "support_unknown",
        "support_other_quote",
        "support_wrong_number",
        "evidence_outside",
        "ambiguous",
        "overlapping",
        "null_evidence",
    ],
)
def test_rejects_mixed_names_catalog_drift_and_invalid_change_statements(mutation):
    mod = api()
    src, data = source(), packet()
    binding = data["bindings"][0]
    change = binding["change"]
    context = data["contexts"][0]
    if mutation == "missing_change":
        del binding["change"]
    elif mutation == "canonical_context":
        context["context_id"] = context.pop("id")
    elif mutation == "mixed_anchor":
        context["entity"]["sentence_id"] = "s1"
    elif mutation == "canonical_event":
        data["events"][0]["event_id"] = data["events"][0].pop("id")
    elif mutation == "extra":
        binding["candidate_id"] = "n1"
    elif mutation == "slot":
        context["id"] = binding["context"] = "custom"
    elif mutation == "candidate":
        binding["number"] = "n99"
    elif mutation == "sentence":
        context["entity"]["s"] = "s99"
    elif mutation == "missing_context":
        binding["context"] = "c2"
    elif mutation == "duplicate_context":
        data["contexts"] *= 2
    elif mutation == "duplicate_binding":
        data["bindings"] *= 2
    elif mutation == "known_status":
        context["status"] = "observed"
    elif mutation == "known_tense":
        data["events"][0]["tense"] = "past"
    elif mutation == "combined_scopes":
        context["scopes"] = [
            dict(kind="other", anchor=anchor(t)) for t in ["이용자", "학교", "증가"]
        ]
        binding["scopes"] = [dict(kind="other", anchor=anchor(t)) for t in ["약", "내외"]]
    elif mutation == "empty_support":
        change["support"] = []
    elif mutation == "support_duplicate":
        change["support"] = ["s1", "s1"]
    elif mutation in ("support_gap", "support_reverse"):
        src = document("이용자 37명 증가. 설명. 학교 83개교 감소.")
        change["support"] = ["s1", "s3"] if mutation == "support_gap" else ["s2", "s1"]
    elif mutation == "support_unknown":
        change["support"] = ["s99"]
    elif mutation == "support_other_quote":
        src = document("이용자 37명 증가.", "학교 83개교 감소.")
        change["support"] = ["s1", "s2"]
    elif mutation == "support_wrong_number":
        src = document("이용자 37명 증가. 학교 83개교 감소.")
        change.update(support=["s2"], evidence=anchor("감소", "s2"))
    elif mutation == "evidence_outside":
        src = document("이용자 37명 증가. 학교 83개교 감소.")
        change["evidence"] = anchor("감소", "s2")
    elif mutation == "ambiguous":
        src = document("이용자 37명 증가, 학교 83개교 증가.")
    elif mutation == "overlapping":
        src = document("이용자 37명 가가가.")
        change["evidence"] = anchor("가가", context="가가가")
    else:
        change["evidence"] = None
    with pytest.raises(mod.RoleAliasContractError):
        mod.build_role_alias_frame(src, data)


def test_explicit_context_and_contiguous_statement_preserve_full_quantity_and_whitespace():
    mod = api()
    src = document("이용자 약\t37여 명 내외 증가.\n 학교 83개교 증가.")
    data = packet()
    data["bindings"][0]["change"].update(
        evidence=anchor("증가", context="내외 증가"), support=["s1", "s2", "s3"]
    )
    got = mod.build_role_alias_frame(src, data)
    assert got.changes[0].change.statement.text == src[1].citations[0].selector.quote
    assert got.changes[0].change.evidence.span.start == 15


def test_object_specific_relation_from_alias_and_encoder_never_invent_change():
    mod = api()
    data = packet()
    data["bindings"].append(
        dict(number="n2", context="c1", scopes=[], status_sentence=None, change=None)
    )
    data["relations"] = [
        dict(kind="parallel", **{"from": "n1", "to": "n2"}, support=["s1"], cue=anchor(","))
    ]
    got = mod.build_role_alias_frame(source(), data)
    encoded = mod._encode_shared_input(got.frame.input)
    assert encoded["relations"] == data["relations"]
    assert all("change" not in b for b in encoded["bindings"])
    assert got.input.model_dump(mode="json")["relations"] == data["relations"]
    for spelling in ("from_", "from_id"):
        bad = deepcopy(data)
        bad["relations"][0][spelling] = bad["relations"][0].pop("from")
        with pytest.raises(mod.RoleAliasContractError):
            mod.build_role_alias_frame(source(), bad)


@pytest.mark.parametrize(
    "node", ["input_dict", "bindings_list", "change_dict", "anchor_dict", "subclass", "frame_dict"]
)
def test_actual_nested_models_and_tuples_checked_before_serialization(node):
    mod = api()
    got = mod.build_role_alias_frame(source(), packet())
    inp = got.input
    if node == "input_dict":
        got = got.model_copy(update={"input": inp.model_dump(mode="json")})
    elif node == "frame_dict":
        got = got.model_copy(update={"frame": got.frame.model_dump(mode="json")})
    else:
        binding = inp.bindings[0]
        if node == "bindings_list":
            inp = inp.model_copy(update={"bindings": list(inp.bindings)})
        else:
            change = binding.change
            if node == "change_dict":
                change = change.model_dump()
            elif node == "anchor_dict":
                change = change.model_copy(update={"evidence": change.evidence.model_dump()})
            else:
                cls = create_model(
                    "ExtraChange",
                    __base__=type(change),
                    secret=(str, Field(default="hidden", exclude=True)),
                )
                change = cls.model_validate(change.model_dump())
            inp = inp.model_copy(
                update={"bindings": (binding.model_copy(update={"change": change}),)}
            )
        got = got.model_copy(update={"input": inp})
    with pytest.raises(mod.RoleAliasContractError):
        mod.validate_role_alias_frame(source(), got)


@pytest.mark.parametrize(
    "mutation", ["profile", "status", "source", "direction", "statement", "old_marker"]
)
def test_saved_frame_rebuilds_markers_original_frame_and_change(mutation):
    mod = api()
    src = source()
    raw = mod.build_role_alias_frame(src, packet()).model_dump(mode="json")
    if mutation in ("profile", "status"):
        del raw[mutation]
    elif mutation == "source":
        src = document("변경. 이용자 약\t37여 명 내외 증가, 학교 83개교 감소.")
    elif mutation == "direction":
        raw["changes"][0]["change"]["direction"] = "decrease"
    elif mutation == "statement":
        raw["changes"][0]["change"]["statement"]["text"] = "37"
    else:
        del raw["frame"]["profile"]
    with pytest.raises(mod.RoleAliasContractError):
        mod.validate_role_alias_frame(src, raw)


def without_frame_marker(frame, path, marker, actual):
    altered = frame.model_copy(deep=True) if actual else frame.model_dump(mode="json")
    node = altered
    for part in path:
        node = node.__dict__[part] if actual else node[part]
    del (node.__dict__ if actual else node)[marker]
    return altered


@pytest.mark.parametrize("path", [(), ("frame",), ("frame", "candidate_index")])
@pytest.mark.parametrize("marker", ["profile", "status"])
@pytest.mark.parametrize("actual", [False, True])
def test_saved_frame_missing_markers_rejected_before_raw_or_actual_default_restoration(
    path, marker, actual
):
    mod = api()
    got = mod.build_role_alias_frame(source(), packet())
    altered = without_frame_marker(got, path, marker, actual)
    with pytest.raises(mod.RoleAliasContractError):
        mod.validate_role_alias_frame(source(), altered)
