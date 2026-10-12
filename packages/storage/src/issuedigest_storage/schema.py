"""Relational references for immutable, JSON-validated evidence records."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()


def common_columns(identity: str) -> list[Column[object]]:
    return [
        Column(identity, UUID(as_uuid=True), primary_key=True),
        Column("workspace_id", UUID(as_uuid=True), nullable=False),
        Column("payload", JSONB, nullable=False),
        Column("content_sha256", String(64), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ]


source_documents = Table(
    "source_documents",
    metadata,
    *common_columns("document_id"),
    Column("provider", Text, nullable=False),
    Column("source_id", Text, nullable=False),
    UniqueConstraint("workspace_id", "document_id"),
    UniqueConstraint("workspace_id", "provider", "source_id"),
)
document_versions = Table(
    "document_versions",
    metadata,
    *common_columns("version_id"),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    UniqueConstraint("workspace_id", "document_id", "version_id"),
    ForeignKeyConstraint(
        ["workspace_id", "document_id"],
        ["source_documents.workspace_id", "source_documents.document_id"],
    ),
)
parsed_representations = Table(
    "parsed_representations",
    metadata,
    *common_columns("representation_id"),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    UniqueConstraint("workspace_id", "document_id", "version_id", "representation_id"),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id"],
        [
            "document_versions.workspace_id",
            "document_versions.document_id",
            "document_versions.version_id",
        ],
    ),
)
citations = Table(
    "citations",
    metadata,
    *common_columns("citation_id"),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("representation_id", UUID(as_uuid=True), nullable=False),
    UniqueConstraint(
        "workspace_id", "document_id", "version_id", "representation_id", "citation_id"
    ),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id", "representation_id"],
        [
            "parsed_representations.workspace_id",
            "parsed_representations.document_id",
            "parsed_representations.version_id",
            "parsed_representations.representation_id",
        ],
    ),
)
evidence_snapshots = Table(
    "evidence_snapshots",
    metadata,
    *common_columns("snapshot_id"),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("representation_id", UUID(as_uuid=True), nullable=False),
    Column("schema_version", Integer, nullable=False),
    CheckConstraint("schema_version = 1", name="snapshot_schema_version"),
    UniqueConstraint(
        "workspace_id", "document_id", "version_id", "representation_id", "snapshot_id"
    ),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id", "representation_id"],
        [
            "parsed_representations.workspace_id",
            "parsed_representations.document_id",
            "parsed_representations.version_id",
            "parsed_representations.representation_id",
        ],
    ),
)
snapshot_citations = Table(
    "snapshot_citations",
    metadata,
    Column("snapshot_id", UUID(as_uuid=True), primary_key=True),
    Column("ordinal", Integer, primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("representation_id", UUID(as_uuid=True), nullable=False),
    Column("citation_id", UUID(as_uuid=True), nullable=False),
    CheckConstraint("ordinal >= 0", name="snapshot_citation_ordinal"),
    UniqueConstraint("snapshot_id", "citation_id"),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id", "representation_id", "snapshot_id"],
        [
            "evidence_snapshots.workspace_id",
            "evidence_snapshots.document_id",
            "evidence_snapshots.version_id",
            "evidence_snapshots.representation_id",
            "evidence_snapshots.snapshot_id",
        ],
    ),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id", "representation_id", "citation_id"],
        [
            "citations.workspace_id",
            "citations.document_id",
            "citations.version_id",
            "citations.representation_id",
            "citations.citation_id",
        ],
    ),
)
outbox = Table(
    "outbox",
    metadata,
    Column("event_id", UUID(as_uuid=True), primary_key=True),
    Column("snapshot_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("representation_id", UUID(as_uuid=True), nullable=False),
    Column("event_type", Text, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    ForeignKeyConstraint(
        ["workspace_id", "document_id", "version_id", "representation_id", "snapshot_id"],
        [
            "evidence_snapshots.workspace_id",
            "evidence_snapshots.document_id",
            "evidence_snapshots.version_id",
            "evidence_snapshots.representation_id",
            "evidence_snapshots.snapshot_id",
        ],
    ),
)
