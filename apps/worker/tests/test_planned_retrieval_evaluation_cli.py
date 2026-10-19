"""Private comparison CLI reports publish only after successful complete lifecycle."""

import importlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import event, text
from test_retrieval_evaluation_cli import files


def api():
    name = "issuedigest_worker.planned_retrieval_evaluation_cli"
    assert importlib.util.find_spec(name) is not None, "planned comparison CLI is missing"
    return importlib.import_module(name)


def planned_files(tmp_path, engine):
    job, report, identity = files(tmp_path, engine)
    baseline = json.loads(job.read_bytes())
    job.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "baseline": baseline,
                "plans": [
                    {
                        "case_id": "private_case",
                        "origin": "recorded_planner_output",
                        "queries": ["private_term"],
                        "irrelevant_snapshot_ids": [],
                    }
                ],
            }
        )
    )
    return job, report, identity


@pytest.mark.parametrize("mode", [0o400, 0o600])
def test_private_report_aggregate_output_and_exclusive_publication(
    tmp_path, engine, database_url, monkeypatch, capsys, mode
):
    job, report, identity = planned_files(tmp_path, engine)
    job.chmod(mode)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", database_url)
    assert api().main([str(job), "--output", str(report)]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    aggregate = json.loads(output.out)
    assert set(aggregate) == {"baseline", "planned", "origin_case_counts"}
    assert aggregate["origin_case_counts"] == {"recorded_planner_output": 1}
    assert aggregate["baseline"]["hit_at_1"] == 1
    assert aggregate["planned"]["relevant_count"] == 1
    for private in ["private_case", "private_term", str(identity), "한"]:
        assert private not in output.out
    saved = report.read_bytes()
    result = json.loads(saved)
    assert result["cases"][0]["planned"]["ranked_snapshot_ids"] == [str(identity)]
    assert result["job"]["plans"][0]["queries"] == ["private_term"]
    assert report.stat().st_mode & 0o777 == 0o600
    assert api().main([str(job), "--output", str(report)]) == 1
    assert report.read_bytes() == saved
    assert capsys.readouterr().err == "Unable to evaluate planned retrieval\n"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["job.json", "report.json"]


@pytest.mark.parametrize(
    "failure",
    [
        "bad_job",
        "wrong_database",
        "missing_projection",
        "partial_case",
        "db_error",
        "pool_error",
        "dispose_error",
        "transaction_close",
        "connection_close",
        "input_mode",
        "parent_mode",
        "input_symlink",
        "output_symlink",
        "parent_symlink",
    ],
)
def test_failures_leave_no_report_and_only_fixed_error(
    tmp_path, engine, database_url, monkeypatch, capsys, failure
):
    job, report, identity = planned_files(tmp_path, engine)
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", database_url)
    arguments = [str(job), "--output", str(report)]
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
    elif failure == "input_symlink":
        link = tmp_path / "link.json"
        link.symlink_to(job)
        arguments[0] = str(link)
    elif failure == "output_symlink":
        report.symlink_to(job)
    elif failure == "parent_symlink":
        link = tmp_path / "link"
        link.symlink_to(tmp_path, target_is_directory=True)
        arguments[2] = str(link / "report.json")
    elif failure == "partial_case":
        data = json.loads(job.read_bytes())
        data["baseline"]["cases"].append(
            {**data["baseline"]["cases"][0], "case_id": "second_private"}
        )
        data["plans"].append({**data["plans"][0], "case_id": "second_private"})
        job.write_text(json.dumps(data))
        module = importlib.import_module("issuedigest_storage.planned_retrieval_evaluation")
        original = module.research_search.search_candidates

        def second_fails(conn, row, queries, parent):
            nonlocal original
            if original is None:
                raise ValueError("private second case failure")
            result = original(conn, row, queries, parent)
            original = None
            return result

        monkeypatch.setattr(module.research_search, "search_candidates", second_fails)
    else:
        real_create = api().create_engine

        def create(*args, **kwargs):
            created = real_create(*args, **kwargs)

            def fail(*args, **kwargs):
                raise RuntimeError("private body in database lifecycle failure")

            if failure == "pool_error":
                event.listen(created.pool, "close", fail)
            elif failure == "db_error":
                event.listen(created, "before_cursor_execute", fail)
            elif failure == "transaction_close":
                event.listen(created, "commit", fail)
            elif failure == "connection_close":
                event.listen(created.pool, "checkin", fail)
            elif failure == "dispose_error":
                real_dispose = created.dispose

                def dispose():
                    real_dispose()
                    fail()

                monkeypatch.setattr(created, "dispose", dispose)
            return created

        monkeypatch.setattr(api(), "create_engine", create)
    assert api().main(arguments) == 1
    assert not report.exists() or report.is_symlink()
    if report.is_symlink():
        assert report.read_bytes() == job.read_bytes()
    output = capsys.readouterr()
    assert output.out == "" and output.err == "Unable to evaluate planned retrieval\n"
    assert not any(p.name.startswith(".hwpx-") for p in tmp_path.iterdir())


def test_bad_arguments_and_installed_entrypoint_do_not_connect(capsys, monkeypatch):
    monkeypatch.setenv("ISSUEDIGEST_DATABASE_URL", "private invalid URL")
    assert api().main(["--private-secret"]) == 2
    output = capsys.readouterr()
    assert output.out == "" and output.err == "Invalid planned retrieval evaluation arguments\n"
    script = Path(os.sys.executable).parent / "issuedigest-evaluate-planned-retrieval"
    assert script.is_file(), "new installed console script is missing"
    help_result = subprocess.run([str(script), "--help"], capture_output=True, text=True)
    assert help_result.returncode == 0 and "--output" in help_result.stdout
    assert help_result.stderr == ""


def test_installed_entrypoint_real_evaluation(tmp_path, engine, database_url):
    job, report, identity = planned_files(tmp_path, engine)
    script = Path(os.sys.executable).parent / "issuedigest-evaluate-planned-retrieval"
    assert script.is_file(), "new installed console script is missing"
    result = subprocess.run(
        [str(script), str(job), "--output", str(report)],
        capture_output=True,
        text=True,
        env={**os.environ, "ISSUEDIGEST_DATABASE_URL": database_url},
    )
    assert result.returncode == 0 and result.stderr == ""
    assert json.loads(result.stdout)["planned"]["returned_count"] == 1
    assert str(identity) not in result.stdout
    assert json.loads(report.read_bytes())["profile"] == "planned-retrieval-comparison-v1"
