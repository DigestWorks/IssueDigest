"""Synthetic explicit matrix coverage; no classification accuracy claims."""

import importlib
import importlib.util
import json
from copy import deepcopy
from hashlib import sha256

import pytest
from pydantic import BaseModel, Field, create_model
from test_role_link_catalog import original
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.role_link_contract"
    assert importlib.util.find_spec(name) is not None, "Missing pure role link contract"
    return importlib.import_module(name)


def build(text="현재 3명.", *, rows=("SO",), incomplete=False, numbers=("n1",)):
    mod = api()
    src, gen = original(text, numbers=numbers)
    return (
        mod,
        src,
        gen,
        mod.build_role_link_report(src, gen, dict(rows=list(rows), incomplete=incomplete)),
    )


def digest(value):
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@pytest.mark.parametrize(
    "cell,incomplete,state,roles,status",
    [
        ("SO", False, "classified_roles", ("measurement_scope", "operator"), "reviewed_candidates"),
        (
            "STOREIBP",
            False,
            "classified_roles",
            (
                "measurement_scope",
                "measurement_period",
                "operator",
                "reporter",
                "entity_qualifier",
                "programme_identity",
                "comparison_baseline",
                "purpose",
            ),
            "reviewed_candidates",
        ),
        ("-", False, "explicitly_unrelated", (), "reviewed_candidates"),
        ("?", False, "linkage_uncertain", (), "candidate_review_uncertain"),
        ("_", True, "not_reviewed", (), "candidate_review_incomplete"),
        ("?", True, "linkage_uncertain", (), "candidate_review_incomplete"),
        ("S", True, "classified_roles", ("measurement_scope",), "candidate_review_incomplete"),
    ],
)
def test_explicit_states_roles_and_conservative_status(cell, incomplete, state, roles, status):
    mod, src, gen, report = build(rows=(cell,), incomplete=incomplete)
    assert report.profile == "role-link-report-v1"
    assert report.encoding_version == "role-link-matrix-v1"
    assert report.role_order == "STOREIBP"
    assert report.source_inventory_exhaustive is False
    assert report.catalog.generation == gen
    assert report.status == status
    (decision,) = report.decisions
    assert (decision.hint_id, decision.number, decision.state, decision.roles) == (
        "m1",
        "n1",
        state,
        roles,
    )
    assert report.coverage.model_dump(mode="json") == dict(
        selected_numbers=1,
        total_hints=1,
        candidate_pairs=1,
        classified_pairs=int(state == "classified_roles"),
        unrelated_pairs=int(state == "explicitly_unrelated"),
        uncertain_pairs=int(state == "linkage_uncertain"),
        unreviewed_pairs=int(state == "not_reviewed"),
    )
    cat = importlib.import_module("issuedigest_agents.role_link_catalog")
    assert report.catalog_sha256 == digest(report.catalog.model_dump(mode="json"))
    assert report.domain_sha256 == digest(
        [d.model_dump(mode="json") for d in report.catalog.domains]
    )
    assert report.encoding_sha256 == digest(cat.role_link_encoding_metadata())
    assert mod.validate_role_link_report(src, report) == report
    assert mod.validate_role_link_report(src, json.loads(report.model_dump_json())) == report
    actual_input = mod.RoleLinkInput(rows=(cell,), incomplete=incomplete)
    assert mod.build_role_link_report(src, gen, actual_input) == report


@pytest.mark.parametrize(
    "cell", ["", "OS", "SS", "s", "X", "S ", " S", "S?", "-_", "S;", ";S", "S;;T", "-;?"]
)
def test_bad_cell_order_symbols_and_separator_gaps_are_rejected(cell):
    mod = api()
    src, gen = original("현재 3명.", numbers=("n1",))
    with pytest.raises(mod.RoleLinkContractError):
        mod.build_role_link_report(src, gen, dict(rows=[cell], incomplete=False))


def test_unreviewed_requires_incomplete_and_missing_rows_or_columns_never_fill():
    mod = api()
    src, gen = original("현재 3명. 올해 4명.", numbers=("n2", "n1"))
    for rows in (["_;-", "-;-"], [], ["S;T"], ["S", "T"], ["S;T", "S;T", "S;T"]):
        with pytest.raises(mod.RoleLinkContractError):
            mod.build_role_link_report(src, gen, dict(rows=rows, incomplete=False))
    report = mod.build_role_link_report(src, gen, dict(rows=["SO;-", "?;_"], incomplete=True))
    assert [(d.hint_id, d.number, d.state) for d in report.decisions] == [
        ("m1", "n2", "classified_roles"),
        ("m1", "n1", "explicitly_unrelated"),
        ("m2", "n2", "linkage_uncertain"),
        ("m2", "n1", "not_reviewed"),
    ]
    assert report.coverage.model_dump(mode="json") == dict(
        selected_numbers=2,
        total_hints=2,
        candidate_pairs=4,
        classified_pairs=1,
        unrelated_pairs=1,
        uncertain_pairs=1,
        unreviewed_pairs=1,
    )


@pytest.mark.parametrize(
    "selected,status,rows",
    [((), "not_applicable", [""]), (("n1",), "candidate_inventory_empty", [])],
)
def test_zero_pair_carriers_require_exact_rows_and_complete(selected, status, rows):
    mod = api()
    src, gen = original("현재 3명." if not selected else "3명.", numbers=selected)
    report = mod.build_role_link_report(src, gen, dict(rows=rows, incomplete=False))
    assert report.status == status
    assert report.decisions == ()
    assert report.coverage.selected_numbers == len(selected)
    for bad in (
        dict(rows=rows, incomplete=True),
        dict(rows=["-"] if not selected else [""], incomplete=False),
    ):
        with pytest.raises(mod.RoleLinkContractError):
            mod.build_role_link_report(src, gen, bad)


def test_multiquote_domains_keep_zero_columns_without_erasing_other_pairs():
    mod = api()
    src, gen = original("현재 설명.", "올해 3명.", "4명.", numbers=("n2", "n1"))
    report = mod.build_role_link_report(src, gen, dict(rows=["", "S"], incomplete=False))
    assert report.status == "reviewed_candidates"
    assert [(d.hint_id, d.number) for d in report.decisions] == [("m2", "n1")]
    assert report.coverage.model_dump(mode="json") == dict(
        selected_numbers=2,
        total_hints=2,
        candidate_pairs=1,
        classified_pairs=1,
        unrelated_pairs=0,
        uncertain_pairs=0,
        unreviewed_pairs=0,
    )
    for rows in (["-", "S"], ["", "S;S"], ["S", ""]):
        with pytest.raises(mod.RoleLinkContractError):
            mod.build_role_link_report(src, gen, dict(rows=rows, incomplete=False))


def test_full_quantity_whole_minimal_support_and_repeated_hint_context():
    text = "앞말.\n현재현재 설명.\n\n중간.\n약 3명~5명 이상.\n뒷말."
    mod, src, _, report = build(text, rows=("-", "?"))
    for d, expected_start in zip(report.decisions, (4, 6), strict=True):
        assert d.quantity.text == "약 3명~5명 이상"
        assert d.hint.text == "현재"
        assert d.hint.start == expected_start
        assert d.hint.end == expected_start + 2
        assert d.support.text == "현재현재 설명.\n\n중간.\n약 3명~5명 이상."
        assert d.support_sentence_ids == ("s3", "s4", "s5", "s6", "s7", "s8")
        assert d.support.start == 4
        assert d.support.end == text.index("뒷말") - 1
    assert mod.validate_role_link_report(src, report) == report


def test_support_over_twenty_sentences_is_kept_in_own_report():
    text = "현재.\n" + "중간.\n" * 22 + "3명.\n끝."
    _, _, _, report = build(text, rows=("?",))
    assert len(report.decisions[0].support_sentence_ids) > 20
    assert report.decisions[0].support.text == text[: text.index("끝") - 1]
    assert report.decisions[0].support_sentence_ids[0] == "s1"


def test_exact_288_pair_boundary_has_no_legacy_144_cap():
    text = (
        " ".join(f"'item{chr(65 + i)}'" for i in range(24))
        + " "
        + " ".join(f"{i}명." for i in range(1, 13))
    )
    mod, src, _, report = build(
        text, rows=(";".join(["?"] * 12),) * 24, numbers=tuple(f"n{i}" for i in range(1, 13))
    )
    assert len(report.decisions) == 288
    assert report.coverage.candidate_pairs == report.coverage.uncertain_pairs == 288
    assert (report.decisions[-1].hint_id, report.decisions[-1].number) == ("m24", "n12")
    assert mod.validate_role_link_report(src, report) == report


class StringSubclass(str):
    pass


class ListSubclass(list):
    pass


class TupleSubclass(tuple):
    pass


class DictSubclass(dict):
    pass


def fields(value):
    return value.__dict__ if isinstance(value, BaseModel) else value


def node_at(value, path):
    for part in path:
        value = fields(value)[part]
    return value


TAMPERS = [
    (("profile",), "other"),
    (("encoding_version",), "other"),
    (("role_order",), "BES"),
    (("source_inventory_exhaustive",), True),
    (("catalog_sha256",), "0" * 64),
    (("domain_sha256",), "0" * 64),
    (("encoding_sha256",), "0" * 64),
    (("status",), "candidate_review_uncertain"),
    (("catalog", "profile"), "other"),
    (("catalog", "generation_sha256"), "0" * 64),
    (("catalog", "source_packet_sha256"), "0" * 64),
    (("catalog", "rules_sha256"), "0" * 64),
    (("catalog", "domains", 0, "quote_id"), "q2"),
    (("catalog", "hints", 0, "anchor", "t"), "다른"),
    (("catalog", "generation", "usage", "input_tokens"), 101),
    (("input", "incomplete"), True),
    (("decisions", 0, "hint_id"), "m2"),
    (("decisions", 0, "number"), "n2"),
    (("decisions", 0, "state"), "explicitly_unrelated"),
    (("decisions", 0, "quantity", "text"), "4명"),
    (("decisions", 0, "quantity", "start"), 2),
    (("decisions", 0, "hint", "text"), "다른"),
    (("decisions", 0, "support", "start"), 1),
    (("decisions", 0, "support", "citation_id"), "other"),
    *(
        (("coverage", key), 9)
        for key in (
            "selected_numbers",
            "total_hints",
            "candidate_pairs",
            "classified_pairs",
            "unrelated_pairs",
            "uncertain_pairs",
            "unreviewed_pairs",
        )
    ),
]


@pytest.mark.parametrize("mode", ["actual", "raw"])
@pytest.mark.parametrize("path,replacement", TAMPERS)
def test_every_report_catalog_decision_count_and_hash_is_reconstructed(mode, path, replacement):
    mod, src, _, report = build()
    body = report if mode == "actual" else report.model_dump(mode="json")
    fields(node_at(body, path[:-1]))[path[-1]] = replacement
    with pytest.raises(mod.RoleLinkContractError) as caught:
        mod.validate_role_link_report(src, body)
    assert caught.value.__cause__ is None
    assert "현재" not in str(caught.value)


@pytest.mark.parametrize("mode", ["actual", "raw"])
@pytest.mark.parametrize(
    "mutation",
    [
        "roles",
        "support_ids",
        "rows",
        "missing_decision",
        "extra_decision",
        "domain_numbers",
        "input_cell",
    ],
)
def test_reconstruction_rejects_sequence_and_input_drift(mode, mutation):
    mod, src, _, report = build()
    body = report if mode == "actual" else report.model_dump(mode="json")
    root = fields(body)
    decision = fields(root["decisions"][0])

    def seq(items):
        return tuple(items) if mode == "actual" else list(items)

    if mutation == "roles":
        decision["roles"] = seq(["operator", "measurement_scope"])
    elif mutation == "support_ids":
        decision["support_sentence_ids"] = seq(["s2"])
    elif mutation == "rows":
        fields(root["input"])["rows"] = seq([])
    elif mutation == "input_cell":
        fields(root["input"])["rows"] = seq(["?"])
    elif mutation == "domain_numbers":
        fields(fields(root["catalog"])["domains"][0])["numbers"] = seq([])
    elif mutation == "missing_decision":
        root["decisions"] = seq([])
    elif mutation == "extra_decision":
        root["decisions"] = seq([*root["decisions"], deepcopy(root["decisions"][0])])
    with pytest.raises(mod.RoleLinkContractError):
        mod.validate_role_link_report(src, body)


@pytest.mark.parametrize("mode", ["actual", "raw"])
@pytest.mark.parametrize(
    "mutation",
    [
        "root_marker",
        "generation_marker",
        "index_marker",
        "anchor_default",
        "source_default",
        "input_missing",
        "coverage_missing",
        "decision_missing",
        "string_subclass",
        "bool_int",
        "int_bool",
        "container_swap",
        "container_subclass",
        "model_subclass",
        "nested_model",
    ],
)
def test_nested_strict_guards_run_before_any_serialization(mode, mutation, monkeypatch):
    mod, src, _, report = build()
    body = report if mode == "actual" else report.model_dump(mode="json")
    root = fields(body)
    catalog = fields(root["catalog"])
    stored = fields(catalog["generation"])
    decision = fields(root["decisions"][0])
    if mutation == "root_marker":
        del root["profile"]
    elif mutation == "generation_marker":
        del stored["status"]
    elif mutation == "index_marker":
        del fields(fields(fields(stored["frame"])["frame"])["candidate_index"])["status"]
    elif mutation == "anchor_default":
        del fields(fields(catalog["hints"][0])["anchor"])["c"]
    elif mutation == "source_default":
        del src[1].document.__dict__["canonical_url"]
    elif mutation == "input_missing":
        del fields(root["input"])["incomplete"]
    elif mutation == "coverage_missing":
        del fields(root["coverage"])["uncertain_pairs"]
    elif mutation == "decision_missing":
        del decision["roles"]
    elif mutation == "string_subclass":
        decision["number"] = StringSubclass("n1")
    elif mutation == "bool_int":
        fields(root["coverage"])["classified_pairs"] = True
    elif mutation == "int_bool":
        fields(root["input"])["incomplete"] = 0
    elif mutation == "container_swap":
        root["decisions"] = (
            list(root["decisions"]) if mode == "actual" else tuple(root["decisions"])
        )
    elif mutation == "container_subclass":
        root["decisions"] = (
            TupleSubclass(root["decisions"])
            if mode == "actual"
            else ListSubclass(root["decisions"])
        )
    elif mutation == "model_subclass":
        if mode == "actual":
            subtype = create_model(
                "ExcludedDecision",
                __base__=type(root["decisions"][0]),
                hidden=(str, Field(default="hidden", exclude=True)),
            )
            root["decisions"] = (subtype.model_validate(root["decisions"][0].model_dump()),)
        else:
            root["decisions"][0] = DictSubclass(root["decisions"][0])
    elif mutation == "nested_model":
        decision["quantity"] = (
            decision["quantity"].model_dump(mode="json")
            if mode == "actual"
            else report.decisions[0].quantity
        )
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("guard before dump")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(mod.RoleLinkContractError):
        mod.validate_role_link_report(src, body)
    assert calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "bool",
        "rows_tuple",
        "row_subclass",
        "raw_model",
        "actual_list",
        "source_marker",
        "gen_marker",
    ],
)
def test_build_guards_all_original_inputs_before_any_dump(mutation, monkeypatch):
    mod, src, gen, _ = build()
    data = dict(rows=["SO"], incomplete=False)
    if mutation == "missing":
        del data["incomplete"]
    elif mutation == "bool":
        data["incomplete"] = 0
    elif mutation == "rows_tuple":
        data["rows"] = ("SO",)
    elif mutation == "row_subclass":
        data["rows"] = [StringSubclass("SO")]
    elif mutation == "raw_model":
        data = DictSubclass(data)
    elif mutation == "actual_list":
        data = mod.RoleLinkInput(rows=("SO",), incomplete=False)
        data.__dict__["rows"] = ["SO"]
    elif mutation == "source_marker":
        del src[1].document.__dict__["canonical_url"]
    elif mutation == "gen_marker":
        del gen.__dict__["status"]
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("guard before dump")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(mod.RoleLinkContractError):
        mod.build_role_link_report(src, gen, data)
    assert calls == []


def test_current_source_drift_and_unchecked_negative_counts_are_rejected():
    mod, src, _, report = build()
    changed = deepcopy(src)
    changed[1].representation.__dict__["text"] += " "
    with pytest.raises(mod.RoleLinkContractError):
        mod.validate_role_link_report(changed, report)
    report.coverage.__dict__["unreviewed_pairs"] = -1
    with pytest.raises(mod.RoleLinkContractError):
        mod.validate_role_link_report(src, report)
