"""Isolated durable question-only source plans."""

from alembic import op
from issuedigest_storage.question_plans import question_source_plans

revision = "0011_question_source_plans"
down_revision = "0010_evidence_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    question_source_plans.create(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    question_source_plans.drop(op.get_bind(), checkfirst=False)
