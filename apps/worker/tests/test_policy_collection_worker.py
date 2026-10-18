"""Bounded collection against real synthetic PostgreSQL and synthetic source HTTP."""

import importlib
import importlib.util
import json
import logging
import os
import signal
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

import httpx2 as httpx
import pytest
from issuedigest_connectors import parse_policy_capture
from issuedigest_storage.policy_collection import PolicyCollectionRepository
from issuedigest_storage.policy_collection_schema import policy_collection_attempts as attempts
from sqlalchemy import event, func, select, text, update
from test_policy_import import NOTICE, URL, page

AT = datetime(2026, 10, 18, tzinfo=UTC)


def api():
    name = "issuedigest_worker.policy_collection"
    assert importlib.util.find_spec(name) is not None, "collection coordinator is missing"
    return importlib.import_module(name)


def job_data(**updates):
    return {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "collection_id": str(uuid4()),
        "news_ids": ["123456789"],
        "minimum_interval_seconds": 60,
        "max_age_seconds": 120,
        "max_attempts": 8,
        **updates,
    }


def job(**updates):
    return api().parse_policy_collection_job(json.dumps(job_data(**updates)))


class Clock:
    def __init__(self):
        self.now = AT

    def __call__(self):
        return self.now

    def advance(self, seconds=60):
        self.now += timedelta(seconds=seconds)


def source(clock, *, html=None, status=200, before=None):
    def handle(request):
        assert str(request.url) == URL
        if before:
            before()
        clock.advance(2)
        return httpx.Response(status, text=html or page(), headers={"Content-Type": "text/html"})

    return httpx.MockTransport(handle)


def forbidden(request):
    pytest.fail("HTTP before admission or baseline validation")


def rows(engine):
    with engine.connect() as conn:
        return [
            dict(row)
            for row in conn.execute(select(attempts).order_by(attempts.c.sequence)).mappings()
        ]


def test_first_repeat_change_exact_bytes_and_real_completion_clock(engine):
    a, cfg, clock = api(), job(), Clock()

    def committed():
        stored = rows(engine)
        assert stored[-1]["state"] == "running"
        assert stored[-1]["capture_bytes"] is None

    result = a.poll_policy_collection(
        engine, cfg, clock=clock, transport=source(clock, before=committed)
    )
    assert (result.outcome, result.new, result.changed, result.unchanged) == ("succeeded", 1, 0, 0)
    stored = rows(engine)
    raw = stored[0]["capture_bytes"]
    assert stored[0]["finished_at"] == AT + timedelta(seconds=2)
    assert parse_policy_capture(raw).collected_at == AT
    assert sha256(raw).hexdigest() == stored[0]["capture_sha256"]
    assert json.loads(stored[0]["report_bytes"])["sources"][0]["status"] == "new"
    clock.advance()
    second = a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    assert (second.outcome, second.new, second.changed, second.unchanged) == ("succeeded", 0, 0, 1)
    clock.advance()
    third = a.poll_policy_collection(
        engine,
        cfg,
        clock=clock,
        transport=source(clock, html=page().replace("둘째 문단", "변경 본문")),
    )
    assert (third.outcome, third.changed) == ("succeeded", 1)
    assert rows(engine)[0] == stored[0]
    assert set(result.model_dump()) <= {
        "schema_version",
        "outcome",
        "failure_code",
        "new",
        "changed",
        "unchanged",
        "started_at",
        "finished_at",
    }


@pytest.mark.parametrize("stage", ["capture_failed", "validation_failed"])
def test_failure_preserves_last_success_and_status_separates_failure(engine, stage):
    a, cfg, clock = api(), job(), Clock()
    a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    original = rows(engine)[0]
    clock.advance()
    transport = (
        source(clock, status=503)
        if stage == "capture_failed"
        else source(clock, html=page().replace(NOTICE, "조건 미확인"))
    )
    result = a.poll_policy_collection(engine, cfg, clock=clock, transport=transport)
    assert (result.outcome, result.failure_code) == ("failed", stage)
    assert rows(engine)[0] == original
    status = a.policy_collection_status(engine, cfg, now=clock())
    assert status.latest.state == "failed"
    assert status.last_success.state == "succeeded"
    assert status.latest.failure_code == stage
    assert status.age_seconds == 62 and not status.stale
    assert "attempt_id" not in status.model_dump_json() and str(cfg.collection_id) not in repr(
        status
    )


def test_busy_interval_limit_and_read_only_empty_status_have_zero_http(engine):
    a, cfg, clock = api(), job(max_attempts=1), Clock()
    empty = a.policy_collection_status(engine, cfg, now=clock())
    assert empty.latest is None and empty.last_success is None and empty.stale
    with engine.connect() as conn:
        assert conn.scalar(select(func.count()).select_from(attempts)) == 0
    with PolicyCollectionRepository(engine).lease(cfg):
        busy = a.poll_policy_collection(
            engine, cfg, clock=clock, transport=httpx.MockTransport(forbidden)
        )
    assert busy.outcome == "busy"
    a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    assert (
        a.poll_policy_collection(
            engine, cfg, clock=clock, transport=httpx.MockTransport(forbidden)
        ).outcome
        == "not_due"
    )
    clock.advance()
    assert (
        a.poll_policy_collection(
            engine, cfg, clock=clock, transport=httpx.MockTransport(forbidden)
        ).outcome
        == "attempt_limit"
    )
    assert len(rows(engine)) == 1
    clock.advance(121)
    assert a.policy_collection_status(engine, cfg, now=clock()).stale


def test_abandoned_running_recovers_before_next_capture(engine):
    a, cfg, clock = api(), job(), Clock()
    with PolicyCollectionRepository(engine).lease(cfg) as session:
        session.start(now=clock())
    status = a.policy_collection_status(engine, cfg, now=clock())
    assert status.latest.state == "running" and status.last_success is None
    clock.advance()
    assert (
        a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock)).outcome
        == "succeeded"
    )
    assert rows(engine)[0]["failure_code"] == "interrupted"


@pytest.mark.parametrize(
    "corruption",
    [
        "scope",
        "old_time",
        "report_hash",
        "report_time",
        "report_fingerprint",
        "report_identity",
        "report_status",
        "duplicate_report_key",
        "ineligible",
    ],
)
def test_forged_baseline_rejected_before_http(engine, corruption):
    a, cfg, clock = api(), job(), Clock()
    a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    original = rows(engine)[0]
    capture, report = json.loads(original["capture_bytes"]), json.loads(original["report_bytes"])
    if corruption == "scope":
        capture["articles"][0]["news_id"] = "234567890"
        capture["articles"][0]["canonical_url"] = URL.replace("123456789", "234567890")
        capture["articles"][0]["html"] = page().replace("123456789", "234567890")
    elif corruption == "old_time":
        capture["collected_at"] = "2026-10-17T00:00:00Z"
    elif corruption == "ineligible":
        capture["articles"][0]["html"] = page().replace(NOTICE, "미확인")
    elif corruption == "report_hash":
        report["after_capture_sha256"] = "f" * 64
    elif corruption == "report_time":
        report["after_collected_at"] = "2026-10-17T00:00:00Z"
    elif corruption == "report_fingerprint":
        report["sources"][0]["after_fingerprint"] = "f" * 64
    elif corruption == "report_identity":
        report["sources"][0]["source_id"] = "234567890"
    elif corruption == "report_status":
        report["sources"][0]["status"] = "unchanged"
    raw = json.dumps(capture, ensure_ascii=False).encode()
    report_raw = json.dumps(report).encode()
    if corruption == "duplicate_report_key":
        report_raw = b'{"schema_version":1,' + report_raw[1:]
    with engine.begin() as conn:
        conn.execute(
            update(attempts)
            .where(attempts.c.attempt_id == original["attempt_id"])
            .values(
                capture_bytes=raw,
                capture_sha256=sha256(raw).hexdigest(),
                report_bytes=report_raw,
                report_sha256=sha256(report_raw).hexdigest(),
            )
        )
    clock.advance()
    result = a.poll_policy_collection(
        engine, cfg, clock=clock, transport=httpx.MockTransport(forbidden)
    )
    assert (result.outcome, result.failure_code) == ("failed", "validation_failed")
    assert rows(engine)[0]["state"] == "succeeded"


@pytest.mark.parametrize(
    "updates",
    [
        {"schema_version": True},
        {"minimum_interval_seconds": True},
        {"max_age_seconds": True},
        {"max_attempts": True},
        {"max_attempts": 4097},
        {"minimum_interval_seconds": 59},
        {"max_age_seconds": 59},
        {"news_ids": ["１２３４５６７８９"]},
        {"news_ids": ["123456789", "123456789"]},
        {"news_ids": "123456789"},
        {"collection_id": "00000000-0000-1000-8000-000000000000"},
        {"extra": "PRIVATE"},
    ],
)
def test_strict_job_rejects_invalid_scope_and_bounds(updates):
    with pytest.raises(ValueError, match="Unable to validate policy collection job"):
        api().parse_policy_collection_job(json.dumps(job_data(**updates)))


@pytest.mark.parametrize(
    "raw", [b"", b"\xff", b" " * 8193, b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}']
)
def test_job_rejects_ambiguous_or_oversize_json(raw):
    with pytest.raises(ValueError, match="Unable to validate policy collection job"):
        api().parse_policy_collection_job(raw)


def test_job_normalizes_article_set():
    cfg = job(news_ids=["234567890", "123456789"])
    assert cfg.news_ids == ("123456789", "234567890")


@pytest.mark.parametrize("boundary", ["start", "success"])
def test_commit_unknown_does_not_retry_or_overwrite_committed_reality(engine, boundary):
    from issuedigest_storage.policy_collection import PolicyCollectionCommitUnknown

    a, cfg, clock = api(), job(), Clock()
    seen = []
    original = engine.dialect.do_commit

    def commit(connection):
        original(connection)
        seen.append(True)
        # Lease lock and backend identity commit before the admitted start commit.
        if len(seen) == (3 if boundary == "start" else 4):
            raise RuntimeError("PRIVATE commit acknowledgment")

    engine.dialect.do_commit = commit
    try:
        with pytest.raises(PolicyCollectionCommitUnknown):
            a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    finally:
        engine.dialect.do_commit = original
    stored = rows(engine)
    assert len(stored) == 1
    assert stored[0]["state"] == ("running" if boundary == "start" else "succeeded")
    assert stored[0]["failure_code"] is None
    assert clock() == AT + timedelta(seconds=0 if boundary == "start" else 2)


def test_connection_loss_during_capture_stays_running_and_does_not_retry(engine):
    from issuedigest_storage.policy_collection import PolicyCollectionError

    a, cfg, clock = api(), job(), Clock()

    def kill_backend():
        with engine.connect() as conn:
            pid = conn.scalar(
                text(
                    "SELECT pid FROM pg_locks WHERE locktype='advisory' "
                    "AND classid=104704 AND objid=2"
                )
            )
            assert pid is not None
            conn.execute(text("SELECT pg_terminate_backend(:pid)"), {"pid": pid})
            conn.commit()

    with pytest.raises(PolicyCollectionError):
        a.poll_policy_collection(
            engine, cfg, clock=clock, transport=source(clock, before=kill_backend)
        )
    assert rows(engine)[0]["state"] == "running"
    assert clock() == AT + timedelta(seconds=2)


def test_status_uses_read_only_transactions_and_creates_no_channels(engine, monkeypatch):
    a, cfg = api(), job()
    monkeypatch.setattr(a, "capture_policy", lambda *args, **kwargs: pytest.fail("source HTTP"))
    transactions = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if "SELECT policy_collection_channels" in statement:
            transactions.append(conn.exec_driver_sql("SHOW transaction_read_only").scalar())

    event.listen(engine, "before_cursor_execute", observe)
    try:
        result = a.policy_collection_status(engine, cfg, now=AT)
    finally:
        event.remove(engine, "before_cursor_execute", observe)
    assert result.attempt_count == 0 and transactions == ["on"]
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM policy_collection_channels")) == 0


def test_live_status_observes_poll_committed_before_its_snapshot(engine, monkeypatch):
    storage_api = importlib.import_module("issuedigest_storage.policy_collection")
    a, cfg, clock = api(), job(), Clock()
    a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    clock.advance()
    monkeypatch.setattr(a, "_now", clock)
    monkeypatch.setattr(storage_api, "_now", clock)
    reader_driver = None
    writer_drivers = []
    pending = True

    def commit_poll_before_snapshot(conn, cursor, statement, parameters, context, many):
        nonlocal pending, reader_driver
        if pending and conn.get_execution_options().get("postgresql_readonly"):
            pending = False
            reader_driver = conn.connection.driver_connection
            clock.advance(1)
            result = a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
            assert result.outcome == "succeeded"
        elif "INSERT INTO policy_collection_attempts" in statement:
            writer_drivers.append(conn.connection.driver_connection)

    event.listen(engine, "before_cursor_execute", commit_poll_before_snapshot)
    try:
        result = a.policy_collection_status(engine, cfg)
    finally:
        event.remove(engine, "before_cursor_execute", commit_poll_before_snapshot)
    assert writer_drivers and all(driver is not reader_driver for driver in writer_drivers)
    assert result.attempt_count == 2
    assert result.latest == result.last_success
    assert result.latest.sequence == 2 and result.latest.state == "succeeded"
    assert result.latest.started_at == AT + timedelta(seconds=63)
    assert result.latest.finished_at == AT + timedelta(seconds=65)
    assert result.age_seconds == 0 and not result.stale
    assert len(rows(engine)) == 2
    with pytest.raises(storage_api.PolicyCollectionError):
        a.policy_collection_status(engine, cfg, now=AT + timedelta(seconds=64))


def test_sigkill_running_is_recovered(engine):
    a, cfg, clock = api(), job(), Clock()
    code = """
import json, os, sys, time
from datetime import datetime
from sqlalchemy import create_engine
from issuedigest_worker.policy_collection import parse_policy_collection_job
from issuedigest_storage.policy_collection import PolicyCollectionRepository
engine = create_engine(os.environ['SYNTHETIC_COLLECTION_URL'])
config = parse_policy_collection_job(sys.stdin.buffer.readline())
with PolicyCollectionRepository(engine).lease(config) as session:
    session.start(now=datetime.fromisoformat('2026-10-18T00:00:00+00:00'))
    print('running', flush=True)
    time.sleep(30)
"""
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "SYNTHETIC_COLLECTION_URL": engine.url.render_as_string(hide_password=False),
        },
        text=True,
    )
    try:
        proc.stdin.write(cfg.model_dump_json() + "\n")
        proc.stdin.flush()
        assert proc.stdout.readline().strip() == "running"
        proc.send_signal(signal.SIGKILL)
        proc.wait(timeout=5)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)
        proc.stdin.close()
        proc.stdout.close()
        proc.stderr.close()
    assert rows(engine)[0]["state"] == "running"
    clock.advance()
    assert (
        a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock)).outcome
        == "succeeded"
    )
    assert rows(engine)[0]["failure_code"] == "interrupted"


def private_job(tmp_path, data=None, mode=0o600):
    path = tmp_path / "private-collection-job.json"
    path.write_text(json.dumps(job_data() if data is None else data))
    path.chmod(mode)
    return str(path)


def test_cli_status_and_poll_safe_metadata_after_disposal(
    engine, tmp_path, monkeypatch, capsys, caplog
):
    from issuedigest_worker import policy_cli

    path = private_job(tmp_path)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(api(), "_now", lambda: AT)
    disposed = []
    event.listen(engine, "engine_disposed", lambda engine: disposed.append(True))
    monkeypatch.setattr(policy_cli, "create_engine", lambda *args, **kwargs: engine, raising=False)
    caplog.set_level(logging.DEBUG)
    assert policy_cli.main(["status", path]) == 0
    result = capsys.readouterr()
    assert disposed == [True] and result.err == ""
    assert json.loads(result.out)["attempt_count"] == 0
    assert path not in result.out and "123456789" not in result.out and caplog.text == ""


@pytest.mark.parametrize(
    "kind", ["mode", "relative", "symlink", "oversize", "missing", "wrong_database", "query"]
)
def test_cli_rejects_private_file_or_database_before_http(
    engine, tmp_path, monkeypatch, capsys, kind
):
    from issuedigest_worker import policy_cli

    path = private_job(tmp_path)
    url = engine.url.render_as_string(hide_password=False)
    if kind == "mode":
        os.chmod(path, 0o644)
    elif kind == "relative":
        path = "private-collection-job.json"
    elif kind == "symlink":
        link = tmp_path / "link"
        link.symlink_to(path)
        path = str(link)
    elif kind == "oversize":
        with open(path, "wb") as file:
            file.write(b" " * 8193)
    elif kind == "missing":
        os.unlink(path)
    elif kind == "wrong_database":
        url = url.replace("/issuedigest_test", "/PRIVATE_other_database")
    else:
        url += "?options=PRIVATE"
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", url)
    monkeypatch.setattr(
        api(), "capture_policy", lambda *args, **kwargs: pytest.fail("HTTP on invalid input")
    )
    assert policy_cli.main(["poll", path]) == 1
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "Unable to complete policy operation\n"


def test_cli_failed_poll_nonzero_and_denials_success(engine, tmp_path, monkeypatch, capsys):
    from issuedigest_worker import policy_cli

    cfg = job(max_attempts=1)
    path = private_job(tmp_path, cfg.model_dump(mode="json"))
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(policy_cli, "create_engine", lambda *args, **kwargs: engine, raising=False)
    clock = Clock()
    real_poll = api().poll_policy_collection
    monkeypatch.setattr(
        policy_cli,
        "poll_policy_collection",
        lambda engine, config: real_poll(
            engine, config, clock=clock, transport=source(clock, status=503)
        ),
        raising=False,
    )
    assert policy_cli.main(["poll", path]) == 1
    assert json.loads(capsys.readouterr().out)["outcome"] == "failed"
    assert policy_cli.main(["poll", path]) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "not_due"
    clock.advance()
    assert policy_cli.main(["poll", path]) == 0
    assert json.loads(capsys.readouterr().out)["outcome"] == "attempt_limit"


def test_cli_disposal_error_suppresses_output_and_private_logs(
    engine, tmp_path, monkeypatch, capsys, caplog
):
    from issuedigest_worker import policy_cli

    path = private_job(tmp_path)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(policy_cli, "create_engine", lambda *args, **kwargs: engine, raising=False)
    real_dispose = engine.dispose

    def dispose():
        engine.pool.logger.error("PRIVATE DSN URL identity")
        real_dispose()

    monkeypatch.setattr(engine, "dispose", dispose)
    assert policy_cli.main(["status", path]) == 1
    output = capsys.readouterr()
    assert output.out == "" and output.err == "Unable to complete policy operation\n"
    assert caplog.text == ""


def test_request_clock_cannot_precede_committed_start(engine):
    a, cfg = api(), job()
    ticks = iter((AT, AT - timedelta(seconds=1), AT + timedelta(seconds=2)))
    result = a.poll_policy_collection(
        engine, cfg, clock=lambda: next(ticks), transport=httpx.MockTransport(forbidden)
    )
    assert (result.outcome, result.failure_code) == ("failed", "validation_failed")
    assert rows(engine)[0]["capture_bytes"] is None


def test_forged_equal_before_time_cannot_validate_baseline(engine):
    a, cfg, clock = api(), job(), Clock()
    a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    original = rows(engine)[0]
    report = json.loads(original["report_bytes"])
    report["before_capture_sha256"] = "f" * 64
    report["before_collected_at"] = report["after_collected_at"]
    report["sources"][0]["status"] = "unchanged"
    report["sources"][0]["before_fingerprint"] = report["sources"][0]["after_fingerprint"]
    raw = json.dumps(report).encode()
    with engine.begin() as conn:
        conn.execute(
            update(attempts).values(report_bytes=raw, report_sha256=sha256(raw).hexdigest())
        )
    clock.advance()
    result = a.poll_policy_collection(
        engine, cfg, clock=clock, transport=httpx.MockTransport(forbidden)
    )
    assert result.failure_code == "validation_failed"


def test_two_explicit_articles_compare_independently_without_discovery(engine):
    a, cfg, clock = api(), job(news_ids=["234567890", "123456789"]), Clock()

    def response(request):
        identity = request.url.params["newsId"]
        assert identity in {"123456789", "234567890"}
        html = page().replace("123456789", identity)
        if clock() > AT + timedelta(seconds=60) and identity == "234567890":
            html = html.replace("둘째 문단", "변경 본문")
        clock.advance(1)
        return httpx.Response(200, text=html, headers={"Content-Type": "text/html"})

    first = a.poll_policy_collection(
        engine, cfg, clock=clock, transport=httpx.MockTransport(response)
    )
    assert first.new == 2 and clock() == AT + timedelta(seconds=2)
    clock.advance()
    second = a.poll_policy_collection(
        engine, cfg, clock=clock, transport=httpx.MockTransport(response)
    )
    assert (second.changed, second.unchanged) == (1, 1)
    assert clock() == AT + timedelta(seconds=64)


def test_storage_hash_corruption_does_not_become_validation_terminal(engine):
    from issuedigest_storage.policy_collection import PolicyCollectionError

    a, cfg, clock = api(), job(), Clock()
    a.poll_policy_collection(engine, cfg, clock=clock, transport=source(clock))
    with engine.begin() as conn:
        conn.execute(update(attempts).values(capture_sha256="f" * 64))
    clock.advance()
    with pytest.raises(PolicyCollectionError):
        a.poll_policy_collection(engine, cfg, clock=clock, transport=httpx.MockTransport(forbidden))
    assert [row["state"] for row in rows(engine)] == ["succeeded", "running"]


def test_cli_success_poll_discards_private_transport_logs(
    engine, tmp_path, monkeypatch, capsys, caplog
):
    from issuedigest_worker import policy_cli

    path = private_job(tmp_path)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(policy_cli, "create_engine", lambda *args, **kwargs: engine)
    clock = Clock()
    real_poll = api().poll_policy_collection

    def private_log():
        logging.getLogger("httpx2").warning("PRIVATE article URL body account DSN")
        logging.getLogger("httpcore2.connection").debug("PRIVATE credentials")

    monkeypatch.setattr(
        policy_cli,
        "poll_policy_collection",
        lambda engine, cfg: real_poll(
            engine, cfg, clock=clock, transport=source(clock, before=private_log)
        ),
    )
    caplog.set_level(logging.DEBUG)
    assert policy_cli.main(["poll", path]) == 0
    output = capsys.readouterr()
    summary = json.loads(output.out)
    assert summary["outcome"] == "succeeded" and summary["new"] == 1
    assert set(summary) == {
        "schema_version",
        "outcome",
        "failure_code",
        "new",
        "changed",
        "unchanged",
        "started_at",
        "finished_at",
    }
    assert output.err == "" and caplog.text == ""


def test_completion_clock_cannot_precede_capture_request(engine):
    a, cfg = api(), job()
    ticks = iter((AT, AT + timedelta(seconds=5), AT + timedelta(seconds=2)))
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text=page(), headers={"Content-Type": "text/html"})
    )
    result = a.poll_policy_collection(engine, cfg, clock=lambda: next(ticks), transport=transport)
    assert (result.outcome, result.failure_code) == ("failed", "validation_failed")
    assert rows(engine)[0]["capture_bytes"] is None
