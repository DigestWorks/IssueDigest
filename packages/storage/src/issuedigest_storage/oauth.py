"""Trusted provider results and explicit operator invitations; no public signup."""

import base64
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from sqlalchemy import Engine, delete, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError

from .auth_schema import (
    auth_identity_invites,
    auth_oauth_flows,
    auth_sessions,
    auth_users,
    auth_workspace_memberships,
)
from .engine import verify_engine
from .identity import _boolean, _identity_value
from .repository import StorageConflict, StorageError, _uuid4
from .sessions import AuthenticationDenied, IssuedSession, token_digest, valid_session_token


@dataclass(frozen=True)
class PendingLogin:
    state: str = field(repr=False)
    browser_token: str = field(repr=False)
    code_challenge: str = field(repr=False)
    oidc_nonce: str = field(repr=False)


@dataclass(frozen=True)
class ConsumedLogin:
    code_verifier: str = field(repr=False)
    oidc_nonce: str = field(repr=False)


def _email(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.isascii()
        or not 3 <= len(value) <= 320
        or value.count("@") != 1
        or any(not 33 <= ord(char) <= 126 for char in value)
        or not all(value.split("@"))
    ):
        raise ValueError("Invalid invitation email")
    return value.lower()


def _invite_identity(value: str) -> None:
    _identity_value(value)
    if not value.strip():
        raise ValueError("Invalid external identity value")


class OAuthRepository:
    """Only trusted operators and cryptographically verified provider callers may write."""

    def __init__(self, engine: Engine):
        verify_engine(engine)
        self._engine = engine

    def begin_login(self) -> PendingLogin:
        state, browser, verifier, nonce = [secrets.token_urlsafe(32) for _ in range(4)]
        if not all(valid_session_token(x) for x in (state, browser, verifier, nonce)):
            raise StorageError("Unable to start login")
        challenge = base64.urlsafe_b64encode(sha256(verifier.encode("ascii")).digest())
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    conn.execute(select(func.pg_advisory_xact_lock(741031)))
                    now: datetime = (
                        conn.execute(select(func.clock_timestamp())).scalar_one().astimezone(UTC)
                    )
                    conn.execute(
                        delete(auth_oauth_flows).where(auth_oauth_flows.c.expires_at <= now)
                    )
                    count = conn.execute(
                        select(func.count()).select_from(auth_oauth_flows)
                    ).scalar_one()
                    if count >= 200:
                        raise StorageError("Unable to start login")
                    conn.execute(
                        insert(auth_oauth_flows).values(
                            state_sha256=token_digest(state),
                            cookie_sha256=token_digest(browser),
                            code_verifier=verifier,
                            oidc_nonce=nonce,
                            issued_at=now,
                            expires_at=now + timedelta(seconds=600),
                        )
                    )
                    return PendingLogin(state, browser, challenge.decode().rstrip("="), nonce)
        except SQLAlchemyError:
            raise StorageError("Unable to start login") from None

    def consume_login(self, state: str, browser_token: str) -> ConsumedLogin:
        state_hash, cookie_hash = token_digest(state), token_digest(browser_token)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    row = conn.execute(
                        delete(auth_oauth_flows)
                        .where(
                            auth_oauth_flows.c.state_sha256 == state_hash,
                            auth_oauth_flows.c.cookie_sha256 == cookie_hash,
                            auth_oauth_flows.c.expires_at > func.clock_timestamp(),
                        )
                        .returning(auth_oauth_flows.c.code_verifier, auth_oauth_flows.c.oidc_nonce)
                    ).one_or_none()
                    if row is None:
                        raise AuthenticationDenied("Authentication required")
                    if not all(valid_session_token(x) for x in row):
                        raise StorageError("Unable to consume login")
                    return ConsumedLogin(row.code_verifier, row.oidc_nonce)
        except SQLAlchemyError:
            raise StorageError("Unable to consume login") from None

    def register_invite(
        self, issuer: str, email: str, user_id: UUID, workspace_id: UUID, role: str
    ) -> bool:
        _invite_identity(issuer)
        canonical = _email(email)
        _uuid4(user_id)
        _uuid4(workspace_id)
        if not isinstance(role, str) or role not in {"viewer", "editor", "owner"}:
            raise ValueError("Unsupported membership role")
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    created = conn.execute(
                        pg_insert(auth_identity_invites)
                        .values(
                            issuer=issuer,
                            email=canonical,
                            user_id=user_id,
                            workspace_id=workspace_id,
                            role=role,
                            enabled=True,
                            bound_subject=None,
                        )
                        .on_conflict_do_nothing()
                        .returning(auth_identity_invites.c.user_id)
                    ).scalar_one_or_none()
                    row = (
                        conn.execute(
                            select(auth_identity_invites)
                            .where(
                                auth_identity_invites.c.issuer == issuer,
                                auth_identity_invites.c.email == canonical,
                            )
                            .with_for_update()
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is None or (row["user_id"], row["workspace_id"], row["role"]) != (
                        user_id,
                        workspace_id,
                        role,
                    ):
                        raise StorageConflict("Invitation registration conflicts")
                    return created is not None
        except SQLAlchemyError:
            raise StorageError("Unable to register invitation") from None

    def set_invite_enabled(self, issuer: str, email: str, enabled: bool) -> None:
        _invite_identity(issuer)
        canonical = _email(email)
        _boolean(enabled)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    found = conn.execute(
                        update(auth_identity_invites)
                        .where(
                            auth_identity_invites.c.issuer == issuer,
                            auth_identity_invites.c.email == canonical,
                        )
                        .values(enabled=enabled)
                        .returning(auth_identity_invites.c.user_id)
                    ).scalar_one_or_none()
                    if found is None:
                        raise StorageError("Invitation does not exist")
        except SQLAlchemyError:
            raise StorageError("Unable to update invitation") from None

    def resolve_invited_identity(
        self, issuer: str, subject: str, email: str | None, authoritative_email: bool
    ) -> UUID:
        _invite_identity(issuer)
        _invite_identity(subject)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    # Serialize each verified pair before reading it. A hash collision
                    # merely serializes unrelated pairs; authority is still exact SQL equality.
                    conn.execute(
                        select(
                            func.pg_advisory_xact_lock(
                                func.hashtextextended(issuer + "\x1f" + subject, 741032)
                            )
                        )
                    )
                    user = (
                        conn.execute(
                            select(auth_users)
                            .where(
                                auth_users.c.issuer == issuer,
                                auth_users.c.subject == subject,
                            )
                            .with_for_update()
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if user is not None:
                        if not user["enabled"]:
                            raise AuthenticationDenied("Authentication required")
                        return UUID(str(user["user_id"]))
                    if authoritative_email is not True or email is None:
                        raise AuthenticationDenied("Authentication required")
                    try:
                        canonical = _email(email)
                    except ValueError:
                        raise AuthenticationDenied("Authentication required") from None
                    invite = (
                        conn.execute(
                            select(auth_identity_invites)
                            .where(
                                auth_identity_invites.c.issuer == issuer,
                                auth_identity_invites.c.email == canonical,
                            )
                            .with_for_update()
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if (
                        invite is None
                        or not invite["enabled"]
                        or invite["bound_subject"] is not None
                    ):
                        raise AuthenticationDenied("Authentication required")
                    reserved = conn.execute(
                        select(auth_users.c.user_id).where(
                            auth_users.c.user_id == invite["user_id"]
                        )
                    ).scalar_one_or_none()
                    if reserved is not None:
                        raise StorageConflict("Invitation identity conflicts")
                    conn.execute(
                        insert(auth_users).values(
                            user_id=invite["user_id"],
                            issuer=issuer,
                            subject=subject,
                            enabled=True,
                        )
                    )
                    conn.execute(
                        insert(auth_workspace_memberships).values(
                            user_id=invite["user_id"],
                            workspace_id=invite["workspace_id"],
                            role=invite["role"],
                            active=True,
                        )
                    )
                    conn.execute(
                        update(auth_identity_invites)
                        .where(
                            auth_identity_invites.c.issuer == issuer,
                            auth_identity_invites.c.email == canonical,
                        )
                        .values(bound_subject=subject)
                    )
                    return UUID(str(invite["user_id"]))
        except SQLAlchemyError:
            raise StorageError("Unable to resolve invited identity") from None

    def issue_authorized_session(
        self, issuer: str, subject: str, previous_token: str | None = None
    ) -> IssuedSession:
        _identity_value(issuer)
        _identity_value(subject)
        previous_hash = (
            token_digest(previous_token)
            if isinstance(previous_token, str) and valid_session_token(previous_token)
            else None
        )
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    if previous_hash is not None:
                        conn.execute(
                            select(auth_sessions)
                            .where(auth_sessions.c.token_sha256 == previous_hash)
                            .with_for_update()
                        ).one_or_none()
                    user = (
                        conn.execute(
                            select(auth_users)
                            .where(
                                auth_users.c.issuer == issuer,
                                auth_users.c.subject == subject,
                            )
                            .with_for_update()
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if user is None or not user["enabled"]:
                        raise AuthenticationDenied("Authentication required")
                    memberships = conn.execute(
                        select(auth_workspace_memberships)
                        .where(
                            auth_workspace_memberships.c.user_id == user["user_id"],
                            auth_workspace_memberships.c.active.is_(True),
                        )
                        .order_by(auth_workspace_memberships.c.workspace_id)
                        .with_for_update()
                    ).all()
                    if not memberships:
                        raise AuthenticationDenied("Authentication required")
                    now: datetime = (
                        conn.execute(select(func.clock_timestamp())).scalar_one().astimezone(UTC)
                    )
                    token = secrets.token_urlsafe(32)
                    expires = now + timedelta(seconds=28800)
                    conn.execute(
                        insert(auth_sessions).values(
                            token_sha256=token_digest(token),
                            user_id=user["user_id"],
                            issued_at=now,
                            expires_at=expires,
                            last_activity_at=now,
                            revoked=False,
                        )
                    )
                    if previous_hash is not None:
                        conn.execute(
                            update(auth_sessions)
                            .where(auth_sessions.c.token_sha256 == previous_hash)
                            .values(revoked=True)
                        )
                    return IssuedSession(token, expires)
        except SQLAlchemyError:
            raise StorageError("Unable to issue authorized session") from None
