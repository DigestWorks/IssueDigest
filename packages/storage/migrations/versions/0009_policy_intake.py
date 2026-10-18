"""Append-only reviewed intake links; journal and canonical evidence remain independent."""

from alembic import op
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()
# Resolve references without creating or changing any of the existing tables.
Table("policy_collection_attempts", metadata, Column("attempt_id", UUID(as_uuid=True)))
Table("policy_collection_channels", metadata, Column("collection_id", UUID(as_uuid=True)))
Table(
    "evidence_snapshots",
    metadata,
    *[
        Column(name, UUID(as_uuid=True))
        for name in (
            "workspace_id",
            "document_id",
            "version_id",
            "representation_id",
            "snapshot_id",
        )
    ],
)

policy_intake_receipts = Table(
    "policy_intake_receipts",
    metadata,
    Column("workspace_id", UUID(as_uuid=True), primary_key=True),
    Column(
        "attempt_id",
        UUID(as_uuid=True),
        ForeignKey("policy_collection_attempts.attempt_id"),
        primary_key=True,
    ),
    Column("news_id", String(9), primary_key=True),
    Column(
        "collection_id",
        UUID(as_uuid=True),
        ForeignKey("policy_collection_channels.collection_id"),
        nullable=False,
    ),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("representation_id", UUID(as_uuid=True), nullable=False),
    Column("snapshot_id", UUID(as_uuid=True), nullable=False),
    Column("capture_collected_at", DateTime(timezone=True), nullable=False),
    *[
        Column(name + "_sha256", String(64), nullable=False)
        for name in ("capture", "report", "request", "approval", "fingerprint")
    ],
    Column("decision", String(8), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("workspace_id", "attempt_id", "news_id", name="policy_intake_identity"),
    UniqueConstraint(
        "workspace_id", "document_id", "capture_collected_at", name="policy_intake_document_time"
    ),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id", "representation_id", "snapshot_id"],
        [
            "evidence_snapshots." + name
            for name in (
                "workspace_id",
                "document_id",
                "version_id",
                "representation_id",
                "snapshot_id",
            )
        ],
    ),
    CheckConstraint("news_id ~ '^[0-9]{9}$'", name="policy_intake_news"),
    CheckConstraint("decision IN ('created','reused')", name="policy_intake_decision"),
    *[
        CheckConstraint(name + "_sha256 ~ '^[0-9a-f]{64}$'", name="policy_intake_" + name + "_hash")
        for name in ("capture", "report", "request", "approval", "fingerprint")
    ],
    *[
        CheckConstraint(
            "substring("
            + name
            + "::text from 15 for 1) = '4' AND substring("
            + name
            + "::text from 20 for 1) IN ('8','9','a','b')",
            name="policy_intake_" + name + "_uuid4",
        )
        for name in (
            "workspace_id",
            "attempt_id",
            "collection_id",
            "document_id",
            "version_id",
            "representation_id",
            "snapshot_id",
        )
    ],
)


Index(
    "ix_policy_intake_latest",
    policy_intake_receipts.c.workspace_id,
    policy_intake_receipts.c.document_id,
    policy_intake_receipts.c.capture_collected_at.desc(),
)

revision = "0009_policy_intake"
down_revision = "0008_policy_collection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    policy_intake_receipts.create(op.get_bind(), checkfirst=False)


def downgrade() -> None:
    policy_intake_receipts.drop(op.get_bind(), checkfirst=False)
