"""Aggregate-only command line interface."""

import argparse
import json
import sys
from dataclasses import asdict
from typing import Never

from .audit import AuditResult, Limits, audit_poll_files
from .errors import AuditError
from .pdf import SUMMARY_FORMAT, PdfLimits, extract_pdf_text
from .reports import save_private_manifest


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuditError("invalid_arguments")


def main(argv: list[str] | None = None) -> int:
    """Return zero for a completed inspection, two for a fixed public error."""
    parser = _Parser(prog="issuedigest-ingestion")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)
    audit = commands.add_parser("audit-polls", help="Inspect unverified local poll candidates")
    audit.add_argument("--data-root", required=True)
    audit.add_argument("--private-manifest")
    audit.add_argument("--max-files", type=int, default=10_000)
    audit.add_argument("--max-json-bytes", type=int, default=8 * 1024 * 1024)
    audit.add_argument("--max-pdf-bytes", type=int, default=128 * 1024 * 1024)
    audit.add_argument("--max-total-bytes", type=int, default=2 * 1024 * 1024 * 1024)
    inspect = commands.add_parser("inspect-pdf", help="Extract unevaluated local PDF text")
    inspect.add_argument("--data-root", required=True)
    inspect.add_argument("--pdf-path", required=True)
    inspect.add_argument("--expected-sha256", required=True)
    inspect.add_argument("--private-manifest")
    inspect.add_argument("--max-pdf-bytes", type=int, default=128 * 1024 * 1024)
    inspect.add_argument("--max-pages", type=int, default=200)
    inspect.add_argument("--max-text-characters", type=int, default=1_000_000)
    inspect.add_argument("--timeout-seconds", type=int, default=30)
    arguments = sys.argv[1:] if argv is None else argv
    format_version = (
        SUMMARY_FORMAT if arguments[:1] == ["inspect-pdf"] else "issuedigest-ingestion-summary-v1"
    )
    code = 0
    try:
        args = parser.parse_args(argv)
        if args.command == "inspect-pdf":
            extraction = extract_pdf_text(
                args.data_root,
                args.pdf_path,
                args.expected_sha256,
                limits=PdfLimits(
                    max_pdf_bytes=args.max_pdf_bytes,
                    max_pages=args.max_pages,
                    max_text_characters=args.max_text_characters,
                    timeout_seconds=args.timeout_seconds,
                ),
            )
            summary = {
                "format_version": SUMMARY_FORMAT,
                "status": "completed",
                "page_count": extraction.page_count,
                "empty_page_count": len(extraction.empty_pages),
                "text_characters": len(extraction.text),
                "raw_bytes": extraction.raw_bytes,
                "source_verification": "not_evaluated",
            }
            details = asdict(extraction)
            details["pages"] = [page.model_dump() for page in extraction.pages]
            result = AuditResult(
                summary,
                {
                    "format_version": "issuedigest-pdf-text-manifest-v1",
                    "summary": summary,
                    "extraction": details,
                },
            )
        else:
            limits = Limits(
                args.max_files, args.max_json_bytes, args.max_pdf_bytes, args.max_total_bytes
            )
            result = audit_poll_files(args.data_root, limits=limits)
        if args.private_manifest is not None:
            save_private_manifest(result, args.data_root, args.private_manifest)
        response = result.summary
    except AuditError as error:
        response = {
            "format_version": format_version,
            "status": "failed",
            "error": str(error),
        }
        code = 2
    try:
        print(json.dumps(response, sort_keys=True))
    except OSError:
        return 2
    return code
