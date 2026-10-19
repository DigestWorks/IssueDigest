"""Public DBOS 3.2 APIs: replay only completed paid checkpoints under their recorded version."""

import re
from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Lock
from typing import Literal
from uuid import UUID

from dbos import DBOSClient, WorkflowStatus
from issuedigest_storage.research import ResearchRepository
from pydantic_ai.messages import ModelResponse
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

# Two int32 keys form a fixed IssueDigest research-worker namespace, with no table/schema changes.
WORKER_LOCK_KEYS = {"namespace": 1230193735, "worker": 1381193523}


@contextmanager
def research_worker_lock(engine: Engine) -> Iterator[Callable[[], None]]:
    try:
        connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    except SQLAlchemyError:
        raise ValueError("Research worker ownership unavailable") from None
    mutex = Lock()
    acquired = False
    try:
        acquired = bool(
            connection.scalar(
                text("SELECT pg_try_advisory_lock(:namespace, :worker)"),
                WORKER_LOCK_KEYS,
            )
        )
        if not acquired:
            raise ValueError("Research worker already running")

        def check() -> None:
            try:
                with mutex:
                    held = connection.scalar(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE locktype='advisory' "
                            "AND pid=pg_backend_pid() AND classid=:namespace AND objid=:worker "
                            "AND objsubid=2 AND granted)"
                        ),
                        WORKER_LOCK_KEYS,
                    )
                if not held:
                    raise ValueError("Research worker ownership lost")
            except SQLAlchemyError:
                raise ValueError("Research worker ownership lost") from None

        yield check
    except SQLAlchemyError:
        raise ValueError("Research worker ownership unavailable") from None
    finally:
        try:
            if acquired:
                connection.execute(
                    text("SELECT pg_advisory_unlock(:namespace, :worker)"), WORKER_LOCK_KEYS
                )
        except SQLAlchemyError:
            pass  # A lost session has already released its lock; never continue worker execution.
        finally:
            connection.close()


WORKFLOW_NAMES = {
    "issuedigest_research_run_v2",
    "issuedigest_research_run_v3",
    "issuedigest_research_run_v4",
    "issuedigest_research_run_v5",
    "issuedigest_research_run_v6",
    "issuedigest_research_run_v7",
    "issuedigest_research_run_v8",
    "issuedigest_research_run_v9",
    "issuedigest_research_run_v10",
}
RECOVERABLE = {"PENDING", "ENQUEUED"}
ACTIVE = {"queued", "retrieving", "generating", "validating"}


def completed_model_checkpoint(client: DBOSClient, workflow_id: str, name: str) -> bool:
    """Metadata only: no checkpoint deserialization, new durable step or payload logging."""
    if name not in WORKFLOW_NAMES or name in {
        "issuedigest_research_run_v7",
        "issuedigest_research_run_v8",
        "issuedigest_research_run_v9",
        "issuedigest_research_run_v10",
    }:
        return False
    steps = client.list_workflow_steps(workflow_id, load_output=False, limit=21)
    model_steps = [step for step in steps if "__model.request" in step["function_name"]]
    return (
        len(steps) <= 20
        and len(model_steps) == 1
        # DBOS replays by workflow ID and durable slot, then verifies the step name.
        and type(model_steps[0].get("function_id")) is int
        and model_steps[0]["function_id"] == 1
        and model_steps[0]["function_name"] == name.replace("_run_", "_") + "__model.request"
        and model_steps[0]["completed_at_epoch_ms"] is not None
    )


def completed_v7_checkpoint(client: DBOSClient, workflow_id: str, stage: str) -> bool:
    """Exact ordered v7 metadata; no deserialization or additional durable operations."""
    return _completed_planned_checkpoint(client, workflow_id, stage, profile="v7")


def completed_v8_checkpoint(client: DBOSClient, workflow_id: str, stage: str) -> bool:
    """Same planner7 paid slot1, distinct search8 slot2 and final8 paid slot3."""
    return _completed_planned_checkpoint(client, workflow_id, stage, profile="v8")


def _completed_planned_checkpoint(
    client: DBOSClient, workflow_id: str, stage: str, *, profile: str
) -> bool:
    steps = client.list_workflow_steps(workflow_id, load_output=False, limit=21)
    expected = [
        (1, "issuedigest_research_plan_v7__model.request"),
        (2, f"issuedigest_research_search_{profile}"),
        (3, f"issuedigest_research_{profile}__model.request"),
    ]
    if stage == "queued":
        return not steps
    if stage == "retrieving":
        if len(steps) not in {1, 2}:
            return False
        expected = expected[: len(steps)]
    elif stage not in {"generating", "validating"}:
        return False
    return len(steps) == len(expected) and all(
        type(step.get("function_id")) is int
        and (step["function_id"], step.get("function_name")) == required
        and step.get("completed_at_epoch_ms") is not None
        for step, required in zip(steps, expected, strict=True)
    )


RelevanceProfile = Literal["v9", "v10"]


def _relevance_names(profile: RelevanceProfile) -> tuple[str, str]:
    if profile == "v9":
        return "issuedigest_research_run_v9", "issuedigest_research_v9__model.request"
    if profile == "v10":
        return "issuedigest_research_run_v10", "issuedigest_research_v10__model.request"
    raise ValueError("Invalid relevance profile")


def completed_v9_checkpoint(client: DBOSClient, workflow_id: str, stage: str) -> bool:
    return _completed_relevance_checkpoint(client, workflow_id, stage, profile="v9")


def _completed_relevance_checkpoint(
    client: DBOSClient, workflow_id: str, stage: str, *, profile: RelevanceProfile
) -> bool:
    """Inspect exact completed prefixes before any raw response is deserialized."""
    _, final_name = _relevance_names(profile)
    steps = client.list_workflow_steps(workflow_id, load_output=False, limit=21)
    expected = [
        (1, "issuedigest_research_plan_v7__model.request"),
        (2, "issuedigest_research_search_v9"),
        (3, "issuedigest_research_select_v9__model.request"),
        (4, "issuedigest_research_apply_v9"),
        (5, final_name),
    ]
    if stage == "queued":
        return not steps
    if stage == "retrieving":
        if not 1 <= len(steps) <= 4:
            return False
        expected = expected[: len(steps)]
    elif stage not in {"generating", "validating"}:
        return False
    return len(steps) == len(expected) and all(
        type(step.get("function_id")) is int
        and (step["function_id"], step.get("function_name")) == required
        and step.get("completed_at_epoch_ms") is not None
        for step, required in zip(steps, expected, strict=True)
    )


SELECTOR_V9_STARTED: dict[str, object] = {"issuedigest_select_v9_started": True}


def v9_attributes(client: DBOSClient, workflow_id: str) -> dict[str, object] | None:
    return _relevance_attributes(client, workflow_id, profile="v9")


def _relevance_attributes(
    client: DBOSClient, workflow_id: str, *, profile: RelevanceProfile
) -> dict[str, object] | None:
    workflow_name, _ = _relevance_names(profile)
    workflows = client.list_workflows(
        workflow_ids=[workflow_id],
        application_name="issuedigest-research",
        load_input=False,
        load_output=False,
    )
    if (
        len(workflows) != 1
        or workflows[0].workflow_id != workflow_id
        or workflows[0].name != workflow_name
    ):
        raise ValueError("Invalid relevance workflow identity")
    attributes = workflows[0].attributes
    if attributes is None or attributes == {}:
        return None
    if (
        type(attributes) is not dict
        or set(attributes)
        != {"issuedigest_select_v9_started", "issuedigest_select_v9_prompt_sha256"}
        or attributes["issuedigest_select_v9_started"] is not True
        or type(attributes["issuedigest_select_v9_prompt_sha256"]) is not str
        or re.fullmatch(r"[0-9a-f]{64}", attributes["issuedigest_select_v9_prompt_sha256"]) is None
    ):
        raise ValueError("Invalid relevance workflow attributes")
    return dict(attributes)


def recoverable_v9_checkpoint(client: DBOSClient, workflow_id: str, stage: str) -> bool:
    return _recoverable_relevance_checkpoint(client, workflow_id, stage, profile="v9")


def _recoverable_relevance_checkpoint(
    client: DBOSClient, workflow_id: str, stage: str, *, profile: RelevanceProfile
) -> bool:
    if not _completed_relevance_checkpoint(client, workflow_id, stage, profile=profile):
        return False
    try:
        attributes = _relevance_attributes(client, workflow_id, profile=profile)
    except ValueError:
        return False
    steps = client.list_workflow_steps(workflow_id, load_output=False, limit=21)
    # DBOSModel records the raw result only upon completion. The public client's
    # unjournaled attribute claim distinguishes never-started from ambiguous paid3.
    if len(steps) < 3:
        return attributes is None
    return attributes is not None


def known_v9_usage(client: DBOSClient, workflow_id: str) -> tuple[int, int]:
    return _known_relevance_usage(client, workflow_id, profile="v9")


def _known_relevance_usage(
    client: DBOSClient, workflow_id: str, *, profile: RelevanceProfile
) -> tuple[int, int]:
    """Only exact completed journal prefixes permit raw-response accounting reads."""
    _relevance_names(profile)
    metadata = client.list_workflow_steps(workflow_id, load_output=False, limit=21)
    count = len(metadata)
    if not count:
        return 0, 0
    stage = "generating" if count == 5 else "retrieving"
    if not _completed_relevance_checkpoint(client, workflow_id, stage, profile=profile):
        return 0, 0
    try:
        attributes = _relevance_attributes(client, workflow_id, profile=profile)
    except ValueError:
        return 0, 0
    # Prefix2 with the exact started marker is not replayable, but its completed
    # planner response is still valid known-cost evidence for terminal repair.
    if (count < 2 and attributes is not None) or (count >= 3 and attributes is None):
        return 0, 0
    steps = client.list_workflow_steps(workflow_id, load_output=True, limit=21)
    if [
        (s.get("function_id"), s.get("function_name"), s.get("completed_at_epoch_ms"))
        for s in steps
    ] != [
        (s.get("function_id"), s.get("function_name"), s.get("completed_at_epoch_ms"))
        for s in metadata
    ]:
        return 0, 0
    inputs, outputs = 0, 0
    bounds = {1: (8_000, 500), 3: (12_000, 500), 5: (24_000, 2_000)}
    for step in steps:
        slot = step["function_id"]
        response = step.get("output")
        if slot not in bounds or not isinstance(response, ModelResponse):
            continue
        usage = response.usage
        incoming, outgoing = usage.input_tokens, usage.output_tokens
        total, cap = bounds[slot]
        if slot == 5:
            total, cap = 24_000 - inputs - outputs, min(2_000, 2_500 - outputs)
        if (
            type(incoming) is int
            and type(outgoing) is int
            and incoming >= 0
            and outgoing >= 0
            and outgoing <= cap
            and incoming + outgoing <= total
        ):
            inputs += incoming
            outputs += outgoing
    return inputs, outputs


def recoverable_checkpoint(client: DBOSClient, workflow_id: str, name: str, stage: str) -> bool:
    if name == "issuedigest_research_run_v9":
        return recoverable_v9_checkpoint(client, workflow_id, stage)
    if name == "issuedigest_research_run_v10":
        return _recoverable_relevance_checkpoint(client, workflow_id, stage, profile="v10")
    if name == "issuedigest_research_run_v7":
        return completed_v7_checkpoint(client, workflow_id, stage)
    if name == "issuedigest_research_run_v8":
        return completed_v8_checkpoint(client, workflow_id, stage)
    return stage not in {"generating", "validating"} or completed_model_checkpoint(
        client, workflow_id, name
    )


def reconcile_v9_accounting(client: DBOSClient, repository: ResearchRepository) -> None:
    _reconcile_relevance_accounting(client, repository, profile="v9")


def _reconcile_relevance_accounting(
    client: DBOSClient, repository: ResearchRepository, *, profile: RelevanceProfile
) -> None:
    """Bounded terminal-only repair; no status, result, reservation or provider action."""
    workflow_name, _ = _relevance_names(profile)
    offset = 0
    while workflows := client.list_workflows(
        name=workflow_name,
        application_name="issuedigest-research",
        load_input=False,
        load_output=False,
        limit=20,
        offset=offset,
    ):
        offset += len(workflows)
        owned = {}
        for workflow in workflows:
            try:
                run_id = UUID(workflow.workflow_id.removeprefix("research-"))
            except ValueError:
                continue
            if (
                run_id.version == 4
                and workflow.workflow_id == f"research-{run_id}"
                and workflow.name == workflow_name
                and workflow.application_name == "issuedigest-research"
            ):
                owned[run_id] = workflow
        states = repository.worker_states(tuple(owned))
        for run_id, stage in states.items():
            if stage in {"completed", "failed", "cancelled"}:
                inputs, outputs = _known_relevance_usage(
                    client, owned[run_id].workflow_id, profile=profile
                )
                if inputs or outputs:
                    repository.worker_record_relevance_usage(
                        run_id, input_tokens=inputs, output_tokens=outputs
                    )


def cancel_owned_orphans(client: DBOSClient, repository: ResearchRepository) -> None:
    """Only exact IDs tied to this application's terminal rows; never arbitrary DBOS IDs."""
    workflows = client.list_workflows(
        status=["PENDING", "ENQUEUED"],
        workflow_id_prefix="research-",
        application_name="issuedigest-research",
        load_input=False,
        load_output=False,
        limit=100,
    )
    owned = {}
    for workflow in workflows:
        try:
            run_id = UUID(workflow.workflow_id.removeprefix("research-"))
        except ValueError:
            continue
        if workflow.workflow_id == f"research-{run_id}":
            owned[run_id] = workflow
    states = repository.worker_states(tuple(owned))
    for run_id, state in states.items():
        if state not in ACTIVE:
            client.cancel_workflow(owned[run_id].workflow_id)


def recovery_cohorts(
    client: DBOSClient,
    repository: ResearchRepository,
) -> Iterator[tuple[str, tuple[WorkflowStatus, ...]]]:
    """Read active application rows in pages of20; do not infer new IDs or rewrite DBOS history."""
    after = None
    while rows := repository.worker_active_runs(after):
        after = rows[-1][0]
        workflows = {
            w.workflow_id: w
            for w in client.list_workflows(
                workflow_ids=[f"research-{run_id}" for run_id, _ in rows],
                application_name="issuedigest-research",
                load_input=False,
                load_output=False,
            )
        }
        cohorts: dict[str, list[WorkflowStatus]] = defaultdict(list)
        for run_id, state in rows:
            workflow_id = f"research-{run_id}"
            workflow = workflows.get(workflow_id)
            if workflow is None and state == "queued":
                continue
            safe = workflow is not None and (
                workflow.name in WORKFLOW_NAMES
                and workflow.status in RECOVERABLE
                and bool(workflow.app_version)
                and recoverable_checkpoint(client, workflow_id, workflow.name, state)
            )
            if not safe:
                if workflow is not None and workflow.name in {
                    "issuedigest_research_run_v9",
                    "issuedigest_research_run_v10",
                }:
                    inputs, outputs = repository.worker_record_relevance_usage(
                        run_id, input_tokens=0, output_tokens=0
                    )
                    repository.worker_transition(
                        run_id,
                        "failed",
                        error_code="generation_failed",
                        input_tokens=inputs,
                        output_tokens=outputs,
                    )
                else:
                    repository.worker_transition(run_id, "failed", error_code="generation_failed")
                if workflow is not None and workflow.status in RECOVERABLE:
                    client.cancel_workflow(workflow_id)
                continue
            assert workflow is not None and workflow.app_version is not None
            cohorts[workflow.app_version].append(workflow)
        for version, items in cohorts.items():
            yield version, tuple(items)
