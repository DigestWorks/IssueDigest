"""Immutable submitted input and ordered execution history; no engine or event store."""

import json
from hashlib import sha256
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import UUID4, Field, model_validator

from .canvas_modules import CanvasModule
from .contract_values import (
    ContractModel,
    NonBlank,
    NonemptyIds,
    SafeCount,
    SafePositive,
    UniqueIds,
    UtcInstant,
    VersionedContract,
    require_model,
    require_safe_cursor,
)
from .sources import Sha256

Stage = Literal["search", "tools", "validation", "composition"]
RunStatus = Literal[
    "queued",
    "running",
    "cancel_requested",
    "awaiting_reconciliation",
    "succeeded",
    "failed",
    "cancelled",
]


class ExecutionVersions(ContractModel):
    model_config_version: NonBlank
    prompt_version: NonBlank
    tool_registry_version: NonBlank
    execution_engine_version: NonBlank
    ontology_version: Literal["issuedigest-relations-v1"] = "issuedigest-relations-v1"
    ui_schema_version: Literal["issuedigest-canvas-v1"] = "issuedigest-canvas-v1"


class RunInput(ContractModel):
    question: NonBlank
    selected_version_ids: UniqueIds
    base_revision_id: UUID4 | None
    versions: ExecutionVersions


def hash_run_input(input: RunInput) -> str:
    """Hash validated input, preserving source order and original text."""
    require_model(input, RunInput)
    try:
        encoded = json.dumps(
            input.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
    except UnicodeEncodeError as error:
        raise ValueError("input must be valid UTF-8 Unicode") from error
    return sha256(encoded).hexdigest()


class RunSubmission(ContractModel):
    workspace_id: UUID4
    requester_id: UUID4
    submission_key: NonBlank
    input: RunInput


class Run(VersionedContract):
    run_id: UUID4
    request_id: UUID4
    trace_id: UUID4
    submission: RunSubmission
    input_sha256: Sha256
    created_at: UtcInstant

    @model_validator(mode="after")
    def input_hash_matches(self) -> Self:
        if self.input_sha256 != hash_run_input(self.submission.input):
            raise ValueError("input_sha256 does not match submitted input")
        return self


class SubmissionAssessment(ContractModel):
    action: Literal["create", "reuse", "conflict"]
    existing_run_id: UUID4 | None

    @model_validator(mode="after")
    def consistent_result(self) -> Self:
        if (self.action == "create") != (self.existing_run_id is None):
            raise ValueError("create alone requires no existing run ID")
        return self


def assess_submission(existing: Run | None, submission: RunSubmission) -> SubmissionAssessment:
    """Assess a supplied existing run; no atomic uniqueness or persistence."""
    require_model(submission, RunSubmission)
    if existing is not None:
        require_model(existing, Run)
        old = existing.submission
        if (old.workspace_id, old.requester_id, old.submission_key) == (
            submission.workspace_id,
            submission.requester_id,
            submission.submission_key,
        ):
            return SubmissionAssessment(
                action="reuse" if old.input == submission.input else "conflict",
                existing_run_id=existing.run_id,
            )
    return SubmissionAssessment(action="create", existing_run_id=None)


class AcceptedPayload(ContractModel):
    kind: Literal["run.accepted"]


class StageChangedPayload(ContractModel):
    kind: Literal["stage.changed"]
    stage: Stage


class ModuleReadyPayload(ContractModel):
    kind: Literal["module.ready"]
    revision_id: UUID4
    module: CanvasModule


class CancelRequestedPayload(ContractModel):
    kind: Literal["run.cancel_requested"]


class AwaitingReconciliationPayload(ContractModel):
    kind: Literal["run.awaiting_reconciliation"]
    attempt_ids: NonemptyIds


class ReconciliationResolvedPayload(ContractModel):
    kind: Literal["run.reconciliation_resolved"]
    attempt_ids: NonemptyIds


class SucceededPayload(ContractModel):
    kind: Literal["run.succeeded"]
    revision_id: UUID4


class FailedPayload(ContractModel):
    kind: Literal["run.failed"]
    error_code: Literal[
        "validation_failed",
        "provider_refused",
        "incomplete_output",
        "tool_failed",
        "internal_error",
        "budget_exceeded",
    ]
    retryable: Annotated[bool, Field(strict=True)]


class CancelledPayload(ContractModel):
    kind: Literal["run.cancelled"]


RunEventPayload = Annotated[
    AcceptedPayload
    | StageChangedPayload
    | ModuleReadyPayload
    | CancelRequestedPayload
    | AwaitingReconciliationPayload
    | ReconciliationResolvedPayload
    | SucceededPayload
    | FailedPayload
    | CancelledPayload,
    Field(discriminator="kind"),
]


class RunEvent(VersionedContract):
    workspace_id: UUID4
    run_id: UUID4
    seq: SafePositive
    occurred_at: UtcInstant
    payload: RunEventPayload


class RunHistory(ContractModel):
    run: Run
    events: tuple[RunEvent, ...]

    @model_validator(mode="after")
    def ordered_history(self) -> Self:
        for seq, event in enumerate(self.events, 1):
            if event.seq != seq:
                raise ValueError("history seq must be contiguous from 1")
            if (
                event.run_id != self.run.run_id
                or event.workspace_id != self.run.submission.workspace_id
            ):
                raise ValueError("foreign run/workspace event")
            if event.occurred_at < self.run.created_at:
                raise ValueError("event precedes run creation")
            if (seq == 1) != isinstance(event.payload, AcceptedPayload):
                raise ValueError("accepted must be the first and only accepted event")
        replay_run(self)
        return self


class RunSnapshot(ContractModel):
    workspace_id: UUID4
    run_id: UUID4
    status: RunStatus
    accepted: Annotated[bool, Field(strict=True)]
    last_seq: SafeCount
    last_event_at: UtcInstant | None
    stage: Stage | None
    base_revision_id: UUID4 | None
    current_revision_id: UUID4 | None
    pending_revision_id: UUID4 | None
    cancel_requested: Annotated[bool, Field(strict=True)]
    unresolved_attempt_ids: UniqueIds

    @model_validator(mode="after")
    def consistent_snapshot(self) -> Self:
        if self.accepted != (self.last_seq > 0) or self.accepted != (
            self.last_event_at is not None
        ):
            raise ValueError("acceptance, seq and last event must agree")
        if self.status == "running" and self.stage is None:
            raise ValueError("running requires a stage")
        if self.status == "queued" and (
            self.stage is not None or self.pending_revision_id is not None
        ):
            raise ValueError("queued has no stage or pending module revision")
        if self.status in {"cancel_requested", "cancelled"} and not self.cancel_requested:
            raise ValueError("cancellation status requires cancellation intent")
        if self.status in {"queued", "running", "succeeded", "failed"} and self.cancel_requested:
            raise ValueError("status contradicts cancellation intent")
        if self.status == "awaiting_reconciliation" and not self.unresolved_attempt_ids:
            raise ValueError("awaiting requires unresolved attempts")
        if (
            self.status in {"queued", "running", "succeeded", "failed"}
            and self.unresolved_attempt_ids
        ):
            raise ValueError("status cannot have unresolved attempts")
        if (
            self.status in {"succeeded", "failed", "cancelled"}
            and self.pending_revision_id is not None
        ):
            raise ValueError("terminal snapshot cannot retain pending revision")
        if self.status != "succeeded" and self.current_revision_id != self.base_revision_id:
            raise ValueError("only success can replace the base revision")
        if self.status == "succeeded" and self.current_revision_id is None:
            raise ValueError("success requires a current revision")
        if not self.accepted and (
            self.status != "queued"
            or self.cancel_requested
            or self.pending_revision_id is not None
            or self.unresolved_attempt_ids
        ):
            raise ValueError("unaccepted snapshot must be completely initial")
        return self


def replay_run(history: RunHistory) -> RunSnapshot:
    """Fold supplied ordered events; reject impossible transitions without sorting."""
    require_model(history, RunHistory)
    run = history.run
    status: RunStatus = "queued"
    stage: Stage | None = None
    current = run.submission.input.base_revision_id
    pending: UUID | None = None
    cancel = False
    unresolved: list[UUID] = []
    resolved: set[UUID] = set()
    for event in history.events:
        payload = event.payload
        if status in {"succeeded", "failed", "cancelled"} and not (
            status == "cancelled" and isinstance(payload, ReconciliationResolvedPayload)
        ):
            raise ValueError("event after terminal status")
        if isinstance(payload, AcceptedPayload):
            if event.seq != 1:
                raise ValueError("accepted only at seq 1")
        elif isinstance(payload, StageChangedPayload):
            if status not in {"queued", "running"}:
                raise ValueError("stage change requires queued/running")
            stage, status = payload.stage, "running"
        elif isinstance(payload, ModuleReadyPayload):
            if status != "running":
                raise ValueError("module ready requires running")
            pending = payload.revision_id
        elif isinstance(payload, CancelRequestedPayload):
            if status not in {"queued", "running", "awaiting_reconciliation"}:
                raise ValueError("cancel request not permitted in current status")
            cancel, status = True, "cancel_requested"
        elif isinstance(payload, AwaitingReconciliationPayload):
            if status not in {"running", "cancel_requested"}:
                raise ValueError("awaiting requires running/cancel_requested")
            if set(payload.attempt_ids) & (set(unresolved) | resolved):
                raise ValueError("duplicate pending or previously resolved attempt")
            unresolved.extend(payload.attempt_ids)
            status = "awaiting_reconciliation"
        elif isinstance(payload, ReconciliationResolvedPayload):
            if not set(payload.attempt_ids) <= set(unresolved):
                raise ValueError("resolved IDs must be a pending subset")
            resolved.update(payload.attempt_ids)
            unresolved = [
                identity for identity in unresolved if identity not in payload.attempt_ids
            ]
            if status != "cancelled":
                status = (
                    "awaiting_reconciliation"
                    if unresolved
                    else ("cancel_requested" if cancel else "running")
                )
        elif isinstance(payload, (SucceededPayload, FailedPayload)):
            if status not in {"queued", "running"} or unresolved or cancel:
                raise ValueError(
                    "completion not permitted while cancellation/reconciliation pending"
                )
            if isinstance(payload, SucceededPayload):
                current, status = payload.revision_id, "succeeded"
            else:
                status = "failed"
            pending = None
        elif isinstance(payload, CancelledPayload):
            if status not in {"queued", "running", "cancel_requested", "awaiting_reconciliation"}:
                raise ValueError("cancellation not permitted in current status")
            cancel, status, pending = True, "cancelled", None
    return RunSnapshot(
        workspace_id=run.submission.workspace_id,
        run_id=run.run_id,
        status=status,
        accepted=bool(history.events),
        last_seq=len(history.events),
        last_event_at=history.events[-1].occurred_at if history.events else None,
        stage=stage,
        base_revision_id=run.submission.input.base_revision_id,
        current_revision_id=current,
        pending_revision_id=pending,
        cancel_requested=cancel,
        unresolved_attempt_ids=tuple(unresolved),
    )


def may_start_paid_step(snapshot: RunSnapshot) -> bool:
    """Supplied state eligibility only; this does not dispatch a provider call."""
    require_model(snapshot, RunSnapshot)
    return (
        snapshot.accepted
        and snapshot.status == "running"
        and not snapshot.cancel_requested
        and not snapshot.unresolved_attempt_ids
    )


class ReplayBatch(ContractModel):
    workspace_id: UUID4
    run_id: UUID4
    after_seq: SafeCount
    events: tuple[RunEvent, ...]
    latest_snapshot: RunSnapshot

    @model_validator(mode="after")
    def consistent_tail(self) -> Self:
        snap = self.latest_snapshot
        if self.workspace_id != snap.workspace_id or self.run_id != snap.run_id:
            raise ValueError("batch identity must match snapshot")
        if self.after_seq > snap.last_seq or len(self.events) != snap.last_seq - self.after_seq:
            raise ValueError("tail must end at latest seq")
        for seq, event in enumerate(self.events, self.after_seq + 1):
            if (
                event.seq != seq
                or event.workspace_id != self.workspace_id
                or event.run_id != self.run_id
            ):
                raise ValueError("tail seq/identity mismatch")
        if self.events and self.events[-1].occurred_at != snap.last_event_at:
            raise ValueError("tail last timestamp must match snapshot")
        return self


def events_after(history: RunHistory, after_seq: int) -> ReplayBatch:
    """Return an immutable tail plus the full latest snapshot."""
    require_model(history, RunHistory)
    cursor = require_safe_cursor(after_seq)
    snap = replay_run(history)
    if cursor > snap.last_seq:
        raise ValueError("cursor is beyond current seq")
    return ReplayBatch(
        workspace_id=snap.workspace_id,
        run_id=snap.run_id,
        after_seq=cursor,
        events=history.events[cursor:],
        latest_snapshot=snap,
    )


class CallAttempt(ContractModel):
    attempt_id: UUID4
    workspace_id: UUID4
    run_id: UUID4
    step_id: UUID4
    attempt_number: SafePositive
    authorized_after_seq: SafeCount
    provider: NonBlank
    operation: NonBlank
    model: NonBlank | None
    paid: Annotated[bool, Field(strict=True)]
    status: Literal[
        "prepared",
        "dispatched",
        "succeeded",
        "failed",
        "outcome_unknown",
        "cancelled_before_dispatch",
    ]
    created_at: UtcInstant
    dispatched_at: UtcInstant | None
    finished_at: UtcInstant | None
    result_id: UUID4 | None
    provider_request_id: NonBlank | None
    provider_idempotency_key: NonBlank | None
    supports_query: Annotated[bool, Field(strict=True)]
    supports_cancel: Annotated[bool, Field(strict=True)]

    @model_validator(mode="after")
    def consistent_attempt(self) -> Self:
        if self.status in {"prepared", "cancelled_before_dispatch"}:
            if self.dispatched_at is not None or self.result_id is not None:
                raise ValueError("undispatched attempt cannot have dispatch/result")
            if self.status == "prepared" and self.finished_at is not None:
                raise ValueError("prepared attempt cannot be finished")
            if self.status == "cancelled_before_dispatch" and (
                self.finished_at is None or self.finished_at < self.created_at
            ):
                raise ValueError("pre-dispatch cancellation needs ordered finished time")
        else:
            if self.dispatched_at is None or self.dispatched_at < self.created_at:
                raise ValueError("dispatched attempt needs ordered dispatch time")
            if self.status == "dispatched":
                if self.finished_at is not None or self.result_id is not None:
                    raise ValueError("in-flight attempt cannot be finished or have result")
            elif self.finished_at is None or self.finished_at < self.dispatched_at:
                raise ValueError("terminal attempt needs ordered finish time")
            if (self.status == "succeeded") != (self.result_id is not None):
                raise ValueError("only succeeded requires a result ID")
        return self
