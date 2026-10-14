"""Disposable bounded literal search projections.

Revision ID: 0004_evidence_search
Revises: 0003_oauth_identity
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0004_evidence_search"
down_revision = "0003_oauth_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_search_projections",
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("representation_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("profile", sa.String(32), nullable=False),
        sa.Column("canonical_sha256", sa.String(64), nullable=False),
        sa.Column("projection_sha256", sa.String(64), nullable=False),
        sa.Column("unit_count", sa.Integer, nullable=False),
        sa.Column("unit_text_characters", sa.Integer, nullable=False),
        sa.Column("skipped_empty_cells", sa.Integer, nullable=False),
        sa.Column("skipped_large_cells", sa.Integer, nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workspace_id", "snapshot_id"),
        sa.ForeignKeyConstraint(
            ["workspace_id", "document_id", "version_id", "representation_id", "snapshot_id"],
            [
                "evidence_snapshots.workspace_id",
                "evidence_snapshots.document_id",
                "evidence_snapshots.version_id",
                "evidence_snapshots.representation_id",
                "evidence_snapshots.snapshot_id",
            ],
        ),
        sa.CheckConstraint("profile = 'literal-ngrams-v1'", name="search_profile"),
        sa.CheckConstraint(
            "canonical_sha256 ~ '^[0-9a-f]{64}$' AND projection_sha256 ~ '^[0-9a-f]{64}$'",
            name="search_manifest_hashes",
        ),
        sa.CheckConstraint(
            "unit_count BETWEEN 0 AND 6000 AND unit_text_characters BETWEEN 0 AND 2000000",
            name="search_manifest_units",
        ),
        sa.CheckConstraint(
            "skipped_empty_cells >= 0 AND skipped_large_cells >= 0 "
            "AND skipped_empty_cells + skipped_large_cells <= 20000",
            name="search_manifest_skipped",
        ),
    )
    op.create_table(
        "evidence_search_units",
        sa.Column("snapshot_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("ordinal", sa.Integer, primary_key=True),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("selector", pg.JSONB, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("ngrams", pg.ARRAY(sa.String(3)), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "snapshot_id"],
            ["evidence_search_projections.workspace_id", "evidence_search_projections.snapshot_id"],
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("ordinal >= 0 AND ordinal < 6000", name="search_unit_ordinal"),
        sa.CheckConstraint("char_length(text) BETWEEN 1 AND 2048", name="search_unit_text"),
        sa.CheckConstraint("text_sha256 ~ '^[0-9a-f]{64}$'", name="search_unit_hash"),
        sa.CheckConstraint(
            "cardinality(ngrams) BETWEEN 1 AND 6144 "
            "AND CASE WHEN array_ndims(ngrams) = 1 "
            "THEN array_position(ngrams, NULL) IS NULL ELSE false END",
            name="search_unit_ngrams",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(selector) = 'object' AND selector ? 'kind' "
            "AND selector->>'kind' IN ('text','pdf','table_cell')",
            name="search_unit_selector",
        ),
    )
    op.create_index(
        "ix_search_units_ngrams", "evidence_search_units", ["ngrams"], postgresql_using="gin"
    )
    op.create_index(
        "ix_search_units_workspace",
        "evidence_search_units",
        ["workspace_id", "snapshot_id", "ordinal"],
    )
    op.create_index(
        "ix_search_projection_order",
        "evidence_search_projections",
        ["workspace_id", sa.text("collected_at DESC"), "snapshot_id"],
    )


def downgrade() -> None:
    op.drop_table("evidence_search_units")
    op.drop_table("evidence_search_projections")
