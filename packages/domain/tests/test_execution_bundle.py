"""Full supplied-object linkage across event publication, attempts and monthly usage."""

import importlib
import importlib.util
import json
from copy import deepcopy

import pytest
from pydantic import ValidationError
from test_canvas import canvas_data, draft_data
from test_execution import attempt_data, event, run_data, uid
from test_usage import book_data

be = (
    importlib.import_module("issuedigest_domain.execution_bundle")
    if importlib.util.find_spec("issuedigest_domain.execution_bundle")
    else None
)


def execution_data(*, paid=False, unknown=False, cancelled=False):
    canvas = canvas_data()
    research, revision = canvas["research"], canvas["revision"]
    run = run_data()
    run["submission"]["workspace_id"] = research["workspace_id"]
    run["submission"]["input"]["selected_version_ids"] = revision["selected_version_ids"]
    from issuedigest_domain.execution import RunInput, hash_run_input

    run["input_sha256"] = hash_run_input(RunInput.model_validate(run["submission"]["input"]))
    revision["run_id"] = run["run_id"]
    events = [event(run, 1, "run.accepted"), event(run, 2, "stage.changed", stage="tools")]
    attempts, usage = [], None
    if paid:
        attempt = attempt_data(
            workspace_id=research["workspace_id"],
            run_id=run["run_id"],
            status="outcome_unknown" if unknown else "succeeded",
            dispatched_at="2026-10-01T00:00:03Z",
            finished_at="2026-10-01T00:00:04Z",
            result_id=None if unknown else uid(),
        )
        attempts = [attempt]
        usage = book_data()
        usage["window"]["workspace_id"] = research["workspace_id"]
        usage["reservations"][0].update(
            workspace_id=research["workspace_id"],
            run_id=run["run_id"],
            created_at="2026-10-01T00:00:02Z",
        )
        usage["entries"][0].update(
            workspace_id=research["workspace_id"],
            run_id=run["run_id"],
            attempt_id=attempt["attempt_id"],
        )
        if not unknown:
            usage["entries"][0].update(charge_status="confirmed", cost_microwon="6000000000")
    if unknown:
        events.append(
            event(run, 3, "run.awaiting_reconciliation", attempt_ids=[attempts[0]["attempt_id"]])
        )
    else:
        events.append(
            event(
                run,
                3,
                "module.ready",
                revision_id=revision["revision_id"],
                module=revision["draft"]["modules"][0],
            )
        )
    if cancelled:
        events.append(event(run, 4, "run.cancelled"))
    elif not unknown:
        events.append(event(run, 4, "run.succeeded", revision_id=revision["revision_id"]))
    return {
        "history": {"run": run, "events": events},
        "research": research,
        "revisions": [revision],
        "attempts": attempts,
        "usage": usage,
    }


def bundle(data):
    return be.RunExecutionBundle.model_validate_json(json.dumps(data))


def test_execution_bundle_available():
    assert be is not None, "full execution contract missing"


@pytest.fixture(autouse=True)
def require_contract(request):
    if be is None and request.node.name != "test_execution_bundle_available":
        pytest.skip("not available")


@pytest.mark.parametrize(
    "paid,unknown,cancelled",
    [
        (False, False, False),
        (True, False, False),
        (True, True, False),
        (True, True, True),
        (True, False, True),
    ],
)
def test_full_bundle_validates_answer_and_unknown_cancellation(paid, unknown, cancelled):
    data = execution_data(paid=paid, unknown=unknown, cancelled=cancelled)
    validated = bundle(data)
    assert be.RunExecutionBundle.model_validate_json(validated.model_dump_json()) == validated
    if unknown or cancelled:
        from issuedigest_domain.usage import assess_budget

        assert assess_budget(validated.usage, "0").used_microwon == (
            "35000000000" if unknown else "36000000000"
        )


def test_empty_research_and_successful_information_request_need_no_module_ready():
    data = execution_data()
    run = data["history"]["run"]
    from issuedigest_domain.execution import RunInput, hash_run_input

    run["submission"]["input"]["selected_version_ids"] = []
    run["input_sha256"] = hash_run_input(RunInput.model_validate(run["submission"]["input"]))
    data["research"] = {
        **data["research"],
        "evidence": [],
        "entities": [],
        "claims": [],
        "relations": [],
        "observations": [],
        "support_reviews": [],
    }
    data["revisions"][0].update(
        selected_version_ids=[],
        draft=draft_data(outcome="clarification_needed", modules=[], message="자료를 골라 주세요"),
    )
    data["history"]["events"] = [
        event(run, 1, "run.accepted"),
        event(run, 2, "run.succeeded", revision_id=data["revisions"][0]["revision_id"]),
    ]
    assert bundle(data).revisions[0].draft.outcome == "clarification_needed"


@pytest.mark.parametrize(
    "change",
    [
        "research_workspace",
        "revision_workspace",
        "attempt_workspace",
        "usage_workspace",
        "selected_unknown",
        "revision_selection_order",
        "base_missing",
        "base_same_run",
        "parent_missing",
        "parent_number",
        "revision_duplicate",
        "current_time",
        "ready_foreign_revision",
        "ready_changed_module",
        "success_without_ready",
        "success_foreign_revision",
    ],
)
def test_bundle_rejects_cross_reference_and_publication_conflicts(change):
    data = execution_data(paid=True)
    run, revision = data["history"]["run"], data["revisions"][0]
    if change == "research_workspace":
        data["research"]["workspace_id"] = uid()
    if change == "revision_workspace":
        revision["workspace_id"] = uid()
    if change == "attempt_workspace":
        data["attempts"][0]["workspace_id"] = uid()
    if change == "usage_workspace":
        data["usage"]["window"]["workspace_id"] = uid()
    if change == "selected_unknown":
        run["submission"]["input"]["selected_version_ids"] = [uid()]
        from issuedigest_domain.execution import RunInput, hash_run_input

        run["input_sha256"] = hash_run_input(RunInput.model_validate(run["submission"]["input"]))
    if change == "revision_selection_order":
        revision["selected_version_ids"] = []
    if change in ["base_missing", "base_same_run"]:
        run["submission"]["input"]["base_revision_id"] = (
            uid() if change == "base_missing" else revision["revision_id"]
        )
        from issuedigest_domain.execution import RunInput, hash_run_input

        run["input_sha256"] = hash_run_input(RunInput.model_validate(run["submission"]["input"]))
    if change == "parent_missing":
        revision.update(parent_revision_id=uid(), revision_number=2)
    if change == "parent_number":
        parent = deepcopy(revision)
        parent.update(revision_id=uid(), run_id=uid())
        data["revisions"].append(parent)
        revision.update(parent_revision_id=parent["revision_id"], revision_number=3)
    if change == "revision_duplicate":
        data["revisions"].append(deepcopy(revision))
    if change == "current_time":
        revision["validated_at"] = "2026-09-30T00:00:00Z"
    if change == "ready_foreign_revision":
        data["history"]["events"][2]["payload"]["revision_id"] = uid()
    if change == "ready_changed_module":
        data["history"]["events"][2]["payload"]["module"]["title"] = "different"
    if change == "success_without_ready":
        data["history"]["events"][2]["payload"] = {"kind": "stage.changed", "stage": "composition"}
    if change == "success_foreign_revision":
        data["history"]["events"][3]["payload"]["revision_id"] = uid()
    with pytest.raises(ValidationError):
        bundle(data)


def test_ancestor_base_chain_and_current_successor_revisions():
    data = execution_data()
    run, current = data["history"]["run"], data["revisions"][0]
    ancestor = deepcopy(current)
    ancestor.update(revision_id=uid(), run_id=uid(), validated_at="2026-09-01T00:00:00Z")
    base = deepcopy(ancestor)
    base.update(revision_id=uid(), parent_revision_id=ancestor["revision_id"], revision_number=2)
    current.update(parent_revision_id=base["revision_id"], revision_number=3)
    run["submission"]["input"]["base_revision_id"] = base["revision_id"]
    from issuedigest_domain.execution import RunInput, hash_run_input

    run["input_sha256"] = hash_run_input(RunInput.model_validate(run["submission"]["input"]))
    later = deepcopy(current)
    later.update(revision_id=uid(), parent_revision_id=current["revision_id"], revision_number=4)
    later["draft"]["modules"][0]["module_id"] = uid()
    data["revisions"] = [later, base, current, ancestor]
    data["history"]["events"][2]["payload"]["module"] = deepcopy(current["draft"]["modules"][0])
    data["history"]["events"][3] = event(
        run,
        4,
        "module.ready",
        revision_id=later["revision_id"],
        module=later["draft"]["modules"][0],
    )
    data["history"]["events"].append(
        event(run, 5, "run.succeeded", revision_id=later["revision_id"])
    )
    assert bundle(data)
    invalid = deepcopy(data)
    invalid["history"]["events"][2], invalid["history"]["events"][3] = (
        invalid["history"]["events"][3],
        invalid["history"]["events"][2],
    )
    invalid["history"]["events"][2]["seq"], invalid["history"]["events"][3]["seq"] = 3, 4
    with pytest.raises(ValidationError):
        bundle(invalid)
    invalid = deepcopy(data)
    invalid["revisions"][0].update(parent_revision_id=ancestor["revision_id"], revision_number=2)
    with pytest.raises(ValidationError):
        bundle(invalid)


@pytest.mark.parametrize(
    "change",
    [
        "attempt_run",
        "duplicate_attempt",
        "duplicate_step_number",
        "cursor_future",
        "cursor_queued",
        "created_before_cursor",
        "usage_missing",
        "entry_missing",
        "entry_provider",
        "entry_other_attempt",
        "reservation_after_dispatch",
        "unknown_not_pending",
        "pending_no_attempt",
        "unknown_confirmed",
        "unknown_settled",
        "unfinished_after_success",
    ],
)
def test_attempt_authorization_and_usage_cross_checks(change):
    data = execution_data(
        paid=True, unknown=change.startswith("unknown") or change == "pending_no_attempt"
    )
    attempt = data["attempts"][0]
    if change == "attempt_run":
        attempt["run_id"] = uid()
    if change == "duplicate_attempt":
        data["attempts"].append(deepcopy(attempt))
    if change == "duplicate_step_number":
        data["attempts"].append({**attempt, "attempt_id": uid()})
    if change == "cursor_future":
        attempt["authorized_after_seq"] = 99
    if change == "cursor_queued":
        attempt["authorized_after_seq"] = 1
    if change == "created_before_cursor":
        attempt.update(created_at="2026-10-01T00:00:00Z")
    if change == "usage_missing":
        data["usage"] = None
    if change == "entry_missing":
        data["usage"]["entries"] = []
    if change == "entry_provider":
        data["usage"]["entries"][0]["provider"] = "other"
        data["usage"]["pricing_snapshots"][0]["provider"] = "other"
    if change == "entry_other_attempt":
        data["usage"]["entries"][0]["attempt_id"] = uid()
    if change == "reservation_after_dispatch":
        data["usage"]["reservations"][0]["created_at"] = "2026-10-01T00:00:04Z"
    if change == "unknown_not_pending":
        data["history"]["events"] = data["history"]["events"][:2]
    if change == "pending_no_attempt":
        data["history"]["events"][2]["payload"]["attempt_ids"] = [uid()]
    if change == "unknown_confirmed":
        data["usage"]["entries"][0].update(charge_status="confirmed", cost_microwon="0")
    if change == "unknown_settled":
        data["usage"]["reservations"][0].update(
            status="settled", settled_at="2026-10-01T00:00:04Z", settled_microwon="0"
        )
        data["usage"]["entries"][0].update(charge_status="not_charged", cost_microwon="0")
    if change == "unfinished_after_success":
        attempt.update(status="dispatched", result_id=None, finished_at=None)
    with pytest.raises(ValidationError):
        bundle(data)


def test_unknown_blocks_retry_dispatch_and_allows_preparation_or_free_calls():
    data = execution_data(paid=True, unknown=True)
    old = data["attempts"][0]
    retry = {
        **old,
        "attempt_id": uid(),
        "attempt_number": 2,
        "status": "succeeded",
        "result_id": uid(),
    }
    data["attempts"].append(retry)
    data["usage"]["entries"].append(
        {
            **data["usage"]["entries"][0],
            "entry_id": uid(),
            "attempt_id": retry["attempt_id"],
            "charge_status": "confirmed",
            "cost_microwon": "1",
        }
    )
    with pytest.raises(ValidationError):
        bundle(data)
    retry.update(
        status="prepared",
        dispatched_at=None,
        finished_at=None,
        result_id=None,
        authorized_after_seq=3,
    )
    data["usage"]["entries"].pop()
    assert bundle(data)
    data = execution_data()
    data["attempts"] = [
        attempt_data(
            workspace_id=data["research"]["workspace_id"],
            run_id=data["history"]["run"]["run_id"],
            status="succeeded",
            paid=False,
            dispatched_at="2026-10-01T00:00:03Z",
            finished_at="2026-10-01T00:00:04Z",
            result_id=uid(),
        )
    ]
    assert bundle(data)


def test_late_resolve_after_cancel_keeps_screen_and_requires_known_attempt_status():
    data = execution_data(paid=True, unknown=True, cancelled=True)
    run, attempt = data["history"]["run"], data["attempts"][0]
    data["history"]["events"].append(
        event(run, 5, "run.reconciliation_resolved", attempt_ids=[attempt["attempt_id"]])
    )
    with pytest.raises(ValidationError):
        bundle(data)
    attempt.update(status="failed")
    data["usage"]["entries"][0].update(charge_status="confirmed", cost_microwon="6000000000")
    validated = bundle(data)
    from issuedigest_domain.execution import replay_run

    assert replay_run(validated.history).status == "cancelled"
    from issuedigest_domain.usage import assess_budget

    assert assess_budget(validated.usage, "0").used_microwon == "36000000000"


def test_cancel_allows_already_dispatched_but_rejects_new_paid_start_after_cancel():
    data = execution_data(paid=True, cancelled=True)
    attempt = data["attempts"][0]
    attempt.update(status="dispatched", finished_at=None, result_id=None)
    assert bundle(data)
    attempt.update(authorized_after_seq=4)
    with pytest.raises(ValidationError):
        bundle(data)


def test_usage_book_may_include_other_run_without_certifying_its_history():
    data = execution_data(paid=True)
    other = deepcopy(data["usage"]["reservations"][0])
    other.update(reservation_id=uid(), run_id=uid())
    data["usage"]["reservations"].append(other)
    data["usage"]["entries"].append(
        {
            **data["usage"]["entries"][0],
            "entry_id": uid(),
            "attempt_id": uid(),
            "reservation_id": other["reservation_id"],
            "run_id": other["run_id"],
        }
    )
    assert bundle(data)


def test_unrelated_valid_historical_revision_can_be_supplied():
    data = execution_data()
    historical = deepcopy(data["revisions"][0])
    historical.update(revision_id=uid(), run_id=uid(), validated_at="2026-09-01T00:00:00Z")
    data["revisions"].append(historical)
    assert bundle(data)


def test_success_requires_all_modules_ready_for_the_same_revision():
    data = execution_data()
    second = deepcopy(data["revisions"][0]["draft"]["modules"][0])
    second["module_id"] = uid()
    data["revisions"][0]["draft"]["modules"].append(second)
    with pytest.raises(ValidationError):
        bundle(data)
    run = data["history"]["run"]
    data["history"]["events"][3] = event(
        run, 4, "module.ready", revision_id=data["revisions"][0]["revision_id"], module=second
    )
    data["history"]["events"].append(
        event(run, 5, "run.succeeded", revision_id=data["revisions"][0]["revision_id"])
    )
    assert bundle(data)


def test_authorization_while_unresolved_is_rejected_even_if_attempt_created_after_cursor():
    data = execution_data(paid=True, unknown=True)
    retry = deepcopy(data["attempts"][0])
    retry.update(
        attempt_id=uid(), step_id=uid(), authorized_after_seq=3, status="failed", result_id=None
    )
    data["attempts"].append(retry)
    data["usage"]["entries"].append(
        {
            **data["usage"]["entries"][0],
            "entry_id": uid(),
            "attempt_id": retry["attempt_id"],
            "charge_status": "confirmed",
            "cost_microwon": "1",
        }
    )
    with pytest.raises(ValidationError):
        bundle(data)


def test_dispatched_requires_held_even_when_charge_is_known():
    data = execution_data(paid=True, cancelled=True)
    data["attempts"][0].update(status="dispatched", result_id=None, finished_at=None)
    data["usage"]["reservations"][0].update(
        status="settled", settled_at="2026-10-01T00:00:04Z", settled_microwon="6000000000"
    )
    with pytest.raises(ValidationError):
        bundle(data)


def test_free_attempt_optional_usage_still_requires_matching_provider():
    data = execution_data(paid=True)
    data["attempts"][0].update(paid=False, provider="different")
    with pytest.raises(ValidationError):
        bundle(data)


@pytest.mark.parametrize("with_base", [False, True])
def test_current_run_cannot_have_two_first_revisions(with_base):
    data = execution_data()
    run, first = data["history"]["run"], data["revisions"][0]
    if with_base:
        base = deepcopy(first)
        base.update(revision_id=uid(), run_id=uid(), validated_at="2026-09-01T00:00:00Z")
        data["revisions"].append(base)
        first.update(parent_revision_id=base["revision_id"], revision_number=2)
        run["submission"]["input"]["base_revision_id"] = base["revision_id"]
        from issuedigest_domain.execution import RunInput, hash_run_input

        run["input_sha256"] = hash_run_input(RunInput.model_validate(run["submission"]["input"]))
    sibling_root = deepcopy(first)
    sibling_root["revision_id"] = uid()
    data["revisions"].insert(0, sibling_root)
    with pytest.raises(ValidationError):
        bundle(data)


def test_later_sibling_candidate_revisions_are_allowed_without_claiming_storage_cas():
    data = execution_data()
    first = data["revisions"][0]
    for _ in range(2):
        later = deepcopy(first)
        later.update(revision_id=uid(), parent_revision_id=first["revision_id"], revision_number=2)
        data["revisions"].insert(0, later)
    assert bundle(data)


def test_known_reconciled_attempt_allows_explicit_retry_from_resolved_cursor():
    data = execution_data(paid=True, unknown=True)
    old = data["attempts"][0]
    old.update(status="failed")
    data["usage"]["entries"][0].update(charge_status="confirmed", cost_microwon="1")
    run, revision = data["history"]["run"], data["revisions"][0]
    data["history"]["events"].append(
        event(run, 4, "run.reconciliation_resolved", attempt_ids=[old["attempt_id"]])
    )
    retry = {
        **old,
        "attempt_id": uid(),
        "attempt_number": 2,
        "authorized_after_seq": 4,
        "status": "succeeded",
        "result_id": uid(),
    }
    data["attempts"].append(retry)
    data["usage"]["entries"].append(
        {
            **data["usage"]["entries"][0],
            "entry_id": uid(),
            "attempt_id": retry["attempt_id"],
            "cost_microwon": "2",
        }
    )
    data["history"]["events"].append(
        event(
            run,
            5,
            "module.ready",
            revision_id=revision["revision_id"],
            module=revision["draft"]["modules"][0],
        )
    )
    data["history"]["events"].append(
        event(run, 6, "run.succeeded", revision_id=revision["revision_id"])
    )
    assert bundle(data)
