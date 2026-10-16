"""Assembly artifact preparation and private CLI, synthetic identities/HTML only."""

import importlib
import json
import os
import socket
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import httpx2 as httpx
import pytest
from issuedigest_connectors import capture_assembly, serialize_capture
from issuedigest_domain import validate_citation
from issuedigest_storage.provisioning import apply_plan, parse_plan, validate_plan

from conftest import bundle_data

BILL = "SYNTHETIC_01"
GET = (
    '<html><head><meta name="_csrf" content="synthetic-token"></head><body>'
    '<form id="form"><input name="billId" value="SYNTHETIC_01"></form>'
    "<h1>합성법안</h1><p>1234567</p></body></html>"
)
POST = '<section id="prntSummary"><p>제안이유😀</p><p>주요내용 e\u0301</p></section>'


def api():
    a = importlib.import_module("issuedigest_worker")
    assert callable(getattr(a, "prepare_assembly_plan", None)), (
        "missing offline Assembly preparation"
    )
    return a


def private_file(path, raw):
    path.write_bytes(raw)
    path.chmod(0o600)
    return path


@pytest.fixture
def assembly_inputs(tmp_path):
    tmp_path.chmod(0o700)
    job = {
        "schema_version": 1,
        "bill_id": BILL,
        "title": "합성법안",
        "bill_number": "1234567",
        "collected_at": "2026-10-16T00:00:00Z",
        "operator_approved": True,
        **{
            key: str(uuid4())
            for key in (
                "document_id",
                "version_id",
                "raw_object_id",
                "representation_id",
                "snapshot_id",
                "citation_id",
            )
        },
    }
    original = bundle_data()
    base = {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": original["document"]["workspace_id"],
        "invites": [
            {"user_id": str(uuid4()), "email": "assembly-synthetic@example.test", "role": "viewer"}
        ],
        "snapshots": [{"snapshot_id": str(uuid4()), "bundle": original}],
    }
    from datetime import UTC, datetime

    def response(request):
        return httpx.Response(
            200,
            content=(GET if request.method == "GET" else POST).encode(),
            headers={"content-type": "text/html"},
        )

    capture = capture_assembly(
        BILL,
        collected_at=datetime(2026, 10, 16, tzinfo=UTC),
        transport=httpx.MockTransport(response),
    )
    # Legal insignificant JSON whitespace must survive as exact raw artifact hash.
    raw = b"\n " + serialize_capture(capture) + b"\n"
    return job, raw, base, tmp_path


def prepare(inputs):
    job, raw, base, _ = inputs
    return api().prepare_assembly_plan(
        api().parse_assembly_job(json.dumps(job)), raw, parse_plan(json.dumps(base))
    )


def test_exact_artifact_plan_preserves_approvals_and_repeat(assembly_inputs):
    job, raw, base, _ = assembly_inputs
    result = prepare(assembly_inputs)
    old = parse_plan(json.dumps(base))
    assert (
        result.expected_database,
        result.workspace_id,
        result.invites,
        result.snapshots[:-1],
    ) == (old.expected_database, old.workspace_id, old.invites, old.snapshots)
    bundle = result.snapshots[-1].bundle
    assert bundle.document.source_kind == "bill"
    assert bundle.document.provider == "assembly"
    assert bundle.document.source_id == BILL
    assert (
        str(bundle.document.canonical_url)
        == "https://likms.assembly.go.kr/bill/bi/billDetailPage.do?billId=SYNTHETIC_01"
    )
    assert bundle.version.raw_sha256 == sha256(raw).hexdigest()
    assert bundle.version.media_type == "application/vnd.issuedigest.assembly-capture+json"
    assert bundle.representation.text == "제안이유😀\n주요내용 e\u0301"
    assert bundle.representation.parser_name == "assembly-prntSummary-htmlparser"
    assert bundle.representation.parser_version == "1"
    assert bundle.representation.normalization_profile == "assembly-summary-visible-blocks-v1"
    assert bundle.representation.pages == bundle.representation.tables == ()
    selector = bundle.citations[0].selector
    assert (selector.start, selector.end, selector.quote, selector.prefix, selector.suffix) == (
        0,
        13,
        "제안이유😀\n주요내용 e\u0301",
        "",
        "",
    )
    assert (
        validate_citation(bundle.citations[0], bundle.representation).support_status
        == "not_evaluated"
    )
    assert validate_plan(result)["snapshots"] == 2
    assert prepare(assembly_inputs).model_dump_json() == result.model_dump_json()
    assert (
        api().prepare_assembly_plan(api().parse_assembly_job(json.dumps(job)), raw, result)
        == result
    )


@pytest.mark.parametrize(
    "change",
    [
        {"operator_approved": False},
        {"operator_approved": 1},
        {"schema_version": True},
        {"bill_id": "https://evil.test"},
        {"title": " "},
        {"title": "x" * 301},
        {"bill_number": "1x"},
        {"bill_number": "1" * 11},
        {"bill_number": "１２"},
        {"collected_at": "2026-10-16T00:00:00"},
        {"document_id": "bad"},
        {"extra": 1},
    ],
)
def test_strict_job_rejects_invalid_or_unapproved_input(assembly_inputs, change):
    with pytest.raises(api().PreparationError):
        api().parse_assembly_job(json.dumps({**assembly_inputs[0], **change}))


def test_job_json_and_repr_are_private(assembly_inputs):
    a = api()
    raw = json.dumps(assembly_inputs[0])
    for bad in (
        raw[:-1] + ',"bill_id":"duplicate"}',
        raw[:-1] + ',"extra":Infinity}',
        b"\xff",
        " " * 16385,
    ):
        with pytest.raises(a.PreparationError):
            a.parse_assembly_job(bad)
    parsed = a.parse_assembly_job(raw)
    assert repr(parsed) == "AssemblyJob(schema_version=1)"


@pytest.mark.parametrize(
    "mutation",
    ["title", "number", "identity", "time", "hidden_title", "hidden_number", "number_substring"],
)
def test_prepare_requires_operator_metadata_visible_in_same_capture(assembly_inputs, mutation):
    job, raw, base, directory = assembly_inputs
    capture = json.loads(raw)
    if mutation == "title":
        job["title"] = "another"
    if mutation == "number":
        job["bill_number"] = "987"
    if mutation == "identity":
        job["bill_id"] = "OTHER"
    if mutation == "time":
        job["collected_at"] = "2026-10-16T00:00:01Z"
    if mutation == "hidden_title":
        capture["detail_html"] = GET.replace("<h1>", "<h1 hidden>")
    if mutation == "hidden_number":
        capture["detail_html"] = GET.replace("<p>", "<p hidden>")
    if mutation == "number_substring":
        job["bill_number"] = "123"
    with pytest.raises(api().PreparationError):
        prepare((job, json.dumps(capture).encode(), base, directory))


@pytest.mark.parametrize(
    "kind", ["document", "version", "raw_object", "representation", "snapshot", "citation"]
)
def test_conflicting_existing_immutable_identity_rejected(assembly_inputs, kind):
    job, raw, base, _ = assembly_inputs
    old = base["snapshots"][0]
    identities = {
        "document": old["bundle"]["document"]["document_id"],
        "version": old["bundle"]["version"]["version_id"],
        "raw_object": old["bundle"]["version"]["raw_object_id"],
        "representation": old["bundle"]["representation"]["representation_id"],
        "snapshot": old["snapshot_id"],
        "citation": old["bundle"]["citations"][0]["citation_id"],
    }
    job[kind + "_id"] = identities[kind]
    with pytest.raises(api().PreparationError):
        prepare(assembly_inputs)


@pytest.mark.parametrize("kind", ["job", "base"])
def test_forged_inputs_fail_before_serialization(assembly_inputs, monkeypatch, kind):
    from pydantic import BaseModel

    a = api()
    job = a.parse_assembly_job(json.dumps(assembly_inputs[0]))
    base = parse_plan(json.dumps(assembly_inputs[2]))
    if kind == "job":
        job = job.model_copy(update={"title": "x" * (8 * 1024 * 1024 + 1)})
    else:
        base = base.model_copy(update={"snapshots": base.snapshots * 100})
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("serialization before bounds")

    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(a.PreparationError):
        a.prepare_assembly_plan(job, assembly_inputs[1], base)
    assert calls == []


def arguments(inputs, mode):
    job, raw, base, directory = inputs
    j = private_file(directory / "job.json", json.dumps(job).encode())
    c = private_file(directory / "capture.json", raw)
    b = private_file(directory / "base.json", json.dumps(base).encode())
    return (
        [str(j), str(directory / "new-capture.json")]
        if mode == "capture"
        else [str(j), str(c), str(b), str(directory / "new-plan.json")]
    )


def test_prepare_cli_is_private_atomic_and_offline(assembly_inputs, monkeypatch, capsys):
    a = api()
    args = arguments(assembly_inputs, "prepare")
    before = {p.name: p.read_bytes() for p in assembly_inputs[3].iterdir()}

    def forbidden(*args, **kwargs):
        raise AssertionError("external call")

    monkeypatch.setattr(socket, "socket", forbidden)
    module = importlib.import_module("issuedigest_worker.assembly_cli")
    assert module.prepare_main(args) == 0
    output = Path(args[-1])
    assert output.stat().st_mode & 0o777 == 0o600
    assert parse_plan(output.read_bytes()) == prepare(assembly_inputs)
    assert all((assembly_inputs[3] / name).read_bytes() == raw for name, raw in before.items())
    assert module.prepare_main(args) == 1
    captured = capsys.readouterr()
    summary = json.loads(captured.out)
    assert summary == {
        "schema_version": 1,
        "status": "prepared",
        "sources": 1,
        "snapshots": 2,
        "citations": 1,
    }
    assert captured.err == "Unable to prepare Assembly plan\n"
    assert a


def test_capture_cli_runs_only_explicit_capture_and_preflights_existing_output(
    assembly_inputs, monkeypatch, capsys
):
    api()
    args = arguments(assembly_inputs, "capture")
    module = importlib.import_module("issuedigest_worker.assembly_cli")
    count = []
    real_capture = capture_assembly

    def bounded(bill_id, *, collected_at):
        def response(request):
            count.append(request.method)
            return httpx.Response(
                200,
                content=(GET if request.method == "GET" else POST).encode(),
                headers={"content-type": "text/html"},
            )

        return real_capture(
            bill_id, collected_at=collected_at, transport=httpx.MockTransport(response)
        )

    monkeypatch.setattr(module, "capture_assembly", bounded)
    assert module.capture_main(args) == 0
    original = Path(args[-1]).read_bytes()
    assert module.capture_main(args) == 1
    assert count == ["GET", "POST"]
    assert Path(args[-1]).read_bytes() == original
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "schema_version": 1,
        "status": "captured",
        "sources": 1,
        "requests": 2,
    }
    assert captured.err == "Unable to capture Assembly source\n"


@pytest.mark.parametrize("mode", ["capture", "prepare"])
@pytest.mark.parametrize(
    "failure",
    [
        "mode",
        "parent",
        "symlink",
        "parent_symlink",
        "invalid_json",
        "output_exists",
        "write",
        "publish",
        "fsync",
        "bad_args",
    ],
)
def test_cli_failure_keeps_inputs_and_leaves_no_partial_output(
    assembly_inputs, mode, failure, monkeypatch, capsys
):
    api()
    args = arguments(assembly_inputs, mode)
    directory = assembly_inputs[3]
    if failure == "mode":
        Path(args[0]).chmod(0o644)
    if failure == "parent":
        directory.chmod(0o755)
    if failure == "symlink":
        link = directory / "link.json"
        link.symlink_to(args[0])
        args[0] = str(link)
    if failure == "parent_symlink":
        link = directory / "link"
        link.symlink_to(directory, target_is_directory=True)
        args[0] = str(link / "job.json")
    if failure == "invalid_json":
        private_file(Path(args[0]), b'{"PRIVATE-MARKER":NaN}')
    if failure == "output_exists":
        private_file(Path(args[-1]), b"original")
    before = {
        p.name: p.read_bytes() for p in directory.iterdir() if p.is_file() and not p.is_symlink()
    }
    module = importlib.import_module("issuedigest_worker.assembly_cli")
    if mode == "capture":
        from issuedigest_connectors import parse_capture

        monkeypatch.setattr(
            module, "capture_assembly", lambda *args, **kwargs: parse_capture(assembly_inputs[1])
        )

    def fail(*args, **kwargs):
        raise OSError("PRIVATE-MARKER")

    if failure == "write":
        monkeypatch.setattr(module, "write_private", fail)
    if failure == "publish":
        monkeypatch.setattr(os, "link", fail)
    if failure == "fsync":
        monkeypatch.setattr(os, "fsync", fail)
    if failure == "bad_args":
        args = ["PRIVATE-MARKER", "--invalid"]
    main = module.capture_main if mode == "capture" else module.prepare_main
    assert main(args) in {1, 2}
    assert all((directory / name).read_bytes() == raw for name, raw in before.items())
    assert not any(p.name.startswith(".hwpx-") for p in directory.iterdir())
    if failure != "output_exists":
        assert not (
            directory / ("new-capture.json" if mode == "capture" else "new-plan.json")
        ).exists()
    output = capsys.readouterr()
    assert (
        output.out == "" and "PRIVATE-MARKER" not in output.err and str(directory) not in output.err
    )


def test_import_does_not_read_keys_or_open_network_or_database():
    script = """
import os, socket, sqlalchemy
from sqlalchemy.engine import Engine

def forbidden(*args, **kwargs): raise AssertionError("external call")
socket.socket = forbidden
sqlalchemy.create_engine = forbidden
Engine.connect = forbidden
original_get = os.environ.get

def guarded_get(key, *args):
    if key in {"ISSUEDIGEST_DATABASE_URL", "OPENAI_API_KEY", "BITBUCKET_TOKEN"}:
        return forbidden()
    return original_get(key, *args)

os.environ.get = guarded_get
import issuedigest_connectors
import issuedigest_worker.assembly_cli
"""
    run = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout == ""


def test_prepared_plan_register_repeat_zero_and_protected_read(assembly_inputs, engine):
    """Guarded engine fixture requires a separately owned local synthetic PostgreSQL DB."""
    from issuedigest_storage import EvidenceAccessRepository, OAuthRepository, SessionRepository

    plan = prepare(assembly_inputs)
    first = apply_plan(engine, plan)
    assert first["snapshots_created"] == 2 and first["invites_created"] == 1
    assert apply_plan(engine, plan)["snapshots_created"] == 0
    assert apply_plan(engine, plan)["invites_created"] == 0
    invite = plan.invites[0]
    user = OAuthRepository(engine).resolve_invited_identity(
        "https://accounts.google.com", "synthetic-assembly-subject", invite.email, True
    )
    assert user == invite.user_id
    sessions = SessionRepository(engine)
    session = sessions.issue_session(user)
    snapshot = plan.snapshots[-1]
    access = EvidenceAccessRepository(engine)
    assert (
        access.load_evidence(session.token, plan.workspace_id, snapshot.snapshot_id)
        == snapshot.bundle
    )
    assert access.load_evidence(session.token, uuid4(), snapshot.snapshot_id) is None


def test_recapture_requires_explicit_new_version_ids_and_keeps_old_snapshot(assembly_inputs):
    job, raw, _, directory = assembly_inputs
    original = prepare(assembly_inputs)
    changed = raw.replace(b"synthetic-token", b"new-synthetic-token")
    a = api()
    parsed = a.parse_assembly_job(json.dumps(job))
    with pytest.raises(a.PreparationError):
        a.prepare_assembly_plan(parsed, changed, original)
    for key in ("version_id", "raw_object_id", "representation_id", "snapshot_id", "citation_id"):
        job[key] = str(uuid4())
    result = a.prepare_assembly_plan(a.parse_assembly_job(json.dumps(job)), changed, original)
    assert len(result.snapshots) == 3
    assert result.snapshots[:-1] == original.snapshots
    assert result.snapshots[-1].bundle.document == original.snapshots[-1].bundle.document
    assert result.snapshots[-1].bundle.version.raw_sha256 == sha256(changed).hexdigest()


def test_hidden_form_bill_number_must_match_approved_number(assembly_inputs):
    job, raw, base, directory = assembly_inputs
    capture = json.loads(raw)
    capture["detail_html"] = GET.replace("</form>", '<input name="billNo" value="7654321"></form>')
    with pytest.raises(api().PreparationError):
        prepare((job, json.dumps(capture).encode(), base, directory))


def test_capture_cli_invalid_output_parent_rejected_before_network(
    assembly_inputs, monkeypatch, capsys
):
    api()
    args = arguments(assembly_inputs, "capture")
    assembly_inputs[3].chmod(0o755)
    attempted = []
    module = importlib.import_module("issuedigest_worker.assembly_cli")

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("network before preflight")

    monkeypatch.setattr(module, "capture_assembly", forbidden)
    assert module.capture_main(args) == 1
    assert attempted == []
    assert capsys.readouterr().err == "Unable to capture Assembly source\n"
