"""Explicit registration for the isolated evidence admission queue."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from dbos import DBOS, Queue
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from openai import AsyncOpenAI

from .evidence_worker import Ownership, register_evidence_workflow


@dataclass(frozen=True)
class RegisteredEvidenceQueue:
    workflow: Callable[..., Any]
    queue: Queue


def register_evidence_queue(
    repository: EvidenceJobRepository, *, client: AsyncOpenAI, check_ownership: Ownership
) -> RegisteredEvidenceQueue:
    """Register after caller launch, outside its event loop (or via to_thread).

    The SDK persists this dedicated queue's configuration. A retained conflicting
    deployment configuration must fail closed before workflow registration.
    Caller owns DBOS configuration, migration, launch and the borrowed client.
    """
    queue = DBOS.register_queue(
        "issuedigest_guarded_evidence_v1", global_concurrency=1, worker_concurrency=1
    )
    if queue.global_concurrency != 1 or queue.worker_concurrency != 1:
        raise ValueError("Evidence queue limits unavailable")
    workflow = register_evidence_workflow(
        repository, client=client, check_ownership=check_ownership
    )
    return RegisteredEvidenceQueue(workflow, queue)
