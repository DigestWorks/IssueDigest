"""Balanced v2 generation with independent receipts and the unchanged alias frame."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, model_validator
from pydantic_ai import ToolOutput
from pydantic_ai.models import Model

from .compact_shared_context import _source_packet
from .measurement_frame_generation import _eligible
from .numeric_candidates import NumericCandidateIndex
from .numeric_candidates_v2 import build_numeric_candidates_v2
from .numeric_evidence import KnownUsage, Source, _json, _StrictModel
from .numeric_selection_evaluation import _read
from .role_alias_contract import (
    RoleAliasFrame,
    _guard,
    _input_model,
    _require_frame_markers,
    validate_role_alias_frame,
)
from .role_alias_generation import ROLE_ALIAS_INSTRUCTIONS, _build_output
from .role_bounded_runtime import RoleRequestError, _request_envelope, _run_role_request
from .shared_context_generation import CONTEXT_ID_SLOTS, REPORTING_EVENT_ID_SLOTS

PROVIDER_IDENTITY = "issuedigest_shared_role_aliases_v2"
BALANCED_ROLE_INSTRUCTIONS = ROLE_ALIAS_INSTRUCTIONS.replace(
    "fill_shared_role_aliases_v1", "fill_shared_role_aliases_v2"
)


class BalancedRoleGenerationError(RoleRequestError):
    """Sanitized v2 failure retaining observed cost and dispatch uncertainty."""


class RoleAliasGenerationV2(_StrictModel):
    profile: Literal["shared-role-aliases-v2"]
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
            raise ValueError("Invalid balanced role generation budget")
        return self


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    _guard(source, Source)
    index = build_numeric_candidates_v2(source)
    tools = [ToolOutput(_input_model(index), name="fill_shared_role_aliases_v2", strict=True)]
    prompt = _json(
        dict(
            profile="shared-role-aliases-v2",
            **_source_packet(index),
            eligible_status_sentence_ids=_eligible(cast(NumericCandidateIndex, index)),
            context_id_slots=CONTEXT_ID_SLOTS,
            reporting_event_id_slots=REPORTING_EVENT_ID_SLOTS,
        )
    )
    if _request_envelope(prompt, tools, BALANCED_ROLE_INSTRUCTIONS, 1800) > 20000:
        raise ValueError("Invalid balanced role request envelope")
    return prompt, tools


def balanced_role_prompt(source: Source) -> str:
    """Preflight the complete source, instructions and raw/normalized schema without I/O."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise BalancedRoleGenerationError("Invalid balanced role generation input") from None


def validate_balanced_role_generation(
    source: Source, result: RoleAliasGenerationV2 | dict[str, Any]
) -> RoleAliasGenerationV2:
    """Reconstruct the v2 receipt, full frame, source and current dynamic catalogs."""
    try:
        prompt, tools = _preflight(source)
        _guard(result, RoleAliasGenerationV2)
        fields = result.__dict__ if isinstance(result, BaseModel) else result
        if not RoleAliasGenerationV2.model_fields.keys() <= fields.keys():
            raise ValueError("Missing stored generation fields")
        _require_frame_markers(fields["frame"])
        checked = _read(RoleAliasGenerationV2, result)
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
            != sha256(BALANCED_ROLE_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stored balanced generation differs from reconstruction")
        return checked
    except Exception:
        raise BalancedRoleGenerationError("Invalid balanced role generation") from None


@dataclass(frozen=True)
class _BalancedRoleFramer:
    model: Model


def create_balanced_role_framer(model: Model) -> _BalancedRoleFramer:
    """Lazily borrow the required Model; its lifecycle stays with the caller."""
    if not isinstance(model, Model):
        raise BalancedRoleGenerationError("Invalid balanced role generation model") from None
    return _BalancedRoleFramer(model)


def run_balanced_role_framer(framer: _BalancedRoleFramer, source: Source) -> RoleAliasGenerationV2:
    """Make one bounded request without retries, repair, fallback or client ownership."""
    try:
        if type(framer) is not _BalancedRoleFramer or not isinstance(framer.model, Model):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
    except Exception:
        raise BalancedRoleGenerationError("Invalid balanced role generation input") from None
    known = None
    try:
        output, known = _run_role_request(
            model=framer.model,
            prompt=prompt,
            tools=tools,
            instructions=BALANCED_ROLE_INSTRUCTIONS,
            identity=PROVIDER_IDENTITY,
            total_limit=20000,
            output_limit=1800,
        )
        output_type = tools[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        result = RoleAliasGenerationV2(
            profile="shared-role-aliases-v2",
            status="unreviewed",
            frame=_build_output(source, output, output_type),
            prompt_sha256=sha256(prompt.encode("utf-8")).hexdigest(),
            instructions_sha256=sha256(BALANCED_ROLE_INSTRUCTIONS.encode("utf-8")).hexdigest(),
            usage=known,
        )
        return validate_balanced_role_generation(source, result)
    except RoleRequestError as error:
        raise BalancedRoleGenerationError(
            "Balanced role generation failed",
            known_usage=error.known_usage,
            may_have_started=error.may_have_started,
        ) from None
    except Exception:
        raise BalancedRoleGenerationError(
            "Balanced role generation failed", known_usage=known, may_have_started=True
        ) from None
