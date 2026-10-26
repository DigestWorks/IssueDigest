"""Explicit DBOS registration for admitted final briefing jobs."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from dbos import DBOS, Queue
from issuedigest_storage.briefing_jobs import BriefingJobRepository
from openai import AsyncOpenAI

from .briefing_worker import Ownership, _owned, execute_briefing_job, read_completed_briefing_job


@dataclass(frozen=True)
class RegisteredBriefingQueue:
    workflow: Callable[..., Any]
    queue: Queue


def register_briefing_queue(
    repository: BriefingJobRepository, *, client: AsyncOpenAI, check_ownership: Ownership
) -> RegisteredBriefingQueue:
    """Register after caller launch, outside its event loop."""
    queue = DBOS.register_queue(
        "issuedigest_guarded_evidence_v1",
        global_concurrency=1,
        worker_concurrency=1,
        on_conflict="never_update",
    )
    if queue.global_concurrency != 1 or queue.worker_concurrency != 1:
        raise ValueError("Briefing queue limits unavailable")

    @DBOS.step(name="issuedigest_question_briefing_call_v1", retries_allowed=False)
    async def call(job_id: str) -> None:
        await execute_briefing_job(
            repository, UUID(job_id), client=client, check_ownership=check_ownership
        )

    @DBOS.workflow(name="issuedigest_question_briefing_job_v1")
    async def workflow(job_id: str) -> None:
        try:
            if type(job_id) is not str:
                raise ValueError
            parsed = UUID(job_id)
            if str(parsed) != job_id or parsed.version != 4:
                raise ValueError
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid briefing workflow identity") from None
        if DBOS.workflow_id != "question-briefing-" + job_id:
            raise ValueError("Invalid briefing workflow identity")
        _owned(parsed, check_ownership)
        await call(job_id)
        await read_completed_briefing_job(repository, parsed, check_ownership=check_ownership)

    return RegisteredBriefingQueue(workflow, queue)
