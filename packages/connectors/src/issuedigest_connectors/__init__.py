"""Bounded source connectors; imports perform no IO or environment-key reads."""

from .assembly import (
    MAX_CAPTURE_BYTES,
    AssemblyCapture,
    AssemblyError,
    canonical_url,
    capture_assembly,
    extract_assembly_summary,
    parse_capture,
    serialize_capture,
)

__all__ = [
    "MAX_CAPTURE_BYTES",
    "AssemblyCapture",
    "AssemblyError",
    "canonical_url",
    "capture_assembly",
    "extract_assembly_summary",
    "parse_capture",
    "serialize_capture",
]
