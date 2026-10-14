"""Real owned PostgreSQL literal search projections and access boundaries."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from threading import Barrier
from uuid import uuid4

import issuedigest_domain as domain
import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import (
    AuthenticationDenied,
    EvidenceRepository,
    IdentityRepository,
    SessionRepository,
    StorageCorruption,
    StorageError,
    WorkspaceAccessRepository,
)
from sqlalchemy import event, text

from conftest import bundle_data, migration_config, overlapping_session_reads


def require_search():
    assert hasattr(EvidenceRepository, "rebuild_projection"), (
        "explicit projection rebuild is missing"
    )
    assert hasattr(WorkspaceAccessRepository, "search_evidence"), "protected search SDK is missing"


def make_bundle(
    body="한국어 ABC 😀e\u0301é %_' OR 1=1 --",
    workspace=None,
    collected="2026-10-14T00:00:00Z",
    cells=(),
):
    data = bundle_data()
    data["citations"] = []
    data["version"]["media_type"] = "text/plain"
    if workspace:
        data["document"]["workspace_id"] = str(workspace)
    data["version"]["collected_at"] = collected
    data["representation"].update(
        text=body,
        text_sha256=sha256(body.encode()).hexdigest(),
        pages=[],
        tables=[{"table_id": "t", "cells": cells}] if cells else [],
    )
    return EvidenceBundle.model_validate(data)


def setup(engine, bundle=None):
    require_search()
    bundle = bundle or make_bundle()
    snapshot, user = uuid4(), uuid4()
    repository = EvidenceRepository(engine)
    repository.save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(user, "synthetic", str(user))
    identities.set_membership(user, bundle.document.workspace_id, "viewer")
    sessions = SessionRepository(engine)
    token = sessions.issue_session(user).token
    return (
        repository,
        WorkspaceAccessRepository(engine),
        bundle,
        snapshot,
        user,
        identities,
        sessions,
        token,
    )


def test_explicit_rebuild_unchanged_missing_and_no_hidden_save_indexing(engine):
    repo, access, bundle, snapshot, _, _, _, token = setup(engine)
    q = domain.EvidenceSearchQuery(terms=("한국어",))
    empty = access.search_evidence(token, bundle.document.workspace_id, q)
    assert empty.hits == () and empty.coverage.total_snapshots == 1
    assert empty.coverage.missing_snapshots == 1 and empty.coverage.indexed_snapshots == 0
    before = repo.load(bundle.document.workspace_id, snapshot)
    rebuilt = repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    assert rebuilt.status == "rebuilt" and rebuilt.unit_count == 1
    assert repo.rebuild_projection(bundle.document.workspace_id, snapshot).status == "unchanged"
    assert repo.rebuild_projection(uuid4(), snapshot) is None
    assert repo.rebuild_projection(bundle.document.workspace_id, uuid4()) is None
    assert repo.load(bundle.document.workspace_id, snapshot) == before
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM outbox")) == 1
        assert conn.scalar(text("SELECT count(*) FROM citations")) == 0


@pytest.mark.parametrize(
    "terms,want",
    [
        (("한국어", "abc", "😀", "e\u0301", "%_' OR"), 1),
        (("é",), 1),
        (("É",), 0),
        (("한국어", "missing"), 0),
        (("%",), 1),
        (("_",), 1),
        (("한국어 ABC",), 1),
    ],
)
def test_literal_and_unicode_sql_metacharacters(engine, terms, want):
    repo, access, bundle, snapshot, _, _, _, token = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=terms)
    )
    assert len(result.hits) == want
    assert result.coverage.indexed_snapshots == 1 and not result.truncated
    for hit in result.hits:
        assert hit.snapshot_id == snapshot and hit.version_id == bundle.version.version_id
        assert hit.selector.quote == bundle.representation.text
        assert hit.matched_terms == terms and hit.support_status == "not_evaluated"
        assert hit.anchor_status == "matched" and not hasattr(hit, "citation_id")
        assert hit.model_config["frozen"] and hit.provider == "synthetic"


def test_candidates_recheck_order_repetition_and_each_term(engine):
    repo, access, bundle, snapshot, _, _, _, token = setup(
        engine, make_bundle("aba bab bca cab bbb aaa")
    )
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("ababa",))
    )
    assert result.scanned_candidates == 1 and result.hits == ()


def test_cells_skipped_coverage_and_empty_search_result(engine):
    bundle = make_bundle(
        "본문",
        cells=(
            {"cell_id": "c", "text": "셀 😀 ABC"},
            {"cell_id": "empty", "text": ""},
            {"cell_id": "big", "text": "가" * 2049},
        ),
    )
    repo, access, bundle, snapshot, _, _, _, token = setup(engine, bundle)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("셀", "abc"))
    )
    assert result.hits[0].selector == domain.TableCellSelector(
        table_id="t", cell_id="c", quote="셀 😀 ABC"
    )
    assert result.coverage.skipped_empty_cells == result.coverage.skipped_large_cells == 1
    empty = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("없음",))
    )
    assert empty.hits == () and empty.coverage == result.coverage


def test_collected_filters_half_open_source_filters_and_workspace_coverage(engine):
    repo, access, bundle, first, _, _, _, token = setup(engine)
    second_bundle = make_bundle(
        workspace=bundle.document.workspace_id, collected="2026-10-15T00:00:00Z"
    )
    second = uuid4()
    repo.save(second, second_bundle)
    other = make_bundle()
    third = uuid4()
    repo.save(third, other)
    repo.rebuild_projection(bundle.document.workspace_id, first)
    repo.rebuild_projection(other.document.workspace_id, third)
    q = domain.EvidenceSearchQuery(
        terms=("한국어",),
        collected_from=datetime(2026, 10, 14, tzinfo=UTC),
        collected_to=datetime(2026, 10, 15, tzinfo=UTC),
    )
    result = access.search_evidence(token, bundle.document.workspace_id, q)
    assert [h.snapshot_id for h in result.hits] == [first]
    assert result.coverage.total_snapshots == result.coverage.indexed_snapshots == 1
    broader = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("한국어",))
    )
    assert broader.coverage.total_snapshots == 2 and broader.coverage.missing_snapshots == 1
    for field, good, bad in [
        ("provider", "synthetic", "Synthetic"),
        ("source_id", bundle.document.source_id, "missing"),
        ("source_kind", "other", "bill"),
    ]:
        hit = access.search_evidence(
            token,
            bundle.document.workspace_id,
            domain.EvidenceSearchQuery(terms=("한국어",), **{field: good}),
        )
        assert hit.hits[0].snapshot_id == first
        empty = access.search_evidence(
            token,
            bundle.document.workspace_id,
            domain.EvidenceSearchQuery(terms=("한국어",), **{field: bad}),
        )
        assert empty.hits == () and empty.coverage.total_snapshots == 0


def test_result_limit_deterministic_order_and_candidate_cap(engine):
    repo, access, bundle, snapshot, _, _, _, token = setup(engine, make_bundle("x " * 3000))
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("x",), limit=2)
    )
    assert [h.unit_ordinal for h in result.hits] == [0, 1] and result.truncated
    # 210 small full cells give 210 distinct candidates without a giant source body.
    big = make_bundle(
        "",
        workspace=bundle.document.workspace_id,
        collected="2026-10-15T00:00:00Z",
        cells=tuple({"cell_id": str(i), "text": "x"} for i in range(210)),
    )
    other = uuid4()
    repo.save(other, big)
    repo.rebuild_projection(bundle.document.workspace_id, other)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("x",), limit=20)
    )
    assert result.scanned_candidates == 200 and result.truncated
    assert len(result.hits) == 20 and all(h.snapshot_id == other for h in result.hits)
    assert [h.unit_ordinal for h in result.hits] == list(range(20))


@pytest.mark.parametrize("field", ["text", "selector", "checksum", "profile", "identity"])
def test_candidate_corruption_fails_closed(engine, field):
    repo, access, bundle, snapshot, _, _, _, token = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    statement = {
        "text": "UPDATE evidence_search_units SET text='한국어 forged'",
        "selector": (
            "UPDATE evidence_search_units SET selector="
            "jsonb_set(selector,'{quote}','\"한국어 forged\"')"
        ),
        "checksum": "UPDATE evidence_search_units SET text_sha256=repeat('f',64)",
        "profile": "UPDATE evidence_search_projections SET projection_sha256=repeat('f',64)",
        "identity": (
            "UPDATE source_documents SET payload=jsonb_set(payload,'{provider}','\"forged\"')"
        ),
    }[field]
    with engine.begin() as conn:
        conn.execute(text(statement))
    with pytest.raises(StorageCorruption) as caught:
        access.search_evidence(
            token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("한국어",))
        )
    assert "forged" not in str(caught.value)


def test_rebuild_failure_preserves_previous_projection_evidence_and_outbox(engine):
    repo, access, bundle, snapshot, _, _, _, token = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    with engine.begin() as conn:
        conn.execute(text("UPDATE evidence_search_units SET text='damaged'"))

    def fail_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO evidence_search_units"):
            cursor.execute("DO $$ BEGIN RAISE EXCEPTION 'synthetic source private error'; END $$")

    event.listen(engine, "before_cursor_execute", fail_insert)
    try:
        with pytest.raises(StorageError) as caught:
            repo.rebuild_projection(bundle.document.workspace_id, snapshot)
        assert "private" not in str(caught.value)
    finally:
        event.remove(engine, "before_cursor_execute", fail_insert)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT text FROM evidence_search_units")) == "damaged"
        assert conn.scalar(text("SELECT count(*) FROM outbox")) == 1
    assert repo.load(bundle.document.workspace_id, snapshot) == bundle
    assert repo.rebuild_projection(bundle.document.workspace_id, snapshot).status == "rebuilt"
    assert access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("한국어",))
    ).hits


def test_parallel_same_snapshot_rebuild_serializes(engine):
    repo, _, bundle, snapshot, _, _, _, _ = setup(engine)
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=5)
        return (
            EvidenceRepository(engine)
            .rebuild_projection(bundle.document.workspace_id, snapshot)
            .status
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run) for _ in range(2)]
        assert sorted(f.result(timeout=10) for f in futures) == ["rebuilt", "unchanged"]
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM evidence_search_units")) == 1


@pytest.mark.parametrize("denial", ["revoked", "disabled", "expired", "idle", "nonmember", "other"])
def test_current_authority_and_activity_boundary(engine, denial):
    repo, access, bundle, snapshot, user, identities, sessions, token = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    if denial == "revoked":
        sessions.revoke_session(token)
    elif denial == "disabled":
        identities.set_enabled(user, False)
    elif denial == "nonmember":
        identities.set_membership(user, bundle.document.workspace_id, "viewer", False)
    elif denial in {"expired", "idle"}:
        with engine.begin() as conn:
            if denial == "expired":
                conn.execute(
                    text(
                        "UPDATE auth_sessions SET issued_at=clock_timestamp()-interval '8 hours', "
                        "expires_at=clock_timestamp()-interval '1 second', "
                        "last_activity_at=clock_timestamp()-interval '1 minute'"
                    )
                )
            else:
                conn.execute(
                    text(
                        "UPDATE auth_sessions SET "
                        "issued_at=clock_timestamp()-interval '31 minutes', "
                        "expires_at=clock_timestamp()+interval '7 hours', "
                        "last_activity_at=clock_timestamp()-interval '30 minutes'"
                    )
                )
    with engine.connect() as conn:
        before = conn.scalar(text("SELECT last_activity_at FROM auth_sessions"))
    q = domain.EvidenceSearchQuery(terms=("한국어",))
    if denial in {"other", "nonmember"}:
        assert (
            access.search_evidence(
                token, uuid4() if denial == "other" else bundle.document.workspace_id, q
            )
            is None
        )
    else:
        with pytest.raises(AuthenticationDenied):
            access.search_evidence(token, bundle.document.workspace_id, q)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT last_activity_at FROM auth_sessions")) == before


def test_authorized_empty_search_refreshes_activity_and_revalidates_construct_query(engine):
    _, access, bundle, _, _, _, _, token = setup(engine)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=clock_timestamp()-interval '10 minutes', "
                "expires_at=clock_timestamp()+interval '7 hours', "
                "last_activity_at=clock_timestamp()-interval '5 minutes'"
            )
        )
        before = conn.scalar(text("SELECT last_activity_at FROM auth_sessions"))
    valid = domain.EvidenceSearchQuery(terms=("없음",))
    assert access.search_evidence(token, bundle.document.workspace_id, valid).hits == ()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT last_activity_at FROM auth_sessions")) > before
    with pytest.raises(ValueError):
        access.search_evidence(
            token, bundle.document.workspace_id, valid.model_copy(update={"terms": ("x",) * 9})
        )


def test_concurrent_search_retries_entire_authorization(engine):
    repo, access, bundle, snapshot, _, _, sessions, token = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)

    def read():
        return access.search_evidence(
            token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("한국어",))
        )

    results, conflicts = overlapping_session_reads(
        engine, read, read, lambda: sessions.revoke_session(token)
    )
    assert conflicts == 1 and results[0][0] == "ok" and results[1][0] == "AuthenticationDenied"


def test_migration_roundtrip_preserves_existing_canonical_data(engine, database_url):
    require_search()
    from alembic import command
    from sqlalchemy import inspect

    repo, _, bundle, snapshot, _, _, _, _ = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    config = migration_config(database_url)
    try:
        command.downgrade(config, "0003_oauth_identity")
        assert "evidence_search_units" not in inspect(engine).get_table_names()
        assert repo.load(bundle.document.workspace_id, snapshot) == bundle
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM evidence_search_projections")) == 0
            indexes = (
                conn.execute(
                    text("SELECT indexdef FROM pg_indexes WHERE tablename='evidence_search_units'")
                )
                .scalars()
                .all()
            )
        assert any("USING gin (ngrams)" in index for index in indexes)
        assert repo.rebuild_projection(bundle.document.workspace_id, snapshot).status == "rebuilt"
    finally:
        command.upgrade(config, "head")


def test_rebuild_requires_no_immutable_source_update_grant(engine, database_url):
    from issuedigest_storage import create_storage_engine

    repo, _, bundle, snapshot, _, _, _, _ = setup(engine)
    role = "search_qa_" + uuid4().hex
    with engine.begin() as conn:
        conn.execute(text(f"CREATE ROLE {role} NOLOGIN"))
        conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        conn.execute(text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {role}"))
        conn.execute(
            text(
                "GRANT INSERT, UPDATE, DELETE ON evidence_search_projections, "
                f"evidence_search_units TO {role}"
            )
        )
    app_engine = create_storage_engine(database_url)

    def assume_role(conn):
        conn.exec_driver_sql(f"SET LOCAL ROLE {role}")

    event.listen(app_engine, "begin", assume_role)
    try:
        result = EvidenceRepository(app_engine).rebuild_projection(
            bundle.document.workspace_id, snapshot
        )
        assert result.status == "rebuilt"
        assert (
            EvidenceRepository(app_engine)
            .rebuild_projection(bundle.document.workspace_id, snapshot)
            .status
            == "unchanged"
        )
    finally:
        event.remove(app_engine, "begin", assume_role)
        app_engine.dispose()
        with engine.begin() as conn:
            conn.execute(text(f"DROP OWNED BY {role}"))
            conn.execute(text(f"DROP ROLE {role}"))


def test_candidate_cap_with_only_false_positives_stays_explicitly_truncated(engine):
    bundle = make_bundle(
        "", cells=tuple({"cell_id": str(i), "text": "aba bab"} for i in range(201))
    )
    repo, access, bundle, snapshot, _, _, _, token = setup(engine, bundle)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("ababa",))
    )
    assert result.hits == () and result.scanned_candidates == 200 and result.truncated
    assert result.coverage.indexed_snapshots == 1


def test_terms_in_different_units_do_not_match_and_snapshot_ties_are_stable(engine):
    bundle = make_bundle("BEGIN" + "가" * 1000 + "END")
    repo, access, bundle, snapshot, _, _, _, token = setup(engine, bundle)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("BEGIN", "END"))
    )
    assert result.hits == ()
    second = uuid4()
    repo.save(second, bundle)
    repo.rebuild_projection(bundle.document.workspace_id, second)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("BEGIN",))
    )
    assert [h.snapshot_id for h in result.hits] == sorted([snapshot, second])


def test_pdf_page_anchors_survive_storage_search(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    repo, access, bundle, snapshot, _, _, _, token = setup(engine, bundle)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("😀", "e\u0301"))
    )
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.selector == domain.PdfQuoteSelector(
        page_number=1, start=0, end=9, quote="앞 😀한e\u0301é 뒤"
    )
    assert hit.selector.regions == ()
    assert repo.load(bundle.document.workspace_id, snapshot).citations == bundle.citations


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE evidence_search_units SET workspace_id=:other",
        "UPDATE evidence_search_units SET ordinal=6000",
        "UPDATE evidence_search_units SET text=repeat('x',2049)",
        "UPDATE evidence_search_units SET text_sha256='invalid'",
        "UPDATE evidence_search_units SET ngrams=ARRAY[]::text[]",
        "UPDATE evidence_search_units SET selector='{}'::jsonb",
        "UPDATE evidence_search_units SET ngrams=ARRAY[NULL]::text[]",
        "UPDATE evidence_search_units SET ngrams=ARRAY[['a'],['b']]::text[]",
        "UPDATE evidence_search_projections SET profile='unsupported'",
        "UPDATE evidence_search_projections SET unit_count=6001",
        "UPDATE evidence_search_projections SET unit_text_characters=2000001",
        "UPDATE evidence_search_projections SET skipped_empty_cells=20001",
    ],
)
def test_schema_rejects_cross_workspace_invalid_bounds_and_selector(engine, mutation):
    from sqlalchemy.exc import IntegrityError

    repo, _, bundle, snapshot, _, _, _, _ = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(text(mutation), {"other": uuid4()})
    assert repo.rebuild_projection(bundle.document.workspace_id, snapshot).status == "unchanged"


def test_unusable_literal_nul_can_return_coverage_without_driver_failure(engine):
    repo, access, bundle, snapshot, _, _, _, token = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    result = access.search_evidence(
        token, bundle.document.workspace_id, domain.EvidenceSearchQuery(terms=("\x00",))
    )
    assert result.hits == () and result.scanned_candidates == 0
    assert result.coverage.indexed_snapshots == 1


def test_stored_ngram_length_is_bounded_by_postgresql_type(engine):
    from sqlalchemy.exc import DBAPIError

    repo, _, bundle, snapshot, _, _, _, _ = setup(engine)
    repo.rebuild_projection(bundle.document.workspace_id, snapshot)
    with pytest.raises(DBAPIError):
        with engine.begin() as conn:
            conn.execute(text("UPDATE evidence_search_units SET ngrams=ARRAY['abcd']::text[]"))
