"""Pure unreviewed briefing composition; references never certify prose meaning.

No transport, persistence, application registration, or historical Canvas conversion.
Texts are untrusted plain text; downstream renderers must handle them safely.
"""

import re
from datetime import date
from hashlib import sha256
from typing import Annotated, Any, Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import UUID4, Field, field_validator, model_validator

from .guarded_question_evidence_v2 import (
    GuardedQuestionEvidenceGenerationV2,
    validate_guarded_question_evidence_v2,
)
from .guarded_question_evidence_v3 import (
    GuardedQuestionEvidenceGenerationV3,
    validate_guarded_question_evidence_v3,
)
from .guarded_question_evidence_v5 import (
    GuardedQuestionEvidenceGenerationV5,
    validate_guarded_question_evidence_v5,
)
from .numeric_evidence import Source, _StrictModel
from .numeric_selection_evaluation import _read
from .question_evidence_propositions import (
    EvidenceProposition,
    PropositionId,
    QuestionCoverage,
    _guard_actual,
    _original,
    _source,
)

QuestionEvidenceReceipt = Annotated[
    GuardedQuestionEvidenceGenerationV2
    | GuardedQuestionEvidenceGenerationV3
    | GuardedQuestionEvidenceGenerationV5,
    Field(discriminator="profile"),
]


def validate_question_evidence_receipt(
    source: Source, question: str, receipt: QuestionEvidenceReceipt | dict[str, Any]
) -> QuestionEvidenceReceipt:
    """Use the original strict version validator without conversion or relabeling."""
    if isinstance(receipt, dict):
        if type(receipt) is not dict or type(receipt.get("profile")) is not str:
            raise ValueError("Invalid evidence profile")
        if receipt["profile"] == "guarded-question-evidence-v2":
            return validate_guarded_question_evidence_v2(source, question, receipt)
        if receipt["profile"] == "guarded-question-evidence-v3":
            return validate_guarded_question_evidence_v3(source, question, receipt)
        if receipt["profile"] == "guarded-question-evidence-v5":
            return validate_guarded_question_evidence_v5(source, question, receipt)
    else:
        _guard_actual(receipt, QuestionEvidenceReceipt)
        if type(receipt) is GuardedQuestionEvidenceGenerationV2:
            return validate_guarded_question_evidence_v2(source, question, receipt)
        if type(receipt) is GuardedQuestionEvidenceGenerationV3:
            return validate_guarded_question_evidence_v3(source, question, receipt)
        if type(receipt) is GuardedQuestionEvidenceGenerationV5:
            return validate_guarded_question_evidence_v5(source, question, receipt)
    raise ValueError("Invalid evidence profile")


class QuestionBriefingError(ValueError):
    """Fixed whole-operation failure, without sensitive input or chained errors."""

    def __init__(self) -> None:
        super().__init__("Invalid question briefing")


class QuestionBriefingReference(_StrictModel):
    snapshot_id: UUID4
    proposition_id: PropositionId


References = Annotated[tuple[QuestionBriefingReference, ...], Field(min_length=1, max_length=8)]
Text = Annotated[str, Field(min_length=1, max_length=400)]
Title = Annotated[str, Field(min_length=1, max_length=100)]
Message = Annotated[str, Field(min_length=1, max_length=500)]


class QuestionBriefingClaimProposal(_StrictModel):
    text: Text
    references: References
    event_date: date | None

    @field_validator("text")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        return _nonblank(value)

    @model_validator(mode="after")
    def unique_references(self) -> Self:
        if len(set(self.references)) != len(self.references):
            raise ValueError("Duplicate references")
        return self


class QuestionBriefingModuleProposal(_StrictModel):
    kind: Literal["summary", "comparison", "timeline"]
    title: Title
    claims: Annotated[tuple[QuestionBriefingClaimProposal, ...], Field(min_length=1, max_length=4)]

    @field_validator("title")
    @classmethod
    def nonblank_title(cls, value: str) -> str:
        return _nonblank(value)

    @model_validator(mode="after")
    def module_shape(self) -> Self:
        if self.kind == "comparison" and len(self.claims) < 2:
            raise ValueError("Comparison needs multiple claims")
        if any(
            (claim.event_date is not None) != (self.kind == "timeline") for claim in self.claims
        ):
            raise ValueError("Dates belong only to timeline claims")
        return self


class QuestionBriefingProposal(_StrictModel):
    outcome: Literal["answer", "insufficient_evidence"]
    message: Message | None
    modules: Annotated[tuple[QuestionBriefingModuleProposal, ...], Field(max_length=3)]

    @field_validator("message")
    @classmethod
    def nonblank_message(cls, value: str | None) -> str | None:
        return None if value is None else _nonblank(value)

    @model_validator(mode="after")
    def outcome_shape(self) -> Self:
        if self.outcome == "answer":
            if self.message is not None or not self.modules or self.modules[0].kind != "summary":
                raise ValueError("Answer requires first summary and no message")
            if any(module.kind == "summary" for module in self.modules[1:]):
                raise ValueError("Only the first module is a summary")
        elif self.modules or self.message is None:
            raise ValueError("Insufficient evidence needs message and no modules")
        return self


class QuestionBriefingClaim(QuestionBriefingClaimProposal):
    epistemic_status: Literal["source_statement", "uncertain"]


class QuestionBriefingModule(_StrictModel):
    kind: Literal["summary", "comparison", "timeline"]
    title: Title
    claims: Annotated[tuple[QuestionBriefingClaim, ...], Field(min_length=1, max_length=4)]


class QuestionBriefingSource(_StrictModel):
    snapshot_id: UUID4
    source_sha256: Sha256
    receipt: QuestionEvidenceReceipt


class QuestionBriefingCoverage(QuestionCoverage):
    snapshot_id: UUID4
    closure_proposition_ids: tuple[PropositionId, ...]
    used_proposition_ids: tuple[PropositionId, ...]
    uncovered_linked_proposition_ids: tuple[PropositionId, ...]


class QuestionBriefing(_StrictModel):
    """Current source-bound composition, with original receipts and proposal intact."""

    profile: Literal["question-briefing-v1"]
    status: Literal["unreviewed"]
    question_sha256: Sha256
    workspace_id: UUID4
    sources: Annotated[tuple[QuestionBriefingSource, ...], Field(min_length=1, max_length=5)]
    outcome: Literal["answer", "insufficient_evidence"]
    message: Message | None
    proposal: QuestionBriefingProposal
    modules: Annotated[tuple[QuestionBriefingModule, ...], Field(max_length=3)]
    coverage: Annotated[tuple[QuestionBriefingCoverage, ...], Field(min_length=1, max_length=5)]


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("Blank text")
    value.encode("utf-8")
    return value


def _closure(propositions: dict[str, EvidenceProposition], ids: tuple[str, ...]) -> set[str]:
    # Existing receipt validator has already checked all local IDs and graph cycles.
    found: set[str] = set()
    pending = list(ids)
    while pending:
        identifier = pending.pop()
        if identifier not in found:
            found.add(identifier)
            pending.extend(propositions[identifier].depends_on_ids)
    return found


def _build(
    question: str,
    sources: tuple[Source, ...],
    receipts: tuple[QuestionEvidenceReceipt, ...],
    proposal: QuestionBriefingProposal | dict[str, Any],
) -> QuestionBriefing:
    if type(question) is not str or not 1 <= len(question) <= 1500:
        raise ValueError("Invalid question")
    _nonblank(question)
    _guard_actual(sources, tuple[Source, ...])
    _guard_actual(receipts, tuple[QuestionEvidenceReceipt, ...])
    if (
        not 1 <= len(sources) <= 5
        or len(receipts) != len(sources)
        or len({receipt.profile for receipt in receipts}) != 1
    ):
        raise ValueError("Invalid source count")
    _original(proposal, QuestionBriefingProposal)
    submitted = _read(QuestionBriefingProposal, proposal)
    bound: list[QuestionBriefingSource] = []
    snapshots: set[Any] = set()
    versions: set[Any] = set()
    citations: set[Any] = set()
    workspace = sources[0][1].document.workspace_id
    for source, receipt in zip(sources, receipts, strict=True):
        sid, bundle, presentation = source
        source_hash, _ = _source(source)
        version = bundle.version.version_id
        identifiers = {citation.citation_id for citation in bundle.citations}
        if (
            sid in snapshots
            or version in versions
            or citations & identifiers
            or bundle.document.workspace_id != workspace
            or presentation.workspace_id != workspace
        ):
            raise ValueError("Duplicate or inconsistent sources")
        snapshots.add(sid)
        versions.add(version)
        citations.update(identifiers)
        checked = validate_question_evidence_receipt(source, question, receipt)
        bound.append(
            QuestionBriefingSource(snapshot_id=sid, source_sha256=source_hash, receipt=checked)
        )
    # Snapshot keys keep reused source-local proposition IDs separate.
    indexes = {
        item.snapshot_id: {p.id: p for p in item.receipt.evidence.propositions} for item in bound
    }
    linked = {
        item.snapshot_id: set(item.receipt.evidence.coverage.linked_proposition_ids)
        for item in bound
    }
    allowed = {
        sid: _closure(indexes[sid], tuple(identifiers)) for sid, identifiers in linked.items()
    }
    used: dict[Any, set[str]] = {item.snapshot_id: set() for item in bound}
    has_link = False
    modules: list[QuestionBriefingModule] = []
    for module in submitted.modules:
        claims: list[QuestionBriefingClaim] = []
        for claim in module.claims:
            certain = True
            date_anchored = claim.event_date is None
            for reference in claim.references:
                sid, pid = reference.snapshot_id, reference.proposition_id
                if sid not in indexes or pid not in allowed[sid]:
                    raise ValueError("Reference outside linked source graph")
                has_link = has_link or pid in linked[sid]
                closure = _closure(indexes[sid], (pid,))
                used[sid].update(closure)
                certain = certain and all(
                    indexes[sid][identifier].epistemic_status == "source_statement"
                    for identifier in closure
                )
                if claim.event_date is not None:
                    literal = claim.event_date.isoformat()
                    date_anchored = date_anchored or any(
                        re.search(r"(?<!\d)" + re.escape(literal) + r"(?!\d)", span.text)
                        is not None
                        for span in indexes[sid][pid].supporting_refs
                    )
            if not date_anchored:
                raise ValueError("Date absent from direct proposition support")
            claims.append(
                QuestionBriefingClaim(
                    text=claim.text,
                    references=claim.references,
                    event_date=claim.event_date,
                    epistemic_status="source_statement" if certain else "uncertain",
                )
            )
        modules.append(
            QuestionBriefingModule(kind=module.kind, title=module.title, claims=tuple(claims))
        )
    if submitted.outcome == "answer" and not has_link:
        raise ValueError("Answer lacks referenced question-linked evidence")
    coverage = tuple(
        QuestionBriefingCoverage(
            snapshot_id=item.snapshot_id,
            linked_proposition_ids=tuple(
                p for p in indexes[item.snapshot_id] if p in linked[item.snapshot_id]
            ),
            closure_proposition_ids=tuple(
                p for p in indexes[item.snapshot_id] if p in allowed[item.snapshot_id]
            ),
            used_proposition_ids=tuple(
                p for p in indexes[item.snapshot_id] if p in used[item.snapshot_id]
            ),
            uncovered_linked_proposition_ids=tuple(
                p
                for p in indexes[item.snapshot_id]
                if p in linked[item.snapshot_id] and p not in used[item.snapshot_id]
            ),
            unresolved_reason=item.receipt.evidence.coverage.unresolved_reason,
        )
        for item in bound
    )
    return QuestionBriefing(
        profile="question-briefing-v1",
        status="unreviewed",
        question_sha256=sha256(question.encode("utf-8")).hexdigest(),
        workspace_id=workspace,
        sources=tuple(bound),
        outcome=submitted.outcome,
        message=submitted.message,
        proposal=submitted,
        modules=tuple(modules),
        coverage=coverage,
    )


def build_question_briefing(
    question: str,
    sources: tuple[Source, ...],
    receipts: tuple[QuestionEvidenceReceipt, ...],
    proposal: QuestionBriefingProposal | dict[str, Any],
) -> QuestionBriefing:
    """Compose only current validated source receipts; no semantic approval."""
    try:
        return _build(question, sources, receipts, proposal)
    except Exception:
        pass
    # Outside the handler: even __context__ must not expose sanitized internals.
    raise QuestionBriefingError()


def validate_question_briefing(
    question: str,
    sources: tuple[Source, ...],
    receipts: tuple[QuestionEvidenceReceipt, ...],
    result: QuestionBriefing | dict[str, Any],
) -> QuestionBriefing:
    """Rebuild the entire saved composition and reject any divergence, without repair."""
    try:
        _original(result, QuestionBriefing)
        checked = _read(QuestionBriefing, result)
        rebuilt = _build(question, sources, receipts, checked.proposal)
        if checked != rebuilt:
            raise ValueError("Changed briefing")
        return rebuilt
    except Exception:
        pass
    raise QuestionBriefingError()
