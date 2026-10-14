"""Synthetic operator plans, exact database guards and atomic provisioning."""

import importlib
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import event, select, text
from sqlalchemy.exc import SQLAlchemyError
from test_provision_transactions import counts

from conftest import bundle_data


def api():
    from pathlib import Path

    from issuedigest_storage import __path__

    assert (Path(next(iter(__path__))) / "provisioning.py").is_file(), "missing provisioning"
    return importlib.import_module("issuedigest_storage.provisioning")


def plan_data(invites=1, snapshots=1):
    workspace = str(uuid4())
    bundles = [bundle_data() for _ in range(snapshots)]
    for bundle in bundles:
        bundle["document"]["workspace_id"] = workspace
    return {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": workspace,
        "invites": [
            {"user_id": str(uuid4()), "email": f"Person.{i}+tag@Example.test", "role": "viewer"}
            for i in range(invites)
        ],
        "snapshots": [{"snapshot_id": str(uuid4()), "bundle": bundle} for bundle in bundles],
    }


def plan(data=None):
    return api().parse_plan(json.dumps(data or plan_data()))


@pytest.mark.parametrize("invites,snapshots", [(1, 1), (2, 50)])
def test_valid_boundaries_hide_contents_and_return_only_aggregate(invites, snapshots):
    p = api()
    data = plan_data(invites, snapshots)
    value = plan(data)
    assert p.validate_plan(value) == {
        "schema_version": 1,
        "status": "validated",
        "invites": invites,
        "snapshots": snapshots,
    }
    assert value.invites[0].email == "person.0+tag@example.test"
    for sensitive in (
        data["workspace_id"],
        data["expected_database"],
        "person",
        "synthetic",
        "tag",
    ):
        assert sensitive not in repr(value)
        assert sensitive not in repr(value.invites[0])
        assert sensitive not in repr(value.snapshots[0])
    with pytest.raises(ValidationError):
        value.workspace_id = uuid4()


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", "1"),
        ("schema_version", 2),
        ("expected_database", ""),
        ("expected_database", "1db"),
        ("expected_database", "a" * 64),
        ("expected_database", "db-name"),
        ("expected_database", "dé"),
        ("workspace_id", "00000000-0000-1000-8000-000000000000"),
        ("workspace_id", "secret"),
        ("extra", "secret"),
    ],
)
def test_rejects_invalid_plan_fields_without_value_disclosure(field, value):
    p = api()
    data = plan_data()
    data[field] = value
    with pytest.raises(p.ProvisioningError) as error:
        plan(data)
    assert str(error.value) == "Unable to validate provisioning plan"
    assert "secret" not in repr(error.value)


@pytest.mark.parametrize("invites,snapshots", [(0, 1), (3, 1), (1, 0), (1, 51)])
def test_rejects_collection_limits(invites, snapshots):
    p = api()
    with pytest.raises(p.ProvisioningError):
        plan(plan_data(invites, snapshots))


@pytest.mark.parametrize(
    "kind", ["email", "user", "snapshot", "workspace", "role", "bad-email", "uuid"]
)
def test_rejects_duplicates_and_invalid_nested_values(kind):
    p = api()
    data = plan_data(2, 2)
    if kind == "email":
        data["invites"][1]["email"] = data["invites"][0]["email"].upper()
    elif kind == "user":
        data["invites"][1]["user_id"] = data["invites"][0]["user_id"]
    elif kind == "snapshot":
        data["snapshots"][1]["snapshot_id"] = data["snapshots"][0]["snapshot_id"]
    elif kind == "workspace":
        data["snapshots"][1]["bundle"]["document"]["workspace_id"] = str(uuid4())
    elif kind == "role":
        data["invites"][0]["role"] = "admin"
    elif kind == "uuid":
        data["invites"][0]["user_id"] = "00000000-0000-1000-8000-000000000000"
    else:
        data["invites"][0]["email"] = "private name@예.test"
    with pytest.raises(p.ProvisioningError):
        plan(data)


@pytest.mark.parametrize(
    "raw",
    [
        '{"schema_version":1,"schema_version":1}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":-Infinity}',
        "\udcff",
        "[]",
        "{",
    ],
)
def test_rejects_ambiguous_or_invalid_json(raw):
    p = api()
    with pytest.raises(p.ProvisioningError):
        p.parse_plan(raw)


def test_bypassed_models_fail_before_connection(engine, monkeypatch):
    p = api()
    value = plan()

    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("connection forbidden")

    monkeypatch.setattr(engine, "connect", forbidden)
    for invalid in (
        value.model_copy(update={"schema_version": True}),
        value.model_copy(update={"invites": ()}),
        value.model_copy(update={"workspace_id": uuid4()}),
        value.model_copy(
            update={"snapshots": (value.snapshots[0].model_copy(update={"snapshot_id": "secret"}),)}
        ),
    ):
        with pytest.raises(p.ProvisioningError):
            p.apply_plan(engine, invalid)
        assert attempted == []
        with pytest.raises(p.ProvisioningError):
            p.check_database(engine, invalid)
        assert attempted == []


def test_url_target_and_dialect_fail_before_connect(monkeypatch):
    from sqlalchemy import create_engine

    p = api()
    value = plan()
    for url in (
        "sqlite://",
        "postgresql+psycopg://localhost/other",
        "postgresql+psycopg://localhost/issuedigest_test?dbname=other",
    ):
        engine = create_engine(url)

        attempted = []

        def forbidden(*args, _attempted=attempted, **kwargs):
            _attempted.append(True)
            raise AssertionError("connection forbidden")

        monkeypatch.setattr(engine, "connect", forbidden)
        try:
            with pytest.raises(p.ProvisioningError):
                p.check_database(engine, value)
            assert attempted == []
            with pytest.raises(p.ProvisioningError):
                p.apply_plan(engine, value)
            assert attempted == []
        finally:
            engine.dispose()


def test_check_is_readonly_and_preserves_all_rows(engine):
    p = api()
    value = plan()
    before = counts(engine)
    observed = []

    # Inspect transaction flags in a non-recursive cursor callback.
    def inspect_readonly(conn, cursor, statement, parameters, context, executemany):
        observed.append(statement)
        cursor.execute(
            "SELECT current_setting('transaction_read_only'), "
            "current_setting('transaction_isolation')"
        )
        assert cursor.fetchone() == ("on", "read committed")

    event.listen(engine, "before_cursor_execute", inspect_readonly)
    try:
        assert p.check_database(engine, value) == {
            "schema_version": 1,
            "status": "database_checked",
            "invites": 1,
            "snapshots": 1,
        }
    finally:
        event.remove(engine, "before_cursor_execute", inspect_readonly)
    assert observed and all(s.lstrip().upper().startswith("SELECT") for s in observed)
    assert counts(engine) == before


def test_apply_atomic_success_and_unchanged_retry(engine):
    from issuedigest_storage import EvidenceRepository

    p = api()
    value = plan(plan_data(2, 2))
    result = p.apply_plan(engine, value)
    assert result == {
        "schema_version": 1,
        "status": "applied",
        "invites_created": 2,
        "invites_unchanged": 0,
        "snapshots_created": 2,
        "snapshots_unchanged": 0,
    }
    before = counts(engine)
    assert before["evidence_snapshots"] == before["outbox"] == before["auth_identity_invites"] == 2
    assert (
        before["auth_users"] == before["auth_sessions"] == before["auth_workspace_memberships"] == 0
    )
    assert p.apply_plan(engine, value) == {
        "schema_version": 1,
        "status": "applied",
        "invites_created": 0,
        "invites_unchanged": 2,
        "snapshots_created": 0,
        "snapshots_unchanged": 2,
    }
    assert counts(engine) == before
    for snapshot in value.snapshots:
        assert (
            EvidenceRepository(engine).load(value.workspace_id, snapshot.snapshot_id)
            == snapshot.bundle
        )


@pytest.mark.parametrize("kind", ["snapshot", "source", "invite"])
def test_second_conflict_rolls_back_every_new_row(engine, kind):
    p = api()
    data = plan_data(2, 2)
    original = plan(data)
    p.apply_plan(engine, original)
    before = counts(engine)
    changed = deepcopy(data)
    fresh = plan_data(1, 1)
    fresh["snapshots"][0]["bundle"]["document"]["workspace_id"] = changed["workspace_id"]
    changed["snapshots"][0] = fresh["snapshots"][0]
    changed["invites"][0] = {"email": "new@example.test", "user_id": str(uuid4()), "role": "editor"}
    if kind == "snapshot":
        changed["snapshots"][1]["bundle"]["representation"]["parser_version"] = "changed"
    elif kind == "source":
        changed["snapshots"][1]["bundle"]["document"]["document_id"] = str(uuid4())
        changed["snapshots"][1]["bundle"]["version"]["document_id"] = changed["snapshots"][1][
            "bundle"
        ]["document"]["document_id"]
    else:
        changed["invites"][1]["role"] = "editor"
    with pytest.raises(p.ProvisioningError) as error:
        p.apply_plan(engine, plan(changed))
    assert str(error.value) == "Unable to apply provisioning plan"
    assert counts(engine) == before


@pytest.mark.parametrize("bound", [False, True])
def test_retry_preserves_disabled_or_bound_invites_and_auth_state(engine, bound):
    from issuedigest_storage import IdentityRepository, OAuthRepository
    from issuedigest_storage.auth_schema import (
        auth_identity_invites,
        auth_sessions,
        auth_users,
        auth_workspace_memberships,
    )

    p = api()
    value = plan()
    p.apply_plan(engine, value)
    oauth = OAuthRepository(engine)
    email = value.invites[0].email
    issuer = "https://accounts.google.com"
    if bound:
        user = oauth.resolve_invited_identity(issuer, "subject", email, True)
        oauth.issue_authorized_session(issuer, "subject")
        IdentityRepository(engine).set_enabled(user, False)
        IdentityRepository(engine).set_membership(user, value.workspace_id, "viewer", False)
    oauth.set_invite_enabled(issuer, email, False)
    tables = (auth_identity_invites, auth_users, auth_workspace_memberships, auth_sessions)
    with engine.connect() as conn:
        before = [conn.execute(select(t)).mappings().all() for t in tables]
    p.apply_plan(engine, value)
    with engine.connect() as conn:
        assert [conn.execute(select(t)).mappings().all() for t in tables] == before


@pytest.mark.parametrize("mode", ["check", "apply"])
def test_server_target_schema_and_commit_errors_are_fixed(engine, mode):
    p = api()
    value = plan()
    run = p.check_database if mode == "check" else p.apply_plan
    before = counts(engine)
    # Missing required column, with reversible owned synthetic DDL.
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE auth_identity_invites RENAME COLUMN email TO missing_email"))
    try:
        with pytest.raises(p.ProvisioningError):
            run(engine, value)
    finally:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE auth_identity_invites RENAME COLUMN missing_email TO email")
            )
    assert counts(engine) == before

    def reject_commit(conn):
        raise SQLAlchemyError("secret: private-email/path/db")

    event.listen(engine, "commit", reject_commit)
    try:
        with pytest.raises(p.ProvisioningError) as error:
            run(engine, value)
        assert "secret" not in str(error.value)
        assert "private" not in repr(error.value)
    finally:
        event.remove(engine, "commit", reject_commit)
    assert counts(engine) == before


def test_permission_denied_rolls_back_without_secret_output(engine):
    p = api()
    value = plan()
    before = counts(engine)
    # SET LOCAL ROLE loses all existing owner privileges for this transaction only.
    with engine.begin() as conn:
        conn.execute(text("CREATE ROLE synthetic_provision_denied NOLOGIN"))

    def deny(conn):
        conn.exec_driver_sql("SET LOCAL ROLE synthetic_provision_denied")

    event.listen(engine, "begin", deny)
    try:
        with pytest.raises(p.ProvisioningError):
            p.apply_plan(engine, value)
    finally:
        event.remove(engine, "begin", deny)
        with engine.begin() as conn:
            conn.execute(text("DROP ROLE synthetic_provision_denied"))
    assert counts(engine) == before


def test_identifier_limit_and_email_aliases_remain_exact():
    p = api()
    data = plan_data(2, 1)
    data["expected_database"] = "A" * 63
    data["invites"][1]["email"] = "Person0@Example.test"
    value = plan(data)
    assert value.expected_database == "A" * 63
    assert [invite.email for invite in value.invites] == [
        "person.0+tag@example.test",
        "person0@example.test",
    ]
    with pytest.raises(p.ProvisioningError):
        p.validate_database_url("postgresql+psycopg://localhost/" + "a" * 63, value)


@pytest.mark.parametrize("mode", ["check", "apply"])
def test_actual_server_database_mismatch_rejected(engine, mode):
    p = api()
    data = plan_data()
    data["expected_database"] = "wrong_target"
    original_url = engine.url
    # URL metadata passes precheck; real connection still reaches the owned test DB.
    engine.url = engine.url.set(database="wrong_target")
    try:
        with pytest.raises(p.ProvisioningError):
            (p.check_database if mode == "check" else p.apply_plan)(engine, plan(data))
    finally:
        engine.url = original_url
    assert all(count == 0 for count in counts(engine).values())


@pytest.mark.parametrize("mode", ["check", "apply"])
def test_shadow_schema_is_rejected_before_writing(engine, mode):
    p = api()
    value = plan()

    def shadow(conn):
        conn.exec_driver_sql("SET LOCAL search_path = pg_catalog")

    event.listen(engine, "begin", shadow)
    try:
        with pytest.raises(p.ProvisioningError):
            (p.check_database if mode == "check" else p.apply_plan)(engine, value)
    finally:
        event.remove(engine, "begin", shadow)
    assert all(count == 0 for count in counts(engine).values())


def test_partial_database_error_rolls_back_first_snapshot_and_all_invites(engine):
    from hashlib import sha256

    p = api()
    data = plan_data(2, 2)
    representation = data["snapshots"][1]["bundle"]["representation"]
    representation["text"] += "\x00"
    representation["text_sha256"] = sha256(representation["text"].encode()).hexdigest()
    with pytest.raises(p.ProvisioningError):
        p.apply_plan(engine, plan(data))
    assert all(count == 0 for count in counts(engine).values())


def test_invite_permission_denied_rolls_back_preceding_evidence(engine):
    p = api()
    value = plan()
    with engine.begin() as conn:
        conn.execute(text("CREATE ROLE synthetic_provision_partial NOLOGIN"))
        conn.execute(text("GRANT USAGE ON SCHEMA public TO synthetic_provision_partial"))
        conn.execute(
            text(
                "GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA public TO synthetic_provision_partial"
            )
        )
        conn.execute(
            text("REVOKE INSERT ON auth_identity_invites FROM synthetic_provision_partial")
        )
    observed_evidence_inserts = []

    def deny(conn):
        conn.exec_driver_sql("SET LOCAL ROLE synthetic_provision_partial")

    def observe(conn, cursor, statement, parameters, context, executemany):
        if statement.startswith("INSERT INTO evidence_snapshots"):
            observed_evidence_inserts.append(True)

    event.listen(engine, "begin", deny)
    event.listen(engine, "after_cursor_execute", observe)
    try:
        with pytest.raises(p.ProvisioningError):
            p.apply_plan(engine, value)
    finally:
        event.remove(engine, "begin", deny)
        event.remove(engine, "after_cursor_execute", observe)
        with engine.begin() as conn:
            conn.execute(text("DROP OWNED BY synthetic_provision_partial"))
            conn.execute(text("DROP ROLE synthetic_provision_partial"))
    assert observed_evidence_inserts == [True]
    assert all(count == 0 for count in counts(engine).values())


def test_lost_commit_response_is_failure_even_when_server_committed(engine, monkeypatch):
    p = api()
    value = plan()
    commit = engine.dialect.do_commit

    def lose_response(connection):
        commit(connection)
        raise SQLAlchemyError("secret uncertain commit")

    monkeypatch.setattr(engine.dialect, "do_commit", lose_response)
    with pytest.raises(p.ProvisioningError) as error:
        p.apply_plan(engine, value)
    assert str(error.value) == "Unable to apply provisioning plan"
    monkeypatch.setattr(engine.dialect, "do_commit", commit)
    # Uncertain commit cannot be claimed rolled back; identical retry is safe.
    assert counts(engine)["evidence_snapshots"] == 1
    assert p.apply_plan(engine, value)["snapshots_unchanged"] == 1
