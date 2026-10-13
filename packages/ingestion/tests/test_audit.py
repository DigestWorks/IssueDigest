import json
from pathlib import Path

import pytest
from issuedigest_ingestion import AuditError, Limits, audit_poll_files

PDF = b"%PDF-1.7\n"
# Independently derived with printf '%s\n' '%PDF-1.7' | sha256sum.
PDF_SHA = "0716f9264c9fe19f5d7455276107f3ddcc1d3497f63d60689a73558ae8a1bf5e"


@pytest.fixture
def root(tmp_path: Path) -> Path:
    path = tmp_path / "source"
    (path / "parsed").mkdir(parents=True)
    (path / "pdfs").mkdir()
    return path


def poll(root: Path, name: str = "poll.json", **changes: object) -> Path:
    data: dict[str, object] = {
        "registration_number": "123",
        "source_url": "https://www.nesdc.go.kr/poll?id=123",
        "pdf_path": "pdfs/poll.pdf",
    }
    data.update(changes)
    path = root / "parsed" / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_candidate_has_full_size_and_independent_hash(root: Path) -> None:
    poll(root)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    result = audit_poll_files(root)
    assert result.summary.get("candidate") == 1
    candidate = result.manifest["polls"][0]
    assert candidate["status"] == "candidate"
    assert candidate["pdf_size_bytes"] == 9
    assert candidate["pdf_sha256"] == PDF_SHA
    assert result.summary["quarantined"] == 0
    assert result.summary["scanned_files"] == {"parsed": 1, "pdfs": 1}
    assert result.summary["format_version"] == "issuedigest-ingestion-summary-v1"
    assert result.summary["completed_at"] >= result.summary["started_at"]


def outcome(root: Path, *, limits: Limits | None = None) -> object:
    try:
        return audit_poll_files(root, limits=limits if limits is not None else Limits())
    except Exception as error:
        return error


@pytest.mark.parametrize(
    "reference,files,reason",
    [
        ("pdfs/missing.pdf", ["poll.pdf"], "pdf_missing"),
        ("poll.pdf", ["a/poll.pdf", "b/poll.pdf"], "pdf_ambiguous"),
        ("poll.pdf", ["poll.pdf"], "pdf_invalid_header"),
    ],
)
def test_pdf_association_quarantines(
    root: Path, reference: str, files: list[str], reason: str
) -> None:
    poll(root, pdf_path=reference)
    for name in files:
        path = root / "pdfs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"HTML" if reason == "pdf_invalid_header" else PDF)
    result = outcome(root)
    assert not isinstance(result, Exception), repr(type(result))
    assert result.summary.get("quarantined") == 1
    assert result.manifest["polls"][0]["reason"] == reason


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("registration_number", "", "invalid_registration_number"),
        ("registration_number", " 123", "invalid_registration_number"),
        ("registration_number", "１２３", "invalid_registration_number"),
        ("registration_number", "1" * 33, "invalid_registration_number"),
        ("registration_number", 123, "invalid_registration_number"),
        ("registration_number", True, "invalid_registration_number"),
        ("source_url", "http://www.nesdc.go.kr/", "invalid_source_url"),
        ("source_url", "https://nesdc.go.kr.evil/", "invalid_source_url"),
        ("source_url", "https://user@nesdc.go.kr/", "invalid_source_url"),
        ("source_url", "https://nesdc.go.kr:444/", "invalid_source_url"),
        ("source_url", "https://nesdc.go.kr:bad/", "invalid_source_url"),
        ("source_url", " https://nesdc.go.kr/", "invalid_source_url"),
        ("source_url", "https://nesdc.go.kr/\n", "invalid_source_url"),
        ("source_url", None, "invalid_source_url"),
        ("pdf_path", "../poll.pdf", "invalid_pdf_reference"),
        ("pdf_path", "pdfs/../poll.pdf", "invalid_pdf_reference"),
        ("pdf_path", "/poll.pdf", "invalid_pdf_reference"),
        ("pdf_path", "C:\\poll.pdf", "invalid_pdf_reference"),
        ("pdf_path", "poll.pdf\x00", "invalid_pdf_reference"),
        ("pdf_path", "https://elsewhere/poll.pdf", "invalid_pdf_reference"),
        ("pdf_path", None, "invalid_pdf_reference"),
        ("pdf_path", "", "invalid_pdf_reference"),
    ],
)
def test_invalid_poll_metadata_is_quarantined(
    root: Path, field: str, value: object, reason: str
) -> None:
    poll(root, **{field: value})
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    result = outcome(root)
    assert not isinstance(result, Exception), repr(type(result))
    assert result.summary.get("candidate") == 0
    assert result.manifest["polls"][0]["reason"] == reason


@pytest.mark.parametrize("data", [[], 123, "text", {}, {"questions": []}])
def test_other_json_shapes_are_unsupported(root: Path, data: object) -> None:
    (root / "parsed" / "other.json").write_text(json.dumps(data))
    result = outcome(root)
    assert not isinstance(result, Exception), repr(type(result))
    assert result.summary.get("unsupported") == 1
    assert result.manifest["polls"][0]["reason"] == "unsupported_json"


@pytest.mark.parametrize(
    "content",
    [b"{", b"\xff", b'{"registration_number":"1","registration_number":"2"}', b'{"x":NaN}'],
)
def test_invalid_json_is_quarantined(root: Path, content: bytes) -> None:
    (root / "parsed" / "broken.json").write_bytes(content)
    result = outcome(root)
    assert not isinstance(result, Exception), repr(type(result))
    assert result.manifest["polls"][0]["reason"] == "invalid_json"


@pytest.mark.parametrize("kind", ["json", "pdf"])
def test_individual_size_limits_quarantine(root: Path, kind: str) -> None:
    poll(root)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    limits = Limits(max_json_bytes=1) if kind == "json" else Limits(max_pdf_bytes=8)
    result = outcome(root, limits=limits)
    assert not isinstance(result, Exception), repr(type(result))
    assert result.manifest["polls"][0]["reason"] == f"{kind}_too_large"


@pytest.mark.parametrize(
    "limits,code",
    [
        (Limits(max_files=1), "file_limit_exceeded"),
        (Limits(max_total_bytes=1), "total_bytes_exceeded"),
    ],
)
def test_global_limits_abort(root: Path, limits: Limits, code: str) -> None:
    poll(root)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    result = outcome(root, limits=limits)
    assert isinstance(result, AuditError)
    assert str(result) == code


@pytest.mark.parametrize(
    "field", ["max_files", "max_json_bytes", "max_pdf_bytes", "max_total_bytes"]
)
@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "2", None])
def test_limit_values_reject_non_positive_integers(field: str, value: object) -> None:
    try:
        result: object = Limits(**{field: value})
    except Exception as error:
        result = error
    assert isinstance(result, AuditError)
    assert str(result) == "invalid_limits"


@pytest.mark.parametrize("missing", ["root", "parsed", "pdfs"])
def test_required_directories_missing_aborts(root: Path, missing: str) -> None:
    path = root if missing == "root" else root / missing
    if missing == "root":
        (root / "parsed").rmdir()
        (root / "pdfs").rmdir()
    path.rmdir()
    result = outcome(root)
    assert isinstance(result, AuditError)
    assert str(result) == "invalid_data_root"


def test_duplicate_groups_do_not_merge_polls(root: Path) -> None:
    poll(root, "a.json")
    poll(root, "b.json", source_url="https://nesdc.go.kr/other", pdf_path="different.pdf")
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    (root / "pdfs" / "different.pdf").write_bytes(PDF)
    result = audit_poll_files(root)
    assert result.summary.get("duplicate_hash_groups") == 1
    assert result.summary["duplicate_registration_groups"] == 1
    assert result.summary["candidate"] == 2
    assert len(result.manifest["polls"]) == 2
    assert len(result.manifest["duplicate_hashes"][0]["pdfs"]) == 2


def test_pdf_header_must_be_inside_first_1024_bytes(root: Path) -> None:
    poll(root)
    (root / "pdfs" / "poll.pdf").write_bytes(b"x" * 1024 + PDF)
    result = audit_poll_files(root)
    assert result.summary.get("candidate") == 0
    assert result.manifest["polls"][0]["reason"] == "pdf_invalid_header"


@pytest.mark.parametrize("tree", ["parsed", "pdfs"])
def test_symlink_and_fifo_are_never_read(root: Path, tree: str, tmp_path: Path) -> None:
    import os

    suffix = ".json" if tree == "parsed" else ".pdf"
    outside = tmp_path / ("outside" + suffix)
    outside.write_bytes(PDF if tree == "pdfs" else b'{"registration_number":"123"}')
    (root / tree / ("link" + suffix)).symlink_to(outside)
    (root / tree / "linked-directory").symlink_to(tmp_path, target_is_directory=True)
    result = outcome(root)
    assert not isinstance(result, Exception), repr(type(result))
    assert result.summary.get("skipped_files") == 2
    os.mkfifo(root / tree / ("pipe" + suffix))
    result = audit_poll_files(root)
    assert result.summary["skipped_files"] == 3
    assert result.summary["skipped_reasons"] == {"special_file": 1, "symlink": 2}
    assert result.summary["bytes_read"] == 0


@pytest.mark.parametrize("name", ["root", "parsed", "pdfs"])
def test_required_directory_symlink_is_rejected(root: Path, name: str, tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    if name == "root":
        link = tmp_path / "linked-root"
        link.symlink_to(root, target_is_directory=True)
        result = outcome(link)
    else:
        (root / name).rmdir()
        (root / name).symlink_to(target, target_is_directory=True)
        result = outcome(root)
    assert isinstance(result, AuditError)
    assert str(result) == "invalid_data_root"


def test_unrecognized_extensions_count_toward_file_limit(root: Path) -> None:
    (root / "parsed" / "a.txt").write_text("unused")
    (root / "pdfs" / "b.txt").write_text("unused")
    result = outcome(root, limits=Limits(max_files=1))
    assert isinstance(result, AuditError)
    assert str(result) == "file_limit_exceeded"


def test_pdf_change_during_read_quarantines_real_file(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import os

    poll(root)
    target = root / "pdfs" / "poll.pdf"
    target.write_bytes(PDF)
    original_read = os.read
    changed = False

    def changing_read(fd: int, size: int) -> bytes:
        nonlocal changed
        data = original_read(fd, size)
        if data.startswith(b"%PDF-") and not changed:
            changed = True
            target.write_bytes(PDF + b"changed")
        return data

    monkeypatch.setattr(os, "read", changing_read)
    result = audit_poll_files(root)
    assert result.summary.get("candidate") == 0
    assert result.manifest["polls"][0]["reason"] == "pdf_changed"


def test_pdf_is_hashed_with_bounded_chunks(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    poll(root)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF + b"x" * 200_000)
    original_read = os.read
    read_sizes = []

    def recording_read(fd: int, size: int) -> bytes:
        read_sizes.append(size)
        return original_read(fd, size)

    monkeypatch.setattr(os, "read", recording_read)
    result = audit_poll_files(root)
    assert result.summary["candidate"] == 1
    assert len(read_sizes) >= 5
    assert max(read_sizes) <= 64 * 1024


def test_os_read_failure_has_fixed_error(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    poll(root)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)

    def failed_read(fd: int, size: int) -> bytes:
        raise OSError("private/path https://secret.invalid body")

    monkeypatch.setattr(os, "read", failed_read)
    result = outcome(root)
    assert isinstance(result, AuditError)
    assert str(result) == "read_failed"


def test_directory_enumeration_failure_aborts(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    def failed_scan(fd: object) -> object:
        raise OSError("private enumeration error")

    monkeypatch.setattr(os, "scandir", failed_scan)
    result = outcome(root)
    assert isinstance(result, AuditError)
    assert str(result) == "read_failed"


def test_invalid_data_root_nul_returns_fixed_error() -> None:
    result = outcome(Path("private\x00root"))
    assert isinstance(result, AuditError)
    assert str(result) == "invalid_data_root"


def test_empty_pdf_basename_is_invalid_metadata(root: Path) -> None:
    poll(root, pdf_path=".")
    result = audit_poll_files(root)
    assert result.manifest["polls"][0]["reason"] == "invalid_pdf_reference"


def test_empty_url_port_is_invalid_metadata(root: Path) -> None:
    poll(root, source_url="https://nesdc.go.kr:/")
    result = audit_poll_files(root)
    assert result.manifest["polls"][0]["reason"] == "invalid_source_url"


@pytest.mark.parametrize(
    "control",
    ["\x00", "\x1f", "\x7f", "\x80", "\x9f"],
    ids=["c0-nul", "c0-unit-separator", "del", "c1-first", "c1-last"],
)
def test_source_url_control_characters_quarantine_poll(root: Path, control: str) -> None:
    poll(root, source_url="https://nesdc.go.kr/poll" + control)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    result = audit_poll_files(root)
    assert result.summary["candidate"] == 0
    assert result.summary["quarantined"] == 1
    assert result.manifest["polls"][0]["reason"] == "invalid_source_url"


@pytest.mark.parametrize(
    "url",
    [
        "https://nesdc.go.kr/poll",
        "https://www.nesdc.go.kr:443/poll",
        "https://nesdc.go.kr/조사",
        "https://nesdc.go.kr/poll\u00ff",
    ],
)
def test_source_url_noncontrol_characters_preserve_candidate(root: Path, url: str) -> None:
    poll(root, source_url=url)
    (root / "pdfs" / "poll.pdf").write_bytes(PDF)
    result = audit_poll_files(root)
    assert result.summary["candidate"] == 1
    assert result.summary["quarantined"] == 0
    assert result.manifest["polls"][0]["source_url"] == url
