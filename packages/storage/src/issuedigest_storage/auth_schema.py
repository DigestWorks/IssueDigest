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
        "expires_at > issued_at AND expires_at <= issued_at + interval '28800 seconds'",
        name="session_absolute_lifetime",
    ),
    CheckConstraint("last_activity_at >= issued_at", name="session_activity"),
)
