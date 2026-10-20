"""Pure contextual role frames; exact source linkage never certifies meaning or access."""

from typing import Any, Literal

from pydantic import Field

from .contextual_anchor import ContextualAnchor, resolve_contextual_anchor
from .numeric_evidence import Source, _StrictModel
from .numeric_frame import (
    _ANCHORS,
    FrameFactInput,
    FrameRelationInput,
    NumericEvidenceFrame,
    build_numeric_frame,
)
from .numeric_selection import SentenceAnchor
from .numeric_selection_evaluation import _read


class ContextualFrameError(ValueError):
    """Sanitized failure of the entire contextual frame, without partial output."""


class ContextualFrameFactInput(FrameFactInput):
    measured_entity: ContextualAnchor | None
    reporting_actor: ContextualAnchor | None
    period: ContextualAnchor | None
    logical_condition: ContextualAnchor | None
    forecast_basis: ContextualAnchor | None
    comparison_baseline: ContextualAnchor | None
    status_text: ContextualAnchor | None
    reporting_tense_text: ContextualAnchor | None


class ContextualFrameRelationInput(FrameRelationInput):
    cue: ContextualAnchor


class ContextualFrameInput(_StrictModel):
    facts: tuple[ContextualFrameFactInput, ...] = Field(max_length=12)
    relations: tuple[ContextualFrameRelationInput, ...] = Field(max_length=16)


class ContextualNumericFrame(_StrictModel):
    """Stored input reconstructs short spans; resolved is a structural DTO only."""

    profile: Literal["numeric-contextual-frame-v1"] = "numeric-contextual-frame-v1"
    status: Literal["unreviewed"] = "unreviewed"
    input: ContextualFrameInput
    resolved: NumericEvidenceFrame


def _temporary(anchor: ContextualAnchor | None) -> dict[str, str] | None:
    if anchor is None:
        return None
    return SentenceAnchor(
        sentence_id=anchor.sentence_id,
        text=anchor.context_text if anchor.context_text is not None else anchor.text,
    ).model_dump()


def _build(source: Source, data: ContextualFrameInput) -> ContextualNumericFrame:
    # Only unique whole contexts are used for the frozen structural validation.
    # Sentence-local contexts preserve all whole-statement and quote boundaries.
    broad = build_numeric_frame(
        source,
        {
            "facts": [
                {
                    "candidate_id": fact.candidate_id,
                    "value_status": fact.value_status,
                    "reporting_tense": fact.reporting_tense,
                    **{role: _temporary(getattr(fact, role)) for role in _ANCHORS},
                }
                for fact in data.facts
            ],
            "relations": [
                {**relation.model_dump(exclude={"cue"}), "cue": _temporary(relation.cue)}
                for relation in data.relations
            ],
        },
    )
    raw = broad.model_dump(mode="json")
    for fact, resolved in zip(data.facts, raw["facts"], strict=True):
        for role in _ANCHORS:
            anchor = getattr(fact, role)
            resolved[role] = (
                resolve_contextual_anchor(source, anchor).resolved.model_dump(mode="json")
                if anchor is not None
                else None
            )
    for relation, resolved in zip(data.relations, raw["relations"], strict=True):
        resolved["cue"] = resolve_contextual_anchor(source, relation.cue).resolved.model_dump(
            mode="json"
        )
    return ContextualNumericFrame(input=data, resolved=_read(NumericEvidenceFrame, raw))


def build_contextual_frame(
    source: Source, input: ContextualFrameInput | dict[str, Any]
) -> ContextualNumericFrame:
    """Validate structure with frozen helpers, then resolve every exact short anchor."""
    try:
        return _build(source, _read(ContextualFrameInput, input))
    except Exception:
        raise ContextualFrameError("Invalid contextual frame input") from None


def validate_contextual_frame(
    source: Source, result: ContextualNumericFrame | dict[str, Any]
) -> ContextualNumericFrame:
    """Reconstruct the complete wrapper from its input against the current source."""
    try:
        checked = _read(ContextualNumericFrame, result)
        expected = _build(source, checked.input)
        if checked != expected:
            raise ValueError("Contextual frame differs from current reconstruction")
        return expected
    except Exception:
        raise ContextualFrameError("Invalid contextual frame") from None
