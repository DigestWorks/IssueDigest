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


def test_question_submit_reopen_and_cancel(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, actor = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
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
    assert client.get(path + "/sources").status_code == 422
    body = {
        "request_id": str(uuid4()),
        "question": "무엇인가?",
        "parent_run_id": None,
    }
    assert client.post(path, json=body).status_code == 403
    headers = {"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"}
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["snapshot_ids"] == []
    for injected in ([str(snapshot)], [str(uuid4())]):
        assert (
            client.post(path, json={**body, "snapshot_ids": injected}, headers=headers).status_code
            == 422
        )
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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
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
    with engine.begin() as conn:
        from issuedigest_storage.search import rebuild_projection

        rebuild_projection(conn, bundle.document.workspace_id, snapshot)
    identities = IdentityRepository(engine)
    identities.register_identity(actor, "synthetic", str(actor))
    identities.set_membership(actor, bundle.document.workspace_id, "owner")
    token = SessionRepository(engine).issue_session(actor).token
    repo = ResearchRepository(engine)
    run = repo.submit(
        token,
        bundle.document.workspace_id,
        ResearchRequest(request_id=uuid4(), question="80% 의미는?"),
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


def test_historical_added_source_is_readable_through_existing_protected_api(
    engine, historical_expanded_run
):
    from issuedigest_storage import EvidenceAccessRepository
    from issuedigest_storage.research_schema import research_runs
    from issuedigest_storage.schema import evidence_snapshots
    from sqlalchemy import select, update

    old = historical_expanded_run
    client = TestClient(
        create_app(
            access_repository=EvidenceAccessRepository(engine), research_repository=old["repo"]
        ),
        base_url=ORIGIN,
    )
    client.cookies.set(SESSION_COOKIE, old["token"])
    path = f"/api/v1/workspaces/{old['workspace']}"
    run_path = f"{path}/research/{old['run'].run_id}"
    added_id, added, _ = old["sources"][1]
    response = client.get(run_path)
    assert response.status_code == 200
    assert response.json()["snapshot_ids"] == [str(source[0]) for source in old["sources"]]
    assert response.json()["result"] == old["result"].model_dump(mode="json")
    assert client.get(path + "/research").json()["items"][0] == response.json()
    original = client.get(f"{path}/evidence/{added_id}")
    assert original.status_code == 200 and original.json() == added.model_dump(mode="json")
    assert original.headers["Cache-Control"] == response.headers["Cache-Control"] == "no-store"
    with engine.connect() as conn:
        assert dict(conn.execute(select(research_runs)).mappings().one()) == old["before"]
    with engine.begin() as conn:
        conn.execute(
            update(evidence_snapshots)
            .where(evidence_snapshots.c.snapshot_id == added_id)
            .values(content_sha256="0" * 64)
        )
    assert client.get(run_path).status_code == 503
    assert client.get(path + "/research").status_code == 503
    assert client.get(f"{path}/evidence/{added_id}").status_code == 503
    IdentityRepository(engine).set_membership(old["actor"], old["workspace"], "owner", False)
    assert client.get(run_path).status_code == 404
    assert client.get(path + "/research").status_code == 404
    assert client.get(f"{path}/evidence/{added_id}").status_code == 404
