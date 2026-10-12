"""Cookie-only protected evidence route; canonical domain schema remains authoritative."""

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Security
from fastapi.responses import Response
from fastapi.security import APIKeyCookie
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import AuthenticationDenied, EvidenceAccessRepository, StorageError
from issuedigest_storage.sessions import valid_session_token
from pydantic import UUID4, ValidationError

from .cookies import SESSION_COOKIE

EVIDENCE_PATH = "/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}"
COOKIE_AUTH = APIKeyCookie(name=SESSION_COOKIE, scheme_name="SessionCookie", auto_error=False)
PROTECTED_HEADERS: dict[str, Any] = {
    "Cache-Control": {"schema": {"type": "string", "const": "no-store"}},
    "X-Request-ID": {
        "description": "Server-generated request UUID.",
        "schema": {"type": "string", "format": "uuid"},
    },
}
PROTECTED_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"description": description, "headers": PROTECTED_HEADERS}
    for code, description in [
        (200, "Validated immutable evidence"),
        (401, "Authentication required"),
        (404, "Evidence not found"),
        (422, "Validation Error"),
        (503, "Evidence service unavailable"),
    ]
}
PROTECTED_RESPONSES[200]["content"] = {
    "application/json": {"schema": {"$ref": "#/components/schemas/EvidenceBundle"}}
}


def evidence_router(access_repository: EvidenceAccessRepository | None) -> APIRouter:
    router = APIRouter()

    @router.get(EVIDENCE_PATH, response_model=None, responses=PROTECTED_RESPONSES)
    def load_evidence(
        workspace_id: UUID4,
        snapshot_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> Response:
        if token is None or not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if access_repository is None:
            raise HTTPException(503, "Evidence service unavailable")
        try:
            bundle = access_repository.load_evidence(token, workspace_id, snapshot_id)
            if bundle is None:
                raise HTTPException(404, "Evidence not found")
            # Validate at the HTTP boundary as well, even when an injected backend is incorrect.
            validated = EvidenceBundle.model_validate_json(bundle.model_dump_json(warnings=False))
            return Response(validated.model_dump_json(), media_type="application/json")
        except AuthenticationDenied:
            raise HTTPException(401, "Authentication required") from None
        except (StorageError, ValidationError, ValueError, TypeError, AttributeError):
            raise HTTPException(503, "Evidence service unavailable") from None

    return router
