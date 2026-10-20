"""Pure comparisons against human-authored exact references, never truth certification."""

from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field, model_validator

from .numeric_candidates import ExactSpan, NumericCandidateIndex, validate_numeric_candidates
from .numeric_evidence import KnownUsage, Source, _json, _plain, _source_data, _StrictModel
from .numeric_selection import FactKind, NumericSelectionProposal, validate_numeric_selection


class NumericSelectionEvaluationError(ValueError):
    """Sanitized failure of the whole evaluation input, without source or validation detail."""


class AnchorRule(_StrictModel):
    mode: Literal["one_of", "absent", "unassessed"]
    alternatives: tuple[ExactSpan, ...] = Field(max_length=4)

    @model_validator(mode="after")
    def exact_alternatives(self) -> Self:
        if (self.mode == "one_of") != bool(self.alternatives):
            raise ValueError("Invalid anchor alternatives")
        if len(set(self.alternatives)) != len(self.alternatives):
            raise ValueError("Duplicate anchor alternatives")
        return self


class ReferenceFact(_StrictModel):
    candidate_id: str
    subject: AnchorRule
    period: AnchorRule
    condition: AnchorRule
    kind: FactKind | None
    status_text: AnchorRule


class NumericSelectionReference(_StrictModel):
    """An evaluator-authored comparison reference, not an automatically generated gold label."""

    profile: Literal["numeric-selection-reference-v1"] = "numeric-selection-reference-v1"
    candidate_index: NumericCandidateIndex
    candidate_set: Literal["complete", "partial"]
    facts: tuple[ReferenceFact, ...] = Field(max_length=12)


type CheckResult = Literal["match", "mismatch", "unassessed"]
type CheckField = Literal["presence", "subject", "period", "condition", "kind", "status_text"]


class NumericSelectionCheck(_StrictModel):
    candidate_id: str
    field: CheckField
    result: CheckResult


class NumericSelectionEvaluationReport(_StrictModel):
    profile: Literal["numeric-selection-evaluation-v1"] = "numeric-selection-evaluation-v1"
    scope: Literal["fact_fields_only"] = "fact_fields_only"
    outcome: Literal["reference_match", "reference_mismatch", "inconclusive", "rejected"]
    reference_sha256: Sha256
    proposal_sha256: Sha256 | None
    expected_facts: Annotated[int, Field(ge=0)]
    received_facts: Annotated[int, Field(ge=0)] | None
    checks: tuple[NumericSelectionCheck, ...]
    usage: KnownUsage | None


def _read[T: BaseModel](model: type[T], value: T | dict[str, Any]) -> T:
    # _plain catches unchecked extras; serialize_as_any also retains declared subclass fields.
    _plain(value)
    raw = (
        value.model_dump_json(serialize_as_any=True, warnings="error")
        if isinstance(value, BaseModel)
        else _json(value)
    )
    return model.model_validate_json(raw, strict=True)


def _validate_reference(source: Source, reference: NumericSelectionReference) -> None:
    index = validate_numeric_candidates(source, reference.candidate_index)
    candidates = {c.candidate_id: c for c in index.candidates}
    quotes = {c.citation_id: c.quote for c in index.citations}
    seen: set[str] = set()
    for fact in reference.facts:
        if fact.candidate_id in seen or fact.candidate_id not in candidates:
            raise ValueError("Invalid reference candidate")
        seen.add(fact.candidate_id)
        citation_id = candidates[fact.candidate_id].expression.citation_id
        for rule in (fact.subject, fact.period, fact.condition, fact.status_text):
            for span in rule.alternatives:
                if (
                    span.citation_id != citation_id
                    or quotes[citation_id][span.start : span.end] != span.text
                ):
                    raise ValueError("Invalid reference anchor")


def _anchor_result(rule: AnchorRule, actual: ExactSpan | None) -> CheckResult:
    if rule.mode == "unassessed":
        return "unassessed"
    matches = actual is None if rule.mode == "absent" else actual in rule.alternatives
    return "match" if matches else "mismatch"


def _checks(
    reference: NumericSelectionReference, proposal: NumericSelectionProposal
) -> tuple[NumericSelectionCheck, ...]:
    actual = {f.candidate_id: f for f in proposal.facts}
    expected_ids = {f.candidate_id for f in reference.facts}
    checks: list[NumericSelectionCheck] = []
    for expected in reference.facts:
        fact = actual.get(expected.candidate_id)
        checks.append(
            NumericSelectionCheck(
                candidate_id=expected.candidate_id,
                field="presence",
                result="match" if fact is not None else "mismatch",
            )
        )
        if fact is None:
            continue
        for field in ("subject", "period", "condition", "kind", "status_text"):
            result: CheckResult
            if field == "kind":
                result = (
                    "unassessed"
                    if expected.kind is None
                    else "match"
                    if expected.kind == fact.kind
                    else "mismatch"
                )
            else:
                anchor = getattr(fact, field)
                result = _anchor_result(getattr(expected, field), anchor.span if anchor else None)
            checks.append(
                NumericSelectionCheck(
                    candidate_id=expected.candidate_id, field=field, result=result
                )
            )
    for fact in proposal.facts:
        if fact.candidate_id not in expected_ids:
            checks.append(
                NumericSelectionCheck(
                    candidate_id=fact.candidate_id,
                    field="presence",
                    result="mismatch" if reference.candidate_set == "complete" else "unassessed",
                )
            )
    return tuple(checks)


def _hash(model: BaseModel) -> str:
    # Inputs have already passed lossless/strict validation; JSON mode encodes UUIDs.
    return sha256(_json(model.model_dump(mode="json")).encode("utf-8")).hexdigest()


def evaluate_numeric_selection(
    source: Source,
    reference: NumericSelectionReference | dict[str, Any],
    proposal: NumericSelectionProposal | dict[str, Any] | None,
    *,
    rejected_usage: KnownUsage | dict[str, Any] | None = None,
) -> NumericSelectionEvaluationReport:
    """Revalidate current inputs and compare fact fields, with no I/O or model requests."""
    try:
        _source_data(source)
        for model in source[1:]:
            if model.model_dump(mode="python", serialize_as_any=True, warnings="error") != _plain(
                model
            ):
                raise ValueError("Unexpected canonical source fields")
        checked_reference = _read(NumericSelectionReference, reference)
        _validate_reference(source, checked_reference)
        if proposal is not None and rejected_usage is not None:
            raise ValueError("Contradictory result and rejection usage")
        reference_hash = _hash(checked_reference)
        if proposal is None:
            usage = _read(KnownUsage, rejected_usage) if rejected_usage is not None else None
            return NumericSelectionEvaluationReport(
                outcome="rejected",
                reference_sha256=reference_hash,
                proposal_sha256=None,
                expected_facts=len(checked_reference.facts),
                received_facts=None,
                checks=(),
                usage=usage,
            )
        checked_proposal = validate_numeric_selection(source, proposal)
        checks = _checks(checked_reference, checked_proposal)
        outcome: Literal["reference_match", "reference_mismatch", "inconclusive"]
        if any(c.result == "mismatch" for c in checks):
            outcome = "reference_mismatch"
        elif checked_reference.candidate_set == "partial" or any(
            c.result == "unassessed" for c in checks
        ):
            outcome = "inconclusive"
        else:
            outcome = "reference_match"
        return NumericSelectionEvaluationReport(
            outcome=outcome,
            reference_sha256=reference_hash,
            proposal_sha256=_hash(checked_proposal),
            expected_facts=len(checked_reference.facts),
            received_facts=len(checked_proposal.facts),
            checks=checks,
            usage=checked_proposal.usage,
        )
    except Exception:
        raise NumericSelectionEvaluationError(
            "Invalid numeric selection evaluation input"
        ) from None
