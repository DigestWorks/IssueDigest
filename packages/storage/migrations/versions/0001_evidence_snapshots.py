"""Immutable evidence objects, exact snapshot references, and atomic outbox.

Revision ID: 0001_evidence_snapshots
Revises: None
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0001_evidence_snapshots"
down_revision = None
branch_labels = None
depends_on = None


def _common(identity: str) -> list[sa.Column[Any]]:
    return [
        sa.Column(identity, pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def _ids(*names: str) -> list[sa.Column[Any]]:
    return [sa.Column(name, pg.UUID(as_uuid=True), nullable=False) for name in names]


def _fk(parent: str, *names: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(list(names), [f"{parent}.{name}" for name in names])


def upgrade() -> None:
    op.create_table(
        "source_documents",
        *_common("document_id"),
        sa.Column("provider", sa.Text, nullable=False),
        sa.Column("source_id", sa.Text, nullable=False),
        sa.UniqueConstraint("workspace_id", "document_id"),
        sa.UniqueConstraint("workspace_id", "provider", "source_id"),
    )
    op.create_table(
        "document_versions",
        *_common("version_id"),
        *_ids("document_id"),
        sa.UniqueConstraint("workspace_id", "document_id", "version_id"),
        _fk("source_documents", "workspace_id", "document_id"),
    )
    op.create_table(
        "parsed_representations",
        *_common("representation_id"),
        *_ids("document_id", "version_id"),
        sa.UniqueConstraint("workspace_id", "document_id", "version_id", "representation_id"),
        _fk("document_versions", "workspace_id", "document_id", "version_id"),
    )
    op.create_table(
        "citations",
        *_common("citation_id"),
        *_ids("document_id", "version_id", "representation_id"),
        sa.UniqueConstraint(
            "workspace_id", "document_id", "version_id", "representation_id", "citation_id"
        ),
        _fk(
            "parsed_representations",
            "workspace_id",
            "document_id",
            "version_id",
            "representation_id",
        ),
    )
    op.create_table(
        "evidence_snapshots",
        *_common("snapshot_id"),
        *_ids("document_id", "version_id", "representation_id"),
        sa.Column("schema_version", sa.Integer, nullable=False),
        sa.CheckConstraint("schema_version = 1", name="snapshot_schema_version"),
        sa.UniqueConstraint(
            "workspace_id", "document_id", "version_id", "representation_id", "snapshot_id"
        ),
        _fk(
            "parsed_representations",
            "workspace_id",
            "document_id",
            "version_id",
            "representation_id",
        ),
    )
    op.create_table(
        "snapshot_citations",
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("ordinal", sa.Integer, primary_key=True),
        *_ids("workspace_id", "document_id", "version_id", "representation_id", "citation_id"),
        sa.CheckConstraint("ordinal >= 0", name="snapshot_citation_ordinal"),
        sa.UniqueConstraint("snapshot_id", "citation_id"),
        _fk(
            "evidence_snapshots",
            "workspace_id",
            "document_id",
            "version_id",
            "representation_id",
            "snapshot_id",
        ),
        _fk(
            "citations",
            "workspace_id",
            "document_id",
            "version_id",
            "representation_id",
            "citation_id",
        ),
    )
    op.create_table(
        "outbox",
        sa.Column("event_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), nullable=False, unique=True),
        *_ids("workspace_id", "document_id", "version_id", "representation_id"),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("payload", pg.JSONB, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        _fk(
            "evidence_snapshots",
            "workspace_id",
            "document_id",
            "version_id",
            "representation_id",
            "snapshot_id",
        ),
    )


def downgrade() -> None:
    for table in (
        "outbox",
        "snapshot_citations",
        "evidence_snapshots",
        "citations",
        "parsed_representations",
        "document_versions",
        "source_documents",
    ):
        op.drop_table(table)
