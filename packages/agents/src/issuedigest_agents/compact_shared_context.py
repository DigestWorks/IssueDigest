"""Lossless local quote packets and a separate bounded shared v2 generation profile."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, model_validator
from pydantic_ai import ToolOutput
from pydantic_ai.models import Model

from . import contextual_frame_generation as _runtime
from . import shared_context_generation as _shared
from .measurement_frame_generation import _eligible
from .numeric_candidates import NumericCandidateIndex
from .numeric_candidates_v2 import NumericCandidateIndexV2, build_numeric_candidates_v2
from .numeric_evidence import (
    MAX_OUTPUT_TOKENS,
    MAX_RUN_TOKENS,
    KnownUsage,
    Source,
    _bounded_usage,
    _json,
    _StrictModel,
)
from .numeric_selection_evaluation import _canonical_models, _read
from .research import PROVIDER_FRAMING_ALLOWANCE
from .research_v5 import _provider_schema_bytes_v5
from .shared_context_generation_v2 import (
    SHARED_CONTEXT_INSTRUCTIONS_V2,
    _build_shared_output_v2,
)
from .shared_measurement_context import _actual_models
from .shared_measurement_context_v2 import (
    SharedMeasurementFrameV2,
    validate_shared_measurement_frame_v2,
)


class CompactSharedContextError(_runtime.ContextualFrameGenerationError):
    """Sanitized whole-operation failure retaining nullable observed usage."""


PROVIDER_IDENTITY = "issuedigest_compact_shared_context_v1"
COMPACT_SHARED_CONTEXT_INSTRUCTIONS = SHARED_CONTEXT_INSTRUCTIONS_V2.replace(
    "fill_shared_context_v2", "fill_compact_shared_context_v1"
) + (
    " Input quotes use local quote_id labels q1..q20 and complete ordered sentences "
    "{id,text}. Concatenate their text without separators to reconstruct each whole quote, "
    "preserving all whitespace and blank sentences. Candidates refer to quote_id; "
    "these local labels are not provenance or authorization."
)


def _source_packet(index: NumericCandidateIndexV2) -> dict[str, Any]:
    """Project a freshly rebuilt canonical source index without private provenance IDs."""
    _canonical_models(index, NumericCandidateIndexV2)
    _actual_models(index, NumericCandidateIndexV2)
    index = _read(NumericCandidateIndexV2, index)
    quote_ids: dict[str, str] = {}
    quotes: list[dict[str, Any]] = []
    position = 0
    sentence_ids: set[str] = set()
    for number, quote in enumerate(index.citations, 1):
        if quote.citation_id in quote_ids:
            raise ValueError("Duplicate quote")
        quote_id = f"q{number}"
        quote_ids[quote.citation_id] = quote_id
        sentences: list[dict[str, str]] = []
        end = 0
        while position < len(index.sentences):
            sentence = index.sentences[position]
            span = sentence.span
            if span.citation_id != quote.citation_id:
                break
            if (
                sentence.sentence_id in sentence_ids
                or span.start != end
                or span.end > len(quote.quote)
                or quote.quote[span.start : span.end] != span.text
            ):
                raise ValueError("Invalid complete sentence partition")
            sentence_ids.add(sentence.sentence_id)
            sentences.append({"id": sentence.sentence_id, "text": span.text})
            end = span.end
            position += 1
        if end != len(quote.quote) or "".join(s["text"] for s in sentences) != quote.quote:
            raise ValueError("Incomplete quote reconstruction")
        quotes.append({"quote_id": quote_id, "sentences": sentences})
    if position != len(index.sentences):
        raise ValueError("Unordered or unknown sentence quote")
    return {
        "quotes": quotes,
        "candidates": [
            {
                "id": c.candidate_id,
                "quote_id": quote_ids[c.expression.citation_id],
                "sentence_ids": c.sentence_ids,
                "lexical_kind": c.lexical_kind,
                "expression": c.expression.text,
                "atoms": [
                    {"number": a.number.text, "unit": a.unit.text if a.unit else None}
                    for a in c.atoms
                ],
                "separator": c.separator.text if c.separator else None,
                "qualifiers": [q.text for q in c.qualifiers],
            }
            for c in index.candidates
        ],
    }


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    _canonical_models(source, Source)
    _actual_models(source, Source)
    index = build_numeric_candidates_v2(source)
    # Frozen schema helpers read only common structural fields. This static cast
    # never converts the full v2 index or regenerates its values through v1.
    structural = cast(NumericCandidateIndex, index)
    tools = [
        ToolOutput(
            tool.output,
            name="fill_compact_shared_context_v1",
            description=tool.description,
            strict=tool.strict,
        )
        for tool in _shared._frame_tools(structural)
    ]
    prompt = _json(
        {
            "profile": "compact-shared-context-v1",
            **_source_packet(index),
            "eligible_status_sentence_ids": _eligible(structural),
            "context_id_slots": _shared.CONTEXT_ID_SLOTS,
            "reporting_event_id_slots": _shared.REPORTING_EVENT_ID_SLOTS,
        }
    )
    envelope = (
        len(prompt.encode("utf-8"))
        + len(COMPACT_SHARED_CONTEXT_INSTRUCTIONS.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + MAX_OUTPUT_TOKENS
    )
    if envelope > MAX_RUN_TOKENS:
        raise ValueError("Invalid compact shared context request envelope")
    return prompt, tools


def compact_shared_context_prompt(source: Source) -> str:
    """Preflight complete source, partition and actual schemas without truncation or I/O."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise CompactSharedContextError("Invalid compact shared context input") from None


class CompactSharedContextGeneration(_StrictModel):
    """Current-source consistency receipts, never semantic or authorization approval."""

    profile: Literal["compact-shared-context-v1"] = "compact-shared-context-v1"
    status: Literal["unreviewed"] = "unreviewed"
    frame: SharedMeasurementFrameV2
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        _bounded_usage(self.usage)
        return self


def validate_compact_shared_context_generation(
    source: Source, result: CompactSharedContextGeneration | dict[str, Any]
) -> CompactSharedContextGeneration:
    """Rebuild the whole frame, current dynamic input and compact receipts from source."""
    try:
        prompt, tools = _preflight(source)
        _canonical_models(result, CompactSharedContextGeneration)
        if isinstance(result, BaseModel):
            _actual_models(result, CompactSharedContextGeneration)
        checked = _read(CompactSharedContextGeneration, result)
        validate_shared_measurement_frame_v2(source, checked.frame)
        output_type = tools[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        dynamic = output_type.model_validate_json(
            checked.frame.input.model_dump_json(), strict=True
        )
        if _build_shared_output_v2(source, dynamic, output_type) != checked.frame:
            raise ValueError("Stored compact frame differs from current reconstruction")
        if (
            checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(COMPACT_SHARED_CONTEXT_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stale compact generation receipts")
        return checked
    except Exception:
        raise CompactSharedContextError("Invalid compact shared context generation") from None


@dataclass(frozen=True)
class _CompactSharedContextFramer:
    model: Model


def create_compact_shared_context_framer(model: Model) -> _CompactSharedContextFramer:
    """Lazily borrow the caller's required model and its client lifecycle."""
    if not isinstance(model, Model):
        raise CompactSharedContextError("Invalid compact shared context model") from None
    return _CompactSharedContextFramer(model)


def run_compact_shared_context_framer(
    framer: _CompactSharedContextFramer, source: Source
) -> CompactSharedContextGeneration:
    """Make one bounded request with no retry, repair, fallback or partial output."""
    try:
        if type(framer) is not _CompactSharedContextFramer or not isinstance(framer.model, Model):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
    except Exception:
        raise CompactSharedContextError("Invalid compact shared context input") from None
    return _runtime._run_contextual_request(
        model=framer.model,
        source=source,
        prompt=prompt,
        tools=tools,
        instructions=COMPACT_SHARED_CONTEXT_INSTRUCTIONS,
        identity=PROVIDER_IDENTITY,
        result_model=CompactSharedContextGeneration,
        validator=validate_compact_shared_context_generation,
        error_type=CompactSharedContextError,
        failure_message="Compact shared context generation failed",
        frame_builder=_build_shared_output_v2,
    )
