"""Trusted OAuth state, explicit invitation and browsing persistence."""

import base64
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from uuid import uuid4

import issuedigest_storage as storage
import pytest
from issuedigest_domain import EvidenceBundle
from sqlalchemy import text

from conftest import bundle_data, migration_config


def oauth(engine):
    assert hasattr(storage, "OAuthRepository"), "missing trusted OAuth persistence"
    return storage.OAuthRepository(engine)


def workspace(engine):
    assert hasattr(storage, "WorkspaceAccessRepository"), "missing protected workspace browsing"
    return storage.WorkspaceAccessRepository(engine)


def invited(engine, subject="subject"):
    repo = oauth(engine)
    user, space = uuid4(), uuid4()
    assert repo.register_invite("issuer", "Member@Example.test", user, space, "viewer") is True
    assert repo.resolve_invited_identity("issuer", subject, "member@example.test", True) == user
    return repo, user, space


def test_login_state_pkce_one_use_browser_binding_and_secret_repr(engine):
    repo = oauth(engine)
    pending = repo.begin_login()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT * FROM auth_oauth_flows")).mappings().one()
    assert row["state_sha256"] == sha256(pending.state.encode()).hexdigest()
    assert row["cookie_sha256"] == sha256(pending.browser_token.encode()).hexdigest()
    assert (row["expires_at"] - row["issued_at"]).total_seconds() == 600
    for secret in [
        pending.state,
        pending.browser_token,
        pending.code_challenge,
        pending.oidc_nonce,
    ]:
        assert secret not in repr(pending)
    with pytest.raises(storage.AuthenticationDenied):
        repo.consume_login(pending.state, repo.begin_login().browser_token)
    consumed = repo.consume_login(pending.state, pending.browser_token)
    challenge = (
        base64.urlsafe_b64encode(sha256(consumed.code_verifier.encode()).digest())
        .decode()
        .rstrip("=")
    )
    assert pending.code_challenge == challenge
    assert consumed.oidc_nonce == pending.oidc_nonce
    assert consumed.code_verifier not in repr(consumed)
    assert consumed.oidc_nonce not in repr(consumed)
    with pytest.raises(storage.AuthenticationDenied):
        repo.consume_login(pending.state, pending.browser_token)


def test_concurrent_consume_is_single_use_and_expiry_is_cleaned(engine):
    repo = oauth(engine)
    pending = repo.begin_login()

    def consume(_):
        try:
            return repo.consume_login(pending.state, pending.browser_token)
        except storage.AuthenticationDenied:
            return None

    with ThreadPoolExecutor(max_workers=4) as workers:
        assert list(workers.map(consume, range(4))).count(None) == 3
    expired = repo.begin_login()
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_oauth_flows SET issued_at=issued_at-interval '11 minutes', "
                "expires_at=expires_at-interval '11 minutes'"
            )
        )
    with pytest.raises(storage.AuthenticationDenied):
        repo.consume_login(expired.state, expired.browser_token)
    repo.begin_login()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_oauth_flows")) == 1


def test_invite_explicit_binding_idempotency_email_change_and_no_reactivation(engine):
    repo, user, space = invited(engine)
    assert repo.register_invite("issuer", "member@example.test", user, space, "viewer") is False
    assert repo.resolve_invited_identity("issuer", "subject", "changed@example.test", False) == user
    with pytest.raises(storage.StorageConflict):
        repo.register_invite("issuer", "member@example.test", user, uuid4(), "viewer")
    with pytest.raises(storage.AuthenticationDenied):
        repo.resolve_invited_identity("issuer", "other", "member@example.test", True)
    repo.set_invite_enabled("issuer", "member@example.test", False)
    assert repo.resolve_invited_identity("issuer", "subject", None, False) == user
    storage.IdentityRepository(engine).set_enabled(user, False)
    with pytest.raises(storage.AuthenticationDenied):
        repo.resolve_invited_identity("issuer", "subject", "member@example.test", True)


@pytest.mark.parametrize(
    "email,flag",
    [
        (None, True),
        ("unknown@example.test", True),
        ("member@example.test", False),
        ("member@example.test", 1),
    ],
)
def test_unapproved_identity_is_denied_without_new_users(engine, email, flag):
    repo = oauth(engine)
    repo.register_invite("issuer", "member@example.test", uuid4(), uuid4(), "owner")
    with pytest.raises(storage.AuthenticationDenied):
        repo.resolve_invited_identity("issuer", "subject", email, flag)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_users")) == 0


@pytest.mark.parametrize(
    "email", ["no-at", "a@@b", " a@b", "a b@c", "한@b", "a@b\x00", "a" * 320 + "@b"]
)
def test_invitation_email_validation(engine, email):
    with pytest.raises(ValueError):
        oauth(engine).register_invite("issuer", email, uuid4(), uuid4(), "viewer")


@pytest.mark.parametrize("same", [True, False])
def test_concurrent_first_identity_binding_converges_or_denies_reuse(engine, same):
    repo = oauth(engine)
    user, space = uuid4(), uuid4()
    repo.register_invite("issuer", "member@example.test", user, space, "editor")

    def resolve(sub):
        try:
            return repo.resolve_invited_identity("issuer", sub, "member@example.test", True)
        except storage.AuthenticationDenied:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        result = list(workers.map(resolve, ["one", "one" if same else "two"]))
    assert result == [user, user] if same else result.count(None) == 1
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_users")) == 1
        assert conn.scalar(text("SELECT count(*) FROM auth_workspace_memberships")) == 1


def test_session_rotation_requires_enabled_identity_active_membership_and_rolls_back(engine):
    repo, user, space = invited(engine)
    old = repo.issue_authorized_session("issuer", "subject")
    storage.IdentityRepository(engine).set_membership(user, space, "viewer", False)
    with pytest.raises(storage.AuthenticationDenied):
        repo.issue_authorized_session("issuer", "subject", old.token)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT revoked FROM auth_sessions")) is False
        assert conn.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
    storage.IdentityRepository(engine).set_membership(user, space, "editor")
    new = repo.issue_authorized_session("issuer", "subject", old.token)
    assert new.token != old.token
    with pytest.raises(storage.AuthenticationDenied):
        workspace(engine).get_session(old.token)
    assert workspace(engine).get_session(new.token).user_id == user


def test_workspace_session_and_catalog_sorting_has_more_unicode_and_isolation(engine):
    repo, user, space = invited(engine)
    token = repo.issue_authorized_session("issuer", "subject").token
    access = workspace(engine)
    assert access.get_session(token).memberships[0].workspace_id == space
    assert access.list_evidence(token, uuid4()) is None
    assert access.list_evidence(token, space).items == ()
    snapshots = sorted([uuid4() for _ in range(4)], key=str)
    for snap in snapshots:
        data = bundle_data()
        data["document"]["workspace_id"] = str(space)
        bundle = EvidenceBundle.model_validate(data)
        storage.EvidenceRepository(engine).save(snap, bundle)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE evidence_snapshots SET created_at=:created_at WHERE snapshot_id=:snapshot"
            ),
            [
                {"snapshot": snapshots[0], "created_at": "2026-10-10T00:00:00Z"},
                {"snapshot": snapshots[1], "created_at": "2026-10-11T00:00:00Z"},
                {"snapshot": snapshots[2], "created_at": "2026-10-11T00:00:00Z"},
                {"snapshot": snapshots[3], "created_at": "2026-10-12T00:00:00Z"},
            ],
        )
    result = access.list_evidence(token, space, 2)
    assert [item.snapshot_id for item in result.items] == [snapshots[3], snapshots[1]]
    assert result.has_more is True
    assert result.items[0].excerpt == bundle.representation.text
    assert result.items[0].citation_count == 3
    complete = access.list_evidence(token, space, 4)
    assert [item.snapshot_id for item in complete.items] == [
        snapshots[3],
        snapshots[1],
        snapshots[2],
        snapshots[0],
    ]
    assert complete.has_more is False
    with engine.begin() as conn:
        conn.execute(text("UPDATE evidence_snapshots SET content_sha256=:h"), {"h": "b" * 64})
    with pytest.raises(storage.StorageError):
        access.list_evidence(token, space)


@pytest.mark.parametrize("limit", [0, 51, True, "20", 1.2])
def test_catalog_limit_strict_validation(engine, limit):
    with pytest.raises(ValueError):
        workspace(engine).list_evidence("invalid", uuid4(), limit)


def test_oauth_migration_preserves_existing_identity_evidence_and_sessions(engine, database_url):
    from alembic import command

    repo = oauth(engine)
    user = uuid4()
    storage.IdentityRepository(engine).register_identity(user, "existing", "subject")
    # This fixture represents a session created under the historical 8-hour policy.
    issued = storage.SessionRepository(engine).issue_session(user, 28800)
    data = EvidenceBundle.model_validate(bundle_data())
    snap = uuid4()
    storage.EvidenceRepository(engine).save(snap, data)
    config = migration_config(database_url)
    try:
        command.downgrade(config, "0002_auth_sessions")
        with engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
            assert conn.scalar(text("SELECT to_regclass('auth_oauth_flows')")) is None
        command.upgrade(config, "head")
        assert workspace(engine).get_session(issued.token).user_id == user
        assert storage.EvidenceRepository(engine).load(data.document.workspace_id, snap) == data
        assert repo.begin_login().state
    finally:
        command.upgrade(config, "head")


def test_concurrent_flow_cap_is_exact_and_cleanup_restores_capacity(engine):
    repo = oauth(engine)
    for _ in range(198):
        repo.begin_login()

    def start(_):
        try:
            repo.begin_login()
            return True
        except storage.StorageError as error:
            assert str(error) == "Unable to start login"
            return False

    with ThreadPoolExecutor(max_workers=8) as workers:
        assert list(workers.map(start, range(8))).count(True) == 2
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_oauth_flows")) == 200
        conn.execute(
            text(
                "UPDATE auth_oauth_flows SET issued_at=issued_at-interval '11 minutes', "
                "expires_at=expires_at-interval '11 minutes'"
            )
        )
    assert repo.begin_login().state
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_oauth_flows")) == 1


@pytest.mark.parametrize("method", ["get_session", "list_evidence"])
@pytest.mark.parametrize("mutation", ["expired", "idle", "revoked", "disabled"])
def test_workspace_rechecks_session_authority(engine, method, mutation):
    repo, user, space = invited(engine)
    issued = repo.issue_authorized_session("issuer", "subject")
    if mutation == "disabled":
        storage.IdentityRepository(engine).set_enabled(user, False)
    elif mutation == "revoked":
        storage.SessionRepository(engine).revoke_session(issued.token)
    else:
        with engine.begin() as conn:
            if mutation == "expired":
                conn.execute(text("UPDATE auth_sessions SET expires_at=clock_timestamp()"))
            else:
                conn.execute(
                    text(
                        "UPDATE auth_sessions SET issued_at=issued_at-interval '8 days', "
                        "expires_at=expires_at-interval '8 days', "
                        "last_activity_at=clock_timestamp()-interval '7 days'"
                    )
                )
    with pytest.raises(storage.AuthenticationDenied):
        call = getattr(workspace(engine), method)
        call(issued.token, space) if method == "list_evidence" else call(issued.token)


def test_memberships_sorted_bounded_empty_and_activity_is_only_refreshed_on_success(engine):
    repo, user, space = invited(engine)
    issued = repo.issue_authorized_session("issuer", "subject")
    registry = storage.IdentityRepository(engine)
    spaces = [space] + [uuid4() for _ in range(99)]
    for item in spaces[1:]:
        registry.set_membership(user, item, "editor")
    access = workspace(engine)
    assert [x.workspace_id for x in access.get_session(issued.token).memberships] == sorted(
        spaces, key=str
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=issued_at-interval '10 minutes', "
                "expires_at=expires_at-interval '10 minutes', "
                "last_activity_at=clock_timestamp()-interval '10 minutes'"
            )
        )
        before = conn.scalar(text("SELECT last_activity_at FROM auth_sessions"))
    assert access.list_evidence(issued.token, uuid4()) is None
    registry.set_membership(user, uuid4(), "owner")
    with pytest.raises(storage.StorageError) as caught:
        access.get_session(issued.token)
    assert str(caught.value) == "Unable to load protected workspace"
    with engine.begin() as conn:
        assert conn.scalar(text("SELECT last_activity_at FROM auth_sessions")) == before
        conn.execute(text("UPDATE auth_workspace_memberships SET active=false"))
    assert access.get_session(issued.token).memberships == ()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT last_activity_at FROM auth_sessions")) > before


def test_disabled_unbound_invite_never_creates_user_and_reinvite_does_not_enable(engine):
    repo = oauth(engine)
    user, space = uuid4(), uuid4()
    repo.register_invite("issuer", "member@example.test", user, space, "viewer")
    repo.set_invite_enabled("issuer", "member@example.test", False)
    assert repo.register_invite("issuer", "member@example.test", user, space, "viewer") is False
    with pytest.raises(storage.AuthenticationDenied):
        repo.resolve_invited_identity("issuer", "subject", "member@example.test", True)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_users")) == 0
    with pytest.raises(storage.StorageError):
        repo.set_invite_enabled("issuer", "missing@example.test", True)


def test_distinct_email_dot_and_plus_aliases_are_never_merged(engine):
    repo = oauth(engine)
    users = [uuid4(), uuid4(), uuid4()]
    emails = ["member@example.test", "mem.ber@example.test", "member+tag@example.test"]
    for index, (user, email) in enumerate(zip(users, emails, strict=True)):
        repo.register_invite("issuer", email, user, uuid4(), "viewer")
        assert repo.resolve_invited_identity("issuer", str(index), email, True) == user


def test_reserved_user_conflict_rolls_back_membership_and_binding(engine):
    repo = oauth(engine)
    user, space = uuid4(), uuid4()
    repo.register_invite("issuer", "member@example.test", user, space, "viewer")
    storage.IdentityRepository(engine).register_identity(user, "different", "subject")
    with pytest.raises(storage.StorageConflict):
        repo.resolve_invited_identity("issuer", "subject", "member@example.test", True)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT bound_subject FROM auth_identity_invites")) is None
        assert conn.scalar(text("SELECT count(*) FROM auth_workspace_memberships")) == 0


def test_session_insert_database_failure_rolls_back_rotation_and_masks_secrets(engine):
    from sqlalchemy import event

    repo, user, space = invited(engine)
    old = repo.issue_authorized_session("issuer", "subject")

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO auth_sessions"):
            cursor.execute("DO $$ BEGIN RAISE EXCEPTION 'synthetic private failure'; END $$")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(storage.StorageError) as caught:
            repo.issue_authorized_session("issuer", "subject", old.token)
        assert str(caught.value) == "Unable to issue authorized session"
        assert old.token not in str(caught.value)
        assert caught.value.__cause__ is None
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
        assert conn.scalar(text("SELECT revoked FROM auth_sessions")) is False


def test_flow_and_invitation_database_constraints(engine):
    from sqlalchemy.exc import IntegrityError

    repo = oauth(engine)
    repo.begin_login()
    repo.register_invite("issuer", "member@example.test", uuid4(), uuid4(), "owner")
    invalid_updates = [
        "UPDATE auth_oauth_flows SET state_sha256='private'",
        "UPDATE auth_oauth_flows SET cookie_sha256='private'",
        "UPDATE auth_oauth_flows SET code_verifier=repeat('!',43)",
        "UPDATE auth_oauth_flows SET oidc_nonce=repeat('!',43)",
        "UPDATE auth_oauth_flows SET expires_at=issued_at",
        "UPDATE auth_oauth_flows SET expires_at=issued_at+interval '601 seconds'",
        "UPDATE auth_identity_invites SET issuer='  '",
        "UPDATE auth_identity_invites SET email='UPPER@example.test'",
        "UPDATE auth_identity_invites SET email='bad email@example.test'",
        "UPDATE auth_identity_invites SET email='a@@b'",
        "UPDATE auth_identity_invites SET role='admin'",
        "UPDATE auth_identity_invites SET bound_subject='  '",
        "UPDATE auth_identity_invites SET workspace_id='00000000-0000-1000-8000-000000000000'",
        "UPDATE auth_identity_invites SET user_id='00000000-0000-1000-8000-000000000000'",
    ]
    for sql in invalid_updates:
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(text(sql))


def test_invalid_canonical_nonce_is_fail_closed(engine):
    repo = oauth(engine)
    pending = repo.begin_login()
    # The SQL URL-safe length constraint permits noncanonical base64 pad bits.
    with engine.begin() as conn:
        conn.execute(text("UPDATE auth_oauth_flows SET oidc_nonce=repeat('A',42)||'B'"))
    with pytest.raises(storage.StorageError) as caught:
        repo.consume_login(pending.state, pending.browser_token)
    assert str(caught.value) == "Unable to consume login"


def test_state_database_error_never_exposes_raw_secrets(engine):
    from sqlalchemy import event

    repo = oauth(engine)
    pending = repo.begin_login()

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("DELETE FROM auth_oauth_flows"):
            cursor.execute("DO $$ BEGIN RAISE EXCEPTION 'synthetic private failure'; END $$")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(storage.StorageError) as caught:
            repo.consume_login(pending.state, pending.browser_token)
        assert str(caught.value) == "Unable to consume login"
        assert pending.state not in str(caught.value)
        assert caught.value.__cause__ is None
        with pytest.raises(storage.StorageError) as caught:
            repo.begin_login()
        assert str(caught.value) == "Unable to start login"
    finally:
        event.remove(engine, "before_cursor_execute", fail)


@pytest.mark.parametrize("method", ["get_session", "list_evidence"])
def test_workspace_overlapping_rr_refresh_retries_full_authority(engine, method):
    from conftest import overlapping_session_reads

    repo, user, space = invited(engine)
    issued = repo.issue_authorized_session("issuer", "subject")
    access = workspace(engine)

    def read():
        return (
            access.get_session(issued.token)
            if method == "get_session"
            else access.list_evidence(issued.token, space)
        )

    results, conflicts = overlapping_session_reads(engine, read, read)
    assert conflicts == 1
    assert [status for status, _ in results] == ["ok", "ok"]
    assert results[0][1] == results[1][1]


@pytest.mark.parametrize("change", ["revoked", "disabled", "membership"])
def test_workspace_overlap_rechecks_changed_authority_after_retry(engine, change):
    from conftest import overlapping_session_reads

    repo, user, space = invited(engine)
    issued = repo.issue_authorized_session("issuer", "subject")
    access = workspace(engine)

    def read():
        return access.list_evidence(issued.token, space)

    def mutate():
        if change == "revoked":
            storage.SessionRepository(engine).revoke_session(issued.token)
        elif change == "disabled":
            storage.IdentityRepository(engine).set_enabled(user, False)
        else:
            storage.IdentityRepository(engine).set_membership(user, space, "viewer", False)

    results, conflicts = overlapping_session_reads(engine, read, read, mutate)
    assert conflicts == 1
    assert results[0][0] == "ok"
    assert results[1] == (
        ("ok", None) if change == "membership" else ("AuthenticationDenied", None)
    )


def test_workspace_rr_retry_is_bounded_and_sanitized(engine):
    from sqlalchemy import event

    repo, user, space = invited(engine)
    issued = repo.issue_authorized_session("issuer", "subject")
    attempts = []

    def fail(conn, cursor, statement, parameters, context, executemany):
        if "SELECT auth_sessions.token_sha256" in statement and "FOR UPDATE" in statement:
            attempts.append(True)
            cursor.execute(
                "DO $$ BEGIN RAISE EXCEPTION 'private failure' USING ERRCODE='40001'; END $$"
            )

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(storage.StorageError) as caught:
            workspace(engine).get_session(issued.token)
        assert len(attempts) == 3
        assert str(caught.value) == "Unable to load protected workspace"
    finally:
        event.remove(engine, "before_cursor_execute", fail)


@pytest.mark.parametrize("column", ["user_id", "workspace_id"])
def test_invite_database_uuid4_requires_rfc_variant(engine, column):
    from sqlalchemy.exc import IntegrityError

    repo = oauth(engine)
    repo.register_invite("issuer", "member@example.test", uuid4(), uuid4(), "viewer")
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                f"UPDATE auth_identity_invites SET {column}='00000000-0000-4000-0000-000000000000'"
            )
        )


def test_rotation_waits_for_read_then_revokes_old_session_without_deadlock(engine):
    from conftest import overlapping_session_reads

    repo, user, space = invited(engine)
    old = repo.issue_authorized_session("issuer", "subject")
    access = workspace(engine)
    results, conflicts = overlapping_session_reads(
        engine,
        lambda: access.get_session(old.token),
        lambda: repo.issue_authorized_session("issuer", "subject", old.token),
    )
    assert conflicts == 0
    assert [status for status, _ in results] == ["ok", "ok"]
    assert results[0][1].user_id == user
    new = results[1][1]
    assert access.get_session(new.token).user_id == user
    with pytest.raises(storage.AuthenticationDenied):
        access.get_session(old.token)


def test_read_waits_for_rotation_then_retries_and_denies_old_session(engine):
    from conftest import overlapping_session_reads

    repo, user, space = invited(engine)
    old = repo.issue_authorized_session("issuer", "subject")
    access = workspace(engine)
    results, conflicts = overlapping_session_reads(
        engine,
        lambda: repo.issue_authorized_session("issuer", "subject", old.token),
        lambda: access.list_evidence(old.token, space),
    )
    assert conflicts == 1
    assert results[0][0] == "ok"
    assert results[1] == ("AuthenticationDenied", None)
    assert access.get_session(results[0][1].token).user_id == user


@pytest.mark.parametrize("authority", ["user", "membership"])
def test_rotation_waits_for_inflight_authority_revocation_and_preserves_old_cookie(
    engine, authority
):
    from threading import Event
    from time import monotonic

    from sqlalchemy import event

    repo, user, space = invited(engine)
    old = repo.issue_authorized_session("issuer", "subject")
    started = Event()
    blocker = engine.connect()
    transaction = blocker.begin()
    if authority == "user":
        blocker.execute(text("UPDATE auth_users SET enabled=false WHERE user_id=:u"), {"u": user})
    else:
        blocker.execute(
            text("UPDATE auth_workspace_memberships SET active=false WHERE user_id=:u"), {"u": user}
        )
    target = (
        "SELECT auth_users.user_id"
        if authority == "user"
        else "SELECT auth_workspace_memberships.user_id"
    )
    pids = {}

    def before(conn, cursor, statement, parameters, context, executemany):
        if target in statement and "FOR UPDATE" in statement:
            pids["worker"] = conn.connection.driver_connection.info.backend_pid
            started.set()

    event.listen(engine, "before_cursor_execute", before)

    def rotate():
        with pytest.raises(storage.AuthenticationDenied):
            repo.issue_authorized_session("issuer", "subject", old.token)

    try:
        with ThreadPoolExecutor(max_workers=1) as workers:
            future = workers.submit(rotate)
            try:
                assert started.wait(timeout=5)
                deadline = monotonic() + 5
                with engine.connect() as observer:
                    blocker_pid = blocker.connection.driver_connection.info.backend_pid
                    while blocker_pid not in observer.scalar(
                        text("SELECT pg_blocking_pids(:pid)"), {"pid": pids["worker"]}
                    ):
                        assert monotonic() < deadline
                        Event().wait(0.01)
                transaction.commit()
                future.result(timeout=5)
            finally:
                if transaction.is_active:
                    transaction.rollback()
    finally:
        event.remove(engine, "before_cursor_execute", before)
        blocker.close()
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_sessions")) == 1
        assert conn.scalar(text("SELECT revoked FROM auth_sessions")) is False


def test_session_cookie_rotation_can_switch_identity_without_moving_membership(engine):
    repo, first, space = invited(engine, "first")
    second, other = uuid4(), uuid4()
    repo.register_invite("issuer", "second@example.test", second, other, "editor")
    repo.resolve_invited_identity("issuer", "second", "second@example.test", True)
    old = repo.issue_authorized_session("issuer", "first")
    new = repo.issue_authorized_session("issuer", "second", old.token)
    info = workspace(engine).get_session(new.token)
    assert info.user_id == second
    assert [m.workspace_id for m in info.memberships] == [other]
    assert workspace(engine).list_evidence(new.token, space) is None
    with pytest.raises(storage.AuthenticationDenied):
        workspace(engine).get_session(old.token)


def test_first_binding_database_failure_rolls_back_user_membership_and_invite(engine):
    from sqlalchemy import event

    repo = oauth(engine)
    repo.register_invite("issuer", "member@example.test", uuid4(), uuid4(), "viewer")

    def fail(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("UPDATE auth_identity_invites"):
            cursor.execute("DO $$ BEGIN RAISE EXCEPTION 'synthetic private failure'; END $$")

    event.listen(engine, "before_cursor_execute", fail)
    try:
        with pytest.raises(storage.StorageError) as caught:
            repo.resolve_invited_identity("issuer", "subject", "member@example.test", True)
        assert str(caught.value) == "Unable to resolve invited identity"
    finally:
        event.remove(engine, "before_cursor_execute", fail)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_users")) == 0
        assert conn.scalar(text("SELECT count(*) FROM auth_workspace_memberships")) == 0
        assert conn.scalar(text("SELECT bound_subject FROM auth_identity_invites")) is None


def test_unregistered_or_disabled_identity_never_issues_session(engine):
    repo = oauth(engine)
    with pytest.raises(storage.AuthenticationDenied):
        repo.issue_authorized_session("issuer", "unregistered")
    repo, user, space = invited(engine)
    storage.IdentityRepository(engine).set_enabled(user, False)
    with pytest.raises(storage.AuthenticationDenied):
        repo.issue_authorized_session("issuer", "subject")
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_sessions")) == 0


def test_catalog_excerpt_is_160_codepoints_without_changing_evidence(engine):
    repo, user, space = invited(engine)
    token = repo.issue_authorized_session("issuer", "subject").token
    data = bundle_data()
    data["document"]["workspace_id"] = str(space)
    data["representation"]["text"] = "😀한e\u0301" * 50
    data["representation"]["text_sha256"] = sha256(
        data["representation"]["text"].encode()
    ).hexdigest()
    data["representation"]["pages"] = []
    data["citations"] = []
    bundle = EvidenceBundle.model_validate(data)
    snap = uuid4()
    storage.EvidenceRepository(engine).save(snap, bundle)
    summary = workspace(engine).list_evidence(token, space).items[0]
    assert summary.excerpt == bundle.representation.text[:160]
    assert len(summary.excerpt) == 160
    assert summary.citation_count == 0
    assert storage.EvidenceRepository(engine).load(space, snap) == bundle


def test_catalog_corrupt_parent_fails_whole_response_without_activity_refresh(engine):
    repo, user, space = invited(engine)
    token = repo.issue_authorized_session("issuer", "subject").token
    for _ in range(2):
        data = bundle_data()
        data["document"]["workspace_id"] = str(space)
        storage.EvidenceRepository(engine).save(uuid4(), EvidenceBundle.model_validate(data))
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=issued_at-interval '10 minutes', "
                "expires_at=expires_at-interval '10 minutes', "
                "last_activity_at=clock_timestamp()-interval '10 minutes'"
            )
        )
        before = conn.scalar(text("SELECT last_activity_at FROM auth_sessions"))
        conn.execute(
            text(
                "UPDATE document_versions SET content_sha256=:h "
                "WHERE version_id=(SELECT version_id FROM document_versions LIMIT 1)"
            ),
            {"h": "b" * 64},
        )
    with pytest.raises(storage.StorageError):
        workspace(engine).list_evidence(token, space)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT last_activity_at FROM auth_sessions")) == before
