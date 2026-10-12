"""Provider independent identity and session access behavior."""

import re
from hashlib import sha256
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import EvidenceRepository, StorageConflict, StorageError
from issuedigest_storage.access import EvidenceAccessRepository
from issuedigest_storage.identity import IdentityRepository
from issuedigest_storage.sessions import AuthenticationDenied, SessionRepository
from sqlalchemy import text

from conftest import bundle_data, migration_config


def test_registered_verified_identity_returns_durable_user(engine):
    user = uuid4()
    assert IdentityRepository(engine).register_identity(user, "issuer", "subject") == user


def test_exact_identity_pairs_are_durable_distinct_and_immutable(engine):
    registry = IdentityRepository(engine)
    first, other = uuid4(), uuid4()
    assert registry.register_identity(first, " issuer ", " subject ") == first
    assert registry.register_identity(first, " issuer ", " subject ") == first
    assert registry.register_identity(other, "issuer", " subject ") == other
    with pytest.raises(StorageConflict):
        registry.register_identity(uuid4(), " issuer ", " subject ")
    with pytest.raises(StorageConflict):
        registry.register_identity(first, "different", " subject ")
    with engine.connect() as conn:
        assert conn.execute(
            text("SELECT issuer, subject FROM auth_users WHERE user_id=:u"), {"u": first}
        ).one() == (" issuer ", " subject ")


@pytest.mark.parametrize("field", ["", "nul\x00value", "x" * 257, None])
def test_invalid_identity_is_rejected_without_storage(engine, field):
    with pytest.raises(ValueError):
        IdentityRepository(engine).register_identity(uuid4(), field, "subject")
    with pytest.raises(ValueError):
        IdentityRepository(engine).register_identity(uuid4(), "issuer", field)


def setup_access(engine):
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    EvidenceRepository(engine).save(snapshot, bundle)
    identities = IdentityRepository(engine)
    identities.register_identity(user, "issuer", str(user))
    identities.set_membership(user, bundle.document.workspace_id, "viewer")
    return (
        bundle,
        snapshot,
        user,
        identities,
        SessionRepository(engine),
        EvidenceAccessRepository(engine),
    )


def test_sessions_store_hash_only_and_authorized_read_updates_activity(engine):
    bundle, snapshot, user, _, sessions, access = setup_access(engine)
    issued = sessions.issue_session(user)
    assert issued is not None
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", issued.token)
    assert issued.token not in repr(issued)
    second = sessions.issue_session(user, 60)
    assert second.token != issued.token
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=issued_at-interval '10 minutes', "
                "expires_at=expires_at-interval '10 minutes', "
                "last_activity_at=clock_timestamp()-interval '10 minutes'"
            )
        )
        before = conn.execute(
            text(
                "SELECT token_sha256, expires_at, last_activity_at FROM auth_sessions WHERE "
                "token_sha256=:h"
            ),
            {"h": sha256(issued.token.encode()).hexdigest()},
        ).one()
        assert before.token_sha256 != issued.token
        assert (
            before.expires_at
            - conn.scalar(
                text("SELECT issued_at FROM auth_sessions WHERE token_sha256=:h"),
                {"h": before.token_sha256},
            )
        ).total_seconds() == 28800
        assert issued.token not in str(conn.execute(text("SELECT * FROM auth_sessions")).all())
    assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) == bundle
    with engine.connect() as conn:
        after = conn.execute(
            text("SELECT expires_at,last_activity_at FROM auth_sessions WHERE token_sha256=:h"),
            {"h": before.token_sha256},
        ).one()
        assert after.expires_at == before.expires_at
        assert after.last_activity_at > before.last_activity_at
    assert issued.expires_at.tzinfo is not None


@pytest.mark.parametrize("seconds", [0, -1, 28801, True, 1.5, "60", None])
def test_invalid_session_lifetimes_are_rejected(engine, seconds):
    with pytest.raises(ValueError):
        SessionRepository(engine).issue_session(uuid4(), seconds)


def test_nonexistent_and_disabled_users_cannot_receive_sessions(engine):
    registry = IdentityRepository(engine)
    user = uuid4()
    sessions = SessionRepository(engine)
    with pytest.raises(AuthenticationDenied):
        sessions.issue_session(user)
    registry.register_identity(user, "issuer", "subject")
    registry.set_enabled(user, False)
    with pytest.raises(AuthenticationDenied):
        sessions.issue_session(user)


@pytest.mark.parametrize("mutation", ["expired", "idle", "revoked", "disabled", "membership"])
def test_database_revocation_and_expiry_apply_on_next_read(engine, mutation):
    bundle, snapshot, user, identities, sessions, access = setup_access(engine)
    issued = sessions.issue_session(user)
    assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) == bundle
    if mutation in {"expired", "idle"}:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE auth_sessions SET "
                    + (
                        "expires_at=clock_timestamp()"
                        if mutation == "expired"
                        else (
                            "issued_at=issued_at-interval '30 minutes', "
                            "expires_at=expires_at-interval '30 minutes', "
                            "last_activity_at=clock_timestamp()-interval '1800 seconds'"
                        )
                    )
                )
            )
    elif mutation == "revoked":
        sessions.revoke_session(issued.token)
        sessions.revoke_session(issued.token)
    elif mutation == "disabled":
        identities.set_enabled(user, False)
    else:
        identities.set_membership(user, bundle.document.workspace_id, "viewer", False)
    if mutation == "membership":
        assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) is None
    else:
        with pytest.raises(AuthenticationDenied):
            access.load_evidence(issued.token, bundle.document.workspace_id, snapshot)


def test_denied_or_missing_evidence_never_refreshes_activity_or_reads_payload(engine):
    bundle, snapshot, user, identities, sessions, access = setup_access(engine)
    issued = sessions.issue_session(user)
    different = uuid4()
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=issued_at-interval '10 minutes', "
                "expires_at=expires_at-interval '10 minutes', "
                "last_activity_at=clock_timestamp()-interval '10 minutes'"
            )
        )
        before = conn.scalar(text("SELECT last_activity_at FROM auth_sessions"))
        # If unauthorized requests read evidence, this deliberately corrupted row raises.
        conn.execute(text("UPDATE evidence_snapshots SET content_sha256=:h"), {"h": "b" * 64})
    assert access.load_evidence(issued.token, different, snapshot) is None
    identities.set_membership(user, bundle.document.workspace_id, "viewer", False)
    assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) is None
    identities.set_membership(user, bundle.document.workspace_id, "owner")
    assert access.load_evidence(issued.token, bundle.document.workspace_id, uuid4()) is None
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT last_activity_at FROM auth_sessions")) == before
    with pytest.raises(StorageError):
        access.load_evidence(issued.token, bundle.document.workspace_id, snapshot)


def test_two_members_can_read_one_snapshot_but_other_workspace_cannot(engine):
    bundle, snapshot, user, identities, sessions, access = setup_access(engine)
    second = uuid4()
    identities.register_identity(second, "other", str(user))
    identities.set_membership(second, bundle.document.workspace_id, "editor")
    for member in [user, second]:
        issued = sessions.issue_session(member)
        assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) == bundle
        other = uuid4()
        identities.set_membership(member, other, "viewer")
        assert access.load_evidence(issued.token, other, snapshot) is None


def test_membership_role_user_reference_and_uuid_validation(engine):
    registry = IdentityRepository(engine)
    user, workspace = uuid4(), uuid4()
    registry.register_identity(user, "issuer", "subject")
    with pytest.raises(ValueError):
        registry.set_membership(user, workspace, "admin")
    with pytest.raises(StorageError):
        registry.set_membership(uuid4(), workspace, "viewer")
    for method, args in [
        (registry.register_identity, (str(user), "issuer", "subject")),
        (registry.set_membership, (user, str(workspace), "viewer")),
        (SessionRepository(engine).issue_session, (str(user),)),
    ]:
        with pytest.raises(ValueError):
            method(*args)
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO auth_workspace_memberships(user_id,workspace_id,role,active) "
                "VALUES(:u,:w,'admin',true)"
            ),
            {"u": user, "w": workspace},
        )
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO auth_workspace_memberships(user_id,workspace_id,role,active) "
                "VALUES(:u,:w,'viewer',true)"
            ),
            {"u": uuid4(), "w": workspace},
        )


def test_auth_migration_upgrade_and_downgrade_preserve_existing_evidence(engine, database_url):
    from alembic import command

    config = migration_config(database_url)
    command.downgrade(config, "0001_evidence_snapshots")
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot = uuid4()
    repository = EvidenceRepository(engine)
    repository.save(snapshot, bundle)
    try:
        command.upgrade(config, "head")
        assert repository.load(bundle.document.workspace_id, snapshot) == bundle
        IdentityRepository(engine).register_identity(uuid4(), "issuer", "subject")
        command.downgrade(config, "0001_evidence_snapshots")
        assert repository.load(bundle.document.workspace_id, snapshot) == bundle
    finally:
        command.upgrade(config, "head")


@pytest.mark.parametrize("seconds", [1, 28800])
def test_session_lifetime_limits_are_stored_exactly(engine, seconds):
    user = uuid4()
    IdentityRepository(engine).register_identity(user, "issuer", str(user))
    issued = SessionRepository(engine).issue_session(user, seconds)
    with engine.connect() as conn:
        duration = conn.scalar(
            text("SELECT extract(epoch FROM expires_at-issued_at) FROM auth_sessions")
        )
        assert duration == seconds
        assert issued.expires_at.utcoffset().total_seconds() == 0


def test_identity_registration_race_cannot_merge_two_user_ids(engine):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)
    registry = IdentityRepository(engine)
    first, second = uuid4(), uuid4()

    def register(user):
        barrier.wait(timeout=5)
        try:
            return registry.register_identity(user, "same-issuer", "same-subject")
        except StorageConflict:
            return None

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(register, [first, second]))
    assert results.count(None) == 1
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM auth_users")) == 1
        assert conn.scalar(text("SELECT user_id FROM auth_users")) in {first, second}


def test_exact_unicode_identity_limits_preserve_values(engine):
    user = uuid4()
    issuer, subject = "😀" * 256, "한" * 256
    assert IdentityRepository(engine).register_identity(user, issuer, subject) == user
    with engine.connect() as conn:
        assert conn.execute(text("SELECT issuer,subject FROM auth_users")).one() == (
            issuer,
            subject,
        )


def test_autocommit_engine_still_uses_atomic_internal_transactions(engine):
    configured = engine.execution_options(isolation_level="AUTOCOMMIT")
    bundle, snapshot, user, _, sessions, access = setup_access(configured)
    issued = sessions.issue_session(user)
    assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) == bundle
    sessions.revoke_session(issued.token)
    with pytest.raises(AuthenticationDenied):
        access.load_evidence(issued.token, bundle.document.workspace_id, snapshot)


def test_successful_read_just_inside_idle_boundary_is_permitted(engine):
    bundle, snapshot, user, _, sessions, access = setup_access(engine)
    issued = sessions.issue_session(user)
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE auth_sessions SET issued_at=issued_at-interval '30 minutes', "
                "expires_at=expires_at-interval '30 minutes', "
                "last_activity_at=clock_timestamp()-interval '1799 seconds'"
            )
        )
    assert access.load_evidence(issued.token, bundle.document.workspace_id, snapshot) == bundle
