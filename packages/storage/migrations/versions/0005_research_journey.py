"""Research presentation, runs, events and conservative monthly reservations."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0005_research_journey"
down_revision = "0004_evidence_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_presentations",
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["evidence_snapshots.snapshot_id"], ondelete="CASCADE"
        ),
    )
    op.create_table(
        "research_budget_months",
        sa.Column("month", sa.String(7), primary_key=True),
        sa.Column("reserved_usd", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("reservation_count", sa.Integer, nullable=False, server_default="0"),
        sa.CheckConstraint(
            "reserved_usd >= 0 AND reserved_usd <= 10 AND reservation_count BETWEEN 0 AND 40",
            name="budget_cap",
        ),
    )
    op.create_table(
        "research_runs",
        sa.Column("run_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("input_hash", sa.String(64), nullable=False),
        sa.Column("question", sa.String(1500), nullable=False),
        sa.Column("snapshot_ids", pg.JSONB, nullable=False),
        sa.Column("parent_run_id", pg.UUID(as_uuid=True)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(32)),
        sa.Column("result", pg.JSONB),
        sa.Column("model", sa.String(32), nullable=False),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("budget_month", sa.String(7), nullable=False),
        sa.Column("reserved_usd", sa.Numeric(4, 2), nullable=False),
        sa.Column("cancel_requested", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("workspace_id", "actor_id", "request_id"),
        sa.CheckConstraint(
            (
                "status IN ('queued','retrieving','generating','validating',"
                "'completed','failed','cancelled')"
            ),
            name="run_status",
        ),
        sa.CheckConstraint("model = 'gpt-5.4-mini' AND reserved_usd = 0.25", name="run_pricing"),
        sa.CheckConstraint("input_tokens >= 0 AND output_tokens >= 0", name="run_tokens"),
    )
    op.create_index(
        "ux_research_workspace_active",
        "research_runs",
        ["workspace_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued','retrieving','generating','validating')"),
    )
    op.create_index(
        "ix_research_workspace_created",
        "research_runs",
        ["workspace_id", sa.text("created_at DESC")],
    )
    op.create_table(
        "research_events",
        sa.Column("run_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("sequence", sa.Integer, primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(["run_id"], ["research_runs.run_id"], ondelete="CASCADE"),
        sa.CheckConstraint("sequence >= 1", name="event_sequence"),
    )


def downgrade() -> None:
    op.drop_table("research_events")
    op.drop_index("ix_research_workspace_created", table_name="research_runs")
    op.drop_index("ux_research_workspace_active", table_name="research_runs")
    op.drop_table("research_runs")
    op.drop_table("research_budget_months")
    op.drop_table("source_presentations")
