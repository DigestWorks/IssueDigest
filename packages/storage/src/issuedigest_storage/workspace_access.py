"""Protected session browsing and validated evidence catalogs in one RR transaction."""

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from issuedigest_domain import EvidenceCatalog, EvidenceSummary, SessionInfo, WorkspaceMembership
from pydantic import ValidationError
from sqlalchemy import Connection, Engine, func, select, update
from sqlalchemy.exc import SQLAlchemyError

from .auth_schema import auth_sessions, auth_users, auth_workspace_memberships
from .engine import verify_engine
from .repository import EvidenceRepository, StorageError, _uuid4
from .schema import evidence_snapshots
from .sessions import AuthenticationDenied, token_digest


class WorkspaceAccessRepository:
    """Authority and integrity are rechecked before any metadata leaves storage."""

    def __init__(self, engine: Engine):
        verify_engine(engine)
        self._engine = engine

    def _transaction[T](self, operation: Callable[[Connection], T]) -> T:
        retries_remaining = 2
        while True:
            try:
                with self._engine.connect().execution_options(
                    isolation_level="REPEATABLE READ"
                ) as conn:
                    with conn.begin():
                        return operation(conn)
            except SQLAlchemyError as error:
                if (
                    getattr(getattr(error, "orig", None), "sqlstate", None) == "40001"
                    and retries_remaining > 0
                ):
                    retries_remaining -= 1
                    continue
                raise StorageError("Unable to load protected workspace") from None
            except (ValidationError, ValueError, TypeError, KeyError):
                raise StorageError("Unable to load protected workspace") from None

    @staticmethod
    def _authorize(conn: Connection, digest: str) -> UUID:
        session = (
            conn.execute(
                select(auth_sessions)
                .where(auth_sessions.c.token_sha256 == digest)
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        now: datetime = conn.execute(select(func.clock_timestamp())).scalar_one()
        if (
            session is None
            or session["revoked"]
            or session["expires_at"] <= now
            or session["last_activity_at"] <= now - timedelta(seconds=1800)
        ):
            raise AuthenticationDenied("Authentication required")
        user = (
            conn.execute(
                select(auth_users)
                .where(auth_users.c.user_id == session["user_id"])
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if user is None or not user["enabled"]:
            raise AuthenticationDenied("Authentication required")
        user_id = UUID(str(user["user_id"]))
        _uuid4(user_id)
        return user_id

    @staticmethod
    def _refresh(conn: Connection, digest: str) -> None:
        conn.execute(
            update(auth_sessions)
            .where(auth_sessions.c.token_sha256 == digest)
            .values(last_activity_at=func.clock_timestamp())
        )

    def get_session(self, token: str) -> SessionInfo:
        digest = token_digest(token)

        def read(conn: Connection) -> SessionInfo:
            user_id = self._authorize(conn, digest)
            rows = (
                conn.execute(
                    select(auth_workspace_memberships)
                    .where(
                        auth_workspace_memberships.c.user_id == user_id,
                        auth_workspace_memberships.c.active.is_(True),
                    )
                    .order_by(auth_workspace_memberships.c.workspace_id)
                    .limit(101)
                    .with_for_update()
                )
                .mappings()
                .all()
            )
            info = SessionInfo(
                user_id=user_id,
                memberships=tuple(
                    WorkspaceMembership(workspace_id=row["workspace_id"], role=row["role"])
                    for row in rows
                ),
            )
            self._refresh(conn, digest)
            return info

        return self._transaction(read)

    def list_evidence(
        self, token: str, workspace_id: UUID, limit: int = 20
    ) -> EvidenceCatalog | None:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError("Catalog limit must be an integer from 1 to 50")
        _uuid4(workspace_id)
        digest = token_digest(token)

        def read(conn: Connection) -> EvidenceCatalog | None:
            user_id = self._authorize(conn, digest)
            membership = (
                conn.execute(
                    select(auth_workspace_memberships)
                    .where(
                        auth_workspace_memberships.c.user_id == user_id,
                        auth_workspace_memberships.c.workspace_id == workspace_id,
                        auth_workspace_memberships.c.active.is_(True),
                    )
                    .with_for_update()
                )
                .mappings()
                .one_or_none()
            )
            if membership is None:
                return None
            WorkspaceMembership(workspace_id=membership["workspace_id"], role=membership["role"])
            snapshots = (
                conn.execute(
                    select(evidence_snapshots.c.snapshot_id)
                    .where(
                        evidence_snapshots.c.workspace_id == workspace_id,
                    )
                    .order_by(
                        evidence_snapshots.c.created_at.desc(), evidence_snapshots.c.snapshot_id
                    )
                    .limit(limit + 1)
                )
                .scalars()
                .all()
            )
            items = []
            for snapshot in snapshots[:limit]:
                bundle = EvidenceRepository._load(conn, workspace_id, snapshot)
                if bundle is None:
                    raise StorageError("Unable to load protected workspace")
                items.append(
                    EvidenceSummary(
                        snapshot_id=snapshot,
                        document_id=bundle.document.document_id,
                        provider=bundle.document.provider,
                        source_id=bundle.document.source_id,
                        source_kind=bundle.document.source_kind,
                        canonical_url=bundle.document.canonical_url,
                        collected_at=bundle.version.collected_at,
                        excerpt=bundle.representation.text[:160],
                        citation_count=len(bundle.citations),
                    )
                )
            catalog = EvidenceCatalog(
                workspace_id=workspace_id, items=tuple(items), has_more=len(snapshots) > limit
            )
            self._refresh(conn, digest)
            return catalog

        return self._transaction(read)
