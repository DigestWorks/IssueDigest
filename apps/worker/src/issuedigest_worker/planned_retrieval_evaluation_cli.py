"""Private recorded/operator-authored planned search comparison; no planner calls."""

from collections.abc import Sequence

from issuedigest_storage.planned_retrieval_evaluation import (
    evaluate,
    parse_job,
    validate_database_url,
)
from sqlalchemy import create_engine

from .evaluation_cli import run_evaluation


def main(argv: Sequence[str] | None = None) -> int:
    return run_evaluation(
        argv,
        prog="issuedigest-evaluate-planned-retrieval",
        description="Read-only stored original/planned search comparison; private report required.",
        argument_error="Invalid planned retrieval evaluation arguments",
        failure="Unable to evaluate planned retrieval",
        parse_job=parse_job,
        validate_database_url=validate_database_url,
        evaluate=evaluate,
        create_engine=create_engine,
        aggregate=lambda report: {
            **report.summary,
            "origin_case_counts": report.origin_case_counts,
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
