"""Explicit owner migration for independent reviewed publication copies."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0007_public_briefings"
down_revision = "0006_persistent_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_briefing_heads",
        sa.Column("slug", sa.String(80), primary_key=True),
        sa.Column("public_id", pg.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("latest_version", sa.BigInteger, nullable=False),
        sa.Column("latest_content_sha256", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "latest_version BETWEEN 1 AND 9007199254740991", name="public_latest_version"
        ),
    )
    op.create_table(
        "public_briefings",
        sa.Column("slug", sa.String(80), primary_key=True),
        sa.Column("version", sa.BigInteger, primary_key=True),
        sa.Column("public_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("plan_sha256", sa.String(64), nullable=False),
        sa.Column("review_record", pg.JSONB, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("public_id", "version", name="public_identity_version"),
        sa.CheckConstraint("version BETWEEN 1 AND 9007199254740991", name="public_version"),
        sa.CheckConstraint(
            "withdrawn_at IS NULL OR withdrawn_at >= published_at", name="public_withdrawal"
        ),
        sa.ForeignKeyConstraint(["slug"], ["public_briefing_heads.slug"], name="public_row_head"),
    )
    op.create_foreign_key(
        "public_latest_row",
        "public_briefing_heads",
        "public_briefings",
        ["slug", "latest_version"],
        ["slug", "version"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint("public_latest_row", "public_briefing_heads", type_="foreignkey")
    op.drop_table("public_briefings")
    op.drop_table("public_briefing_heads")
