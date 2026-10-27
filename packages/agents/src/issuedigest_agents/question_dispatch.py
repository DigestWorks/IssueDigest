"""Explicit, sequential admission of a writer-owned fixed source plan.

The caller owns the DBOS client and application version and invokes again after
completion. Evidence completion is a transport result, never a briefing or a
semantic certification. A cancelled SQL waiter can leave an admitted child, but
has no hidden continuation to enqueue it or admit another child.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from hashlib import sha256
from typing import Literal
from uuid import UUID

from dbos import DBOSClient
from issuedigest_domain.question_source_plan import QuestionSourceChoice, QuestionSourcePlan
from issuedigest_storage.evidence_jobs import EvidenceJob, EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository
from issuedigest_storage.repository import StorageCorruption
from pydantic import ValidationError

from .evidence_dispatch import EvidenceDispatch, submit_evidence_job


@dataclass(frozen=True)
class QuestionDispatch:
    """Opaque acknowledgements and validated completed-prefix counters only."""

    plan_id: UUID
    status: Literal["no_match", "in_progress", "blocked", "evidence_complete"]
    completed_count: int
    total_sources: int
    dispatches: tuple[EvidenceDispatch, ...]


def _id(value: object) -> None:
    if type(value) is not UUID or value.version != 4:
        raise ValueError("A UUID v4 is required")


def _plan(
    value: QuestionSourcePlan, workspace: UUID, request: UUID, question: str
) -> QuestionSourcePlan:
    """Reconstruct raw fields, including shallow model_copy additions, strictly."""
    try:
        if type(value) is not QuestionSourcePlan or set(vars(value)) != set(
            QuestionSourcePlan.model_fields
        ):
            raise ValueError
        for field in ("plan_id", "workspace_id", "request_id"):
            _id(getattr(value, field))
        if type(value.sources) is not tuple:
            raise ValueError
        sources = []
        for source in value.sources:
            if type(source) is not QuestionSourceChoice or set(vars(source)) != set(
                QuestionSourceChoice.model_fields
            ):
                raise ValueError
            _id(source.snapshot_id)
            sources.append(
                dict(snapshot_id=str(source.snapshot_id), source_sha256=source.source_sha256)
            )
        raw = vars(value) | dict(
            plan_id=str(value.plan_id),
            workspace_id=str(value.workspace_id),
            request_id=str(value.request_id),
            sources=sources,
        )
        plan = QuestionSourcePlan.model_validate_json(
            json.dumps(raw, ensure_ascii=False, allow_nan=False), strict=True
        )
        if (
            plan.workspace_id != workspace
            or plan.request_id != request
            or plan.question != question
        ):
            raise ValueError
        return plan
    except (ValidationError, ValueError, TypeError, AttributeError):
        raise StorageCorruption("Question dispatch plan integrity check failed") from None


def _child(plan: UUID, snapshot: UUID, order: int) -> UUID:
    """v1 profile: UTF-8 namespace|canonical plan UUID|snapshot UUID|zero-based order.

    Take the first 16 SHA256 bytes and set RFC UUID version 4/variant bits. This
    stable profile must never change: it is the durable child recovery identity.
    """
    payload = f"issuedigest:question-plan-child:v1|{plan}|{snapshot}|{order}"
    return UUID(bytes=sha256(payload.encode("utf-8")).digest()[:16], version=4)


def _job(
    job: EvidenceJob,
    admitted: EvidenceJob,
    source: QuestionSourceChoice,
    workspace: UUID,
    question: str,
    model: str,
    profile: str = "guarded-question-evidence-v2",
) -> None:
    if (
        type(job) is not EvidenceJob
        or type(admitted) is not EvidenceJob
        or type(job.job_id) is not UUID
        or job.job_id.version != 4
        or profile not in ("guarded-question-evidence-v2", "guarded-question-evidence-v3")
        or type(job.profile) is not str
        or job.profile != profile
        or admitted.profile != profile
        or job.job_id != admitted.job_id
        or job.workspace_id != workspace
        or job.snapshot_id != source.snapshot_id
        or job.source_sha256 != source.source_sha256
        or type(job.question) is not str
        or job.question != question
        or type(job.model) is not str
        or job.model != model
        or type(job.status) is not str
        or job.status
        not in ("pending", "running", "completed", "failed", "cancelled", "indeterminate")
    ):
        raise StorageCorruption("Question dispatch job integrity check failed")


async def advance_question_plan(
    plans: QuestionPlanRepository,
    jobs: EvidenceJobRepository,
    *,
    client: DBOSClient,
    app_version: str,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    question: str,
    model: str,
    reservation_usd: Decimal,
) -> QuestionDispatch | None:
    """Admit/acknowledge through the first unfinished child, without paid retries.

    Exact repository classes sharing the very same Engine exclude arbitrary
    caller-provided plan repositories. Per-source transactions may commit a
    prefix; exceptions never refund reservations or select alternative children.
    """
    if (
        type(plans) is not QuestionPlanRepository
        or type(jobs) is not EvidenceJobRepository
        or plans.engine is not jobs.engine
    ):
        raise ValueError("Matching concrete question repositories are required")
    _id(workspace_id)
    _id(request_id)
    if (
        type(question) is not str
        or not question.strip()
        or len(question) > 1500
        or type(model) is not str
        or model != "gpt-6.1-sol"
    ):
        raise ValueError("Invalid question dispatch input")
    if (
        type(reservation_usd) is not Decimal
        or not reservation_usd.is_finite()
        or not Decimal("0") < reservation_usd <= Decimal("10")
        or reservation_usd != reservation_usd.quantize(Decimal(".01"))
    ):
        raise ValueError("Invalid evidence reservation")
    if type(app_version) is not str or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", app_version) is None:
        raise ValueError("Invalid evidence application version")
    saved = await asyncio.to_thread(plans.submit, token, workspace_id, request_id, question)
    if saved is None:
        return None
    plan = _plan(saved, workspace_id, request_id, question)
    profile = await asyncio.to_thread(plans.get_evidence_profile, token, workspace_id, plan.plan_id)
    if profile is None:
        return None
    if profile not in ("guarded-question-evidence-v2", "guarded-question-evidence-v3"):
        raise StorageCorruption("Question dispatch profile integrity check failed")
    if not plan.sources:
        return QuestionDispatch(plan.plan_id, "no_match", 0, 0, ())
    dispatches: list[EvidenceDispatch] = []
    completed = 0
    for order, source in enumerate(plan.sources):
        child = _child(plan.plan_id, source.snapshot_id, order)
        admitted = await asyncio.to_thread(
            jobs.submit,
            token,
            workspace_id,
            child,
            source.snapshot_id,
            question,
            model=model,
            reservation_usd=reservation_usd,
            expected_source_sha256=source.source_sha256,
            profile=profile,
        )
        if admitted is None:
            return None
        current = await asyncio.to_thread(jobs.get, token, workspace_id, admitted.job_id)
        if current is None:
            return None
        _job(current, admitted, source, workspace_id, question, model, profile)
        if current.status == "pending":
            ack = await submit_evidence_job(
                jobs,
                client=client,
                app_version=app_version,
                token=token,
                workspace_id=workspace_id,
                request_id=child,
                snapshot_id=source.snapshot_id,
                question=question,
                model=model,
                reservation_usd=reservation_usd,
                profile=profile,
            )
            if ack is None:
                return None
            dispatches.append(ack)
            # Even a completed acknowledgement race stops this invocation.
            status: Literal["in_progress", "blocked"] = (
                "blocked"
                if ack.status in ("failed", "cancelled", "indeterminate")
                else "in_progress"
            )
            return QuestionDispatch(
                plan.plan_id, status, completed, len(plan.sources), tuple(dispatches)
            )
        dispatches.append(
            EvidenceDispatch(
                current.job_id, "guarded-evidence-" + str(current.job_id), current.status, False
            )
        )
        if current.status == "completed":
            completed += 1
            continue
        return QuestionDispatch(
            plan.plan_id,
            "in_progress" if current.status == "running" else "blocked",
            completed,
            len(plan.sources),
            tuple(dispatches),
        )
    return QuestionDispatch(
        plan.plan_id, "evidence_complete", completed, len(plan.sources), tuple(dispatches)
    )
