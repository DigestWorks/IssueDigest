"""Internal administration for already verified identities and approved memberships."""

from uuid import UUID

from sqlalchemy import Engine, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from .auth_schema import auth_users, auth_workspace_memberships
from .engine import verify_engine
from .repository import StorageConflict, StorageError, _uuid4


def _identity_value(value: str) -> None:
    if not isinstance(value, str) or not value or "\x00" in value or len(value) > 256:
        raise ValueError("Invalid external identity value")


def _boolean(value: bool) -> None:
    if not isinstance(value, bool):
        raise ValueError("A boolean is required")


class IdentityRepository:
    """Trusted connector/admin boundary; no token verification or invitation approval."""

    def __init__(self, engine: Engine):
        verify_engine(engine)
        self._engine = engine

    def register_identity(self, user_id: UUID, issuer: str, subject: str) -> UUID:
        """Preserve the exact issuer/subject pair; identical registration is idempotent."""
        _uuid4(user_id)
        _identity_value(issuer)
        _identity_value(subject)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    conn.execute(
                        insert(auth_users)
                        .values(user_id=user_id, issuer=issuer, subject=subject, enabled=True)
                        .on_conflict_do_nothing()
                    )
                    row = (
                        conn.execute(select(auth_users).where(auth_users.c.user_id == user_id))
                        .mappings()
                        .one_or_none()
                    )
                    if row is None or row["issuer"] != issuer or row["subject"] != subject:
                        raise StorageConflict("External identity registration conflicts")
                    return user_id
        except SQLAlchemyError:
            raise StorageError("Unable to register external identity") from None

    def set_enabled(self, user_id: UUID, enabled: bool) -> None:
        _uuid4(user_id)
        _boolean(enabled)
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    found = conn.execute(
                        update(auth_users)
                        .where(auth_users.c.user_id == user_id)
                        .values(enabled=enabled)
                        .returning(auth_users.c.user_id)
                    ).scalar_one_or_none()
                    if found is None:
                        raise StorageError("User does not exist")
        except SQLAlchemyError:
            raise StorageError("Unable to update user") from None

    def set_membership(
        self, user_id: UUID, workspace_id: UUID, role: str, active: bool = True
    ) -> None:
        """Apply an already approved grant/revocation within an existing evidence namespace."""
        _uuid4(user_id)
        _uuid4(workspace_id)
        _boolean(active)
        if not isinstance(role, str) or role not in {"viewer", "editor", "owner"}:
            raise ValueError("Unsupported membership role")
        try:
            with self._engine.connect().execution_options(isolation_level="READ COMMITTED") as conn:
                with conn.begin():
                    conn.execute(
                        insert(auth_workspace_memberships)
                        .values(
                            user_id=user_id, workspace_id=workspace_id, role=role, active=active
                        )
                        .on_conflict_do_update(
                            index_elements=["user_id", "workspace_id"],
                            set_={"role": role, "active": active},
                        )
                    )
        except SQLAlchemyError:
            raise StorageError("Unable to update membership") from None
