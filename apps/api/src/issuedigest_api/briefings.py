"""Anonymous read-only publication transport; no private-context lookups or writes."""

import re
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Path
from issuedigest_domain.contract_values import MAX_SAFE_INT, ContractModel
from issuedigest_domain.public_briefings import (
    PublicBriefingDetail,
    PublicBriefingList,
    Slug,
    revalidate_public_detail,
    revalidate_public_list,
)
from issuedigest_storage.public_briefings import PublicBriefingRepository

from .evidence import PROTECTED_HEADERS


class PublicBriefingError(ContractModel):
    detail: Literal[
        "Public briefing not found",
        "Public briefing service unavailable",
        "Invalid public briefing request",
    ]


PUBLIC_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {
        "description": description,
        "headers": PROTECTED_HEADERS,
        **({"model": PublicBriefingError} if code != 200 else {}),
    }
    for code, description in [
        (200, "Validated public publication"),
        (404, "Public briefing not found"),
        (422, "Invalid public briefing request"),
        (503, "Public briefing service unavailable"),
    ]
}


def briefings_router(repository: PublicBriefingRepository | None) -> APIRouter:
    router = APIRouter(prefix="/api/v1/briefings", responses=PUBLIC_RESPONSES)

    @router.get("", response_model=PublicBriefingList)
    def list_briefings() -> PublicBriefingList:
        if repository is None:
            raise HTTPException(503, "Public briefing service unavailable")
        try:
            return revalidate_public_list(repository.list_latest())
        except Exception:
            raise HTTPException(503, "Public briefing service unavailable") from None

    def load(slug: str, version: int | None = None) -> PublicBriefingDetail:
        if repository is None:
            raise HTTPException(503, "Public briefing service unavailable")
        try:
            value = repository.load(slug, version)
            if value is None:
                raise HTTPException(404, "Public briefing not found")
            detail = revalidate_public_detail(value)
            if detail.slug != slug or (version is not None and detail.version != version):
                raise ValueError("Public response identity mismatch")
            return detail
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(503, "Public briefing service unavailable") from None

    @router.get("/{slug}", response_model=PublicBriefingDetail)
    def latest_briefing(slug: Slug) -> PublicBriefingDetail:
        return load(slug)

    @router.get("/{slug}/versions/{version}", response_model=PublicBriefingDetail)
    def versioned_briefing(
        slug: Slug,
        version: Annotated[str, Path(pattern=r"^[1-9][0-9]{0,15}$")],
    ) -> PublicBriefingDetail:
        if re.fullmatch(r"[1-9][0-9]{0,15}", version) is None or int(version) > MAX_SAFE_INT:
            raise HTTPException(422, "Invalid public briefing request")
        return load(slug, int(version))

    return router
