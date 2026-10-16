"""Explicit private capture (network) and preparation (offline) operator entrypoints."""

import json
import sys
from collections.abc import Sequence

from issuedigest_connectors import MAX_CAPTURE_BYTES, capture_assembly, serialize_capture
from issuedigest_storage.provisioning import MAX_PLAN_BYTES, parse_plan

from .assembly_models import MAX_ASSEMBLY_JOB_BYTES, parse_assembly_job
from .assembly_prepare import prepare_assembly_plan
from .cli import _ArgumentError, _Parser
from .files import check_private_output, read_private, write_private


def _run(argv: Sequence[str] | None, *, capture: bool) -> int:
    parser = _Parser(
        prog="issuedigest-capture-assembly" if capture else "issuedigest-prepare-assembly",
        allow_abbrev=False,
    )
    parser.add_argument("job", metavar="PRIVATE_JOB")
    if not capture:
        parser.add_argument("capture", metavar="PRIVATE_CAPTURE")
        parser.add_argument("base", metavar="PRIVATE_BASE_PLAN")
    parser.add_argument("output", metavar="PRIVATE_NEW_CAPTURE" if capture else "PRIVATE_NEW_PLAN")
    try:
        args = parser.parse_args(argv)
    except _ArgumentError:
        print("Invalid Assembly arguments", file=sys.stderr)
        return 2
    try:
        check_private_output(args.output)
        job = parse_assembly_job(read_private(args.job, MAX_ASSEMBLY_JOB_BYTES))
        if capture:
            result = capture_assembly(job.bill_id, collected_at=job.collected_at)
            raw = serialize_capture(result)
            summary: dict[str, int | str] = {
                "schema_version": 1,
                "status": "captured",
                "sources": 1,
                "requests": 2,
            }
        else:
            capture_raw = read_private(args.capture, MAX_CAPTURE_BYTES)
            base = parse_plan(read_private(args.base, MAX_PLAN_BYTES))
            plan = prepare_assembly_plan(job, capture_raw, base)
            raw = plan.model_dump_json(warnings="error").encode("utf-8")
            summary = {
                "schema_version": 1,
                "status": "prepared",
                "sources": 1,
                "snapshots": len(plan.snapshots),
                "citations": 1,
            }
        write_private(args.output, raw)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except Exception:
        print(
            "Unable to capture Assembly source" if capture else "Unable to prepare Assembly plan",
            file=sys.stderr,
        )
        return 1


def capture_main(argv: Sequence[str] | None = None) -> int:
    return _run(argv, capture=True)


def prepare_main(argv: Sequence[str] | None = None) -> int:
    return _run(argv, capture=False)
