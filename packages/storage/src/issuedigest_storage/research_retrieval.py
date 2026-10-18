"""Bounded question retrieval over the verified, workspace-scoped literal index.

This is lexical retrieval from stored projections, not web or semantic search.
The interface isolates the strategy so retrieval can improve without changing requests.
"""

import re
from collections import Counter
from uuid import UUID

from issuedigest_domain import EvidenceSearchQuery
from issuedigest_domain.search import ascii_fold
from sqlalchemy import Connection

from .search import search_evidence

RETRIEVAL_PROFILE = "question-terms-v1"

_GENERIC = frozenset(
    "질문 무엇 무엇인가 무엇인가요 무엇인지 무슨 어떤 어떻게 왜 알려줘 알려주세요 "
    "설명 설명해줘 설명해주세요 요약 요약해줘 요약해주세요 자세히 더 좀 해줘 주세요 "
    "그다음 다음 그럼 그러면 그래서 이것 이거 그것 그거 그 이 저 것 다시 "
    "의미 의미인가 의미인가요 자료 내용 "
    "대해 대한 관련 소식 최근 현재 what why how please explain summarize the a an is are "
    "this that it and or about".split()
)
_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+(?:\.[0-9]+)?%?")
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
    """Keep at most eight distinct topical tokens, with basic Korean particle support."""
    terms = dict.fromkeys(
        term for term in _tokens(question) if 1 <= len(term) <= 64 and term not in _GENERIC
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


def retrieve_snapshot_ids(
    conn: Connection, workspace_id: UUID, terms: tuple[str, ...]
) -> tuple[UUID, ...]:
    """Rank by distinct matched question terms; break ties by stable snapshot identity."""
    scores: Counter[UUID] = Counter()
    for term in terms[:8]:
        result = search_evidence(conn, workspace_id, EvidenceSearchQuery(terms=(term,), limit=20))
        scores.update({hit.snapshot_id for hit in result.hits})
    return tuple(sorted(scores, key=lambda identity: (-scores[identity], str(identity)))[:5])
