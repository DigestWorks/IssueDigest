"""Read-only file inspection; associations are never validated evidence."""

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from unicodedata import category
from urllib.parse import urlsplit

from .errors import AuditError
from .filesystem import Budget, FileRef, input_directories, read_file, scan


@dataclass(frozen=True)
class Limits:
    max_files: int = 10_000
    max_json_bytes: int = 8 * 1024 * 1024
    max_pdf_bytes: int = 128 * 1024 * 1024
    max_total_bytes: int = 2 * 1024 * 1024 * 1024

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value <= 0:
                raise AuditError("invalid_limits")


_DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class AuditResult:
    summary: dict[str, Any]
    manifest: dict[str, Any]


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _constant(value: str) -> None:
    raise ValueError("non-finite value")


def _metadata(data: dict[str, Any]) -> str | None:
    registration = data.get("registration_number")
    if not isinstance(registration, str) or not re.fullmatch(r"[0-9]{1,32}", registration):
        return "invalid_registration_number"
    url = data.get("source_url")
    if not isinstance(url, str) or any(c.isspace() or category(c) == "Cc" for c in url):
        return "invalid_source_url"
    try:
        split = urlsplit(url)
        if (
            split.scheme != "https"
            or split.hostname not in {"www.nesdc.go.kr", "nesdc.go.kr"}
            or split.netloc
            not in {"nesdc.go.kr", "www.nesdc.go.kr", "nesdc.go.kr:443", "www.nesdc.go.kr:443"}
            or split.username is not None
            or split.password is not None
            or split.port not in {None, 443}
            or "\\" in url
        ):
            return "invalid_source_url"
    except ValueError:
        return "invalid_source_url"
    reference = data.get("pdf_path")
    if (
        not isinstance(reference, str)
        or not reference
        or "\\" in reference
        or "\x00" in reference
        or ":" in reference
        or not PurePosixPath(reference).name
        or reference.endswith("/")
        or PurePosixPath(reference).is_absolute()
        or ".." in reference.split("/")
    ):
        return "invalid_pdf_reference"
    return None


def audit_poll_files(data_root: str | Path, *, limits: Limits = _DEFAULT_LIMITS) -> AuditResult:
    """Inspect explicit parsed/pdfs inputs and return public and private v1 reports."""
    started = datetime.now(UTC).isoformat()
    root = Path(data_root)
    try:
        with input_directories(root) as descriptors:
            found, skipped = scan(descriptors, limits.max_files)
            return _audit(found, skipped, descriptors, limits, started)
    except OSError:
        raise AuditError("read_failed") from None


def _audit(
    found: dict[str, list[FileRef]],
    skipped: list[dict[str, str]],
    descriptors: dict[str, int],
    limits: Limits,
    started: str,
) -> AuditResult:
    parsed = found["parsed"]
    pdf_paths = found["pdfs"]
    budget = Budget(limits.max_total_bytes)
    pdfs: list[dict[str, Any]] = []
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_hash: dict[str, list[str]] = defaultdict(list)
    for path in pdf_paths:
        header, digest, size, reason = read_file(
            descriptors["pdfs"], path, limits.max_pdf_bytes, budget, json_content=False
        )
        if reason is not None:
            reason = "pdf_" + reason
        elif b"%PDF-" not in header:
            reason = "pdf_invalid_header"
        item: dict[str, Any] = {
            "path": path.path,
            "reason": reason,
            "size_bytes": size,
            "sha256": digest if reason is None else None,
        }
        pdfs.append(item)
        by_name[path.parts[-1]].append(item)
        if reason is None:
            by_hash[digest].append(item["path"])
    polls: list[dict[str, Any]] = []
    by_registration: dict[str, list[str]] = defaultdict(list)
    for path in parsed:
        content, _, _, read_reason = read_file(
            descriptors["parsed"], path, limits.max_json_bytes, budget, json_content=True
        )
        item = {"path": path.path, "status": "quarantined"}
        if read_reason:
            item["reason"] = "json_" + read_reason
            polls.append(item)
            continue
        try:
            data = json.loads(content, object_pairs_hook=_object, parse_constant=_constant)
        except (ValueError, UnicodeError, RecursionError):
            item["reason"] = "invalid_json"
            polls.append(item)
            continue
        if not isinstance(data, dict) or "registration_number" not in data:
            item.update(status="unsupported", reason="unsupported_json")
            polls.append(item)
            continue
        reason = _metadata(data)
        registration = data.get("registration_number")
        if isinstance(registration, str) and re.fullmatch(r"[0-9]{1,32}", registration):
            by_registration[registration].append(item["path"])
        if reason is None:
            item.update(
                registration_number=registration,
                source_url=data["source_url"],
                pdf_reference=data["pdf_path"],
            )
            matches = by_name[PurePosixPath(data["pdf_path"]).name]
            if not matches:
                reason = "pdf_missing"
            elif len(matches) > 1:
                reason = "pdf_ambiguous"
            else:
                pdf = matches[0]
                reason = pdf["reason"]
                if reason is None:
                    item.update(
                        status="candidate",
                        pdf_path=pdf["path"],
                        pdf_size_bytes=pdf["size_bytes"],
                        pdf_sha256=pdf["sha256"],
                    )
        item["reason"] = reason
        polls.append(item)
    counts = Counter(item["status"] for item in polls)
    reasons = Counter(item["reason"] for item in polls if item["reason"] is not None)
    duplicate_hashes = [
        {"sha256": key, "pdfs": value} for key, value in sorted(by_hash.items()) if len(value) > 1
    ]
    duplicate_registrations = [
        {"registration_number": key, "polls": value}
        for key, value in sorted(by_registration.items())
        if len(value) > 1
    ]
    summary = {
        "format_version": "issuedigest-ingestion-summary-v1",
        "status": "completed",
        "started_at": started,
        "completed_at": datetime.now(UTC).isoformat(),
        "scanned_files": {
            tree: len(found[tree]) + sum(item["path"].startswith(tree + "/") for item in skipped)
            for tree in ("parsed", "pdfs")
        },
        "skipped_files": len(skipped),
        "skipped_reasons": dict(sorted(Counter(item["reason"] for item in skipped).items())),
        "candidate": counts["candidate"],
        "quarantined": counts["quarantined"],
        "unsupported": counts["unsupported"],
        "reasons": dict(sorted(reasons.items())),
        "pdf_reasons": dict(sorted(Counter(p["reason"] for p in pdfs if p["reason"]).items())),
        "duplicate_hash_groups": len(duplicate_hashes),
        "duplicate_registration_groups": len(duplicate_registrations),
        "bytes_read": budget.used,
    }
    return AuditResult(
        summary,
        {
            "format_version": "issuedigest-ingestion-manifest-v1",
            "summary": summary,
            "polls": polls,
            "pdfs": pdfs,
            "skipped": skipped,
            "duplicate_hashes": duplicate_hashes,
            "duplicate_registrations": duplicate_registrations,
        },
    )
