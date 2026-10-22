"""Synthetic current receipts and lexical witnesses, never semantic certification."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256

import pytest
from pydantic import BaseModel, create_model
from test_numeric_evidence import document
from test_role_alias_contract import anchor
from test_role_link_catalog import original
from test_semantic_role_audit_contract import generation
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.role_reference_coverage"
    assert importlib.util.find_spec(name) is not None, "Missing pure role reference coverage"
    return importlib.import_module(name)


def receipt(src, gen, cells=None):
    """Construct canonical public synthetic SDK receipts without invoking a Model."""
    sdk = importlib.import_module("issuedigest_agents.role_link_sdk")
    contract = importlib.import_module("issuedigest_agents.role_link_contract")
    catalog = importlib.import_module("issuedigest_agents.role_link_catalog")
    usage = importlib.import_module("issuedigest_agents.numeric_evidence").KnownUsage
    cat = catalog.build_role_link_catalog(src, gen)
    domains = {d.quote_id: d.numbers for d in cat.domains}
    rows = (
        [";".join("SE" for _ in domains[h.quote_id]) for h in cat.hints] if cells is None else cells
    )
    report = contract.build_role_link_report(
        src, gen, dict(rows=rows, incomplete=any("_" in r for r in rows))
    )
    selected = bool(report.decisions)
    link_usage = usage(input_tokens=10, output_tokens=5, requests=1) if selected else None
    combined = (
        usage(
            input_tokens=gen.usage.input_tokens + 10,
            output_tokens=gen.usage.output_tokens + 5,
            requests=2,
        )
        if selected
        else gen.usage
    )
    result = sdk.RoleLinkGeneration(
        profile="role-link-generation-v1",
        input_format="named-columns-matrix-v1",
        report=report,
        prompt_sha256=sha256(sdk.role_link_prompt(src, gen).encode()).hexdigest(),
        instructions_sha256=sha256(sdk.ROLE_LINK_INSTRUCTIONS.encode()).hexdigest(),
        link_usage=link_usage,
        combined_usage=combined,
    )
    return sdk.validate_role_link_generation(src, result)


def packet(numbers=("n1", "n2")):
    return dict(
        contexts=[
            dict(
                id="c1",
                event="e1",
                entity=anchor("서울"),
                period=anchor("현재"),
                condition=anchor("서울·부산"),
                purpose=anchor("부산"),
                basis=anchor("합성부"),
                baseline=anchor("서울"),
                status="unknown",
                scopes=[dict(kind="geographic", anchor=anchor("서울·부산"))],
            )
        ],
        events=[
            dict(
                id="e1",
                kind="attributed_report",
                actor=anchor("부산"),
                predicate=anchor("증가"),
                tense="unknown",
            )
        ],
        bindings=[
            dict(
                number=n,
                context="c1",
                scopes=([dict(kind="institutional", anchor=anchor("합성부"))] if n == "n1" else []),
                status_sentence="s1" if n == "n1" else None,
                change=dict(direction="increase", evidence=anchor("증가"), support=["s1"])
                if n == "n1"
                else None,
            )
            for n in numbers
        ],
        relations=[
            dict(kind="unknown", **{"from": "n1", "to": "n2"}, support=["s1"], cue=anchor("·"))
        ]
        if len(numbers) > 1
        else [],
    )


def full():
    src = document("현재 서울·부산 합성부는 3명 증가 4명.")
    return src, receipt(src, generation(src, packet()))


def build(text="현재 3명.", *, numbers=("n1",), data=None, cells=None):
    mod = api()
    if data is None:
        src, gen = original(text, numbers=numbers)
    else:
        src = document(text)
        gen = generation(src, data)
    link = receipt(src, gen, cells)
    return mod, src, link, mod.build_role_reference_coverage(src, link)


def test_literal_binding_major_inventory_every_field_owner_path_and_id():
    mod = api()
    src, link = full()
    result = mod.build_role_reference_coverage(src, link)
    expected = [
        ("n1", "contexts/c1/entity", "entity", "primary", "서울"),
        ("n1", "contexts/c1/period", "period", "primary", "현재"),
        ("n1", "contexts/c1/condition", "condition", "primary", "서울·부산"),
        ("n1", "contexts/c1/purpose", "purpose", "primary", "부산"),
        ("n1", "contexts/c1/basis", "basis", "primary", "합성부"),
        ("n1", "contexts/c1/baseline", "baseline", "primary", "서울"),
        ("n1", "contexts/c1/scopes/0/anchor", "context_scope", "primary", "서울·부산"),
        ("n1", "bindings/n1/scopes/0/anchor", "binding_scope", "primary", "합성부"),
        ("n1", "events/e1/actor", "reporting_actor", "primary", "부산"),
        ("n1", "events/e1/predicate", "reporting_predicate", "auxiliary", "증가"),
        ("n1", "bindings/n1/change/evidence", "change_evidence", "auxiliary", "증가"),
        ("n1", "relations/0/cue", "relation_cue", "auxiliary", "·"),
        ("n1", "quantities/n1/expression", "quantity", "auxiliary", "3명"),
        (
            "n1",
            "bindings/n1/status_sentence",
            "status_context",
            "auxiliary",
            "현재 서울·부산 합성부는 3명 증가 4명.",
        ),
        ("n2", "contexts/c1/entity", "entity", "primary", "서울"),
        ("n2", "contexts/c1/period", "period", "primary", "현재"),
        ("n2", "contexts/c1/condition", "condition", "primary", "서울·부산"),
        ("n2", "contexts/c1/purpose", "purpose", "primary", "부산"),
        ("n2", "contexts/c1/basis", "basis", "primary", "합성부"),
        ("n2", "contexts/c1/baseline", "baseline", "primary", "서울"),
        ("n2", "contexts/c1/scopes/0/anchor", "context_scope", "primary", "서울·부산"),
        ("n2", "events/e1/actor", "reporting_actor", "primary", "부산"),
        ("n2", "events/e1/predicate", "reporting_predicate", "auxiliary", "증가"),
        ("n2", "relations/0/cue", "relation_cue", "auxiliary", "·"),
        ("n2", "quantities/n2/expression", "quantity", "auxiliary", "4명"),
    ]
    assert [
        (c.number, c.path, c.field, c.category, c.span.text) for c in result.carriers
    ] == expected
    assert [c.carrier_id for c in result.carriers] == [f"c{i}" for i in range(1, 26)]
    assert result.coverage.primary_carriers == 17
    assert result.coverage.auxiliary_carriers == 8
    assert result.original_link == link
    cat = importlib.import_module("issuedigest_agents.role_link_catalog")
    assert result.original_link_sha256 == cat._hash(link.model_dump(mode="json"))
    assert result.rules_sha256 == cat._hash(mod.role_reference_rules())
    assert mod.validate_role_reference_coverage(src, result) == result
    assert mod.validate_role_reference_coverage(src, result.model_dump(mode="json")) == result
    assert mod.build_role_reference_coverage(src, link.model_dump(mode="json")) == result
    row = next(r for r in result.rows if r.number == "n1" and r.hint.text == "서울")
    assert [(w.carrier_id, w.overlap) for w in row.matches] == [
        ("c1", "exact"),
        ("c3", "contains"),
        ("c6", "exact"),
        ("c7", "contains"),
    ]
    assert [(w.carrier_id, w.overlap) for w in row.auxiliary] == [("c14", "contains")]
    assert [(w.carrier_id, w.overlap) for w in row.other_facts] == [
        ("c15", "exact"),
        ("c17", "contains"),
        ("c20", "exact"),
        ("c21", "contains"),
    ]
    assert row.lexical_status == "exact_reference"


@pytest.mark.parametrize(
    "selected,expected",
    [
        ("서울", ["exact_reference", "partial_reference", "no_reference_in_selected_fields"]),
        ("서울·부산", ["containing_reference", "exact_reference", "containing_reference"]),
        ("울·부", ["partial_reference", "partial_reference", "partial_reference"]),
    ],
)
def test_exact_containing_partial_and_group_fragment(selected, expected):
    data = packet(("n1",))
    ctx = data["contexts"][0]
    for key in ("entity", "period", "condition", "purpose", "basis", "baseline"):
        ctx[key] = anchor(selected) if key == "entity" else None
    if selected == "서울·부산":
        ctx["condition"] = anchor("울·부")
    ctx["scopes"] = []
    data["events"][0].update(kind="unknown", actor=None, predicate=None)
    data["bindings"][0].update(scopes=[], status_sentence=None, change=None)
    mod, src, _, result = build("서울·부산 3명.", data=data)
    assert [r.lexical_status for r in result.rows] == expected
    if selected == "서울·부산":
        assert [w.overlap for w in result.rows[0].matches] == ["contains", "partial"]
        assert [w.overlap for w in result.rows[1].matches] == ["exact", "partial"]
    assert mod.validate_role_reference_coverage(src, result) == result


@pytest.mark.parametrize(
    "scenario", ["context_only", "support_only", "other_fact", "repeat", "touch", "predicate"]
)
def test_auxiliary_other_fact_context_and_other_occurrences_never_fill_primary(scenario):
    data = packet(("n1",))
    data["contexts"][0].update(
        entity=None, period=None, condition=None, purpose=None, basis=None, baseline=None, scopes=[]
    )
    data["events"][0].update(kind="unknown", actor=None, predicate=None)
    data["bindings"][0].update(scopes=[], status_sentence=None, change=None)
    text = "현재 3명 증가 4명."
    if scenario == "context_only":
        data["contexts"][0]["entity"] = anchor("3명", context="현재 3명")
    elif scenario == "support_only":
        data["bindings"][0]["change"] = dict(direction="uncertain", evidence=None, support=["s1"])
    elif scenario == "predicate":
        data["events"][0].update(kind="narration", predicate=anchor("현재"))
    elif scenario == "other_fact":
        data["contexts"].append(
            {**deepcopy(data["contexts"][0]), "id": "c2", "entity": anchor("현재")}
        )
        data["bindings"].append(
            dict(number="n2", context="c2", scopes=[], status_sentence=None, change=None)
        )
    elif scenario == "repeat":
        text = "현재현재 3명 증가 4명."
        data["contexts"][0]["entity"] = anchor("현재", context="현재 3명")
    elif scenario == "touch":
        data["contexts"][0]["entity"] = anchor(" 3명")
    _, _, _, result = build(text, data=data)
    row = result.rows[0]
    assert row.lexical_status == "no_reference_in_selected_fields"
    assert row.matches == ()
    if scenario == "other_fact":
        assert len(row.other_facts) == 1
    elif scenario == "predicate":
        assert len(row.auxiliary) == 1
    elif scenario == "repeat":
        assert result.rows[1].lexical_status == "exact_reference"


@pytest.mark.parametrize(
    "cell,state",
    [
        ("SE", "classified_roles"),
        ("-", "explicitly_unrelated"),
        ("?", "linkage_uncertain"),
        ("_", "not_reviewed"),
    ],
)
def test_all_states_and_wrong_actor_placement_preserve_roles_without_semantic_claims(cell, state):
    data = packet(("n1",))
    for key in ("entity", "period", "condition", "purpose", "basis", "baseline"):
        data["contexts"][0][key] = None
    data["contexts"][0]["scopes"] = []
    data["events"][0].update(actor=anchor("현재"), predicate=anchor("현재"))
    data["bindings"][0].update(scopes=[], change=None, status_sentence=None)
    _, _, link, result = build(data=data, cells=[cell])
    row = result.rows[0]
    assert row.lexical_status == "exact_reference"
    assert row.link_state == state
    assert row.roles == link.report.decisions[0].roles
    assert row.semantic_equivalence == row.materiality == "not_assessed"
    assert result.semantic_equivalence == result.materiality == "not_assessed"
    assert result.semantic_approval is result.source_inventory_exhaustive is False
    assert result.status == "unreviewed"


@pytest.mark.parametrize(
    "quotes,numbers,expected_carriers,expected_hints",
    [
        (("현재 3명.",), (), 0, 1),
        (("3명.",), ("n1",), 1, 0),
        (("현재 설명.", "3명."), ("n1",), 1, 1),
    ],
)
def test_zero_pairs_still_validate_full_link_inventory(
    quotes, numbers, expected_carriers, expected_hints
):
    mod = api()
    src, gen = original(*quotes, numbers=numbers)
    link = receipt(src, gen)
    result = mod.build_role_reference_coverage(src, link)
    assert result.rows == () and result.coverage.candidate_pairs == 0
    assert len(result.carriers) == expected_carriers
    assert result.coverage.total_hints == expected_hints
    assert result.coverage.selected_numbers == len(numbers)
    assert mod.validate_role_reference_coverage(src, result) == result
    raw = result.model_dump(mode="json")
    raw["original_link"]["prompt_sha256"] = "0" * 64
    with pytest.raises(mod.RoleReferenceCoverageError):
        mod.validate_role_reference_coverage(src, raw)


def test_full_288_pairs_all_witnesses_without_legacy_cap_or_truncation():
    text = (
        " ".join(f"'item{chr(65 + i)}'" for i in range(24))
        + " "
        + " ".join(f"{i}명" for i in range(1, 13))
        + "."
    )
    mod = api()
    src, gen = original(text, numbers=tuple(f"n{i}" for i in range(1, 13)))
    result = mod.build_role_reference_coverage(src, receipt(src, gen))
    assert len(result.rows) == result.coverage.candidate_pairs == 288
    assert result.coverage.no_reference_in_selected_fields == 288
    assert len(result.carriers) == 12
    assert mod.validate_role_reference_coverage(src, result.model_dump(mode="json")) == result


def test_rules_are_fresh_complete_json_and_all_new_fields_are_required():
    mod = api()
    rules = mod.role_reference_rules()
    assert rules["rules_version"] == "selected-anchor-overlap-v1"
    serialized = json.dumps(rules)
    for term in (
        "entity",
        "baseline",
        "context_scope",
        "binding_scope",
        "reporting_actor",
        "reporting_predicate",
        "change_evidence",
        "relation_cue",
        "quantity",
        "status_context",
        "other_facts",
        "not_assessed",
    ):
        assert term in serialized
    rules.clear()
    assert mod.role_reference_rules()["rules_version"] == "selected-anchor-overlap-v1"
    for name in (
        "ReferenceCarrier",
        "ReferenceWitness",
        "ReferenceRow",
        "ReferenceCoverageCounts",
        "RoleReferenceCoverage",
    ):
        model = getattr(mod, name)
        assert all(f.is_required() for f in model.model_fields.values())


def leaves(value, path=()):
    if type(value) is dict:
        for key, child in value.items():
            yield from leaves(child, (*path, key))
    elif type(value) is list:
        for i, child in enumerate(value):
            yield from leaves(child, (*path, i))
    else:
        yield path, value


def put(value, path, replacement):
    for key in path[:-1]:
        value = value[key]
    value[path[-1]] = replacement


def test_each_new_field_kind_and_original_receipt_drift_is_reconstructed():
    mod = api()
    src, link = full()
    raw = mod.build_role_reference_coverage(src, link).model_dump(mode="json")
    paths = []
    seen = set()
    for path, value in leaves(raw):
        if path[0] == "original_link":
            continue
        # Repeated DTO instances share one schema; cover each nested field kind once.
        schema_path = tuple("[]" if type(p) is int else p for p in path)
        if schema_path not in seen:
            seen.add(schema_path)
            paths.append((path, value))
    for path in (
        ("original_link", "prompt_sha256"),
        ("original_link", "instructions_sha256"),
        ("original_link", "combined_usage", "requests"),
        ("original_link", "link_usage", "input_tokens"),
        ("original_link", "report", "catalog", "generation_sha256"),
        ("original_link", "report", "catalog", "generation", "prompt_sha256"),
        ("original_link", "report", "catalog", "generation", "usage", "requests"),
        ("original_link", "report", "domain_sha256"),
        ("original_link", "report", "catalog_sha256"),
        ("original_link", "report", "encoding_sha256"),
    ):
        value = raw
        for key in path:
            value = value[key]
        paths.append((path, value))
    for path, value in paths:
        changed = deepcopy(raw)
        replacement = (
            not value
            if type(value) is bool
            else value + 1
            if type(value) is int
            else "tampered"
            if value is None
            else value + "!"
        )
        put(changed, path, replacement)
        with pytest.raises(
            mod.RoleReferenceCoverageError, match="^Invalid role reference coverage$"
        ) as caught:
            mod.validate_role_reference_coverage(src, changed)
        assert caught.value.__cause__ is None
        assert caught.value.__dict__ == {}


@pytest.mark.parametrize(
    "shape",
    [
        "raw_tuple",
        "raw_int_bool",
        "raw_bool_int",
        "raw_subclass",
        "actual_list",
        "actual_dict",
        "actual_scalar",
        "actual_subclass",
        "missing_marker",
        "missing_nested_marker",
        "actual_nested_missing",
        "source_list",
        "source_subclass",
        "link_unchecked",
        "raw_missing_link_marker",
    ],
)
def test_exact_original_shape_guard_before_any_serialization(monkeypatch, shape):
    mod, src, link, result = build()
    value = result
    if shape.startswith("raw_"):
        value = result.model_dump(mode="json")
    if shape == "raw_tuple":
        value["rows"] = tuple(value["rows"])
    elif shape == "raw_int_bool":
        value["semantic_approval"] = 0
    elif shape == "raw_bool_int":
        value["coverage"]["selected_numbers"] = True
    elif shape == "raw_subclass":

        class Text(str):
            pass

        value["rows"][0]["hint_id"] = Text("m1")
    elif shape == "actual_list":
        value = result.model_copy(update={"rows": list(result.rows)})
    elif shape == "actual_dict":
        value = result.model_copy(update={"coverage": result.coverage.model_dump()})
    elif shape == "actual_scalar":
        value = result.model_copy(
            update={"coverage": result.coverage.model_copy(update={"selected_numbers": True})}
        )
    elif shape == "actual_subclass":
        cls = create_model("ImpostorReference", __base__=type(result))
        value = cls.model_validate_json(result.model_dump_json())
    elif shape == "missing_marker":
        value = result.model_dump(mode="json")
        del value["status"]
    elif shape == "missing_nested_marker":
        value = result.model_dump(mode="json")
        del value["original_link"]["report"]["catalog"]["generation"]["frame"]["frame"]["profile"]
    elif shape == "actual_nested_missing":
        value = deepcopy(result)
        del value.original_link.report.catalog.generation.frame.frame.__dict__["profile"]
    elif shape == "source_list":
        src = list(src)
    elif shape == "source_subclass":
        cls = create_model("ImpostorBundle", __base__=type(src[1]))
        src = (src[0], cls.model_validate(src[1].model_dump()))
    elif shape == "link_unchecked":
        value = result.model_copy(
            update={
                "original_link": link.model_copy(
                    update={
                        "combined_usage": link.combined_usage.model_copy(update={"requests": True})
                    }
                )
            }
        )
    elif shape == "raw_missing_link_marker":
        del value["original_link"]["profile"]
    dumps = []

    def forbidden(*args, **kwargs):
        dumps.append(True)
        raise AssertionError("Invalid original was serialized before rejection")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(mod.RoleReferenceCoverageError):
        mod.validate_role_reference_coverage(src, value)
    assert dumps == []


def test_build_guards_source_and_original_link_before_serializing(monkeypatch):
    mod, src, link, _ = build()
    dumps = []

    def forbidden(*args, **kwargs):
        dumps.append(True)
        raise AssertionError("Invalid original was serialized")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    for bad in (
        link.model_copy(update={"profile": "wrong"}),
        {"profile": "role-link-generation-v1"},
    ):
        with pytest.raises(mod.RoleReferenceCoverageError):
            mod.build_role_reference_coverage(src, bad)
    assert dumps == []


def test_import_and_operations_do_not_create_clients_or_call_network(tmp_path):
    api()
    code = """
import socket
import httpx2 as httpx
import openai

def forbidden(*args, **kwargs):
    raise AssertionError("I/O forbidden")
socket.socket.connect = forbidden
httpx.Client.__init__ = forbidden
httpx.AsyncClient.__init__ = forbidden
openai.OpenAI.__init__ = forbidden
openai.AsyncOpenAI.__init__ = forbidden
from issuedigest_agents.role_reference_coverage import role_reference_rules
assert role_reference_rules()["rules_version"] == "selected-anchor-overlap-v1"
"""
    env = {k: v for k, v in os.environ.items() if not k.endswith("API_KEY")}
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    run = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert run.returncode == 0, run.stderr


def test_direct_relations_do_not_propagate_carriers_along_chain():
    mod = api()
    src, gen = original("현재 3명 4명 5명.", numbers=("n1", "n2", "n3"))
    data = gen.frame.input.model_dump(mode="json")
    data["contexts"][0]["entity"] = anchor("3명")
    data["relations"] = [
        dict(kind=kind, **{"from": a, "to": b}, support=["s1"], cue=anchor("현재"))
        for a, b, kind in (("n1", "n2", "included_in"), ("n2", "n3", "parallel"))
    ]
    result = mod.build_role_reference_coverage(src, receipt(src, generation(src, data)))
    assert [(c.number, c.path) for c in result.carriers if c.field == "relation_cue"] == [
        ("n1", "relations/0/cue"),
        ("n2", "relations/0/cue"),
        ("n2", "relations/1/cue"),
        ("n3", "relations/1/cue"),
    ]
    assert all(r.lexical_status == "no_reference_in_selected_fields" for r in result.rows)
    assert [len(r.auxiliary) for r in result.rows] == [1, 2, 1]
    assert [len(r.other_facts) for r in result.rows] == [3, 2, 3]


def test_different_quotes_do_not_witness_equal_text_or_coordinates():
    mod = api()
    src, gen = original("현재 3명.", "현재 4명.", numbers=("n1", "n2"))
    data = gen.frame.input.model_dump(mode="json")
    data["contexts"][0]["entity"] = anchor("현재", "s1")
    data["contexts"].append({**deepcopy(data["contexts"][0]), "id": "c2", "entity": None})
    data["bindings"][1]["context"] = "c2"
    result = mod.build_role_reference_coverage(src, receipt(src, generation(src, data)))
    first, second = result.rows
    assert first.lexical_status == "exact_reference"
    assert second.lexical_status == "no_reference_in_selected_fields"
    assert second.matches == second.auxiliary == second.other_facts == ()
    assert first.hint.text == second.hint.text and first.hint.start == second.hint.start


def test_worst_allowed_carrier_inventory_and_all_overlapping_witnesses_are_uncapped():
    mod = api()
    group = "·".join(chr(65 + i) for i in range(23))
    text = "ABCDEFGH " + group + " " + " ".join(f"{i}명" for i in range(1, 13)) + "."
    group_end = len("ABCDEFGH ") + len(group)
    src, gen = original(text, numbers=tuple(f"n{i}" for i in range(1, 13)))
    data = gen.frame.input.model_dump(mode="json")
    for key in ("entity", "period", "condition", "purpose", "basis", "baseline"):
        data["contexts"][0][key] = anchor(group)
    data["contexts"][0]["scopes"] = [
        dict(kind="other", anchor=anchor(text[i:group_end])) for i in range(2)
    ]
    data["events"][0].update(kind="attributed_report", actor=anchor(group), predicate=anchor(group))
    for binding in data["bindings"]:
        binding.update(
            scopes=[dict(kind="other", anchor=anchor(text[i:group_end])) for i in range(2, 4)],
            status_sentence="s1",
            change=dict(direction="uncertain", evidence=anchor(group), support=["s1"]),
        )
    pairs = [(i, j) for i in range(1, 13) for j in range(i + 1, 13)][:16]
    data["relations"] = [
        dict(kind="unknown", **{"from": f"n{i}", "to": f"n{j}"}, support=["s1"], cue=anchor(group))
        for i, j in pairs
    ]
    result = mod.build_role_reference_coverage(src, receipt(src, generation(src, data)))
    assert len(result.carriers) == 212
    assert result.coverage.primary_carriers == 132
    assert result.coverage.auxiliary_carriers == 80
    assert len(result.rows) == 288
    assert result.coverage.exact_reference == 12
    assert result.coverage.containing_reference == 276
    for row in result.rows:
        # Every carrier except each number's disjoint quantity overlaps every hint.
        assert len(row.matches) == 11
        assert len(row.matches) + len(row.auxiliary) + len(row.other_facts) == 200
    assert mod.validate_role_reference_coverage(src, result) == result


def test_every_new_field_is_required_and_no_array_reorder_or_truncation_is_canonical():
    mod = api()
    src, link = full()
    raw = mod.build_role_reference_coverage(src, link).model_dump(mode="json")
    objects = [(), ("coverage",), ("carriers", 0), ("rows", 0), ("rows", 0, "matches", 0)]
    for path in objects:
        target = raw
        for key in path:
            target = target[key]
        for field in target:
            changed = deepcopy(raw)
            obj = changed
            for key in path:
                obj = obj[key]
            del obj[field]
            with pytest.raises(mod.RoleReferenceCoverageError):
                mod.validate_role_reference_coverage(src, changed)
    for path in (("carriers",), ("rows",), ("rows", 2, "matches")):
        for transform in (lambda a: a[::-1], lambda a: a[:-1], lambda a: a + a[:1]):
            changed = deepcopy(raw)
            target = changed
            for key in path:
                target = target[key]
            put(changed, path, transform(target))
            with pytest.raises(mod.RoleReferenceCoverageError):
                mod.validate_role_reference_coverage(src, changed)


def test_current_source_drift_is_rejected_for_both_apis():
    mod, _, link, result = build()
    changed = document("올해 3명.")
    for value, operation in (
        (link, mod.build_role_reference_coverage),
        (result, mod.validate_role_reference_coverage),
    ):
        with pytest.raises(mod.RoleReferenceCoverageError):
            operation(changed, value)


def test_long_original_support_and_full_quantity_are_preserved_without_new_support_cap():
    text = "현재.\n" + "중간.\n" * 22 + "약 3명~5명 이상.\n끝."
    mod, src, link, result = build(text, cells=["?"])
    assert len(link.report.decisions[0].support_sentence_ids) > 20
    assert result.original_link == link
    assert result.carriers[0].span.text == "약 3명~5명 이상"
    assert result.rows[0].lexical_status == "no_reference_in_selected_fields"
    assert mod.validate_role_reference_coverage(src, result) == result
