"""Exact object-specific role aliases and explicit, unreviewed quantity directions."""

from typing import Annotated, Any, Literal, TypeAliasType, cast

from pydantic import BaseModel, ConfigDict, Field, create_model, field_validator

from .contextual_anchor import ContextualAnchor
from .measurement_frame_generation import _eligible
from .measurement_scope import ScopeKind
from .numeric_candidates import ExactSpan, NumericCandidateIndex
from .numeric_candidates_v2 import NumericCandidateIndexV2, build_numeric_candidates_v2
from .numeric_evidence import Source, _StrictModel
from .numeric_frame import ReportingTense
from .numeric_selection import FactKind, ResolvedAnchor, _inside
from .numeric_selection_evaluation import _canonical_models, _read
from .shared_context_generation import CONTEXT_ID_SLOTS, REPORTING_EVENT_ID_SLOTS, _frame_tools
from .shared_measurement_context import SharedId, SharedMeasurementInput, _actual_models
from .shared_measurement_context_v2 import (
    SharedMeasurementFrameV2,
    _broad,
    _resolve,
    build_shared_measurement_frame_v2,
)


class RoleAliasContractError(ValueError):
    """Sanitized whole-operation rejection without source or partial output."""


class _WireModel(_StrictModel):
    # Only the reserved Python word `from` needs an alias. Its internal from_ name
    # must never become a second accepted provider/stored spelling.
    model_config = ConfigDict(validate_by_name=False, serialize_by_alias=True)


class RoleAliasAnchor(_WireModel):
    s: Annotated[str, Field(min_length=1, max_length=1000)]
    t: Annotated[str, Field(min_length=1, max_length=1000)]
    c: Annotated[str, Field(min_length=1, max_length=1000)] | None

    @field_validator("t", "c")
    @classmethod
    def nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Blank exact anchor")
        return value


class RoleAliasScope(_WireModel):
    kind: ScopeKind
    anchor: RoleAliasAnchor


class RoleAliasContext(_WireModel):
    id: SharedId
    event: SharedId
    entity: RoleAliasAnchor | None
    scopes: tuple[RoleAliasScope, ...] = Field(max_length=4)
    period: RoleAliasAnchor | None
    status: FactKind
    condition: RoleAliasAnchor | None
    purpose: RoleAliasAnchor | None
    basis: RoleAliasAnchor | None
    baseline: RoleAliasAnchor | None


class RoleAliasEvent(_WireModel):
    id: SharedId
    kind: Literal["attributed_report", "narration", "unknown"]
    actor: RoleAliasAnchor | None
    predicate: RoleAliasAnchor | None
    tense: ReportingTense


class RoleAliasChange(_WireModel):
    direction: Literal["increase", "decrease", "unchanged", "uncertain"]
    evidence: RoleAliasAnchor | None
    support: tuple[str, ...] = Field(min_length=1, max_length=20)


class RoleAliasBinding(_WireModel):
    number: SharedId
    context: SharedId
    scopes: tuple[RoleAliasScope, ...] = Field(max_length=4)
    status_sentence: Annotated[str, Field(min_length=1, max_length=1000)] | None
    change: RoleAliasChange | None


class RoleAliasRelation(_WireModel):
    kind: Literal["included_in", "parallel", "unknown"]
    from_: SharedId = Field(alias="from")
    to: SharedId
    support: tuple[str, ...] = Field(min_length=1, max_length=20)
    cue: RoleAliasAnchor


class RoleAliasInput(_WireModel):
    contexts: tuple[RoleAliasContext, ...] = Field(max_length=12)
    events: tuple[RoleAliasEvent, ...] = Field(max_length=12)
    bindings: tuple[RoleAliasBinding, ...] = Field(max_length=12)
    relations: tuple[RoleAliasRelation, ...] = Field(max_length=16)


class ResolvedRoleChange(_StrictModel):
    direction: Literal["increase", "decrease", "unchanged", "uncertain"]
    evidence: ResolvedAnchor | None
    support: tuple[str, ...] = Field(min_length=1, max_length=20)
    statement: ExactSpan


class RoleChangeBinding(_StrictModel):
    candidate_id: SharedId
    change: ResolvedRoleChange | None


class RoleAliasFrame(_StrictModel):
    """Original explicit aliases and full frozen v2 reconstruction; no semantic approval."""

    profile: Literal["role-alias-frame-v1"]
    status: Literal["unreviewed"]
    input: RoleAliasInput
    frame: SharedMeasurementFrameV2
    changes: tuple[RoleChangeBinding, ...] = Field(max_length=12)


def _guard(value: Any, annotation: Any) -> None:
    _canonical_models(value, annotation)
    if isinstance(value, BaseModel) or isinstance(value, tuple):
        _actual_models(value, annotation)


def _anchor(value: RoleAliasAnchor | None) -> dict[str, Any] | None:
    return None if value is None else dict(sentence_id=value.s, text=value.t, context_text=value.c)


def _decode_shared_input(data: RoleAliasInput) -> SharedMeasurementInput:
    def scopes(rows: tuple[RoleAliasScope, ...]) -> list[dict[str, Any]]:
        return [dict(kind=row.kind, anchor=_anchor(row.anchor)) for row in rows]

    return _read(
        SharedMeasurementInput,
        dict(
            contexts=[
                dict(
                    context_id=c.id,
                    reporting_event_id=c.event,
                    measured_variable=_anchor(c.entity),
                    target_scopes=scopes(c.scopes),
                    period=_anchor(c.period),
                    value_status=c.status,
                    logical_condition=_anchor(c.condition),
                    purpose=_anchor(c.purpose),
                    forecast_basis=_anchor(c.basis),
                    comparison_baseline=_anchor(c.baseline),
                )
                for c in data.contexts
            ],
            events=[
                dict(
                    event_id=e.id,
                    kind=e.kind,
                    reporting_actor=_anchor(e.actor),
                    predicate=_anchor(e.predicate),
                    reporting_tense=e.tense,
                )
                for e in data.events
            ],
            bindings=[
                dict(
                    candidate_id=b.number,
                    context_id=b.context,
                    target_scopes=scopes(b.scopes),
                    status_evidence_sentence_id=b.status_sentence,
                )
                for b in data.bindings
            ],
            relations=[
                dict(
                    kind=r.kind,
                    from_id=r.from_,
                    to_id=r.to,
                    statement_sentence_ids=r.support,
                    cue=_anchor(r.cue),
                )
                for r in data.relations
            ],
        ),
    )


def _encode_shared_input(input: SharedMeasurementInput) -> dict[str, Any]:
    """Encode the actual original canonical input exactly; never invent a change field."""
    _guard(input, SharedMeasurementInput)
    if type(input) is not SharedMeasurementInput:
        raise ValueError("Expected actual shared input")
    data = _read(SharedMeasurementInput, input)

    def anchor(a: ContextualAnchor | None) -> dict[str, Any] | None:
        return None if a is None else dict(s=a.sentence_id, t=a.text, c=a.context_text)

    def scopes(rows: Any) -> list[dict[str, Any]]:
        return [dict(kind=s.kind, anchor=anchor(s.anchor)) for s in rows]

    return dict(
        contexts=[
            dict(
                id=c.context_id,
                event=c.reporting_event_id,
                entity=anchor(c.measured_variable),
                scopes=scopes(c.target_scopes),
                period=anchor(c.period),
                status=c.value_status,
                condition=anchor(c.logical_condition),
                purpose=anchor(c.purpose),
                basis=anchor(c.forecast_basis),
                baseline=anchor(c.comparison_baseline),
            )
            for c in data.contexts
        ],
        events=[
            dict(
                id=e.event_id,
                kind=e.kind,
                actor=anchor(e.reporting_actor),
                predicate=anchor(e.predicate),
                tense=e.reporting_tense,
            )
            for e in data.events
        ],
        bindings=[
            dict(
                number=b.candidate_id,
                context=b.context_id,
                scopes=scopes(b.target_scopes),
                status_sentence=b.status_evidence_sentence_id,
            )
            for b in data.bindings
        ],
        relations=[
            dict(
                kind=r.kind,
                **{"from": r.from_id},
                to=r.to_id,
                support=list(r.statement_sentence_ids),
                cue=anchor(r.cue),
            )
            for r in data.relations
        ],
    )


def _input_model(index: NumericCandidateIndexV2) -> type[BaseModel]:
    """Current strict DTO with object-local aliases and exact dynamic catalogs."""
    if not index.candidates or not index.sentences:
        raise ValueError("No numeric candidates")
    number: Any = TypeAliasType(
        "RoleNumberV1", Literal[tuple(c.candidate_id for c in index.candidates)]
    )
    sentence: Any = TypeAliasType(
        "RoleSentenceV1", Literal[tuple(s.sentence_id for s in index.sentences)]
    )
    context_id: Any = TypeAliasType("RoleContextIdV1", Literal[CONTEXT_ID_SLOTS])
    event_id: Any = TypeAliasType("RoleEventIdV1", Literal[REPORTING_EVENT_ID_SLOTS])
    structural = cast(NumericCandidateIndex, index)
    eligible = _eligible(structural)
    status_sentence: Any = (
        TypeAliasType("RoleStatusSentenceV1", Literal[eligible]) if eligible else type(None)
    )
    anchor = create_model("RoleAnchorV1", __base__=RoleAliasAnchor, s=(sentence, ...))
    scope = create_model("RoleScopeV1", __base__=RoleAliasScope, anchor=(anchor, ...))
    context_fields: dict[str, Any] = dict(
        id=(context_id, ...),
        event=(event_id, ...),
        scopes=(tuple[scope, ...], Field(max_length=4)),  # type: ignore[valid-type]
        **{
            role: (anchor | None, ...)
            for role in ("entity", "period", "condition", "purpose", "basis", "baseline")
        },
    )
    if not eligible:
        context_fields["status"] = (Literal["unknown"], ...)
    context = create_model("RoleContextV1", __base__=RoleAliasContext, **context_fields)
    events: list[type[BaseModel]] = []
    for kind in ("attributed_report", "narration", "unknown"):
        fields: dict[str, Any] = dict(
            id=(event_id, ...),
            kind=(Literal[kind], ...),
            actor=(anchor if kind == "attributed_report" else type(None), ...),
            predicate=(type(None) if kind == "unknown" else anchor, ...),
        )
        if kind == "unknown":
            fields["tense"] = (Literal["unknown"], ...)
        events.append(
            create_model(
                f"RoleEvent{kind.title().replace('_', '')}V1", __base__=RoleAliasEvent, **fields
            )
        )
    event: Any = events[0] | events[1] | events[2]
    nullable_anchor: Any = anchor | None
    change = create_model(
        "RoleChangeV1",
        __base__=RoleAliasChange,
        evidence=(nullable_anchor, ...),
        support=(tuple[sentence, ...], Field(min_length=1, max_length=20)),
    )
    nullable_change: Any = change | None
    binding = create_model(
        "RoleBindingV1",
        __base__=RoleAliasBinding,
        number=(number, ...),
        context=(context_id, ...),
        scopes=(tuple[scope, ...], Field(max_length=4)),  # type: ignore[valid-type]
        status_sentence=(status_sentence | None if eligible else type(None), ...),
        change=(nullable_change, ...),
    )
    relation = create_model(
        "RoleRelationV1",
        __base__=RoleAliasRelation,
        from_=(number, Field(alias="from")),
        to=(number, ...),
        cue=(anchor, ...),
        support=(tuple[sentence, ...], Field(min_length=1, max_length=20)),
    )
    return create_model(
        "RoleOutputV1",
        __base__=_WireModel,
        contexts=(tuple[context, ...], Field(max_length=12)),  # type: ignore[valid-type]
        events=(tuple[event, ...], Field(max_length=12)),
        bindings=(tuple[binding, ...], Field(max_length=12)),  # type: ignore[valid-type]
        relations=(tuple[relation, ...], Field(max_length=16)),  # type: ignore[valid-type]
    )


def _build(source: Source, data: RoleAliasInput) -> RoleAliasFrame:
    index = build_numeric_candidates_v2(source)
    if index.candidates:
        _input_model(index).model_validate_json(data.model_dump_json(), strict=True)
    elif any((data.contexts, data.events, data.bindings, data.relations)):
        raise ValueError("No numeric candidates")
    canonical = _decode_shared_input(data)
    if index.candidates:
        output_type = _frame_tools(cast(NumericCandidateIndex, index))[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        output_type.model_validate_json(canonical.model_dump_json(), strict=True)
    frame = build_shared_measurement_frame_v2(source, canonical)
    positions = {s.sentence_id: i for i, s in enumerate(index.sentences)}
    candidates = {c.candidate_id: c for c in index.candidates}
    quotes = {q.citation_id: q.quote for q in index.citations}
    changes: list[RoleChangeBinding] = []
    for binding in data.bindings:
        change = binding.change
        resolved = None
        if change is not None:
            if change.direction != "uncertain" and change.evidence is None:
                raise ValueError("Known direction requires exact evidence")
            ids = change.support
            start = positions[ids[0]]
            sentences = index.sentences[start : start + len(ids)]
            if tuple(s.sentence_id for s in sentences) != ids:
                raise ValueError("Support must be ordered contiguous current sentences")
            first, last = sentences[0].span, sentences[-1].span
            if any(s.span.citation_id != first.citation_id for s in sentences):
                raise ValueError("Support must share one quote")
            statement = ExactSpan(
                citation_id=first.citation_id,
                start=first.start,
                end=last.end,
                text=quotes[first.citation_id][first.start : last.end],
            )
            _inside(statement, candidates[binding.number].expression)
            evidence = None
            if change.evidence is not None:
                a = _read(ContextualAnchor, cast(dict[str, Any], _anchor(change.evidence)))
                if a.sentence_id not in ids:
                    raise ValueError("Evidence sentence outside support")
                _inside(statement, _broad(index, a).span)
                evidence = _resolve(index, a)
                _inside(statement, evidence.span)
            resolved = ResolvedRoleChange(
                direction=change.direction, evidence=evidence, support=ids, statement=statement
            )
        changes.append(RoleChangeBinding(candidate_id=binding.number, change=resolved))
    return RoleAliasFrame(
        profile="role-alias-frame-v1",
        status="unreviewed",
        input=data,
        frame=frame,
        changes=tuple(changes),
    )


def build_role_alias_frame(
    source: Source, input: RoleAliasInput | dict[str, Any]
) -> RoleAliasFrame:
    """Reconstruct full canonical v2 roles and explicit direction evidence without I/O."""
    try:
        _guard(source, Source)
        _guard(input, RoleAliasInput)
        return _build(source, _read(RoleAliasInput, input))
    except Exception:
        raise RoleAliasContractError("Invalid role alias input") from None


def _require_frame_markers(value: dict[str, Any]) -> None:
    for frame in (value, value["frame"]):
        if not {"profile", "status"} <= frame.keys():
            raise ValueError("Missing stored frame markers")


def validate_role_alias_frame(
    source: Source, result: RoleAliasFrame | dict[str, Any]
) -> RoleAliasFrame:
    """Rebuild all stored source, aliases, canonical roles, and directions exactly."""
    try:
        _guard(source, Source)
        _guard(result, RoleAliasFrame)
        if isinstance(result, dict):
            _require_frame_markers(result)
        checked = _read(RoleAliasFrame, result)
        expected = _build(source, checked.input)
        if checked != expected:
            raise ValueError("Stored role alias frame differs from reconstruction")
        return expected
    except Exception:
        raise RoleAliasContractError("Invalid role alias frame") from None
