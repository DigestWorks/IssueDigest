"""Synthetic structural diagnosis cases; these do not measure AI semantic success."""

import importlib
import importlib.util
import json
from copy import deepcopy
from hashlib import sha256

import pytest
from test_numeric_evidence import document
from test_shared_measurement_context_v2 import anchor, binding, event, packet, scope
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.scope_audit_contract"
    assert importlib.util.find_spec(name) is not None, "Missing pure scope audit contract"
    return importlib.import_module(name)


def generation(src, data=None, *, compact=True, inputs=100, outputs=30):
    """Build validated synthetic receipts without calling any model or generator."""
    frame_api = importlib.import_module("issuedigest_agents.shared_measurement_context_v2")
    mod = importlib.import_module(
        "issuedigest_agents.compact_shared_context"
        if compact
        else "issuedigest_agents.shared_context_generation_v2"
    )
    prompt = mod._preflight(src)[0]
    cls = mod.CompactSharedContextGeneration if compact else mod.SharedContextGenerationV2
    instructions = (
        mod.COMPACT_SHARED_CONTEXT_INSTRUCTIONS if compact else mod.SHARED_CONTEXT_INSTRUCTIONS_V2
    )
    return cls(
        frame=frame_api.build_shared_measurement_frame_v2(src, packet() if data is None else data),
        prompt_sha256=sha256(prompt.encode()).hexdigest(),
        instructions_sha256=sha256(instructions.encode()).hexdigest(),
        usage=importlib.import_module("issuedigest_agents.numeric_evidence").KnownUsage(
            input_tokens=inputs, output_tokens=outputs, requests=1
        ),
    )


def audit_input(*ids, issues=(), incomplete=False, status="no_issue_found"):
    return dict(
        checks=[dict(candidate_id=id, status=status) for id in ids],
        issues=list(issues),
        incomplete=incomplete,
    )


def issue(
    *,
    candidate="n1",
    role="target_scope",
    kind="missing",
    slot=None,
    text="동부",
    sentence="s1",
    support=("s1",),
    context_text=None,
):
    return dict(
        candidate_id=candidate,
        role=role,
        kind=kind,
        scope_slot=slot,
        source_anchor=anchor(text, sentence, context_text) if text is not None else None,
        support_sentence_ids=list(support),
    )


def test_projection_preserves_explicit_context_binding_order_and_original_generation():
    mod = api()
    src = document("발표처는 알렸다. 내년 합성국 동부 청년 이용자 37명과 서부 이용자 59명.")
    data = packet()
    data["contexts"][0].update(
        measured_variable=anchor("이용자", "s2", "청년 이용자"),
        target_scopes=[scope("합성국", "s2")],
        period=anchor("내년", "s2"),
    )
    data["events"][0] = event(
        kind="attributed_report",
        reporting_actor=anchor("발표처"),
        predicate=anchor("알렸다"),
        reporting_tense="past",
    )
    data["bindings"] = [
        binding("n2", target_scopes=[scope("서부", "s2")]),
        binding("n1", target_scopes=[scope("동부", "s2"), scope("청년", "s2", "population")]),
    ]
    original = generation(src, data)
    report = mod.build_scope_audit_report(src, original, audit_input("n2", "n1"))
    assert report.generation == original
    assert [p.candidate_id for p in report.projection] == ["n2", "n1"]
    assert [[(s.slot, s.anchor.text) for s in p.target_scopes] for p in report.projection] == [
        [("r1", "합성국"), ("r2", "서부")],
        [("r1", "합성국"), ("r2", "동부"), ("r3", "청년")],
    ]
    assert report.projection[0].reporting_actor.text == "발표처"
    assert report.projection[0].reporting_tense == "past"
    assert report.projection[0].value_status == "unknown"
    assert report.status == "no_issues_flagged" and report.issues == ()
    assert mod.validate_scope_audit_report(src, json.loads(report.model_dump_json())) == report


@pytest.mark.parametrize("compact", [True, False])
def test_missing_scope_resolves_exact_source_without_repair_for_both_generations(compact):
    mod = api()
    src = document("합성국 동부 이용자 약 37여 명 내외.")
    original = generation(src, compact=compact)
    report = mod.build_scope_audit_report(
        src, original, audit_input("n1", issues=[issue()], status="issues_found")
    )
    assert report.status == "issues_flagged"
    resolved = report.issues[0]
    assert (resolved.source_anchor.span.text, resolved.source_anchor.span.start) == ("동부", 4)
    assert resolved.statement.text == "합성국 동부 이용자 약 37여 명 내외."
    assert report.generation == original
    assert report.generation.frame.facts[0].target_scopes == ()


@pytest.mark.parametrize("case", ["regional", "year", "operator", "affiliation", "ambiguous"])
def test_independent_synthetic_semantic_scenarios_preserve_diagnosis_only(case):
    mod = api()
    data = packet()
    if case == "regional":
        src = document("가상도 동부와 서부 이용자 37명.")
        data["contexts"][0]["target_scopes"] = [scope("가상도"), scope("동부")]
        diagnostic = issue(text="서부")
    elif case == "year":
        src = document("내년 사업 이용자 37명.")
        diagnostic = issue(role="period", text="내년")
    elif case == "operator":
        src = document("운영원은 지역 이용자 37명 사업을 주관한다.")
        data["contexts"][0]["target_scopes"] = [scope("운영원", kind="institutional")]
        diagnostic = issue(kind="unsupported", slot="r1", text="운영원")
    elif case == "affiliation":
        src = document("운영원 소속 이용자 37명.")
        data["contexts"][0]["target_scopes"] = [scope("운영원", kind="institutional")]
        diagnostic = None
    else:
        src = document("기관이 주관한다. 이용자 37명도 거론됐다.")
        diagnostic = issue(kind="uncertain", text=None, support=("s2",))
    raw = audit_input(
        "n1",
        issues=[diagnostic] if diagnostic else [],
        status="uncertain"
        if case == "ambiguous"
        else "no_issue_found"
        if case == "affiliation"
        else "issues_found",
    )
    original = generation(src, data)
    report = mod.build_scope_audit_report(src, original, raw)
    assert report.status == (
        "uncertain"
        if case == "ambiguous"
        else "no_issues_flagged"
        if case == "affiliation"
        else "issues_flagged"
    )
    assert report.generation == original


@pytest.mark.parametrize(
    "incomplete,hard,expected",
    [
        (False, False, "no_issues_flagged"),
        (True, False, "uncertain"),
        (False, True, "issues_flagged"),
        (True, True, "issues_flagged"),
    ],
)
def test_incomplete_never_becomes_a_positive_review(incomplete, hard, expected):
    mod = api()
    src = document("동부 이용자 37명과 서부 이용자 59명.")
    data = packet()
    data["bindings"].append(binding("n2"))
    raw = audit_input(
        "n1", "n2", incomplete=incomplete, status="uncertain" if incomplete else "no_issue_found"
    )
    if hard:
        raw["issues"] = [issue()]
        raw["checks"][0]["status"] = "issues_found"
    result = mod.build_scope_audit_report(src, generation(src, data), raw)
    assert result.status == expected and result.input.incomplete is incomplete
    empty = dict(contexts=[], events=[], bindings=[], relations=[])
    report = mod.build_scope_audit_report(src, generation(src, empty), audit_input())
    assert report.status == "not_applicable"
    for bad in (audit_input(incomplete=True), audit_input("n1")):
        with pytest.raises(mod.ScopeAuditError):
            mod.build_scope_audit_report(src, generation(src, empty), bad)


@pytest.mark.parametrize(
    "change",
    [
        "unknown_candidate",
        "missing_check",
        "duplicate_check",
        "order",
        "contradiction",
        "incomplete_ok",
        "missing_anchor",
        "missing_slot",
        "nonscope_slot",
        "bad_slot",
        "unsupported_null",
        "duplicate",
        "support_gap",
        "support_order",
        "support_other",
        "support_no_expression",
        "anchor_outside",
        "ambiguous_anchor",
        "extra",
        "overflow",
    ],
)
def test_whole_report_rejects_invalid_ids_slots_anchors_support_and_checks(change):
    mod = api()
    src = document("동부 이용자 37명. 설명. 서부 이용자 59명.", "다른 곳 83명.")
    data = packet()
    data["bindings"].append(binding("n2"))
    raw = audit_input("n1", "n2", issues=[issue()], status="no_issue_found")
    raw["checks"][0]["status"] = "issues_found"
    row = raw["issues"][0]
    if change == "unknown_candidate":
        row["candidate_id"] = "n3"
    elif change == "missing_check":
        raw["checks"].pop()
    elif change == "duplicate_check":
        raw["checks"][1] = deepcopy(raw["checks"][0])
    elif change == "order":
        raw["checks"].reverse()
    elif change == "contradiction":
        raw["checks"][0]["status"] = "no_issue_found"
    elif change == "incomplete_ok":
        raw["incomplete"] = True
    elif change == "missing_anchor":
        row["source_anchor"] = None
    elif change == "missing_slot":
        row["scope_slot"] = "r1"
    elif change == "nonscope_slot":
        row.update(role="period", kind="uncertain", scope_slot="r1")
    elif change == "bad_slot":
        row.update(kind="unsupported", scope_slot="r4")
    elif change == "unsupported_null":
        row.update(role="period", kind="unsupported")
    elif change == "duplicate":
        raw["issues"] *= 2
    elif change == "support_gap":
        row["support_sentence_ids"] = ["s1", "s3"]
    elif change == "support_order":
        row["support_sentence_ids"] = ["s2", "s1"]
    elif change == "support_other":
        row["support_sentence_ids"] = ["s3", "s4"]
    elif change == "support_no_expression":
        row["support_sentence_ids"] = ["s2"]
    elif change == "anchor_outside":
        row["source_anchor"] = anchor("다른", "s4")
    elif change == "ambiguous_anchor":
        row["source_anchor"] = anchor("이용자", "s3", "없음")
    elif change == "extra":
        row["approved"] = True
    else:
        raw["issues"] *= 13
    with pytest.raises(mod.ScopeAuditError) as caught:
        mod.build_scope_audit_report(src, generation(src, data), raw)
    assert caught.value.__cause__ is None


@pytest.mark.parametrize(
    "change",
    [
        "generation_dict",
        "generation_subclass",
        "usage_dict",
        "checks_list",
        "check_dict",
        "anchor_dict",
        "issue_subclass",
        "source_list",
    ],
)
def test_actual_canonical_models_and_tuples_precede_any_dump(change):
    from pydantic import Field, create_model

    mod = api()
    src = document("동부 이용자 37명.")
    original = generation(src)
    inp = mod.ScopeAuditInput.model_validate_json(
        json.dumps(audit_input("n1", issues=[issue()], status="issues_found")), strict=True
    )
    if change == "generation_dict":
        original = original.model_dump(mode="json")
    elif change == "generation_subclass":
        cls = create_model(
            "ExtraGeneration",
            __base__=type(original),
            hidden=(str, Field(default="hidden", exclude=True)),
        )
        original = cls.model_validate(original.model_dump())
    elif change == "usage_dict":
        original = original.model_copy(update={"usage": original.usage.model_dump()})
    elif change == "checks_list":
        inp = inp.model_copy(update={"checks": list(inp.checks)})
    elif change == "check_dict":
        inp = inp.model_copy(update={"checks": (inp.checks[0].model_dump(),)})
    elif change == "source_list":
        src = list(src)
    else:
        row = inp.issues[0]
        if change == "anchor_dict":
            row = row.model_copy(update={"source_anchor": row.source_anchor.model_dump()})
        else:
            cls = create_model(
                "ExtraIssue",
                __base__=type(row),
                hidden=(str, Field(default="hidden", exclude=True)),
            )
            row = cls.model_validate(row.model_dump())
        inp = inp.model_copy(update={"issues": (row,)})
    with pytest.raises(mod.ScopeAuditError):
        mod.build_scope_audit_report(src, original, inp)


@pytest.mark.parametrize(
    "field",
    [
        "projection",
        "projection_sha256",
        "source_sha256",
        "status",
        "resolved",
        "generation",
        "input",
        "extra",
        "source",
        "missing_profile",
    ],
)
def test_stored_report_reconstructs_current_generation_projection_diagnosis_and_status(field):
    mod = api()
    src = document("동부 이용자 37명.")
    report = mod.build_scope_audit_report(
        src, generation(src), audit_input("n1", issues=[issue()], status="issues_found")
    )
    raw = json.loads(report.model_dump_json())
    if field == "missing_profile":
        raw.pop("profile")
    elif field == "projection":
        raw["projection"][0]["period"] = anchor("동부")
    elif field.endswith("sha256"):
        raw[field] = "0" * 64
    elif field == "status":
        raw["status"] = "no_issues_flagged"
    elif field == "resolved":
        raw["issues"][0]["source_anchor"]["span"]["text"] = "서부"
    elif field == "generation":
        raw["generation"]["instructions_sha256"] = "0" * 64
    elif field == "input":
        raw["input"]["checks"][0]["status"] = "no_issue_found"
    elif field == "extra":
        raw["certified"] = True
    else:
        src = document("동부 이용자 38명.")
    with pytest.raises(mod.ScopeAuditError):
        mod.validate_scope_audit_report(src, raw)


def test_pure_report_cannot_reinvoke_generators_and_preserves_disambiguated_unicode_span(
    monkeypatch,
):
    mod = api()
    src = document("🧪 동부 이용자와 서부 이용자 약 37여 명 내외. 설명.")
    original = generation(src)

    def forbidden(*args, **kwargs):
        raise AssertionError("A report cannot generate or request a model")

    for name, function in [
        ("compact_shared_context", "run_compact_shared_context_framer"),
        ("shared_context_generation_v2", "run_shared_context_framer_v2"),
    ]:
        monkeypatch.setattr(
            importlib.import_module(f"issuedigest_agents.{name}"), function, forbidden
        )
    raw = audit_input(
        "n1",
        issues=[
            issue(
                role="measured_entity",
                text="이용자",
                context_text="서부 이용자",
                support=("s1", "s2"),
            )
        ],
        status="issues_found",
    )
    report = mod.build_scope_audit_report(src, original, raw)
    span = report.issues[0].source_anchor.span
    assert (span.start, span.end, span.text) == (13, 16, "이용자")
    assert report.issues[0].statement.text == "🧪 동부 이용자와 서부 이용자 약 37여 명 내외. 설명."
    assert report.generation == original
