"""Synthetic capture approvals and explicit PostgreSQL intake; no live source/model IO."""

import importlib
import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from issuedigest_storage.policy_collection import PolicyCollectionConfig, PolicyCollectionRepository
from issuedigest_storage.provisioning import parse_plan
from test_policy_import import policy_inputs as _policy_inputs


@pytest.fixture
def policy_inputs(tmp_path):
    return _policy_inputs.__wrapped__(tmp_path)


NOW = datetime(2026, 10, 16, tzinfo=UTC)


def api():
    try:
        return importlib.import_module("issuedigest_worker.policy_intake")
    except ModuleNotFoundError:
        pytest.fail("Missing reviewed policy intake worker")


def envelope(inputs):
    job, _, base, _ = inputs
    return {
        "schema_version": 1,
        "workspace_id": base["workspace_id"],
        "attempt_id": str(uuid4()),
        "collection": {
            "schema_version": 1,
            "expected_database": "issuedigest_test",
            "collection_id": str(uuid4()),
            "news_ids": [s["news_id"] for s in job["sources"]],
            "minimum_interval_seconds": 60,
            "max_age_seconds": 120,
            "max_attempts": 24,
        },
        "approval": job,
    }


def test_pure_candidates_equal_existing_exact_preparation_without_base_or_ids(
    policy_inputs, monkeypatch
):
    from issuedigest_worker import parse_policy_job, policy_prepare, prepare_policy_plan

    prepare = getattr(policy_prepare, "prepare_policy_candidates", None)
    assert callable(prepare), "Missing pure candidate preparation"
    job, raw, base, _ = policy_inputs
    job = parse_policy_job(json.dumps(job))
    original = prepare_policy_plan(job, raw, parse_plan(json.dumps(base)))

    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected side effect")

    import socket

    import sqlalchemy

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    monkeypatch.setattr("uuid.uuid4", forbidden)
    actual = prepare(job, raw, UUID(base["workspace_id"]))
    assert actual.snapshots == original.plan.snapshots[-1:]
    assert actual.presentations == original.presentations
    assert prepare(job, raw, UUID(base["workspace_id"])) == actual
    assert "합성" not in repr(actual)


def test_strict_approval_parser_reuses_existing_job_and_config(policy_inputs):
    a = api()
    data = envelope(policy_inputs)
    parsed = a.parse_policy_intake_approval(json.dumps(data, ensure_ascii=False))
    assert parsed.approval.model_dump(mode="json") == data["approval"]
    assert parsed.collection.news_ids == ("123456789",)
    assert parsed.workspace_id == UUID(data["workspace_id"])
    assert repr(parsed) == "PolicyIntakeApproval(schema_version=1)"


def journal(engine, data, raw, now=NOW, previous=None):
    from issuedigest_worker.policy_changes import compare_policy_captures

    cfg = PolicyCollectionConfig.model_validate_json(json.dumps(data["collection"]), strict=True)
    report = compare_policy_captures(raw, previous_raw=previous)
    with PolicyCollectionRepository(engine).lease(cfg) as session:
        attempt = session.start(now=now).attempt
        assert attempt is not None
        session.succeed(attempt.attempt_id, raw, report.model_dump_json().encode(), finished_at=now)
    data["attempt_id"] = str(attempt.attempt_id)
    return report


def counts(engine):
    from sqlalchemy import text

    with engine.connect() as conn:
        return {
            name: conn.scalar(text(f"SELECT count(*) FROM {name}"))
            for name in (
                "source_documents",
                "document_versions",
                "parsed_representations",
                "citations",
                "evidence_snapshots",
                "snapshot_citations",
                "outbox",
                "source_presentations",
                "evidence_search_projections",
                "evidence_search_units",
                "policy_intake_receipts",
                "policy_collection_attempts",
            )
        }


def test_coordinator_exact_hash_receipt_quote_and_readonly_check(
    engine, policy_inputs, monkeypatch
):
    from issuedigest_storage.policy_intake_schema import policy_intake_receipts
    from sqlalchemy import event, select

    a, data = api(), envelope(policy_inputs)
    report = journal(engine, data, policy_inputs[1])
    approved = a.parse_policy_intake_approval(json.dumps(data))
    prepare = getattr(a, "prepare_policy_intake_plan", None)
    assert callable(prepare), "Missing fixed capture intake coordination"
    plan = prepare(engine, approved)
    assert plan.entries[0].fingerprint_sha256 == report.sources[0].after_fingerprint
    canonical = json.dumps(
        approved.approval.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    assert plan.approval_sha256 == sha256(canonical).hexdigest()
    assert plan.entries[0].bundle.citations[0].selector.quote == "😀한é"
    before = counts(engine)
    statements = []

    def observe(conn, cursor, statement, parameters, context, many):
        statements.append(statement)
        if "FROM policy_collection" in statement:
            assert conn.exec_driver_sql("SHOW transaction_read_only").scalar() == "on"

    def forbidden(*args, **kwargs):
        raise AssertionError("source/model call")

    import httpx2

    monkeypatch.setattr(httpx2.Client, "send", forbidden)
    monkeypatch.setattr("issuedigest_worker.policy_collection.capture_policy", forbidden)
    monkeypatch.setattr("uuid.uuid4", forbidden)
    event.listen(engine, "before_cursor_execute", observe)
    try:
        result = a.intake_policy_capture(engine, approved, apply=False)
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert (result.outcome, result.new_versions, result.receipts_created) == ("checked", 1, 0)
    assert before == counts(engine)
    assert not any(
        s.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE")) or "advisory" in s.lower()
        for s in statements
    )
    applied = a.intake_policy_capture(engine, approved, apply=True)
    assert (applied.outcome, applied.new_versions, applied.receipts_created) == ("applied", 1, 1)
    after = counts(engine)
    assert after["evidence_search_projections"] == after["policy_intake_receipts"] == 1
    with engine.connect() as conn:
        receipt = conn.execute(select(policy_intake_receipts)).mappings().one()
        assert receipt["approval_sha256"] == sha256(canonical).hexdigest()
        assert receipt["fingerprint_sha256"] == report.sources[0].after_fingerprint
    assert a.intake_policy_capture(engine, approved, apply=True).outcome == "already_applied"
    assert after == counts(engine)


def test_cli_explicit_modes_cleanup_allowlist_and_exact_retry(
    engine, policy_inputs, monkeypatch, capsys
):
    from issuedigest_worker import policy_cli
    from test_policy_import import private_file

    data = envelope(policy_inputs)
    journal(engine, data, policy_inputs[1])
    path = private_file(policy_inputs[3] / "approval.json", json.dumps(data).encode())
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    created = policy_cli.create_engine
    disposed = []

    def create(*args, **kwargs):
        value = created(*args, **kwargs)
        dispose = value.dispose

        def cleanup():
            assert capsys.readouterr().out == ""
            disposed.append(True)
            dispose()

        value.dispose = cleanup
        return value

    monkeypatch.setattr(policy_cli, "create_engine", create)
    for mode, outcome in (
        ("--check", "checked"),
        ("--apply", "applied"),
        ("--apply", "already_applied"),
    ):
        assert policy_cli.main(["intake", path, mode]) == 0
        logs = capsys.readouterr()
        result = json.loads(logs.out)
        assert logs.err == ""
        assert set(result) == {
            "schema_version",
            "outcome",
            "sources",
            "new_versions",
            "reused_versions",
            "receipts_created",
        }
        assert result["outcome"] == outcome
    assert disposed == [True] * 3


@pytest.mark.parametrize("flags", [[], ["--check", "--apply"], ["--ch"], ["--apply", "--unknown"]])
def test_cli_requires_unambiguous_explicit_mode_before_io(flags, monkeypatch, capsys):
    from issuedigest_worker import policy_cli

    def forbidden(*args, **kwargs):
        raise AssertionError("IO before argument validation")

    monkeypatch.setattr(policy_cli, "read_private", forbidden)
    monkeypatch.setattr(policy_cli, "create_engine", forbidden)
    assert policy_cli.main(["intake", "/PRIVATE/approval.json", *flags]) == 2
    logs = capsys.readouterr()
    assert logs.out == "" and logs.err == "Invalid policy arguments\n"


@pytest.mark.parametrize(
    "kind",
    [
        "duplicate",
        "nonfinite",
        "utf8",
        "oversize",
        "extra",
        "bool",
        "workspace",
        "attempt",
        "collection",
        "scope",
        "rights",
        "quote",
        "nested_extra",
    ],
)
def test_parser_rejects_untrusted_private_envelopes(policy_inputs, kind):
    from issuedigest_worker import PreparationError

    a, data = api(), envelope(policy_inputs)
    if kind == "extra":
        data["secret"] = "PRIVATE"
    if kind == "bool":
        data["schema_version"] = True
    if kind in {"workspace", "attempt"}:
        data[kind + "_id"] = "00000000-0000-1000-8000-000000000001"
    if kind == "collection":
        data["collection"]["max_attempts"] = True
    if kind == "scope":
        data["collection"]["news_ids"] = ["234567890"]
    if kind == "rights":
        data["approval"]["sources"][0]["license"]["operator_approved"] = False
    if kind == "quote":
        data["approval"]["sources"][0]["citations"][0]["quote"] = "x" * 2001
    if kind == "nested_extra":
        data["approval"]["sources"][0]["private"] = "PRIVATE"
    raw = json.dumps(data)
    if kind == "duplicate":
        raw = raw[:-1] + ',"schema_version":1}'
    if kind == "nonfinite":
        raw = raw[:-1] + ',"private":Infinity}'
    if kind == "utf8":
        raw = b"\xff"
    if kind == "oversize":
        raw = " " * (a.MAX_POLICY_INTAKE_APPROVAL_BYTES + 1)
    with pytest.raises(PreparationError, match="^Unable to validate policy intake approval$"):
        a.parse_policy_intake_approval(raw)


@pytest.mark.parametrize("kind", ["approval", "config", "extra", "workspace", "mode"])
def test_forged_sdk_graphs_reject_before_serialization_or_connection(
    policy_inputs, monkeypatch, kind
):
    from issuedigest_storage.policy_intake import PolicyIntakeError
    from pydantic import BaseModel

    a = api()
    value = a.parse_policy_intake_approval(json.dumps(envelope(policy_inputs)))
    if kind == "approval":
        value = value.model_copy(
            update={
                "approval": value.approval.model_copy(
                    update={"sources": value.approval.sources * 10000}
                )
            }
        )
    if kind == "config":
        value = value.model_copy(
            update={
                "collection": value.collection.model_copy(
                    update={"news_ids": ("123456789",) * 10000}
                )
            }
        )
    if kind == "extra":
        value = value.model_copy(update={"private": "PRIVATE"})
    if kind == "workspace":
        value = value.model_copy(update={"workspace_id": uuid4().hex})
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("IO or serialization before validation")

    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(PolicyIntakeError, match="^Policy intake unavailable$"):
        a.intake_policy_capture(object(), value, apply=1 if kind == "mode" else False)
    assert calls == []


def newer(data, raw, now, *, body=None, quote=None):
    data = json.loads(json.dumps(data))
    capture = json.loads(raw)
    capture["collected_at"] = now.isoformat()
    if body:
        capture["articles"][0]["html"] = capture["articles"][0]["html"].replace("둘째 문단", body)
    raw = json.dumps(capture, ensure_ascii=False).encode()
    approval = data["approval"]
    approval.update(collected_at=now.isoformat(), capture_sha256=sha256(raw).hexdigest())
    source = approval["sources"][0]
    source["article_sha256"] = sha256(capture["articles"][0]["html"].encode()).hexdigest()
    source["text_sha256"] = sha256(f"앞 😀한é 뒤\n\n{body or '둘째 문단'}".encode()).hexdigest()
    for name in ("version_id", "raw_object_id", "representation_id", "snapshot_id"):
        source[name] = str(uuid4())
    source["citations"][0]["citation_id"] = str(uuid4())
    if quote:
        source["citations"][0].update(quote=quote, start=None)
    return data, raw


def test_fixed_older_attempt_ignores_newer_poll_then_reuse_change_revert_and_quote(
    engine, policy_inputs
):
    from issuedigest_storage.policy_intake import PolicyIntakeError

    a, first = api(), envelope(policy_inputs)
    raw = policy_inputs[1]
    journal(engine, first, raw)
    second, raw2 = newer(first, raw, NOW + timedelta(seconds=60))
    journal(engine, second, raw2, NOW + timedelta(seconds=60), raw)
    # Later poll exists, but only the explicitly approved first artifact is prepared/applied.
    assert (
        a.intake_policy_capture(
            engine, a.parse_policy_intake_approval(json.dumps(first)), apply=True
        ).new_versions
        == 1
    )
    assert (
        a.intake_policy_capture(
            engine, a.parse_policy_intake_approval(json.dumps(second)), apply=True
        ).reused_versions
        == 1
    )
    after_reuse = counts(engine)
    assert after_reuse["document_versions"] == after_reuse["outbox"] == 1
    for minute, body, quote in ((2, "새 문단", None), (3, None, None), (4, None, "둘째 문단")):
        next_data, next_raw = newer(
            first, raw, NOW + timedelta(minutes=minute), body=body, quote=quote
        )
        journal(engine, next_data, next_raw, NOW + timedelta(minutes=minute), raw2)
        result = a.intake_policy_capture(
            engine, a.parse_policy_intake_approval(json.dumps(next_data)), apply=True
        )
        assert result.new_versions == 1
        raw2 = next_raw
    after = counts(engine)
    assert after["source_documents"] == 1
    assert after["document_versions"] == after["citations"] == after["outbox"] == 4
    assert after["policy_intake_receipts"] == 5
    altered = json.loads(json.dumps(first))
    altered["approval"]["sources"][0]["citations"][0]["citation_id"] = str(uuid4())
    with pytest.raises(PolicyIntakeError):
        a.intake_policy_capture(
            engine, a.parse_policy_intake_approval(json.dumps(altered)), apply=True
        )
    assert counts(engine) == after


@pytest.mark.parametrize(
    "kind",
    ["fingerprint", "report_state", "rights", "capture", "unknown", "foreign", "failed", "running"],
)
def test_unapproved_or_forged_journal_rejects_without_any_intake_rows(engine, policy_inputs, kind):
    from issuedigest_storage.policy_collection_schema import policy_collection_attempts as attempts
    from issuedigest_storage.policy_intake import PolicyIntakeError
    from sqlalchemy import update

    a, data = api(), envelope(policy_inputs)
    report = journal(engine, data, policy_inputs[1])
    if kind in {"fingerprint", "report_state"}:
        changed = report.model_dump(mode="json")
        changed["sources"][0].update(
            {"after_fingerprint": "f" * 64} if kind == "fingerprint" else {"status": "unchanged"}
        )
        raw = json.dumps(changed).encode()
        with engine.begin() as conn:
            conn.execute(
                update(attempts).values(report_bytes=raw, report_sha256=sha256(raw).hexdigest())
            )
    if kind in {"rights", "capture"}:
        changed = (
            policy_inputs[1].replace("제1유형".encode(), "제2유형".encode())
            if kind == "rights"
            else policy_inputs[1] + b" "
        )
        with engine.begin() as conn:
            conn.execute(
                update(attempts).values(
                    capture_bytes=changed, capture_sha256=sha256(changed).hexdigest()
                )
            )
    if kind == "unknown":
        data["attempt_id"] = str(uuid4())
    if kind == "foreign":
        data["collection"]["collection_id"] = str(uuid4())
    if kind in {"failed", "running"}:
        cfg = PolicyCollectionConfig.model_validate_json(
            json.dumps(data["collection"]), strict=True
        )
        with PolicyCollectionRepository(engine).lease(cfg) as session:
            attempt = session.start(now=NOW + timedelta(minutes=1)).attempt
            if kind == "failed":
                session.fail(
                    attempt.attempt_id, "capture_failed", finished_at=NOW + timedelta(minutes=1)
                )
        data["attempt_id"] = str(attempt.attempt_id)
    before = counts(engine)
    with pytest.raises(PolicyIntakeError, match="^Policy intake unavailable$"):
        a.intake_policy_capture(
            engine, a.parse_policy_intake_approval(json.dumps(data)), apply=True
        )
    assert before == counts(engine)
    assert before["policy_intake_receipts"] == 0


@pytest.mark.parametrize(
    "kind",
    [
        "mode",
        "relative",
        "symlink",
        "missing_env",
        "wrong_database",
        "query",
        "dispose",
        "pool",
        "commit_unknown",
        "busy",
    ],
)
def test_cli_private_failures_or_busy_never_publish_private_diagnostics(
    engine, policy_inputs, monkeypatch, capsys, caplog, kind
):
    import logging

    from issuedigest_storage.policy_intake import PolicyIntakeCommitUnknown, PolicyIntakeRepository
    from issuedigest_worker import policy_cli
    from test_policy_import import private_file

    data = envelope(policy_inputs)
    journal(engine, data, policy_inputs[1])
    path = private_file(policy_inputs[3] / "approval.json", json.dumps(data).encode())
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    if kind == "mode":
        (policy_inputs[3] / "approval.json").chmod(0o644)
    if kind == "relative":
        path = "PRIVATE.json"
    if kind == "symlink":
        link = policy_inputs[3] / "link.json"
        link.symlink_to(path)
        path = str(link)
    if kind == "missing_env":
        monkeypatch.delenv("ISSUEDIGEST_DATABASE_URL")
    if kind == "wrong_database":
        monkeypatch.setenv(
            "ISSUEDIGEST_DATABASE_URL", "postgresql+psycopg://PRIVATE@127.0.0.1/PRIVATE"
        )
    if kind == "query":
        monkeypatch.setenv(
            "ISSUEDIGEST_DATABASE_URL",
            engine.url.render_as_string(hide_password=False) + "?options=PRIVATE",
        )
    if kind in {"dispose", "pool"}:
        created = policy_cli.create_engine

        def create(*args, **kwargs):
            value = created(*args, **kwargs)
            dispose = value.dispose

            def cleanup():
                if kind == "pool":
                    value.pool.logger.error("PRIVATE %s", path)
                dispose()
                if kind == "dispose":
                    raise OSError("PRIVATE " + path)

            value.dispose = cleanup
            return value

        monkeypatch.setattr(policy_cli, "create_engine", create)
    if kind == "commit_unknown":

        def fail(*args, **kwargs):
            raise PolicyIntakeCommitUnknown()

        monkeypatch.setattr(PolicyIntakeRepository, "apply", fail)
    before = counts(engine)
    caplog.set_level(logging.DEBUG)
    if kind == "busy":
        from sqlalchemy import text

        with engine.connect() as conn, conn.begin():
            conn.execute(text("SELECT pg_advisory_xact_lock(104704,3)"))
            assert policy_cli.main(["intake", path, "--apply"]) == 0
        assert json.loads(capsys.readouterr().out)["outcome"] == "busy"
    else:
        assert policy_cli.main(["intake", path, "--apply"]) == 1
        logs = capsys.readouterr()
        assert logs.out == "" and logs.err == "Unable to complete policy operation\n"
    assert "PRIVATE" not in caplog.text and path not in caplog.text
    if kind in {"dispose", "pool"}:
        # Cleanup failure suppresses output after a completed commit; it cannot undo that commit.
        assert counts(engine)["policy_intake_receipts"] == 1
    else:
        assert before == counts(engine)


@pytest.mark.parametrize("rollback", [False, True])
def test_two_source_coordinator_atomically_persists_or_rolls_back(engine, policy_inputs, rollback):
    from issuedigest_storage import EvidenceRepository
    from issuedigest_storage.policy_intake import PolicyIntakeError
    from sqlalchemy import event

    a, data = api(), envelope(policy_inputs)
    capture = json.loads(policy_inputs[1])
    second = dict(capture["articles"][0])
    second.update(
        news_id="234567890", canonical_url=second["canonical_url"].replace("123456789", "234567890")
    )
    second["html"] = second["html"].replace("123456789", "234567890")
    capture["articles"].append(second)
    raw = json.dumps(capture, ensure_ascii=False).encode()
    source = json.loads(json.dumps(data["approval"]["sources"][0]))
    source.update(
        news_id=second["news_id"], article_sha256=sha256(second["html"].encode()).hexdigest()
    )
    source["license"]["evidence_url"] = second["canonical_url"]
    for name in ("document_id", "version_id", "raw_object_id", "representation_id", "snapshot_id"):
        source[name] = str(uuid4())
    source["citations"][0]["citation_id"] = str(uuid4())
    data["approval"]["sources"].append(source)
    data["approval"]["capture_sha256"] = sha256(raw).hexdigest()
    data["collection"]["news_ids"].append("234567890")
    journal(engine, data, raw)
    approved = a.parse_policy_intake_approval(json.dumps(data))
    before = counts(engine)
    inserted = []

    def fail_second(conn, cursor, statement, parameters, context, many):
        if statement.startswith("INSERT INTO policy_intake_receipts"):
            inserted.append(True)
            if len(inserted) == 2:
                raise RuntimeError("PRIVATE second receipt")

    if rollback:
        event.listen(engine, "before_cursor_execute", fail_second)
        try:
            with pytest.raises(PolicyIntakeError):
                a.intake_policy_capture(engine, approved, apply=True)
        finally:
            event.remove(engine, "before_cursor_execute", fail_second)
        assert inserted == [True, True]
        assert counts(engine) == before
    else:
        result = a.intake_policy_capture(engine, approved, apply=True)
        assert (result.sources, result.new_versions, result.receipts_created) == (2, 2, 2)
        assert counts(engine)["evidence_search_projections"] == 2
        for candidate in approved.approval.sources:
            saved = EvidenceRepository(engine).load(approved.workspace_id, candidate.snapshot_id)
            assert saved.citations[0].selector.quote == "😀한é"
            assert saved.representation.text == "앞 😀한é 뒤\n\n둘째 문단"
