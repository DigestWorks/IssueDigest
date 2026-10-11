"""HTTP entry point for IssueDigest; status endpoints need no external services."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from issuedigest_domain.status import Liveness, ServiceStatus

from .contracts import add_evidence_schemas


class IssueDigestAPI(FastAPI):
    def openapi(self) -> dict[str, Any]:
        return add_evidence_schemas(super().openapi())


app = IssueDigestAPI(title="IssueDigest API", version="v1")
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


@app.middleware("http")
async def request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    identifier = str(uuid4())
    try:
        response = await call_next(request)
    except Exception:
        # Keep unexpected error responses traceable without exposing exception details.
        logger.exception("Unhandled request error request_id=%s", identifier)
        response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
    response.headers["X-Request-ID"] = identifier
    return response


@app.get("/health/live", response_model=Liveness, responses=REQUEST_ID_RESPONSE)
async def liveness() -> Liveness:
    """The API process responds; database and execution-engine readiness are not checked."""
    return Liveness(status="ok")


@app.get("/api/v1/status", response_model=ServiceStatus, responses=REQUEST_ID_RESPONSE)
async def status() -> ServiceStatus:
    return ServiceStatus(service="issuedigest-api", api_version="v1", status="ok")
