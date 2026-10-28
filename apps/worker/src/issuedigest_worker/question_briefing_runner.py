"""Bounded, caller-lived evidence-to-briefing admission; no runtime activation."""

import asyncio
import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from dbos import DBOSClient
from issuedigest_agents.briefing_dispatch import (
    BriefingDispatch,
    BriefingDispatchError,
    enqueue_briefing_job,
)
from issuedigest_agents.briefing_receipts import validate_briefing_evidence
from issuedigest_agents.evidence_dispatch import EvidenceDispatchError
from issuedigest_agents.guarded_question_evidence_v2 import GuardedQuestionEvidenceGenerationV2
from issuedigest_agents.guarded_question_evidence_v3 import GuardedQuestionEvidenceGenerationV3
from issuedigest_agents.guarded_question_evidence_v5 import GuardedQuestionEvidenceGenerationV5
from issuedigest_agents.guarded_responses_stream import GuardedResponsesError
from issuedigest_agents.question_briefing import build_question_briefing
from issuedigest_agents.question_briefing_generation import (
    BRIEFING_INPUT_V1,
    briefing_generation_instructions,
)
from issuedigest_agents.question_dispatch import QuestionDispatch
from issuedigest_domain.question_model_policy import (
    briefing_model_allowed,
    evidence_model_allowed,
    reservation_allowed,
)
from issuedigest_storage.briefing_jobs import REASONS, BriefingJob, BriefingJobRepository
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository
from issuedigest_storage.repository import StorageError
from issuedigest_storage.research import ResearchBudgetExceeded, ResearchConflict, ResearchForbidden
from issuedigest_storage.sessions import AuthenticationDenied, valid_session_token

from .briefing_worker import submit_briefing_job
from .question_runner import QuestionEvidenceRun, QuestionRunError, _dispatch, run_question_plan


@dataclass(frozen=True)
class QuestionBriefingRun:
    """Admission acknowledgements, never a final generation or semantic verdict."""

    evidence: QuestionDispatch
    briefing: BriefingDispatch | None


class QuestionBriefingRunError(Exception):
    """Safe failure; existing durable admissions and reservations survive."""

    def __init__(self) -> None:
        super().__init__("Question briefing run unavailable")


def _uuid(value: object) -> bool:
    return type(value) is UUID and value.version == 4


async def _linked_evidence(
    repository: BriefingJobRepository,
    evidence: QuestionEvidenceRun,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    question: str,
    model: str,
) -> bool | None:
    children = tuple(ack.job_id for ack in evidence.dispatch.dispatches)
    packet = await asyncio.to_thread(
        repository.inputs, token, workspace_id, evidence.dispatch.plan_id, children
    )
    if packet is None:
        return None
    receipts = validate_briefing_evidence(packet)
    if (
        packet.question != question
        or packet.plan.workspace_id != workspace_id
        or packet.plan.request_id != request_id
        or packet.plan.plan_id != evidence.dispatch.plan_id
        or tuple(child.job_id for child in packet.children) != children
        or any(child.model != model for child in packet.children)
        or receipts != evidence.receipts
    ):
        raise QuestionBriefingRunError
    probe = build_question_briefing(
        question,
        packet.sources,
        receipts,
        {"outcome": "insufficient_evidence", "message": "근거 검증용", "modules": []},
    )
    return any(item.linked_proposition_ids for item in probe.coverage)


async def run_question_briefing(
    plans: QuestionPlanRepository,
    evidence_jobs: EvidenceJobRepository,
    briefing_jobs: BriefingJobRepository,
    *,
    client: DBOSClient,
    app_version: str,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    question: str,
    model: str,
    evidence_reservation_usd: Decimal,
    briefing_reservation_usd: Decimal,
    total_timeout_seconds: int = 600,
    input_format: str = BRIEFING_INPUT_V1,
) -> QuestionBriefingRun | None:
    """Compose existing guarded helpers using the original request and borrowed client.

    Cancellation can outlive SQL admission, but creates no continuation or refund.
    Explicitly repeat the same request to discover its durable progress.
    """
    briefing_generation_instructions(input_format)
    if (
        type(plans) is not QuestionPlanRepository
        or type(evidence_jobs) is not EvidenceJobRepository
        or type(briefing_jobs) is not BriefingJobRepository
        or plans.engine is not evidence_jobs.engine
        or plans.engine is not briefing_jobs.engine
        or type(total_timeout_seconds) is not int
        or not 1 <= total_timeout_seconds <= 600
        or type(app_version) is not str
        or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", app_version) is None
        or not _uuid(workspace_id)
        or not _uuid(request_id)
        or type(token) is not str
        or not valid_session_token(token)
        or type(question) is not str
        or not 1 <= len(question) <= 1500
        or not question.strip()
        or not briefing_model_allowed(model)
        or not reservation_allowed(model, evidence_reservation_usd)
        or not reservation_allowed(model, briefing_reservation_usd)
    ):
        raise ValueError("Invalid question briefing run inputs")
    async with asyncio.timeout(total_timeout_seconds):
        try:
            evidence = await run_question_plan(
                plans,
                evidence_jobs,
                client=client,
                app_version=app_version,
                token=token,
                workspace_id=workspace_id,
                request_id=request_id,
                question=question,
                model=model,
                reservation_usd=evidence_reservation_usd,
                total_timeout_seconds=total_timeout_seconds,
            )
            if evidence is None:
                return None
            if (
                type(evidence) is not QuestionEvidenceRun
                or set(vars(evidence)) != set(QuestionEvidenceRun.__dataclass_fields__)
                or type(evidence.receipts) is not tuple
                or any(
                    type(r)
                    not in (
                        GuardedQuestionEvidenceGenerationV2,
                        GuardedQuestionEvidenceGenerationV3,
                        GuardedQuestionEvidenceGenerationV5,
                    )
                    for r in evidence.receipts
                )
            ):
                raise QuestionBriefingRunError
            try:
                _dispatch(evidence.dispatch)
            except QuestionRunError:
                raise QuestionBriefingRunError from None
            dispatch = evidence.dispatch
            if dispatch.status in ("no_match", "blocked"):
                if evidence.receipts:
                    raise QuestionBriefingRunError
                return QuestionBriefingRun(dispatch, None)
            if (
                dispatch.status != "evidence_complete"
                or len(evidence.receipts) != dispatch.completed_count
            ):
                raise QuestionBriefingRunError
            if len({r.profile for r in evidence.receipts}) != 1 or any(
                not evidence_model_allowed(model, receipt.profile) for receipt in evidence.receipts
            ):
                raise QuestionBriefingRunError
            linked = await _linked_evidence(
                briefing_jobs, evidence, token, workspace_id, request_id, question, model
            )
            if linked is None:
                return None
            if not linked:
                return QuestionBriefingRun(dispatch, None)
            children = tuple(ack.job_id for ack in dispatch.dispatches)
            job = await submit_briefing_job(
                briefing_jobs,
                token,
                workspace_id,
                request_id,
                dispatch.plan_id,
                children,
                model=model,
                reservation_usd=briefing_reservation_usd,
                **({"input_format": input_format} if input_format != BRIEFING_INPUT_V1 else {}),
            )
            if job is None:
                return None
            if (
                type(job) is not BriefingJob
                or set(vars(job)) != set(BriefingJob.__dataclass_fields__)
                or any(
                    not _uuid(getattr(job, n))
                    for n in ("job_id", "workspace_id", "actor_id", "request_id", "plan_id")
                )
                or type(job.status) is not str
                or job.status
                not in ("pending", "running", "completed", "failed", "cancelled", "indeterminate")
                or type(job.profile) is not str
                or job.profile != "question-briefing-generation-v1"
                or not reservation_allowed(job.model, job.reservation_usd)
                or type(job.usage_complete) is not bool
                or type(job.stream_closed) is not bool
                or any(
                    type(getattr(job, n)) is not str
                    or re.fullmatch("[0-9a-f]{64}", getattr(job, n)) is None
                    for n in ("inputs_sha256", "prompt_sha256", "instructions_sha256")
                )
                or (
                    job.reason is not None
                    and (type(job.reason) is not str or job.reason not in REASONS)
                )
                or (job.receipt is not None and type(job.receipt) is not dict)
                or (
                    job.known_usage is not None
                    and (
                        type(job.known_usage) is not dict
                        or set(job.known_usage) != {"input_tokens", "output_tokens", "requests"}
                        or any(type(v) is not int or v < 0 for v in job.known_usage.values())
                        or job.known_usage["requests"] != 1
                    )
                )
                or job.workspace_id != workspace_id
                or job.request_id != request_id
                or job.plan_id != dispatch.plan_id
                or type(job.child_job_ids) is not tuple
                or any(not _uuid(c) for c in job.child_job_ids)
                or job.child_job_ids != children
                or type(job.question) is not str
                or job.question != question
                or type(job.model) is not str
                or job.model != model
            ):
                raise QuestionBriefingRunError
            ack = await enqueue_briefing_job(
                briefing_jobs,
                client=client,
                app_version=app_version,
                token=token,
                workspace_id=workspace_id,
                job_id=job.job_id,
            )
            if ack is None:
                return None
            if (
                type(ack) is not BriefingDispatch
                or set(vars(ack)) != set(BriefingDispatch.__dataclass_fields__)
                or not _uuid(ack.job_id)
                or ack.job_id != job.job_id
                or type(ack.workflow_id) is not str
                or ack.workflow_id != "question-briefing-" + str(job.job_id)
                or type(ack.status) is not str
                or ack.status
                not in ("pending", "running", "completed", "failed", "cancelled", "indeterminate")
                or type(ack.queued) is not bool
                or (ack.queued and ack.status != "pending")
            ):
                raise QuestionBriefingRunError
            return QuestionBriefingRun(dispatch, ack)
        except (
            AuthenticationDenied,
            ResearchForbidden,
            ResearchConflict,
            ResearchBudgetExceeded,
            StorageError,
            EvidenceDispatchError,
            BriefingDispatchError,
            QuestionRunError,
            GuardedResponsesError,
            TimeoutError,
        ):
            raise
        except Exception:
            pass
        # Raise after leaving the handler: even __context__ must not retain raw input.
        raise QuestionBriefingRunError
