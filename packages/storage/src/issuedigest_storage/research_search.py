"""Bounded planner queries over existing approved workspace evidence only."""

import unicodedata
from collections.abc import Mapping
from typing import Any
from uuid import UUID

from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchRun
from sqlalchemy import Connection

from .research_retrieval import is_generic_followup, question_terms, retrieve_snapshot_ids


def validate_plan(queries: tuple[str, ...], input_tokens: int, output_tokens: int) -> None:
    """Validate again at the storage boundary, including forged Python values."""
    if (
        type(queries) is not tuple
        or not 1 <= len(queries) <= 3
        or any(
            type(query) is not str
            or not 1 <= len(query) <= 64
            or not query.strip()
            or any(unicodedata.category(char).startswith("C") for char in query)
            for query in queries
        )
    ):
        raise ValueError("Invalid research search queries")
    if (
        type(input_tokens) is not int
        or type(output_tokens) is not int
        or input_tokens < 0
        or not 0 <= output_tokens <= 500
        or input_tokens + output_tokens > 8000
    ):
        raise ValueError("Invalid research planner usage")


def search_candidates(
    conn: Connection,
    row: Mapping[Any, Any],
    queries: tuple[str, ...],
    parent: ResearchRun | None,
) -> tuple[tuple[UUID, ...], tuple[EvidenceBundle, ...] | None]:
    """Select original-first round-robin results; generic followups keep exact parents."""
    terms = question_terms(row["question"])
    if not terms and parent is not None and is_generic_followup(row["question"]):
        assert parent.result is not None
        return parent.snapshot_ids, parent.result.canvas.research.evidence
    groups = [retrieve_snapshot_ids(conn, row["workspace_id"], terms)]
    groups.extend(
        retrieve_snapshot_ids(conn, row["workspace_id"], question_terms(query)) for query in queries
    )
    selected: list[UUID] = []
    for depth in range(5):
        for group in groups:
            if depth < len(group) and group[depth] not in selected:
                selected.append(group[depth])
                if len(selected) == 5:
                    return tuple(selected), None
    return tuple(selected), None
