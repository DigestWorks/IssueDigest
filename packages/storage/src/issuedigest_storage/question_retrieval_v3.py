"""Versioned, operator-reviewed legal nicknames for new question source plans.

The registry is explicit: no inferred law names, external lookups or broad suffix
removal. Each topic adds at most two alias queries to v2's three literal variants.
Canonical checks, workspace scope and candidate bounds remain those of v2.
"""

from collections import Counter
from types import MappingProxyType
from typing import Final
from uuid import UUID

from sqlalchemy import Connection

from . import research_retrieval as v2

RETRIEVAL_PROFILE: Final = "question-legal-aliases-ko-v3"
# Reviewed umbrella topic covers both statutes and proposals whose body omits
# the title; a topic match never infers legal status. Short names stay title-specific.
LEGAL_ALIASES = MappingProxyType(
    {
        "스토킹법": ("스토킹",),
        "스토킹처벌법": ("스토킹범죄의 처벌 등에 관한 법률",),
        "스토킹방지법": ("스토킹방지 및 피해자보호 등에 관한 법률",),
    }
)
# Exact reviewed conversational forms only; v2 tokenization and topic cap stay frozen.
_CONVERSATIONAL_FILLERS = frozenset(("관련하여", "관련해서", "궁금해", "궁금해요", "궁금합니다"))


def question_terms(question: str) -> tuple[str, ...]:
    """Exclude reviewed fillers, including v2's one known particle variant."""
    # Remove complete matching tokens before v2 applies its eight-topic cap.
    # Whitespace replacement preserves neighbouring token boundaries and leaves
    # the original question stored in the plan untouched.
    filtered = v2._TOPIC_TOKEN_PATTERN.sub(
        lambda match: (
            " "
            if any(
                variant in _CONVERSATIONAL_FILLERS for variant in v2.topic_variants(match.group())
            )
            else match.group()
        ),
        question,
    )
    return v2.question_terms(filtered)


def retrieve_snapshot_ids(
    conn: Connection, workspace_id: UUID, terms: tuple[str, ...]
) -> tuple[UUID, ...]:
    """Award one coverage credit per topic, preferring original literal matches."""
    scores: Counter[UUID] = Counter()
    direct_scores: Counter[UUID] = Counter()
    groups: dict[str, set[str]] = {}
    for term in terms[:8]:
        groups.setdefault(v2.topic_variants(term)[-1], set()).add(term)
    for root, originals in sorted(groups.items()):
        original_terms = tuple(sorted(originals))
        variants = (root, *sorted(originals - {root})[:2], *LEGAL_ALIASES.get(root, ()))
        matched: set[UUID] = set()
        direct: set[UUID] = set()
        for variant in variants:
            result = v2.variant_candidates(
                conn, workspace_id, variant, original_terms=original_terms
            )
            matched.update(result.snapshot_ids)
            direct.update(result.direct_snapshot_ids)
        scores.update(matched)
        direct_scores.update(direct)
    ranked = sorted(
        scores, key=lambda identity: (-scores[identity], -direct_scores[identity], str(identity))
    )
    return tuple(ranked[:5])
