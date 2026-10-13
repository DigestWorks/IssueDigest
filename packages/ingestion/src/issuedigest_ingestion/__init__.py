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

__all__ = [
    "AuditError",
    "AuditResult",
    "Limits",
    "audit_poll_files",
    "PdfExtraction",
    "PdfLimits",
    "extract_pdf_text",
    "locate_pdf_quote",
    "to_pdf_representation",
]
