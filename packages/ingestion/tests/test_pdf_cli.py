import json
from pathlib import Path

import pytest
from issuedigest_ingestion.cli import main
from pdf_fixtures import source


def test_inspect_pdf_aggregate_privacy(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    root, file, digest = source(tmp_path, ["PRIVATE 한글😀", "", "last"])
    code = main(
        [
            "inspect-pdf",
            "--data-root",
            str(root),
            "--pdf-path",
            "pdfs/PRIVATE.pdf",
            "--expected-sha256",
            digest,
        ]
    )
    out, err = capsys.readouterr()
    assert code == 0
    assert json.loads(out) == {
        "format_version": "issuedigest-pdf-text-summary-v1",
        "status": "completed",
        "page_count": 3,
        "empty_page_count": 1,
        "text_characters": 21,
        "raw_bytes": file.stat().st_size,
        "source_verification": "not_evaluated",
    }
    assert err == ""
    for secret in [digest, str(root), "PRIVATE", "한글"]:
        assert secret not in out


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--data-root"],
        [
            "--data-root",
            "/private/missing",
            "--pdf-path",
            "pdfs/a.pdf",
            "--expected-sha256",
            "0" * 64,
        ],
        [
            "--data-root",
            "/private/missing",
            "--pdf-path",
            "pdfs/a.pdf",
            "--expected-sha256",
            "0" * 64,
            "--max-pages",
            "0",
        ],
        ["--unknown", "PRIVATE"],
    ],
)
def test_inspect_errors_preserve_safe_pdf_format(
    extra: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["inspect-pdf", *extra])
    out, err = capsys.readouterr()
    assert code == 2
    assert json.loads(out)["format_version"] == "issuedigest-pdf-text-summary-v1"
    assert json.loads(out)["status"] == "failed"
    assert set(json.loads(out)) == {"format_version", "status", "error"}
    assert "private" not in out.lower()
    assert err == ""


def test_pdf_private_manifest_uses_safe_existing_saver(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import stat

    root, _, digest = source(tmp_path, ["PRIVATE 한글😀"])
    destination = tmp_path / "private.json"
    args = [
        "inspect-pdf",
        "--data-root",
        str(root),
        "--pdf-path",
        "pdfs/PRIVATE.pdf",
        "--expected-sha256",
        digest,
        "--private-manifest",
        str(destination),
    ]
    assert main(args) == 0
    capsys.readouterr()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    data = json.loads(destination.read_text())
    assert data["format_version"] == "issuedigest-pdf-text-manifest-v1"
    assert data["extraction"]["text"] == "PRIVATE 한글😀"
    assert data["extraction"]["raw_sha256"] == digest
    assert data["extraction"]["pages"] == [{"page_number": 1, "start": 0, "end": 11}]
    before = destination.read_bytes()
    assert main(args) == 2
    out, err = capsys.readouterr()
    assert json.loads(out) == {
        "format_version": "issuedigest-pdf-text-summary-v1",
        "status": "failed",
        "error": "manifest_failed",
    }
    assert err == ""
    assert destination.read_bytes() == before


def test_private_pdf_manifest_is_not_created_inside_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root, _, digest = source(tmp_path, ["text"])
    assert (
        main(
            [
                "inspect-pdf",
                "--data-root",
                str(root),
                "--pdf-path",
                "pdfs/PRIVATE.pdf",
                "--expected-sha256",
                digest,
                "--private-manifest",
                str(root / "output.json"),
            ]
        )
        == 2
    )
    assert json.loads(capsys.readouterr().out)["error"] == "manifest_failed"
    assert not (root / "output.json").exists()
