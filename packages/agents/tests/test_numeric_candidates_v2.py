"""Synthetic v2 lexical boundaries and complete, strict source reconstruction."""

import builtins
import importlib
import importlib.util
import json
import socket
import sys
from uuid import uuid4

import pytest
from issuedigest_agents import numeric_candidates as v1
from pydantic import Field, ValidationError
from test_numeric_evidence import document


@pytest.fixture(scope="module", autouse=True)
def restore_new_module_imports():
    # Frozen selection tests reload their models. Leave their dependent modules
    # unloaded if this module introduced them, so later tests bind the current classes.
    existing = set(sys.modules)
    yield
    for name in set(sys.modules) - existing:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)


def sdk():
    name = "issuedigest_agents.numeric_candidates_v2"
    assert importlib.util.find_spec(name) is not None, "Missing pure numeric candidates v2"
    return importlib.import_module(name)


def test_unicode_exact_spans_and_separate_medial_qualifier():
    api = sdk()
    src = document("🧪 e\u0301 약\t37여 명 내외.\n학교 83개교는 참여.")
    index = api.build_numeric_candidates_v2(src)
    assert (index.profile, index.status) == ("numeric-candidates-v2", "unreviewed")
    assert [(c.candidate_id, c.expression.text, c.sentence_ids) for c in index.candidates] == [
        ("n1", "약\t37여 명 내외", ("s1",)),
        ("n2", "83개교", ("s3",)),
    ]
    c = index.candidates[0]
    assert (c.expression.start, c.expression.end) == (5, 15)
    assert (c.atoms[0].number.text, c.atoms[0].number.start, c.atoms[0].number.end) == ("37", 7, 9)
    assert (c.atoms[0].unit.text, c.atoms[0].unit.start, c.atoms[0].unit.end) == ("명", 11, 12)
    assert [(q.text, q.start, q.end) for q in c.qualifiers] == [
        ("약", 5, 6),
        ("여", 9, 10),
        ("내외", 13, 15),
    ]
    assert c.lexical_kind == "number"
    assert api.validate_numeric_candidates_v2(src, index) == index
    packet = api.numeric_candidates_packet_v2(src, index)
    raw = json.loads(packet)
    assert raw["citations"][0]["quote"] == src[1].citations[0].selector.quote
    assert packet == json.dumps(raw, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


@pytest.mark.parametrize(
    "text,numbers,units,qualifiers",
    [
        ("83개교", ("83",), ("개교",), ()),
        ("83 개교에서", ("83",), ("개교",), ()),
        ("83개교 내외를", ("83",), ("개교",), ("내외",)),
        ("37여명", ("37",), ("명",), ("여",)),
        ("37여 명", ("37",), ("명",), ("여",)),
        ("최대 37여명~59여 명 내외", ("37", "59"), ("명", "명"), ("최대", "여", "여", "내외")),
        ("최소 37여명~59명 이하", ("37", "59"), ("명", "명"), ("최소", "여", "이하")),
        ("83~97개교 내외", ("83", "97"), (None, "개교"), ("내외",)),
        ("37여명~59", ("37", "59"), ("명", None), ("여",)),
        ("37~59여명", ("37", "59"), (None, "명"), ("여",)),
        ("-37여명~-19여명", ("-37", "-19"), ("명", "명"), ("여", "여")),
        ("2만 7000여명 내외", ("2만 7000",), ("명",), ("여", "내외")),
        ("37내외", ("37",), (None,), ("내외",)),
    ],
)
def test_extension_grammar_preserves_each_endpoint_without_propagating_units(
    text, numbers, units, qualifiers
):
    (c,) = sdk().build_numeric_candidates_v2(document(text)).candidates
    assert tuple(a.number.text for a in c.atoms) == numbers
    assert tuple(a.unit.text if a.unit else None for a in c.atoms) == units
    assert tuple(q.text for q in c.qualifiers) == qualifiers
    assert c.lexical_kind == "number"


@pytest.mark.parametrize("text", ["A83개교", "기관83개교", "83개교회", "37여명부", "A37여명"])
def test_attached_names_are_not_extended_quantity_hints(text):
    (c,) = sdk().build_numeric_candidates_v2(document(text)).candidates
    assert c.lexical_kind == "identifier"
    assert all(a.unit is None or a.unit.text != "개교" for a in c.atoms)
    assert not c.qualifiers


def test_unsupported_approximation_and_word_suffix_remain_conservative():
    src = document("37여개, 59명 내외부, 83개교회")
    index = sdk().build_numeric_candidates_v2(src)
    assert [(c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("37", "identifier"),
        ("59명", "number"),
        ("83개", "identifier"),
    ]
    assert all(not c.qualifiers for c in index.candidates)


@pytest.mark.parametrize(
    "text,unit,qualifiers",
    [
        ("83개교내외", "개교", ("내외",)),
        ("37여명이상", "명", ("여", "이상")),
        ("37여명내외", "명", ("여", "내외")),
    ],
)
def test_complete_attached_suffix_licenses_new_unit_boundary(text, unit, qualifiers):
    (c,) = sdk().build_numeric_candidates_v2(document(text)).candidates
    assert c.expression.text == text
    assert c.atoms[0].unit.text == unit
    assert tuple(q.text for q in c.qualifiers) == qualifiers


@pytest.mark.parametrize(
    "text,numbers,units,qualifiers",
    [
        ("14개월 내외", ("14",), ("개월",), ("내외",)),
        ("약 14개월~26개월 내외", ("14", "26"), ("개월", "개월"), ("약", "내외")),
        ("31초내외", ("31",), ("초",), ("내외",)),
    ],
)
def test_duration_approximation_preserves_temporal_hint_and_endpoint_units(
    text, numbers, units, qualifiers
):
    (c,) = sdk().build_numeric_candidates_v2(document(text)).candidates
    assert c.expression.text == text
    assert c.lexical_kind == "temporal"
    assert tuple(a.number.text for a in c.atoms) == numbers
    assert tuple(a.unit.text if a.unit else None for a in c.atoms) == units
    assert tuple(q.text for q in c.qualifiers) == qualifiers


@pytest.mark.parametrize("text", ["A37명내외", "기관37명 내외", "A14개월 내외"])
def test_new_approximation_does_not_extend_legacy_attached_identifier(text):
    src = document(text)
    old = v1.build_numeric_candidates(src)
    index = sdk().build_numeric_candidates_v2(src)
    assert index.candidates[0].model_dump() == old.candidates[0].model_dump()
    assert not index.candidates[0].qualifiers


def test_bounded_quantity_extends_but_calendar_and_legal_tokens_do_not():
    index = sdk().build_numeric_candidates_v2(document("37명내외, 2031-04-17 내외, 제87조 내외"))
    assert [
        (c.expression.text, c.lexical_kind, tuple(q.text for q in c.qualifiers))
        for c in index.candidates
    ] == [
        ("37명내외", "number", ("내외",)),
        ("2031-04-17", "temporal", ()),
        ("제87조", "identifier", ()),
    ]


def test_old_grammar_dates_legal_and_packet_are_unchanged():
    api = sdk()
    src = document("약 61만-79만 원 이상. -2031/04/17 제87조 A53B 4.2.6")
    before = v1.build_numeric_candidates(src)
    packet = v1.numeric_candidates_packet(src, before)
    index = api.build_numeric_candidates_v2(src)
    raw = index.model_dump()
    raw["profile"] = "numeric-candidates-v1"
    assert raw == before.model_dump()
    assert [(c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("약 61만-79만 원 이상", "number"),
        ("2031/04/17", "temporal"),
        ("제87조", "identifier"),
        ("53", "identifier"),
        ("4.2.6", "ambiguous"),
    ]
    assert v1.numeric_candidates_packet(src, before) == packet
    with pytest.raises(v1.NumericCandidateError):
        v1.validate_numeric_candidates(src, index)
    with pytest.raises(api.NumericCandidateError):
        api.validate_numeric_candidates_v2(src, before)


def test_range_endpoint_does_not_consume_signed_whole_date_or_legal_identifier():
    index = sdk().build_numeric_candidates_v2(document("37여명~-2031-04-17 83개교~제87조"))
    assert [(c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("37여명", "number"),
        ("2031-04-17", "temporal"),
        ("83개교", "number"),
        ("제87조", "identifier"),
    ]
    assert all(c.separator is None for c in index.candidates)


@pytest.mark.parametrize("mutation", ["omit", "extra", "version", "span", "qualifier", "order"])
def test_reconstruction_rejects_missing_added_or_forged_fields(mutation):
    api = sdk()
    src = document("약37여명~59여명 내외")
    index = api.build_numeric_candidates_v2(src)
    c = index.candidates[0]
    if mutation == "omit":
        forged = index.model_copy(update={"candidates": ()})
    elif mutation == "extra":
        forged = index.model_copy(update={"candidates": (c, c)})
    elif mutation == "version":
        forged = index.model_copy(update={"profile": "numeric-candidates-v1"})
    else:
        if mutation == "span":
            c = c.model_copy(
                update={"expression": c.expression.model_copy(update={"text": "SECRET"})}
            )
        elif mutation == "qualifier":
            c = c.model_copy(update={"qualifiers": c.qualifiers[1:]})
        else:
            c = c.model_copy(update={"qualifiers": tuple(reversed(c.qualifiers))})
        forged = index.model_copy(update={"candidates": (c,)})
    with pytest.raises(api.NumericCandidateError, match="^Invalid numeric candidate index$") as exc:
        api.numeric_candidates_packet_v2(src, forged)
    assert exc.value.__suppress_context__
    assert exc.value.__cause__ is None
    assert "SECRET" not in str(exc.value)


def test_source_provenance_and_quote_drift_are_rejected():
    api = sdk()
    src = document("83개교 내외")
    index = api.build_numeric_candidates_v2(src)
    for drifted in [document("97개교 내외"), (uuid4(), src[1], src[2])]:
        with pytest.raises(api.NumericCandidateError):
            api.validate_numeric_candidates_v2(drifted, index)


@pytest.mark.parametrize(
    "mutation", ["root", "model_dict", "list", "atom_dict", "subclass", "extra"]
)
def test_actual_types_are_checked_before_lossy_serialization(mutation):
    api = sdk()
    src = document("37여명")
    index = api.build_numeric_candidates_v2(src)
    c = index.candidates[0]
    if mutation == "root":
        forged = index.model_dump()
    elif mutation == "model_dict":
        forged = index.model_copy(update={"candidates": (c.model_dump(),)})
    elif mutation == "list":
        forged = index.model_copy(update={"candidates": [c]})
    else:
        if mutation == "atom_dict":
            c = c.model_copy(update={"atoms": (c.atoms[0].model_dump(),)})
        elif mutation == "subclass":

            class HiddenSpan(v1.ExactSpan):
                secret: str = Field(default="hidden", exclude=True)

            c = c.model_copy(update={"expression": HiddenSpan(**c.expression.model_dump())})
        else:
            c = c.model_copy(update={"unexpected": "hidden"})
        forged = index.model_copy(update={"candidates": (c,)})
    with pytest.raises(api.NumericCandidateError):
        api.numeric_candidates_packet_v2(src, forged)


def test_unchecked_source_nested_container_and_subclass_are_rejected():
    api = sdk()
    src = document("83개교")

    class HiddenSelector(type(src[1].citations[0].selector)):
        secret: str = Field(default="hidden", exclude=True)

    citation = src[1].citations[0]
    bad_citation = citation.model_copy(
        update={"selector": HiddenSelector(**citation.selector.model_dump())}
    )
    for bundle in [
        src[1].model_copy(update={"citations": list(src[1].citations)}),
        src[1].model_copy(update={"citations": (bad_citation,)}),
        src[1].model_copy(update={"document": src[1].document.model_dump()}),
    ]:
        with pytest.raises(api.NumericCandidateError):
            api.build_numeric_candidates_v2((src[0], bundle, src[2]))


def test_caps_are_reached_independently_of_provenance_and_span_failures():
    api = sdk()
    assert len(api.build_numeric_candidates_v2(document(*["83개교"] * 20)).citations) == 20
    with pytest.raises(api.NumericCandidateError):
        api.build_numeric_candidates_v2(document(*["83개교"] * 21))
    assert len(api.build_numeric_candidates_v2(document("37 " * 256)).candidates) == 256
    with pytest.raises(api.NumericCandidateError):
        api.build_numeric_candidates_v2(document("37 " * 257))


def test_qualifier_cap_independently_rejects_five_disjoint_valid_position_spans():
    api = sdk()
    src = document("약 최대 37여명~59여명 내외")
    index = api.build_numeric_candidates_v2(src)
    c = index.candidates[0]
    expression = v1._span(c.expression.citation_id, src[1].citations[0].selector.quote, 0, 17)
    extra_prefix = v1.ExactSpan(citation_id=expression.citation_id, text="약", start=0, end=1)
    # Removing only the cap would accept these otherwise disjoint, ordered, outside/medial spans.
    with pytest.raises(ValidationError) as exc:
        api.NumericCandidateV2(
            **{
                **c.model_dump(),
                "expression": expression,
                "qualifiers": (extra_prefix, *c.qualifiers),
            }
        )
    assert exc.value.errors()[0]["type"] == "too_long"
    assert exc.value.errors()[0]["loc"] == ("qualifiers",)


def test_medial_qualifier_requires_exact_yeo_and_people_unit():
    api = sdk()
    c = api.build_numeric_candidates_v2(document("37여명")).candidates[0]
    for update in [
        {"qualifiers": (c.qualifiers[0].model_copy(update={"text": "쯤"}),)},
        {
            "atoms": (
                c.atoms[0].model_copy(
                    update={"unit": c.atoms[0].unit.model_copy(update={"text": "개"})}
                ),
            )
        },
        {"qualifiers": (c.atoms[0].number,)},
    ]:
        with pytest.raises(ValidationError):
            api.NumericCandidateV2(**{**c.model_dump(), **update})


def test_pure_build_validate_and_packet_use_no_file_or_socket_io(monkeypatch):
    api = sdk()
    src = document("83개교 내외와 37여명")

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected I/O")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", forbidden)
        patch.setattr(socket, "socket", forbidden)
        index = api.build_numeric_candidates_v2(src)
        assert api.validate_numeric_candidates_v2(src, index) == index
        assert json.loads(api.numeric_candidates_packet_v2(src, index))["profile"] == (
            "numeric-candidates-v2"
        )
