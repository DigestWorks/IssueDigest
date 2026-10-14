"""Version-bound citation locators and exact anchor validation."""

from typing import Annotated, Literal, Self

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .sources import NonBlank, NonNegativeInt, ParsedRepresentation, PositiveInt


class _QuoteFields(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: NonNegativeInt
    end: PositiveInt
    quote: Annotated[str, Field(min_length=1)]
    prefix: str | None = None
    suffix: str | None = None

    @model_validator(mode="after")
    def nonempty_range(self) -> Self:
        if self.end <= self.start:
            raise ValueError("quote range must be nonempty")
        return self


class TextQuoteSelector(_QuoteFields):
    kind: Literal["text"] = "text"


Coordinate = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=0, le=1)]


class NormalizedBox(BaseModel):
    """Coordinates after crop/rotation, measured from displayed page top-left."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x0: Coordinate
    y0: Coordinate
    x1: Coordinate
    y1: Coordinate

    @model_validator(mode="after")
    def positive_area(self) -> Self:
        if self.x0 >= self.x1 or self.y0 >= self.y1:
            raise ValueError("normalized box must have positive width and height")
        return self


class PdfQuoteSelector(_QuoteFields):
    kind: Literal["pdf"] = "pdf"
    page_number: PositiveInt
    regions: tuple[NormalizedBox, ...] = ()


class TableCellSelector(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["table_cell"] = "table_cell"
    table_id: NonBlank
    cell_id: NonBlank
    quote: str


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: UUID4
    document_version_id: UUID4
    representation_id: UUID4
    selector: Annotated[
        TextQuoteSelector | PdfQuoteSelector | TableCellSelector, Field(discriminator="kind")
    ]


class CitationAnchorValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    citation_id: UUID4
    anchor_status: Literal["matched"] = "matched"
    support_status: Literal["not_evaluated"] = "not_evaluated"


def validate_citation(
    citation: Citation, representation: ParsedRepresentation
) -> CitationAnchorValidation:
    """Validate an exact anchor on validated models; support remains unevaluated."""
    if citation.document_version_id != representation.document_version_id:
        raise ValueError("citation document_version_id does not match representation")
    if citation.representation_id != representation.representation_id:
        raise ValueError("citation representation_id does not match representation")
    validate_selector(citation.selector, representation)
    return CitationAnchorValidation(citation_id=citation.citation_id)


Selector = Annotated[
    TextQuoteSelector | PdfQuoteSelector | TableCellSelector, Field(discriminator="kind")
]


def validate_selector(selector: Selector, representation: ParsedRepresentation) -> None:
    """Check an exact version-bound text, page or complete cell anchor."""
    if isinstance(selector, TableCellSelector):
        table = next((t for t in representation.tables if t.table_id == selector.table_id), None)
        if table is None:
            raise ValueError("citation table_id not found")
        cell = next((c for c in table.cells if c.cell_id == selector.cell_id), None)
        if cell is None:
            raise ValueError("citation cell_id not found in specified table")
        if cell.text != selector.quote:
            raise ValueError("citation quote does not match complete cell text")
    else:
        text = representation.text
        if selector.end > len(text) or text[selector.start : selector.end] != selector.quote:
            raise ValueError("citation range or quote does not match text")
        if selector.prefix is not None:
            context_start = selector.start - len(selector.prefix)
            if context_start < 0 or text[context_start : selector.start] != selector.prefix:
                raise ValueError("citation prefix does not match adjacent text")
        if selector.suffix is not None:
            context_end = selector.end + len(selector.suffix)
            if context_end > len(text) or text[selector.end : context_end] != selector.suffix:
                raise ValueError("citation suffix does not match adjacent text")
        if isinstance(selector, PdfQuoteSelector):
            page = next(
                (p for p in representation.pages if p.page_number == selector.page_number), None
            )
            if page is None or selector.start < page.start or selector.end > page.end:
                raise ValueError("PDF citation range is outside specified page span")
