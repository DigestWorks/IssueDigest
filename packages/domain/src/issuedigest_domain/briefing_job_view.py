"""Private source-bound briefing views. Source statements are not independent verification."""

from datetime import date
from typing import Annotated, Literal, Self

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator


class _View(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    @field_validator("*")
    @classmethod
    def nonblank(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            raise ValueError("Blank text")
        return value


class BriefingQuoteView(_View):
    snapshot_id: UUID4
    citation_id: UUID4
    source_title: Annotated[str, Field(min_length=1, max_length=500)]
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(gt=0)]
    text: Annotated[str, Field(min_length=1, max_length=20000)]
    citation_quote: Annotated[str, Field(min_length=1, max_length=20000)]

    @model_validator(mode="after")
    def span(self) -> Self:
        if (
            self.end <= self.start
            or self.end > len(self.citation_quote)
            or self.citation_quote[self.start : self.end] != self.text
        ):
            raise ValueError("Invalid quote")
        return self


class BriefingClaimView(_View):
    text: Annotated[str, Field(min_length=1, max_length=400)]
    epistemic_status: Literal["source_statement", "uncertain"]
    event_date: date | None
    quotes: Annotated[tuple[BriefingQuoteView, ...], Field(min_length=1, max_length=960)]


class BriefingModuleView(_View):
    kind: Literal["summary", "comparison", "timeline"]
    title: Annotated[str, Field(min_length=1, max_length=100)]
    claims: Annotated[tuple[BriefingClaimView, ...], Field(min_length=1, max_length=4)]

    @model_validator(mode="after")
    def shape(self) -> Self:
        if self.kind == "comparison" and len(self.claims) < 2:
            raise ValueError("Invalid comparison")
        if any((c.event_date is not None) != (self.kind == "timeline") for c in self.claims):
            raise ValueError("Invalid date")
        return self


class BriefingResultView(_View):
    outcome: Literal["answer", "insufficient_evidence"]
    message: Annotated[str, Field(min_length=1, max_length=500)] | None
    modules: Annotated[tuple[BriefingModuleView, ...], Field(max_length=3)]
    additional_quotes: Annotated[tuple[BriefingQuoteView, ...], Field(max_length=960)]

    @model_validator(mode="after")
    def shape(self) -> Self:
        if self.outcome == "answer":
            if (
                self.message is not None
                or not self.modules
                or self.modules[0].kind != "summary"
                or any(m.kind == "summary" for m in self.modules[1:])
            ):
                raise ValueError("Invalid answer")
        elif self.message is None or self.modules:
            raise ValueError("Invalid insufficient evidence")
        return self


class BriefingJobView(_View):
    job_id: UUID4
    question: Annotated[str, Field(min_length=1, max_length=1500)]
    status: Literal["pending", "running", "completed", "failed", "cancelled", "indeterminate"]
    result: BriefingResultView | None

    @model_validator(mode="after")
    def shape(self) -> Self:
        if (self.status == "completed") != (self.result is not None):
            raise ValueError("Invalid completion")
        return self
