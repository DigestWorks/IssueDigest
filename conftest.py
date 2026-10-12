"""Shared guarded synthetic PostgreSQL fixtures."""

import importlib
import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest


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

    config = Config(str(Path(__file__).parent / "packages/storage/alembic.ini"))
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
                "TRUNCATE auth_sessions, auth_workspace_memberships, auth_users, outbox, "
                "snapshot_citations, evidence_snapshots, citations, "
                "parsed_representations, document_versions, source_documents CASCADE"
            )
        )
    return migrated
