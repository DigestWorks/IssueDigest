"""Independent bounded journal, without evidence, publication or research relationships."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .schema import metadata

policy_collection_channels = Table(
    "policy_collection_channels",
    metadata,
    Column("collection_id", UUID(as_uuid=True), primary_key=True),
    Column("config", JSONB, nullable=False),
    Column("config_sha256", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(
        "substring(collection_id::text from 15 for 1) = '4' AND "
        "substring(collection_id::text from 20 for 1) IN ('8','9','a','b')",
        name="collection_uuid4",
    ),
    CheckConstraint("config_sha256 ~ '^[0-9a-f]{64}$'", name="collection_config_hash"),
)
policy_collection_attempts = Table(
    "policy_collection_attempts",
    metadata,
    Column("attempt_id", UUID(as_uuid=True), primary_key=True),
    Column(
        "collection_id",
        UUID(as_uuid=True),
        ForeignKey("policy_collection_channels.collection_id"),
        nullable=False,
    ),
    Column("sequence", Integer, nullable=False),
    Column("state", String(16), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("failure_code", String(32)),
    Column("capture_bytes", LargeBinary),
    Column("capture_sha256", String(64)),
    Column("report_bytes", LargeBinary),
    Column("report_sha256", String(64)),
    CheckConstraint(
        "substring(attempt_id::text from 15 for 1) = '4' AND "
        "substring(attempt_id::text from 20 for 1) IN ('8','9','a','b')",
        name="collection_attempt_uuid4",
    ),
    UniqueConstraint("collection_id", "sequence", name="collection_sequence"),
    CheckConstraint("sequence BETWEEN 1 AND 4096", name="collection_sequence_bound"),
    CheckConstraint("finished_at IS NULL OR finished_at >= started_at", name="collection_time"),
    CheckConstraint(
        "(state = 'running' AND finished_at IS NULL AND failure_code IS NULL "
        "AND capture_bytes IS NULL AND capture_sha256 IS NULL "
        "AND report_bytes IS NULL AND report_sha256 IS NULL) OR "
        "(state = 'failed' AND finished_at IS NOT NULL "
        "AND failure_code IS NOT NULL "
        "AND failure_code IN ('capture_failed','validation_failed','interrupted') "
        "AND capture_bytes IS NULL AND capture_sha256 IS NULL "
        "AND report_bytes IS NULL AND report_sha256 IS NULL) OR "
        "(state = 'succeeded' AND finished_at IS NOT NULL AND failure_code IS NULL "
        "AND capture_bytes IS NOT NULL AND capture_sha256 IS NOT NULL "
        "AND report_bytes IS NOT NULL AND report_sha256 IS NOT NULL "
        "AND octet_length(capture_bytes) BETWEEN 1 AND 8404992 "
        "AND octet_length(report_bytes) BETWEEN 1 AND 65536 "
        "AND capture_sha256 ~ '^[0-9a-f]{64}$' AND report_sha256 ~ '^[0-9a-f]{64}$')",
        name="collection_attempt_shape",
    ),
)
Index(
    "ux_policy_collection_running",
    policy_collection_attempts.c.collection_id,
    unique=True,
    postgresql_where=policy_collection_attempts.c.state == "running",
)
