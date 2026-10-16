"""Internal helpers for a future trusted login callback; no issuance endpoint."""

from datetime import UTC, datetime, timedelta

from fastapi import Response
from issuedigest_storage import IssuedSession
from issuedigest_storage.session_policy import SESSION_ABSOLUTE_MAX_SECONDS
from issuedigest_storage.sessions import valid_session_token

SESSION_COOKIE = "__Host-issuedigest_session"


def set_session_cookie(response: Response, issued: IssuedSession) -> None:
    """Use secure HTTPS transport; never persist the cookie beyond absolute expiry."""
    if not valid_session_token(issued.token) or issued.expires_at.tzinfo is None:
        raise ValueError("Invalid issued session")
    now = datetime.now(UTC)
    expires_at = min(
        issued.expires_at.astimezone(UTC), now + timedelta(seconds=SESSION_ABSOLUTE_MAX_SECONDS)
    )
    remaining = (expires_at - now).total_seconds()
    response.set_cookie(
        key=SESSION_COOKIE,
        value=issued.token,
        max_age=max(0, min(SESSION_ABSOLUTE_MAX_SECONDS, int(remaining))),
        expires=expires_at,
        path="/",
        secure=True,
        httponly=True,
        samesite="lax",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="lax")
