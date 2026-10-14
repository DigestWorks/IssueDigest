"""Disposable literal-search projections, separate from immutable evidence."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from .schema import metadata

projections = Table(
    "evidence_search_projections",
    metadata,
    Column("snapshot_id", UUID(as_uuid=True), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("document_id", UUID(as_uuid=True), nullable=False),
    Column("version_id", UUID(as_uuid=True), nullable=False),
    Column("representation_id", UUID(as_uuid=True), nullable=False),
    Column("profile", String(32), nullable=False),
    Column("canonical_sha256", String(64), nullable=False),
    Column("projection_sha256", String(64), nullable=False),
    Column("unit_count", Integer, nullable=False),
    Column("unit_text_characters", Integer, nullable=False),
    Column("skipped_empty_cells", Integer, nullable=False),
    Column("skipped_large_cells", Integer, nullable=False),
    Column("collected_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("workspace_id", "snapshot_id"),
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
    CheckConstraint("profile = 'literal-ngrams-v1'", name="search_profile"),
    CheckConstraint(
        "canonical_sha256 ~ '^[0-9a-f]{64}$' AND projection_sha256 ~ '^[0-9a-f]{64}$'",
        name="search_manifest_hashes",
    ),
    CheckConstraint(
        "unit_count BETWEEN 0 AND 6000 AND unit_text_characters BETWEEN 0 AND 2000000",
        name="search_manifest_units",
    ),
    CheckConstraint(
        "skipped_empty_cells >= 0 AND skipped_large_cells >= 0 "
        "AND skipped_empty_cells + skipped_large_cells <= 20000",
        name="search_manifest_skipped",
    ),
)
units = Table(
    "evidence_search_units",
    metadata,
    Column("snapshot_id", UUID(as_uuid=True), primary_key=True),
    Column("ordinal", Integer, primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("selector", JSONB, nullable=False),
    Column("text", Text, nullable=False),
    Column("text_sha256", String(64), nullable=False),
    Column("ngrams", ARRAY(String(3)), nullable=False),
    ForeignKeyConstraint(
        ["workspace_id", "snapshot_id"],
        ["evidence_search_projections.workspace_id", "evidence_search_projections.snapshot_id"],
        ondelete="CASCADE",
    ),
    CheckConstraint("ordinal >= 0 AND ordinal < 6000", name="search_unit_ordinal"),
    CheckConstraint("char_length(text) BETWEEN 1 AND 2048", name="search_unit_text"),
    CheckConstraint("text_sha256 ~ '^[0-9a-f]{64}$'", name="search_unit_hash"),
    CheckConstraint(
        "cardinality(ngrams) BETWEEN 1 AND 6144 "
        "AND CASE WHEN array_ndims(ngrams) = 1 "
        "THEN array_position(ngrams, NULL) IS NULL ELSE false END",
        name="search_unit_ngrams",
    ),
    CheckConstraint(
        "jsonb_typeof(selector) = 'object' AND selector ? 'kind' "
        "AND selector->>'kind' IN ('text','pdf','table_cell')",
        name="search_unit_selector",
    ),
)
Index("ix_search_units_ngrams", units.c.ngrams, postgresql_using="gin")
Index("ix_search_units_workspace", units.c.workspace_id, units.c.snapshot_id, units.c.ordinal)
Index(
    "ix_search_projection_order",
    projections.c.workspace_id,
    projections.c.collected_at.desc(),
    projections.c.snapshot_id,
)
