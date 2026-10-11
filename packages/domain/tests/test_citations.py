"""Anchors match parsed text, without claiming semantic support or storage."""

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import issuedigest_domain as domain
import pytest
from pydantic import ValidationError

FIXTURE = json.loads(
    (Path(__file__).parents[3] / "tests/fixtures/citation-unicode.json").read_text()
)
TEXT = FIXTURE["text"]
DOCUMENT_ID = "11111111-1111-4111-8111-111111111111"
VERSION_ID = "33333333-3333-4333-8333-333333333333"
REPRESENTATION_ID = "55555555-5555-4555-8555-555555555555"
OTHER_ID = "99999999-9999-4999-8999-999999999999"
CITATION_ID = "66666666-6666-4666-8666-666666666666"


def representation_data():
    return {
        "representation_id": REPRESENTATION_ID,
        "document_version_id": VERSION_ID,
        "parser_name": "synthetic",
        "parser_version": "1",
        "normalization_profile": "identity-v1",
        "text": TEXT,
        "text_sha256": sha256(TEXT.encode()).hexdigest(),
        "pages": [
            {"page_number": 1, "start": 0, "end": 7},
            {"page_number": 2, "start": 8, "end": 10},
        ],
        "tables": [
            {"table_id": "t1", "cells": [{"cell_id": "c1", "text": "80%"}]},
            {"table_id": "t2", "cells": [{"cell_id": "c1", "text": ""}]},
        ],
    }


def citation_data(selector=None):
    return {
        "citation_id": CITATION_ID,
        "document_version_id": VERSION_ID,
        "representation_id": REPRESENTATION_ID,
        "selector": deepcopy(selector if selector is not None else FIXTURE["cases"][0]["selector"]),
    }


def bundle_data():
    return {
        "document": {
            "document_id": DOCUMENT_ID,
            "workspace_id": "22222222-2222-4222-8222-222222222222",
            "provider": "synthetic",
            "source_id": "fixture",
            "source_kind": "other",
        },
        "version": {
            "version_id": VERSION_ID,
            "document_id": DOCUMENT_ID,
            "raw_object_id": "44444444-4444-4444-8444-444444444444",
            "raw_sha256": "a" * 64,
            "media_type": "application/pdf",
            "collected_at": "2026-10-11T00:00:00Z",
        },
        "representation": representation_data(),
        "citations": [citation_data()],
    }


def test_evidence_bundle_round_trip_keeps_anchor_and_semantic_status_separate():
    model = getattr(domain, "EvidenceBundle", None)
    assert model is not None, "EvidenceBundle JSON contract unavailable"
    bundle = model.model_validate_json(json.dumps(bundle_data()))
    assert model.model_validate_json(bundle.model_dump_json()) == bundle
    result = domain.validate_citation(bundle.citations[0], bundle.representation)
    assert json.loads(result.model_dump_json()) == {
        "citation_id": CITATION_ID,
        "anchor_status": "matched",
        "support_status": "not_evaluated",
    }
    assert isinstance(bundle.citations, tuple)
    with pytest.raises(ValidationError):
        bundle.citations[0].selector.quote = "changed"


@pytest.mark.parametrize("case", FIXTURE["cases"])
def test_shared_unicode_fixture_selects_exact_code_points(case):
    model = getattr(domain, "Citation", None)
    assert model is not None, "Citation JSON contract unavailable"
    citation = model.model_validate_json(json.dumps(citation_data(case["selector"])))
    representation = domain.ParsedRepresentation.model_validate_json(
        json.dumps(representation_data())
    )
    assert domain.validate_citation(citation, representation).anchor_status == "matched"
    selector = citation.selector
    assert representation.text[selector.start : selector.end] == selector.quote


@pytest.mark.parametrize(
    "patch",
    [
        {"start": -1},
        {"start": True},
        {"start": 2.0},
        {"start": "2"},
        {"end": True},
        {"end": 7.0},
        {"end": "7"},
        {"end": 2},
        {"end": 30},
        {"quote": ""},
        {"quote": "😀한éé"},
        {"quote": "😀한e\u0301é "},
        {"prefix": "앞 "},
        {"prefix": "too long prefix"},
        {"suffix": "뒤 "},
        {"suffix": " 뒤 too long"},
        {"extra": 1},
        {"kind": "unknown"},
    ],
)
def test_text_anchor_rejects_bad_range_quote_context_or_shape(patch):
    data = bundle_data()
    data["citations"][0]["selector"].update(patch)
    with pytest.raises(ValueError):
        domain.EvidenceBundle.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "selector",
    [
        {"kind": "pdf", "page_number": 2, "start": 2, "end": 7, "quote": "😀한e\u0301é"},
        {"kind": "pdf", "page_number": 1, "start": 6, "end": 8, "quote": "é "},
        {"kind": "pdf", "page_number": 3, "start": 0, "end": 2, "quote": " 앞"},
        {"kind": "pdf", "page_number": True, "start": 0, "end": 2, "quote": " 앞"},
        {"kind": "table_cell", "table_id": "missing", "cell_id": "c1", "quote": "80%"},
        {"kind": "table_cell", "table_id": "t1", "cell_id": "missing", "quote": "80%"},
        {"kind": "table_cell", "table_id": "t1", "cell_id": "c1", "quote": "80"},
        {"kind": "table_cell", "table_id": "t2", "cell_id": "c1", "quote": "80%"},
    ],
)
def test_pdf_and_table_anchors_reject_missing_locations_or_wrong_quote(selector):
    with pytest.raises(ValueError):
        domain.EvidenceBundle.model_validate_json(
            json.dumps({**bundle_data(), "citations": [citation_data(selector)]})
        )


@pytest.mark.parametrize(
    "selector",
    [
        {
            "kind": "pdf",
            "page_number": 1,
            "start": 2,
            "end": 7,
            "quote": "😀한e\u0301é",
            "regions": [{"x0": 0, "y0": 0.1, "x1": 1, "y1": 0.9}],
        },
        {"kind": "table_cell", "table_id": "t1", "cell_id": "c1", "quote": "80%"},
        {"kind": "table_cell", "table_id": "t2", "cell_id": "c1", "quote": ""},
        {"kind": "text", "start": 0, "end": 2, "quote": " 앞", "prefix": "", "suffix": "😀"},
        {
            "kind": "text",
            "start": 2,
            "end": 7,
            "quote": "😀한e\u0301é",
            "prefix": "앞",
            "suffix": " 뒤",
        },
    ],
)
def test_exact_pdf_table_and_boundary_context_anchors_are_accepted(selector):
    bundle = domain.EvidenceBundle.model_validate_json(
        json.dumps({**bundle_data(), "citations": [citation_data(selector)]})
    )
    assert (
        domain.validate_citation(bundle.citations[0], bundle.representation).support_status
        == "not_evaluated"
    )
    if isinstance(bundle.citations[0].selector, domain.PdfQuoteSelector):
        assert isinstance(bundle.citations[0].selector.regions, tuple)
        with pytest.raises(ValidationError):
            bundle.citations[0].selector.regions[0].x0 = 0.2


@pytest.mark.parametrize(
    "patch",
    [
        {"x0": True},
        {"x0": "0.2"},
        {"x0": float("nan")},
        {"x1": float("inf")},
        {"x0": -0.1},
        {"y0": -0.1},
        {"x1": 1.1},
        {"y1": 1.1},
        {"x0": 0.8, "x1": 0.8},
        {"y0": 0.9, "y1": 0.8},
        {"extra": 1},
    ],
)
def test_pdf_boxes_reject_nonfinite_coerced_or_inverted_coordinates(patch):
    with pytest.raises(ValidationError):
        domain.NormalizedBox.model_validate_json(
            json.dumps({"x0": 0, "y0": 0, "x1": 1, "y1": 1, **patch})
        )


@pytest.mark.parametrize(
    "section,field",
    [
        ("version", "document_id"),
        ("representation", "document_version_id"),
        ("citation", "document_version_id"),
        ("citation", "representation_id"),
    ],
)
def test_bundle_rejects_broken_chain_and_cross_version_citations(section, field):
    data = bundle_data()
    target = data["citations"][0] if section == "citation" else data[section]
    target[field] = OTHER_ID
    with pytest.raises(ValueError):
        domain.EvidenceBundle.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("field", ["document_version_id", "representation_id"])
def test_standalone_validator_rejects_mismatched_versions(field):
    citation = domain.Citation.model_validate({**citation_data(), field: OTHER_ID})
    with pytest.raises(ValueError):
        domain.validate_citation(
            citation, domain.ParsedRepresentation.model_validate(representation_data())
        )


def test_standalone_validator_rejects_wrong_anchor():
    data = citation_data({"kind": "text", "start": 2, "end": 3, "quote": "wrong"})
    with pytest.raises(ValueError):
        domain.validate_citation(
            domain.Citation.model_validate(data),
            domain.ParsedRepresentation.model_validate(representation_data()),
        )


def test_bundle_rejects_duplicate_citation_id():
    data = bundle_data()
    data["citations"].append(citation_data())
    with pytest.raises(ValueError):
        domain.EvidenceBundle.model_validate_json(json.dumps(data))


@pytest.mark.parametrize("version", [True, 1.0, "1", 2])
def test_bundle_schema_version_rejects_coercion(version):
    with pytest.raises(ValueError):
        domain.EvidenceBundle.model_validate_json(
            json.dumps({**bundle_data(), "schema_version": version})
        )


def test_parser_only_revision_coexists_and_keeps_previous_citation():
    first = domain.EvidenceBundle.model_validate(bundle_data())
    revised = bundle_data()
    revised["representation"]["representation_id"] = OTHER_ID
    revised["representation"]["parser_version"] = "2"
    revised["citations"][0]["representation_id"] = OTHER_ID
    second = domain.EvidenceBundle.model_validate(revised)
    assert first.version == second.version
    assert first.representation.representation_id != second.representation.representation_id
    assert first.representation.parser_version == "1"
    assert (
        domain.validate_citation(first.citations[0], first.representation).anchor_status
        == "matched"
    )
    with pytest.raises(ValueError):
        domain.validate_citation(first.citations[0], second.representation)


@pytest.mark.parametrize(
    "model,data",
    [
        (domain.Citation, citation_data()),
        (domain.CitationAnchorValidation, {"citation_id": CITATION_ID}),
        (domain.EvidenceBundle, bundle_data()),
        (
            domain.TableCellSelector,
            {"kind": "table_cell", "table_id": "t1", "cell_id": "c1", "quote": ""},
        ),
    ],
)
def test_citation_models_reject_extra_fields(model, data):
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps({**data, "extra": 1}))


@pytest.mark.parametrize("field", ["citation_id", "document_version_id", "representation_id"])
def test_citation_ids_reject_non_v4_uuids_in_json(field):
    with pytest.raises(ValidationError):
        domain.Citation.model_validate_json(
            json.dumps({**citation_data(), field: "11111111-1111-1111-8111-111111111111"})
        )


def test_pdf_defaults_to_no_invented_coordinates():
    selector = domain.PdfQuoteSelector.model_validate_json(
        json.dumps({"kind": "pdf", "page_number": 1, "start": 0, "end": 2, "quote": " 앞"})
    )
    assert selector.regions == ()
    assert json.loads(selector.model_dump_json())["regions"] == []


def test_validated_bundle_chain_and_result_models_are_immutable():
    bundle = domain.EvidenceBundle.model_validate_json(json.dumps(bundle_data()))
    result = domain.validate_citation(bundle.citations[0], bundle.representation)
    for model, field, replacement in [
        (bundle, "schema_version", 2),
        (bundle.document, "provider", "changed"),
        (bundle.version, "raw_sha256", "0" * 64),
        (bundle.representation.tables[0], "table_id", "changed"),
        (bundle.citations[0], "representation_id", OTHER_ID),
        (result, "support_status", "supported"),
    ]:
        with pytest.raises(ValidationError):
            setattr(model, field, replacement)
