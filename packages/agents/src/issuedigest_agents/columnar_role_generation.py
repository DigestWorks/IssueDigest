"""Columnar source generation with independent receipts and unchanged role frames."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, model_validator
from pydantic_ai import ToolOutput
from pydantic_ai.messages import ModelResponse, ThinkingPart, ToolCallPart
from pydantic_ai.models import Model

from .balanced_role_generation import BALANCED_ROLE_INSTRUCTIONS
from .generation_source_packet import (
    GENERATION_SOURCE_PACKET_INSTRUCTIONS,
    generation_source_packet_prompt,
)
from .numeric_candidates_v2 import build_numeric_candidates_v2
from .numeric_evidence import KnownUsage, Source, _StrictModel
from .numeric_selection_evaluation import _read
from .role_alias_contract import (
    RoleAliasFrame,
    _guard,
    _input_model,
    _require_frame_markers,
    validate_role_alias_frame,
)
from .role_alias_generation import _build_output
from .role_bounded_runtime import RoleRequestError, _request_envelope, _run_role_request
from .role_link_catalog import _required_raw
from .role_table_packet import _copy_json, _original_values
from .scope_role_audit import _ObservedAuditModel

PROVIDER_IDENTITY = "issuedigest_columnar_role_generation_v1"
COLUMNAR_ROLE_INSTRUCTIONS = BALANCED_ROLE_INSTRUCTIONS.replace(
    "fill_shared_role_aliases_v2", "fill_columnar_roles_v1"
).replace(
    "Each quote contains complete ordered sentences {id,text}; concatenate without separators, "
    "preserving whitespace and blank sentences. ",
    "Input format is columnar-generation-source-v1. "
    + GENERATION_SOURCE_PACKET_INSTRUCTIONS
    + " Concatenate decoded quote sentences without separators, preserving whitespace and blanks. ",
)


class ColumnarRoleGenerationError(RoleRequestError):
    """Sanitized failure retaining observed cost and dispatch uncertainty."""


class ColumnarRoleGeneration(_StrictModel):
    profile: Literal["columnar-role-generation-v1"]
    input_format: Literal["columnar-generation-source-v1"]
    status: Literal["unreviewed"]
    frame: RoleAliasFrame
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        if (
            self.usage.requests != 1
            or self.usage.output_tokens > 1800
            or self.usage.input_tokens + self.usage.output_tokens > 20000
        ):
            raise ValueError("Invalid columnar role generation budget")
        return self


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    # The codec guards the exact live Source before any serialization.
    prompt = generation_source_packet_prompt(source)
    index = build_numeric_candidates_v2(source)
    tools = [ToolOutput(_input_model(index), name="fill_columnar_roles_v1", strict=True)]
    if _request_envelope(prompt, tools, COLUMNAR_ROLE_INSTRUCTIONS, 1800) > 20000:
        raise ValueError("Invalid columnar role request envelope")
    return prompt, tools


def columnar_role_prompt(source: Source) -> str:
    """Preflight the complete canonical packet, instructions and dynamic tool without I/O."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise ColumnarRoleGenerationError("Invalid columnar role generation input") from None


def validate_columnar_role_generation(
    source: Source, result: ColumnarRoleGeneration | dict[str, Any]
) -> ColumnarRoleGeneration:
    """Reconstruct current source, catalogs, frame and hashes without semantic approval."""
    try:
        prompt, tools = _preflight(source)
        _guard(result, ColumnarRoleGeneration)
        if isinstance(result, BaseModel):
            _original_values(result, ColumnarRoleGeneration)
        else:
            _copy_json(result)
            _required_raw(result, ColumnarRoleGeneration)
        fields = result.__dict__ if isinstance(result, BaseModel) else result
        if not ColumnarRoleGeneration.model_fields.keys() <= fields.keys():
            raise ValueError("Missing stored generation fields")
        _require_frame_markers(fields["frame"])
        checked = _read(ColumnarRoleGeneration, result)
        validate_role_alias_frame(source, checked.frame)
        output_type = tools[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        dynamic = output_type.model_validate_json(
            checked.frame.input.model_dump_json(), strict=True
        )
        if (
            _build_output(source, dynamic, output_type) != checked.frame
            or checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(COLUMNAR_ROLE_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stored columnar generation differs from reconstruction")
        return checked
    except Exception:
        raise ColumnarRoleGenerationError("Invalid columnar role generation") from None


@dataclass(frozen=True)
class _ColumnarRoleFramer:
    model: Model


def create_columnar_role_framer(model: Model) -> _ColumnarRoleFramer:
    """Lazily borrow the required Model; its lifecycle stays with the caller."""
    if not isinstance(model, Model):
        raise ColumnarRoleGenerationError("Invalid columnar role generation model") from None
    return _ColumnarRoleFramer(model)


def run_columnar_role_framer(framer: _ColumnarRoleFramer, source: Source) -> ColumnarRoleGeneration:
    """Make one bounded request without retries, repair, fallback or client ownership."""
    try:
        if type(framer) is not _ColumnarRoleFramer or not isinstance(framer.model, Model):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
    except Exception:
        raise ColumnarRoleGenerationError("Invalid columnar role generation input") from None
    known = None
    try:
        observed = _ObservedAuditModel(framer.model)
        output, known = _run_role_request(
            model=observed,
            prompt=prompt,
            tools=tools,
            instructions=COLUMNAR_ROLE_INSTRUCTIONS,
            identity=PROVIDER_IDENTITY,
            total_limit=20000,
            output_limit=1800,
        )
        if len(observed.responses) != 1 or not isinstance(observed.responses[0], ModelResponse):
            raise ValueError("Expected one original model response")
        parts = observed.responses[0].parts
        calls = [part for part in parts if isinstance(part, ToolCallPart)]
        if (
            len(calls) != 1
            or calls[0].tool_name != "fill_columnar_roles_v1"
            or any(not isinstance(part, (ToolCallPart, ThinkingPart)) for part in parts)
        ):
            raise ValueError("Expected only the single columnar output tool")
        output_type = tools[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        result = ColumnarRoleGeneration(
            profile="columnar-role-generation-v1",
            input_format="columnar-generation-source-v1",
            status="unreviewed",
            frame=_build_output(source, output, output_type),
            prompt_sha256=sha256(prompt.encode("utf-8")).hexdigest(),
            instructions_sha256=sha256(COLUMNAR_ROLE_INSTRUCTIONS.encode("utf-8")).hexdigest(),
            usage=known,
        )
        return validate_columnar_role_generation(source, result)
    except RoleRequestError as error:
        raise ColumnarRoleGenerationError(
            "Columnar role generation failed",
            known_usage=known if known is not None else error.known_usage,
            may_have_started=known is not None or error.may_have_started,
        ) from None
    except Exception:
        raise ColumnarRoleGenerationError(
            "Columnar role generation failed", known_usage=known, may_have_started=True
        ) from None
