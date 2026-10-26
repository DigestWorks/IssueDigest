"""Isolated opaque private evidence jobs."""

from alembic import op
from issuedigest_storage.evidence_jobs import evidence_jobs

revision = "0010_evidence_jobs"
down_revision = "0009_policy_intake"
branch_labels = None
depends_on = None


def upgrade() -> None:
    evidence_jobs.create(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    evidence_jobs.drop(op.get_bind(), checkfirst=False)
