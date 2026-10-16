"""One database transaction authorizes a session and revalidates existing evidence."""

from datetime import datetime, timedelta
from uuid import UUID

from issuedigest_domain import EvidenceBundle
from sqlalchemy import Engine, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from .auth_schema import auth_sessions, auth_users, auth_workspace_memberships
from .engine import verify_engine
from .repository import EvidenceRepository, StorageError, _uuid4
from .session_policy import SESSION_IDLE_TIMEOUT_SECONDS
from .sessions import AuthenticationDenied, token_digest


class EvidenceAccessRepository:
    """Refresh only successful permitted reads; recheck every authority on each request."""

    def __init__(self, engine: Engine):
        verify_engine(engine)
        self._engine = engine

    def load_evidence(
        self, token: str, workspace_id: UUID, snapshot_id: UUID
    ) -> EvidenceBundle | None:
        _uuid4(workspace_id)
        _uuid4(snapshot_id)
        digest = token_digest(token)
        # A conflicting session activity update can abort RR reads. Retry the
        # entire transaction so each attempt rechecks all authority and integrity.
        retries_remaining = 2
        while True:
            try:
                with self._engine.connect().execution_options(
                    isolation_level="REPEATABLE READ"
                ) as conn:
                    with conn.begin():
                        session = (
                            conn.execute(
                                select(auth_sessions, auth_users.c.enabled)
                                .join(auth_users)
                                .where(auth_sessions.c.token_sha256 == digest)
                                .with_for_update(of=[auth_sessions, auth_users])
                            )
                            .mappings()
                            .one_or_none()
                        )
                        now: datetime = conn.execute(select(func.clock_timestamp())).scalar_one()
                        if (
                            session is None
                            or session["revoked"]
                            or not session["enabled"]
                            or session["expires_at"] <= now
                            or session["last_activity_at"]
                            <= now - timedelta(seconds=SESSION_IDLE_TIMEOUT_SECONDS)
                        ):
                            raise AuthenticationDenied("Authentication required")
                        membership = conn.execute(
                            select(auth_workspace_memberships)
                            .where(
                                auth_workspace_memberships.c.user_id == session["user_id"],
                                auth_workspace_memberships.c.workspace_id == workspace_id,
                                auth_workspace_memberships.c.active.is_(True),
                            )
                            .with_for_update()
                        ).one_or_none()
                        if membership is None:
                            return None
                        bundle = EvidenceRepository._load(conn, workspace_id, snapshot_id)
                        if bundle is not None:
                            conn.execute(
                                update(auth_sessions)
                                .where(auth_sessions.c.token_sha256 == digest)
                                .values(last_activity_at=func.clock_timestamp())
                            )
                        return bundle
            except SQLAlchemyError as error:
                if (
                    getattr(getattr(error, "orig", None), "sqlstate", None) == "40001"
                    and retries_remaining > 0
                ):
                    retries_remaining -= 1
                    continue
                raise StorageError("Unable to load protected evidence") from None
