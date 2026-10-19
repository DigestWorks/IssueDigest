"""Public DBOS 3.2 APIs: replay only completed paid checkpoints under their recorded version."""

from collections import defaultdict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from threading import Lock
from uuid import UUID

from dbos import DBOSClient, WorkflowStatus
from issuedigest_storage.research import ResearchRepository
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
}
RECOVERABLE = {"PENDING", "ENQUEUED"}
ACTIVE = {"queued", "retrieving", "generating", "validating"}


def completed_model_checkpoint(client: DBOSClient, workflow_id: str, name: str) -> bool:
    """Metadata only: no checkpoint deserialization, new durable step or payload logging."""
    if name not in WORKFLOW_NAMES or name in {
        "issuedigest_research_run_v7",
        "issuedigest_research_run_v8",
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


def recoverable_checkpoint(client: DBOSClient, workflow_id: str, name: str, stage: str) -> bool:
    if name in {"issuedigest_research_run_v7", "issuedigest_research_run_v8"}:
        return _completed_planned_checkpoint(client, workflow_id, stage, profile=name[-2:])
    return stage not in {"generating", "validating"} or completed_model_checkpoint(
        client, workflow_id, name
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
                repository.worker_transition(run_id, "failed", error_code="generation_failed")
                if workflow is not None and workflow.status in RECOVERABLE:
                    client.cancel_workflow(workflow_id)
                continue
            assert workflow is not None and workflow.app_version is not None
            cohorts[workflow.app_version].append(workflow)
        for version, items in cohorts.items():
            yield version, tuple(items)
