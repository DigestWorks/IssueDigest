"""Synthetic provider and owned PostgreSQL exercise the entire protected journey."""

import importlib
import secrets
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from issuedigest_api.cookies import SESSION_COOKIE
from issuedigest_api.main import create_app
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import (
    EvidenceAccessRepository,
    EvidenceRepository,
    IdentityRepository,
    OAuthRepository,
    SessionRepository,
    StorageError,
    WorkspaceAccessRepository,
)
from sqlalchemy import text
from test_google_oauth import CONFIG, claims, signed
from test_google_oauth import signing as signing  # fixture

from conftest import bundle_data

ORIGIN = CONFIG.public_origin
FLOW_COOKIE = "__Host-issuedigest_oauth"
HEADERS = {"Origin": ORIGIN, "Sec-Fetch-Site": "same-origin"}


def checked(response, status):
    assert response.status_code == status
    assert response.headers["Cache-Control"] == "no-store"
    assert UUID(response.headers["X-Request-ID"]).version == 4


def test_unconfigured_routes_fail_closed_and_callback_is_fixed(caplog):
    client = TestClient(create_app(), base_url=ORIGIN)
    checked(client.post("/api/v1/auth/google/start", headers=HEADERS), 503)
    checked(client.get("/api/v1/auth/session"), 401)
    client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
    checked(client.get("/api/v1/auth/session"), 503)
    checked(client.get(f"/api/v1/workspaces/{uuid4()}/evidence"), 503)
    checked(client.post("/api/v1/auth/logout", headers=HEADERS), 503)
    response = client.get(
        "/api/v1/auth/google/callback?code=PRIVATE&state=PRIVATE", follow_redirects=False
    )
    checked(response, 303)
    assert response.headers["location"] == "/login?error=unavailable"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Max-Age=0" in response.headers["set-cookie"]
    checked(client.get("/api/v1/auth/PRIVATE?token=PRIVATE"), 404)
    assert "PRIVATE" not in caplog.text


def setup(engine, signing):
    auth = importlib.import_module("issuedigest_api.auth")
    google = importlib.import_module("issuedigest_api.google_oauth")
    repo = OAuthRepository(engine)
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    repo.register_invite(
        google.GOOGLE_ISSUER, "invited@gmail.com", user, bundle.document.workspace_id, "viewer"
    )
    pending = {}
    requests = []

    def transport(request):
        requests.append(request)
        if str(request.url) == google.TOKEN_URL:
            return httpx2.Response(
                200, json={"id_token": signed(signing, claims(nonce=pending["nonce"]))}
            )
        return httpx2.Response(200, json={"synthetic-key": signing[1]})

    service = auth.AuthService(
        CONFIG,
        repo,
        SessionRepository(engine),
        google.GoogleOAuthProvider(CONFIG, transport=httpx2.MockTransport(transport)),
    )
    client = TestClient(
        create_app(
            EvidenceAccessRepository(engine),
            auth_service=service,
            workspace_repository=WorkspaceAccessRepository(engine),
        ),
        base_url=ORIGIN,
    )
    return client, repo, bundle, snapshot, user, pending, requests


def start(client, pending):
    response = client.post("/api/v1/auth/google/start", headers=HEADERS, follow_redirects=False)
    checked(response, 303)
    parsed = urlsplit(response.headers["location"])
    assert parsed.netloc == "accounts.google.com"
    params = parse_qs(parsed.query)
    pending.update({key: values[0] for key, values in params.items()})
    cookie = response.headers["set-cookie"]
    for flag in ["Secure", "HttpOnly", "SameSite=lax", "Path=/", "Max-Age=600"]:
        assert flag in cookie
    assert "Domain=" not in cookie
    return pending["state"]


def callback(client, state, **params):
    return client.get(
        "/api/v1/auth/google/callback",
        params={"state": state, "code": "synthetic-code"} | params,
        follow_redirects=False,
    )


def test_signed_start_callback_session_catalog_detail_logout_journey(engine, signing):
    client, repo, bundle, snapshot, user, pending, requests = setup(engine, signing)
    state = start(client, pending)
    response = callback(client, state)
    checked(response, 303)
    assert response.headers["location"] == "/"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert len(requests) == 2
    cookie = response.headers.get_list("set-cookie")
    session_cookie = next(item for item in cookie if item.startswith(SESSION_COOKIE + "="))
    for flag in ["Secure", "HttpOnly", "SameSite=lax", "Path=/"]:
        assert flag in session_cookie
    assert any(item.startswith(FLOW_COOKIE + "=") and "Max-Age=0" in item for item in cookie)
    info = client.get("/api/v1/auth/session")
    checked(info, 200)
    assert info.json() == {
        "schema_version": 1,
        "user_id": str(user),
        "memberships": [{"workspace_id": str(bundle.document.workspace_id), "role": "viewer"}],
    }
    assert "synthetic-subject" not in info.text and "gmail" not in info.text
    catalog = client.get(f"/api/v1/workspaces/{bundle.document.workspace_id}/evidence")
    checked(catalog, 200)
    assert catalog.json()["items"][0]["snapshot_id"] == str(snapshot)
    detail = client.get(f"/api/v1/workspaces/{bundle.document.workspace_id}/evidence/{snapshot}")
    checked(detail, 200)
    assert detail.json() == bundle.model_dump(mode="json")
    token = client.cookies.get(SESSION_COOKIE)
    response = callback(client, state)
    assert response.headers["location"] == "/login?error=invalid"
    assert client.cookies.get(SESSION_COOKIE) == token
    checked(client.get("/api/v1/auth/session"), 200)
    checked(client.get("/api/v1/auth/logout"), 405)
    checked(client.get("/api/v1/auth/session"), 200)
    checked(client.post("/api/v1/auth/logout", headers=HEADERS), 204)
    assert client.cookies.get(SESSION_COOKIE) is None
    checked(client.get("/api/v1/auth/session"), 401)
    client.cookies.set(SESSION_COOKIE, token)
    checked(client.get("/api/v1/auth/session"), 401)


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.test"},
        {"Origin": ORIGIN, "Sec-Fetch-Site": "cross-site"},
        {"Origin": ORIGIN + "/"},
    ],
)
def test_csrf_rejected_before_storage(engine, signing, headers):
    client, _, _, _, _, pending, requests = setup(engine, signing)
    for path in ["/api/v1/auth/google/start", "/api/v1/auth/logout"]:
        checked(client.post(path, headers=headers), 403)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_oauth_flows")) == 0
    assert not requests


@pytest.mark.parametrize(
    "query",
    [
        "state=bad&code=PRIVATE",
        "state={state}&code=PRIVATE&code=other",
        "state={state}&state={state}&code=PRIVATE",
        "state={state}&code=PRIVATE&error=PRIVATE",
        "state={state}&code=PRIVATE&iss=https://evil.test",
        "state={state}&code=%00",
        "state={state}&code=" + "x" * 2049,
        "state={state}",
    ],
)
def test_callback_invalid_inputs_do_not_call_provider_or_reflect(engine, signing, query):
    client, _, _, _, _, pending, requests = setup(engine, signing)
    state = start(client, pending)
    response = client.get(
        "/api/v1/auth/google/callback?" + query.format(state=state), follow_redirects=False
    )
    checked(response, 303)
    assert response.headers["location"] == "/login?error=invalid"
    assert "PRIVATE" not in response.text and not requests


def test_decline_consumes_valid_flow_and_clears_cookie(engine, signing):
    client, _, _, _, _, pending, requests = setup(engine, signing)
    state = start(client, pending)
    response = client.get(
        "/api/v1/auth/google/callback",
        params={"state": state, "error": "PRIVATE", "error_description": "PRIVATE"},
        follow_redirects=False,
    )
    checked(response, 303)
    assert response.headers["location"] == "/login?error=denied"
    assert not requests
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_oauth_flows")) == 0


def test_browser_binding_mismatch_keeps_flow_for_correct_browser(engine, signing):
    client, _, _, _, _, pending, requests = setup(engine, signing)
    state = start(client, pending)
    cookie = client.cookies.get(FLOW_COOKIE)
    client.cookies.set(FLOW_COOKIE, secrets.token_urlsafe(32), domain="localhost.local", path="/")
    assert callback(client, state).headers["location"] == "/login?error=invalid"
    assert not requests
    client.cookies.set(FLOW_COOKIE, cookie, domain="localhost.local", path="/")
    assert callback(client, state).headers["location"] == "/"


def test_session_replacement_failure_preserves_previous_and_success_revokes(engine, signing):
    client, repo, _, _, user, pending, _ = setup(engine, signing)
    state = start(client, pending)
    assert callback(client, state).headers["location"] == "/"
    previous = client.cookies.get(SESSION_COOKIE)
    state = start(client, pending)
    IdentityRepository(engine).set_enabled(user, False)
    assert callback(client, state).headers["location"] == "/login?error=invalid"
    assert client.cookies.get(SESSION_COOKIE) == previous
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT revoked FROM auth_sessions")) is False
    IdentityRepository(engine).set_enabled(user, True)
    state = start(client, pending)
    assert callback(client, state).headers["location"] == "/"
    assert client.cookies.get(SESSION_COOKIE) != previous
    client.cookies.set(SESSION_COOKIE, previous, domain="localhost.local", path="/")
    checked(client.get("/api/v1/auth/session"), 401)


@pytest.mark.parametrize("limit", ["0", "51", "1.0", "01", "true", "PRIVATE"])
def test_catalog_limit_is_strict_and_validation_private(limit):
    client = TestClient(create_app())
    response = client.get(f"/api/v1/workspaces/{uuid4()}/evidence", params={"limit": limit})
    checked(response, 422)
    assert "PRIVATE" not in response.text and "input" not in response.text


def test_membership_revocation_empty_catalog_and_nonmember(engine, signing):
    client, _, bundle, _, user, pending, _ = setup(engine, signing)
    assert callback(client, start(client, pending)).headers["location"] == "/"
    checked(client.get(f"/api/v1/workspaces/{uuid4()}/evidence"), 404)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM outbox"))
        conn.execute(text("DELETE FROM snapshot_citations"))
        conn.execute(text("DELETE FROM evidence_snapshots"))
    response = client.get(f"/api/v1/workspaces/{bundle.document.workspace_id}/evidence")
    checked(response, 200)
    assert response.json()["items"] == [] and response.json()["has_more"] is False
    IdentityRepository(engine).set_membership(user, bundle.document.workspace_id, "viewer", False)
    checked(client.get(f"/api/v1/workspaces/{bundle.document.workspace_id}/evidence"), 404)
    assert client.get("/api/v1/auth/session").json()["memberships"] == []
    assert callback(client, start(client, pending)).headers["location"] == "/login?error=invalid"


def test_storage_failure_is_fixed_and_logout_does_not_clear_session(engine, signing, monkeypatch):
    client, repo, _, _, _, pending, _ = setup(engine, signing)

    def fail(*args):
        raise StorageError("PRIVATE")

    monkeypatch.setattr(repo, "begin_login", fail)
    response = client.post("/api/v1/auth/google/start", headers=HEADERS, follow_redirects=False)
    assert response.headers["location"] == "/login?error=unavailable"
    client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
    monkeypatch.setattr(SessionRepository, "revoke_session", fail)
    response = client.post("/api/v1/auth/logout", headers=HEADERS)
    checked(response, 503)
    assert "set-cookie" not in response.headers and "PRIVATE" not in response.text


def test_unexpected_callback_failure_still_clears_flow_and_preserves_session(
    engine, signing, monkeypatch
):
    from issuedigest_api.auth import AuthService

    client, _, _, _, _, pending, _ = setup(engine, signing)
    previous = secrets.token_urlsafe(32)
    client.cookies.set(SESSION_COOKIE, previous)
    state = start(client, pending)

    async def broken(*args):
        raise RuntimeError("PRIVATE")

    monkeypatch.setattr(AuthService, "complete", broken)
    response = callback(client, state)
    checked(response, 303)
    assert response.headers["location"] == "/login?error=unavailable"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert client.cookies.get(SESSION_COOKIE) == previous


def test_disabled_invitation_cannot_bind(engine, signing):
    client, repo, _, _, _, pending, _ = setup(engine, signing)
    repo.set_invite_enabled("https://accounts.google.com", "invited@gmail.com", False)
    assert callback(client, start(client, pending)).headers["location"] == "/login?error=invalid"
    assert client.cookies.get(SESSION_COOKIE) is None
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_users")) == 0


@pytest.mark.parametrize("mutation", ["absolute", "idle", "disabled", "revoked"])
def test_session_current_authority_rechecked(engine, signing, mutation):
    client, _, _, _, user, pending, _ = setup(engine, signing)
    assert callback(client, start(client, pending)).headers["location"] == "/"
    with engine.begin() as conn:
        if mutation == "absolute":
            conn.execute(text("UPDATE auth_sessions SET expires_at=clock_timestamp()"))
        elif mutation == "idle":
            conn.execute(
                text(
                    "UPDATE auth_sessions SET issued_at=issued_at-interval '31 minutes', "
                    "expires_at=expires_at-interval '31 minutes', "
                    "last_activity_at=last_activity_at-interval '31 minutes'"
                )
            )
        elif mutation == "revoked":
            conn.execute(text("UPDATE auth_sessions SET revoked=true"))
    if mutation == "disabled":
        IdentityRepository(engine).set_enabled(user, False)
    checked(client.get("/api/v1/auth/session"), 401)


def test_invalid_logout_cookie_is_idempotent_and_cleared(engine, signing):
    client, _, _, _, _, _, _ = setup(engine, signing)
    for token in [None, "PRIVATE"]:
        client.cookies.clear()
        if token:
            client.cookies.set(SESSION_COOKIE, token)
        response = client.post("/api/v1/auth/logout", headers=HEADERS)
        checked(response, 204)
        assert "Max-Age=0" in response.headers["set-cookie"]


def test_session_and_catalog_storage_failure_never_reflects(engine, signing, monkeypatch):
    client, _, bundle, _, _, pending, _ = setup(engine, signing)
    assert callback(client, start(client, pending)).headers["location"] == "/"

    def failure(*args):
        raise StorageError("PRIVATE")

    monkeypatch.setattr(WorkspaceAccessRepository, "get_session", failure)
    monkeypatch.setattr(WorkspaceAccessRepository, "list_evidence", failure)
    for path in [
        "/api/v1/auth/session",
        f"/api/v1/workspaces/{bundle.document.workspace_id}/evidence",
    ]:
        response = client.get(path)
        checked(response, 503)
        assert "PRIVATE" not in response.text


def test_auth_trailing_slash_never_reflects_callback_secrets():
    client = TestClient(create_app())
    response = client.get(
        "/api/v1/auth/google/callback/?state=PRIVATE&code=PRIVATE", follow_redirects=False
    )
    checked(response, 404)
    assert "location" not in response.headers
    assert "PRIVATE" not in response.text


def test_auth_root_also_has_protected_error_headers():
    checked(TestClient(create_app()).get("/api/v1/auth?secret=PRIVATE"), 404)
