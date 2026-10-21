"""Pure whole-proposal diagnosis with explicit coverage and target-only expansion."""

from hashlib import sha256
from typing import Any, Literal, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field

from .compact_shared_context import (
    CompactSharedContextGeneration,
    _require_stored_generation_markers,
    validate_compact_shared_context_generation,
)
from .contextual_anchor import ContextualAnchor
from .numeric_candidates import ExactSpan
from .numeric_evidence import Source, _json, _StrictModel
from .numeric_selection import ResolvedAnchor, _inside
from .numeric_selection_evaluation import _read
from .role_alias_contract import (
    RoleAliasAnchor,
    RoleAliasInput,
    RoleAliasScope,
    _encode_shared_input,
    _guard,
)
from .role_alias_generation import RoleAliasGeneration, validate_role_alias_generation
from .scope_audit_contract import AuditCheckStatus, AuditKind, AuditStatus, ScopeSlot
from .shared_context_generation_v2 import (
    SharedContextGenerationV2,
    validate_shared_context_generation_v2,
)
from .shared_measurement_context import SharedId
from .shared_measurement_context_v2 import SharedMeasurementFrameV2, _broad, _resolve

AuditedGeneration = RoleAliasGeneration | SharedContextGenerationV2 | CompactSharedContextGeneration
type AuditRole = Literal[
    "measured_entity", "target_scope", "period", "reporting_actor", "change_direction"
]
ROLES: tuple[AuditRole, ...] = (
    "measured_entity",
    "target_scope",
    "period",
    "reporting_actor",
    "change_direction",
)


class RoleAwareAuditContractError(ValueError):
    """Sanitized rejection, without source data or partial diagnostics."""


class LegacyRoleBinding(_StrictModel):
    number: SharedId
    context: SharedId
    scopes: tuple[RoleAliasScope, ...] = Field(max_length=4)
    status_sentence: str | None


class LegacyRoleProposal(RoleAliasInput):
    bindings: tuple[LegacyRoleBinding, ...] = Field(max_length=12)  # type: ignore[assignment]


class RoleAwareAuditCheck(_StrictModel):
    number: SharedId
    status: AuditCheckStatus


class RoleAwareAuditTarget(_StrictModel):
    number: SharedId
    slot: ScopeSlot | None


class RoleAwareAuditIssue(_StrictModel):
    role: AuditRole
    kind: AuditKind
    evidence: RoleAliasAnchor | None
    support: tuple[str, ...] = Field(min_length=1, max_length=20)
    targets: tuple[RoleAwareAuditTarget, ...] = Field(min_length=1, max_length=12)


class RoleAwareAuditInput(_StrictModel):
    checks: tuple[RoleAwareAuditCheck, ...] = Field(max_length=12)
    issues: tuple[RoleAwareAuditIssue, ...] = Field(max_length=12)
    incomplete: bool


class RoleAwareAuditScope(RoleAliasScope):
    slot: ScopeSlot


class RoleAwareScopeSlots(_StrictModel):
    number: SharedId
    scopes: tuple[RoleAwareAuditScope, ...] = Field(max_length=4)


class ResolvedRoleAwareAuditIssue(_StrictModel):
    candidate_id: SharedId
    role: AuditRole
    kind: AuditKind
    scope_slot: ScopeSlot | None
    source_anchor: ResolvedAnchor | None
    support_sentence_ids: tuple[str, ...] = Field(min_length=1, max_length=20)
    statement: ExactSpan


class RoleAwareAuditReport(_StrictModel):
    """Reconstructable original roles and diagnoses, never semantic approval."""

    profile: Literal["role-aware-audit-report-v1"]
    generation: AuditedGeneration
    source_sha256: Sha256
    generation_sha256: Sha256
    proposal: RoleAliasInput | LegacyRoleProposal
    proposal_sha256: Sha256
    change_coverage: Literal["available", "unavailable"]
    roles: tuple[AuditRole, ...] = Field(min_length=4, max_length=5)
    scope_slots: tuple[RoleAwareScopeSlots, ...] = Field(max_length=12)
    coverage_sha256: Sha256
    input: RoleAwareAuditInput
    issues: tuple[ResolvedRoleAwareAuditIssue, ...] = Field(max_length=144)
    status: AuditStatus


def _stored_markers(value: AuditedGeneration | dict[str, Any]) -> None:
    # Inspect actual fields directly; dumping first would silently restore defaults.
    def fields(node: Any) -> dict[str, Any]:
        if isinstance(node, BaseModel):
            node = node.__dict__
        if type(node) is not dict or not {"profile", "status"} <= node.keys():
            raise ValueError("Missing original identity markers")
        return node

    original = fields(value)
    _require_stored_generation_markers(original)
    frame = fields(original["frame"])
    if original["profile"] == "shared-role-aliases-v1":
        frame = fields(frame["frame"])
    fields(frame["candidate_index"])


def _checked_generation(source: Source, generation: AuditedGeneration) -> AuditedGeneration:
    _guard(source, Source)
    _guard(generation, AuditedGeneration)
    _stored_markers(generation)
    if type(generation) is RoleAliasGeneration:
        return validate_role_alias_generation(source, generation)
    if type(generation) is SharedContextGenerationV2:
        return validate_shared_context_generation_v2(source, generation)
    if type(generation) is CompactSharedContextGeneration:
        return validate_compact_shared_context_generation(source, generation)
    raise ValueError("Expected concrete generation")


def _frame(generation: AuditedGeneration) -> SharedMeasurementFrameV2:
    if type(generation) is RoleAliasGeneration:
        return generation.frame.frame
    return cast(SharedMeasurementFrameV2, generation.frame)


def _proposal(generation: AuditedGeneration) -> RoleAliasInput | LegacyRoleProposal:
    if type(generation) is RoleAliasGeneration:
        return generation.frame.input
    return _read(LegacyRoleProposal, _encode_shared_input(_frame(generation).input))


def _coverage(
    generation: AuditedGeneration,
) -> tuple[
    RoleAliasInput | LegacyRoleProposal,
    Literal["available", "unavailable"],
    tuple[AuditRole, ...],
    tuple[RoleAwareScopeSlots, ...],
]:
    proposal = _proposal(generation)
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
    available = type(generation) is RoleAliasGeneration
    return (
        proposal,
        "available" if available else "unavailable",
        ROLES if available else ROLES[:4],
        slots,
    )


def _hash(value: Any) -> str:
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _build(
    source: Source, generation: AuditedGeneration, data: RoleAwareAuditInput
) -> RoleAwareAuditReport:
    generation = _checked_generation(source, generation)
    proposal, coverage, roles, slots = _coverage(generation)
    selected = {b.number: b for b in proposal.bindings}
    if tuple(c.number for c in data.checks) != tuple(selected):
        raise ValueError("Checks must cover selected numbers exactly once in order")
    if not selected and (data.incomplete or data.issues):
        raise ValueError("Empty selection cannot have incomplete diagnosis")
    contexts = {c.id: c for c in proposal.contexts}
    events = {e.id: e for e in proposal.events}
    scopes = {s.number: {r.slot: r for r in s.scopes} for s in slots}
    index = _frame(generation).candidate_index
    positions = {s.sentence_id: i for i, s in enumerate(index.sentences)}
    candidates = {c.candidate_id: c for c in index.candidates}
    quotes = {q.citation_id: q.quote for q in index.citations}
    resolved: list[ResolvedRoleAwareAuditIssue] = []
    seen: set[tuple[Any, ...]] = set()
    for issue in data.issues:
        if issue.role not in roles:
            raise ValueError("Role outside original coverage")
        ids = issue.support
        start = positions[ids[0]]
        sentences = index.sentences[start : start + len(ids)]
        if tuple(s.sentence_id for s in sentences) != ids:
            raise ValueError("Support must be ordered contiguous current sentences")
        first, last = sentences[0].span, sentences[-1].span
        if any(s.span.citation_id != first.citation_id for s in sentences):
            raise ValueError("Support crosses quotes")
        statement = ExactSpan(
            citation_id=first.citation_id,
            start=first.start,
            end=last.end,
            text=quotes[first.citation_id][first.start : last.end],
        )
        location = None
        if issue.evidence is not None:
            anchor = ContextualAnchor(
                sentence_id=issue.evidence.s, text=issue.evidence.t, context_text=issue.evidence.c
            )
            if anchor.sentence_id not in ids:
                raise ValueError("Evidence outside support")
            _inside(statement, _broad(index, anchor).span)
            location = _resolve(index, anchor)
            _inside(statement, location.span)
        if issue.kind == "missing" and location is None:
            raise ValueError("Missing requires exact evidence")
        target_keys: set[tuple[str, ScopeSlot | None]] = set()
        for target in issue.targets:
            key = (target.number, target.slot)
            if key in target_keys:
                raise ValueError("Duplicate explicit target")
            target_keys.add(key)
            binding = selected[target.number]
            context = contexts[binding.context]
            if target.slot is not None and (
                issue.role != "target_scope" or target.slot not in scopes[target.number]
            ):
                raise ValueError("Slot must identify this number's current scope")
            if issue.kind == "missing" and target.slot is not None:
                raise ValueError("Missing must not target an existing slot")
            if issue.kind == "unsupported":
                if issue.role == "target_scope":
                    if target.slot is None:
                        raise ValueError("Unsupported scope requires current slot")
                else:
                    value = (
                        context.entity
                        if issue.role == "measured_entity"
                        else context.period
                        if issue.role == "period"
                        else events[context.event].actor
                        if issue.role == "reporting_actor"
                        else getattr(binding, "change", None)
                    )
                    if value is None:
                        raise ValueError("Unsupported requires nonnull original role")
            _inside(statement, candidates[target.number].expression)
            diagnosis = (target.number, issue.role, target.slot, location)
            if diagnosis in seen:
                raise ValueError("Duplicate or conflicting diagnosis location")
            seen.add(diagnosis)
            resolved.append(
                ResolvedRoleAwareAuditIssue(
                    candidate_id=target.number,
                    role=issue.role,
                    kind=issue.kind,
                    scope_slot=target.slot,
                    source_anchor=location,
                    support_sentence_ids=ids,
                    statement=statement,
                )
            )
    hard, uncertain = False, data.incomplete
    for check in data.checks:
        kinds = {i.kind for i in resolved if i.candidate_id == check.number}
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
    return RoleAwareAuditReport(
        profile="role-aware-audit-report-v1",
        generation=generation,
        source_sha256=index.source_sha256,
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
        issues=tuple(resolved),
        status=status,
    )


def build_role_aware_audit_report(
    source: Source, generation: AuditedGeneration, input: RoleAwareAuditInput | dict[str, Any]
) -> RoleAwareAuditReport:
    """Validate each explicit target without repairing or expanding the original proposal."""
    try:
        _guard(input, RoleAwareAuditInput)
        return _build(source, generation, _read(RoleAwareAuditInput, input))
    except Exception:
        raise RoleAwareAuditContractError("Invalid role aware audit input") from None


def validate_role_aware_audit_report(
    source: Source, report: RoleAwareAuditReport | dict[str, Any]
) -> RoleAwareAuditReport:
    """Reconstruct original concrete generation, full roles, coverage and every diagnosis."""
    try:
        _guard(report, RoleAwareAuditReport)
        _stored_markers(report["generation"] if isinstance(report, dict) else report.generation)
        checked = _read(RoleAwareAuditReport, report)
        expected = _build(source, checked.generation, checked.input)
        if checked != expected:
            raise ValueError("Stored report differs from reconstruction")
        return expected
    except Exception:
        raise RoleAwareAuditContractError("Invalid role aware audit report") from None
