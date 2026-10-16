"""Bounded public research journey contracts and verified source presentation."""

import re
import unicodedata
from datetime import date
from typing import Literal, Self
from uuid import UUID

from pydantic import UUID4, AwareDatetime, Field, field_validator, model_validator

from .canvas import CanvasBundle
from .contract_values import ContractModel
from .evidence import EvidenceBundle

RunStatus = Literal[
    "queued", "retrieving", "generating", "validating", "completed", "failed", "cancelled"
]


class ResearchRequest(ContractModel):
    request_id: UUID4
    question: str = Field(min_length=1, max_length=1500)
    parent_run_id: UUID4 | None = None

    @model_validator(mode="after")
    def valid_question(self) -> Self:
        if not self.question.strip():
            raise ValueError("Question must be nonblank")
        return self


class SourcePresentation(ContractModel):
    snapshot_id: UUID4
    workspace_id: UUID4
    title: str = Field(min_length=1, max_length=255)
    bill_number: str | None = None
    proposed_on: date | None = None
    profile: Literal[
        "legacy-bill-metadata-v1", "policy-html-v1", "source-kind-v1", "operator-verified-v1"
    ]

    @field_validator("title")
    @classmethod
    def display_title(cls, value: str) -> str:
        if (
            not value.strip()
            or value != value.strip()
            or any(unicodedata.category(char).startswith("C") for char in value)
        ):
            raise ValueError("Invalid display title")
        try:
            UUID(value)
        except ValueError:
            return value
        raise ValueError("Display title must not be an identifier")


class ResearchRunEvent(ContractModel):
    sequence: int = Field(ge=1)
    status: RunStatus
    created_at: AwareDatetime


class ResearchResult(ContractModel):
    canvas: CanvasBundle
    source_titles: dict[UUID, str]


class ResearchRun(ContractModel):
    run_id: UUID4
    workspace_id: UUID4
    request_id: UUID4
    question: str
    snapshot_ids: tuple[UUID4, ...] = Field(max_length=5)
    parent_run_id: UUID4 | None
    status: RunStatus
    error_code: (
        Literal[
            "insufficient_evidence",
            "model_unavailable",
            "generation_failed",
            "authority_changed",
            "cancelled",
        ]
        | None
    )
    created_at: AwareDatetime
    updated_at: AwareDatetime
    events: tuple[ResearchRunEvent, ...]
    result: ResearchResult | None
    model: Literal["gpt-5.4-mini"]
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_provenance(self) -> Self:
        if len(set(self.snapshot_ids)) != len(self.snapshot_ids):
            raise ValueError("Research provenance must be unique")
        if self.status == "completed":
            if (
                not self.snapshot_ids
                or self.result is None
                or not self.result.canvas.research.evidence
                or self.result.canvas.revision.run_id != self.run_id
                or self.result.canvas.revision.workspace_id != self.workspace_id
            ):
                raise ValueError("Completed research requires valid evidence and result")
        return self


class ResearchRunList(ContractModel):
    workspace_id: UUID4
    items: tuple[ResearchRun, ...]


_FALLBACK: dict[str, str] = {
    "bill": "법안 자료",
    "legal_text": "법령 자료",
    "government_document": "정부 자료",
    "news": "보도 자료",
    "poll": "여론조사 자료",
    "statistics": "통계 자료",
    "petition": "청원 자료",
    "other": "수집 자료",
}


def presentation_for(bundle: EvidenceBundle, snapshot_id: UUID) -> SourcePresentation:
    """Derive display metadata solely from a validated, profile-specific representation."""
    representation = bundle.representation
    title = _FALLBACK[bundle.document.source_kind]
    bill_number: str | None = None
    proposed_on: date | None = None
    profile: Literal[
        "legacy-bill-metadata-v1", "policy-html-v1", "source-kind-v1", "operator-verified-v1"
    ] = "source-kind-v1"
    if (
        representation.normalization_profile == "legacy-bill-metadata-v1"
        and bundle.document.source_kind == "bill"
    ):
        lines = representation.text.splitlines()
        if len(lines) >= 5:
            candidate = lines[0].strip()
            number = re.fullmatch(r"의안번호: ([0-9]{7})", lines[3])
            proposed = re.fullmatch(r"제안일: ([0-9]{4}-[0-9]{2}-[0-9]{2})", lines[4])
            if 1 <= len(candidate) <= 255 and number and proposed:
                try:
                    proposed_on = date.fromisoformat(proposed[1])
                except ValueError:
                    pass
                else:
                    title = candidate
                    bill_number = number[1]
                    profile = "legacy-bill-metadata-v1"
    return SourcePresentation(
        snapshot_id=snapshot_id,
        workspace_id=bundle.document.workspace_id,
        title=title,
        bill_number=bill_number,
        proposed_on=proposed_on,
        profile=profile,
    )
