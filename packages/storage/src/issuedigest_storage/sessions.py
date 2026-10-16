"""Internal session issuance; callers must be trusted identity connectors/admins."""

import base64
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Engine, func, insert, select, update
from sqlalchemy.exc import SQLAlchemyError

from .auth_schema import auth_sessions, auth_users
from .engine import verify_engine
from .repository import StorageError, _uuid4
from .session_policy import SESSION_ABSOLUTE_MAX_SECONDS


class AuthenticationDenied(RuntimeError):
    """No active authenticated session."""


def valid_session_token(token: str | None) -> bool:
    """Accept only canonical URL-safe encodings of exactly 32 random bytes."""
    if not isinstance(token, str) or re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
        return False
    raw = base64.urlsafe_b64decode(token + "=")
    return len(raw) == 32 and base64.urlsafe_b64encode(raw).decode().rstrip("=") == token


def token_digest(token: str) -> str:
    if not valid_session_token(token):
        raise AuthenticationDenied("Authentication required")
    return sha256(token.encode("ascii")).hexdigest()


@dataclass(frozen=True)
class IssuedSession:
    token: str = field(repr=False)
    expires_at: datetime


class SessionRepository:
    """Hash-only persistence; no provider verification or public session issuance."""

    def __init__(self, engine: Engine):
        verify_engine(engine)
        self._engine = engine

    def issue_session(
        self, user_id: UUID, lifetime_seconds: int = SESSION_ABSOLUTE_MAX_SECONDS
    ) -> IssuedSession:
        _uuid4(user_id)
        if (
            type(lifetime_seconds) is not int
            or not 1 <= lifetime_seconds <= SESSION_ABSOLUTE_MAX_SECONDS
        ):
            raise ValueError(
                f"Session lifetime must be an integer from 1 to {SESSION_ABSOLUTE_MAX_SECONDS}"
                " seconds"
            )
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    user = (
                        conn.execute(
                            select(auth_users)
                            .where(auth_users.c.user_id == user_id)
                            .with_for_update()
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if user is None or not user["enabled"]:
                        raise AuthenticationDenied("Authentication required")
                    now: datetime = (
                        conn.execute(select(func.clock_timestamp())).scalar_one().astimezone(UTC)
                    )
                    token = secrets.token_urlsafe(32)
                    expires = now + timedelta(seconds=lifetime_seconds)
                    conn.execute(
                        insert(auth_sessions).values(
                            token_sha256=token_digest(token),
                            user_id=user_id,
                            issued_at=now,
                            expires_at=expires,
                            last_activity_at=now,
                            revoked=False,
                        )
                    )
                    return IssuedSession(token, expires)
        except SQLAlchemyError:
            raise StorageError("Unable to issue session") from None

    def revoke_session(self, token: str) -> None:
        digest = token_digest(token)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    conn.execute(
                        update(auth_sessions)
                        .where(auth_sessions.c.token_sha256 == digest)
                        .values(revoked=True)
                    )
        except SQLAlchemyError:
            raise StorageError("Unable to revoke session") from None
