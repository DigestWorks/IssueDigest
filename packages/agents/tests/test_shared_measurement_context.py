"""Synthetic shared roles test structure and provenance, never semantic approval."""

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
from pydantic import Field, ValidationError, create_model
from pydantic_ai import Agent
from pydantic_ai.models import Model
from test_numeric_evidence import document


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_modules():
    names = (
        "shared_measurement_context",
        "measurement_scope",
        "contextual_frame",
        "contextual_anchor",
        "numeric_frame",
        "numeric_selection_evaluation",
        "numeric_selection",
    )
    introduced = [
        f"issuedigest_agents.{n}" for n in names if f"issuedigest_agents.{n}" not in sys.modules
    ]
    yield
    for name in introduced:
        sys.modules.pop(name, None)


def api():
    name = "issuedigest_agents.shared_measurement_context"
    assert importlib.util.find_spec(name) is not None, "Missing shared measurement contract"
    return importlib.import_module(name)


def anchor(text, sentence="s1", context=None):
    return {"sentence_id": sentence, "text": text, "context_text": context}


def scope(text, sentence="s1", context=None, kind="geographic"):
    return {"kind": kind, "anchor": anchor(text, sentence, context)}


def context(context_id="c1", event_id="e1", **fields):
    return {
        "context_id": context_id,
        "reporting_event_id": event_id,
        "measured_variable": None,
        "target_scopes": [],
        "period": None,
        "value_status": "unknown",
        "logical_condition": None,
        "purpose": None,
        "forecast_basis": None,
        "comparison_baseline": None,
        **fields,
    }


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


def simple(text="동부 서부 이용자 10명, 20명."):
    return document(text), {
        "contexts": [context()],
        "events": [event()],
        "bindings": [binding()],
        "relations": [],
    }


def example():
    src = document(
        "발표처는 알렸다. 운영기관이 안정 지원을 위해 조건 충족 시 내년 합성국 동부 청년 이용자 "
        "10명과 서부 이용자 20명을 공급할 예정이다."
    )
    data = {
        "contexts": [
            context(
                measured_variable=anchor("이용자", "s2", "청년 이용자"),
                target_scopes=[scope("합성국", "s2")],
                period=anchor("내년", "s2"),
                value_status="planned",
                logical_condition=anchor("조건 충족 시", "s2"),
                purpose=anchor("안정 지원을 위해", "s2"),
            )
        ],
        "events": [
            event(
                kind="attributed_report",
                reporting_actor=anchor("발표처"),
                predicate=anchor("알렸다"),
                reporting_tense="past",
            )
        ],
        "bindings": [
            binding(
                target_scopes=[scope("동부", "s2"), scope("청년", "s2", kind="population")],
                status_evidence_sentence_id="s2",
            ),
            binding("n2", target_scopes=[scope("서부", "s2")], status_evidence_sentence_id="s2"),
        ],
        "relations": [
            {
                "kind": "parallel",
                "from_id": "n1",
                "to_id": "n2",
                "statement_sentence_ids": ["s2"],
                "cue": anchor("과", "s2"),
            }
        ],
    }
    return src, data


def rejects(src, data):
    mod = api()
    with pytest.raises(mod.SharedMeasurementContextError) as error:
        mod.build_shared_measurement_frame(src, data)
    assert str(error.value) == "Invalid shared measurement input"
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


def test_explicit_shared_context_preserves_scopes_reporting_status_and_separate_purpose():
    mod = api()
    src, data = example()
    result = mod.build_shared_measurement_frame(src, data)
    assert (result.profile, result.status) == ("shared-measurement-context-v1", "unreviewed")
    assert result.input.model_dump(mode="json") == data
    facts = result.frame.frame.resolved.facts
    assert [f.measured_entity.span.text for f in facts] == ["이용자", "이용자"]
    assert [f.reporting_actor.span.text for f in facts] == ["발표처", "발표처"]
    assert [(f.reporting_tense, f.reporting_tense_text.span.text) for f in facts] == [
        ("past", "알렸다"),
        ("past", "알렸다"),
    ]
    assert [f.value_status for f in facts] == ["planned", "planned"]
    assert [f.status_text.span.text for f in facts] == [
        " 운영기관이 안정 지원을 위해 조건 충족 시 내년 합성국 동부 청년 이용자 "
        "10명과 서부 이용자 20명을 공급할 예정이다."
    ] * 2
    assert [f.logical_condition.span.text for f in facts] == ["조건 충족 시"] * 2
    assert [(p.context_id, p.purpose.span.text) for p in result.purposes] == [
        ("c1", "안정 지원을 위해")
    ]
    assert [[s.anchor.span.text for s in f.target_scopes] for f in result.frame.scopes] == [
        ["합성국", "동부", "청년"],
        ["합성국", "서부"],
    ]
    assert result.frame.frame.resolved.relations[0].cue.span.text == "과"
    assert mod.validate_shared_measurement_frame(src, result) == result
    assert (
        mod.validate_shared_measurement_frame(src, json.loads(result.model_dump_json())) == result
    )
    assert mod.build_shared_measurement_frame(src, result.input) == result


def test_selected_context_only_and_input_ordered_nullable_purposes():
    src, data = simple("운영기관이 동부 이용자 10명, 서부 이용자 20명을 운영한다.")
    data["contexts"] = [
        context("c2", measured_variable=anchor("이용자", context="서부 이용자")),
        context("c1", purpose=anchor("동부")),
    ]
    data["bindings"] = [binding(), binding("n2", "c2")]
    data["events"] = [
        event(kind="narration", predicate=anchor("운영한다"), reporting_tense="present")
    ]
    result = api().build_shared_measurement_frame(src, data)
    assert result.frame.frame.resolved.facts[0].measured_entity is None
    assert result.frame.frame.resolved.facts[0].logical_condition is None
    assert all(f.reporting_actor is None for f in result.frame.frame.resolved.facts)
    assert [(p.context_id, p.purpose is None) for p in result.purposes] == [
        ("c2", True),
        ("c1", False),
    ]


def test_same_purpose_and_condition_location_is_preserved_without_semantic_repair():
    src, data = simple()
    data["contexts"][0].update(purpose=anchor("동부"), logical_condition=anchor("동부"))
    result = api().build_shared_measurement_frame(src, data)
    assert result.purposes[0].purpose == result.frame.frame.resolved.facts[0].logical_condition
    assert result.status == "unreviewed"


def test_empty_full_input_is_valid_with_or_without_numeric_candidates():
    for text in ("수치가 없다.", "이용자 10명."):
        result = api().build_shared_measurement_frame(
            document(text), {"contexts": [], "events": [], "bindings": [], "relations": []}
        )
        assert result.purposes == result.frame.scopes == result.frame.frame.resolved.facts == ()


@pytest.mark.parametrize("field", ["contexts", "events", "bindings", "relations"])
def test_each_collection_over_cap_rejects(field):
    src, data = example()
    data[field] = [data[field][0]] * (17 if field == "relations" else 13)
    with pytest.raises(ValidationError) as error:
        api().SharedMeasurementInput.model_validate_json(json.dumps(data), strict=True)
    assert [(item["loc"], item["type"]) for item in error.value.errors()] == [
        ((field,), "too_long")
    ]
    rejects(src, data)


@pytest.mark.parametrize("field", ["contexts", "bindings"])
def test_individual_scope_cap_and_combined_scope_cap_reject(field):
    src, data = simple("A B C D E 이용자 10명.")
    data[field][0]["target_scopes"] = [scope(t) for t in "ABCDE"]
    rejects(src, data)
    data[field][0]["target_scopes"] = [scope(t) for t in "ABCD"]
    other = "contexts" if field == "bindings" else "bindings"
    data[other][0]["target_scopes"] = [scope("E")]
    rejects(src, data)


def test_all_collection_and_combined_scope_limits_are_accepted():
    src = document(
        "A B C D 전체 " + ", ".join(f"항목{chr(97 + i)} {10 + i}명" for i in range(12)) + " 포함."
    )
    ids = [f"n{i + 1}" for i in range(12)]
    pairs = [(a, b) for i, a in enumerate(ids) for b in ids[i + 1 :]][:16]
    result = api().build_shared_measurement_frame(
        src,
        {
            "contexts": [
                context(
                    f"c{i}",
                    f"e{i}",
                    measured_variable=anchor("전체"),
                    target_scopes=[scope("A"), scope("B")],
                )
                for i in range(12)
            ],
            "events": [event(f"e{i}") for i in range(12)],
            "bindings": [
                binding(f"n{i + 1}", f"c{i}", target_scopes=[scope("C"), scope("D")])
                for i in range(12)
            ],
            "relations": [
                {
                    "kind": "parallel",
                    "from_id": a,
                    "to_id": b,
                    "statement_sentence_ids": ["s1"],
                    "cue": anchor("포함"),
                }
                for a, b in pairs
            ],
        },
    )
    assert len(result.purposes) == len(result.frame.scopes) == 12
    assert len(result.frame.frame.resolved.relations) == 16
    assert all(len(f.target_scopes) == 4 for f in result.frame.scopes)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_context",
        "duplicate_event",
        "duplicate_binding",
        "missing_context",
        "missing_event",
        "missing_candidate",
        "unused_context",
        "unused_event",
    ],
)
def test_duplicate_missing_and_unused_references_reject(mutation):
    src, data = simple()
    if mutation.startswith("duplicate_"):
        group = {"context": "contexts", "event": "events", "binding": "bindings"}[mutation[10:]]
        data[group].append(deepcopy(data[group][0]))
    elif mutation == "missing_context":
        data["bindings"][0]["context_id"] = "absent"
    elif mutation == "missing_event":
        data["contexts"][0]["reporting_event_id"] = "absent"
    elif mutation == "missing_candidate":
        data["bindings"][0]["candidate_id"] = "n999"
    elif mutation == "unused_context":
        data["contexts"].append(context("unused"))
    else:
        data["events"].append(event("unused"))
    rejects(src, data)


@pytest.mark.parametrize("bad", ["", "a" * 65, "지역", "a b", "a.b", "a\n", True, 1])
@pytest.mark.parametrize(
    "group,field",
    [
        ("contexts", "context_id"),
        ("contexts", "reporting_event_id"),
        ("events", "event_id"),
        ("bindings", "context_id"),
        ("bindings", "candidate_id"),
    ],
)
def test_ids_are_exact_bounded_ascii(group, field, bad):
    src, data = simple()
    data[group][0][field] = bad
    rejects(src, data)


@pytest.mark.parametrize(
    "fields",
    [
        {"kind": "attributed_report"},
        {"kind": "attributed_report", "reporting_actor": anchor("동부")},
        {"kind": "narration"},
        {"kind": "narration", "predicate": anchor("동부"), "reporting_actor": anchor("서부")},
        {"predicate": anchor("동부")},
        {"reporting_actor": anchor("동부")},
        {"reporting_tense": "past"},
        {"kind": "invalid"},
    ],
)
def test_reporting_event_consistency_rejects(fields):
    src, data = simple()
    data["events"] = [event(**fields)]
    rejects(src, data)


@pytest.mark.parametrize("status", ["observed", "planned", "forecast"])
def test_known_status_requires_candidate_whole_sentence_and_accepts_valid_sentence(status):
    src, data = simple("동부 이용자 10명. 다른 문장 20명.")
    data["contexts"][0]["value_status"] = status
    rejects(src, data)
    for invalid in ("s2", "s999", "", "s1 ", True):
        data["bindings"][0]["status_evidence_sentence_id"] = invalid
        rejects(src, data)
    data["bindings"][0]["status_evidence_sentence_id"] = "s1"
    result = api().build_shared_measurement_frame(src, data)
    assert result.frame.frame.resolved.facts[0].status_text.span.text == "동부 이용자 10명."


def test_unknown_status_allows_valid_sentence_but_rejects_ineligible_long_sentence():
    src, data = simple()
    data["bindings"][0]["status_evidence_sentence_id"] = "s1"
    assert api().build_shared_measurement_frame(src, data).frame.input.facts[
        0
    ].status_text.text == ("동부 서부 이용자 10명, 20명.")
    rejects(document("가" * 1000 + " 10명."), data)


@pytest.mark.parametrize(
    "role",
    [
        "measured_variable",
        "period",
        "logical_condition",
        "purpose",
        "forecast_basis",
        "comparison_baseline",
        "common_scope",
        "additional_scope",
        "reporting_actor",
        "predicate",
        "status",
    ],
)
def test_all_anchor_roles_must_share_each_bound_candidates_quote(role):
    src, data = simple()
    src = document("동부 이용자 10명.", "서부 운영 20명.")
    other = anchor("서부", "s2")
    if role == "common_scope":
        data["contexts"][0]["target_scopes"] = [scope("서부", "s2")]
    elif role == "additional_scope":
        data["bindings"][0]["target_scopes"] = [scope("서부", "s2")]
    elif role in ("reporting_actor", "predicate"):
        data["events"] = [
            event(
                kind="attributed_report", reporting_actor=anchor("동부"), predicate=anchor("이용자")
            )
        ]
        data["events"][0][role] = other
    elif role == "status":
        data["bindings"][0]["status_evidence_sentence_id"] = "s2"
    else:
        data["contexts"][0][role] = other
    rejects(src, data)


def test_scopes_duplicate_locations_reject_across_groups_but_distinct_locations_are_valid():
    src, data = simple("동부 왼쪽 동부 오른쪽 10명.")
    data["contexts"][0]["target_scopes"] = [scope("동부", context="동부 왼쪽")]
    data["bindings"][0]["target_scopes"] = [scope("동부", context="동부 왼쪽", kind="other")]
    rejects(src, data)
    data["bindings"][0]["target_scopes"] = [scope("동부", context="동부 오른쪽")]
    result = api().build_shared_measurement_frame(src, data)
    assert [s.anchor.span.start for s in result.frame.scopes[0].target_scopes] == [0, 6]


@pytest.mark.parametrize(
    "text,selected",
    [
        ("동부 동부 10명.", anchor("동부")),
        ("aaaa 10명.", anchor("a", context="aa")),
        ("A 10명. B 20명.", anchor("명", context="명. B")),
        ("e\u0301 10명.", anchor("é")),
    ],
)
def test_exact_contextual_purpose_rejects_ambiguous_overlap_cross_sentence_normalization(
    text, selected
):
    src, data = simple(text)
    data["contexts"][0]["purpose"] = selected
    rejects(src, data)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_endpoint",
        "duplicate_pair",
        "cycle",
        "no_object",
        "partial_statement",
        "ambiguous_cue",
    ],
)
def test_existing_relation_guards_are_reused_without_repair(mutation):
    src, data = example()
    rel = data["relations"][0]
    if mutation == "missing_endpoint":
        rel["to_id"] = "n999"
    elif mutation == "duplicate_pair":
        data["relations"].append({**rel, "kind": "unknown", "from_id": "n2", "to_id": "n1"})
    elif mutation == "cycle":
        data["relations"] = [
            {**rel, "kind": "included_in"},
            {**rel, "kind": "included_in", "from_id": "n2", "to_id": "n1"},
        ]
    elif mutation == "no_object":
        data["contexts"][0]["measured_variable"] = None
    elif mutation == "partial_statement":
        rel["statement_sentence_ids"] = ["s1"]
    else:
        src = document(
            "발표처는 알렸다. 운영기관이 안정 지원을 위해 조건 충족 시 "
            "내년 합성국 동부 청년 이용자 "
            "10명과 서부 이용자 20명을 공급할 예정이다 과."
        )
    rejects(src, data)


def update_path(root, path, value):
    target = root
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


@pytest.mark.parametrize(
    "path,value",
    [
        (("profile",), "forged"),
        (("status",), "reviewed"),
        (("input", "contexts", 0, "purpose"), None),
        (("input", "events", 0, "reporting_tense"), "present"),
        (("input", "bindings", 0, "context_id"), "c999"),
        (("purposes", 0, "context_id"), "c999"),
        (("purposes", 0, "purpose"), None),
        (("purposes", 0, "purpose", "span", "start"), 0),
        (("frame", "scopes", 0, "target_scopes", 0, "kind"), "population"),
        (("frame", "input", "facts", 0, "reporting_tense"), "present"),
        (("frame", "frame", "resolved", "facts", 0, "value_status"), "observed"),
        (("frame", "frame", "resolved", "candidate_index", "source_sha256"), "0" * 64),
        (("frame", "frame", "resolved", "relations", 0, "kind"), "unknown"),
        (("secret",), "sensitive"),
    ],
)
def test_entire_wrapper_reconstruction_rejects_tampering(path, value):
    src, data = example()
    raw = api().build_shared_measurement_frame(src, data).model_dump(mode="json")
    update_path(raw, path, value)
    with pytest.raises(
        api().SharedMeasurementContextError, match="^Invalid shared measurement frame$"
    ):
        api().validate_shared_measurement_frame(src, raw)


def replace_model(root, path, replacement):
    if not path:
        return replacement(root)
    key, *rest = path
    if isinstance(key, int):
        values = list(root)
        values[key] = replace_model(values[key], rest, replacement)
        return tuple(values)
    return root.model_copy(update={key: replace_model(getattr(root, key), rest, replacement)})


INPUT_NODES = [
    (),
    ("contexts", 0),
    ("contexts", 0, "purpose"),
    ("contexts", 0, "target_scopes", 0),
    ("contexts", 0, "target_scopes", 0, "anchor"),
    ("events", 0),
    ("events", 0, "predicate"),
    ("bindings", 0),
    ("bindings", 0, "target_scopes", 0),
    ("relations", 0),
    ("relations", 0, "cue"),
]
RESULT_NODES = [
    (),
    ("purposes", 0),
    ("purposes", 0, "purpose"),
    ("frame",),
    ("frame", "frame", "resolved"),
    ("frame", "frame", "resolved", "candidate_index"),
    ("frame", "frame", "resolved", "facts", 0),
    ("frame", "scopes", 0, "target_scopes", 0, "anchor", "span"),
]


def forged(item, kind):
    if kind in ("subclass", "malicious_dump"):
        cls = create_model("Hidden", __base__=type(item), secret=(str, Field(exclude=True)))
        result = cls(**item.model_dump(), secret="sensitive")
        if kind == "malicious_dump":

            def forbidden(*args, **kwargs):
                pytest.fail("Noncanonical dump was called")

            cls.model_dump = forbidden
            cls.model_dump_json = forbidden
        return result
    if kind == "dict":
        return item.model_dump()
    result = item.model_copy()
    if kind == "extra":
        result.__dict__["secret"] = "sensitive"
    elif kind == "pydantic_extra":
        object.__setattr__(result, "__pydantic_extra__", {"secret": "sensitive"})
    else:
        name = next(iter(type(item).model_fields))
        result = type(item).model_construct(**{**item.__dict__, name: True})
    return result


FORGERIES = ["subclass", "malicious_dump", "extra", "pydantic_extra", "construct", "dict"]


@pytest.mark.parametrize(
    "path,kind", [(p, k) for p in INPUT_NODES for k in FORGERIES if p or k != "dict"]
)
def test_actual_input_models_checked_before_any_dump(path, kind):
    src, data = example()
    result = api().build_shared_measurement_frame(src, data)
    bad = replace_model(result.input, path, lambda item: forged(item, kind))
    rejects(src, bad)
    with pytest.raises(api().SharedMeasurementContextError):
        api().validate_shared_measurement_frame(src, result.model_copy(update={"input": bad}))


@pytest.mark.parametrize(
    "path,kind", [(p, k) for p in RESULT_NODES for k in FORGERIES if p or k != "dict"]
)
def test_actual_output_models_checked_before_any_dump(path, kind):
    src, data = example()
    result = api().build_shared_measurement_frame(src, data)
    bad = replace_model(result, path, lambda item: forged(item, kind))
    with pytest.raises(api().SharedMeasurementContextError):
        api().validate_shared_measurement_frame(src, bad)


@pytest.mark.parametrize(
    "mutation",
    [
        "snapshot",
        "workspace",
        "quote",
        "source_list",
        "nested_dict",
        "nested_subclass",
        "nested_extra",
        "nested_malicious_dump",
    ],
)
def test_current_source_drift_and_noncanonical_actual_source_reject(mutation):
    src, data = example()
    result = api().build_shared_measurement_frame(src, data)
    sid, bundle, presentation = src
    if mutation == "snapshot":
        bad = (uuid4(), bundle, presentation)
    elif mutation == "workspace":
        bad = (sid, bundle, presentation.model_copy(update={"workspace_id": uuid4()}))
    elif mutation == "quote":
        bad = document("다른 자료 10명.")
    elif mutation == "source_list":
        bad = list(src)
    else:
        selector = forged(bundle.citations[0].selector, mutation.removeprefix("nested_"))
        citation = bundle.citations[0].model_copy(update={"selector": selector})
        bad = (sid, bundle.model_copy(update={"citations": (citation,)}), presentation)
    rejects(bad, data)
    with pytest.raises(api().SharedMeasurementContextError):
        api().validate_shared_measurement_frame(bad, result)


@pytest.mark.parametrize("group", [None, "contexts", "events", "bindings"])
def test_every_declared_input_field_is_required(group):
    src, data = simple()
    row = data if group is None else data[group][0]
    for field in tuple(row):
        broken = deepcopy(data)
        del (broken if group is None else broken[group][0])[field]
        rejects(src, broken)


@pytest.mark.parametrize(
    "path,value",
    [
        (("contexts",), None),
        (("contexts",), {}),
        (("bindings", 0, "target_scopes"), None),
        (("contexts", 0, "purpose"), 1),
        (("contexts", 0, "value_status"), "conditional_forecast"),
        (("bindings", 0, "measured_variable"), None),
        (("contexts", 0, "secret"), "sensitive"),
    ],
)
def test_strict_raw_containers_scalars_and_extras_reject(path, value):
    src, data = simple()
    update_path(data, path, value)
    rejects(src, data)


@pytest.mark.parametrize("role", ["purpose", "reporting_actor", "predicate"])
def test_shared_anchor_quote_checked_for_second_binding_too(role):
    src = document("발표처는 알렸다. 목적을 위한 이용자 10명.", "별도 이용자 20명.")
    data = {
        "contexts": [context()],
        "events": [event()],
        "bindings": [binding(), binding("n2")],
        "relations": [],
    }
    if role == "purpose":
        data["contexts"][0]["purpose"] = anchor("목적을 위한", "s2")
    else:
        data["events"] = [
            event(
                kind="attributed_report",
                reporting_actor=anchor("발표처"),
                predicate=anchor("알렸다"),
            )
        ]
    # The record works for the first binding, then fails for a later quote.
    first_only = deepcopy(data)
    first_only["bindings"].pop()
    assert len(api().build_shared_measurement_frame(src, first_only).frame.scopes) == 1
    rejects(src, data)


def test_inclusion_three_edge_cycle_rejects_with_distinct_unordered_pairs():
    src = document("전체 이용자 10명, 20명, 30명 포함.")
    data = {
        "contexts": [context(measured_variable=anchor("이용자"))],
        "events": [event()],
        "bindings": [binding(), binding("n2"), binding("n3")],
        "relations": [
            {
                "kind": "included_in",
                "from_id": a,
                "to_id": b,
                "statement_sentence_ids": ["s1"],
                "cue": anchor("포함"),
            }
            for a, b in [("n1", "n2"), ("n2", "n3"), ("n3", "n1")]
        ],
    }
    acyclic = deepcopy(data)
    acyclic["relations"].pop()
    assert (
        len(api().build_shared_measurement_frame(src, acyclic).frame.frame.resolved.relations) == 2
    )
    rejects(src, data)


@pytest.mark.parametrize("identity", ["_", "a" * 62 + "-_"])
def test_id_boundaries_and_same_id_in_different_groups_are_allowed(identity):
    src, data = simple()
    data["contexts"][0].update(context_id=identity, reporting_event_id=identity)
    data["events"][0]["event_id"] = identity
    data["bindings"][0]["context_id"] = identity
    result = api().build_shared_measurement_frame(src, data)
    assert result.purposes[0].context_id == identity


@pytest.mark.parametrize(
    "path", [("contexts",), ("contexts", 0, "target_scopes"), ("bindings", 0, "target_scopes")]
)
def test_list_in_actual_model_is_rejected_before_narrowing(path):
    src, data = example()
    result = api().build_shared_measurement_frame(src, data)
    rejects(src, replace_model(result.input, path, list))


def test_purpose_order_is_checked_when_contexts_are_selected_in_different_order():
    src, data = simple()
    data["contexts"] = [context("c2"), context("c1", purpose=anchor("동부"))]
    data["bindings"] = [binding(), binding("n2", "c2")]
    result = api().build_shared_measurement_frame(src, data)
    raw = result.model_dump(mode="json")
    raw["purposes"].reverse()
    with pytest.raises(api().SharedMeasurementContextError):
        api().validate_shared_measurement_frame(src, raw)


def test_pure_build_and_validate_use_no_file_network_or_model_io(monkeypatch):
    mod = api()
    src, data = example()

    def forbidden(*args, **kwargs):
        raise AssertionError("I/O forbidden")

    with monkeypatch.context() as patch:
        for owner, name in [
            (builtins, "open"),
            (io, "open"),
            (os, "open"),
            (Path, "open"),
            (socket, "socket"),
            (socket, "create_connection"),
            (Agent, "run_sync"),
            (Model, "request"),
        ]:
            patch.setattr(owner, name, forbidden)
        result = mod.build_shared_measurement_frame(src, data)
        assert mod.validate_shared_measurement_frame(src, result) == result
