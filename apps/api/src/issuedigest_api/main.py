"""Explicit server factory; the default app needs no external services."""

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from issuedigest_agents.question_submission import QuestionExecutionService
from issuedigest_domain.status import Liveness, ServiceStatus
from issuedigest_storage import EvidenceAccessRepository, WorkspaceAccessRepository
from issuedigest_storage.briefing_jobs import BriefingJobRepository
from issuedigest_storage.public_briefings import PublicBriefingRepository
from issuedigest_storage.research import ResearchRepository

from .auth import AuthService, auth_router
from .briefing_jobs import briefing_jobs_router
from .briefings import briefings_router
from .contracts import add_evidence_schemas
from .errors import EvidencePathValidationError
from .evidence import evidence_router
from .question_submissions import question_submissions_router
from .research import research_router
from .search import search_router
from .workspace_catalog import catalog_router


class IssueDigestAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        return add_evidence_schemas(super().openapi())


logger = logging.getLogger(__name__)
REQUEST_ID_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {
        "headers": {
            "X-Request-ID": {
                "description": "Server-generated request UUID (also present on error responses).",
                "schema": {"type": "string", "format": "uuid"},
            }
        }
    }
}


def _auth_path(path: str) -> bool:
    return path == "/api/v1/auth" or path.startswith("/api/v1/auth/")


def _public_path(path: str) -> bool:
    return path == "/api/v1/briefings" or path.startswith("/api/v1/briefings/")


def _protected_path(path: str) -> bool:
    return (
        _auth_path(path)
        or re.fullmatch(
            r"/api/v1/workspaces/[^/]+/(?:question-briefings|briefing-jobs(?:/[^/]+(?:/cancel)?)?)/?",
            path,
        )
        is not None
        or re.fullmatch(r"/api/v1/workspaces/[^/]+/evidence(?:/[^/]+)?/?", path) is not None
        or re.fullmatch(
            r"/api/v1/workspaces/[^/]+/research(?:/sources|/[^/]+(?:/cancel)?)?/?", path
        )
        is not None
    )


def create_app(
    access_repository: EvidenceAccessRepository | None = None,
    *,
    auth_service: AuthService | None = None,
    workspace_repository: WorkspaceAccessRepository | None = None,
    research_repository: ResearchRepository | None = None,
    research_model_available: bool = True,
    briefing_job_repository: BriefingJobRepository | None = None,
    public_repository: PublicBriefingRepository | None = None,
    question_service: QuestionExecutionService | None = None,
) -> IssueDigestAPI:
    """Configure only from trusted server code; the default protected route fails closed."""
    application = IssueDigestAPI(title="IssueDigest API", version="v1")

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exception: RequestValidationError) -> Response:
        if _public_path(request.url.path):
            return JSONResponse(
                status_code=422, content={"detail": "Invalid public briefing request"}
            )
        if not _protected_path(request.url.path):
            return await request_validation_exception_handler(request, exception)
        validated = EvidencePathValidationError.model_validate(
            {
                "detail": [
                    {
                        "type": error["type"],
                        "loc": error["loc"],
                        "msg": (
                            "Invalid UUID4 path parameter"
                            if error["loc"][0] == "path"
                            else "Invalid catalog limit"
                        ),
                    }
                    for error in exception.errors()
                ]
            }
        )
        return JSONResponse(status_code=422, content=validated.model_dump(mode="json"))

    @application.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        identifier = str(uuid4())
        protected = _protected_path(request.url.path)
        public = _public_path(request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            # Do not include exceptions, cookies, paths or source text in logs.
            logger.error("Unhandled request error request_id=%s", identifier)
            response = JSONResponse(
                status_code=503 if protected or public else 500,
                content={
                    "detail": (
                        "Authentication service unavailable"
                        if _auth_path(request.url.path)
                        else (
                            "Public briefing service unavailable"
                            if public
                            else (
                                "Evidence service unavailable"
                                if protected
                                else "Internal server error"
                            )
                        )
                    )
                },
            )
        if (
            ("/briefing-jobs" in request.url.path or "/question-briefings" in request.url.path)
            and protected
            and response.status_code in {307, 308}
        ):
            response = JSONResponse(status_code=422, content={"detail": "Invalid briefing request"})
        if _auth_path(request.url.path) and response.status_code in {307, 308}:
            # Automatic slash redirects otherwise copy sensitive callback queries to Location.
            response = JSONResponse(status_code=404, content={"detail": "Not Found"})
        if (
            request.method == "POST"
            and re.fullmatch(r"/api/v1/workspaces/[^/]+/evidence/search/?", request.url.path)
            and response.status_code in {307, 308}
        ):
            response = JSONResponse(
                status_code=422, content={"detail": "Invalid evidence search request"}
            )
        response.headers["X-Request-ID"] = identifier
        if public and response.status_code in {307, 308}:
            response = JSONResponse(
                status_code=422, content={"detail": "Invalid public briefing request"}
            )
            response.headers["X-Request-ID"] = identifier
        if protected or public:
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health/live", response_model=Liveness, responses=REQUEST_ID_RESPONSE)
    async def liveness() -> Liveness:
        """The process responds; database and execution-engine readiness are not checked."""
        return Liveness(status="ok")

    @application.get("/api/v1/status", response_model=ServiceStatus, responses=REQUEST_ID_RESPONSE)
    async def status() -> ServiceStatus:
        return ServiceStatus(service="issuedigest-api", api_version="v1", status="ok")

    application.include_router(auth_router(auth_service, workspace_repository))
    application.include_router(catalog_router(workspace_repository))
    application.include_router(search_router(workspace_repository, auth_service))
    application.include_router(
        research_router(research_repository, auth_service, model_available=research_model_available)
    )
    application.include_router(briefing_jobs_router(briefing_job_repository, auth_service))
    application.include_router(question_submissions_router(question_service, auth_service))
    application.include_router(evidence_router(access_repository))
    application.include_router(briefings_router(public_repository))
    return application


app = create_app()
