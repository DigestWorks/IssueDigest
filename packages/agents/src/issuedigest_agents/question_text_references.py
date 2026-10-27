"""Pure unique text references; no execution integration or semantic approval."""

from typing import Annotated, Any, Literal

from pydantic import Field, TypeAdapter

from . import question_evidence_propositions as canonical
from .numeric_evidence import Source, _StrictModel
from .numeric_selection_evaluation import _read
from .question_evidence_propositions import (
    FacetId,
    PropositionId,
    QuestionEvidenceError,
    QuestionEvidencePropositions,
    _guard_actual,
    _original,
    _question,
    _source,
)


class EvidenceRef(_StrictModel):
    citation_id: str
    text: str


Refs = Annotated[tuple[EvidenceRef, ...], Field(max_length=8)]


class QuantityValue(_StrictModel):
    expression: EvidenceRef
    metric_refs: Refs


class BoundValue(_StrictModel):
    operator: Literal["eq", "gte", "gt", "lte", "lt", "unknown"]


class DistributionValue(_StrictModel):
    mode: Literal["per_member", "collective", "unknown"]
    member_refs: Refs


class TimeValue(_StrictModel):
    kind: Literal["deadline", "target", "period", "relative", "unknown"]
    literal_ref: EvidenceRef
    anchor_refs: Refs


class LiteralValue(_StrictModel):
    literal_ref: EvidenceRef


class LegalEffectValue(_StrictModel):
    polarity: Literal["affirmed", "negated", "unknown"]
    literal_ref: EvidenceRef


class ProcedureValue(_StrictModel):
    state: Literal["planned", "observed", "conditional", "unknown"]
    literal_ref: EvidenceRef


class _Facet(_StrictModel):
    id: FacetId
    refs: Annotated[Refs, Field(min_length=1)]
    target_ids: tuple[FacetId, ...] = Field(max_length=1)


class QuantityFacet(_Facet):
    kind: Literal["quantity"]
    value: QuantityValue


class BoundFacet(_Facet):
    kind: Literal["bound"]
    value: BoundValue


class DistributionFacet(_Facet):
    kind: Literal["distribution"]
    value: DistributionValue


class TimeFacet(_Facet):
    kind: Literal["time"]
    value: TimeValue


class EligibilityFacet(_Facet):
    kind: Literal["eligibility"]
    value: LiteralValue


class PrerequisiteFacet(_Facet):
    kind: Literal["prerequisite"]
    value: LiteralValue


class LegalEffectFacet(_Facet):
    kind: Literal["legal_effect"]
    value: LegalEffectValue


class ProcedureFacet(_Facet):
    kind: Literal["procedure"]
    value: ProcedureValue


EvidenceFacet = Annotated[
    QuantityFacet
    | BoundFacet
    | DistributionFacet
    | TimeFacet
    | EligibilityFacet
    | PrerequisiteFacet
    | LegalEffectFacet
    | ProcedureFacet,
    Field(discriminator="kind"),
]


class EvidenceProposition(_StrictModel):
    id: PropositionId
    epistemic_status: Literal["source_statement", "uncertain"]
    supporting_refs: Annotated[Refs, Field(min_length=1)]
    subject_refs: Refs
    predicate_refs: Refs
    facets: tuple[EvidenceFacet, ...] = Field(max_length=16)
    depends_on_ids: tuple[PropositionId, ...] = Field(max_length=8)


class QuestionCoverage(_StrictModel):
    linked_proposition_ids: tuple[PropositionId, ...] = Field(max_length=24)
    unresolved_reason: Literal["no_linked_evidence", "ambiguous", "insufficient"] | None


class QuestionEvidenceTextInput(_StrictModel):
    propositions: tuple[EvidenceProposition, ...] = Field(max_length=24)
    coverage: QuestionCoverage


def _resolve(ref: EvidenceRef, quotes: dict[str, str]) -> canonical.EvidenceRef:
    if not ref.citation_id.strip() or not ref.text.strip():
        raise ValueError("Blank reference")
    ref.citation_id.encode("utf-8")
    ref.text.encode("utf-8")
    quote = quotes[ref.citation_id]
    start = quote.find(ref.text)
    if start < 0 or quote.find(ref.text, start + 1) >= 0:
        raise ValueError("Expected exactly one occurrence")
    return canonical.EvidenceRef(
        citation_id=ref.citation_id, text=ref.text, start=start, end=start + len(ref.text)
    )


def _refs(
    refs: tuple[EvidenceRef, ...], quotes: dict[str, str]
) -> tuple[canonical.EvidenceRef, ...]:
    return tuple(_resolve(ref, quotes) for ref in refs)


def _facet(facet: EvidenceFacet, quotes: dict[str, str]) -> canonical.EvidenceFacet:
    value = facet.value
    fields: dict[str, Any]
    if isinstance(value, QuantityValue):
        fields = dict(
            expression=_resolve(value.expression, quotes),
            metric_refs=_refs(value.metric_refs, quotes),
        )
    elif isinstance(value, BoundValue):
        fields = dict(operator=value.operator)
    elif isinstance(value, DistributionValue):
        fields = dict(mode=value.mode, member_refs=_refs(value.member_refs, quotes))
    elif isinstance(value, TimeValue):
        fields = dict(
            kind=value.kind,
            literal_ref=_resolve(value.literal_ref, quotes),
            anchor_refs=_refs(value.anchor_refs, quotes),
        )
    elif isinstance(value, LegalEffectValue):
        fields = dict(polarity=value.polarity, literal_ref=_resolve(value.literal_ref, quotes))
    elif isinstance(value, ProcedureValue):
        fields = dict(state=value.state, literal_ref=_resolve(value.literal_ref, quotes))
    else:
        fields = dict(literal_ref=_resolve(value.literal_ref, quotes))
    return TypeAdapter(canonical.EvidenceFacet).validate_python(
        dict(
            id=facet.id,
            kind=facet.kind,
            value=fields,
            refs=_refs(facet.refs, quotes),
            target_ids=facet.target_ids,
        ),
        strict=True,
    )


def build_question_text_evidence(
    source: Source, question: str, data: QuestionEvidenceTextInput | dict[str, Any]
) -> QuestionEvidencePropositions:
    """Resolve exact unique spans and delegate existing contract checks to the existing builder."""
    try:
        _guard_actual(source, Source)
        _original(data, QuestionEvidenceTextInput)
        _question(question)
        source_hash, quotes = _source(source)
        checked = _read(QuestionEvidenceTextInput, data)
        propositions = tuple(
            canonical.EvidenceProposition(
                id=p.id,
                epistemic_status=p.epistemic_status,
                supporting_refs=_refs(p.supporting_refs, quotes),
                subject_refs=_refs(p.subject_refs, quotes),
                predicate_refs=_refs(p.predicate_refs, quotes),
                facets=tuple(_facet(f, quotes) for f in p.facets),
                depends_on_ids=p.depends_on_ids,
            )
            for p in checked.propositions
        )
        result = canonical.build_question_evidence_propositions(
            source,
            question,
            canonical.QuestionEvidenceInput(
                propositions=propositions,
                coverage=canonical.QuestionCoverage(
                    linked_proposition_ids=checked.coverage.linked_proposition_ids,
                    unresolved_reason=checked.coverage.unresolved_reason,
                ),
            ),
        )
        if result.source_sha256 != source_hash or _source(source)[0] != source_hash:
            raise ValueError("Source changed")
        return result
    except Exception:
        raise QuestionEvidenceError() from None
