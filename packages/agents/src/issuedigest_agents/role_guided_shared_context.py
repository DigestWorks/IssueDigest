"""Separate role guidance over the frozen shared-context schema and borrowed runtime."""

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, model_validator
from pydantic_ai import ToolOutput
from pydantic_ai.models import Model

from . import contextual_frame_generation as _runtime
from . import shared_context_generation as _v1
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
from .shared_measurement_context import SharedMeasurementFrame, _actual_models


class RoleGuidedSharedContextError(_v1.SharedContextGenerationError):
    """Sanitized failure retaining nullable observed usage."""


class RoleGuidedSharedContextGeneration(_StrictModel):
    """New-profile consistency receipts; never semantic review or authorization."""

    profile: Literal["role-guided-shared-context-v1"] = "role-guided-shared-context-v1"
    status: Literal["unreviewed"] = "unreviewed"
    frame: SharedMeasurementFrame
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        _bounded_usage(self.usage)
        return self


PROVIDER_IDENTITY = "issuedigest_role_guided_shared_context_v1"
ROLE_GUIDANCE = (
    "The measured_variable must identify the object or phenomenon counted by the quantity. "
    "An action or state predicate alone must not replace what is being counted. Keep "
    "geographic, population and institutional scope in separate target_scopes. Preserve "
    "every explicitly applicable broader and narrower scope, including hierarchical "
    "geographic levels. A broad context_text only locates the selected role text; it does "
    "not restore an object or scope missing from that role. Do not infer location from an "
    "institution's name or propagate scope from neighboring sentences without explicit "
    "applicability evidence. Do not arbitrarily drop or merge scopes to hide exceeding the "
    "combined limit of four. Do not invent ambiguous roles."
)
ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS = (
    _v1.SHARED_CONTEXT_INSTRUCTIONS.replace(
        "fill_shared_context_v1", "fill_role_guided_shared_context_v1"
    )
    + " "
    + ROLE_GUIDANCE
)


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    original_prompt, original_tools = _v1._preflight(source)
    packet = json.loads(original_prompt)
    packet["profile"] = "role-guided-shared-context-v1"
    prompt = _json(packet)
    tools = [
        ToolOutput(
            tool.output,
            name="fill_role_guided_shared_context_v1",
            description=tool.description,
            strict=tool.strict,
        )
        for tool in original_tools
    ]
    envelope = (
        len(prompt.encode("utf-8"))
        + len(ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + MAX_OUTPUT_TOKENS
    )
    if envelope > MAX_RUN_TOKENS:
        raise ValueError("Invalid role-guided request envelope")
    return prompt, tools


def role_guided_shared_context_prompt(source: Source) -> str:
    """Preflight the complete source and actual new envelope without I/O or truncation."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise RoleGuidedSharedContextError("Invalid role-guided shared context input") from None


def validate_role_guided_shared_context(
    source: Source, result: RoleGuidedSharedContextGeneration | dict[str, Any]
) -> RoleGuidedSharedContextGeneration:
    """Check this profile before delegating full reconstruction to the frozen validator."""
    try:
        prompt, _ = _preflight(source)
        # Inspect actual types before reparsing: serialization can hide subclasses and
        # unchecked dict/list replacements. The receipt translation must not erase them.
        _canonical_models(result, RoleGuidedSharedContextGeneration)
        if isinstance(result, BaseModel):
            _actual_models(result, RoleGuidedSharedContextGeneration)
        checked = _read(RoleGuidedSharedContextGeneration, result)
        if (
            checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stale role-guided receipts")
        original_prompt = _v1.shared_context_prompt(source)
        # Only validated new-profile receipts cross this internal adapter. The v1
        # validator then enforces today's exact dynamic slots and complete source frame.
        translated = _v1.SharedContextGeneration(
            frame=checked.frame,
            prompt_sha256=sha256(original_prompt.encode("utf-8")).hexdigest(),
            instructions_sha256=sha256(_v1.SHARED_CONTEXT_INSTRUCTIONS.encode("utf-8")).hexdigest(),
            usage=checked.usage,
        )
        _v1.validate_shared_context_generation(source, translated)
        return checked
    except Exception:
        raise RoleGuidedSharedContextError("Invalid role-guided shared context") from None


@dataclass(frozen=True)
class _RoleGuidedSharedContextFramer:
    model: Model


def create_role_guided_shared_context_framer(model: Model) -> _RoleGuidedSharedContextFramer:
    """Lazily borrow the caller's required Model and its client lifecycle."""
    if not isinstance(model, Model):
        raise RoleGuidedSharedContextError("Invalid role-guided shared context model") from None
    return _RoleGuidedSharedContextFramer(model)


def run_role_guided_shared_context_framer(
    framer: _RoleGuidedSharedContextFramer, source: Source
) -> RoleGuidedSharedContextGeneration:
    """Make one bounded request with the original builder, no retry, repair or fallback."""
    try:
        if type(framer) is not _RoleGuidedSharedContextFramer or not isinstance(
            framer.model, Model
        ):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
    except Exception:
        raise RoleGuidedSharedContextError("Invalid role-guided shared context input") from None
    return _runtime._run_contextual_request(
        model=framer.model,
        source=source,
        prompt=prompt,
        tools=tools,
        instructions=ROLE_GUIDED_SHARED_CONTEXT_INSTRUCTIONS,
        identity=PROVIDER_IDENTITY,
        result_model=RoleGuidedSharedContextGeneration,
        validator=validate_role_guided_shared_context,
        error_type=RoleGuidedSharedContextError,
        failure_message="Role-guided shared context generation failed",
        frame_builder=_v1._build_shared_output,
    )
