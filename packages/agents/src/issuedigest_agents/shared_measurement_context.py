"""Pure shared measurement roles; exact linkage never certifies meaning or access."""

from typing import Annotated, Any, Literal, Self, get_args, get_origin

from pydantic import BaseModel, Field, model_validator

from .contextual_anchor import ContextualAnchor, resolve_contextual_anchor
from .contextual_frame import ContextualFrameRelationInput
from .measurement_scope import (
    MeasurementFactInput,
    MeasurementFrameInput,
    MeasurementScopeFrame,
    MeasurementScopeInput,
    build_measurement_scope_frame,
)
from .numeric_candidates import build_numeric_candidates
from .numeric_evidence import Source, _source_data, _StrictModel
from .numeric_frame import ReportingTense
from .numeric_selection import FactKind, ResolvedAnchor
from .numeric_selection_evaluation import _canonical_models, _model_types, _read

type SharedId = Annotated[str, Field(min_length=1, max_length=64, pattern=r"\A[A-Za-z0-9_-]+\z")]


class SharedMeasurementContextError(ValueError):
    """Sanitized whole-operation failure without source, validation details or partial output."""


class SharedMeasurementContext(_StrictModel):
    context_id: SharedId
    reporting_event_id: SharedId
    measured_variable: ContextualAnchor | None
    target_scopes: tuple[MeasurementScopeInput, ...] = Field(max_length=4)
    period: ContextualAnchor | None
    value_status: FactKind
    logical_condition: ContextualAnchor | None
    purpose: ContextualAnchor | None
    forecast_basis: ContextualAnchor | None
    comparison_baseline: ContextualAnchor | None


class SharedReportingEvent(_StrictModel):
    event_id: SharedId
    kind: Literal["attributed_report", "narration", "unknown"]
    reporting_actor: ContextualAnchor | None
    predicate: ContextualAnchor | None
    reporting_tense: ReportingTense

    @model_validator(mode="after")
    def explicit_reporting_roles(self) -> Self:
        if self.kind == "attributed_report":
            if self.reporting_actor is None or self.predicate is None:
                raise ValueError("Attributed report needs actor and predicate")
        elif self.kind == "narration":
            if self.reporting_actor is not None or self.predicate is None:
                raise ValueError("Narration needs predicate without actor")
        elif (
            self.reporting_actor is not None
            or self.predicate is not None
            or self.reporting_tense != "unknown"
        ):
            raise ValueError("Unknown event cannot assert reporting roles or tense")
        return self


class SharedNumericBinding(_StrictModel):
    candidate_id: SharedId
    context_id: SharedId
    target_scopes: tuple[MeasurementScopeInput, ...] = Field(max_length=4)
    status_evidence_sentence_id: Annotated[str, Field(min_length=1, max_length=1000)] | None


class SharedMeasurementInput(_StrictModel):
    contexts: tuple[SharedMeasurementContext, ...] = Field(max_length=12)
    events: tuple[SharedReportingEvent, ...] = Field(max_length=12)
    bindings: tuple[SharedNumericBinding, ...] = Field(max_length=12)
    relations: tuple[ContextualFrameRelationInput, ...] = Field(max_length=16)


class ResolvedSharedPurpose(_StrictModel):
    context_id: SharedId
    purpose: ResolvedAnchor | None


class SharedMeasurementFrame(_StrictModel):
    """Original shared input and all derived roles, with no semantic approval implied."""

    profile: Literal["shared-measurement-context-v1"] = "shared-measurement-context-v1"
    status: Literal["unreviewed"] = "unreviewed"
    input: SharedMeasurementInput
    frame: MeasurementScopeFrame
    purposes: tuple[ResolvedSharedPurpose, ...] = Field(max_length=12)


def _actual_models(value: Any, annotation: Any) -> None:
    # The existing canonical guard rejects subclasses/extras before any serialization.
    # Also reject dictionaries/lists installed into actual models by unchecked copies.
    if isinstance(value, BaseModel):
        for name, child in value.__dict__.items():
            _actual_models(child, type(value).model_fields[name].annotation)
    elif isinstance(value, (tuple, list)):
        if get_origin(annotation) is not tuple or type(value) is not tuple:
            raise ValueError("Expected actual tuple")
        args = get_args(annotation)
        for i, child in enumerate(value):
            _actual_models(child, args[0] if args[-1] is Ellipsis else args[i])
    elif value is not None and _model_types(annotation):
        raise ValueError("Expected actual nested model")


def _build(source: Source, data: SharedMeasurementInput) -> SharedMeasurementFrame:
    index = build_numeric_candidates(source)
    candidates = {candidate.candidate_id: candidate for candidate in index.candidates}
    sentences = {sentence.sentence_id: sentence for sentence in index.sentences}
    contexts = {context.context_id: context for context in data.contexts}
    events = {event.event_id: event for event in data.events}
    if len(contexts) != len(data.contexts) or len(events) != len(data.events):
        raise ValueError("Duplicate shared record ID")
    if {binding.context_id for binding in data.bindings} != contexts.keys():
        raise ValueError("Missing or unused context")
    if {context.reporting_event_id for context in data.contexts} != events.keys():
        raise ValueError("Missing or unused reporting event")
    if len({binding.candidate_id for binding in data.bindings}) != len(data.bindings):
        raise ValueError("Duplicate candidate binding")
    purposes = tuple(
        ResolvedSharedPurpose(
            context_id=context.context_id,
            purpose=resolve_contextual_anchor(source, context.purpose).resolved
            if context.purpose is not None
            else None,
        )
        for context in data.contexts
    )
    purpose_by_id = {purpose.context_id: purpose.purpose for purpose in purposes}
    facts: list[MeasurementFactInput] = []
    for binding in data.bindings:
        context = contexts[binding.context_id]
        event = events[context.reporting_event_id]
        candidate = candidates[binding.candidate_id]
        purpose = purpose_by_id[context.context_id]
        if purpose is not None and purpose.span.citation_id != candidate.expression.citation_id:
            raise ValueError("Purpose outside candidate quote")
        status_text = None
        if binding.status_evidence_sentence_id is not None:
            sentence = sentences[binding.status_evidence_sentence_id]
            if (
                sentence.sentence_id not in candidate.sentence_ids
                or sentence.span.citation_id != candidate.expression.citation_id
            ):
                raise ValueError("Wrong candidate status sentence")
            # ContextualAnchor enforces exact nonblank text of 1..1000 code points.
            status_text = ContextualAnchor(
                sentence_id=sentence.sentence_id, text=sentence.span.text, context_text=None
            )
        facts.append(
            MeasurementFactInput(
                candidate_id=binding.candidate_id,
                measured_entity=context.measured_variable,
                reporting_actor=event.reporting_actor,
                period=context.period,
                value_status=context.value_status,
                logical_condition=context.logical_condition,
                forecast_basis=context.forecast_basis,
                comparison_baseline=context.comparison_baseline,
                status_text=status_text,
                reporting_tense=event.reporting_tense,
                reporting_tense_text=event.predicate,
                target_scopes=context.target_scopes + binding.target_scopes,
            )
        )
    # Preserve every direct relation and reuse frozen statement/cue/reference/cycle checks.
    frame = build_measurement_scope_frame(
        source, MeasurementFrameInput(facts=tuple(facts), relations=data.relations)
    )
    return SharedMeasurementFrame(input=data, frame=frame, purposes=purposes)


def build_shared_measurement_frame(
    source: Source, input: SharedMeasurementInput | dict[str, Any]
) -> SharedMeasurementFrame:
    """Expand only explicitly selected shared records, or reject the entire canonical input."""
    try:
        _canonical_models(source, Source)
        _canonical_models(input, SharedMeasurementInput)
        _actual_models(source, Source)
        if isinstance(input, BaseModel):
            _actual_models(input, SharedMeasurementInput)
        _source_data(source)
        return _build(source, _read(SharedMeasurementInput, input))
    except Exception:
        raise SharedMeasurementContextError("Invalid shared measurement input") from None


def validate_shared_measurement_frame(
    source: Source, result: SharedMeasurementFrame | dict[str, Any]
) -> SharedMeasurementFrame:
    """Rebuild the entire wrapper from current source, including separately resolved purposes."""
    try:
        _canonical_models(source, Source)
        _canonical_models(result, SharedMeasurementFrame)
        _actual_models(source, Source)
        if isinstance(result, BaseModel):
            _actual_models(result, SharedMeasurementFrame)
        _source_data(source)
        checked = _read(SharedMeasurementFrame, result)
        expected = _build(source, checked.input)
        if checked != expected:
            raise ValueError("Shared frame differs from current source reconstruction")
        return expected
    except Exception:
        raise SharedMeasurementContextError("Invalid shared measurement frame") from None
