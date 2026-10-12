"""Real PostgreSQL-backed protected evidence HTTP contract."""

import logging
import secrets
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from uuid import UUID, uuid4

import pytest
from fastapi import Response
from fastapi.testclient import TestClient
from issuedigest_api.cookies import SESSION_COOKIE, clear_session_cookie, set_session_cookie
from issuedigest_api.main import create_app
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import (
    EvidenceAccessRepository,
    EvidenceRepository,
    IdentityRepository,
    SessionRepository,
)
from issuedigest_storage.sessions import IssuedSession
from sqlalchemy import text

from conftest import bundle_data


def path(workspace=None, snapshot=None):
    return f"/api/v1/workspaces/{workspace or uuid4()}/evidence/{snapshot or uuid4()}"


def checked(response, status):
    assert response.status_code == status
    assert response.headers["Cache-Control"] == "no-store"
    assert UUID(response.headers["X-Request-ID"]).version == 4
    if status != 200:
        assert set(response.json()) == {"detail"}


@pytest.mark.parametrize(
    "channel", ["missing", "bearer", "header", "query", "malformed", "noncanonical"]
)
def test_missing_or_invalid_cookie_is_denied_before_backend(channel):
    client = TestClient(create_app())
    token = secrets.token_urlsafe(32)
    headers, params = {}, {}
    if channel == "bearer":
        headers["Authorization"] = "Bearer " + token
    elif channel == "header":
        headers["X-Session-Token"] = token
    elif channel == "query":
        params["session"] = token
    elif channel == "malformed":
        client.cookies.set(SESSION_COOKIE, "bad")
    elif channel == "noncanonical":
        client.cookies.set(SESSION_COOKIE, "A" * 42 + "B")
    checked(client.get(path(), headers=headers, params=params), 401)


def test_unconfigured_backend_with_valid_cookie_fails_closed():
    client = TestClient(create_app())
    client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
    checked(client.get(path()), 503)
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/api/v1/status").status_code == 200


def setup_http(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    registry = IdentityRepository(engine)
    registry.register_identity(user, "synthetic", str(user))
    registry.set_membership(user, bundle.document.workspace_id, "viewer")
    sessions = SessionRepository(engine)
    issued = sessions.issue_session(user)
    client = TestClient(create_app(EvidenceAccessRepository(engine)))
    client.cookies.set(SESSION_COOKIE, issued.token)
    return client, bundle, snapshot, user, registry, sessions, issued


def test_authorized_http_preserves_exact_bundle_and_citation_order(engine):
    client, bundle, snapshot, *_ = setup_http(engine)
    response = client.get(
        path(bundle.document.workspace_id, snapshot),
        headers={
            "X-Request-ID": "client-id",
            "user_id": str(uuid4()),
            "workspace_id": str(uuid4()),
        },
    )
    checked(response, 200)
    assert response.json() == bundle.model_dump(mode="json")
    assert [c["selector"]["kind"] for c in response.json()["citations"]] == [
        "table_cell",
        "pdf",
        "text",
    ]
    assert response.headers["X-Request-ID"] != "client-id"


@pytest.mark.parametrize(
    "state",
    [
        "unknown",
        "expired",
        "idle",
        "revoked",
        "disabled",
        "no_membership",
        "other_workspace",
        "missing",
    ],
)
def test_actual_database_http_authentication_and_authorization_matrix(engine, state):
    client, bundle, snapshot, user, registry, sessions, issued = setup_http(engine)
    workspace = bundle.document.workspace_id
    expected = 401
    if state == "unknown":
        client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
    elif state == "expired":
        with engine.begin() as conn:
            conn.execute(text("UPDATE auth_sessions SET expires_at=clock_timestamp()"))
    elif state == "idle":
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE auth_sessions SET issued_at=issued_at-interval '30 "
                    "minutes',expires_at=expires_at-interval '30 "
                    "minutes',last_activity_at=clock_timestamp()-interval '1800 seconds'"
                )
            )
    elif state == "revoked":
        sessions.revoke_session(issued.token)
    elif state == "disabled":
        registry.set_enabled(user, False)
    elif state == "no_membership":
        registry.set_membership(user, workspace, "viewer", False)
        expected = 404
    elif state == "other_workspace":
        workspace = uuid4()
        registry.set_membership(user, workspace, "owner")
        expected = 404
    else:
        snapshot = uuid4()
        expected = 404
    response = client.get(path(workspace, snapshot))
    checked(response, expected)
    assert response.json() == {
        "detail": "Authentication required" if expected == 401 else "Evidence not found"
    }
    assert bundle.representation.text not in response.text
    assert issued.token not in response.text


@pytest.mark.parametrize("failure", ["db", "corruption"])
def test_storage_failures_are_sanitized_and_not_logged(engine, failure, caplog):
    client, bundle, snapshot, *_, issued = setup_http(engine)
    with engine.begin() as conn:
        if failure == "db":
            conn.execute(text("ALTER TABLE auth_sessions RENAME TO synthetic_unavailable_sessions"))
        else:
            conn.execute(text("UPDATE evidence_snapshots SET content_sha256=:h"), {"h": "f" * 64})
    try:
        with caplog.at_level(logging.WARNING):
            response = client.get(path(bundle.document.workspace_id, snapshot))
        checked(response, 503)
        assert response.json() == {"detail": "Evidence service unavailable"}
        for sensitive in [
            issued.token,
            bundle.representation.text,
            "synthetic_unavailable_sessions",
            "SELECT",
            "postgresql",
        ]:
            assert sensitive not in response.text
            assert sensitive not in caplog.text
    finally:
        if failure == "db":
            with engine.begin() as conn:
                conn.execute(
                    text("ALTER TABLE synthetic_unavailable_sessions RENAME TO auth_sessions")
                )


def test_uuid4_paths_keep_validation_errors_and_protected_headers():
    client = TestClient(create_app())
    client.cookies.set(SESSION_COOKIE, secrets.token_urlsafe(32))
    for url in [path("invalid"), path("00000000-0000-1000-8000-000000000000")]:
        checked(client.get(url), 422)


def test_cookie_helpers_secure_host_scoped_and_expiry_bounded():
    response = Response()
    issued = IssuedSession(secrets.token_urlsafe(32), datetime.now(UTC) + timedelta(seconds=60))
    set_session_cookie(response, issued)
    parsed = SimpleCookie(response.headers["set-cookie"])[SESSION_COOKIE]
    assert parsed.value == issued.token
    assert parsed["secure"] and parsed["httponly"]
    assert parsed["samesite"] == "lax"
    assert parsed["path"] == "/" and parsed["domain"] == ""
    assert 0 <= int(parsed["max-age"]) <= 60
    from email.utils import parsedate_to_datetime

    assert parsedate_to_datetime(parsed["expires"]) <= issued.expires_at
    cleared = Response()
    clear_session_cookie(cleared)
    deleted = SimpleCookie(cleared.headers["set-cookie"])[SESSION_COOKIE]
    assert deleted["max-age"] == "0"
    assert deleted["secure"] and deleted["httponly"]
    assert deleted["samesite"] == "lax" and deleted["path"] == "/" and deleted["domain"] == ""


def test_openapi_documents_only_cookie_security_and_canonical_response():
    schema = TestClient(create_app()).get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/EvidenceBundle"
    }
    security_name = next(iter(operation["security"][0]))
    assert schema["components"]["securitySchemes"][security_name] == {
        "type": "apiKey",
        "in": "cookie",
        "name": SESSION_COOKIE,
    }
    assert len(operation["security"]) == 1
    for anonymous in ["/health/live", "/api/v1/status"]:
        assert "security" not in schema["paths"][anonymous]["get"]
    for status in ["200", "401", "404", "422", "503"]:
        assert (
            operation["responses"][status]["headers"]["Cache-Control"]["schema"]["const"]
            == "no-store"
        )
        assert (
            operation["responses"][status]["headers"]["X-Request-ID"]["schema"]["format"] == "uuid"
        )


def test_protected_validation_does_not_echo_untrusted_path_input():
    client = TestClient(create_app())
    response = client.get(path(secrets.token_urlsafe(32)))
    checked(response, 422)
    error = response.json()["detail"][0]
    assert error["loc"] == ["path", "workspace_id"]
    assert set(error) == {"type", "loc", "msg"}


def test_absent_and_malformed_cookies_do_not_open_configured_database(engine):
    from sqlalchemy import event

    backend = EvidenceAccessRepository(engine)
    client = TestClient(create_app(backend))
    checkouts = []

    def checkout(*args):
        checkouts.append(True)

    event.listen(engine, "checkout", checkout)
    try:
        checked(client.get(path()), 401)
        client.cookies.set(SESSION_COOKIE, "malformed")
        checked(client.get(path()), 401)
        assert checkouts == []
    finally:
        event.remove(engine, "checkout", checkout)
