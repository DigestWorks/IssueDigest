"""Protected catalog; metadata leaves storage only after current membership checks."""

import re
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Security
from fastapi.responses import Response
from issuedigest_domain import EvidenceCatalog
from issuedigest_storage import AuthenticationDenied, StorageError, WorkspaceAccessRepository
from issuedigest_storage.sessions import valid_session_token
from pydantic import UUID4, BeforeValidator

from .evidence import COOKIE_AUTH, PROTECTED_RESPONSES


def _parse_limit(value: object) -> int:
    if type(value) is int and 1 <= value <= 50:
        return value
    if not isinstance(value, str) or re.fullmatch(r"(?:[1-9]|[1-4][0-9]|50)", value) is None:
        raise ValueError("Invalid catalog limit")
    return int(value)


def catalog_router(repository: WorkspaceAccessRepository | None) -> APIRouter:
    router = APIRouter()
    responses = {code: dict(value) for code, value in PROTECTED_RESPONSES.items()}
    responses[200]["content"] = {
        "application/json": {"schema": {"$ref": "#/components/schemas/EvidenceCatalog"}}
    }

    @router.get(
        "/api/v1/workspaces/{workspace_id}/evidence", response_model=None, responses=responses
    )
    def catalog(
        request: Request,
        workspace_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
        limit: Annotated[int, BeforeValidator(_parse_limit), Query(ge=1, le=50)] = 20,
    ) -> Response:
        if len(request.query_params.getlist("limit")) > 1:
            raise HTTPException(
                422,
                [
                    {
                        "type": "value_error",
                        "loc": ["query", "limit"],
                        "msg": "Invalid catalog limit",
                    }
                ],
            )
        if not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if repository is None:
            raise HTTPException(503, "Evidence service unavailable")
        try:
            assert token is not None
            result = repository.list_evidence(token, workspace_id, int(limit))
            if result is None:
                raise HTTPException(404, "Evidence not found")
            checked = EvidenceCatalog.model_validate_json(result.model_dump_json(warnings=False))
            if checked.workspace_id != workspace_id:
                raise ValueError
            return Response(checked.model_dump_json(), media_type="application/json")
        except AuthenticationDenied:
            raise HTTPException(401, "Authentication required") from None
        except (StorageError, ValueError, TypeError, AttributeError):
            raise HTTPException(503, "Evidence service unavailable") from None

    return router
