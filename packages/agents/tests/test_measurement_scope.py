"""Hand-authored synthetic scope linkage; structural validity remains unreviewed."""

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
from pydantic import Field, create_model
from pydantic_ai import Agent
from pydantic_ai.models import Model
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
def restore_introduced_modules():
    names = (
        "issuedigest_agents.measurement_scope",
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
    name = "issuedigest_agents.measurement_scope"
    assert importlib.util.find_spec(name) is not None, "Missing measurement scope contract"
    return importlib.import_module(name)


def anchor(text, context=None, sentence="s1"):
    return {"sentence_id": sentence, "text": text, "context_text": context}


def scope(text, kind="geographic", context=None, sentence="s1"):
    return {"kind": kind, "anchor": anchor(text, context, sentence)}


def fact(candidate="n1", scopes=(), **fields):
    return {
        "candidate_id": candidate,
        **dict.fromkeys(ROLES),
        "value_status": "unknown",
        "reporting_tense": "unknown",
        "target_scopes": list(scopes),
        **fields,
    }


def example():
    src = document(
        "발표처는 알렸다. 동부 기관군 청년 이용자 10명 포함, 서부 학교군 이용자 20명 포함."
    )
    data = {
        "facts": [
            fact(
                scopes=[
                    scope("동부", sentence="s2"),
                    scope("기관군", "institutional", sentence="s2"),
                    scope("청년", "population", sentence="s2"),
                ],
                measured_entity=anchor("이용자", "청년 이용자", "s2"),
                reporting_actor=anchor("발표처"),
            ),
            fact(
                "n2",
                scopes=[
                    scope("서부", sentence="s2"),
                    scope("학교군", "institutional", sentence="s2"),
                ],
                measured_entity=anchor("이용자", "학교군 이용자", "s2"),
            ),
        ],
        "relations": [
            {
                "from_id": "n1",
                "to_id": "n2",
                "kind": "parallel",
                "statement_sentence_ids": ["s2"],
                "cue": anchor("포함", "이용자 20명 포함", "s2"),
            }
        ],
    }
    return src, data


def test_separates_same_measured_object_scopes_and_independently_nullable_reporter():
    mod = api()
    src, data = example()
    result = mod.build_measurement_scope_frame(src, data)
    assert (result.profile, result.status) == ("measurement-scope-frame-v1", "unreviewed")
    assert result.input.model_dump(mode="json") == data
    assert [f.measured_entity.span.text for f in result.frame.resolved.facts] == ["이용자"] * 2
    assert [
        f.reporting_actor.span.text if f.reporting_actor else None
        for f in result.frame.resolved.facts
    ] == ["발표처", None]
    assert [[(s.kind, s.anchor.span.text) for s in row.target_scopes] for row in result.scopes] == [
        [("geographic", "동부"), ("institutional", "기관군"), ("population", "청년")],
        [("geographic", "서부"), ("institutional", "학교군")],
    ]
    assert [s.candidate_id for s in result.scopes] == ["n1", "n2"]
    assert result.frame.resolved.relations[0].cue.span.text == "포함"
    assert "target_scopes" not in result.frame.input.model_dump()["facts"][0]
    assert mod.validate_measurement_scope_frame(src, result) == result
    assert mod.validate_measurement_scope_frame(src, json.loads(result.model_dump_json())) == result
    assert mod.build_measurement_scope_frame(src, result.input) == result


def test_operator_without_reporter_and_wrong_semantic_kind_are_structurally_unreviewed():
    mod = api()
    src = document("운영기관이 운영하는 동부 시설 방문 10건.")
    data = {
        "facts": [
            fact(
                scopes=[scope("운영기관", "institutional"), scope("동부", "population")],
                measured_entity=anchor("방문"),
            )
        ],
        "relations": [],
    }
    result = mod.build_measurement_scope_frame(src, data)
    assert result.frame.resolved.facts[0].reporting_actor is None
    assert result.scopes[0].target_scopes[1].kind == "population"
    assert result.status == result.frame.status == result.frame.resolved.status == "unreviewed"


def test_roles_can_share_scope_anchor_and_scopes_can_be_in_another_sentence():
    src = document("기관이 발표했다. 방문 10건.")
    result = api().build_measurement_scope_frame(
        src,
        {
            "facts": [
                fact(
                    scopes=[scope("기관", "institutional")],
                    reporting_actor=anchor("기관"),
                    measured_entity=anchor("기관"),
                )
            ],
            "relations": [],
        },
    )
    row = result.frame.resolved.facts[0]
    assert result.scopes[0].target_scopes[0].anchor == row.reporting_actor == row.measured_entity
    assert result.scopes[0].target_scopes[0].anchor.sentence_id == "s1"
    assert result.frame.resolved.candidate_index.candidates[0].sentence_ids == ("s2",)


@pytest.mark.parametrize("empty", [True, False])
def test_empty_scopes_or_facts_do_not_invent_evidence(empty):
    src = document("대상 10명.")
    result = api().build_measurement_scope_frame(
        src,
        {
            "facts": [] if empty else [fact()],
            "relations": [],
        },
    )
    assert result.scopes == () if empty else result.scopes[0].target_scopes == ()
    assert len(result.frame.resolved.candidate_index.candidates) == 1


def test_four_scopes_and_twelve_facts_and_sixteen_relations_are_accepted():
    # Unique numeric candidates and directed pairs avoid the frozen duplicate guards.
    src = document(
        "A B C D 전체 " + ", ".join(f"항목{chr(97 + i)} {i + 10}명" for i in range(12)) + " 포함."
    )
    facts = [
        fact(f"n{i + 1}", [scope(t, "other") for t in "ABCD"], measured_entity=anchor("전체"))
        for i in range(12)
    ]
    ids = [f"n{i + 1}" for i in range(12)]
    pairs = [(left, right) for i, left in enumerate(ids) for right in ids[i + 1 :]][:16]
    relations = [
        {
            "from_id": left,
            "to_id": right,
            "kind": "parallel",
            "statement_sentence_ids": ["s1"],
            "cue": anchor("포함"),
        }
        for left, right in pairs
    ]
    result = api().build_measurement_scope_frame(src, {"facts": facts, "relations": relations})
    assert (len(result.scopes), len(result.frame.resolved.relations)) == (12, 16)
    assert all(len(row.target_scopes) == 4 for row in result.scopes)


@pytest.mark.parametrize("field", ["scopes", "facts", "relations"])
def test_over_caps_reject_at_public_boundary(field):
    src, data = example()
    if field == "scopes":
        data["facts"][0]["target_scopes"] = [scope("동부", sentence="s2")] * 5
    elif field == "facts":
        data["facts"] *= 7
    else:
        data["relations"] *= 17
    with pytest.raises(api().MeasurementScopeError, match="^Invalid measurement scope input$"):
        api().build_measurement_scope_frame(src, data)


@pytest.mark.parametrize("kinds", [("geographic", "geographic"), ("geographic", "other")])
def test_duplicate_resolved_anchor_rejects_even_under_different_kind(kinds):
    src = document("동부 동부 10명.")
    data = {"facts": [fact(scopes=[scope("동부", k, "동부 10명") for k in kinds])], "relations": []}
    with pytest.raises(api().MeasurementScopeError):
        api().build_measurement_scope_frame(src, data)


def test_repeated_same_kind_at_distinct_locations_keeps_exact_short_spans():
    result = api().build_measurement_scope_frame(
        document("동부 왼쪽 동부 오른쪽 10명."),
        {
            "facts": [
                fact(
                    scopes=[
                        scope("동부", context="동부 왼쪽"),
                        scope("동부", context="동부 오른쪽"),
                    ]
                )
            ],
            "relations": [],
        },
    )
    assert [
        (s.kind, s.anchor.span.start, s.anchor.span.end) for s in result.scopes[0].target_scopes
    ] == [("geographic", 0, 2), ("geographic", 6, 8)]


@pytest.mark.parametrize(
    "text,selected",
    [
        ("동부 동부 10명.", scope("동부")),
        ("동부 동부 10명.", scope("동부", context="동부 동부")),
        ("aaaa 10명.", scope("a", context="aa")),
        ("X aaaa 10명.", scope("aa", context="X aaaa")),
        ("A 10명. B 20명.", scope("명", context="명. B")),
        ("e\u0301 10명.", scope("é", context="e\u0301 10명")),
        ("A 10명.", scope("A", context="absent")),
    ],
)
def test_ambiguous_overlapping_cross_sentence_or_normalized_scope_rejects(text, selected):
    with pytest.raises(api().MeasurementScopeError):
        api().build_measurement_scope_frame(
            document(text),
            {
                "facts": [fact(scopes=[selected])],
                "relations": [],
            },
        )


def test_scope_cannot_cross_selected_candidate_quote():
    src = document("A 10명.", "B 20명.")
    with pytest.raises(api().MeasurementScopeError):
        api().build_measurement_scope_frame(
            src,
            {
                "facts": [fact(scopes=[scope("B", sentence="s2")])],
                "relations": [],
            },
        )


@pytest.mark.parametrize(
    "path,value",
    [
        (("profile",), "measurement-scope-frame-v2"),
        (("status",), "reviewed"),
        (("input", "facts", 0, "target_scopes", 0, "kind"), "other"),
        (("input", "facts", 0, "target_scopes", 0, "anchor", "text"), "서부"),
        (("input", "facts", 0, "reporting_actor"), None),
        (("input", "relations", 0, "kind"), "unknown"),
        (("frame", "profile"), "numeric-contextual-frame-v2"),
        (("frame", "status"), "reviewed"),
        (("frame", "input", "facts", 0, "measured_entity", "context_text"), "학교군 이용자"),
        (("frame", "resolved", "profile"), "numeric-evidence-frame-v2"),
        (("frame", "resolved", "status"), "reviewed"),
        (("frame", "resolved", "candidate_index", "source_sha256"), "0" * 64),
        (("frame", "resolved", "candidate_index", "snapshot_id"), str(uuid4())),
        (("frame", "resolved", "candidate_index", "workspace_id"), str(uuid4())),
        (("frame", "resolved", "candidate_index", "citations", 0, "quote"), "forged"),
        (("frame", "resolved", "candidate_index", "candidates", 0, "expression", "start"), 0),
        (("frame", "resolved", "facts", 0, "reporting_actor", "span", "text"), "forged"),
        (("frame", "resolved", "facts", 0, "measured_entity", "span", "start"), 1),
        (("frame", "resolved", "facts", 0, "value_status"), "planned"),
        (("frame", "resolved", "facts", 0, "reporting_tense"), "past"),
        (("frame", "resolved", "relations", 0, "statement", "text"), "forged"),
        (("frame", "resolved", "relations", 0, "cue", "span", "start"), 0),
        (("scopes", 0, "candidate_id"), "n2"),
        (("scopes", 0, "target_scopes", 0, "kind"), "other"),
        (("scopes", 0, "target_scopes", 0, "anchor", "sentence_id"), "s1"),
        (("scopes", 0, "target_scopes", 0, "anchor", "span", "start"), 0),
        (("scopes", 0, "target_scopes", 0, "anchor", "span", "citation_id"), str(uuid4())),
        (("scopes", 0, "target_scopes", 0, "anchor", "span", "text"), "서부"),
        (("secret",), "hidden"),
    ],
)
def test_rebuild_rejects_every_wrapper_component_tampering(path, value):
    src, data = example()
    raw = api().build_measurement_scope_frame(src, data).model_dump(mode="json")
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(api().MeasurementScopeError, match="^Invalid measurement scope frame$"):
        api().validate_measurement_scope_frame(src, raw)


@pytest.mark.parametrize(
    "path",
    [
        ("scopes",),
        ("scopes", 0, "target_scopes"),
        ("frame", "resolved", "facts"),
        ("input", "facts"),
    ],
)
def test_ordering_or_missing_resolved_facts_rejects(path):
    src, data = example()
    raw = api().build_measurement_scope_frame(src, data).model_dump(mode="json")
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]].reverse()
    with pytest.raises(api().MeasurementScopeError):
        api().validate_measurement_scope_frame(src, raw)


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
    ("facts", 0),
    ("facts", 0, "target_scopes", 0),
    ("facts", 0, "target_scopes", 0, "anchor"),
    ("facts", 0, "measured_entity"),
    ("relations", 0),
    ("relations", 0, "cue"),
]
RESULT_NODES = [
    (),
    ("frame",),
    ("frame", "resolved"),
    ("frame", "input"),
    ("frame", "resolved", "candidate_index"),
    ("frame", "resolved", "facts", 0),
    ("frame", "resolved", "relations", 0),
    ("scopes", 0),
    ("scopes", 0, "target_scopes", 0),
    ("scopes", 0, "target_scopes", 0, "anchor"),
    ("scopes", 0, "target_scopes", 0, "anchor", "span"),
]


def forged(item, kind):
    if kind in {"hidden", "malicious_dump"}:
        cls = create_model("Hidden", __base__=type(item), secret=(str, Field(exclude=True)))
        value = cls(**item.model_dump(), secret="sensitive")
        if kind == "malicious_dump":

            def forbidden(*args, **kwargs):
                pytest.fail("Noncanonical model dump was invoked")

            cls.model_dump = forbidden
            cls.model_dump_json = forbidden
        return value
    value = item.model_copy()
    if kind == "extra":
        value.__dict__["secret"] = "sensitive"
    elif kind == "pydantic_extra":
        object.__setattr__(value, "__pydantic_extra__", {"secret": "sensitive"})
    else:
        field = next(iter(type(item).model_fields))
        value = type(item).model_construct(**{**item.__dict__, field: True})
    return value


@pytest.mark.parametrize("path", INPUT_NODES)
@pytest.mark.parametrize(
    "kind", ["hidden", "extra", "pydantic_extra", "construct", "malicious_dump"]
)
def test_input_canonical_models_are_checked_before_narrowing_or_dump(path, kind):
    mod = api()
    src, data = example()
    original = mod.build_measurement_scope_frame(src, data)
    bad = replace_model(original.input, path, lambda item: forged(item, kind))
    with pytest.raises(mod.MeasurementScopeError):
        mod.build_measurement_scope_frame(src, bad)
    with pytest.raises(mod.MeasurementScopeError):
        mod.validate_measurement_scope_frame(src, original.model_copy(update={"input": bad}))


@pytest.mark.parametrize("path", RESULT_NODES)
@pytest.mark.parametrize(
    "kind", ["hidden", "extra", "pydantic_extra", "construct", "malicious_dump"]
)
def test_result_canonical_models_are_checked_recursively_before_dump(path, kind):
    src, data = example()
    result = api().build_measurement_scope_frame(src, data)
    bad = replace_model(result, path, lambda item: forged(item, kind))
    with pytest.raises(api().MeasurementScopeError):
        api().validate_measurement_scope_frame(src, bad)


@pytest.mark.parametrize(
    "mutation",
    [
        "quote",
        "snapshot",
        "workspace",
        "source_list",
        "dict",
        "nested_hidden",
        "nested_extra",
        "nested_construct",
        "hidden",
        "malicious_dump",
    ],
)
def test_current_source_identity_drift_and_forgery_rejects(mutation):
    src, data = example()
    result = api().build_measurement_scope_frame(src, data)
    sid, bundle, presentation = src
    if mutation == "quote":
        bad = document("현재 다른 자료 10명.")
    elif mutation == "snapshot":
        bad = (uuid4(), bundle, presentation)
    elif mutation == "workspace":
        bad = (sid, bundle, presentation.model_copy(update={"workspace_id": uuid4()}))
    elif mutation == "source_list":
        bad = list(src)
    elif mutation == "dict":
        bad = (sid, bundle.model_dump(), presentation)
    elif mutation.startswith("nested_"):
        selector = forged(bundle.citations[0].selector, mutation.removeprefix("nested_"))
        citation = bundle.citations[0].model_copy(update={"selector": selector})
        bad = (sid, bundle.model_copy(update={"citations": (citation,)}), presentation)
    else:
        bad = (sid, forged(bundle, mutation), presentation)
    for function, value in [
        (api().build_measurement_scope_frame, data),
        (api().validate_measurement_scope_frame, result),
    ]:
        with pytest.raises(api().MeasurementScopeError):
            function(bad, value)


@pytest.mark.parametrize(
    "path,value",
    [
        (("facts",), None),
        (("facts",), {}),
        (("relations",), "bad"),
        (("facts", 0, "target_scopes"), None),
        (("facts", 0, "target_scopes"), {}),
        (("facts", 0, "target_scopes", 0, "kind"), True),
        (("facts", 0, "target_scopes", 0, "kind"), "region"),
        (("facts", 0, "target_scopes", 0, "anchor", "text"), 1),
        (("facts", 0, "target_scopes", 0, "anchor", "context_text"), False),
        (("facts", 0, "target_scopes", 0, "anchor", "sentence_id"), True),
        (("facts", 0, "candidate_id"), 1),
        (("facts", 0, "secret"), "hidden"),
    ],
)
def test_strict_raw_scalars_containers_and_extras_reject(path, value):
    src, data = example()
    target = data
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(api().MeasurementScopeError):
        api().build_measurement_scope_frame(src, data)


@pytest.mark.parametrize(
    "path",
    [("facts", 0, "target_scopes"), ("facts", 0, "target_scopes", 0, "anchor", "context_text")],
)
def test_new_input_fields_are_required_even_when_nullable_or_empty(path):
    src, data = example()
    target = data
    for key in path[:-1]:
        target = target[key]
    del target[path[-1]]
    with pytest.raises(api().MeasurementScopeError):
        api().build_measurement_scope_frame(src, data)


def test_legacy_frame_alone_is_not_measurement_contract():
    src, data = example()
    result = api().build_measurement_scope_frame(src, data)
    with pytest.raises(api().MeasurementScopeError):
        api().validate_measurement_scope_frame(src, result.frame)


def test_build_and_validate_use_no_file_network_or_model_io(monkeypatch):
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
            (Agent, "run"),
            (Agent, "run_sync"),
            (Model, "request"),
        ]:
            patch.setattr(owner, name, forbidden)
        result = mod.build_measurement_scope_frame(src, data)
        assert mod.validate_measurement_scope_frame(src, result) == result


def test_public_errors_are_sanitized_and_suppress_chaining():
    mod = api()
    src, data = example()
    data["facts"][0]["target_scopes"][0]["anchor"]["text"] = "private-secret"
    for function, value, message in [
        (mod.build_measurement_scope_frame, data, "Invalid measurement scope input"),
        (
            mod.validate_measurement_scope_frame,
            {"private-secret": "x"},
            "Invalid measurement scope frame",
        ),
    ]:
        with pytest.raises(mod.MeasurementScopeError) as caught:
            function(src, value)
        assert str(caught.value) == message
        assert caught.value.__suppress_context__ is True
        assert caught.value.__cause__ is None


@pytest.mark.parametrize("path", [("facts",), ("relations",), ("facts", 0, "target_scopes")])
def test_constructed_models_cannot_hide_wrong_tuple_containers_by_json_dump(path):
    mod = api()
    src, data = example()
    original = mod.build_measurement_scope_frame(src, data)
    bad = replace_model(original.input, path, list)
    with pytest.raises(mod.MeasurementScopeError):
        mod.build_measurement_scope_frame(src, bad)
    with pytest.raises(mod.MeasurementScopeError):
        mod.validate_measurement_scope_frame(src, original.model_copy(update={"input": bad}))


@pytest.mark.parametrize("role", ROLES)
def test_every_base_role_span_participates_in_wrapper_reconstruction(role):
    src, data = example()
    raw = api().build_measurement_scope_frame(src, data).model_dump(mode="json")
    replacement = deepcopy(raw["frame"]["resolved"]["facts"][1]["measured_entity"])
    raw["frame"]["resolved"]["facts"][0][role] = replacement
    with pytest.raises(api().MeasurementScopeError):
        api().validate_measurement_scope_frame(src, raw)


@pytest.mark.parametrize(
    "path", [("scopes",), ("scopes", 0, "target_scopes"), ("frame", "resolved", "relations")]
)
def test_resolved_collection_caps_and_alignment_reject_extra_entries(path):
    src, data = example()
    raw = api().build_measurement_scope_frame(src, data).model_dump(mode="json")
    target = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] *= 20
    with pytest.raises(api().MeasurementScopeError):
        api().validate_measurement_scope_frame(src, raw)


@pytest.mark.parametrize("field", ["input", "frame", "scopes"])
def test_original_input_base_frame_and_aligned_scopes_are_required(field):
    src, data = example()
    raw = api().build_measurement_scope_frame(src, data).model_dump(mode="json")
    del raw[field]
    with pytest.raises(api().MeasurementScopeError):
        api().validate_measurement_scope_frame(src, raw)


@pytest.mark.parametrize("status", ["observed", "planned", "forecast", "unknown"])
@pytest.mark.parametrize("tense", ["past", "present", "future", "unknown"])
def test_inherited_status_and_tense_keep_explicit_evidence_requirements(status, tense):
    src = document("기관 10명 전망 발표했다.")
    data = {
        "facts": [
            fact(
                value_status=status,
                reporting_tense=tense,
                status_text=anchor("전망"),
                reporting_tense_text=anchor("발표했다"),
            )
        ],
        "relations": [],
    }
    result = api().build_measurement_scope_frame(src, data)
    row = result.frame.resolved.facts[0]
    assert (row.value_status, row.reporting_tense) == (status, tense)
    for name, required in [
        ("status_text", status != "unknown"),
        ("reporting_tense_text", tense != "unknown"),
    ]:
        if required:
            bad = deepcopy(data)
            bad["facts"][0][name] = None
            with pytest.raises(api().MeasurementScopeError):
                api().build_measurement_scope_frame(src, bad)


def test_different_context_inputs_resolving_to_same_anchor_are_duplicates():
    src = document("동부 10명.")
    with pytest.raises(api().MeasurementScopeError):
        api().build_measurement_scope_frame(
            src,
            {
                "facts": [fact(scopes=[scope("동부"), scope("동부", "other", "동부 10명")])],
                "relations": [],
            },
        )


@pytest.mark.parametrize("mutation", ["quote", "snapshot", "workspace"])
def test_reconstruction_rejects_otherwise_canonical_changed_source(mutation):
    from hashlib import sha256

    mod = api()
    src, data = example()
    result = mod.build_measurement_scope_frame(src, data)
    sid, bundle, presentation = src
    raw = bundle.model_dump(mode="json")
    if mutation == "quote":
        raw["representation"]["text"] = raw["representation"]["text"].replace("10명", "11명")
        raw["representation"]["text_sha256"] = sha256(
            raw["representation"]["text"].encode()
        ).hexdigest()
        raw["citations"][0]["selector"]["quote"] = raw["citations"][0]["selector"]["quote"].replace(
            "10명", "11명"
        )
    elif mutation == "snapshot":
        sid = uuid4()
        presentation = presentation.model_copy(update={"snapshot_id": sid})
    else:
        workspace_id = uuid4()
        raw["document"]["workspace_id"] = str(workspace_id)
        presentation = presentation.model_copy(update={"workspace_id": workspace_id})
    bundle = type(bundle).model_validate_json(json.dumps(raw), strict=True)
    changed = (sid, bundle, presentation)
    # The changed canonical source is valid for a fresh frame; only stored linkage is stale.
    fresh = mod.build_measurement_scope_frame(changed, data)
    assert fresh != result
    with pytest.raises(mod.MeasurementScopeError):
        mod.validate_measurement_scope_frame(changed, result)
