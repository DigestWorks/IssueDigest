"""Synthetic literal search contracts; expected positions are hand calculated."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib import import_module

import pytest
from issuedigest_domain import EvidenceBundle, PdfQuoteSelector, TableCellSelector

from conftest import bundle_data


def search():
    domain = import_module("issuedigest_domain")
    assert hasattr(domain, "EvidenceSearchQuery"), "literal search query contract is missing"
    return domain


def make_bundle(
    text="한국어 ABC 😀e\u0301é %_' OR 1=1 --", pages=(), cells=(), media_type="text/plain"
):
    data = bundle_data()
    data["citations"] = []
    data["version"]["media_type"] = media_type
    data["representation"].update(
        text=text,
        text_sha256=sha256(text.encode()).hexdigest(),
        pages=pages,
        tables=[{"table_id": "t", "cells": cells}] if cells else [],
    )
    return EvidenceBundle.model_validate(data)


def test_literal_query_preserves_unicode_and_ascii_only_comparison():
    api = search()
    query = api.EvidenceSearchQuery(terms=("한국어", "ABC", "😀", "e\u0301", "%_' OR"))
    assert query.terms == ("한국어", "ABC", "😀", "e\u0301", "%_' OR")
    assert api.ascii_fold("ÄÉABC한국어") == "ÄÉabc한국어"
    assert api.literal_matches(query, "한국어 abc 😀e\u0301 %_' or")
    assert not api.literal_matches(query, "한국어 abc 😀é %_' or")
    assert not api.literal_matches(api.EvidenceSearchQuery(terms=("É",)), "é")
    assert api.literal_ngrams("ABAB") == ("a", "ab", "aba", "b", "ba", "bab")


@pytest.mark.parametrize(
    "terms", [(), ("x",) * 9, ("",), (" ",), (" x",), ("x ",), ("x" * 65,), ("A", "a"), (1,), "x"]
)
def test_invalid_terms_are_rejected(terms):
    with pytest.raises(ValueError):
        search().EvidenceSearchQuery(terms=terms)


@pytest.mark.parametrize("limit", [0, 21, True, "2", 2.0])
def test_limit_is_strict(limit):
    with pytest.raises(ValueError):
        search().EvidenceSearchQuery(terms=("x",), limit=limit)


def test_query_revalidation_rejects_construct_copy_and_time_order():
    api = search()
    query = api.EvidenceSearchQuery(terms=("x",))
    for forged in [
        query.model_copy(update={"terms": ("",)}),
        query.model_construct(terms=("x",) * 9, limit=1),
    ]:
        with pytest.raises(ValueError):
            api.validate_search_query(forged)
    with pytest.raises(ValueError):
        api.EvidenceSearchQuery(terms=("x",), collected_from=datetime(2026, 1, 1))
    instant = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError):
        api.EvidenceSearchQuery(terms=("x",), collected_from=instant, collected_to=instant)
    with pytest.raises(ValueError):
        api.EvidenceSearchQuery(terms=("x",), collected_from=instant.astimezone(timedelta_zone()))


def timedelta_zone():
    from datetime import timezone

    return timezone(timedelta(hours=9))


def test_overlapping_units_keep_unicode_offsets_and_boundary_terms():
    api = search()
    bundle = make_bundle("😀" + "가" * 499 + "정확검색어" + "나" * 520)
    projection = api.build_search_projection(bundle)
    assert [(u.selector.start, u.selector.end) for u in projection.units] == [
        (0, 512),
        (449, 961),
        (898, 1025),
    ]
    assert [u.ordinal for u in projection.units] == [0, 1, 2]
    assert projection.units[1].text[51:56] == "정확검색어"
    assert api.literal_matches(
        api.EvidenceSearchQuery(terms=("정확검색어",)), projection.units[1].text
    )
    assert api.build_search_projection(bundle) == projection
    assert (
        projection.units[0].text_sha256
        == sha256(bundle.representation.text[:512].encode()).hexdigest()
    )


def test_pdf_units_stay_inside_real_pages_and_cells_are_complete():
    api = search()
    bundle = make_bundle(
        "첫째둘째",
        media_type="application/pdf",
        pages=({"page_number": 7, "start": 0, "end": 2}, {"page_number": 9, "start": 2, "end": 4}),
        cells=(
            {"cell_id": "c", "text": "표 전체 😀"},
            {"cell_id": "blank", "text": ""},
            {"cell_id": "large", "text": "가" * 2049},
        ),
    )
    projection = api.build_search_projection(bundle)
    assert [(u.selector.page_number, u.text) for u in projection.units[:2]] == [
        (7, "첫째"),
        (9, "둘째"),
    ]
    assert all(
        isinstance(u.selector, PdfQuoteSelector) and u.selector.regions == ()
        for u in projection.units[:2]
    )
    assert projection.units[2].selector == TableCellSelector(
        table_id="t", cell_id="c", quote="표 전체 😀"
    )
    assert projection.skipped_empty_cells == 1
    assert projection.skipped_large_cells == 1
    assert not any(
        api.literal_matches(api.EvidenceSearchQuery(terms=("째둘",)), u.text)
        for u in projection.units
    )
    with pytest.raises(ValueError):
        api.validate_selector(
            TableCellSelector(table_id="t", cell_id="c", quote="표"), bundle.representation
        )


@pytest.mark.parametrize("kind", ["text", "tables", "cells", "units", "total", "metadata"])
def test_projection_bounds_forged_graph_before_serialization(kind, monkeypatch):
    api = search()
    bundle = make_bundle("가")
    rep = bundle.representation
    if kind == "text":
        rep = rep.model_copy(update={"text": "가" * 1_000_001})
    elif kind == "tables":
        from issuedigest_domain import ParsedTable

        rep = rep.model_copy(
            update={"tables": tuple(ParsedTable(table_id=str(i), cells=()) for i in range(1001))}
        )
    elif kind in {"cells", "units", "total"}:
        from issuedigest_domain import ParsedTable, TableCell

        count, size = {"cells": (20001, 1), "units": (6001, 1), "total": (1000, 2048)}[kind]
        rep = rep.model_copy(
            update={
                "tables": (
                    ParsedTable(
                        table_id="t",
                        cells=tuple(
                            TableCell(cell_id=str(i), text="가" * size) for i in range(count)
                        ),
                    ),
                )
            }
        )
    else:
        bundle = bundle.model_copy(
            update={"document": bundle.document.model_copy(update={"provider": "가" * 12_000_001})}
        )
    forged = bundle.model_copy(update={"representation": rep})

    def serialization_forbidden(*args, **kwargs):
        pytest.fail("serialization happened before the input bound check")

    monkeypatch.setattr(EvidenceBundle, "model_dump_json", serialization_forbidden)
    with pytest.raises(ValueError, match="Invalid search projection input"):
        api.build_search_projection(forged)


def test_forged_query_unknown_fields_and_oversized_terms_fail_before_dump(monkeypatch):
    api = search()
    query = api.EvidenceSearchQuery(terms=("x",))
    with pytest.raises(ValueError):
        api.validate_search_query(query.model_copy(update={"unknown_field": "x"}))

    def forbidden(*args, **kwargs):
        pytest.fail("query serialized before exact term bounds")

    monkeypatch.setattr(api.EvidenceSearchQuery, "model_dump", forbidden)
    for forged in [
        query.model_copy(update={"terms": ("x" * 1_000_000,)}),
        query.model_copy(update={"terms": ("x",) * 10_000}),
    ]:
        with pytest.raises(ValueError):
            api.validate_search_query(forged)


def test_search_query_datetime_json_roundtrip_and_frozen_extra_contract():
    api = search()
    query = api.EvidenceSearchQuery(terms=("x",), collected_from=datetime(2026, 1, 1, tzinfo=UTC))
    assert api.EvidenceSearchQuery.model_validate_json(query.model_dump_json()) == query
    with pytest.raises(ValueError):
        api.EvidenceSearchQuery(terms=("x",), unknown=True)
    with pytest.raises(ValueError):
        query.limit = 2


def test_projection_rejects_unknown_copied_fields():
    api = search()
    bundle = make_bundle()
    with pytest.raises(ValueError, match="Invalid search projection input"):
        api.build_search_projection(bundle.model_copy(update={"unknown_field": "ignored"}))


def test_pdf_body_without_page_spans_is_rejected_without_fabricated_text_anchor():
    api = search()
    bundle = make_bundle("PDF text whose actual page is unknown")
    bundle = bundle.model_copy(
        update={"version": bundle.version.model_copy(update={"media_type": "application/pdf"})}
    )
    with pytest.raises(ValueError, match="Invalid search projection input"):
        api.build_search_projection(bundle)


def test_empty_pdf_body_can_index_complete_cells_without_page_claims():
    api = search()
    bundle = make_bundle("", cells=({"cell_id": "c", "text": "온전한 셀"},))
    bundle = bundle.model_copy(
        update={"version": bundle.version.model_copy(update={"media_type": "application/pdf"})}
    )
    projection = api.build_search_projection(bundle)
    assert len(projection.units) == 1
    assert projection.units[0].selector == TableCellSelector(
        table_id="t", cell_id="c", quote="온전한 셀"
    )


@pytest.mark.parametrize("field", ["provider", "source_id"])
def test_hit_preserves_long_valid_canonical_source_metadata(field):
    api = search()
    bundle = make_bundle("찾을 본문")
    original = "canonical-" + ("x" * 1025)
    bundle = bundle.model_copy(
        update={"document": bundle.document.model_copy(update={field: original})}
    )
    selector = api.build_search_projection(bundle).units[0].selector
    from uuid import uuid4

    from pydantic import ValidationError

    try:
        hit = api.EvidenceSearchHit(
            workspace_id=bundle.document.workspace_id,
            snapshot_id=uuid4(),
            document_id=bundle.document.document_id,
            version_id=bundle.version.version_id,
            representation_id=bundle.representation.representation_id,
            provider=bundle.document.provider,
            source_id=bundle.document.source_id,
            source_kind=bundle.document.source_kind,
            collected_at=bundle.version.collected_at,
            unit_ordinal=0,
            selector=selector,
            matched_terms=("본문",),
        )
    except ValidationError:
        hit = None
    assert hit is not None, "valid canonical source metadata cannot be returned"
    assert getattr(hit, field) == original
    with pytest.raises(ValueError):
        api.EvidenceSearchQuery(terms=("본문",), **{field: original})


def test_ordinary_body_with_page_metadata_covers_gaps_as_text():
    api = search()
    bundle = make_bundle(
        "앞😀숨은e\u0301뒤",
        pages=({"page_number": 3, "start": 0, "end": 1}, {"page_number": 8, "start": 6, "end": 7}),
    )
    projection = api.build_search_projection(bundle)
    assert len(projection.units) == 1
    assert projection.units[0].selector == api.TextQuoteSelector(
        start=0, end=7, quote="앞😀숨은e\u0301뒤"
    )
    assert api.literal_matches(
        api.EvidenceSearchQuery(terms=("숨은e\u0301",)), projection.units[0].text
    )


def test_ordinary_page_metadata_does_not_bypass_full_body_admission_limit(monkeypatch):
    api = search()
    bundle = make_bundle(
        "x" * 1_000_000,
        pages=({"page_number": 1, "start": 0, "end": 1},),
        cells=tuple({"cell_id": str(i), "text": "x"} for i in range(5000)),
    )

    def forbidden(*args, **kwargs):
        pytest.fail("ordinary body exceeded unit bound before serialization")

    monkeypatch.setattr(EvidenceBundle, "model_dump_json", forbidden)
    with pytest.raises(ValueError, match="Invalid search projection input"):
        api.build_search_projection(bundle)
