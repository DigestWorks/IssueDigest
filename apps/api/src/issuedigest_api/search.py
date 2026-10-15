"""Cookie-protected, bounded literal evidence search HTTP boundary."""

import json
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.responses import Response
from issuedigest_domain import (
    EvidenceSearchQuery,
    EvidenceSearchResult,
    literal_matches,
)
from issuedigest_storage import AuthenticationDenied, StorageError, WorkspaceAccessRepository
from issuedigest_storage.sessions import valid_session_token
from pydantic import UUID4, BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from .auth import AuthService, _same_origin
from .errors import OriginDeniedError
from .evidence import COOKIE_AUTH, PROTECTED_RESPONSES

SEARCH_PATH = "/api/v1/workspaces/{workspace_id}/evidence/search"
MAX_BODY = 16_384


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("invalid JSON number")


async def _query(request: Request) -> EvidenceSearchQuery:
    if request.query_params or request.headers.getlist("content-type") != ["application/json"]:
        raise HTTPException(422, "Invalid evidence search request")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BODY:
            raise HTTPException(422, "Invalid evidence search request")
        body.extend(chunk)
    try:
        json.loads(
            body.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant
        )
        return EvidenceSearchQuery.model_validate_json(body)
    except (UnicodeError, ValueError, TypeError, ValidationError, RecursionError):
        raise HTTPException(422, "Invalid evidence search request") from None


def _clean_model(value: BaseModel) -> bool:
    return not value.__pydantic_extra__ and set(value.__dict__) == set(type(value).model_fields)


def _validated_result(
    result: EvidenceSearchResult, workspace_id: UUID4, query: EvidenceSearchQuery
) -> EvidenceSearchResult:
    if not isinstance(result, EvidenceSearchResult) or not _clean_model(result):
        raise ValueError
    if not isinstance(result.query, EvidenceSearchQuery) or not _clean_model(result.query):
        raise ValueError
    if not all(isinstance(hit, BaseModel) and _clean_model(hit) for hit in result.hits):
        raise ValueError
    checked = EvidenceSearchResult.model_validate_json(result.model_dump_json(warnings=False))
    if checked.workspace_id != workspace_id or checked.query != query:
        raise ValueError
    if len(checked.hits) > query.limit or len(checked.hits) > checked.scanned_candidates:
        raise ValueError
    if checked.hits and checked.coverage.indexed_snapshots == 0:
        raise ValueError
    identities = set()
    snapshots = set()
    for hit in checked.hits:
        if (
            hit.workspace_id != workspace_id
            or hit.matched_terms != query.terms
            or not literal_matches(query, hit.selector.quote)
            or (query.provider is not None and hit.provider != query.provider)
            or (query.source_id is not None and hit.source_id != query.source_id)
            or (query.source_kind is not None and hit.source_kind != query.source_kind)
            or (query.collected_from is not None and hit.collected_at < query.collected_from)
            or (query.collected_to is not None and hit.collected_at >= query.collected_to)
        ):
            raise ValueError
        identity = (hit.snapshot_id, hit.unit_ordinal)
        if identity in identities:
            raise ValueError
        identities.add(identity)
        snapshots.add(hit.snapshot_id)
    if len(snapshots) > checked.coverage.indexed_snapshots:
        raise ValueError
    return checked


def search_router(
    repository: WorkspaceAccessRepository | None, auth_service: AuthService | None
) -> APIRouter:
    router = APIRouter()
    responses = {code: dict(value) for code, value in PROTECTED_RESPONSES.items()}
    responses[200]["content"] = {
        "application/json": {"schema": {"$ref": "#/components/schemas/EvidenceSearchResult"}}
    }
    responses[422] = {
        **responses[422],
        "content": {
            "application/json": {
                "schema": {
                    "oneOf": [
                        {"$ref": "#/components/schemas/EvidenceSearchRequestError"},
                        {"$ref": "#/components/schemas/EvidencePathValidationError"},
                    ]
                }
            }
        },
    }
    responses[422].pop("model", None)
    responses[403] = {"model": OriginDeniedError, "headers": PROTECTED_RESPONSES[200]["headers"]}

    @router.post(
        SEARCH_PATH,
        response_model=None,
        responses=responses,
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/EvidenceSearchQuery"}
                    }
                },
            }
        },
    )
    async def search(
        request: Request,
        workspace_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> Response:
        if not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if auth_service is None or repository is None:
            raise HTTPException(503, "Evidence service unavailable")
        _same_origin(request, auth_service)
        query = await _query(request)
        try:
            assert token is not None
            result = await run_in_threadpool(repository.search_evidence, token, workspace_id, query)
            if result is None:
                raise HTTPException(404, "Evidence not found")
            checked = _validated_result(result, workspace_id, query)
            return Response(checked.model_dump_json(), media_type="application/json")
        except AuthenticationDenied:
            raise HTTPException(401, "Authentication required") from None
        except (
            StorageError,
            ValidationError,
            ValueError,
            TypeError,
            AttributeError,
            RecursionError,
        ):
            raise HTTPException(503, "Evidence service unavailable") from None

    return router
