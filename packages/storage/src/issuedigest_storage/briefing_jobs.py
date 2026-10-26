"""Opaque final jobs. Semantic SDK acceptance belongs to the trusted worker.

Hashes detect corruption, not replacement of records and all their hashes. No
transaction gate is held across a provider call. Reservations are never refunded.
"""

import re
from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from issuedigest_domain import EvidenceBundle
from issuedigest_domain.question_source_plan import QuestionSourcePlan
from issuedigest_domain.research_journey import SourcePresentation
from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Connection, Engine

from .briefing_job_schema import briefing_jobs
from .evidence_jobs import EvidenceJob, EvidenceJobRepository, digest, evidence_jobs, source_digest
from .question_plans import QuestionPlanRepository, _id, question_source_plans
from .repository import StorageCorruption
from .research import (
    ResearchBudgetExceeded,
    ResearchConflict,
    ResearchRepository,
)
from .research_schema import research_budget_months

Source = tuple[UUID, EvidenceBundle, SourcePresentation]
PROFILE = "question-briefing-generation-v1"
MODEL = "gpt-6.1-sol"
REASONS = (
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
)


def _hashes(*values: object) -> None:
    if any(type(v) is not str or re.fullmatch("[0-9a-f]{64}", v) is None for v in values):
        raise ValueError("Invalid briefing hashes")


def _ids(workspace_id: UUID, plan_id: UUID, child_job_ids: tuple[UUID, ...]) -> None:
    _id(workspace_id)
    _id(plan_id)
    if type(child_job_ids) is not tuple or not 1 <= len(child_job_ids) <= 5:
        raise ValueError("Invalid briefing children")
    for value in child_job_ids:
        _id(value)
    if len(set(child_job_ids)) != len(child_job_ids):
        raise ValueError("Duplicate briefing children")


def _usage(value: object) -> None:
    if value is not None and (
        type(value) is not dict
        or set(value) != {"input_tokens", "output_tokens", "requests"}
        or any(type(v) is not int or v < 0 for v in value.values())
        or value["requests"] != 1
    ):
        raise ValueError("Invalid observed usage")


@dataclass(frozen=True)
class BriefingJob:
    job_id: UUID
    workspace_id: UUID
    actor_id: UUID
    request_id: UUID
    plan_id: UUID
    question: str
    model: str
    profile: str
    reservation_usd: Decimal
    status: str
    inputs_sha256: str
    child_job_ids: tuple[UUID, ...]
    prompt_sha256: str
    instructions_sha256: str
    receipt: dict[str, Any] | None
    known_usage: dict[str, int] | None
    usage_complete: bool
    stream_closed: bool
    reason: str | None


@dataclass(frozen=True)
class BriefingJobInputs:
    question: str
    plan: QuestionSourcePlan
    sources: tuple[Source, ...]
    children: tuple[EvidenceJob, ...]
    inputs_sha256: str


class BriefingJobRepository:
    def __init__(self, engine: Engine):
        self.engine = engine
        self._base = ResearchRepository(engine)

    @staticmethod
    def _row(conn: Connection, job_id: UUID) -> Any:
        _id(job_id)
        EvidenceJobRepository._lock_jobs(conn)
        row = (
            conn.execute(
                select(briefing_jobs).where(briefing_jobs.c.job_id == job_id).with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ResearchConflict("Briefing job unavailable")
        return row

    @staticmethod
    def _dto(row: Any) -> BriefingJob:
        try:
            for name in ("job_id", "workspace_id", "actor_id", "request_id", "plan_id"):
                _id(row[name])
            if type(row["child_job_ids"]) is not list or any(
                type(v) is not str for v in row["child_job_ids"]
            ):
                raise ValueError
            children = tuple(UUID(v) for v in row["child_job_ids"])
            if [str(v) for v in children] != row["child_job_ids"]:
                raise ValueError
            _ids(row["workspace_id"], row["plan_id"], children)
            _hashes(row["inputs_sha256"], row["prompt_sha256"], row["instructions_sha256"])
            _usage(row["known_usage"])
            if (
                row["model"] != MODEL
                or row["profile"] != PROFILE
                or type(row["question"]) is not str
                or not row["question"].strip()
                or len(row["question"]) > 1500
                or row["status"]
                not in ("pending", "running", "completed", "failed", "cancelled", "indeterminate")
                or type(row["usage_complete"]) is not bool
                or type(row["stream_closed"]) is not bool
                or row["reason"] is not None
                and row["reason"] not in REASONS
            ):
                raise ValueError
            receipt = row["receipt"] if row["status"] == "completed" else None
            if row["status"] == "completed" and (
                type(receipt) is not dict
                or digest(receipt) != row["receipt_sha256"]
                or row["known_usage"] is None
                or not row["usage_complete"]
                or not row["stream_closed"]
            ):
                raise ValueError
            fields = {n: row[n] for n in BriefingJob.__dataclass_fields__}
            fields.update(child_job_ids=children, receipt=receipt)
            return BriefingJob(**fields)
        except (ValueError, TypeError, KeyError):
            raise StorageCorruption("Briefing job integrity check failed") from None

    @staticmethod
    def _packet(
        conn: Connection,
        actor: UUID,
        workspace: UUID,
        plan_id: UUID,
        child_job_ids: tuple[UUID, ...],
    ) -> BriefingJobInputs:
        row = (
            conn.execute(
                select(question_source_plans)
                .where(
                    question_source_plans.c.plan_id == plan_id,
                    question_source_plans.c.workspace_id == workspace,
                    question_source_plans.c.actor_id == actor,
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ResearchConflict("Briefing plan unavailable")
        plan = QuestionPlanRepository._dto(conn, row)
        if plan.status != "selected" or len(plan.sources) != len(child_job_ids):
            raise ResearchConflict("Briefing plan incomplete")
        children, sources = [], []
        fingerprints = []
        for identity, choice in zip(child_job_ids, plan.sources, strict=True):
            child_row = EvidenceJobRepository._row(conn, identity)
            child = EvidenceJobRepository._dto(child_row)
            if (
                child_row["actor_id"] != actor
                or child.workspace_id != workspace
                or child.status != "completed"
                or child.question != plan.question
                or child.snapshot_id != choice.snapshot_id
                or child.source_sha256 != choice.source_sha256
                or not child.usage_complete
                or not child.stream_closed
                or child.known_usage is None
            ):
                raise ResearchConflict("Briefing child unavailable")
            try:
                _hashes(child.prompt_sha256, child.instructions_sha256, child.source_sha256)
            except ValueError:
                raise StorageCorruption("Briefing child hashes changed") from None
            source = EvidenceJobRepository._current(conn, child_row)
            receipt = child.receipt
            if (
                type(receipt) is not dict
                or receipt.get("prompt_sha256") != child.prompt_sha256
                or receipt.get("instructions_sha256") != child.instructions_sha256
                or receipt.get("usage") != child.known_usage
            ):
                raise StorageCorruption("Briefing child receipt changed")
            children.append(child)
            sources.append(source)
            child_fields = asdict(child)
            child_fields.update(
                job_id=str(child.job_id),
                workspace_id=str(child.workspace_id),
                snapshot_id=str(child.snapshot_id),
            )
            fingerprints.append(dict(child=child_fields, source_sha256=source_digest(source)))
        fingerprint = digest(
            dict(
                actor_id=str(actor),
                plan=plan.model_dump(mode="json"),
                child_job_ids=[str(v) for v in child_job_ids],
                children=fingerprints,
            )
        )
        return BriefingJobInputs(plan.question, plan, tuple(sources), tuple(children), fingerprint)

    @classmethod
    def _current(cls, conn: Connection, row: Any) -> BriefingJobInputs:
        job = cls._dto(row)
        packet = cls._packet(
            conn, row["actor_id"], row["workspace_id"], row["plan_id"], job.child_job_ids
        )
        if packet.inputs_sha256 != job.inputs_sha256 or packet.question != job.question:
            raise StorageCorruption("Briefing inputs changed")
        return packet

    def inputs(
        self, token: str, workspace_id: UUID, plan_id: UUID, child_job_ids: tuple[UUID, ...]
    ) -> BriefingJobInputs | None:
        _ids(workspace_id, plan_id, child_job_ids)

        def read(conn: Connection) -> BriefingJobInputs | None:
            EvidenceJobRepository._lock_jobs(conn)
            actor = self._base._actor(conn, token, workspace_id, write=True)
            return (
                None
                if actor is None
                else self._packet(conn, actor, workspace_id, plan_id, child_job_ids)
            )

        return self._base._transaction(read)

    def submit(
        self,
        token: str,
        workspace_id: UUID,
        request_id: UUID,
        plan_id: UUID,
        child_job_ids: tuple[UUID, ...],
        *,
        model: str,
        reservation_usd: Decimal,
        expected_inputs_sha256: str,
        prompt_sha256: str,
        instructions_sha256: str,
    ) -> BriefingJob | None:
        _ids(workspace_id, plan_id, child_job_ids)
        _id(request_id)
        _hashes(expected_inputs_sha256, prompt_sha256, instructions_sha256)
        if type(model) is not str or model != MODEL:
            raise ValueError("Invalid briefing model")
        if (
            type(reservation_usd) is not Decimal
            or not reservation_usd.is_finite()
            or not Decimal("0") < reservation_usd <= Decimal("10")
            or reservation_usd != reservation_usd.quantize(Decimal(".01"))
        ):
            raise ValueError("Invalid briefing reservation")
        reservation_usd = reservation_usd.quantize(Decimal(".01"))

        def save(conn: Connection) -> BriefingJob | None:
            EvidenceJobRepository._lock_jobs(conn)
            actor = self._base._actor(conn, token, workspace_id, write=True)
            if actor is None:
                return None
            packet = self._packet(conn, actor, workspace_id, plan_id, child_job_ids)
            if packet.inputs_sha256 != expected_inputs_sha256:
                raise ResearchConflict("Briefing inputs changed")
            prior = (
                conn.execute(
                    select(briefing_jobs).where(
                        briefing_jobs.c.workspace_id == workspace_id,
                        briefing_jobs.c.actor_id == actor,
                        briefing_jobs.c.request_id == request_id,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is not None:
                job = self._dto(prior)
                if (
                    job.plan_id != plan_id
                    or job.child_job_ids != child_job_ids
                    or job.model != model
                    or job.reservation_usd != reservation_usd
                    or job.inputs_sha256 != expected_inputs_sha256
                    or job.prompt_sha256 != prompt_sha256
                    or job.instructions_sha256 != instructions_sha256
                ):
                    raise ResearchConflict("Briefing request changed")
                self._current(conn, prior)
                return job
            for table in (evidence_jobs, briefing_jobs):
                if conn.scalar(
                    select(table.c.job_id).where(
                        table.c.workspace_id == workspace_id,
                        table.c.status.in_(["pending", "running"]),
                    )
                ):
                    raise ResearchConflict("Workspace job already active")
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
                insert(briefing_jobs).values(
                    job_id=job_id,
                    workspace_id=workspace_id,
                    actor_id=actor,
                    request_id=request_id,
                    plan_id=plan_id,
                    question=packet.question,
                    child_job_ids=[str(v) for v in child_job_ids],
                    model=model,
                    profile=PROFILE,
                    reservation_usd=reservation_usd,
                    inputs_sha256=expected_inputs_sha256,
                    prompt_sha256=prompt_sha256,
                    instructions_sha256=instructions_sha256,
                    status="pending",
                )
            )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(save)

    def prepare(self, job_id: UUID) -> tuple[BriefingJob, BriefingJobInputs]:
        _id(job_id)

        def read(conn: Connection) -> tuple[BriefingJob, BriefingJobInputs]:
            row = self._row(conn, job_id)
            return self._dto(row), self._current(conn, row)

        return self._base._transaction(read)

    def get(self, token: str, workspace_id: UUID, job_id: UUID) -> BriefingJob | None:
        _id(workspace_id)
        _id(job_id)

        def read(conn: Connection) -> BriefingJob | None:
            EvidenceJobRepository._lock_jobs(conn)
            if self._base._actor(conn, token, workspace_id) is None:
                return None
            row = self._row(conn, job_id)
            if row["workspace_id"] != workspace_id:
                return None
            self._current(conn, row)
            return self._dto(row)

        return self._base._transaction(read)

    def claim(
        self,
        job_id: UUID,
        *,
        expected_inputs_sha256: str,
        prompt_sha256: str,
        instructions_sha256: str,
    ) -> bool:
        _id(job_id)
        _hashes(expected_inputs_sha256, prompt_sha256, instructions_sha256)

        def start(conn: Connection) -> bool:
            row = self._row(conn, job_id)
            self._current(conn, row)
            if (
                row["inputs_sha256"] != expected_inputs_sha256
                or row["prompt_sha256"] != prompt_sha256
                or row["instructions_sha256"] != instructions_sha256
            ):
                raise ResearchConflict("Briefing admission changed")
            if row["status"] != "pending":
                return False
            conn.execute(
                update(briefing_jobs)
                .where(briefing_jobs.c.job_id == job_id)
                .values(status="running")
            )
            return True

        return self._base._transaction(start)

    def recover(self, job_id: UUID) -> BriefingJob:
        _id(job_id)

        def lost(conn: Connection) -> BriefingJob:
            row = self._row(conn, job_id)
            if row["status"] == "running":
                conn.execute(
                    update(briefing_jobs)
                    .where(briefing_jobs.c.job_id == job_id)
                    .values(status="indeterminate", reason="unknown")
                )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(lost)

    def cancel(self, token: str, workspace_id: UUID, job_id: UUID) -> BriefingJob | None:
        _id(workspace_id)
        _id(job_id)

        def stop(conn: Connection) -> BriefingJob | None:
            EvidenceJobRepository._lock_jobs(conn)
            if self._base._actor(conn, token, workspace_id, write=True) is None:
                return None
            row = self._row(conn, job_id)
            if row["workspace_id"] != workspace_id:
                return None
            if row["status"] == "completed":
                self._current(conn, row)
            if row["status"] in ("pending", "running"):
                conn.execute(
                    update(briefing_jobs)
                    .where(briefing_jobs.c.job_id == job_id)
                    .values(status="cancelled", reason="cancelled")
                )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(stop)

    def finish(
        self,
        job_id: UUID,
        *,
        receipt: dict[str, Any] | None = None,
        known_usage: dict[str, int] | None = None,
        usage_complete: bool = False,
        stream_closed: bool = False,
        reason: str = "unknown",
    ) -> BriefingJob:
        _id(job_id)
        _usage(known_usage)
        if type(usage_complete) is not bool or type(stream_closed) is not bool:
            raise ValueError("Invalid observations")
        if type(reason) is not str or reason not in REASONS:
            reason = "unknown"
        if receipt is not None:
            if type(receipt) is not dict:
                raise ValueError("Invalid briefing receipt")
            digest(receipt)  # Reject non-JSON/nonfinite values before SQL.

        def complete(conn: Connection) -> BriefingJob:
            row = self._row(conn, job_id)
            self._dto(row)
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
            if receipt is not None and row["status"] == "running":
                packet = self._current(conn, row)
                briefing = receipt.get("briefing")
                if (
                    receipt.get("prompt_sha256") != row["prompt_sha256"]
                    or receipt.get("instructions_sha256") != row["instructions_sha256"]
                    or receipt.get("profile") != PROFILE
                    or receipt.get("model") != MODEL
                    or receipt.get("status") != "unreviewed"
                    or type(briefing) is not dict
                    or briefing.get("workspace_id") != str(row["workspace_id"])
                    or type(briefing.get("sources")) is not list
                    or [
                        s.get("snapshot_id") if type(s) is dict else None
                        for s in briefing["sources"]
                    ]
                    != [str(s[0]) for s in packet.sources]
                    or receipt.get("usage") != known_usage
                    or known_usage != usage
                    or known_usage is None
                    or not usage_complete
                    or not stream_closed
                ):
                    raise StorageCorruption("Briefing receipt identity changed")
                values.update(
                    status="completed", receipt=receipt, receipt_sha256=digest(receipt), reason=None
                )
            elif receipt is None and row["status"] in ("pending", "running"):
                values.update(
                    status="indeterminate"
                    if reason == "unknown"
                    else "cancelled"
                    if reason == "cancelled"
                    else "failed",
                    reason=reason,
                )
            conn.execute(
                update(briefing_jobs).where(briefing_jobs.c.job_id == job_id).values(**values)
            )
            return self._dto(self._row(conn, job_id))

        return self._base._transaction(complete)
