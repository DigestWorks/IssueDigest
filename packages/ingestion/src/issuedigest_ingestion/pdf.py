"""Bounded local PDF snapshots and exact, unevaluated citation preparation."""

import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass, fields
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from issuedigest_domain.citations import PdfQuoteSelector
from issuedigest_domain.sources import PageSpan, ParsedRepresentation
from pydantic import ValidationError

from .errors import AuditError
from .filesystem import DIRECTORY_FLAGS, identity, open_directory

SEPARATOR = "\n\f\n"
PARSER_VERSION = "6.20.1"
PROFILE = "pypdf-plain-v1"
SUMMARY_FORMAT = "issuedigest-pdf-text-summary-v1"
_WORKER_ERRORS = frozenset(
    {
        "pdf_parse_failed",
        "pdf_encrypted",
        "no_extractable_text",
        "pdf_page_limit_exceeded",
        "pdf_text_limit_exceeded",
        "pdf_invalid_unicode",
    }
)


@dataclass(frozen=True)
class PdfLimits:
    max_pdf_bytes: int = 128 * 1024 * 1024
    max_pages: int = 200
    max_text_characters: int = 1_000_000
    timeout_seconds: int = 30
    cpu_seconds: int = 30
    max_address_space_bytes: int = 512 * 1024 * 1024
    max_output_bytes: int = 16 * 1024 * 1024

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value <= 0:
                raise AuditError("invalid_limits")


_DEFAULT_LIMITS = PdfLimits()


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class PdfExtraction:
    text: str
    pages: tuple[PageSpan, ...]
    empty_pages: tuple[int, ...]
    page_count: int
    raw_sha256: str
    raw_bytes: int
    text_sha256: str
    parser_name: str = "pypdf"
    parser_version: str = PARSER_VERSION
    normalization_profile: str = PROFILE

    def __post_init__(self) -> None:
        try:
            if (
                type(self.text) is not str
                or not self.text.strip()
                or not _hash(self.raw_sha256)
                or not _hash(self.text_sha256)
                or type(self.raw_bytes) is not int
                or self.raw_bytes <= 0
                or type(self.page_count) is not int
                or self.page_count <= 0
                or type(self.pages) is not tuple
                or type(self.empty_pages) is not tuple
                or self.parser_name != "pypdf"
                or self.parser_version != PARSER_VERSION
                or self.normalization_profile != PROFILE
                or hashlib.sha256(self.text.encode("utf-8")).hexdigest() != self.text_sha256
            ):
                raise ValueError
            # Validate models again rather than accepting construction/copy bypasses.
            pages = tuple(PageSpan.model_validate(p.model_dump()) for p in self.pages)
            if pages != self.pages:
                raise ValueError
            numbers = tuple(p.page_number for p in pages)
            if numbers != tuple(sorted(set(numbers))):
                raise ValueError
            if any(type(p) is not int for p in self.empty_pages):
                raise ValueError
            if self.empty_pages != tuple(sorted(set(self.empty_pages))):
                raise ValueError
            if set(numbers) & set(self.empty_pages):
                raise ValueError
            if sorted((*numbers, *self.empty_pages)) != list(range(1, self.page_count + 1)):
                raise ValueError
            previous_end = 0
            previous_number = 0
            for page in pages:
                if page.start < previous_end or page.end > len(self.text):
                    raise ValueError
                if not self.text[page.start : page.end].strip():
                    raise ValueError
                gap = self.text[previous_end : page.start]
                separators = page.page_number - max(previous_number, 1)
                if (
                    gap.strip()
                    or gap.count(SEPARATOR) < separators
                    or (separators and not gap.endswith(SEPARATOR))
                    or (previous_number and not gap.startswith(SEPARATOR))
                ):
                    raise ValueError
                previous_end, previous_number = page.end, page.page_number
            tail = self.text[previous_end:]
            trailing_pages = self.page_count - previous_number
            if (
                tail.strip()
                or tail.count(SEPARATOR) < trailing_pages
                or (trailing_pages and not tail.startswith(SEPARATOR))
            ):
                raise ValueError
        except (ValueError, UnicodeError, AttributeError, TypeError, ValidationError):
            raise AuditError("pdf_invalid_result") from None


def _path_parts(pdf_path: str) -> tuple[str, ...]:
    if (
        not isinstance(pdf_path, str)
        or "\x00" in pdf_path
        or "\\" in pdf_path
        or pdf_path.startswith("/")
    ):
        raise AuditError("invalid_pdf_path")
    parts = tuple(pdf_path.split("/"))
    if len(parts) < 2 or parts[0] != "pdfs" or any(p in {"", ".", ".."} for p in parts):
        raise AuditError("invalid_pdf_path")
    return parts


def _snapshot(
    root: Path, parts: tuple[str, ...], expected: str, limits: PdfLimits, destination: BinaryIO
) -> tuple[str, int]:
    """Copy bounded chunks through read-only descriptors; check path and file changes."""
    directories: list[int] = []
    ancestry: list[tuple[int, str, os.stat_result]] = []
    source_fd: int | None = None
    try:
        try:
            directories.append(open_directory(root))
        except (OSError, ValueError):
            raise AuditError("invalid_data_root") from None
        try:
            for part in parts[:-1]:
                parent = directories[-1]
                child = os.open(part, DIRECTORY_FLAGS, dir_fd=parent)
                directories.append(child)
                ancestry.append((parent, part, os.fstat(child)))
            parent = directories[-1]
            source_fd = os.open(
                parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=parent,
            )
            before = os.fstat(source_fd)
            if not stat.S_ISREG(before.st_mode):
                raise AuditError("pdf_read_failed")
            if before.st_size > limits.max_pdf_bytes:
                raise AuditError("pdf_byte_limit_exceeded")
            digest = hashlib.sha256()
            size = 0
            header = bytearray()
            while chunk := os.read(source_fd, min(64 * 1024, limits.max_pdf_bytes - size + 1)):
                size += len(chunk)
                if size > limits.max_pdf_bytes:
                    raise AuditError("pdf_byte_limit_exceeded")
                digest.update(chunk)
                destination.write(chunk)
                if len(header) < 1024:
                    header.extend(chunk[: 1024 - len(header)])
            after = os.fstat(source_fd)
            try:
                current = os.stat(parts[-1], dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                raise AuditError("pdf_changed") from None
            if (
                identity(before) != identity(after)
                or identity(before) != identity(current)
                or size != before.st_size
            ):
                raise AuditError("pdf_changed")
            for ancestor_fd, name, previous in ancestry:
                now = os.stat(name, dir_fd=ancestor_fd, follow_symlinks=False)
                if (now.st_dev, now.st_ino, now.st_mode) != (
                    previous.st_dev,
                    previous.st_ino,
                    previous.st_mode,
                ):
                    raise AuditError("pdf_changed")
            actual = digest.hexdigest()
            if actual != expected:
                raise AuditError("pdf_hash_mismatch")
            if b"%PDF-" not in header:
                raise AuditError("pdf_invalid_header")
            destination.flush()
            destination.seek(0)
            return actual, size
        except OSError:
            raise AuditError("pdf_read_failed") from None
    finally:
        if source_fd is not None:
            os.close(source_fd)
        for fd in reversed(directories):
            os.close(fd)


def _worker_command(input_fd: int, output_fd: int, limits: PdfLimits) -> list[str]:
    # A script entrypoint avoids package/domain/PDF imports before applying rlimits.
    return [
        sys.executable,
        str(Path(__file__).with_name("_pdf_worker.py")),
        str(input_fd),
        str(output_fd),
        str(limits.max_pages),
        str(limits.max_text_characters),
        str(limits.cpu_seconds),
        str(limits.max_address_space_bytes),
        str(limits.max_output_bytes),
    ]


def _run_worker(snapshot: BinaryIO, output: BinaryIO, limits: PdfLimits) -> None:
    try:
        with subprocess.Popen(
            _worker_command(snapshot.fileno(), output.fileno(), limits),
            pass_fds=(snapshot.fileno(), output.fileno()),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        ) as process:
            try:
                code = process.wait(timeout=limits.timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise AuditError("pdf_timeout") from None
            if code == 3 or code == -signal.SIGXFSZ:
                raise AuditError("pdf_output_limit_exceeded")
            if code != 0:
                raise AuditError("pdf_worker_failed")
    except (OSError, ValueError, OverflowError):
        raise AuditError("pdf_worker_failed") from None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _decode_result(
    output: BinaryIO, limits: PdfLimits, raw_hash: str, raw_bytes: int
) -> PdfExtraction:
    if os.fstat(output.fileno()).st_size > limits.max_output_bytes:
        raise AuditError("pdf_output_limit_exceeded")
    output.seek(0)
    try:
        data = json.loads(
            output.read(limits.max_output_bytes + 1), object_pairs_hook=_unique_object
        )
        if not isinstance(data, dict):
            raise ValueError
        if data.get("status") == "failed":
            error = data.get("error")
            if set(data) != {"status", "error"} or error not in _WORKER_ERRORS:
                raise ValueError
            raise AuditError(str(error))
        if set(data) != {
            "status",
            "text",
            "page_texts",
            "pages",
            "empty_pages",
            "page_count",
            "text_sha256",
            "parser_name",
            "parser_version",
            "normalization_profile",
        }:
            raise ValueError
        if data["status"] != "completed":
            raise ValueError
        count = data["page_count"]
        if type(count) is not int or not 0 < count <= limits.max_pages:
            raise ValueError
        text = data["text"]
        if type(text) is not str or len(text) > limits.max_text_characters:
            raise ValueError
        if not isinstance(data["pages"], list) or not isinstance(data["empty_pages"], list):
            raise ValueError
        pages = tuple(PageSpan.model_validate(item) for item in data["pages"])
        page_texts = data["page_texts"]
        if (
            not isinstance(page_texts, list)
            or len(page_texts) != count
            or any(type(part) is not str for part in page_texts)
            or SEPARATOR.join(page_texts) != text
        ):
            raise ValueError
        expected_pages: list[PageSpan] = []
        expected_empty: list[int] = []
        offset = 0
        for number, part in enumerate(page_texts, 1):
            end = offset + len(part)
            if part.strip():
                expected_pages.append(PageSpan(page_number=number, start=offset, end=end))
            else:
                expected_empty.append(number)
            offset = end + len(SEPARATOR)
        if pages != tuple(expected_pages) or data["empty_pages"] != expected_empty:
            raise ValueError
        return PdfExtraction(
            text=text,
            pages=pages,
            empty_pages=tuple(data["empty_pages"]),
            page_count=count,
            raw_sha256=raw_hash,
            raw_bytes=raw_bytes,
            text_sha256=data["text_sha256"],
            parser_name=data["parser_name"],
            parser_version=data["parser_version"],
            normalization_profile=data["normalization_profile"],
        )
    except (ValueError, UnicodeError, TypeError, ValidationError, RecursionError):
        raise AuditError("pdf_invalid_result") from None


def extract_pdf_text(
    data_root: str | Path,
    pdf_path: str,
    expected_sha256: str,
    *,
    limits: PdfLimits = _DEFAULT_LIMITS,
) -> PdfExtraction:
    """Extract a verified local snapshot, without establishing source authenticity."""
    if sys.platform != "linux":
        raise AuditError("unsupported_platform")
    if not isinstance(limits, PdfLimits):
        raise AuditError("invalid_limits")
    if not _hash(expected_sha256):
        raise AuditError("invalid_expected_sha256")
    parts = _path_parts(pdf_path)
    try:
        root = Path(data_root)
        with tempfile.TemporaryFile("w+b") as snapshot, tempfile.TemporaryFile("w+b") as output:
            raw_hash, size = _snapshot(root, parts, expected_sha256, limits, snapshot)
            _run_worker(snapshot, output, limits)
            return _decode_result(output, limits, raw_hash, size)
    except (OSError, ValueError, TypeError):
        raise AuditError("pdf_read_failed") from None


def to_pdf_representation(
    extraction: PdfExtraction, *, document_version_id: UUID, representation_id: UUID
) -> ParsedRepresentation:
    """Consume the existing model with caller-owned UUID4 identities and no geometry."""
    return ParsedRepresentation(
        representation_id=representation_id,
        document_version_id=document_version_id,
        parser_name=extraction.parser_name,
        parser_version=extraction.parser_version,
        normalization_profile=extraction.normalization_profile,
        text=extraction.text,
        text_sha256=extraction.text_sha256,
        pages=extraction.pages,
        tables=(),
    )


def locate_pdf_quote(
    representation: ParsedRepresentation, quote: str, *, page_number: int | None = None
) -> PdfQuoteSelector:
    """Locate exactly one occurrence contained in one real page; support is unevaluated."""
    try:
        if not isinstance(quote, str) or not quote.strip():
            raise ValueError
        quote.encode("utf-8")
    except (ValueError, UnicodeError):
        raise AuditError("invalid_quote") from None
    pages = representation.pages
    if page_number is not None:
        if type(page_number) is not int or page_number <= 0:
            raise AuditError("invalid_page_number")
        page = next((p for p in pages if p.page_number == page_number), None)
        if page is None:
            raise AuditError("invalid_page_number")
        pages = (page,)
    start_bound = pages[0].start if page_number is not None else 0
    end_bound = pages[0].end if page_number is not None else len(representation.text)
    start = representation.text.find(quote, start_bound, end_bound)
    if start == -1:
        raise AuditError("quote_not_found")
    if representation.text.find(quote, start + 1, end_bound) != -1:
        raise AuditError("quote_ambiguous")
    end = start + len(quote)
    page = next((p for p in pages if p.start <= start and end <= p.end), None)
    if page is None:
        raise AuditError("quote_crosses_page")
    return PdfQuoteSelector(
        start=start, end=end, quote=quote, page_number=page.page_number, regions=()
    )
