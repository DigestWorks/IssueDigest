"""Explicit final briefing admission and execution, without runtime activation."""

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from functools import wraps
from hashlib import sha256
from uuid import UUID

from issuedigest_agents.guarded_question_evidence_v2 import (
    GuardedQuestionEvidenceGenerationV2,
    validate_guarded_question_evidence_v2,
)
from issuedigest_agents.guarded_responses_stream import (
    GuardedResponsesCancelled,
    GuardedResponsesError,
)
from issuedigest_agents.question_briefing_generation import (
    BRIEFING_GENERATION_INSTRUCTIONS,
    QuestionBriefingGeneration,
    question_briefing_prompt,
    run_question_briefing_generation,
    validate_question_briefing_generation,
)
from issuedigest_storage.briefing_jobs import BriefingJob, BriefingJobInputs, BriefingJobRepository
from issuedigest_storage.evidence_jobs import EvidenceJob
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchBudgetExceeded, ResearchConflict, ResearchForbidden
from openai import AsyncOpenAI

Ownership = Callable[[UUID], bool]
_INSTRUCTIONS_HASH = sha256(BRIEFING_GENERATION_INSTRUCTIONS.encode()).hexdigest()


def _safe[**P, R](operation: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @wraps(operation)
    async def run(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await operation(*args, **kwargs)
        except (
            ResearchForbidden,
            ResearchConflict,
            ResearchBudgetExceeded,
            StorageCorruption,
            GuardedResponsesError,
        ):
            raise
        except Exception:
            pass
        raise ValueError("Briefing job outcome unavailable")

    return run


def _id(value: UUID) -> None:
    if type(value) is not UUID or value.version != 4:
        raise ValueError("Invalid briefing identity")


def _owned(job_id: UUID, check_ownership: Ownership) -> None:
    _id(job_id)
    failed = False
    try:
        allowed = check_ownership(job_id)
    except ResearchForbidden:
        raise
    except Exception:
        failed = True
        allowed = False
    if failed:
        raise ValueError("Briefing ownership unavailable")
    if allowed is not True:
        raise ResearchForbidden("Briefing ownership unavailable")


def _packet(
    packet: BriefingJobInputs,
) -> tuple[tuple[GuardedQuestionEvidenceGenerationV2, ...], str]:
    if (
        type(packet) is not BriefingJobInputs
        or type(packet.question) is not str
        or type(packet.sources) is not tuple
        or type(packet.children) is not tuple
        or not 1 <= len(packet.sources) <= 5
        or len(packet.sources) != len(packet.children)
        or type(packet.inputs_sha256) is not str
    ):
        raise ValueError("Briefing inputs unavailable")
    receipts = []
    for source, child in zip(packet.sources, packet.children, strict=True):
        if (
            type(source) is not tuple
            or type(child) is not EvidenceJob
            or child.status != "completed"
            or child.question != packet.question
            or child.snapshot_id != source[0]
            or child.model != "gpt-6.1-sol"
            or type(child.receipt) is not dict
            or child.usage_complete is not True
            or child.stream_closed is not True
        ):
            raise ValueError("Briefing evidence unavailable")
        receipt = validate_guarded_question_evidence_v2(source, packet.question, child.receipt)
        if (
            receipt.prompt_sha256 != child.prompt_sha256
            or receipt.instructions_sha256 != child.instructions_sha256
            or receipt.usage.model_dump() != child.known_usage
        ):
            raise ValueError("Briefing evidence changed")
        receipts.append(receipt)
    checked = tuple(receipts)
    prompt = question_briefing_prompt(packet.question, packet.sources, checked)
    return checked, sha256(prompt.encode()).hexdigest()


def _bound(job: BriefingJob, packet: BriefingJobInputs, prompt_hash: str) -> None:
    if (
        type(job) is not BriefingJob
        or job.question != packet.question
        or job.inputs_sha256 != packet.inputs_sha256
        or job.prompt_sha256 != prompt_hash
        or job.instructions_sha256 != _INSTRUCTIONS_HASH
        or job.profile != "question-briefing-generation-v1"
        or job.model != "gpt-6.1-sol"
        or job.child_job_ids != tuple(c.job_id for c in packet.children)
    ):
        raise ValueError("Briefing job inputs changed")


@_safe
async def submit_briefing_job(
    repository: BriefingJobRepository,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    plan_id: UUID,
    child_job_ids: tuple[UUID, ...],
    *,
    model: str,
    reservation_usd: Decimal,
) -> BriefingJob | None:
    """Deep complete SDK preflight precedes the repository's atomic reservation."""
    for value in (workspace_id, request_id, plan_id):
        _id(value)
    if type(child_job_ids) is not tuple or not 1 <= len(child_job_ids) <= 5:
        raise ValueError("Invalid briefing children")
    for value in child_job_ids:
        _id(value)
    if (
        len(set(child_job_ids)) != len(child_job_ids)
        or type(token) is not str
        or type(model) is not str
        or model != "gpt-6.1-sol"
        or type(reservation_usd) is not Decimal
        or not reservation_usd.is_finite()
        or not 0 < reservation_usd <= 10
    ):
        raise ValueError("Invalid briefing admission")
    packet = await asyncio.to_thread(repository.inputs, token, workspace_id, plan_id, child_job_ids)
    if packet is None:
        return None
    _, prompt_hash = _packet(packet)
    return await asyncio.to_thread(
        repository.submit,
        token,
        workspace_id,
        request_id,
        plan_id,
        child_job_ids,
        model=model,
        reservation_usd=reservation_usd,
        expected_inputs_sha256=packet.inputs_sha256,
        prompt_sha256=prompt_hash,
        instructions_sha256=_INSTRUCTIONS_HASH,
    )


@_safe
async def read_completed_briefing_job(
    repository: BriefingJobRepository, job_id: UUID, *, check_ownership: Ownership
) -> QuestionBriefingGeneration | None:
    """Read canonical immutable completion against current rights and all sources."""
    _owned(job_id, check_ownership)
    job, packet = await asyncio.to_thread(repository.prepare, job_id)
    if job.status != "completed":
        return None
    receipts, prompt_hash = _packet(packet)
    _bound(job, packet, prompt_hash)
    if job.receipt is None:
        raise ValueError("Briefing completion unavailable")
    result = validate_question_briefing_generation(
        packet.question, packet.sources, receipts, job.receipt
    )
    if (
        result.usage.model_dump() != job.known_usage
        or job.usage_complete is not True
        or job.stream_closed is not True
    ):
        raise ValueError("Briefing completion changed")
    _owned(job_id, check_ownership)
    return result


@_safe
async def execute_briefing_job(
    repository: BriefingJobRepository,
    job_id: UUID,
    *,
    client: AsyncOpenAI,
    check_ownership: Ownership,
) -> QuestionBriefingGeneration | None:
    """Commit one call intent; running waiters never infer an interrupted owner."""
    _owned(job_id, check_ownership)
    job, packet = await asyncio.to_thread(repository.prepare, job_id)
    if job.status == "completed":
        return await read_completed_briefing_job(
            repository, job_id, check_ownership=check_ownership
        )
    if job.status != "pending":
        return None
    invalid = False
    try:
        receipts, prompt_hash = _packet(packet)
        _bound(job, packet, prompt_hash)
    except Exception:
        invalid = True
    if invalid:
        await asyncio.to_thread(repository.finish, job_id, reason="input")
        raise ValueError("Briefing job input unavailable")
    _owned(job_id, check_ownership)
    if not await asyncio.to_thread(
        repository.claim,
        job_id,
        expected_inputs_sha256=packet.inputs_sha256,
        prompt_sha256=prompt_hash,
        instructions_sha256=_INSTRUCTIONS_HASH,
    ):
        return None
    unknown = False
    try:
        _owned(job_id, check_ownership)
        result = await run_question_briefing_generation(
            client=client,
            model=job.model,
            question=packet.question,
            sources=packet.sources,
            receipts=receipts,
        )
    except ResearchForbidden:
        await asyncio.to_thread(repository.finish, job_id, reason="input")
        raise
    except (GuardedResponsesError, GuardedResponsesCancelled) as error:
        await asyncio.to_thread(
            repository.finish,
            job_id,
            known_usage=error.known_usage.model_dump() if error.known_usage is not None else None,
            usage_complete=error.usage_complete,
            stream_closed=error.stream_closed,
            reason="cancelled" if isinstance(error, asyncio.CancelledError) else error.reason,
        )
        raise
    except asyncio.CancelledError:
        await asyncio.to_thread(repository.finish, job_id, reason="cancelled")
        raise
    except Exception:
        unknown = True
    if unknown:
        await asyncio.to_thread(repository.finish, job_id, reason="unknown")
        raise ValueError("Briefing job outcome unavailable")
    if type(result) is not QuestionBriefingGeneration:
        await asyncio.to_thread(repository.finish, job_id, reason="output")
        raise ValueError("Briefing job outcome unavailable")
    # The SDK's successful observations survive later authority or receipt rejection.
    accepted = False
    try:
        _owned(job_id, check_ownership)
        current, current_packet = await asyncio.to_thread(repository.prepare, job_id)
        _owned(job_id, check_ownership)
        current_receipts, current_prompt = _packet(current_packet)
        _bound(current, current_packet, current_prompt)
        validate_question_briefing_generation(
            current_packet.question, current_packet.sources, current_receipts, result
        )
        saved = await asyncio.to_thread(
            repository.finish,
            job_id,
            receipt=result.model_dump(mode="json"),
            known_usage=result.usage.model_dump(),
            usage_complete=True,
            stream_closed=True,
        )
        accepted = saved.status == "completed"
    except asyncio.CancelledError:
        await asyncio.to_thread(
            repository.finish,
            job_id,
            known_usage=result.usage.model_dump(),
            usage_complete=True,
            stream_closed=True,
            reason="cancelled",
        )
        raise
    except Exception:
        pass
    if not accepted:
        # Also handles commit success followed by lost acknowledgement; completed wins.
        await asyncio.to_thread(
            repository.finish,
            job_id,
            known_usage=result.usage.model_dump(),
            usage_complete=True,
            stream_closed=True,
            reason="input",
        )
    return await read_completed_briefing_job(repository, job_id, check_ownership=check_ownership)
