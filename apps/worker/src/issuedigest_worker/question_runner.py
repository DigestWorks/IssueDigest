"""Bounded caller-lived progression and current-authority evidence collection.

Children remain durable on timeout/cancellation; the caller must explicitly resume
with the same request. This does not register a parent workflow or certify meaning.
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from dbos import DBOSClient, WorkflowHandleAsync
from issuedigest_agents.evidence_dispatch import EvidenceDispatch
from issuedigest_agents.guarded_question_evidence_v2 import GuardedQuestionEvidenceGenerationV2
from issuedigest_agents.guarded_question_evidence_v3 import GuardedQuestionEvidenceGenerationV3
from issuedigest_agents.question_briefing import QuestionEvidenceReceipt
from issuedigest_agents.question_dispatch import (
    QuestionDispatch,
    _job,
    _plan,
    advance_question_plan,
)
from issuedigest_domain.question_source_plan import QuestionSourceChoice
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchConflict, ResearchForbidden
from issuedigest_storage.sessions import AuthenticationDenied

from . import evidence_worker


@dataclass(frozen=True)
class QuestionEvidenceRun:
    """Validated private transport progress and unreviewed synthesis inputs only."""

    dispatch: QuestionDispatch
    receipts: tuple[QuestionEvidenceReceipt, ...]


class QuestionRunError(Exception):
    """Fixed safe failure; durable child admission is not rolled back."""

    def __init__(self, reason: Literal["workflow", "receipt", "progress"]):
        super().__init__("Question run " + reason + " unavailable")
        self.reason = reason


def _uuid(value: object) -> bool:
    return type(value) is UUID and value.version == 4


def _dispatch(value: QuestionDispatch) -> None:
    """Reject raw dataclass mutation, subclasses, and impossible acknowledgements."""
    if (
        type(value) is not QuestionDispatch
        or set(vars(value)) != set(QuestionDispatch.__dataclass_fields__)
        or not _uuid(value.plan_id)
        or type(value.status) is not str
        or value.status not in ("no_match", "in_progress", "blocked", "evidence_complete")
        or type(value.completed_count) is not int
        or type(value.total_sources) is not int
        or not 0 <= value.completed_count <= value.total_sources <= 5
        or type(value.dispatches) is not tuple
    ):
        raise QuestionRunError("progress")
    seen = set()
    for ack in value.dispatches:
        if (
            type(ack) is not EvidenceDispatch
            or set(vars(ack)) != set(EvidenceDispatch.__dataclass_fields__)
            or not _uuid(ack.job_id)
            or ack.job_id in seen
            or type(ack.workflow_id) is not str
            or ack.workflow_id != "guarded-evidence-" + str(ack.job_id)
            or type(ack.status) is not str
            or ack.status
            not in ("pending", "running", "completed", "failed", "cancelled", "indeterminate")
            or type(ack.queued) is not bool
            or (ack.queued and ack.status != "pending")
        ):
            raise QuestionRunError("progress")
        seen.add(ack.job_id)
    prefix = value.dispatches[: value.completed_count]
    if len(prefix) != value.completed_count or any(
        ack.status != "completed" or ack.queued for ack in prefix
    ):
        raise QuestionRunError("progress")
    if value.status == "no_match":
        valid = value.total_sources == 0 and value.completed_count == 0 and not value.dispatches
    elif value.status == "evidence_complete":
        valid = value.total_sources > 0 and value.completed_count == value.total_sources == len(
            value.dispatches
        )
    else:
        valid = (
            value.completed_count < value.total_sources
            and len(value.dispatches) == value.completed_count + 1
            and value.dispatches[-1].status
            in (
                ("pending", "running", "completed")
                if value.status == "in_progress"
                else ("failed", "cancelled", "indeterminate")
            )
        )
    if not valid:
        raise QuestionRunError("progress")


def _wait_authorized(
    plans: QuestionPlanRepository,
    jobs: EvidenceJobRepository,
    dispatch: QuestionDispatch,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    question: str,
    model: str,
) -> bool:
    saved = plans.submit(token, workspace_id, request_id, question)
    if saved is None:
        return False
    plan = _plan(saved, workspace_id, request_id, question)
    if plan.plan_id != dispatch.plan_id or len(plan.sources) != dispatch.total_sources:
        raise QuestionRunError("progress")
    profile = plans.get_evidence_profile(token, workspace_id, plan.plan_id)
    if profile is None:
        return False
    ack = dispatch.dispatches[-1]
    current = jobs.get(token, workspace_id, ack.job_id)
    if current is None:
        return False
    if current.job_id != ack.job_id:
        raise QuestionRunError("progress")
    _job(
        current,
        current,
        plan.sources[dispatch.completed_count],
        workspace_id,
        question,
        model,
        profile,
    )
    return True


def _collect(
    plans: QuestionPlanRepository,
    jobs: EvidenceJobRepository,
    dispatch: QuestionDispatch,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    question: str,
    model: str,
) -> tuple[QuestionEvidenceReceipt, ...] | None:
    saved = plans.submit(token, workspace_id, request_id, question)
    if saved is None:
        return None
    plan = _plan(saved, workspace_id, request_id, question)
    if plan.plan_id != dispatch.plan_id or len(plan.sources) != dispatch.total_sources:
        raise QuestionRunError("receipt")

    profile = plans.get_evidence_profile(token, workspace_id, plan.plan_id)
    if profile is None:
        return None
    if profile not in ("guarded-question-evidence-v2", "guarded-question-evidence-v3"):
        raise QuestionRunError("receipt")

    def authorization(expected: UUID, source: QuestionSourceChoice) -> Callable[[UUID], bool]:
        def authorized(job_id: UUID) -> bool:
            if type(job_id) is not UUID or job_id != expected:
                return False
            if plans.get_evidence_profile(token, workspace_id, plan.plan_id) != profile:
                return False
            current = jobs.get(token, workspace_id, expected)
            if current is None or current.job_id != expected:
                return False
            _job(current, current, source, workspace_id, question, model, profile)
            return current.status == "completed"

        return authorized

    receipts = []
    for source, ack in zip(plan.sources, dispatch.dispatches, strict=True):
        authorized = authorization(ack.job_id, source)
        if not authorized(ack.job_id):
            raise QuestionRunError("receipt")
        receipt = evidence_worker.read_completed_evidence_job(
            jobs, ack.job_id, check_ownership=authorized
        )
        if (
            type(receipt)
            is not (
                GuardedQuestionEvidenceGenerationV2
                if profile == "guarded-question-evidence-v2"
                else GuardedQuestionEvidenceGenerationV3
            )
            or receipt.profile != profile
            or receipt.status != "unreviewed"
        ):
            raise QuestionRunError("receipt")
        receipts.append(receipt)
    final = plans.submit(token, workspace_id, request_id, question)
    if final is None:
        return None
    if (
        _plan(final, workspace_id, request_id, question) != plan
        or plans.get_evidence_profile(token, workspace_id, plan.plan_id) != profile
    ):
        raise QuestionRunError("receipt")
    return tuple(receipts)


async def run_question_plan(
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
    total_timeout_seconds: int = 600,
) -> QuestionEvidenceRun | None:
    """Advance, observe each existing native child, and collect all current receipts.

    The caller owns the borrowed client and coroutine lifetime. Native workflow
    results are ignored; completion is accepted only through current SQL guards.
    """
    if type(total_timeout_seconds) is not int or not 1 <= total_timeout_seconds <= 600:
        raise ValueError("Invalid question run timeout")
    async with asyncio.timeout(total_timeout_seconds):
        previous = None
        waits = 0
        while True:
            current = await advance_question_plan(
                plans,
                jobs,
                client=client,
                app_version=app_version,
                token=token,
                workspace_id=workspace_id,
                request_id=request_id,
                question=question,
                model=model,
                reservation_usd=reservation_usd,
            )
            if current is None:
                return None
            _dispatch(current)
            if previous is not None and (
                current.plan_id != previous.plan_id
                or current.total_sources != previous.total_sources
                or current.completed_count < previous.completed_count
                or len(current.dispatches) < len(previous.dispatches)
                or any(
                    a.job_id != b.job_id
                    for a, b in zip(current.dispatches, previous.dispatches, strict=False)
                )
                or (
                    current.status == "in_progress"
                    and (
                        current.completed_count <= previous.completed_count
                        or current.dispatches[-1].job_id == previous.dispatches[-1].job_id
                    )
                )
            ):
                raise QuestionRunError("progress")
            if current.status in ("no_match", "blocked"):
                return QuestionEvidenceRun(current, ())
            if current.status == "evidence_complete":
                failed = False
                try:
                    receipts = await asyncio.to_thread(
                        _collect,
                        plans,
                        jobs,
                        current,
                        token,
                        workspace_id,
                        request_id,
                        question,
                        model,
                    )
                except (
                    AuthenticationDenied,
                    ResearchForbidden,
                    ResearchConflict,
                    StorageCorruption,
                ):
                    raise
                except Exception:
                    failed = True
                if failed:
                    raise QuestionRunError("receipt") from None
                return None if receipts is None else QuestionEvidenceRun(current, receipts)
            if waits >= current.total_sources:
                raise QuestionRunError("progress")
            if not await asyncio.to_thread(
                _wait_authorized,
                plans,
                jobs,
                current,
                token,
                workspace_id,
                request_id,
                question,
                model,
            ):
                return None
            failed = False
            try:
                handle: WorkflowHandleAsync[object] = await client.retrieve_workflow_async(
                    current.dispatches[-1].workflow_id
                )
                await handle.get_result()
            except Exception:
                failed = True
            if failed:
                raise QuestionRunError("workflow") from None
            waits += 1
            previous = current
