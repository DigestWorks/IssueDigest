"""Borrowed native transport for unreviewed source-specific evidence receipts.

Structural consistency does not establish meaning, access approval, or provider cancellation.
"""

from typing import Any, Literal, Self

from issuedigest_domain.sources import Sha256
from openai import AsyncOpenAI
from pydantic import BaseModel, model_validator
from pydantic_ai import ToolOutput

from .guarded_question_evidence import _budget, _hash
from .guarded_responses_stream import (
    GUARDED_RESPONSES_PROFILE,
    GuardedResponsesError,
    GuardedResponsesToolResult,
    run_guarded_responses_tool,
)
from .numeric_evidence import KnownUsage, Source, _StrictModel
from .numeric_selection_evaluation import _read
from .question_evidence_generation_v2 import (
    QUESTION_EVIDENCE_V2_INSTRUCTIONS,
)
from .question_evidence_generation_v2 import (
    _preflight as _base_preflight,
)
from .question_evidence_propositions import (
    QuestionEvidenceInput,
    QuestionEvidencePropositions,
    _guard_actual,
    _original,
    _source,
    build_question_evidence_propositions,
    validate_question_evidence_propositions,
)
from .role_bounded_runtime import _request_envelope

REFERENCE_RULES_SUFFIX = (
    " Field rules: fill subject_refs and predicate_refs with exact spans when supported."
    " If subject_refs or predicate_refs is empty, epistemic_status must be uncertain."
    " Empty quantity metric_refs or relative-time anchor_refs also requires uncertain."
    " Broad supporting_refs cannot replace these fields; never invent missing references."
)
GUARDED_QUESTION_V2_INSTRUCTIONS = QUESTION_EVIDENCE_V2_INSTRUCTIONS + REFERENCE_RULES_SUFFIX


class GuardedQuestionEvidenceV2Error(GuardedResponsesError):
    """Sanitized failure preserving native observations without partial evidence."""


class GuardedQuestionEvidenceGenerationV2(_StrictModel):
    profile: Literal["guarded-question-evidence-v2"]
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


def _preflight(source: Source, question: str) -> tuple[str, list[ToolOutput[BaseModel]]]:
    prompt, tools = _base_preflight(source, question)
    if _request_envelope(prompt, tools, GUARDED_QUESTION_V2_INSTRUCTIONS, 4000) > 20000:
        raise ValueError("Invalid guarded question v2 request envelope")
    return prompt, tools


def validate_guarded_question_evidence_v2(
    source: Source,
    question: str,
    result: GuardedQuestionEvidenceGenerationV2 | dict[str, Any],
) -> GuardedQuestionEvidenceGenerationV2:
    """Rebuild fresh evidence and receipt from original actual types and current source."""
    try:
        _guard_actual(source, Source)
        _original(result, GuardedQuestionEvidenceGenerationV2)
        prompt, _ = _preflight(source, question)
        checked = _read(GuardedQuestionEvidenceGenerationV2, result)
        evidence = validate_question_evidence_propositions(source, question, checked.evidence)
        _budget(checked.usage)
        if (
            evidence != checked.evidence
            or checked.prompt_sha256 != _hash(prompt)
            or checked.instructions_sha256 != _hash(GUARDED_QUESTION_V2_INSTRUCTIONS)
        ):
            raise ValueError("Changed question evidence receipt")
        return checked
    except Exception:
        raise GuardedQuestionEvidenceV2Error(reason="input") from None


async def run_guarded_question_evidence_v2(
    *, client: AsyncOpenAI, model: str, source: Source, question: str
) -> GuardedQuestionEvidenceGenerationV2:
    """Make one native request; caller owns the client and all application acceptance."""
    try:
        _guard_actual(source, Source)
        prompt, tools = _preflight(source, question)
        source_hash, _ = _source(source)
    except Exception:
        raise GuardedQuestionEvidenceV2Error(reason="input") from None
    terminal = False
    known = None
    try:
        result = await run_guarded_responses_tool(
            client=client,
            model=model,
            prompt=prompt,
            instructions=GUARDED_QUESTION_V2_INSTRUCTIONS,
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
        receipt = GuardedQuestionEvidenceGenerationV2(
            profile="guarded-question-evidence-v2",
            transport_profile="guarded-responses-tool-v1",
            input_format="question-evidence-source-v2",
            status="unreviewed",
            evidence=evidence,
            prompt_sha256=_hash(prompt),
            instructions_sha256=_hash(GUARDED_QUESTION_V2_INSTRUCTIONS),
            usage=known,
        )
        checked = validate_guarded_question_evidence_v2(source, question, receipt)
        if _source(source)[0] != source_hash:
            raise ValueError("Changed source during receipt validation")
        return checked
    except GuardedResponsesError as error:
        if not terminal:
            raise GuardedQuestionEvidenceV2Error(
                reason=error.reason,
                known_usage=error.known_usage,
                may_have_started=error.may_have_started,
                usage_complete=error.usage_complete,
                stream_closed=error.stream_closed,
            ) from None
        raise GuardedQuestionEvidenceV2Error(
            reason="output",
            known_usage=known,
            may_have_started=True,
            usage_complete=True,
            stream_closed=True,
        ) from None
    except Exception:
        raise GuardedQuestionEvidenceV2Error(
            reason="output",
            known_usage=known,
            may_have_started=True,
            usage_complete=terminal,
            stream_closed=terminal,
        ) from None
