"""Strict private question submission and metadata-only history contracts."""

from typing import Annotated, Literal, Self

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator

QuestionErrorKind = Literal["unauthorized", "forbidden", "conflict", "budget", "unavailable"]
QuestionText = Annotated[str, Field(min_length=1, max_length=1500)]


class _Strict(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    @field_validator("question", mode="before", check_fields=False)
    @classmethod
    def text(cls, value: object) -> object:
        if isinstance(value, str):
            if not value.strip():
                raise ValueError("Blank text")
            value.encode("utf-8", errors="strict")
        return value


class QuestionSubmissionRequest(_Strict):
    request_id: UUID4
    question: QuestionText


class QuestionSubmissionResult(_Strict):
    request_id: UUID4
    kind: Literal["briefing", "no_match", "blocked"]
    job_id: UUID4 | None

    @model_validator(mode="after")
    def identity(self) -> Self:
        if (self.kind == "briefing") != (self.job_id is not None):
            raise ValueError("Invalid briefing identity")
        return self


class QuestionSubmissionProgress(_Strict):
    request_id: UUID4
    stage: Literal["analysing"]


class QuestionSubmissionErrorEvent(_Strict):
    request_id: UUID4
    kind: QuestionErrorKind


class BriefingJobSummary(_Strict):
    job_id: UUID4
    question: QuestionText
    status: Literal["pending", "running", "completed", "failed", "cancelled", "indeterminate"]


class BriefingJobList(_Strict):
    items: Annotated[tuple[BriefingJobSummary, ...], Field(max_length=50)]
