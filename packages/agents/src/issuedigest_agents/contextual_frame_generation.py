"""One bounded borrowed-model request for an exact, unreviewed numeric role frame."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self, cast

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, Field, create_model, model_validator
from pydantic_ai import Agent, ToolOutput, UsageLimits, capture_run_messages
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from .contextual_anchor import ContextualAnchor
from .contextual_frame import (
    ContextualFrameFactInput,
    ContextualFrameInput,
    ContextualFrameRelationInput,
    ContextualNumericFrame,
    build_contextual_frame,
    validate_contextual_frame,
)
from .numeric_candidates import NumericCandidateIndex, build_numeric_candidates
from .numeric_evidence import (
    MAX_OUTPUT_TOKENS,
    MAX_RUN_TOKENS,
    KnownUsage,
    NumericEvidenceError,
    Source,
    _bounded_usage,
    _json,
    _known_usage,
    _StrictModel,
)
from .numeric_frame import _ANCHORS
from .numeric_frame_generation import NUMERIC_FRAME_INSTRUCTIONS
from .numeric_selection import _captured_usage, _prompt
from .numeric_selection_evaluation import _canonical_models, _read
from .research import PROVIDER_FRAMING_ALLOWANCE
from .research_v5 import _provider_schema_bytes_v5
from .research_v7 import _validate_result_usage


class ContextualFrameGenerationError(NumericEvidenceError):
    """Sanitized failure; nullable known_usage never implies that a request was free."""


class ContextualFrameGeneration(_StrictModel):
    """Current-input consistency receipts, never signatures or semantic review."""

    profile: Literal["contextual-frame-generation-v1"] = "contextual-frame-generation-v1"
    status: Literal["unreviewed"] = "unreviewed"
    frame: ContextualNumericFrame
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        _bounded_usage(self.usage)
        return self


# Reuse the frozen role/relation semantics verbatim, replacing only anchor syntax/rules.
CONTEXTUAL_FRAME_INSTRUCTIONS = NUMERIC_FRAME_INSTRUCTIONS.replace(
    "fill_numeric_frame_v1", "fill_contextual_frame_v1"
).replace(
    "Each role anchor is {sentence_id,text} or null. Use exact "
    "nonblank text of 1..1000 code points occurring exactly once, counting overlapping "
    "matches, within one current sentence.",
    "Each role anchor is {sentence_id,text,context_text} or null. text and nonnull "
    "context_text are exact nonblank strings of 1..1000 code points. context_text is "
    "required nullable: null only when text occurs exactly once within its sentence. "
    "Repeated text requires an explicit context_text occurring exactly once in that "
    "sentence, and text occurring exactly once inside that context, counting overlapping "
    "matches. Return the necessary short role or relation phrase in text even when "
    "context_text is broader. Never infer a location, generate or repair context, or "
    "select the first occurrence.",
)
PROVIDER_IDENTITY = "issuedigest_contextual_frame_v1"


def _frame_tools(index: NumericCandidateIndex) -> list[ToolOutput[BaseModel]]:
    if not index.candidates or not index.sentences:
        raise ValueError("No numeric candidates")
    candidate_id: Any = Literal[tuple(c.candidate_id for c in index.candidates)]
    sentence_id: Any = Literal[tuple(s.sentence_id for s in index.sentences)]
    anchor = create_model(
        "ContextualFrameAnchorV1", __base__=ContextualAnchor, sentence_id=(sentence_id, ...)
    )
    # Four combinations express nonnull known evidence directly in provider JSON schema,
    # while inheriting the canonical runtime validator rather than duplicating it.
    variants: list[type[BaseModel]] = []
    for known_status in (True, False):
        for known_tense in (True, False):
            fields: dict[str, Any] = {
                "candidate_id": (candidate_id, ...),
                **{role: (anchor | None, ...) for role in _ANCHORS},
                "value_status": (
                    Literal["observed", "planned", "forecast"]
                    if known_status
                    else Literal["unknown"],
                    ...,
                ),
                "reporting_tense": (
                    Literal["past", "present", "future"] if known_tense else Literal["unknown"],
                    ...,
                ),
            }
            if known_status:
                fields["status_text"] = (anchor, ...)
            if known_tense:
                fields["reporting_tense_text"] = (anchor, ...)
            variants.append(
                create_model(
                    f"ContextualFrameFact{int(known_status)}{int(known_tense)}V1",
                    __base__=ContextualFrameFactInput,
                    **fields,
                )
            )
    fact_type = variants[0] | variants[1] | variants[2] | variants[3]
    relation = create_model(
        "ContextualFrameRelationV1",
        __base__=ContextualFrameRelationInput,
        from_id=(candidate_id, ...),
        to_id=(candidate_id, ...),
        statement_sentence_ids=(tuple[sentence_id, ...], Field(min_length=1, max_length=20)),
        cue=(anchor, ...),
    )
    output = create_model(
        "ContextualFrameOutputV1",
        __base__=ContextualFrameInput,
        facts=(tuple[fact_type, ...], Field(max_length=12)),  # type: ignore[valid-type]
        relations=(tuple[relation, ...], Field(max_length=16)),  # type: ignore[valid-type]
    )
    return [ToolOutput(output, name="fill_contextual_frame_v1", strict=True)]


def _preflight(source: Source) -> tuple[str, list[ToolOutput[BaseModel]]]:
    # Check actual nested types, including excluded subclass fields, before any dump.
    _canonical_models(source, Source)
    index = build_numeric_candidates(source)
    tools = _frame_tools(index)
    packet = json.loads(_prompt(source, index))
    packet["profile"] = "contextual-frame-generation-v1"
    prompt = _json(packet)
    envelope = (
        len(prompt.encode("utf-8"))
        + len(CONTEXTUAL_FRAME_INSTRUCTIONS.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + MAX_OUTPUT_TOKENS
    )
    if envelope > MAX_RUN_TOKENS:
        raise ValueError("Invalid frame request envelope")
    return prompt, tools


def contextual_frame_prompt(source: Source) -> str:
    """Preflight the whole source and actual provider schema, without truncation or I/O."""
    try:
        return _preflight(source)[0]
    except Exception:
        raise ContextualFrameGenerationError("Invalid contextual frame generation input") from None


def validate_contextual_frame_generation(
    source: Source, result: ContextualFrameGeneration | dict[str, Any]
) -> ContextualFrameGeneration:
    """Recheck current instructions, full preflight and exact source frame without I/O."""
    try:
        prompt, _ = _preflight(source)
        checked = _read(ContextualFrameGeneration, result)
        validate_contextual_frame(source, checked.frame)
        if (
            checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(CONTEXTUAL_FRAME_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stale generation receipts")
        return checked
    except Exception:
        raise ContextualFrameGenerationError("Invalid contextual frame generation") from None


@dataclass(frozen=True)
class _ContextualFramer:
    model: Model


def create_contextual_framer(model: Model) -> _ContextualFramer:
    """Lazily borrow a required Model; allocation and lifecycle belong to the caller."""
    if not isinstance(model, Model):
        raise ContextualFrameGenerationError("Invalid contextual frame generation model") from None
    return _ContextualFramer(model)


def run_contextual_framer(framer: _ContextualFramer, source: Source) -> ContextualFrameGeneration:
    """Make one bounded request with no retry or repair and retain observed raw usage."""
    try:
        if type(framer) is not _ContextualFramer or not isinstance(framer.model, Model):
            raise ValueError("Invalid borrowed framer")
        prompt, tools = _preflight(source)
        instructions = CONTEXTUAL_FRAME_INSTRUCTIONS
    except Exception:
        raise ContextualFrameGenerationError("Invalid contextual frame generation input") from None
    return _run_contextual_request(
        model=framer.model,
        source=source,
        prompt=prompt,
        tools=tools,
        instructions=instructions,
        identity=PROVIDER_IDENTITY,
        result_model=ContextualFrameGeneration,
        validator=validate_contextual_frame_generation,
        error_type=ContextualFrameGenerationError,
        failure_message="Contextual frame generation failed",
    )


def _build_contextual_output(
    source: Source, output: BaseModel, output_type: type[BaseModel]
) -> ContextualNumericFrame:
    output = cast(ContextualFrameInput, output)
    # The shared reader intentionally accepts dictionaries. Here every model node
    # must already exist before its exact dynamic type is checked by that reader.
    for fact in output.facts:
        if not isinstance(fact, ContextualFrameFactInput):
            raise ValueError("Expected actual dynamic fact")
        for role in _ANCHORS:
            anchor = getattr(fact, role)
            if anchor is not None and not isinstance(anchor, ContextualAnchor):
                raise ValueError("Expected actual dynamic role anchor")
    for relation in output.relations:
        if not isinstance(relation, ContextualFrameRelationInput) or not isinstance(
            relation.cue, ContextualAnchor
        ):
            raise ValueError("Expected actual dynamic relation and cue")
    # The exact dynamic types must pass before their narrowing conversion drops them.
    dynamic = _read(output_type, output)
    canonical = ContextualFrameInput.model_validate_json(dynamic.model_dump_json(), strict=True)
    return build_contextual_frame(source, canonical)


def _run_contextual_request[Generation: BaseModel](
    *,
    model: Model,
    source: Source,
    prompt: str,
    tools: list[ToolOutput[BaseModel]],
    instructions: str,
    identity: str,
    result_model: type[Generation],
    validator: Callable[[Source, Generation | dict[str, Any]], Generation],
    error_type: type[ContextualFrameGenerationError],
    failure_message: str,
    frame_builder: Callable[[Source, BaseModel, type[BaseModel]], BaseModel] | None = None,
) -> Generation:
    """Trusted internal request runtime; each caller owns preflight and its result policy."""
    known_usage = None
    captured: list[ModelMessage] = []
    try:
        agent: Agent[None, BaseModel] = Agent(
            model,
            name=identity,
            instructions=instructions,
            output_type=tools,
            retries=0,
        )
        with capture_run_messages() as captured:
            result = agent.run_sync(
                prompt,
                model_settings=OpenAIResponsesModelSettings(
                    openai_store=False, max_tokens=MAX_OUTPUT_TOKENS, timeout=30
                ),
                usage_limits=UsageLimits(
                    request_limit=1,
                    output_tokens_limit=MAX_OUTPUT_TOKENS,
                    total_tokens_limit=MAX_RUN_TOKENS,
                ),
                retries=0,
            )
        known_usage = _known_usage(result)
        _validate_result_usage(result, total=MAX_RUN_TOKENS, output=MAX_OUTPUT_TOKENS)
        if (
            type(result.usage.requests) is not int
            or result.usage.requests != 1
            or known_usage is None
        ):
            raise ValueError("Invalid request count or raw usage")
        _bounded_usage(known_usage)
        output_type = tools[0].output
        assert isinstance(output_type, type) and issubclass(output_type, BaseModel)
        if type(result.output) is not output_type:
            raise ValueError("Expected actual dynamic frame output")
        _canonical_models(result.output, output_type)
        frame = (frame_builder or _build_contextual_output)(source, result.output, output_type)
        generation = result_model(
            frame=frame,
            prompt_sha256=sha256(prompt.encode("utf-8")).hexdigest(),
            instructions_sha256=sha256(instructions.encode("utf-8")).hexdigest(),
            usage=known_usage,
        )
        return validator(source, generation)
    except Exception:
        if known_usage is None:
            known_usage = _captured_usage(captured)
        raise error_type(failure_message, known_usage=known_usage) from None
