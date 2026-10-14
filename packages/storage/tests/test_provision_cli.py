"""Private synthetic files and silent offline/operator CLI boundaries."""

import importlib
import json
import os
import socket
from pathlib import Path

import pytest
from test_provisioning import plan_data


def cli():
    from issuedigest_storage import __path__

    assert (Path(next(iter(__path__))) / "provision_cli.py").is_file(), "missing operator CLI"
    return importlib.import_module("issuedigest_storage.provision_cli")


@pytest.fixture
def private_plan(tmp_path):
    path = tmp_path / "private-secret-path.json"
    path.write_text(json.dumps(plan_data()), encoding="utf-8")
    path.chmod(0o600)
    return path


def test_default_offline_has_no_database_network_or_file_writes(private_plan, monkeypatch, capsys):
    c = cli()

    def forbidden(*args, **kwargs):
        raise AssertionError("offline operation attempted external side effects")

    monkeypatch.setattr(c, "create_engine", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", "secret-invalid-url")
    before = private_plan.read_bytes()
    old_open = os.open

    def only_reads(path, flags, *args, **kwargs):
        assert not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)
        return old_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", only_reads)
    assert c.main([str(private_plan)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {
        "schema_version": 1,
        "status": "validated",
        "invites": 1,
        "snapshots": 1,
    }
    assert output.err == ""
    assert private_plan.read_bytes() == before


@pytest.mark.parametrize(
    "kind",
    [
        "relative",
        "missing",
        "permissions",
        "group-write",
        "owner",
        "symlink",
        "directory",
        "fifo",
        "oversized",
        "utf8",
        "duplicate",
        "nan",
        "invalid",
    ],
)
def test_private_file_guard_reports_fixed_errors(private_plan, tmp_path, monkeypatch, capsys, kind):
    c = cli()
    path = private_plan
    if kind == "relative":
        path = Path("secret-relative.json")
    elif kind == "missing":
        path = tmp_path / "secret-missing.json"
    elif kind == "permissions":
        path.chmod(0o640)
    elif kind == "group-write":
        path.chmod(0o620)
    elif kind == "owner":
        monkeypatch.setattr(os, "geteuid", lambda: os.stat(private_plan).st_uid + 1)
    elif kind == "symlink":
        path = tmp_path / "secret-link.json"
        path.symlink_to(private_plan)
    elif kind == "directory":
        path = tmp_path
    elif kind == "fifo":
        path = tmp_path / "secret-fifo.json"
        os.mkfifo(path, 0o600)
    elif kind == "oversized":
        with path.open("wb") as file:
            file.truncate(8 * 1024 * 1024 + 1)
    elif kind == "utf8":
        path.write_bytes(b"\xff")
    elif kind == "duplicate":
        path.write_text('{"secret":1,"secret":2}')
    elif kind == "nan":
        path.write_text('{"secret":NaN}')
    else:
        path.write_text('{"email":"private-email-secret@example.test"}')
    assert c.main([str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Unable to provision workspace\n"


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["secret", "--bad-secret"],
        ["secret", "--apply", "--check-database"],
        ["secret", "extra-private-path"],
        ["--apply"],
    ],
)
def test_argument_errors_never_echo_input(args, capsys):
    assert cli().main(args) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Invalid provisioning arguments\n"


@pytest.mark.parametrize("mode", ["--apply", "--check-database"])
@pytest.mark.parametrize(
    "configuration",
    [
        None,
        "",
        "secret-url",
        "sqlite:///secret",
        "postgresql+psycopg://localhost/other",
        "postgresql+psycopg://localhost/issuedigest_test?dbname=secret",
    ],
)
def test_invalid_environment_rejected_before_engine(
    private_plan, monkeypatch, capsys, mode, configuration
):
    c = cli()
    if configuration is None:
        monkeypatch.delenv("ISSUEDIGEST_DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", configuration)

    def forbidden(*args, **kwargs):
        raise AssertionError("invalid environment reached engine creation")

    monkeypatch.setattr(c, "create_engine", forbidden)
    assert c.main([str(private_plan), mode]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Unable to provision workspace\n"


@pytest.mark.parametrize("mode", ["--apply", "--check-database"])
@pytest.mark.parametrize("failure", [False, True])
def test_database_cli_disposes_real_engine_on_success_and_failure(
    private_plan, engine, monkeypatch, capsys, mode, failure
):
    from sqlalchemy import event

    c = cli()
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(c, "create_engine", lambda *args, **kwargs: engine)
    disposed = []
    event.listen(engine, "engine_disposed", lambda e: disposed.append(True))
    if failure:

        def fail(*args, **kwargs):
            raise RuntimeError("secret-input-value@example.test")

        monkeypatch.setattr(engine, "connect", fail)
    assert c.main([str(private_plan), mode]) == (1 if failure else 0)
    output = capsys.readouterr()
    assert disposed == [True]
    assert "private" not in output.out + output.err
    assert "secret" not in output.out + output.err
    if failure:
        assert output.out == ""
        assert output.err == "Unable to provision workspace\n"
    else:
        assert output.err == ""
        assert json.loads(output.out)["status"] == (
            "applied" if mode == "--apply" else "database_checked"
        )


def test_dispose_failure_does_not_report_success(private_plan, engine, monkeypatch, capsys):
    c = cli()
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setattr(c, "create_engine", lambda *args, **kwargs: engine)

    def fail():
        raise RuntimeError("secret-dispose-error")

    monkeypatch.setattr(engine, "dispose", fail)
    assert c.main([str(private_plan), "--check-database"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Unable to provision workspace\n"


def test_symlink_parent_is_rejected(private_plan, tmp_path, capsys):
    link = tmp_path / "secret-parent"
    link.symlink_to(private_plan.parent, target_is_directory=True)
    assert cli().main([str(link / private_plan.name)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Unable to provision workspace\n"


def test_real_module_entrypoint_offline(private_plan):
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, "-m", "issuedigest_storage.provision_cli", str(private_plan)],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "ISSUEDIGEST_DATABASE_URL": "secret-invalid-url"},
    )
    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout) == {
        "schema_version": 1,
        "status": "validated",
        "invites": 1,
        "snapshots": 1,
    }


def test_partial_apply_flag_is_not_accepted(private_plan, capsys):
    assert cli().main([str(private_plan), "--app"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "Invalid provisioning arguments\n"


def test_exact_size_limit_accepts_valid_private_plan(private_plan, capsys):
    raw = private_plan.read_bytes()
    private_plan.write_bytes(raw + b" " * (8 * 1024 * 1024 - len(raw)))
    assert cli().main([str(private_plan)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out)["status"] == "validated"
    assert output.err == ""
