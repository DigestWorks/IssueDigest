"""Synthetic lossless columnar generation inputs and exact current-source boundaries."""

import importlib
import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy

import pytest
from pydantic import BaseModel, create_model
from test_numeric_evidence import document
from test_shared_measurement_context_v2 import (
    restore_introduced_modules as restore_introduced_modules,
)


def api():
    name = "issuedigest_agents.generation_source_packet"
    assert importlib.util.find_spec(name) is not None, "Missing generation source codec"
    return importlib.import_module(name)


def test_short_packet_decodes_the_complete_original_candidate_and_quote():
    mod = api()
    src = document("값 7명.")
    packet = mod.build_generation_source_packet(src)
    decoded = mod.decode_generation_source_packet(src, packet)
    assert decoded["candidates"] == [
        dict(
            id="n1",
            quote_id="q1",
            sentence_ids=["s1"],
            expression="7명",
            atoms=[dict(number="7", unit="명")],
            lexical_kind="number",
            qualifiers=[],
            separator=None,
        )
    ]
    assert decoded["quotes"] == [dict(quote_id="q1", sentences=[dict(id="s1", text="값 7명.")])]
    assert packet == dict(
        input_format="columnar-generation-source-v1",
        profile="shared-role-aliases-v2",
        atom_columns=["number", "unit"],
        candidate_count=1,
        candidate_columns=dict(
            id=["values", ["n1"]],
            quote_id=["values", ["q1"]],
            sentence_ids=["values", [["s1"]]],
            expression=["values", ["7명"]],
            atoms=["values", [[["7", "명"]]]],
            lexical_kind=["values", ["number"]],
            qualifiers=["values", [[]]],
            separator=["values", [None]],
        ),
        quotes=[
            dict(
                quote_id="q1",
                sentence_count=1,
                sentence_columns=dict(id=["values", ["s1"]], text=["values", ["값 7명."]]),
            )
        ],
        eligible_status_sentence_ids=["values", ["s1"]],
        context_id_slots=["indexed", "c", list(range(1, 13))],
        reporting_event_id_slots=["indexed", "e", list(range(1, 13))],
    )
    assert decoded["profile"] == "shared-role-aliases-v2"
    assert decoded["eligible_status_sentence_ids"] == ["s1"]
    assert decoded["context_id_slots"] == [f"c{i}" for i in range(1, 13)]
    assert decoded["reporting_event_id_slots"] == [f"e{i}" for i in range(1, 13)]
    assert mod.validate_generation_source_packet(src, packet) == packet
    assert mod.generation_source_packet_prompt(src) == json.dumps(
        packet, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


@pytest.mark.parametrize(
    "values,expected",
    [
        ([], ["values", []]),
        ([None], ["values", [None]]),
        (["q1"], ["values", ["q1"]]),  # values wins the constant tie
        ([True, 1], ["values", [True, 1]]),
        ([None, ""], ["values", [None, ""]]),
        ([None] * 10, ["constant", None]),
        ([[]] * 10, ["constant", []]),
        (["한글🧪"] * 3, ["constant", "한글🧪"]),
        (["q01", "q02"], ["values", ["q01", "q02"]]),
        (["q0", "q-1"], ["values", ["q0", "q-1"]]),
        (["x1", "x2"], ["values", ["x1", "x2"]]),
        (["s1\n", "s2\n"], ["values", ["s1\n", "s2\n"]]),
        ([f"n{i}" for i in range(1, 13)], ["indexed", "n", list(range(1, 13))]),
        (["s19", "s4", "s19", "s200", "s1"] * 3, ["indexed", "s", [19, 4, 19, 200, 1] * 3]),
        (
            [["s91", "s4"], [], ["s91"], ["s123"]],
            ["indexed_lists", "s", [[91, 4], [], [91], [123]]],
        ),
        ([[]] * 20, ["constant", []]),
        (
            ["long-first-value", "long-second-value"] * 10,
            ["dictionary", ["long-first-value", "long-second-value"], [0, 1] * 10],
        ),
        ([[True] * 10, [1] * 10] * 10, ["dictionary", [[True] * 10, [1] * 10], [0, 1] * 10]),
        (
            [{"long": "first"}, {"long": "second"}, {"long": "first"}] * 10,
            ["dictionary", [{"long": "first"}, {"long": "second"}], [0, 1, 0] * 10],
        ),
    ],
)
def test_canonical_shortest_columns_preserve_exact_types_ids_duplicates_and_order(values, expected):
    mod = api()
    assert mod._column(values, id_bearing=True) == expected


@pytest.mark.parametrize(
    "quotes",
    [
        ("q" + "1" * 4301,),
        ("q" + "1" * 4301, "s" + "2" * 4301, "n123456789"),
        tuple(f"q{i}" for i in range(1, 13)),
    ],
)
def test_literal_id_like_source_text_roundtrips_without_identifier_integer_conversion(quotes):
    mod = api()
    src = document(*quotes)
    packet = mod.build_generation_source_packet(src)
    assert json.loads(mod.generation_source_packet_prompt(src)) == packet
    assert mod.validate_generation_source_packet(src, packet) == packet
    decoded = mod.decode_generation_source_packet(src, packet)
    assert [q["sentences"] for q in decoded["quotes"]] == [
        [dict(id=f"s{i}", text=text)] for i, text in enumerate(quotes, 1)
    ]
    assert [quote["sentence_columns"]["text"] for quote in packet["quotes"]] == [
        ["values", [text]] for text in quotes
    ]
    assert packet["context_id_slots"] == ["indexed", "c", list(range(1, 13))]
    assert packet["reporting_event_id_slots"] == ["indexed", "e", list(range(1, 13))]


@pytest.mark.parametrize(
    "values,expected",
    [
        (["q" + "1" * 4301, "q" + "2" * 4301], ["values", ["q" + "1" * 4301, "q" + "2" * 4301]]),
        (["q" + "1" * 4301] * 3, ["constant", "q" + "1" * 4301]),
        (
            ["q" + "1" * 4301, "q" + "2" * 4301] * 3,
            ["dictionary", ["q" + "1" * 4301, "q" + "2" * 4301], [0, 1] * 3],
        ),
        ([f"s{i}" for i in range(1, 13)], ["values", [f"s{i}" for i in range(1, 13)]]),
        (
            [["s91", "s4"], [], ["s91"], ["s123"]],
            ["values", [["s91", "s4"], [], ["s91"], ["s123"]]],
        ),
    ],
)
def test_literal_columns_only_use_values_constant_dictionary_even_for_id_like_content(
    values, expected
):
    mod = api()
    assert mod._column(values) == expected


def test_actual_identifier_columns_keep_canonical_prefix_encodings():
    mod = api()
    src = document(*("7명." for _ in range(20)))
    packet = mod.build_generation_source_packet(src)
    assert packet["candidate_columns"]["id"] == ["indexed", "n", list(range(1, 21))]
    assert packet["candidate_columns"]["quote_id"] == ["indexed", "q", list(range(1, 21))]
    assert packet["candidate_columns"]["sentence_ids"] == [
        "indexed_lists",
        "s",
        [[i] for i in range(1, 21)],
    ]
    assert packet["eligible_status_sentence_ids"] == ["indexed", "s", list(range(1, 21))]
    src = document(" ".join(f"{i}명." for i in range(1, 33)))
    packet = mod.build_generation_source_packet(src)
    assert packet["quotes"][0]["sentence_columns"]["id"] == ["indexed", "s", list(range(1, 33))]
    decoded = mod.decode_generation_source_packet(src, packet)
    assert [sentence["id"] for sentence in decoded["quotes"][0]["sentences"]] == [
        f"s{i}" for i in range(1, 33)
    ]


def assert_plain_json(value):
    assert type(value) in (dict, list, str, int, bool, float, type(None))
    if type(value) is dict:
        assert all(type(key) is str for key in value)
        for child in value.values():
            assert_plain_json(child)
    elif type(value) is list:
        for child in value:
            assert_plain_json(child)


@pytest.mark.parametrize(
    "quotes",
    [
        ("설명만. \n\n 뒤 설명. \t",),
        ("🧪 e\u0301 설명.\n\n 약\t37여 명 내외. \t", "학교 83개교와 61~79명 내외."),
        ("최대 37여명~59여 명 내외. -37여명~-19여명. A83개교.",),
        ("약 14개월~26개월 내외, 4.2.6, 제87조, 2031-04-17.",),
        ("37", "37", "\t 빈 설명.\n", "61~79명 내외."),
        (" ".join(f"{i}명" for i in range(1, 257)),),
        tuple(f"항목 {i}명.\n\n 끝. \t" for i in range(1, 21)),
        ("반복. " * 180 + "7명.",),
    ],
)
def test_complete_source_projection_matches_frozen_builder_without_new_limits(quotes):
    mod = api()
    src = document(*quotes)
    body = mod.build_generation_source_packet(src)
    decoded = mod.decode_generation_source_packet(src, body)
    compact = importlib.import_module("issuedigest_agents.compact_shared_context")
    index = compact.build_numeric_candidates_v2(src)
    original = json.loads(
        compact._json(
            dict(
                profile="shared-role-aliases-v2",
                **compact._source_packet(index),
                eligible_status_sentence_ids=compact._eligible(index),
                context_id_slots=[f"c{i}" for i in range(1, 13)],
                reporting_event_id_slots=[f"e{i}" for i in range(1, 13)],
            )
        )
    )
    assert decoded == original
    assert ["".join(s["text"] for s in q["sentences"]) for q in decoded["quotes"]] == list(quotes)
    assert body["candidate_count"] == len(index.candidates)
    assert [q["sentence_count"] for q in body["quotes"]] == [
        len(q["sentences"]) for q in original["quotes"]
    ]
    assert_plain_json(body)
    assert_plain_json(decoded)
    prompt = mod.generation_source_packet_prompt(src)
    for private_id in (
        str(src[0]),
        str(src[1].document.workspace_id),
        *(str(c.citation_id) for c in src[1].citations),
    ):
        assert private_id not in prompt
    if not index.candidates:
        assert all(c == ["values", []] for c in body["candidate_columns"].values())
        assert body["eligible_status_sentence_ids"] == ["values", []]
    if len(index.candidates) == 256:
        assert [c["id"] for c in decoded["candidates"]] == [f"n{i}" for i in range(1, 257)]


def test_unicode_whitespace_ranges_qualifiers_and_null_units_have_literal_projection():
    mod = api()
    src = document("🧪 e\u0301 설명.\n\n 약\t37여 명 내외. \t", "61~79명 내외.")
    decoded = mod.decode_generation_source_packet(src, mod.build_generation_source_packet(src))
    assert decoded["quotes"][0] == dict(
        quote_id="q1",
        sentences=[
            dict(id="s1", text="🧪 e\u0301 설명."),
            dict(id="s2", text="\n"),
            dict(id="s3", text="\n"),
            dict(id="s4", text=" 약\t37여 명 내외."),
            dict(id="s5", text=" \t"),
        ],
    )
    assert decoded["candidates"] == [
        dict(
            id="n1",
            quote_id="q1",
            sentence_ids=["s4"],
            lexical_kind="number",
            expression="약\t37여 명 내외",
            atoms=[dict(number="37", unit="명")],
            separator=None,
            qualifiers=["약", "여", "내외"],
        ),
        dict(
            id="n2",
            quote_id="q2",
            sentence_ids=["s6"],
            lexical_kind="number",
            expression="61~79명 내외",
            atoms=[dict(number="61", unit=None), dict(number="79", unit="명")],
            separator="~",
            qualifiers=["내외"],
        ),
    ]


class DictSubclass(dict):
    pass


class ListSubclass(list):
    pass


class TupleSubclass(tuple):
    pass


class StringSubclass(str):
    pass


class IntSubclass(int):
    pass


def reject(mod, src, body):
    for operation in (mod.validate_generation_source_packet, mod.decode_generation_source_packet):
        with pytest.raises(mod.GenerationSourcePacketError) as caught:
            operation(src, body)
        assert str(caught.value) == "Invalid generation source packet"
        assert caught.value.__cause__ is None
        assert caught.value.__suppress_context__ is True
        assert caught.value.__dict__ == {}


@pytest.mark.parametrize(
    "mutation",
    [
        "root_subclass",
        "tuple",
        "list_subclass",
        "string_subclass",
        "int_subclass",
        "key_subclass",
        "nonstring_key",
        "model",
        "nested_model",
        "new_field",
        "missing_field",
        "format",
        "profile",
        "atom_columns",
        "atom_columns_order",
        "count",
        "count_bool",
        "count_float",
        "candidate_field",
        "missing_candidate_field",
        "quote_field",
        "quote_count",
        "quote_id",
        "sentence_field",
        "missing_sentence_field",
        "sentence_count_bool",
        "sentence_text",
        "sentence_id",
        "expression",
        "atoms",
        "atom_number",
        "atom_unit",
        "qualifiers",
        "separator",
        "lexical_kind",
        "sentence_reference",
        "quote_reference",
        "candidate_id",
        "eligible",
        "contexts",
        "events",
        "mode",
        "constant",
        "same_semantics",
        "indexed_prefix",
        "indexed_suffix",
        "indexed_bool",
        "indexed_float",
        "indexed_order",
        "indexed_lists",
        "quote_duplicate",
        "quote_order",
    ],
)
def test_every_packet_field_and_raw_shape_rejects_tampering(mutation):
    mod = api()
    src = document("값 61~79명 내외.", "다른 83개교.")
    body = mod.build_generation_source_packet(src)
    columns = body["candidate_columns"]
    quote = body["quotes"][0]
    if mutation == "root_subclass":
        body = DictSubclass(body)
    elif mutation == "tuple":
        body["quotes"] = tuple(body["quotes"])
    elif mutation == "list_subclass":
        body["quotes"] = ListSubclass(body["quotes"])
    elif mutation == "string_subclass":
        body["profile"] = StringSubclass(body["profile"])
    elif mutation == "int_subclass":
        body["candidate_count"] = IntSubclass(2)
    elif mutation in ("key_subclass", "nonstring_key"):
        value = body.pop("profile")
        body[StringSubclass("profile") if mutation == "key_subclass" else 1] = value
    elif mutation in ("model", "nested_model"):
        model = create_model("UncheckedPacket", value=(int, 1))()
        if mutation == "model":
            body = model
        else:
            columns["atoms"] = model
    elif mutation == "new_field":
        body["extra"] = None
    elif mutation == "missing_field":
        del body["atom_columns"]
    elif mutation in ("format", "profile"):
        body["input_format" if mutation == "format" else "profile"] = "other"
    elif mutation == "atom_columns":
        body["atom_columns"].append("extra")
    elif mutation == "atom_columns_order":
        body["atom_columns"].reverse()
    elif mutation.startswith("count"):
        body["candidate_count"] = {"count": 3, "count_bool": True, "count_float": 2.0}[mutation]
    elif mutation == "candidate_field":
        columns["extra"] = ["values", []]
    elif mutation == "missing_candidate_field":
        del columns["separator"]
    elif mutation == "quote_field":
        quote["extra"] = None
    elif mutation == "quote_count":
        quote["sentence_count"] += 1
    elif mutation == "quote_id":
        quote["quote_id"] = "q2"
    elif mutation == "sentence_field":
        quote["sentence_columns"]["extra"] = ["values", []]
    elif mutation == "missing_sentence_field":
        del quote["sentence_columns"]["text"]
    elif mutation == "sentence_count_bool":
        quote["sentence_count"] = True
    elif mutation in ("sentence_text", "sentence_id"):
        quote["sentence_columns"]["text" if mutation == "sentence_text" else "id"][1][0] = "fake"
    elif mutation in ("expression", "atoms", "qualifiers", "separator", "lexical_kind"):
        columns[mutation] = ["constant", "fake"]
    elif mutation in ("atom_number", "atom_unit"):
        columns["atoms"][1][0][0][0 if mutation == "atom_number" else 1] = True
    elif mutation in ("sentence_reference", "quote_reference", "candidate_id"):
        field = {
            "sentence_reference": "sentence_ids",
            "quote_reference": "quote_id",
            "candidate_id": "id",
        }[mutation]
        columns[field] = ["values", ["n99", "n99"]]
    elif mutation in ("eligible", "contexts", "events"):
        field = {
            "eligible": "eligible_status_sentence_ids",
            "contexts": "context_id_slots",
            "events": "reporting_event_id_slots",
        }[mutation]
        body[field] = ["values", []]
    elif mutation == "mode":
        columns["id"][0] = "unknown"
    elif mutation == "constant":
        columns["id"] = ["constant", "n1"]
    elif mutation == "same_semantics":
        quote["sentence_columns"]["id"] = ["constant", "s1"]
    elif mutation.startswith("indexed_") and mutation != "indexed_lists":
        column = body["context_id_slots"]
        if mutation == "indexed_prefix":
            column[1] = "e"
        elif mutation == "indexed_order":
            column[2].reverse()
        else:
            column[2][0] = {"indexed_suffix": 99, "indexed_bool": True, "indexed_float": 1.0}[
                mutation
            ]
    elif mutation == "indexed_lists":
        columns["sentence_ids"] = ["indexed_lists", "s", [[1], [1]]]
    elif mutation == "quote_duplicate":
        body["quotes"].append(deepcopy(quote))
    elif mutation == "quote_order":
        body["quotes"].reverse()
    else:
        raise AssertionError(mutation)
    reject(mod, src, body)


@pytest.mark.parametrize(
    "mutation",
    [
        "pool_order",
        "pool_duplicate",
        "index",
        "bool",
        "float",
        "missing_index",
        "row_order",
        "mode",
        "nested",
    ],
)
def test_dictionary_pools_and_indices_must_match_first_occurrence_canonical_encoding(mutation):
    mod = api()
    src = document(" ".join(["약 37명 내외", "최대 61명 이상"] * 16))
    body = mod.build_generation_source_packet(src)
    column = body["candidate_columns"]["expression"]
    assert column[0] == "dictionary"
    if mutation == "pool_order":
        column[1].reverse()
        column[2] = [1 - index for index in column[2]]  # same semantic vector still rejects
    elif mutation == "pool_duplicate":
        column[1].append(column[1][0])
    elif mutation in ("index", "bool", "float"):
        column[2][0] = {"index": 999, "bool": True, "float": 0.0}[mutation]
    elif mutation == "missing_index":
        column[2].pop()
    elif mutation == "row_order":
        column[2].reverse()
    elif mutation == "mode":
        column[0] = "values"
    else:
        column[1] = ListSubclass(column[1])
    reject(mod, src, body)


@pytest.mark.parametrize("mutation", ["prefix", "nested_index", "bool", "float", "empty_row"])
def test_indexed_lists_preserve_every_nested_reference_and_type(mutation):
    mod = api()
    src = document(" ".join(f"{i}명." for i in range(1, 33)))
    body = mod.build_generation_source_packet(src)
    column = body["candidate_columns"]["sentence_ids"]
    assert column[0] == "indexed_lists"
    if mutation == "prefix":
        column[1] = "q"
    elif mutation == "empty_row":
        column[2][0] = []
    else:
        column[2][0][0] = {"nested_index": 999, "bool": True, "float": 1.0}[mutation]
    reject(mod, src, body)


@pytest.mark.parametrize(
    "mutation",
    [
        "source_list",
        "source_subclass",
        "model_subclass",
        "nested_subclass",
        "container_list",
        "container_subclass",
        "scalar_subclass",
        "unchecked_scalar",
        "nested_dict",
        "missing_default",
        "missing_marker",
        "extra",
    ],
)
def test_source_live_values_are_guarded_before_any_serialization(mutation, monkeypatch):
    mod = api()
    src = document("값 7명.")
    body = mod.build_generation_source_packet(src)
    sid, bundle, presentation = src
    if mutation == "source_list":
        src = list(src)
    elif mutation == "source_subclass":
        src = TupleSubclass(src)
    elif mutation == "model_subclass":
        derived = create_model("DerivedBundle", __base__=type(bundle))
        src = sid, derived(**bundle.__dict__), presentation
    elif mutation == "nested_subclass":
        derived = create_model("DerivedCitation", __base__=type(bundle.citations[0]))
        bundle.__dict__["citations"] = (derived(**bundle.citations[0].__dict__),)
    elif mutation in ("container_list", "container_subclass"):
        bundle.__dict__["citations"] = (list if mutation == "container_list" else TupleSubclass)(
            bundle.citations
        )
    elif mutation in ("scalar_subclass", "unchecked_scalar"):
        bundle.citations[0].selector.__dict__["start"] = (
            IntSubclass(0) if mutation == "scalar_subclass" else True
        )
    elif mutation == "nested_dict":
        bundle.__dict__["representation"] = bundle.representation.model_dump(mode="json")
    elif mutation == "missing_default":
        del bundle.document.__dict__["canonical_url"]
    elif mutation == "missing_marker":
        del bundle.citations[0].selector.__dict__["kind"]
    else:
        bundle.document.__dict__["unchecked"] = None
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("guard must precede dumping")

    monkeypatch.setattr(BaseModel, "model_dump", forbidden)
    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    for operation, arguments in (
        (mod.build_generation_source_packet, (src,)),
        (mod.generation_source_packet_prompt, (src,)),
        (mod.validate_generation_source_packet, (src, body)),
        (mod.decode_generation_source_packet, (src, body)),
    ):
        with pytest.raises(
            mod.GenerationSourcePacketError, match="^Invalid generation source packet$"
        ):
            operation(*arguments)
    assert calls == []


def test_untrusted_packet_is_copied_and_guarded_before_its_first_dump(monkeypatch):
    mod = api()
    src = document("값 7명.")
    body = mod.build_generation_source_packet(src)

    class ExplosiveString(str):
        def __eq__(self, other):
            raise AssertionError("untrusted scalar interpreted before guard")

    body["profile"] = ExplosiveString(body["profile"])
    original_json = mod._json

    def guarded_dump(value):
        assert_plain_json(value)
        return original_json(value)

    monkeypatch.setattr(mod, "_json", guarded_dump)
    reject(mod, src, body)


def test_source_drift_and_invalid_reference_spans_reject_whole_packet():
    mod = api()
    src = document("값 7명.", "학교 3개교.")
    body = mod.build_generation_source_packet(src)
    for changed in (document("값 8명.", "학교 3개교."), document("학교 3개교.", "값 7명.")):
        reject(mod, changed, body)
    changed = deepcopy(src)
    changed[1].citations[0].selector.__dict__["end"] += 1
    reject(mod, changed, body)


def test_results_are_fresh_mutable_json_with_no_shared_rows_or_calls():
    mod = api()
    src = document("값 7명. 값 7명.")
    original = mod.build_generation_source_packet(src)
    built = mod.build_generation_source_packet(src)
    validated = mod.validate_generation_source_packet(src, built)
    decoded = mod.decode_generation_source_packet(src, built)
    validated["atom_columns"].reverse()
    assert built == original
    built["quotes"].clear()
    decoded["candidates"][0]["atoms"][0]["number"] = "changed"
    assert decoded["candidates"][1]["atoms"][0]["number"] == "7"
    assert mod.build_generation_source_packet(src) == original
    assert mod.validate_generation_source_packet(src, original) == original
    assert mod.decode_generation_source_packet(src, original)["candidates"][0]["atoms"][0] == dict(
        number="7", unit="명"
    )


def test_decode_exercises_columns_and_compares_reconstruction(monkeypatch):
    mod = api()
    src = document("값 7명.")
    body = mod.build_generation_source_packet(src)
    original_expand = mod._expand
    calls = []

    def corrupt(column, count):
        original_expand(column, count)
        calls.append(column[0])
        return ["corrupted"] * count

    monkeypatch.setattr(mod, "_expand", corrupt)
    with pytest.raises(mod.GenerationSourcePacketError):
        mod.decode_generation_source_packet(src, body)
    assert calls  # returning the current source without decoding cannot pass


def test_cold_import_and_all_operations_have_no_io_client_or_model_creation():
    code = r"""
import builtins, importlib, io, os, socket
import openai, pydantic_ai
from test_numeric_evidence import document
src = document("🧪 e\u0301 약\t37여 명 내외.\n\n 61~79명.")
def forbidden(*args, **kwargs): raise AssertionError("Unexpected I/O/client/model")
openai.AsyncOpenAI.__init__ = openai.OpenAI.__init__ = forbidden
pydantic_ai.Agent.__init__ = forbidden
original = type(os.environ).__getitem__
def no_env(self, key):
    if key != "PYDANTIC_DISABLE_PLUGINS": forbidden()
    return original(self, key)
type(os.environ).__getitem__ = no_env
builtins.open = io.open = forbidden
socket.socket = forbidden
mod = importlib.import_module("issuedigest_agents.generation_source_packet")
body = mod.build_generation_source_packet(src)
assert mod.validate_generation_source_packet(src, body) == body
assert mod.decode_generation_source_packet(src, body)["candidates"]
assert mod.generation_source_packet_prompt(src)
"""
    env = dict(os.environ)
    env.pop("OPENAI_API_KEY", None)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
