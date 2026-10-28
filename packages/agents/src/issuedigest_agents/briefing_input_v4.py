"""Lossless v4 input and a provider schema with explicit temporal applicability."""

from copy import deepcopy
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import Field

from .briefing_input_v3 import decode_briefing_input_v3, encode_briefing_input_v3
from .numeric_evidence import Source, _StrictModel
from .question_briefing import Message, QuestionBriefingProposal, Text, Title
from .question_evidence_propositions import PropositionId

INPUT_V4_FORMAT = "question-briefing-source-v4"
INPUT_V4_DECODING_INSTRUCTIONS = (
    "V4 lossless input: join quote text_segments in order. Local reference_catalog rows "
    "[quote,first,past_last] select segments; {$ref:n} selects that row. "
    "proposition_columns names table row fields; epistemic_status indexes epistemic_statuses. "
    "Duplicate evidence source/question hashes are omitted. Preserve all conditions/statuses. "
    "V4 overrides legacy snapshot_id/modules output: use source ordinals and summary/details. "
    "Return MINIFIED JSON, no whitespace outside strings. Answer result: summary(title,claims), "
    "details(0..2 comparison/timeline blocks). Plain claims:text,references; "
    "timeline also event_date. "
    "Reference source is zero-based source ordinal; retain proposition_id. "
    "Supported limitations belong in claim text; otherwise insufficient_evidence message only."
)


class Ref(_StrictModel):
    source: Annotated[int, Field(ge=0, le=4)]
    proposition_id: PropositionId


Refs = Annotated[tuple[Ref, ...], Field(min_length=1, max_length=8)]


class Claim(_StrictModel):
    text: Text
    references: Refs


class DatedClaim(Claim):
    event_date: date


class Summary(_StrictModel):
    title: Title
    claims: Annotated[tuple[Claim, ...], Field(min_length=1, max_length=4)]


class Compare(_StrictModel):
    kind: Literal["comparison"]
    title: Title
    claims: Annotated[tuple[Claim, ...], Field(min_length=2, max_length=4)]


class Timeline(_StrictModel):
    kind: Literal["timeline"]
    title: Title
    claims: Annotated[tuple[DatedClaim, ...], Field(min_length=1, max_length=4)]


class Answer(_StrictModel):
    outcome: Literal["answer"]
    summary: Summary
    details: Annotated[tuple[Compare | Timeline, ...], Field(max_length=2)]


class Insufficient(_StrictModel):
    outcome: Literal["insufficient_evidence"]
    message: Message


class BriefingToolResultV4(_StrictModel):
    result: Answer | Insufficient

    def canonical(self, sources: tuple[Source, ...]) -> QuestionBriefingProposal:
        if type(self.result) is Insufficient:
            return QuestionBriefingProposal(
                outcome=self.result.outcome, message=self.result.message, modules=()
            )
        if type(self.result) is not Answer:
            raise ValueError("Invalid briefing branch")
        modules = []
        for block in (self.result.summary, *self.result.details):
            kind = "summary" if isinstance(block, Summary) else block.kind
            claims = []
            for claim in block.claims:
                refs = []
                for ref in claim.references:
                    if ref.source >= len(sources):
                        raise ValueError("Source ordinal unavailable")
                    refs.append(
                        {
                            "snapshot_id": sources[ref.source][0],
                            "proposition_id": ref.proposition_id,
                        }
                    )
                claims.append(
                    {
                        "text": claim.text,
                        "references": tuple(refs),
                        "event_date": claim.event_date if type(claim) is DatedClaim else None,
                    }
                )
            modules.append({"kind": kind, "title": block.title, "claims": tuple(claims)})
        return QuestionBriefingProposal.model_validate(
            {"outcome": "answer", "message": None, "modules": tuple(modules)}
        )


def encode_briefing_input_v4(v1_payload: dict[str, Any]) -> dict[str, Any]:
    out = encode_briefing_input_v3(v1_payload)
    if "proposition_columns" in out or "epistemic_statuses" in out:
        raise ValueError("Reserved briefing v4 metadata")
    columns: list[str] = next(
        (
            s["evidence"]["propositions"]["columns"]
            for s in out["sources"]
            if s["evidence"]["propositions"]["rows"]
        ),
        [],
    )
    statuses = []
    for source in out["sources"]:
        table = source["evidence"]["propositions"]
        if not table["rows"]:
            continue
        if table["columns"] != columns:
            raise ValueError("Inconsistent proposition columns")
        index = columns.index("epistemic_status")
        for row in table["rows"]:
            status = row[index]
            if type(status) is not str:
                raise ValueError("Invalid epistemic status")
            if status not in statuses:
                statuses.append(status)
            row[index] = statuses.index(status)
        del table["columns"]
    out["proposition_columns"] = columns
    out["epistemic_statuses"] = statuses
    out["input_format"] = INPUT_V4_FORMAT
    return out


def decode_briefing_input_v4(v4_payload: dict[str, Any]) -> dict[str, Any]:
    if type(v4_payload) is not dict or v4_payload.get("input_format") != INPUT_V4_FORMAT:
        raise ValueError("Invalid briefing input v4")
    out = deepcopy(v4_payload)
    columns = out.pop("proposition_columns")
    statuses = out.pop("epistemic_statuses")
    index = columns.index("epistemic_status") if columns else None
    for source in out["sources"]:
        table = source["evidence"]["propositions"]
        if "columns" in table:
            if table["rows"]:
                raise ValueError("Duplicate proposition columns")
            continue
        table["columns"] = deepcopy(columns)
        for row in table["rows"]:
            if index is None:
                raise ValueError("Missing proposition columns")
            status = row[index]
            if type(status) is not int or not 0 <= status < len(statuses):
                raise ValueError("Invalid epistemic status index")
            row[index] = statuses[status]
    out["input_format"] = "question-briefing-source-v3"
    decoded = decode_briefing_input_v3(out)
    if encode_briefing_input_v4(decoded) != v4_payload:
        raise ValueError("Noncanonical briefing v4 metadata")
    return decoded
