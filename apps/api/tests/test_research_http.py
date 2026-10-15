"""Protected research HTTP journey over dedicated synthetic PostgreSQL."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from issuedigest_api.cookies import SESSION_COOKIE
from issuedigest_api.main import create_app
from issuedigest_api.research import _bounded_bytes
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchRequest
from issuedigest_storage import EvidenceRepository, IdentityRepository, SessionRepository
from issuedigest_storage.research import ResearchRepository
from starlette.requests import Request

from conftest import bundle_data

ORIGIN = "https://example.test"


def test_selected_source_submit_reopen_and_cancel(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    client = TestClient(
        create_app(
            research_repository=repo,
            auth_service=SimpleNamespace(config=SimpleNamespace(public_origin=ORIGIN)),
        ),
        base_url=ORIGIN,
    )
    client.cookies.set(SESSION_COOKIE, token)
    path = f"/api/v1/workspaces/{bundle.document.workspace_id}/research"
    sources = client.get(path + "/sources")
    assert sources.status_code == 200
    assert sources.json()["items"][0]["title"] == "수집 자료"
    assert sources.headers["Cache-Control"] == "no-store"
    body = {
        "request_id": str(uuid4()),
        "question": "무엇인가?",
        "snapshot_ids": [str(snapshot)],
        "parent_run_id": None,
    }
    assert client.post(path, json=body).status_code == 403
    headers = {"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"}
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert client.post(path, json=body, headers=headers).json()["run_id"] == run_id
    assert client.get(path).json()["items"][0]["run_id"] == run_id
    assert client.get(path + "/" + run_id).json()["status"] == "queued"
    assert (
        client.post(
            path + "/" + run_id + "/cancel",
            content=b"{}",
            headers={**headers, "Content-Type": "application/json"},
        ).json()["status"]
        == "cancelled"
    )
    assert client.get(path + "/" + run_id).json()["status"] == "cancelled"
    assert (
        client.post(
            path,
            content=b'{"question":"A","question":"B"}',
            headers={**headers, "Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert client.get(path, params={"question": "secret"}).status_code == 422


def test_disabled_model_rejects_paid_submission_before_reservation(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    client = TestClient(
        create_app(
            research_repository=repo,
            research_model_available=False,
            auth_service=SimpleNamespace(config=SimpleNamespace(public_origin=ORIGIN)),
        ),
        base_url=ORIGIN,
    )
    client.cookies.set(SESSION_COOKIE, token)
    path = f"/api/v1/workspaces/{bundle.document.workspace_id}/research"
    response = client.post(
        path,
        json={
            "request_id": str(uuid4()),
            "question": "질문",
            "snapshot_ids": [str(snapshot)],
            "parent_run_id": None,
        },
        headers={"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"},
    )
    assert response.status_code == 503 and response.json() == {
        "detail": "Research model unavailable"
    }
    assert repo.list_runs(token, bundle.document.workspace_id).items == ()


def test_cancel_rejects_oversized_stream_before_reading_later_chunks(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="질문", snapshot_ids=(snapshot,)),
    )
    assert run is not None
    client = TestClient(
        create_app(
            research_repository=repo,
            auth_service=SimpleNamespace(config=SimpleNamespace(public_origin=ORIGIN)),
        ),
        base_url=ORIGIN,
    )
    client.cookies.set(SESSION_COOKIE, token)
    response = client.post(
        f"/api/v1/workspaces/{bundle.document.workspace_id}/research/{run.run_id}/cancel",
        content=b"{" + b" " * 16_384 + b"}",
        headers={
            "Origin": ORIGIN,
            "Sec-Fetch-Site": "same-origin",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 422 and response.json() == {"detail": "Invalid research request"}
    assert response.headers["Cache-Control"] == "no-store"

    consumed = 0

    async def receive():
        nonlocal consumed
        consumed += 1
        return {
            "type": "http.request",
            "body": b"{" + b" " * 16_384 if consumed == 1 else b"}",
            "more_body": consumed == 1,
        }

    request = Request({"type": "http", "method": "POST", "path": "/"}, receive)
    with pytest.raises(HTTPException) as error:
        asyncio.run(_bounded_bytes(request))
    assert error.value.status_code == 422
    assert consumed == 1
