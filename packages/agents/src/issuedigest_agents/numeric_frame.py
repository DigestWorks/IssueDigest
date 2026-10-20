"""Pure, unreviewed numeric roles with exact source reconstruction, never truth certification."""

from typing import Any, Literal, Self

from pydantic import Field, model_validator

from .numeric_candidates import NumericCandidateIndex, build_numeric_candidates
from .numeric_evidence import Source, _source_data, _StrictModel
from .numeric_selection import (
    FactKind,
    ProposedRelation,
    ResolvedAnchor,
    ResolvedFact,
    ResolvedRelation,
    SentenceAnchor,
    _anchor,
    _ProviderOutput,
    _resolve_anchor,
    _resolve_relations,
)
from .numeric_selection_evaluation import _canonical_models, _read


class NumericFrameError(ValueError):
    """Sanitized failure of the entire frame operation without source or validation detail."""


type ReportingTense = Literal["past", "present", "future", "unknown"]


class _FrameFact[Anchor: SentenceAnchor | ResolvedAnchor](_StrictModel):
    candidate_id: str
    measured_entity: Anchor | None
    reporting_actor: Anchor | None
    period: Anchor | None
    logical_condition: Anchor | None
    forecast_basis: Anchor | None
    comparison_baseline: Anchor | None
    value_status: FactKind
    status_text: Anchor | None
    reporting_tense: ReportingTense
    reporting_tense_text: Anchor | None

    @model_validator(mode="after")
    def explicit_status_and_tense(self) -> Self:
        if self.value_status != "unknown" and self.status_text is None:
            raise ValueError("Known value status requires explicit text")
        if self.reporting_tense != "unknown" and self.reporting_tense_text is None:
            raise ValueError("Known reporting tense requires explicit text")
        return self


class FrameFactInput(_FrameFact[SentenceAnchor]):
    """One selected candidate with separate, required nullable source role anchors."""


class FrameRelationInput(ProposedRelation):
    """An explicit directed relation between two selected measured entities."""


class NumericFrameInput(_StrictModel):
    facts: tuple[FrameFactInput, ...] = Field(max_length=12)
    relations: tuple[FrameRelationInput, ...] = Field(max_length=16)


class _ResolvedFrameFact(_FrameFact[ResolvedAnchor]):
    pass


class NumericEvidenceFrame(_StrictModel):
    """A reconstructable structural result; callers separately check current authorization."""

    profile: Literal["numeric-evidence-frame-v1"] = "numeric-evidence-frame-v1"
    status: Literal["unreviewed"] = "unreviewed"
    candidate_index: NumericCandidateIndex
    facts: tuple[_ResolvedFrameFact, ...] = Field(max_length=12)
    relations: tuple[ResolvedRelation, ...] = Field(max_length=16)


_ANCHORS = (
    "measured_entity",
    "reporting_actor",
    "period",
    "logical_condition",
    "forecast_basis",
    "comparison_baseline",
    "status_text",
    "reporting_tense_text",
)


def _build(source: Source, data: NumericFrameInput) -> NumericEvidenceFrame:
    _canonical_models(source, Source)
    _source_data(source)
    index = build_numeric_candidates(source)
    candidates = {candidate.candidate_id: candidate for candidate in index.candidates}
    seen: set[str] = set()
    facts: list[_ResolvedFrameFact] = []
    for fact in data.facts:
        candidate = candidates[fact.candidate_id]
        if fact.candidate_id in seen:
            raise ValueError("Duplicate selected candidate")
        seen.add(fact.candidate_id)
        anchors: dict[str, ResolvedAnchor | None] = {}
        for name in _ANCHORS:
            anchor = getattr(fact, name)
            resolved = _resolve_anchor(index, anchor) if anchor is not None else None
            if (
                resolved is not None
                and resolved.span.citation_id != candidate.expression.citation_id
            ):
                raise ValueError("Anchor must share candidate quote")
            anchors[name] = resolved
        facts.append(
            _ResolvedFrameFact.model_validate(
                {
                    "candidate_id": fact.candidate_id,
                    "value_status": fact.value_status,
                    "reporting_tense": fact.reporting_tense,
                    **anchors,
                },
                strict=True,
            )
        )
    # The existing pure relation resolver checks subjects as measured entities only.
    # This temporary adapter never changes or merges roles in the resulting frame.
    endpoints = tuple(
        ResolvedFact(
            candidate_id=fact.candidate_id,
            subject=fact.measured_entity,
            period=None,
            condition=None,
            kind="unknown",
            status_text=None,
        )
        for fact in facts
    )
    relations = _ProviderOutput(
        facts=(),
        relations=tuple(ProposedRelation(**relation.model_dump()) for relation in data.relations),
    )
    return NumericEvidenceFrame(
        candidate_index=index,
        facts=tuple(facts),
        relations=_resolve_relations(index, relations, endpoints),
    )


def build_numeric_frame(
    source: Source, input: NumericFrameInput | dict[str, Any]
) -> NumericEvidenceFrame:
    """Resolve all roles from current source or reject the entire input without I/O or repair."""
    try:
        return _build(source, _read(NumericFrameInput, input))
    except Exception:
        raise NumericFrameError("Invalid numeric frame input") from None


def validate_numeric_frame(
    source: Source, frame: NumericEvidenceFrame | dict[str, Any]
) -> NumericEvidenceFrame:
    """Strictly rebuild every output field; structural validity does not certify semantics."""
    try:
        checked = _read(NumericEvidenceFrame, frame)
        data = {
            "facts": [
                {
                    "candidate_id": fact.candidate_id,
                    "value_status": fact.value_status,
                    "reporting_tense": fact.reporting_tense,
                    **{name: _anchor(getattr(fact, name)) for name in _ANCHORS},
                }
                for fact in checked.facts
            ],
            "relations": [
                {
                    "kind": relation.kind,
                    "from_id": relation.from_id,
                    "to_id": relation.to_id,
                    "statement_sentence_ids": relation.statement_sentence_ids,
                    "cue": _anchor(relation.cue),
                }
                for relation in checked.relations
            ],
        }
        expected = build_numeric_frame(source, data)
        if expected != checked:
            raise ValueError("Frame differs from current source reconstruction")
        return expected
    except Exception:
        raise NumericFrameError("Invalid numeric frame") from None
