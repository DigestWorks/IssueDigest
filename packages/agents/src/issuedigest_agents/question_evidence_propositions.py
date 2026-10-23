"""Pure question-specific source structure; no semantic, access, or completeness approval."""

from hashlib import sha256
from typing import Annotated, Any, Literal

from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field

from .numeric_evidence import Source, _json, _source_data, _StrictModel
from .numeric_selection_evaluation import _read
from .role_link_catalog import _actual, _required_raw
from .role_table_packet import _copy_json

PropositionId = Annotated[str, Field(pattern=r"^p(?:[1-9]|1[0-9]|2[0-4])$")]
FacetId = Annotated[str, Field(pattern=r"^f(?:[1-9]|1[0-6])$")]


class QuestionEvidenceError(ValueError):
    """Sanitized whole-operation failure without input, partial result, or cause."""

    def __init__(self) -> None:
        super().__init__("Invalid question evidence propositions")


class EvidenceRef(_StrictModel):
    citation_id: str
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]
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


class QuestionEvidenceInput(_StrictModel):
    propositions: tuple[EvidenceProposition, ...] = Field(max_length=24)
    coverage: QuestionCoverage


class QuestionEvidencePropositions(_StrictModel):
    """Unreviewed structural/source consistency; hashes are not semantic approval."""

    profile: Literal["question-evidence-propositions-v1"]
    status: Literal["unreviewed"]
    question_sha256: Sha256
    source_sha256: Sha256
    propositions: tuple[EvidenceProposition, ...] = Field(max_length=24)
    coverage: QuestionCoverage


def _model_field_maps(value: Any) -> None:
    # Field-name equality in the frozen guard does not distinguish str subclasses;
    # inspect the original maps before extraction or serialization can erase them.
    if isinstance(value, BaseModel):
        fields = value.__dict__
        if type(fields) is not dict or any(type(key) is not str for key in fields):
            raise ValueError("Noncanonical original model field map")
        for child in fields.values():
            _model_field_maps(child)
    elif isinstance(value, (tuple, list)):
        for child in value:
            _model_field_maps(child)


def _guard_actual(value: Any, annotation: Any) -> None:
    _model_field_maps(value)
    _actual(value, annotation)


def _original(value: Any, model: type[BaseModel]) -> None:
    if isinstance(value, BaseModel):
        _guard_actual(value, model)
    else:
        _copy_json(value)
        _required_raw(value, model)


def _python_fields(value: Any) -> Any:
    # Source integrity must be checked before even a safe model dump. Preserve actual
    # scalars here; the original-type guard has already rejected unchecked coercions.
    if isinstance(value, BaseModel):
        return {name: _python_fields(child) for name, child in value.__dict__.items()}
    if type(value) is tuple:
        return tuple(_python_fields(child) for child in value)
    return value


def _source(source: Source) -> tuple[str, dict[str, str]]:
    _guard_actual(source, Source)
    sid, bundle, presentation = source
    if sid.version != 4 or sid != presentation.snapshot_id:
        raise ValueError("Invalid snapshot provenance")
    if bundle.document.workspace_id != presentation.workspace_id:
        raise ValueError("Invalid workspace provenance")
    EvidenceBundle.model_validate(_python_fields(bundle), strict=True)
    SourcePresentation.model_validate(_python_fields(presentation), strict=True)
    current = _source_data(source)
    canonical = dict(
        snapshot_id=str(sid),
        bundle=bundle.model_dump(mode="json"),
        presentation=presentation.model_dump(mode="json"),
    )
    digest = sha256(_json(canonical).encode("utf-8")).hexdigest()
    return digest, {c.citation_id: c.quote for c in current.citations}


def _question(question: str) -> str:
    if type(question) is not str or not 1 <= len(question) <= 2000 or not question.strip():
        raise ValueError("Invalid exact question")
    return sha256(question.encode("utf-8")).hexdigest()


def _refs(refs: tuple[EvidenceRef, ...], quotes: dict[str, str]) -> None:
    seen: set[tuple[str, int, int, str]] = set()
    for ref in refs:
        key = (ref.citation_id, ref.start, ref.end, ref.text)
        if key in seen:
            raise ValueError("Duplicate reference")
        seen.add(key)
        for text in (ref.citation_id, ref.text):
            if not text.strip():
                raise ValueError("Blank reference")
            text.encode("utf-8")
        quote = quotes[ref.citation_id]
        if not 0 <= ref.start < ref.end <= len(quote):
            raise ValueError("Invalid quote-relative range")
        if quote[ref.start : ref.end] != ref.text:
            raise ValueError("Reference differs from exact source")


def _contained(ref: EvidenceRef, support: tuple[EvidenceRef, ...]) -> bool:
    return any(
        ref.citation_id == outer.citation_id and outer.start <= ref.start < ref.end <= outer.end
        for outer in support
    )


def _ids(ids: tuple[str, ...], domain: set[str]) -> None:
    if len(set(ids)) != len(ids) or not set(ids) <= domain:
        raise ValueError("Duplicate or unknown local ID")


def _facet(facet: EvidenceFacet, quotes: dict[str, str]) -> bool:
    """Validate value references and return whether explicit uncertainty is required."""
    value = facet.value
    groups: tuple[tuple[EvidenceRef, ...], ...]
    uncertain = False
    if isinstance(value, QuantityValue):
        groups = ((value.expression,), value.metric_refs)
        uncertain = not value.metric_refs
    elif isinstance(value, DistributionValue):
        groups = (value.member_refs,)
        if value.mode != "unknown" and not value.member_refs:
            raise ValueError("Distribution requires explicit members")
    elif isinstance(value, TimeValue):
        groups = ((value.literal_ref,), value.anchor_refs)
        uncertain = value.kind == "relative" and not value.anchor_refs
    elif isinstance(value, (LiteralValue, LegalEffectValue, ProcedureValue)):
        groups = ((value.literal_ref,),)
    else:
        groups = ()
    for group in groups:
        _refs(group, quotes)
        if any(ref not in facet.refs for ref in group):
            raise ValueError("Value reference absent from facet references")
    return uncertain


def _check(
    propositions: tuple[EvidenceProposition, ...],
    coverage: QuestionCoverage,
    quotes: dict[str, str],
) -> None:
    proposition_ids = {p.id for p in propositions}
    if len(proposition_ids) != len(propositions):
        raise ValueError("Duplicate proposition ID")
    for proposition in propositions:
        _refs(proposition.supporting_refs, quotes)
        uncertain = not proposition.subject_refs or not proposition.predicate_refs
        for group in (proposition.subject_refs, proposition.predicate_refs):
            _refs(group, quotes)
            if any(not _contained(ref, proposition.supporting_refs) for ref in group):
                raise ValueError("Element reference outside proposition support")
        facets = {facet.id: facet for facet in proposition.facets}
        if len(facets) != len(proposition.facets):
            raise ValueError("Duplicate facet ID")
        for facet in proposition.facets:
            _refs(facet.refs, quotes)
            if any(not _contained(ref, proposition.supporting_refs) for ref in facet.refs):
                raise ValueError("Facet reference outside proposition support")
            _ids(facet.target_ids, set(facets))
            if facet.kind in ("bound", "distribution"):
                if len(facet.target_ids) != 1 or facets[facet.target_ids[0]].kind != "quantity":
                    raise ValueError("Expected one local quantity target")
            elif facet.target_ids:
                raise ValueError("Unexpected facet target")
            uncertain = _facet(facet, quotes) or uncertain
        if uncertain and proposition.epistemic_status != "uncertain":
            raise ValueError("Missing evidence requires explicit uncertainty")
        _ids(proposition.depends_on_ids, proposition_ids - {proposition.id})
    # Direction is dependent -> prerequisite; preserve submitted edges without inferring any.
    edges = {p.id: p.depends_on_ids for p in propositions}
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(identifier: str) -> None:
        if identifier in visiting:
            raise ValueError("Cyclic proposition dependencies")
        if identifier in visited:
            return
        visiting.add(identifier)
        for prerequisite in edges[identifier]:
            visit(prerequisite)
        visiting.remove(identifier)
        visited.add(identifier)

    for identifier in edges:
        visit(identifier)
    _ids(coverage.linked_proposition_ids, proposition_ids)
    linked = bool(coverage.linked_proposition_ids)
    if (not linked and coverage.unresolved_reason is None) or (
        linked and coverage.unresolved_reason == "no_linked_evidence"
    ):
        raise ValueError("Invalid unresolved coverage reason")


def build_question_evidence_propositions(
    source: Source, question: str, data: QuestionEvidenceInput | dict[str, Any]
) -> QuestionEvidencePropositions:
    """Bind explicit propositions to the complete current source and exact question."""
    try:
        _guard_actual(source, Source)
        _original(data, QuestionEvidenceInput)
        question_sha256 = _question(question)
        source_sha256, quotes = _source(source)
        checked = _read(QuestionEvidenceInput, data)
        _check(checked.propositions, checked.coverage, quotes)
        return QuestionEvidencePropositions(
            profile="question-evidence-propositions-v1",
            status="unreviewed",
            question_sha256=question_sha256,
            source_sha256=source_sha256,
            propositions=checked.propositions,
            coverage=checked.coverage,
        )
    except Exception:
        raise QuestionEvidenceError() from None


def validate_question_evidence_propositions(
    source: Source, question: str, result: QuestionEvidencePropositions | dict[str, Any]
) -> QuestionEvidencePropositions:
    """Revalidate original shapes, hashes, source spans, and links; return a fresh DTO."""
    try:
        _guard_actual(source, Source)
        _original(result, QuestionEvidencePropositions)
        question_sha256 = _question(question)
        source_sha256, quotes = _source(source)
        checked = _read(QuestionEvidencePropositions, result)
        if checked.question_sha256 != question_sha256 or checked.source_sha256 != source_sha256:
            raise ValueError("Stale question or source receipt")
        _check(checked.propositions, checked.coverage, quotes)
        return checked
    except Exception:
        raise QuestionEvidenceError() from None
