"""Offline candidate comparison and private CLI over synthetic discovery captures."""

import importlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, date, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from issuedigest_connectors import MAX_POLICY_DISCOVERY_BYTES
from issuedigest_worker import PreparationError
from pydantic import ValidationError
from test_policy_import import private_file


def row(
    identity="123456789", day="2026.10.18", title="PRIVATE 합성 제목", publisher="PRIVATE 합성부"
):
    return (
        f'<li><a href="/news/policyNewsView.do?newsId={identity}">'
        f'<span class="text"><strong>{title}</strong><span class="source">'
        f"<span>{day}</span><span>{publisher}</span></span></span></a></li>"
    )


def discovery(*rows, time="2026-10-19T00:00:00Z"):
    return json.dumps(
        {
            "schema_version": 1,
            "collected_at": time,
            "list_html": '<div class="article_body"><div class="list_type"><ul>'
            + "".join(rows or [row()])
            + "</ul></div></div>",
        },
        ensure_ascii=False,
    ).encode()


def build(current, previous=None, since=date(2026, 10, 18), through=date(2026, 10, 19)):
    name = "issuedigest_worker.policy_candidates"
    assert importlib.util.find_spec(name) is not None, "missing pure candidate report SDK"
    return importlib.import_module(name).build_policy_candidate_report(
        current, since=since, through=through, previous_raw=previous
    )


def test_first_observation_retains_exact_bytes_time_range_and_private_metadata(capsys, caplog):
    raw = b"\n " + discovery() + b" \n"
    report = build(raw)
    assert report.schema_version == 1 and type(report.schema_version) is int
    assert report.current_discovery_sha256 == sha256(raw).hexdigest()
    assert report.current_collected_at == datetime(2026, 10, 19, tzinfo=UTC)
    assert report.previous_discovery_sha256 is report.previous_collected_at is None
    assert report.since == date(2026, 10, 18) and report.through == date(2026, 10, 19)
    assert len(report.entries) == 1
    entry = report.entries[0]
    assert entry.model_dump(mode="json") == {
        "news_id": "123456789",
        "canonical_url": "https://www.korea.kr/news/policyNewsView.do?newsId=123456789",
        "title": "PRIVATE 합성 제목",
        "published_on": "2026-10-18",
        "publisher": "PRIVATE 합성부",
        "status": "new",
    }
    assert "PRIVATE" not in repr(entry) + repr(report)
    assert "123456789" not in repr(entry) + repr(report)
    with pytest.raises(ValidationError):
        entry.status = "unchanged"
    for update in (
        {"schema_version": True},
        {"extra": "PRIVATE"},
        {"since": "2026-10-18"},
        {"entries": []},
    ):
        with pytest.raises(ValidationError):
            type(report).model_validate({**report.model_dump(), **update})
    assert capsys.readouterr() == ("", "") and caplog.text == ""


def test_empty_date_window_is_valid():
    report = build(discovery(row(day="2026.10.17")))
    assert report.entries == ()


def test_comparison_classifies_all_states_sorts_ids_and_preserves_previous_metadata():
    previous = discovery(
        row("333333333"),
        row("111111111"),
        row("222222222"),
        row("555555555", day="2026.10.19"),
        time="2026-10-18T23:59:59Z",
    )
    current = discovery(
        row("444444444", day="2026.10.19"),
        row("333333333", title="PRIVATE changed"),
        row("222222222"),
        row("555555555", day="2026.10.17"),
    )
    report = build(current, previous)
    assert [(e.news_id, e.status) for e in report.entries] == [
        ("111111111", "not_observed"),
        ("222222222", "unchanged"),
        ("333333333", "metadata_changed"),
        ("444444444", "new"),
    ]
    assert report.entries[0].title == "PRIVATE 합성 제목"
    assert report.previous_discovery_sha256 == sha256(previous).hexdigest()
    assert report.previous_collected_at == datetime(2026, 10, 18, 23, 59, 59, tzinfo=UTC)


@pytest.mark.parametrize(
    "field,value", [("title", "other"), ("publisher", "other"), ("day", "2026.10.19")]
)
def test_each_metadata_change_is_classified(field, value):
    report = build(discovery(row(**{field: value})), discovery(time="2026-10-18T00:00:00Z"))
    assert report.entries[0].status == "metadata_changed"


def test_previous_range_does_not_limit_identity_lookup_or_create_false_absence():
    old = discovery(
        row(day="2026.10.17"), row("222222222", day="2026.10.17"), time="2026-10-18T00:00:00Z"
    )
    report = build(discovery(row(day="2026.10.18")), old)
    assert [(e.news_id, e.status) for e in report.entries] == [("123456789", "metadata_changed")]


@pytest.mark.parametrize(
    "time", ["2026-10-19T00:00:00Z", "2026-10-19T09:00:00+09:00", "2026-10-20T00:00:00Z"]
)
def test_previous_must_be_strictly_earlier_instant_even_for_identical_bytes(time):
    old = discovery(time=time)
    with pytest.raises(PreparationError, match="^Unable to build policy candidate report$"):
        build(discovery(), old)


@pytest.mark.parametrize(
    "since,through",
    [
        (datetime(2026, 10, 18), date(2026, 10, 19)),
        ("2026-10-18", date(2026, 10, 19)),
        (date(2026, 10, 20), date(2026, 10, 19)),
        (None, date(2026, 10, 19)),
    ],
)
def test_range_requires_exact_dates_in_order(since, through):
    with pytest.raises(PreparationError):
        build(discovery(), since=since, through=through)


@pytest.mark.parametrize("side", ["current", "previous"])
@pytest.mark.parametrize(
    "failure",
    [
        "json",
        "duplicate",
        "extra",
        "nonfinite",
        "utf8",
        "oversize",
        "string",
        "bytearray",
        "none",
        "time",
        "version",
        "date",
        "conflict",
        "hidden",
        "count",
        "noncanonical",
    ],
)
def test_malformed_discovery_fails_whole_report_without_private_diagnostics(
    side, failure, caplog, capsys
):
    data = json.loads(
        discovery(time="2026-10-18T00:00:00Z" if side == "previous" else "2026-10-19T00:00:00Z")
    )
    if failure == "extra":
        data["PRIVATE"] = "PRIVATE"
    if failure == "time":
        data["collected_at"] = "2026-10-19T00:00:00"
    if failure == "version":
        data["schema_version"] = True
    if failure == "date":
        data["list_html"] = data["list_html"].replace("2026.10.18", "2026.02.29")
    if failure == "hidden":
        data["list_html"] = data["list_html"].replace(
            "<span>PRIVATE 합성부", "<span hidden>PRIVATE 합성부"
        )
    if failure == "noncanonical":
        data["list_html"] = data["list_html"].replace(
            "newsId=123456789", "newsId=123456789&amp;PRIVATE=x"
        )
    bad = json.dumps(data, ensure_ascii=False).encode()
    if failure == "json":
        bad = b"PRIVATE invalid"
    if failure == "duplicate":
        bad = bad[:-1] + b',"schema_version":1}'
    if failure == "nonfinite":
        bad = bad[:-1] + b',"PRIVATE":NaN}'
    if failure == "utf8":
        bad = b"\xffPRIVATE"
    if failure == "oversize":
        bad = b" " * (MAX_POLICY_DISCOVERY_BYTES + 1)
    if failure == "string":
        bad = bad.decode()
    if failure == "bytearray":
        bad = bytearray(bad)
    if failure == "none":
        bad = None if side == "current" else 123
    if failure == "conflict":
        bad = discovery(row(), row(publisher="PRIVATE other"), time=data["collected_at"])
    if failure == "count":
        bad = discovery(*(row(str(100000000 + i)) for i in range(101)), time=data["collected_at"])
    with pytest.raises(
        PreparationError, match="^Unable to build policy candidate report$"
    ) as caught:
        build(bad if side == "current" else discovery(), bad if side == "previous" else None)
    assert caught.value.__suppress_context__
    assert "PRIVATE" not in str(caught.value) and caplog.text == ""
    assert capsys.readouterr() == ("", "")


def test_maximum_disjoint_lists_produce_200_sorted_rows_within_output_budget():
    previous = discovery(
        *(row(str(100000000 + i), title="😀" * 300, publisher="😀" * 200) for i in range(100)),
        time="2026-10-18T00:00:00Z",
    )
    current = discovery(
        *(row(str(200000000 + i), title="😀" * 300, publisher="😀" * 200) for i in range(100))
    )
    report = build(current, previous)
    assert len(report.entries) == 200
    assert report.entries[0].news_id == "100000000"
    assert report.entries[-1].news_id == "200000099"
    assert len(report.model_dump_json().encode()) <= 512 * 1024


@pytest.fixture
def cli_inputs(tmp_path):
    tmp_path.chmod(0o700)
    current = private_file(tmp_path / "PRIVATE-current.json", discovery())
    previous = private_file(
        tmp_path / "PRIVATE-previous.json",
        discovery(row(), row("222222222"), time="2026-10-18T00:00:00Z"),
    )
    return [
        "candidates",
        current,
        "2026-10-18",
        "2026-10-19",
        str(tmp_path / "PRIVATE-report.json"),
        "--previous",
        previous,
    ]


def test_cli_is_offline_private_atomic_and_aggregate_only(cli_inputs, monkeypatch, capsys):
    cli = importlib.import_module("issuedigest_worker.policy_cli")

    def forbidden(*args, **kwargs):
        raise AssertionError("PRIVATE external call")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(cli, "discover_policy", forbidden)
    monkeypatch.setattr(cli, "capture_policy", forbidden)
    monkeypatch.setattr(cli, "create_engine", forbidden)
    assert cli.main(cli_inputs) == 0
    output = Path(cli_inputs[4])
    raw = output.read_bytes()
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(raw)["entries"][1]["status"] == "not_observed"
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "status": "candidates_reported",
        "candidates": 1,
        "new": 0,
        "unchanged": 1,
        "metadata_changed": 0,
        "not_observed": 1,
    }
    assert cli.main(cli_inputs) == 1 and output.read_bytes() == raw
    assert capsys.readouterr() == ("", "Unable to complete policy operation\n")


def test_cli_no_previous_in_explicit_private_parent(cli_inputs, capsys):
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    cli_inputs[4] = str(Path(cli_inputs[4]).parent / "new" / "report.json")
    Path(cli_inputs[4]).parent.mkdir(mode=0o700)
    assert cli.main(cli_inputs[:5]) == 0
    assert Path(cli_inputs[4]).parent.stat().st_mode & 0o777 == 0o700
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "status": "candidates_reported",
        "candidates": 1,
        "new": 1,
        "unchanged": 0,
        "metadata_changed": 0,
        "not_observed": 0,
    }


@pytest.mark.parametrize(
    "day",
    [
        "20261018",
        "2026-1-18",
        "２０２６-10-18",
        "2026-10-18 ",
        "2026-02-29",
        "2026-10-18T00:00:00",
        "PRIVATE",
    ],
)
@pytest.mark.parametrize("position", [2, 3])
def test_cli_rejects_noncanonical_dates_without_publishing(cli_inputs, day, position, capsys):
    cli_inputs[position] = day
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    assert cli.main(cli_inputs) == 1
    assert capsys.readouterr() == ("", "Unable to complete policy operation\n")
    assert not Path(cli_inputs[4]).exists()


@pytest.mark.parametrize(
    "failure",
    [
        "mode",
        "previous_mode",
        "parent",
        "symlink",
        "parent_symlink",
        "relative",
        "oversize",
        "invalid",
        "previous_invalid",
        "existing",
        "write",
        "publish",
        "fsync",
        "args",
    ],
)
def test_cli_reuses_private_guards_and_atomic_fixed_failures(
    cli_inputs, failure, monkeypatch, capsys
):
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    directory = Path(cli_inputs[4]).parent
    if failure in {"mode", "previous_mode"}:
        Path(cli_inputs[1 if failure == "mode" else 6]).chmod(0o644)
    if failure == "parent":
        directory.chmod(0o755)
    if failure == "symlink":
        link = directory / "link.json"
        link.symlink_to(cli_inputs[1])
        cli_inputs[1] = str(link)
    if failure == "parent_symlink":
        link = directory / "link"
        link.symlink_to(directory, target_is_directory=True)
        cli_inputs[1] = str(link / Path(cli_inputs[1]).name)
    if failure == "relative":
        cli_inputs[1] = "PRIVATE.json"
    if failure == "oversize":
        Path(cli_inputs[1]).write_bytes(b" " * (MAX_POLICY_DISCOVERY_BYTES + 1))
    if failure in {"invalid", "previous_invalid"}:
        Path(cli_inputs[1 if failure == "invalid" else 6]).write_bytes(b"PRIVATE invalid JSON")
    if failure == "existing":
        private_file(Path(cli_inputs[4]), b"PRIVATE existing")

        def no_read(*args, **kwargs):
            pytest.fail("must reject output before input read")

        monkeypatch.setattr(cli, "read_private", no_read)

    def fail(*args, **kwargs):
        raise OSError("PRIVATE failure")

    if failure == "write":
        monkeypatch.setattr(cli, "write_private", fail)
    if failure == "publish":
        monkeypatch.setattr(os, "link", fail)
    if failure == "fsync":
        monkeypatch.setattr(os, "fsync", fail)
    if failure == "args":
        cli_inputs += ["--PRIVATE-invalid"]
    assert cli.main(cli_inputs) == (2 if failure == "args" else 1)
    output = Path(cli_inputs[4])
    assert (
        output.read_bytes() == b"PRIVATE existing" if failure == "existing" else not output.exists()
    )
    assert capsys.readouterr() == (
        "",
        "Invalid policy arguments\n"
        if failure == "args"
        else "Unable to complete policy operation\n",
    )
    assert not any(p.name.startswith(".hwpx-") for p in directory.iterdir())


def test_report_import_and_execution_do_not_read_secrets_or_connect():
    script = """
import os, socket, sqlalchemy
from sqlalchemy.engine import Engine
def forbidden(*args, **kwargs): raise AssertionError("PRIVATE external call")
socket.socket = forbidden
sqlalchemy.create_engine = forbidden
Engine.connect = forbidden
original_get = os.environ.get
def guarded(key, *args):
    if key in {"ISSUEDIGEST_DATABASE_URL", "OPENAI_API_KEY", "BITBUCKET_TOKEN"}: return forbidden()
    return original_get(key, *args)
os.environ.get = guarded
from datetime import date
from issuedigest_worker.policy_candidates import build_policy_candidate_report
import issuedigest_worker.policy_cli
build_policy_candidate_report(
    bytes.fromhex(os.environ["SYNTHETIC_DISCOVERY_HEX"]),
    since=date(2026,10,18), through=date(2026,10,19),
)
"""
    run = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "SYNTHETIC_DISCOVERY_HEX": discovery().hex()},
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == run.stderr == ""


def test_exact_discovery_size_boundary_is_inclusive_and_preserves_raw_hash():
    raw = discovery()
    bounded = raw + b" " * (MAX_POLICY_DISCOVERY_BYTES - len(raw))
    assert build(bounded).current_discovery_sha256 == sha256(bounded).hexdigest()
    with pytest.raises(PreparationError):
        build(bounded + b" ")


def test_one_day_inclusive_window_and_timezone_instant_order():
    old = discovery(time="2026-10-19T08:59:59+09:00")
    result = build(discovery(), old, since=date(2026, 10, 18), through=date(2026, 10, 18))
    assert len(result.entries) == 1 and result.entries[0].status == "unchanged"


def test_cli_accepts_readonly_owned_inputs(cli_inputs, capsys):
    Path(cli_inputs[1]).chmod(0o400)
    Path(cli_inputs[6]).chmod(0o400)
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    assert cli.main(cli_inputs) == 0
    assert json.loads(capsys.readouterr().out)["candidates"] == 1


def test_cli_does_not_create_missing_parent(cli_inputs, capsys):
    output = Path(cli_inputs[4]).parent / "missing" / "report.json"
    cli_inputs[4] = str(output)
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    assert cli.main(cli_inputs) == 1
    assert not output.parent.exists()
    assert capsys.readouterr() == ("", "Unable to complete policy operation\n")
