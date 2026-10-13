"""Read-only, unverified source file preflight."""

from .audit import AuditResult, Limits, audit_poll_files
from .errors import AuditError
from .pdf import (
    PdfExtraction,
    PdfLimits,
    extract_pdf_text,
    locate_pdf_quote,
    to_pdf_representation,
)
from .quotes import (
    PdfQuoteSearchLimits,
    PdfQuoteSearchResult,
    find_pdf_quote_candidates,
    resolve_pdf_quote,
)

__all__ = [
    "AuditError",
    "AuditResult",
    "Limits",
    "audit_poll_files",
    "PdfExtraction",
    "PdfLimits",
    "PdfQuoteSearchLimits",
    "PdfQuoteSearchResult",
    "find_pdf_quote_candidates",
    "resolve_pdf_quote",
    "extract_pdf_text",
    "locate_pdf_quote",
    "to_pdf_representation",
]
