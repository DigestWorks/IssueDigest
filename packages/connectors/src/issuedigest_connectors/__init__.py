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

from .policy_sdk import (
    MAX_POLICY_CAPTURE_BYTES,
    MAX_POLICY_DISCOVERY_BYTES,
    POLICY_LIST_URL,
    PolicyArticle,
    PolicyCandidate,
    PolicyCapture,
    PolicyDiscovery,
    PolicyError,
    capture_policy,
    discover_policy,
    parse_policy_capture,
    parse_policy_discovery,
    policy_candidates,
    policy_url,
    serialize_policy_capture,
    serialize_policy_discovery,
)

__all__ += [
    "MAX_POLICY_CAPTURE_BYTES",
    "MAX_POLICY_DISCOVERY_BYTES",
    "POLICY_LIST_URL",
    "PolicyArticle",
    "PolicyCandidate",
    "PolicyCapture",
    "PolicyDiscovery",
    "PolicyError",
    "capture_policy",
    "discover_policy",
    "parse_policy_capture",
    "parse_policy_discovery",
    "policy_candidates",
    "policy_url",
    "serialize_policy_capture",
    "serialize_policy_discovery",
]
