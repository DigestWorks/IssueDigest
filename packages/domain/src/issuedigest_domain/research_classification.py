"""Bounded private v3/v4/v5/v6/v7 profiles, separate from generic and public Canvas contracts."""

import re
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from .canvas import CanvasBundle
from .research_text import has_v6_text


def _field(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, dict) else getattr(value, key, default)


def require_raw_classification_utc(canvas: Any) -> None:
    """Check original UTC spelling before generic metadata validators normalize offsets."""
    research = _field(canvas, "research")
    claims = _field(research, "claims", ())
    reviews = _field(research, "support_reviews", ())
    if not isinstance(claims, (tuple, list)) or not isinstance(reviews, (tuple, list)):
        return  # Generic Canvas validation reports malformed collections.
    if (
        not any(
            _field(_field(c, "derivation"), "method_version")
            in ("research-v3", "research-v4", "research-v5", "research-v6", "research-v7")
            for c in claims
        )
        and not reviews
    ):
        return
    values = [_field(_field(canvas, "revision"), "validated_at")]
    values.extend(_field(review, "reviewed_at") for review in reviews)
    for value in values:
        if isinstance(value, str):
            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value
            ):
                raise ValueError("Research classification timestamps require explicit UTC")
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime) or value.utcoffset() != timedelta(0):
            raise ValueError("Research classification timestamps require explicit UTC")


def validate_research_classification(canvas: CanvasBundle) -> None:
    """Never infer reviews for legacy results; every new inference has exactly one assessment."""
    research, revision = canvas.research, canvas.revision
    claims, reviews = research.claims, research.support_reviews
    versions = {c.derivation.method_version if c.derivation else None for c in claims}
    classified = {
        version
        for version in ("research-v3", "research-v4", "research-v5", "research-v6", "research-v7")
        if version in versions
    }
    if not classified:
        if reviews:
            raise ValueError("Legacy research cannot carry classification")
        return
    if len(versions) != 1 or len(reviews) != len(claims) or len(claims) > 12:
        raise ValueError("Incomplete or mixed research classification")
    if (
        not 1 <= len(research.evidence) <= 5
        or research.entities
        or research.relations
        or research.observations
        or revision.revision_number != 1
        or revision.parent_revision_id is not None
        or set(revision.selected_version_ids) != {e.version.version_id for e in research.evidence}
        or len(revision.selected_version_ids) != len(research.evidence)
    ):
        raise ValueError("Invalid classified research profile")
    (method_version,) = classified
    reviewer_id = "issuedigest-" + method_version
    by_id = {c.claim_id: c for c in claims}
    reviewed = set()
    for review in reviews:
        if review.target.kind != "claim" or review.target.claim_id not in by_id:
            raise ValueError("Classification target must be a real claim")
        claim = by_id[review.target.claim_id]
        if (
            claim.claim_id in reviewed
            or claim.basis != "inference"
            or claim.derivation is None
            or claim.derivation.method != "pydantic-ai"
            or len(claim.derivation.rationale) > 200
            or len(claim.text) > 500
            or len(claim.citation_ids) > 3
            or claim.speaker_entity_id is not None
            or claim.subject_entity_ids
            or claim.raw_event_time_text is not None
            or review.citation_ids != claim.citation_ids
            or (review.reviewer_kind, review.reviewer_id, review.method, review.method_version)
            != (
                "automated",
                reviewer_id,
                "pydantic-ai",
                method_version,
            )
            or (review.scope, review.assessment)
            not in {
                ("content", "supported"),
                ("attribution", "supported"),
                ("content", "insufficient"),
            }
            or not 1 <= len(review.rationale) <= 300
            or review.reviewed_at != revision.validated_at
            or review.reviewed_at.utcoffset() != timedelta(0)
            or revision.validated_at.utcoffset() != timedelta(0)
        ):
            raise ValueError("Invalid claim classification metadata")
        reviewed.add(claim.claim_id)
    modules = revision.draft.modules
    if revision.draft.outcome != "answer" or not 2 <= len(modules) <= 4:
        raise ValueError("Classified answer requires analysis and evidence")
    if method_version in {"research-v6", "research-v7"}:
        first = modules[0]
        if first.kind != "summary" or any(m.kind == "summary" for m in modules[1:]):
            raise ValueError("v6 requires first summary and comparison/timeline details")
        core_id = first.claim_ids[0]
        if not any(
            r.target.kind == "claim"
            and r.target.claim_id == core_id
            and r.assessment == "supported"
            for r in reviews
        ):
            raise ValueError("v6 core answer must be supported")
        quotes = {c.citation_id: c.selector.quote for e in research.evidence for c in e.citations}
        for review in reviews:
            if review.target.kind != "claim":
                continue
            claim = by_id[review.target.claim_id]
            if review.scope != "attribution":
                if not has_v6_text(claim.text):
                    raise ValueError("v6 claim body must be nonblank")
                continue
            # The exact subject may itself contain the separator. Accept any exact
            # bounded decomposition; never strip or infer a speaker from metadata.
            separator = "에 따르면, "
            if not any(
                claim.text.startswith(separator, end)
                and has_v6_text(claim.text[:end])
                and 1 <= len(claim.text[end + len(separator) :]) <= 400
                and has_v6_text(claim.text[end + len(separator) :])
                and (
                    claim.text[:end] == "제공 자료"
                    or all(claim.text[:end] in quotes[c] for c in claim.citation_ids)
                )
                for end in range(1, min(80, len(claim.text)) + 1)
            ):
                raise ValueError("v6 attribution requires exact selected quote subject")
    used = set()
    all_cited: set[UUID] = set()
    quotes = {c.citation_id: c.selector.quote for e in research.evidence for c in e.citations}
    for index, module in enumerate(modules):
        if module.span != "full" or len(module.title) > 100:
            raise ValueError("Invalid classified module")
        if module.kind == "evidence":
            if index != len(modules) - 1 or set(module.citation_ids) != all_cited:
                raise ValueError("Classified evidence must be last and exact")
        elif module.kind in {"summary", "comparison", "timeline"}:
            if not (2 if module.kind == "comparison" else 1) <= len(module.claim_ids) <= 4:
                raise ValueError("Invalid classified module claim count")
            for claim_id in module.claim_ids:
                if claim_id in used:
                    raise ValueError("Classified claim must be displayed exactly once")
                used.add(claim_id)
                claim = by_id[claim_id]
                if module.kind == "timeline":
                    period = claim.valid_period
                    if (
                        period is None
                        or period.start_date != period.end_date
                        or not any(
                            period.start_date.isoformat() in quotes[c] for c in claim.citation_ids
                        )
                    ):
                        raise ValueError("Classified timeline date requires exact quote")
                elif claim.valid_period is not None:
                    raise ValueError("Only classified timeline claims carry dates")
            all_cited.update(module.citation_ids)
        else:
            raise ValueError("Unsupported classified module")
        if len(module.actions) != len(module.citation_ids) or {
            a.citation_id for a in module.actions if a.kind == "open_evidence"
        } != set(module.citation_ids):
            raise ValueError("Classified evidence actions must be exact")
    if used != set(by_id) or modules[-1].kind != "evidence":
        raise ValueError("Classified claims must be displayed")
