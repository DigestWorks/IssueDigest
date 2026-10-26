"""Private opaque durable jobs; external call intent is committed before dispatch."""

import json
import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Index,
    MetaData,
    Numeric,
    String,
    Table,
    UniqueConstraint,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine

from .repository import EvidenceRepository, StorageCorruption, _uuid4
from .research import (
    ResearchBudgetExceeded,
    ResearchConflict,
    ResearchForbidden,
    ResearchRepository,
)
from .research_schema import research_budget_months

metadata = MetaData()
evidence_jobs = Table(
    "evidence_jobs",
    metadata,
    *[
        Column(n, PGUUID(as_uuid=True), primary_key=n == "job_id", nullable=False)
        for n in ("job_id", "workspace_id", "actor_id", "request_id", "snapshot_id")
    ],
    *[
        Column(n, String, nullable=False)
        for n in ("question", "model", "profile", "source_sha256", "input_sha256", "status")
    ],
    Column("reservation_usd", Numeric(6, 2), nullable=False),
    *[
        Column(n, String, nullable=True)
        for n in ("prompt_sha256", "instructions_sha256", "receipt_sha256", "reason")
    ],
    Column("receipt", JSONB),
    Column("known_usage", JSONB),
    Column("usage_complete", Boolean, nullable=False, server_default="false"),
    Column("stream_closed", Boolean, nullable=False, server_default="false"),
    UniqueConstraint("workspace_id", "actor_id", "request_id"),
    CheckConstraint(
        "status IN ('pending','running','completed','failed','cancelled','indeterminate')"
    ),
    CheckConstraint("model = 'gpt-6.1-sol' AND profile = 'guarded-question-evidence-v2'"),
    CheckConstraint("reservation_usd > 0 AND reservation_usd <= 10"),
)
Index(
    "evidence_jobs_active",
    evidence_jobs.c.workspace_id,
    unique=True,
    postgresql_where=evidence_jobs.c.status.in_(["pending", "running"]),
)


def digest(value: Any) -> str:
    return sha256(
        json.dumps(
            value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def source_digest(source: tuple[UUID, EvidenceBundle, SourcePresentation]) -> str:
    sid, bundle, presentation = source
    return digest(
        dict(
            snapshot_id=str(sid),
            bundle=bundle.model_dump(mode="json"),
            presentation=presentation.model_dump(mode="json"),
        )
    )


@dataclass(frozen=True)
class EvidenceJob:
    job_id: UUID
    workspace_id: UUID
    snapshot_id: UUID
    question: str
    model: str
    status: str
    source_sha256: str
    prompt_sha256: str | None
    instructions_sha256: str | None
    receipt: dict[str, Any] | None
    known_usage: dict[str, int] | None
    usage_complete: bool
    stream_closed: bool
    reason: str | None


class EvidenceJobRepository:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._base = ResearchRepository(engine)

    @staticmethod
    def _lock_jobs(conn: Connection) -> None:
        # Session/member checks also lock shared auth_users across workspaces.
        # Order every short new-job SQL transaction before those and job row locks;
        # this transaction gate is never held across native I/O.
        key = int.from_bytes(
            sha256(b"issuedigest:evidence-jobs:transaction-v1").digest()[:8],
            "big",
            signed=True,
        )
        conn.scalar(select(func.pg_advisory_xact_lock(key)))

    @staticmethod
    def _row(conn: Connection, job_id: UUID) -> Any:
        _uuid4(job_id)
        EvidenceJobRepository._lock_jobs(conn)
        row = (
            conn.execute(
                select(evidence_jobs).where(evidence_jobs.c.job_id == job_id).with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ResearchConflict("Evidence job unavailable")
        return row

    @staticmethod
    def _dto(row: Any) -> EvidenceJob:
        receipt = row["receipt"] if row["status"] == "completed" else None
        if row["model"] != "gpt-6.1-sol" or row["profile"] != "guarded-question-evidence-v2":
            raise StorageCorruption("Evidence job identity changed")
        usage = row["known_usage"]
        if usage is not None and (
            type(usage) is not dict
            or set(usage) != {"input_tokens", "output_tokens", "requests"}
            or any(type(value) is not int or value < 0 for value in usage.values())
            or usage["requests"] != 1
        ):
            raise StorageCorruption("Evidence job usage changed")
        if row["status"] == "completed" and type(receipt) is not dict:
            raise StorageCorruption("Evidence job receipt unavailable")
        if receipt is not None and digest(receipt) != row["receipt_sha256"]:
            raise StorageCorruption("Evidence job receipt changed")
        fields: dict[str, Any] = {
            n: receipt if n == "receipt" else row[n] for n in EvidenceJob.__dataclass_fields__
        }
        return EvidenceJob(**fields)

    @staticmethod
    def _current(conn: Connection, row: Any) -> tuple[UUID, EvidenceBundle, SourcePresentation]:
        if not ResearchRepository._member(conn, row["actor_id"], row["workspace_id"], write=True):
            raise ResearchForbidden("Evidence job authority unavailable")
        bundle = EvidenceRepository._load(conn, row["workspace_id"], row["snapshot_id"])
        if bundle is None:
            raise ResearchConflict("Evidence job source unavailable")
        presentation = ResearchRepository._presentation(
            conn, row["workspace_id"], row["snapshot_id"], bundle
        )
        source = row["snapshot_id"], bundle, presentation
        if source_digest(source) != row["source_sha256"]:
            raise StorageCorruption("Evidence job source changed")
        identity = dict(
            snapshot_id=str(row["snapshot_id"]),
            source_sha256=row["source_sha256"],
            question=row["question"],
            model=row["model"],
            reservation_usd=str(row["reservation_usd"]),
        )
        if digest(identity) != row["input_sha256"]:
            raise StorageCorruption("Evidence job input changed")
        return source

    def submit(
        self,
        token: str,
        workspace_id: UUID,
        request_id: UUID,
        snapshot_id: UUID,
        question: str,
        *,
        model: str,
        reservation_usd: Decimal,
    ) -> EvidenceJob | None:
        for value in (workspace_id, request_id, snapshot_id):
            _uuid4(value)
        if (
            type(question) is not str
            or not question.strip()
            or len(question) > 1500
            or type(model) is not str
            or model != "gpt-6.1-sol"
        ):
            raise ValueError("Invalid evidence job input")
        if (
            type(reservation_usd) is not Decimal
            or not reservation_usd.is_finite()
            or not Decimal("0") < reservation_usd <= Decimal("10")
            or reservation_usd != reservation_usd.quantize(Decimal(".01"))
        ):
            raise ValueError("Invalid evidence reservation")
        reservation_usd = reservation_usd.quantize(Decimal(".01"))

        def save(conn: Connection) -> EvidenceJob | None:
            self._lock_jobs(conn)
            actor = self._base._actor(conn, token, workspace_id, write=True)
            if actor is None:
                return None
            bundle = EvidenceRepository._load(conn, workspace_id, snapshot_id)
            if bundle is None:
                raise ResearchConflict("Evidence source unavailable")
            presentation = self._base._presentation(conn, workspace_id, snapshot_id, bundle)
            hashed = source_digest((snapshot_id, bundle, presentation))
            identity = digest(
                dict(
                    snapshot_id=str(snapshot_id),
                    source_sha256=hashed,
                    question=question,
                    model=model,
                    reservation_usd=str(reservation_usd),
                )
            )
            prior = (
                conn.execute(
                    select(evidence_jobs).where(
                        evidence_jobs.c.workspace_id == workspace_id,
                        evidence_jobs.c.actor_id == actor,
                        evidence_jobs.c.request_id == request_id,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                if prior["input_sha256"] != identity:
                    raise ResearchConflict("Evidence request changed")
                return self._dto(prior)
            month = conn.scalar(select(func.to_char(func.clock_timestamp(), "YYYY-MM")))
            conn.execute(
                pg_insert(research_budget_months).values(month=month).on_conflict_do_nothing()
            )
            budget = (
                conn.execute(
                    select(research_budget_months)
                    .where(research_budget_months.c.month == month)
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if budget["reservation_count"] >= 40 or budget[
                "reserved_usd"
            ] + reservation_usd > Decimal("10"):
                raise ResearchBudgetExceeded("Monthly research budget reached")
            conn.execute(
                update(research_budget_months)
                .where(research_budget_months.c.month == month)
                .values(
                    reserved_usd=budget["reserved_usd"] + reservation_usd,
                    reservation_count=budget["reservation_count"] + 1,
                )
            )
            job_id = uuid4()
            conn.execute(
                insert(evidence_jobs).values(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    actor_id=actor,
                    request_id=request_id,
                    snapshot_id=snapshot_id,
                    question=question,
                    model=model,
                    profile="guarded-question-evidence-v2",
                    source_sha256=hashed,
                    input_sha256=identity,
                    reservation_usd=reservation_usd,
                    status="pending",
                )
            )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(save)

    def prepare(
        self, job_id: UUID
    ) -> tuple[EvidenceJob, tuple[UUID, EvidenceBundle, SourcePresentation]]:
        def read(
            conn: Connection,
        ) -> tuple[EvidenceJob, tuple[UUID, EvidenceBundle, SourcePresentation]]:
            row = self._row(conn, job_id)
            return self._dto(row), self._current(conn, row)

        return self._base._transaction(read)

    def get(self, token: str, workspace_id: UUID, job_id: UUID) -> EvidenceJob | None:
        _uuid4(workspace_id)
        _uuid4(job_id)

        def read(conn: Connection) -> EvidenceJob | None:
            self._lock_jobs(conn)
            if self._base._actor(conn, token, workspace_id) is None:
                return None
            row = self._row(conn, job_id)
            if row["workspace_id"] != workspace_id:
                return None
            self._current(conn, row)
            return self._dto(row)

        return self._base._transaction(read)

    def cancel(self, token: str, workspace_id: UUID, job_id: UUID) -> EvidenceJob | None:
        _uuid4(workspace_id)
        _uuid4(job_id)

        def stop(conn: Connection) -> EvidenceJob | None:
            self._lock_jobs(conn)
            if self._base._actor(conn, token, workspace_id, write=True) is None:
                return None
            row = self._row(conn, job_id)
            if row["workspace_id"] != workspace_id:
                return None
            if row["status"] == "completed":
                self._current(conn, row)
            if row["status"] in ("pending", "running"):
                conn.execute(
                    update(evidence_jobs)
                    .where(evidence_jobs.c.job_id == job_id)
                    .values(status="cancelled", reason="cancelled", receipt=None)
                )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(stop)

    def claim(self, job_id: UUID, *, prompt_sha256: str, instructions_sha256: str) -> bool:
        if any(
            type(v) is not str or re.fullmatch("[0-9a-f]{64}", v) is None
            for v in (prompt_sha256, instructions_sha256)
        ):
            raise ValueError("Invalid evidence hashes")

        def claim_one(conn: Connection) -> bool:
            row = self._row(conn, job_id)
            self._current(conn, row)
            if row["status"] != "pending":
                return False
            conn.execute(
                update(evidence_jobs)
                .where(evidence_jobs.c.job_id == job_id)
                .values(
                    status="running",
                    prompt_sha256=prompt_sha256,
                    instructions_sha256=instructions_sha256,
                )
            )
            return True

        return self._base._transaction(claim_one)

    def recover(self, job_id: UUID) -> EvidenceJob:
        def recover_one(conn: Connection) -> EvidenceJob:
            row = self._row(conn, job_id)
            if row["status"] == "running":
                conn.execute(
                    update(evidence_jobs)
                    .where(evidence_jobs.c.job_id == job_id)
                    .values(status="indeterminate", reason="unknown")
                )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(recover_one)

    def finish(
        self,
        job_id: UUID,
        *,
        receipt: dict[str, Any] | None = None,
        known_usage: dict[str, int] | None = None,
        usage_complete: bool = False,
        stream_closed: bool = False,
        reason: str = "unknown",
    ) -> EvidenceJob:
        if known_usage is not None and (
            type(known_usage) is not dict
            or set(known_usage) != {"input_tokens", "output_tokens", "requests"}
            or any(type(v) is not int or v < 0 for v in known_usage.values())
            or known_usage["requests"] != 1
        ):
            raise ValueError("Invalid observed usage")
        if type(usage_complete) is not bool or type(stream_closed) is not bool:
            raise ValueError("Invalid observations")
        if reason not in (
            "unknown",
            "input",
            "output",
            "cancelled",
            "timeout",
            "transport",
            "whitespace",
            "incomplete",
            "protocol",
            "usage",
            "limit",
        ):
            reason = "unknown"

        def complete(conn: Connection) -> EvidenceJob:
            row = self._row(conn, job_id)
            if row["status"] == "completed":
                return self._dto(row)
            previous = row["known_usage"]
            usage = known_usage
            if previous is not None:
                usage = {k: max(previous[k], (known_usage or previous)[k]) for k in previous}
            values: dict[str, Any] = dict(
                known_usage=usage,
                usage_complete=row["usage_complete"] or usage_complete,
                stream_closed=row["stream_closed"] or stream_closed,
            )
            if receipt is not None:
                self._current(conn, row)
                if row["status"] == "running":
                    if (
                        receipt.get("prompt_sha256") != row["prompt_sha256"]
                        or receipt.get("instructions_sha256") != row["instructions_sha256"]
                        or receipt.get("profile") != "guarded-question-evidence-v2"
                        or receipt.get("status") != "unreviewed"
                        or receipt.get("transport_profile") != "guarded-responses-tool-v1"
                        or receipt.get("input_format") != "question-evidence-source-v2"
                        or type(receipt.get("evidence")) is not dict
                        or receipt["evidence"].get("source_sha256") != row["source_sha256"]
                        or receipt["evidence"].get("question_sha256")
                        != sha256(row["question"].encode()).hexdigest()
                        or receipt.get("usage") != usage
                        or not usage_complete
                        or not stream_closed
                    ):
                        raise StorageCorruption("Evidence receipt identity changed")
                    values.update(
                        status="completed",
                        receipt=receipt,
                        receipt_sha256=digest(receipt),
                        reason=None,
                    )
            elif row["status"] in ("pending", "running"):
                values.update(
                    status=(
                        "indeterminate"
                        if reason == "unknown"
                        else "cancelled"
                        if reason == "cancelled"
                        else "failed"
                    ),
                    reason=reason,
                )
            conn.execute(
                update(evidence_jobs).where(evidence_jobs.c.job_id == job_id).values(**values)
            )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(complete)
