"""Explicit DBOS research worker: poll queued rows and dispatch stable workflows."""

import os
import time
from collections.abc import Callable
from hashlib import sha256
from typing import Literal
from uuid import UUID

from dbos import DBOS, DBOSClient, SetWorkflowID, WorkflowHandle, WorkflowStatus
from issuedigest_agents.relevance_selection import (
    RelevanceSelection,
    create_selector,
    run_selector,
    selection_prompt,
)
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
from issuedigest_agents.research_v8 import (
    build_canvas_v8,
    create_agent_v8,
    model_prompt_v8,
    run_agent_v8,
)
from issuedigest_agents.research_v9 import (
    build_canvas_v9,
    create_agent_v9,
    model_prompt_v9,
    run_agent_v9,
)
from issuedigest_agents.research_v10 import (
    build_canvas_v10,
    create_agent_v10,
    model_prompt_v10,
    run_agent_v10,
)
from issuedigest_domain.research_journey import ResearchResult, RunStatus
from issuedigest_storage import StorageCorruption, StorageError, create_storage_engine
from issuedigest_storage.research import ResearchRepository
from pydantic_ai import Agent
from pydantic_ai.durable_exec.dbos import DBOSModel
from sqlalchemy import Engine

from .research_recovery import (
    SELECTOR_V9_STARTED,
    _known_relevance_usage,
    _reconcile_relevance_accounting,
    _recoverable_relevance_checkpoint,
    _relevance_attributes,
    cancel_owned_orphans,
    completed_model_checkpoint,
    completed_v7_checkpoint,
    completed_v8_checkpoint,
    reconcile_v9_accounting,
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
    agent_v8: Agent[None, AIOutputV3]
    agent_v9: Agent[None, AIOutputV3]
    agent_v10: Agent[None, AIOutputV3]
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

    search_v8: Callable[[str, tuple[str, ...], int, int], tuple[UUID, ...] | None]

    def execute_planned_body(run_id_text: str, *, profile: Literal["v7", "v8"]) -> None:
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
            if not {"v7": completed_v7_checkpoint, "v8": completed_v8_checkpoint}[profile](
                client, f"research-{run_id}", run.status
            ):
                persist(run_id, "failed", error_code="generation_failed")
                return
            parent = repository.worker_parent_context(run_id)
            prompt = planning_prompt_v7(run.question, parent)
            if not persist(run_id, "retrieving"):
                return
            plan, input_tokens, output_tokens = run_planner_v7(planner_v7, prompt)
            fixed = {"v7": search_v7, "v8": search_v8}[profile](
                run_id_text, plan.queries, input_tokens, output_tokens
            )
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
                prompt = {"v7": model_prompt_v7, "v8": model_prompt_v8}[profile](
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
            output, final_input, final_output = {"v7": run_agent_v7, "v8": run_agent_v8}[profile](
                {"v7": agent_v7, "v8": agent_v8}[profile],
                prompt,
                prior_input_tokens=input_tokens,
                prior_output_tokens=output_tokens,
            )
            input_tokens += final_input
            output_tokens += final_output
            if not persist(run_id, "validating"):
                return
            canvas = {"v7": build_canvas_v7, "v8": build_canvas_v8}[profile](
                run_id, run.workspace_id, sources, output
            )
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

    search_v9: Callable[[str, tuple[str, ...], int, int], tuple[UUID, ...] | None]
    apply_v9: Callable[[str, tuple[UUID, ...], tuple[UUID, ...], int, int], tuple[UUID, ...] | None]
    selector_model: DBOSModel

    def storage_call[T](operation: Callable[[], T]) -> T:
        """v9 application operations only; model requests never enter this retry."""
        while True:
            check_ownership()
            try:
                return operation()
            except StorageCorruption:
                raise
            except StorageError:
                time.sleep(poll_seconds)

    def execute_relevant_body(run_id_text: str, *, profile: Literal["v9", "v10"]) -> None:
        if profile == "v9":
            final_agent, final_prompt_builder, final_runner, final_builder = (
                agent_v9,
                model_prompt_v9,
                run_agent_v9,
                build_canvas_v9,
            )
        elif profile == "v10":
            final_agent, final_prompt_builder, final_runner, final_builder = (
                agent_v10,
                model_prompt_v10,
                run_agent_v10,
                build_canvas_v10,
            )
        else:
            raise ValueError("Invalid relevance profile")
        check_ownership()
        run_id = UUID(run_id_text)
        known_input, known_output = storage_call(
            lambda: repository.worker_record_relevance_usage(
                run_id, input_tokens=0, output_tokens=0
            )
        )
        input_tokens, output_tokens = 0, 0

        def persist_relevant(
            status: RunStatus,
            *,
            error_code: str | None = None,
            result: ResearchResult | None = None,
            input_tokens: int = 0,
            output_tokens: int = 0,
        ) -> bool:
            nonlocal known_input, known_output
            stored_input, stored_output = storage_call(
                lambda: repository.worker_record_relevance_usage(
                    run_id, input_tokens=input_tokens, output_tokens=output_tokens
                )
            )
            known_input, known_output = (
                max(known_input, stored_input),
                max(known_output, stored_output),
            )
            return persist(
                run_id,
                status,
                error_code=error_code,
                result=result,
                input_tokens=known_input,
                output_tokens=known_output,
            )

        try:
            run = storage_call(lambda: repository.worker_prepare_search(run_id))
            if run is None:
                return
            if not _recoverable_relevance_checkpoint(
                client, f"research-{run_id}", run.status, profile=profile
            ):
                persist_relevant("failed", error_code="generation_failed")
                return
            parent = repository.worker_parent_context(run_id)
            if not persist_relevant("retrieving"):
                return
            plan, input_tokens, output_tokens = run_planner_v7(
                planner_v7, planning_prompt_v7(run.question, parent)
            )
            storage_call(
                lambda: repository.worker_record_relevance_usage(
                    run_id, input_tokens=input_tokens, output_tokens=output_tokens
                )
            )
            candidates = search_v9(run_id_text, plan.queries, input_tokens, output_tokens)
            if candidates is None:
                return
            # The search2 journal is the original candidate authority. Reopening it
            # remains possible after the application row has already been narrowed.
            loaded = storage_call(
                lambda: repository.worker_load_relevance_candidates(run_id, candidates)
            )
            if loaded is None:
                return
            current, sources = loaded
            if current.question != run.question:
                raise ValueError("Question changed")
            try:
                prompt = selection_prompt(run.question, sources)
            except ValueError:
                persist_relevant(
                    "failed",
                    error_code="insufficient_evidence",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                return
            attributes = _relevance_attributes(client, f"research-{run_id}", profile=profile)
            prompt_hash = sha256(prompt.encode()).hexdigest()
            if attributes is None:
                # Public CLIENT method does not allocate a durable operation slot.
                # Failure here must never proceed to the paid request.
                client.update_workflow_attributes(
                    f"research-{run_id}",
                    {**SELECTOR_V9_STARTED, "issuedigest_select_v9_prompt_sha256": prompt_hash},
                )
            elif attributes["issuedigest_select_v9_prompt_sha256"] != prompt_hash:
                raise ValueError("Original relevance prompt identity changed")
            report = run_selector(create_selector(selector_model), prompt)
            report = RelevanceSelection.model_validate(report.model_dump())
            if (
                report.candidate_snapshot_ids != candidates
                or report.prompt_sha256 != sha256(prompt.encode()).hexdigest()
                or report.question_sha256 != sha256(run.question.encode()).hexdigest()
            ):
                raise ValueError("Relevance request identity changed")
            input_tokens += report.input_tokens
            output_tokens += report.output_tokens
            storage_call(
                lambda: repository.worker_record_relevance_usage(
                    run_id, input_tokens=input_tokens, output_tokens=output_tokens
                )
            )
            selected = report.selected_snapshot_ids
            applied = apply_v9(run_id_text, candidates, selected, input_tokens, output_tokens)
            if applied is None:
                return
            # A cached apply4 result never substitutes for present authority or originals.
            rechecked = storage_call(
                lambda: repository.worker_apply_relevance_selection(
                    run_id,
                    candidates,
                    selected,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
            if rechecked is None:
                return
            if applied != selected or rechecked != selected:
                raise ValueError("Relevance application provenance changed")
            loaded = storage_call(
                lambda: repository.worker_load_relevance_candidates(run_id, candidates)
            )
            if loaded is None:
                return
            current, originals = loaded
            if (
                current.question != run.question
                or current.snapshot_ids != selected
                or selection_prompt(current.question, originals) != prompt
            ):
                raise ValueError("Relevance source identity changed")
            sources = tuple(source for source in originals if source[0] in selected)
            try:
                final_prompt = final_prompt_builder(
                    run.question,
                    sources,
                    parent,
                    prior_input_tokens=input_tokens,
                    prior_output_tokens=output_tokens,
                )
            except ValueError:
                persist_relevant(
                    "failed",
                    error_code="insufficient_evidence",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
                return
            if not persist_relevant(
                "generating", input_tokens=input_tokens, output_tokens=output_tokens
            ):
                return
            output, final_input, final_output = final_runner(
                final_agent,
                final_prompt,
                prior_input_tokens=input_tokens,
                prior_output_tokens=output_tokens,
            )
            input_tokens += final_input
            output_tokens += final_output
            if not persist_relevant(
                "validating", input_tokens=input_tokens, output_tokens=output_tokens
            ):
                return
            # Repeat all-candidate exact identity checks after the paid response too.
            loaded = storage_call(
                lambda: repository.worker_load_relevance_candidates(run_id, candidates)
            )
            if loaded is None:
                return
            current, originals = loaded
            if (
                current.question != run.question
                or current.snapshot_ids != selected
                or selection_prompt(current.question, originals) != prompt
            ):
                raise ValueError("Relevance source identity changed")
            canvas = final_builder(run_id, run.workspace_id, sources, output)
            titles = {bundle.document.document_id: title.title for _, bundle, title in sources}
            persist_relevant(
                "completed",
                result=ResearchResult(canvas=canvas, source_titles=titles),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            persist_relevant(
                "failed",
                error_code="generation_failed",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        finally:
            journal_input, journal_output = _known_relevance_usage(
                client, f"research-{run_id}", profile=profile
            )
            storage_call(
                lambda: repository.worker_record_relevance_usage(
                    run_id,
                    input_tokens=max(known_input, input_tokens, journal_input),
                    output_tokens=max(known_output, output_tokens, journal_output),
                )
            )

    def cycle(
        version: str | None = None,
        recoveries: tuple[WorkflowStatus, ...] = (),
        *,
        dispatch_new: bool = False,
    ) -> None:
        nonlocal agent_v2, agent_v3, agent_v4, agent_v5, agent_v6, agent_v7, agent_v8
        nonlocal planner_v7, search_v7, search_v8, agent_v9, agent_v10
        nonlocal selector_model, search_v9, apply_v9
        agent_v2 = create_agent(model)  # type: ignore[arg-type]
        agent_v3 = create_agent_v3(model)  # type: ignore[arg-type]
        agent_v4 = create_agent_v4(model)  # type: ignore[arg-type]
        agent_v5 = create_agent_v5(model)  # type: ignore[arg-type]
        agent_v6 = create_agent_v6(model)  # type: ignore[arg-type]
        agent_v7 = create_agent_v7(model)  # type: ignore[arg-type]
        agent_v8 = create_agent_v8(model)  # type: ignore[arg-type]
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
        # Register the SDK's public raw-response model wrapper after configuration,
        # before launch. Borrow the already-created v8 base model; no new client.
        assert agent_v8.model is not None and not isinstance(agent_v8.model, str)
        agent_v9 = create_agent_v9(agent_v8.model)
        agent_v10 = create_agent_v10(agent_v8.model)
        selector_model = DBOSModel(
            agent_v8.model,
            step_name_prefix="issuedigest_research_select_v9",
            step_config={"retries_allowed": False},
            get_event_stream_handler=lambda: None,
        )

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
            execute_planned_body(run_id_text, profile="v7")

        @DBOS.step(name="issuedigest_research_search_v8", retries_allowed=False)
        def search_v8(
            run_id_text: str, queries: tuple[str, ...], input_tokens: int, output_tokens: int
        ) -> tuple[UUID, ...] | None:
            check_ownership()
            return repository.worker_search_and_fix(
                UUID(run_id_text), queries, input_tokens=input_tokens, output_tokens=output_tokens
            )

        @DBOS.workflow(name="issuedigest_research_run_v8", max_recovery_attempts=3)
        def execute_v8(run_id_text: str) -> None:
            execute_planned_body(run_id_text, profile="v8")

        @DBOS.step(name="issuedigest_research_search_v9", retries_allowed=False)
        def search_v9(
            run_id_text: str, queries: tuple[str, ...], input_tokens: int, output_tokens: int
        ) -> tuple[UUID, ...] | None:
            return storage_call(
                lambda: repository.worker_search_and_fix(
                    UUID(run_id_text),
                    queries,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )

        @DBOS.step(name="issuedigest_research_apply_v9", retries_allowed=False)
        def apply_v9(
            run_id_text: str,
            candidates: tuple[UUID, ...],
            selected: tuple[UUID, ...],
            input_tokens: int,
            output_tokens: int,
        ) -> tuple[UUID, ...] | None:
            return storage_call(
                lambda: repository.worker_apply_relevance_selection(
                    UUID(run_id_text),
                    candidates,
                    selected,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )

        @DBOS.workflow(name="issuedigest_research_run_v9", max_recovery_attempts=3)
        def execute_v9(run_id_text: str) -> None:
            execute_relevant_body(run_id_text, profile="v9")

        @DBOS.workflow(name="issuedigest_research_run_v10", max_recovery_attempts=3)
        def execute_v10(run_id_text: str) -> None:
            execute_relevant_body(run_id_text, profile="v10")

        functions = {
            "issuedigest_research_run_v2": execute_v2,
            "issuedigest_research_run_v3": execute_v3,
            "issuedigest_research_run_v4": execute_v4,
            "issuedigest_research_run_v5": execute_v5,
            "issuedigest_research_run_v6": execute_v6,
            "issuedigest_research_run_v7": execute_v7,
            "issuedigest_research_run_v8": execute_v8,
            "issuedigest_research_run_v9": execute_v9,
            "issuedigest_research_run_v10": execute_v10,
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
                    function = functions[status.name] if status is not None else execute_v10
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
        reconcile_v9_accounting(client, repository)
        _reconcile_relevance_accounting(client, repository, profile="v10")
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
