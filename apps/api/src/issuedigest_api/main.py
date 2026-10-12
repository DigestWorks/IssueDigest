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
from issuedigest_domain.status import Liveness, ServiceStatus
from issuedigest_storage import EvidenceAccessRepository

from .contracts import add_evidence_schemas
from .evidence import evidence_router


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


def _protected_path(path: str) -> bool:
    return re.fullmatch(r"/api/v1/workspaces/[^/]+/evidence/[^/]+/?", path) is not None


def create_app(access_repository: EvidenceAccessRepository | None = None) -> IssueDigestAPI:
    """Configure only from trusted server code; the default protected route fails closed."""
    application = IssueDigestAPI(title="IssueDigest API", version="v1")

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exception: RequestValidationError) -> Response:
        if not _protected_path(request.url.path):
            return await request_validation_exception_handler(request, exception)
        return JSONResponse(
            status_code=422,
            content={
                "detail": [
                    {
                        "type": error["type"],
                        "loc": error["loc"],
                        "msg": "Invalid UUID4 path parameter",
                    }
                    for error in exception.errors()
                ]
            },
        )

    @application.middleware("http")
    async def request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        identifier = str(uuid4())
        protected = _protected_path(request.url.path)
        try:
            response = await call_next(request)
        except Exception:
            # Do not include exceptions, cookies, paths or source text in logs.
            logger.error("Unhandled request error request_id=%s", identifier)
            response = JSONResponse(
                status_code=503 if protected else 500,
                content={
                    "detail": "Evidence service unavailable"
                    if protected
                    else "Internal server error"
                },
            )
        response.headers["X-Request-ID"] = identifier
        if protected:
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/health/live", response_model=Liveness, responses=REQUEST_ID_RESPONSE)
    async def liveness() -> Liveness:
        """The process responds; database and execution-engine readiness are not checked."""
        return Liveness(status="ok")

    @application.get("/api/v1/status", response_model=ServiceStatus, responses=REQUEST_ID_RESPONSE)
    async def status() -> ServiceStatus:
        return ServiceStatus(service="issuedigest-api", api_version="v1", status="ok")

    application.include_router(evidence_router(access_repository))
    return application


app = create_app()
