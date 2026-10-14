"""Bounded literal search units; no normalization, relevance or claim support."""

from datetime import datetime, timedelta
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from .citations import (
    PdfQuoteSelector,
    Selector,
    TableCellSelector,
    TextQuoteSelector,
    validate_selector,
)
from .evidence import EvidenceBundle
from .sources import NonBlank, SourceKind, SourceUrl

PROFILE: Literal["literal-ngrams-v1"] = "literal-ngrams-v1"
StrictCount = Annotated[int, Field(strict=True, ge=0)]
Term = Annotated[str, Field(strict=True, min_length=1, max_length=64)]
FilterText = Annotated[str, Field(strict=True, min_length=1, max_length=1024)]


def ascii_fold(text: str) -> str:
    return text.translate(str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"))


def literal_ngrams(text: str) -> tuple[str, ...]:
    folded = ascii_fold(text)
    return tuple(sorted({folded[i : i + n] for n in (1, 2, 3) for i in range(len(folded) - n + 1)}))


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceSearchQuery(_Model):
    terms: Annotated[tuple[Term, ...], Field(min_length=1, max_length=8)]
    limit: Annotated[int, Field(strict=True, ge=1, le=20)] = 20
    provider: FilterText | None = None
    source_id: FilterText | None = None
    source_kind: SourceKind | None = None
    collected_from: AwareDatetime | None = None
    collected_to: AwareDatetime | None = None

    @field_validator("terms")
    @classmethod
    def literal_terms(cls, terms: tuple[str, ...]) -> tuple[str, ...]:
        if any(not term.strip() or term != term.strip() for term in terms):
            raise ValueError("Literal terms must be nonblank with no outer whitespace")
        if len({ascii_fold(term) for term in terms}) != len(terms):
            raise ValueError("Literal terms must be distinct under ASCII comparison")
        try:
            for term in terms:
                term.encode("utf-8")
        except UnicodeError:
            raise ValueError("Literal terms must be valid Unicode") from None
        return terms

    @field_validator("provider", "source_id")
    @classmethod
    def nonblank_filter(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Search filters must be nonblank")
        return value

    @field_validator("collected_from", "collected_to", mode="before")
    @classmethod
    def utc_filter(cls, value: object, info: ValidationInfo) -> object:
        if (
            info.mode == "python"
            and value is not None
            and (not isinstance(value, datetime) or value.utcoffset() != timedelta(0))
        ):
            raise ValueError("Collection time filters must be UTC-aware datetimes")
        return value

    @field_validator("collected_from", "collected_to")
    @classmethod
    def utc_offset(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() != timedelta(0):
            raise ValueError("Collection time filters must be UTC-aware datetimes")
        return value

    @model_validator(mode="after")
    def ordered_interval(self) -> Self:
        if (
            self.collected_from is not None
            and self.collected_to is not None
            and self.collected_from >= self.collected_to
        ):
            raise ValueError("Collection time interval must be increasing")
        return self


def _bound_graph(root: object) -> None:
    """Bound even forged model graphs before any recursive serialization."""
    stack = [(root, 0)]
    nodes = characters = 0
    while stack:
        value, depth = stack.pop()
        nodes += 1
        if nodes > 500_000 or depth > 32:
            raise ValueError("Invalid search projection input")
        if isinstance(value, str):
            characters += len(value)
            if characters > 12_000_000:
                raise ValueError("Invalid search projection input")
        elif isinstance(value, BaseModel):
            if set(value.__dict__) - set(type(value).model_fields) or value.__pydantic_extra__:
                raise ValueError("Invalid search projection input")
            stack.extend((v, depth + 1) for v in value.__dict__.values())
            if value.__pydantic_extra__:
                stack.extend((v, depth + 1) for v in value.__pydantic_extra__.values())
        elif isinstance(value, dict):
            if len(value) > 500_000:
                raise ValueError("Invalid search projection input")
            stack.extend((v, depth + 1) for v in value.values())
        elif isinstance(value, (tuple, list)):
            if len(value) > 20_000:
                raise ValueError("Invalid search projection input")
            stack.extend((v, depth + 1) for v in value)


def validate_search_query(query: EvidenceSearchQuery) -> EvidenceSearchQuery:
    try:
        _bound_graph(query)
        # Preserve unknown model_copy fields instead of silently dropping them in model_dump.
        return EvidenceSearchQuery.model_validate(dict(query.__dict__))
    except (ValidationError, ValueError, TypeError, AttributeError, RecursionError):
        raise ValueError("Invalid evidence search query") from None


def literal_matches(query: EvidenceSearchQuery, text: str) -> bool:
    return all(ascii_fold(term) in ascii_fold(text) for term in query.terms)


class SearchUnit(_Model):
    ordinal: Annotated[int, Field(strict=True, ge=0, lt=6000)]
    selector: Selector
    text: Annotated[str, Field(strict=True, min_length=1, max_length=2048)]
    text_sha256: Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
    ngrams: Annotated[
        tuple[Annotated[str, Field(strict=True, min_length=1, max_length=3)], ...],
        Field(max_length=6144),
    ]


class SearchProjection(_Model):
    profile: Literal["literal-ngrams-v1"] = PROFILE
    units: Annotated[tuple[SearchUnit, ...], Field(max_length=6000)]
    skipped_empty_cells: Annotated[int, Field(strict=True, ge=0, le=20000)]
    skipped_large_cells: Annotated[int, Field(strict=True, ge=0, le=20000)]


def _is_pdf(bundle: EvidenceBundle) -> bool:
    return bundle.version.media_type == "application/pdf"


def _preflight(bundle: EvidenceBundle) -> None:
    rep = bundle.representation
    if not isinstance(rep.text, str) or len(rep.text) > 1_000_000 or len(rep.tables) > 1000:
        raise ValueError("Invalid search projection input")
    if _is_pdf(bundle) and rep.text and not rep.pages:
        raise ValueError("Invalid search projection input")
    cells = sum(len(t.cells) for t in rep.tables)
    if cells > 20_000:
        raise ValueError("Invalid search projection input")
    _bound_graph(bundle)
    spans = [(p.start, p.end) for p in rep.pages] if _is_pdf(bundle) else [(0, len(rep.text))]
    units = total = 0
    for start, end in spans:
        if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(rep.text):
            raise ValueError("Invalid search projection input")
        while start < end:
            stop = min(start + 512, end)
            units += 1
            total += stop - start
            if stop == end:
                break
            start += 449
    for table in rep.tables:
        for cell in table.cells:
            if not isinstance(cell.text, str):
                raise ValueError("Invalid search projection input")
            if 0 < len(cell.text) <= 2048:
                units += 1
                total += len(cell.text)
    if units > 6000 or total > 2_000_000:
        raise ValueError("Invalid search projection input")
    _bound_graph(bundle)


def build_search_projection(bundle: EvidenceBundle) -> SearchProjection:
    try:
        _preflight(bundle)
        validated = EvidenceBundle.model_validate_json(bundle.model_dump_json(warnings=False))
        rep = validated.representation
        units: list[SearchUnit] = []

        def add(selector: Selector) -> None:
            validate_selector(selector, rep)
            units.append(
                SearchUnit(
                    ordinal=len(units),
                    selector=selector,
                    text=selector.quote,
                    text_sha256=sha256(selector.quote.encode()).hexdigest(),
                    ngrams=literal_ngrams(selector.quote),
                )
            )

        spans = (
            [(p.start, p.end, p.page_number) for p in rep.pages]
            if _is_pdf(validated)
            else [(0, len(rep.text), None)]
        )
        for start, end, page in spans:
            while start < end:
                stop = min(start + 512, end)
                quote = rep.text[start:stop]
                selector = (
                    TextQuoteSelector(start=start, end=stop, quote=quote)
                    if page is None
                    else PdfQuoteSelector(start=start, end=stop, quote=quote, page_number=page)
                )
                add(selector)
                if stop == end:
                    break
                start += 449
        empty = large = 0
        for table in rep.tables:
            for cell in table.cells:
                if not cell.text:
                    empty += 1
                elif len(cell.text) > 2048:
                    large += 1
                else:
                    add(
                        TableCellSelector(
                            table_id=table.table_id, cell_id=cell.cell_id, quote=cell.text
                        )
                    )
        return SearchProjection(
            units=tuple(units), skipped_empty_cells=empty, skipped_large_cells=large
        )
    except (ValidationError, ValueError, TypeError, AttributeError, RecursionError):
        raise ValueError("Invalid search projection input") from None


class EvidenceSearchHit(_Model):
    workspace_id: UUID4
    snapshot_id: UUID4
    document_id: UUID4
    version_id: UUID4
    representation_id: UUID4
    provider: NonBlank
    source_id: NonBlank
    source_kind: SourceKind
    canonical_url: SourceUrl | None = None
    collected_at: AwareDatetime
    unit_ordinal: Annotated[int, Field(strict=True, ge=0, lt=6000)]
    profile: Literal["literal-ngrams-v1"] = PROFILE
    selector: Selector
    matched_terms: Annotated[tuple[Term, ...], Field(min_length=1, max_length=8)]
    anchor_status: Literal["matched"] = "matched"
    support_status: Literal["not_evaluated"] = "not_evaluated"


class SearchCoverage(_Model):
    total_snapshots: StrictCount
    indexed_snapshots: StrictCount
    missing_snapshots: StrictCount
    skipped_empty_cells: StrictCount
    skipped_large_cells: StrictCount

    @model_validator(mode="after")
    def counts_match(self) -> Self:
        if self.total_snapshots != self.indexed_snapshots + self.missing_snapshots:
            raise ValueError("Search coverage counts are inconsistent")
        return self


class EvidenceSearchResult(_Model):
    workspace_id: UUID4
    query: EvidenceSearchQuery
    hits: Annotated[tuple[EvidenceSearchHit, ...], Field(max_length=20)]
    coverage: SearchCoverage
    scanned_candidates: Annotated[int, Field(strict=True, ge=0, le=200)]
    truncated: Annotated[bool, Field(strict=True)]
