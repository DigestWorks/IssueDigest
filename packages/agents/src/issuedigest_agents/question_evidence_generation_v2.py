"""One borrowed-model request for unreviewed, question-specific source propositions."""

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Literal, Self

from issuedigest_domain.sources import Sha256
from pydantic import BaseModel, model_validator
from pydantic_ai import Agent, ToolOutput, UsageLimits, capture_run_messages
from pydantic_ai.messages import ModelMessage, ModelResponse, ThinkingPart, ToolCallPart
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from .numeric_evidence import KnownUsage, Source, _json, _known_usage, _StrictModel
from .numeric_selection import _captured_usage
from .numeric_selection_evaluation import _canonical_models, _read
from .question_evidence_generation import QUESTION_EVIDENCE_INSTRUCTIONS
from .question_evidence_propositions import (
    QuestionEvidenceInput,
    QuestionEvidencePropositions,
    _guard_actual,
    _original,
    _question,
    _source,
    build_question_evidence_propositions,
    validate_question_evidence_propositions,
)
from .research_v7 import _validate_result_usage
from .role_bounded_runtime import RoleRequestError, _request_envelope
from .scope_role_audit import _ObservedAuditModel
from .shared_measurement_context import _actual_models

PROVIDER_IDENTITY = "issuedigest_question_evidence_generation_v2"
QUESTION_EVIDENCE_V2_INSTRUCTIONS = QUESTION_EVIDENCE_INSTRUCTIONS.replace(
    "fill_question_evidence_v1", "fill_question_evidence_v2"
)


class QuestionEvidenceGenerationV2Error(RoleRequestError):
    """Sanitized failure retaining observed usage and dispatch uncertainty."""


class QuestionEvidenceGenerationV2(_StrictModel):
    profile: Literal["question-evidence-generation-v2"]
    input_format: Literal["question-evidence-source-v2"]
    status: Literal["unreviewed"]
    evidence: QuestionEvidencePropositions
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        if (
            self.usage.requests != 1
            or self.usage.output_tokens > 4000
            or self.usage.input_tokens + self.usage.output_tokens > 20000
        ):
            raise ValueError("Invalid question evidence v2 generation budget")
        return self


def _preflight(source: Source, question: str) -> tuple[str, list[ToolOutput[BaseModel]]]:
    _question(question)
    _, quotes = _source(source)
    prompt = _json(
        {
            "input_format": "question-evidence-source-v2",
            "question": question,
            "quotes": [
                {"citation_id": citation_id, "text": text} for citation_id, text in quotes.items()
            ],
        }
    )
    tools: list[ToolOutput[BaseModel]] = [
        ToolOutput(QuestionEvidenceInput, name="fill_question_evidence_v2", strict=True)
    ]
    if _request_envelope(prompt, tools, QUESTION_EVIDENCE_V2_INSTRUCTIONS, 4000) > 20000:
        raise ValueError("Invalid question evidence request envelope")
    return prompt, tools


def question_evidence_prompt_v2(source: Source, question: str) -> str:
    """Preflight the exact question, whole quotes, instructions and strict output schema."""
    try:
        return _preflight(source, question)[0]
    except Exception:
        raise QuestionEvidenceGenerationV2Error("Invalid question evidence v2 input") from None


def validate_question_evidence_generation_v2(
    source: Source,
    question: str,
    result: QuestionEvidenceGenerationV2 | dict[str, Any],
) -> QuestionEvidenceGenerationV2:
    """Reconstruct fresh structural evidence and receipt; never approve semantics or access."""
    try:
        # Guard both original inputs before any dump can erase unchecked types.
        _guard_actual(source, Source)
        _original(result, QuestionEvidenceGenerationV2)
        prompt, _ = _preflight(source, question)
        checked = _read(QuestionEvidenceGenerationV2, result)
        evidence = validate_question_evidence_propositions(source, question, checked.evidence)
        if (
            evidence != checked.evidence
            or checked.prompt_sha256 != sha256(prompt.encode("utf-8")).hexdigest()
            or checked.instructions_sha256
            != sha256(QUESTION_EVIDENCE_V2_INSTRUCTIONS.encode("utf-8")).hexdigest()
        ):
            raise ValueError("Stored question generation differs from reconstruction")
        return checked
    except Exception:
        raise QuestionEvidenceGenerationV2Error("Invalid question evidence v2 generation") from None


def _run_role_request(
    *, model: Model, prompt: str, tools: list[ToolOutput[BaseModel]]
) -> tuple[BaseModel, KnownUsage]:
    """Return actual dynamic output and known single-stage usage; never own a client."""
    # Keep the historical helper and its 30-second provider contract frozen.
    # This request timeout is a transport setting, not a total wall-clock SLA.
    total_limit, output_limit = 20000, 4000
    instructions, identity = QUESTION_EVIDENCE_V2_INSTRUCTIONS, PROVIDER_IDENTITY
    known = None
    captured: list[ModelMessage] = []
    observed = None
    try:
        if (
            not isinstance(model, Model)
            or type(total_limit) is not int
            or type(output_limit) is not int
            or output_limit <= 0
            or total_limit <= 0
            or len(tools) != 1
            or _request_envelope(prompt, tools, instructions, output_limit) > total_limit
        ):
            raise ValueError("Invalid stage request budget")
        output_type = tools[0].output
        if not isinstance(output_type, type) or not issubclass(output_type, BaseModel):
            raise ValueError("Expected dynamic tool model")
        observed = _ObservedAuditModel(model)
        agent: Agent[None, BaseModel] = Agent(
            observed, name=identity, instructions=instructions, output_type=tools, retries=0
        )
        with capture_run_messages() as captured:
            result = agent.run_sync(
                prompt,
                model_settings=OpenAIResponsesModelSettings(
                    openai_store=False, max_tokens=output_limit, timeout=60
                ),
                usage_limits=UsageLimits(
                    request_limit=1,
                    output_tokens_limit=output_limit,
                    total_tokens_limit=total_limit,
                ),
                retries=0,
            )
        known = _known_usage(result)
        _validate_result_usage(result, total=total_limit, output=output_limit)
        if (
            known is None
            or type(result.usage.requests) is not int
            or result.usage.requests != 1
            or known.requests != 1
            or known.output_tokens > output_limit
            or known.input_tokens + known.output_tokens > total_limit
        ):
            raise ValueError("Invalid single-stage raw usage")
        # Valid tool arguments do not imply completion. Responses API preserves
        # raw "incomplete" in provider_details even when the SDK state is complete.
        if any(
            isinstance(response, ModelResponse)
            and (
                response.state != "complete"
                or response.finish_reason == "length"
                or (response.provider_details or {}).get("finish_reason")
                in ("length", "max_output_tokens", "incomplete")
            )
            for response in observed.responses
        ):
            raise ValueError("Incomplete role response")
        if type(result.output) is not output_type:
            raise ValueError("Expected actual dynamic output")
        _canonical_models(result.output, output_type)
        _actual_models(result.output, output_type)
        return result.output, known
    except Exception:
        if known is None:
            known = _captured_usage(observed.responses if observed is not None else captured)
        raise RoleRequestError(
            "Role request failed",
            known_usage=known,
            may_have_started=observed.request_started if observed else False,
        ) from None


@dataclass(frozen=True)
class _QuestionEvidenceGeneratorV2:
    model: Model


def create_question_evidence_generator_v2(model: Model) -> _QuestionEvidenceGeneratorV2:
    """Lazily borrow a required Model; the caller owns its transport and lifecycle."""
    if not isinstance(model, Model):
        raise QuestionEvidenceGenerationV2Error("Invalid question evidence v2 model") from None
    return _QuestionEvidenceGeneratorV2(model)


def run_question_evidence_generator_v2(
    generator: _QuestionEvidenceGeneratorV2, source: Source, question: str
) -> QuestionEvidenceGenerationV2:
    """Run one bounded request without retries, repair, fallback or client ownership."""
    try:
        if type(generator) is not _QuestionEvidenceGeneratorV2 or not isinstance(
            generator.model, Model
        ):
            raise ValueError("Invalid borrowed generator")
        prompt, tools = _preflight(source, question)
        source_sha256, _ = _source(source)
    except Exception:
        raise QuestionEvidenceGenerationV2Error("Invalid question evidence v2 input") from None
    known = None
    try:
        observed = _ObservedAuditModel(generator.model)
        output, known = _run_role_request(
            model=observed,
            prompt=prompt,
            tools=tools,
        )
        if len(observed.responses) != 1 or not isinstance(observed.responses[0], ModelResponse):
            raise ValueError("Expected one original model response")
        parts = observed.responses[0].parts
        calls = [part for part in parts if isinstance(part, ToolCallPart)]
        if (
            len(calls) != 1
            or calls[0].tool_name != "fill_question_evidence_v2"
            or any(not isinstance(part, (ToolCallPart, ThinkingPart)) for part in parts)
            or type(output) is not QuestionEvidenceInput
        ):
            raise ValueError("Expected only the single question evidence output tool")
        evidence = build_question_evidence_propositions(source, question, output)
        if evidence.source_sha256 != source_sha256:
            raise ValueError("Source changed during question evidence request")
        result = QuestionEvidenceGenerationV2(
            profile="question-evidence-generation-v2",
            input_format="question-evidence-source-v2",
            status="unreviewed",
            evidence=evidence,
            prompt_sha256=sha256(prompt.encode("utf-8")).hexdigest(),
            instructions_sha256=sha256(
                QUESTION_EVIDENCE_V2_INSTRUCTIONS.encode("utf-8")
            ).hexdigest(),
            usage=known,
        )
        return validate_question_evidence_generation_v2(source, question, result)
    except RoleRequestError as error:
        raise QuestionEvidenceGenerationV2Error(
            "Question evidence v2 generation failed",
            known_usage=known if known is not None else error.known_usage,
            may_have_started=True if known is not None else error.may_have_started,
        ) from None
    except Exception:
        raise QuestionEvidenceGenerationV2Error(
            "Question evidence v2 generation failed", known_usage=known, may_have_started=True
        ) from None
