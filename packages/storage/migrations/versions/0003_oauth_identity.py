"""Short-lived OAuth flows and operator-approved first identity bindings.

Revision ID: 0003_oauth_identity
Revises: 0002_auth_sessions
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "0003_oauth_identity"
down_revision = "0002_auth_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_oauth_flows",
        sa.Column("state_sha256", sa.String(64), primary_key=True),
        sa.Column("cookie_sha256", sa.String(64), nullable=False),
        sa.Column("code_verifier", sa.String(43), nullable=False),
        sa.Column("oidc_nonce", sa.String(43), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state_sha256 ~ '^[0-9a-f]{64}$'", name="oauth_state_hash"),
        sa.CheckConstraint("cookie_sha256 ~ '^[0-9a-f]{64}$'", name="oauth_cookie_hash"),
        sa.CheckConstraint("code_verifier ~ '^[A-Za-z0-9_-]{43}$'", name="oauth_verifier"),
        sa.CheckConstraint("oidc_nonce ~ '^[A-Za-z0-9_-]{43}$'", name="oauth_nonce"),
        sa.CheckConstraint(
            "expires_at > issued_at AND expires_at <= issued_at + interval '600 seconds'",
            name="oauth_lifetime",
        ),
    )
    op.create_table(
        "auth_identity_invites",
        sa.Column("issuer", sa.String(256), primary_key=True),
        sa.Column("email", sa.String(320), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("workspace_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(6), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("bound_subject", sa.String(256), nullable=True),
        sa.CheckConstraint("issuer ~ '[^[:space:]]'", name="invite_issuer_nonblank"),
        sa.CheckConstraint(
            "email = lower(email) AND email ~ '^[!-~]+@[!-~]+$' "
            "AND length(email) - length(replace(email, '@', '')) = 1",
            name="invite_email",
        ),
        sa.CheckConstraint(
            "bound_subject IS NULL OR bound_subject ~ '[^[:space:]]'",
            name="invite_bound_subject",
        ),
        sa.CheckConstraint("role IN ('viewer', 'editor', 'owner')", name="invite_role"),
        sa.CheckConstraint(
            "substring(user_id::text from 15 for 1) = '4' "
            "AND substring(user_id::text from 20 for 1) IN ('8', '9', 'a', 'b')",
            name="invite_user_uuid4",
        ),
        sa.CheckConstraint(
            "substring(workspace_id::text from 15 for 1) = '4' "
            "AND substring(workspace_id::text from 20 for 1) IN ('8', '9', 'a', 'b')",
            name="invite_workspace_uuid4",
        ),
    )


def downgrade() -> None:
    op.drop_table("auth_identity_invites")
    op.drop_table("auth_oauth_flows")
