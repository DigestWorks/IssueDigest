"""Synthetic v2 shared frames preserve complete quantities and exact source linkage."""

import importlib
import importlib.util
import json
import sys
from copy import deepcopy

import pytest
from pydantic import Field, create_model
from test_numeric_evidence import document


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_modules():
    package = importlib.import_module("issuedigest_agents")
    existing = set(sys.modules)
    attributes = vars(package).copy()
    yield
    for name in set(sys.modules) - existing:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)
    # A from-package import can reuse an unloaded module through this namespace.
    # Restore both caches so later frozen reload tests see the same class identities.
    for name in set(vars(package)) - attributes.keys():
        delattr(package, name)
    for name, value in attributes.items():
        setattr(package, name, value)


def api():
    name = "issuedigest_agents.shared_measurement_context_v2"
    assert importlib.util.find_spec(name) is not None, "Missing v2 shared frame"
    return importlib.import_module(name)


def anchor(text, sentence="s1", context=None):
    return dict(sentence_id=sentence, text=text, context_text=context)


def scope(text, sentence="s1", kind="geographic", context=None):
    return dict(kind=kind, anchor=anchor(text, sentence, context))


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


def event(**fields):
    return {
        "event_id": "e1",
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


def packet():
    return dict(contexts=[context()], events=[event()], bindings=[binding()], relations=[])


def example():
    src = document(
        "🧪 발표처는 알렸다. 내년 수요로 조건 충족 시 합성국 동부 청년 이용자 "
        "전월비 약\t37여 명 내외와 서부 이용자 61~79명 내외를 지원 목적으로 모집할 예정이다. "
        "학교 83개교도 참여한다."
    )
    data = packet()
    data["contexts"][0].update(
        measured_variable=anchor("이용자", "s2", "청년 이용자"),
        target_scopes=[scope("합성국", "s2")],
        period=anchor("내년", "s2"),
        value_status="planned",
        logical_condition=anchor("조건 충족 시", "s2"),
        purpose=anchor("지원 목적으로", "s2"),
        forecast_basis=anchor("수요로", "s2"),
        comparison_baseline=anchor("전월비", "s2"),
    )
    data["events"][0] = event(
        kind="attributed_report",
        reporting_actor=anchor("발표처"),
        predicate=anchor("알렸다"),
        reporting_tense="past",
    )
    data["bindings"] = [
        binding(
            target_scopes=[scope("동부", "s2"), scope("청년", "s2", "population")],
            status_evidence_sentence_id="s2",
        ),
        binding("n2", target_scopes=[scope("서부", "s2")], status_evidence_sentence_id="s2"),
    ]
    data["relations"] = [
        dict(
            kind="parallel",
            from_id="n1",
            to_id="n2",
            statement_sentence_ids=["s2"],
            cue=anchor("와", "s2"),
        )
    ]
    return src, data


def test_complete_v2_index_flat_roles_scopes_purpose_and_relation_reconstruct():
    mod = api()
    src, data = example()
    result = mod.build_shared_measurement_frame_v2(src, data)
    assert (result.profile, result.status) == ("shared-measurement-context-v2", "unreviewed")
    assert result.input.model_dump(mode="json") == data
    assert result.candidate_index.profile == "numeric-candidates-v2"
    assert [c.expression.text for c in result.candidate_index.candidates] == [
        "약\t37여 명 내외",
        "61~79명 내외",
        "83개교",
    ]
    assert [
        a.unit.text if a.unit else None for a in result.candidate_index.candidates[1].atoms
    ] == [None, "명"]
    assert [q.text for q in result.candidate_index.candidates[0].qualifiers] == ["약", "여", "내외"]
    assert [f.measured_entity.span.text for f in result.facts] == ["이용자"] * 2
    assert [(f.context_id, f.reporting_event_id) for f in result.facts] == [("c1", "e1")] * 2
    fact = result.facts[0]
    assert (
        fact.reporting_actor.span.text,
        fact.reporting_tense,
        fact.reporting_tense_text.span.text,
    ) == ("발표처", "past", "알렸다")
    assert (fact.value_status, fact.period.span.text, fact.logical_condition.span.text) == (
        "planned",
        "내년",
        "조건 충족 시",
    )
    assert (
        fact.purpose.span.text,
        fact.forecast_basis.span.text,
        fact.comparison_baseline.span.text,
    ) == ("지원 목적으로", "수요로", "전월비")
    assert fact.status_text.span == result.candidate_index.sentences[1].span
    assert [[s.anchor.span.text for s in f.target_scopes] for f in result.facts] == [
        ["합성국", "동부", "청년"],
        ["합성국", "서부"],
    ]
    relation = result.relations[0]
    assert relation.statement.text == result.candidate_index.sentences[1].span.text
    assert relation.cue.span.text == "와"
    assert mod.validate_shared_measurement_frame_v2(src, result) == result
    assert (
        mod.validate_shared_measurement_frame_v2(src, json.loads(result.model_dump_json()))
        == result
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_context",
        "duplicate_event",
        "unused_context",
        "missing_context",
        "unused_event",
        "missing_event",
        "duplicate_binding",
        "unknown_candidate",
        "status_missing",
        "status_other",
        "known_tense_missing",
        "combined_scopes",
        "duplicate_scope",
        "ambiguous_anchor",
        "wrong_purpose",
        "wrong_scope",
        "wrong_role",
        "duplicate_pair",
        "cycle",
        "statement_gap",
        "cue_outside",
        "no_entity",
        "no_binding_relation",
    ],
)
def test_whole_operation_rejects_invalid_links_evidence_scopes_and_relations(mutation):
    mod = api()
    src, data = example()
    if mutation == "duplicate_context":
        data["contexts"] *= 2
    elif mutation == "duplicate_event":
        data["events"] *= 2
    elif mutation == "unused_context":
        data["contexts"].append(context("c2"))
    elif mutation == "missing_context":
        data["bindings"][0]["context_id"] = "c2"
    elif mutation == "unused_event":
        data["events"].append(event(event_id="e2"))
    elif mutation == "missing_event":
        data["contexts"][0]["reporting_event_id"] = "e2"
    elif mutation == "duplicate_binding":
        data["bindings"] *= 2
    elif mutation == "unknown_candidate":
        data["bindings"][0]["candidate_id"] = "n99"
    elif mutation == "status_missing":
        data["bindings"][0]["status_evidence_sentence_id"] = None
    elif mutation == "status_other":
        data["bindings"][0]["status_evidence_sentence_id"] = "s3"
    elif mutation == "known_tense_missing":
        data["events"][0]["predicate"] = None
    elif mutation == "combined_scopes":
        data["contexts"][0]["target_scopes"] += [scope("내년", "s2"), scope("수요로", "s2")]
    elif mutation == "duplicate_scope":
        data["bindings"][0]["target_scopes"].append(scope("합성국", "s2", "other"))
    elif mutation == "ambiguous_anchor":
        data["contexts"][0]["measured_variable"] = anchor("이용자", "s2")
    elif mutation in ("wrong_purpose", "wrong_scope", "wrong_role"):
        src = document(src[1].citations[0].selector.quote, "다른 인용.")
        if mutation == "wrong_purpose":
            data["contexts"][0]["purpose"] = anchor("다른", "s4")
        elif mutation == "wrong_scope":
            data["bindings"][0]["target_scopes"] = [scope("다른", "s4")]
        else:
            data["events"][0]["reporting_actor"] = anchor("다른", "s4")
    elif mutation == "duplicate_pair":
        data["relations"] *= 2
    elif mutation == "cycle":
        data["bindings"].append(binding("n3", status_evidence_sentence_id="s3"))
        data["relations"] = [
            dict(
                kind="included_in",
                from_id=a,
                to_id=b,
                statement_sentence_ids=["s2", "s3"],
                cue=anchor("와", "s2"),
            )
            for a, b in (("n1", "n2"), ("n2", "n3"), ("n3", "n1"))
        ]
    elif mutation == "statement_gap":
        data["relations"][0]["statement_sentence_ids"] = ["s1", "s3"]
    elif mutation == "cue_outside":
        data["relations"][0]["cue"] = anchor("알렸다")
    elif mutation == "no_entity":
        data["contexts"][0]["measured_variable"] = None
    else:
        data["bindings"] = []
        data["contexts"] = []
        data["events"] = []
    with pytest.raises(mod.SharedMeasurementContextError) as caught:
        mod.build_shared_measurement_frame_v2(src, data)
    assert str(caught.value) == "Invalid shared measurement v2 input"
    assert caught.value.__cause__ is None


def test_unicode_whitespace_overlapping_context_and_short_relation_cue():
    mod = api()
    text = "🧪 e\u0301 가가가 동부 이용자 37여 명과 서부 이용자 59명, 동부 이용자도 포함."
    data = packet()
    data["contexts"][0]["measured_variable"] = anchor("이용자", context="서부 이용자")
    data["bindings"].append(binding("n2"))
    data["relations"] = [
        dict(
            kind="parallel",
            from_id="n1",
            to_id="n2",
            statement_sentence_ids=["s1"],
            cue=anchor("과", context="37여 명과 서부"),
        )
    ]
    result = mod.build_shared_measurement_frame_v2(document(text), data)
    got = result.facts[0].measured_entity.span
    assert (got.start, got.end, got.text) == (
        text.index("서부 이용자") + 3,
        text.index("서부 이용자") + 6,
        "이용자",
    )
    assert result.relations[0].cue.span.text == "과"
    data["contexts"][0]["purpose"] = anchor("가가", context="가가가")
    with pytest.raises(mod.SharedMeasurementContextError):
        mod.build_shared_measurement_frame_v2(document(text), data)


@pytest.mark.parametrize(
    "node",
    [
        "input_dict",
        "contexts_list",
        "context_dict",
        "anchor_dict",
        "scope_dict",
        "subclass",
        "index_dict",
        "candidates_list",
        "candidate_dict",
        "fact_dict",
        "scopes_list",
        "purpose_dict",
        "relations_list",
    ],
)
def test_unchecked_nested_models_and_containers_rejected_before_serialization(node):
    mod = api()
    src, data = example()
    result = mod.build_shared_measurement_frame_v2(src, data)
    inp, row = result.input, result.input.contexts[0]
    if node == "input_dict":
        forged = result.model_copy(update={"input": inp.model_dump(mode="json")})
    elif node in ("contexts_list", "context_dict", "anchor_dict", "scope_dict", "subclass"):
        if node == "contexts_list":
            inp = inp.model_copy(update={"contexts": list(inp.contexts)})
        else:
            if node == "anchor_dict":
                row = row.model_copy(update={"purpose": row.purpose.model_dump()})
            elif node == "scope_dict":
                row = row.model_copy(update={"target_scopes": (row.target_scopes[0].model_dump(),)})
            elif node == "subclass":
                extra = create_model(
                    "ExtraContext",
                    __base__=type(row),
                    secret=(str, Field(default="hidden", exclude=True)),
                )
                row = extra.model_validate(row.model_dump())
            else:
                row = row.model_dump()
            inp = inp.model_copy(update={"contexts": (row,)})
        forged = result.model_copy(update={"input": inp})
    elif node.startswith("index") or node in ("candidates_list", "candidate_dict"):
        idx = result.candidate_index
        idx = (
            idx.model_dump()
            if node == "index_dict"
            else idx.model_copy(
                update={
                    "candidates": list(idx.candidates)
                    if node == "candidates_list"
                    else (idx.candidates[0].model_dump(),)
                }
            )
        )
        forged = result.model_copy(update={"candidate_index": idx})
    elif node == "relations_list":
        forged = result.model_copy(update={"relations": list(result.relations)})
    else:
        fact = result.facts[0]
        fact = (
            fact.model_dump()
            if node == "fact_dict"
            else fact.model_copy(
                update={"target_scopes": list(fact.target_scopes)}
                if node == "scopes_list"
                else {"purpose": fact.purpose.model_dump()}
            )
        )
        forged = result.model_copy(update={"facts": (fact, result.facts[1])})
    with pytest.raises(mod.SharedMeasurementContextError):
        mod.validate_shared_measurement_frame_v2(src, forged)
    if node in ("contexts_list", "context_dict", "anchor_dict", "scope_dict", "subclass"):
        with pytest.raises(mod.SharedMeasurementContextError):
            mod.build_shared_measurement_frame_v2(src, inp)


@pytest.mark.parametrize(
    "change",
    [
        "version",
        "index_version",
        "omit_candidate",
        "expression",
        "purpose",
        "extra",
        "source_drift",
    ],
)
def test_stored_complete_reconstruction_rejects_tampering_and_v1_crossing(change):
    mod = api()
    src, data = example()
    raw = json.loads(mod.build_shared_measurement_frame_v2(src, data).model_dump_json())
    if change == "version":
        raw["profile"] = "shared-measurement-context-v1"
    elif change == "index_version":
        raw["candidate_index"]["profile"] = "numeric-candidates-v1"
    elif change == "omit_candidate":
        raw["candidate_index"]["candidates"].pop()
    elif change == "expression":
        raw["candidate_index"]["candidates"][0]["expression"]["text"] = "37"
    elif change == "purpose":
        raw["facts"][0]["purpose"] = None
    elif change == "extra":
        raw["certified"] = True
    else:
        src = document(src[1].citations[0].selector.quote + " 추가.")
    with pytest.raises(mod.SharedMeasurementContextError):
        mod.validate_shared_measurement_frame_v2(src, raw)


def test_empty_frame_and_v1_result_remain_separate():
    mod = api()
    old = importlib.import_module("issuedigest_agents.shared_measurement_context")
    src = document("학교 83개교, 이용자 37여 명 내외.")
    data = packet()
    before = old.build_shared_measurement_frame(src, deepcopy(data))
    result = mod.build_shared_measurement_frame_v2(src, data)
    assert before.frame.frame.resolved.candidate_index.candidates[0].expression.text == "83개"
    assert result.candidate_index.candidates[0].expression.text == "83개교"
    assert old.build_shared_measurement_frame(src, data) == before
    with pytest.raises(mod.SharedMeasurementContextError):
        mod.validate_shared_measurement_frame_v2(src, before)
    with pytest.raises(old.SharedMeasurementContextError):
        old.validate_shared_measurement_frame(src, result)
    empty = mod.build_shared_measurement_frame_v2(
        document("수치 없음."), dict(contexts=[], events=[], bindings=[], relations=[])
    )
    assert empty.facts == empty.relations == empty.candidate_index.candidates == ()
