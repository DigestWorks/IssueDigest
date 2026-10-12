"""Provider independent internal users, memberships and hashed sessions.

Revision ID: 0002_auth_sessions
Revises: 0001_evidence_snapshots
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0002_auth_sessions"
down_revision = "0001_evidence_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_users",
        sa.Column("user_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("issuer", sa.String(256), nullable=False),
        sa.Column("subject", sa.String(256), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.UniqueConstraint("issuer", "subject"),
        sa.CheckConstraint(
            "char_length(issuer) > 0 AND char_length(subject) > 0", name="identity_nonempty"
        ),
        sa.CheckConstraint("substring(user_id::text from 15 for 1) = '4'", name="user_id_uuid4"),
    )
    op.create_table(
        "auth_workspace_memberships",
        sa.Column(
            "user_id", pg.UUID(as_uuid=True), sa.ForeignKey("auth_users.user_id"), primary_key=True
        ),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("role", sa.String(6), nullable=False),
        sa.Column("active", sa.Boolean, nullable=False),
        sa.CheckConstraint("role IN ('viewer', 'editor', 'owner')", name="membership_role"),
        sa.CheckConstraint(
            "substring(workspace_id::text from 15 for 1) = '4'", name="workspace_id_uuid4"
        ),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("token_sha256", sa.String(64), primary_key=True),
        sa.Column(
            "user_id", pg.UUID(as_uuid=True), sa.ForeignKey("auth_users.user_id"), nullable=False
        ),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False),
        sa.CheckConstraint("token_sha256 ~ '^[0-9a-f]{64}$'", name="session_hash"),
        sa.CheckConstraint(
            "expires_at > issued_at AND expires_at <= issued_at + interval '28800 seconds'",
            name="session_absolute_lifetime",
        ),
        sa.CheckConstraint("last_activity_at >= issued_at", name="session_activity"),
    )


def downgrade() -> None:
    for table in ("auth_sessions", "auth_workspace_memberships", "auth_users"):
        op.drop_table(table)
