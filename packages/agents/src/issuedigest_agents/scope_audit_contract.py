"""Pure four-role diagnosis over an unchanged, validated shared generation.

Exact locations and consistent diagnoses certify neither role meaning nor the
completeness of numeric selection. No generation, repair or model call occurs here.
"""

from hashlib import sha256
from typing import Any, Literal, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field

from .compact_shared_context import (
    CompactSharedContextGeneration,
    validate_compact_shared_context_generation,
)
from .contextual_anchor import ContextualAnchor
from .measurement_scope import ScopeKind
from .numeric_candidates import ExactSpan
from .numeric_evidence import Source, _json, _StrictModel
from .numeric_frame import ReportingTense
from .numeric_selection import FactKind, ResolvedAnchor, _inside
from .numeric_selection_evaluation import _canonical_models, _read
from .shared_context_generation_v2 import (
    SharedContextGenerationV2,
    validate_shared_context_generation_v2,
)
from .shared_measurement_context import SharedId, _actual_models
from .shared_measurement_context_v2 import _broad, _resolve

AuditedGeneration = SharedContextGenerationV2 | CompactSharedContextGeneration
type ScopeSlot = Literal["r1", "r2", "r3", "r4"]
type AuditRole = Literal["measured_entity", "target_scope", "period", "reporting_actor"]
type AuditKind = Literal["missing", "unsupported", "uncertain"]
type AuditCheckStatus = Literal["no_issue_found", "issues_found", "uncertain"]
type AuditStatus = Literal["not_applicable", "no_issues_flagged", "uncertain", "issues_flagged"]


class ScopeAuditError(ValueError):
    """Sanitized whole-report rejection; never exposes source or partial diagnoses."""


class ScopeAuditCheck(_StrictModel):
    candidate_id: SharedId
    status: AuditCheckStatus


class ScopeAuditIssue(_StrictModel):
    candidate_id: SharedId
    role: AuditRole
    kind: AuditKind
    scope_slot: ScopeSlot | None
    source_anchor: ContextualAnchor | None
    support_sentence_ids: tuple[str, ...] = Field(min_length=1, max_length=20)


class ScopeAuditInput(_StrictModel):
    checks: tuple[ScopeAuditCheck, ...] = Field(max_length=12)
    issues: tuple[ScopeAuditIssue, ...] = Field(max_length=12)
    incomplete: bool


class ScopeAuditScope(_StrictModel):
    slot: ScopeSlot
    kind: ScopeKind
    anchor: ContextualAnchor


class ScopeAuditProjection(_StrictModel):
    candidate_id: SharedId
    measured_entity: ContextualAnchor | None
    target_scopes: tuple[ScopeAuditScope, ...] = Field(max_length=4)
    period: ContextualAnchor | None
    reporting_actor: ContextualAnchor | None
    value_status: FactKind
    status_evidence_sentence_id: str | None
    reporting_kind: Literal["attributed_report", "narration", "unknown"]
    reporting_predicate: ContextualAnchor | None
    reporting_tense: ReportingTense


class ResolvedScopeAuditIssue(_StrictModel):
    candidate_id: SharedId
    role: AuditRole
    kind: AuditKind
    scope_slot: ScopeSlot | None
    source_anchor: ResolvedAnchor | None
    support_sentence_ids: tuple[str, ...] = Field(min_length=1, max_length=20)
    statement: ExactSpan


class ScopeAuditReport(_StrictModel):
    """Original proposal and reproducible diagnosis, without a semantic approval flag."""

    profile: Literal["scope-audit-report-v1"]
    generation: AuditedGeneration
    source_sha256: Sha256
    projection_sha256: Sha256
    projection: tuple[ScopeAuditProjection, ...] = Field(max_length=12)
    input: ScopeAuditInput
    issues: tuple[ResolvedScopeAuditIssue, ...] = Field(max_length=12)
    status: AuditStatus


def _checked_generation(source: Source, generation: AuditedGeneration) -> AuditedGeneration:
    # Public input requires actual concrete generation nodes before validators dump.
    _canonical_models(source, Source)
    _actual_models(source, Source)
    _canonical_models(generation, AuditedGeneration)
    _actual_models(generation, AuditedGeneration)
    if type(generation) is CompactSharedContextGeneration:
        return validate_compact_shared_context_generation(source, generation)
    if type(generation) is SharedContextGenerationV2:
        return validate_shared_context_generation_v2(source, generation)
    raise ValueError("Expected concrete validated generation")


def _projection(generation: AuditedGeneration) -> tuple[ScopeAuditProjection, ...]:
    contexts = {c.context_id: c for c in generation.frame.input.contexts}
    events = {e.event_id: e for e in generation.frame.input.events}
    projected: list[ScopeAuditProjection] = []
    for binding in generation.frame.input.bindings:
        context = contexts[binding.context_id]
        event = events[context.reporting_event_id]
        scopes = tuple(
            ScopeAuditScope(slot=cast(ScopeSlot, f"r{i}"), kind=scope.kind, anchor=scope.anchor)
            for i, scope in enumerate(context.target_scopes + binding.target_scopes, 1)
        )
        projected.append(
            ScopeAuditProjection(
                candidate_id=binding.candidate_id,
                measured_entity=context.measured_variable,
                target_scopes=scopes,
                period=context.period,
                reporting_actor=event.reporting_actor,
                value_status=context.value_status,
                status_evidence_sentence_id=binding.status_evidence_sentence_id,
                reporting_kind=event.kind,
                reporting_predicate=event.predicate,
                reporting_tense=event.reporting_tense,
            )
        )
    return tuple(projected)


def _projection_hash(projection: tuple[ScopeAuditProjection, ...]) -> str:
    return sha256(_json([p.model_dump(mode="json") for p in projection]).encode()).hexdigest()


def _build(
    source: Source, generation: AuditedGeneration, data: ScopeAuditInput
) -> ScopeAuditReport:
    generation = _checked_generation(source, generation)
    projection = _projection(generation)
    selected = {p.candidate_id: p for p in projection}
    if tuple(c.candidate_id for c in data.checks) != tuple(selected):
        raise ValueError("Checks must cover selected candidates exactly once in order")
    if not selected and (data.incomplete or data.issues):
        raise ValueError("Empty selection is not an incomplete review")
    index = generation.frame.candidate_index
    positions = {s.sentence_id: i for i, s in enumerate(index.sentences)}
    candidates = {c.candidate_id: c for c in index.candidates}
    quotes = {q.citation_id: q.quote for q in index.citations}
    resolved: list[ResolvedScopeAuditIssue] = []
    seen: set[tuple[Any, ...]] = set()
    for issue in data.issues:
        proposal = selected[issue.candidate_id]
        if issue.role != "target_scope" and issue.scope_slot is not None:
            raise ValueError("Only scope diagnoses may identify a scope slot")
        scopes = {s.slot: s for s in proposal.target_scopes}
        if issue.scope_slot is not None and issue.scope_slot not in scopes:
            raise ValueError("Unknown candidate scope slot")
        if issue.kind == "missing":
            if issue.scope_slot is not None or issue.source_anchor is None:
                raise ValueError("Missing role requires new source evidence without a slot")
        if issue.kind == "unsupported":
            if issue.role == "target_scope":
                if issue.scope_slot is None:
                    raise ValueError("Unsupported scope requires an existing slot")
            elif getattr(proposal, issue.role) is None:
                raise ValueError("Unsupported diagnosis requires a nonnull proposed field")
        ids = issue.support_sentence_ids
        first_pos = positions[ids[0]]
        sentences = index.sentences[first_pos : first_pos + len(ids)]
        if tuple(s.sentence_id for s in sentences) != ids:
            raise ValueError("Support must select ordered contiguous current sentences")
        first, last = sentences[0].span, sentences[-1].span
        if any(s.span.citation_id != first.citation_id for s in sentences):
            raise ValueError("Support must share one quote")
        statement = ExactSpan(
            citation_id=first.citation_id,
            start=first.start,
            end=last.end,
            text=quotes[first.citation_id][first.start : last.end],
        )
        _inside(statement, candidates[issue.candidate_id].expression)
        location = None
        if issue.source_anchor is not None:
            if issue.source_anchor.sentence_id not in ids:
                raise ValueError("Anchor sentence outside support")
            _inside(statement, _broad(index, issue.source_anchor).span)
            location = _resolve(index, issue.source_anchor)
            _inside(statement, location.span)
        key = (issue.candidate_id, issue.role, issue.scope_slot, location)
        if key in seen:
            raise ValueError("Duplicate or conflicting diagnosis location")
        seen.add(key)
        resolved.append(
            ResolvedScopeAuditIssue(
                candidate_id=issue.candidate_id,
                role=issue.role,
                kind=issue.kind,
                scope_slot=issue.scope_slot,
                source_anchor=location,
                support_sentence_ids=ids,
                statement=statement,
            )
        )
    hard = False
    uncertain = data.incomplete
    for check in data.checks:
        kinds = {i.kind for i in data.issues if i.candidate_id == check.candidate_id}
        expected = (
            "issues_found"
            if kinds & {"missing", "unsupported"}
            else "uncertain"
            if kinds or data.incomplete
            else "no_issue_found"
        )
        if check.status != expected:
            raise ValueError("Check contradicts diagnosis or completion")
        hard |= expected == "issues_found"
        uncertain |= expected == "uncertain"
    status: AuditStatus = (
        "not_applicable"
        if not selected
        else "issues_flagged"
        if hard
        else "uncertain"
        if uncertain
        else "no_issues_flagged"
    )
    return ScopeAuditReport(
        profile="scope-audit-report-v1",
        generation=generation,
        source_sha256=index.source_sha256,
        projection_sha256=_projection_hash(projection),
        projection=projection,
        input=data,
        issues=tuple(resolved),
        status=status,
    )


def build_scope_audit_report(
    source: Source, generation: AuditedGeneration, input: ScopeAuditInput | dict[str, Any]
) -> ScopeAuditReport:
    """Resolve diagnostics only; never fill, select, inherit, repair or regenerate roles."""
    try:
        _canonical_models(input, ScopeAuditInput)
        if isinstance(input, BaseModel):
            _actual_models(input, ScopeAuditInput)
        return _build(source, generation, _read(ScopeAuditInput, input))
    except Exception:
        raise ScopeAuditError("Invalid scope audit input") from None


def validate_scope_audit_report(
    source: Source, report: ScopeAuditReport | dict[str, Any]
) -> ScopeAuditReport:
    """Rebuild generation, ordered projection, all evidence and status from current source."""
    try:
        _canonical_models(report, ScopeAuditReport)
        if isinstance(report, BaseModel):
            _actual_models(report, ScopeAuditReport)
        checked = _read(ScopeAuditReport, report)
        expected = _build(source, checked.generation, checked.input)
        if expected != checked:
            raise ValueError("Stored scope report differs from reconstruction")
        return expected
    except Exception:
        raise ScopeAuditError("Invalid scope audit report") from None
