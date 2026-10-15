"""Explicit DBOS research worker: poll queued rows and dispatch stable workflows."""

import os
import time
from uuid import UUID

from dbos import DBOS, SetWorkflowID
from issuedigest_agents.research import (
    AIOutput,
    build_canvas,
    create_agent,
    model_prompt,
    run_agent,
)
from issuedigest_domain.research_journey import ResearchResult
from issuedigest_storage import create_storage_engine
from issuedigest_storage.research import ResearchRepository
from sqlalchemy import Engine


def run_worker(
    database_url: str, *, model: object | None = None, poll_seconds: float = 1.0, once: bool = False
) -> None:
    """No migration or provider call at import/startup; operator explicitly runs DBOS.migrate."""
    if not database_url.startswith("postgresql+psycopg://"):
        raise ValueError("PostgreSQL URL required")
    if model is None and not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("OPENAI_API_KEY required")
    engine: Engine = create_storage_engine(database_url)
    repository = ResearchRepository(engine)
    agent = create_agent(model)  # type: ignore[arg-type]
    DBOS(
        config={
            "name": "issuedigest-research",
            "system_database_url": database_url,
            "run_migrations": False,
            "sys_db_pool_size": 3,
            "enable_otlp": False,
            "log_level": "ERROR",
            "console_log_level": "ERROR",
            "dbos_system_schema": "dbos",
        }
    )

    @DBOS.workflow(name="issuedigest_research_run_v1", max_recovery_attempts=3)
    def execute(run_id_text: str) -> None:
        run_id = UUID(run_id_text)
        try:
            loaded = repository.worker_load(run_id)
        except Exception:
            # Canonical evidence or storage errors cannot leak through DBOS exception logs.
            try:
                repository.worker_transition(run_id, "failed", error_code="generation_failed")
            except Exception:
                pass  # A later operator repair can reconcile a temporarily unavailable DB.
            return
        if loaded is None:
            return
        run, sources = loaded
        try:
            if not repository.worker_transition(run_id, "retrieving"):
                return
            try:
                prompt = model_prompt(
                    run.question, sources, repository.worker_parent_context(run_id)
                )
            except ValueError:
                output = AIOutput(
                    outcome="insufficient_evidence",
                    message="선택한 자료에 인용 가능한 내용이 부족합니다.",
                    modules=(),
                )
                input_tokens, output_tokens = 0, 0
            else:
                if not repository.worker_transition(run_id, "generating"):
                    return
                output, input_tokens, output_tokens = run_agent(agent, prompt)
            if not repository.worker_transition(run_id, "validating"):
                return
            canvas = build_canvas(run_id, run.workspace_id, sources, output)
            titles = {
                bundle.document.document_id: title.title for _snapshot, bundle, title in sources
            }
            repository.worker_transition(
                run_id,
                "completed",
                result=ResearchResult(canvas=canvas, source_titles=titles),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        except Exception:
            # Ambiguous provider outcomes remain reserved; no retries or raw error logging.
            try:
                repository.worker_transition(run_id, "failed", error_code="generation_failed")
            except Exception:
                pass

    try:
        DBOS.launch()
        while True:
            handles = []
            for run_id in repository.queued_ids():
                with SetWorkflowID(f"research-{run_id}"):
                    handles.append(DBOS.start_workflow(execute, str(run_id)))
            if once:
                for handle in handles:
                    handle.get_result()
                return
            time.sleep(poll_seconds)
    finally:
        DBOS.destroy(destroy_registry=True)
        engine.dispose()


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
