"""Bounded operator approval after capture inspection; no inferred identities or rights."""

import json
from typing import Annotated, Literal, Self

from issuedigest_connectors import policy_url
from pydantic import UUID4, AwareDatetime, Field, field_validator, model_validator

from .models import (
    LicenseAttestation,
    PreparationError,
    _PrivateModel,
    _reject_constant,
    _unique_object,
)

MAX_POLICY_JOB_BYTES = 131_072
_Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)]


class PolicyQuote(_PrivateModel):
    citation_id: UUID4 = Field(repr=False)
    quote: Annotated[str, Field(min_length=1, max_length=2000)] = Field(repr=False)
    start: Annotated[int, Field(ge=0, le=100_000)] | None = Field(default=None, repr=False)

    @field_validator("quote")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nonblank quote required")
        return value


class PolicySource(_PrivateModel):
    news_id: Annotated[str, Field(min_length=9, max_length=9)] = Field(repr=False)
    article_sha256: _Hash = Field(repr=False)
    text_sha256: _Hash = Field(repr=False)
    photos_and_external_works_excluded: bool = Field(repr=False)
    license: LicenseAttestation = Field(repr=False)
    document_id: UUID4 = Field(repr=False)
    version_id: UUID4 = Field(repr=False)
    raw_object_id: UUID4 = Field(repr=False)
    representation_id: UUID4 = Field(repr=False)
    snapshot_id: UUID4 = Field(repr=False)
    citations: Annotated[tuple[PolicyQuote, ...], Field(min_length=1, max_length=10)] = Field(
        repr=False
    )

    @model_validator(mode="after")
    def approved(self) -> Self:
        if (
            self.license.evidence_url != policy_url(self.news_id)
            or not self.photos_and_external_works_excluded
        ):
            raise ValueError("Explicit source and exclusion approval required")
        return self


class PolicyJob(_PrivateModel):
    schema_version: Literal[1]
    capture_sha256: _Hash = Field(repr=False)
    collected_at: AwareDatetime = Field(repr=False)
    sources: Annotated[tuple[PolicySource, ...], Field(min_length=1, max_length=2)] = Field(
        repr=False
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid job version")
        return value

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        for values in (
            [s.news_id for s in self.sources],
            [s.document_id for s in self.sources],
            [s.version_id for s in self.sources],
            [s.raw_object_id for s in self.sources],
            [s.representation_id for s in self.sources],
            [s.snapshot_id for s in self.sources],
            [c.citation_id for s in self.sources for c in s.citations],
        ):
            if len(values) != len(set(values)):
                raise ValueError("Duplicate job identities")
        return self


def parse_policy_job(raw: str | bytes) -> PolicyJob:
    try:
        if type(raw) is str:
            if len(raw) > MAX_POLICY_JOB_BYTES:
                raise ValueError("Job budget exceeded")
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or len(raw) > MAX_POLICY_JOB_BYTES:
            raise ValueError("Job budget exceeded")
        data = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        return PolicyJob.model_validate_json(json.dumps(data, allow_nan=False), strict=True)
    except Exception:
        raise PreparationError("Unable to validate policy job") from None
