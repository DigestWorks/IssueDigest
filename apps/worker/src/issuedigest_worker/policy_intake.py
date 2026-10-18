"""Strict private reviewed-capture approval and explicit intake coordination."""

import json
from hashlib import sha256
from typing import Literal

from issuedigest_storage.operator_security import reject_json_constant, unique_json_object
from issuedigest_storage.policy_collection import PolicyCollectionConfig
from issuedigest_storage.policy_intake import (
    PolicyIntakeCommitUnknown,
    PolicyIntakeEntry,
    PolicyIntakeError,
    PolicyIntakePlan,
    PolicyIntakeRepository,
    PolicyIntakeResult,
)
from pydantic import UUID4, Field, field_validator
from sqlalchemy import Engine

from .bounds import preflight_model
from .models import PreparationError, _PrivateModel
from .policy_changes import PolicyChangeReport
from .policy_collection import _baseline, parse_policy_collection_job
from .policy_job import PolicyJob, parse_policy_job
from .policy_prepare import prepare_policy_candidates

MAX_POLICY_INTAKE_APPROVAL_BYTES = 256 * 1024


class PolicyIntakeApproval(_PrivateModel):
    schema_version: Literal[1]
    workspace_id: UUID4 = Field(repr=False)
    collection: PolicyCollectionConfig = Field(repr=False)
    attempt_id: UUID4 = Field(repr=False)
    approval: PolicyJob = Field(repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid approval version")
        return value


def parse_policy_intake_approval(raw: str | bytes) -> PolicyIntakeApproval:
    """Reject ambiguous, oversized or coerced envelopes; reuse both existing parsers."""
    try:
        if type(raw) is str:
            if len(raw) > MAX_POLICY_INTAKE_APPROVAL_BYTES:
                raise ValueError("Approval budget exceeded")
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_POLICY_INTAKE_APPROVAL_BYTES:
            raise ValueError("Approval budget exceeded")
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
        )
        value = PolicyIntakeApproval.model_validate_json(
            json.dumps(data, ensure_ascii=False, allow_nan=False), strict=True
        )
        parse_policy_collection_job(json.dumps(data["collection"], allow_nan=False))
        parse_policy_job(json.dumps(data["approval"], ensure_ascii=False, allow_nan=False))
        if set(value.collection.news_ids) != {s.news_id for s in value.approval.sources}:
            raise ValueError("Approval scope mismatch")
        return value
    except Exception:
        raise PreparationError("Unable to validate policy intake approval") from None


def _revalidate(approval: PolicyIntakeApproval) -> PolicyIntakeApproval:
    if (
        type(approval) is not PolicyIntakeApproval
        or set(approval.__dict__) != set(PolicyIntakeApproval.model_fields)
        or approval.__pydantic_extra__
        or type(approval.collection) is not PolicyCollectionConfig
        or approval.collection.__pydantic_extra__
    ):
        raise ValueError("Invalid approval input")
    # Strict field validation bounds caller-forged config graphs before serialization.
    collection = PolicyCollectionConfig.model_validate(
        dict(approval.collection.__dict__), strict=True
    )
    preflight_model(approval.approval)
    value = PolicyIntakeApproval.model_validate(
        {**approval.__dict__, "collection": collection}, strict=True
    )
    return parse_policy_intake_approval(value.model_dump_json(warnings="error"))


def prepare_policy_intake_plan(engine: Engine, approval: PolicyIntakeApproval) -> PolicyIntakePlan:
    """Load only the selected success; re-extract its approved semantics without writes."""
    try:
        approval = _revalidate(approval)
        baseline = PolicyIntakeRepository(engine).load_capture(
            approval.collection, approval.attempt_id
        )
        capture_raw = _baseline(baseline, approval.collection)
        candidates = prepare_policy_candidates(
            approval.approval, capture_raw, approval.workspace_id
        )
        # _baseline already rejected duplicate JSON and checked every after-side semantic.
        report = PolicyChangeReport.model_validate_json(baseline.report_bytes, strict=True)
        fingerprints = {s.source_id: s.after_fingerprint for s in report.sources}
        entries = []
        for snapshot, presentation in zip(
            candidates.snapshots, candidates.presentations, strict=True
        ):
            fingerprint = fingerprints[snapshot.bundle.document.source_id]
            if fingerprint is None:
                raise ValueError("Missing observed fingerprint")
            entries.append(
                PolicyIntakeEntry(
                    snapshot_id=snapshot.snapshot_id,
                    bundle=snapshot.bundle,
                    presentation=presentation,
                    fingerprint_sha256=fingerprint,
                )
            )
        canonical = json.dumps(
            approval.approval.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        return PolicyIntakePlan(
            collection=approval.collection,
            attempt_id=approval.attempt_id,
            workspace_id=approval.workspace_id,
            approval_sha256=sha256(canonical).hexdigest(),
            entries=tuple(entries),
        )
    except Exception:
        raise PolicyIntakeError() from None


def intake_policy_capture(
    engine: Engine, approval: PolicyIntakeApproval, *, apply: bool
) -> PolicyIntakeResult:
    """Explicit check/apply only; callers own private engine cleanup. Never retry a commit."""
    try:
        if type(apply) is not bool:
            raise ValueError("Explicit intake mode required")
        plan = prepare_policy_intake_plan(engine, approval)
        repository = PolicyIntakeRepository(engine)
        return repository.apply(plan) if apply else repository.check(plan)
    except PolicyIntakeCommitUnknown:
        raise PolicyIntakeCommitUnknown() from None
    except Exception:
        raise PolicyIntakeError() from None
