"""Private policy operator jobs and pure preparation, synthetic captures only."""

import importlib
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest
from issuedigest_domain import validate_citation
from issuedigest_storage.provisioning import parse_plan, validate_plan

from conftest import bundle_data

URL = "https://www.korea.kr/news/policyNewsView.do?newsId=123456789"
NOTICE = "이 자료는 텍스트에 한하여 공공누리 제1유형(출처표시)의 조건에 따라 이용할 수 있습니다."


def api():
    module = importlib.import_module("issuedigest_worker")
    assert callable(getattr(module, "prepare_policy_plan", None)), "missing pure policy preparation"
    return module


def page():
    return (
        f'<html><head><meta property="og:url" content="{URL}"></head><body>'
        '<div class="view_title"><h1>합성 정책</h1></div>'
        '<div class="variety"><div class="info">2026.10.16 '
        '<a class="gotosite">합성부</a></div></div>'
        '<div class="view_cont"><p>앞 😀한é 뒤</p><figure><p>PRIVATE PHOTO</p></figure>'
        "<p>둘째 문단</p></div>"
        f'<div class="kogl_wrap"><div class="type"><span>{NOTICE}</span></div></div>'
        "</body></html>"
    )


@pytest.fixture
def policy_inputs(tmp_path):
    # Construct the on-disk format independently of the SDK under test.
    tmp_path.chmod(0o700)
    html = page()
    raw = (
        "\n "
        + json.dumps(
            {
                "schema_version": 1,
                "collected_at": "2026-10-16T00:00:00Z",
                "articles": [{"news_id": "123456789", "canonical_url": URL, "html": html}],
            },
            ensure_ascii=False,
        )
        + "\n"
    ).encode()
    source = {
        "news_id": "123456789",
        "article_sha256": sha256(html.encode()).hexdigest(),
        "text_sha256": sha256("앞 😀한é 뒤\n\n둘째 문단".encode()).hexdigest(),
        "photos_and_external_works_excluded": True,
        "license": {
            "license_type": "public_nuri_type_1",
            "text_only": True,
            "operator_approved": True,
            "evidence_url": URL,
        },
        **{
            key: str(uuid4())
            for key in (
                "document_id",
                "version_id",
                "raw_object_id",
                "representation_id",
                "snapshot_id",
            )
        },
        "citations": [{"citation_id": str(uuid4()), "quote": "😀한é", "start": 2}],
    }
    job = {
        "schema_version": 1,
        "capture_sha256": sha256(raw).hexdigest(),
        "collected_at": "2026-10-16T00:00:00Z",
        "sources": [source],
    }
    original = bundle_data()
    base = {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": original["document"]["workspace_id"],
        "invites": [
            {"user_id": str(uuid4()), "email": "policy-synthetic@example.test", "role": "viewer"}
        ],
        "snapshots": [{"snapshot_id": str(uuid4()), "bundle": original}],
    }
    return job, raw, base, tmp_path


def prepare(inputs):
    job, raw, base, _ = inputs
    a = api()
    return a.prepare_policy_plan(
        a.parse_policy_job(json.dumps(job)), raw, parse_plan(json.dumps(base))
    )


def test_exact_artifact_unicode_quote_and_verified_title_preserve_base_repeat(
    policy_inputs, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("external call")

    monkeypatch.setattr(socket, "socket", forbidden)
    a = api()
    result = prepare(policy_inputs)
    job, raw, base, _ = policy_inputs
    old = parse_plan(json.dumps(base))
    plan = result.plan
    assert (plan.expected_database, plan.workspace_id, plan.invites, plan.snapshots[:-1]) == (
        old.expected_database,
        old.workspace_id,
        old.invites,
        old.snapshots,
    )
    bundle = plan.snapshots[-1].bundle
    assert (bundle.document.source_kind, bundle.document.provider, bundle.document.source_id) == (
        "government_document",
        "korea_policy",
        "123456789",
    )
    assert str(bundle.document.canonical_url) == URL
    assert bundle.version.raw_sha256 == sha256(raw).hexdigest()
    assert bundle.version.media_type == "application/vnd.issuedigest.policy-capture+json"
    assert bundle.representation.text == "앞 😀한é 뒤\n\n둘째 문단"
    assert bundle.representation.text_sha256 == job["sources"][0]["text_sha256"]
    selector = bundle.citations[0].selector
    assert (selector.start, selector.end, selector.quote) == (2, 6, "😀한é")
    assert (
        validate_citation(bundle.citations[0], bundle.representation).support_status
        == "not_evaluated"
    )
    presentation = result.presentations[0]
    assert (
        presentation.snapshot_id,
        presentation.workspace_id,
        presentation.title,
        presentation.profile,
    ) == (plan.snapshots[-1].snapshot_id, plan.workspace_id, "합성 정책", "policy-html-v1")
    assert presentation.bill_number is None and presentation.proposed_on is None
    assert validate_plan(plan)["snapshots"] == 2
    assert prepare(policy_inputs) == result
    assert a.prepare_policy_plan(a.parse_policy_job(json.dumps(job)), raw, plan) == result
    assert "합성" not in repr(result)


@pytest.mark.parametrize(
    "mutation",
    [
        "approval",
        "exclude",
        "license",
        "license_url",
        "hash",
        "body_hash",
        "identity",
        "time",
        "quote",
        "quote_normalization",
        "quote_photo",
        "quote_start",
        "missing",
        "extra",
        "ids",
        "capture_hash",
    ],
)
def test_jobs_require_exact_approved_capture_and_quote(policy_inputs, mutation):
    job, raw, base, directory = policy_inputs
    source = job["sources"][0]
    if mutation == "approval":
        source["license"]["operator_approved"] = False
    if mutation == "exclude":
        source["photos_and_external_works_excluded"] = False
    if mutation == "license":
        source["license"]["license_type"] = "public_nuri_type_2"
    if mutation == "license_url":
        source["license"]["evidence_url"] = URL + "&track=1"
    if mutation == "hash":
        source["article_sha256"] = "a" * 64
    if mutation == "body_hash":
        source["text_sha256"] = "a" * 64
    if mutation == "identity":
        source["news_id"] = "234567890"
    if mutation == "time":
        job["collected_at"] = "2026-10-16T00:00:01Z"
    if mutation == "quote":
        source["citations"][0]["quote"] = "missing"
    if mutation == "quote_normalization":
        source["citations"][0]["quote"] = "😀한é"
    if mutation == "quote_photo":
        source["citations"][0].update(quote="PRIVATE PHOTO", start=None)
    if mutation == "quote_start":
        source["citations"][0]["start"] = 3
    if mutation == "missing":
        source.pop("raw_object_id")
    if mutation == "extra":
        source["title"] = "UNVERIFIED TITLE"
    if mutation == "ids":
        source["version_id"] = "invalid"
    if mutation == "capture_hash":
        raw += b" "
    with pytest.raises(
        api().PreparationError, match="^Unable to (validate policy job|prepare policy plan)$"
    ):
        prepare((job, raw, base, directory))


@pytest.mark.parametrize(
    "replacement", ["different_article", "license", "publisher", "title", "body"]
)
def test_parser_conditions_rechecked_even_for_matching_artifact_hash(policy_inputs, replacement):
    job, raw, base, directory = policy_inputs
    capture = json.loads(raw)
    html = capture["articles"][0]["html"]
    if replacement == "different_article":
        html = html.replace(URL, URL.replace("123456789", "234567890"))
    if replacement == "license":
        html = html.replace("제1유형", "제2유형")
    if replacement == "publisher":
        html = html.replace('class="gotosite"', 'class="other"')
    if replacement == "title":
        html = html.replace("<h1>합성 정책</h1>", "<h1></h1>")
    if replacement == "body":
        html = html.replace('class="view_cont"', 'class="other"')
    capture["articles"][0]["html"] = html
    raw = json.dumps(capture).encode()
    job["capture_sha256"] = sha256(raw).hexdigest()
    job["sources"][0]["article_sha256"] = sha256(html.encode()).hexdigest()
    with pytest.raises(api().PreparationError):
        prepare((job, raw, base, directory))


@pytest.mark.parametrize(
    "kind", ["document", "version", "raw_object", "representation", "snapshot", "citation"]
)
def test_conflicting_existing_immutable_identity_rejected(policy_inputs, kind):
    job, _, base, _ = policy_inputs
    old = base["snapshots"][0]
    values = {
        "document": old["bundle"]["document"]["document_id"],
        "version": old["bundle"]["version"]["version_id"],
        "raw_object": old["bundle"]["version"]["raw_object_id"],
        "representation": old["bundle"]["representation"]["representation_id"],
        "snapshot": old["snapshot_id"],
        "citation": old["bundle"]["citations"][0]["citation_id"],
    }
    if kind == "citation":
        job["sources"][0]["citations"][0]["citation_id"] = values[kind]
    else:
        job["sources"][0][kind + "_id"] = values[kind]
    with pytest.raises(api().PreparationError):
        prepare(policy_inputs)


def test_strict_json_bounds_and_model_construct_bypasses(policy_inputs, monkeypatch):
    a = api()
    raw = json.dumps(policy_inputs[0])
    for bad in [
        raw[:-1] + ',"schema_version":1}',
        raw[:-1] + ',"extra":Infinity}',
        b"\xff",
        " " * 131073,
    ]:
        with pytest.raises(a.PreparationError):
            a.parse_policy_job(bad)
    job = a.parse_policy_job(raw)
    assert repr(job) == "PolicyJob(schema_version=1)"
    source = job.sources[0]
    forged = job.model_copy(
        update={
            "sources": (
                source.model_copy(
                    update={
                        "citations": (source.citations[0].model_copy(update={"quote": "x" * 2001}),)
                    }
                ),
            )
        }
    )
    base = parse_plan(json.dumps(policy_inputs[2]))
    from pydantic import BaseModel

    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("serialize before bounds")

    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(a.PreparationError):
        a.prepare_policy_plan(forged, policy_inputs[1], base)
    assert calls == []


def private_file(path, raw):
    path.write_bytes(raw)
    path.chmod(0o600)
    return str(path)


def cli_args(inputs, output_kind="plan"):
    job, raw, base, directory = inputs
    return [
        "prepare",
        private_file(directory / "job.json", json.dumps(job).encode()),
        private_file(directory / "capture.json", raw),
        private_file(directory / "base.json", json.dumps(base).encode()),
        str(directory / f"{output_kind}.json"),
        "--output-kind",
        output_kind,
    ]


@pytest.mark.parametrize("kind", ["plan", "presentations"])
def test_private_cli_offline_atomic_no_overwrite(policy_inputs, monkeypatch, capsys, kind):
    api()
    module = importlib.import_module("issuedigest_worker.policy_cli")
    args = cli_args(policy_inputs, kind)

    def forbidden(*args, **kwargs):
        raise AssertionError("external call")

    monkeypatch.setattr(socket, "socket", forbidden)
    assert module.main(args) == 0
    output = Path(args[4])
    assert output.stat().st_mode & 0o777 == 0o600
    expected = prepare(policy_inputs)
    if kind == "plan":
        assert parse_plan(output.read_bytes()) == expected.plan
    else:
        assert json.loads(output.read_bytes()) == [
            p.model_dump(mode="json") for p in expected.presentations
        ]
    original = output.read_bytes()
    assert module.main(args) == 1
    assert output.read_bytes() == original
    logs = capsys.readouterr()
    assert json.loads(logs.out)["status"] == "prepared"
    assert logs.err == "Unable to complete policy operation\n"


@pytest.mark.parametrize(
    "failure",
    [
        "mode",
        "parent",
        "symlink",
        "parent_symlink",
        "invalid_json",
        "write",
        "publish",
        "fsync",
        "bad_args",
    ],
)
def test_cli_failure_leaves_no_partial_artifact_or_private_diagnostics(
    policy_inputs, monkeypatch, capsys, failure
):
    api()
    module = importlib.import_module("issuedigest_worker.policy_cli")
    args = cli_args(policy_inputs)
    directory = policy_inputs[3]
    if failure == "mode":
        Path(args[1]).chmod(0o644)
    if failure == "parent":
        directory.chmod(0o755)
    if failure == "symlink":
        link = directory / "link.json"
        link.symlink_to(args[1])
        args[1] = str(link)
    if failure == "parent_symlink":
        link = directory / "link"
        link.symlink_to(directory, target_is_directory=True)
        args[1] = str(link / "job.json")
    if failure == "invalid_json":
        private_file(Path(args[1]), b'{"PRIVATE":NaN}')

    def fail(*args, **kwargs):
        raise OSError("PRIVATE")

    if failure == "write":
        monkeypatch.setattr(module, "write_private", fail)
    if failure == "publish":
        monkeypatch.setattr(os, "link", fail)
    if failure == "fsync":
        monkeypatch.setattr(os, "fsync", fail)
    if failure == "bad_args":
        args = ["PRIVATE", "--invalid"]
    assert module.main(args) in {1, 2}
    assert not (directory / "plan.json").exists()
    logs = capsys.readouterr()
    assert logs.out == "" and "PRIVATE" not in logs.err and str(directory) not in logs.err
    assert not any(p.name.startswith(".hwpx-") for p in directory.iterdir())


def test_import_has_no_network_env_database_access():
    script = """
import os, socket, sqlalchemy
from sqlalchemy.engine import Engine

def forbidden(*args, **kwargs): raise AssertionError("external call")
socket.socket = forbidden
sqlalchemy.create_engine = forbidden
Engine.connect = forbidden
original_get = os.environ.get

def guarded_get(key, *args):
    if key in {"ISSUEDIGEST_DATABASE_URL", "OPENAI_API_KEY", "BITBUCKET_TOKEN"}: return forbidden()
    return original_get(key, *args)

os.environ.get = guarded_get
import issuedigest_connectors
import issuedigest_worker.policy_cli
"""
    run = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout == ""


def test_recapture_uses_new_explicit_version_ids_preserves_old(policy_inputs):
    job, raw, base, directory = policy_inputs
    original = prepare(policy_inputs)
    capture = json.loads(raw)
    capture["articles"][0]["html"] = capture["articles"][0]["html"].replace("둘째 문단", "새 문단")
    changed = json.dumps(capture, ensure_ascii=False).encode()
    job["capture_sha256"] = sha256(changed).hexdigest()
    source = job["sources"][0]
    source["article_sha256"] = sha256(capture["articles"][0]["html"].encode()).hexdigest()
    source["text_sha256"] = sha256("앞 😀한é 뒤\n\n새 문단".encode()).hexdigest()
    a = api()
    with pytest.raises(a.PreparationError):
        a.prepare_policy_plan(a.parse_policy_job(json.dumps(job)), changed, original.plan)
    for key in ("version_id", "raw_object_id", "representation_id", "snapshot_id"):
        source[key] = str(uuid4())
    source["citations"][0]["citation_id"] = str(uuid4())
    result = a.prepare_policy_plan(a.parse_policy_job(json.dumps(job)), changed, original.plan)
    assert result.plan.snapshots[:-1] == original.plan.snapshots
    assert len(result.plan.snapshots) == 3
    assert result.plan.snapshots[-1].bundle.document == original.plan.snapshots[-1].bundle.document
    assert result.plan.snapshots[-1].bundle.version.raw_sha256 == sha256(changed).hexdigest()


@pytest.mark.parametrize(
    "mutation",
    [
        "version_bool",
        "false_exclusion",
        "false_license",
        "max_sources",
        "duplicates",
        "too_many_quotes",
        "long_quote",
        "naive_time",
        "foreign_id",
    ],
)
def test_job_scalar_collection_and_identity_bounds(policy_inputs, mutation):
    job = policy_inputs[0]
    source = job["sources"][0]
    if mutation == "version_bool":
        job["schema_version"] = True
    if mutation == "false_exclusion":
        source["photos_and_external_works_excluded"] = 1
    if mutation == "false_license":
        source["license"]["operator_approved"] = 1
    if mutation == "max_sources":
        job["sources"] *= 3
    if mutation == "duplicates":
        job["sources"] *= 2
    if mutation == "too_many_quotes":
        source["citations"] *= 11
    if mutation == "long_quote":
        source["citations"][0]["quote"] = "x" * 2001
    if mutation == "naive_time":
        job["collected_at"] = "2026-10-16T00:00:00"
    if mutation == "foreign_id":
        source["news_id"] = URL
    with pytest.raises(api().PreparationError):
        api().parse_policy_job(json.dumps(job))


def test_two_article_batch_prepares_two_distinct_exact_snapshots(policy_inputs):
    job, raw, base, directory = policy_inputs
    capture = json.loads(raw)
    second_article = dict(capture["articles"][0])
    second_article["news_id"] = "234567890"
    second_article["canonical_url"] = URL.replace("123456789", "234567890")
    second_article["html"] = (
        second_article["html"]
        .replace(URL, second_article["canonical_url"])
        .replace("합성 정책", "둘째 정책")
    )
    capture["articles"].append(second_article)
    changed = json.dumps(capture, ensure_ascii=False).encode()
    job["capture_sha256"] = sha256(changed).hexdigest()
    source = json.loads(json.dumps(job["sources"][0]))
    source["news_id"] = second_article["news_id"]
    source["article_sha256"] = sha256(second_article["html"].encode()).hexdigest()
    source["license"]["evidence_url"] = second_article["canonical_url"]
    for key in ("document_id", "version_id", "raw_object_id", "representation_id", "snapshot_id"):
        source[key] = str(uuid4())
    source["citations"][0]["citation_id"] = str(uuid4())
    job["sources"].append(source)
    result = prepare((job, changed, base, directory))
    assert len(result.plan.snapshots) == 3
    assert [p.title for p in result.presentations] == ["합성 정책", "둘째 정책"]
    assert all(
        s.bundle.version.raw_sha256 == sha256(changed).hexdigest()
        for s in result.plan.snapshots[1:]
    )


def synthetic_listing():
    return (
        '<html><div class="article_body"><div class="list_type"><ul><li>'
        '<a href="/news/policyNewsView.do?newsId=123456789">'
        '<span class="text"><strong>LIST TITLE NEVER EVIDENCE</strong>'
        '<span class="source"><span>2026.10.16</span><span>LIST PUBLISHER</span></span>'
        "</span></a></li></ul></div></div></html>"
    )


def test_cli_explicit_discovery_capture_uses_only_injected_http(policy_inputs, monkeypatch, capsys):
    from issuedigest_connectors import (
        capture_policy,
        discover_policy,
        parse_policy_capture,
        parse_policy_discovery,
        policy_candidates,
    )

    api()
    from datetime import datetime

    module = importlib.import_module("issuedigest_worker.policy_cli")
    directory = policy_inputs[3]
    requests = []

    def respond(request):
        requests.append(str(request.url))
        html = synthetic_listing() if request.url.path.endswith("List.do") else page()
        return httpx.Response(200, content=html.encode(), headers={"content-type": "text/html"})

    monkeypatch.setattr(
        module,
        "discover_policy",
        lambda **kw: discover_policy(**kw, transport=httpx.MockTransport(respond)),
    )
    monkeypatch.setattr(
        module,
        "capture_policy",
        lambda *a, **kw: capture_policy(*a, **kw, transport=httpx.MockTransport(respond)),
    )
    discovery_path = str(directory / "discovery.json")
    capture_path = str(directory / "new-capture.json")
    timestamp = "2026-10-16T00:00:00Z"
    assert module.main(["discover", timestamp, discovery_path]) == 0
    discovered = parse_policy_discovery(Path(discovery_path).read_bytes())
    assert len(policy_candidates(discovered)) == 1
    assert module.main(["capture", discovery_path, timestamp, capture_path, "123456789"]) == 0
    captured = parse_policy_capture(Path(capture_path).read_bytes())
    assert captured.collected_at == datetime.fromisoformat(timestamp)
    assert captured.articles[0].html == page()
    assert requests == ["https://www.korea.kr/news/policyNewsList.do", URL]
    assert module.main(["capture", discovery_path, timestamp, capture_path, "123456789"]) == 1
    assert len(requests) == 2
    logs = capsys.readouterr()
    assert len(logs.out.splitlines()) == 2
    assert all("123456789" not in line and "TITLE" not in line for line in logs.out.splitlines())


@pytest.mark.parametrize(
    "ids", [[], ["234567890"], ["123456789"] * 2, ["123456789", "234567890", "345678901"], [URL]]
)
def test_capture_cli_rejects_undiscovered_invalid_batch_before_network(
    policy_inputs, monkeypatch, ids, capsys
):
    import httpx2 as httpx
    from issuedigest_connectors import discover_policy, serialize_policy_discovery

    api()
    module = importlib.import_module("issuedigest_worker.policy_cli")
    directory = policy_inputs[3]
    discovery = discover_policy(
        collected_at=datetime(2026, 10, 16, tzinfo=UTC),
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, content=synthetic_listing().encode(), headers={"content-type": "text/html"}
            )
        ),
    )
    path = private_file(directory / "discovery.json", serialize_policy_discovery(discovery))
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("network")

    monkeypatch.setattr(module, "capture_policy", forbidden)
    assert module.main(
        ["capture", path, "2026-10-16T00:00:00Z", str(directory / "output.json"), *ids]
    ) in {1, 2}
    assert attempted == []
    assert not (directory / "output.json").exists()
    assert "123456789" not in capsys.readouterr().err


@pytest.mark.parametrize("kind", ["base", "job"])
def test_forged_graphs_are_bounded_before_any_serialization(policy_inputs, monkeypatch, kind):
    from pydantic import BaseModel

    a = api()
    job = a.parse_policy_job(json.dumps(policy_inputs[0]))
    base = parse_plan(json.dumps(policy_inputs[2]))
    if kind == "base":
        base = base.model_copy(update={"snapshots": base.snapshots * 100})
    else:
        job = job.model_copy(update={"sources": job.sources * 100})
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("serialized before graph bounds")

    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(a.PreparationError):
        a.prepare_policy_plan(job, policy_inputs[1], base)
    assert calls == []


@pytest.mark.parametrize("operation", ["discover", "capture"])
def test_network_cli_preflights_private_output_before_fetch(
    policy_inputs, monkeypatch, operation, capsys
):
    api()
    module = importlib.import_module("issuedigest_worker.policy_cli")
    directory = policy_inputs[3]
    directory.chmod(0o755)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("network")

    monkeypatch.setattr(module, "discover_policy", forbidden)
    monkeypatch.setattr(module, "capture_policy", forbidden)
    args = ["discover", "2026-10-16T00:00:00Z", str(directory / "new.json")]
    if operation == "capture":
        args = [
            "capture",
            str(directory / "PRIVATE.json"),
            "2026-10-16T00:00:00Z",
            str(directory / "new.json"),
            "123456789",
        ]
    assert module.main(args) == 1
    assert calls == []
    assert capsys.readouterr().err == "Unable to complete policy operation\n"


def test_plain_publisher_capture_prepares_version_two_without_changing_job_contract(policy_inputs):
    job, raw, base, directory = policy_inputs
    capture = json.loads(raw)
    html = capture["articles"][0]["html"].replace(
        '2026.10.16 <a class="gotosite">합성부</a>',
        "<span>2026.01.15</span><span>합성부처</span>",
    )
    capture["articles"][0]["html"] = html
    changed = json.dumps(capture, ensure_ascii=False).encode()
    job["capture_sha256"] = sha256(changed).hexdigest()
    job["sources"][0]["article_sha256"] = sha256(html.encode()).hexdigest()
    result = prepare((job, changed, base, directory))
    bundle = result.plan.snapshots[-1].bundle
    assert bundle.representation.parser_version == "2"
    assert bundle.representation.normalization_profile == "korea-policy-paragraphs-v1"
    assert bundle.representation.text_sha256 == job["sources"][0]["text_sha256"]
    assert bundle.citations[0].selector.quote == "😀한é"
    assert result.presentations[0].title == "합성 정책"
    assert bundle.version.raw_sha256 == sha256(changed).hexdigest()
    assert result == prepare((job, changed, base, directory))
