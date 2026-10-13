"""Faults use real subprocesses and temporary files at the private worker boundary."""

import importlib
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest
from issuedigest_domain.sources import PageSpan, ParsedRepresentation
from issuedigest_ingestion import AuditError
from pdf_fixtures import source
from test_pdf_text import api


def test_unique_quote_rejects_a_second_match_crossing_a_page_boundary() -> None:
    text = "A\n\f\nB A\n\f\nB"
    representation = ParsedRepresentation(
        document_version_id="11111111-1111-4111-8111-111111111111",
        representation_id="22222222-2222-4222-8222-222222222222",
        parser_name="pypdf",
        parser_version="6.20.1",
        normalization_profile="pypdf-plain-v1",
        text=text,
        text_sha256=sha256(text.encode()).hexdigest(),
        tables=(),
        pages=(PageSpan(page_number=1, start=0, end=7), PageSpan(page_number=2, start=10, end=11)),
    )
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        api("locate_pdf_quote")(representation, "A\n\f\nB")
    scoped = api("locate_pdf_quote")(representation, "A\n\f\nB", page_number=1)
    assert (scoped.start, scoped.end) == (0, 5)


@pytest.mark.parametrize("mutation", ["append", "replace", "delete"])
def test_source_changes_before_snapshot_completion_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    root, file, digest = source(tmp_path, ["text"])
    original_read = os.read
    changed = False

    def read_and_change(fd: int, size: int) -> bytes:
        nonlocal changed
        data = original_read(fd, size)
        if data and not changed:
            changed = True
            if mutation == "append":
                with file.open("ab") as output:
                    output.write(b"changed")
            elif mutation == "replace":
                replacement = file.with_name("replacement")
                replacement.write_bytes(file.read_bytes())
                replacement.replace(file)
            else:
                file.unlink()
        return data

    monkeypatch.setattr(os, "read", read_and_change)
    with pytest.raises(AuditError, match="^pdf_changed$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)


def inject_child(monkeypatch: pytest.MonkeyPatch, script: str) -> list[subprocess.Popen]:
    module = importlib.import_module("issuedigest_ingestion.pdf")
    original = module.subprocess.Popen
    children = []

    def launch(command: list[str], **kwargs):
        child = original([sys.executable, "-c", script, command[2], command[3]], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(module.subprocess, "Popen", launch)
    return children


@pytest.mark.parametrize(
    ("script", "error"),
    [
        ("import time; time.sleep(60)", "pdf_timeout"),
        ("import os; os._exit(7)", "pdf_worker_failed"),
        ('import os,sys; os.write(int(sys.argv[2]), b"x" * 1025)', "pdf_output_limit_exceeded"),
        (
            'import os,sys; os.write(int(sys.argv[2]), b"not JSON private exception")',
            "pdf_invalid_result",
        ),
    ],
)
def test_fault_child_is_reaped_and_returns_fixed_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, script: str, error: str
) -> None:
    api("extract_pdf_text")
    root, file, digest = source(tmp_path, ["text"])
    before = file.read_bytes()
    children = inject_child(monkeypatch, script)
    with pytest.raises(AuditError, match=f"^{error}$"):
        api("extract_pdf_text")(
            root,
            "pdfs/PRIVATE.pdf",
            digest,
            limits=api("PdfLimits")(timeout_seconds=1, max_output_bytes=1024),
        )
    assert len(children) == 1
    with pytest.raises(ChildProcessError):
        os.waitpid(children[0].pid, os.WNOHANG)
    assert file.read_bytes() == before


def worker_data() -> dict:
    return {
        "status": "completed",
        "text": "first\n\f\n\n\f\nlast",
        "page_count": 3,
        "empty_pages": [2],
        "page_texts": ["first", "", "last"],
        "pages": [
            {"page_number": 1, "start": 0, "end": 5},
            {"page_number": 3, "start": 11, "end": 15},
        ],
        "text_sha256": "6b533bb04f59916c481c506470a9ea7bae6fbb571a386b30a67ceff20a8fa4ae",
        "parser_name": "pypdf",
        "parser_version": "6.20.1",
        "normalization_profile": "pypdf-plain-v1",
    }


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("text_sha256", "0" * 64),
        ("page_count", True),
        ("page_count", 201),
        ("empty_pages", [1, 2]),
        ("empty_pages", [True]),
        ("pages", []),
        (
            "pages",
            [{"page_number": 1, "start": 1, "end": 5}, {"page_number": 3, "start": 11, "end": 15}],
        ),
        (
            "pages",
            [{"page_number": 3, "start": 11, "end": 15}, {"page_number": 1, "start": 0, "end": 5}],
        ),
        ("text", "first---\n\f\nlast"),
        ("text", "\ud800"),
        ("parser_version", "other"),
        ("parser_name", "other"),
        ("normalization_profile", "other"),
        ("status", "other"),
        ("extra", "private"),
    ],
)
def test_parent_validates_worker_content_hash_types_pages_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, key: str, value: object
) -> None:
    api("extract_pdf_text")
    data = worker_data()
    data[key] = value
    payload = json.dumps(data).encode()
    script = f"import os,sys; os.write(int(sys.argv[2]), {payload!r})"
    root, _, digest = source(tmp_path, ["first", "", "last"])
    inject_child(monkeypatch, script)
    with pytest.raises(AuditError, match="^pdf_invalid_result$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)


@pytest.mark.parametrize(
    "payload",
    [
        b'{"status":"failed","error":"PRIVATE exception"}',
        b'{"status":"failed","error":[]}',
        b'{"status":"failed","error":"pdf_parse_failed","private":"body"}',
        b'{"status":"completed","status":"completed"}',
        b"\xff",
        b"[]",
    ],
)
def test_parent_does_not_accept_untrusted_protocol_errors_or_duplicate_fields(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: bytes
) -> None:
    api("extract_pdf_text")
    root, _, digest = source(tmp_path, ["text"])
    inject_child(monkeypatch, f"import os,sys; os.write(int(sys.argv[2]), {payload!r})")
    with pytest.raises(AuditError, match="^pdf_invalid_result$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)


def test_snapshot_and_worker_fds_close_on_success_and_failure(tmp_path: Path) -> None:
    root, _, digest = source(tmp_path, ["text"])
    before = set(os.listdir("/proc/self/fd"))
    api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    with pytest.raises(AuditError, match="^pdf_hash_mismatch$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", "0" * 64)
    assert set(os.listdir("/proc/self/fd")) == before


def test_parent_accepts_the_complete_valid_protocol_control(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, digest = source(tmp_path, ["first", "", "last"])
    payload = json.dumps(worker_data()).encode()
    inject_child(monkeypatch, f"import os,sys; os.write(int(sys.argv[2]), {payload!r})")
    result = api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    assert result.text == "first\n\f\n\n\f\nlast"
    assert [(p.page_number, p.start, p.end) for p in result.pages] == [(1, 0, 5), (3, 11, 15)]


def wrap_real_worker(monkeypatch: pytest.MonkeyPatch, after_pdf_import: str) -> None:
    module = importlib.import_module("issuedigest_ingestion.pdf")
    original = module._worker_command
    script = (
        """import builtins, runpy, sys
original_import = builtins.__import__
def import_pdf(name, globals=None, locals=None, fromlist=(), level=0):
    module = original_import(name, globals, locals, fromlist, level)
    if name == 'pypdf' and 'PdfReader' in fromlist:
"""
        + "".join("        " + line + "\n" for line in after_pdf_import.splitlines())
        + """    return module
builtins.__import__ = import_pdf
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
"""
    )

    def command(input_fd, output_fd, limits):
        return [sys.executable, "-c", script, *original(input_fd, output_fd, limits)[1:]]

    monkeypatch.setattr(module, "_worker_command", command)


def test_encryption_is_rejected_before_pypdf_attempts_even_empty_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter

    root, file, _ = source(tmp_path, ["private"])
    writer = PdfWriter(clone_from=PdfReader(file))
    writer.encrypt("")
    buffer = BytesIO()
    writer.write(buffer)
    file.write_bytes(buffer.getvalue())
    marker = tmp_path / "password-attempt"
    wrap_real_worker(
        monkeypatch,
        f"""from pathlib import Path
original_verify = sys.modules['pypdf._encryption'].Encryption.verify
def verify(self, *args, **kwargs):
    Path({str(marker)!r}).write_text('attempted')
    return original_verify(self, *args, **kwargs)
sys.modules['pypdf._encryption'].Encryption.verify = verify""",
    )
    with pytest.raises(AuditError, match="^pdf_encrypted$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", sha256(buffer.getvalue()).hexdigest())
    assert not marker.exists(), "encrypted inputs must never attempt even an empty password"


def test_worker_has_all_resource_limits_before_first_pdf_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _, digest = source(tmp_path, ["text"])
    marker = tmp_path / "limits.json"
    wrap_real_worker(
        monkeypatch,
        f"""import resource, json
from pathlib import Path
Path({str(marker)!r}).write_text(json.dumps([
    resource.getrlimit(resource.RLIMIT_CPU), resource.getrlimit(resource.RLIMIT_AS),
    resource.getrlimit(resource.RLIMIT_FSIZE), resource.getrlimit(resource.RLIMIT_CORE)]))""",
    )
    result = api("extract_pdf_text")(
        root,
        "pdfs/PRIVATE.pdf",
        digest,
        limits=api("PdfLimits")(
            cpu_seconds=2, max_address_space_bytes=256 * 1024 * 1024, max_output_bytes=4096
        ),
    )
    assert result.text == "text"
    assert json.loads(marker.read_text()) == [[2, 2], [268435456, 268435456], [4096, 4096], [0, 0]]


@pytest.mark.parametrize(
    ("fault", "error"),
    [
        ("while True: pass", "pdf_worker_failed"),
        ("bytearray(512 * 1024 * 1024)", "pdf_parse_failed"),
        ("return '\\ud800'", "pdf_invalid_unicode"),
    ],
)
def test_actual_worker_enforces_cpu_memory_and_unicode_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str, error: str
) -> None:
    root, _, digest = source(tmp_path, ["text"])
    wrap_real_worker(
        monkeypatch,
        f"""def extract(self, *args, **kwargs):
    {fault}
sys.modules['pypdf._page'].PageObject.extract_text = extract""",
    )
    with pytest.raises(AuditError, match=f"^{error}$"):
        api("extract_pdf_text")(
            root,
            "pdfs/PRIVATE.pdf",
            digest,
            limits=api("PdfLimits")(
                timeout_seconds=4, cpu_seconds=1, max_address_space_bytes=128 * 1024 * 1024
            ),
        )


def test_preparse_rejections_never_launch_worker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("issuedigest_ingestion.pdf")
    root, file, digest = source(tmp_path, ["text"])

    def unexpected(*args, **kwargs):
        raise AssertionError("unverified source must never reach a parser")

    monkeypatch.setattr(module.subprocess, "Popen", unexpected)
    with pytest.raises(AuditError, match="^pdf_hash_mismatch$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", "0" * 64)
    file.write_bytes(b"not PDF")
    with pytest.raises(AuditError, match="^pdf_invalid_header$"):
        api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", sha256(b"not PDF").hexdigest())
    assert digest != sha256(b"not PDF").hexdigest()


def test_worker_reads_verified_snapshot_if_original_changes_after_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("issuedigest_ingestion.pdf")
    original = module._worker_command
    root, file, digest = source(tmp_path, ["verified snapshot"])

    def command(input_fd, output_fd, limits):
        file.write_bytes(b"changed after snapshot")
        return original(input_fd, output_fd, limits)

    monkeypatch.setattr(module, "_worker_command", command)
    result = api("extract_pdf_text")(root, "pdfs/PRIVATE.pdf", digest)
    assert result.text == "verified snapshot"
    assert result.raw_sha256 == digest


def test_subprocess_stderr_and_warnings_are_never_public(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from issuedigest_ingestion.cli import main

    root, _, digest = source(tmp_path, ["text"])
    inject_child(
        monkeypatch,
        'import sys,warnings; print("PRIVATE",file=sys.stderr); '
        'warnings.warn("PRIVATE PDF BODY"); sys.exit(7)',
    )
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
            ]
        )
        == 2
    )
    out, err = capsys.readouterr()
    assert json.loads(out)["error"] == "pdf_worker_failed"
    assert err == ""
    assert "PRIVATE" not in out
