"""Explicit operator-only retrieval evaluation with private atomic reports."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from typing import NoReturn

from issuedigest_storage.operator_security import private_engine_lifecycle
from issuedigest_storage.retrieval_evaluation import (
    MAX_JOB_BYTES,
    evaluate,
    parse_job,
    validate_database_url,
)
from sqlalchemy import create_engine

from .files import check_private_output, read_private, write_private


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError("Invalid retrieval evaluation arguments")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(
        prog="issuedigest-evaluate-retrieval",
        allow_abbrev=False,
        description="Read-only stored lexical retrieval metrics; private report required.",
    )
    parser.add_argument("job", metavar="ABSOLUTE_PRIVATE_JOB")
    parser.add_argument("--output", required=True, metavar="NEW_ABSOLUTE_PRIVATE_REPORT")
    try:
        args = parser.parse_args(argv)
    except ValueError:
        print("Invalid retrieval evaluation arguments", file=sys.stderr)
        return 2
    try:
        check_private_output(args.output)
        raw = read_private(args.job, MAX_JOB_BYTES)
        job = parse_job(raw)
        url = validate_database_url(os.environ.get("ISSUEDIGEST_DATABASE_URL", ""), job)
        engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=False)
        # Publication follows successful transaction close AND pool disposal.
        with private_engine_lifecycle(engine):
            report = evaluate(engine, raw)
        write_private(args.output, report.model_dump_json(warnings="error").encode("utf-8"))
        print(json.dumps(report.summary, sort_keys=True, allow_nan=False))
        return 0
    except Exception:
        print("Unable to evaluate retrieval", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
