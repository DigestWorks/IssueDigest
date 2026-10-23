"""Synthetic question-specific source contracts, without semantic certification."""

import importlib
import importlib.util
import json
from copy import deepcopy
from hashlib import sha256
from uuid import uuid4

import pytest
from pydantic import BaseModel, ValidationError, create_model
from test_numeric_evidence import document
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.question_evidence_propositions"
    assert importlib.util.find_spec(name) is not None, "Missing question evidence contract"
    return importlib.import_module(name)


def test_empty_non_numeric_source_keeps_unresolved_question_explicit():
    mod = api()
    src = document("기관의 승인이 필요하다.")
    data = dict(
        propositions=[],
        coverage=dict(linked_proposition_ids=[], unresolved_reason="no_linked_evidence"),
    )
    result = mod.build_question_evidence_propositions(src, "신청 조건은?", data)
    assert result.propositions == ()
    assert result.coverage.unresolved_reason == "no_linked_evidence"
    assert result.status == "unreviewed"
    assert mod.validate_question_evidence_propositions(src, "신청 조건은?", result) == result


QUESTION = "  어떤 조건과 기한인가? 🧪  "
TEXT = (
    "🧪 기관은 좌석·수용 인원 각각 3 이내를 계획한다. "
    "승인 후 다음 달 신청 예정이며 법적 지위 부여 아님. 기관은 반복한다 e\u0301."
)


class Text(str):
    pass


class Integer(int):
    pass


class Number(float):
    pass


class Array(list):
    pass


class Object(dict):
    pass


class Tuple(tuple):
    pass


def ref(src, text, citation=0, start=None):
    quote = src[1].citations[citation].selector.quote
    if start is None:
        start = quote.index(text)
    return dict(
        citation_id=str(src[1].citations[citation].citation_id),
        start=start,
        end=start + len(text),
        text=text,
    )


def facet(identifier, kind, value, refs, targets=()):
    return dict(id=identifier, kind=kind, value=value, refs=refs, target_ids=list(targets))


def proposition(src, identifier="p1", **updates):
    quote = src[1].citations[0].selector.quote
    return (
        dict(
            id=identifier,
            epistemic_status="source_statement",
            supporting_refs=[ref(src, quote)],
            subject_refs=[ref(src, "기관")],
            predicate_refs=[ref(src, "계획한다")],
            facets=[],
            depends_on_ids=[],
        )
        | updates
    )


def packet(src):
    r = lambda text: ref(src, text)  # noqa: E731
    number, seats, people = r("3"), r("좌석"), r("수용 인원")
    facets = [
        facet("f1", "quantity", dict(expression=number, metric_refs=[seats]), [number, seats]),
        facet("f2", "quantity", dict(expression=number, metric_refs=[people]), [number, people]),
        facet("f3", "bound", dict(operator="lte"), [r("이내")], ["f1"]),
        facet(
            "f4",
            "distribution",
            dict(mode="per_member", member_refs=[seats, people]),
            [r("각각"), seats, people],
            ["f2"],
        ),
        facet(
            "f5",
            "time",
            dict(kind="relative", literal_ref=r("다음 달"), anchor_refs=[r("승인 후")]),
            [r("다음 달"), r("승인 후")],
        ),
        facet("f6", "eligibility", dict(literal_ref=r("기관")), [r("기관")]),
        facet("f7", "prerequisite", dict(literal_ref=r("승인 후")), [r("승인 후")]),
        facet(
            "f8",
            "legal_effect",
            dict(polarity="negated", literal_ref=r("지위 부여 아님")),
            [r("지위 부여 아님")],
        ),
        facet(
            "f9",
            "procedure",
            dict(state="planned", literal_ref=r("신청 예정")),
            [r("신청 예정")],
        ),
    ]
    return dict(
        propositions=[proposition(src, facets=facets)],
        coverage=dict(linked_proposition_ids=["p1"], unresolved_reason=None),
    )


def put(obj, path, replacement):
    for key in path[:-1]:
        obj = obj[key]
    obj[path[-1]] = replacement


def at(obj, path):
    for key in path:
        obj = obj[key]
    return obj


def rejected(mod, operation, *args):
    with pytest.raises(mod.QuestionEvidenceError) as caught:
        operation(*args)
    assert str(caught.value) == "Invalid question evidence propositions"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__ is True
    assert caught.value.__dict__ == {}


def test_all_facet_variants_share_number_preserve_cues_order_and_raw_actual_roundtrip():
    mod, src = api(), document(TEXT)
    data = packet(src)
    before = deepcopy(data)
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert data == before
    assert result.model_dump(mode="json")["propositions"] == data["propositions"]
    assert result.profile == "question-evidence-propositions-v1"
    assert result.status == "unreviewed"
    f = result.propositions[0].facets
    assert f[0].value.expression == f[1].value.expression
    assert [f[i].value.metric_refs[0].text for i in (0, 1)] == ["좌석", "수용 인원"]
    assert [f[i].refs[0].text for i in (2, 3, 4, 7, 8)] == [
        "이내",
        "각각",
        "다음 달",
        "지위 부여 아님",
        "신청 예정",
    ]
    assert f[2].value.operator == "lte" and f[2].target_ids == ("f1",)
    assert f[7].value.polarity == "negated"
    assert result.question_sha256 == sha256(QUESTION.encode("utf-8")).hexdigest()
    canonical_source = {
        "snapshot_id": str(src[0]),
        "bundle": src[1].model_dump(mode="json"),
        "presentation": src[2].model_dump(mode="json"),
    }
    expected_source_hash = sha256(
        json.dumps(
            canonical_source, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()
    assert result.source_sha256 == expected_source_hash
    for original in (result, result.model_dump(mode="json")):
        checked = mod.validate_question_evidence_propositions(src, QUESTION, original)
        assert checked == result and checked is not result
        assert checked.propositions[0] is not result.propositions[0]
    typed = mod.QuestionEvidenceInput.model_validate_json(json.dumps(data), strict=True)
    assert mod.build_question_evidence_propositions(src, QUESTION, typed) == result


def test_quote_relative_unicode_offsets_multiple_quotes_repetition_and_long_refs():
    mod = api()
    src = document("기관은 계획한다 원문 앞부분", "🧪 기관은 계획한다 e\u0301 기관 " + "긴" * 1100)
    quote = src[1].citations[1].selector.quote
    second = quote.index("기관", quote.index("기관") + 1)
    p = proposition(
        src,
        supporting_refs=[ref(src, quote, 1)],
        subject_refs=[ref(src, "기관", 1, second)],
        predicate_refs=[ref(src, "계획한다", 1)],
    )
    data = dict(
        propositions=[p], coverage=dict(linked_proposition_ids=["p1"], unresolved_reason=None)
    )
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.propositions[0].subject_refs[0].start == second
    assert result.propositions[0].supporting_refs[0].text == quote
    for replacement in (second + 1, len(quote[:second].encode("utf-8"))):
        bad = deepcopy(data)
        bad["propositions"][0]["subject_refs"][0]["start"] = replacement
        rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, bad)
    bad = deepcopy(data)
    bad["propositions"][0]["subject_refs"][0]["text"] = "é"
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, bad)


@pytest.mark.parametrize("reason", [None, "ambiguous", "insufficient", "no_linked_evidence"])
@pytest.mark.parametrize("linked", [False, True])
def test_coverage_connection_reason_rules_without_completion_claims(reason, linked):
    mod, src = api(), document(TEXT)
    data = packet(src)
    data["coverage"] = dict(
        linked_proposition_ids=["p1"] if linked else [], unresolved_reason=reason
    )
    if (not linked and reason is None) or (linked and reason == "no_linked_evidence"):
        rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)
    else:
        result = mod.build_question_evidence_propositions(src, QUESTION, data)
        assert result.coverage.unresolved_reason == reason
        assert result.status == "unreviewed"


@pytest.mark.parametrize(
    "path",
    [
        ("subject_refs",),
        ("predicate_refs",),
        ("facets", 0, "value", "metric_refs"),
        ("facets", 4, "value", "anchor_refs"),
    ],
)
def test_missing_evidence_demands_explicit_uncertain_and_is_never_upgraded(path):
    mod, src = api(), document(TEXT)
    data = packet(src)
    put(data["propositions"][0], path, [])
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)
    data["propositions"][0]["epistemic_status"] = "uncertain"
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.propositions[0].epistemic_status == "uncertain"


def test_non_numeric_facets_empty_dependency_and_semantic_mislabel_are_structurally_valid():
    mod = api()
    src = document("기관은 계획한다. 법적 지위 부여 아님.")
    p = proposition(
        src,
        facets=[
            facet("f1", "prerequisite", dict(literal_ref=ref(src, "기관")), [ref(src, "기관")])
        ],
    )
    data = dict(
        propositions=[p],
        coverage=dict(linked_proposition_ids=["p1"], unresolved_reason="insufficient"),
    )
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.propositions[0].depends_on_ids == ()
    # A quantity attached to legal wording is deliberately semantically wrong, but exact.
    literal = ref(src, "지위 부여 아님")
    p["facets"] = [facet("f1", "quantity", dict(expression=literal, metric_refs=[]), [literal])]
    p["epistemic_status"] = "uncertain"
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.propositions[0].facets[0].value.expression.text == "지위 부여 아님"
    assert set(result.model_dump()) == {
        "profile",
        "status",
        "question_sha256",
        "source_sha256",
        "propositions",
        "coverage",
    }
    assert result.status == "unreviewed"


def test_dependencies_preserve_dependent_to_prerequisite_order_and_reject_cycles():
    mod, src = api(), document(TEXT)
    data = packet(src)
    data["propositions"] += [proposition(src, "p2"), proposition(src, "p3")]
    data["propositions"][0]["depends_on_ids"] = ["p3", "p2"]
    data["propositions"][1]["depends_on_ids"] = ["p3"]
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.propositions[0].depends_on_ids == ("p3", "p2")
    for edges in (["p1"], ["p2"], ["p24"], ["p2", "p2"]):
        bad = deepcopy(data)
        bad["propositions"][2]["depends_on_ids"] = edges
        rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, bad)


@pytest.mark.parametrize(
    "question", ["", " \t\n", "x" * 2001, "\ud800", 1, True, None, Text("질문")]
)
def test_invalid_original_questions_are_not_coerced_or_truncated(question):
    mod, src = api(), document(TEXT)
    rejected(mod, mod.build_question_evidence_propositions, src, question, packet(src))


def test_question_limit_and_literal_whitespace_hash_do_not_normalize():
    mod, src = api(), document(TEXT)
    result = mod.build_question_evidence_propositions(src, "🧪" * 2000, packet(src))
    assert result.question_sha256 == sha256(("🧪" * 2000).encode()).hexdigest()
    result = mod.build_question_evidence_propositions(src, QUESTION, packet(src))
    for question in (QUESTION.strip(), QUESTION + " ", QUESTION.replace("🧪", "")):
        rejected(mod, mod.validate_question_evidence_propositions, src, question, result)


def test_source_receipt_binds_identity_presentation_quote_order_and_source_text():
    mod, src = api(), document(TEXT, "별도 인용")
    result = mod.build_question_evidence_propositions(src, QUESTION, packet(src))
    new_id = uuid4()
    variants = [
        (new_id, src[1], src[2].model_copy(update={"snapshot_id": new_id})),
        (src[0], src[1], src[2].model_copy(update={"title": "변경된 제목"})),
        (src[0], src[1].model_copy(update={"citations": src[1].citations[::-1]}), src[2]),
        document(TEXT, "변경된 별도 인용"),
    ]
    for changed in variants:
        rejected(mod, mod.validate_question_evidence_propositions, changed, QUESTION, result)


@pytest.mark.parametrize(
    "path,replacement",
    [
        (("propositions", 0, "id"), "p0"),
        (("propositions", 0, "id"), "p25"),
        (("propositions", 0, "epistemic_status"), "verified"),
        (("propositions", 0, "facets", 0, "id"), "f17"),
        (("propositions", 0, "facets", 0, "kind"), "summary"),
        (("propositions", 0, "facets", 2, "value", "operator"), "at_most"),
        (("propositions", 0, "facets", 3, "value", "mode"), "each"),
        (("propositions", 0, "facets", 4, "value", "kind"), "date"),
        (("propositions", 0, "facets", 7, "value", "polarity"), "false"),
        (("propositions", 0, "facets", 8, "value", "state"), "completed"),
        (("coverage", "linked_proposition_ids"), ["p2"]),
        (("coverage", "linked_proposition_ids"), ["p1", "p1"]),
        (("coverage", "unresolved_reason"), "complete"),
    ],
)
def test_invalid_domains_enums_and_links_reject_whole_operation(path, replacement):
    mod, src = api(), document(TEXT)
    data = packet(src)
    put(data, path, replacement)
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


def object_paths(value, path=()):
    if type(value) is dict:
        yield path
        for key, child in value.items():
            yield from object_paths(child, (*path, key))
    elif type(value) is list:
        for i, child in enumerate(value):
            yield from object_paths(child, (*path, i))


def test_every_raw_root_nested_nullable_and_empty_field_is_required_and_extras_rejected():
    mod, src = api(), document(TEXT)
    result = mod.build_question_evidence_propositions(src, QUESTION, packet(src))
    raw = result.model_dump(mode="json")
    for path in object_paths(raw):
        for field in [*at(raw, path), "unexpected"]:
            bad = deepcopy(raw)
            target = at(bad, path)
            if field == "unexpected":
                target[field] = "private input must never appear in errors"
            else:
                del target[field]
            rejected(mod, mod.validate_question_evidence_propositions, src, QUESTION, bad)
    for field in ("propositions", "coverage"):
        data = packet(src)
        del data[field]
        rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize(
    "path,replacement",
    [
        (("profile",), "question-evidence-propositions-v2"),
        (("status",), "verified"),
        (("question_sha256",), "0" * 64),
        (("source_sha256",), "0" * 64),
        (("source_sha256",), "A" * 64),
        (("question_sha256",), "not-a-hash"),
    ],
)
def test_receipt_markers_and_hashes_are_freshly_revalidated(path, replacement):
    mod, src = api(), document(TEXT)
    result = mod.build_question_evidence_propositions(src, QUESTION, packet(src))
    raw = result.model_dump(mode="json")
    put(raw, path, replacement)
    rejected(mod, mod.validate_question_evidence_propositions, src, QUESTION, raw)
    changed = result.model_copy(update={path[0]: replacement})
    rejected(mod, mod.validate_question_evidence_propositions, src, QUESTION, changed)


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("citation_id", "missing"),
        ("citation_id", Text("missing")),
        ("start", True),
        ("start", 0.0),
        ("start", Integer(0)),
        ("start", Number(0.0)),
        ("end", False),
        ("end", 1.0),
        ("start", -1),
        ("start", 9999),
        ("end", 9999),
        ("end", 0),
        ("text", ""),
        ("text", " "),
        ("text", "\ud800"),
        ("text", Text("기관")),
        ("text", "기 관"),
    ],
)
def test_exact_ref_scalar_offset_utf8_and_slice_rules(field, replacement):
    mod, src = api(), document(TEXT)
    data = packet(src)
    data["propositions"][0]["subject_refs"][0][field] = replacement
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize(
    "path",
    [
        ("subject_refs",),
        ("predicate_refs",),
        ("facets", 0, "refs"),
        ("facets", 0, "value", "metric_refs"),
        ("facets", 3, "value", "member_refs"),
        ("facets", 4, "value", "anchor_refs"),
    ],
)
def test_element_refs_require_support_and_nested_refs_require_facet_membership(path):
    mod, src = api(), document(TEXT, "기관 계획한다 다음 달")
    data = packet(src)
    put(data["propositions"][0], path, [ref(src, "기관", 1)])
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)
    # A valid same-source nested ref still cannot silently add evidence absent from facet.refs.
    if "value" in path:
        data = packet(src)
        put(data["propositions"][0], path, [ref(src, "기관")])
        rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize(
    "index,field",
    [
        (0, "expression"),
        (4, "literal_ref"),
        (5, "literal_ref"),
        (6, "literal_ref"),
        (7, "literal_ref"),
        (8, "literal_ref"),
    ],
)
def test_every_value_nested_ref_must_exactly_match_a_facet_ref(index, field):
    mod, src = api(), document(TEXT)
    data = packet(src)
    data["propositions"][0]["facets"][index]["value"][field] = ref(src, "계획한다")
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize(
    "path",
    [
        ("supporting_refs",),
        ("subject_refs",),
        ("predicate_refs",),
        ("facets", 0, "refs"),
        ("facets", 0, "value", "metric_refs"),
        ("facets", 3, "value", "member_refs"),
        ("facets", 4, "value", "anchor_refs"),
    ],
)
def test_duplicates_in_each_ref_list_rejected_but_cross_field_sharing_is_valid(path):
    mod, src = api(), document(TEXT)
    data = packet(src)
    current = at(data["propositions"][0], path)
    put(data["propositions"][0], path, current + current[:1])
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize(
    "scenario",
    [
        "proposition",
        "facet",
        "target_duplicate",
        "target_self",
        "target_kind",
        "target_missing",
        "target_other_owner",
        "target_empty",
        "target_multiple",
        "other_kind_target",
        "distribution_empty",
        "collective_empty",
    ],
)
def test_id_uniqueness_local_quantity_targets_and_distribution_member_rules(scenario):
    mod, src = api(), document(TEXT)
    data = packet(src)
    p = data["propositions"][0]
    if scenario == "proposition":
        data["propositions"].append(deepcopy(p))
    elif scenario == "facet":
        p["facets"].append(deepcopy(p["facets"][0]))
    elif scenario == "target_other_owner":
        q = proposition(src, "p2", facets=[{**deepcopy(p["facets"][0]), "id": "f16"}])
        data["propositions"].append(q)
        p["facets"][2]["target_ids"] = ["f16"]
    elif scenario in ("distribution_empty", "collective_empty"):
        p["facets"][3]["value"].update(
            mode="collective" if scenario == "collective_empty" else "per_member", member_refs=[]
        )
    elif scenario == "other_kind_target":
        p["facets"][0]["target_ids"] = ["f2"]
    else:
        p["facets"][2]["target_ids"] = {
            "target_duplicate": ["f1", "f1"],
            "target_self": ["f3"],
            "target_kind": ["f5"],
            "target_missing": ["f16"],
            "target_empty": [],
            "target_multiple": ["f1", "f2"],
        }[scenario]
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


def test_unknown_states_remain_explicit_and_never_infer_bounds_dates_or_dependencies():
    mod, src = api(), document(TEXT)
    data = packet(src)
    facets = data["propositions"][0]["facets"]
    facets[2]["value"]["operator"] = "unknown"
    facets[3]["value"].update(mode="unknown", member_refs=[])
    facets[4]["value"].update(kind="unknown", anchor_refs=[])
    facets[7]["value"]["polarity"] = "unknown"
    facets[8]["value"]["state"] = "unknown"
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.model_dump(mode="json")["propositions"] == data["propositions"]
    data["propositions"][0]["facets"] = facets[:2]
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert [f.kind for f in result.propositions[0].facets] == ["quantity", "quantity"]


def typed_replace(value, path, replacement):
    if not path:
        return replacement
    key, *rest = path
    if isinstance(value, BaseModel):
        return value.model_copy(update={key: typed_replace(getattr(value, key), rest, replacement)})
    children = list(value)
    children[key] = typed_replace(children[key], rest, replacement)
    return tuple(children)


@pytest.mark.parametrize(
    "scenario",
    [
        "raw_tuple",
        "raw_nested_model",
        "raw_list_subclass",
        "raw_dict_subclass",
        "raw_key_subclass",
        "raw_text_subclass",
        "raw_int_subclass",
        "raw_float",
        "raw_bool",
        "actual_list",
        "actual_tuple_subclass",
        "actual_dict",
        "actual_model_subclass",
        "actual_nested_subclass",
        "actual_text_subclass",
        "actual_int_subclass",
        "actual_bool",
        "actual_wrong_value_model",
        "actual_missing_status",
        "actual_missing_nested",
        "actual_extra",
        "actual_wrong_root",
        "raw_wrong_root",
    ],
)
def test_original_raw_actual_shapes_reject_before_any_serialization(monkeypatch, scenario):
    mod, src = api(), document(TEXT)
    original = mod.build_question_evidence_propositions(src, QUESTION, packet(src))
    value = original.model_dump(mode="json") if scenario.startswith("raw_") else original
    subject = ("propositions", 0, "subject_refs")
    if scenario == "raw_tuple":
        value["propositions"] = tuple(value["propositions"])
    elif scenario == "raw_nested_model":
        value["coverage"] = original.coverage
    elif scenario == "raw_list_subclass":
        value["propositions"] = Array(value["propositions"])
    elif scenario == "raw_dict_subclass":
        value["coverage"] = Object(value["coverage"])
    elif scenario == "raw_key_subclass":
        value["coverage"] = {Text(k): v for k, v in value["coverage"].items()}
    elif scenario == "raw_text_subclass":
        value["status"] = Text("unreviewed")
    elif scenario == "raw_int_subclass":
        put(value, (*subject, 0, "start"), Integer(at(value, (*subject, 0, "start"))))
    elif scenario == "raw_float":
        put(value, (*subject, 0, "start"), float(at(value, (*subject, 0, "start"))))
    elif scenario == "raw_bool":
        put(value, (*subject, 0, "start"), True)
    elif scenario == "actual_list":
        value = original.model_copy(update={"propositions": list(original.propositions)})
    elif scenario == "actual_tuple_subclass":
        value = original.model_copy(update={"propositions": Tuple(original.propositions)})
    elif scenario == "actual_dict":
        value = original.model_copy(update={"coverage": original.coverage.model_dump()})
    elif scenario == "actual_model_subclass":
        cls = create_model("ImpostorReceipt", __base__=type(original))
        value = cls.model_validate_json(original.model_dump_json())
    elif scenario == "actual_nested_subclass":
        p = original.propositions[0]
        cls = create_model("ImpostorProposition", __base__=type(p))
        value = typed_replace(
            original, ("propositions", 0), cls.model_validate_json(p.model_dump_json())
        )
    elif scenario == "actual_text_subclass":
        value = typed_replace(original, (*subject, 0, "text"), Text("기관"))
    elif scenario == "actual_int_subclass":
        value = typed_replace(original, (*subject, 0, "start"), Integer(2))
    elif scenario == "actual_bool":
        value = typed_replace(original, (*subject, 0, "start"), True)
    elif scenario == "actual_wrong_value_model":
        value = typed_replace(
            original, ("propositions", 0, "facets", 0, "value"), original.coverage
        )
    elif scenario == "actual_missing_status":
        value = deepcopy(original)
        del value.__dict__["status"]
    elif scenario == "actual_missing_nested":
        value = deepcopy(original)
        del value.propositions[0].facets[0].value.__dict__["metric_refs"]
    elif scenario == "actual_extra":
        value = original.model_copy(update={"private": "hidden input"})
    elif scenario == "actual_wrong_root":
        value = original.coverage
    elif scenario == "raw_wrong_root":
        value = []
    dumps = []

    def forbidden(*args, **kwargs):
        dumps.append(True)
        raise AssertionError("Invalid original was serialized")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    rejected(mod, mod.validate_question_evidence_propositions, src, QUESTION, value)
    assert dumps == []


@pytest.mark.parametrize(
    "scenario",
    [
        "list",
        "tuple_subclass",
        "snapshot_string",
        "snapshot_mismatch",
        "workspace_mismatch",
        "bundle_subclass",
        "presentation_subclass",
        "source_scalar_subclass",
        "source_int_bool",
        "source_array",
        "source_missing_default",
        "source_extra",
        "text_hash",
        "quote_text",
        "version_chain",
        "representation_chain",
        "citation_chain",
        "presentation_blank",
    ],
)
def test_original_source_shapes_and_full_current_provenance_guard_before_dump(
    monkeypatch, scenario
):
    mod, src = api(), document(TEXT)
    data = packet(src)
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    changed = src
    if scenario == "list":
        changed = list(src)
    elif scenario == "tuple_subclass":
        changed = Tuple(src)
    elif scenario == "snapshot_string":
        changed = (str(src[0]), *src[1:])
    elif scenario == "snapshot_mismatch":
        changed = (uuid4(), *src[1:])
    elif scenario == "workspace_mismatch":
        changed = (src[0], src[1], src[2].model_copy(update={"workspace_id": uuid4()}))
    elif scenario in ("bundle_subclass", "presentation_subclass"):
        i = 1 if scenario == "bundle_subclass" else 2
        cls = create_model("ImpostorSource", __base__=type(src[i]))
        changed = tuple(
            cls.model_validate_json(child.model_dump_json()) if j == i else child
            for j, child in enumerate(src)
        )
    elif scenario == "source_scalar_subclass":
        changed = typed_replace(src, (1, "representation", "text"), Text(TEXT))
    elif scenario == "source_int_bool":
        changed = typed_replace(src, (1, "schema_version"), True)
    elif scenario == "source_array":
        changed = typed_replace(src, (1, "citations"), list(src[1].citations))
    elif scenario == "source_missing_default":
        changed = deepcopy(src)
        del changed[1].__dict__["schema_version"]
    elif scenario == "source_extra":
        changed = (src[0], src[1].model_copy(update={"hidden": "private"}), src[2])
    elif scenario == "text_hash":
        changed = typed_replace(src, (1, "representation", "text_sha256"), "0" * 64)
    elif scenario == "quote_text":
        changed = typed_replace(src, (1, "citations", 0, "selector", "quote"), "원문 불일치")
    elif scenario == "version_chain":
        changed = typed_replace(src, (1, "version", "document_id"), uuid4())
    elif scenario == "representation_chain":
        changed = typed_replace(src, (1, "representation", "document_version_id"), uuid4())
    elif scenario == "citation_chain":
        changed = typed_replace(src, (1, "citations", 0, "representation_id"), uuid4())
    elif scenario == "presentation_blank":
        changed = typed_replace(src, (2, "title"), " ")
    dumps = []

    def forbidden(*args, **kwargs):
        dumps.append(True)
        raise AssertionError("Invalid source was serialized")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    rejected(mod, mod.build_question_evidence_propositions, changed, QUESTION, data)
    rejected(mod, mod.validate_question_evidence_propositions, changed, QUESTION, result)
    assert dumps == []


@pytest.mark.parametrize(
    "path",
    [
        ("propositions",),
        ("propositions", 0, "supporting_refs"),
        ("propositions", 0, "subject_refs"),
        ("propositions", 0, "predicate_refs"),
        ("propositions", 0, "facets"),
        ("propositions", 0, "depends_on_ids"),
        ("propositions", 0, "facets", 0, "refs"),
        ("propositions", 0, "facets", 0, "value", "metric_refs"),
        ("propositions", 0, "facets", 3, "value", "member_refs"),
        ("propositions", 0, "facets", 4, "value", "anchor_refs"),
        ("coverage", "linked_proposition_ids"),
    ],
)
def test_list_caps_have_valid_exact_boundaries_and_reject_only_one_extra(path):
    mod, src = api(), document(TEXT)
    data = packet(src)
    p = data["propositions"][0]
    cap = (
        24
        if path in (("propositions",), ("coverage", "linked_proposition_ids"))
        else 16
        if path == ("propositions", 0, "facets")
        else 8
    )
    if path in (
        ("propositions",),
        ("coverage", "linked_proposition_ids"),
        ("propositions", 0, "depends_on_ids"),
    ):
        # IDs beyond the domain would mask the 24-proposition cap, so the rejected
        # 25th row deliberately reuses a valid ID; coverage has the same finite domain.
        data["propositions"] = [proposition(src, f"p{i}") for i in range(1, 25)]
        if path == ("propositions",):
            pass
        elif path == ("coverage", "linked_proposition_ids"):
            data["coverage"]["linked_proposition_ids"] = [f"p{i}" for i in range(24, 0, -1)]
        else:
            data["propositions"][0]["depends_on_ids"] = [f"p{i}" for i in range(2, 10)]
    elif path == ("propositions", 0, "facets"):
        p["facets"] = [
            facet(f"f{i}", "eligibility", dict(literal_ref=ref(src, "기관")), [ref(src, "기관")])
            for i in range(1, 17)
        ]
    else:
        refs = [ref(src, TEXT[:i]) for i in range(1, 10)]
        # Every prefix starts with a visible emoji, so refs are distinct and nonblank.
        put(data, path, refs[:8])
        if "value" in path:
            index = path[3]
            p["facets"][index]["refs"] = refs[:8]
            value = p["facets"][index]["value"]
            if "expression" in value:
                value["expression"] = refs[0]
            if "literal_ref" in value:
                value["literal_ref"] = refs[0]
        if path == ("propositions", 0, "facets", 0, "refs"):
            p["facets"][0]["value"] = dict(expression=refs[0], metric_refs=[refs[1]])
        if path == ("propositions", 0, "supporting_refs"):
            # Distinct whole-suffix supports retain all facet containment, unlike prefixes.
            put(data, path, [ref(src, TEXT[i:]) for i in range(8)])
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert len(at(result.model_dump(mode="json"), path)) == cap
    bad = deepcopy(data)
    values = at(bad, path)
    if path == ("propositions", 0, "depends_on_ids"):
        extra = "p10"
    elif path in (
        ("propositions",),
        ("coverage", "linked_proposition_ids"),
        ("propositions", 0, "facets"),
    ):
        extra = deepcopy(values[0])
    elif path == ("propositions", 0, "supporting_refs"):
        extra = ref(src, TEXT[8:])
    else:
        extra = ref(src, TEXT[:9])
    put(bad, path, values + [extra])
    # Finite ID domains and nested membership can independently reject over-cap
    # data. Assert the DTO itself rejects its array length before those checks,
    # so a removed cap cannot hide behind a later structural rejection.
    with pytest.raises(ValidationError) as caught:
        mod.QuestionEvidenceInput.model_validate_json(json.dumps(bad), strict=True)
    assert any(
        error["type"] == "too_long"
        and error["loc"][-1] == path[-1]
        and error["ctx"]["max_length"] == cap
        for error in caught.value.errors()
    )
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, bad)


def test_actual_stored_nested_span_mutations_and_raw_rejection_do_not_mutate_inputs():
    mod, src = api(), document(TEXT)
    original = mod.build_question_evidence_propositions(src, QUESTION, packet(src))
    for replacement in ("기 관", "기관은"):
        bad = typed_replace(original, ("propositions", 0, "subject_refs", 0, "text"), replacement)
        before = bad.model_dump(mode="json")
        rejected(mod, mod.validate_question_evidence_propositions, src, QUESTION, bad)
        assert bad.model_dump(mode="json") == before
    raw = original.model_dump(mode="json")
    raw["propositions"][0]["depends_on_ids"] = ["p1"]
    before = deepcopy(raw)
    rejected(mod, mod.validate_question_evidence_propositions, src, QUESTION, raw)
    assert raw == before
    assert mod.validate_question_evidence_propositions(src, QUESTION, original) == original


@pytest.mark.parametrize(
    "index,field,value",
    [
        (2, "operator", "eq"),
        (2, "operator", "gte"),
        (2, "operator", "gt"),
        (2, "operator", "lt"),
        (3, "mode", "collective"),
        (4, "kind", "deadline"),
        (4, "kind", "target"),
        (4, "kind", "period"),
        (7, "polarity", "affirmed"),
        (8, "state", "observed"),
        (8, "state", "conditional"),
    ],
)
def test_explicit_facet_states_are_preserved_without_lexical_reclassification(index, field, value):
    mod, src = api(), document(TEXT)
    data = packet(src)
    data["propositions"][0]["facets"][index]["value"][field] = value
    result = mod.build_question_evidence_propositions(src, QUESTION, data)
    assert result.model_dump(mode="json")["propositions"] == data["propositions"]
    assert result.status == "unreviewed"


@pytest.mark.parametrize("targets", [[], ["f1", "f2"], ["f1", "f1"], ["f4"], ["f5"], ["f16"]])
def test_distribution_needs_exactly_one_other_local_quantity_target(targets):
    mod, src = api(), document(TEXT)
    data = packet(src)
    data["propositions"][0]["facets"][3]["target_ids"] = targets
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize("path", [("supporting_refs",), ("facets", 0, "refs")])
def test_required_evidence_lists_cannot_be_empty(path):
    mod, src = api(), document(TEXT)
    data = packet(src)
    put(data["propositions"][0], path, [])
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)


@pytest.mark.parametrize("replacement", [2.0, Number(2.0), True, Integer(2), Text("2")])
def test_build_guards_unchecked_actual_input_offsets_before_any_dump(monkeypatch, replacement):
    mod, src = api(), document(TEXT)
    typed = mod.QuestionEvidenceInput.model_validate_json(json.dumps(packet(src)), strict=True)
    changed = typed_replace(typed, ("propositions", 0, "subject_refs", 0, "start"), replacement)
    dumps = []

    def forbidden(*args, **kwargs):
        dumps.append(True)
        raise AssertionError("Unchecked input was serialized")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, changed)
    assert dumps == []


def test_each_facet_ref_and_subject_predicate_must_stay_within_exact_support():
    mod, src = api(), document(TEXT)
    data = packet(src)
    # Support narrows to the subject; all refs remain exact source references,
    # so rejecting cannot be attributed to a missing citation or bad slice.
    data["propositions"][0]["supporting_refs"] = [ref(src, "기관")]
    rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, data)
    for index in range(9):
        narrowed = packet(src)
        p = narrowed["propositions"][0]
        selected = p["facets"][index]
        p.update(
            supporting_refs=[ref(src, "🧪")],
            subject_refs=[],
            predicate_refs=[],
            epistemic_status="uncertain",
            facets=[selected],
        )
        if selected["kind"] in ("bound", "distribution"):
            # Keep a local target so dangling links cannot mask support containment.
            quantity = deepcopy(data["propositions"][0]["facets"][0])
            quantity["refs"] = [ref(src, "🧪")]
            quantity["value"] = dict(expression=ref(src, "🧪"), metric_refs=[])
            selected["target_ids"] = [quantity["id"]]
            p["facets"].insert(0, quantity)
        rejected(mod, mod.build_question_evidence_propositions, src, QUESTION, narrowed)
