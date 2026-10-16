"""Explicit operator metadata for one public bill; no inferred legislative history."""

import json
import re
from typing import Annotated, Literal, Self

from issuedigest_connectors import canonical_url
from pydantic import UUID4, AwareDatetime, Field, field_validator, model_validator

from .models import PreparationError, _PrivateModel, _reject_constant, _unique_object

MAX_ASSEMBLY_JOB_BYTES = 16_384


class AssemblyJob(_PrivateModel):
    schema_version: Literal[1]
    bill_id: Annotated[str, Field(min_length=1, max_length=80)] = Field(repr=False)
    title: Annotated[str, Field(min_length=1, max_length=300)] = Field(repr=False)
    bill_number: Annotated[str, Field(min_length=1, max_length=10)] = Field(repr=False)
    collected_at: AwareDatetime = Field(repr=False)
    operator_approved: bool = Field(repr=False)
    document_id: UUID4 = Field(repr=False)
    version_id: UUID4 = Field(repr=False)
    raw_object_id: UUID4 = Field(repr=False)
    representation_id: UUID4 = Field(repr=False)
    snapshot_id: UUID4 = Field(repr=False)
    citation_id: UUID4 = Field(repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid job version")
        return value

    @model_validator(mode="after")
    def approved(self) -> Self:
        canonical_url(self.bill_id)
        if (
            not self.operator_approved
            or not self.title.strip()
            or any(ord(c) < 32 for c in self.title)
            or re.fullmatch(r"[0-9]{1,10}", self.bill_number, flags=re.ASCII) is None
        ):
            raise ValueError("Invalid operator approval")
        return self


def parse_assembly_job(raw: str | bytes) -> AssemblyJob:
    try:
        if type(raw) is str:
            if len(raw) > MAX_ASSEMBLY_JOB_BYTES:
                raise ValueError("Job budget exceeded")
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or len(raw) > MAX_ASSEMBLY_JOB_BYTES:
            raise ValueError("Job budget exceeded")
        data = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        return AssemblyJob.model_validate_json(json.dumps(data, allow_nan=False), strict=True)
    except Exception:
        raise PreparationError("Unable to validate Assembly job") from None
