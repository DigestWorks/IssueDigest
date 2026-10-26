"""Bounded authenticated question admission and cancellable SSE caller lifetime."""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Annotated

import anyio
from fastapi import APIRouter, HTTPException, Request, Security
from fastapi.responses import StreamingResponse
from issuedigest_agents.question_submission import QuestionExecutionService, QuestionSubmissionError
from issuedigest_domain.question_submission import (
    QuestionSubmissionErrorEvent,
    QuestionSubmissionProgress,
    QuestionSubmissionRequest,
    QuestionSubmissionResult,
)
from issuedigest_storage.sessions import valid_session_token
from pydantic import UUID4

from .auth import AuthService, _same_origin
from .evidence import COOKIE_AUTH, PROTECTED_HEADERS
from .search import MAX_BODY, _invalid_constant, _unique_pairs

PATH = "/api/v1/workspaces/{workspace_id}/question-briefings"
HEARTBEAT_SECONDS = 10.0
ERRORS = {
    "unauthorized": (401, "Authentication required"),
    "forbidden": (403, "Question submission forbidden"),
    "conflict": (409, "Question submission conflict"),
    "budget": (429, "Question submission budget exceeded"),
    "unavailable": (503, "Question submission unavailable"),
}


async def _body(request: Request) -> QuestionSubmissionRequest:
    if request.query_params or request.headers.getlist("content-type") != ["application/json"]:
        raise HTTPException(422, "Invalid question submission request")
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > MAX_BODY:
            raise HTTPException(422, "Invalid question submission request")
        raw.extend(chunk)
    try:
        json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=_invalid_constant
        )
        return QuestionSubmissionRequest.model_validate_json(raw)
    except (ValueError, TypeError, RecursionError):
        raise HTTPException(422, "Invalid question submission request") from None


def _error_kind(error: QuestionSubmissionError) -> str:
    return error.kind if type(error.kind) is str and error.kind in ERRORS else "unavailable"


def question_submissions_router(
    service: QuestionExecutionService | None, auth_service: AuthService | None
) -> APIRouter:
    router = APIRouter()

    @router.post(
        PATH,
        response_model=None,
        response_class=StreamingResponse,
        responses={
            200: {
                "headers": PROTECTED_HEADERS,
                "content": {"text/event-stream": {"schema": {"type": "string"}}},
            }
        },
        openapi_extra={
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/QuestionSubmissionRequest"}
                    }
                },
            }
        },
    )
    async def submit(
        request: Request,
        workspace_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> StreamingResponse:
        if not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if service is None or auth_service is None:
            raise HTTPException(503, "Question submission unavailable")
        _same_origin(request, auth_service)
        body = await _body(request)
        assert token is not None
        args = (token, workspace_id, body.request_id, body.question)
        try:
            allowed = await service.authorize(*args)
            if type(allowed) is not bool:
                raise ValueError
        except QuestionSubmissionError as error:
            status, detail = ERRORS[_error_kind(error)]
            raise HTTPException(status, detail) from None
        except Exception:
            raise HTTPException(503, "Question submission unavailable") from None
        if not allowed:
            raise HTTPException(404, "Question submission not found")

        async def stream() -> AsyncIterator[str]:
            task = asyncio.create_task(service.run(*args))
            try:
                progress = QuestionSubmissionProgress(request_id=body.request_id, stage="analysing")
                yield f"event: progress\ndata: {progress.model_dump_json()}\n\n"
                while not task.done():
                    done, _ = await asyncio.wait({task}, timeout=HEARTBEAT_SECONDS)
                    if not done:
                        yield ": keepalive\n\n"
                try:
                    result = task.result()
                    if (
                        type(result) is not QuestionSubmissionResult
                        or result.__pydantic_extra__
                        or set(result.__dict__) != set(QuestionSubmissionResult.model_fields)
                    ):
                        raise ValueError
                    checked = QuestionSubmissionResult.model_validate_json(
                        result.model_dump_json(warnings=False)
                    )
                    if checked.request_id != body.request_id:
                        raise ValueError
                    yield f"event: result\ndata: {checked.model_dump_json()}\n\n"
                except Exception as error:
                    kind = (
                        _error_kind(error)
                        if isinstance(error, QuestionSubmissionError)
                        else "unavailable"
                    )
                    event = QuestionSubmissionErrorEvent.model_validate(
                        dict(request_id=body.request_id, kind=kind)
                    )
                    yield f"event: error\ndata: {event.model_dump_json()}\n\n"
            finally:
                if not task.done():
                    task.cancel()
                with anyio.CancelScope(shield=True):
                    await asyncio.gather(task, return_exceptions=True)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
        )

    return router
