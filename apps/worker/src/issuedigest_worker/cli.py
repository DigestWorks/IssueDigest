"""Explicit offline artifact preparation, safe fixed messages and count-only summary."""

import argparse
import json
import sys
from collections.abc import Sequence
from typing import NoReturn

from issuedigest_storage.provisioning import MAX_PLAN_BYTES, parse_plan

from .files import read_private, write_private
from .models import parse_job
from .prepare import prepare_hwpx_plan


class _ArgumentError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError("Invalid HWPX preparation arguments")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(
        prog="issuedigest-prepare-hwpx",
        allow_abbrev=False,
        description="Prepare a private HWPX registration artifact offline.",
    )
    parser.add_argument("job", metavar="PRIVATE_JOB_PLAN")
    parser.add_argument("base", metavar="PRIVATE_BASE_PLAN")
    parser.add_argument("output", metavar="PRIVATE_OUTPUT_PLAN")
    try:
        args = parser.parse_args(argv)
    except _ArgumentError:
        print("Invalid HWPX preparation arguments", file=sys.stderr)
        return 2
    try:
        job = parse_job(read_private(args.job, MAX_PLAN_BYTES))
        base = parse_plan(read_private(args.base, MAX_PLAN_BYTES))
        result = prepare_hwpx_plan(job, base)
        write_private(args.output, result.model_dump_json(warnings="error").encode("utf-8"))
        print(
            json.dumps(
                {
                    "schema_version": 1,
                    "status": "prepared",
                    "sources": len(job.sources),
                    "snapshots": len(result.snapshots),
                    "citations": sum(len(s.citations) for s in job.sources),
                },
                sort_keys=True,
            )
        )
        return 0
    except Exception:
        print("Unable to prepare HWPX plan", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
