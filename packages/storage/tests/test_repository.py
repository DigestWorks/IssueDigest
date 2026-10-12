"""Synthetic PostgreSQL persistence boundaries; no production database access."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC
from hashlib import sha256
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from issuedigest_domain import EvidenceBundle

from conftest import bundle_data, migration_config, storage


def counts(engine):
    from sqlalchemy import text

    with engine.connect() as connection:
        return {
            table: connection.scalar(text(f"SELECT count(*) FROM {table}"))
            for table in [
                "source_documents",
                "document_versions",
                "parsed_representations",
                "citations",
                "evidence_snapshots",
                "snapshot_citations",
                "outbox",
            ]
        }


def test_repository_round_trip_and_retry_are_durable(engine, database_url):
    api = storage()
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot = uuid4()
    assert api.EvidenceRepository(engine).save(snapshot, bundle) is True
    before = counts(engine)
    assert before == {
        "source_documents": 1,
        "document_versions": 1,
        "parsed_representations": 1,
        "citations": 3,
        "evidence_snapshots": 1,
        "snapshot_citations": 3,
        "outbox": 1,
    }
    fresh = api.create_storage_engine(database_url)
    try:
        repository = api.EvidenceRepository(fresh)
        loaded = repository.load(bundle.document.workspace_id, snapshot)
        assert loaded == bundle
        assert loaded.version.collected_at.tzinfo == UTC
        assert [c.selector.kind for c in loaded.citations] == ["table_cell", "pdf", "text"]
        assert loaded.representation.text == "앞 😀한e\u0301é 뒤"
        assert repository.save(snapshot, bundle) is False
        assert repository.load(uuid4(), snapshot) is None
        assert repository.load(bundle.document.workspace_id, uuid4()) is None
    finally:
        fresh.dispose()
    assert counts(engine) == before
    from sqlalchemy import text

    with engine.connect() as connection:
        event = connection.execute(text("SELECT event_id, event_type, payload FROM outbox")).one()
    assert event.event_id == snapshot
    assert event.event_type == "evidence.snapshot_saved.v1"
    assert event.payload == {
        "workspace_id": str(bundle.document.workspace_id),
        "snapshot_id": str(snapshot),
        "document_id": str(bundle.document.document_id),
        "version_id": str(bundle.version.version_id),
        "representation_id": str(bundle.representation.representation_id),
    }


def test_versions_representations_and_added_citations_preserve_old_snapshots(engine):
    api = storage()
    repository = api.EvidenceRepository(engine)
    data = bundle_data()
    first = EvidenceBundle.model_validate(data)
    snapshots = [uuid4() for _ in range(4)]
    repository.save(snapshots[0], first)
    more = deepcopy(data)
    more["citations"].append({**more["citations"][2], "citation_id": str(uuid4())})
    second = EvidenceBundle.model_validate(more)
    repository.save(snapshots[1], second)
    revised = deepcopy(data)
    revised["representation"]["representation_id"] = str(uuid4())
    revised["representation"]["parser_version"] = "2"
    for citation in revised["citations"]:
        citation["citation_id"] = str(uuid4())
        citation["representation_id"] = revised["representation"]["representation_id"]
    third = EvidenceBundle.model_validate(revised)
    repository.save(snapshots[2], third)
    revised["version"]["version_id"] = str(uuid4())
    revised["version"]["raw_object_id"] = str(uuid4())
    revised["representation"]["representation_id"] = str(uuid4())
    revised["representation"]["document_version_id"] = revised["version"]["version_id"]
    for citation in revised["citations"]:
        citation["citation_id"] = str(uuid4())
        citation["representation_id"] = revised["representation"]["representation_id"]
        citation["document_version_id"] = revised["version"]["version_id"]
    fourth = EvidenceBundle.model_validate(revised)
    repository.save(snapshots[3], fourth)
    for snapshot, expected in zip(snapshots, [first, second, third, fourth], strict=True):
        assert repository.load(first.document.workspace_id, snapshot) == expected
    assert counts(engine)["document_versions"] == 2  # Same raw digest does not merge versions.


@pytest.mark.parametrize(
    "kind",
    [
        "snapshot_order",
        "document",
        "version",
        "representation",
        "citation",
        "workspace",
        "identity",
    ],
)
def test_changed_immutable_ids_conflict_and_roll_back(engine, kind):
    api = storage()
    repository = api.EvidenceRepository(engine)
    data = bundle_data()
    original = EvidenceBundle.model_validate(data)
    snapshot = uuid4()
    repository.save(snapshot, original)
    before = counts(engine)
    changed = deepcopy(data)
    target = uuid4()
    if kind == "snapshot_order":
        changed["citations"].reverse()
        target = snapshot
    elif kind == "document":
        changed["document"]["source_kind"] = "news"
    elif kind == "version":
        changed["version"]["media_type"] = "text/plain"
    elif kind == "representation":
        changed["representation"]["parser_version"] = "2"
    elif kind == "citation":
        changed["citations"][2]["selector"]["suffix"] = None
    elif kind == "workspace":
        changed["document"]["workspace_id"] = str(uuid4())
    else:
        changed["document"]["document_id"] = str(uuid4())
        changed["version"]["document_id"] = changed["document"]["document_id"]
    with pytest.raises(api.StorageConflict):
        repository.save(target, EvidenceBundle.model_validate(changed))
    assert counts(engine) == before
    assert repository.load(original.document.workspace_id, snapshot) == original


@pytest.mark.parametrize("method", ["copy", "construct"])
def test_unvalidated_bundle_is_revalidated_before_any_write(engine, method):
    api = storage()
    valid = EvidenceBundle.model_validate(bundle_data())
    invalid = (
        valid.model_copy(update={"schema_version": True})
        if method == "copy"
        else EvidenceBundle.model_construct(**{**valid.model_dump(), "schema_version": True})
    )
    with pytest.raises(ValueError):
        api.EvidenceRepository(engine).save(uuid4(), invalid)
    assert all(value == 0 for value in counts(engine).values())


def test_uuid4_snapshot_is_required_before_writing(engine):
    api = storage()
    with pytest.raises(ValueError):
        api.EvidenceRepository(engine).save(
            UUID(int=1), EvidenceBundle.model_validate(bundle_data())
        )
    assert all(value == 0 for value in counts(engine).values())


@pytest.mark.parametrize("failure", ["unicode", "outbox"])
def test_database_write_failures_roll_back_new_objects(engine, failure):
    api = storage()
    from sqlalchemy import text

    data = bundle_data()
    if failure == "unicode":
        data["representation"]["text"] += "\x00"
        data["representation"]["text_sha256"] = sha256(
            data["representation"]["text"].encode()
        ).hexdigest()
    else:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE outbox ADD CONSTRAINT synthetic_failure CHECK (false)")
            )
    try:
        with pytest.raises(Exception) as raised:
            api.EvidenceRepository(engine).save(uuid4(), EvidenceBundle.model_validate(data))
        assert data["representation"]["text"] not in str(raised.value)
        assert all(value == 0 for value in counts(engine).values())
    finally:
        if failure == "outbox":
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE outbox DROP CONSTRAINT synthetic_failure"))


@pytest.mark.parametrize(
    "damage",
    [
        "payload",
        "hash",
        "parent_payload",
        "snapshot_hash",
        "citation_link",
        "missing_link",
        "column_identity",
    ],
)
def test_load_detects_stored_corruption_without_exposing_content(engine, damage):
    api = storage()
    from sqlalchemy import text

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot = uuid4()
    repository = api.EvidenceRepository(engine)
    repository.save(snapshot, bundle)
    statements = {
        "payload": "UPDATE parsed_representations SET payload = "
        "jsonb_set(payload, '{text}', '\"tampered synthetic secret\"')",
        "hash": "UPDATE citations SET content_sha256 = repeat('0', 64)",
        "parent_payload": "UPDATE document_versions SET payload = "
        "jsonb_set(payload, '{document_id}', to_jsonb(CAST(:other AS text)))",
        "snapshot_hash": "UPDATE evidence_snapshots SET content_sha256 = repeat('0', 64)",
        "citation_link": "UPDATE snapshot_citations SET ordinal = ordinal + 10",
        "missing_link": "DELETE FROM snapshot_citations WHERE ordinal = 0",
        "column_identity": "UPDATE source_documents SET provider = 'tampered'",
    }
    with engine.begin() as connection:
        connection.execute(text(statements[damage]), {"other": str(uuid4())})
    with pytest.raises(api.StorageCorruption) as raised:
        repository.load(bundle.document.workspace_id, snapshot)
    assert bundle.representation.text not in str(raised.value)
    assert "tampered synthetic secret" not in str(raised.value)


@pytest.mark.parametrize("changed", [False, True])
def test_concurrent_snapshot_writes_have_one_winner(engine, changed):
    api = storage()
    bundle = EvidenceBundle.model_validate(bundle_data())
    second = bundle.model_copy(update={"citations": tuple(reversed(bundle.citations))})
    snapshot = uuid4()
    barrier = Barrier(2)

    def write(candidate):
        barrier.wait(timeout=10)
        try:
            return api.EvidenceRepository(engine).save(snapshot, candidate)
        except api.StorageConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(write, bundle),
            executor.submit(write, second if changed else bundle),
        ]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(results, key=str) == sorted([True, "conflict" if changed else False], key=str)
    loaded = api.EvidenceRepository(engine).load(bundle.document.workspace_id, snapshot)
    assert loaded in [bundle, second] if changed else loaded == bundle
    assert counts(engine) == {
        "source_documents": 1,
        "document_versions": 1,
        "parsed_representations": 1,
        "citations": 3,
        "evidence_snapshots": 1,
        "snapshot_citations": 3,
        "outbox": 1,
    }


def test_migrations_upgrade_repeat_and_downgrade_on_dedicated_database(database_url):
    api = storage()
    from alembic import command
    from sqlalchemy import inspect, text

    config = migration_config(database_url)
    command.downgrade(config, "base")
    engine = api.create_storage_engine(database_url)
    try:
        assert "source_documents" not in inspect(engine).get_table_names()
        command.upgrade(config, "head")
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert connection.scalar(text("SHOW server_version")).split()[0] == "18.6"
        assert "outbox" in inspect(engine).get_table_names()
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite://",
        "postgresql://user:secret@localhost/db",
        "postgresql+asyncpg://user:secret@localhost/db",
        "malformed secret",
    ],
)
def test_engine_rejects_unsupported_urls_without_leaking_credentials(url):
    api = storage()
    with pytest.raises(ValueError) as raised:
        api.create_storage_engine(url)
    assert "secret" not in str(raised.value)
    assert url not in str(raised.value)


def test_connection_failure_is_sanitized():
    api = storage()
    with pytest.raises(ValueError) as raised:
        api.create_storage_engine("postgresql+psycopg://user:synthetic-secret@127.0.0.1:1/db")
    assert "synthetic-secret" not in str(raised.value)
    assert "127.0.0.1" not in str(raised.value)
    assert raised.value.__cause__ is None


def test_verified_storage_engine_connects_to_real_postgresql(database_url):
    from sqlalchemy import text

    backend = storage().create_storage_engine(database_url)
    try:
        with backend.connect() as connection:
            assert connection.scalar(text("SHOW server_version")).split()[0] == "18.6"
        assert hasattr(storage(), "EvidenceRepository"), (
            "EvidenceRepository storage boundary missing"
        )
    finally:
        backend.dispose()


@pytest.mark.parametrize("object_kind", ["version", "representation", "citation"])
def test_global_object_ids_cannot_move_to_another_workspace(engine, object_kind):
    api = storage()
    repository = api.EvidenceRepository(engine)
    data = bundle_data()
    first = EvidenceBundle.model_validate(data)
    snapshot = uuid4()
    repository.save(snapshot, first)
    before = counts(engine)
    changed = deepcopy(data)
    changed["document"]["workspace_id"] = str(uuid4())
    changed["document"]["document_id"] = str(uuid4())
    changed["version"]["document_id"] = changed["document"]["document_id"]
    if object_kind != "version":
        changed["version"]["version_id"] = str(uuid4())
        changed["representation"]["document_version_id"] = changed["version"]["version_id"]
        for citation in changed["citations"]:
            citation["document_version_id"] = changed["version"]["version_id"]
    if object_kind == "citation":
        changed["representation"]["representation_id"] = str(uuid4())
        for citation in changed["citations"]:
            citation["representation_id"] = changed["representation"]["representation_id"]
    with pytest.raises(api.StorageConflict):
        repository.save(uuid4(), EvidenceBundle.model_validate(changed))
    assert counts(engine) == before
    assert repository.load(first.document.workspace_id, snapshot) == first


def test_concurrent_changed_object_with_distinct_snapshots_does_not_overwrite(engine):
    api = storage()
    bundle = EvidenceBundle.model_validate(bundle_data())
    changed = bundle.model_copy(
        update={"document": bundle.document.model_copy(update={"source_kind": "news"})}
    )
    barrier = Barrier(2)
    snapshots = [uuid4(), uuid4()]

    def write(snapshot, candidate):
        barrier.wait(timeout=10)
        try:
            return api.EvidenceRepository(engine).save(snapshot, candidate)
        except api.StorageConflict:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(write, snapshot, candidate)
            for snapshot, candidate in zip(snapshots, [bundle, changed], strict=True)
        ]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(results, key=str) == sorted([True, "conflict"], key=str)
    repository = api.EvidenceRepository(engine)
    for snapshot, candidate, result in zip(snapshots, [bundle, changed], results, strict=True):
        assert repository.load(bundle.document.workspace_id, snapshot) == (
            candidate if result is True else None
        )
    assert counts(engine)["outbox"] == 1
    assert counts(engine)["evidence_snapshots"] == 1


def test_relational_parent_corruption_is_detected_even_when_payload_is_valid(engine):
    api = storage()
    from sqlalchemy import text

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot = uuid4()
    repository = api.EvidenceRepository(engine)
    repository.save(snapshot, bundle)
    # The dedicated synthetic DB owner can emulate corruption below the FK boundary.
    # Both trigger changes are transactional, and this fixture only addresses issuedigest_test.
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE document_versions DISABLE TRIGGER ALL"))
        connection.execute(
            text("UPDATE document_versions SET document_id = :other"), {"other": uuid4()}
        )
        connection.execute(text("ALTER TABLE document_versions ENABLE TRIGGER ALL"))
    with pytest.raises(api.StorageCorruption):
        repository.load(bundle.document.workspace_id, snapshot)


def test_database_constraints_prevent_cross_workspace_and_cross_parent_links(engine):
    api = storage()
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    first = EvidenceBundle.model_validate(bundle_data())
    second = EvidenceBundle.model_validate(bundle_data())
    repository = api.EvidenceRepository(engine)
    snapshot = uuid4()
    repository.save(snapshot, first)
    repository.save(uuid4(), second)
    before = counts(engine)
    for query, params in [
        (
            "UPDATE document_versions SET workspace_id = :other WHERE version_id = :identity",
            {"other": second.document.workspace_id, "identity": first.version.version_id},
        ),
        (
            "UPDATE snapshot_citations SET citation_id = :other WHERE snapshot_id = :identity "
            "AND ordinal = 0",
            {"other": second.citations[0].citation_id, "identity": snapshot},
        ),
    ]:
        with pytest.raises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text(query), params)
    assert counts(engine) == before
    assert repository.load(first.document.workspace_id, snapshot) == first


def test_autocommit_engine_save_is_atomic_on_outbox_failure(engine):
    api = storage()
    from sqlalchemy import text

    supplied = engine.execution_options(isolation_level="AUTOCOMMIT")
    repository = api.EvidenceRepository(supplied)
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE outbox ADD CONSTRAINT synthetic_failure CHECK (false)")
        )
    try:
        with pytest.raises(api.StorageError):
            repository.save(snapshot, bundle)
        # The outbox is last: every object, snapshot and citation membership must roll back.
        assert counts(engine) == {
            "source_documents": 0,
            "document_versions": 0,
            "parsed_representations": 0,
            "citations": 0,
            "evidence_snapshots": 0,
            "snapshot_citations": 0,
            "outbox": 0,
        }
        assert repository.load(bundle.document.workspace_id, snapshot) is None
    finally:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE outbox DROP CONSTRAINT synthetic_failure"))
    # Keep the supplied AUTOCOMMIT engine: a normal write and same-ID retry still work.
    assert repository.save(snapshot, bundle) is True
    before = counts(engine)
    assert repository.save(snapshot, bundle) is False
    assert counts(engine) == before
    assert before == {
        "source_documents": 1,
        "document_versions": 1,
        "parsed_representations": 1,
        "citations": 3,
        "evidence_snapshots": 1,
        "snapshot_citations": 3,
        "outbox": 1,
    }
    assert repository.load(bundle.document.workspace_id, snapshot) == bundle


@pytest.mark.parametrize("negative_first", [True, False])
def test_pdf_signed_zero_round_trip_and_opposite_sign_retry(engine, negative_first):
    api = storage()
    data = bundle_data()
    zero = -0.0 if negative_first else 0.0
    data["citations"][1]["selector"]["regions"] = [{"x0": zero, "y0": zero, "x1": 0.5, "y1": 0.75}]
    # Numeric normalization must leave text containing a minus sign untouched.
    data["representation"]["tables"][0]["cells"][0]["unit"] = "-0.0"
    bundle = EvidenceBundle.model_validate(data)
    repository = api.EvidenceRepository(engine)
    snapshot = uuid4()
    assert repository.save(snapshot, bundle) is True
    before = counts(engine)
    loaded = api.EvidenceRepository(engine).load(bundle.document.workspace_id, snapshot)
    assert loaded == bundle
    assert loaded.model_dump(mode="json") == bundle.model_dump(mode="json")
    assert loaded.representation.tables[0].cells[0].unit == "-0.0"
    opposite = deepcopy(data)
    opposite["citations"][1]["selector"]["regions"][0].update(
        {
            "x0": 0.0 if negative_first else -0.0,
            "y0": 0.0 if negative_first else -0.0,
        }
    )
    assert repository.save(snapshot, EvidenceBundle.model_validate(opposite)) is False
    assert counts(engine) == before
    changed = deepcopy(opposite)
    changed["citations"][1]["selector"]["regions"][0]["x1"] = 0.6
    with pytest.raises(api.StorageConflict):
        repository.save(snapshot, EvidenceBundle.model_validate(changed))
    assert counts(engine) == before
    assert repository.load(bundle.document.workspace_id, snapshot) == loaded
