"""Pure canonical column encoding of the complete balanced v2 source projection."""

import json
import re
from typing import Any, cast

from .compact_shared_context import _source_packet
from .measurement_frame_generation import _eligible
from .numeric_candidates import NumericCandidateIndex
from .numeric_candidates_v2 import build_numeric_candidates_v2
from .numeric_evidence import Source, _json
from .role_link_catalog import _actual
from .role_table_packet import _copy_json, _same_json
from .shared_context_generation import CONTEXT_ID_SLOTS, REPORTING_EVENT_ID_SLOTS

GENERATION_SOURCE_PACKET_INSTRUCTIONS = (
    "Columns align by zero-based row. values stores a vector; constant repeats one value; "
    "dictionary stores pool,indices; indexed stores prefix,suffixes; indexed_lists stores "
    "prefix,suffix-lists. Atoms use atom_columns."
)

_CANDIDATE_FIELDS = (
    "id",
    "quote_id",
    "sentence_ids",
    "expression",
    "atoms",
    "lexical_kind",
    "qualifiers",
    "separator",
)
_ATOM_FIELDS = ("number", "unit")
_LOCAL_ID = re.compile(r"([qsnec])([1-9][0-9]*)")


class GenerationSourcePacketError(ValueError):
    """Sanitized whole-operation failure without source or partial output."""


def _original(source: Source) -> dict[str, Any]:
    # Inspect exact live model/container/scalar types and required fields before dumping.
    _actual(source, Source)
    index = build_numeric_candidates_v2(source)
    return cast(
        dict[str, Any],
        json.loads(
            _json(
                dict(
                    profile="shared-role-aliases-v2",
                    **_source_packet(index),
                    eligible_status_sentence_ids=_eligible(cast(NumericCandidateIndex, index)),
                    context_id_slots=CONTEXT_ID_SLOTS,
                    reporting_event_id_slots=REPORTING_EVENT_ID_SLOTS,
                )
            )
        ),
    )


def _indexed(values: list[Any]) -> tuple[str, list[int]] | None:
    if not values or any(type(value) is not str for value in values):
        return None
    matches = [_LOCAL_ID.fullmatch(value) for value in values]
    if any(match is None for match in matches):
        return None
    parts = [match.groups() for match in matches if match is not None]
    prefix = parts[0][0]
    if any(part[0] != prefix for part in parts):
        return None
    return prefix, [int(suffix) for _, suffix in parts]


def _column(values: list[Any], *, id_bearing: bool = False) -> list[Any]:
    """Choose by canonical UTF-8 byte length, with stable specified option precedence."""
    options: list[list[Any]] = [["values", values]]
    if values:
        # Canonical JSON keys preserve JSON type distinctions, including true versus 1.
        keys = [_json(value) for value in values]
        if all(key == keys[0] for key in keys):
            options.append(["constant", values[0]])
        pool: list[Any] = []
        positions: dict[str, int] = {}
        indices: list[int] = []
        for key, value in zip(keys, values, strict=True):
            if key not in positions:
                positions[key] = len(pool)
                pool.append(value)
            indices.append(positions[key])
        options.append(["dictionary", pool, indices])
        # Only machine identifiers are eligible; literal source content stays opaque.
        if id_bearing:
            indexed = _indexed(values)
            if indexed is not None:
                options.append(["indexed", indexed[0], indexed[1]])
            if all(type(value) is list for value in values):
                flattened = [child for value in values for child in value]
                indexed = _indexed(flattened)
                if indexed is not None:
                    offset = 0
                    suffix_lists = []
                    for value in values:
                        suffix_lists.append(indexed[1][offset : offset + len(value)])
                        offset += len(value)
                    options.append(["indexed_lists", indexed[0], suffix_lists])
    chosen = min(options, key=lambda option: len(_json(option).encode("utf-8")))
    return cast(list[Any], _copy_json(chosen))


def _encode(original: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        {
            **candidate,
            "atoms": [[atom[field] for field in _ATOM_FIELDS] for atom in candidate["atoms"]],
        }
        for candidate in original["candidates"]
    ]
    return dict(
        input_format="columnar-generation-source-v1",
        profile=original["profile"],
        atom_columns=list(_ATOM_FIELDS),
        candidate_count=len(candidates),
        candidate_columns={
            field: _column(
                [candidate[field] for candidate in candidates],
                id_bearing=field in ("id", "quote_id", "sentence_ids"),
            )
            for field in _CANDIDATE_FIELDS
        },
        quotes=[
            dict(
                quote_id=quote["quote_id"],
                sentence_count=len(quote["sentences"]),
                sentence_columns={
                    field: _column(
                        [sentence[field] for sentence in quote["sentences"]],
                        id_bearing=field == "id",
                    )
                    for field in ("id", "text")
                },
            )
            for quote in original["quotes"]
        ],
        **{
            field: _column(original[field], id_bearing=True)
            for field in (
                "eligible_status_sentence_ids",
                "context_id_slots",
                "reporting_event_id_slots",
            )
        },
    )


def build_generation_source_packet(source: Source) -> dict[str, Any]:
    """Return a fresh mutable JSON packet retaining every current-source value."""
    try:
        return _encode(_original(source))
    except Exception:
        raise GenerationSourcePacketError("Invalid generation source packet") from None


def _checked(source: Source, packet: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    # Raw packet types are inspected before they can be erased by dumping or decoding.
    packet = _copy_json(packet)
    original = _original(source)
    _same_json(packet, _encode(original))
    return original, cast(dict[str, Any], packet)


def validate_generation_source_packet(source: Source, packet: Any) -> dict[str, Any]:
    """Require the exact canonical current-source encoding before interpreting columns."""
    try:
        return _checked(source, packet)[1]
    except Exception:
        raise GenerationSourcePacketError("Invalid generation source packet") from None


def _expand(column: list[Any], count: int | None) -> list[Any]:
    # This helper only receives a complete packet already matched against its canonical form.
    mode = column[0]
    if mode == "values":
        values = column[1]
    elif mode == "constant":
        if count is None:
            raise ValueError("Constant column requires a row count")
        values = [column[1] for _ in range(count)]
    elif mode == "dictionary":
        values = [column[1][index] for index in column[2]]
    elif mode == "indexed":
        values = [column[1] + str(suffix) for suffix in column[2]]
    elif mode == "indexed_lists":
        values = [[column[1] + str(suffix) for suffix in row] for row in column[2]]
    else:
        raise ValueError("Invalid column mode")
    if count is not None and len(values) != count:
        raise ValueError("Invalid column length")
    return cast(list[Any], _copy_json(values))


def decode_generation_source_packet(source: Source, packet: Any) -> dict[str, Any]:
    """Expand canonical columns and verify the entire reconstructed original projection."""
    try:
        original, packet = _checked(source, packet)
        columns = {
            field: _expand(packet["candidate_columns"][field], packet["candidate_count"])
            for field in _CANDIDATE_FIELDS
        }
        candidates = []
        for row in range(packet["candidate_count"]):
            candidate = {field: columns[field][row] for field in _CANDIDATE_FIELDS}
            candidate["atoms"] = [
                dict(zip(packet["atom_columns"], atom, strict=True)) for atom in candidate["atoms"]
            ]
            candidates.append(candidate)
        quotes = []
        for quote in packet["quotes"]:
            ids = _expand(quote["sentence_columns"]["id"], quote["sentence_count"])
            texts = _expand(quote["sentence_columns"]["text"], quote["sentence_count"])
            quotes.append(
                dict(
                    quote_id=quote["quote_id"],
                    sentences=[
                        dict(id=sid, text=text) for sid, text in zip(ids, texts, strict=True)
                    ],
                )
            )
        decoded = dict(
            profile=packet["profile"],
            candidates=candidates,
            quotes=quotes,
            **{
                field: _expand(packet[field], len(original[field]))
                for field in (
                    "eligible_status_sentence_ids",
                    "context_id_slots",
                    "reporting_event_id_slots",
                )
            },
        )
        _same_json(decoded, original)
        return decoded
    except Exception:
        raise GenerationSourcePacketError("Invalid generation source packet") from None


def generation_source_packet_prompt(source: Source) -> str:
    """Serialize the complete packet without asserting provider-envelope acceptance."""
    try:
        return _json(build_generation_source_packet(source))
    except Exception:
        raise GenerationSourcePacketError("Invalid generation source packet") from None
