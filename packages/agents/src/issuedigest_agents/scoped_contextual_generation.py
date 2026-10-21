"""One unreviewed contextual frame request with explicit scope and status guidance."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel
from pydantic_ai import ToolOutput
from pydantic_ai.models import Model

from . import contextual_frame_generation as _v1
from .contextual_frame import validate_contextual_frame
from .numeric_evidence import MAX_OUTPUT_TOKENS, MAX_RUN_TOKENS, Source, _json
from .numeric_selection_evaluation import _read
from .research import PROVIDER_FRAMING_ALLOWANCE
from .research_v5 import _provider_schema_bytes_v5


class ScopedContextualGenerationError(_v1.ContextualFrameGenerationError):
    """Sanitized scoped request failure with nullable observed usage."""


class ScopedContextualFrameGeneration(_v1.ContextualFrameGeneration):
    """Scoped instruction receipts, never semantic review or truth certification."""

    profile: Literal["scoped-contextual-frame-generation-v1"] = (
        "scoped-contextual-frame-generation-v1"  # type: ignore[assignment]
    )


SCOPE_STATUS_GUIDANCE = (
    "Measured_entity must identify the measured object and its explicit geographic, "
    "population, institutional or subgroup scope. Preserve necessary scope in a sufficient "
    "contiguous source phrase; an event or action predicate alone drops scope. A broader "
    "context_text locates text but does not restore scope omitted from measured_entity.text. "
    "For known value_status, status_text.text itself must contain explicit predicate or "
    "status evidence attached to that quantity. Topic or case particles, connectives, "
    "punctuation or numbers alone do not supply that evidence, even if context_text or "
    "reporting_tense_text contains it. Prefer sufficient evidence over maximum brevity. "
    "If support is absent, use unknown/null; never infer missing scope or status."
)
SCOPED_CONTEXTUAL_INSTRUCTIONS = (
    _v1.CONTEXTUAL_FRAME_INSTRUCTIONS.replace(
        "fill_contextual_frame_v1", "fill_scoped_contextual_frame_v1"
    )
    + " "
    + SCOPE_STATUS_GUIDANCE
)
PROVIDER_IDENTITY = "issuedigest_scoped_contextual_frame_v1"


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    prompt, original_tools = _v1._preflight(source)
    packet = json.loads(prompt)
    packet["profile"] = "scoped-contextual-frame-generation-v1"
    prompt = _json(packet)
    tools = [
        ToolOutput(
            tool.output,
            name="fill_scoped_contextual_frame_v1",
            description=tool.description,
            strict=tool.strict,
        )
        for tool in original_tools
    ]
    envelope = (
        len(prompt.encode("utf-8"))
        + len(SCOPED_CONTEXTUAL_INSTRUCTIONS.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + MAX_OUTPUT_TOKENS
    )
    if envelope > MAX_RUN_TOKENS:
        raise ValueError("Invalid frame request envelope")
    return prompt, tools


def scoped_contextual_frame_prompt(source: Source) -> str:
    """Preflight the complete source and scoped envelope without truncation or I/O."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise ScopedContextualGenerationError(
            "Invalid scoped contextual frame generation input"
        ) from None


def validate_scoped_contextual_frame_generation(
    source: Source, result: ScopedContextualFrameGeneration | dict[str, Any]
) -> ScopedContextualFrameGeneration:
    """Rebuild the exact source frame and check the scoped instruction receipts."""
    try:
        prompt, _ = _preflight(source)
        checked = _read(ScopedContextualFrameGeneration, result)
        validate_contextual_frame(source, checked.frame)
        if (
            checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(SCOPED_CONTEXTUAL_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stale generation receipts")
        return checked
    except Exception:
        raise ScopedContextualGenerationError(
            "Invalid scoped contextual frame generation"
        ) from None


@dataclass(frozen=True)
class _ScopedContextualFramer:
    model: Model


def create_scoped_contextual_framer(model: Model) -> _ScopedContextualFramer:
    """Borrow the caller's required Model without allocating a client or owning lifecycle."""
    if not isinstance(model, Model):
        raise ScopedContextualGenerationError(
            "Invalid scoped contextual frame generation model"
        ) from None
    return _ScopedContextualFramer(model)


def run_scoped_contextual_framer(
    framer: _ScopedContextualFramer, source: Source
) -> ScopedContextualFrameGeneration:
    """Make one bounded request using the shared strict contextual frame runtime."""
    try:
        if type(framer) is not _ScopedContextualFramer or not isinstance(framer.model, Model):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
        instructions = SCOPED_CONTEXTUAL_INSTRUCTIONS
    except Exception:
        raise ScopedContextualGenerationError(
            "Invalid scoped contextual frame generation input"
        ) from None
    return _v1._run_contextual_request(
        model=framer.model,
        source=source,
        prompt=prompt,
        tools=tools,
        instructions=instructions,
        identity=PROVIDER_IDENTITY,
        result_model=ScopedContextualFrameGeneration,
        validator=validate_scoped_contextual_frame_generation,
        error_type=ScopedContextualGenerationError,
        failure_message="Scoped contextual frame generation failed",
    )
