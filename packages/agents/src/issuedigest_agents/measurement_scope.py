"""Pure measurement scopes; exact linkage never certifies roles, truth or access."""

from typing import Any, Literal

from pydantic import Field

from .contextual_anchor import ContextualAnchor, resolve_contextual_anchor
from .contextual_frame import (
    ContextualFrameFactInput,
    ContextualFrameInput,
    ContextualFrameRelationInput,
    ContextualNumericFrame,
    build_contextual_frame,
)
from .numeric_evidence import Source, _source_data, _StrictModel
from .numeric_selection import ResolvedAnchor
from .numeric_selection_evaluation import _canonical_models, _read

type ScopeKind = Literal["geographic", "population", "institutional", "other"]


class MeasurementScopeError(ValueError):
    """Sanitized failure of the whole operation without source or validation details."""


class MeasurementScopeInput(_StrictModel):
    kind: ScopeKind
    anchor: ContextualAnchor


class MeasurementFactInput(ContextualFrameFactInput):
    target_scopes: tuple[MeasurementScopeInput, ...] = Field(max_length=4)


class MeasurementFrameInput(_StrictModel):
    facts: tuple[MeasurementFactInput, ...] = Field(max_length=12)
    relations: tuple[ContextualFrameRelationInput, ...] = Field(max_length=16)


class ResolvedMeasurementScope(_StrictModel):
    kind: ScopeKind
    anchor: ResolvedAnchor


class ResolvedMeasurementFact(_StrictModel):
    candidate_id: str
    target_scopes: tuple[ResolvedMeasurementScope, ...] = Field(max_length=4)


class MeasurementScopeFrame(_StrictModel):
    """Stored input reconstructs roles and scopes; status is never semantic approval."""

    profile: Literal["measurement-scope-frame-v1"] = "measurement-scope-frame-v1"
    status: Literal["unreviewed"] = "unreviewed"
    input: MeasurementFrameInput
    frame: ContextualNumericFrame
    scopes: tuple[ResolvedMeasurementFact, ...] = Field(max_length=12)


def _build(source: Source, data: MeasurementFrameInput) -> MeasurementScopeFrame:
    # Public preflight has checked actual declared types before this narrowing.
    base = ContextualFrameInput.model_validate_json(
        data.model_dump_json(exclude={"facts": {"__all__": {"target_scopes"}}}), strict=True
    )
    frame = build_contextual_frame(source, base)
    candidates = {
        candidate.candidate_id: candidate for candidate in frame.resolved.candidate_index.candidates
    }
    scopes: list[ResolvedMeasurementFact] = []
    for fact in data.facts:
        citation_id = candidates[fact.candidate_id].expression.citation_id
        resolved_scopes: list[ResolvedMeasurementScope] = []
        seen: set[ResolvedAnchor] = set()
        for scope in fact.target_scopes:
            resolved = resolve_contextual_anchor(source, scope.anchor).resolved
            if resolved.span.citation_id != citation_id or resolved in seen:
                raise ValueError("Scope outside candidate quote or duplicate location")
            seen.add(resolved)
            resolved_scopes.append(ResolvedMeasurementScope(kind=scope.kind, anchor=resolved))
        scopes.append(
            ResolvedMeasurementFact(
                candidate_id=fact.candidate_id, target_scopes=tuple(resolved_scopes)
            )
        )
    return MeasurementScopeFrame(input=data, frame=frame, scopes=tuple(scopes))


def build_measurement_scope_frame(
    source: Source, input: MeasurementFrameInput | dict[str, Any]
) -> MeasurementScopeFrame:
    """Validate canonical inputs, reuse exact contextual linkage and return no partial output."""
    try:
        _canonical_models(source, Source)
        _canonical_models(input, MeasurementFrameInput)
        _source_data(source)
        return _build(source, _read(MeasurementFrameInput, input))
    except Exception:
        raise MeasurementScopeError("Invalid measurement scope input") from None


def validate_measurement_scope_frame(
    source: Source, result: MeasurementScopeFrame | dict[str, Any]
) -> MeasurementScopeFrame:
    """Rebuild the entire stored wrapper against current source and compare every field."""
    try:
        _canonical_models(source, Source)
        _canonical_models(result, MeasurementScopeFrame)
        _source_data(source)
        checked = _read(MeasurementScopeFrame, result)
        expected = _build(source, checked.input)
        if checked != expected:
            raise ValueError("Measurement scopes differ from current source reconstruction")
        return expected
    except Exception:
        raise MeasurementScopeError("Invalid measurement scope frame") from None
