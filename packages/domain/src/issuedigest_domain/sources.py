"""Source identity and immutable raw/parsed versions, independent of storage."""

from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Literal, Self
from urllib.parse import urlsplit

from pydantic import (
    UUID4,
    AfterValidator,
    AnyHttpUrl,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("value must not be blank")
    return value


NonBlank = Annotated[str, AfterValidator(_nonblank)]


def _validate_source_url(value: object) -> object:
    if isinstance(value, str):
        parsed = urlsplit(value)
        if not parsed.netloc:
            raise ValueError("source URL must include a host")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("source URL must not include credentials")
    return value


SourceUrl = Annotated[AnyHttpUrl, BeforeValidator(_validate_source_url)]


class SourceDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    document_id: UUID4
    workspace_id: UUID4
    provider: NonBlank
    source_id: NonBlank
    source_kind: Literal[
        "bill",
        "legal_text",
        "government_document",
        "news",
        "poll",
        "statistics",
        "petition",
        "other",
    ]
    canonical_url: SourceUrl | None = None

    @field_validator("canonical_url")
    @classmethod
    def no_url_credentials(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and (value.username is not None or value.password is not None):
            raise ValueError("source URL must not include credentials")
        return value


Sha256 = Annotated[str, StringConstraints(strict=True, pattern=r"^[0-9a-f]{64}$")]


class DocumentVersion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version_id: UUID4
    document_id: UUID4
    raw_object_id: UUID4
    raw_sha256: Sha256
    media_type: str
    collected_at: AwareDatetime

    @field_validator("collected_at")
    @classmethod
    def utc_instant(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]


class PageSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    page_number: PositiveInt
    start: NonNegativeInt
    end: PositiveInt

    @model_validator(mode="after")
    def nonempty_span(self) -> Self:
        if self.end <= self.start:
            raise ValueError("page span must be nonempty")
        return self


class TableCell(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    cell_id: NonBlank
    text: str
    unit: str | None = None
    period: str | None = None
    question: str | None = None
    population: str | None = None
    methodology: str | None = None
    sample_size: PositiveInt | None = None
    weighting: str | None = None


class ParsedTable(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    table_id: NonBlank
    cells: tuple[TableCell, ...]

    @model_validator(mode="after")
    def unique_cells(self) -> Self:
        if len({cell.cell_id for cell in self.cells}) != len(self.cells):
            raise ValueError("cell_id must be unique within a table")
        return self


class ParsedRepresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    representation_id: UUID4
    document_version_id: UUID4
    parser_name: NonBlank
    parser_version: NonBlank
    normalization_profile: NonBlank
    text: str
    text_sha256: Sha256
    pages: tuple[PageSpan, ...]
    tables: tuple[ParsedTable, ...]

    @model_validator(mode="after")
    def validate_content(self) -> Self:
        try:
            digest = sha256(self.text.encode("utf-8")).hexdigest()
        except UnicodeEncodeError as error:
            raise ValueError("text must be valid UTF-8 Unicode") from error
        if self.text_sha256 != digest:
            raise ValueError("text_sha256 does not match UTF-8 text")
        previous_end = 0
        page_numbers: set[int] = set()
        for page in self.pages:
            if page.page_number in page_numbers:
                raise ValueError("page_number must be unique")
            if page.start < previous_end or page.end > len(self.text):
                raise ValueError("page spans must be ordered, non-overlapping and within text")
            page_numbers.add(page.page_number)
            previous_end = page.end
        if len({table.table_id for table in self.tables}) != len(self.tables):
            raise ValueError("table_id must be unique within a representation")
        return self
