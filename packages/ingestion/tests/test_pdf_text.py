from dataclasses import FrozenInstanceError
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import issuedigest_ingestion as ingestion
import pytest
from issuedigest_domain.citations import Citation, validate_citation
from issuedigest_ingestion import AuditError
from pdf_fixtures import source


def api(name: str):
    value = getattr(ingestion, name, None)
    assert callable(value), f"{name} must expose the bounded PDF behavior"
    return value


def test_real_pdf_preserves_unicode_offsets_empty_pages_and_source(tmp_path: Path) -> None:
    root, file, digest = source(tmp_path, [" 한글😀e\u0301 repeat ", "", "repeat tail"])
    before = file.read_bytes(), file.stat()
    result = api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    assert result.text == " 한글😀e\u0301 repeat \n\f\n\n\f\nrepeat tail"
    assert result.page_count == 3
    assert result.empty_pages == (2,)
    assert [(p.page_number, p.start, p.end) for p in result.pages] == [(1, 0, 14), (3, 20, 31)]
    assert result.raw_sha256 == digest
    assert result.raw_bytes == len(before[0])
    assert result.text_sha256 == sha256(result.text.encode()).hexdigest()
    assert result.parser_name == "pypdf"
    assert result.parser_version == "6.20.1"
    assert result.normalization_profile == "pypdf-plain-v1"
    assert (file.read_bytes(), file.stat()) == before
    with pytest.raises(FrozenInstanceError):
        result.text = "changed"


def test_exact_quote_consumes_real_existing_anchor_contract(tmp_path: Path) -> None:
    root, _, digest = source(tmp_path, ["한글😀e\u0301 repeat", "", "repeat tail"])
    extraction = api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    version = UUID("11111111-1111-4111-8111-111111111111")
    representation_id = UUID("22222222-2222-4222-8222-222222222222")
    representation = api("to_pdf_representation")(
        extraction, document_version_id=version, representation_id=representation_id
    )
    assert representation.tables == ()
    selector = api("locate_pdf_quote")(representation, "😀e\u0301")
    assert (selector.page_number, selector.start, selector.end, selector.regions) == (1, 2, 5, ())
    citation = Citation(
        citation_id=UUID("33333333-3333-4333-8333-333333333333"),
        document_version_id=version,
        representation_id=representation_id,
        selector=selector,
    )
    validated = validate_citation(citation, representation)
    assert (validated.anchor_status, validated.support_status) == ("matched", "not_evaluated")
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("locate_pdf_quote")(representation, "repeat")
    scoped = api("locate_pdf_quote")(representation, "repeat", page_number=3)
    assert (scoped.start, scoped.end, scoped.page_number) == (18, 24, 3)


@pytest.mark.parametrize("value", [True, 0, -1, "2", 1.5])
def test_pdf_limits_reject_nonpositive_or_coercible_values(value: object) -> None:
    with pytest.raises(AuditError, match="^invalid_limits$"):
        api("PdfLimits")(max_pages=value)


@pytest.mark.parametrize(
    "path",
    [
        "/pdfs/PRIVATE.pdf",
        "pdfs/../PRIVATE.pdf",
        "PRIVATE.pdf",
        "pdfs/PRIVATE.pdf\x00",
        "pdfs\\PRIVATE.pdf",
        "pdfs/",
        "pdfs//PRIVATE.pdf",
        "pdfs/./PRIVATE.pdf",
    ],
)
def test_rejects_unsafe_relative_pdf_paths(tmp_path: Path, path: str) -> None:
    root, _, digest = source(tmp_path, ["text"])
    with pytest.raises(AuditError, match="^invalid_pdf_path$"):
        api("extract_pdf_text")(root, path, digest)


@pytest.mark.parametrize("digest", ["", "A" * 64, "g" * 64, "0" * 63, "0" * 64 + "\n", 1])
def test_expected_hash_is_strict(tmp_path: Path, digest: object) -> None:
    root, _, _ = source(tmp_path, ["text"])
    with pytest.raises(AuditError, match="^invalid_expected_sha256$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)


@pytest.mark.parametrize(
    "kind", ["file_link", "ancestor_link", "root_link", "fifo", "directory", "missing"]
)
def test_descriptor_path_refuses_links_special_files_and_missing(tmp_path: Path, kind: str) -> None:
    import os

    root, file, digest = source(tmp_path, ["text"])
    path = "pdfs/other.pdf"
    if kind == "file_link":
        (root / path).symlink_to(file)
    elif kind == "ancestor_link":
        (root / "pdfs" / "linked").symlink_to(root / "pdfs", target_is_directory=True)
        path = "pdfs/linked/PRIVATE.pdf"
    elif kind == "root_link":
        linked = tmp_path / "linked"
        linked.symlink_to(root, target_is_directory=True)
        root, path = linked, "pdfs/PRIVATE.pdf"
    elif kind == "fifo":
        os.mkfifo(root / path)
    elif kind == "directory":
        (root / path).mkdir()
    with pytest.raises(AuditError, match="^(invalid_data_root|pdf_read_failed)$"):
        api("extract_pdf_text")(root, path, digest)


@pytest.mark.parametrize(
    ("content", "digest", "error"),
    [
        (b"%PDF-1.7\ninvalid", None, "pdf_parse_failed"),
        (b"private no header", None, "pdf_invalid_header"),
        (b"%PDF-1.7\ninvalid", "0" * 64, "pdf_hash_mismatch"),
    ],
)
def test_snapshot_checks_precede_parsing(
    tmp_path: Path, content: bytes, digest: str | None, error: str
) -> None:
    root, file, _ = source(tmp_path, ["text"])
    file.write_bytes(content)
    with pytest.raises(AuditError, match=f"^{error}$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest or sha256(content).hexdigest())


@pytest.mark.parametrize(
    ("pages", "kwargs", "error"),
    [
        (["", "   "], {}, "no_extractable_text"),
        (["first", "second"], {"max_pages": 1}, "pdf_page_limit_exceeded"),
        (["first", "second"], {"max_text_characters": 10}, "pdf_text_limit_exceeded"),
        (["first"], {"max_pdf_bytes": 10}, "pdf_byte_limit_exceeded"),
        (["first"], {"max_output_bytes": 20}, "pdf_output_limit_exceeded"),
    ],
)
def test_real_subprocess_rejects_whole_results_at_limits(
    tmp_path: Path, pages: list[str], kwargs: dict, error: str
) -> None:
    root, _, digest = source(tmp_path, pages)
    limits = api("PdfLimits")(**kwargs)
    with pytest.raises(AuditError, match=f"^{error}$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest, limits=limits)


def test_encrypted_pdf_is_rejected_without_password_attempt(tmp_path: Path) -> None:
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter

    root, file, _ = source(tmp_path, ["private"])
    writer = PdfWriter(clone_from=PdfReader(file))
    writer.encrypt("private password")
    output = BytesIO()
    writer.write(output)
    file.write_bytes(output.getvalue())
    with pytest.raises(AuditError, match="^pdf_encrypted$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", sha256(output.getvalue()).hexdigest())


@pytest.mark.parametrize(
    ("quote", "page", "error"),
    [
        ("", None, "invalid_quote"),
        ("   ", None, "invalid_quote"),
        ("\ud800", None, "invalid_quote"),
        ("missing", None, "quote_not_found"),
        ("first\n\f\nsecond", None, "quote_crosses_page"),
        ("first", 0, "invalid_page_number"),
        ("first", True, "invalid_page_number"),
        ("first", 1.0, "invalid_page_number"),
        ("first", 3, "invalid_page_number"),
        ("first", 2, "quote_not_found"),
        ("é", None, "quote_not_found"),
    ],
)
def test_quote_is_exact_valid_and_contained_in_one_page(
    tmp_path: Path, quote: str, page: object, error: str
) -> None:
    root, _, digest = source(tmp_path, ["first", "second e\u0301"])
    representation = api("to_pdf_representation")(
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest),
        document_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        representation_id=UUID("22222222-2222-4222-8222-222222222222"),
    )
    with pytest.raises(AuditError, match=f"^{error}$"):
        api("locate_pdf_quote")(representation, quote, page_number=page)


def test_whitespace_only_pages_keep_every_character_and_separator(tmp_path: Path) -> None:
    root, _, digest = source(tmp_path, ["start", " \n\f\n ", "", "last"])
    result = api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    assert result.text == "start\n\f\n \n\f\n \n\f\n\n\f\nlast"
    assert result.empty_pages == (2, 3)
    assert [(p.page_number, p.start, p.end) for p in result.pages] == [(1, 0, 5), (4, 19, 23)]


@pytest.mark.parametrize(
    "field",
    [
        "max_pdf_bytes",
        "max_pages",
        "max_text_characters",
        "timeout_seconds",
        "cpu_seconds",
        "max_address_space_bytes",
        "max_output_bytes",
    ],
)
@pytest.mark.parametrize("value", [True, 0, -1, "2", 1.5])
def test_every_pdf_limit_rejects_coercion(field: str, value: object) -> None:
    with pytest.raises(AuditError, match="^invalid_limits$"):
        api("PdfLimits")(**{field: value})


def test_text_limit_counts_page_separators_and_allows_exact_boundary(tmp_path: Path) -> None:
    root, _, digest = source(tmp_path, ["a", "b"])
    result = api("extract_pdf_text")(
        root, "pdfs/PRIVATE.pdf", digest, limits=api("PdfLimits")(max_text_characters=5)
    )
    assert result.text == "a\n\f\nb"
    with pytest.raises(AuditError, match="^pdf_text_limit_exceeded$"):
        api("extract_pdf_text")(
            root, "pdfs/PRIVATE.pdf", digest, limits=api("PdfLimits")(max_text_characters=4)
        )


def test_overlapping_matches_are_ambiguous_even_on_one_page(tmp_path: Path) -> None:
    root, _, digest = source(tmp_path, ["aaa"])
    representation = api("to_pdf_representation")(
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest),
        document_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        representation_id=UUID("22222222-2222-4222-8222-222222222222"),
    )
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("locate_pdf_quote")(representation, "aa", page_number=1)


def test_adapter_requires_caller_uuid4_identities(tmp_path: Path) -> None:
    from pydantic import ValidationError

    root, _, digest = source(tmp_path, ["text"])
    extraction = api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    with pytest.raises(ValidationError):
        api("to_pdf_representation")(
            extraction,
            document_version_id=UUID("11111111-1111-1111-8111-111111111111"),
            representation_id=UUID("22222222-2222-4222-8222-222222222222"),
        )
