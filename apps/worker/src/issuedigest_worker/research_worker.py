"""Explicit DBOS research worker: poll queued rows and dispatch stable workflows."""

import os
import time
from collections.abc import Callable
from typing import Literal
from uuid import UUID

from dbos import DBOS, DBOSClient, SetWorkflowID, WorkflowHandle, WorkflowStatus
from issuedigest_agents.research import (
    AIOutput,
    build_canvas,
    create_agent,
    model_prompt,
    run_agent,
)
from issuedigest_agents.research_v3 import (
    AIOutputV3,
    build_canvas_v3,
    create_agent_v3,
    model_prompt_v3,
    run_agent_v3,
)
from issuedigest_agents.research_v4 import (
    build_canvas_v4,
    create_agent_v4,
    model_prompt_v4,
    run_agent_v4,
)
from issuedigest_agents.research_v5 import (
    build_canvas_v5,
    create_agent_v5,
    model_prompt_v5,
    run_agent_v5,
)
from issuedigest_agents.research_v6 import (
    build_canvas_v6,
    create_agent_v6,
    model_prompt_v6,
    run_agent_v6,
)
from issuedigest_agents.research_v7 import (
    build_canvas_v7,
    create_agent_v7,
    create_planner_v7,
    model_prompt_v7,
    planning_prompt_v7,
    run_agent_v7,
    run_planner_v7,
)
from issuedigest_domain.research_journey import ResearchResult, RunStatus
from issuedigest_storage import StorageCorruption, StorageError, create_storage_engine
from issuedigest_storage.research import ResearchRepository
from pydantic_ai import Agent
from sqlalchemy import Engine

from .research_recovery import (
    cancel_owned_orphans,
    completed_model_checkpoint,
    completed_v7_checkpoint,
    recovery_cohorts,
    research_worker_lock,
)


def run_worker(
    database_url: str, *, model: object | None = None, poll_seconds: float = 1.0, once: bool = False
) -> None:
    """No migration or provider call at import/startup; operator explicitly runs DBOS.migrate."""
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("PostgreSQL URL required")
    if model is None and not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY required")
    engine: Engine = create_storage_engine(database_url)
    try:
        with research_worker_lock(engine) as check_ownership:
            _run_worker(database_url, engine, check_ownership, model, poll_seconds, once)
    finally:
        engine.dispose()


def _run_worker(
    database_url: str,
    engine: Engine,
    check_ownership: Callable[[], None],
    model: object | None,
    poll_seconds: float,
    once: bool,
) -> None:
    repository = ResearchRepository(engine)
    agent_v2: Agent[None, AIOutput]
    agent_v3: Agent[None, AIOutputV3]
    agent_v4: Agent[None, AIOutputV3]
    agent_v5: Agent[None, AIOutputV3]
    agent_v6: Agent[None, AIOutputV3]
    agent_v7: Agent[None, AIOutputV3]
    planner_v7: Agent[None, AIOutputV3]
    client = DBOSClient(
        system_database_url=database_url,
        application_name="issuedigest-research",
        system_database_pool_size=3,
    )

    def persist(
        run_id: UUID,
        status: RunStatus,
        *,
        error_code: str | None = None,
        result: ResearchResult | None = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> bool:
        """Retry only application writes; never repeat a paid model request here."""
        while True:
            check_ownership()
            try:
                return repository.worker_transition(
                    run_id,
                    status,
                    error_code=error_code,
                    result=result,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            except StorageCorruption:
                raise
            except StorageError:
                time.sleep(poll_seconds)

    def execute(run_id_text: str, *, profile: Literal["v2", "v3", "v4", "v5", "v6"]) -> None:
        check_ownership()
        run_id = UUID(run_id_text)
        while True:
            try:
                loaded = repository.worker_load(run_id)
                break
            except StorageCorruption:
                persist(run_id, "failed", error_code="generation_failed")
                return
            except StorageError:
                time.sleep(poll_seconds)
            except Exception:
                # Canonical evidence errors are fixed-code failures, not DBOS log payloads.
                persist(run_id, "failed", error_code="generation_failed")
                return
        if loaded is None:
            return
        run, sources = loaded
        if run.status in {"generating", "validating"} and not completed_model_checkpoint(
            client,
            f"research-{run_id}",
            f"issuedigest_research_run_{profile}",
        ):
            persist(run_id, "failed", error_code="generation_failed")
            return
        input_tokens, output_tokens = 0, 0
        try:
            try:
                prompt = {
                    "v2": model_prompt,
                    "v3": model_prompt_v3,
                    "v4": model_prompt_v4,
                    "v5": model_prompt_v5,
                    "v6": model_prompt_v6,
                }[profile](
                    run.question,
                    sources,
                    repository.worker_parent_context(run_id),
                )
            except ValueError:
                persist(run_id, "failed", error_code="insufficient_evidence")
                return
            else:
                if not persist(run_id, "generating"):
                    return
                # No new durable step may precede the model request: slot 1 is historical.
                if profile == "v2":
                    output_v2, input_tokens, output_tokens = run_agent(agent_v2, prompt)
                else:
                    agent = {"v3": agent_v3, "v4": agent_v4, "v5": agent_v5, "v6": agent_v6}[
                        profile
                    ]
                    runner = {
                        "v3": run_agent_v3,
                        "v4": run_agent_v4,
                        "v5": run_agent_v5,
                        "v6": run_agent_v6,
                    }[profile]
                    output_classified, input_tokens, output_tokens = runner(agent, prompt)
            if not persist(run_id, "validating"):
                return
            canvas = (
                build_canvas(run_id, run.workspace_id, sources, output_v2)
                if profile == "v2"
                else {
                    "v3": build_canvas_v3,
                    "v4": build_canvas_v4,
                    "v5": build_canvas_v5,
                    "v6": build_canvas_v6,
                }[profile](run_id, run.workspace_id, sources, output_classified)
            )
            titles = {
                bundle.document.document_id: title.title for _snapshot, bundle, title in sources
            }
            persist(
                run_id,
                "completed",
                result=ResearchResult(canvas=canvas, source_titles=titles),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            # Provider/validation failures are final; ambiguous outcomes stay reserved.
            persist(
                run_id,
                "failed",
                error_code="generation_failed",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

    search_v7: Callable[[str, tuple[str, ...], int, int], tuple[UUID, ...] | None]

    def execute_v7_body(run_id_text: str) -> None:
        check_ownership()
        run_id = UUID(run_id_text)
        input_tokens, output_tokens = 0, 0
        try:
            while True:
                try:
                    run = repository.worker_prepare_search(run_id)
                    break
                except StorageCorruption:
                    raise
                except StorageError:
                    check_ownership()
                    time.sleep(poll_seconds)
            if run is None:
                return
            if not completed_v7_checkpoint(client, f"research-{run_id}", run.status):
                persist(run_id, "failed", error_code="generation_failed")
                return
            parent = repository.worker_parent_context(run_id)
            prompt = planning_prompt_v7(run.question, parent)
            if not persist(run_id, "retrieving"):
                return
            plan, input_tokens, output_tokens = run_planner_v7(planner_v7, prompt)
            fixed = search_v7(run_id_text, plan.queries, input_tokens, output_tokens)
            if fixed is None:
                return
            # Cached search results never bypass current authority, parent, or exact originals.
            rechecked = repository.worker_search_and_fix(
                run_id, plan.queries, input_tokens=input_tokens, output_tokens=output_tokens
            )
            if rechecked is None:
                return
            if rechecked != fixed:
                raise ValueError("Fixed search provenance changed")
            loaded = repository.worker_load(run_id)
            if loaded is None:
                return
            current, sources = loaded
            if current.snapshot_ids != fixed:
                raise ValueError("Fixed search provenance changed")
            try:
                prompt = model_prompt_v7(
                    run.question,
                    sources,
                    parent,
                    prior_input_tokens=input_tokens,
                    prior_output_tokens=output_tokens,
                )
            except ValueError:
                persist(
                    run_id,
                    "failed",
                    error_code="insufficient_evidence",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                return
            if not persist(run_id, "generating"):
                return
            output, final_input, final_output = run_agent_v7(
                agent_v7, prompt, prior_input_tokens=input_tokens, prior_output_tokens=output_tokens
            )
            input_tokens += final_input
            output_tokens += final_output
            if not persist(run_id, "validating"):
                return
            canvas = build_canvas_v7(run_id, run.workspace_id, sources, output)
            titles = {bundle.document.document_id: title.title for _, bundle, title in sources}
            persist(
                run_id,
                "completed",
                result=ResearchResult(canvas=canvas, source_titles=titles),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            persist(
                run_id,
                "failed",
                error_code="generation_failed",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

    def cycle(
        version: str | None = None,
        recoveries: tuple[WorkflowStatus, ...] = (),
        *,
        dispatch_new: bool = False,
    ) -> None:
        nonlocal agent_v2, agent_v3, agent_v4, agent_v5, agent_v6, agent_v7, planner_v7, search_v7
        agent_v2 = create_agent(model)  # type: ignore[arg-type]
        agent_v3 = create_agent_v3(model)  # type: ignore[arg-type]
        agent_v4 = create_agent_v4(model)  # type: ignore[arg-type]
        agent_v5 = create_agent_v5(model)  # type: ignore[arg-type]
        agent_v6 = create_agent_v6(model)  # type: ignore[arg-type]
        agent_v7 = create_agent_v7(model)  # type: ignore[arg-type]
        planner_v7 = create_planner_v7(model)  # type: ignore[arg-type]
        config = {
            "name": "issuedigest-research",
            "system_database_url": database_url,
            "run_migrations": False,
            "sys_db_pool_size": 3,
            "enable_otlp": False,
            "log_level": "ERROR",
            "console_log_level": "ERROR",
            "dbos_system_schema": "dbos",
        }
        if version is not None:
            config["application_version"] = version
        DBOS(config=config)  # type: ignore[arg-type]

        @DBOS.workflow(name="issuedigest_research_run_v2", max_recovery_attempts=3)
        def execute_v2(run_id_text: str) -> None:
            execute(run_id_text, profile="v2")

        @DBOS.workflow(name="issuedigest_research_run_v3", max_recovery_attempts=3)
        def execute_v3(run_id_text: str) -> None:
            execute(run_id_text, profile="v3")

        @DBOS.workflow(name="issuedigest_research_run_v4", max_recovery_attempts=3)
        def execute_v4(run_id_text: str) -> None:
            execute(run_id_text, profile="v4")

        @DBOS.workflow(name="issuedigest_research_run_v5", max_recovery_attempts=3)
        def execute_v5(run_id_text: str) -> None:
            execute(run_id_text, profile="v5")

        @DBOS.workflow(name="issuedigest_research_run_v6", max_recovery_attempts=3)
        def execute_v6(run_id_text: str) -> None:
            execute(run_id_text, profile="v6")

        @DBOS.step(name="issuedigest_research_search_v7", retries_allowed=False)
        def search_v7(
            run_id_text: str, queries: tuple[str, ...], input_tokens: int, output_tokens: int
        ) -> tuple[UUID, ...] | None:
            check_ownership()
            return repository.worker_search_and_fix(
                UUID(run_id_text), queries, input_tokens=input_tokens, output_tokens=output_tokens
            )

        @DBOS.workflow(name="issuedigest_research_run_v7", max_recovery_attempts=3)
        def execute_v7(run_id_text: str) -> None:
            execute_v7_body(run_id_text)

        functions = {
            "issuedigest_research_run_v2": execute_v2,
            "issuedigest_research_run_v3": execute_v3,
            "issuedigest_research_run_v4": execute_v4,
            "issuedigest_research_run_v5": execute_v5,
            "issuedigest_research_run_v6": execute_v6,
            "issuedigest_research_run_v7": execute_v7,
        }
        try:
            # Public resume retains original version and all steps; launch that version's registry.
            for workflow in recoveries:
                if workflow.status == "PENDING":
                    client.resume_workflow(workflow.workflow_id)
            DBOS.launch()
            handles: list[WorkflowHandle[None]] = [
                DBOS.retrieve_workflow(item.workflow_id) for item in recoveries
            ]
            if not dispatch_new:
                for handle in handles:
                    handle.get_result()
                return
            while True:
                check_ownership()
                handles = []
                for run_id in repository.queued_ids():
                    workflow_id = f"research-{run_id}"
                    status = DBOS.get_workflow_status(workflow_id)
                    if status is not None and status.name not in functions:
                        persist(run_id, "failed", error_code="generation_failed")
                        if status.status in {"PENDING", "ENQUEUED"}:
                            client.cancel_workflow(workflow_id)
                        continue
                    function = functions[status.name] if status is not None else execute_v7
                    with SetWorkflowID(workflow_id):
                        handles.append(DBOS.start_workflow(function, str(run_id)))
                if once:
                    for handle in handles:
                        handle.get_result()
                    return
                time.sleep(poll_seconds)
        finally:
            DBOS.destroy(destroy_registry=True)

    # Each cycle registers all profiles, then destroys the registry before the next version.
    try:
        check_ownership()
        cancel_owned_orphans(client, repository)
        for version, recoveries in recovery_cohorts(client, repository):
            check_ownership()
            cycle(version, recoveries)
        cycle(dispatch_new=True)
    finally:
        client.destroy()


def main() -> None:
    database_url = os.environ.get("ISSUEDIGEST_DATABASE_URL")
    if not database_url:
        raise SystemExit("ISSUEDIGEST_DATABASE_URL required")
    run_worker(database_url)


def migrate_dbos() -> None:
    database_url = os.environ.get("ISSUEDIGEST_DATABASE_URL")
    application_role = os.environ.get("ISSUEDIGEST_DBOS_APPLICATION_ROLE")
    if not database_url or not application_role:
        raise SystemExit("DB URL and existing application role required")
    DBOS.migrate(database_url, application_role=application_role)
