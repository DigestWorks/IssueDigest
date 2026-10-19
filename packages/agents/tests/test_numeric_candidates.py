"""Synthetic lexical gold tests; source consistency does not certify meaning."""

import importlib
import importlib.util
import json
from hashlib import sha256
from uuid import uuid4

import pytest
from test_numeric_evidence import document


def sdk():
    name = "issuedigest_agents.numeric_candidates"
    assert importlib.util.find_spec(name) is not None, "Missing numeric candidate foundation"
    return importlib.import_module(name)


def test_fixed_gold_preserves_exact_offsets_atoms_units_and_qualifiers():
    api = sdk()
    src = document("🧪 약 21만 8000~23만 5000호 이상. 지수 -2.5, 1,200.5원과 9만 9000명.")
    index = api.build_numeric_candidates(src)
    assert [(c.candidate_id, c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("n1", "약 21만 8000~23만 5000호 이상", "number"),
        ("n2", "-2.5", "number"),
        ("n3", "1,200.5원", "number"),
        ("n4", "9만 9000명", "number"),
    ]
    c = index.candidates[0]
    assert (c.expression.start, c.expression.end) == (2, 25)
    assert [
        (a.number.text, a.number.start, a.number.end, a.unit.text if a.unit else None)
        for a in c.atoms
    ] == [("21만 8000", 4, 12, None), ("23만 5000", 13, 21, "호")]
    assert (c.separator.text, c.separator.start, c.separator.end) == ("~", 12, 13)
    assert [(q.text, q.start, q.end) for q in c.qualifiers] == [("약", 2, 3), ("이상", 23, 25)]
    assert c.sentence_ids == ("s1",)
    assert index.candidates[1].atoms[0].unit is None
    assert api.validate_numeric_candidates(src, index) == index
    packet = api.numeric_candidates_packet(src, index)
    assert json.loads(packet)["citations"][0]["quote"] == src[1].citations[0].selector.quote
    assert packet == json.dumps(
        json.loads(packet), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


@pytest.mark.parametrize(
    "text,numbers,units,separator,qualifiers,kind",
    [
        ("1~2호", ("1", "2"), (None, "호"), "~", (), "number"),
        ("1호~2호", ("1", "2"), ("호", "호"), "~", (), "number"),
        ("-2~-1", ("-2", "-1"), (None, None), "~", (), "number"),
        ("+2 – −1명", ("+2", "−1"), (None, "명"), "–", (), "number"),
        ("3억 5천만 원", ("3억 5천만",), ("원",), None, (), "number"),
        ("최대\t1,200.5 %p 이하를", ("1,200.5",), ("%p",), None, ("최대", "이하"), "number"),
        ("최소 2kg 초과", ("2",), ("kg",), None, ("최소", "초과"), "number"),
        ("약1m² 미만", ("1",), ("m²",), None, ("약", "미만"), "number"),
        ("2026-99-99", ("2026-99-99",), (None,), None, (), "temporal"),
        ("2026/10/19", ("2026/10/19",), (None,), None, (), "temporal"),
        ("12개월", ("12",), ("개월",), None, (), "temporal"),
        ("12,34", ("12,34",), (None,), None, (), "ambiguous"),
        ("1.2.3", ("1.2.3",), (None,), None, (), "ambiguous"),
        ("3기", ("3",), (None,), None, (), "identifier"),
        ("A12B", ("12",), (None,), None, (), "identifier"),
        ("2구역", ("2",), (None,), None, (), "identifier"),
        ("2명은", ("2",), ("명",), None, (), "number"),
        ("42", ("42",), (None,), None, (), "number"),
    ],
)
def test_finite_grammar(text, numbers, units, separator, qualifiers, kind):
    (c,) = sdk().build_numeric_candidates(document(text)).candidates
    assert tuple(a.number.text for a in c.atoms) == numbers
    assert tuple(a.unit.text if a.unit else None for a in c.atoms) == units
    assert (c.separator.text if c.separator else None) == separator
    assert tuple(q.text for q in c.qualifiers) == qualifiers
    assert c.lexical_kind == kind


@pytest.mark.parametrize(
    "unit",
    [
        "%p",
        "%",
        "bp",
        "p",
        "호",
        "명",
        "원",
        "건",
        "개",
        "배",
        "점",
        "석",
        "곳",
        "km²",
        "km2",
        "㎢",
        "km",
        "m²",
        "m2",
        "㎡",
        "m",
        "kg",
        "g",
        "t",
    ],
)
def test_every_explicit_unit_excludes_following_particle(unit):
    (c,) = sdk().build_numeric_candidates(document(f"2{unit}은")).candidates
    assert c.atoms[0].unit.text == unit
    assert c.expression.text == f"2{unit}"


@pytest.mark.parametrize("unit", ["개월", "년", "월", "일", "시", "분", "초"])
def test_every_temporal_unit_is_preserved(unit):
    (c,) = sdk().build_numeric_candidates(document(f"2{unit}에")).candidates
    assert c.lexical_kind == "temporal"
    assert c.atoms[0].unit.text == unit
    assert c.expression.text == f"2{unit}"


def test_sentence_partition_keeps_every_unicode_codepoint_and_multiple_quotes():
    api = sdk()
    text = " \x00\u0085\ufeffe\u0301🧪 1.5.?!。！？\r\n \n끝"
    src = document(text, "1명 1명")
    index = api.build_numeric_candidates(src)
    assert [s.span.text for s in index.sentences] == [
        " \x00\u0085\ufeffe\u0301🧪 1.5.",
        "?",
        "!",
        "。",
        "！",
        "？",
        "\r\n",
        " \n",
        "끝",
        "1명 1명",
    ]
    assert [s.sentence_id for s in index.sentences] == [f"s{i}" for i in range(1, 11)]
    for citation in index.citations:
        parts = [s.span for s in index.sentences if s.span.citation_id == citation.citation_id]
        assert "".join(p.text for p in parts) == citation.quote
        assert parts[0].start == 0 and parts[-1].end == len(citation.quote)
        assert all(a.end == b.start for a, b in zip(parts, parts[1:], strict=False))
    assert [(c.expression.start, c.expression.end) for c in index.candidates[1:]] == [
        (0, 2),
        (3, 5),
    ]
    assert [c.candidate_id for c in index.candidates] == ["n1", "n2", "n3"]
    assert index.candidates[0].atoms[0].number.start == 8


def test_range_can_cross_punctuation_sentence_boundary_but_not_newline():
    api = sdk()
    index = api.build_numeric_candidates(document("1. ~ 2명\n3~\n4명"))
    # A decimal needs a following digit; terminal '.' is punctuation, outside the first atom.
    assert [c.expression.text for c in index.candidates] == ["1", "2명", "3", "4명"]
    crossing = api.build_numeric_candidates(document("1~2.5명"))
    assert crossing.candidates[0].sentence_ids == ("s1",)
    # The finite malformed-dot run remains one atom even when sentence partition splits it.
    crossing = api.build_numeric_candidates(document("1..2~3명"))
    assert crossing.candidates[0].sentence_ids == ("s1", "s2", "s3")


def test_units_are_never_inferred_or_copied_and_unhandled_forms_are_not_truth():
    index = sdk().build_numeric_candidates(document("지수 1.5; 2명 3; 1e3; 오명; 1/2; 2리터"))
    assert [
        (c.expression.text, tuple(a.unit.text if a.unit else None for a in c.atoms))
        for c in index.candidates
    ] == [
        ("1.5", (None,)),
        ("2명", ("명",)),
        ("3", (None,)),
        ("1", (None,)),
        ("3", (None,)),
        ("1", (None,)),
        ("2", (None,)),
        ("2", (None,)),
    ]
    assert index.status == "unreviewed"
    # False statements, conditions and unrelated subjects still produce lexical candidates.
    false = sdk().build_numeric_candidates(document("거짓: 달에 99명. 조건이 틀리면 4명 계획."))
    assert [c.expression.text for c in false.candidates] == ["99명", "4명"]
    assert sdk().build_numeric_candidates(document("다섯 명")).candidates == ()


def test_packet_preserves_whole_quotes_hash_order_and_metadata_independence():
    api = sdk()
    src = document("원문 1명", "다른 2명")
    index = api.build_numeric_candidates(src)
    payload = {
        "snapshot_id": str(src[0]),
        "workspace_id": str(src[2].workspace_id),
        "citations": [c.model_dump() for c in index.citations],
    }
    assert (
        index.source_sha256
        == sha256(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest()
    )
    assert index.profile == "numeric-candidates-v1"
    assert index.snapshot_id == src[0] and index.workspace_id == src[2].workspace_id
    packet = json.loads(api.numeric_candidates_packet(src, index))
    assert [c["quote"] for c in packet["citations"]] == ["원문 1명", "다른 2명"]
    presentation = src[2].model_copy(update={"title": "999명 metadata"})
    assert api.validate_numeric_candidates((src[0], src[1], presentation), index) == index
    with pytest.raises(ValueError):
        index.status = "reviewed"


@pytest.mark.parametrize("count", [0, 1, 256, 257])
def test_candidate_cap_rejects_whole_index_without_truncating(count):
    api = sdk()
    src = document("숫자 없음" if not count else " ".join(["1"] * count))
    if count > 256:
        with pytest.raises(api.NumericCandidateError):
            api.build_numeric_candidates(src)
    else:
        assert len(api.build_numeric_candidates(src).candidates) == count


def test_noise_counts_toward_cap():
    with pytest.raises(sdk().NumericCandidateError):
        sdk().build_numeric_candidates(document(" ".join(["2026-10-19", "1.2.3", "2기"] * 86)))


@pytest.mark.parametrize(
    "quotes,valid",
    [(["x"] * 20, True), (["x"] * 21, False), (["x" * 12000], True), (["x" * 12001], False)],
)
def test_source_bounds_are_independent_of_candidates(quotes, valid):
    api = sdk()
    src = document(*quotes)
    if valid:
        index = api.build_numeric_candidates(src)
        assert sum(len(c.quote) for c in index.citations) == sum(map(len, quotes))
    else:
        with pytest.raises(api.NumericCandidateError):
            api.build_numeric_candidates(src)


@pytest.mark.parametrize(
    "change", ["snapshot", "workspace", "hash", "source_extra", "outer", "selector", "canonical"]
)
def test_canonical_source_provenance_and_unchecked_fields_are_revalidated(change):
    api = sdk()
    src = document("secret 1명")
    sid, bundle, presentation = src
    if change == "snapshot":
        src = uuid4(), bundle, presentation
    elif change == "workspace":
        src = sid, bundle, presentation.model_copy(update={"workspace_id": uuid4()})
    elif change == "hash":
        src = (
            sid,
            bundle.model_copy(
                update={
                    "representation": bundle.representation.model_copy(
                        update={"text_sha256": "0" * 64}
                    )
                }
            ),
            presentation,
        )
    elif change == "source_extra":
        src = sid, bundle.model_copy(update={"secret": "hidden"}), presentation
    elif change == "outer":
        src = list(src)
    elif change == "selector":
        citation = bundle.citations[0]
        bad = citation.model_copy(
            update={"selector": citation.selector.model_copy(update={"quote": "secret 2명"})}
        )
        src = sid, bundle.model_copy(update={"citations": (bad,)}), presentation
    else:
        src = sid, bundle.model_dump(), presentation
    with pytest.raises(api.NumericCandidateError) as exc:
        api.build_numeric_candidates(src)
    assert "secret" not in str(exc.value) and str(sid) not in str(exc.value)
    assert exc.value.__cause__ is None


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "status",
        "snapshot_id",
        "workspace_id",
        "source_sha256",
        "citations",
        "sentences",
        "candidates",
        "extra",
        "outer",
        "bool",
        "nested_extra",
        "offset",
        "kind",
        "unit",
        "qualifier",
        "separator",
        "sentence_ids",
        "candidate_id",
        "missing",
        "order",
        "duplicate",
        "schema",
    ],
)
def test_index_all_fields_and_unchecked_tampering_are_regenerated(field):
    api = sdk()
    src = document("약 1~2명 이상. 3명")
    index = api.build_numeric_candidates(src)
    candidate = index.candidates[0]
    values = {
        "profile": "other",
        "status": "verified",
        "snapshot_id": uuid4(),
        "workspace_id": uuid4(),
        "source_sha256": "0" * 64,
        "citations": tuple(reversed(index.citations)) + index.citations,
        "sentences": tuple(reversed(index.sentences)),
        "candidates": tuple(reversed(index.candidates)),
        "extra": 1,
    }
    if field in values:
        bad = index.model_copy(update={field: values[field]})
    elif field == "outer":
        bad = index.model_dump()
    elif field == "schema":

        class Forged(api.NumericCandidateIndex):
            pass

        bad = Forged.model_validate(index.model_dump())
    else:
        if field == "bool":
            span = candidate.expression.model_copy(update={"start": False})
            candidate = candidate.model_copy(update={"expression": span})
        elif field == "nested_extra":
            span = candidate.expression.model_copy(update={"hidden": 1})
            candidate = candidate.model_copy(update={"expression": span})
        elif field == "offset":
            # Coherent current-source replacement is still not this deterministic candidate.
            span = candidate.expression.model_copy(update={"start": 12, "end": 14, "text": "3명"})
            candidate = candidate.model_copy(update={"expression": span})
        elif field == "kind":
            candidate = candidate.model_copy(update={"lexical_kind": "identifier"})
        elif field == "unit":
            atom = candidate.atoms[0].model_copy(update={"unit": candidate.atoms[1].unit})
            candidate = candidate.model_copy(update={"atoms": (atom, candidate.atoms[1])})
        elif field == "qualifier":
            candidate = candidate.model_copy(update={"qualifiers": ()})
        elif field == "separator":
            candidate = candidate.model_copy(update={"separator": None})
        elif field == "sentence_ids":
            candidate = candidate.model_copy(update={"sentence_ids": ("s2",)})
        elif field == "candidate_id":
            candidate = candidate.model_copy(update={"candidate_id": "n9"})
        replacements = (candidate,) + index.candidates[1:]
        if field == "missing":
            replacements = index.candidates[1:]
        elif field == "order":
            replacements = tuple(reversed(index.candidates))
        elif field == "duplicate":
            replacements = index.candidates + (candidate,)
        bad = index.model_copy(update={"candidates": replacements})
    for call in (api.validate_numeric_candidates, api.numeric_candidates_packet):
        with pytest.raises(api.NumericCandidateError):
            call(src, bad)


def test_stale_source_quote_or_order_is_rejected():
    api = sdk()
    src = document("1명", "2명")
    index = api.build_numeric_candidates(src)
    for changed in (
        document("1명", "3명"),
        (
            src[0],
            src[1].model_copy(update={"citations": tuple(reversed(src[1].citations))}),
            src[2],
        ),
    ):
        with pytest.raises(api.NumericCandidateError):
            api.validate_numeric_candidates(changed, index)


def test_span_models_reject_reverse_empty_non_ascii_atom_and_overlapping_children():
    api = sdk()
    base = {"citation_id": "c", "text": "1", "start": 0, "end": 1}
    for update in ({"end": 0}, {"start": 2}, {"text": ""}, {"start": True}, {"extra": 1}):
        with pytest.raises(ValueError):
            api.ExactSpan(**{**base, **update})
    with pytest.raises(ValueError):
        api.NumericAtom(number=api.ExactSpan(**{**base, "text": "삼"}), unit=None)
    index = api.build_numeric_candidates(document("1~2명"))
    candidate = index.candidates[0]
    with pytest.raises(ValueError):
        api.NumericCandidate.model_validate(
            {**candidate.model_dump(), "atoms": (candidate.atoms[0], candidate.atoms[0])}
        )


def test_import_and_all_apis_have_no_external_side_effects(monkeypatch):
    # Keep imports real; prohibit key lookup, client creation, I/O and outbound calls.
    import builtins
    import io
    import os
    import socket

    import pydantic_ai
    import pydantic_ai.models.openai

    src = document("1명")

    def denied(*args, **kwargs):
        raise AssertionError("External side effect")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", denied)
        patch.setattr(io, "open", denied)
        getenv = os.getenv

        def guarded_getenv(key, *args):
            if key != "PYDANTIC_DISABLE_PLUGINS":
                return denied(key)
            return getenv(key, *args)

        patch.setattr(os, "getenv", guarded_getenv)
        patch.setattr(socket, "socket", denied)
        patch.setattr(pydantic_ai, "Agent", denied)
        patch.setattr(pydantic_ai.models.openai, "AsyncOpenAI", denied)
        api = importlib.reload(sdk())
        index = api.build_numeric_candidates(src)
        assert api.validate_numeric_candidates(src, index) == index
        assert (
            json.loads(api.numeric_candidates_packet(src, index))["candidates"][0]["expression"][
                "text"
            ]
            == "1명"
        )
        for call in (api.build_numeric_candidates,):
            with pytest.raises(api.NumericCandidateError):
                call(None)


@pytest.mark.parametrize("text,number", [("제12조", "12"), ("제3항", "3"), ("제2호", "2")])
def test_legal_identifiers_precede_multipliers_and_units(text, number):
    (c,) = sdk().build_numeric_candidates(document(text)).candidates
    assert c.expression.text == text
    assert c.atoms[0].number.text == number
    assert c.atoms[0].unit is None
    assert c.lexical_kind == "identifier"


@pytest.mark.parametrize("ending", ["으로", "로", "이다"])
def test_decimal_grammatical_endings_are_not_names_or_units(ending):
    (c,) = sdk().build_numeric_candidates(document(f"106.6{ending}")).candidates
    assert c.expression.text == "106.6"
    assert c.lexical_kind == "number"
    assert c.atoms[0].unit is None


@pytest.mark.parametrize("separator", ["~", "∼", "～", "–", "—", "-"])
def test_range_separators_preserve_units_and_do_not_copy(separator):
    (c,) = sdk().build_numeric_candidates(document(f"1명 {separator}\t2호")).candidates
    assert c.separator.text == separator
    assert tuple(a.unit.text for a in c.atoms) == ("명", "호")


def test_dates_have_priority_over_range_end_and_lf_prevents_range_join():
    index = sdk().build_numeric_candidates(document("1~2026-10-19; 1호~\n2호"))
    assert [(c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("1", "number"),
        ("2026-10-19", "temporal"),
        ("1호", "number"),
        ("2호", "number"),
    ]


@pytest.mark.parametrize(
    "bad_type",
    [
        "list_candidates",
        "list_sentences",
        "span_float",
        "span_string",
        "span_extra",
        "citation_extra",
        "sentence_extra",
        "atom_extra",
        "hidden_extra",
    ],
)
def test_recursive_strictness_and_hidden_extras_are_not_lost_on_dump(bad_type):
    api = sdk()
    src = document("1명")
    index = api.build_numeric_candidates(src)
    candidate = index.candidates[0]
    if bad_type == "list_candidates":
        bad = index.model_copy(update={"candidates": list(index.candidates)})
    elif bad_type == "list_sentences":
        bad = index.model_copy(update={"sentences": list(index.sentences)})
    elif bad_type == "citation_extra":
        bad = index.model_copy(
            update={"citations": (index.citations[0].model_copy(update={"hidden": 1}),)}
        )
    elif bad_type == "sentence_extra":
        bad = index.model_copy(
            update={"sentences": (index.sentences[0].model_copy(update={"hidden": 1}),)}
        )
    elif bad_type == "hidden_extra":
        bad = index.model_copy()
        object.__setattr__(bad, "__pydantic_extra__", {"hidden": 1})
    else:
        if bad_type == "atom_extra":
            atom = candidate.atoms[0].model_copy(update={"hidden": 1})
        else:
            update = (
                {"start": 0.0}
                if bad_type == "span_float"
                else {"start": "0"}
                if bad_type == "span_string"
                else {"hidden": 1}
            )
            number = candidate.atoms[0].number.model_copy(update=update)
            atom = candidate.atoms[0].model_copy(update={"number": number})
        bad = index.model_copy(
            update={"candidates": (candidate.model_copy(update={"atoms": (atom,)}),)}
        )
    with pytest.raises(api.NumericCandidateError):
        api.validate_numeric_candidates(src, bad)


def test_qualifiers_are_adjacent_spans_even_for_temporal_and_identifier_hints():
    index = sdk().build_numeric_candidates(document("약 2026/10/19 이후; 최대 제12조 이하"))
    assert [(c.expression.text, tuple(q.text for q in c.qualifiers)) for c in index.candidates] == [
        ("약 2026/10/19", ("약",)),
        ("최대 제12조 이하", ("최대", "이하")),
    ]


@pytest.mark.parametrize("prefix", ["약", "최대", "최소"])
def test_adjacent_prefix_does_not_turn_a_bare_number_into_identifier(prefix):
    (c,) = sdk().build_numeric_candidates(document(f"{prefix}106.6")).candidates
    assert c.lexical_kind == "number"
    assert c.expression.text == f"{prefix}106.6"
    assert tuple(q.text for q in c.qualifiers) == (prefix,)


@pytest.mark.parametrize(
    "text,left,right,separator,left_bounds,right_bounds,separator_bounds",
    [
        ("1만-2만", "1만", "2만", "-", (0, 2), (3, 5), (2, 3)),
        ("1만 -2만", "1만", "2만", "-", (0, 2), (4, 6), (3, 4)),
        ("-1만--2만", "-1만", "-2만", "-", (0, 3), (4, 7), (3, 4)),
        ("−1만 - −2만", "−1만", "−2만", "-", (0, 3), (6, 9), (4, 5)),
        ("1만~-2만", "1만", "-2만", "~", (0, 2), (3, 6), (2, 3)),
    ],
)
def test_multiplier_continuation_leaves_range_delimiter_and_signed_endpoints(
    text, left, right, separator, left_bounds, right_bounds, separator_bounds
):
    (candidate,) = sdk().build_numeric_candidates(document(text)).candidates
    assert candidate.expression.text == text
    assert candidate.lexical_kind == "number"
    assert len(candidate.atoms) == 2
    assert [(a.number.text, a.number.start, a.number.end) for a in candidate.atoms] == [
        (left, *left_bounds),
        (right, *right_bounds),
    ]
    assert tuple(a.unit for a in candidate.atoms) == (None, None)
    assert (candidate.separator.text, candidate.separator.start, candidate.separator.end) == (
        separator,
        *separator_bounds,
    )


def test_unsigned_multiplier_continuation_still_preserves_a_compound_quantity():
    (candidate,) = sdk().build_numeric_candidates(document("1만 2천명")).candidates
    assert candidate.expression.text == "1만 2천명"
    assert len(candidate.atoms) == 1 and candidate.separator is None
    atom = candidate.atoms[0]
    assert (atom.number.text, atom.number.start, atom.number.end) == ("1만 2천", 0, 5)
    assert (atom.unit.text, atom.unit.start, atom.unit.end) == ("명", 5, 6)


@pytest.mark.parametrize("date", ["2026/10/19", "2026-10-19"])
def test_multiplier_continuation_stops_before_a_prioritized_whole_date(date):
    index = sdk().build_numeric_candidates(document(f"1만 {date}"))
    assert [(c.candidate_id, c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("n1", "1만", "number"),
        ("n2", date, "temporal"),
    ]
    quantity, temporal = index.candidates
    assert (quantity.atoms[0].number.start, quantity.atoms[0].number.end) == (0, 2)
    assert len(temporal.atoms) == 1
    atom = temporal.atoms[0]
    assert (atom.number.text, atom.number.start, atom.number.end) == (date, 3, 13)
    assert atom.unit is None
    assert quantity.separator is None and temporal.separator is None
    assert temporal.sentence_ids == ("s1",)


@pytest.mark.parametrize("qualifier", ["이상", "이하", "초과", "미만"])
@pytest.mark.parametrize("gap", ["", " "])
@pytest.mark.parametrize(
    "prefix,number_bounds,separator_bounds", [("", (0, 1), None), ("0~", (2, 3), (1, 2))]
)
def test_complete_suffix_qualifier_precedes_unit_prefix_and_name_hint(
    qualifier, gap, prefix, number_bounds, separator_bounds
):
    text = f"{prefix}1{gap}{qualifier}은"
    (candidate,) = sdk().build_numeric_candidates(document(text)).candidates
    assert candidate.lexical_kind == "number"
    assert candidate.expression.text == text[:-1]
    assert (candidate.expression.start, candidate.expression.end) == (0, len(text) - 1)
    atom = candidate.atoms[-1]
    assert (atom.number.text, atom.number.start, atom.number.end) == ("1", *number_bounds)
    assert atom.unit is None
    (span,) = candidate.qualifiers
    assert (span.text, span.start, span.end) == (
        qualifier,
        number_bounds[1] + len(gap),
        len(text) - 1,
    )
    if separator_bounds is None:
        assert candidate.separator is None and len(candidate.atoms) == 1
    else:
        assert len(candidate.atoms) == 2
        assert (candidate.separator.text, candidate.separator.start, candidate.separator.end) == (
            "~",
            *separator_bounds,
        )


@pytest.mark.parametrize(
    "text,number,unit,qualifier,kind",
    [
        ("1초", "1", "초", None, "temporal"),
        ("1 초", "1", "초", None, "temporal"),
        ("1초 초과", "1", "초", "초과", "temporal"),
        ("1명 초과", "1", "명", "초과", "number"),
        ("1명미만", "1", "명", "미만", "number"),
    ],
)
def test_suffix_precedence_keeps_real_units_and_their_qualifiers(
    text, number, unit, qualifier, kind
):
    (candidate,) = sdk().build_numeric_candidates(document(text)).candidates
    assert candidate.expression.text == text
    assert candidate.lexical_kind == kind
    assert candidate.atoms[0].number.text == number
    assert candidate.atoms[0].unit.text == unit
    assert tuple(q.text for q in candidate.qualifiers) == (
        () if qualifier is None else (qualifier,)
    )


@pytest.mark.parametrize("date", ["2026-10-19", "2026/10/19"])
@pytest.mark.parametrize(
    "left,gap,date_start", [("1", "", 2), ("1", " ", 3), ("1만", "", 3), ("1만", " ", 4)]
)
def test_rejected_hyphen_date_endpoint_resumes_at_whole_date(left, gap, date_start, date):
    api = sdk()
    text = f"{left}{gap}-{date}"
    src = document(text)
    index = api.build_numeric_candidates(src)
    assert [(c.candidate_id, c.expression.text, c.lexical_kind) for c in index.candidates] == [
        ("n1", left, "number"),
        ("n2", date, "temporal"),
    ]
    quantity, temporal = index.candidates
    assert len(quantity.atoms) == len(temporal.atoms) == 1
    assert quantity.separator is None and temporal.separator is None
    assert quantity.atoms[0].unit is None and temporal.atoms[0].unit is None
    number = temporal.atoms[0].number
    assert (number.text, number.start, number.end) == (date, date_start, date_start + 10)
    assert temporal.expression == number
    assert quantity.sentence_ids == temporal.sentence_ids == ("s1",)
    assert len(index.sentences) == 1
    sentence = index.sentences[0].span
    assert (sentence.text, sentence.start, sentence.end) == (text, 0, len(text))
    assert api.validate_numeric_candidates(src, index) == index
    packet = json.loads(api.numeric_candidates_packet(src, index))
    assert packet["citations"][0]["quote"] == text
    assert packet["sentences"][0]["span"]["text"] == text
    assert [c["expression"]["text"] for c in packet["candidates"]] == [left, date]


@pytest.mark.parametrize(
    "text,left,date,date_start",
    [
        ("1~2026-10-19", "1", "2026-10-19", 2),
        ("1~2026/10/19", "1", "2026/10/19", 2),
        ("1만 - 2026/10/19", "1만", "2026/10/19", 5),
        ("1만 - 2026-10-19", "1만", "2026-10-19", 5),
    ],
)
def test_declined_date_range_controls_keep_delimiter_in_partition(text, left, date, date_start):
    index = sdk().build_numeric_candidates(document(text))
    assert [c.expression.text for c in index.candidates] == [left, date]
    assert index.candidates[1].lexical_kind == "temporal"
    assert (index.candidates[1].expression.start, index.candidates[1].expression.end) == (
        date_start,
        date_start + 10,
    )
    assert index.sentences[0].span.text == text


@pytest.mark.parametrize(
    "text,left,right,separator",
    [
        ("1-2", "1", "2", "-"),
        ("1만-2만", "1만", "2만", "-"),
        ("1--2", "1", "-2", "-"),
        ("-2~-1", "-2", "-1", "~"),
    ],
)
def test_date_resume_fix_preserves_normal_ranges_and_negative_endpoints(
    text, left, right, separator
):
    (candidate,) = sdk().build_numeric_candidates(document(text)).candidates
    assert candidate.expression.text == text
    assert candidate.lexical_kind == "number"
    assert tuple(a.number.text for a in candidate.atoms) == (left, right)
    assert candidate.separator.text == separator


@pytest.mark.parametrize(
    "text,expressions,date_start",
    [
        ("-2026-10-19", ("2026-10-19",), 1),
        ("-2026/10/19", ("2026/10/19",), 1),
        ("+2026-10-19", ("2026-10-19",), 1),
        ("−2026/10/19", ("2026/10/19",), 1),
        ("1초과-2026/10/19", ("1초과", "2026/10/19"), 4),
        ("1초과 -2026-10-19", ("1초과", "2026-10-19"), 5),
        ("1명미만-2026/10/19", ("1명미만", "2026/10/19"), 5),
        ("1--2026-10-19", ("1", "2026-10-19"), 3),
        ("1~-2026/10/19", ("1", "2026/10/19"), 3),
        ("1만~-2026-10-19", ("1만", "2026-10-19"), 4),
    ],
)
def test_whole_date_priority_survives_signs_at_every_atom_entry(text, expressions, date_start):
    api = sdk()
    src = document(text)
    index = api.build_numeric_candidates(src)
    assert tuple(c.expression.text for c in index.candidates) == expressions
    assert tuple(c.candidate_id for c in index.candidates) == tuple(
        f"n{i}" for i in range(1, len(expressions) + 1)
    )
    date = index.candidates[-1]
    assert date.lexical_kind == "temporal"
    assert len(date.atoms) == 1 and date.separator is None
    assert date.atoms[0].unit is None
    assert (date.atoms[0].number.text, date.atoms[0].number.start, date.atoms[0].number.end) == (
        expressions[-1],
        date_start,
        date_start + 10,
    )
    assert date.expression == date.atoms[0].number
    assert date.sentence_ids == ("s1",)
    assert (
        index.sentences[0].span.text,
        index.sentences[0].span.start,
        index.sentences[0].span.end,
    ) == (text, 0, len(text))
    assert api.validate_numeric_candidates(src, index) == index
    packet = json.loads(api.numeric_candidates_packet(src, index))
    assert packet["citations"][0]["quote"] == text
    assert tuple(c["expression"]["text"] for c in packet["candidates"]) == expressions


@pytest.mark.parametrize(
    "text,number", [("-2026", "-2026"), ("+2026", "+2026"), ("−2026", "−2026")]
)
def test_date_priority_does_not_remove_a_real_numeric_leading_sign(text, number):
    (candidate,) = sdk().build_numeric_candidates(document(text)).candidates
    assert candidate.lexical_kind == "number"
    assert candidate.atoms[0].number.text == number
    assert candidate.expression.text == text
