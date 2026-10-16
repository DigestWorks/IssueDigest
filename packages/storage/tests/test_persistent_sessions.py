"""Long-lived session security boundaries on the disposable real PostgreSQL DB."""

from datetime import timedelta
from hashlib import sha256
from uuid import uuid4

import pytest
from alembic import command
from issuedigest_domain import EvidenceBundle, EvidenceSearchQuery
from issuedigest_storage import (
    AuthenticationDenied,
    EvidenceRepository,
    IdentityRepository,
    OAuthRepository,
    SessionRepository,
    WorkspaceAccessRepository,
)
from issuedigest_storage.access import EvidenceAccessRepository
from issuedigest_storage.research import ResearchRepository
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from conftest import bundle_data, migration_config


@pytest.fixture
def authorized(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(user, "synthetic", str(user))
    identities.set_membership(user, bundle.document.workspace_id, "owner")
    issued = SessionRepository(engine).issue_session(user)
    return bundle, snapshot, user, issued


@pytest.mark.parametrize("seconds", [None, 1209600])
def test_server_issues_exactly_fourteen_days_by_default_and_at_limit(engine, authorized, seconds):
    _, _, user, _ = authorized
    sessions = SessionRepository(engine)
    issued = (
        sessions.issue_session(user) if seconds is None else sessions.issue_session(user, seconds)
    )
    with engine.connect() as conn:
        duration = conn.scalar(
            text(
                "SELECT extract(epoch FROM expires_at-issued_at) FROM auth_sessions "
                "WHERE token_sha256=:h"
            ),
            {"h": sha256(issued.token.encode()).hexdigest()},
        )
    assert duration == 1209600
    with pytest.raises(ValueError):
        sessions.issue_session(user, 1209601)


def read_path(engine, authorized, path):
    bundle, snapshot, _, issued = authorized
    workspace = bundle.document.workspace_id
    access = WorkspaceAccessRepository(engine)
    if path == "evidence":
        return EvidenceAccessRepository(engine).load_evidence(issued.token, workspace, snapshot)
    if path == "session":
        return access.get_session(issued.token)
    if path == "catalog":
        return access.list_evidence(issued.token, workspace)
    if path == "search":
        return access.search_evidence(issued.token, workspace, EvidenceSearchQuery(terms=("앞",)))
    research = ResearchRepository(engine)
    if path == "sources":
        return research.list_sources(issued.token, workspace)
    return research.list_runs(issued.token, workspace)


PATHS = ["evidence", "session", "catalog", "search", "sources", "runs"]


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("idle_seconds,allowed", [(604799, True), (604800, False)])
def test_all_reads_enforce_seven_day_idle_boundary_without_extending_expiry(
    engine, authorized, path, idle_seconds, allowed
):
    # One second inside the boundary tolerates normal local query latency.
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=transaction_timestamp()-interval '8 days', "
                "expires_at=transaction_timestamp()+interval '6 days', "
                "last_activity_at=clock_timestamp()-:idle * interval '1 second'"
            ),
            {"idle": idle_seconds},
        )
        before = conn.execute(text("SELECT expires_at,last_activity_at FROM auth_sessions")).one()
    if allowed:
        assert read_path(engine, authorized, path) is not None
    else:
        with pytest.raises(AuthenticationDenied):
            read_path(engine, authorized, path)
    with engine.connect() as conn:
        after = conn.execute(text("SELECT expires_at,last_activity_at FROM auth_sessions")).one()
    assert after.expires_at == before.expires_at
    assert (after.last_activity_at > before.last_activity_at) is allowed


@pytest.mark.parametrize("path", PATHS)
@pytest.mark.parametrize("mutation", ["absolute", "revoked", "disabled", "membership"])
def test_long_sessions_recheck_current_authority(engine, authorized, path, mutation):
    bundle, _, user, issued = authorized
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=transaction_timestamp()-interval '8 days', "
                "expires_at=transaction_timestamp()+interval '6 days', "
                "last_activity_at=clock_timestamp()-interval '1 day'"
            )
        )
    identities = IdentityRepository(engine)
    if mutation == "revoked":
        SessionRepository(engine).revoke_session(issued.token)
    elif mutation == "disabled":
        identities.set_enabled(user, False)
    elif mutation == "membership":
        identities.set_membership(user, bundle.document.workspace_id, "owner", False)
    else:
        with engine.begin() as conn:
            conn.execute(text("UPDATE auth_sessions SET expires_at=clock_timestamp()"))
    if mutation == "membership":
        result = read_path(engine, authorized, path)
        assert result.memberships == () if path == "session" else result is None
    elif mutation == "disabled" and path in {"sources", "runs"}:
        assert read_path(engine, authorized, path) is None
    else:
        with pytest.raises(AuthenticationDenied):
            read_path(engine, authorized, path)


def test_oauth_issues_fourteen_day_session_and_atomically_replaces_previous(engine):
    oauth = OAuthRepository(engine)
    user, workspace = uuid4(), uuid4()
    oauth.register_invite("synthetic", "member@example.test", user, workspace, "owner")
    oauth.resolve_invited_identity("synthetic", "subject", "member@example.test", True)
    old = oauth.issue_authorized_session("synthetic", "subject")
    new = oauth.issue_authorized_session("synthetic", "subject", old.token)
    with engine.connect() as conn:
        durations = (
            conn.execute(text("SELECT extract(epoch FROM expires_at-issued_at) FROM auth_sessions"))
            .scalars()
            .all()
        )
    assert durations == [1209600, 1209600]
    with pytest.raises(AuthenticationDenied):
        WorkspaceAccessRepository(engine).get_session(old.token)
    assert WorkspaceAccessRepository(engine).get_session(new.token).user_id == user


def test_migration_preserves_old_expiry_enforces_cap_and_safely_downgrades(
    engine, database_url, authorized
):
    config = migration_config(database_url)
    _, _, user, old = authorized
    with engine.begin() as conn:
        conn.execute(text("UPDATE auth_sessions SET expires_at=issued_at+interval '8 hours'"))
        old_expiry = conn.scalar(text("SELECT expires_at FROM auth_sessions"))
    command.downgrade(config, "0005_research_journey")
    try:
        command.upgrade(config, "head")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT expires_at FROM auth_sessions")) == old_expiry
        long_session = SessionRepository(engine).issue_session(user, 1209600)
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text("UPDATE auth_sessions SET expires_at=issued_at+interval '1209601 seconds'")
            )
        command.downgrade(config, "0005_research_journey")
        with engine.connect() as conn:
            assert (
                conn.scalar(
                    text("SELECT expires_at FROM auth_sessions WHERE token_sha256=:h"),
                    {"h": sha256(old.token.encode()).hexdigest()},
                )
                == old_expiry
            )
            row = conn.execute(
                text(
                    "SELECT revoked,expires_at,issued_at FROM auth_sessions WHERE token_sha256=:h"
                ),
                {"h": sha256(long_session.token.encode()).hexdigest()},
            ).one_or_none()
            assert row is None or (
                row.revoked and row.expires_at <= row.issued_at + timedelta(hours=8)
            )
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(
                text("UPDATE auth_sessions SET expires_at=issued_at+interval '28801 seconds'")
            )
    finally:
        command.upgrade(config, "head")
