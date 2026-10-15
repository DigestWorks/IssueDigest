"""Mutable research runs and source presentation, isolated from immutable evidence."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .schema import metadata

source_presentations = Table(
    "source_presentations",
    metadata,
    Column("snapshot_id", UUID(as_uuid=True), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("payload", JSONB, nullable=False),
    ForeignKeyConstraint(["snapshot_id"], ["evidence_snapshots.snapshot_id"], ondelete="CASCADE"),
)
research_budget_months = Table(
    "research_budget_months",
    metadata,
    Column("month", String(7), primary_key=True),
    Column("reserved_usd", Numeric(6, 2), nullable=False, server_default="0"),
    Column("reservation_count", Integer, nullable=False, server_default="0"),
    CheckConstraint(
        "reserved_usd >= 0 AND reserved_usd <= 10 AND reservation_count BETWEEN 0 AND 40",
        name="budget_cap",
    ),
)
research_runs = Table(
    "research_runs",
    metadata,
    Column("run_id", UUID(as_uuid=True), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("actor_id", UUID(as_uuid=True), nullable=False),
    Column("request_id", UUID(as_uuid=True), nullable=False),
    Column("input_hash", String(64), nullable=False),
    Column("question", String(1500), nullable=False),
    Column("snapshot_ids", JSONB, nullable=False),
    Column("parent_run_id", UUID(as_uuid=True), nullable=True),
    Column("status", String(16), nullable=False),
    Column("error_code", String(32), nullable=True),
    Column("result", JSONB, nullable=True),
    Column("model", String(32), nullable=False),
    Column("input_tokens", Integer, nullable=False, server_default="0"),
    Column("output_tokens", Integer, nullable=False, server_default="0"),
    Column("budget_month", String(7), nullable=False),
    Column("reserved_usd", Numeric(4, 2), nullable=False),
    Column("cancel_requested", Boolean, nullable=False, server_default="false"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("workspace_id", "actor_id", "request_id"),
    CheckConstraint(
        (
            "status IN ('queued','retrieving','generating','validating',"
            "'completed','failed','cancelled')"
        ),
        name="run_status",
    ),
    CheckConstraint("model = 'gpt-5.4-mini' AND reserved_usd = 0.25", name="run_pricing"),
    CheckConstraint("input_tokens >= 0 AND output_tokens >= 0", name="run_tokens"),
)
Index(
    "ux_research_workspace_active",
    research_runs.c.workspace_id,
    unique=True,
    postgresql_where=research_runs.c.status.in_(
        ["queued", "retrieving", "generating", "validating"]
    ),
)
Index(
    "ix_research_workspace_created", research_runs.c.workspace_id, research_runs.c.created_at.desc()
)
research_events = Table(
    "research_events",
    metadata,
    Column("run_id", UUID(as_uuid=True), primary_key=True),
    Column("sequence", Integer, primary_key=True),
    Column("status", String(16), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(["run_id"], ["research_runs.run_id"], ondelete="CASCADE"),
    CheckConstraint("sequence >= 1", name="event_sequence"),
)
