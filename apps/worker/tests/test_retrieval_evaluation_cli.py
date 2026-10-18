"""Private CLI publication and aggregate-only output, with a leased synthetic PG."""

import importlib
import json
import os
import subprocess
import sys
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_storage import EvidenceRepository
from sqlalchemy import event, text

from conftest import bundle_data


def api():
    return importlib.import_module("issuedigest_worker.retrieval_evaluation_cli")


def files(tmp_path, engine):
    tmp_path.chmod(0o700)
    bundle = EvidenceBundle.model_validate(bundle_data())
    repo = EvidenceRepository(engine)
    identity = uuid4()
    repo.save(identity, bundle)
    repo.rebuild_projection(bundle.document.workspace_id, identity)
    data = {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": str(bundle.document.workspace_id),
        "corpus_snapshot_ids": [str(identity)],
        "cases": [
            {
                "case_id": "private_case",
                "question": "한",
                "expected_families": [[str(identity)]],
                "no_match": False,
            }
        ],
    }
    job = tmp_path / "job.json"
    job.write_text(json.dumps(data), encoding="utf-8")
    job.chmod(0o600)
    return job, tmp_path / "report.json", identity


def test_real_cli_aggregate_output_private_atomic_report(
    tmp_path, engine, database_url, monkeypatch, capsys
):
    job, report, identity = files(tmp_path, engine)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", database_url)
    assert api().main([str(job), "--output", str(report)]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    summary = json.loads(output.out)
    assert summary["cases"] == 1 and summary["hit_at_1"] == 1
    assert str(identity) not in output.out and "private_case" not in output.out
    saved = json.loads(report.read_bytes())
    assert saved["cases"][0]["ranked_snapshot_ids"] == [str(identity)]
    assert saved["job"]["cases"][0]["question"] == "한"
    assert report.stat().st_mode & 0o777 == 0o600
    assert api().main([str(job), "--output", str(report)]) == 1
    assert (
        report.read_bytes() == json.dumps(saved, separators=(",", ":"), ensure_ascii=False).encode()
    )
    assert capsys.readouterr().err == "Unable to evaluate retrieval\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["job.json", "report.json"]


@pytest.mark.parametrize(
    "failure",
    [
        "bad_job",
        "wrong_database",
        "missing_projection",
        "db_error",
        "pool_error",
        "input_mode",
        "parent_mode",
    ],
)
def test_failures_leave_no_partial_output_or_private_diagnostics(
    tmp_path, engine, database_url, monkeypatch, capsys, failure
):
    job, report, identity = files(tmp_path, engine)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", database_url)
    if failure == "bad_job":
        job.write_bytes(b'{"private":"private body","private":2}')
    elif failure == "wrong_database":
        monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", database_url + "?private=secret")
    elif failure == "missing_projection":
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM evidence_search_projections"))
    elif failure == "input_mode":
        job.chmod(0o644)
    elif failure == "parent_mode":
        tmp_path.chmod(0o755)
    elif failure == "db_error":
        real_create = api().create_engine

        def create(*args, **kwargs):
            created = real_create(*args, **kwargs)

            def fail(conn, cursor, statement, parameters, context, executemany):
                cursor.execute("DO $$ BEGIN RAISE EXCEPTION 'private database body'; END $$")

            event.listen(created, "before_cursor_execute", fail)
            return created

        monkeypatch.setattr(api(), "create_engine", create)
    elif failure == "pool_error":
        real_create = api().create_engine

        def create(*args, **kwargs):
            created = real_create(*args, **kwargs)

            def fail_close(connection, record):
                raise RuntimeError("private body in lifecycle failure")

            event.listen(created.pool, "close", fail_close)
            return created

        monkeypatch.setattr(api(), "create_engine", create)
    assert api().main([str(job), "--output", str(report)]) == 1
    assert not report.exists()
    output = capsys.readouterr()
    assert output.out == "" and output.err == "Unable to evaluate retrieval\n"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["job.json"]


def test_help_and_argument_failures_do_not_connect_or_echo_values(capsys, monkeypatch):
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", "private invalid URL")
    assert api().main(["--private-secret"]) == 2
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == "Invalid retrieval evaluation arguments\n"
    completed = subprocess.run(
        [sys.executable, "-m", "issuedigest_worker.retrieval_evaluation_cli", "--help"],
        capture_output=True,
        text=True,
        env={**os.environ, "ISSUEDIGEST_DATABASE_URL": "invalid"},
    )
    assert completed.returncode == 0 and "--output" in completed.stdout
    assert completed.stderr == ""
