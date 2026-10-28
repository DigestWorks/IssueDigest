"""Immutable, question-only selection from the stored literal evidence index."""

from typing import Literal, Self

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator


class QuestionSourceChoice(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    snapshot_id: UUID4
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)


class QuestionSourcePlan(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")

    profile: Literal["question-source-plan-v1"] = "question-source-plan-v1"
    retrieval_profile: Literal["question-topics-ko-v2", "question-legal-aliases-ko-v3"] = (
        "question-topics-ko-v2"
    )
    plan_id: UUID4
    workspace_id: UUID4
    request_id: UUID4
    question: str = Field(min_length=1, max_length=1500)
    status: Literal["selected", "no_match"]
    reason: Literal["no_terms", "no_candidates"] | None
    sources: tuple[QuestionSourceChoice, ...] = Field(max_length=5)

    @model_validator(mode="after")
    def consistent_selection(self) -> Self:
        if not self.question.strip():
            raise ValueError("Question must be nonblank")
        ids = tuple(source.snapshot_id for source in self.sources)
        if len(ids) != len(set(ids)):
            raise ValueError("Sources must be unique")
        if self.status == "selected":
            if not self.sources or self.reason is not None:
                raise ValueError("Invalid selected plan")
        elif self.sources or self.reason is None:
            raise ValueError("Invalid no-match plan")
        return self
