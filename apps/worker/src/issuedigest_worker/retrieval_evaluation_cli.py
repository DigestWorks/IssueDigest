"""Explicit operator-only retrieval evaluation with private atomic reports."""

from collections.abc import Sequence

from issuedigest_storage.retrieval_evaluation import evaluate, parse_job, validate_database_url
from sqlalchemy import create_engine

from .evaluation_cli import run_evaluation


def main(argv: Sequence[str] | None = None) -> int:
    return run_evaluation(
        argv,
        prog="issuedigest-evaluate-retrieval",
        description="Read-only stored lexical retrieval metrics; private report required.",
        argument_error="Invalid retrieval evaluation arguments",
        failure="Unable to evaluate retrieval",
        parse_job=parse_job,
        validate_database_url=validate_database_url,
        evaluate=evaluate,
        create_engine=create_engine,
        aggregate=lambda report: report.summary,
    )


if __name__ == "__main__":
    raise SystemExit(main())
