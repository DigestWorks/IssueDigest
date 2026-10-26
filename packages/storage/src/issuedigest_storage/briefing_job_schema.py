"""Isolated final briefing job schema, safe to import from old admission code."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Index,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID

metadata = MetaData()
briefing_jobs = Table(
    "briefing_jobs",
    metadata,
    *[
        Column(n, PGUUID(as_uuid=True), primary_key=n == "job_id", nullable=False)
        for n in ("job_id", "workspace_id", "actor_id", "request_id", "plan_id")
    ],
    *[
        Column(n, String, nullable=False)
        for n in (
            "question",
            "model",
            "profile",
            "inputs_sha256",
            "prompt_sha256",
            "instructions_sha256",
            "status",
        )
    ],
    Column("child_job_ids", JSONB, nullable=False),
    Column("reservation_usd", Numeric(6, 2), nullable=False),
    Column("receipt", JSONB),
    Column("receipt_sha256", String),
    Column("known_usage", JSONB),
    Column("reason", String),
    Column("usage_complete", Boolean, nullable=False, server_default="false"),
    Column("stream_closed", Boolean, nullable=False, server_default="false"),
    UniqueConstraint("workspace_id", "actor_id", "request_id"),
    CheckConstraint(
        "status IN ('pending','running','completed','failed','cancelled','indeterminate')"
    ),
    CheckConstraint("model = 'gpt-6.1-sol' AND profile = 'question-briefing-generation-v1'"),
    CheckConstraint("reservation_usd > 0 AND reservation_usd <= 10"),
)
Index(
    "briefing_jobs_active",
    briefing_jobs.c.workspace_id,
    unique=True,
    postgresql_where=briefing_jobs.c.status.in_(["pending", "running"]),
)
