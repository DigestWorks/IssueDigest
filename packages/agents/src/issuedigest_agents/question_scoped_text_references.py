"""Pure exact text references inside explicitly declared proposition support."""

from typing import Any

from . import question_evidence_propositions as canonical
from .numeric_evidence import Source
from .numeric_selection_evaluation import _read
from .question_evidence_propositions import (
    QuestionEvidenceError,
    QuestionEvidencePropositions,
    _guard_actual,
    _original,
    _question,
    _source,
)
from .question_text_references import (
    EvidenceProposition,
    EvidenceRef,
    QuestionEvidenceTextInput,
    _refs,
)


def _resolve_scoped(
    ref: EvidenceRef, supports: tuple[canonical.EvidenceRef, ...], quotes: dict[str, str]
) -> canonical.EvidenceRef:
    if not ref.citation_id.strip() or not ref.text.strip():
        raise ValueError("Blank reference")
    ref.citation_id.encode("utf-8")
    ref.text.encode("utf-8")
    quote = quotes[ref.citation_id]
    positions: set[tuple[int, int]] = set()
    for support in supports:
        if support.citation_id != ref.citation_id:
            continue
        start = quote.find(ref.text, support.start, support.end)
        while start >= 0:
            positions.add((start, start + len(ref.text)))
            start = quote.find(ref.text, start + 1, support.end)
    if len(positions) != 1:
        raise ValueError("Expected exactly one supported occurrence")
    start, end = positions.pop()
    return canonical.EvidenceRef(citation_id=ref.citation_id, text=ref.text, start=start, end=end)


def _proposition(p: EvidenceProposition, quotes: dict[str, str]) -> canonical.EvidenceProposition:
    supports = _refs(p.supporting_refs, quotes)

    def resolve(value: Any) -> Any:
        # This tree comes only from the checked DTO; preserve every collection and field.
        if isinstance(value, dict):
            if set(value) == {"citation_id", "text"}:
                ref = EvidenceRef.model_validate(value, strict=True)
                return _resolve_scoped(ref, supports, quotes).model_dump()
            return {key: resolve(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return tuple(resolve(item) for item in value)
        return value

    fields = p.model_dump(exclude={"supporting_refs"})
    resolved = resolve(fields)
    resolved["supporting_refs"] = supports
    return canonical.EvidenceProposition.model_validate(resolved, strict=True)


def build_question_scoped_text_evidence(
    source: Source, question: str, data: QuestionEvidenceTextInput | dict[str, Any]
) -> QuestionEvidencePropositions:
    """Resolve support globally, other refs within it, then delegate canonical validation."""
    try:
        _guard_actual(source, Source)
        _original(data, QuestionEvidenceTextInput)
        _question(question)
        source_hash, quotes = _source(source)
        checked = _read(QuestionEvidenceTextInput, data)
        result = canonical.build_question_evidence_propositions(
            source,
            question,
            canonical.QuestionEvidenceInput(
                propositions=tuple(_proposition(p, quotes) for p in checked.propositions),
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
