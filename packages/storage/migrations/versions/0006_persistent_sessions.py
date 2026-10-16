"""Fourteen-day absolute sessions without extending existing sessions.

Revision ID: 0006_persistent_sessions
Revises: 0005_research_journey
"""

from alembic import op

revision = "0006_persistent_sessions"
down_revision = "0005_research_journey"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("session_absolute_lifetime", "auth_sessions", type_="check")
    op.create_check_constraint(
        "session_absolute_lifetime",
        "auth_sessions",
        "expires_at > issued_at AND expires_at <= issued_at + interval '1209600 seconds'",
    )


def downgrade() -> None:
    # Old applications cannot safely retain sessions issued under the longer policy.
    # Delete only those sessions; short sessions retain their original expiry.
    op.execute("DELETE FROM auth_sessions WHERE expires_at > issued_at + interval '28800 seconds'")
    op.drop_constraint("session_absolute_lifetime", "auth_sessions", type_="check")
    op.create_check_constraint(
        "session_absolute_lifetime",
        "auth_sessions",
        "expires_at > issued_at AND expires_at <= issued_at + interval '28800 seconds'",
    )
