"""Pure deterministic surface hints and explicit domains; never semantic coverage."""

import re
from hashlib import sha256
from types import MappingProxyType, UnionType
from typing import Annotated, Any, Literal, TypeAliasType, Union, cast, get_args, get_origin

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel

from .balanced_role_generation import RoleAliasGenerationV2, validate_balanced_role_generation
from .contextual_anchor import ContextualAnchor
from .numeric_candidates import ExactSpan, SentenceCandidate
from .numeric_evidence import Source, _json, _StrictModel
from .numeric_selection_evaluation import _read
from .role_alias_contract import RoleAliasAnchor, _guard
from .role_table_packet import _copy_json, _original_values, _same_json, build_role_table_packet
from .semantic_role_audit_contract import _checked_generation, _frame
from .shared_measurement_context_v2 import _resolve

ROLE_ORDER = "STOREIBP"
MATRIX_ENCODING_VERSION = "role-link-matrix-v1"
ROLE_LEGEND = MappingProxyType(
    dict(
        S="measurement_scope",
        T="measurement_period",
        O="operator",
        R="reporter",
        E="entity_qualifier",
        I="programme_identity",
        B="comparison_baseline",
        P="purpose",
    )
)
STATE_LEGEND = MappingProxyType(
    {
        "-": "explicitly_unrelated",
        "?": "linkage_uncertain",
        "_": "not_reviewed",
    }
)
_PATTERNS = (
    ("dot_list", r"[가-힣A-Za-z0-9]+(?:·[가-힣A-Za-z0-9]+)+"),
    ("year_surface", r"[0-9]{1,4}년(?:간|까지|부터)?"),
    ("relative_time_surface", r"(?:올해(?:\s*[0-9]+월(?:부터|까지)?)?|전년도(?:\s*대비)?|현재)"),
    (
        "institution_suffix_surface",
        r"[가-힣]+(?:부|청|공단|위원회|정부|대학)(?=[은는이가을를의에과와]|으로|에서|로|[^가-힣]|$)",
    ),  # noqa: E501
    (
        "place_suffix_surface",
        r"[가-힣]+(?:특별자치도|특별시|광역시|도|시|군|구)(?=[은는이가을를의에과와]|으로|에서|로|[^가-힣]|$)",
    ),  # noqa: E501
    ("quoted_phrase", r"'[^'\n]+'|‘[^’\n]+’|｢[^｣\n]+｣"),
)
_MEMBER_PATTERN = r"[^·]+"
_MAX_HINTS = 24
_MAX_ANCHOR = 1000

type HintOrigin = Literal[
    "dot_list",
    "dot_member",
    "year_surface",
    "relative_time_surface",
    "institution_suffix_surface",
    "place_suffix_surface",
    "quoted_phrase",
]
type CatalogFailure = Literal["invalid_input", "candidate_overflow", "unlocatable_hint"]


class RoleLinkCatalogError(ValueError):
    """Sanitized whole-operation failure without a source or partial inventory."""

    def __init__(self, reason: CatalogFailure = "invalid_input") -> None:
        self.reason = reason
        super().__init__(f"Role link catalog rejected: {reason}")


class RoleLinkHint(_StrictModel):
    hint_id: str
    quote_id: str
    anchor: RoleAliasAnchor
    span: ExactSpan
    origins: tuple[HintOrigin, ...]


class RoleLinkDomain(_StrictModel):
    quote_id: str
    numbers: tuple[str, ...]
    hints: tuple[str, ...]


class RoleLinkCatalog(_StrictModel):
    profile: Literal["role-link-catalog-v1"]
    rules_version: Literal["surface-role-hints-v1"]
    source_inventory_exhaustive: Literal[False]
    generation: RoleAliasGenerationV2
    generation_sha256: Sha256
    source_packet_sha256: Sha256
    rules_sha256: Sha256
    hints: tuple[RoleLinkHint, ...]
    domains: tuple[RoleLinkDomain, ...]


def role_link_encoding_metadata() -> dict[str, Any]:
    """Return fresh complete matrix encoding metadata, independent of object key order."""
    return dict(
        encoding_version=MATRIX_ENCODING_VERSION,
        role_order=ROLE_ORDER,
        role_legend=dict(ROLE_LEGEND),
        state_legend=dict(STATE_LEGEND),
    )


def _rules() -> dict[str, Any]:
    return dict(
        rules_version="surface-role-hints-v1",
        patterns=[list(p) for p in _PATTERNS],
        dot_member_pattern=_MEMBER_PATTERN,
        max_hints_per_quote=_MAX_HINTS,
        max_anchor_length=_MAX_ANCHOR,
        occurrence_count="overlapping-exact-codepoints",
        context="null-if-unique-else-increasing-extra-length-then-left-position;"
        "phrase-once-in-context-and-context-once-in-sentence;strict-locator-exact-position",
        ordering="current-sentence-order-then-start-end;global-m1;original-quote-order-q1",
        dedup="same-quote-sentence-start-end-only;sorted-origins;overflow-before-location",
    )


def _hash(value: Any) -> str:
    return sha256(_json(value).encode("utf-8")).hexdigest()


def _actual(value: Any, annotation: Any) -> None:
    _guard(value, annotation)
    _original_values(value, annotation)


def _required_raw(value: Any, annotation: Any) -> None:
    """Require every original JSON field before defaults or serialization can restore it."""
    if isinstance(annotation, TypeAliasType):
        _required_raw(value, annotation.__value__)
        return
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        _required_raw(value, args[0])
    elif origin in (Union, UnionType):
        for option in args:
            try:
                _required_raw(value, option)
                return
            except ValueError:
                pass
        raise ValueError("No exact raw union branch")
    elif isinstance(annotation, type) and issubclass(annotation, BaseModel):
        if type(value) is not dict:
            raise ValueError("Expected raw model object")
        fields = annotation.model_fields
        names = {field.alias or name for name, field in fields.items()}
        if value.keys() != names:
            raise ValueError("Missing or extra raw model fields")
        for name, field in fields.items():
            _required_raw(value[field.alias or name], field.annotation)
    elif origin is tuple:
        if type(value) is not list:
            raise ValueError("Expected raw JSON array")
        if args[-1] is not Ellipsis and len(value) != len(args):
            raise ValueError("Wrong raw tuple length")
        for i, child in enumerate(value):
            _required_raw(child, args[0] if args[-1] is Ellipsis else args[i])
    elif origin is Literal:
        if not any(type(value) is type(option) and value == option for option in args):
            raise ValueError("Wrong raw literal")
    elif annotation in (str, int, bool, float, type(None)) and type(value) is not annotation:
        raise ValueError("Wrong raw scalar")


def _once(text: str, phrase: str) -> bool:
    start = text.find(phrase)
    return start >= 0 and text.find(phrase, start + 1) < 0


def _context(text: str, start: int, end: int) -> str | None:
    phrase = text[start:end]
    if len(phrase) > _MAX_ANCHOR:
        raise RoleLinkCatalogError("unlocatable_hint")
    if _once(text, phrase):
        return None
    for extra in range(1, min(_MAX_ANCHOR, len(text)) - len(phrase) + 1):
        length = len(phrase) + extra
        for left in range(max(0, start - extra), min(start, len(text) - length) + 1):
            context = text[left : left + length]
            if _once(context, phrase) and _once(text, context):
                return context
    raise RoleLinkCatalogError("unlocatable_hint")


def _build(source: Source, generation: RoleAliasGenerationV2) -> RoleLinkCatalog:
    _actual(source, Source)
    _actual(generation, RoleAliasGenerationV2)
    generation = _checked_generation(source, generation)
    source_packet = build_role_table_packet(source, generation)
    index = _frame(generation).candidate_index
    quotes = {c.citation_id: f"q{i}" for i, c in enumerate(index.citations, 1)}
    counts = dict.fromkeys(quotes, 0)
    inventory: list[tuple[SentenceCandidate, int, int, tuple[HintOrigin, ...]]] = []
    for sentence in index.sentences:
        positions: dict[tuple[int, int], set[HintOrigin]] = {}
        for label, pattern in _PATTERNS:
            for match in re.finditer(pattern, sentence.span.text):
                positions.setdefault(match.span(), set()).add(cast(HintOrigin, label))
                if label == "dot_list":
                    for member in re.finditer(_MEMBER_PATTERN, match.group()):
                        key = (match.start() + member.start(), match.start() + member.end())
                        positions.setdefault(key, set()).add("dot_member")
        counts[sentence.span.citation_id] += len(positions)
        for (start, end), labels in sorted(positions.items()):
            inventory.append((sentence, start, end, tuple(sorted(labels))))
    if any(count > _MAX_HINTS for count in counts.values()):
        raise RoleLinkCatalogError("candidate_overflow")
    hints: list[RoleLinkHint] = []
    for sentence, start, end, origins in inventory:
        try:
            text = sentence.span.text[start:end]
            context = _context(sentence.span.text, start, end)
            anchor = RoleAliasAnchor(s=sentence.sentence_id, t=text, c=context)
            resolved = _resolve(
                index, ContextualAnchor(sentence_id=anchor.s, text=anchor.t, context_text=anchor.c)
            )
            span = ExactSpan(
                citation_id=sentence.span.citation_id,
                text=text,
                start=sentence.span.start + start,
                end=sentence.span.start + end,
            )
            if resolved.span != span:
                raise ValueError("Locator changed original position")
            hints.append(
                RoleLinkHint(
                    hint_id=f"m{len(hints) + 1}",
                    quote_id=quotes[span.citation_id],
                    anchor=anchor,
                    span=span,
                    origins=origins,
                )
            )
        except Exception:
            raise RoleLinkCatalogError("unlocatable_hint") from None
    candidates = {c.candidate_id: c for c in index.candidates}
    domains = tuple(
        RoleLinkDomain(
            quote_id=qid,
            numbers=tuple(
                b.number
                for b in generation.frame.input.bindings
                if candidates[b.number].expression.citation_id == cid
            ),
            hints=tuple(h.hint_id for h in hints if h.quote_id == qid),
        )
        for cid, qid in quotes.items()
    )
    return RoleLinkCatalog(
        profile="role-link-catalog-v1",
        rules_version="surface-role-hints-v1",
        source_inventory_exhaustive=False,
        generation=generation,
        generation_sha256=_hash(generation.model_dump(mode="json")),
        source_packet_sha256=_hash(source_packet),
        rules_sha256=_hash(_rules()),
        hints=tuple(hints),
        domains=domains,
    )


def build_role_link_catalog(source: Source, generation: RoleAliasGenerationV2) -> RoleLinkCatalog:
    """Rebuild every lexical hint and same-quote domain from complete current source."""
    try:
        return _build(source, generation)
    except RoleLinkCatalogError:
        raise
    except Exception:
        raise RoleLinkCatalogError() from None


def validate_role_link_catalog(
    source: Source,
    result: RoleLinkCatalog | dict[str, Any],
) -> RoleLinkCatalog:
    """Reconstruct the complete catalog after guarding original raw or actual values."""
    try:
        _actual(source, Source)
        if isinstance(result, BaseModel):
            _actual(result, RoleLinkCatalog)
            original = result.generation
        else:
            _copy_json(result)
            _required_raw(result, RoleLinkCatalog)
            original = result["generation"]
        # Inspect/reconstruct the ORIGINAL generation before dumping the catalog.
        generation = validate_balanced_role_generation(source, original)
        checked = _read(RoleLinkCatalog, result)
        expected = _build(source, generation)
        _same_json(checked.model_dump(mode="json"), expected.model_dump(mode="json"))
        if type(result) is dict:
            _same_json(result, expected.model_dump(mode="json"))
        return expected
    except RoleLinkCatalogError:
        raise
    except Exception:
        raise RoleLinkCatalogError() from None


def role_link_packet(source: Source, generation: RoleAliasGenerationV2) -> dict[str, Any]:
    """Project only a freshly rebuilt catalog; retain the full existing table packet."""
    try:
        catalog = _build(source, generation)
        return dict(
            profile="role-link-review-v1",
            source_packet=build_role_table_packet(source, generation),
            hint_table=dict(
                columns=["id", "quote_id", "s", "t", "c"],
                rows=[
                    [h.hint_id, h.quote_id, h.anchor.s, h.anchor.t, h.anchor.c]
                    for h in catalog.hints
                ],
            ),
            domains=[d.model_dump(mode="json") for d in catalog.domains],
            role_legend=dict(ROLE_LEGEND),
            role_order=ROLE_ORDER,
            state_legend=dict(STATE_LEGEND),
            source_inventory_exhaustive=False,
        )
    except RoleLinkCatalogError:
        raise
    except Exception:
        raise RoleLinkCatalogError() from None
