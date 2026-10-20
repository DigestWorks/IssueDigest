"""Pure exact contextual locations; unreviewed provenance never certifies meaning or access."""

from typing import Annotated, Any, Literal

from issuedigest_domain.sources import Sha256
from pydantic import UUID4, Field, field_validator

from .numeric_candidates import ExactSpan, build_numeric_candidates
from .numeric_evidence import Source, _StrictModel
from .numeric_selection import ResolvedAnchor, SentenceAnchor, _resolve_anchor
from .numeric_selection_evaluation import _canonical_models, _read


class ContextualAnchorError(ValueError):
    """Sanitized failure without source text, validation details or partial results."""


class ContextualAnchor(SentenceAnchor):
    """A short exact phrase with required nullable, exact sentence-local disambiguation."""

    context_text: Annotated[str, Field(min_length=1, max_length=1000)] | None

    @field_validator("context_text")
    @classmethod
    def exact_context(cls, value: str | None) -> str | None:
        return cls.exact_nonblank(value) if value is not None else None


class ContextualAnchorResolution(_StrictModel):
    """A reconstructable source location, without a duplicate source or candidate index."""

    profile: Literal["contextual-anchor-v1"] = "contextual-anchor-v1"
    status: Literal["unreviewed"] = "unreviewed"
    snapshot_id: UUID4
    workspace_id: UUID4
    source_sha256: Sha256
    anchor: ContextualAnchor
    resolved: ResolvedAnchor


def _resolve(source: Source, anchor: ContextualAnchor) -> ContextualAnchorResolution:
    _canonical_models(source, Source)
    index = build_numeric_candidates(source)
    if anchor.context_text is None:
        resolved = _resolve_anchor(index, anchor)
    else:
        context = _resolve_anchor(
            index, SentenceAnchor(sentence_id=anchor.sentence_id, text=anchor.context_text)
        )
        offset = context.span.text.find(anchor.text)
        if offset < 0 or context.span.text.find(anchor.text, offset + 1) >= 0:
            raise ValueError("Phrase must occur exactly once inside context")
        start = context.span.start + offset
        resolved = ResolvedAnchor(
            sentence_id=anchor.sentence_id,
            span=ExactSpan(
                citation_id=context.span.citation_id,
                text=anchor.text,
                start=start,
                end=start + len(anchor.text),
            ),
        )
    return ContextualAnchorResolution(
        snapshot_id=index.snapshot_id,
        workspace_id=index.workspace_id,
        source_sha256=index.source_sha256,
        anchor=anchor,
        resolved=resolved,
    )


def resolve_contextual_anchor(
    source: Source, anchor: ContextualAnchor | dict[str, Any]
) -> ContextualAnchorResolution:
    """Resolve an explicit exact location in the current canonical source without I/O or repair."""
    try:
        return _resolve(source, _read(ContextualAnchor, anchor))
    except Exception:
        raise ContextualAnchorError("Invalid contextual anchor input") from None


def validate_contextual_anchor(
    source: Source, resolution: ContextualAnchorResolution | dict[str, Any]
) -> ContextualAnchorResolution:
    """Rebuild and compare every field; current authorization and meaning remain caller concerns."""
    try:
        checked = _read(ContextualAnchorResolution, resolution)
        expected = _resolve(source, checked.anchor)
        if expected != checked:
            raise ValueError("Resolution differs from current source reconstruction")
        return expected
    except Exception:
        raise ContextualAnchorError("Invalid contextual anchor resolution") from None
