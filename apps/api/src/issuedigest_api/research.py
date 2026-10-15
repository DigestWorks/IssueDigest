"""Cookie protected source and durable research HTTP boundary."""

import json
from typing import Annotated, Any, cast

from fastapi import APIRouter, HTTPException, Request, Security
from issuedigest_domain.research_journey import (
    ResearchRequest,
    ResearchRun,
    ResearchRunList,
    ResearchSourceCatalog,
)
from issuedigest_storage import AuthenticationDenied, StorageError
from issuedigest_storage.research import (
    ResearchBudgetExceeded,
    ResearchConflict,
    ResearchForbidden,
    ResearchRepository,
)
from issuedigest_storage.sessions import valid_session_token
from pydantic import UUID4, ValidationError
from starlette.concurrency import run_in_threadpool

from .auth import AuthService, _same_origin
from .evidence import COOKIE_AUTH
from .search import _invalid_constant, _unique_pairs

BASE = "/api/v1/workspaces/{workspace_id}/research"


async def _body(request: Request) -> ResearchRequest:
    if request.query_params or request.headers.getlist("content-type") != ["application/json"]:
        raise HTTPException(422, "Invalid research request")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > 16_384:
            raise HTTPException(422, "Invalid research request")
        body.extend(chunk)
    try:
        parsed = json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant
        )
        return ResearchRequest.model_validate(parsed)
    except (UnicodeError, ValueError, TypeError, ValidationError, RecursionError):
        raise HTTPException(422, "Invalid research request") from None


def research_router(
    repository: ResearchRepository | None,
    auth_service: AuthService | None,
    *,
    model_available: bool = True,
) -> APIRouter:
    router = APIRouter()

    def check_token(token: str | None) -> str:
        if token is None or not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if repository is None:
            raise HTTPException(503, "Research service unavailable")
        return token

    async def call(method: str, *args: Any) -> Any:
        assert repository is not None
        try:
            result = await run_in_threadpool(getattr(repository, method), *args)
            if result is None:
                raise HTTPException(404, "Research not found")
            return result
        except AuthenticationDenied:
            raise HTTPException(401, "Authentication required") from None
        except ResearchForbidden:
            raise HTTPException(403, "Research write forbidden") from None
        except ResearchBudgetExceeded:
            raise HTTPException(429, "Research budget reached") from None
        except ResearchConflict:
            raise HTTPException(409, "Research request conflicts") from None
        except (StorageError, ValueError, ValidationError, TypeError):
            raise HTTPException(503, "Research service unavailable") from None

    @router.get(BASE + "/sources", response_model=ResearchSourceCatalog)
    async def sources(
        request: Request, workspace_id: UUID4, token: Annotated[str | None, Security(COOKIE_AUTH)]
    ) -> ResearchSourceCatalog:
        if request.query_params:
            raise HTTPException(422, "Invalid research request")
        return cast(
            ResearchSourceCatalog, await call("list_sources", check_token(token), workspace_id)
        )

    @router.get(BASE, response_model=ResearchRunList)
    async def runs(
        request: Request, workspace_id: UUID4, token: Annotated[str | None, Security(COOKIE_AUTH)]
    ) -> ResearchRunList:
        if request.query_params:
            raise HTTPException(422, "Invalid research request")
        return cast(ResearchRunList, await call("list_runs", check_token(token), workspace_id))

    @router.post(
        BASE,
        response_model=ResearchRun,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {"schema": {"$ref": "#/components/schemas/ResearchRequest"}}
                },
            }
        },
    )
    async def submit(
        request: Request, workspace_id: UUID4, token: Annotated[str | None, Security(COOKIE_AUTH)]
    ) -> ResearchRun:
        valid = check_token(token)
        if auth_service is None:
            raise HTTPException(503, "Research service unavailable")
        _same_origin(request, auth_service)
        payload = await _body(request)
        if not model_available:
            raise HTTPException(503, "Research model unavailable")
        return cast(ResearchRun, await call("submit", valid, workspace_id, payload))

    @router.get(BASE + "/{run_id}", response_model=ResearchRun)
    async def run(
        request: Request,
        workspace_id: UUID4,
        run_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> ResearchRun:
        if request.query_params:
            raise HTTPException(422, "Invalid research request")
        return cast(ResearchRun, await call("get_run", check_token(token), workspace_id, run_id))

    @router.post(BASE + "/{run_id}/cancel", response_model=ResearchRun)
    async def cancel(
        request: Request,
        workspace_id: UUID4,
        run_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> ResearchRun:
        valid = check_token(token)
        if auth_service is None:
            raise HTTPException(503, "Research service unavailable")
        _same_origin(request, auth_service)
        if (
            request.query_params
            or request.headers.getlist("content-type") != ["application/json"]
            or await request.body() != b"{}"
        ):
            raise HTTPException(422, "Invalid research request")
        return cast(ResearchRun, await call("cancel", valid, workspace_id, run_id))

    return router
