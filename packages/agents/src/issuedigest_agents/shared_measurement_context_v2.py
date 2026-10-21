"""Pure v2 shared roles over complete quantities; linkage never certifies meaning or access."""

from typing import Any, Literal, cast

from pydantic import BaseModel, Field

from .contextual_anchor import ContextualAnchor
from .measurement_scope import ResolvedMeasurementScope
from .numeric_candidates import ExactSpan, NumericCandidateIndex
from .numeric_candidates_v2 import NumericCandidateIndexV2, build_numeric_candidates_v2
from .numeric_evidence import Source, _StrictModel
from .numeric_frame import _ResolvedFrameFact
from .numeric_selection import (
    ProposedRelation,
    ResolvedAnchor,
    ResolvedFact,
    ResolvedRelation,
    SentenceAnchor,
    _ProviderOutput,
    _resolve_anchor,
    _resolve_relations,
)
from .numeric_selection_evaluation import _canonical_models, _read
from .shared_measurement_context import (
    SharedId,
    SharedMeasurementContextError,
    SharedMeasurementInput,
    _actual_models,
)


class ResolvedSharedMeasurementFactV2(_ResolvedFrameFact):
    """All resolved roles and scopes, with purpose separate from condition and outlook basis."""

    context_id: SharedId
    reporting_event_id: SharedId
    target_scopes: tuple[ResolvedMeasurementScope, ...] = Field(max_length=4)
    purpose: ResolvedAnchor | None


class SharedMeasurementFrameV2(_StrictModel):
    """Flat reconstructable v2 result preserving its original explicit shared input."""

    profile: Literal["shared-measurement-context-v2"] = "shared-measurement-context-v2"
    status: Literal["unreviewed"] = "unreviewed"
    input: SharedMeasurementInput
    candidate_index: NumericCandidateIndexV2
    facts: tuple[ResolvedSharedMeasurementFactV2, ...] = Field(max_length=12)
    relations: tuple[ResolvedRelation, ...] = Field(max_length=16)


def _broad(index: NumericCandidateIndexV2, anchor: ContextualAnchor) -> ResolvedAnchor:
    # These frozen helpers read only common sentence/candidate structural fields.
    # The cast is static: the complete v2 index is neither converted nor rebuilt as v1.
    return _resolve_anchor(
        cast(NumericCandidateIndex, index),
        SentenceAnchor(
            sentence_id=anchor.sentence_id,
            text=anchor.context_text if anchor.context_text is not None else anchor.text,
        ),
    )


def _resolve(index: NumericCandidateIndexV2, anchor: ContextualAnchor) -> ResolvedAnchor:
    context = _broad(index, anchor)
    offset = context.span.text.find(anchor.text)
    if offset < 0 or context.span.text.find(anchor.text, offset + 1) >= 0:
        raise ValueError("Phrase must occur exactly once inside context")
    start = context.span.start + offset
    return ResolvedAnchor(
        sentence_id=anchor.sentence_id,
        span=ExactSpan(
            citation_id=context.span.citation_id,
            text=anchor.text,
            start=start,
            end=start + len(anchor.text),
        ),
    )


def _build(source: Source, data: SharedMeasurementInput) -> SharedMeasurementFrameV2:
    index = build_numeric_candidates_v2(source)
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
    facts: list[ResolvedSharedMeasurementFactV2] = []
    endpoints: list[ResolvedFact] = []
    for binding in data.bindings:
        context = contexts[binding.context_id]
        event = events[context.reporting_event_id]
        candidate = candidates[binding.candidate_id]
        anchors: dict[str, ResolvedAnchor | None] = {}
        for name, anchor in (
            ("measured_entity", context.measured_variable),
            ("reporting_actor", event.reporting_actor),
            ("period", context.period),
            ("logical_condition", context.logical_condition),
            ("purpose", context.purpose),
            ("forecast_basis", context.forecast_basis),
            ("comparison_baseline", context.comparison_baseline),
            ("reporting_tense_text", event.predicate),
        ):
            resolved = _resolve(index, anchor) if anchor is not None else None
            if (
                resolved is not None
                and resolved.span.citation_id != candidate.expression.citation_id
            ):
                raise ValueError("Role outside candidate quote")
            anchors[name] = resolved
        status = None
        if binding.status_evidence_sentence_id is not None:
            sentence = sentences[binding.status_evidence_sentence_id]
            if (
                sentence.sentence_id not in candidate.sentence_ids
                or sentence.span.citation_id != candidate.expression.citation_id
            ):
                raise ValueError("Wrong candidate status sentence")
            # Enforce the same exact, nonblank 1..1000 code point anchor limit as v1.
            status = _resolve(
                index,
                ContextualAnchor(
                    sentence_id=sentence.sentence_id, text=sentence.span.text, context_text=None
                ),
            )
        scopes: list[ResolvedMeasurementScope] = []
        seen: set[ResolvedAnchor] = set()
        for scope in context.target_scopes + binding.target_scopes:
            resolved = _resolve(index, scope.anchor)
            if resolved.span.citation_id != candidate.expression.citation_id or resolved in seen:
                raise ValueError("Scope outside candidate quote or duplicate location")
            seen.add(resolved)
            scopes.append(ResolvedMeasurementScope(kind=scope.kind, anchor=resolved))
        facts.append(
            ResolvedSharedMeasurementFactV2(
                candidate_id=binding.candidate_id,
                context_id=context.context_id,
                reporting_event_id=event.event_id,
                value_status=context.value_status,
                reporting_tense=event.reporting_tense,
                status_text=status,
                target_scopes=tuple(scopes),
                **anchors,
            )
        )
        # Whole explicit contexts must pass statement containment before short roles
        # are stored, matching the frozen contextual frame's structural policy.
        endpoints.append(
            ResolvedFact(
                candidate_id=binding.candidate_id,
                subject=_broad(index, context.measured_variable)
                if context.measured_variable is not None
                else None,
                period=None,
                condition=None,
                kind="unknown",
                status_text=None,
            )
        )
    relations = _resolve_relations(
        cast(NumericCandidateIndex, index),
        _ProviderOutput(
            facts=(),
            relations=tuple(
                ProposedRelation(
                    kind=relation.kind,
                    from_id=relation.from_id,
                    to_id=relation.to_id,
                    statement_sentence_ids=relation.statement_sentence_ids,
                    cue=SentenceAnchor(
                        sentence_id=relation.cue.sentence_id,
                        text=relation.cue.context_text
                        if relation.cue.context_text is not None
                        else relation.cue.text,
                    ),
                )
                for relation in data.relations
            ),
        ),
        tuple(endpoints),
    )
    short_relations = tuple(
        relation.model_copy(update={"cue": _resolve(index, original.cue)})
        for original, relation in zip(data.relations, relations, strict=True)
    )
    return SharedMeasurementFrameV2(
        input=data, candidate_index=index, facts=tuple(facts), relations=short_relations
    )


def build_shared_measurement_frame_v2(
    source: Source, input: SharedMeasurementInput | dict[str, Any]
) -> SharedMeasurementFrameV2:
    """Resolve explicit shared records against the full v2 source index without I/O or repair."""
    try:
        _canonical_models(source, Source)
        _actual_models(source, Source)
        _canonical_models(input, SharedMeasurementInput)
        if isinstance(input, BaseModel):
            _actual_models(input, SharedMeasurementInput)
        return _build(source, _read(SharedMeasurementInput, input))
    except Exception:
        raise SharedMeasurementContextError("Invalid shared measurement v2 input") from None


def validate_shared_measurement_frame_v2(
    source: Source, result: SharedMeasurementFrameV2 | dict[str, Any]
) -> SharedMeasurementFrameV2:
    """Rebuild every index entry and role from current source; reject the whole altered result."""
    try:
        _canonical_models(source, Source)
        _actual_models(source, Source)
        _canonical_models(result, SharedMeasurementFrameV2)
        if isinstance(result, BaseModel):
            _actual_models(result, SharedMeasurementFrameV2)
        checked = _read(SharedMeasurementFrameV2, result)
        expected = _build(source, checked.input)
        if checked != expected:
            raise ValueError("Shared v2 frame differs from current source reconstruction")
        return expected
    except Exception:
        raise SharedMeasurementContextError("Invalid shared measurement v2 frame") from None
