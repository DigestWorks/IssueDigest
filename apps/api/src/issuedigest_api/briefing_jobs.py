"""Private current-rights briefing reads and cancellation; no execution admission."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, Security
from issuedigest_agents.briefing_receipts import validate_stored_briefing
from issuedigest_agents.question_briefing_generation import QuestionBriefingGeneration
from issuedigest_domain.briefing_job_view import (
    BriefingClaimView,
    BriefingJobView,
    BriefingModuleView,
    BriefingQuoteView,
    BriefingResultView,
)
from issuedigest_storage import AuthenticationDenied
from issuedigest_storage.briefing_jobs import BriefingJobInputs, BriefingJobRepository
from issuedigest_storage.research import ResearchConflict, ResearchForbidden
from issuedigest_storage.sessions import valid_session_token
from pydantic import UUID4
from starlette.concurrency import run_in_threadpool

from .auth import AuthService, _same_origin
from .evidence import COOKIE_AUTH

BASE = "/api/v1/workspaces/{workspace_id}/briefing-jobs/{job_id}"


def project_briefing(
    result: QuestionBriefingGeneration, packet: BriefingJobInputs
) -> BriefingResultView:
    briefing = result.briefing
    sources = {s[0]: s for s in packet.sources}
    indexes = {
        s.snapshot_id: {p.id: p for p in s.receipt.evidence.propositions} for s in briefing.sources
    }

    def quotes(references: tuple[tuple[UUID, str], ...]) -> tuple[BriefingQuoteView, ...]:
        wanted: dict[UUID, set[str]] = {}
        for sid, pid in references:
            pending = [pid]
            found = wanted.setdefault(sid, set())
            while pending:
                identifier = pending.pop()
                if identifier not in found:
                    found.add(identifier)
                    pending.extend(indexes[sid][identifier].depends_on_ids)
        collected: dict[tuple[UUID, str, int, int, str], BriefingQuoteView] = {}
        for sid, index in indexes.items():
            if sid not in wanted:
                continue
            _, bundle, presentation = sources[sid]
            citations = {str(c.citation_id): c.selector.quote for c in bundle.citations}
            for pid, proposition in index.items():
                if pid not in wanted[sid]:
                    continue
                for ref in proposition.supporting_refs:
                    key = (sid, ref.citation_id, ref.start, ref.end, ref.text)
                    collected.setdefault(
                        key,
                        BriefingQuoteView(
                            snapshot_id=sid,
                            citation_id=UUID(ref.citation_id),
                            source_title=presentation.title,
                            start=ref.start,
                            end=ref.end,
                            text=ref.text,
                            citation_quote=citations[ref.citation_id],
                        ),
                    )
        return tuple(collected.values())

    return BriefingResultView(
        outcome=briefing.outcome,
        message=briefing.message,
        modules=tuple(
            BriefingModuleView(
                kind=m.kind,
                title=m.title,
                claims=tuple(
                    BriefingClaimView(
                        text=c.text,
                        epistemic_status=c.epistemic_status,
                        event_date=c.event_date,
                        quotes=quotes(
                            tuple((r.snapshot_id, r.proposition_id) for r in c.references)
                        ),
                    )
                    for c in m.claims
                ),
            )
            for m in briefing.modules
        ),
        additional_quotes=quotes(
            tuple(
                (c.snapshot_id, pid)
                for c in briefing.coverage
                for pid in c.uncovered_linked_proposition_ids
            )
        ),
    )


def briefing_jobs_router(
    repository: BriefingJobRepository | None, auth_service: AuthService | None
) -> APIRouter:
    router = APIRouter()

    def view(token: str, workspace_id: UUID, job_id: UUID, cancel: bool) -> BriefingJobView:
        assert repository is not None
        try:
            job = (
                repository.cancel(token, workspace_id, job_id)
                if cancel
                else repository.get(token, workspace_id, job_id)
            )
            if cancel and job is not None:
                current = repository.get(token, workspace_id, job_id)
                if current is None:
                    raise HTTPException(404, "Briefing job not found")
                if current != job:
                    raise ResearchConflict("Changed job")
            if job is None:
                raise HTTPException(404, "Briefing job not found")
            result = None
            if job.status == "completed":
                prepared, packet = repository.prepare(job_id)
                if prepared != job:
                    raise ResearchConflict("Changed job")
                result = project_briefing(validate_stored_briefing(job, packet), packet)
                if repository.get(token, workspace_id, job_id) != job:
                    raise ResearchConflict("Changed job")
            return BriefingJobView.model_validate(
                dict(job_id=job.job_id, question=job.question, status=job.status, result=result)
            )
        except HTTPException:
            raise
        except AuthenticationDenied:
            raise HTTPException(401, "Authentication required") from None
        except ResearchForbidden:
            raise HTTPException(403, "Briefing access forbidden") from None
        except ResearchConflict:
            raise HTTPException(409, "Briefing request conflicts") from None
        except Exception:
            raise HTTPException(503, "Briefing service unavailable") from None

    def check(token: str | None) -> str:
        if token is None or not valid_session_token(token):
            raise HTTPException(401, "Authentication required")
        if repository is None:
            raise HTTPException(503, "Briefing service unavailable")
        return token

    @router.get(BASE, response_model=BriefingJobView)
    async def read(
        request: Request,
        workspace_id: UUID4,
        job_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> BriefingJobView:
        if request.query_params:
            raise HTTPException(422, "Invalid briefing request")
        return await run_in_threadpool(view, check(token), workspace_id, job_id, False)

    @router.post(BASE + "/cancel", response_model=BriefingJobView)
    async def cancel(
        request: Request,
        workspace_id: UUID4,
        job_id: UUID4,
        token: Annotated[str | None, Security(COOKIE_AUTH)],
    ) -> BriefingJobView:
        valid = check(token)
        if auth_service is None:
            raise HTTPException(503, "Briefing service unavailable")
        _same_origin(request, auth_service)
        if request.query_params or request.headers.getlist("content-type") != ["application/json"]:
            raise HTTPException(422, "Invalid briefing request")
        body = bytearray()
        async for chunk in request.stream():
            if len(body) + len(chunk) > 16384:
                raise HTTPException(422, "Invalid briefing request")
            body.extend(chunk)
        if body != b"{}":
            raise HTTPException(422, "Invalid briefing request")
        return await run_in_threadpool(view, valid, workspace_id, job_id, True)

    return router
