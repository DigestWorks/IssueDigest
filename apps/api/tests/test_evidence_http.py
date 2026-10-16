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
                    "UPDATE auth_sessions SET issued_at=issued_at-interval '7 "
                    "days',expires_at=expires_at-interval '7 "
                    "days',last_activity_at=clock_timestamp()-interval '604800 seconds'"
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


def test_overlapping_same_cookie_http_reads_both_succeed(engine):
    from conftest import overlapping_session_reads

    client, bundle, snapshot, *_, issued = setup_http(engine)
    second_client = TestClient(create_app(EvidenceAccessRepository(engine)))
    second_client.cookies.set(SESSION_COOKIE, issued.token)

    def load(client):
        return client.get(path(bundle.document.workspace_id, snapshot))

    # TestClient executes the sync handler on its own thread. Coordinate by actual
    # PostgreSQL session locks rather than Python worker identity for HTTP calls.
    results, conflicts = overlapping_session_reads(
        engine, lambda: load(client), lambda: load(second_client)
    )
    assert conflicts == 1
    assert [status for status, _ in results] == ["ok", "ok"]
    for _, response in results:
        checked(response, 200)
        assert response.json() == bundle.model_dump(mode="json")


@pytest.mark.parametrize("status", ["401", "404", "422", "503"])
def test_protected_error_responses_document_actual_json_detail_bodies(status):
    schema = TestClient(create_app()).get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}"]["get"]
    assert "application/json" in operation["responses"][status].get("content", {})
    names = {
        "401": "EvidenceAuthenticationError",
        "404": "EvidenceNotFoundError",
        "422": "EvidencePathValidationError",
        "503": "EvidenceUnavailableError",
    }
    assert operation["responses"][status]["content"]["application/json"]["schema"] == {
        "$ref": f"#/components/schemas/{names[status]}"
    }
    model = schema["components"]["schemas"][names[status]]
    assert model["required"] == ["detail"]
    assert model["additionalProperties"] is False
    if status != "422":
        expected = {
            "401": "Authentication required",
            "404": "Evidence not found",
            "503": "Evidence service unavailable",
        }
        assert model["properties"]["detail"]["const"] == expected[status]
    else:
        assert model["properties"]["detail"]["minItems"] == 1
        validation = schema["components"]["schemas"]["EvidencePathValidationDetail"]
        assert set(validation["required"]) == {"type", "loc", "msg"}
        assert set(validation["properties"]) == {"type", "loc", "msg"}


@pytest.mark.parametrize("sqlstate, attempts_expected", [("40001", 3), ("23514", 1)])
def test_exhausted_or_nonretryable_database_failures_keep_fixed_private_http_error(
    engine, caplog, sqlstate, attempts_expected
):
    from sqlalchemy import event

    client, bundle, snapshot, *_, issued = setup_http(engine)
    attempts = []

    def force_database_failure(conn, cursor, statement, parameters, context, executemany):
        if "SELECT auth_sessions.token_sha256" in statement and "FOR UPDATE" in statement:
            attempts.append(True)
            cursor.execute(
                "DO $$ BEGIN RAISE EXCEPTION 'synthetic private retry failure' "
                f"USING ERRCODE='{sqlstate}'; END $$"
            )

    event.listen(engine, "before_cursor_execute", force_database_failure)
    try:
        with caplog.at_level(logging.WARNING):
            response = client.get(path(bundle.document.workspace_id, snapshot))
        checked(response, 503)
        assert response.json() == {"detail": "Evidence service unavailable"}
        assert len(attempts) == attempts_expected
        private_content_hidden = all(
            item not in response.text and item not in caplog.text
            for item in [
                issued.token,
                bundle.representation.text,
                "synthetic private retry failure",
            ]
        )
        assert private_content_hidden
    finally:
        event.remove(engine, "before_cursor_execute", force_database_failure)


@pytest.mark.parametrize("days,want_max", [(14, 1209600), (30, 1209600), (-1, 0)])
def test_persistent_cookie_is_secure_and_bounded_to_fourteen_days(days, want_max):
    from email.utils import parsedate_to_datetime
    from http.cookies import SimpleCookie

    issued = IssuedSession(secrets.token_urlsafe(32), datetime.now(UTC) + timedelta(days=days))
    response = Response()
    set_session_cookie(response, issued)
    cookie = SimpleCookie(response.headers["set-cookie"])[SESSION_COOKIE]
    assert max(0, want_max - 1) <= int(cookie["max-age"]) <= want_max
    assert cookie["secure"] and cookie["httponly"] and cookie["samesite"] == "lax"
    assert cookie["path"] == "/" and cookie["domain"] == ""
    expires = parsedate_to_datetime(cookie["expires"])
    assert expires <= issued.expires_at
    assert expires <= datetime.now(UTC) + timedelta(days=14)
    if days <= 14:
        assert expires == issued.expires_at.replace(microsecond=0)
    else:
        assert expires >= datetime.now(UTC) + timedelta(days=14, seconds=-1)
