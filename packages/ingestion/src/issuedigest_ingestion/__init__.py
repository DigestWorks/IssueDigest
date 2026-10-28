"""Read-only, unverified source file preflight."""

from .audit import AuditResult, Limits, audit_poll_files
from .errors import AuditError
from .hwpx import (
    HwpxCell,
    HwpxExtraction,
    HwpxLimits,
    HwpxSection,
    HwpxSpan,
    HwpxTable,
    HwpxTextSpan,
    extract_hwpx,
    locate_hwpx_cell,
    locate_hwpx_quote,
    to_hwpx_representation,
)
from .legacy_bill import (
    LegacyBillMetadata,
    locate_legacy_bill_quote,
    parse_legacy_bill_metadata,
    to_legacy_bill_representation,
)
from .pdf import (
    PdfExtraction,
    PdfLimits,
    extract_pdf_text,
    locate_pdf_quote,
    to_pdf_representation,
)
from .policy_html import (
    PolicyHtmlExtraction,
    PolicyHtmlLimits,
    extract_policy_html,
    locate_policy_html_quote,
    to_policy_html_representation,
)
from .quotes import (
    PdfQuoteSearchLimits,
    PdfQuoteSearchResult,
    find_pdf_quote_candidates,
    resolve_pdf_quote,
)

__all__ = [
    "LegacyBillMetadata",
    "parse_legacy_bill_metadata",
    "to_legacy_bill_representation",
    "locate_legacy_bill_quote",
    "HwpxLimits",
    "HwpxExtraction",
    "HwpxSpan",
    "HwpxTextSpan",
    "HwpxSection",
    "HwpxCell",
    "HwpxTable",
    "extract_hwpx",
    "to_hwpx_representation",
    "locate_hwpx_quote",
    "locate_hwpx_cell",
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
    "PolicyHtmlExtraction",
    "PolicyHtmlLimits",
    "extract_policy_html",
    "locate_policy_html_quote",
    "to_policy_html_representation",
]

from .legal_html import LegalHtmlExtraction, LegalHtmlLimits, extract_legal_html

__all__ += ["LegalHtmlExtraction", "LegalHtmlLimits", "extract_legal_html"]
