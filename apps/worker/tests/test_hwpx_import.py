"""Synthetic contracts: every boundary exercises real parser and storage models."""

import importlib
import json
import os
import socket
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile

import pytest
from issuedigest_domain import validate_citation
from issuedigest_storage.provisioning import parse_plan, validate_plan


def api():
    path = Path(__file__).parents[1] / "src/issuedigest_worker/__init__.py"
    assert path.is_file(), "missing typed HWPX preparation SDK"
    return importlib.import_module("issuedigest_worker")


def raw_hwpx(extra="", cell_extra=""):
    paragraph = "<hp:p><hp:run><hp:t>합성 본문😀" + extra + "</hp:t></hp:run></hp:p>"
    cell = (
        '<hp:tbl rowCnt="1" colCnt="1"><hp:tr><hp:tc>'
        '<hp:cellAddr rowAddr="0" colAddr="0"/><hp:cellSpan rowSpan="1" colSpan="1"/>'
        "<hp:subList><hp:p><hp:run><hp:t>단위: 억원</hp:t></hp:run></hp:p></hp:subList>"
        "</hp:tc></hp:tr></hp:tbl>"
    )
    cell = cell.replace("단위: 억원", "단위: 억원" + cell_extra)
    section = (
        '<hs:sec xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
        'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph">'
        + paragraph
        + "<hp:p><hp:run>"
        + cell
        + "</hp:run></hp:p></hs:sec>"
    )
    package = (
        '<opf:package xmlns:opf="http://www.idpf.org/2007/opf/"><opf:manifest>'
        '<opf:item id="s" href="Contents/section0.xml" media-type="application/xml"/>'
        '</opf:manifest><opf:spine><opf:itemref idref="s"/></opf:spine></opf:package>'
    )
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr("mimetype", "application/hwp+zip")
        archive.writestr("Contents/content.hpf", package)
        archive.writestr("Contents/section0.xml", section)
    return output.getvalue()


def private_file(path, data):
    path.write_bytes(data)
    path.chmod(0o600)
    return path


@pytest.fixture
def inputs(tmp_path):
    tmp_path.chmod(0o700)
    raw = raw_hwpx()
    source_path = private_file(tmp_path / "source.hwpx", raw)
    workspace, document, version, representation = [str(uuid4()) for _ in range(4)]
    source = {
        "raw_path": str(source_path),
        "document": {
            "document_id": document,
            "workspace_id": workspace,
            "provider": "synthetic",
            "source_id": "synthetic-source",
            "source_kind": "government_document",
            "canonical_url": "https://example.test/source",
        },
        "version": {
            "version_id": version,
            "document_id": document,
            "raw_object_id": str(uuid4()),
            "raw_sha256": sha256(raw).hexdigest(),
            "media_type": "application/hwp+zip",
            "collected_at": "2026-10-14T00:00:00Z",
        },
        "representation_id": representation,
        "snapshot_id": str(uuid4()),
        "license": {
            "license_type": "public_nuri_type_1",
            "text_only": True,
            "operator_approved": True,
            "evidence_url": "https://example.test/source",
        },
        "citations": [
            {"kind": "text", "citation_id": str(uuid4()), "quote": "합성 본문😀"},
            {
                "kind": "table_cell",
                "citation_id": str(uuid4()),
                "table_id": "s0-t0",
                "cell_id": "s0-t0-r0-c0",
            },
        ],
    }
    text = "기존 근거"
    base_doc, base_ver, base_rep = [str(uuid4()) for _ in range(3)]
    base = {
        "schema_version": 1,
        "expected_database": "issuedigest_test",
        "workspace_id": workspace,
        "invites": [{"user_id": str(uuid4()), "email": "synthetic@example.test", "role": "viewer"}],
        "snapshots": [
            {
                "snapshot_id": str(uuid4()),
                "bundle": {
                    "schema_version": 1,
                    "document": {
                        **source["document"],
                        "document_id": base_doc,
                        "source_id": "base",
                    },
                    "version": {
                        **source["version"],
                        "version_id": base_ver,
                        "document_id": base_doc,
                    },
                    "representation": {
                        "representation_id": base_rep,
                        "document_version_id": base_ver,
                        "parser_name": "synthetic",
                        "parser_version": "1",
                        "normalization_profile": "exact",
                        "text": text,
                        "text_sha256": sha256(text.encode()).hexdigest(),
                        "pages": [],
                        "tables": [],
                    },
                    "citations": [],
                },
            }
        ],
    }
    return {"schema_version": 1, "sources": [source]}, base, tmp_path


def prepare(job, base):
    a = api()
    return a.prepare_hwpx_plan(a.parse_job(json.dumps(job)), parse_plan(json.dumps(base)))


def test_exact_parser_evidence_preserves_base_and_repeat_is_deterministic(inputs):
    job, base, _ = inputs
    result = prepare(job, base)
    output = result.model_dump(mode="json")
    assert {k: output[k] for k in base if k != "snapshots"} == {
        k: parse_plan(json.dumps(base)).model_dump(mode="json")[k] for k in base if k != "snapshots"
    }
    assert (
        output["snapshots"][0]
        == parse_plan(json.dumps(base)).model_dump(mode="json")["snapshots"][0]
    )
    bundle = result.snapshots[1].bundle
    assert bundle.representation.text == "합성 본문😀\n단위: 억원"
    assert bundle.representation.pages == ()
    assert bundle.representation.tables[0].cells[0].unit is None
    assert bundle.citations[0].selector.quote == "합성 본문😀"
    assert bundle.citations[1].selector.quote == "단위: 억원"
    assert str(result.snapshots[1].snapshot_id) == job["sources"][0]["snapshot_id"]
    for citation in bundle.citations:
        assert validate_citation(citation, bundle.representation).support_status == "not_evaluated"
    assert validate_plan(parse_plan(result.model_dump_json()))["snapshots"] == 2
    assert prepare(job, base).model_dump_json() == result.model_dump_json()
    assert api().prepare_hwpx_plan(api().parse_job(json.dumps(job)), result) == result


@pytest.mark.parametrize(
    "mutation",
    [
        "approval",
        "text_only",
        "license",
        "evidence",
        "http",
        "kind",
        "media",
        "version_ref",
        "workspace",
        "no_citations",
        "duplicate_source",
        "duplicate_citation",
        "wrong_quote",
        "wrong_cell",
        "hash",
        "boolean_version",
        "boolean_start",
        "unknown",
        "empty_quote",
        "too_many_sources",
        "too_many_citations",
        "bad_time",
        "relative",
        "uuid",
    ],
)
def test_rejects_invalid_jobs_and_exact_evidence_without_disclosure(inputs, mutation):
    job, base, _ = inputs
    source = job["sources"][0]
    match mutation:
        case "approval":
            source["license"]["operator_approved"] = False
        case "text_only":
            source["license"]["text_only"] = False
        case "license":
            source["license"]["license_type"] = "other"
        case "evidence":
            source["license"]["evidence_url"] = "https://example.test/other"
        case "http":
            source["document"]["canonical_url"] = "http://example.test/source"
        case "kind":
            source["document"]["source_kind"] = "news"
        case "media":
            source["version"]["media_type"] = "application/pdf"
        case "version_ref":
            source["version"]["document_id"] = str(uuid4())
        case "workspace":
            source["document"]["workspace_id"] = str(uuid4())
        case "no_citations":
            source["citations"] = []
        case "duplicate_source":
            job["sources"].append(deepcopy(source))
        case "duplicate_citation":
            source["citations"].append(deepcopy(source["citations"][0]))
        case "wrong_quote":
            source["citations"][0]["quote"] = "PRIVATE-MARKER"
        case "wrong_cell":
            source["citations"][1]["cell_id"] = "PRIVATE-MARKER"
        case "hash":
            source["version"]["raw_sha256"] = "0" * 64
        case "boolean_version":
            job["schema_version"] = True
        case "boolean_start":
            source["citations"][0]["start"] = True
        case "unknown":
            source["unknown"] = "PRIVATE-MARKER"
        case "empty_quote":
            source["citations"][0]["quote"] = " "
        case "too_many_sources":
            job["sources"] *= 11
        case "too_many_citations":
            source["citations"] *= 51
        case "bad_time":
            source["version"]["collected_at"] = "2026-10-14"
        case "relative":
            source["raw_path"] = "private.hwpx"
        case "uuid":
            source["snapshot_id"] = "00000000-0000-1000-8000-000000000000"
    with pytest.raises(api().PreparationError) as error:
        prepare(job, base)
    assert "PRIVATE-MARKER" not in str(error.value)
    assert str(error.value) in {"Unable to validate HWPX job", "Unable to prepare HWPX plan"}


@pytest.mark.parametrize(
    "raw",
    [
        '{"schema_version":1,"schema_version":1}',
        '{"x":NaN}',
        '{"x":Infinity}',
        '{"x":1e999}',
        b"\xff",
        "[]",
        "{",
    ],
)
def test_unambiguous_bounded_json(raw):
    with pytest.raises(api().PreparationError):
        api().parse_job(raw)


@pytest.mark.parametrize("field", ["document", "version", "representation", "citation", "snapshot"])
def test_conflicting_aliases_in_base_and_new_are_rejected(inputs, field):
    job, base, _ = inputs
    ready = prepare(job, base).model_dump(mode="json")
    duplicate = deepcopy(ready["snapshots"][1])
    if field == "snapshot":
        duplicate["bundle"]["document"]["provider"] = "different"
    else:
        duplicate["snapshot_id"] = str(uuid4())
        match field:
            case "document":
                duplicate["bundle"]["document"]["provider"] = "different"
            case "version":
                duplicate["bundle"]["version"]["collected_at"] = "2026-10-15T00:00:00Z"
            case "representation":
                duplicate["bundle"]["representation"]["parser_version"] = "different"
            case "citation":
                duplicate["bundle"]["citations"][0]["selector"]["prefix"] = ""
    if field == "snapshot":
        ready["snapshots"][1] = duplicate
    else:
        ready["snapshots"].append(duplicate)
    # Different snapshot IDs with legal shared refs remain valid in storage's parser.
    with pytest.raises(api().PreparationError):
        api().prepare_hwpx_plan(
            api().parse_job(json.dumps(job)),
            parse_plan(json.dumps(ready)),
        )


def test_legal_shared_references_in_base_remain_supported(inputs):
    job, base, _ = inputs
    other = deepcopy(base["snapshots"][0])
    other["snapshot_id"] = str(uuid4())
    base["snapshots"].append(other)
    assert len(prepare(job, base).snapshots) == 3


def test_construct_copy_bypasses_are_revalidated(inputs):
    job, base, _ = inputs
    a = api()
    valid = a.parse_job(json.dumps(job))
    invalid = valid.model_copy(update={"schema_version": True})
    with pytest.raises(a.PreparationError):
        a.prepare_hwpx_plan(invalid, parse_plan(json.dumps(base)))
    with pytest.raises(a.PreparationError):
        a.prepare_hwpx_plan(valid, parse_plan(json.dumps(base)).model_copy(update={"invites": ()}))
    source = valid.sources[0]
    changed = source.model_copy(
        update={"license": source.license.model_copy(update={"operator_approved": False})}
    )
    with pytest.raises(a.PreparationError):
        a.prepare_hwpx_plan(
            valid.model_copy(update={"sources": (changed,)}), parse_plan(json.dumps(base))
        )


@pytest.mark.parametrize(
    "kind", ["public", "symlink", "parent_symlink", "fifo", "directory", "changed", "oversized"]
)
def test_private_raw_guards(inputs, kind, monkeypatch):
    job, base, directory = inputs
    path = Path(job["sources"][0]["raw_path"])
    if kind == "public":
        path.chmod(0o644)
    elif kind == "symlink":
        link = directory / "link.hwpx"
        link.symlink_to(path)
        job["sources"][0]["raw_path"] = str(link)
    elif kind == "parent_symlink":
        link = directory / "linkdir"
        link.symlink_to(directory, target_is_directory=True)
        job["sources"][0]["raw_path"] = str(link / path.name)
    elif kind in {"fifo", "directory"}:
        path.unlink()
        if kind == "fifo":
            os.mkfifo(path, 0o600)
        else:
            path.mkdir(mode=0o700)
    elif kind == "oversized":
        with path.open("ab") as file:
            file.truncate(16 * 1024 * 1024 + 1)
    elif kind == "changed":
        original = os.read

        changed = False

        def changing(fd, count):
            nonlocal changed
            result = original(fd, count)
            if not changed:
                with path.open("ab") as file:
                    file.write(b"changed")
                changed = True
            return result

        monkeypatch.setattr(os, "read", changing)
    with pytest.raises(api().PreparationError):
        prepare(job, base)


def cli(inputs, output=None):
    job, base, directory = inputs
    job_file = private_file(directory / "job.json", json.dumps(job).encode())
    base_file = private_file(directory / "base.json", json.dumps(base).encode())
    module = importlib.import_module("issuedigest_worker.cli")
    return module.main([str(job_file), str(base_file), str(output or directory / "result.json")])


def test_cli_exclusive_private_output_and_fixed_summary(inputs, capsys):
    api()
    assert cli(inputs) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {
        "schema_version": 1,
        "status": "prepared",
        "sources": 1,
        "snapshots": 2,
        "citations": 2,
    }
    output = inputs[2] / "result.json"
    assert output.stat().st_mode & 0o777 == 0o600
    original = output.read_bytes()
    assert validate_plan(parse_plan(original))["snapshots"] == 2
    assert cli(inputs) == 1
    assert output.read_bytes() == original
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == "Unable to prepare HWPX plan\n"
    assert set(p.name for p in inputs[2].iterdir()) == {
        "source.hwpx",
        "job.json",
        "base.json",
        "result.json",
    }


@pytest.mark.parametrize(
    "failure", ["public_parent", "link", "fsync", "input_public", "bad_arguments"]
)
def test_cli_failures_are_private_and_leave_no_partial_output(inputs, failure, monkeypatch, capsys):
    api()
    directory = inputs[2]
    if failure == "public_parent":
        directory.chmod(0o755)
    elif failure in {"link", "fsync"}:

        def fail(*args, **kwargs):
            raise OSError("PRIVATE-MARKER")

        monkeypatch.setattr(os, failure, fail)
    elif failure == "input_public":
        job, base, directory = inputs
        j = private_file(directory / "job.json", json.dumps(job).encode())
        b = private_file(directory / "base.json", json.dumps(base).encode())
        j.chmod(0o644)
        rc = importlib.import_module("issuedigest_worker.cli").main(
            [str(j), str(b), str(directory / "result.json")]
        )
    if failure == "bad_arguments":
        rc = importlib.import_module("issuedigest_worker.cli").main(["PRIVATE-MARKER", "--invalid"])
    elif failure != "input_public":
        rc = cli(inputs)
    assert rc in {1, 2}
    assert not (directory / "result.json").exists()
    assert not any(p.name.startswith(".hwpx-") for p in directory.iterdir())
    captured = capsys.readouterr()
    assert "PRIVATE-MARKER" not in captured.out + captured.err
    assert str(directory) not in captured.out + captured.err


def test_import_and_prepare_never_open_network_or_database(inputs, monkeypatch):
    api()
    import sqlalchemy

    def forbidden(*args, **kwargs):
        raise AssertionError("external call")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(sqlalchemy, "create_engine", forbidden)
    assert prepare(inputs[0], inputs[1]).snapshots
    script = """
import socket, sqlalchemy
from sqlalchemy.engine import Engine

def forbidden(*args, **kwargs):
    raise AssertionError("external call")
socket.socket = forbidden
sqlalchemy.create_engine = forbidden
Engine.connect = forbidden
import issuedigest_worker
import issuedigest_worker.cli
"""
    run = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert run.stdout == ""


def test_writer_temp_collision_preserves_existing_private_file(inputs, monkeypatch):
    files = importlib.import_module("issuedigest_worker.files")
    marker = private_file(inputs[2] / ".hwpx-collision", b"existing-private-artifact")
    monkeypatch.setattr(files.secrets, "token_hex", lambda size: "collision")
    with pytest.raises(api().PreparationError):
        files.write_private(str(inputs[2] / "result.json"), b"new")
    assert marker.read_bytes() == b"existing-private-artifact"
    assert not (inputs[2] / "result.json").exists()


def test_writer_open_failure_is_safe_and_leaves_no_artifact(inputs, monkeypatch):
    files = importlib.import_module("issuedigest_worker.files")
    original = os.open

    def failing(path, flags, *args, **kwargs):
        if str(path).startswith(".hwpx-"):
            raise OSError("PRIVATE-MARKER")
        return original(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", failing)
    with pytest.raises(api().PreparationError) as error:
        files.write_private(str(inputs[2] / "result.json"), b"new")
    assert "PRIVATE-MARKER" not in str(error.value)
    assert set(p.name for p in inputs[2].iterdir()) == {"source.hwpx"}


def test_bounded_json_and_output_plan_are_rejected(inputs):
    from issuedigest_storage.provisioning import MAX_PLAN_BYTES

    with pytest.raises(api().PreparationError):
        api().parse_job(b" " * (MAX_PLAN_BYTES + 1))
    job, base, _ = inputs
    # Each base snapshot is legal and compact, but appending new evidence exceeds output budget.
    original = base["snapshots"][0]
    original["bundle"]["document"]["provider"] = "x" * (MAX_PLAN_BYTES // 49 - 2_000)
    base["snapshots"] = [deepcopy(original) for _ in range(49)]
    for snapshot in base["snapshots"]:
        snapshot["snapshot_id"] = str(uuid4())
    parsed = parse_plan(json.dumps(base))
    raw = raw_hwpx("x" * 200_000)
    private_file(Path(job["sources"][0]["raw_path"]), raw)
    job["sources"][0]["version"]["raw_sha256"] = sha256(raw).hexdigest()
    with pytest.raises(api().PreparationError):
        api().prepare_hwpx_plan(api().parse_job(json.dumps(job)), parsed)


def test_raw_owner_and_readonly_private_files(inputs, monkeypatch):
    job, base, _ = inputs
    path = Path(job["sources"][0]["raw_path"])
    path.chmod(0o400)
    assert len(prepare(job, base).snapshots) == 2
    owner = os.geteuid()
    monkeypatch.setattr(os, "geteuid", lambda: owner + 1)
    with pytest.raises(api().PreparationError):
        prepare(job, base)


@pytest.mark.parametrize(
    "field", ["document_id", "version_id", "representation_id", "snapshot_id", "citation_id"]
)
def test_individual_duplicate_ids_are_rejected(inputs, field):
    job, _, _ = inputs
    original = job["sources"][0]
    other = deepcopy(original)
    other["document"]["document_id"] = str(uuid4())
    other["version"]["document_id"] = other["document"]["document_id"]
    other["version"]["version_id"] = str(uuid4())
    other["representation_id"] = str(uuid4())
    other["snapshot_id"] = str(uuid4())
    for citation in other["citations"]:
        citation["citation_id"] = str(uuid4())
    if field == "document_id":
        other["document"][field] = original["document"][field]
        other["version"]["document_id"] = original["document"][field]
    elif field == "version_id":
        other["version"][field] = original["version"][field]
    elif field == "citation_id":
        other["citations"][0][field] = original["citations"][0][field]
    else:
        other[field] = original[field]
    job["sources"].append(other)
    with pytest.raises(api().PreparationError):
        api().parse_job(json.dumps(job))


def test_new_and_existing_conflicting_document_ids_are_rejected(inputs):
    job, base, _ = inputs
    source = job["sources"][0]
    source["document"]["document_id"] = base["snapshots"][0]["bundle"]["document"]["document_id"]
    source["version"]["document_id"] = source["document"]["document_id"]
    with pytest.raises(api().PreparationError):
        prepare(job, base)


def test_job_and_nested_reprs_hide_private_values(inputs):
    job, _, directory = inputs
    value = api().parse_job(json.dumps(job))
    for model in (value, value.sources[0], value.sources[0].license, *value.sources[0].citations):
        for private in (str(directory), "합성", "example.test", job["sources"][0]["snapshot_id"]):
            assert private not in repr(model)


def test_cli_directory_fsync_failure_rolls_back_publication(inputs, monkeypatch, capsys):
    import stat

    original = os.fsync

    def failing(fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            raise OSError("PRIVATE-MARKER")
        return original(fd)

    monkeypatch.setattr(os, "fsync", failing)
    assert cli(inputs) == 1
    assert not (inputs[2] / "result.json").exists()
    assert not any(p.name.startswith(".hwpx-") for p in inputs[2].iterdir())
    assert capsys.readouterr().err == "Unable to prepare HWPX plan\n"


@pytest.mark.parametrize("root", ["job", "base"])
@pytest.mark.parametrize("bypass", ["construct", "copy"])
@pytest.mark.parametrize(
    "kind", ["root_count", "nested_count", "field_bytes", "shared_bytes", "cycle"]
)
def test_forged_input_bounds_before_serialization_and_io(inputs, monkeypatch, root, bypass, kind):
    """Moving bounds after model_dump_json must fail before any serializer or file read."""
    from pydantic import BaseModel

    a = api()
    job = a.parse_job(json.dumps(inputs[0]))
    base = parse_plan(json.dumps(inputs[1]))

    def forge(model, updates):
        if bypass == "copy":
            return model.model_copy(update=updates)
        return type(model).model_construct(**{**model.__dict__, **updates})

    if root == "job":
        source = job.sources[0]
        if kind == "root_count":
            job = forge(job, {"sources": (source,) * 100})
        elif kind == "nested_count":
            source = forge(source, {"citations": (source.citations[0],) * 10_000})
            job = forge(job, {"sources": (source,)})
        elif kind == "field_bytes":
            source = forge(
                source,
                {
                    "document": source.document.model_copy(
                        update={"provider": "x" * (8 * 1024 * 1024 + 1)}
                    )
                },
            )
            job = forge(job, {"sources": (source,)})
        elif kind == "shared_bytes":
            request = forge(source.citations[0], {"quote": "😀" * 100_000})
            source = forge(source, {"citations": (request,) * 100})
            job = forge(job, {"sources": (source,)})
        else:
            source = forge(source, {"document": job})
            object.__setattr__(job, "sources", (source,))
    else:
        snapshot = base.snapshots[0]
        if kind == "root_count":
            base = forge(base, {"snapshots": (snapshot,) * 100})
        elif kind == "nested_count":
            bundle = forge(snapshot.bundle, {"citations": (snapshot.bundle,) * 1_000_000})
            base = forge(base, {"snapshots": (forge(snapshot, {"bundle": bundle}),)})
        elif kind == "field_bytes":
            document = forge(snapshot.bundle.document, {"provider": "x" * (8 * 1024 * 1024 + 1)})
            bundle = forge(snapshot.bundle, {"document": document})
            base = forge(base, {"snapshots": (forge(snapshot, {"bundle": bundle}),)})
        elif kind == "shared_bytes":
            document = forge(snapshot.bundle.document, {"provider": "x" * 200_000})
            bundle = forge(snapshot.bundle, {"document": document})
            base = forge(base, {"snapshots": (forge(snapshot, {"bundle": bundle}),) * 50})
        else:
            snapshot = forge(snapshot, {"bundle": base})
            object.__setattr__(base, "snapshots", (snapshot,))

    serialization_or_io = []

    def forbidden(*args, **kwargs):
        serialization_or_io.append(True)
        raise AssertionError("full serialization/file IO before bounds")

    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    monkeypatch.setattr(os, "open", forbidden)
    with pytest.raises(a.PreparationError):
        a.prepare_hwpx_plan(job, base)
    assert serialization_or_io == []


@pytest.mark.parametrize("root", ["job", "base"])
def test_forged_url_is_bounded_before_wrapper_string_conversion(inputs, monkeypatch, root):
    from pydantic import AnyHttpUrl, BaseModel

    a = api()
    job = a.parse_job(json.dumps(inputs[0]))
    base = parse_plan(json.dumps(inputs[1]))
    oversized = AnyHttpUrl("https://example.test/" + "x" * (8 * 1024 * 1024))
    if root == "job":
        source = job.sources[0]
        document = source.document.model_copy(update={"canonical_url": oversized})
        job = job.model_copy(
            update={"sources": (source.model_copy(update={"document": document}),)}
        )
    else:
        snapshot = base.snapshots[0]
        document = snapshot.bundle.document.model_copy(update={"canonical_url": oversized})
        bundle = snapshot.bundle.model_copy(update={"document": document})
        base = base.model_copy(
            update={"snapshots": (snapshot.model_copy(update={"bundle": bundle}),)}
        )
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("unbounded serialization")

    original_string = AnyHttpUrl.__str__

    def guarded_string(value):
        if value._url == oversized._url:
            return forbidden()
        return original_string(value)

    monkeypatch.setattr(AnyHttpUrl, "__str__", guarded_string)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(a.PreparationError):
        a.prepare_hwpx_plan(job, base)
    assert attempted == []


def test_large_cell_repeated_selectors_reject_before_derived_alias_serialization(
    inputs, monkeypatch
):
    """A tiny job must not expand cell quotes into unbounded alias JSON before output bounds."""
    from issuedigest_worker import prepare as preparation

    job, base, directory = inputs
    # Local synthetic ZIP, never an actual attachment/private QA fixture.
    raw = raw_hwpx(cell_extra="x" * 200_000)
    private_file(directory / "source.hwpx", raw)
    source = job["sources"][0]
    source["version"]["raw_sha256"] = sha256(raw).hexdigest()
    source["citations"] = [
        {
            "kind": "table_cell",
            "citation_id": str(uuid4()),
            "table_id": "s0-t0",
            "cell_id": "s0-t0-r0-c0",
        }
        for _ in range(100)
    ]
    raw_job = json.dumps(job)
    assert len(raw_job.encode()) < 20_000
    validated = api().parse_job(raw_job)
    original_aliases = preparation._aliases
    derived_alias_attempts = []

    def guarded_aliases(snapshots):
        if len(snapshots) > 1:
            derived_alias_attempts.append(True)
            raise AssertionError("derived alias serialization before output budget")
        return original_aliases(snapshots)

    monkeypatch.setattr(preparation, "_aliases", guarded_aliases)
    with pytest.raises(api().PreparationError):
        api().prepare_hwpx_plan(validated, parse_plan(json.dumps(base)))
    assert derived_alias_attempts == []
