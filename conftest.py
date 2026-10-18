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
                "TRUNCATE policy_collection_attempts, policy_collection_channels, "
                "public_briefings, public_briefing_heads, research_events, "
                "research_runs, research_budget_months, "
                "source_presentations, auth_oauth_flows, auth_identity_invites, auth_sessions, "
                "auth_workspace_memberships, auth_users, outbox, "
                "snapshot_citations, evidence_snapshots, citations, "
                "parsed_representations, document_versions, source_documents CASCADE"
            )
        )
    return migrated


def overlapping_session_reads(engine, first_call, second_call, after_conflict=None):
    """Hold the first real session row lock until PostgreSQL proves the second is blocked."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic

    from sqlalchemy import event, text

    first_locked, second_started, release_first = Event(), Event(), Event()
    pids = {}
    conflicts = []

    def is_session_lock(statement):
        return "SELECT auth_sessions.token_sha256" in statement and "FOR UPDATE" in statement

    def before_execute(conn, cursor, statement, parameters, context, executemany):
        if not is_session_lock(statement):
            return
        pid = conn.connection.driver_connection.info.backend_pid
        if "first" not in pids:
            pids["first"] = pid
        elif pid != pids["first"]:
            pids.setdefault("second", pid)
            second_started.set()

    def after_execute(conn, cursor, statement, parameters, context, executemany):
        if is_session_lock(
            statement
        ) and conn.connection.driver_connection.info.backend_pid == pids.get("first"):
            first_locked.set()
            assert release_first.wait(timeout=10), "overlap coordinator did not release first read"

    def on_error(context):
        if (
            context.connection is not None
            and context.connection.connection.driver_connection.info.backend_pid
            == pids.get("second")
            and getattr(context.original_exception, "sqlstate", None) == "40001"
        ):
            conflicts.append(True)
            if after_conflict is not None:
                after_conflict()

    def run(call):
        try:
            value = call()
            return "ok", value
        except Exception as error:
            return type(error).__name__, None

    listeners = [
        ("before_cursor_execute", before_execute),
        ("after_cursor_execute", after_execute),
        ("handle_error", on_error),
    ]
    for name, callback in listeners:
        event.listen(engine, name, callback)
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(run, first_call)
            try:
                assert first_locked.wait(timeout=5), "first session lock was not acquired"
                second = executor.submit(run, second_call)
                assert second_started.wait(timeout=5), "second session read did not start"
                # Observer connection only inspects wait state; both worker reads remain real.
                deadline = monotonic() + 5
                with engine.connect() as observer:
                    while pids["first"] not in observer.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["second"]}
                    ):
                        assert monotonic() < deadline, "second read did not block on first lock"
                        Event().wait(0.01)
                release_first.set()
                results = [first.result(timeout=5), second.result(timeout=5)]
            finally:
                release_first.set()
        return results, len(conflicts)
    finally:
        for name, callback in listeners:
            event.remove(engine, name, callback)


@pytest.fixture
def historical_expanded_run(engine):
    """A real v1 seed plus later indexed hit; the added document is cited."""
    import json

    from issuedigest_agents.research import AIOutput, build_canvas
    from issuedigest_domain import EvidenceBundle
    from issuedigest_domain.research_journey import (
        ResearchRequest,
        ResearchResult,
        presentation_for,
    )
    from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
    from issuedigest_storage.research import ResearchRepository
    from issuedigest_storage.research_schema import research_events, research_runs
    from issuedigest_storage.search import rebuild_projection
    from sqlalchemy import insert, select, update

    workspace, actor = uuid4(), uuid4()
    sources = []
    for text in ("주거지원 기존 발표", "주거지원 추가 발표"):
        data = bundle_data()
        data["document"]["workspace_id"] = str(workspace)
        data["version"]["media_type"] = "text/plain"
        data["representation"].update(
            text=text, text_sha256=sha256(text.encode()).hexdigest(), pages=[], tables=[]
        )
        data["citations"] = [data["citations"][0]]
        data["citations"][0]["selector"] = {
            "kind": "text",
            "start": 0,
            "end": len(text),
            "quote": text,
        }
        bundle = EvidenceBundle.model_validate(data)
        snapshot = uuid4()
        EvidenceRepository(engine).save(snapshot, bundle)
        with engine.begin() as conn:
            rebuild_projection(conn, workspace, snapshot)
        sources.append((snapshot, bundle, presentation_for(bundle, snapshot)))
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, workspace, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(token, workspace, ResearchRequest(request_id=uuid4(), question="주거지원은?"))
    proposal = AIOutput.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "summary",
                    "title": "요약",
                    "claims": [
                        {
                            "text": "추가 발표의 합성 해석",
                            "citation_ids": [sources[1][1].citations[0].citation_id],
                        }
                    ],
                }
            ],
        }
    )
    canvas = build_canvas(run.run_id, workspace, tuple(sources), proposal).model_dump(mode="json")
    canvas["research"]["claims"][0]["derivation"]["method_version"] = "research-v1"
    result = ResearchResult.model_validate(
        {
            "canvas": canvas,
            "source_titles": {
                str(bundle.document.document_id): f"합성 자료 {index}"
                for index, (_, bundle, _) in enumerate(sources)
            },
        }
    )
    seed_ids = [str(sources[0][0])]
    legacy_input = {"question": run.question, "snapshot_ids": seed_ids, "parent_run_id": None}
    with engine.begin() as conn:
        # Reproduce the historical persisted shape rather than publishing it through v2.
        conn.execute(
            update(research_runs)
            .where(research_runs.c.run_id == run.run_id)
            .values(
                status="completed",
                snapshot_ids=seed_ids,
                result=result.model_dump(mode="json"),
                input_hash=sha256(
                    json.dumps(legacy_input, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest(),
            )
        )
        conn.execute(
            insert(research_events).values(run_id=run.run_id, sequence=2, status="completed")
        )
        before = dict(conn.execute(select(research_runs)).mappings().one())
        events = [dict(row) for row in conn.execute(select(research_events)).mappings()]
    return {
        "repo": repo,
        "run": run,
        "workspace": workspace,
        "actor": actor,
        "token": token,
        "sources": tuple(sources),
        "result": result,
        "before": before,
        "events": events,
    }


def public_plan_data():
    proof = bundle_data()
    proof["document"]["canonical_url"] = (
        "https://www.korea.kr/news/policyNewsView.do?newsId=148000001"
    )
    workspace = proof["document"]["workspace_id"]
    citation = proof["citations"][0]["citation_id"]
    claim_id = str(uuid4())
    return {
        "slug": "synthetic-policy",
        "public_id": str(uuid4()),
        "version": 1,
        "title": "합성 정책 브리핑",
        "description": "검토한 합성 설명",
        "as_of": "2026-10-13T00:00:00Z",
        "canvas": {
            "research": {
                "workspace_id": workspace,
                "evidence": [proof],
                "entities": [],
                "claims": [
                    {
                        "claim_id": claim_id,
                        "workspace_id": workspace,
                        "text": "합성 근거에서 도출한 해석",
                        "basis": "inference",
                        "citation_ids": [citation],
                        "derivation": {
                            "method": "pydantic-ai",
                            "method_version": "research-v2",
                            "rationale": "합성 인용에 대한 해석",
                        },
                    }
                ],
                "relations": [],
                "observations": [],
                "support_reviews": [],
            },
            "revision": {
                "revision_id": str(uuid4()),
                "workspace_id": workspace,
                "run_id": str(uuid4()),
                "revision_number": 1,
                "parent_revision_id": None,
                "selected_version_ids": [proof["version"]["version_id"]],
                "validated_at": "2026-10-13T00:00:00Z",
                "draft": {
                    "draft_id": str(uuid4()),
                    "outcome": "answer",
                    "message": None,
                    "modules": [
                        {
                            "kind": "summary",
                            "module_id": str(uuid4()),
                            "title": "요약",
                            "span": "full",
                            "citation_ids": [citation],
                            "claim_ids": [claim_id],
                            "actions": [{"kind": "open_evidence", "citation_id": citation}],
                        },
                        {
                            "kind": "evidence",
                            "module_id": str(uuid4()),
                            "title": "근거",
                            "span": "full",
                            "citation_ids": [citation],
                            "actions": [{"kind": "open_evidence", "citation_id": citation}],
                        },
                    ],
                },
            },
        },
        "sources": [
            {
                "document_id": proof["document"]["document_id"],
                "official_url": proof["document"]["canonical_url"],
                "title": "합성 정책 원문",
                "publisher": "합성 발행처",
                "published_on": "2026-10-12",
                "checked_at": "2026-10-13T00:00:00Z",
                "reviewer": "private-reviewer",
                "license": "kogl-type-1",
                "attribution": "합성 발행처 / 합성 정책 원문 / 공공누리 제1유형",
                "text_sha256": proof["representation"]["text_sha256"],
                "photos_excluded": True,
                "third_party_material_excluded": True,
            }
        ],
    }
