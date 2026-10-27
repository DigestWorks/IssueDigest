"""Admit Astra v5 evidence/final work without rewriting historical Sol rows."""

import re

from alembic import op
from sqlalchemy import NUMERIC, VARCHAR, inspect, text

revision = "0015_question_astra_models"
down_revision = "0014_question_scoped_profile"
branch_labels = None
depends_on = None

_TABLES = ("evidence_jobs", "briefing_jobs")
_MODEL_CHECK = {
    "evidence_jobs": "evidence_jobs_model_profile_check",
    "briefing_jobs": "briefing_jobs_check",
}


def _normalized(expression: str) -> str:
    # Keep literal bytes AND grouping; only known deparser casts/spacing are ignorable.
    return "".join(
        part
        if index % 2
        else re.sub(r"\s", "", re.sub(r"::(?:character varying|text|numeric)(?:\[\])?", "", part))
        for index, part in enumerate(re.split(r"('(?:[^']|'')*')", expression))
    )


def _model_expression(table: str, *, astra: bool) -> str:
    if table == "evidence_jobs":
        sol = (
            "model = 'gpt-6.1-sol' AND profile IN "
            "('guarded-question-evidence-v2','guarded-question-evidence-v3',"
            "'guarded-question-evidence-v5')"
        )
        return (
            "(" + sol + ") OR (model = 'gpt-6-astra' AND profile = 'guarded-question-evidence-v5')"
            if astra
            else sol
        )
    models = "model IN ('gpt-6.1-sol','gpt-6-astra')" if astra else "model = 'gpt-6.1-sol'"
    return models + " AND profile = 'question-briefing-generation-v1'"


def _expected(table: str, *, astra: bool) -> dict[str, str]:
    # Exact PostgreSQL deparse shapes. Parentheses remain significant for OR/AND.
    if table == "evidence_jobs":
        expression = (
            "model = 'gpt-6.1-sol' AND (profile = ANY (ARRAY["
            "'guarded-question-evidence-v2','guarded-question-evidence-v3',"
            "'guarded-question-evidence-v5']))"
        )
        if astra:
            expression += " OR model = 'gpt-6-astra' AND profile = 'guarded-question-evidence-v5'"
    else:
        expression = (
            "(model = ANY (ARRAY['gpt-6.1-sol','gpt-6-astra']))"
            if astra
            else "model = 'gpt-6.1-sol'"
        ) + " AND profile = 'question-briefing-generation-v1'"
    result = {
        _MODEL_CHECK[table]: expression,
        table + "_reservation_usd_check": "reservation_usd > 0 AND reservation_usd <= 10",
    }
    if astra:
        result[table + "_astra_reservation_check"] = (
            "model <> 'gpt-6-astra' OR reservation_usd >= 1"
        )
    return {name: _normalized(value) for name, value in result.items()}


def _validate(*, astra: bool) -> None:
    inspector = inspect(op.get_bind())
    for table in _TABLES:
        columns = {column["name"]: column for column in inspector.get_columns(table)}
        for name in ("model", "profile", "reservation_usd"):
            column = columns.get(name)
            if column is None:
                raise RuntimeError(f"Unexpected {table} {name} column")
            kind = column["type"]
            valid_type = (
                isinstance(kind, NUMERIC) and kind.precision == 6 and kind.scale == 2
                if name == "reservation_usd"
                else isinstance(kind, VARCHAR) and kind.length is None
            )
            if not valid_type or column["nullable"] or column["default"] is not None:
                raise RuntimeError(f"Unexpected {table} {name} column")
        expected = _expected(table, astra=astra)
        checks = [
            check
            for check in inspector.get_check_constraints(table)
            if re.search(r"\b(model|profile|reservation_usd)\b", check["sqltext"])
            or check["name"] in expected
            or check["name"] == table + "_astra_reservation_check"
        ]
        if (
            len(checks) != len(expected)
            or {check["name"] for check in checks} != set(expected)
            or any(
                _normalized(check["sqltext"]) != expected.get(check["name"] or "")
                or check.get("dialect_options", {}).get("not_valid", False)
                for check in checks
            )
        ):
            raise RuntimeError(f"Unexpected {table} model/reservation constraints")


def _replace(*, astra: bool) -> None:
    for table in _TABLES:
        op.drop_constraint(_MODEL_CHECK[table], table, type_="check")
        op.create_check_constraint(
            _MODEL_CHECK[table], table, _model_expression(table, astra=astra)
        )
        name = table + "_astra_reservation_check"
        if astra:
            op.create_check_constraint(
                name, table, "model <> 'gpt-6-astra' OR reservation_usd >= 1"
            )
        else:
            op.drop_constraint(name, table, type_="check")


def upgrade() -> None:
    # Both complete target schemas must be known before the first DDL.
    _validate(astra=False)
    _replace(astra=True)


def downgrade() -> None:
    _validate(astra=True)
    if op.get_bind().scalar(
        text(
            "SELECT EXISTS (SELECT 1 FROM evidence_jobs WHERE model = 'gpt-6-astra') "
            "OR EXISTS (SELECT 1 FROM briefing_jobs WHERE model = 'gpt-6-astra')"
        )
    ):
        raise RuntimeError("Cannot downgrade while Astra evidence or briefing jobs remain")
    _replace(astra=False)
