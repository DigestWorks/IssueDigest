"""Synthetic composition contracts; no provider, storage, or application activation."""

import importlib
import importlib.util
import json
import sys
from copy import deepcopy
from datetime import date, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from pydantic import BaseModel
from test_numeric_evidence import document
from test_question_evidence_propositions import QUESTION, TEXT, packet, proposition, ref


@pytest.fixture(scope="module", autouse=True)
def restore_imports():
    package = importlib.import_module("issuedigest_agents")
    before, attributes, path = set(sys.modules), vars(package).copy(), sys.path.copy()
    yield
    for name in set(sys.modules) - before:
        if name.startswith("issuedigest_agents."):
            sys.modules.pop(name, None)
    for name in set(vars(package)) - attributes.keys():
        delattr(package, name)
    for name, value in attributes.items():
        setattr(package, name, value)
    sys.path[:] = path


def api():
    name = "issuedigest_agents.question_briefing"
    assert importlib.util.find_spec(name) is not None, "Missing question briefing composition"
    return importlib.import_module(name)


def source(text=TEXT, *extra):
    sid, bundle, presentation = document(text, *extra)
    raw = bundle.model_dump_json()
    for identifier in (bundle.document.document_id, bundle.version.version_id):
        raw = raw.replace(str(identifier), str(uuid4()))
    return sid, EvidenceBundle.model_validate_json(raw), presentation


def receipt(src, data=None):
    guarded = importlib.import_module("issuedigest_agents.guarded_question_evidence_v2")
    evidence = importlib.import_module("issuedigest_agents.question_evidence_propositions")
    prompt, _ = guarded._preflight(src, QUESTION)
    return guarded.GuardedQuestionEvidenceGenerationV2(
        profile="guarded-question-evidence-v2",
        transport_profile="guarded-responses-tool-v1",
        input_format="question-evidence-source-v2",
        status="unreviewed",
        evidence=evidence.build_question_evidence_propositions(src, QUESTION, data or packet(src)),
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        instructions_sha256=sha256(guarded.GUARDED_QUESTION_V2_INSTRUCTIONS.encode()).hexdigest(),
        usage=guarded.KnownUsage(input_tokens=10, output_tokens=5, requests=1),
    )


def reference(src, identifier="p1"):
    return dict(snapshot_id=str(src[0]), proposition_id=identifier)


def claim(*refs, text="자료에 따르면 조건이 있다.", event_date=None):
    return dict(text=text, references=list(refs), event_date=event_date)


def proposal(*claims):
    return dict(
        outcome="answer",
        message=None,
        modules=[dict(kind="summary", title="요약", claims=list(claims))],
    )


def setup():
    src = source()
    return api(), src, receipt(src), proposal(claim(reference(src)))


def reject(operation, *args):
    mod = api()
    with pytest.raises(mod.QuestionBriefingError) as caught:
        operation(*args)
    assert str(caught.value) == "Invalid question briefing"
    assert caught.value.__cause__ is None and caught.value.__context__ is None


def test_multisource_preserves_full_receipts_and_derives_dependency_uncertainty_coverage():
    mod = api()
    first, second = source(), source(TEXT + " 2026-10-26")
    data = packet(first)
    data["propositions"] += [
        proposition(first, "p2", depends_on_ids=["p3"]),
        proposition(first, "p3", epistemic_status="uncertain", subject_refs=[]),
        proposition(first, "p4"),
    ]
    data["propositions"][0]["depends_on_ids"] = ["p2"]
    data["coverage"] = dict(linked_proposition_ids=["p4", "p1"], unresolved_reason="ambiguous")
    receipts = (receipt(first, data), receipt(second))
    submitted = proposal(claim(reference(first)), claim(reference(second)))
    got = mod.build_question_briefing(QUESTION, (first, second), receipts, submitted)
    assert got.profile == "question-briefing-v1" and got.status == "unreviewed"
    assert got.question_sha256 == sha256(QUESTION.encode()).hexdigest()
    assert got.workspace_id == first[1].document.workspace_id
    assert tuple(item.snapshot_id for item in got.sources) == (first[0], second[0])
    assert tuple(item.receipt for item in got.sources) == receipts
    assert [c.epistemic_status for c in got.modules[0].claims] == ["uncertain", "source_statement"]
    coverage = got.coverage[0]
    assert coverage.snapshot_id == first[0]
    assert coverage.linked_proposition_ids == ("p1", "p4")
    assert coverage.closure_proposition_ids == ("p1", "p2", "p3", "p4")
    assert coverage.used_proposition_ids == ("p1", "p2", "p3")
    assert coverage.uncovered_linked_proposition_ids == ("p4",)
    assert coverage.unresolved_reason == "ambiguous"
    assert got.proposal.model_dump(mode="json") == submitted
    assert got == mod.build_question_briefing(QUESTION, (first, second), receipts, submitted)
    for saved in (got, json.loads(got.model_dump_json())):
        checked = mod.validate_question_briefing(QUESTION, (first, second), receipts, saved)
        assert checked == got and checked is not got


def test_insufficient_preserves_every_source_and_unrepresented_link():
    mod, src, rec, _ = setup()
    empty = source()
    no_link = dict(
        propositions=[],
        coverage=dict(linked_proposition_ids=[], unresolved_reason="no_linked_evidence"),
    )
    receipts = (rec, receipt(empty, no_link))
    submitted = dict(outcome="insufficient_evidence", message="근거가 부족합니다.", modules=[])
    got = mod.build_question_briefing(QUESTION, (src, empty), receipts, submitted)
    assert got.modules == () and got.message == submitted["message"]
    assert got.coverage[0].used_proposition_ids == ()
    assert got.coverage[0].uncovered_linked_proposition_ids == ("p1",)
    assert got.coverage[1].unresolved_reason == "no_linked_evidence"
    assert tuple(item.receipt for item in got.sources) == receipts
    assert mod.validate_question_briefing(QUESTION, (src, empty), receipts, got) == got


@pytest.mark.parametrize(
    "kind",
    ["unrelated", "unknown", "wrong_source", "duplicate", "dependency_only", "no_link", "cycle"],
)
def test_references_require_current_local_link_or_dependency_and_some_direct_link(kind):
    mod, src, rec, submitted = setup()
    data = packet(src)
    data["propositions"] += [proposition(src, "p2"), proposition(src, "p3")]
    data["propositions"][0]["depends_on_ids"] = ["p2"]
    if kind == "cycle":
        data["propositions"][1]["depends_on_ids"] = ["p1"]
        # Corrupt an otherwise validated receipt: builder must recheck the whole graph.
        rec = receipt(src)
        evidence = importlib.import_module("issuedigest_agents.question_evidence_propositions")
        bad = evidence.QuestionEvidenceInput.model_validate_json(json.dumps(data), strict=True)
        rec = rec.model_copy(
            update={"evidence": rec.evidence.model_copy(update={"propositions": bad.propositions})}
        )
    else:
        if kind == "no_link":
            data["coverage"] = dict(linked_proposition_ids=[], unresolved_reason="insufficient")
        rec = receipt(src, data)
    target = submitted["modules"][0]["claims"][0]["references"]
    if kind == "unrelated":
        target[0]["proposition_id"] = "p3"
    elif kind in ("dependency_only", "no_link"):
        target[0]["proposition_id"] = "p2"
    elif kind == "unknown":
        target[0]["proposition_id"] = "p24"
    elif kind == "wrong_source":
        target[0]["snapshot_id"] = str(uuid4())
    elif kind == "duplicate":
        target.append(deepcopy(target[0]))
    reject(mod.build_question_briefing, QUESTION, (src,), (rec,), submitted)


def test_linked_plus_dependency_reference_is_allowed_without_flattening():
    mod, src, _, submitted = setup()
    data = packet(src)
    data["propositions"].append(proposition(src, "p2"))
    data["propositions"][0]["depends_on_ids"] = ["p2"]
    submitted["modules"][0]["claims"].append(claim(reference(src, "p2")))
    got = mod.build_question_briefing(QUESTION, (src,), (receipt(src, data),), submitted)
    assert len(got.sources[0].receipt.evidence.propositions[0].facets) == 9
    assert got.coverage[0].used_proposition_ids == ("p1", "p2")


@pytest.mark.parametrize(
    "kind",
    [
        "exact",
        "metadata",
        "unrelated_quote",
        "dependency",
        "partial",
        "invalid_date",
        "non_timeline",
    ],
)
def test_dates_only_anchor_to_direct_proposition_support(kind):
    mod = api()
    text = TEXT + (" 2026-10-26" if kind in ("exact", "partial", "non_timeline") else "")
    if kind == "partial":
        text += "0"
    src = source(text, "2026-10-26")
    data = packet(src)
    if kind == "metadata":
        src = (src[0], src[1], src[2].model_copy(update={"bill_number": "2026-10-26"}))
    if kind == "dependency":
        data["propositions"].append(
            proposition(
                src,
                "p2",
                supporting_refs=[ref(src, "2026-10-26", 1)],
                subject_refs=[],
                predicate_refs=[],
                epistemic_status="uncertain",
            )
        )
        data["propositions"][0]["depends_on_ids"] = ["p2"]
    rec = receipt(src, data)
    submitted = proposal(claim(reference(src)))
    dated = claim(
        reference(src), event_date="2026-10-26" if kind != "invalid_date" else "2026-02-30"
    )
    if kind == "non_timeline":
        submitted["modules"][0]["claims"] = [dated]
    else:
        submitted["modules"].append(dict(kind="timeline", title="시간축", claims=[dated]))
    if kind == "exact":
        got = mod.build_question_briefing(QUESTION, (src,), (rec,), submitted)
        assert got.modules[1].claims[0].event_date == date(2026, 10, 26)
        assert (
            mod.validate_question_briefing(
                QUESTION, (src,), (rec,), json.loads(got.model_dump_json())
            )
            == got
        )
    else:
        reject(mod.build_question_briefing, QUESTION, (src,), (rec,), submitted)


@pytest.mark.parametrize(
    "kind",
    [
        "question",
        "question_bool",
        "question_long",
        "blank",
        "source_metadata",
        "source_quote",
        "prompt",
        "instructions",
        "usage",
        "receipt_order",
        "receipt_missing",
        "raw_receipt",
        "sources_list",
        "empty",
        "six",
        "snapshot_duplicate",
        "version_duplicate",
        "citation_duplicate",
        "workspace",
    ],
)
def test_all_sources_receipts_and_original_question_are_rechecked(kind):
    mod, src, rec, submitted = setup()
    sources, receipts, question = (src,), (rec,), QUESTION
    if kind == "question":
        question += " "
    elif kind == "question_bool":
        question = True
    elif kind == "question_long":
        question = "x" * 1501
    elif kind == "blank":
        question = " "
    elif kind in ("source_metadata", "source_quote"):
        target, field = (
            (src[2], "title")
            if kind == "source_metadata"
            else (src[1].citations[0].selector, "quote")
        )
        object.__setattr__(target, field, "sensitive changed source")
    elif kind in ("prompt", "instructions"):
        receipts = (rec.model_copy(update={kind + "_sha256": "0" * 64}),)
    elif kind == "usage":
        receipts = (
            rec.model_copy(update={"usage": rec.usage.model_copy(update={"requests": True})}),
        )
    elif kind == "receipt_missing":
        receipts = ()
    elif kind == "raw_receipt":
        receipts = (rec.model_dump(mode="json"),)
    elif kind == "sources_list":
        sources = [src]
    elif kind == "empty":
        sources, receipts = (), ()
    elif kind == "six":
        sources, receipts = (src,) * 6, (rec,) * 6
    else:
        other = source()
        if kind == "workspace":
            wid = uuid4()
            other = (
                other[0],
                other[1].model_copy(
                    update={"document": other[1].document.model_copy(update={"workspace_id": wid})}
                ),
                other[2].model_copy(update={"workspace_id": wid}),
            )
        if kind == "snapshot_duplicate":
            other = (src[0], other[1], other[2].model_copy(update={"snapshot_id": src[0]}))
        if kind in ("version_duplicate", "citation_duplicate"):
            raw = other[1].model_dump_json()
            old, new = (
                (other[1].version.version_id, src[1].version.version_id)
                if kind == "version_duplicate"
                else (other[1].citations[0].citation_id, src[1].citations[0].citation_id)
            )
            other = (
                other[0],
                EvidenceBundle.model_validate_json(raw.replace(str(old), str(new))),
                other[2],
            )
        sources, receipts = (src, other), (rec, receipt(other))
        if kind == "receipt_order":
            receipts = tuple(reversed(receipts))
    reject(mod.build_question_briefing, question, sources, receipts, submitted)


@pytest.mark.parametrize(
    "kind",
    [
        "category",
        "extra",
        "missing_message",
        "missing_date",
        "blank_title",
        "blank_text",
        "long_text",
        "long_title",
        "zero_claim",
        "five_claims",
        "four_modules",
        "comparison_one",
        "timeline_null",
        "late_summary",
        "first_comparison",
        "answer_message",
        "insufficient_modules",
        "insufficient_no_message",
        "insufficient_long_message",
        "bad_kind",
        "bool_text",
        "tuple_raw",
        "string_subclass",
        "model_copy",
        "model_construct",
        "datetime",
    ],
)
def test_proposal_strict_shape_and_module_semantics(kind):
    mod, src, rec, submitted = setup()
    module, item = submitted["modules"][0], submitted["modules"][0]["claims"][0]
    if kind == "category":
        item["category"] = "documented"
    elif kind == "extra":
        submitted["action"] = "execute"
    elif kind == "missing_message":
        del submitted["message"]
    elif kind == "missing_date":
        del item["event_date"]
    elif kind == "blank_title":
        module["title"] = " "
    elif kind == "blank_text":
        item["text"] = "\t"
    elif kind == "long_text":
        item["text"] = "x" * 401
    elif kind == "long_title":
        module["title"] = "x" * 101
    elif kind == "zero_claim":
        module["claims"] = []
    elif kind == "five_claims":
        module["claims"] *= 5
    elif kind == "four_modules":
        submitted["modules"] *= 4
    elif kind == "comparison_one":
        submitted["modules"].append(dict(module, kind="comparison"))
    elif kind == "timeline_null":
        submitted["modules"].append(dict(module, kind="timeline"))
    elif kind == "late_summary":
        submitted["modules"].append(deepcopy(module))
    elif kind == "first_comparison":
        module["kind"] = "comparison"
        module["claims"] *= 2
    elif kind == "answer_message":
        submitted["message"] = "unexpected"
    elif kind == "insufficient_modules":
        submitted["outcome"] = "insufficient_evidence"
        submitted["message"] = "missing"
    elif kind in ("insufficient_no_message", "insufficient_long_message"):
        submitted = dict(
            outcome="insufficient_evidence",
            message=None if kind == "insufficient_no_message" else "x" * 501,
            modules=[],
        )
    elif kind == "bad_kind":
        module["kind"] = "html"
    elif kind == "bool_text":
        item["text"] = True
    elif kind == "tuple_raw":
        item["references"] = tuple(item["references"])
    elif kind == "string_subclass":

        class Text(str):
            pass

        item["text"] = Text(item["text"])
    elif kind in ("model_copy", "model_construct", "datetime"):
        actual = mod.QuestionBriefingProposal.model_validate_json(
            json.dumps(submitted), strict=True
        )
        if kind == "model_copy":
            submitted = actual.model_copy(update={"modules": list(actual.modules)})
        elif kind == "model_construct":
            submitted = mod.QuestionBriefingProposal.model_construct(
                **dict(actual.__dict__, message=False)
            )
        else:
            changed = (
                actual.modules[0]
                .claims[0]
                .model_copy(update={"event_date": datetime(2026, 10, 26)})
            )
            submitted = actual.model_copy(
                update={"modules": (actual.modules[0].model_copy(update={"claims": (changed,)}),)}
            )
    reject(mod.build_question_briefing, QUESTION, (src,), (rec,), submitted)


def paths(value, prefix=()):
    if type(value) is dict:
        for key, child in value.items():
            yield (*prefix, key)
            yield from paths(child, (*prefix, key))
    elif type(value) is list:
        for i, child in enumerate(value):
            yield from paths(child, (*prefix, i))


@pytest.mark.parametrize("actual", [False, True])
def test_every_saved_field_required_even_null_or_empty(actual):
    mod, src, rec, submitted = setup()
    got = mod.build_question_briefing(QUESTION, (src,), (rec,), submitted)
    for path in paths(got.model_dump(mode="json")):
        changed = deepcopy(got) if actual else got.model_dump(mode="json")
        parent = changed
        for key in path[:-1]:
            parent = getattr(parent, key) if isinstance(parent, BaseModel) else parent[key]
        del (parent.__dict__ if isinstance(parent, BaseModel) else parent)[path[-1]]
        reject(mod.validate_question_briefing, QUESTION, (src,), (rec,), changed)


@pytest.mark.parametrize(
    "kind",
    [
        "profile",
        "status",
        "question_hash",
        "workspace",
        "text",
        "category",
        "date",
        "coverage",
        "receipt",
        "proposal",
        "extra",
        "order",
    ],
)
def test_rebuild_compares_every_saved_value(kind):
    mod, src, rec, submitted = setup()
    submitted["modules"][0]["claims"].append(claim(reference(src), text="두 번째 미검토 문장"))
    got = mod.build_question_briefing(QUESTION, (src,), (rec,), submitted)
    raw = got.model_dump(mode="json")
    if kind == "profile":
        raw["profile"] = "research-v10"
    elif kind == "status":
        raw["status"] = "reviewed"
    elif kind == "question_hash":
        raw["question_sha256"] = "0" * 64
    elif kind == "workspace":
        raw["workspace_id"] = str(uuid4())
    elif kind == "text":
        raw["modules"][0]["claims"][0]["text"] = "forged"
    elif kind == "category":
        raw["modules"][0]["claims"][0]["epistemic_status"] = "uncertain"
    elif kind == "date":
        raw["modules"][0]["claims"][0]["event_date"] = "2026-10-26"
    elif kind == "coverage":
        raw["coverage"][0]["used_proposition_ids"] = []
    elif kind == "receipt":
        raw["sources"][0]["receipt"]["usage"]["input_tokens"] += 1
    elif kind == "proposal":
        raw["proposal"]["modules"][0]["claims"][0]["text"] = "forged"
    elif kind == "extra":
        raw["untrusted"] = "sensitive"
    else:
        raw["modules"][0]["claims"].reverse()
    reject(mod.validate_question_briefing, QUESTION, (src,), (rec,), raw)


def test_plain_untrusted_text_and_typed_proposal_work_without_network_or_app_imports(monkeypatch):
    import socket

    before = set(sys.modules)
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("Unexpected network"))
    mod, src, rec, submitted = setup()
    submitted["modules"][0]["claims"][0]["text"] = "<script>untrusted prose</script>"
    actual = mod.QuestionBriefingProposal.model_validate_json(json.dumps(submitted), strict=True)
    got = mod.build_question_briefing(QUESTION, (src,), (rec,), actual)
    assert got.modules[0].claims[0].text == "<script>untrusted prose</script>"
    assert got.status == "unreviewed"
    assert not any(
        name.startswith(("issuedigest_api", "issuedigest_worker", "dbos"))
        for name in set(sys.modules) - before
    )


@pytest.mark.parametrize("kind", ["prompt", "instructions", "usage", "question", "metadata"])
def test_unreferenced_source_receipt_is_never_skipped(kind):
    mod, first, first_receipt, submitted = setup()
    second = source()
    second_receipt = receipt(second)
    if kind in ("prompt", "instructions"):
        second_receipt = second_receipt.model_copy(update={kind + "_sha256": "0" * 64})
    elif kind == "usage":
        second_receipt = second_receipt.model_copy(
            update={"usage": second_receipt.usage.model_copy(update={"output_tokens": 4001})}
        )
    elif kind == "question":
        second_receipt = second_receipt.model_copy(
            update={
                "evidence": second_receipt.evidence.model_copy(update={"question_sha256": "0" * 64})
            }
        )
    else:
        second = (second[0], second[1], second[2].model_copy(update={"title": "changed"}))
    reject(
        mod.build_question_briefing,
        QUESTION,
        (first, second),
        (first_receipt, second_receipt),
        submitted,
    )


@pytest.mark.parametrize(
    "kind",
    [
        "source",
        "receipt",
        "proposal",
        "saved",
        "scalar",
        "container",
        "field_key",
        "extra_model",
        "raw_dict",
        "raw_list",
        "raw_int",
        "raw_uuid",
        "raw_date",
    ],
)
def test_original_subclasses_and_unchecked_copies_are_rejected_before_normalization(kind):
    mod, src, rec, submitted = setup()
    sources, receipts = (src,), (rec,)
    actual = mod.QuestionBriefingProposal.model_validate_json(json.dumps(submitted), strict=True)
    if kind == "source":

        class SourceTuple(tuple):
            pass

        sources = (SourceTuple(src),)
    elif kind == "receipt":

        class ChildReceipt(type(rec)):
            pass

        receipts = (ChildReceipt(**rec.__dict__),)
    elif kind == "proposal":

        class ChildProposal(mod.QuestionBriefingProposal):
            pass

        submitted = ChildProposal(**actual.__dict__)
    elif kind == "saved":
        got = mod.build_question_briefing(QUESTION, sources, receipts, actual)

        class ChildBriefing(mod.QuestionBriefing):
            pass

        reject(
            mod.validate_question_briefing,
            QUESTION,
            sources,
            receipts,
            ChildBriefing(**got.__dict__),
        )
        return
    elif kind in ("scalar", "field_key", "extra_model"):

        class TextSubclass(str):
            pass

        submitted = deepcopy(actual)
        item = submitted.modules[0].claims[0]
        if kind == "scalar":
            item.__dict__["text"] = TextSubclass(item.text)
        elif kind == "field_key":
            item.__dict__[TextSubclass("text")] = item.__dict__.pop("text")
        else:
            item.__dict__["extra"] = "sensitive"
    elif kind == "container":
        submitted = actual.model_copy(update={"modules": list(actual.modules)})
    elif kind == "raw_dict":

        class Object(dict):
            pass

        submitted = Object(submitted)
    elif kind == "raw_list":

        class Array(list):
            pass

        submitted["modules"] = Array(submitted["modules"])
    elif kind == "raw_int":

        class Integer(int):
            pass

        receipts = (
            rec.model_copy(
                update={"usage": rec.usage.model_copy(update={"input_tokens": Integer(10)})}
            ),
        )
    elif kind == "raw_uuid":
        submitted["modules"][0]["claims"][0]["references"][0]["snapshot_id"] = 1
    else:
        submitted["modules"][0]["claims"][0]["event_date"] = 1792972800
    reject(mod.build_question_briefing, QUESTION, sources, receipts, submitted)


def test_five_sources_comparison_and_date_in_other_claim_support():
    mod = api()
    sources = tuple(source(TEXT + " (2026-10-26).") for _ in range(5))
    receipts = tuple(receipt(src) for src in sources)
    submitted = proposal(claim(*(reference(src) for src in sources)))
    submitted["modules"] += [
        dict(
            kind="comparison", title="비교", claims=[claim(reference(src)) for src in sources[:4]]
        ),
        dict(
            kind="timeline",
            title="시점",
            claims=[claim(reference(sources[0]), event_date="2026-10-26")],
        ),
    ]
    got = mod.build_question_briefing(QUESTION, sources, receipts, submitted)
    assert len(got.sources) == 5 and len(got.modules[1].claims) == 4
    assert all(item.used_proposition_ids == ("p1",) for item in got.coverage)
    assert got.modules[2].claims[0].event_date == date(2026, 10, 26)
    assert mod.validate_question_briefing(QUESTION, sources, receipts, got) == got


def test_date_elsewhere_in_same_quote_is_not_support():
    mod = api()
    src = source(TEXT + " 2026-10-26")
    data = packet(src)
    data["propositions"][0]["supporting_refs"] = [ref(src, TEXT)]
    submitted = proposal(claim(reference(src)))
    submitted["modules"].append(
        dict(kind="timeline", title="날짜", claims=[claim(reference(src), event_date="2026-10-26")])
    )
    reject(mod.build_question_briefing, QUESTION, (src,), (receipt(src, data),), submitted)
