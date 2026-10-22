"""Synthetic exact table packets preserve source and reject any reconstruction drift."""

import importlib
import importlib.util
from copy import deepcopy

import pytest
from test_numeric_evidence import document
from test_role_alias_contract import anchor, packet, source
from test_semantic_role_audit_contract import generation
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.role_table_packet"
    assert importlib.util.find_spec(name) is not None, "Missing lossless role table codec"
    return importlib.import_module(name)


def test_roundtrip_preserves_full_source_quantities_and_unchanged_proposal():
    mod = api()
    src = source()
    original = generation(src)
    table = mod.build_role_table_packet(src, original)
    decoded = mod.decode_role_table_packet(src, original, table)
    assert decoded["profile"] == "role-table-audit-v1"
    assert decoded["input_format"] == "named-columns-v1"
    assert decoded["proposal"] == packet()
    assert decoded["change_coverage"] == "available"
    assert decoded["roles"] == [
        "measured_entity",
        "target_scope",
        "period",
        "reporting_actor",
        "change_direction",
    ]
    assert decoded["scope_slots"] == [{"number": "n1", "slots": []}]
    assert decoded["quotes"] == [
        {
            "quote_id": "q1",
            "sentences": [{"id": "s1", "text": "이용자 약\t37여 명 내외 증가, 학교 83개교 감소."}],
        }
    ]
    assert decoded["candidates"] == [
        {
            "id": "n1",
            "quote_id": "q1",
            "expression": "약\t37여 명 내외",
            "atoms": [{"number": "37", "unit": "명"}],
            "separator": None,
            "qualifiers": ["약", "여", "내외"],
            "lexical_kind": "number",
            "sentence_ids": ["s1"],
        },
        {
            "id": "n2",
            "quote_id": "q1",
            "expression": "83개교",
            "atoms": [{"number": "83", "unit": "개교"}],
            "separator": None,
            "qualifiers": [],
            "lexical_kind": "number",
            "sentence_ids": ["s1"],
        },
    ]


class ListSubclass(list):
    pass


class DictSubclass(dict):
    pass


class StringSubclass(str):
    pass


@pytest.fixture(scope="module")
def rich_original():
    src = document("합성국 동부 이용자 약\t37여 명 내외 증가, 학교 83개교 감소.")
    data = packet()
    data["contexts"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("합성국"))]
    data["bindings"][0]["scopes"] = [dict(kind="geographic", anchor=anchor("동부"))]
    data["bindings"].append(
        dict(number="n2", context="c1", scopes=[], status_sentence=None, change=None)
    )
    data["relations"] = [
        dict(kind="parallel", **{"from": "n1"}, to="n2", support=["s1"], cue=anchor("증가"))
    ]
    return src, generation(src, data)


def table_at(body, name):
    if name in ("contexts", "events", "bindings", "relations"):
        return body["proposal"][name]
    if name == "sentences":
        return body["quotes"][0]["sentences"]
    return body[name]


@pytest.mark.parametrize(
    "name",
    ["contexts", "events", "bindings", "relations", "candidates", "sentences", "scope_slots"],
)
@pytest.mark.parametrize(
    "mutation",
    [
        "columns_reverse",
        "columns_missing",
        "columns_extra",
        "columns_tuple",
        "columns_subclass",
        "column_subclass",
        "table_extra",
        "table_subclass",
        "rows_tuple",
        "rows_subclass",
        "row_tuple",
        "row_subclass",
        "short_row",
        "long_row",
        "row_object",
        "missing_rows",
    ],
)
def test_each_table_rejects_header_shape_and_exact_container_drift(rich_original, name, mutation):
    mod = api()
    src, original = rich_original
    body = mod.build_role_table_packet(src, original)
    table = table_at(body, name)
    if mutation == "columns_reverse":
        table["columns"].reverse()
    elif mutation == "columns_missing":
        table["columns"].pop()
    elif mutation == "columns_extra":
        table["columns"].append("extra")
    elif mutation == "columns_tuple":
        table["columns"] = tuple(table["columns"])
    elif mutation == "columns_subclass":
        table["columns"] = ListSubclass(table["columns"])
    elif mutation == "column_subclass":
        table["columns"][0] = StringSubclass(table["columns"][0])
    elif mutation == "table_extra":
        table["extra"] = None
    elif mutation == "table_subclass":
        replacement = DictSubclass(table)
        if name in body["proposal"]:
            body["proposal"][name] = replacement
        elif name == "sentences":
            body["quotes"][0]["sentences"] = replacement
        else:
            body[name] = replacement
    elif mutation == "rows_tuple":
        table["rows"] = tuple(table["rows"])
    elif mutation == "rows_subclass":
        table["rows"] = ListSubclass(table["rows"])
    elif mutation == "row_tuple":
        table["rows"][0] = tuple(table["rows"][0])
    elif mutation == "row_subclass":
        table["rows"][0] = ListSubclass(table["rows"][0])
    elif mutation == "short_row":
        table["rows"][0].pop()
    elif mutation == "long_row":
        table["rows"][0].append(None)
    elif mutation == "row_object":
        table["rows"][0] = dict(zip(table["columns"], table["rows"][0], strict=True))
    elif mutation == "missing_rows":
        del table["rows"]
    with pytest.raises(mod.RoleTablePacketError, match="^Invalid role table packet$"):
        mod.decode_role_table_packet(src, original, body)


@pytest.mark.parametrize(
    "mutation",
    [
        "packet_subclass",
        "proposal_subclass",
        "quote_subclass",
        "quotes_tuple",
        "roles_tuple",
        "roles_subclass",
        "anchor_subclass",
        "anchor_missing_null",
        "anchor_extra",
        "anchor_value",
        "change_missing",
        "change_extra",
        "change_support_tuple",
        "scopes_tuple",
        "scope_extra",
        "atoms_tuple",
        "atom_missing_unit",
        "atom_extra",
        "atom_bool",
        "atom_int",
        "qualifiers_tuple",
        "sentence_ids_tuple",
        "nested_string_subclass",
        "slot_subclass",
        "slot_order",
        "roles_order",
        "candidate_order",
        "quote_text",
        "quote_extra",
        "quote_id",
        "proposal_extra",
        "packet_extra",
        "packet_missing",
        "profile",
        "input_format",
        "coverage",
        "from_alias",
        "boolean_null",
    ],
)
def test_nested_cells_and_metadata_cannot_be_repaired_or_normalized(rich_original, mutation):
    mod = api()
    src, original = rich_original
    body = mod.build_role_table_packet(src, original)
    context = body["proposal"]["contexts"]["rows"][0]
    binding = body["proposal"]["bindings"]["rows"][0]
    candidate = body["candidates"]["rows"][0]
    if mutation == "packet_subclass":
        body = DictSubclass(body)
    elif mutation == "proposal_subclass":
        body["proposal"] = DictSubclass(body["proposal"])
    elif mutation == "quote_subclass":
        body["quotes"][0] = DictSubclass(body["quotes"][0])
    elif mutation == "quotes_tuple":
        body["quotes"] = tuple(body["quotes"])
    elif mutation.startswith("roles_"):
        if mutation == "roles_order":
            body["roles"].reverse()
        else:
            body["roles"] = (tuple if mutation == "roles_tuple" else ListSubclass)(body["roles"])
    elif mutation == "anchor_subclass":
        context[2] = DictSubclass(context[2])
    elif mutation == "anchor_missing_null":
        del context[2]["c"]
    elif mutation == "anchor_extra":
        context[2]["context_text"] = None
    elif mutation == "anchor_value":
        context[2]["t"] = "학교"
    elif mutation == "change_missing":
        del binding[4]["evidence"]
    elif mutation == "change_extra":
        binding[4]["extra"] = None
    elif mutation == "change_support_tuple":
        binding[4]["support"] = tuple(binding[4]["support"])
    elif mutation == "scopes_tuple":
        context[3] = tuple(context[3])
    elif mutation == "scope_extra":
        context[3][0]["slot"] = "r1"
    elif mutation == "atoms_tuple":
        candidate[3] = tuple(candidate[3])
    elif mutation == "atom_missing_unit":
        del candidate[3][0]["unit"]
    elif mutation == "atom_extra":
        candidate[3][0]["extra"] = None
    elif mutation in ("atom_bool", "atom_int"):
        candidate[3][0]["number"] = True if mutation == "atom_bool" else 37
    elif mutation == "qualifiers_tuple":
        candidate[5] = tuple(candidate[5])
    elif mutation == "sentence_ids_tuple":
        candidate[7] = tuple(candidate[7])
    elif mutation == "nested_string_subclass":
        candidate[3][0]["number"] = StringSubclass("37")
    elif mutation == "slot_subclass":
        body["scope_slots"]["rows"][0][1] = ListSubclass(["r1", "r2"])
    elif mutation == "slot_order":
        body["scope_slots"]["rows"][0][1].reverse()
    elif mutation == "candidate_order":
        body["candidates"]["rows"].reverse()
    elif mutation == "quote_text":
        body["quotes"][0]["sentences"]["rows"][0][1] += " "
    elif mutation == "quote_extra":
        body["quotes"][0]["extra"] = None
    elif mutation == "quote_id":
        body["quotes"][0]["quote_id"] = "q2"
    elif mutation == "proposal_extra":
        body["proposal"]["extra"] = []
    elif mutation == "packet_extra":
        body["extra"] = None
    elif mutation == "packet_missing":
        del body["roles"]
    elif mutation in ("profile", "input_format", "coverage"):
        body["change_coverage" if mutation == "coverage" else mutation] = "other"
    elif mutation == "from_alias":
        body["proposal"]["relations"]["columns"][1] = "from_"
    elif mutation == "boolean_null":
        context[4] = False
    with pytest.raises(mod.RoleTablePacketError, match="^Invalid role table packet$"):
        mod.decode_role_table_packet(src, original, body)


def test_scope_slots_preserve_context_then_binding_position(rich_original):
    mod = api()
    src, original = rich_original
    body = mod.build_role_table_packet(src, original)
    decoded = mod.decode_role_table_packet(src, original, body)
    assert decoded["scope_slots"] == [
        {"number": "n1", "slots": ["r1", "r2"]},
        {"number": "n2", "slots": ["r1"]},
    ]
    assert decoded["proposal"] == original.frame.input.model_dump(mode="json")
    before = deepcopy(body)
    decoded["proposal"]["contexts"][0]["entity"]["t"] = "changed"
    assert body == before, "Returned data must not alias the supplied table"


@pytest.mark.parametrize(
    "mutation",
    [
        "raw_generation",
        "raw_frame",
        "raw_index",
        "generation_subclass",
        "anchor_subclass",
        "generation_profile",
        "generation_status",
        "frame_profile",
        "frame_status",
        "canonical_profile",
        "canonical_status",
        "index_profile",
        "index_status",
        "nullable_default",
        "source_default",
        "source_subclass",
        "source_list",
        "source_tuple_subclass",
        "contexts_list",
        "contexts_tuple_subclass",
        "source_text",
        "candidate_text",
        "proposal_text",
        "usage_bool",
        "scalar_subclass",
        "usage_scalar_subclass",
    ],
)
@pytest.mark.parametrize("operation", ["build", "decode"])
def test_original_actual_and_raw_tampering_is_rejected_before_reconstruction(
    rich_original, mutation, operation
):
    mod = api()
    src, original = rich_original
    body = mod.build_role_table_packet(src, original)
    src, original = deepcopy(src), original.model_copy(deep=True)
    frames = {
        "generation": original,
        "frame": original.frame,
        "canonical": original.frame.frame,
        "index": original.frame.frame.candidate_index,
    }
    if mutation == "raw_generation":
        original = original.model_dump(mode="json")
    elif mutation in ("raw_frame", "raw_index"):
        parent, key = (
            (original, "frame")
            if mutation == "raw_frame"
            else (original.frame.frame, "candidate_index")
        )
        parent.__dict__[key] = parent.__dict__[key].model_dump(mode="json")
    elif mutation in ("generation_subclass", "anchor_subclass", "source_subclass"):
        from pydantic import Field, create_model

        target = (
            original
            if mutation == "generation_subclass"
            else (
                original.frame.input.contexts[0].entity if mutation == "anchor_subclass" else src[1]
            )
        )
        subclass = create_model(
            "ExcludedSubclass",
            __base__=type(target),
            hidden=(str, Field(default="hidden", exclude=True)),
        )
        replacement = subclass.model_validate(target.model_dump())
        if mutation == "generation_subclass":
            original = replacement
        elif mutation == "anchor_subclass":
            original.frame.input.contexts[0].__dict__["entity"] = replacement
        else:
            src = (src[0], replacement, src[2])
    elif mutation.rsplit("_", 1)[0] in frames:
        node, field = mutation.rsplit("_", 1)
        del frames[node].__dict__[field]
    elif mutation == "nullable_default":
        del original.frame.input.contexts[0].entity.__dict__["c"]
    elif mutation == "source_default":
        del src[1].document.__dict__["canonical_url"]
    elif mutation == "source_list":
        src = list(src)
    elif mutation in ("source_tuple_subclass", "contexts_tuple_subclass"):

        class TupleSubclass(tuple):
            pass

        if mutation == "source_tuple_subclass":
            src = TupleSubclass(src)
        else:
            original.frame.input.__dict__["contexts"] = TupleSubclass(original.frame.input.contexts)
    elif mutation == "contexts_list":
        original.frame.input.__dict__["contexts"] = list(original.frame.input.contexts)
    elif mutation == "source_text":
        src[1].representation.__dict__["text"] += " changed"
    elif mutation == "candidate_text":
        original.frame.frame.candidate_index.candidates[0].expression.__dict__["text"] = "38명"
    elif mutation == "proposal_text":
        original.frame.input.contexts[0].entity.__dict__["t"] = "학교"
    elif mutation == "usage_bool":
        original.usage.__dict__["requests"] = True
    elif mutation == "scalar_subclass":
        original.__dict__["profile"] = StringSubclass(original.profile)
    elif mutation == "usage_scalar_subclass":

        class IntSubclass(int):
            pass

        original.usage.__dict__["requests"] = IntSubclass(1)
    with pytest.raises(mod.RoleTablePacketError, match="^Invalid role table packet$"):
        if operation == "build":
            mod.build_role_table_packet(src, original)
        else:
            mod.decode_role_table_packet(src, original, body)


def test_empty_selection_preserves_blank_sentences_whitespace_ranges_and_missing_units():
    mod = api()
    quotes = ["\n\n이용자 약\t37여 명 내외 증가.\n\n학교 3~5개교. 6 이상.\n", " \t추가 설명.\n "]
    src = document(*quotes)
    original = generation(src, dict(contexts=[], events=[], bindings=[], relations=[]))
    body = mod.build_role_table_packet(src, original)
    decoded = mod.decode_role_table_packet(src, original, body)
    assert ["".join(s["text"] for s in q["sentences"]) for q in decoded["quotes"]] == quotes
    assert any(not s["text"].strip() for q in decoded["quotes"] for s in q["sentences"])
    assert decoded["scope_slots"] == []
    assert decoded["proposal"] == dict(contexts=[], events=[], bindings=[], relations=[])
    for name, columns in [
        (
            "contexts",
            [
                "id",
                "event",
                "entity",
                "scopes",
                "period",
                "status",
                "condition",
                "purpose",
                "basis",
                "baseline",
            ],
        ),
        ("events", ["id", "kind", "actor", "predicate", "tense"]),
        ("bindings", ["number", "context", "scopes", "status_sentence", "change"]),
        ("relations", ["kind", "from", "to", "support", "cue"]),
    ]:
        assert body["proposal"][name] == {"columns": columns, "rows": []}
    assert [c["expression"] for c in decoded["candidates"]] == [
        "약\t37여 명 내외",
        "3~5개교",
        "6 이상",
    ]
    assert decoded["candidates"][1]["atoms"] == [
        {"number": "3", "unit": None},
        {"number": "5", "unit": "개교"},
    ]
    assert decoded["candidates"][1]["separator"] == "~"
    assert decoded["candidates"][2]["atoms"] == [{"number": "6", "unit": None}]


def test_decoder_rebuilds_current_source_instead_of_accepting_caller_canonical():
    mod = api()
    src = source()
    original = generation(src)
    changed = packet()
    changed["bindings"][0]["change"]["direction"] = "decrease"
    different = generation(src, changed)
    body = mod.build_role_table_packet(src, different)
    with pytest.raises(mod.RoleTablePacketError):
        mod.decode_role_table_packet(src, original, body)


@pytest.mark.parametrize("mutation", ["scalar_subclass", "bool_as_int"])
def test_invalid_actual_values_are_rejected_before_any_serialization(
    rich_original, monkeypatch, mutation
):
    from pydantic import BaseModel

    mod = api()
    src, original = rich_original
    original = original.model_copy(deep=True)
    if mutation == "scalar_subclass":
        original.__dict__["profile"] = StringSubclass(original.profile)
    else:
        original.usage.__dict__["requests"] = True
    calls = []

    def forbidden_dump(*args, **kwargs):
        calls.append(True)
        raise RuntimeError("serialization must not start")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden_dump)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden_dump)
    with pytest.raises(mod.RoleTablePacketError):
        mod.build_role_table_packet(src, original)
    assert calls == []
