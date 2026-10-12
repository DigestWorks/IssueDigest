"""Synthetic PostgreSQL persistence boundaries; no production database access."""

import importlib
import os
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC
from hashlib import sha256
from pathlib import Path
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from issuedigest_domain import EvidenceBundle


def storage():
    try:
        return importlib.import_module("issuedigest_storage")
    except ModuleNotFoundError:
        pytest.fail("PostgreSQL EvidenceRepository is not implemented")


def bundle_data():
    document, workspace, version, representation = [str(uuid4()) for _ in range(4)]
    text = "앞 😀한e\u0301é 뒤"
    selectors = [
        {"kind": "table_cell", "table_id": "t1", "cell_id": "c1", "quote": "80%"},
        {"kind": "pdf", "page_number": 1, "start": 2, "end": 7, "quote": "😀한e\u0301é"},
        {"kind": "text", "start": 0, "end": 1, "quote": "앞", "suffix": " "},
    ]
    return {
        "document": {
            "document_id": document,
            "workspace_id": workspace,
            "provider": "synthetic",
            "source_id": str(uuid4()),
            "source_kind": "other",
        },
        "version": {
            "version_id": version,
            "document_id": document,
            "raw_object_id": str(uuid4()),
            "raw_sha256": "a" * 64,
            "media_type": "application/pdf",
            "collected_at": "2026-10-12T09:00:00+09:00",
        },
        "representation": {
            "representation_id": representation,
            "document_version_id": version,
            "parser_name": "synthetic",
            "parser_version": "1",
            "normalization_profile": "identity",
            "text": text,
            "text_sha256": sha256(text.encode()).hexdigest(),
            "pages": [{"page_number": 1, "start": 0, "end": len(text)}],
            "tables": [{"table_id": "t1", "cells": [{"cell_id": "c1", "text": "80%"}]}],
        },
        "citations": [
            {
                "citation_id": str(uuid4()),
                "document_version_id": version,
                "representation_id": representation,
                "selector": selector,
            }
            for selector in selectors
        ],
    }


@pytest.fixture(scope="session")
def database_url():
    url = os.environ.get("ISSUEDIGEST_TEST_DATABASE_URL")
    if not url:
        if os.environ.get("CI"):
            pytest.fail("CI must supply ISSUEDIGEST_TEST_DATABASE_URL")
        pytest.skip("PostgreSQL integration: ISSUEDIGEST_TEST_DATABASE_URL is not set")
    # Parsing the URL never opens a connection. Guard every destructive fixture operation.
    from sqlalchemy.engine import make_url

    parsed = make_url(url)
    assert parsed.drivername == "postgresql+psycopg", "dedicated PostgreSQL URL required"
    assert parsed.database == "issuedigest_test", "only the dedicated synthetic DB may be reset"
    assert parsed.host in {"127.0.0.1", "localhost"}, "local synthetic DB required"
    assert not parsed.query, "query overrides are forbidden for the synthetic database"
    return url


def migration_config(database_url):
    from alembic.config import Config

    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


@pytest.fixture(scope="session")
def migrated(database_url):
    api = storage()
    from alembic import command

    engine = api.create_storage_engine(database_url)
    config = migration_config(database_url)
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def engine(migrated):
    from sqlalchemy import text

    with migrated.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE outbox, snapshot_citations, evidence_snapshots, citations, "
                "parsed_representations, document_versions, source_documents CASCADE"
            )
        )
    return migrated


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
