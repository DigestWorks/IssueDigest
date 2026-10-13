import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from issuedigest_ingestion import AuditError, audit_poll_files
from issuedigest_ingestion.cli import main
from issuedigest_ingestion.reports import save_private_manifest


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "source"
    (path / "parsed").mkdir(parents=True)
    (path / "pdfs").mkdir()
    (path / "parsed" / "sensitive-name.json").write_text(
        json.dumps(
            {
                "registration_number": "987654321",
                "source_url": "https://www.nesdc.go.kr/private-source",
                "pdf_path": "sensitive-pdf.pdf",
                "questions": ["PRIVATE POLL TEXT"],
            }
        )
    )
    (path / "pdfs" / "sensitive-pdf.pdf").write_bytes(b"%PDF-1.7\n")
    return path


def test_cli_returns_aggregate_without_private_values(
    root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["audit-polls", "--data-root", str(root)])
    out, err = capsys.readouterr()
    assert code == 0
    assert json.loads(out).get("candidate") == 1
    assert err == ""
    for secret in [str(root), "sensitive", "987654321", "nesdc", "PRIVATE POLL TEXT", "0716f926"]:
        assert secret not in out


@pytest.mark.parametrize(
    "extra",
    [
        [],
        ["--data-root"],
        ["--data-root", "/private/missing"],
        ["--data-root", "/private/missing", "--max-files", "0"],
        ["--data-root", "/private/missing", "--max-total-bytes", "-1"],
        ["--data-root", "/private/missing", "--max-json-bytes", "True"],
        ["--data-root", "/private/missing", "--secret", "private-body"],
    ],
)
def test_cli_failures_are_fixed_json_exit2(
    extra: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["audit-polls", *extra])
    out, err = capsys.readouterr()
    assert code == 2
    response = json.loads(out)
    assert response["status"] == "failed"
    assert response["error"] in {"invalid_arguments", "invalid_data_root", "invalid_limits"}
    assert err == ""
    assert "private" not in out


def test_cli_limit_failure_does_not_create_manifest(
    root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    destination = tmp_path / "private.json"
    code = main(
        [
            "audit-polls",
            "--data-root",
            str(root),
            "--private-manifest",
            str(destination),
            "--max-files",
            "1",
        ]
    )
    out, _ = capsys.readouterr()
    assert code == 2
    assert json.loads(out)["error"] == "file_limit_exceeded"
    assert not destination.exists()


def test_private_manifest_is_exclusive_and_mode600(root: Path, tmp_path: Path) -> None:
    destination = tmp_path / "private.json"
    result = audit_poll_files(root)
    save_private_manifest(result, root, destination)
    assert destination.exists()
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    data = json.loads(destination.read_bytes())
    assert data["format_version"] == "issuedigest-ingestion-manifest-v1"
    assert data["polls"][0]["registration_number"] == "987654321"
    original = destination.read_bytes()
    with pytest.raises(AuditError, match="^manifest_failed$"):
        save_private_manifest(result, root, destination)
    assert destination.read_bytes() == original


@pytest.mark.parametrize(
    "location", ["inside", "parent_link_inside", "file_link", "parent_link_outside"]
)
def test_manifest_unsafe_locations_are_rejected(root: Path, tmp_path: Path, location: str) -> None:
    if location == "inside":
        destination = root / "private.json"
    elif location.startswith("parent_link"):
        target = root if location == "parent_link_inside" else tmp_path / "safe"
        target.mkdir(exist_ok=True)
        link = tmp_path / "linked"
        link.symlink_to(target, target_is_directory=True)
        destination = link / "private.json"
    else:
        destination = tmp_path / "private.json"
        destination.symlink_to(root / "parsed" / "sensitive-name.json")
    before = (root / "parsed" / "sensitive-name.json").read_bytes()
    try:
        result: object = save_private_manifest(audit_poll_files(root), root, destination)
    except Exception as error:
        result = error
    assert isinstance(result, AuditError)
    assert str(result) == "manifest_failed"
    assert (root / "parsed" / "sensitive-name.json").read_bytes() == before


def test_manifest_partial_write_is_removed(
    root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "private.json"
    original_write = os.write
    calls = 0

    def fail_after_partial(fd: int, content: bytes) -> int:
        nonlocal calls
        calls += 1
        if calls == 1:
            return original_write(fd, content[:5])
        raise OSError("private write error")

    monkeypatch.setattr(os, "write", fail_after_partial)
    try:
        result: object = save_private_manifest(audit_poll_files(root), root, destination)
    except Exception as error:
        result = error
    assert isinstance(result, AuditError)
    assert str(result) == "manifest_failed"
    assert not destination.exists()


def test_module_command_exits_two_with_safe_error() -> None:
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "issuedigest_ingestion",
            "audit-polls",
            "--data-root",
            "/private/missing",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert process.returncode == 2
    assert json.loads(process.stdout)["error"] == "invalid_data_root"
    assert process.stderr == ""
