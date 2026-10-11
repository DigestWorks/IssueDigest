"""Synthetic execution histories: sequence, cancellation and paid-step policy."""

import importlib
import importlib.util
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta, timezone
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

ex = (
    importlib.import_module("issuedigest_domain.execution")
    if importlib.util.find_spec("issuedigest_domain.execution")
    else None
)


def uid():
    return str(uuid4())


def input_data(**changes):
    return {
        "question": " 질문 😀 ",
        "selected_version_ids": [],
        "base_revision_id": None,
        "versions": {
            "model_config_version": "config1",
            "prompt_version": "prompt1",
            "tool_registry_version": "tools1",
            "execution_engine_version": "engine1",
        },
        **changes,
    }


def submission_data(**changes):
    return {
        "workspace_id": uid(),
        "requester_id": uid(),
        "submission_key": " key ",
        "input": input_data(),
        **changes,
    }


def run_data(**changes):
    submission = submission_data()
    # Independent JSON normalization, including literal version defaults.
    dumped = deepcopy(submission["input"])
    dumped["versions"].update(
        ontology_version="issuedigest-relations-v1", ui_schema_version="issuedigest-canvas-v1"
    )
    return {
        "run_id": uid(),
        "request_id": uid(),
        "trace_id": uid(),
        "submission": submission,
        "input_sha256": sha256(
            json.dumps(dumped, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
        ).hexdigest(),
        "created_at": "2026-10-01T00:00:00Z",
        **changes,
    }


def event(run, seq, kind, **payload):
    return {
        "workspace_id": run["submission"]["workspace_id"],
        "run_id": run["run_id"],
        "seq": seq,
        "occurred_at": "2026-10-01T00:00:01Z",
        "payload": {"kind": kind, **deepcopy(payload)},
    }


def history_data(*payloads, run=None):
    run = run or run_data()
    return {
        "run": run,
        "events": [event(run, i + 1, kind, **fields) for i, (kind, fields) in enumerate(payloads)],
    }


def module_data(**changes):
    return {
        "kind": "evidence",
        "module_id": uid(),
        "title": "제공 인용",
        "span": "full",
        "citation_ids": [uid()],
        "actions": [],
        **changes,
    }


def attempt_data(**changes):
    return {
        "attempt_id": uid(),
        "workspace_id": uid(),
        "run_id": uid(),
        "step_id": uid(),
        "attempt_number": 1,
        "authorized_after_seq": 2,
        "provider": "synthetic",
        "operation": "generate",
        "model": None,
        "paid": True,
        "status": "prepared",
        "created_at": "2026-10-01T00:00:02Z",
        "dispatched_at": None,
        "finished_at": None,
        "result_id": None,
        "provider_request_id": None,
        "provider_idempotency_key": None,
        "supports_query": False,
        "supports_cancel": False,
        **changes,
    }


def test_execution_available():
    assert ex is not None, "execution contract missing"


@pytest.fixture(autouse=True)
def require_contract(request):
    if ex is None and request.node.name != "test_execution_available":
        pytest.skip("models not yet available")


def test_hash_preserves_unicode_whitespace_versions_and_selected_order():
    data = input_data(selected_version_ids=[uid(), uid()])
    validated = ex.RunInput.model_validate(data)
    normalized = deepcopy(data)
    normalized["versions"].update(
        ontology_version="issuedigest-relations-v1", ui_schema_version="issuedigest-canvas-v1"
    )
    expected = sha256(
        json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    assert ex.hash_run_input(validated) == expected
    assert (
        ex.hash_run_input(
            ex.RunInput.model_validate({**data, "question": data["question"].strip()})
        )
        != expected
    )
    assert (
        ex.hash_run_input(
            ex.RunInput.model_validate(
                {**data, "selected_version_ids": data["selected_version_ids"][::-1]}
            )
        )
        != expected
    )
    normalized["versions"]["prompt_version"] = "prompt2"
    assert ex.hash_run_input(ex.RunInput.model_validate(normalized)) != expected


def test_submission_reuse_conflict_and_scope():
    run = ex.Run.model_validate(run_data())
    submission = run.submission
    assert ex.assess_submission(None, submission).action == "create"
    assert ex.assess_submission(run, submission).model_dump(mode="json") == {
        "action": "reuse",
        "existing_run_id": str(run.run_id),
    }
    changed = submission.model_dump(mode="json")
    changed["input"]["question"] = "다른 질문"
    assert ex.assess_submission(run, ex.RunSubmission.model_validate(changed)).action == "conflict"
    for field in ["workspace_id", "requester_id", "submission_key"]:
        changed = submission.model_dump(mode="json")
        changed[field] = "different" if field == "submission_key" else uid()
        result = ex.assess_submission(run, ex.RunSubmission.model_validate(changed))
        assert result.action == "create" and result.existing_run_id is None


def test_run_hash_and_selection_validation():
    data = run_data(input_sha256="a" * 64)
    with pytest.raises(ValidationError):
        ex.Run.model_validate(data)
    identity = uid()
    with pytest.raises(ValidationError):
        ex.RunInput.model_validate(input_data(selected_version_ids=[identity, identity]))
    for value in ["", "  ", 1, True]:
        with pytest.raises(ValidationError):
            ex.RunInput.model_validate(input_data(question=value))


@pytest.mark.parametrize("action,identity", [("create", "id"), ("reuse", None), ("conflict", None)])
def test_assessment_rejects_result_contradiction(action, identity):
    with pytest.raises(ValidationError):
        ex.SubmissionAssessment(action=action, existing_run_id=uid() if identity else None)


def test_replay_initial_running_and_success_preserves_last_stage():
    data = history_data()
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert (snap.status, snap.accepted, snap.last_seq, snap.last_event_at) == (
        "queued",
        False,
        0,
        None,
    )
    revision = uid()
    data = history_data(
        ("run.accepted", {}),
        ("stage.changed", {"stage": "composition"}),
        ("module.ready", {"revision_id": revision, "module": module_data()}),
        ("run.succeeded", {"revision_id": revision}),
    )
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert (
        snap.status,
        snap.current_revision_id,
        snap.pending_revision_id,
        snap.stage,
        snap.last_seq,
    ) == ("succeeded", UUID(revision), None, "composition", 4)


def test_paid_step_policy_at_queued_running_and_cancel_boundaries():
    data = history_data(("run.accepted", {}), ("stage.changed", {"stage": "tools"}))
    history = ex.RunHistory.model_validate(data)
    assert ex.may_start_paid_step(ex.replay_run(history)) is True
    data["events"].append(event(data["run"], 3, "run.cancel_requested"))
    assert ex.may_start_paid_step(ex.replay_run(ex.RunHistory.model_validate(data))) is False
    assert (
        ex.may_start_paid_step(ex.replay_run(ex.RunHistory.model_validate(history_data()))) is False
    )
    assert (
        ex.may_start_paid_step(
            ex.replay_run(ex.RunHistory.model_validate(history_data(("run.accepted", {}))))
        )
        is False
    )


def test_cancel_preserves_base_and_unknown_until_late_reconciliation():
    a, b, base = uid(), uid(), uid()
    data = history_data(
        ("run.accepted", {}),
        ("stage.changed", {"stage": "tools"}),
        ("module.ready", {"revision_id": uid(), "module": module_data()}),
        ("run.awaiting_reconciliation", {"attempt_ids": [a, b]}),
        ("run.cancel_requested", {}),
        ("run.cancelled", {}),
    )
    data["run"]["submission"]["input"]["base_revision_id"] = base
    data["run"]["input_sha256"] = ex.hash_run_input(
        ex.RunInput.model_validate(data["run"]["submission"]["input"])
    )
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert (
        snap.status,
        str(snap.current_revision_id),
        snap.pending_revision_id,
        snap.cancel_requested,
    ) == ("cancelled", base, None, True)
    assert tuple(map(str, snap.unresolved_attempt_ids)) == (a, b)
    data["events"].append(event(data["run"], 7, "run.reconciliation_resolved", attempt_ids=[a]))
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert snap.status == "cancelled" and tuple(map(str, snap.unresolved_attempt_ids)) == (b,)
    data["events"].append(event(data["run"], 8, "run.reconciliation_resolved", attempt_ids=[b]))
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert snap.status == "cancelled" and not snap.unresolved_attempt_ids


@pytest.mark.parametrize("cancel", [False, True])
def test_reconciliation_resumes_according_to_cancel_intent(cancel):
    a, b = uid(), uid()
    payloads = [("run.accepted", {}), ("stage.changed", {"stage": "search"})]
    if cancel:
        payloads.append(("run.cancel_requested", {}))
    payloads += [
        ("run.awaiting_reconciliation", {"attempt_ids": [a, b]}),
        ("run.reconciliation_resolved", {"attempt_ids": [b]}),
    ]
    data = history_data(*payloads)
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert snap.status == "awaiting_reconciliation"
    assert not ex.may_start_paid_step(snap)
    data["events"].append(
        event(data["run"], len(data["events"]) + 1, "run.reconciliation_resolved", attempt_ids=[a])
    )
    assert ex.replay_run(ex.RunHistory.model_validate(data)).status == (
        "cancel_requested" if cancel else "running"
    )


@pytest.mark.parametrize("ending", ["run.failed", "run.cancelled"])
def test_failure_and_cancellation_keep_last_normal_revision(ending):
    data = history_data(
        ("run.accepted", {}),
        ("stage.changed", {"stage": "validation"}),
        ("module.ready", {"revision_id": uid(), "module": module_data()}),
        (
            ending,
            {"error_code": "incomplete_output", "retryable": True}
            if ending == "run.failed"
            else {},
        ),
    )
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert snap.current_revision_id == snap.base_revision_id and snap.pending_revision_id is None


@pytest.mark.parametrize(
    "payloads",
    [
        [("stage.changed", {"stage": "tools"})],
        [("run.accepted", {}), ("run.accepted", {})],
        [("run.accepted", {}), ("module.ready", {"revision_id": uid(), "module": module_data()})],
        [
            ("run.accepted", {}),
            ("run.cancel_requested", {}),
            ("run.succeeded", {"revision_id": uid()}),
        ],
        [
            ("run.accepted", {}),
            ("run.succeeded", {"revision_id": uid()}),
            ("stage.changed", {"stage": "tools"}),
        ],
        [
            ("run.accepted", {}),
            ("run.cancelled", {}),
            ("module.ready", {"revision_id": uid(), "module": module_data()}),
        ],
        [
            ("run.accepted", {}),
            ("stage.changed", {"stage": "tools"}),
            ("run.awaiting_reconciliation", {"attempt_ids": [uid()]}),
            ("run.failed", {"error_code": "internal_error", "retryable": False}),
        ],
        [
            ("run.accepted", {}),
            ("stage.changed", {"stage": "tools"}),
            ("run.reconciliation_resolved", {"attempt_ids": [uid()]}),
        ],
    ],
)
def test_rejects_invalid_state_transitions(payloads):
    with pytest.raises((ValidationError, ValueError)):
        ex.replay_run(ex.RunHistory.model_validate(history_data(*payloads)))


def test_rejects_duplicate_pending_and_previously_resolved_attempt():
    a = uid()
    data = history_data(
        ("run.accepted", {}),
        ("stage.changed", {"stage": "tools"}),
        ("run.awaiting_reconciliation", {"attempt_ids": [a]}),
        ("run.cancel_requested", {}),
        ("run.awaiting_reconciliation", {"attempt_ids": [a]}),
    )
    with pytest.raises((ValidationError, ValueError)):
        ex.replay_run(ex.RunHistory.model_validate(data))
    data = history_data(
        ("run.accepted", {}),
        ("stage.changed", {"stage": "tools"}),
        ("run.awaiting_reconciliation", {"attempt_ids": [a]}),
        ("run.reconciliation_resolved", {"attempt_ids": [a]}),
        ("run.awaiting_reconciliation", {"attempt_ids": [a]}),
    )
    with pytest.raises((ValidationError, ValueError)):
        ex.replay_run(ex.RunHistory.model_validate(data))


@pytest.mark.parametrize(
    "change", ["gap", "duplicate", "workspace", "run", "early", "kind", "extra"]
)
def test_history_rejects_gap_conflict_foreign_and_unknown_fields(change):
    data = history_data(("run.accepted", {}), ("stage.changed", {"stage": "tools"}))
    item = data["events"][1]
    if change == "gap":
        item["seq"] = 3
    if change == "duplicate":
        item["seq"] = 1
    if change == "workspace":
        item["workspace_id"] = uid()
    if change == "run":
        item["run_id"] = uid()
    if change == "early":
        item["occurred_at"] = "2026-09-30T23:59:59Z"
    if change == "kind":
        item["payload"]["kind"] = "arbitrary"
    if change == "extra":
        item["payload"]["progress"] = 0.5
    with pytest.raises(ValidationError):
        ex.RunHistory.model_validate(data)


def test_seq_is_order_even_when_event_clock_moves_back():
    data = history_data(("run.accepted", {}), ("stage.changed", {"stage": "tools"}))
    data["events"][0]["occurred_at"] = "2026-10-01T00:00:05Z"
    assert ex.replay_run(ex.RunHistory.model_validate(data)).last_seq == 2


def test_events_after_returns_exact_tail_and_latest_snapshot():
    history = ex.RunHistory.model_validate(
        history_data(("run.accepted", {}), ("stage.changed", {"stage": "search"}))
    )
    batch = ex.events_after(history, 1)
    assert batch.events == history.events[1:]
    assert batch.latest_snapshot.status == "running" and batch.latest_snapshot.last_seq == 2
    assert ex.events_after(history, 2).events == ()
    assert ex.events_after(history, 0).events == history.events


@pytest.mark.parametrize("cursor", [True, "1", -1, 3, 2**53, 1.0])
def test_cursor_rejects_coercion_unsafe_and_future(cursor):
    history = ex.RunHistory.model_validate(
        history_data(("run.accepted", {}), ("stage.changed", {"stage": "search"}))
    )
    with pytest.raises(ValueError):
        ex.events_after(history, cursor)


@pytest.mark.parametrize("value", [True, "1", 1.0, 0, -1, 2**53])
def test_event_seq_is_strict_safe_positive(value):
    data = history_data(("run.accepted", {}))
    data["events"][0]["seq"] = value
    with pytest.raises(ValidationError):
        ex.RunHistory.model_validate(data)


@pytest.mark.parametrize("value", [True, "1", 1.0, 2, 0])
def test_new_schema_version_is_strict(value):
    with pytest.raises(ValidationError):
        ex.Run.model_validate({**run_data(), "schema_version": value})


@pytest.mark.parametrize(
    "value",
    [
        0,
        1770000000,
        True,
        "1770000000",
        "2026-10-01",
        "2026-10-01T00:00:00",
        datetime(2026, 10, 1),
        "0001-01-01T00:00:00+14:00",
        "9999-12-31T23:59:59-14:00",
    ],
)
def test_new_instants_reject_epochs_naive_date_and_normalization_overflow(value):
    with pytest.raises(ValidationError):
        ex.Run.model_validate({**run_data(), "created_at": value})


def test_utc_tuple_frozen_and_json_roundtrip():
    data = history_data(("run.accepted", {}))
    data["run"]["created_at"] = datetime(2026, 10, 1, 9, tzinfo=timezone(timedelta(hours=9)))
    history = ex.RunHistory.model_validate(data)
    assert history.run.created_at == datetime(2026, 10, 1, tzinfo=UTC)
    assert isinstance(history.events, tuple) and isinstance(
        history.run.submission.input.selected_version_ids, tuple
    )
    with pytest.raises(ValidationError):
        history.run.created_at = datetime.now(UTC)
    assert ex.RunHistory.model_validate_json(history.model_dump_json()) == history


def test_snapshot_and_batch_reject_internally_contradictory_results():
    history = ex.RunHistory.model_validate(
        history_data(("run.accepted", {}), ("stage.changed", {"stage": "search"}))
    )
    data = ex.replay_run(history).model_dump(mode="json")
    for change in [
        {"accepted": False},
        {"last_seq": 0},
        {"last_event_at": None},
        {"stage": None},
        {"cancel_requested": True},
        {"unresolved_attempt_ids": [uid()]},
        {"status": "failed", "current_revision_id": uid()},
        {"status": "succeeded", "current_revision_id": None},
        {"status": "cancelled", "cancel_requested": True, "pending_revision_id": uid()},
    ]:
        with pytest.raises(ValidationError):
            ex.RunSnapshot.model_validate({**data, **change})
    batch = ex.events_after(history, 0).model_dump(mode="json")
    for change in [{"after_seq": 3}, {"events": []}, {"workspace_id": uid()}, {"run_id": uid()}]:
        with pytest.raises(ValidationError):
            ex.ReplayBatch.model_validate({**batch, **change})


@pytest.mark.parametrize(
    "status",
    [
        "prepared",
        "dispatched",
        "succeeded",
        "failed",
        "outcome_unknown",
        "cancelled_before_dispatch",
    ],
)
def test_call_attempt_status_timestamps_and_result(status):
    data = attempt_data(status=status)
    if status in ["dispatched", "succeeded", "failed", "outcome_unknown"]:
        data["dispatched_at"] = "2026-10-01T00:00:03Z"
    if status in ["succeeded", "failed", "outcome_unknown", "cancelled_before_dispatch"]:
        data["finished_at"] = "2026-10-01T00:00:04Z"
    if status == "succeeded":
        data["result_id"] = uid()
    assert ex.CallAttempt.model_validate_json(json.dumps(data)).status == status
    invalid = {**data, "finished_at": "2026-09-30T00:00:00Z"}
    with pytest.raises(ValidationError):
        ex.CallAttempt.model_validate(invalid)
    invalid = {**data, "result_id": None if status == "succeeded" else uid()}
    with pytest.raises(ValidationError):
        ex.CallAttempt.model_validate(invalid)


def test_new_display_and_provider_strings_reject_bytes_without_trimming_text():
    with pytest.raises(ValidationError):
        ex.RunInput.model_validate(input_data(question=b"question"))
    with pytest.raises(ValidationError):
        ex.CallAttempt.model_validate(attempt_data(provider=b"synthetic"))
    assert ex.RunInput.model_validate(input_data()).question == " 질문 😀 "


def test_terminal_rejects_every_late_event_except_resolution_on_cancelled():
    for kind in ["run.succeeded", "run.failed", "run.cancelled"]:
        fields = (
            {"revision_id": uid()}
            if kind == "run.succeeded"
            else (
                {"error_code": "internal_error", "retryable": False} if kind == "run.failed" else {}
            )
        )
        data = history_data(("run.accepted", {}), (kind, fields))
        for late_kind, late_fields in [
            ("run.cancel_requested", {}),
            ("run.cancelled", {}),
            ("run.failed", {"error_code": "internal_error", "retryable": False}),
            ("run.succeeded", {"revision_id": uid()}),
            ("run.reconciliation_resolved", {"attempt_ids": [uid()]}),
        ]:
            invalid = deepcopy(data)
            invalid["events"].append(event(data["run"], 3, late_kind, **late_fields))
            with pytest.raises(ValidationError):
                ex.RunHistory.model_validate(invalid)


def test_queued_snapshot_cannot_have_pending_module_revision():
    snap = ex.replay_run(ex.RunHistory.model_validate(history_data(("run.accepted", {}))))
    with pytest.raises(ValidationError):
        ex.RunSnapshot.model_validate({**snap.model_dump(), "pending_revision_id": uid()})


@pytest.mark.parametrize("field", ["paid", "supports_query", "supports_cancel"])
@pytest.mark.parametrize("value", [0, 1, "false", "true"])
def test_attempt_flags_are_strict_bool(field, value):
    with pytest.raises(ValidationError):
        ex.CallAttempt.model_validate(attempt_data(**{field: value}))


@pytest.mark.parametrize("field", ["attempt_number", "authorized_after_seq"])
@pytest.mark.parametrize("value", [True, "1", 1.0, -1, 2**53])
def test_attempt_counts_are_js_safe_and_strict(field, value):
    with pytest.raises(ValidationError):
        ex.CallAttempt.model_validate(attempt_data(**{field: value}))


def test_reconciliation_subset_keeps_order_and_can_add_distinct_pending_ids_after_cancel():
    a, b, c = uid(), uid(), uid()
    data = history_data(
        ("run.accepted", {}),
        ("stage.changed", {"stage": "tools"}),
        ("run.awaiting_reconciliation", {"attempt_ids": [a, b]}),
        ("run.cancel_requested", {}),
        ("run.awaiting_reconciliation", {"attempt_ids": [c]}),
        ("run.reconciliation_resolved", {"attempt_ids": [b]}),
    )
    snap = ex.replay_run(ex.RunHistory.model_validate(data))
    assert tuple(map(str, snap.unresolved_attempt_ids)) == (a, c)
    assert snap.status == "awaiting_reconciliation" and snap.cancel_requested


def test_attempt_accepts_exact_js_safe_upper_bound_and_json_rejects_coercion():
    data = attempt_data(attempt_number=2**53 - 1, authorized_after_seq=2**53 - 1)
    validated = ex.CallAttempt.model_validate_json(json.dumps(data))
    assert validated.attempt_number == 9007199254740991
    for field, value in [("attempt_number", True), ("authorized_after_seq", "1"), ("paid", 1)]:
        with pytest.raises(ValidationError):
            ex.CallAttempt.model_validate_json(json.dumps({**data, field: value}))


def test_failed_payload_rejects_coerced_retryable_and_unknown_error_codes():
    run = run_data()
    for fields in [
        {"error_code": "internal_error", "retryable": 1},
        {"error_code": "other", "retryable": False},
    ]:
        with pytest.raises(ValidationError):
            ex.RunEvent.model_validate(event(run, 2, "run.failed", **fields))
