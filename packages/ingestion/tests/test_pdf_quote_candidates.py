from dataclasses import FrozenInstanceError
from hashlib import sha256
from uuid import UUID

import issuedigest_ingestion as ingestion
import pytest
from issuedigest_domain.citations import Citation, validate_citation
from issuedigest_domain.sources import PageSpan, ParsedRepresentation
from issuedigest_ingestion import AuditError
from pydantic import ValidationError

VERSION = UUID("11111111-1111-4111-8111-111111111111")
REPRESENTATION = UUID("22222222-2222-4222-8222-222222222222")


def api(name: str):
    value = getattr(ingestion, name, None)
    assert callable(value), f"{name} must expose bounded exact quote search"
    return value


def representation(text: str, spans: tuple[tuple[int, int, int], ...]):
    return ParsedRepresentation(
        representation_id=REPRESENTATION,
        document_version_id=VERSION,
        parser_name="synthetic",
        parser_version="1",
        normalization_profile="unchanged",
        text=text,
        text_sha256=sha256(text.encode()).hexdigest(),
        pages=tuple(PageSpan(page_number=n, start=s, end=e) for n, s, e in spans),
        tables=(),
    )


def test_candidates_preserve_overlap_offsets_identity_and_real_citation_contract():
    rep = representation("aaa|aaa", ((2, 0, 3), (5, 4, 7)))
    result = api("find_pdf_quote_candidates")(rep, "aa")
    assert isinstance(result, api("PdfQuoteSearchResult"))
    assert (result.representation_id, result.document_version_id, result.text_sha256) == (
        REPRESENTATION,
        VERSION,
        rep.text_sha256,
    )
    assert (result.occurrence_count, result.candidate_count, result.cross_page_match_count) == (
        4,
        4,
        0,
    )
    assert result.has_more is False
    assert isinstance(result.candidates, tuple)
    assert [(s.start, s.end, s.page_number, s.prefix, s.suffix) for s in result.candidates] == [
        (0, 2, 2, None, "a"),
        (1, 3, 2, "a", None),
        (4, 6, 5, None, "a"),
        (5, 7, 5, "a", None),
    ]
    for selector in result.candidates:
        assert (selector.quote, selector.regions) == ("aa", ())
        citation = Citation(
            citation_id=UUID("33333333-3333-4333-8333-333333333333"),
            document_version_id=result.document_version_id,
            representation_id=result.representation_id,
            selector=selector,
        )
        validated = validate_citation(citation, rep)
        assert (validated.anchor_status, validated.support_status) == ("matched", "not_evaluated")
    with pytest.raises(FrozenInstanceError):
        result.candidate_count = 0
    with pytest.raises(ValidationError):
        result.candidates[0].start = 5


def test_truncation_counts_every_occurrence_including_unanchorable_matches():
    rep = representation("abxabxab", ((1, 0, 2), (4, 3, 5)))
    result = api("find_pdf_quote_candidates")(
        rep, "ab", limits=api("PdfQuoteSearchLimits")(max_candidates=1)
    )
    assert (result.occurrence_count, result.candidate_count, result.cross_page_match_count) == (
        3,
        2,
        1,
    )
    assert [s.start for s in result.candidates] == [0]
    assert result.has_more is True


def test_all_unanchorable_and_absent_quotes_return_empty_success():
    rep = representation("a|b", ((1, 0, 1), (3, 2, 3)))
    crossing = api("find_pdf_quote_candidates")(rep, "a|b")
    assert (
        crossing.candidates,
        crossing.occurrence_count,
        crossing.candidate_count,
        crossing.cross_page_match_count,
        crossing.has_more,
    ) == ((), 1, 0, 1, False)
    absent = api("find_pdf_quote_candidates")(rep, "missing")
    assert (
        absent.candidates,
        absent.occurrence_count,
        absent.candidate_count,
        absent.cross_page_match_count,
        absent.has_more,
    ) == ((), 0, 0, 0, False)


def test_page_scope_uses_real_page_number_and_excludes_cross_boundary_quotes():
    rep = representation("aaa|aaa", ((2, 0, 3), (5, 4, 7)))
    result = api("find_pdf_quote_candidates")(rep, "aa", page_number=5)
    assert [s.start for s in result.candidates] == [4, 5]
    assert (result.occurrence_count, result.candidate_count, result.cross_page_match_count) == (
        2,
        2,
        0,
    )
    assert api("find_pdf_quote_candidates")(rep, "a|a", page_number=2).occurrence_count == 0


@pytest.mark.parametrize(
    "length, expected", [(0, (None, None)), (1, (" ", " ")), (200, ("😀e\u0301 ", " tail"))]
)
def test_preview_is_bounded_exact_unicode_and_preserves_whitespace(length, expected):
    rep = representation("😀e\u0301 q tail", ((7, 0, 10),))
    result = api("find_pdf_quote_candidates")(
        rep, "q", limits=api("PdfQuoteSearchLimits")(context_characters=length)
    )
    selector = result.candidates[0]
    assert (selector.start, selector.end, selector.page_number) == (4, 5, 7)
    assert (selector.prefix, selector.suffix) == expected
    assert api("find_pdf_quote_candidates")(rep, "é").occurrence_count == 0


@pytest.mark.parametrize(
    "field", ["max_text_characters", "max_occurrences", "max_candidates", "context_characters"]
)
@pytest.mark.parametrize("value", [True, "2", 1.5, -1])
def test_limits_reject_non_integer_values_and_negative_values(field, value):
    with pytest.raises(AuditError, match="^invalid_quote_search_limits$"):
        api("PdfQuoteSearchLimits")(**{field: value})


@pytest.mark.parametrize(
    "field, value",
    [
        ("max_text_characters", 0),
        ("max_occurrences", 0),
        ("max_candidates", 0),
        ("max_candidates", 1001),
        ("context_characters", 201),
    ],
)
def test_limits_enforce_field_specific_ranges(field, value):
    with pytest.raises(AuditError, match="^invalid_quote_search_limits$"):
        api("PdfQuoteSearchLimits")(**{field: value})


def test_limits_are_immutable_and_allow_inclusive_boundaries():
    limits = api("PdfQuoteSearchLimits")(
        max_text_characters=3, max_occurrences=2, max_candidates=1000, context_characters=200
    )
    rep = representation("aaa", ((1, 0, 3),))
    result = api("find_pdf_quote_candidates")(rep, "aa", limits=limits)
    assert (result.occurrence_count, result.candidate_count, result.has_more) == (2, 2, False)
    with pytest.raises(FrozenInstanceError):
        limits.max_occurrences = 9


@pytest.mark.parametrize(
    "kwargs, code",
    [
        ({"max_text_characters": 2}, "quote_search_text_limit_exceeded"),
        ({"max_occurrences": 1, "max_candidates": 1}, "quote_search_occurrence_limit_exceeded"),
    ],
)
def test_exceeded_limits_fail_instead_of_returning_partial_results(kwargs, code):
    rep = representation("aaa", ((1, 0, 3),))
    with pytest.raises(AuditError, match=f"^{code}$"):
        api("find_pdf_quote_candidates")(rep, "aa", limits=api("PdfQuoteSearchLimits")(**kwargs))


@pytest.mark.parametrize("page", [True, 0, -1, "2", 2.0, 1, 3])
def test_invalid_pages_do_not_guess_or_coerce(page):
    rep = representation("text", ((2, 0, 4),))
    with pytest.raises(AuditError, match="^invalid_page_number$"):
        api("find_pdf_quote_candidates")(rep, "text", page_number=page)


@pytest.mark.parametrize("quote", [None, 1, "", " \t", "\ud800"])
def test_invalid_quotes_keep_existing_fixed_error(quote):
    rep = representation("text", ((1, 0, 4),))
    with pytest.raises(AuditError, match="^invalid_quote$"):
        api("find_pdf_quote_candidates")(rep, quote)


@pytest.mark.parametrize(
    "contexts, expected",
    [
        ({"prefix": "B"}, (4, 5, "B", None)),
        ({"suffix": "y"}, (4, 5, None, "y")),
        ({"prefix": "A", "suffix": "x"}, (1, 2, "A", "x")),
    ],
)
def test_resolver_uses_exact_adjacent_prefix_suffix_or_both(contexts, expected):
    rep = representation("AqxBqy", ((6, 0, 6),))
    selector = api("resolve_pdf_quote")(rep, "q", **contexts)
    assert (selector.start, selector.end, selector.prefix, selector.suffix) == expected
    assert (selector.page_number, selector.quote, selector.regions) == (6, "q", ())
    validated = validate_citation(
        Citation(
            citation_id=UUID("33333333-3333-4333-8333-333333333333"),
            document_version_id=VERSION,
            representation_id=REPRESENTATION,
            selector=selector,
        ),
        rep,
    )
    assert (validated.anchor_status, validated.support_status) == ("matched", "not_evaluated")


@pytest.mark.parametrize(
    "contexts, code",
    [
        ({}, "quote_ambiguous"),
        ({"prefix": "A", "suffix": "y"}, "quote_not_found"),
        ({"prefix": "Bq"}, "quote_not_found"),
        ({"suffix": "B"}, "quote_not_found"),
    ],
)
def test_resolver_never_guesses_nonadjacent_or_conflicting_context(contexts, code):
    rep = representation("AqxBqy", ((6, 0, 6),))
    with pytest.raises(AuditError, match=f"^{code}$"):
        api("resolve_pdf_quote")(rep, "q", **contexts)


def test_resolver_keeps_overlapping_matches_in_uniqueness():
    rep = representation("aaa", ((1, 0, 3),))
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("resolve_pdf_quote")(rep, "aa")
    selector = api("resolve_pdf_quote")(rep, "aa", prefix="a")
    assert (selector.start, selector.end, selector.prefix, selector.suffix) == (1, 3, "a", None)


@pytest.mark.parametrize("field", ["prefix", "suffix"])
@pytest.mark.parametrize("context", ["", "\ud800", 1, True, "a" * 201])
def test_resolver_rejects_invalid_context_without_echoing_it(field, context):
    rep = representation("q", ((1, 0, 1),))
    with pytest.raises(AuditError, match="^invalid_quote_context$"):
        api("resolve_pdf_quote")(rep, "q", **{field: context})


def test_contexts_use_codepoints_preserve_whitespace_and_do_not_normalize():
    rep = representation(" \tq \n|😀e\u0301q", ((1, 0, 5), (8, 6, 10)))
    whitespace = api("resolve_pdf_quote")(rep, "q", prefix=" \t", suffix=" \n")
    assert (whitespace.start, whitespace.end, whitespace.prefix, whitespace.suffix) == (
        2,
        3,
        " \t",
        " \n",
    )
    unicode = api("resolve_pdf_quote")(rep, "q", prefix="😀e\u0301")
    assert (unicode.start, unicode.end, unicode.page_number, unicode.prefix) == (
        9,
        10,
        8,
        "😀e\u0301",
    )
    with pytest.raises(AuditError, match="^quote_not_found$"):
        api("resolve_pdf_quote")(rep, "q", prefix="😀é")
    text = "😀" * 200 + "q" + "e\u0301" * 100
    boundary = api("resolve_pdf_quote")(
        representation(text, ((9, 0, 401),)), "q", prefix="😀" * 200, suffix="e\u0301" * 100
    )
    assert (boundary.start, boundary.end, len(boundary.prefix), len(boundary.suffix)) == (
        200,
        201,
        200,
        200,
    )


@pytest.mark.parametrize(
    "contexts, code",
    [
        ({}, "quote_ambiguous"),
        ({"prefix": "x"}, "quote_crosses_page"),
    ],
)
def test_cross_page_quote_matches_are_not_discarded_from_uniqueness(contexts, code):
    rep = representation("abxab", ((1, 0, 2), (4, 4, 5)))
    with pytest.raises(AuditError, match=f"^{code}$"):
        api("resolve_pdf_quote")(rep, "ab", **contexts)


def test_single_cross_page_quote_is_unanchorable():
    rep = representation("a|b", ((1, 0, 1), (3, 2, 3)))
    with pytest.raises(AuditError, match="^quote_crosses_page$"):
        api("resolve_pdf_quote")(rep, "a|b")


@pytest.mark.parametrize("spans", [((1, 0, 3), (2, 4, 6)), ((1, 0, 3), (2, 3, 5))])
def test_matching_cross_boundary_context_does_not_hide_ambiguous_occurrences(spans):
    rep = representation("LqRLqR", spans)
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("resolve_pdf_quote")(rep, "q", prefix="L", suffix="R")


@pytest.mark.parametrize(
    "contexts", [{"prefix": "L"}, {"suffix": "R"}, {"prefix": "L", "suffix": "R"}]
)
@pytest.mark.parametrize("page", [None, 4])
def test_matching_context_outside_selected_page_is_unanchorable(contexts, page):
    rep = representation("LqR", ((4, 1, 2),))
    with pytest.raises(AuditError, match="^quote_crosses_page$"):
        api("resolve_pdf_quote")(rep, "q", page_number=page, **contexts)


@pytest.mark.parametrize("page", [None, 5])
def test_unprovided_context_is_none_and_unique_resolution_matches_existing_locator(page):
    rep = representation("first|last", ((2, 0, 5), (5, 6, 10)))
    selector = api("resolve_pdf_quote")(rep, "last", page_number=page)
    assert selector == ingestion.locate_pdf_quote(rep, "last", page_number=page)
    assert (
        selector.start,
        selector.end,
        selector.page_number,
        selector.prefix,
        selector.suffix,
    ) == (6, 10, 5, None, None)


@pytest.mark.parametrize("function", ["find_pdf_quote_candidates", "resolve_pdf_quote"])
def test_page_scope_text_and_occurrence_limits_ignore_other_pages(function):
    rep = representation("qqqqqq|q", ((1, 0, 6), (7, 7, 8)))
    limits = api("PdfQuoteSearchLimits")(max_text_characters=1, max_occurrences=1)
    result = api(function)(rep, "q", page_number=7, limits=limits)
    selector = result.candidates[0] if function == "find_pdf_quote_candidates" else result
    assert (selector.start, selector.end, selector.page_number) == (7, 8, 7)
    with pytest.raises(AuditError, match="^quote_search_text_limit_exceeded$"):
        api(function)(rep, "q", limits=limits)


@pytest.mark.parametrize("contexts", [{}, {"prefix": "B"}, {"prefix": "Z"}])
def test_resolver_counts_raw_occurrences_before_context_filter_and_fails_at_limit(contexts):
    rep = representation("AqBq", ((1, 0, 4),))
    with pytest.raises(AuditError, match="^quote_search_occurrence_limit_exceeded$"):
        api("resolve_pdf_quote")(
            rep, "q", limits=api("PdfQuoteSearchLimits")(max_occurrences=1), **contexts
        )


def test_resolver_does_not_infer_uniqueness_from_truncated_candidates():
    rep = representation("AqBq", ((1, 0, 4),))
    limits = api("PdfQuoteSearchLimits")(max_candidates=1, max_occurrences=2)
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("resolve_pdf_quote")(rep, "q", limits=limits)
    selector = api("resolve_pdf_quote")(rep, "q", prefix="B", limits=limits)
    assert (selector.start, selector.end, selector.prefix, selector.suffix) == (3, 4, "B", None)


@pytest.mark.parametrize(
    "quote, page, code",
    [
        ("", None, "invalid_quote"),
        (" \t", None, "invalid_quote"),
        ("\ud800", None, "invalid_quote"),
        (None, None, "invalid_quote"),
        ("q", True, "invalid_page_number"),
        ("q", "2", "invalid_page_number"),
        ("q", 2.0, "invalid_page_number"),
        ("q", 0, "invalid_page_number"),
        ("q", -1, "invalid_page_number"),
        ("q", 1, "invalid_page_number"),
        ("missing", None, "quote_not_found"),
    ],
)
def test_resolver_preserves_existing_quote_and_page_errors(quote, page, code):
    rep = representation("q", ((2, 0, 1),))
    with pytest.raises(AuditError, match=f"^{code}$"):
        api("resolve_pdf_quote")(rep, quote, page_number=page)


def test_resolver_can_disambiguate_repetition_by_real_page_number():
    rep = representation("q|q", ((2, 0, 1), (8, 2, 3)))
    selector = api("resolve_pdf_quote")(rep, "q", page_number=8)
    assert (selector.start, selector.end, selector.page_number) == (2, 3, 8)
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("resolve_pdf_quote")(rep, "q")


@pytest.mark.parametrize("function", ["find_pdf_quote_candidates", "resolve_pdf_quote"])
@pytest.mark.parametrize("limits", [None, {}, 1])
def test_search_rejects_invalid_limits_argument_with_public_safe_error(function, limits):
    rep = representation("q", ((1, 0, 1),))
    with pytest.raises(AuditError, match="^invalid_quote_search_limits$"):
        api(function)(rep, "q", limits=limits)


def test_default_candidate_and_preview_bounds_are_applied_to_results():
    text = "L" * 90 + "q" * 101 + "R" * 90
    rep = representation(text, ((1, 0, 281),))
    result = api("find_pdf_quote_candidates")(rep, "q")
    assert (
        len(result.candidates),
        result.candidate_count,
        result.occurrence_count,
        result.has_more,
    ) == (100, 101, 101, True)
    assert (result.candidates[0].prefix, result.candidates[0].suffix) == ("L" * 80, "q" * 80)


def test_maximum_candidate_bound_preserves_complete_counts():
    rep = representation("q" * 1001, ((1, 0, 1001),))
    result = api("find_pdf_quote_candidates")(
        rep, "q", limits=api("PdfQuoteSearchLimits")(max_candidates=1000, context_characters=0)
    )
    assert (
        len(result.candidates),
        result.candidate_count,
        result.occurrence_count,
        result.has_more,
    ) == (1000, 1001, 1001, True)
    assert (result.candidates[-1].start, result.candidates[-1].end) == (999, 1000)


@pytest.mark.parametrize("function", ["find_pdf_quote_candidates", "resolve_pdf_quote"])
def test_default_text_scan_limit_is_inclusive_and_refuses_oversized_scope(function):
    text = "x" * 999_999 + "q"
    result = api(function)(representation(text, ((1, 0, 1_000_000),)), "q")
    selector = result.candidates[0] if function == "find_pdf_quote_candidates" else result
    assert (selector.start, selector.end) == (999_999, 1_000_000)
    with pytest.raises(AuditError, match="^quote_search_text_limit_exceeded$"):
        api(function)(representation(text + "x", ((1, 0, 1_000_001),)), "q")


@pytest.mark.parametrize("function", ["find_pdf_quote_candidates", "resolve_pdf_quote"])
def test_default_raw_occurrence_limit_applies_even_after_return_or_context_bounds(function):
    rep = representation("q" * 10_001, ((1, 0, 10_001),))
    with pytest.raises(AuditError, match="^quote_search_occurrence_limit_exceeded$"):
        api(function)(rep, "q")


def test_real_synthetic_pdf_candidates_and_context_resolution_round_trip(tmp_path):
    from pdf_fixtures import source

    root, _, digest = source(tmp_path, ["left 한글😀e\u0301 right", "", "other 한글😀e\u0301 tail"])
    rep = ingestion.to_pdf_representation(
        ingestion.extract_pdf_text(root, "pdfs/PRIVATE.pdf", digest),
        document_version_id=VERSION,
        representation_id=REPRESENTATION,
    )
    result = api("find_pdf_quote_candidates")(rep, "한글😀e\u0301")
    assert [(s.start, s.end, s.page_number) for s in result.candidates] == [(5, 10, 1), (28, 33, 3)]
    selected = api("resolve_pdf_quote")(rep, "한글😀e\u0301", prefix="other ", suffix=" tail")
    assert (selected.start, selected.end, selected.page_number) == (28, 33, 3)
    validated = validate_citation(
        Citation(
            citation_id=UUID("33333333-3333-4333-8333-333333333333"),
            document_version_id=VERSION,
            representation_id=REPRESENTATION,
            selector=selected,
        ),
        rep,
    )
    assert (validated.anchor_status, validated.support_status) == ("matched", "not_evaluated")
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        ingestion.locate_pdf_quote(rep, "한글😀e\u0301")
