"""Pure semantic v2 diagnosis of the unchanged balanced proposal and explicit targets."""

from hashlib import sha256
from typing import Any, Literal, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field

from .balanced_role_generation import RoleAliasGenerationV2, validate_balanced_role_generation
from .contextual_anchor import ContextualAnchor
from .numeric_candidates import ExactSpan
from .numeric_evidence import Source, _json, _StrictModel
from .numeric_selection import ResolvedAnchor, _inside
from .numeric_selection_evaluation import _read
from .role_alias_contract import RoleAliasInput, _guard
from .role_aware_audit_contract import (
    ROLES,
    AuditRole,
    ResolvedRoleAwareAuditIssue,
    RoleAwareAuditInput,
    RoleAwareAuditIssue,
    RoleAwareAuditScope,
    RoleAwareAuditTarget,
    RoleAwareScopeSlots,
)
from .scope_audit_contract import AuditStatus, ScopeSlot
from .shared_measurement_context_v2 import SharedMeasurementFrameV2, _broad, _resolve


class SemanticRoleAuditContractError(ValueError):
    """Sanitized rejection without source data or partial diagnostics."""


class SemanticRoleAuditReport(_StrictModel):
    profile: Literal["role-aware-audit-report-v2"]
    generation: RoleAliasGenerationV2
    source_sha256: Sha256
    generation_sha256: Sha256
    proposal: RoleAliasInput
    proposal_sha256: Sha256
    change_coverage: Literal["available"]
    roles: tuple[AuditRole, ...] = Field(min_length=5, max_length=5)
    scope_slots: tuple[RoleAwareScopeSlots, ...] = Field(max_length=12)
    coverage_sha256: Sha256
    input: RoleAwareAuditInput
    issues: tuple[ResolvedRoleAwareAuditIssue, ...] = Field(max_length=144)
    status: AuditStatus


def _stored_generation(value: Any) -> None:
    if isinstance(value, BaseModel):
        value = value.__dict__
    if type(value) is not dict or not RoleAliasGenerationV2.model_fields.keys() <= value.keys():
        raise ValueError("Missing original generation fields")
    # Validation of the original frame's nested markers belongs to the v2 validator.


def _checked_generation(source: Source, generation: RoleAliasGenerationV2) -> RoleAliasGenerationV2:
    _guard(source, Source)
    _guard(generation, RoleAliasGenerationV2)
    if type(generation) is not RoleAliasGenerationV2:
        raise ValueError("Expected concrete balanced generation")
    _stored_generation(generation)
    return validate_balanced_role_generation(source, generation)


def _frame(generation: RoleAliasGenerationV2) -> SharedMeasurementFrameV2:
    return generation.frame.frame


def _coverage(
    generation: RoleAliasGenerationV2,
) -> tuple[
    RoleAliasInput, Literal["available"], tuple[AuditRole, ...], tuple[RoleAwareScopeSlots, ...]
]:
    proposal = generation.frame.input
    contexts = {c.id: c for c in proposal.contexts}
    slots = tuple(
        RoleAwareScopeSlots(
            number=b.number,
            scopes=tuple(
                RoleAwareAuditScope(slot=cast(ScopeSlot, f"r{i}"), kind=s.kind, anchor=s.anchor)
                for i, s in enumerate(contexts[b.context].scopes + b.scopes, 1)
            ),
        )
        for b in proposal.bindings
    )
    return proposal, "available", ROLES, slots


def _hash(value: Any) -> str:
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _support(
    generation: RoleAliasGenerationV2, issue: RoleAwareAuditIssue
) -> tuple[ExactSpan, ResolvedAnchor | None]:
    index = _frame(generation).candidate_index
    positions = {s.sentence_id: i for i, s in enumerate(index.sentences)}
    start = positions[issue.support[0]]
    sentences = index.sentences[start : start + len(issue.support)]
    if tuple(s.sentence_id for s in sentences) != issue.support:
        raise ValueError("Support must be ordered contiguous current sentences")
    first, last = sentences[0].span, sentences[-1].span
    if any(s.span.citation_id != first.citation_id for s in sentences):
        raise ValueError("Support crosses quotes")
    quote = next(q.quote for q in index.citations if q.citation_id == first.citation_id)
    statement = ExactSpan(
        citation_id=first.citation_id,
        start=first.start,
        end=last.end,
        text=quote[first.start : last.end],
    )
    location = None
    if issue.evidence is not None:
        anchor = ContextualAnchor(
            sentence_id=issue.evidence.s, text=issue.evidence.t, context_text=issue.evidence.c
        )
        if anchor.sentence_id not in issue.support:
            raise ValueError("Evidence outside support")
        _inside(statement, _broad(index, anchor).span)
        location = _resolve(index, anchor)
        _inside(statement, location.span)
    if issue.kind == "missing" and location is None:
        raise ValueError("Missing requires exact evidence")
    return statement, location


def _target(
    proposal: RoleAliasInput,
    slots: tuple[RoleAwareScopeSlots, ...],
    issue: RoleAwareAuditIssue,
    target: RoleAwareAuditTarget,
) -> None:
    binding = next(b for b in proposal.bindings if b.number == target.number)
    context = next(c for c in proposal.contexts if c.id == binding.context)
    current_slots = next(row.scopes for row in slots if row.number == target.number)
    if target.slot is not None and (
        issue.role != "target_scope" or target.slot not in {s.slot for s in current_slots}
    ):
        raise ValueError("Slot must identify this number's current scope")
    if issue.kind == "missing" and target.slot is not None:
        raise ValueError("Missing must not target an existing slot")
    if issue.kind != "unsupported":
        return
    if issue.role == "target_scope":
        if target.slot is None:
            raise ValueError("Unsupported scope requires current slot")
        return
    actor = next(e.actor for e in proposal.events if e.id == context.event)
    values = {
        "measured_entity": context.entity,
        "period": context.period,
        "reporting_actor": actor,
        "change_direction": binding.change,
    }
    if values[issue.role] is None:
        raise ValueError("Unsupported requires nonnull original role")


def _diagnoses(
    generation: RoleAliasGenerationV2,
    data: RoleAwareAuditInput,
    slots: tuple[RoleAwareScopeSlots, ...],
) -> tuple[ResolvedRoleAwareAuditIssue, ...]:
    proposal = generation.frame.input
    candidates = {c.candidate_id: c for c in _frame(generation).candidate_index.candidates}
    resolved = []
    seen: set[tuple[Any, ...]] = set()
    for issue in data.issues:
        statement, location = _support(generation, issue)
        targets = tuple((t.number, t.slot) for t in issue.targets)
        if len(set(targets)) != len(targets):
            raise ValueError("Duplicate explicit target")
        for target in issue.targets:
            _target(proposal, slots, issue, target)
            _inside(statement, candidates[target.number].expression)
            key = (target.number, issue.role, target.slot, location)
            if key in seen:
                raise ValueError("Duplicate or conflicting diagnosis location")
            seen.add(key)
            resolved.append(
                ResolvedRoleAwareAuditIssue(
                    candidate_id=target.number,
                    role=issue.role,
                    kind=issue.kind,
                    scope_slot=target.slot,
                    source_anchor=location,
                    support_sentence_ids=issue.support,
                    statement=statement,
                )
            )
    return tuple(resolved)


def _status(
    data: RoleAwareAuditInput, issues: tuple[ResolvedRoleAwareAuditIssue, ...]
) -> AuditStatus:
    hard = False
    uncertain = data.incomplete
    for check in data.checks:
        kinds = {i.kind for i in issues if i.candidate_id == check.number}
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
    return (
        "not_applicable"
        if not data.checks
        else "issues_flagged"
        if hard
        else "uncertain"
        if uncertain
        else "no_issues_flagged"
    )


def _build_report(
    source: Source, generation: RoleAliasGenerationV2, data: RoleAwareAuditInput
) -> SemanticRoleAuditReport:
    generation = _checked_generation(source, generation)
    proposal, coverage, roles, slots = _coverage(generation)
    if tuple(c.number for c in data.checks) != tuple(b.number for b in proposal.bindings):
        raise ValueError("Checks must cover selected numbers exactly once in order")
    if not proposal.bindings and (data.incomplete or data.issues):
        raise ValueError("Empty selection cannot have incomplete diagnosis")
    issues = _diagnoses(generation, data, slots)
    return SemanticRoleAuditReport(
        profile="role-aware-audit-report-v2",
        generation=generation,
        source_sha256=_frame(generation).candidate_index.source_sha256,
        generation_sha256=_hash(generation.model_dump(mode="json")),
        proposal=proposal,
        proposal_sha256=_hash(proposal.model_dump(mode="json")),
        change_coverage=coverage,
        roles=roles,
        scope_slots=slots,
        coverage_sha256=_hash(
            dict(
                change_coverage=coverage,
                roles=roles,
                scope_slots=[s.model_dump(mode="json") for s in slots],
            )
        ),
        input=data,
        issues=issues,
        status=_status(data, issues),
    )


def build_semantic_role_audit_report(
    source: Source, generation: RoleAliasGenerationV2, input: RoleAwareAuditInput | dict[str, Any]
) -> SemanticRoleAuditReport:
    """Validate explicit diagnoses without editing the original proposal."""
    try:
        _guard(input, RoleAwareAuditInput)
        return _build_report(source, generation, _read(RoleAwareAuditInput, input))
    except Exception:
        raise SemanticRoleAuditContractError("Invalid semantic role audit input") from None


def validate_semantic_role_audit_report(
    source: Source, report: SemanticRoleAuditReport | dict[str, Any]
) -> SemanticRoleAuditReport:
    """Reconstruct full balanced generation, coverage, hashes and each diagnosis."""
    try:
        _guard(report, SemanticRoleAuditReport)
        fields = report.__dict__ if isinstance(report, BaseModel) else report
        _stored_generation(fields["generation"])
        validate_balanced_role_generation(source, fields["generation"])
        checked = _read(SemanticRoleAuditReport, report)
        expected = _build_report(source, checked.generation, checked.input)
        if checked != expected:
            raise ValueError("Stored report differs from reconstruction")
        return expected
    except Exception:
        raise SemanticRoleAuditContractError("Invalid semantic role audit report") from None
