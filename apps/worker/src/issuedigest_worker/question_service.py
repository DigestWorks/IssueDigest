"""Explicit owned worker loop for private question execution; no migrations."""

import asyncio
import re
from collections.abc import Coroutine, Mapping
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from decimal import Decimal
from functools import partial
from threading import Event, Lock, Thread
from typing import Any
from uuid import UUID

import dbos._dbos as dbos_runtime
from dbos import DBOS, DBOSClient
from issuedigest_agents.question_submission import QuestionSubmissionError
from issuedigest_domain.question_submission import (
    QuestionSubmissionRequest,
    QuestionSubmissionResult,
)
from issuedigest_storage.briefing_jobs import BriefingJobRepository
from issuedigest_storage.evidence_jobs import EvidenceJobRepository
from issuedigest_storage.question_plans import QuestionPlanRepository
from issuedigest_storage.research import ResearchBudgetExceeded, ResearchConflict, ResearchForbidden
from issuedigest_storage.sessions import AuthenticationDenied
from openai import AsyncOpenAI
from sqlalchemy import Engine

from .briefing_queue import configure_briefing_queue, register_briefing_workflow
from .evidence_worker import (
    register_evidence_workflow,
    register_evidence_workflow_v3,
    register_evidence_workflow_v5,
)
from .question_briefing_runner import QuestionBriefingRun, run_question_briefing
from .research_recovery import research_worker_lock

_HOST_LOCK = Lock()


@dataclass(frozen=True)
class QuestionServiceConfig:
    api_key: str = field(repr=False)
    schema: str = "issuedigest_question_briefing"
    app_version: str = "question-briefing-http-v1"
    evidence_profile: str = "guarded-question-evidence-v2"

    def __post_init__(self) -> None:
        if (
            type(self.api_key) is not str
            or not self.api_key.strip()
            or self.api_key != self.api_key.strip()
            or len(self.api_key) > 4096
            or type(self.schema) is not str
            or re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.schema) is None
            or self.schema in {"dbos", "public"}
            or self.schema.startswith("pg_")
            or type(self.evidence_profile) is not str
            or self.evidence_profile
            not in (
                "guarded-question-evidence-v2",
                "guarded-question-evidence-v3",
                "guarded-question-evidence-v5",
            )
            or self.app_version != "question-briefing-http-v1"
        ):
            raise QuestionSubmissionError("unavailable")

    @classmethod
    def from_environment(cls, values: Mapping[str, str]) -> "QuestionServiceConfig":
        if values.get("ISSUEDIGEST_QUESTION_BRIEFING_ENABLED") != "1":
            raise QuestionSubmissionError("unavailable")
        return cls(
            api_key=values.get("OPENAI_API_KEY", ""),
            evidence_profile=values.get(
                "ISSUEDIGEST_QUESTION_EVIDENCE_PROFILE", "guarded-question-evidence-v2"
            ),
            schema=values.get(
                "ISSUEDIGEST_QUESTION_BRIEFING_SCHEMA", "issuedigest_question_briefing"
            ),
        )


class OwnedQuestionExecutionService:
    def __init__(self, engine: Engine, config: QuestionServiceConfig):
        self.engine, self.config = engine, config
        self._plans = QuestionPlanRepository(engine, evidence_profile=config.evidence_profile)
        self._evidence = EvidenceJobRepository(engine)
        self._briefings = BriefingJobRepository(engine)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: Thread | None = None
        self._ready = Event()
        self._started = False
        self._closed = False
        self._provider: AsyncOpenAI | None = None
        self._client: DBOSClient | None = None
        self._lease: AbstractContextManager[Any] | None = None
        self._owns_host = False
        self._owns_dbos = False
        self._callers: set[Future[Any]] = set()

    def _thread_main(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._ready.set()
        try:
            loop.run_forever()
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.run_until_complete(loop.shutdown_default_executor())
        finally:
            loop.close()

    async def _bridge[T](self, operation: Coroutine[Any, Any, T]) -> T:
        if self._loop is None:
            operation.close()
            raise QuestionSubmissionError("unavailable")
        loop = self._loop
        cancellation: Future[None] = Future()
        completed: Future[None] = Future()

        async def execute() -> T:
            task = asyncio.current_task()
            assert task is not None
            task.add_done_callback(lambda _: completed.set_result(None))
            # Never cancel this wrapper through its concurrent future: that
            # future can acknowledge cancellation before the Task terminates.
            if cancellation.cancelled():
                operation.close()
                raise asyncio.CancelledError

            def cancel_worker(request: Future[None]) -> None:
                if request.cancelled():
                    loop.call_soon_threadsafe(task.cancel)

            cancellation.add_done_callback(cancel_worker)
            return await operation

        future = asyncio.run_coroutine_threadsafe(execute(), loop)
        result = asyncio.wrap_future(future)
        # A cancelled API caller still owns the wrapper until its completion
        # acknowledgement. Retrieve any cleanup error without exposing its text.
        result.add_done_callback(lambda value: None if value.cancelled() else value.exception())
        self._callers.add(cancellation)
        try:
            return await asyncio.shield(result)
        except asyncio.CancelledError:
            cancellation.cancel()
            acknowledgement = asyncio.wrap_future(completed)
            while not acknowledgement.done():
                try:
                    await asyncio.shield(acknowledgement)
                except asyncio.CancelledError:
                    continue
            raise
        finally:
            self._callers.discard(cancellation)

    async def start(self) -> None:
        if self._started and not self._closed:
            return
        if self._closed or self._thread is not None:
            raise QuestionSubmissionError("unavailable")
        self._thread = Thread(
            target=self._thread_main, name="issuedigest-question-worker", daemon=True
        )
        self._thread.start()
        await asyncio.to_thread(self._ready.wait)
        failed = False
        try:
            await self._bridge(self._start_worker())
            self._started = True
        except Exception:
            failed = True
        if failed:
            await self.aclose()
            raise QuestionSubmissionError("unavailable")

    async def _start_worker(self) -> None:
        if not _HOST_LOCK.acquire(blocking=False):
            raise QuestionSubmissionError("unavailable")
        self._owns_host = True
        # Pinned DBOS 3.2 has no public non-creating singleton query. Read only;
        # reject foreign state before registering anything or claiming ownership.
        if dbos_runtime._dbos_global_instance is not None:
            raise QuestionSubmissionError("unavailable")
        self._lease = research_worker_lock(self.engine)
        check = await asyncio.to_thread(self._lease.__enter__)

        def owned(_: UUID) -> bool:
            check()
            return True

        self._provider = AsyncOpenAI(api_key=self.config.api_key, max_retries=0)
        self._owns_dbos = True  # Constructor may leave a partial owned singleton.
        url = self.engine.url.render_as_string(hide_password=False)
        runtime_config = dict(
            name="issuedigest-question-briefing",
            system_database_url=url,
            dbos_system_schema=self.config.schema,
            application_version=self.config.app_version,
            run_migrations=False,
            run_admin_server=False,
            enable_otlp=False,
            log_level="ERROR",
            console_log_level="ERROR",
            sys_db_pool_size=3,
        )
        DBOS(config=runtime_config)  # type: ignore[arg-type]
        register_evidence_workflow(self._evidence, client=self._provider, check_ownership=owned)
        register_evidence_workflow_v3(self._evidence, client=self._provider, check_ownership=owned)
        register_evidence_workflow_v5(self._evidence, client=self._provider, check_ownership=owned)
        register_briefing_workflow(self._briefings, client=self._provider, check_ownership=owned)
        DBOS.launch()
        await asyncio.to_thread(configure_briefing_queue)
        self._client = await asyncio.to_thread(
            DBOSClient,
            system_database_url=url,
            application_name="issuedigest-question-briefing",
            dbos_system_schema=self.config.schema,
            system_database_pool_size=3,
        )

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._started = False
        for caller in tuple(self._callers):
            caller.cancel()
        if self._loop is None:
            return
        failed = False
        try:
            await self._bridge(self._close_worker())
        except Exception:
            failed = True
        finally:
            self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                await asyncio.to_thread(self._thread.join)
        if failed:
            raise QuestionSubmissionError("unavailable")

    async def _close_worker(self) -> None:
        # DBOS adopts the loop's default executor and shuts it down in destroy.
        # Cleanup needs its own executor so client/lease cleanup remains possible.
        cleanup = ThreadPoolExecutor(max_workers=1, thread_name_prefix="question-cleanup")
        loop = asyncio.get_running_loop()
        try:
            if self._owns_dbos:
                await loop.run_in_executor(
                    cleanup,
                    partial(
                        DBOS.destroy, destroy_registry=True, workflow_completion_timeout_sec=70
                    ),
                )
        finally:
            try:
                current = asyncio.current_task()
                tasks = [t for t in asyncio.all_tasks() if t is not current]
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                if self._provider is not None:
                    await self._provider.close()
            finally:
                try:
                    if self._client is not None:
                        await loop.run_in_executor(cleanup, self._client.destroy)
                finally:
                    try:
                        if self._lease is not None:
                            await loop.run_in_executor(
                                cleanup, partial(self._lease.__exit__, None, None, None)
                            )
                    finally:
                        if self._owns_host:
                            _HOST_LOCK.release()
                            self._owns_host = False
                        cleanup.shutdown(wait=True)

    async def _safe[T](self, operation: Coroutine[Any, Any, T]) -> T:
        if not self._started or self._closed:
            operation.close()
            raise QuestionSubmissionError("unavailable")
        kind = "unavailable"
        try:
            return await self._bridge(operation)
        except AuthenticationDenied:
            kind = "unauthorized"
        except ResearchForbidden:
            kind = "forbidden"
        except ResearchBudgetExceeded:
            kind = "budget"
        except ResearchConflict:
            kind = "conflict"
        except Exception:
            pass
        raise QuestionSubmissionError(kind)  # type: ignore[arg-type]

    async def authorize(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> bool:
        return await self._safe(self._authorize_worker(token, workspace_id, request_id, question))

    async def _authorize_worker(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> bool:
        QuestionSubmissionRequest(request_id=request_id, question=question)
        return (
            await asyncio.to_thread(self._plans.submit, token, workspace_id, request_id, question)
            is not None
        )

    async def run(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> QuestionSubmissionResult:
        return await self._safe(self._run_worker(token, workspace_id, request_id, question))

    async def _run_worker(
        self, token: str, workspace_id: UUID, request_id: UUID, question: str
    ) -> QuestionSubmissionResult:
        if self._client is None:
            raise QuestionSubmissionError("unavailable")
        result = await run_question_briefing(
            self._plans,
            self._evidence,
            self._briefings,
            client=self._client,
            app_version=self.config.app_version,
            token=token,
            workspace_id=workspace_id,
            request_id=request_id,
            question=question,
            model="gpt-6.1-sol",
            evidence_reservation_usd=Decimal(".50"),
            briefing_reservation_usd=Decimal(".50"),
        )
        if type(result) is not QuestionBriefingRun:
            raise QuestionSubmissionError("unavailable")
        if result.briefing is not None:
            return QuestionSubmissionResult(
                request_id=request_id, kind="briefing", job_id=result.briefing.job_id
            )
        if result.evidence.status not in ("no_match", "blocked"):
            raise QuestionSubmissionError("unavailable")
        return QuestionSubmissionResult(
            request_id=request_id, kind=result.evidence.status, job_id=None
        )
