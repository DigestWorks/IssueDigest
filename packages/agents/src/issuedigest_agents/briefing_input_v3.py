"""Lossless v3 input projection and an outcome-specific provider tool contract."""

from copy import deepcopy
from hashlib import sha256
from typing import Annotated, Any, Literal

from pydantic import Field

from .briefing_input_v2 import (
    INPUT_V2_DECODING_INSTRUCTIONS,
    INPUT_V2_FORMAT,
    decode_briefing_input_v2,
    encode_briefing_input_v2,
)
from .numeric_evidence import _StrictModel
from .question_briefing import Message, QuestionBriefingModuleProposal, QuestionBriefingProposal

INPUT_V3_FORMAT = "question-briefing-source-v3"
INPUT_V3_DECODING_INSTRUCTIONS = INPUT_V2_DECODING_INSTRUCTIONS.replace(
    "Input v2", "Input v3", 1
) + (
    " V3 omits duplicate evidence source/question hashes; source hash is on source, "
    "question hash is SHA256 of UTF8 question. Return result: answer has modules only, "
    "first summary; put supported limitations in claim text. Otherwise return "
    "insufficient_evidence with message only."
)


class AnswerBranch(_StrictModel):
    outcome: Literal["answer"]
    modules: Annotated[
        tuple[QuestionBriefingModuleProposal, ...], Field(min_length=1, max_length=3)
    ]


class InsufficientBranch(_StrictModel):
    outcome: Literal["insufficient_evidence"]
    message: Message


class BriefingToolResultV3(_StrictModel):
    result: AnswerBranch | InsufficientBranch

    def canonical(self) -> QuestionBriefingProposal:
        """Add only fields absent by branch design; retain every provider field."""
        if type(self.result) is AnswerBranch:
            return QuestionBriefingProposal(
                outcome=self.result.outcome, message=None, modules=self.result.modules
            )
        if type(self.result) is InsufficientBranch:
            return QuestionBriefingProposal(
                outcome=self.result.outcome, message=self.result.message, modules=()
            )
        raise ValueError("Invalid briefing tool branch")


def encode_briefing_input_v3(v1_payload: dict[str, Any]) -> dict[str, Any]:
    out = encode_briefing_input_v2(v1_payload)
    question_hash = sha256(out["question"].encode("utf-8")).hexdigest()
    for source in out["sources"]:
        evidence = source["evidence"]
        if (
            evidence.get("source_sha256") != source.get("source_sha256")
            or evidence.get("question_sha256") != question_hash
        ):
            raise ValueError("Mismatched duplicate briefing hashes")
        del evidence["source_sha256"], evidence["question_sha256"]
    out["input_format"] = INPUT_V3_FORMAT
    return out


def decode_briefing_input_v3(v3_payload: dict[str, Any]) -> dict[str, Any]:
    if type(v3_payload) is not dict or v3_payload.get("input_format") != INPUT_V3_FORMAT:
        raise ValueError("Invalid briefing input v3")
    out = deepcopy(v3_payload)
    question_hash = sha256(out["question"].encode("utf-8")).hexdigest()
    for source in out["sources"]:
        evidence = source["evidence"]
        if "source_sha256" in evidence or "question_sha256" in evidence:
            raise ValueError("Duplicate briefing hashes must be omitted")
        evidence["source_sha256"] = source["source_sha256"]
        evidence["question_sha256"] = question_hash
    out["input_format"] = INPUT_V2_FORMAT
    return decode_briefing_input_v2(out)
