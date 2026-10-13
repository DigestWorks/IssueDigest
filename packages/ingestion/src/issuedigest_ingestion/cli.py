"""Aggregate-only command line interface."""

import argparse
import json
from typing import Never

from .audit import Limits, audit_poll_files
from .errors import AuditError
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
    code = 0
    try:
        args = parser.parse_args(argv)
        limits = Limits(
            args.max_files, args.max_json_bytes, args.max_pdf_bytes, args.max_total_bytes
        )
        result = audit_poll_files(args.data_root, limits=limits)
        if args.private_manifest is not None:
            save_private_manifest(result, args.data_root, args.private_manifest)
        response = result.summary
    except AuditError as error:
        response = {
            "format_version": "issuedigest-ingestion-summary-v1",
            "status": "failed",
            "error": str(error),
        }
        code = 2
    try:
        print(json.dumps(response, sort_keys=True))
    except OSError:
        return 2
    return code
