"""Synthetic registration in a caller-owned PostgreSQL transaction."""

from copy import deepcopy
from uuid import UUID, uuid4

import issuedigest_storage as storage
import pytest
from issuedigest_domain import EvidenceBundle
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from conftest import bundle_data


def helpers():
    save = getattr(storage.EvidenceRepository, "_save", None)
    invite = getattr(storage.OAuthRepository, "_register_invite", None)
    assert callable(save), "missing caller-connection evidence persistence"
    assert callable(invite), "missing caller-connection invitation persistence"
    return save, invite


def counts(engine):
    tables = (
        "source_documents",
        "document_versions",
        "parsed_representations",
        "citations",
        "evidence_snapshots",
        "snapshot_citations",
        "outbox",
        "auth_identity_invites",
        "auth_users",
        "auth_workspace_memberships",
        "auth_sessions",
        "auth_oauth_flows",
    )
    with engine.connect() as connection:
        return {table: connection.scalar(text(f"SELECT count(*) FROM {table}")) for table in tables}


def test_caller_can_read_both_registrations_then_roll_back_together(engine):
    save, invite = helpers()
    from issuedigest_storage.auth_schema import auth_identity_invites

    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    before = counts(engine)
    with pytest.raises(RuntimeError, match="synthetic abort"):
        with engine.connect().execution_options(isolation_level="READ COMMITTED") as connection:
            with connection.begin():
                assert save(connection, snapshot, bundle) is True
                assert (
                    invite(
                        connection,
                        "issuer",
                        "Member@Example.test",
                        user,
                        bundle.document.workspace_id,
                        "viewer",
                    )
                    is True
                )
                assert (
                    storage.EvidenceRepository._load(
                        connection, bundle.document.workspace_id, snapshot
                    )
                    == bundle
                )
                row = connection.execute(select(auth_identity_invites)).mappings().one()
                assert (row["email"], row["enabled"], row["bound_subject"]) == (
                    "member@example.test",
                    True,
                    None,
                )
                raise RuntimeError("synthetic abort")
    assert counts(engine) == before


def test_caller_commit_matches_public_load_binding_and_normalized_retry(engine):
    save, invite = helpers()
    bundle = EvidenceBundle.model_validate(bundle_data())
    snapshot, user = uuid4(), uuid4()
    with engine.begin() as connection:
        assert save(connection, snapshot, bundle) is True
        assert (
            invite(
                connection,
                "issuer",
                "Member@Example.test",
                user,
                bundle.document.workspace_id,
                "editor",
            )
            is True
        )
    before = counts(engine)
    assert before["evidence_snapshots"] == before["outbox"] == before["auth_identity_invites"] == 1
    assert before["snapshot_citations"] == before["citations"] == 3
    assert before["auth_users"] == before["auth_workspace_memberships"] == 0
    assert storage.EvidenceRepository(engine).load(bundle.document.workspace_id, snapshot) == bundle
    with engine.begin() as connection:
        assert save(connection, snapshot, bundle) is False
        assert (
            invite(
                connection,
                "issuer",
                "MEMBER@example.test",
                user,
                bundle.document.workspace_id,
                "editor",
            )
            is False
        )
    assert counts(engine) == before
    assert storage.EvidenceRepository(engine).save(snapshot, bundle) is False
    assert (
        storage.OAuthRepository(engine).register_invite(
            "issuer", "member@example.test", user, bundle.document.workspace_id, "editor"
        )
        is False
    )
    assert (
        storage.OAuthRepository(engine).resolve_invited_identity(
            "issuer", "synthetic-subject", "member@example.test", True
        )
        == user
    )


@pytest.mark.parametrize("conflict", ["immutable", "source", "invite"])
def test_conflicts_roll_back_previous_new_rows_and_preserve_existing(engine, conflict):
    save, invite = helpers()
    original_data = bundle_data()
    original = EvidenceBundle.model_validate(original_data)
    snapshot, user = uuid4(), uuid4()
    storage.EvidenceRepository(engine).save(snapshot, original)
    oauth = storage.OAuthRepository(engine)
    oauth.register_invite(
        "issuer", "member@example.test", user, original.document.workspace_id, "viewer"
    )
    before = counts(engine)
    changed = deepcopy(original_data)
    if conflict == "immutable":
        changed["representation"]["parser_version"] = "2"
    elif conflict == "source":
        changed["document"]["document_id"] = str(uuid4())
        changed["version"]["document_id"] = changed["document"]["document_id"]
    with pytest.raises(storage.StorageConflict):
        with engine.begin() as connection:
            assert save(connection, uuid4(), EvidenceBundle.model_validate(bundle_data())) is True
            assert (
                invite(connection, "issuer", "new@example.test", uuid4(), uuid4(), "viewer") is True
            )
            if conflict == "invite":
                invite(connection, "issuer", "member@example.test", user, uuid4(), "viewer")
            else:
                save(connection, uuid4(), EvidenceBundle.model_validate(changed))
    assert counts(engine) == before
    assert (
        storage.EvidenceRepository(engine).load(original.document.workspace_id, snapshot)
        == original
    )
    assert (
        oauth.register_invite(
            "issuer", "member@example.test", user, original.document.workspace_id, "viewer"
        )
        is False
    )


@pytest.mark.parametrize("failure", ["unicode", "outbox"])
def test_database_failures_roll_back_invite_and_partial_evidence(engine, failure):
    save, invite = helpers()
    data = bundle_data()
    if failure == "unicode":
        from hashlib import sha256

        data["representation"]["text"] += "\x00"
        data["representation"]["text_sha256"] = sha256(
            data["representation"]["text"].encode()
        ).hexdigest()
    else:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE outbox ADD CONSTRAINT synthetic_failure CHECK (false)")
            )
    before = counts(engine)
    try:
        with pytest.raises(SQLAlchemyError):
            with engine.begin() as connection:
                assert (
                    invite(connection, "issuer", "member@example.test", uuid4(), uuid4(), "viewer")
                    is True
                )
                save(connection, uuid4(), EvidenceBundle.model_validate(data))
        assert counts(engine) == before
    finally:
        if failure == "outbox":
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE outbox DROP CONSTRAINT synthetic_failure"))


@pytest.mark.parametrize("bound", [False, True])
def test_repeated_invite_preserves_disabled_bound_and_authority_state(engine, bound):
    _, invite = helpers()
    from issuedigest_storage.auth_schema import (
        auth_identity_invites,
        auth_sessions,
        auth_users,
        auth_workspace_memberships,
    )

    user, workspace = uuid4(), uuid4()
    oauth = storage.OAuthRepository(engine)
    oauth.register_invite("issuer", "member@example.test", user, workspace, "viewer")
    if bound:
        oauth.resolve_invited_identity("issuer", "synthetic-subject", "member@example.test", True)
        oauth.issue_authorized_session("issuer", "synthetic-subject")
        storage.IdentityRepository(engine).set_enabled(user, False)
        storage.IdentityRepository(engine).set_membership(user, workspace, "viewer", False)
    oauth.set_invite_enabled("issuer", "member@example.test", False)
    tables = (auth_identity_invites, auth_users, auth_workspace_memberships, auth_sessions)
    with engine.connect() as connection:
        before = [connection.execute(select(table)).mappings().all() for table in tables]
    with engine.begin() as connection:
        assert (
            invite(connection, "issuer", "MEMBER@example.test", user, workspace, "viewer") is False
        )
    with engine.connect() as connection:
        assert [connection.execute(select(table)).mappings().all() for table in tables] == before


def test_connection_helpers_revalidate_untrusted_models_and_ids_without_writing(engine):
    save, invite = helpers()
    valid = EvidenceBundle.model_validate(bundle_data())
    invalid = valid.model_copy(update={"schema_version": True})
    with engine.begin() as connection:
        with pytest.raises(ValueError):
            save(connection, uuid4(), invalid)
        with pytest.raises(ValueError):
            save(connection, UUID(int=1), valid)
        with pytest.raises(ValueError):
            invite(connection, "issuer", "invalid email", uuid4(), uuid4(), "viewer")
        with pytest.raises(ValueError):
            invite(connection, "issuer", "member@example.test", uuid4(), uuid4(), "admin")
    assert all(value == 0 for value in counts(engine).values())


def test_public_invalid_input_is_rejected_before_opening_connection(engine, monkeypatch):
    repository, oauth = storage.EvidenceRepository(engine), storage.OAuthRepository(engine)
    bundle = EvidenceBundle.model_validate(bundle_data())

    def forbidden_connection(*args, **kwargs):
        raise AssertionError("invalid input attempted a DB connection")

    monkeypatch.setattr(engine, "connect", forbidden_connection)
    with pytest.raises(ValueError):
        repository.save(UUID(int=1), bundle)
    with pytest.raises(ValueError):
        repository.save(uuid4(), bundle.model_copy(update={"schema_version": True}))
    for issuer, email, user, workspace, role in (
        ("", "member@example.test", uuid4(), uuid4(), "viewer"),
        ("issuer", "invalid email", uuid4(), uuid4(), "viewer"),
        ("issuer", "member@example.test", UUID(int=1), uuid4(), "viewer"),
        ("issuer", "member@example.test", uuid4(), UUID(int=1), "viewer"),
        ("issuer", "member@example.test", uuid4(), uuid4(), "admin"),
    ):
        with pytest.raises(ValueError):
            oauth.register_invite(issuer, email, user, workspace, role)
