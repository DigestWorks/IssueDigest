"""Isolated opaque final briefing jobs."""

from alembic import op
from issuedigest_storage.briefing_job_schema import briefing_jobs

revision = "0012_briefing_jobs"
down_revision = "0011_question_source_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    briefing_jobs.create(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    briefing_jobs.drop(op.get_bind(), checkfirst=False)
