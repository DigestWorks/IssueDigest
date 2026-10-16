"""Private offline publication review and explicit sanitized operator writes."""

import importlib
import json
import os
import socket
from pathlib import Path

import pytest
from issuedigest_domain.public_briefings import PublicBriefingPlan, plan_hash

from conftest import public_plan_data


def cli():
    from issuedigest_storage import __path__

    assert (Path(next(iter(__path__))) / "public_briefing_cli.py").is_file(), (
        "missing publication CLI"
    )
    return importlib.import_module("issuedigest_storage.public_briefing_cli")


@pytest.fixture
def public_plan(tmp_path):
    path = tmp_path / "private-review-secret.json"
    path.write_text(json.dumps(public_plan_data()), encoding="utf-8")
    path.chmod(0o600)
    return path


def test_offline_hash_covers_complete_normalized_plan_without_network(
    public_plan, monkeypatch, capsys
):
    c = cli()

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline publication contacted external service")

    monkeypatch.setattr(c, "create_engine", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", "secret-invalid-url")
    assert c.main([str(public_plan)]) == 0
    output = capsys.readouterr()
    expected = plan_hash(PublicBriefingPlan.model_validate_json(public_plan.read_bytes()))
    assert json.loads(output.out) == {"status": "validated", "plan_sha256": expected}
    assert output.err == ""
    assert "private-reviewer" not in output.out


@pytest.mark.parametrize("mode", ["--apply", "--withdraw"])
@pytest.mark.parametrize("digest", [None, "0" * 64])
def test_no_write_engine_without_explicit_exact_review_hash(
    public_plan, monkeypatch, capsys, mode, digest
):
    c = cli()
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("Unreviewed plan reached engine")

    monkeypatch.setattr(c, "create_engine", forbidden)
    args = [str(public_plan), mode]
    if digest:
        args += ["--reviewed-sha256", digest]
    assert c.main(args) == 1
    assert attempted == []
    assert capsys.readouterr().err == "Unable to operate public briefing\n"


@pytest.mark.parametrize(
    "kind",
    ["permissions", "symlink", "parent_symlink", "fifo", "duplicate", "nan", "extra", "oversized"],
)
def test_unsafe_files_and_json_never_echo_private_values(public_plan, tmp_path, capsys, kind):
    path = public_plan
    if kind == "permissions":
        path.chmod(0o640)
    elif kind == "symlink":
        path = tmp_path / "secret-link"
        path.symlink_to(public_plan)
    elif kind == "parent_symlink":
        parent = tmp_path / "secret-parent"
        parent.symlink_to(public_plan.parent)
        path = parent / public_plan.name
    elif kind == "fifo":
        path = tmp_path / "secret-fifo"
        os.mkfifo(path, 0o600)
    elif kind == "oversized":
        with path.open("wb") as file:
            file.truncate(8 * 1024 * 1024 + 1)
    elif kind == "duplicate":
        path.write_text('{"private-secret":1,"private-secret":2}')
    elif kind == "nan":
        path.write_text('{"private-secret":NaN}')
    else:
        data = json.loads(path.read_text())
        data["private-secret"] = "private-secret"
        path.write_text(json.dumps(data))
    assert cli().main([str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Unable to operate public briefing\n"


@pytest.mark.parametrize(
    "url",
    [
        None,
        "secret-url",
        "sqlite:///secret",
        "postgresql+psycopg://localhost/issuedigest_test?dbname=secret",
    ],
)
def test_invalid_urls_rejected_before_engine(public_plan, monkeypatch, capsys, url):
    c = cli()
    if url is None:
        monkeypatch.delenv("ISSUEDIGEST_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", url)
    calls = []
    monkeypatch.setattr(c, "create_engine", lambda *a, **kw: calls.append(True))
    assert c.main([str(public_plan), "--check-database"]) == 1
    assert calls == []
    assert capsys.readouterr().err == "Unable to operate public briefing\n"


def test_real_check_apply_repeat_withdraw_and_dispose(public_plan, engine, monkeypatch, capsys):
    from issuedigest_storage.public_briefings import PublicBriefingRepository
    from sqlalchemy import event

    c = cli()
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(c, "create_engine", lambda *args, **kwargs: engine)
    disposed = []
    event.listen(engine, "engine_disposed", lambda e: disposed.append(True))
    digest = plan_hash(PublicBriefingPlan.model_validate_json(public_plan.read_bytes()))
    for mode in ["--check-database", "--apply", "--apply", "--withdraw"]:
        args = [str(public_plan), mode]
        if mode != "--check-database":
            args += ["--reviewed-sha256", digest]
        assert c.main(args) == 0
        output = capsys.readouterr()
        assert "private-reviewer" not in output.out
        assert output.err == ""
    assert disposed == [True] * 4
    assert PublicBriefingRepository(engine).list_latest().items == ()


@pytest.mark.parametrize("fault", ["close", "reset"])
def test_pool_lifecycle_failure_is_sanitized(
    public_plan, engine, monkeypatch, capsys, caplog, fault
):
    from sqlalchemy.exc import SQLAlchemyError

    c = cli()
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(c, "create_engine", lambda *args, **kwargs: engine)
    method = "do_close" if fault == "close" else "do_rollback"
    original = getattr(engine.dialect, method)
    previous_logger = engine.pool.logger
    attempts = []

    def fail(connection):
        original(connection)
        attempts.append(True)
        raise SQLAlchemyError("PRIVATE-SECRET")

    monkeypatch.setattr(engine.dialect, method, fail)
    try:
        assert c.main([str(public_plan), "--check-database"]) == 1
    finally:
        monkeypatch.setattr(engine.dialect, method, original)
    assert attempts
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Unable to operate public briefing\n"
    assert not caplog.records
    assert engine.pool.logger is previous_logger


def test_arguments_never_echo_inputs(capsys):
    assert cli().main(["SECRET", "--unknown-secret"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Invalid public briefing arguments\n"
