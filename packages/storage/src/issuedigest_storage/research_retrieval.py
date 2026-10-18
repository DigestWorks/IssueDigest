"""Bounded question retrieval over the verified, workspace-scoped literal index.

This is lexical retrieval from stored projections, not web or semantic search.
The interface isolates the strategy so retrieval can improve without changing requests.
"""

import re
from collections import Counter
from dataclasses import dataclass
from uuid import UUID

from issuedigest_domain import EvidenceSearchQuery, build_search_projection, literal_ngrams
from issuedigest_domain.search import ascii_fold
from sqlalchemy import Connection, and_, func, or_, select

from .repository import EvidenceRepository, StorageCorruption
from .schema import evidence_snapshots
from .search import _check_manifest, _scope, _unit_values
from .search_schema import projections, units

RETRIEVAL_PROFILE = "question-topics-ko-v2"

# Presentation words affect query interpretation only. They do not authorize reuse.
_PRESENTATION = frozenset("비교 비교해줘 비교해주세요 정리 정리해줘 정리해주세요".split())
# Only these six ASCII whitespace characters may disappear for whole-string matching.
_SPACES = " \t\n\r\f\v"
_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_LOWER = "abcdefghijklmnopqrstuvwxyz"

_GENERIC = frozenset(
    "질문 무엇 무엇인가 무엇인가요 무엇인지 무슨 어떤 어떻게 왜 알려줘 알려주세요 "
    "설명 설명해줘 설명해주세요 요약 요약해줘 요약해주세요 자세히 더 좀 해줘 주세요 "
    "그다음 다음 그럼 그러면 그래서 이것 이거 그것 그거 그 이 저 것 다시 "
    "의미 의미인가 의미인가요 자료 내용 "
    "대해 대한 관련 소식 최근 현재 what why how please explain summarize the a an is are "
    "this that it and or about".split()
)
_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+(?:\.[0-9]+)?%?")
# Preserve Unicode word/number identity for retrieval; never reinterpret ２０２６년 as 년.
# The conservative follow-up recognizer below deliberately retains its old grammar.
_TOPIC_TOKEN_PATTERN = re.compile(r"[^\W_]+(?:\.\d+[^\W_]*)?%?")
# Only known prose punctuation may disappear when deciding whether to reuse evidence.
# Unsupported words, symbols and hidden controls must never become a generic follow-up.
_FOLLOWUP_PUNCTUATION = frozenset("?!.,;:()[]{}'\"‘’“”…，。！？、-–—")
_PARTICLES = (
    "에서는",
    "으로는",
    "에게는",
    "에서",
    "으로",
    "처럼",
    "부터",
    "까지",
    "에는",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "와",
    "과",
    "도",
    "만",
)
# These literal endings keep an explicit unit when a numeric base loses 만/도.
# Unknown mixed quantities keep their full original; no numeric parsing/conversion.
_RETAINED_NUMERIC_UNIT_ENDINGS = ("원", "년", "월", "일", "명", "개", "건", "회", "도", "%")


def _tokens(question: str) -> tuple[str, ...]:
    tokens = []
    for token in _TOKEN_PATTERN.findall(question):
        term = ascii_fold(token)
        if term not in _GENERIC and re.fullmatch(r"[가-힣]+", term):
            for suffix in _PARTICLES:
                if term.endswith(suffix) and len(term) - len(suffix) >= 2:
                    term = term[: -len(suffix)]
                    break
        tokens.append(term)
    return tuple(tokens)


def question_terms(question: str) -> tuple[str, ...]:
    """Preserve up to eight original topics, separate from presentation requests."""
    terms = dict.fromkeys(
        ascii_fold(raw)
        for raw in _TOPIC_TOKEN_PATTERN.findall(question)
        if 1 <= len(raw) <= 64
        and not (_TOKEN_PATTERN.fullmatch(raw) is not None and _tokens(raw)[0] in _GENERIC)
        and ascii_fold(raw) not in _PRESENTATION
    )
    return tuple(terms)[:8]


def is_generic_followup(question: str) -> bool:
    """Unknown/oversized tokens are new topics, never permission to reuse old evidence."""
    tokens = _tokens(question)
    unmatched = _TOKEN_PATTERN.sub("", question)
    return (
        bool(tokens)
        and all(token in _GENERIC for token in tokens)
        and all(char.isspace() or char in _FOLLOWUP_PUNCTUATION for char in unmatched)
    )


def topic_variants(term: str) -> tuple[str, ...]:
    """Keep the original and at most one known particle removal, including AI/2026년."""
    variants = [term]
    for suffix in _PARTICLES:
        if term.endswith(suffix) and len(term) - len(suffix) >= 2:
            stem = term[: -len(suffix)]
            # A numeral anywhere in a mixed base can introduce magnitude/temperature
            # (1천만, 10여만). Strip ambiguous 만/도 only after a retained literal unit.
            ambiguous_quantity = (
                suffix in {"만", "도"}
                and any(char.isnumeric() for char in stem)
                and not stem.endswith(_RETAINED_NUMERIC_UNIT_ENDINGS)
            )
            if not ambiguous_quantity:
                variants.append(stem)
            break
    return tuple(variants)


@dataclass(frozen=True)
class VariantCandidates:
    """Internal diagnostics; truncation is a bounded-index limitation, not absence."""

    snapshot_ids: tuple[UUID, ...]
    direct_snapshot_ids: frozenset[UUID]
    scanned_candidates: int
    truncated: bool


def variant_candidates(
    conn: Connection,
    workspace_id: UUID,
    term: str,
    *,
    original_terms: tuple[str, ...] | None = None,
) -> VariantCandidates:
    """Round-robin up to 200 actually matching units; canonical-check before selection.

    The 201st row detects truncation. Existing projection ngrams only prefilter;
    ASCII-folded literal or explicit-whitespace-compacted full strings must match.
    Direct-match eligibility includes every supplied original in the topic group.
    No compacted offsets or selectors leave this internal strategy.
    """
    query = EvidenceSearchQuery(terms=(term,))
    if "\x00" in term:
        return VariantCandidates((), frozenset(), 0, False)
    folded = ascii_fold(term)
    originals_to_match = tuple(ascii_fold(value) for value in (original_terms or (term,)))
    compact = folded.translate(str.maketrans("", "", _SPACES))
    body = func.translate(units.c.text, _UPPER, _LOWER)
    direct = func.strpos(body, folded) > 0
    # A compact match can cross whitespace, so only unigram requirements are safe.
    required = sorted({gram for gram in literal_ngrams(compact) if len(gram) == 1})
    actual = direct
    if len(compact) >= 4:
        actual = or_(direct, func.strpos(func.translate(body, _SPACES, ""), compact) > 0)
    scoped, predicates = _scope(workspace_id, query)
    joined = scoped.join(
        projections,
        and_(
            projections.c.workspace_id == workspace_id,
            projections.c.snapshot_id == evidence_snapshots.c.snapshot_id,
        ),
    ).join(
        units,
        and_(
            units.c.workspace_id == workspace_id,
            units.c.snapshot_id == evidence_snapshots.c.snapshot_id,
        ),
    )
    balanced = (
        select(
            *units.c,
            direct.label("direct"),
            func.row_number()
            .over(partition_by=units.c.snapshot_id, order_by=units.c.ordinal)
            .label("depth"),
        )
        .select_from(joined)
        .where(*predicates, units.c.ngrams.contains(required), actual)
        .subquery()
    )
    rows = (
        conn.execute(
            select(balanced)
            .order_by(balanced.c.depth, balanced.c.snapshot_id, balanced.c.ordinal)
            .limit(201)
        )
        .mappings()
        .all()
    )
    matched: set[UUID] = set()
    originals: set[UUID] = set()
    current = None
    bundle = projection = None
    # Group only the bounded fetched rows, releasing each canonical before the next.
    for row in sorted(rows[:200], key=lambda r: (str(r["snapshot_id"]), r["ordinal"])):
        identity = row["snapshot_id"]
        if current != identity:
            bundle = projection = None
            bundle = EvidenceRepository._load(conn, workspace_id, identity)
            if bundle is None:
                raise StorageCorruption("Stored search evidence is inconsistent")
            try:
                projection = build_search_projection(bundle)
            except ValueError:
                raise StorageCorruption("Stored search projection is inconsistent") from None
            manifest = (
                conn.execute(
                    select(projections).where(
                        projections.c.workspace_id == workspace_id,
                        projections.c.snapshot_id == identity,
                    )
                )
                .mappings()
                .one_or_none()
            )
            if manifest is None:
                raise StorageCorruption("Stored search projection is inconsistent")
            _check_manifest(manifest, bundle, identity, projection)
            current = identity
        assert projection is not None
        ordinal = row["ordinal"]
        stored = {column.name: row[column.name] for column in units.c}
        if not 0 <= ordinal < len(projection.units) or stored != _unit_values(
            workspace_id, identity, projection.units[ordinal]
        ):
            raise StorageCorruption("Stored search unit is inconsistent")
        canonical = ascii_fold(projection.units[ordinal].text)
        is_direct = folded in canonical
        if not is_direct and not (
            len(compact) >= 4 and compact in canonical.translate(str.maketrans("", "", _SPACES))
        ):
            continue
        matched.add(identity)
        if any(original in canonical for original in originals_to_match):
            originals.add(identity)
    pool = tuple(
        sorted(matched, key=lambda identity: (identity not in originals, str(identity)))[:20]
    )
    return VariantCandidates(
        pool,
        frozenset(originals.intersection(pool)),
        min(len(rows), 200),
        len(rows) > 200 or len(matched) > 20,
    )


def retrieve_snapshot_ids(
    conn: Connection, workspace_id: UUID, terms: tuple[str, ...]
) -> tuple[UUID, ...]:
    """Rank distinct topic coverage, then original literal coverage, then snapshot ID."""
    scores: Counter[UUID] = Counter()
    direct_scores: Counter[UUID] = Counter()
    groups: dict[str, set[str]] = {}
    for term in terms[:8]:
        variants = topic_variants(term)
        groups.setdefault(variants[-1], set()).add(term)
    for root, originals in sorted(groups.items()):
        # All original forms contribute direct-match eligibility, regardless of order.
        # The root can find every original; two extra literal queries improve coverage
        # within the per-group three-variant cap. Never award more than one credit.
        original_terms = tuple(sorted(originals))
        variants = (root, *sorted(originals - {root})[:2])
        matched: set[UUID] = set()
        direct: set[UUID] = set()
        for variant in variants:
            result = variant_candidates(conn, workspace_id, variant, original_terms=original_terms)
            matched.update(result.snapshot_ids)
            direct.update(result.direct_snapshot_ids)
        scores.update(matched)
        direct_scores.update(direct)
    ranked = sorted(
        scores, key=lambda identity: (-scores[identity], -direct_scores[identity], str(identity))
    )[:20]
    return tuple(ranked[:5])
