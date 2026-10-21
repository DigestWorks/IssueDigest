"""One bounded borrowed-model shared context request preserving the full v2 numeric index."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, model_validator
from pydantic_ai import ToolOutput
from pydantic_ai.models import Model

from . import contextual_frame_generation as _runtime
from . import shared_context_generation as _v1
from .measurement_frame_generation import _eligible
from .numeric_candidates import NumericCandidateIndex
from .numeric_candidates_v2 import build_numeric_candidates_v2
from .numeric_evidence import (
    MAX_OUTPUT_TOKENS,
    MAX_RUN_TOKENS,
    KnownUsage,
    Source,
    _bounded_usage,
    _json,
    _StrictModel,
)
from .numeric_selection import _prompt
from .numeric_selection_evaluation import _canonical_models, _read
from .research import PROVIDER_FRAMING_ALLOWANCE
from .research_v5 import _provider_schema_bytes_v5
from .role_guided_shared_context import ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS
from .shared_measurement_context import SharedMeasurementInput, _actual_models
from .shared_measurement_context_v2 import (
    SharedMeasurementFrameV2,
    build_shared_measurement_frame_v2,
    validate_shared_measurement_frame_v2,
)


class SharedContextGenerationError(_runtime.ContextualFrameGenerationError):
    """Sanitized whole-operation failure retaining nullable observed usage."""


class SharedContextGenerationV2(_StrictModel):
    """Current-source consistency receipts, never semantic or authorization approval."""

    profile: Literal["shared-context-generation-v2"] = "shared-context-generation-v2"
    status: Literal["unreviewed"] = "unreviewed"
    frame: SharedMeasurementFrameV2
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        _bounded_usage(self.usage)
        return self


PROVIDER_IDENTITY = "issuedigest_shared_context_v2"
SHARED_CONTEXT_INSTRUCTIONS_V2 = ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS.replace(
    "fill_role_guided_shared_context_v1", "fill_shared_context_v2"
)


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    _canonical_models(source, Source)
    _actual_models(source, Source)
    index = build_numeric_candidates_v2(source)
    # The frozen helpers enumerate only common structural fields. This cast has
    # no runtime effect and never converts or regenerates the index as v1.
    structural = cast(NumericCandidateIndex, index)
    tools = [
        ToolOutput(
            tool.output,
            name="fill_shared_context_v2",
            description=tool.description,
            strict=tool.strict,
        )
        for tool in _v1._frame_tools(structural)
    ]
    packet = json.loads(_prompt(source, structural))
    packet.update(
        profile="shared-context-generation-v2",
        eligible_status_sentence_ids=_eligible(structural),
        context_id_slots=_v1.CONTEXT_ID_SLOTS,
        reporting_event_id_slots=_v1.REPORTING_EVENT_ID_SLOTS,
    )
    prompt = _json(packet)
    envelope = (
        len(prompt.encode("utf-8"))
        + len(SHARED_CONTEXT_INSTRUCTIONS_V2.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + MAX_OUTPUT_TOKENS
    )
    if envelope > MAX_RUN_TOKENS:
        raise ValueError("Invalid shared v2 request envelope")
    return prompt, tools


def shared_context_prompt_v2(source: Source) -> str:
    """Preflight whole source, v2 candidates and actual schemas without truncation or I/O."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise SharedContextGenerationError("Invalid shared context v2 input") from None


def _build_shared_output_v2(
    source: Source, output: BaseModel, output_type: type[BaseModel]
) -> SharedMeasurementFrameV2:
    # Validate actual dynamic nodes/tuples before narrowing drops their types.
    _canonical_models(output, output_type)
    _actual_models(output, output_type)
    dynamic = _read(output_type, output)
    canonical = SharedMeasurementInput.model_validate_json(dynamic.model_dump_json(), strict=True)
    return build_shared_measurement_frame_v2(source, canonical)


def validate_shared_context_generation_v2(
    source: Source, result: SharedContextGenerationV2 | dict[str, Any]
) -> SharedContextGenerationV2:
    """Rebuild the whole v2 frame and check today's dynamic catalogs, slots and receipts."""
    try:
        prompt, tools = _preflight(source)
        _canonical_models(result, SharedContextGenerationV2)
        if isinstance(result, BaseModel):
            _actual_models(result, SharedContextGenerationV2)
        checked = _read(SharedContextGenerationV2, result)
        validate_shared_measurement_frame_v2(source, checked.frame)
        output_type = tools[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        # The stored input is canonical; enforce current source-specific enums and
        # event variants before reconstructing its complete resolved v2 frame.
        dynamic = output_type.model_validate_json(
            checked.frame.input.model_dump_json(), strict=True
        )
        if _build_shared_output_v2(source, dynamic, output_type) != checked.frame:
            raise ValueError("Stored shared v2 frame differs from current reconstruction")
        if (
            checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(SHARED_CONTEXT_INSTRUCTIONS_V2.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stale shared v2 generation receipts")
        return checked
    except Exception:
        raise SharedContextGenerationError("Invalid shared context v2 generation") from None


@dataclass(frozen=True)
class _SharedContextFramerV2:
    model: Model


def create_shared_context_framer_v2(model: Model) -> _SharedContextFramerV2:
    """Lazily borrow the caller's required model and its client lifecycle."""
    if not isinstance(model, Model):
        raise SharedContextGenerationError("Invalid shared context v2 model") from None
    return _SharedContextFramerV2(model)


def run_shared_context_framer_v2(
    framer: _SharedContextFramerV2, source: Source
) -> SharedContextGenerationV2:
    """Make one bounded request with no retry, repair, fallback or partial output."""
    try:
        if type(framer) is not _SharedContextFramerV2 or not isinstance(framer.model, Model):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
    except Exception:
        raise SharedContextGenerationError("Invalid shared context v2 input") from None
    return _runtime._run_contextual_request(
        model=framer.model,
        source=source,
        prompt=prompt,
        tools=tools,
        instructions=SHARED_CONTEXT_INSTRUCTIONS_V2,
        identity=PROVIDER_IDENTITY,
        result_model=SharedContextGenerationV2,
        validator=validate_shared_context_generation_v2,
        error_type=SharedContextGenerationError,
        failure_message="Shared context v2 generation failed",
        frame_builder=_build_shared_output_v2,
    )
