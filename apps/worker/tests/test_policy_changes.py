"""Offline policy change decisions over synthetic captures and private local files."""

import importlib
import importlib.util
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from issuedigest_connectors import MAX_POLICY_CAPTURE_BYTES
from issuedigest_worker import PreparationError
from pydantic import ValidationError
from test_policy_import import NOTICE, URL, page, private_file


def api():
    name = "issuedigest_worker.policy_changes"
    assert importlib.util.find_spec(name) is not None, "missing pure capture comparison SDK"
    module = importlib.import_module(name)
    assert callable(getattr(module, "compare_policy_captures", None)), "missing comparison API"
    return module


def article(news_id="123456789", html=None):
    url = URL.replace("123456789", news_id)
    return {
        "news_id": news_id,
        "canonical_url": url,
        "html": (page() if html is None else html).replace(URL, url),
    }


def capture(*articles, time="2026-10-18T00:00:00Z"):
    return json.dumps(
        {
            "schema_version": 1,
            "collected_at": time,
            "articles": list(articles) or [article()],
        },
        ensure_ascii=False,
    ).encode()


def compare(current, previous=None):
    return api().compare_policy_captures(current, previous_raw=previous)


def test_first_capture_preserves_exact_artifact_and_canonical_semantic_hash(capsys, caplog):
    raw = b"\n " + capture() + b"\n"
    report = compare(raw)
    assert report.schema_version == 1 and report.profile == "policy-change-v1"
    assert report.before_capture_sha256 is None and report.before_collected_at is None
    assert report.after_capture_sha256 == sha256(raw).hexdigest()
    assert report.after_collected_at == datetime(2026, 10, 18, tzinfo=UTC)
    assert len(report.sources) == 1
    source = report.sources[0]
    assert (source.source_id, source.status, source.before_fingerprint, source.changed_fields) == (
        "123456789",
        "new",
        None,
        (),
    )
    # Independent expected payload: no article HTML SHA, URL, capture time or photo text.
    semantic = {
        "text_sha256": sha256("앞 😀한é 뒤\n\n둘째 문단".encode()).hexdigest(),
        "title": "합성 정책",
        "publisher": "합성부",
        "publication_date": "2026-10-16",
        "license_notice": NOTICE,
        "license_url": "https://www.kogl.or.kr/info/license.do",
        "parser_name": "korea-policy-html",
        "parser_version": "1",
        "normalization_profile": "korea-policy-paragraphs-v1",
    }
    expected = sha256(
        json.dumps(
            semantic, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
    assert source.after_fingerprint == expected
    serialized = report.model_dump_json().encode()
    assert len(serialized) <= 65536
    for private in ("합성 정책", "합성부", "둘째 문단", "PRIVATE PHOTO", URL, "<html>"):
        assert private not in serialized.decode() and private not in repr(report)
        assert private not in repr(source)
    assert "123456789" not in repr(report) and "123456789" not in repr(source)
    assert compare(raw) == report
    assert capsys.readouterr() == ("", "") and caplog.text == ""


def test_report_is_frozen_strict_and_extra_forbidden():
    report = compare(capture())
    with pytest.raises(ValidationError):
        report.profile = "other"
    with pytest.raises(ValidationError):
        report.sources[0].status = "changed"
    for update in ({"schema_version": True}, {"extra": "PRIVATE"}, {"sources": []}):
        with pytest.raises(ValidationError):
            type(report).model_validate({**report.model_dump(), **update}, strict=True)


@pytest.mark.parametrize("mutation", ["time", "decoration", "photo", "token", "exact"])
def test_nonsemantic_capture_changes_remain_unchanged(mutation):
    old = capture()
    html = page()
    if mutation == "decoration":
        html = html.replace("<body>", "<body><nav>PRIVATE DECORATION</nav>")
    if mutation == "photo":
        html = html.replace("PRIVATE PHOTO", "PRIVATE NEW PHOTO")
    if mutation == "token":
        html = html.replace("<body>", '<body><input type="hidden" value="PRIVATE TOKEN">')
    new = old if mutation == "exact" else capture(article(html=html), time="2026-10-18T00:00:01Z")
    report = compare(new, old)
    source = report.sources[0]
    assert source.status == "unchanged" and source.changed_fields == ()
    assert source.before_fingerprint == source.after_fingerprint
    assert report.before_capture_sha256 == sha256(old).hexdigest()
    assert report.after_capture_sha256 == sha256(new).hexdigest()
    assert report.before_collected_at == datetime(2026, 10, 18, tzinfo=UTC)


@pytest.mark.parametrize(
    ("before", "after", "fields"),
    [
        ("둘째 문단", "새 문단", ("text_sha256",)),
        ("합성 정책", "새 정책", ("title",)),
        ("합성부", "새 부처", ("publisher",)),
        ("2026.10.16", "2026.10.17", ("publication_date",)),
        (
            '2026.10.16 <a class="gotosite">합성부</a>',
            "<span>2026.10.16</span><span>합성부</span>",
            ("parser_version",),
        ),
    ],
)
def test_semantic_changes_report_exact_field_names(before, after, fields):
    report = compare(
        capture(article(html=page().replace(before, after)), time="2026-10-18T00:00:01Z"),
        capture(),
    )
    source = report.sources[0]
    assert source.status == "changed" and source.changed_fields == fields
    assert source.before_fingerprint != source.after_fingerprint


def test_multiple_changed_fields_are_sorted():
    html = page().replace("합성 정책", "새 정책").replace("둘째 문단", "새 문단")
    html = html.replace("합성부", "새 부처").replace("2026.10.16", "2026.10.17")
    source = compare(capture(article(html=html), time="2026-10-18T01:00:00Z"), capture()).sources[0]
    assert source.changed_fields == ("publication_date", "publisher", "text_sha256", "title")


def test_addition_absence_and_order_do_not_infer_deletion():
    first, second, third = article(), article("234567890"), article("345678901")
    old = capture(second, first)
    current = capture(third, second, time="2026-10-18T00:00:01Z")
    report = compare(current, old)
    assert [(s.source_id, s.status) for s in report.sources] == [
        ("123456789", "not_observed"),
        ("234567890", "unchanged"),
        ("345678901", "new"),
    ]
    absent, _, added = report.sources
    assert absent.after_fingerprint is None and absent.before_fingerprint is not None
    assert added.before_fingerprint is None and added.after_fingerprint is not None
    assert absent.changed_fields == added.changed_fields == ()
    reordered = compare(capture(second, third, time="2026-10-18T00:00:01Z"), capture(first, second))
    assert reordered.sources == report.sources
    same = compare(capture(first, second, time="2026-10-18T00:00:01Z"), old)
    assert [s.status for s in same.sources] == ["unchanged", "unchanged"]


@pytest.mark.parametrize("current_time", ["2026-10-17T23:59:59Z", "2026-10-18T00:00:00Z"])
def test_ambiguous_or_older_capture_order_is_rejected(current_time):
    with pytest.raises(PreparationError, match="^Unable to compare policy captures$"):
        compare(capture(time=current_time) + b" ", capture())


def test_same_instant_different_timezone_and_bytes_is_ambiguous():
    with pytest.raises(PreparationError, match="^Unable to compare policy captures$"):
        compare(capture(time="2026-10-18T09:00:00+09:00"), capture())


@pytest.mark.parametrize("side", ["current", "previous"])
@pytest.mark.parametrize(
    "failure",
    [
        "invalid_json",
        "duplicate_key",
        "nonfinite",
        "oversize",
        "string",
        "bytearray",
        "none",
        "invalid_utf8",
        "duplicate_article",
        "empty",
        "count",
        "type",
        "url",
        "time",
        "version",
        "license",
        "body",
        "title",
        "publisher",
        "identity",
    ],
)
def test_malformed_capture_or_article_fails_whole_comparison_safely(side, failure, caplog, capsys):
    data = json.loads(capture())
    bad = capture()
    replacements = {
        "license": ("제1유형", "제2유형"),
        "body": ('class="view_cont"', 'class="PRIVATE"'),
        "title": ("<h1>합성 정책</h1>", "<h1></h1>"),
        "publisher": ('class="gotosite"', 'class="PRIVATE"'),
        "identity": (URL, URL.replace("123456789", "999999999")),
    }
    if failure in replacements:
        data["articles"][0]["html"] = page().replace(*replacements[failure])
    if failure == "duplicate_article":
        data["articles"] *= 2
    if failure == "empty":
        data["articles"] = []
    if failure == "count":
        data["articles"] = [article(), article("234567890"), article("345678901")]
    if failure == "type":
        data["articles"][0]["html"] = 123
    if failure == "url":
        data["articles"][0]["canonical_url"] += "&track=PRIVATE"
    if failure == "time":
        data["collected_at"] = "2026-10-18T00:00:00"
    if failure == "version":
        data["schema_version"] = True
    bad = json.dumps(data, ensure_ascii=False).encode()
    if failure == "invalid_json":
        bad = b'{"PRIVATE"'
    if failure == "duplicate_key":
        bad = bad[:-1] + b',"schema_version":1}'
    if failure == "nonfinite":
        bad = bad[:-1] + b',"PRIVATE":NaN}'
    if failure == "oversize":
        bad = b" " * (MAX_POLICY_CAPTURE_BYTES + 1)
    if failure == "string":
        bad = bad.decode()
    if failure == "bytearray":
        bad = bytearray(bad)
    if failure == "none":
        bad = None if side == "current" else 123
    if failure == "invalid_utf8":
        bad = b"\xffPRIVATE"
    with pytest.raises(PreparationError, match="^Unable to compare policy captures$") as caught:
        compare(
            bad if side == "current" else capture(time="2026-10-18T00:00:01Z"),
            bad if side == "previous" else None,
        )
    assert caught.value.__suppress_context__ is True
    assert capsys.readouterr() == ("", "") and caplog.text == ""


@pytest.fixture
def cli_inputs(tmp_path):
    tmp_path.chmod(0o700)
    previous = private_file(tmp_path / "PRIVATE-old.json", capture(article(), article("234567890")))
    current = private_file(
        tmp_path / "PRIVATE-new.json",
        capture(
            article(html=page().replace("둘째 문단", "새 문단")),
            article("345678901"),
            time="2026-10-18T00:00:01Z",
        ),
    )
    output = str(tmp_path / "PRIVATE-report.json")
    return ["compare", current, output, "--previous", previous]


def test_compare_cli_is_offline_private_atomic_and_aggregate_only(cli_inputs, monkeypatch, capsys):
    cli = importlib.import_module("issuedigest_worker.policy_cli")

    def forbidden(*args, **kwargs):
        raise AssertionError("external call")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(cli, "discover_policy", forbidden)
    monkeypatch.setattr(cli, "capture_policy", forbidden)
    assert cli.main(cli_inputs) == 0
    output = Path(cli_inputs[2])
    raw = output.read_bytes()
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(raw)["sources"][0]["status"] == "changed"
    assert capsys.readouterr() == (
        json.dumps(
            {
                "schema_version": 1,
                "status": "compared",
                "new": 1,
                "changed": 1,
                "unchanged": 0,
                "not_observed": 1,
            },
            sort_keys=True,
        )
        + "\n",
        "",
    )
    assert cli.main(cli_inputs) == 1 and output.read_bytes() == raw
    assert capsys.readouterr() == ("", "Unable to complete policy operation\n")


def test_compare_cli_without_previous_counts_new_only(cli_inputs, capsys):
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    assert cli.main(cli_inputs[:3]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "schema_version": 1,
        "status": "compared",
        "new": 2,
        "changed": 0,
        "unchanged": 0,
        "not_observed": 0,
    }


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
def test_compare_cli_reuses_private_guards_and_fixed_diagnostics(
    cli_inputs, failure, monkeypatch, capsys
):
    cli = importlib.import_module("issuedigest_worker.policy_cli")
    directory = Path(cli_inputs[2]).parent
    if failure in {"mode", "previous_mode"}:
        Path(cli_inputs[1 if failure == "mode" else 4]).chmod(0o644)
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
        Path(cli_inputs[1]).write_bytes(b" " * (MAX_POLICY_CAPTURE_BYTES + 1))
    if failure in {"invalid", "previous_invalid"}:
        Path(cli_inputs[1 if failure == "invalid" else 4]).write_bytes(b"PRIVATE invalid JSON")
    if failure == "existing":
        private_file(Path(cli_inputs[2]), b"PRIVATE existing")

        def no_read(*args, **kwargs):
            pytest.fail("output must be checked before input read")

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
    output = Path(cli_inputs[2])
    assert (
        (output.read_bytes() == b"PRIVATE existing")
        if failure == "existing"
        else not output.exists()
    )
    logs = capsys.readouterr()
    assert logs.out == ""
    assert logs.err == (
        "Invalid policy arguments\n"
        if failure == "args"
        else "Unable to complete policy operation\n"
    )
    assert not any(p.name.startswith(".hwpx-") for p in directory.iterdir())


def test_comparison_import_and_execution_never_read_secrets_or_connect():
    script = """
import os, socket, sqlalchemy, json
from sqlalchemy.engine import Engine
def forbidden(*args, **kwargs): raise AssertionError("external call")
socket.socket = forbidden
sqlalchemy.create_engine = forbidden
Engine.connect = forbidden
original_get = os.environ.get
def guarded(key, *args):
    if key in {"ISSUEDIGEST_DATABASE_URL", "OPENAI_API_KEY", "BITBUCKET_TOKEN"}: return forbidden()
    return original_get(key, *args)
os.environ.get = guarded
from issuedigest_worker.policy_changes import compare_policy_captures
import issuedigest_worker.policy_cli
compare_policy_captures(bytes.fromhex(os.environ["SYNTHETIC_CAPTURE_HEX"]))
"""
    run = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env={**os.environ, "SYNTHETIC_CAPTURE_HEX": capture().hex()},
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == run.stderr == ""
