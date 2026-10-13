"""Workspace browsing contracts are immutable and fail closed."""

from uuid import uuid4

import issuedigest_domain as domain
import pytest
from pydantic import ValidationError


def contract(name):
    assert hasattr(domain, name), f"missing auth contract: {name}"
    return getattr(domain, name)


def test_memberships_are_unique_sorted_bounded_and_frozen():
    membership = contract("WorkspaceMembership")
    session = contract("SessionInfo")
    ids = sorted([uuid4(), uuid4()], key=str)
    rows = tuple(membership(workspace_id=x, role="viewer") for x in ids)
    info = session(user_id=uuid4(), memberships=rows)
    assert info.memberships == rows
    for invalid in [rows[::-1], (rows[0], rows[0]), rows * 51]:
        with pytest.raises(ValidationError):
            session(user_id=uuid4(), memberships=invalid)
    with pytest.raises(ValidationError):
        info.user_id = uuid4()
    with pytest.raises(ValidationError):
        session(user_id=uuid4(), memberships=(), schema_version=True)


def test_catalog_summary_strict_values_and_limits():
    summary = contract("EvidenceSummary")
    catalog = contract("EvidenceCatalog")
    values = dict(
        snapshot_id=uuid4(),
        document_id=uuid4(),
        provider="synthetic",
        source_id="source",
        source_kind="other",
        collected_at="2026-10-12T09:00:00+09:00",
        excerpt="😀" * 160,
        citation_count=0,
    )
    item = summary(**values)
    assert item.collected_at.utcoffset().total_seconds() == 0
    assert catalog(workspace_id=uuid4(), items=(item,), has_more=False).items == (item,)
    for field, invalid in [
        ("excerpt", "😀" * 161),
        ("citation_count", True),
        ("citation_count", -1),
        ("source_kind", "unknown"),
        ("canonical_url", "https://user:secret@example.test"),
    ]:
        with pytest.raises(ValidationError):
            summary(**(values | {field: invalid}))
    for items in [(item, item), (item,) * 51]:
        with pytest.raises(ValidationError):
            catalog(workspace_id=uuid4(), items=items, has_more=False)
    with pytest.raises(ValidationError):
        catalog(workspace_id=uuid4(), items=(), has_more=1)
