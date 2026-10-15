"""Protected literal search HTTP boundary and owned PostgreSQL integration."""

import asyncio
import logging
import secrets
import time
from threading import Event, Timer
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from issuedigest_api.cookies import SESSION_COOKIE
from issuedigest_api.main import create_app
from issuedigest_domain import (
    EvidenceBundle,
    EvidenceSearchHit,
    EvidenceSearchQuery,
    EvidenceSearchResult,
)
from issuedigest_storage import (
    EvidenceRepository,
    IdentityRepository,
    SessionRepository,
    StorageError,
    WorkspaceAccessRepository,
)

from conftest import bundle_data

ORIGIN = "https://example.test"
HEADERS = {"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"}
WORKSPACE = uuid4()
PATH = f"/api/v1/workspaces/{WORKSPACE}/evidence/search"
QUERY = {"terms": ["한국어"]}


def client_with(repository=None, origin=True):
    service = SimpleNamespace(config=SimpleNamespace(public_origin=ORIGIN)) if origin else None
    client = TestClient(
        create_app(auth_service=service, workspace_repository=repository), base_url=ORIGIN
    )
    client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
    return client


def checked(response, status):
    assert response.status_code == status
    assert response.headers["Cache-Control"] == "no-store"
    assert UUID(response.headers["X-Request-ID"]).version == 4


class SearchRepository:
    def search_evidence(self, token, workspace_id, query):
        return EvidenceSearchResult(
            workspace_id=workspace_id,
            query=query,
            hits=(),
            coverage={
                "total_snapshots": 1,
                "indexed_snapshots": 0,
                "missing_snapshots": 1,
                "skipped_empty_cells": 0,
                "skipped_large_cells": 0,
            },
            scanned_candidates=0,
            truncated=False,
        )


def test_search_is_cookie_origin_bound_and_reports_missing_index():
    client = client_with(SearchRepository())
    result = client.post(PATH, json=QUERY, headers=HEADERS)
    checked(result, 200)
    assert result.json()["query"]["terms"] == ["한국어"]
    assert result.json()["coverage"]["missing_snapshots"] == 1
    checked(client.post(PATH, json=QUERY), 403)
    checked(client.post(PATH, json=QUERY, headers={"Origin": "https://elsewhere.test"}), 403)
    checked(client.post(PATH, json=QUERY, headers=HEADERS, params={"private": "x"}), 422)
    checked(
        client_with(SearchRepository(), origin=False).post(PATH, json=QUERY, headers=HEADERS), 503
    )
    anonymous = TestClient(create_app(workspace_repository=SearchRepository()), base_url=ORIGIN)
    checked(anonymous.post(PATH, json=QUERY, headers=HEADERS), 401)


def test_search_accepts_utc_json_date_filters_and_rejects_bad_intervals():
    client = client_with(SearchRepository())
    valid = {
        **QUERY,
        "collected_from": "2026-10-14T00:00:00.000001Z",
        "collected_to": "2026-10-14T00:00:00.000002+00:00",
    }
    response = client.post(PATH, json=valid, headers=HEADERS)
    checked(response, 200)
    assert response.json()["query"]["collected_from"] == valid["collected_from"]
    assert response.json()["query"]["collected_to"] == "2026-10-14T00:00:00.000002Z"
    for bad in [
        {**QUERY, "collected_from": "2026-10-14T09:00:00+09:00"},
        {**QUERY, "collected_from": valid["collected_to"], "collected_to": valid["collected_from"]},
    ]:
        rejected = client.post(PATH, json=bad, headers=HEADERS)
        checked(rejected, 422)
        assert rejected.json() == {"detail": "Invalid evidence search request"}


def test_slow_search_storage_does_not_block_health_requests():
    entered, release = Event(), Event()
    started = []
    timers = []

    class Slow(SearchRepository):
        def search_evidence(self, token, workspace_id, query):
            started.append(time.monotonic())
            entered.set()
            timer = Timer(0.75, release.set)
            timers.append(timer)
            timer.start()
            release.wait(2)
            return super().search_evidence(token, workspace_id, query)

    async def concurrent_requests():
        transport = httpx2.ASGITransport(
            app=create_app(
                auth_service=SimpleNamespace(config=SimpleNamespace(public_origin=ORIGIN)),
                workspace_repository=Slow(),
            )
        )
        async with httpx2.AsyncClient(transport=transport, base_url=ORIGIN) as client:
            client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
            pending = asyncio.create_task(client.post(PATH, json=QUERY, headers=HEADERS))
            assert await asyncio.to_thread(entered.wait, 2)
            health = await client.get("/health/live")
            elapsed = time.monotonic() - started[0]
            release.set()
            search = await pending
            return health, search, elapsed

    try:
        health, search, elapsed = asyncio.run(concurrent_requests())
        assert health.status_code == 200
        checked(search, 200)
        assert elapsed < 0.5
    finally:
        release.set()
        for timer in timers:
            timer.cancel()


def test_search_slash_redirect_does_not_reflect_query_string():
    response = client_with(SearchRepository()).post(
        PATH + "/?private=sentinel", json=QUERY, headers=HEADERS, follow_redirects=False
    )
    checked(response, 422)
    assert response.json() == {"detail": "Invalid evidence search request"}
    assert "sentinel" not in str(response.headers) + response.text


def test_search_openapi_describes_body_cookie_and_both_422_shapes():
    schema = TestClient(create_app()).get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/workspaces/{workspace_id}/evidence/search"]["post"]
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EvidenceSearchQuery"
    }
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EvidenceSearchResult"
    }
    assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
        "oneOf": [
            {"$ref": "#/components/schemas/EvidenceSearchRequestError"},
            {"$ref": "#/components/schemas/EvidencePathValidationError"},
        ]
    }
    security = next(iter(operation["security"][0]))
    assert schema["components"]["securitySchemes"][security]["in"] == "cookie"


@pytest.mark.parametrize(
    "body,media",
    [
        (b'{"terms":["x"],"terms":["y"]}', "application/json"),
        (b'{"terms":["x"]} PRIVATE', "application/json"),
        (b'{"terms":["\xff"]}', "application/json"),
        (b'{"terms":[]}', "application/json"),
        (b'{"terms":["x"]}' + b" " * 16385, "application/json"),
        (b'{"terms":["x"]}', "text/plain"),
    ],
)
def test_invalid_requests_are_fixed_and_do_not_echo_input(body, media, caplog):
    with caplog.at_level(logging.WARNING):
        response = client_with(SearchRepository()).post(
            PATH, content=body, headers=HEADERS | {"Content-Type": media}
        )
    checked(response, 422)
    assert response.json() == {"detail": "Invalid evidence search request"}
    assert "PRIVATE" not in response.text + caplog.text


def test_bad_path_and_backend_failure_are_sanitized(caplog):
    client = client_with(SearchRepository())
    checked(client.post("/api/v1/workspaces/bad/evidence/search", json=QUERY, headers=HEADERS), 422)

    class Broken(SearchRepository):
        def search_evidence(self, token, workspace_id, query):
            raise StorageError("PRIVATE backend failure")

    with caplog.at_level(logging.WARNING):
        response = client_with(Broken()).post(PATH, json=QUERY, headers=HEADERS)
    checked(response, 503)
    assert response.json() == {"detail": "Evidence service unavailable"}
    assert "PRIVATE" not in response.text + caplog.text


@pytest.mark.parametrize(
    "mutation", ["workspace", "query", "hit_workspace", "terms", "quote", "coverage", "filter"]
)
def test_forged_backend_results_fail_closed(mutation):
    query = EvidenceSearchQuery(terms=("한국어",), provider="synthetic")
    hit = EvidenceSearchHit(
        workspace_id=WORKSPACE,
        snapshot_id=uuid4(),
        document_id=uuid4(),
        version_id=uuid4(),
        representation_id=uuid4(),
        provider="synthetic",
        source_id="item",
        source_kind="other",
        collected_at="2026-10-14T00:00:00Z",
        unit_ordinal=0,
        selector={"kind": "text", "start": 0, "end": 3, "quote": "한국어"},
        matched_terms=query.terms,
    )
    result = EvidenceSearchResult(
        workspace_id=WORKSPACE,
        query=query,
        hits=(hit,),
        coverage={
            "total_snapshots": 1,
            "indexed_snapshots": 1,
            "missing_snapshots": 0,
            "skipped_empty_cells": 0,
            "skipped_large_cells": 0,
        },
        scanned_candidates=1,
        truncated=False,
    )
    if mutation == "workspace":
        result = result.model_copy(update={"workspace_id": uuid4()})
    elif mutation == "query":
        result = result.model_copy(update={"query": EvidenceSearchQuery(terms=("other",))})
    elif mutation == "hit_workspace":
        result = result.model_copy(
            update={"hits": (hit.model_copy(update={"workspace_id": uuid4()}),)}
        )
    elif mutation == "terms":
        result = result.model_copy(
            update={"hits": (hit.model_copy(update={"matched_terms": ("other",)}),)}
        )
    elif mutation == "quote":
        result = result.model_copy(
            update={
                "hits": (
                    hit.model_copy(
                        update={"selector": hit.selector.model_copy(update={"quote": "other"})}
                    ),
                )
            }
        )
    elif mutation == "coverage":
        result = result.model_copy(
            update={"coverage": result.coverage.model_copy(update={"indexed_snapshots": 0})}
        )
    else:
        result = result.model_copy(update={"hits": (hit.model_copy(update={"provider": "other"}),)})

    class Forged:
        def search_evidence(self, token, workspace_id, requested):
            return result

    response = client_with(Forged()).post(
        PATH, json={"terms": ["한국어"], "provider": "synthetic"}, headers=HEADERS
    )
    checked(response, 503)
    assert response.json() == {"detail": "Evidence service unavailable"}


def test_duplicate_backend_hit_identity_is_unavailable():
    query = EvidenceSearchQuery(terms=("한국어",), limit=2)
    hit = EvidenceSearchHit(
        workspace_id=WORKSPACE,
        snapshot_id=uuid4(),
        document_id=uuid4(),
        version_id=uuid4(),
        representation_id=uuid4(),
        provider="synthetic",
        source_id="item",
        source_kind="other",
        collected_at="2026-10-14T00:00:00Z",
        unit_ordinal=0,
        selector={"kind": "text", "start": 0, "end": 3, "quote": "한국어"},
        matched_terms=query.terms,
    )
    result = EvidenceSearchResult(
        workspace_id=WORKSPACE,
        query=query,
        hits=(hit, hit),
        coverage={
            "total_snapshots": 1,
            "indexed_snapshots": 1,
            "missing_snapshots": 0,
            "skipped_empty_cells": 0,
            "skipped_large_cells": 0,
        },
        scanned_candidates=2,
        truncated=False,
    )

    class Duplicate:
        def search_evidence(self, token, workspace_id, requested):
            return result

    response = client_with(Duplicate()).post(
        PATH, json={"terms": ["한국어"], "limit": 2}, headers=HEADERS
    )
    checked(response, 503)


def test_real_storage_search_requires_membership_and_live_session(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(user, "synthetic", str(user))
    identities.set_membership(user, bundle.document.workspace_id, "viewer")
    sessions = SessionRepository(engine)
    issued = sessions.issue_session(user)
    client = TestClient(
        create_app(
            workspace_repository=WorkspaceAccessRepository(engine),
            auth_service=SimpleNamespace(config=SimpleNamespace(public_origin=ORIGIN)),
        ),
        base_url=ORIGIN,
    )
    client.cookies.set(SESSION_COOKIE, issued.token)
    path = f"/api/v1/workspaces/{bundle.document.workspace_id}/evidence/search"
    missing = client.post(path, json={"terms": [bundle.representation.text[:4]]}, headers=HEADERS)
    checked(missing, 200)
    assert missing.json()["coverage"]["missing_snapshots"] == 1
    EvidenceRepository(engine).rebuild_projection(bundle.document.workspace_id, snapshot)
    found = client.post(
        path, json={"terms": [bundle.representation.text[:4]], "limit": 1}, headers=HEADERS
    )
    checked(found, 200)
    assert found.json()["hits"]
    assert len(found.json()["hits"]) <= 1
    filtered = client.post(
        path,
        json={
            "terms": [bundle.representation.text[:4]],
            "collected_from": "2026-10-11T23:59:59.999999Z",
            "collected_to": "2026-10-12T00:00:00.000001Z",
        },
        headers=HEADERS,
    )
    checked(filtered, 200)
    assert filtered.json()["hits"]
    checked(
        client.post(f"/api/v1/workspaces/{uuid4()}/evidence/search", json=QUERY, headers=HEADERS),
        404,
    )
    sessions.revoke_session(issued.token)
    checked(client.post(path, json=QUERY, headers=HEADERS), 401)
