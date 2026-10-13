"""Opt-in Uvicorn factory; explicit configuration, owned engine, no migrations."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from issuedigest_storage import (
    EvidenceAccessRepository,
    OAuthRepository,
    SessionRepository,
    WorkspaceAccessRepository,
    create_storage_engine,
)
from sqlalchemy import Engine
from starlette.concurrency import run_in_threadpool

from .auth import AuthService
from .auth_config import AuthConfig, RuntimeConfigurationError
from .google_oauth import GoogleOAuthProvider
from .main import IssueDigestAPI, create_app


def create_configured_app() -> IssueDigestAPI:
    config = AuthConfig.from_environment(os.environ)
    engine: Engine | None = None
    try:
        engine = create_storage_engine(config.database_url)
        oauth = OAuthRepository(engine)
        sessions = SessionRepository(engine)
        workspace = WorkspaceAccessRepository(engine)
        application = create_app(
            EvidenceAccessRepository(engine),
            auth_service=AuthService(config, oauth, sessions, GoogleOAuthProvider(config)),
            workspace_repository=workspace,
        )
    except Exception:
        if engine is not None:
            engine.dispose()
        raise RuntimeConfigurationError() from None

    @asynccontextmanager
    async def owned_lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            assert engine is not None
            await run_in_threadpool(engine.dispose)

    application.router.lifespan_context = owned_lifespan
    return application
