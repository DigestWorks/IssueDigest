"""Freeze private question evidence profiles without rewriting historic identities."""

import re

from alembic import op
from sqlalchemy import Column, String, inspect, text

revision = "0013_question_evidence_profiles"
down_revision = "0012_briefing_jobs"
branch_labels = None
depends_on = None


def _evidence_constraint_name() -> str:
    bind = op.get_bind()
    candidates = [
        constraint
        for constraint in inspect(bind).get_check_constraints("evidence_jobs")
        if re.search(r"\bprofile\b", constraint["sqltext"])
    ]
    if len(candidates) != 1:
        raise RuntimeError("Unexpected evidence profile constraints")
    constraint = candidates[0]
    normalized = re.sub(r"::(?:character varying|text)(?:\[\])?", "", constraint["sqltext"])
    normalized = re.sub(r"[\s()]", "", normalized)
    if normalized not in {
        "model='gpt-6.1-sol'ANDprofile='guarded-question-evidence-v2'",
        "model='gpt-6.1-sol'ANDprofile=ANYARRAY['guarded-question-evidence-v2','guarded-question-evidence-v3']",
    }:
        raise RuntimeError("Unexpected evidence profile constraint expression")
    name = constraint["name"]
    if name is None:
        raise RuntimeError("Evidence profile constraint has no name")
    return name


def _replace_evidence_constraint(v3: bool, name: str) -> None:
    op.drop_constraint(name, "evidence_jobs", type_="check")
    profiles = (
        "profile IN ('guarded-question-evidence-v2','guarded-question-evidence-v3')"
        if v3
        else "profile = 'guarded-question-evidence-v2'"
    )
    op.create_check_constraint(
        "evidence_jobs_model_profile_check",
        "evidence_jobs",
        "model = 'gpt-6.1-sol' AND " + profiles,
    )


def _plan_profile_exists(*, required: bool) -> bool:
    bind = op.get_bind()
    columns = {
        column["name"]: column for column in inspect(bind).get_columns("question_source_plans")
    }
    checks = [
        constraint
        for constraint in inspect(bind).get_check_constraints("question_source_plans")
        if re.search(r"\bevidence_profile\b", constraint["sqltext"])
        or constraint["name"] == "question_source_plans_evidence_profile_check"
    ]
    column = columns.get("evidence_profile")
    if column is None:
        if required or checks:
            raise RuntimeError("Unexpected question plan profile schema")
        return False
    default = re.sub(r"::(?:character varying|text)", "", column["default"] or "")
    if (
        not isinstance(column["type"], String)
        or column["type"].length is not None
        or column["nullable"]
        or default != "'guarded-question-evidence-v2'"
        or len(checks) != 1
    ):
        raise RuntimeError("Unexpected question plan profile column or constraints")
    check = checks[0]
    normalized = re.sub(r"::(?:character varying|text)(?:\[\])?", "", check["sqltext"])
    normalized = re.sub(r"[\s()]", "", normalized)
    if check["name"] != "question_source_plans_evidence_profile_check" or normalized != (
        "evidence_profile=ANYARRAY['guarded-question-evidence-v2','guarded-question-evidence-v3']"
    ):
        raise RuntimeError("Unexpected question plan profile constraint expression")
    return True


def upgrade() -> None:
    # Validate both tables before any schema mutation, including legacy upgrades.
    exists = _plan_profile_exists(required=False)
    evidence_name = _evidence_constraint_name()
    if not exists:
        op.add_column(
            "question_source_plans",
            Column(
                "evidence_profile",
                String,
                nullable=False,
                server_default="guarded-question-evidence-v2",
            ),
        )
        op.create_check_constraint(
            "question_source_plans_evidence_profile_check",
            "question_source_plans",
            "evidence_profile IN ('guarded-question-evidence-v2','guarded-question-evidence-v3')",
        )
    _replace_evidence_constraint(True, evidence_name)


def downgrade() -> None:
    _plan_profile_exists(required=True)
    evidence_name = _evidence_constraint_name()
    bind = op.get_bind()
    if bind.scalar(
        text(
            "SELECT EXISTS (SELECT 1 FROM question_source_plans "
            "WHERE evidence_profile <> 'guarded-question-evidence-v2') "
            "OR EXISTS (SELECT 1 FROM evidence_jobs "
            "WHERE profile <> 'guarded-question-evidence-v2')"
        )
    ):
        raise RuntimeError("Cannot downgrade while v3 evidence plans or jobs remain")
    _replace_evidence_constraint(False, evidence_name)
    op.drop_constraint(
        "question_source_plans_evidence_profile_check", "question_source_plans", type_="check"
    )
    op.drop_column("question_source_plans", "evidence_profile")
