"""Explicit acknowledgement for an already admitted final briefing job."""

import asyncio
import re
from dataclasses import dataclass
from uuid import UUID

from dbos import DBOSClient
from issuedigest_storage.briefing_jobs import BriefingJob, BriefingJobRepository


@dataclass(frozen=True)
class BriefingDispatch:
    job_id: UUID
    workflow_id: str
    status: str
    queued: bool


class BriefingDispatchError(Exception):
    """The queue outcome is unknown; the caller may resend the same job ID."""

    def __init__(self, job_id: UUID, workflow_id: str) -> None:
        super().__init__("Briefing queue acknowledgement unavailable")
        self.job_id = job_id
        self.workflow_id = workflow_id


def _identity(value: UUID) -> None:
    if type(value) is not UUID or value.version != 4:
        raise ValueError("Invalid briefing identity")


def _current(job: BriefingJob, workspace_id: UUID, job_id: UUID) -> None:
    if (
        type(job) is not BriefingJob
        or job.job_id != job_id
        or job.workspace_id != workspace_id
        or job.status
        not in ("pending", "running", "completed", "failed", "cancelled", "indeterminate")
    ):
        raise ValueError("Invalid briefing job")


async def enqueue_briefing_job(
    repository: BriefingJobRepository,
    *,
    client: DBOSClient,
    app_version: str,
    token: str,
    workspace_id: UUID,
    job_id: UUID,
) -> BriefingDispatch | None:
    """Recheck current authority and enqueue only a still pending job."""
    if type(app_version) is not str or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", app_version) is None:
        raise ValueError("Invalid briefing application version")
    _identity(workspace_id)
    _identity(job_id)
    workflow_id = "question-briefing-" + str(job_id)
    job = await asyncio.to_thread(repository.get, token, workspace_id, job_id)
    if job is None:
        return None
    _current(job, workspace_id, job_id)
    if job.status == "pending":
        job = await asyncio.to_thread(repository.get, token, workspace_id, job_id)
        if job is None:
            return None
        _current(job, workspace_id, job_id)
    if job.status != "pending":
        return BriefingDispatch(job_id, workflow_id, job.status, False)
    failed = False
    try:
        await client.enqueue_async(
            {
                "workflow_name": "issuedigest_question_briefing_job_v1",
                "queue_name": "issuedigest_guarded_evidence_v1",
                "workflow_id": workflow_id,
                "app_version": app_version,
                "workflow_id_reuse_policy": "return-existing",
            },
            str(job_id),
        )
    except Exception:
        failed = True
    if failed:
        raise BriefingDispatchError(job_id, workflow_id) from None
    return BriefingDispatch(job_id, workflow_id, job.status, True)
