"""Trusted-server admission followed by an explicit durable queue acknowledgement."""

import asyncio
import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from dbos import DBOSClient
from issuedigest_storage.evidence_jobs import EvidenceJobRepository


@dataclass(frozen=True)
class EvidenceDispatch:
    """Queue acknowledgement only; never a generation receipt."""

    job_id: UUID
    workflow_id: str
    status: str
    queued: bool


class EvidenceDispatchError(Exception):
    """Admission survived an ambiguous queue outcome; retry the same request."""

    def __init__(self, job_id: UUID, workflow_id: str):
        super().__init__("Evidence queue acknowledgement unavailable")
        self.job_id = job_id
        self.workflow_id = workflow_id


async def submit_evidence_job(
    repository: EvidenceJobRepository,
    *,
    client: DBOSClient,
    app_version: str,
    token: str,
    workspace_id: UUID,
    request_id: UUID,
    snapshot_id: UUID,
    question: str,
    model: str,
    reservation_usd: Decimal,
    profile: str = "guarded-question-evidence-v2",
) -> EvidenceDispatch | None:
    """Commit admission before queueing; caller owns client/version and retries.

    Cancellation can outlive the SQL thread and commit its reservation. No hidden
    continuation enqueues that job; retrying the exact request discovers it.
    """
    if type(app_version) is not str or re.fullmatch(r"[A-Za-z0-9._-]{1,128}", app_version) is None:
        raise ValueError("Invalid evidence application version")
    if type(profile) is not str or profile not in (
        "guarded-question-evidence-v2",
        "guarded-question-evidence-v3",
    ):
        raise ValueError("Invalid evidence profile")
    job = await asyncio.to_thread(
        repository.submit,
        token,
        workspace_id,
        request_id,
        snapshot_id,
        question,
        model=model,
        reservation_usd=reservation_usd,
        profile=profile,
    )
    if job is None:
        return None
    if job.profile != profile:
        raise ValueError("Evidence dispatch profile mismatch")
    workflow_id = "guarded-evidence-" + str(job.job_id)
    if job.status == "pending":
        job = await asyncio.to_thread(repository.get, token, workspace_id, job.job_id)
        if job is None:
            return None
    if job.profile != profile:
        raise ValueError("Evidence dispatch profile mismatch")
    if job.status != "pending":
        return EvidenceDispatch(job.job_id, workflow_id, job.status, False)
    failed = False
    try:
        await client.enqueue_async(
            {
                "workflow_name": (
                    "issuedigest_guarded_evidence_job_v1"
                    if job.profile == "guarded-question-evidence-v2"
                    else "issuedigest_guarded_evidence_job_v2"
                ),
                "queue_name": "issuedigest_guarded_evidence_v1",
                "workflow_id": workflow_id,
                "app_version": app_version,
                "workflow_id_reuse_policy": "return-existing",
            },
            str(job.job_id),
        )
    except Exception:
        # Raise outside the handler so even __context__ contains no queue secret.
        failed = True
    if failed:
        raise EvidenceDispatchError(job.job_id, workflow_id) from None
    return EvidenceDispatch(job.job_id, workflow_id, job.status, True)
