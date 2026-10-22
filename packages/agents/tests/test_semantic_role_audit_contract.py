"""Synthetic whole-role coverage and grouped diagnosis; no semantic approval."""

import importlib
import importlib.util
import json
from hashlib import sha256

import pytest
from pydantic import Field, create_model
from test_numeric_evidence import document
from test_role_alias_contract import anchor, packet, source
from test_scope_audit_contract import generation as legacy_generation
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.semantic_role_audit_contract"
    assert importlib.util.find_spec(name) is not None, "Missing role aware audit contract"
    return importlib.import_module(name)


def generation(src=None, data=None, *, profile="new", inputs=100, outputs=30):
    src = source() if src is None else src
    if profile != "new":
        return legacy_generation(
            src, data, compact=profile == "compact", inputs=inputs, outputs=outputs
        )
    mod = importlib.import_module("issuedigest_agents.balanced_role_generation")
    contract = importlib.import_module("issuedigest_agents.role_alias_contract")
    usage = importlib.import_module("issuedigest_agents.numeric_evidence").KnownUsage
    return mod.RoleAliasGenerationV2(
        profile="shared-role-aliases-v2",
        status="unreviewed",
        frame=contract.build_role_alias_frame(src, packet() if data is None else data),
        prompt_sha256=sha256(mod.balanced_role_prompt(src).encode()).hexdigest(),
        instructions_sha256=sha256(mod.BALANCED_ROLE_INSTRUCTIONS.encode()).hexdigest(),
        usage=usage(input_tokens=inputs, output_tokens=outputs, requests=1),
    )


def audit_input(*numbers, issues=(), incomplete=False, status="no_issue_found"):
    return dict(
        checks=[dict(number=n, status=status) for n in numbers],
        issues=list(issues),
        incomplete=incomplete,
    )


def issue(
    *numbers, role="target_scope", kind="missing", slots=None, evidence=None, support=("s1",)
):
    return dict(
        role=role,
        kind=kind,
        evidence=anchor("이용자") if evidence is None else evidence,
        support=list(support),
        targets=[
            dict(number=n, slot=None if slots is None else slots[i]) for i, n in enumerate(numbers)
        ],
    )


@pytest.mark.parametrize("profile", ["new"])
def test_original_concrete_generation_full_proposal_and_explicit_coverage(profile):
    mod = api()
    original = generation(profile=profile)
    report = mod.build_semantic_role_audit_report(source(), original, audit_input("n1"))
    assert report.generation == original and type(report.generation) is type(original)
    assert report.change_coverage == ("available" if profile == "new" else "unavailable")
    assert len(report.roles) == (5 if profile == "new" else 4)
    proposal = report.proposal.model_dump(mode="json")
    assert set(proposal) == {"contexts", "events", "bindings", "relations"}
    assert ("change" in proposal["bindings"][0]) is (profile == "new")
    assert report.status == "no_issues_flagged"
    assert mod.validate_semantic_role_audit_report(source(), report) == report
    assert (
        mod.validate_semantic_role_audit_report(source(), json.loads(report.model_dump_json()))
        == report
    )


def test_full_original_roles_and_scopes_order_preserved_without_repair():
    mod = api()
    src = document("목적 조건 근거 전년비 내년 합성국 동부 이용자 37명 증가.")
    data = packet()
    data["contexts"][0].update(
        purpose=anchor("목적"),
        condition=anchor("조건"),
        basis=anchor("근거"),
        baseline=anchor("전년비"),
        period=anchor("내년"),
        scopes=[dict(kind="geographic", anchor=anchor("합성국"))],
    )
    data["bindings"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("동부"))]
    original = generation(src, data)
    result = mod.build_semantic_role_audit_report(src, original, audit_input("n1"))
    assert result.proposal.model_dump(mode="json") == data
    assert [(s.slot, s.anchor.t) for s in result.scope_slots[0].scopes] == [
        ("r1", "합성국"),
        ("r2", "동부"),
    ]
    assert result.generation == original


def test_group_expands_only_explicit_targets_and_preserves_group_order():
    mod = api()
    data = packet()
    data["bindings"].append(
        dict(number="n2", context="c1", scopes=[], status_sentence=None, change=None)
    )
    original = generation(data=data)
    raw = audit_input("n1", "n2", issues=[issue("n2", "n1")], status="issues_found")
    result = mod.build_semantic_role_audit_report(source(), original, raw)
    assert [i.candidate_id for i in result.issues] == ["n2", "n1"]
    assert all(i.statement.text == source()[1].citations[0].selector.quote for i in result.issues)
    raw["issues"][0]["targets"].pop()
    raw["checks"][0]["status"] = "no_issue_found"
    assert len(mod.build_semantic_role_audit_report(source(), original, raw).issues) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "empty_targets",
        "duplicate_target",
        "duplicate_group",
        "unknown_target",
        "missing_check",
        "order",
        "contradiction",
        "missing_evidence",
        "missing_slot",
        "nonscope_slot",
        "bad_slot",
        "unsupported_null",
        "wrong_support",
        "support_order",
        "support_gap",
        "anchor_outside",
        "extra",
        "group_overflow",
        "target_overflow",
        "legacy_direction",
        "null_direction",
    ],
)
def test_group_target_and_evidence_guards_reject_whole_report(mutation):
    mod = api()
    src = document("이용자 37명 증가. 설명. 학교 83개교 감소.")
    data = packet()
    data["bindings"].append(
        dict(number="n2", context="c1", scopes=[], status_sentence=None, change=None)
    )
    original = generation(src, data)
    raw = audit_input("n1", "n2", issues=[issue("n1")])
    raw["checks"][0]["status"] = "issues_found"
    row = raw["issues"][0]
    if mutation == "empty_targets":
        row["targets"] = []
    elif mutation == "duplicate_target":
        row["targets"] *= 2
    elif mutation == "duplicate_group":
        raw["issues"] *= 2
    elif mutation == "unknown_target":
        row["targets"][0]["number"] = "n99"
    elif mutation == "missing_check":
        raw["checks"].pop()
    elif mutation == "order":
        raw["checks"].reverse()
    elif mutation == "contradiction":
        raw["checks"][0]["status"] = "no_issue_found"
    elif mutation == "missing_evidence":
        row["evidence"] = None
    elif mutation == "missing_slot":
        row["targets"][0]["slot"] = "r1"
    elif mutation == "nonscope_slot":
        row.update(role="period", kind="uncertain")
        row["targets"][0]["slot"] = "r1"
    elif mutation == "bad_slot":
        row.update(kind="unsupported")
        row["targets"][0]["slot"] = "r4"
    elif mutation == "unsupported_null":
        row.update(role="period", kind="unsupported")
    elif mutation == "wrong_support":
        row["support"] = ["s3"]
    elif mutation == "support_order":
        row["support"] = ["s2", "s1"]
    elif mutation == "support_gap":
        row["support"] = ["s1", "s3"]
    elif mutation == "anchor_outside":
        row["evidence"] = anchor("학교", "s3")
    elif mutation == "extra":
        row["approved"] = True
    elif mutation == "group_overflow":
        raw["issues"] *= 13
    elif mutation == "target_overflow":
        row["targets"] *= 13
    elif mutation == "legacy_direction":
        original = generation(src, profile="compact")
        raw = audit_input(
            "n1", issues=[issue("n1", role="change_direction")], status="issues_found"
        )
    else:
        row.update(role="change_direction", kind="unsupported")
        row["targets"][0]["number"] = "n2"
        row["support"] = ["s3"]
        row["evidence"] = anchor("감소", "s3")
        raw["checks"][0]["status"] = "no_issue_found"
        raw["checks"][1]["status"] = "issues_found"
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(src, original, raw)


def test_target_specific_quantity_quote_and_scope_guards():
    mod = api()
    src = document("동부 이용자 37명 증가.", "학교 83개교 감소.")
    data = packet()
    data["bindings"].append(
        dict(number="n2", context="c1", scopes=[], status_sentence=None, change=None)
    )
    # Shared contexts themselves cannot cross quotes with an explicit entity.
    data["contexts"][0]["entity"] = None
    original = generation(src, data)
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(
            src,
            original,
            audit_input(
                "n1",
                "n2",
                issues=[issue("n1", "n2", evidence=anchor("동부"))],
                status="issues_found",
            ),
        )
    src = source()
    data = packet()
    data["contexts"][0]["scopes"] = [dict(kind="other", anchor=anchor("이용자"))]
    data["bindings"].append(
        dict(number="n2", context="c1", scopes=[], status_sentence=None, change=None)
    )
    data["bindings"][0]["scopes"] = [dict(kind="other", anchor=anchor("학교"))]
    original = generation(src, data)
    raw = audit_input(
        "n1",
        "n2",
        issues=[issue("n1", "n2", kind="unsupported", slots=["r2", "r2"])],
        status="issues_found",
    )
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(src, original, raw)
    raw["issues"][0]["targets"][1]["slot"] = "r1"
    assert len(mod.build_semantic_role_audit_report(src, original, raw).issues) == 2


@pytest.mark.parametrize(
    "incomplete,hard", [(False, False), (True, False), (False, True), (True, True)]
)
def test_conservative_status_incomplete_and_nonnull_direction(incomplete, hard):
    mod = api()
    raw = audit_input(
        "n1", incomplete=incomplete, status="uncertain" if incomplete else "no_issue_found"
    )
    if hard:
        raw.update(
            issues=[
                issue("n1", role="change_direction", kind="unsupported", evidence=anchor("증가"))
            ]
        )
        raw["checks"][0]["status"] = "issues_found"
    result = mod.build_semantic_role_audit_report(source(), generation(), raw)
    assert result.status == (
        "issues_flagged" if hard else "uncertain" if incomplete else "no_issues_flagged"
    )
    assert result.input.incomplete is incomplete
    uncertain = issue("n1", kind="uncertain")
    uncertain["evidence"] = None
    assert (
        mod.build_semantic_role_audit_report(
            source(), generation(), audit_input("n1", issues=[uncertain], status="uncertain")
        ).status
        == "uncertain"
    )


def test_explicit_twelve_groups_twelve_targets_expand_144_without_old_limit():
    mod = api()
    src = document(" ".join(f"대상 {i}명" for i in range(31, 43)) + ".")
    data = packet()
    data["contexts"][0]["entity"] = None
    data["bindings"] = [
        dict(number=f"n{i}", context="c1", scopes=[], status_sentence=None, change=None)
        for i in range(1, 13)
    ]
    numbers = [f"n{i}" for i in range(1, 13)]
    groups = [issue(*numbers, evidence=anchor(f"{i}명")) for i in range(31, 43)]
    result = mod.build_semantic_role_audit_report(
        src, generation(src, data), audit_input(*numbers, issues=groups, status="issues_found")
    )
    assert len(result.issues) == 144
    assert (
        mod.validate_semantic_role_audit_report(src, json.loads(result.model_dump_json())) == result
    )


@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "status",
        "source_sha256",
        "generation_sha256",
        "proposal_sha256",
        "coverage_sha256",
        "proposal",
        "coverage",
        "roles",
        "slots",
        "resolved",
        "original_profile",
        "original_status",
        "frame_profile",
        "input_missing",
        "source",
    ],
)
def test_stored_report_reconstructs_all_receipts_and_markers(field):
    mod = api()
    src = source()
    result = mod.build_semantic_role_audit_report(
        src, generation(), audit_input("n1", issues=[issue("n1")], status="issues_found")
    )
    raw = json.loads(result.model_dump_json())
    if field in ("profile", "status"):
        raw.pop(field)
    elif field.endswith("sha256"):
        raw[field] = "0" * 64
    elif field == "proposal":
        raw["proposal"]["contexts"][0]["baseline"] = anchor("이용자")
    elif field == "coverage":
        raw["change_coverage"] = "unavailable"
    elif field == "roles":
        raw["roles"].pop()
    elif field == "slots":
        raw["scope_slots"][0]["number"] = "n2"
    elif field == "resolved":
        raw["issues"][0]["statement"]["text"] = "37"
    elif field.startswith("original_"):
        raw["generation"].pop(field.removeprefix("original_"))
    elif field == "frame_profile":
        raw["generation"]["frame"].pop("profile")
    elif field == "input_missing":
        raw["input"]["issues"][0].pop("evidence")
    else:
        src = document("다름. 이용자 37명 증가.")
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.validate_semantic_role_audit_report(src, raw)


@pytest.mark.parametrize(
    "node",
    [
        "original_dict",
        "original_subclass",
        "usage_dict",
        "source_list",
        "checks_list",
        "target_dict",
        "anchor_dict",
        "issue_subclass",
        "report_proposal_dict",
    ],
)
def test_strict_actual_nested_models_before_serialization(node):
    mod = api()
    src = source()
    original = generation()
    raw = audit_input("n1", issues=[issue("n1")], status="issues_found")
    inp = mod.RoleAwareAuditInput.model_validate_json(json.dumps(raw), strict=True)
    if node == "original_dict":
        original = original.model_dump(mode="json")
    elif node == "original_subclass":
        cls = create_model(
            "ExtraGeneration",
            __base__=type(original),
            secret=(str, Field(default="hidden", exclude=True)),
        )
        original = cls.model_validate(original.model_dump())
    elif node == "usage_dict":
        original = original.model_copy(update={"usage": original.usage.model_dump()})
    elif node == "source_list":
        src = list(src)
    elif node == "checks_list":
        inp = inp.model_copy(update={"checks": list(inp.checks)})
    elif node == "report_proposal_dict":
        report = mod.build_semantic_role_audit_report(src, original, inp)
        report = report.model_copy(update={"proposal": report.proposal.model_dump(mode="json")})
        with pytest.raises(mod.SemanticRoleAuditContractError):
            mod.validate_semantic_role_audit_report(src, report)
        return
    else:
        row = inp.issues[0]
        if node == "target_dict":
            row = row.model_copy(update={"targets": (row.targets[0].model_dump(),)})
        elif node == "anchor_dict":
            row = row.model_copy(update={"evidence": row.evidence.model_dump()})
        else:
            cls = create_model(
                "ExtraIssue",
                __base__=type(row),
                secret=(str, Field(default="hidden", exclude=True)),
            )
            row = cls.model_validate(row.model_dump())
        inp = inp.model_copy(update={"issues": (row,)})
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(src, original, inp)


@pytest.mark.parametrize("profile", ["new"])
@pytest.mark.parametrize("path", ["frame", "index"])
@pytest.mark.parametrize("marker", ["profile", "status"])
def test_stored_original_nested_identity_markers_required_before_defaults(profile, path, marker):
    mod = api()
    result = mod.build_semantic_role_audit_report(
        source(), generation(profile=profile), audit_input("n1")
    )
    raw = json.loads(result.model_dump_json())
    frame = raw["generation"]["frame"]
    if profile == "new":
        frame = frame["frame"]
    node = frame if path == "frame" else frame["candidate_index"]
    node.pop(marker)
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.validate_semantic_role_audit_report(source(), raw)


@pytest.mark.parametrize("profile", ["new"])
@pytest.mark.parametrize("path", ["generation", "frame", "index"])
@pytest.mark.parametrize("marker", ["profile", "status"])
def test_actual_original_missing_identity_rejected_before_any_dump(profile, path, marker):
    mod = api()
    original = generation(profile=profile)
    report = mod.build_semantic_role_audit_report(source(), original, audit_input("n1"))
    # Copy every affected ancestor so immutable shared fixture nodes are preserved.
    original = original.model_copy(deep=True)
    frame = original.frame.frame if profile == "new" else original.frame
    node = original if path == "generation" else frame if path == "frame" else frame.candidate_index
    node.__dict__.pop(marker)
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(source(), original, audit_input("n1"))
    forged_report = report.model_copy(update={"generation": original})
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.validate_semantic_role_audit_report(source(), forged_report)


def semantic_case(name):
    """Hand-authored synthetic diagnosis examples; these do not evaluate a model's judgment."""
    src = document("청년 취업을 위해 특별프로그램 포함 이용자 37명 증가.")
    data = packet()
    context = data["contexts"][0]
    context["purpose"] = anchor("청년 취업")
    raw = audit_input("n1")
    expected = "no_issues_flagged"
    if name == "composition_in_entity":
        context["entity"] = anchor("특별프로그램 포함 이용자")
    elif name == "composition_in_other_scope":
        context["scopes"] = [dict(kind="other", anchor=anchor("특별프로그램 포함"))]
    elif name == "material_entity_loss":
        raw = audit_input(
            "n1",
            issues=[issue("n1", role="measured_entity", evidence=anchor("특별프로그램 포함"))],
            status="issues_found",
        )
        expected = "issues_flagged"
    elif name == "ambiguous_materiality":
        raw = audit_input(
            "n1",
            issues=[
                issue(
                    "n1",
                    role="measured_entity",
                    kind="uncertain",
                    evidence=anchor("특별프로그램 포함"),
                )
            ],
            status="uncertain",
        )
        expected = "uncertain"
    elif name in ("population_restriction", "geographic_restriction", "measurement_year"):
        text, role = {
            "population_restriction": ("청년만", "target_scope"),
            "geographic_restriction": ("동부에서만", "target_scope"),
            "measurement_year": ("2037년", "period"),
        }[name]
        src = document(f"{text} 이용자 37명 증가.")
        context["purpose"] = None
        raw = audit_input(
            "n1", issues=[issue("n1", role=role, evidence=anchor(text))], status="issues_found"
        )
        expected = "issues_flagged"
    elif name == "baseline_instead_of_period":
        src = document("전년비 이용자 37명 증가.")
        context["purpose"] = None
        context["baseline"] = anchor("전년비")
    elif name != "purpose_does_not_restrict_population":
        raise AssertionError("Unknown synthetic case")
    return src, data, raw, expected


SEMANTIC_CASES = [
    "composition_in_entity",
    "composition_in_other_scope",
    "material_entity_loss",
    "ambiguous_materiality",
    "population_restriction",
    "geographic_restriction",
    "measurement_year",
    "baseline_instead_of_period",
    "purpose_does_not_restrict_population",
]


@pytest.mark.parametrize("name", SEMANTIC_CASES)
def test_synthetic_diagnosis_representations_preserve_original_and_exact_evidence(name):
    mod = api()
    src, proposal, raw, expected = semantic_case(name)
    original = generation(src, proposal)
    report = mod.build_semantic_role_audit_report(src, original, raw)
    assert report.status == expected
    assert report.generation == original
    assert report.proposal.model_dump(mode="json") == proposal
    assert report.input.model_dump(mode="json") == raw
    if report.issues:
        assert report.issues[0].source_anchor.span.text == raw["issues"][0]["evidence"]["t"]
        assert report.issues[0].kind == raw["issues"][0]["kind"]
        assert report.issues[0].role == raw["issues"][0]["role"]
    assert mod.validate_semantic_role_audit_report(src, report) == report


@pytest.mark.parametrize("profile", ["new", "v2", "compact"])
def test_historical_generations_cannot_enter_new_report(profile):
    from test_role_aware_audit_contract import generation as historical_generation

    mod = api()
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(
            source(), historical_generation(profile=profile), audit_input("n1")
        )


@pytest.mark.parametrize("actual", [False, True])
@pytest.mark.parametrize(
    "field",
    [
        "profile",
        "generation",
        "source_sha256",
        "generation_sha256",
        "proposal",
        "proposal_sha256",
        "change_coverage",
        "roles",
        "scope_slots",
        "coverage_sha256",
        "input",
        "issues",
        "status",
    ],
)
def test_all_report_fields_required_raw_and_actual(field, actual):
    mod = api()
    report = mod.build_semantic_role_audit_report(source(), generation(), audit_input("n1"))
    altered = report.model_copy(deep=True) if actual else report.model_dump(mode="json")
    del (altered.__dict__ if actual else altered)[field]
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.validate_semantic_role_audit_report(source(), altered)


@pytest.mark.parametrize(
    "evidence",
    [
        anchor("가"),
        anchor("가", context="가가"),
        anchor("가가", context="가가가"),
    ],
)
def test_ambiguous_overlapping_anchor_matches_are_rejected(evidence):
    mod = api()
    src = document("가가가 이용자 37명 증가.")
    with pytest.raises(mod.SemanticRoleAuditContractError):
        mod.build_semantic_role_audit_report(
            src,
            generation(src),
            audit_input("n1", issues=[issue("n1", evidence=evidence)], status="issues_found"),
        )


def test_support_must_include_full_quantity_and_entire_disambiguating_context():
    mod = api()
    src = source()
    original = generation()
    raw = audit_input(
        "n1",
        issues=[issue("n1", evidence=anchor("37", context="약\t37여 명 내외"))],
        status="issues_found",
    )
    report = mod.build_semantic_role_audit_report(src, original, raw)
    assert report.issues[0].statement.text == "이용자 약\t37여 명 내외 증가, 학교 83개교 감소."
    assert report.input.issues[0].evidence.c == "약\t37여 명 내외"
    assert report.issues[0].source_anchor.span.text == "37"
