"""Supplied execution/research/canvas/usage referential integrity; no operational proof."""

from typing import Self
from uuid import UUID

from pydantic import model_validator

from .canvas import CanvasBundle, CanvasRevision
from .contract_values import VersionedContract, index_records
from .execution import (
    AwaitingReconciliationPayload,
    CallAttempt,
    ModuleReadyPayload,
    ReconciliationResolvedPayload,
    RunHistory,
    SucceededPayload,
    may_start_paid_step,
    replay_run,
)
from .research import ResearchBundle
from .usage import UsageBook


class RunExecutionBundle(VersionedContract):
    history: RunHistory
    research: ResearchBundle
    revisions: tuple[CanvasRevision, ...]
    attempts: tuple[CallAttempt, ...]
    usage: UsageBook | None

    @model_validator(mode="after")
    def consistent_execution(self) -> Self:
        run = self.history.run
        workspace = run.submission.workspace_id
        if self.research.workspace_id != workspace:
            raise ValueError("research workspace differs from run")
        selected = set(run.submission.input.selected_version_ids)
        versions = {proof.version.version_id for proof in self.research.evidence}
        if not selected <= versions:
            raise ValueError("run selected versions must exist in research")
        revisions = index_records(self.revisions, "revision_id")
        self._validate_revisions(revisions)
        self._validate_publication(revisions)
        self._validate_attempts()
        self._validate_usage()
        return self

    def _validate_revisions(self, revisions: dict[UUID, CanvasRevision]) -> None:
        run = self.history.run
        base = run.submission.input.base_revision_id
        if base is not None and (base not in revisions or revisions[base].run_id == run.run_id):
            raise ValueError("base must be a supplied revision belonging to another run")
        first_revisions = tuple(
            revision
            for revision in self.revisions
            if revision.run_id == run.run_id and revision.parent_revision_id == base
        )
        if len(first_revisions) > 1:
            raise ValueError("current run can have at most one first revision")
        for revision in self.revisions:
            if revision.workspace_id != run.submission.workspace_id:
                raise ValueError("revision workspace differs from run")
            CanvasBundle(research=self.research, revision=revision)
            parent = (
                revisions.get(revision.parent_revision_id)
                if revision.parent_revision_id is not None
                else None
            )
            if revision.parent_revision_id is not None:
                if parent is None or revision.revision_number != parent.revision_number + 1:
                    raise ValueError("revision parent must exist with previous number")
            if revision.run_id == run.run_id:
                if revision.selected_version_ids != run.submission.input.selected_version_ids:
                    raise ValueError("current-run revision selection/order differs from input")
                if revision.validated_at < run.created_at:
                    raise ValueError("current-run revision validated before creation")
                if parent is None:
                    if base is not None:
                        raise ValueError("first current-run revision requires base parent")
                elif parent.run_id != run.run_id and parent.revision_id != base:
                    raise ValueError("foreign-run parent must be the input base revision")

    def _validate_publication(self, revisions: dict[UUID, CanvasRevision]) -> None:
        run = self.history.run
        announced: dict[UUID, set[UUID]] = {}
        last_number = 0
        for event in self.history.events:
            payload = event.payload
            if isinstance(payload, (ModuleReadyPayload, SucceededPayload)):
                revision = revisions.get(payload.revision_id)
                if revision is None or revision.run_id != run.run_id:
                    raise ValueError("published revision must belong to current run")
                modules = {module.module_id: module for module in revision.draft.modules}
                if isinstance(payload, ModuleReadyPayload):
                    if modules.get(payload.module.module_id) != payload.module:
                        raise ValueError("ready module must exactly match referenced revision")
                    if revision.revision_number < last_number:
                        raise ValueError("ready revision number cannot move backwards")
                    last_number = revision.revision_number
                    announced.setdefault(revision.revision_id, set()).add(payload.module.module_id)
                elif not set(modules) <= announced.get(revision.revision_id, set()):
                    raise ValueError("success requires every module ready for the same revision")

    def _validate_attempts(self) -> None:
        run = self.history.run
        attempts = index_records(self.attempts, "attempt_id")
        if len({(attempt.step_id, attempt.attempt_number) for attempt in self.attempts}) != len(
            self.attempts
        ):
            raise ValueError("step/attempt_number pair must be unique")
        snapshot = replay_run(self.history)
        for attempt in self.attempts:
            if attempt.workspace_id != run.submission.workspace_id or attempt.run_id != run.run_id:
                raise ValueError("attempt must belong to current workspace/run")
            if attempt.authorized_after_seq > snapshot.last_seq:
                raise ValueError("attempt authorization cursor beyond current history")
            prefix = RunHistory(run=run, events=self.history.events[: attempt.authorized_after_seq])
            authorization = replay_run(prefix)
            if attempt.created_at < (authorization.last_event_at or run.created_at):
                raise ValueError("attempt created before its authorization cursor time")
            if (
                attempt.paid
                and attempt.dispatched_at is not None
                and not may_start_paid_step(authorization)
            ):
                raise ValueError("paid dispatch requires eligible running authorization")
            if snapshot.status in {"succeeded", "failed"} and attempt.status in {
                "prepared",
                "dispatched",
            }:
                raise ValueError("completed run cannot have unfinished attempts")
            if attempt.dispatched_at is not None and any(
                other.paid
                and other.status == "outcome_unknown"
                and other.step_id == attempt.step_id
                and other.attempt_number < attempt.attempt_number
                for other in self.attempts
            ):
                raise ValueError("unknown paid outcome prohibits automatic higher attempt dispatch")
        unknown = {
            attempt.attempt_id for attempt in self.attempts if attempt.status == "outcome_unknown"
        }
        if unknown != set(snapshot.unresolved_attempt_ids):
            raise ValueError("unknown attempts must exactly match current unresolved IDs")
        for event in self.history.events:
            payload = event.payload
            if isinstance(payload, (AwaitingReconciliationPayload, ReconciliationResolvedPayload)):
                if any(identity not in attempts for identity in payload.attempt_ids):
                    raise ValueError("reconciliation references an unknown attempt")
                if isinstance(payload, ReconciliationResolvedPayload) and any(
                    attempts[identity].status not in {"succeeded", "failed"}
                    for identity in payload.attempt_ids
                ):
                    raise ValueError("resolved attempts require a known succeeded/failed outcome")

    def _validate_usage(self) -> None:
        run = self.history.run
        if self.usage is None:
            if any(attempt.paid and attempt.dispatched_at is not None for attempt in self.attempts):
                raise ValueError("dispatched paid attempts require a usage book")
            return
        if self.usage.window.workspace_id != run.submission.workspace_id:
            raise ValueError("usage window workspace differs from run")
        attempts = index_records(self.attempts, "attempt_id")
        entries = index_records(self.usage.entries, "attempt_id")
        reservations = index_records(self.usage.reservations, "reservation_id")
        for supplied_entry in self.usage.entries:
            if supplied_entry.run_id == run.run_id and supplied_entry.attempt_id not in attempts:
                raise ValueError("current-run entry must reference a supplied attempt")
        for attempt in self.attempts:
            entry = entries.get(attempt.attempt_id)
            if entry is None:
                if attempt.paid and attempt.dispatched_at is not None:
                    raise ValueError("dispatched paid attempt requires exactly one usage entry")
                continue
            if entry.run_id != run.run_id or (entry.provider, entry.operation, entry.model) != (
                attempt.provider,
                attempt.operation,
                attempt.model,
            ):
                raise ValueError("usage entry run/provider/operation/model differs from attempt")
            reservation = reservations[entry.reservation_id]
            if attempt.dispatched_at is not None and reservation.created_at > attempt.dispatched_at:
                raise ValueError("reservation must predate dispatch")
            if attempt.status == "outcome_unknown" and entry.charge_status not in {
                "unknown",
                "estimated",
            }:
                raise ValueError("unknown outcome requires unknown/estimated charge")
            if attempt.status in {"dispatched", "outcome_unknown"} and reservation.status != "held":
                raise ValueError("in-flight/unknown attempt requires held reservation")
