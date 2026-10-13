"""Bounded exact PDF quote positions on caller-owned validated representations."""

from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

from issuedigest_domain.citations import PdfQuoteSelector
from issuedigest_domain.sources import PageSpan, ParsedRepresentation

from .errors import AuditError


@dataclass(frozen=True)
class PdfQuoteSearchLimits:
    """Bound scanning, examined raw occurrences, returned selectors and previews."""

    max_text_characters: int = 1_000_000
    max_occurrences: int = 10_000
    max_candidates: int = 100
    context_characters: int = 80

    def __post_init__(self) -> None:
        values = (
            self.max_text_characters,
            self.max_occurrences,
            self.max_candidates,
            self.context_characters,
        )
        if (
            any(type(value) is not int for value in values)
            or self.max_text_characters <= 0
            or self.max_occurrences <= 0
            or not 1 <= self.max_candidates <= 1000
            or not 0 <= self.context_characters <= 200
        ):
            raise AuditError("invalid_quote_search_limits")


_DEFAULT_LIMITS = PdfQuoteSearchLimits()


@dataclass(frozen=True)
class PdfQuoteSearchResult:
    """Unranked positions only; no source identity or factual support evaluation."""

    representation_id: UUID
    document_version_id: UUID
    text_sha256: str
    candidates: tuple[PdfQuoteSelector, ...]
    occurrence_count: int
    candidate_count: int
    cross_page_match_count: int
    has_more: bool


def _scope(
    representation: ParsedRepresentation,
    quote: str,
    page_number: int | None,
    limits: PdfQuoteSearchLimits,
) -> tuple[int, int, tuple[PageSpan, ...]]:
    # Avoid allocating copies of a potentially long supplied quote for validation.
    if (
        not isinstance(quote, str)
        or not quote
        or quote.isspace()
        or any(0xD800 <= ord(character) <= 0xDFFF for character in quote)
    ):
        raise AuditError("invalid_quote")
    pages = representation.pages
    start, end = 0, len(representation.text)
    if page_number is not None:
        if type(page_number) is not int or page_number <= 0:
            raise AuditError("invalid_page_number")
        page = next((p for p in pages if p.page_number == page_number), None)
        if page is None:
            raise AuditError("invalid_page_number")
        pages = (page,)
        start, end = page.start, page.end
    if not isinstance(limits, PdfQuoteSearchLimits):
        raise AuditError("invalid_quote_search_limits")
    if end - start > limits.max_text_characters:
        raise AuditError("quote_search_text_limit_exceeded")
    return start, end, pages


def _occurrences(
    representation: ParsedRepresentation,
    quote: str,
    scope: tuple[int, int, tuple[PageSpan, ...]],
    limits: PdfQuoteSearchLimits,
) -> Iterator[tuple[int, int, PageSpan | None]]:
    start_bound, end_bound, pages = scope
    count, page_index = 0, 0
    start = representation.text.find(quote, start_bound, end_bound)
    while start != -1:
        count += 1
        if count > limits.max_occurrences:
            raise AuditError("quote_search_occurrence_limit_exceeded")
        end = start + len(quote)
        # Both matches and validated non-overlapping page spans are ordered.
        while page_index < len(pages) and pages[page_index].end <= start:
            page_index += 1
        page = pages[page_index] if page_index < len(pages) else None
        if page is not None and (start < page.start or end > page.end):
            page = None
        yield start, end, page
        start = representation.text.find(quote, start + 1, end_bound)


def find_pdf_quote_candidates(
    representation: ParsedRepresentation,
    quote: str,
    *,
    page_number: int | None = None,
    limits: PdfQuoteSearchLimits = _DEFAULT_LIMITS,
) -> PdfQuoteSearchResult:
    """Count all scoped exact matches, returning bounded page-contained previews.

    A text limit applies to the selected page span, or to the entire text when
    no page is supplied. Limit failures never return completed partial results.
    """
    scope = _scope(representation, quote, page_number, limits)
    candidates: list[PdfQuoteSelector] = []
    occurrence_count = candidate_count = cross_page_match_count = 0
    for start, end, page in _occurrences(representation, quote, scope, limits):
        occurrence_count += 1
        if page is None:
            cross_page_match_count += 1
            continue
        candidate_count += 1
        if len(candidates) < limits.max_candidates:
            prefix = representation.text[max(page.start, start - limits.context_characters) : start]
            suffix = representation.text[end : min(page.end, end + limits.context_characters)]
            candidates.append(
                PdfQuoteSelector(
                    start=start,
                    end=end,
                    quote=quote,
                    page_number=page.page_number,
                    prefix=prefix or None,
                    suffix=suffix or None,
                    regions=(),
                )
            )
    return PdfQuoteSearchResult(
        representation_id=representation.representation_id,
        document_version_id=representation.document_version_id,
        text_sha256=representation.text_sha256,
        candidates=tuple(candidates),
        occurrence_count=occurrence_count,
        candidate_count=candidate_count,
        cross_page_match_count=cross_page_match_count,
        has_more=len(candidates) < candidate_count,
    )


def _validate_context(context: str | None) -> None:
    if context is not None and (
        not isinstance(context, str)
        or not 1 <= len(context) <= 200
        or any(0xD800 <= ord(character) <= 0xDFFF for character in context)
    ):
        raise AuditError("invalid_quote_context")


def resolve_pdf_quote(
    representation: ParsedRepresentation,
    quote: str,
    *,
    page_number: int | None = None,
    prefix: str | None = None,
    suffix: str | None = None,
    limits: PdfQuoteSearchLimits = _DEFAULT_LIMITS,
) -> PdfQuoteSelector:
    """Resolve exactly one match with supplied adjacent, page-contained context.

    The text limit applies to a selected page span or to the entire text. Raw
    occurrences count before context filtering. Compatible cross-page quotes
    and contexts remain in the uniqueness count; support stays unevaluated.
    """
    scope = _scope(representation, quote, page_number, limits)
    _validate_context(prefix)
    _validate_context(suffix)
    prefix_length = len(prefix) if prefix is not None else 0
    suffix_length = len(suffix) if suffix is not None else 0
    text = representation.text
    matching_count = 0
    matching: tuple[int, int, PageSpan | None] | None = None
    for start, end, page in _occurrences(representation, quote, scope, limits):
        context_start, context_end = start - prefix_length, end + suffix_length
        if prefix is not None and (
            context_start < 0 or not text.startswith(prefix, context_start, start)
        ):
            continue
        if suffix is not None and not text.startswith(suffix, end, context_end):
            continue
        matching_count += 1
        if matching_count == 1:
            if page is not None and (context_start < page.start or context_end > page.end):
                page = None
            matching = start, end, page
    if matching_count == 0:
        raise AuditError("quote_not_found")
    if matching_count > 1:
        raise AuditError("quote_ambiguous")
    assert matching is not None
    start, end, page = matching
    if page is None:
        raise AuditError("quote_crosses_page")
    return PdfQuoteSelector(
        start=start,
        end=end,
        quote=quote,
        page_number=page.page_number,
        prefix=prefix,
        suffix=suffix,
        regions=(),
    )
