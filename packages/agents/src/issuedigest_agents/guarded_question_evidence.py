"""Borrowed native transport for unreviewed source-specific evidence receipts.

Structural consistency does not establish meaning, access approval, or provider cancellation.
"""

from hashlib import sha256
from typing import Any, Literal, Self

from issuedigest_domain.sources import Sha256
from openai import AsyncOpenAI
from pydantic import model_validator

from .guarded_responses_stream import (
    GUARDED_RESPONSES_PROFILE,
    GuardedResponsesError,
    GuardedResponsesToolResult,
    run_guarded_responses_tool,
)
from .numeric_evidence import KnownUsage, Source, _StrictModel
from .numeric_selection_evaluation import _read
from .question_evidence_generation_v2 import QUESTION_EVIDENCE_V2_INSTRUCTIONS, _preflight
from .question_evidence_propositions import (
    QuestionEvidenceInput,
    QuestionEvidencePropositions,
    _guard_actual,
    _original,
    _source,
    build_question_evidence_propositions,
    validate_question_evidence_propositions,
)


class GuardedQuestionEvidenceError(GuardedResponsesError):
    """Sanitized failure preserving native observations without partial evidence."""


class GuardedQuestionEvidenceGeneration(_StrictModel):
    profile: Literal["guarded-question-evidence-v1"]
    transport_profile: Literal["guarded-responses-tool-v1"]
    input_format: Literal["question-evidence-source-v2"]
    status: Literal["unreviewed"]
    evidence: QuestionEvidencePropositions
    prompt_sha256: Sha256
    instructions_sha256: Sha256
    usage: KnownUsage

    @model_validator(mode="after")
    def bounded_usage(self) -> Self:
        _budget(self.usage)
        return self


def _budget(usage: KnownUsage) -> None:
    _guard_actual(usage, KnownUsage)
    KnownUsage.model_validate(usage.__dict__, strict=True)
    if (
        usage.requests != 1
        or usage.output_tokens > 4000
        or usage.input_tokens + usage.output_tokens > 20000
    ):
        raise ValueError("Invalid question evidence usage")


def _hash(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def validate_guarded_question_evidence(
    source: Source,
    question: str,
    result: GuardedQuestionEvidenceGeneration | dict[str, Any],
) -> GuardedQuestionEvidenceGeneration:
    """Rebuild fresh evidence and receipt from original actual types and current source."""
    try:
        _guard_actual(source, Source)
        _original(result, GuardedQuestionEvidenceGeneration)
        prompt, _ = _preflight(source, question)
        checked = _read(GuardedQuestionEvidenceGeneration, result)
        evidence = validate_question_evidence_propositions(source, question, checked.evidence)
        _budget(checked.usage)
        if (
            evidence != checked.evidence
            or checked.prompt_sha256 != _hash(prompt)
            or checked.instructions_sha256 != _hash(QUESTION_EVIDENCE_V2_INSTRUCTIONS)
        ):
            raise ValueError("Changed question evidence receipt")
        return checked
    except Exception:
        raise GuardedQuestionEvidenceError(reason="input") from None


async def run_guarded_question_evidence(
    *, client: AsyncOpenAI, model: str, source: Source, question: str
) -> GuardedQuestionEvidenceGeneration:
    """Make one native request; caller owns the client and all application acceptance."""
    try:
        _guard_actual(source, Source)
        prompt, tools = _preflight(source, question)
        source_hash, _ = _source(source)
    except Exception:
        raise GuardedQuestionEvidenceError(reason="input") from None
    terminal = False
    known = None
    try:
        result = await run_guarded_responses_tool(
            client=client,
            model=model,
            prompt=prompt,
            instructions=QUESTION_EVIDENCE_V2_INSTRUCTIONS,
            tool=tools[0],
        )
        if (
            type(result) is not GuardedResponsesToolResult
            or type(result.profile) is not str
            or result.profile != GUARDED_RESPONSES_PROFILE
            or result.usage_complete is not True
        ):
            raise ValueError("Invalid native completion")
        _guard_actual(result.usage, KnownUsage)
        KnownUsage.model_validate(result.usage.__dict__, strict=True)
        known, terminal = result.usage, True
        _budget(result.usage)
        if type(result.output) is not QuestionEvidenceInput or _source(source)[0] != source_hash:
            raise ValueError("Changed source or output")
        evidence = build_question_evidence_propositions(source, question, result.output)
        if evidence.source_sha256 != source_hash or _source(source)[0] != source_hash:
            raise ValueError("Changed source during evidence construction")
        receipt = GuardedQuestionEvidenceGeneration(
            profile="guarded-question-evidence-v1",
            transport_profile="guarded-responses-tool-v1",
            input_format="question-evidence-source-v2",
            status="unreviewed",
            evidence=evidence,
            prompt_sha256=_hash(prompt),
            instructions_sha256=_hash(QUESTION_EVIDENCE_V2_INSTRUCTIONS),
            usage=known,
        )
        checked = validate_guarded_question_evidence(source, question, receipt)
        if _source(source)[0] != source_hash:
            raise ValueError("Changed source during receipt validation")
        return checked
    except GuardedResponsesError as error:
        if not terminal:
            raise GuardedQuestionEvidenceError(
                reason=error.reason,
                known_usage=error.known_usage,
                may_have_started=error.may_have_started,
                usage_complete=error.usage_complete,
                stream_closed=error.stream_closed,
            ) from None
        raise GuardedQuestionEvidenceError(
            reason="output",
            known_usage=known,
            may_have_started=True,
            usage_complete=True,
            stream_closed=True,
        ) from None
    except Exception:
        raise GuardedQuestionEvidenceError(
            reason="output",
            known_usage=known,
            may_have_started=True,
            usage_complete=terminal,
            stream_closed=terminal,
        ) from None
