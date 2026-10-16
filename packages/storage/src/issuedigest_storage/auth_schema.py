"""Authentication tables; evidence namespaces acquire no retroactive foreign keys."""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from .schema import metadata
from .session_policy import SESSION_ABSOLUTE_MAX_SECONDS


def uuid4_check(column: str) -> CheckConstraint:
    return CheckConstraint(f"substring({column}::text from 15 for 1) = '4'", name=f"{column}_uuid4")


auth_users = Table(
    "auth_users",
    metadata,
    Column("user_id", UUID(as_uuid=True), primary_key=True),
    Column("issuer", String(256), nullable=False),
    Column("subject", String(256), nullable=False),
    Column("enabled", Boolean, nullable=False),
    UniqueConstraint("issuer", "subject"),
    CheckConstraint(
        "char_length(issuer) > 0 AND char_length(subject) > 0", name="identity_nonempty"
    ),
    uuid4_check("user_id"),
)
auth_workspace_memberships = Table(
    "auth_workspace_memberships",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("auth_users.user_id"), primary_key=True),
    Column("workspace_id", UUID(as_uuid=True), primary_key=True),
    Column("role", String(6), nullable=False),
    Column("active", Boolean, nullable=False),
    CheckConstraint("role IN ('viewer', 'editor', 'owner')", name="membership_role"),
    uuid4_check("workspace_id"),
)
auth_sessions = Table(
    "auth_sessions",
    metadata,
    Column("token_sha256", String(64), primary_key=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("auth_users.user_id"), nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("last_activity_at", DateTime(timezone=True), nullable=False),
    Column("revoked", Boolean, nullable=False),
    CheckConstraint("token_sha256 ~ '^[0-9a-f]{64}$'", name="session_hash"),
    CheckConstraint(
        f"expires_at > issued_at AND expires_at <= issued_at + "
        f"interval '{SESSION_ABSOLUTE_MAX_SECONDS} seconds'",
        name="session_absolute_lifetime",
    ),
    CheckConstraint("last_activity_at >= issued_at", name="session_activity"),
)


auth_oauth_flows = Table(
    "auth_oauth_flows",
    metadata,
    Column("state_sha256", String(64), primary_key=True),
    Column("cookie_sha256", String(64), nullable=False),
    Column("code_verifier", String(43), nullable=False),
    Column("oidc_nonce", String(43), nullable=False),
    Column("issued_at", DateTime(timezone=True), nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    CheckConstraint("state_sha256 ~ '^[0-9a-f]{64}$'", name="oauth_state_hash"),
    CheckConstraint("cookie_sha256 ~ '^[0-9a-f]{64}$'", name="oauth_cookie_hash"),
    CheckConstraint("code_verifier ~ '^[A-Za-z0-9_-]{43}$'", name="oauth_verifier"),
    CheckConstraint("oidc_nonce ~ '^[A-Za-z0-9_-]{43}$'", name="oauth_nonce"),
    CheckConstraint(
        "expires_at > issued_at AND expires_at <= issued_at + interval '600 seconds'",
        name="oauth_lifetime",
    ),
)
auth_identity_invites = Table(
    "auth_identity_invites",
    metadata,
    Column("issuer", String(256), primary_key=True),
    Column("email", String(320), primary_key=True),
    Column("user_id", UUID(as_uuid=True), nullable=False, unique=True),
    Column("workspace_id", UUID(as_uuid=True), nullable=False),
    Column("role", String(6), nullable=False),
    Column("enabled", Boolean, nullable=False),
    Column("bound_subject", String(256), nullable=True),
    CheckConstraint("issuer ~ '[^[:space:]]'", name="invite_issuer_nonblank"),
    CheckConstraint(
        "email = lower(email) AND email ~ '^[!-~]+@[!-~]+$' "
        "AND length(email) - length(replace(email, '@', '')) = 1",
        name="invite_email",
    ),
    CheckConstraint(
        "bound_subject IS NULL OR bound_subject ~ '[^[:space:]]'",
        name="invite_bound_subject",
    ),
    CheckConstraint("role IN ('viewer', 'editor', 'owner')", name="invite_role"),
    CheckConstraint(
        "substring(user_id::text from 15 for 1) = '4' "
        "AND substring(user_id::text from 20 for 1) IN ('8', '9', 'a', 'b')",
        name="invite_user_uuid4",
    ),
    CheckConstraint(
        "substring(workspace_id::text from 15 for 1) = '4' "
        "AND substring(workspace_id::text from 20 for 1) IN ('8', '9', 'a', 'b')",
        name="invite_workspace_uuid4",
    ),
)
