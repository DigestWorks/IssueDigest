"""Pure selected-anchor references; lexical overlap never certifies semantic coverage."""

from typing import Annotated, Any, Literal, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field

from .contextual_anchor import ContextualAnchor
from .numeric_candidates import ExactSpan
from .numeric_evidence import Source, _StrictModel
from .numeric_selection_evaluation import _read
from .role_alias_contract import RoleAliasAnchor
from .role_link_catalog import _actual, _hash
from .role_link_contract import LinkRole, LinkState, _original
from .role_link_sdk import RoleLinkGeneration, validate_role_link_generation
from .role_table_packet import _same_json
from .semantic_role_audit_contract import _frame
from .shared_measurement_context_v2 import _resolve

type ReferenceField = Literal[
    "entity",
    "period",
    "condition",
    "purpose",
    "basis",
    "baseline",
    "context_scope",
    "binding_scope",
    "reporting_actor",
    "reporting_predicate",
    "change_evidence",
    "relation_cue",
    "quantity",
    "status_context",
]
type ReferenceCategory = Literal["primary", "auxiliary"]
type ReferenceOverlap = Literal["exact", "contains", "partial"]
type LexicalStatus = Literal[
    "exact_reference",
    "containing_reference",
    "partial_reference",
    "no_reference_in_selected_fields",
]
type Count = Annotated[int, Field(ge=0)]

_CONTEXT_FIELDS = ("entity", "period", "condition", "purpose", "basis", "baseline")


class RoleReferenceCoverageError(ValueError):
    """Sanitized whole-operation rejection without source or partial output."""

    def __init__(self) -> None:
        super().__init__("Invalid role reference coverage")


class ReferenceCarrier(_StrictModel):
    carrier_id: str
    number: str
    path: str
    field: ReferenceField
    category: ReferenceCategory
    span: ExactSpan


class ReferenceWitness(_StrictModel):
    carrier_id: str
    overlap: ReferenceOverlap


class ReferenceRow(_StrictModel):
    hint_id: str
    number: str
    link_state: LinkState
    roles: tuple[LinkRole, ...]
    hint: ExactSpan
    lexical_status: LexicalStatus
    matches: tuple[ReferenceWitness, ...]
    auxiliary: tuple[ReferenceWitness, ...]
    other_facts: tuple[ReferenceWitness, ...]
    semantic_equivalence: Literal["not_assessed"]
    materiality: Literal["not_assessed"]


class ReferenceCoverageCounts(_StrictModel):
    selected_numbers: Count
    total_hints: Count
    candidate_pairs: Count
    exact_reference: Count
    containing_reference: Count
    partial_reference: Count
    no_reference_in_selected_fields: Count
    primary_carriers: Count
    auxiliary_carriers: Count


class RoleReferenceCoverage(_StrictModel):
    profile: Literal["role-reference-coverage-v1"]
    rules_version: Literal["selected-anchor-overlap-v1"]
    status: Literal["unreviewed"]
    source_inventory_exhaustive: Literal[False]
    semantic_approval: Literal[False]
    semantic_equivalence: Literal["not_assessed"]
    materiality: Literal["not_assessed"]
    original_link: RoleLinkGeneration
    original_link_sha256: Sha256
    rules_sha256: Sha256
    carriers: tuple[ReferenceCarrier, ...]
    rows: tuple[ReferenceRow, ...]
    coverage: ReferenceCoverageCounts


def role_reference_rules() -> dict[str, Any]:
    """Return fresh complete JSON rules, independent of mutable caller state."""
    return dict(
        rules_version="selected-anchor-overlap-v1",
        primary=[
            *[dict(field=key, path=f"contexts/{{context.id}}/{key}") for key in _CONTEXT_FIELDS],
            dict(field="context_scope", path="contexts/{context.id}/scopes/{zeroindex}/anchor"),
            dict(field="binding_scope", path="bindings/{number}/scopes/{zeroindex}/anchor"),
            dict(field="reporting_actor", path="events/{event.id}/actor"),
        ],
        auxiliary=[
            dict(field="reporting_predicate", path="events/{event.id}/predicate"),
            dict(field="change_evidence", path="bindings/{number}/change/evidence"),
            dict(field="relation_cue", path="relations/{zeroindex}/cue"),
            dict(field="quantity", path="quantities/{number}/expression"),
            dict(field="status_context", path="bindings/{number}/status_sentence"),
        ],
        routing="binding.context then context.event; direct relation from OR to endpoints only; "
        "no implicit sharing, inherited scopes, or transitive relation propagation",
        resolution="strict current ContextualAnchor(s,t,c); select narrow t span only; "
        "c disambiguates and is excluded; skip only null anchors; quantity uses current full "
        "candidate.expression; status_context uses current full selected sentence.span",
        inventory_order="original binding order, primary then auxiliary field order, original "
        "scope/relation order; global c1 onward; no dedup even shared path/span across owners "
        "or repeated positions in different fields",
        overlap=dict(
            citation="same citation_id required",
            exact="carrier.start == hint.start and carrier.end == hint.end",
            contains="carrier.start <= hint.start and carrier.end >= hint.end after exact",
            partial="max(starts) < min(ends) after exact and contains; touching is excluded",
            priority=[
                "exact_reference",
                "containing_reference",
                "partial_reference",
                "no_reference_in_selected_fields",
            ],
        ),
        witnesses=dict(
            matches="same number and primary",
            auxiliary="same number and auxiliary",
            other_facts="different number regardless of primary or auxiliary category",
            order="all overlaps in inventory order in each destination; no cap or best-only filter",
        ),
        rows="all original decisions in original order including classified_roles, "
        "explicitly_unrelated, linkage_uncertain, not_reviewed; preserve hint/number/roles/state",
        counts="sum every row/status and inventory/category; selected_numbers/total_hints "
        "from original coverage; empty selection or zero pairs still validates full original",
        exclusions=[
            "support",
            "statement",
            "title",
            "metadata",
            "scope kind as correctness",
            "unselected context/event",
            "string search",
            "normalization",
            "paraphrase",
            "equal text at different occurrences",
            "group completion from fragments",
        ],
        semantics="unreviewed; source_inventory_exhaustive=false; semantic_approval=false; "
        "semantic_equivalence/materiality=not_assessed; no hard missing, semantic preserved, "
        "truth, role correction, approval, repair, or model calls",
    )


def _carriers(link: RoleLinkGeneration) -> tuple[ReferenceCarrier, ...]:
    generation = link.report.catalog.generation
    proposal = generation.frame.input
    index = _frame(generation).candidate_index
    contexts = {c.id: c for c in proposal.contexts}
    events = {e.id: e for e in proposal.events}
    candidates = {c.candidate_id: c for c in index.candidates}
    sentences = {s.sentence_id: s for s in index.sentences}
    inventory: list[ReferenceCarrier] = []

    def append(
        number: str, path: str, field: ReferenceField, category: ReferenceCategory, span: ExactSpan
    ) -> None:
        inventory.append(
            ReferenceCarrier(
                carrier_id=f"c{len(inventory) + 1}",
                number=number,
                path=path,
                field=field,
                category=category,
                span=span,
            )
        )

    def anchor(
        number: str,
        path: str,
        field: ReferenceField,
        category: ReferenceCategory,
        value: RoleAliasAnchor | None,
    ) -> None:
        if value is not None:
            span = _resolve(
                index,
                ContextualAnchor(
                    sentence_id=value.s,
                    text=value.t,
                    context_text=value.c,
                ),
            ).span
            append(number, path, field, category, span)

    for binding in proposal.bindings:
        number = binding.number
        context = contexts[binding.context]
        event = events[context.event]
        for key in _CONTEXT_FIELDS:
            anchor(
                number,
                f"contexts/{context.id}/{key}",
                cast(ReferenceField, key),
                "primary",
                getattr(context, key),
            )
        for i, scope in enumerate(context.scopes):
            anchor(
                number,
                f"contexts/{context.id}/scopes/{i}/anchor",
                "context_scope",
                "primary",
                scope.anchor,
            )
        for i, scope in enumerate(binding.scopes):
            anchor(
                number,
                f"bindings/{number}/scopes/{i}/anchor",
                "binding_scope",
                "primary",
                scope.anchor,
            )
        anchor(number, f"events/{event.id}/actor", "reporting_actor", "primary", event.actor)
        anchor(
            number,
            f"events/{event.id}/predicate",
            "reporting_predicate",
            "auxiliary",
            event.predicate,
        )
        if binding.change is not None:
            anchor(
                number,
                f"bindings/{number}/change/evidence",
                "change_evidence",
                "auxiliary",
                binding.change.evidence,
            )
        for i, relation in enumerate(proposal.relations):
            if number in (relation.from_, relation.to):
                anchor(number, f"relations/{i}/cue", "relation_cue", "auxiliary", relation.cue)
        append(
            number,
            f"quantities/{number}/expression",
            "quantity",
            "auxiliary",
            candidates[number].expression,
        )
        if binding.status_sentence is not None:
            append(
                number,
                f"bindings/{number}/status_sentence",
                "status_context",
                "auxiliary",
                sentences[binding.status_sentence].span,
            )
    return tuple(inventory)


def _overlap(carrier: ExactSpan, hint: ExactSpan) -> ReferenceOverlap | None:
    if carrier.citation_id != hint.citation_id:
        return None
    if carrier.start == hint.start and carrier.end == hint.end:
        return "exact"
    if carrier.start <= hint.start and carrier.end >= hint.end:
        return "contains"
    if max(carrier.start, hint.start) < min(carrier.end, hint.end):
        return "partial"
    return None


def _reconstruct(link: RoleLinkGeneration) -> RoleReferenceCoverage:
    carriers = _carriers(link)
    rows: list[ReferenceRow] = []
    for decision in link.report.decisions:
        matches: list[ReferenceWitness] = []
        auxiliary: list[ReferenceWitness] = []
        other_facts: list[ReferenceWitness] = []
        for carrier in carriers:
            overlap = _overlap(carrier.span, decision.hint)
            if overlap is None:
                continue
            destination = (
                other_facts
                if carrier.number != decision.number
                else matches
                if carrier.category == "primary"
                else auxiliary
            )
            destination.append(ReferenceWitness(carrier_id=carrier.carrier_id, overlap=overlap))
        overlaps = {w.overlap for w in matches}
        status: LexicalStatus = (
            "exact_reference"
            if "exact" in overlaps
            else "containing_reference"
            if "contains" in overlaps
            else "partial_reference"
            if "partial" in overlaps
            else "no_reference_in_selected_fields"
        )
        rows.append(
            ReferenceRow(
                hint_id=decision.hint_id,
                number=decision.number,
                link_state=decision.state,
                roles=decision.roles,
                hint=decision.hint,
                lexical_status=status,
                matches=tuple(matches),
                auxiliary=tuple(auxiliary),
                other_facts=tuple(other_facts),
                semantic_equivalence="not_assessed",
                materiality="not_assessed",
            )
        )
    return RoleReferenceCoverage(
        profile="role-reference-coverage-v1",
        rules_version="selected-anchor-overlap-v1",
        status="unreviewed",
        source_inventory_exhaustive=False,
        semantic_approval=False,
        semantic_equivalence="not_assessed",
        materiality="not_assessed",
        original_link=link,
        original_link_sha256=_hash(link.model_dump(mode="json")),
        rules_sha256=_hash(role_reference_rules()),
        carriers=carriers,
        rows=tuple(rows),
        coverage=ReferenceCoverageCounts(
            selected_numbers=link.report.coverage.selected_numbers,
            total_hints=link.report.coverage.total_hints,
            candidate_pairs=len(rows),
            exact_reference=sum(r.lexical_status == "exact_reference" for r in rows),
            containing_reference=sum(r.lexical_status == "containing_reference" for r in rows),
            partial_reference=sum(r.lexical_status == "partial_reference" for r in rows),
            no_reference_in_selected_fields=sum(
                r.lexical_status == "no_reference_in_selected_fields" for r in rows
            ),
            primary_carriers=sum(c.category == "primary" for c in carriers),
            auxiliary_carriers=sum(c.category == "auxiliary" for c in carriers),
        ),
    )


def build_role_reference_coverage(
    source: Source, link: RoleLinkGeneration | dict[str, Any]
) -> RoleReferenceCoverage:
    """Validate the original current source/link, then derive every carrier and row."""
    try:
        _actual(source, Source)
        _original(link, RoleLinkGeneration)
        return _reconstruct(validate_role_link_generation(source, link))
    except Exception:
        raise RoleReferenceCoverageError() from None


def validate_role_reference_coverage(
    source: Source, result: RoleReferenceCoverage | dict[str, Any]
) -> RoleReferenceCoverage:
    """Guard original types before serialization and reconstruct the entire report."""
    try:
        _actual(source, Source)
        _original(result, RoleReferenceCoverage)
        original = (
            result.original_link if isinstance(result, BaseModel) else result["original_link"]
        )
        link = validate_role_link_generation(source, original)
        checked = _read(RoleReferenceCoverage, result)
        expected = _reconstruct(link)
        canonical = expected.model_dump(mode="json")
        _same_json(checked.model_dump(mode="json"), canonical)
        if type(result) is dict:
            _same_json(result, canonical)
        return expected
    except Exception:
        raise RoleReferenceCoverageError() from None
