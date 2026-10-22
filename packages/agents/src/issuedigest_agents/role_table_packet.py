"""Pure lossless named-column input for the separate table audit profile."""

import json
from datetime import datetime
from types import UnionType
from typing import Annotated, Any, Literal, TypeAliasType, Union, cast, get_args, get_origin

from pydantic import AwareDatetime, BaseModel

from .balanced_role_generation import RoleAliasGenerationV2
from .compact_shared_context import _source_packet
from .numeric_evidence import Source, _json
from .semantic_role_audit_contract import _checked_generation, _coverage, _frame

_COLUMNS = {
    "contexts": [
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
    "events": ["id", "kind", "actor", "predicate", "tense"],
    "bindings": ["number", "context", "scopes", "status_sentence", "change"],
    "relations": ["kind", "from", "to", "support", "cue"],
    "candidates": [
        "id",
        "quote_id",
        "expression",
        "atoms",
        "separator",
        "qualifiers",
        "lexical_kind",
        "sentence_ids",
    ],
    "sentences": ["id", "text"],
    "scope_slots": ["number", "slots"],
}


class RoleTablePacketError(ValueError):
    """Sanitized whole-packet rejection without source or partial output."""


def _canonical(source: Source, generation: RoleAliasGenerationV2) -> dict[str, Any]:
    _original_values(source, Source)
    _original_values(generation, RoleAliasGenerationV2)
    generation = _checked_generation(source, generation)
    proposal, coverage, roles, slots = _coverage(generation)
    return cast(
        dict[str, Any],
        json.loads(
            _json(
                dict(
                    profile="role-table-audit-v1",
                    input_format="named-columns-v1",
                    **_source_packet(_frame(generation).candidate_index),
                    proposal=proposal.model_dump(mode="json"),
                    change_coverage=coverage,
                    roles=roles,
                    scope_slots=[
                        dict(number=row.number, slots=[s.slot for s in row.scopes]) for row in slots
                    ],
                )
            )
        ),
    )


def _scalar_matches(value: Any, annotation: Any) -> bool:
    if isinstance(annotation, TypeAliasType):
        return _scalar_matches(value, annotation.__value__)
    if annotation is AwareDatetime:
        return type(value) is datetime and value.utcoffset() is not None
    origin, args = get_origin(annotation), get_args(annotation)
    if origin is Annotated:
        return _scalar_matches(value, args[0])
    if origin in (Union, UnionType):
        return any(_scalar_matches(value, option) for option in args)
    if origin is Literal:
        return any(type(value) is type(option) and value == option for option in args)
    return type(value) is annotation


def _original_values(value: Any, annotation: Any) -> None:
    # Inspect live fields first: serialization can erase subclasses or restore defaults.
    if isinstance(value, BaseModel):
        if value.__dict__.keys() != type(value).model_fields.keys():
            raise ValueError("Missing or extra original fields")
        for key, child in value.__dict__.items():
            _original_values(child, type(value).model_fields[key].annotation)
    elif isinstance(value, (tuple, list, dict)):
        if type(value) not in (tuple, list, dict):
            raise ValueError("Unexpected original container subclass")
        if get_origin(annotation) is not tuple or type(value) is not tuple:
            raise ValueError("Expected original tuple")
        args = get_args(annotation)
        for i, child in enumerate(value):
            _original_values(child, args[0] if args[-1] is Ellipsis else args[i])
    elif not _scalar_matches(value, annotation):
        raise ValueError("Unexpected original scalar type")


def _table(name: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    columns = _COLUMNS[name]
    return dict(columns=columns.copy(), rows=[[row[key] for key in columns] for row in records])


def build_role_table_packet(source: Source, generation: RoleAliasGenerationV2) -> dict[str, Any]:
    """Encode the complete current source and unchanged validated v2 role proposal."""
    try:
        packet = _canonical(source, generation)
        packet["candidates"] = _table("candidates", packet["candidates"])
        packet["scope_slots"] = _table("scope_slots", packet["scope_slots"])
        packet["proposal"] = {key: _table(key, rows) for key, rows in packet["proposal"].items()}
        for quote in packet["quotes"]:
            quote["sentences"] = _table("sentences", quote["sentences"])
        return packet
    except Exception:
        raise RoleTablePacketError("Invalid role table packet") from None


def _records(name: str, table: Any) -> list[dict[str, Any]]:
    if set(table) != {"columns", "rows"}:
        raise ValueError("Invalid table keys")
    _same_json(table["columns"], _COLUMNS[name])
    if type(table["rows"]) is not list or any(type(row) is not list for row in table["rows"]):
        raise ValueError("Expected exact row arrays")
    return [dict(zip(_COLUMNS[name], row, strict=True)) for row in table["rows"]]


def _copy_json(value: Any) -> Any:
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError("Expected exact string keys")
        return {key: _copy_json(child) for key, child in value.items()}
    if type(value) is list:
        return [_copy_json(child) for child in value]
    if type(value) not in (str, int, float, bool, type(None)):
        raise ValueError("Expected exact JSON values")
    return value


def _same_json(value: Any, expected: Any) -> None:
    if type(value) is not type(expected):
        raise ValueError("JSON value type differs")
    if type(expected) is dict:
        if value.keys() != expected.keys():
            raise ValueError("JSON object fields differ")
        for key in expected:
            _same_json(value[key], expected[key])
    elif type(expected) is list:
        if len(value) != len(expected):
            raise ValueError("JSON array length differs")
        for child, original in zip(value, expected, strict=True):
            _same_json(child, original)
    elif value != expected:
        raise ValueError("JSON scalar differs")


def decode_role_table_packet(
    source: Source, generation: RoleAliasGenerationV2, packet: Any
) -> dict[str, Any]:
    """Decode only a complete packet matching the current source and original roles."""
    try:
        expected = _canonical(source, generation)
        packet = _copy_json(packet)
        decoded = dict(packet)
        decoded["candidates"] = _records("candidates", packet["candidates"])
        decoded["scope_slots"] = _records("scope_slots", packet["scope_slots"])
        decoded["proposal"] = {
            key: _records(key, table) for key, table in packet["proposal"].items()
        }
        decoded["quotes"] = [
            {**quote, "sentences": _records("sentences", quote["sentences"])}
            for quote in packet["quotes"]
        ]
        _same_json(decoded, expected)
        return decoded
    except Exception:
        raise RoleTablePacketError("Invalid role table packet") from None
