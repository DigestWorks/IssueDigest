"""Allow scoped v5 execution while preserving historical v2/v3 storage identities."""

import re

from alembic import op
from sqlalchemy import VARCHAR, inspect, text

revision = "0014_question_scoped_profile"
down_revision = "0013_question_evidence_profiles"
branch_labels = None
depends_on = None

_PLAN = "question_source_plans"
_JOBS = "evidence_jobs"
_NAMES = {
    _PLAN: "question_source_plans_evidence_profile_check",
    _JOBS: "evidence_jobs_model_profile_check",
}


def _normalized(expression: str) -> str:
    # SQL literal contents, including cast-like text and escaped quotes, are significant.
    return "".join(
        part
        if index % 2
        else re.sub(r"[\s()]", "", re.sub(r"::(?:character varying|text)(?:\[\])?", "", part))
        for index, part in enumerate(re.split(r"('(?:[^']|'')*')", expression))
    )


def _expression(table: str, *, scoped: bool) -> str:
    column = "evidence_profile" if table == _PLAN else "profile"
    profiles = "'guarded-question-evidence-v2','guarded-question-evidence-v3'"
    if scoped:
        profiles += ",'guarded-question-evidence-v5'"
    prefix = "" if table == _PLAN else "model = 'gpt-6.1-sol' AND "
    return prefix + column + " IN (" + profiles + ")"


def _validate(*, scoped: bool) -> None:
    inspector = inspect(op.get_bind())
    for table in (_PLAN, _JOBS):
        column_name = "evidence_profile" if table == _PLAN else "profile"
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        column = columns.get(column_name)
        expected_default = "'guarded-question-evidence-v2'" if table == _PLAN else ""
        if (
            column is None
            or not isinstance(column["type"], VARCHAR)
            or column["type"].length is not None
            or column["nullable"]
            or _normalized(column["default"] or "") != expected_default
        ):
            raise RuntimeError(f"Unexpected {table} profile column")
        checks = [
            check
            for check in inspector.get_check_constraints(table)
            if re.search(r"\b" + column_name + r"\b", check["sqltext"])
            or check["name"] == _NAMES[table]
        ]
        column_expression = _expression(table, scoped=scoped)
        # PostgreSQL deparses IN as = ANY (ARRAY[...]); accept only that exact shape.
        prefix, values = column_expression.split(" IN (")
        expected = _normalized(prefix + "=ANYARRAY[" + values[:-1] + "]")
        if (
            len(checks) != 1
            or checks[0]["name"] != _NAMES[table]
            or _normalized(checks[0]["sqltext"]) != expected
            or checks[0].get("dialect_options", {}).get("not_valid", False)
        ):
            raise RuntimeError(f"Unexpected {table} profile constraints")


def _replace(*, scoped: bool) -> None:
    for table in (_PLAN, _JOBS):
        op.drop_constraint(_NAMES[table], table, type_="check")
        op.create_check_constraint(_NAMES[table], table, _expression(table, scoped=scoped))


def upgrade() -> None:
    # Validate both tables before the first DDL so drift never causes partial changes.
    _validate(scoped=False)
    _replace(scoped=True)


def downgrade() -> None:
    _validate(scoped=True)
    if op.get_bind().scalar(
        text(
            "SELECT EXISTS (SELECT 1 FROM question_source_plans "
            "WHERE evidence_profile = 'guarded-question-evidence-v5') "
            "OR EXISTS (SELECT 1 FROM evidence_jobs WHERE profile = 'guarded-question-evidence-v5')"
        )
    ):
        raise RuntimeError("Cannot downgrade while v5 evidence plans or jobs remain")
    _replace(scoped=False)
