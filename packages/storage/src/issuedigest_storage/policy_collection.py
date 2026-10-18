"""Explicit leased PostgreSQL policy journal. No HTTP, connector or worker imports."""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Connection, Engine, insert, select, text, update
from sqlalchemy.exc import SQLAlchemyError

from .policy_collection_schema import policy_collection_attempts as attempts
from .policy_collection_schema import policy_collection_channels as channels

MAX_CAPTURE_BYTES = 8 * 1024 * 1024 + 16384
MAX_REPORT_BYTES = 64 * 1024
FailureCode = Literal["capture_failed", "validation_failed", "interrupted"]


class PolicyCollectionError(Exception):
    """Fixed private storage failure; never contains supplied or stored values."""

    def __init__(self) -> None:
        super().__init__("Policy collection storage unavailable")


class PolicyCollectionCommitUnknown(PolicyCollectionError):
    """Commit acknowledgement was lost; no automatic retry or terminal overwrite."""

    def __init__(self) -> None:
        Exception.__init__(self, "Policy collection commit unknown")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True, hide_input_in_errors=True)


class PolicyCollectionConfig(_Frozen):
    schema_version: Literal[1]
    expected_database: str = Field(min_length=1, max_length=63)
    collection_id: UUID4
    news_ids: tuple[str, ...] = Field(min_length=1, max_length=2)
    minimum_interval_seconds: int = Field(ge=60, le=86400)
    max_age_seconds: int = Field(ge=60, le=604800)
    max_attempts: int = Field(ge=1, le=4096)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid version")
        return value

    @field_validator("expected_database")
    @classmethod
    def _database(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,62}", value):
            raise ValueError("Invalid database")
        return value

    @field_validator("news_ids")
    @classmethod
    def _news(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value) or any(not re.fullmatch(r"[0-9]{9}", n) for n in value):
            raise ValueError("Invalid scope")
        return tuple(sorted(value))

    @model_validator(mode="after")
    def _interval(self) -> PolicyCollectionConfig:
        if self.max_age_seconds < self.minimum_interval_seconds:
            raise ValueError("Invalid age")
        return self


class PolicyCollectionAttempt(_Frozen):
    attempt_id: UUID4
    sequence: int = Field(ge=1, le=4096)
    state: Literal["running", "succeeded", "failed"]
    started_at: datetime
    finished_at: datetime | None
    failure_code: FailureCode | None


class PolicyCollectionStatus(_Frozen):
    attempt_count: int
    latest: PolicyCollectionAttempt | None
    last_success: PolicyCollectionAttempt | None
    age_seconds: float | None
    stale: bool


class PolicyCollectionStart(_Frozen):
    outcome: Literal["started", "not_due", "attempt_limit"]
    attempt: PolicyCollectionAttempt | None = None


class PolicyCollectionBaseline(_Frozen):
    attempt: PolicyCollectionAttempt
    capture_bytes: bytes = Field(repr=False)
    capture_sha256: str
    report_bytes: bytes = Field(repr=False)
    report_sha256: str


def _config(value: PolicyCollectionConfig) -> PolicyCollectionConfig:
    if not isinstance(value, PolicyCollectionConfig):
        raise PolicyCollectionError()
    return PolicyCollectionConfig.model_validate(
        {name: getattr(value, name) for name in PolicyCollectionConfig.model_fields}
    )


def _time(value: datetime) -> datetime:
    try:
        if type(value) is not datetime or value.tzinfo is None or value.utcoffset() is None:
            raise PolicyCollectionError()
        return value.astimezone(UTC)
    except Exception:
        raise PolicyCollectionError() from None


def _now() -> datetime:
    return datetime.now(UTC)


def _payload(config: PolicyCollectionConfig) -> tuple[dict[str, Any], str]:
    payload = config.model_dump(mode="json")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return payload, sha256(raw).hexdigest()


def _database(conn: Connection, config: PolicyCollectionConfig) -> None:
    if conn.scalar(text("SELECT current_database()")) != config.expected_database:
        raise PolicyCollectionError()


def _binding(conn: Connection, config: PolicyCollectionConfig) -> bool:
    row = (
        conn.execute(select(channels).where(channels.c.collection_id == config.collection_id))
        .mappings()
        .one_or_none()
    )
    if row is None:
        return False
    payload, digest = _payload(config)
    stored_raw = json.dumps(
        row["config"], sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()
    if (
        row["config"] != payload
        or row["config_sha256"] != digest
        or sha256(stored_raw).hexdigest() != digest
    ):
        raise PolicyCollectionError()
    _time(row["created_at"])
    return True


_META = (
    attempts.c.attempt_id,
    attempts.c.sequence,
    attempts.c.state,
    attempts.c.started_at,
    attempts.c.finished_at,
    attempts.c.failure_code,
)


def _attempt(row: Mapping[Any, Any]) -> PolicyCollectionAttempt:
    attempt = PolicyCollectionAttempt.model_validate({c.name: row[c.name] for c in _META})
    _time(attempt.started_at)
    if attempt.state == "running":
        if attempt.finished_at is not None or attempt.failure_code is not None:
            raise PolicyCollectionError()
    else:
        if attempt.finished_at is None or _time(attempt.finished_at) < attempt.started_at:
            raise PolicyCollectionError()
        if (attempt.state == "failed") != (attempt.failure_code is not None):
            raise PolicyCollectionError()
    return attempt


def _history(
    conn: Connection, config: PolicyCollectionConfig, now: datetime | None
) -> PolicyCollectionStatus:
    rows = (
        conn.execute(
            select(*_META)
            .where(attempts.c.collection_id == config.collection_id)
            .order_by(attempts.c.sequence)
        )
        .mappings()
        .all()
    )
    if len(rows) > config.max_attempts:
        raise PolicyCollectionError()
    parsed = [_attempt(r) for r in rows]
    previous: PolicyCollectionAttempt | None = None
    for index, attempt in enumerate(parsed, 1):
        if attempt.sequence != index or (
            now is not None
            and (
                attempt.started_at > now
                or (attempt.finished_at is not None and attempt.finished_at > now)
            )
        ):
            raise PolicyCollectionError()
        if previous is not None and (
            previous.state == "running" or attempt.started_at < cast(datetime, previous.finished_at)
        ):
            raise PolicyCollectionError()
        previous = attempt
    last_success = next((a for a in reversed(parsed) if a.state == "succeeded"), None)
    age = (
        (now - cast(datetime, last_success.finished_at)).total_seconds()
        if last_success and now is not None
        else None
    )
    return PolicyCollectionStatus(
        attempt_count=len(parsed),
        latest=previous,
        last_success=last_success,
        age_seconds=age,
        stale=age is None or age > config.max_age_seconds,
    )


class PolicyCollectionRepository:
    def __init__(self, engine: Engine):
        # Constructing a repository performs no connection, migration or collection.
        self._engine = engine

    def _validate(self, config: PolicyCollectionConfig) -> PolicyCollectionConfig:
        try:
            config = _config(config)
            if (
                self._engine.dialect.name != "postgresql"
                or self._engine.dialect.driver != "psycopg"
                or self._engine.url.database != config.expected_database
            ):
                raise PolicyCollectionError()
            return config
        except Exception:
            raise PolicyCollectionError() from None

    def status(
        self, config: PolicyCollectionConfig, *, now: datetime | None = None
    ) -> PolicyCollectionStatus:
        try:
            config = self._validate(config)
            if now is not None:
                now = _time(now)
            with self._engine.connect().execution_options(
                isolation_level="REPEATABLE READ", postgresql_readonly=True
            ) as conn:
                with conn.begin():
                    _database(conn, config)
                    bound = _binding(conn, config)
                    # The metadata read has established the consistent snapshot. Sampling
                    # earlier can falsely reject a healthy poll committed before that read.
                    observed_at = _time(_now()) if now is None else now
                    state = _history(conn, config, observed_at)
                    if not bound and state.attempt_count:
                        raise PolicyCollectionError()
                    return state
        except Exception:
            raise PolicyCollectionError() from None

    @contextmanager
    def lease(self, config: PolicyCollectionConfig) -> Iterator[PolicyCollectionSession | None]:
        config = self._validate(config)
        conn: Connection | None = None
        session: PolicyCollectionSession | None = None
        acquired = False
        try:
            try:
                conn = self._engine.connect().execution_options(
                    isolation_level="READ COMMITTED", postgresql_readonly=False
                )
                _database(conn, config)
                acquired = bool(conn.scalar(text("SELECT pg_try_advisory_lock(104704, 2)")))
                conn.commit()
                if acquired:
                    session = PolicyCollectionSession(conn, config)
            except Exception:
                raise PolicyCollectionError() from None
            yield session
        finally:
            propagating = sys.exc_info()[0] is not None
            cleanup_failed = False
            if session is not None:
                session._closed = True
            if conn is not None:
                try:
                    if conn.closed or conn.invalidated:
                        cleanup_failed = session is None or not session._poisoned
                    else:
                        conn.rollback()
                        if acquired:
                            if (
                                session is not None
                                and conn.connection.driver_connection is not session._driver
                            ):
                                raise PolicyCollectionError()
                            released = conn.scalar(text("SELECT pg_advisory_unlock(104704, 2)"))
                            if not released and (session is None or not session._poisoned):
                                raise PolicyCollectionError()
                            conn.commit()
                except Exception:
                    cleanup_failed = True
                    conn.invalidate()
                finally:
                    try:
                        conn.close()
                    except Exception:
                        cleanup_failed = True
                        conn.invalidate()
            if cleanup_failed and not propagating:
                raise PolicyCollectionError() from None


class PolicyCollectionSession:
    """One explicit dedicated session lock; methods never open replacement connections."""

    def __init__(self, connection: Connection, config: PolicyCollectionConfig):
        self._connection = connection
        self._config = config
        self._driver = connection.connection.driver_connection
        self._pid = connection.scalar(text("SELECT pg_backend_pid()"))
        connection.commit()
        self._closed = False
        self._poisoned = False
        self._active: UUID | None = None

    def _guard(self) -> None:
        conn = self._connection
        if (
            self._closed
            or self._poisoned
            or conn.closed
            or conn.invalidated
            or conn.connection.driver_connection is not self._driver
        ):
            self._poisoned = True
            raise PolicyCollectionError()
        _database(conn, self._config)
        owned = conn.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype='advisory' "
                "AND pid=pg_backend_pid() AND classid=104704 AND objid=2 "
                "AND objsubid=2 AND granted) AND pg_backend_pid()=:pid"
            ),
            {"pid": self._pid},
        )
        if not owned:
            self._poisoned = True
            raise PolicyCollectionError()

    def _transaction[T](self, operation: Callable[[Connection], T], *, write: bool = False) -> T:
        conn = self._connection
        try:
            self._guard()
            result = operation(conn)
            if write:
                self._guard()
                try:
                    conn.commit()
                except Exception:
                    self._poisoned = True
                    raise PolicyCollectionCommitUnknown() from None
            else:
                conn.rollback()
            return result
        except PolicyCollectionCommitUnknown:
            raise
        except Exception as error:
            if isinstance(error, SQLAlchemyError):
                self._poisoned = True
            try:
                conn.rollback()
            except Exception:
                self._poisoned = True
            raise PolicyCollectionError() from None

    def start(self, *, now: datetime) -> PolicyCollectionStart:
        now = _time(now)

        def operation(conn: Connection) -> PolicyCollectionStart:
            if self._active is not None:
                raise PolicyCollectionError()
            if not _binding(conn, self._config):
                payload, digest = _payload(self._config)
                conn.execute(
                    insert(channels).values(
                        collection_id=self._config.collection_id,
                        config=payload,
                        config_sha256=digest,
                        created_at=now,
                    )
                )
            state = _history(conn, self._config, now)
            if state.latest and state.latest.state == "running":
                conn.execute(
                    update(attempts)
                    .where(
                        attempts.c.attempt_id == state.latest.attempt_id,
                        attempts.c.state == "running",
                    )
                    .values(state="failed", failure_code="interrupted", finished_at=now)
                )
            if (
                state.latest
                and (now - state.latest.started_at).total_seconds()
                < self._config.minimum_interval_seconds
            ):
                return PolicyCollectionStart(outcome="not_due")
            if state.attempt_count >= self._config.max_attempts:
                return PolicyCollectionStart(outcome="attempt_limit")
            attempt = PolicyCollectionAttempt(
                attempt_id=uuid4(),
                sequence=state.attempt_count + 1,
                state="running",
                started_at=now,
                finished_at=None,
                failure_code=None,
            )
            conn.execute(
                insert(attempts).values(
                    collection_id=self._config.collection_id, **attempt.model_dump()
                )
            )
            return PolicyCollectionStart(outcome="started", attempt=attempt)

        result = self._transaction(operation, write=True)
        if result.attempt is not None:
            self._active = result.attempt.attempt_id
        return result

    def baseline(self) -> PolicyCollectionBaseline | None:
        def operation(conn: Connection) -> PolicyCollectionBaseline | None:
            is_bound = _binding(conn, self._config)
            state = _history(conn, self._config, None)
            if not is_bound and state.attempt_count:
                raise PolicyCollectionError()
            row = (
                conn.execute(
                    select(attempts)
                    .where(
                        attempts.c.collection_id == self._config.collection_id,
                        attempts.c.state == "succeeded",
                    )
                    .order_by(attempts.c.sequence.desc())
                    .limit(1)
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            attempt = _attempt(row)
            for name, bound in (("capture", MAX_CAPTURE_BYTES), ("report", MAX_REPORT_BYTES)):
                raw = row[f"{name}_bytes"]
                if (
                    type(raw) is not bytes
                    or not 1 <= len(raw) <= bound
                    or sha256(raw).hexdigest() != row[f"{name}_sha256"]
                ):
                    raise PolicyCollectionError()
            return PolicyCollectionBaseline(
                attempt=attempt,
                capture_bytes=row["capture_bytes"],
                capture_sha256=row["capture_sha256"],
                report_bytes=row["report_bytes"],
                report_sha256=row["report_sha256"],
            )

        return self._transaction(operation)

    def succeed(
        self, attempt_id: UUID, capture_bytes: bytes, report_bytes: bytes, *, finished_at: datetime
    ) -> None:
        for raw, bound in ((capture_bytes, MAX_CAPTURE_BYTES), (report_bytes, MAX_REPORT_BYTES)):
            if type(raw) is not bytes or not 1 <= len(raw) <= bound:
                raise PolicyCollectionError()
        self._terminal(
            attempt_id,
            finished_at,
            state="succeeded",
            failure_code=None,
            capture_bytes=capture_bytes,
            capture_sha256=sha256(capture_bytes).hexdigest(),
            report_bytes=report_bytes,
            report_sha256=sha256(report_bytes).hexdigest(),
        )

    def fail(self, attempt_id: UUID, failure_code: FailureCode, *, finished_at: datetime) -> None:
        if type(failure_code) is not str or failure_code not in {
            "capture_failed",
            "validation_failed",
        }:
            raise PolicyCollectionError()
        self._terminal(attempt_id, finished_at, state="failed", failure_code=failure_code)

    def _terminal(self, attempt_id: UUID, finished_at: datetime, **values: Any) -> None:
        finished_at = _time(finished_at)
        if type(attempt_id) is not UUID or attempt_id.version != 4 or attempt_id != self._active:
            raise PolicyCollectionError()

        def operation(conn: Connection) -> None:
            if not _binding(conn, self._config):
                raise PolicyCollectionError()
            state = _history(conn, self._config, finished_at)
            if (
                state.latest is None
                or state.latest.attempt_id != attempt_id
                or state.latest.state != "running"
            ):
                raise PolicyCollectionError()
            result = conn.execute(
                update(attempts)
                .where(
                    attempts.c.attempt_id == attempt_id,
                    attempts.c.collection_id == self._config.collection_id,
                    attempts.c.state == "running",
                )
                .values(finished_at=finished_at, **values)
            )
            if result.rowcount != 1:
                raise PolicyCollectionError()

        self._transaction(operation, write=True)
        self._active = None
