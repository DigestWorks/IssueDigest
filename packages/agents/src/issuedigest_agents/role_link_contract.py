"""Pure explicit same-quote relation reports; locations never certify semantic truth."""

from typing import Annotated, Any, Literal, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field

from .balanced_role_generation import RoleAliasGenerationV2
from .contextual_anchor import ContextualAnchor
from .numeric_candidates import ExactSpan
from .numeric_candidates_v2 import NumericCandidateV2
from .numeric_evidence import Source, _StrictModel
from .numeric_selection_evaluation import _read
from .role_link_catalog import (
    MATRIX_ENCODING_VERSION,
    ROLE_LEGEND,
    ROLE_ORDER,
    STATE_LEGEND,
    RoleLinkCatalog,
    RoleLinkHint,
    _actual,
    _hash,
    _required_raw,
    build_role_link_catalog,
    role_link_encoding_metadata,
    validate_role_link_catalog,
)
from .role_table_packet import _copy_json, _same_json
from .semantic_role_audit_contract import _frame
from .shared_measurement_context_v2 import _broad, _resolve

type LinkRole = Literal[
    "measurement_scope",
    "measurement_period",
    "operator",
    "reporter",
    "entity_qualifier",
    "programme_identity",
    "comparison_baseline",
    "purpose",
]
type LinkState = Literal[
    "classified_roles", "explicitly_unrelated", "linkage_uncertain", "not_reviewed"
]
type LinkStatus = Literal[
    "not_applicable",
    "candidate_inventory_empty",
    "candidate_review_incomplete",
    "candidate_review_uncertain",
    "reviewed_candidates",
]
type Count = Annotated[int, Field(ge=0)]


class RoleLinkContractError(ValueError):
    """Sanitized whole-operation rejection with no source or partial report."""

    def __init__(self) -> None:
        super().__init__("Invalid role link contract")


class RoleLinkInput(_StrictModel):
    rows: tuple[str, ...]
    incomplete: bool


class RoleLinkDecision(_StrictModel):
    hint_id: str
    number: str
    state: LinkState
    roles: tuple[LinkRole, ...]
    quantity: ExactSpan
    hint: ExactSpan
    support: ExactSpan
    support_sentence_ids: tuple[str, ...]


class RoleLinkCoverage(_StrictModel):
    selected_numbers: Count
    total_hints: Count
    candidate_pairs: Count
    classified_pairs: Count
    unrelated_pairs: Count
    uncertain_pairs: Count
    unreviewed_pairs: Count


class RoleLinkReport(_StrictModel):
    profile: Literal["role-link-report-v1"]
    encoding_version: Literal["role-link-matrix-v1"]
    role_order: Literal["STOREIBP"]
    source_inventory_exhaustive: Literal[False]
    catalog: RoleLinkCatalog
    catalog_sha256: Sha256
    domain_sha256: Sha256
    encoding_sha256: Sha256
    input: RoleLinkInput
    decisions: tuple[RoleLinkDecision, ...]
    coverage: RoleLinkCoverage
    status: LinkStatus


def _original(value: Any, annotation: Any) -> None:
    if isinstance(value, BaseModel):
        _actual(value, annotation)
    else:
        _copy_json(value)
        _required_raw(value, annotation)


def _decode(cell: str) -> tuple[LinkState, tuple[LinkRole, ...]]:
    if cell in STATE_LEGEND:
        return cast(LinkState, STATE_LEGEND[cell]), ()
    if not cell or any(c not in ROLE_ORDER for c in cell):
        raise ValueError("Unknown relation cell")
    if cell != "".join(c for c in ROLE_ORDER if c in cell):
        raise ValueError("Roles must be unique and follow explicit role order")
    return "classified_roles", tuple(cast(LinkRole, ROLE_LEGEND[c]) for c in cell)


def _locations(
    catalog: RoleLinkCatalog, hint: RoleLinkHint, candidate: NumericCandidateV2
) -> tuple[ExactSpan, tuple[str, ...]]:
    index = _frame(catalog.generation).candidate_index
    anchor = ContextualAnchor(
        sentence_id=hint.anchor.s, text=hint.anchor.t, context_text=hint.anchor.c
    )
    located = _resolve(index, anchor).span
    context = _broad(index, anchor).span
    quantity = candidate.expression
    if located != hint.span or quantity.citation_id != located.citation_id:
        raise ValueError("Pair location differs from current quote")
    quote = next(q.quote for q in index.citations if q.citation_id == located.citation_id)
    for span in (quantity, located, context):
        if span.citation_id != located.citation_id or quote[span.start : span.end] != span.text:
            raise ValueError("Span differs from exact current source")
    left, right = min(quantity.start, context.start), max(quantity.end, context.end)
    sentences = tuple(
        s
        for s in index.sentences
        if s.span.citation_id == located.citation_id and s.span.start < right and s.span.end > left
    )
    if not sentences or sentences[0].span.start > left or sentences[-1].span.end < right:
        raise ValueError("Missing current covering sentences")
    if any(a.span.end != b.span.start for a, b in zip(sentences, sentences[1:], strict=False)):
        raise ValueError("Support is not contiguous")
    start, end = sentences[0].span.start, sentences[-1].span.end
    return ExactSpan(
        citation_id=located.citation_id, text=quote[start:end], start=start, end=end
    ), tuple(s.sentence_id for s in sentences)


def _reconstruct(catalog: RoleLinkCatalog, data: RoleLinkInput) -> RoleLinkReport:
    if len(data.rows) != len(catalog.hints):
        raise ValueError("Rows must cover every current hint in order")
    domains = {d.quote_id: d for d in catalog.domains}
    candidates = {c.candidate_id: c for c in _frame(catalog.generation).candidate_index.candidates}
    decisions: list[RoleLinkDecision] = []
    for hint, row in zip(catalog.hints, data.rows, strict=True):
        numbers = domains[hint.quote_id].numbers
        if not numbers:
            if row != "":
                raise ValueError("Zero columns require an empty row")
            continue
        cells = row.split(";")
        if len(cells) != len(numbers):
            raise ValueError("Columns must cover exact current quote domain")
        for number, cell in zip(numbers, cells, strict=True):
            state, roles = _decode(cell)
            if state == "not_reviewed" and not data.incomplete:
                raise ValueError("Unreviewed requires incomplete")
            candidate = candidates[number]
            support, sentence_ids = _locations(catalog, hint, candidate)
            decisions.append(
                RoleLinkDecision(
                    hint_id=hint.hint_id,
                    number=number,
                    state=state,
                    roles=roles,
                    quantity=candidate.expression,
                    hint=hint.span,
                    support=support,
                    support_sentence_ids=sentence_ids,
                )
            )
    selected = len(catalog.generation.frame.input.bindings)
    if not decisions and data.incomplete:
        raise ValueError("Zero-pair carrier must be complete")
    counts = {
        state: sum(d.state == state for d in decisions)
        for state in (
            "classified_roles",
            "explicitly_unrelated",
            "linkage_uncertain",
            "not_reviewed",
        )
    }
    status: LinkStatus = (
        "not_applicable"
        if not selected
        else "candidate_inventory_empty"
        if not decisions
        else "candidate_review_incomplete"
        if data.incomplete
        else "candidate_review_uncertain"
        if counts["linkage_uncertain"]
        else "reviewed_candidates"
    )
    return RoleLinkReport(
        profile="role-link-report-v1",
        encoding_version=cast(Literal["role-link-matrix-v1"], MATRIX_ENCODING_VERSION),
        role_order=cast(Literal["STOREIBP"], ROLE_ORDER),
        source_inventory_exhaustive=False,
        catalog=catalog,
        catalog_sha256=_hash(catalog.model_dump(mode="json")),
        domain_sha256=_hash([d.model_dump(mode="json") for d in catalog.domains]),
        encoding_sha256=_hash(role_link_encoding_metadata()),
        input=data,
        decisions=tuple(decisions),
        coverage=RoleLinkCoverage(
            selected_numbers=selected,
            total_hints=len(catalog.hints),
            candidate_pairs=len(decisions),
            classified_pairs=counts["classified_roles"],
            unrelated_pairs=counts["explicitly_unrelated"],
            uncertain_pairs=counts["linkage_uncertain"],
            unreviewed_pairs=counts["not_reviewed"],
        ),
        status=status,
    )


def build_role_link_report(
    source: Source, generation: RoleAliasGenerationV2, data: RoleLinkInput | dict[str, Any]
) -> RoleLinkReport:
    """Decode every explicit cell and reconstruct full current same-quote locations."""
    try:
        # Guard all originals before any dependency can serialize a different input.
        _actual(source, Source)
        _actual(generation, RoleAliasGenerationV2)
        _original(data, RoleLinkInput)
        catalog = build_role_link_catalog(source, generation)
        return _reconstruct(catalog, _read(RoleLinkInput, data))
    except Exception:
        raise RoleLinkContractError() from None


def validate_role_link_report(
    source: Source, result: RoleLinkReport | dict[str, Any]
) -> RoleLinkReport:
    """Rebuild the original catalog and every report field from current source."""
    try:
        _actual(source, Source)
        _original(result, RoleLinkReport)
        original = result.catalog if isinstance(result, BaseModel) else result["catalog"]
        catalog = validate_role_link_catalog(source, original)
        checked = _read(RoleLinkReport, result)
        expected = _reconstruct(catalog, checked.input)
        canonical = expected.model_dump(mode="json")
        _same_json(checked.model_dump(mode="json"), canonical)
        if type(result) is dict:
            _same_json(result, canonical)
        return expected
    except Exception:
        raise RoleLinkContractError() from None
