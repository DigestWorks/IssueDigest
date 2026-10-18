"""Explicit bounded policy collection; no import IO, scheduling or evidence registration."""

import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

import httpx2 as httpx
from issuedigest_connectors import capture_policy, parse_policy_capture, serialize_policy_capture
from issuedigest_storage.operator_security import reject_json_constant, unique_json_object
from issuedigest_storage.policy_collection import (
    PolicyCollectionAttempt,
    PolicyCollectionBaseline,
    PolicyCollectionConfig,
    PolicyCollectionRepository,
)
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Engine

from .policy_changes import PolicyChangeReport, compare_policy_captures

MAX_POLICY_COLLECTION_JOB_BYTES = 8192
FailureCode = Literal["capture_failed", "validation_failed"]


class _Summary(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class PolicyCollectionPoll(_Summary):
    schema_version: Literal[1] = 1
    outcome: Literal["busy", "not_due", "attempt_limit", "succeeded", "failed"]
    failure_code: FailureCode | None = None
    new: int = 0
    changed: int = 0
    unchanged: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


class PolicyCollectionAttemptSummary(_Summary):
    sequence: int
    state: Literal["running", "succeeded", "failed"]
    started_at: datetime
    finished_at: datetime | None
    failure_code: Literal["capture_failed", "validation_failed", "interrupted"] | None


class PolicyCollectionStatusSummary(_Summary):
    schema_version: Literal[1] = 1
    attempt_count: int
    latest: PolicyCollectionAttemptSummary | None
    last_success: PolicyCollectionAttemptSummary | None
    age_seconds: float | None
    stale: bool


def parse_policy_collection_job(raw: str | bytes) -> PolicyCollectionConfig:
    """Strict JSON boundary; repository independently revalidates the resulting config."""
    try:
        if type(raw) is str:
            if len(raw) > MAX_POLICY_COLLECTION_JOB_BYTES:
                raise ValueError("Job size exceeded")
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or not 0 < len(raw) <= MAX_POLICY_COLLECTION_JOB_BYTES:
            raise ValueError("Job size exceeded")
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
        )
        if (
            type(data) is not dict
            or type(data.get("collection_id")) is not str
            or type(data.get("news_ids")) is not list
        ):
            raise ValueError("Invalid job shape")
        data["collection_id"] = UUID(data["collection_id"])
        data["news_ids"] = tuple(data["news_ids"])
        return PolicyCollectionConfig.model_validate(data, strict=True)
    except Exception:
        raise ValueError("Unable to validate policy collection job") from None


def _now() -> datetime:
    return datetime.now(UTC)


def _capture_scope(raw: bytes, config: PolicyCollectionConfig) -> datetime:
    capture = parse_policy_capture(raw)
    if tuple(sorted(article.news_id for article in capture.articles)) != config.news_ids:
        raise ValueError("Invalid collection scope")
    return capture.collected_at


def _baseline(raw: PolicyCollectionBaseline, config: PolicyCollectionConfig) -> bytes:
    """Validate eligible semantics and the stored report's observable after-side."""
    collected_at = _capture_scope(raw.capture_bytes, config)
    if (
        raw.attempt.finished_at is None
        or not raw.attempt.started_at <= collected_at <= raw.attempt.finished_at
    ):
        raise ValueError("Invalid baseline time")
    # Existing comparison re-extracts the body and license, including identity checks.
    expected = compare_policy_captures(raw.capture_bytes)
    data = json.loads(
        raw.report_bytes.decode("utf-8"),
        object_pairs_hook=unique_json_object,
        parse_constant=reject_json_constant,
    )
    report = PolicyChangeReport.model_validate_json(json.dumps(data, allow_nan=False), strict=True)
    if (
        report.after_capture_sha256 != sha256(raw.capture_bytes).hexdigest()
        or report.after_collected_at != collected_at
        or tuple(s.source_id for s in report.sources) != config.news_ids
        or (report.before_capture_sha256 is None) != (report.before_collected_at is None)
        or (report.before_collected_at is not None and report.before_collected_at >= collected_at)
    ):
        raise ValueError("Invalid baseline report")
    first = report.before_capture_sha256 is None
    for stored, current in zip(report.sources, expected.sources, strict=True):
        if stored.after_fingerprint != current.after_fingerprint:
            raise ValueError("Invalid baseline fingerprint")
        if first:
            valid = (
                stored.status == "new"
                and stored.before_fingerprint is None
                and not stored.changed_fields
            )
        elif stored.status == "unchanged":
            valid = (
                stored.before_fingerprint == stored.after_fingerprint and not stored.changed_fields
            )
        elif stored.status == "changed":
            valid = (
                stored.before_fingerprint is not None
                and stored.before_fingerprint != stored.after_fingerprint
                and bool(stored.changed_fields)
                and stored.changed_fields == tuple(sorted(set(stored.changed_fields)))
            )
        else:
            valid = False
        if not valid:
            raise ValueError("Invalid baseline source state")
    return raw.capture_bytes


def poll_policy_collection(
    engine: Engine,
    config: PolicyCollectionConfig,
    *,
    clock: Callable[[], datetime] = _now,
    transport: httpx.BaseTransport | None = None,
) -> PolicyCollectionPoll:
    """One admitted attempt only. Storage/unknown commit errors propagate without retry."""
    with PolicyCollectionRepository(engine).lease(config) as session:
        if session is None:
            return PolicyCollectionPoll(outcome="busy")
        start = session.start(now=clock())
        if start.outcome != "started":
            return PolicyCollectionPoll(outcome=start.outcome)
        attempt = start.attempt
        assert attempt is not None
        # Storage reads stay outside validation catches: never terminalize a DB error.
        baseline = session.baseline()
        failure: FailureCode | None = None
        previous = None
        try:
            previous = _baseline(baseline, config) if baseline is not None else None
        except Exception:
            failure = "validation_failed"
        capture_raw = b""
        report: PolicyChangeReport | None = None
        if failure is None:
            try:
                request_at = clock()
                if (
                    type(request_at) is not datetime
                    or request_at.tzinfo is None
                    or request_at.utcoffset() is None
                    or request_at < attempt.started_at
                ):
                    raise ValueError("Invalid request time")
            except Exception:
                failure = "validation_failed"
        if failure is None:
            try:
                capture = capture_policy(
                    config.news_ids, collected_at=request_at, transport=transport
                )
            except Exception:
                failure = "capture_failed"
            else:
                try:
                    capture_raw = serialize_policy_capture(capture)
                    _capture_scope(capture_raw, config)
                    report = compare_policy_captures(capture_raw, previous_raw=previous)
                except Exception:
                    failure = "validation_failed"
        finished_at = clock()
        if report is not None and failure is None:
            try:
                if finished_at < report.after_collected_at:
                    raise ValueError("Invalid completion time")
            except Exception:
                failure = "validation_failed"
        if failure is not None:
            session.fail(attempt.attempt_id, failure, finished_at=finished_at)
            return PolicyCollectionPoll(
                outcome="failed",
                failure_code=failure,
                started_at=attempt.started_at,
                finished_at=finished_at,
            )
        assert report is not None
        session.succeed(
            attempt.attempt_id,
            capture_raw,
            report.model_dump_json(warnings="error").encode("utf-8"),
            finished_at=finished_at,
        )
        return PolicyCollectionPoll(
            outcome="succeeded",
            new=sum(s.status == "new" for s in report.sources),
            changed=sum(s.status == "changed" for s in report.sources),
            unchanged=sum(s.status == "unchanged" for s in report.sources),
            started_at=attempt.started_at,
            finished_at=finished_at,
        )


def _attempt_summary(
    attempt: PolicyCollectionAttempt | None,
) -> PolicyCollectionAttemptSummary | None:
    if attempt is None:
        return None
    return PolicyCollectionAttemptSummary(
        sequence=attempt.sequence,
        state=attempt.state,
        started_at=attempt.started_at,
        finished_at=attempt.finished_at,
        failure_code=attempt.failure_code,
    )


def policy_collection_status(
    engine: Engine, config: PolicyCollectionConfig, *, now: datetime | None = None
) -> PolicyCollectionStatusSummary:
    state = PolicyCollectionRepository(engine).status(config, now=_now() if now is None else now)
    return PolicyCollectionStatusSummary(
        attempt_count=state.attempt_count,
        latest=_attempt_summary(state.latest),
        last_success=_attempt_summary(state.last_success),
        age_seconds=state.age_seconds,
        stale=state.stale,
    )
