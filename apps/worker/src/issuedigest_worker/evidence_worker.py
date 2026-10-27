"""Explicit private durable evidence workflow; no import-time activation."""

import asyncio
import logging
from collections.abc import Callable
from hashlib import sha256
from typing import Any
from uuid import UUID

from dbos import DBOS
from issuedigest_agents.guarded_question_evidence_v2 import (
    GUARDED_QUESTION_V2_INSTRUCTIONS,
    _preflight,
    run_guarded_question_evidence_v2,
)
from issuedigest_agents.guarded_question_evidence_v3 import (
    GUARDED_QUESTION_V3_INSTRUCTIONS,
    run_guarded_question_evidence_v3,
)
from issuedigest_agents.guarded_question_evidence_v3 import (
    _preflight as _preflight_v3,
)
from issuedigest_agents.guarded_question_evidence_v5 import (
    GUARDED_QUESTION_V5_INSTRUCTIONS,
    run_guarded_question_evidence_v5,
)
from issuedigest_agents.guarded_question_evidence_v5 import _preflight as _preflight_v5
from issuedigest_agents.guarded_responses_stream import (
    DIAGNOSTIC_STAGES,
    GuardedResponsesCancelled,
    GuardedResponsesError,
)
from issuedigest_agents.question_briefing import (
    QuestionEvidenceReceipt,
    validate_question_evidence_receipt,
)
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.research import ResearchForbidden
from openai import AsyncOpenAI

Ownership = Callable[[UUID], bool]


def _owned(job_id: UUID, check_ownership: Ownership) -> None:
    if check_ownership(job_id) is not True:
        raise ResearchForbidden("Evidence worker ownership unavailable")


def read_completed_evidence_job(
    repository: EvidenceJobRepository, job_id: UUID, *, check_ownership: Ownership
) -> QuestionEvidenceReceipt | None:
    """Deep current-source receipt read; SQL's opaque payload is never enough."""
    _owned(job_id, check_ownership)
    job, source = repository.prepare(job_id)
    if job.status != "completed" or job.receipt is None:
        return None
    receipt = validate_question_evidence_receipt(source, job.question, job.receipt)
    if receipt.profile != job.profile:
        raise ValueError("Evidence job receipt profile changed")
    if (
        receipt.prompt_sha256 != job.prompt_sha256
        or receipt.instructions_sha256 != job.instructions_sha256
        or receipt.usage.model_dump() != job.known_usage
        or job.usage_complete is not True
        or job.stream_closed is not True
    ):
        raise ValueError("Evidence job receipt changed")
    _owned(job_id, check_ownership)
    return receipt


async def execute_evidence_job(
    repository: EvidenceJobRepository,
    job_id: UUID,
    *,
    client: AsyncOpenAI,
    check_ownership: Ownership,
    expected_profile: str = "guarded-question-evidence-v2",
) -> QuestionEvidenceReceipt | None:
    """One native request at most, with a separately committed SQL intent."""
    _owned(job_id, check_ownership)
    job, source = repository.prepare(job_id)
    if (
        type(expected_profile) is not str
        or expected_profile
        not in (
            "guarded-question-evidence-v2",
            "guarded-question-evidence-v3",
            "guarded-question-evidence-v5",
        )
        or job.profile != expected_profile
    ):
        raise ValueError("Evidence workflow profile mismatch")
    if job.status == "completed":
        return read_completed_evidence_job(repository, job_id, check_ownership=check_ownership)
    if job.status != "pending":
        repository.recover(job_id)
        return None
    try:
        prompt, _ = (
            _preflight(source, job.question)
            if expected_profile == "guarded-question-evidence-v2"
            else (
                _preflight_v3(source, job.question)
                if expected_profile == "guarded-question-evidence-v3"
                else _preflight_v5(source, job.question)
            )
        )
        instructions = (
            GUARDED_QUESTION_V2_INSTRUCTIONS
            if expected_profile == "guarded-question-evidence-v2"
            else (
                GUARDED_QUESTION_V3_INSTRUCTIONS
                if expected_profile == "guarded-question-evidence-v3"
                else GUARDED_QUESTION_V5_INSTRUCTIONS
            )
        )
    except Exception:
        repository.finish(job_id, reason="input")
        raise ValueError("Evidence job input unavailable") from None
    _owned(job_id, check_ownership)
    if not repository.claim(
        job_id,
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        instructions_sha256=sha256(instructions.encode()).hexdigest(),
    ):
        return None
    try:
        result: QuestionEvidenceReceipt
        if expected_profile == "guarded-question-evidence-v2":
            result = await run_guarded_question_evidence_v2(
                client=client, model=job.model, source=source, question=job.question
            )
        elif expected_profile == "guarded-question-evidence-v3":
            result = await run_guarded_question_evidence_v3(
                client=client, model=job.model, source=source, question=job.question
            )
        else:
            result = await run_guarded_question_evidence_v5(
                client=client, model=job.model, source=source, question=job.question
            )
    except (GuardedResponsesError, GuardedResponsesCancelled) as error:
        try:
            stage = error.diagnostic_stage
            safe_stage = (
                stage if type(stage) is str and stage in DIAGNOSTIC_STAGES else "unavailable"
            )
            logging.getLogger(__name__).warning(
                "evidence_generation_rejected stage=%s",
                safe_stage,
                extra={"diagnostic_stage": safe_stage},
            )
        except Exception:
            # Observability must not interfere with durable failure observations.
            pass
        repository.finish(
            job_id,
            known_usage=error.known_usage.model_dump() if error.known_usage is not None else None,
            usage_complete=error.usage_complete,
            stream_closed=error.stream_closed,
            reason="cancelled" if isinstance(error, asyncio.CancelledError) else error.reason,
        )
        raise
    except asyncio.CancelledError:
        repository.finish(job_id, reason="cancelled")
        raise
    except Exception:
        repository.finish(job_id, reason="unknown")
        raise ValueError("Evidence job outcome unavailable") from None
    # Persist observations independently if current authority blocks acceptance.
    try:
        _owned(job_id, check_ownership)
        current, current_source = repository.prepare(job_id)
        if current.profile != expected_profile or result.profile != expected_profile:
            raise ValueError("Evidence workflow profile mismatch")
        validate_question_evidence_receipt(current_source, current.question, result)
        saved = repository.finish(
            job_id,
            receipt=result.model_dump(mode="json"),
            known_usage=result.usage.model_dump(),
            usage_complete=True,
            stream_closed=True,
        )
    except Exception:
        # A successful SQL commit followed by a lost acknowledgement must win.
        repository.finish(
            job_id,
            known_usage=result.usage.model_dump(),
            usage_complete=True,
            stream_closed=True,
            reason="input",
        )
        return read_completed_evidence_job(repository, job_id, check_ownership=check_ownership)
    if saved.status != "completed":
        return None
    return read_completed_evidence_job(repository, job_id, check_ownership=check_ownership)


def register_evidence_workflow(
    repository: EvidenceJobRepository, *, client: AsyncOpenAI, check_ownership: Ownership
) -> Callable[..., Any]:
    """Register only; caller owns DBOS configuration, launch and workflow starts."""

    @DBOS.step(name="issuedigest_guarded_evidence_call_v1", retries_allowed=False)
    async def call(job_id: str) -> None:
        await execute_evidence_job(
            repository, UUID(job_id), client=client, check_ownership=check_ownership
        )

    @DBOS.workflow(name="issuedigest_guarded_evidence_job_v1")
    async def workflow(job_id: str) -> None:
        parsed = UUID(job_id)
        if (
            str(parsed) != job_id
            or parsed.version != 4
            or DBOS.workflow_id != "guarded-evidence-" + job_id
        ):
            raise ValueError("Invalid evidence workflow identity")
        _owned(parsed, check_ownership)
        await call(job_id)
        read_completed_evidence_job(repository, parsed, check_ownership=check_ownership)

    return workflow


def register_evidence_workflow_v3(
    repository: EvidenceJobRepository, *, client: AsyncOpenAI, check_ownership: Ownership
) -> Callable[..., Any]:
    """Register only; caller owns DBOS configuration, launch and workflow starts."""

    @DBOS.step(name="issuedigest_guarded_evidence_call_v2", retries_allowed=False)
    async def call(job_id: str) -> None:
        await execute_evidence_job(
            repository,
            UUID(job_id),
            client=client,
            check_ownership=check_ownership,
            expected_profile="guarded-question-evidence-v3",
        )

    @DBOS.workflow(name="issuedigest_guarded_evidence_job_v2")
    async def workflow(job_id: str) -> None:
        parsed = UUID(job_id)
        if (
            str(parsed) != job_id
            or parsed.version != 4
            or DBOS.workflow_id != "guarded-evidence-" + job_id
        ):
            raise ValueError("Invalid evidence workflow identity")
        _owned(parsed, check_ownership)
        await call(job_id)
        read_completed_evidence_job(repository, parsed, check_ownership=check_ownership)

    return workflow


def register_evidence_workflow_v5(
    repository: EvidenceJobRepository, *, client: AsyncOpenAI, check_ownership: Ownership
) -> Callable[..., Any]:
    """Register only; caller owns DBOS configuration, launch and workflow starts."""

    @DBOS.step(name="issuedigest_guarded_evidence_call_v3", retries_allowed=False)
    async def call(job_id: str) -> None:
        await execute_evidence_job(
            repository,
            UUID(job_id),
            client=client,
            check_ownership=check_ownership,
            expected_profile="guarded-question-evidence-v5",
        )

    @DBOS.workflow(name="issuedigest_guarded_evidence_job_v3")
    async def workflow(job_id: str) -> None:
        parsed = UUID(job_id)
        if (
            str(parsed) != job_id
            or parsed.version != 4
            or DBOS.workflow_id != "guarded-evidence-" + job_id
        ):
            raise ValueError("Invalid evidence workflow identity")
        _owned(parsed, check_ownership)
        await call(job_id)
        read_completed_evidence_job(repository, parsed, check_ownership=check_ownership)

    return workflow
