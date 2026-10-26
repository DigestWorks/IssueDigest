"""Opt-in Uvicorn factory; explicit configuration, owned engine, no migrations."""

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from issuedigest_agents.question_submission import QuestionExecutionService
from issuedigest_storage import (
    EvidenceAccessRepository,
    OAuthRepository,
    SessionRepository,
    WorkspaceAccessRepository,
    create_storage_engine,
)
from issuedigest_storage.briefing_jobs import BriefingJobRepository
from issuedigest_storage.public_briefings import PublicBriefingRepository
from issuedigest_storage.research import ResearchRepository
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from .auth import AuthService
from .auth_config import AuthConfig, RuntimeConfigurationError
from .google_oauth import GoogleOAuthProvider
from .main import IssueDigestAPI, create_app


def create_configured_app(
    *, service_factory: Callable[[Engine], QuestionExecutionService] | None = None
) -> IssueDigestAPI:
    config = AuthConfig.from_environment(os.environ)
    engine: Engine | None = None
    try:
        engine = create_storage_engine(config.database_url)
        oauth = OAuthRepository(engine)
        sessions = SessionRepository(engine)
        workspace = WorkspaceAccessRepository(engine)
        service = service_factory(engine) if service_factory is not None else None
        application = create_app(
            EvidenceAccessRepository(engine),
            question_service=service,
            auth_service=AuthService(config, oauth, sessions, GoogleOAuthProvider(config)),
            workspace_repository=workspace,
            research_repository=ResearchRepository(engine),
            briefing_job_repository=BriefingJobRepository(engine),
            public_repository=PublicBriefingRepository(engine),
            research_model_available=os.environ.get("ISSUEDIGEST_RESEARCH_ENABLED") == "1",
        )
    except Exception:
        if engine is not None:
            engine.dispose()
        raise RuntimeConfigurationError() from None

    @asynccontextmanager
    async def owned_lifespan(app: FastAPI) -> AsyncIterator[None]:
        failed = False
        try:
            if service is not None:
                await service.start()
            yield
        except Exception:
            failed = True
        finally:
            try:
                if service is not None:
                    await service.aclose()
            except Exception:
                failed = True
            finally:
                assert engine is not None
                await run_in_threadpool(engine.dispose)
        if failed:
            raise RuntimeConfigurationError()

    application.router.lifespan_context = owned_lifespan
    return application
