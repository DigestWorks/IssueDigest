"""Supplied measurement conditions; comparison never certifies aggregation."""

import re
from datetime import date
from typing import Annotated, Literal, Self

from pydantic import (
    UUID4,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationInfo,
    field_validator,
    model_validator,
)

from .sources import NonBlank, PositiveInt


class DateInterval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    start_date: date
    end_date: date

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def precise_date(cls, value: object, info: ValidationInfo) -> date:
        if type(value) is date:
            return value
        if (
            info.mode == "json"
            and isinstance(value, str)
            and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value)
        ):
            return date.fromisoformat(value)
        raise ValueError("date must be a Python date or exact JSON YYYY-MM-DD")

    @model_validator(mode="after")
    def ordered_interval(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    key: NonBlank
    value: NonBlank


class ComparisonContext(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    metric: NonBlank
    unit: NonBlank | None = None
    population: NonBlank | None = None
    geography: NonBlank | None = None
    question: NonBlank | None = None
    methodology: NonBlank | None = None
    weighting: NonBlank | None = None
    denominator: NonBlank | None = None
    series_id: NonBlank | None = None
    period: DateInterval | None = None
    sample_size: PositiveInt | None = None
    dimensions: tuple[Dimension, ...] = ()

    @model_validator(mode="after")
    def unique_dimensions(self) -> Self:
        if len({dimension.key for dimension in self.dimensions}) != len(self.dimensions):
            raise ValueError("dimension key must be unique")
        return self


class Observation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    observation_id: UUID4
    workspace_id: UUID4
    subject_entity_id: UUID4 | None = None
    raw_value: NonBlank | None = None
    value: Annotated[str, StringConstraints(strict=True, max_length=128)] | None = None
    missing_reason: Literal["not_reported", "unreadable", "not_applicable", "withheld"] | None = (
        None
    )
    raw_period: NonBlank | None = None
    context: ComparisonContext
    citation_ids: Annotated[tuple[UUID4, ...], Field(min_length=1)]

    @field_validator("value")
    @classmethod
    def exact_decimal(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?", value):
            raise ValueError("value must be an exact ASCII decimal string")
        return value

    @model_validator(mode="after")
    def validate_measurement(self) -> Self:
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("citation_ids must be unique")
        if self.value is None:
            if self.missing_reason is None:
                raise ValueError("missing value requires missing_reason")
        elif self.raw_value is None or self.missing_reason is not None:
            raise ValueError("reported value requires raw_value and no missing_reason")
        return self


ComparisonField = Literal[
    "metric",
    "unit",
    "period",
    "population",
    "geography",
    "question",
    "methodology",
    "sample_size",
    "weighting",
    "denominator",
    "series_id",
    "dimensions",
    "value",
]
ComparisonStatus = Literal["same_context", "different_context", "insufficient_context"]
_COMPARISON_FIELDS: tuple[ComparisonField, ...] = (
    "metric",
    "unit",
    "period",
    "population",
    "geography",
    "question",
    "methodology",
    "sample_size",
    "weighting",
    "denominator",
    "series_id",
    "dimensions",
    "value",
)


class ComparisonReason(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    field: ComparisonField
    kind: Literal["different", "missing"]
    observation_ids: Annotated[tuple[UUID4, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def valid_reason(self) -> Self:
        if len(set(self.observation_ids)) != len(self.observation_ids):
            raise ValueError("reason observation_ids must be unique")
        if self.kind == "different":
            if self.field == "value" or len(self.observation_ids) < 2:
                raise ValueError("different requires at least two IDs and a context field")
        return self


def _comparison_status(reasons: tuple[ComparisonReason, ...]) -> ComparisonStatus:
    if any(reason.kind == "different" for reason in reasons):
        return "different_context"
    return "insufficient_context" if reasons else "same_context"


class ComparisonAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    policy_version: Literal["issuedigest-comparison-v1"] = "issuedigest-comparison-v1"
    observation_ids: Annotated[tuple[UUID4, ...], Field(min_length=2)]
    status: ComparisonStatus
    reasons: tuple[ComparisonReason, ...]
    aggregation_status: Literal["not_evaluated"] = "not_evaluated"

    @model_validator(mode="after")
    def consistent_assessment(self) -> Self:
        ids = set(self.observation_ids)
        if len(ids) != len(self.observation_ids):
            raise ValueError("assessment observation_ids must be unique")
        if len({(reason.field, reason.kind) for reason in self.reasons}) != len(self.reasons):
            raise ValueError("field/kind reasons must be unique")
        if any(not set(reason.observation_ids) <= ids for reason in self.reasons):
            raise ValueError("reason observation_ids must belong to assessment")
        if self.status != _comparison_status(self.reasons):
            raise ValueError("status is inconsistent with reasons")
        return self


def assess_comparison(observations: tuple[Observation, ...]) -> ComparisonAssessment:
    """Compare supplied conditions only, preserving order and uncertainty."""
    if not isinstance(observations, tuple) or len(observations) < 2:
        raise ValueError("comparison requires a tuple of at least two observations")
    if not all(isinstance(item, Observation) for item in observations):
        raise ValueError("comparison requires validated Observation models")
    ids = tuple(item.observation_id for item in observations)
    if len(set(ids)) != len(ids):
        raise ValueError("observation_ids must be unique")
    if len({item.workspace_id for item in observations}) != 1:
        raise ValueError("comparison observations must share a workspace")
    reasons: list[ComparisonReason] = []
    for field in _COMPARISON_FIELDS:
        values: list[object] = []
        for item in observations:
            if field == "value":
                values.append(item.value)
            elif field == "dimensions":
                values.append(
                    {dimension.key: dimension.value for dimension in item.context.dimensions}
                )
            else:
                values.append(getattr(item.context, field))
        missing = tuple(
            item.observation_id
            for item, value in zip(observations, values, strict=True)
            if value is None
        )
        known = [
            (item.observation_id, value)
            for item, value in zip(observations, values, strict=True)
            if value is not None
        ]
        if missing:
            reasons.append(ComparisonReason(field=field, kind="missing", observation_ids=missing))
        if field != "value" and known and any(value != known[0][1] for _, value in known[1:]):
            reasons.append(
                ComparisonReason(
                    field=field,
                    kind="different",
                    observation_ids=tuple(identity for identity, _ in known),
                )
            )
    reason_tuple = tuple(reasons)
    return ComparisonAssessment(
        observation_ids=ids, status=_comparison_status(reason_tuple), reasons=reason_tuple
    )
