"""Synthetic source contracts; no provider requests or production data."""

import json
from hashlib import sha256

import issuedigest_domain as domain
import pytest
from pydantic import ValidationError

DOCUMENT = {
    "document_id": "11111111-1111-4111-8111-111111111111",
    "workspace_id": "22222222-2222-4222-8222-222222222222",
    "provider": " synthetic ",
    "source_id": " fixture-1 ",
    "source_kind": "other",
    "canonical_url": "https://example.invalid/synthetic",
}


def test_source_document_round_trip_preserves_provider_identity():
    model = getattr(domain, "SourceDocument", None)
    assert model is not None, "SourceDocument public JSON contract is unavailable"
    document = model.model_validate_json(json.dumps(DOCUMENT))
    assert json.loads(document.model_dump_json()) == DOCUMENT


@pytest.mark.parametrize("field", ["provider", "source_id"])
@pytest.mark.parametrize("value", ["", " \t\n"])
def test_source_identity_rejects_blank_values(field, value):
    with pytest.raises(ValidationError):
        domain.SourceDocument.model_validate_json(json.dumps({**DOCUMENT, field: value}))


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.invalid/a",
        "relative/path",
        "https://user@example.invalid/a",
        "https://user:password@example.invalid/a",
        "https:///missing-host",
    ],
)
def test_source_url_rejects_unsupported_or_credentialed_locations(url):
    with pytest.raises(ValidationError):
        domain.SourceDocument.model_validate_json(json.dumps({**DOCUMENT, "canonical_url": url}))


@pytest.mark.parametrize(
    "patch",
    [
        {"extra": 1},
        {"document_id": "11111111-1111-1111-8111-111111111111"},
        {"workspace_id": "bad"},
        {"source_kind": "unknown"},
        {"provider": 2},
    ],
)
def test_source_rejects_invalid_json_contract(patch):
    with pytest.raises(ValidationError):
        domain.SourceDocument.model_validate_json(json.dumps({**DOCUMENT, **patch}))


VERSION = {
    "version_id": "33333333-3333-4333-8333-333333333333",
    "document_id": DOCUMENT["document_id"],
    "raw_object_id": "44444444-4444-4444-8444-444444444444",
    "raw_sha256": "a" * 64,
    "media_type": "text/plain",
    "collected_at": "2026-10-11T09:00:00+09:00",
}


def test_raw_version_json_round_trip_normalizes_only_collection_instant():
    model = getattr(domain, "DocumentVersion", None)
    assert model is not None, "DocumentVersion JSON contract is unavailable"
    version = model.model_validate_json(json.dumps(VERSION))
    output = json.loads(version.model_dump_json())
    assert output == {**VERSION, "collected_at": "2026-10-11T00:00:00Z"}
    assert model.model_validate_json(version.model_dump_json()) == version


@pytest.mark.parametrize(
    "patch",
    [
        {"version_id": "bad"},
        {"document_id": "bad"},
        {"raw_object_id": "/private/raw.pdf"},
        {"raw_object_id": "https://example.invalid/signed"},
        {"raw_sha256": "A" * 64},
        {"raw_sha256": "0" * 63},
        {"raw_sha256": "g" * 64},
        {"collected_at": "2026-10-11T00:00:00"},
        {"published_at": "2026-10-11"},
    ],
)
def test_raw_version_rejects_untrusted_fields(patch):
    model = getattr(domain, "DocumentVersion", None)
    assert model is not None, "DocumentVersion validation is unavailable"
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps({**VERSION, **patch}))


TEXT = " 앞😀한e\u0301 뒤 "
REPRESENTATION = {
    "representation_id": "55555555-5555-4555-8555-555555555555",
    "document_version_id": VERSION["version_id"],
    "parser_name": "synthetic",
    "parser_version": "1",
    "normalization_profile": "identity-v1",
    "text": TEXT,
    "text_sha256": sha256(TEXT.encode()).hexdigest(),
    "pages": [{"page_number": 1, "start": 0, "end": 4}, {"page_number": 2, "start": 5, "end": 9}],
    "tables": [
        {"table_id": "t1", "cells": [{"cell_id": "c1", "text": "80%"}]},
        {"table_id": "t2", "cells": [{"cell_id": "c1", "text": ""}]},
        {"table_id": "empty", "cells": []},
    ],
}


def test_parsed_json_round_trip_keeps_missing_conditions_and_empty_table():
    model = getattr(domain, "ParsedRepresentation", None)
    assert model is not None, "ParsedRepresentation public contract is unavailable"
    parsed = model.model_validate_json(json.dumps(REPRESENTATION))
    assert model.model_validate_json(parsed.model_dump_json()) == parsed
    assert parsed.text == TEXT
    assert parsed.tables[0].cells[0].sample_size is None
    assert parsed.tables[0].cells[0].question is None
    assert parsed.tables[1].cells[0].text == ""
    assert parsed.tables[2].cells == ()
    assert isinstance(parsed.pages, tuple)
    assert isinstance(parsed.tables[0].cells, tuple)
    with pytest.raises(ValidationError):
        parsed.tables[0].cells[0].text = "made up"
    with pytest.raises(ValidationError):
        parsed.pages[0].start = 3
    with pytest.raises(ValidationError):
        parsed.text = "changed"


@pytest.mark.parametrize(
    "patch",
    [
        {"text_sha256": "0" * 64},
        {"text": "\ud800"},
        {"parser_name": " "},
        {"parser_version": ""},
        {"normalization_profile": "\t"},
        {"representation_id": "bad"},
        {"document_version_id": "bad"},
        {"extra": True},
    ],
)
def test_parsed_representation_rejects_bad_hash_identity_or_profile(patch):
    with pytest.raises(ValidationError):
        domain.ParsedRepresentation.model_validate_json(json.dumps({**REPRESENTATION, **patch}))


@pytest.mark.parametrize(
    "pages",
    [
        [{"page_number": 1, "start": 0, "end": 3}, {"page_number": 1, "start": 4, "end": 5}],
        [{"page_number": 1, "start": 0, "end": 5}, {"page_number": 2, "start": 4, "end": 6}],
        [{"page_number": 1, "start": 4, "end": 6}, {"page_number": 2, "start": 0, "end": 3}],
        [{"page_number": 1, "start": 0, "end": 10}],
        [{"page_number": 1, "start": 3, "end": 3}],
        [{"page_number": 0, "start": 0, "end": 1}],
        [{"page_number": True, "start": 0, "end": 1}],
        [{"page_number": 1.0, "start": 0, "end": 1}],
        [{"page_number": "1", "start": 0, "end": 1}],
        [{"page_number": 1, "start": False, "end": 1}],
        [{"page_number": 1, "start": 0.0, "end": 1}],
        [{"page_number": 1, "start": "0", "end": 1}],
        [{"page_number": 1, "start": -1, "end": 1}],
        [{"page_number": 1, "start": 0, "end": "1"}],
        [{"page_number": 1, "start": 0, "end": 1, "extra": 1}],
    ],
)
def test_parsed_pages_reject_invalid_order_bounds_or_scalar_types(pages):
    with pytest.raises(ValidationError):
        domain.ParsedRepresentation.model_validate_json(
            json.dumps({**REPRESENTATION, "pages": pages})
        )


@pytest.mark.parametrize(
    "tables",
    [
        [{"table_id": "t", "cells": []}, {"table_id": "t", "cells": []}],
        [{"table_id": "t", "cells": [{"cell_id": "c", "text": ""}, {"cell_id": "c", "text": ""}]}],
        [{"table_id": " ", "cells": []}],
        [{"table_id": "t", "cells": [{"cell_id": "", "text": ""}]}],
    ],
)
def test_parsed_tables_reject_duplicate_or_blank_identity(tables):
    with pytest.raises(ValidationError):
        domain.ParsedRepresentation.model_validate_json(
            json.dumps({**REPRESENTATION, "tables": tables})
        )


@pytest.mark.parametrize("sample_size", [0, -1, True, 1.5, "100"])
def test_table_sample_size_rejects_nonpositive_or_coerced_numbers(sample_size):
    with pytest.raises(ValidationError):
        domain.TableCell.model_validate_json(
            json.dumps({"cell_id": "c", "text": "", "sample_size": sample_size})
        )


@pytest.mark.parametrize("url", ["https://@example.invalid/a", "https://:pass@example.invalid/a"])
def test_source_rejects_even_empty_url_userinfo(url):
    with pytest.raises(ValidationError):
        domain.SourceDocument.model_validate_json(json.dumps({**DOCUMENT, "canonical_url": url}))


def test_python_input_rejects_invalid_utf8_text_as_validation_error():
    with pytest.raises(ValidationError, match="UTF-8"):
        domain.ParsedRepresentation.model_validate({**REPRESENTATION, "text": "\ud800"})


@pytest.mark.parametrize(
    "model,data",
    [
        (domain.PageSpan, {"page_number": 1, "start": 0, "end": 1}),
        (domain.TableCell, {"cell_id": "c", "text": ""}),
        (domain.ParsedTable, {"table_id": "t", "cells": []}),
    ],
)
def test_nested_source_models_reject_extra_fields(model, data):
    with pytest.raises(ValidationError):
        model.model_validate_json(json.dumps({**data, "extra": 1}))


def test_table_preserves_incomplete_statistics_without_filling_conditions():
    cell = domain.TableCell.model_validate_json(
        json.dumps(
            {
                "cell_id": "80-percent",
                "text": "80%",
                "unit": "%",
                "sample_size": 100,
                "period": "2026-10",
                "question": "synthetic question",
                "population": None,
                "methodology": None,
                "weighting": None,
            }
        )
    )
    assert json.loads(cell.model_dump_json()) == {
        "cell_id": "80-percent",
        "text": "80%",
        "unit": "%",
        "sample_size": 100,
        "period": "2026-10",
        "question": "synthetic question",
        "population": None,
        "methodology": None,
        "weighting": None,
    }


@pytest.mark.parametrize("digest", ["a" * 64 + "\n", "a" * 64 + " ", " " + "a" * 64, 0])
def test_raw_sha256_is_exactly_64_lowercase_hex_characters(digest):
    with pytest.raises(ValidationError):
        domain.DocumentVersion.model_validate_json(json.dumps({**VERSION, "raw_sha256": digest}))
