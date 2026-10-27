"""Exact unique text references reuse the existing canonical source guards."""

import importlib
from copy import deepcopy

import pytest
from test_numeric_evidence import document
from test_question_evidence_propositions import QUESTION, packet


def api():
    return importlib.import_module("issuedigest_agents.question_text_references")


def text_only(value):
    if isinstance(value, dict):
        return {k: text_only(v) for k, v in value.items() if k not in ("start", "end")}
    if isinstance(value, list):
        return [text_only(v) for v in value]
    return value


def test_all_facets_roundtrip_without_mutation():
    mod = api()
    src = document(
        "🧪 기관은 좌석·수용 인원 각각 3 이내를 계획한다. "
        "승인 후 다음 달 신청 예정이며 법적 지위 부여 아님. e\u0301.\n끝"
    )
    raw = packet(src)
    data = text_only(raw)
    before = deepcopy(data)
    result = mod.build_question_text_evidence(src, QUESTION, data)
    assert result.model_dump(mode="json")["propositions"] == raw["propositions"]
    assert data == before


@pytest.mark.parametrize("text", ["", " ", "없음", "é", "기관", "aa"])
def test_invalid_missing_blank_normalized_and_overlapping_ambiguous(text):
    mod = api()
    src = document("기관 기관 aaa e\u0301")
    data = dict(
        propositions=[
            dict(
                id="p1",
                epistemic_status="uncertain",
                supporting_refs=[dict(citation_id=str(src[1].citations[0].citation_id), text=text)],
                subject_refs=[],
                predicate_refs=[],
                facets=[],
                depends_on_ids=[],
            )
        ],
        coverage=dict(linked_proposition_ids=["p1"], unresolved_reason=None),
    )
    with pytest.raises(mod.QuestionEvidenceError, match="^Invalid question evidence propositions$"):
        mod.build_question_text_evidence(src, QUESTION, data)


def good():
    src = document(
        "🧪 기관은 좌석·수용 인원 각각 3 이내를 계획한다. "
        "승인 후 다음 달 신청 예정이며 법적 지위 부여 아님. e\u0301.\n끝"
    )
    return src, text_only(packet(src))


def reject(src, data):
    mod = api()
    before = deepcopy(data)
    with pytest.raises(mod.QuestionEvidenceError) as caught:
        mod.build_question_text_evidence(src, QUESTION, data)
    assert str(caught.value) == "Invalid question evidence propositions"
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__
    assert data == before


@pytest.mark.parametrize("field", ["start", "end", "occurrence", "extra"])
def test_no_offset_or_other_injection(field):
    src, data = good()
    data["propositions"][0]["supporting_refs"][0][field] = 0
    reject(src, data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("citation_id", "missing"),
        ("citation_id", ""),
        ("text", 1),
        ("text", None),
        ("text", "\ud800"),
    ],
)
def test_reference_scalar_and_unknown_citation(field, value):
    src, data = good()
    data["propositions"][0]["subject_refs"][0][field] = value
    reject(src, data)


@pytest.mark.parametrize(
    "path",
    [
        ("subject_refs",),
        ("predicate_refs",),
        ("facets", 0, "value", "metric_refs"),
        ("facets", 4, "value", "anchor_refs"),
    ],
)
def test_uncertainty_required_and_preserved(path):
    from test_question_evidence_propositions import put

    src, data = good()
    put(data["propositions"][0], path, [])
    reject(src, data)
    data["propositions"][0]["epistemic_status"] = "uncertain"
    assert (
        api().build_question_text_evidence(src, QUESTION, data).propositions[0].epistemic_status
        == "uncertain"
    )


@pytest.mark.parametrize(
    "scenario", ["target", "cycle", "coverage", "containment", "membership", "duplicate"]
)
def test_canonical_relationship_guards(scenario):
    src, data = good()
    p = data["propositions"][0]
    if scenario == "target":
        p["facets"][2]["target_ids"] = ["f4"]
    elif scenario == "cycle":
        p["depends_on_ids"] = ["p1"]
    elif scenario == "coverage":
        data["coverage"]["linked_proposition_ids"] = ["p24"]
    elif scenario == "containment":
        p["supporting_refs"] = p["subject_refs"]
    elif scenario == "membership":
        p["facets"][0]["value"]["expression"] = p["subject_refs"][0]
    else:
        p["subject_refs"] *= 2
    reject(src, data)


@pytest.mark.parametrize("reason", [None, "ambiguous", "insufficient", "no_linked_evidence"])
@pytest.mark.parametrize("linked", [True, False])
def test_coverage(reason, linked):
    src, data = good()
    data["coverage"] = dict(
        linked_proposition_ids=["p1"] if linked else [], unresolved_reason=reason
    )
    if (not linked and reason is None) or (linked and reason == "no_linked_evidence"):
        reject(src, data)
    else:
        assert (
            api().build_question_text_evidence(src, QUESTION, data).coverage.unresolved_reason
            == reason
        )


def test_every_nested_field_is_required_extra_forbidden():
    from test_question_evidence_propositions import at, object_paths

    src, data = good()
    for path in object_paths(data):
        for name in [*at(data, path), "extra"]:
            bad = deepcopy(data)
            target = at(bad, path)
            if name == "extra":
                target[name] = "SECRET"
            else:
                del target[name]
            reject(src, bad)


@pytest.mark.parametrize(
    "kind", ["extra", "missing", "list", "str_subclass", "model_subclass", "construct"]
)
def test_actual_original_tampering(kind):
    import json

    from pydantic import create_model
    from test_question_evidence_propositions import Text, typed_replace

    src, raw = good()
    cls = api().QuestionEvidenceTextInput
    typed = cls.model_validate_json(json.dumps(raw), strict=True)
    if kind == "extra":
        typed = typed.model_copy(update={"extra": "SECRET"})
    elif kind == "missing":
        del typed.__dict__["coverage"]
    elif kind == "list":
        typed = typed.model_copy(update={"propositions": list(typed.propositions)})
    elif kind == "str_subclass":
        typed = typed_replace(typed, ("propositions", 0, "subject_refs", 0, "text"), Text("기관"))
    elif kind == "model_subclass":
        typed = create_model("Impostor", __base__=cls).model_validate_json(json.dumps(raw))
    else:
        typed = cls.model_construct(**raw)
    reject(src, typed)


def test_unicode_newline_long_context_and_source_receipt():
    from issuedigest_agents.question_evidence_propositions import _source

    src = document("다른 인용", "🧪 기관 반복 기관\ne\u0301 " + "긴" * 1100 + "끝")
    quote = src[1].citations[1].selector.quote
    ref = dict(citation_id=str(src[1].citations[1].citation_id), text=quote)
    data = dict(
        propositions=[
            dict(
                id="p1",
                epistemic_status="uncertain",
                supporting_refs=[ref],
                subject_refs=[],
                predicate_refs=[],
                facets=[],
                depends_on_ids=[],
            )
        ],
        coverage=dict(linked_proposition_ids=["p1"], unresolved_reason=None),
    )
    before = _source(src)[0]
    result = api().build_question_text_evidence(src, QUESTION, data)
    assert result.source_sha256 == before == _source(src)[0]
    assert result.propositions[0].supporting_refs[0].end == len(quote)
    data["propositions"][0]["supporting_refs"][0]["text"] = "기관 반복 기관\ne\u0301"
    assert (
        api()
        .build_question_text_evidence(src, QUESTION, data)
        .propositions[0]
        .supporting_refs[0]
        .start
        == 2
    )


@pytest.mark.parametrize("scenario", ["list", "id", "workspace", "hash", "quote"])
def test_invalid_source(scenario):
    from uuid import uuid4

    from test_question_evidence_propositions import typed_replace

    src, data = good()
    if scenario == "list":
        src = list(src)
    elif scenario == "id":
        src = (uuid4(), *src[1:])
    elif scenario == "workspace":
        src = (src[0], src[1], src[2].model_copy(update={"workspace_id": uuid4()}))
    elif scenario == "hash":
        src = typed_replace(src, (1, "representation", "text_sha256"), "0" * 64)
    else:
        src = typed_replace(src, (1, "citations", 0, "selector", "quote"), "changed")
    reject(src, data)


@pytest.mark.parametrize(
    "path,cap",
    [
        (("propositions",), 24),
        (("coverage", "linked_proposition_ids"), 24),
        (("propositions", 0, "facets"), 16),
        (("propositions", 0, "depends_on_ids"), 8),
        (("propositions", 0, "supporting_refs"), 8),
        (("propositions", 0, "facets", 0, "value", "metric_refs"), 8),
        (("propositions", 0, "facets", 0, "refs"), 8),
        (("propositions", 0, "facets", 2, "target_ids"), 1),
    ],
)
def test_schema_exact_array_caps(path, cap):
    import json

    from pydantic import ValidationError
    from test_question_evidence_propositions import at, put

    _, data = good()
    values = at(data, path) or ["p2"]
    for count in (cap, cap + 1):
        changed = deepcopy(data)
        put(changed, path, [deepcopy(values[0])] * count)
        if count == cap:
            api().QuestionEvidenceTextInput.model_validate_json(json.dumps(changed), strict=True)
        else:
            with pytest.raises(ValidationError) as caught:
                api().QuestionEvidenceTextInput.model_validate_json(
                    json.dumps(changed), strict=True
                )
            assert any(
                e["type"] == "too_long" and e["ctx"]["max_length"] == cap
                for e in caught.value.errors()
            )


def test_source_change_after_delegate_fails_whole_operation(monkeypatch):
    mod = api()
    src, data = good()
    original = mod.canonical.build_question_evidence_propositions

    def changed_source(*args):
        result = original(*args)
        object.__setattr__(src[2], "title", src[2].title + " changed")
        return result

    monkeypatch.setattr(mod.canonical, "build_question_evidence_propositions", changed_source)
    reject(src, data)
