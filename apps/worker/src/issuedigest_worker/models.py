"""Bounded private preparation requests; no inferred source or license metadata."""

import json
from pathlib import Path
from typing import Annotated, Literal, Self

from issuedigest_domain import DocumentVersion, SourceDocument
from issuedigest_storage.provisioning import MAX_PLAN_BYTES
from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator


class PreparationError(ValueError):
    """Fixed safe operation failure without private input details."""


class _PrivateModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class LicenseAttestation(_PrivateModel):
    license_type: Literal["public_nuri_type_1"] = Field(repr=False)
    text_only: bool = Field(repr=False)
    operator_approved: bool = Field(repr=False)
    evidence_url: Annotated[str, Field(min_length=1, max_length=4096)] = Field(repr=False)

    @model_validator(mode="after")
    def approved(self) -> Self:
        if not self.text_only or not self.operator_approved:
            raise ValueError("Explicit text license approval required")
        return self


class TextCitationRequest(_PrivateModel):
    kind: Literal["text"]
    citation_id: UUID4 = Field(repr=False)
    quote: Annotated[str, Field(min_length=1, max_length=100_000)] = Field(repr=False)
    start: Annotated[int, Field(ge=0, le=1_000_000)] | None = Field(default=None, repr=False)

    @field_validator("quote")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Nonblank quote required")
        return value


class CellCitationRequest(_PrivateModel):
    kind: Literal["table_cell"]
    citation_id: UUID4 = Field(repr=False)
    table_id: Annotated[str, Field(min_length=1, max_length=96)] = Field(repr=False)
    cell_id: Annotated[str, Field(min_length=1, max_length=96)] = Field(repr=False)


CitationRequest = Annotated[TextCitationRequest | CellCitationRequest, Field(discriminator="kind")]


class HwpxSource(_PrivateModel):
    raw_path: Annotated[str, Field(min_length=1, max_length=4096)] = Field(repr=False)
    document: SourceDocument = Field(repr=False)
    version: DocumentVersion = Field(repr=False)
    representation_id: UUID4 = Field(repr=False)
    snapshot_id: UUID4 = Field(repr=False)
    license: LicenseAttestation = Field(repr=False)
    citations: Annotated[tuple[CitationRequest, ...], Field(min_length=1, max_length=100)] = Field(
        repr=False
    )

    @model_validator(mode="after")
    def relationships(self) -> Self:
        url = self.document.canonical_url
        if (
            not Path(self.raw_path).is_absolute()
            or any(p in {".", ".."} for p in self.raw_path.split("/"))
            or self.document.source_kind != "government_document"
            or url is None
            or url.scheme != "https"
            or str(url) != self.license.evidence_url
            or self.version.document_id != self.document.document_id
            or self.version.media_type != "application/hwp+zip"
        ):
            raise ValueError("Invalid HWPX source relationships")
        return self


class HwpxJob(_PrivateModel):
    schema_version: Literal[1]
    sources: Annotated[tuple[HwpxSource, ...], Field(min_length=1, max_length=10)] = Field(
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
        for ids in (
            [s.document.document_id for s in self.sources],
            [s.version.version_id for s in self.sources],
            [s.representation_id for s in self.sources],
            [s.snapshot_id for s in self.sources],
            [c.citation_id for s in self.sources for c in s.citations],
        ):
            if len(ids) != len(set(ids)):
                raise ValueError("Duplicate job identities")
        if sum(len(s.citations) for s in self.sources) > 200:
            raise ValueError("Too many citations")
        return self


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("Invalid JSON number")


def parse_job(raw: str | bytes) -> HwpxJob:
    """Parse bounded, unambiguous UTF-8 JSON with strict nested domain validation."""
    try:
        encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
        if type(encoded) is not bytes or len(encoded) > MAX_PLAN_BYTES:
            raise ValueError("Invalid job size")
        data = json.loads(
            encoded.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        return HwpxJob.model_validate_json(json.dumps(data, allow_nan=False), strict=True)
    except Exception:
        raise PreparationError("Unable to validate HWPX job") from None
