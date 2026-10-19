"""Shared private evaluator runner: successful lifecycle precedes atomic publication."""

import argparse
import json
import os
import sys
from collections.abc import Callable, Sequence
from typing import NoReturn

from issuedigest_storage.operator_security import private_engine_lifecycle
from issuedigest_storage.retrieval_evaluation import MAX_JOB_BYTES
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.engine import URL

from .files import check_private_output, read_private, write_private


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError("Invalid evaluation arguments")


def run_evaluation[Job: BaseModel, Report: BaseModel](
    argv: Sequence[str] | None,
    *,
    prog: str,
    description: str,
    argument_error: str,
    failure: str,
    parse_job: Callable[[bytes], Job],
    validate_database_url: Callable[[str, Job], URL],
    evaluate: Callable[[Engine, bytes], Report],
    create_engine: Callable[..., Engine],
    aggregate: Callable[[Report], object],
) -> int:
    parser = _Parser(prog=prog, allow_abbrev=False, description=description)
    parser.add_argument("job", metavar="ABSOLUTE_PRIVATE_JOB")
    parser.add_argument("--output", required=True, metavar="NEW_ABSOLUTE_PRIVATE_REPORT")
    try:
        args = parser.parse_args(argv)
    except ValueError:
        print(argument_error, file=sys.stderr)
        return 2
    try:
        check_private_output(args.output)
        raw = read_private(args.job, MAX_JOB_BYTES)
        job = parse_job(raw)
        url = validate_database_url(os.environ.get("ISSUEDIGEST_DATABASE_URL", ""), job)
        engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=False)
        # Publication follows successful transaction close AND connection/pool disposal.
        with private_engine_lifecycle(engine):
            report = evaluate(engine, raw)
        write_private(args.output, report.model_dump_json(warnings="error").encode("utf-8"))
        print(json.dumps(aggregate(report), sort_keys=True, allow_nan=False))
        return 0
    except Exception:
        print(failure, file=sys.stderr)
        return 1
