"""Explicit final briefing admission and execution, without runtime activation."""

import asyncio
from collections.abc import Awaitable, Callable
from decimal import Decimal
from functools import wraps
from hashlib import sha256
from uuid import UUID

from issuedigest_agents.briefing_receipts import (
    validate_briefing_binding as _bound,
)
from issuedigest_agents.briefing_receipts import (
    validate_briefing_packet as _packet,
)
from issuedigest_agents.briefing_receipts import (
    validate_stored_briefing,
)
from issuedigest_agents.guarded_responses_stream import (
    GuardedResponsesCancelled,
    GuardedResponsesError,
)
from issuedigest_agents.question_briefing_generation import (
    BRIEFING_INPUT_V1,
    QuestionBriefingGeneration,
    briefing_generation_instructions,
    briefing_input_format_from_instructions_hash,
    run_question_briefing_generation,
    validate_question_briefing_generation,
)
from issuedigest_domain.question_model_policy import briefing_model_allowed, reservation_allowed
from issuedigest_storage.briefing_jobs import BriefingJob, BriefingJobRepository
from issuedigest_storage.repository import StorageCorruption
from issuedigest_storage.research import ResearchBudgetExceeded, ResearchConflict, ResearchForbidden
from openai import AsyncOpenAI

Ownership = Callable[[UUID], bool]


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
    input_format: str = BRIEFING_INPUT_V1,
) -> BriefingJob | None:
    """Deep complete SDK preflight precedes the repository's atomic reservation."""
    instructions_hash = sha256(briefing_generation_instructions(input_format).encode()).hexdigest()
    for value in (workspace_id, request_id, plan_id):
        _id(value)
    if type(child_job_ids) is not tuple or not 1 <= len(child_job_ids) <= 5:
        raise ValueError("Invalid briefing children")
    for value in child_job_ids:
        _id(value)
    if (
        len(set(child_job_ids)) != len(child_job_ids)
        or type(token) is not str
        or not briefing_model_allowed(model)
        or not reservation_allowed(model, reservation_usd)
    ):
        raise ValueError("Invalid briefing admission")
    packet = await asyncio.to_thread(repository.inputs, token, workspace_id, plan_id, child_job_ids)
    if packet is None:
        return None
    _, prompt_hash = _packet(packet, input_format)
    if any(child.model != model for child in packet.children):
        raise ValueError("Briefing child model mismatch")
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
        instructions_sha256=instructions_hash,
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
    result = validate_stored_briefing(job, packet)
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
        input_format = briefing_input_format_from_instructions_hash(job.instructions_sha256)
        receipts, prompt_hash = _packet(packet, input_format)
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
        instructions_sha256=job.instructions_sha256,
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
            **({"input_format": input_format} if input_format != BRIEFING_INPUT_V1 else {}),
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
        current_format = briefing_input_format_from_instructions_hash(current.instructions_sha256)
        current_receipts, current_prompt = _packet(current_packet, current_format)
        _bound(current, current_packet, current_prompt)
        if (
            result.model != current.model
            or result.input_format != current_format
            or result.instructions_sha256 != current.instructions_sha256
        ):
            raise ValueError("Briefing result model mismatch")
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
