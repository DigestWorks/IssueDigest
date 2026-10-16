"""Independent publication rows and explicit latest heads, without private foreign keys."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from .schema import metadata

public_briefing_heads = Table(
    "public_briefing_heads",
    metadata,
    Column("slug", String(80), primary_key=True),
    Column("public_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("latest_version", BigInteger, nullable=False),
    Column("latest_content_sha256", String(64), nullable=False),
    CheckConstraint("latest_version BETWEEN 1 AND 9007199254740991", name="public_latest_version"),
    ForeignKeyConstraint(
        ["slug", "latest_version"],
        ["public_briefings.slug", "public_briefings.version"],
        name="public_latest_row",
        use_alter=True,
        deferrable=True,
        initially="DEFERRED",
    ),
)
public_briefings = Table(
    "public_briefings",
    metadata,
    Column("slug", String(80), primary_key=True),
    Column("version", BigInteger, primary_key=True),
    Column("public_id", UUID(as_uuid=True), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("content_sha256", String(64), nullable=False),
    Column("plan_sha256", String(64), nullable=False),
    Column("review_record", JSONB, nullable=False),
    Column("published_at", DateTime(timezone=True), nullable=False),
    Column("withdrawn_at", DateTime(timezone=True)),
    UniqueConstraint("public_id", "version", name="public_identity_version"),
    ForeignKeyConstraint(["slug"], ["public_briefing_heads.slug"], name="public_row_head"),
    CheckConstraint("version BETWEEN 1 AND 9007199254740991", name="public_version"),
    CheckConstraint(
        "withdrawn_at IS NULL OR withdrawn_at >= published_at", name="public_withdrawal"
    ),
)
