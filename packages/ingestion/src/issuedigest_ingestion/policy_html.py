"""Local Korea policy HTML extraction and existing exact evidence contracts."""

import re
from dataclasses import dataclass, fields
from datetime import date
from hashlib import sha256
from uuid import UUID

from issuedigest_domain.citations import TextQuoteSelector
from issuedigest_domain.sources import ParsedRepresentation
from pydantic import ValidationError

from ._policy_html_parser import (
    Node,
    PolicyParser,
    body_text,
    descendants,
    metadata_text,
    require_complete,
)
from .errors import AuditError

_URL = re.compile(r"https://www\.korea\.kr/news/policyNewsView\.do\?newsId=([0-9]{9})")
_NOTICE = "이 자료는 텍스트에 한하여 공공누리 제1유형(출처표시)의 조건에 따라 이용할 수 있습니다."
_LICENSE_URL = "https://www.kogl.or.kr/info/license.do"
_PARSER_NAME = "korea-policy-html"
_PARSER_VERSION = "1"
_PROFILE = "korea-policy-paragraphs-v1"


@dataclass(frozen=True)
class PolicyHtmlLimits:
    max_raw_bytes: int = 2 * 1024 * 1024
    max_text_characters: int = 100_000
    max_depth: int = 128

    def __post_init__(self) -> None:
        maxima = (8 * 1024 * 1024, 1_000_000, 256)
        for field, maximum in zip(fields(self), maxima, strict=True):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 < value <= maximum:
                raise AuditError("invalid_policy_html_limits")


def _limits(limits: PolicyHtmlLimits) -> None:
    if type(limits) is not PolicyHtmlLimits:
        raise AuditError("invalid_policy_html_limits")
    limits.__post_init__()


def _hash(value: object) -> bool:
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _normalized_text(text: str) -> bool:
    return (
        bool(text)
        and text.strip() == text
        and all(re.sub(r"\s+", " ", line).strip() == line for line in text.split("\n"))
    )


def _source_id(url: str) -> str:
    match = _URL.fullmatch(url) if type(url) is str else None
    if match is None:
        raise AuditError("invalid_policy_html_url")
    return match[1]


def _attribution(publisher: str, title: str, publication_date: date, url: str) -> str:
    return f"{publisher} · 대한민국 정책브리핑 · {title} · {publication_date.isoformat()} · {url}"


@dataclass(frozen=True)
class PolicyHtmlExtraction:
    source_id: str
    canonical_url: str
    title: str
    publisher: str
    publication_date: date
    attribution: str
    license_notice: str
    license_url: str
    text: str
    raw_sha256: str
    raw_bytes: int
    text_sha256: str
    parser_name: str = _PARSER_NAME
    parser_version: str = _PARSER_VERSION
    normalization_profile: str = _PROFILE
    limits: PolicyHtmlLimits = PolicyHtmlLimits()

    def __post_init__(self) -> None:
        try:
            _limits(self.limits)
            for field in fields(self):
                if field.name not in {"publication_date", "raw_bytes", "limits"}:
                    if type(getattr(self, field.name)) is not str:
                        raise ValueError
            if (
                type(self.source_id) is not str
                or self.source_id != _source_id(self.canonical_url)
                or type(self.publication_date) is not date
                or type(self.raw_bytes) is not int
                or not 0 < self.raw_bytes <= self.limits.max_raw_bytes
                or not _hash(self.raw_sha256)
                or not _hash(self.text_sha256)
                or self.parser_name != _PARSER_NAME
                or self.parser_version != _PARSER_VERSION
                or self.normalization_profile != _PROFILE
                or self.license_notice != _NOTICE
                or self.license_url != _LICENSE_URL
                or type(self.text) is not str
                or not _normalized_text(self.text)
                or len(self.text) > self.limits.max_text_characters
                or self.text_sha256 != sha256(self.text.encode("utf-8")).hexdigest()
            ):
                raise ValueError
            for value in (self.title, self.publisher):
                if (
                    type(value) is not str
                    or not value
                    or re.sub(r"\s+", " ", value).strip() != value
                ):
                    raise ValueError
                value.encode("utf-8")
            if self.attribution != _attribution(
                self.publisher, self.title, self.publication_date, self.canonical_url
            ):
                raise ValueError
        except (AuditError, ValueError, UnicodeError, TypeError, AttributeError):
            raise AuditError("policy_html_invalid_result") from None


def _one(nodes: list[Node], error: str) -> Node:
    if len(nodes) != 1:
        raise AuditError(error)
    require_complete(nodes[0])
    return nodes[0]


def _select(node: Node, tag: str, class_name: str) -> list[Node]:
    return [part for part in descendants(node) if part.tag == tag and part.has_class(class_name)]


def extract_policy_html(
    raw: bytes,
    *,
    expected_sha256: str,
    canonical_url: str,
    limits: PolicyHtmlLimits | None = None,
) -> PolicyHtmlExtraction:
    """Verify a supplied snapshot and observed template; source authenticity is external."""
    limits = PolicyHtmlLimits() if limits is None else limits
    _limits(limits)
    if type(raw) is not bytes:
        raise AuditError("invalid_policy_html_raw")
    if not _hash(expected_sha256):
        raise AuditError("invalid_expected_sha256")
    source_id = _source_id(canonical_url)
    if not raw:
        raise AuditError("policy_html_empty_raw")
    if len(raw) > limits.max_raw_bytes:
        raise AuditError("policy_html_byte_limit_exceeded")
    raw_hash = sha256(raw).hexdigest()
    if raw_hash != expected_sha256:
        raise AuditError("policy_html_hash_mismatch")
    try:
        html = raw.decode("utf-8-sig", errors="strict").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeError:
        raise AuditError("policy_html_invalid_utf8") from None
    parser = PolicyParser(limits.max_depth)
    try:
        parser.feed(html)
        parser.close()
    except (ValueError, RecursionError):
        raise AuditError("policy_html_invalid_structure") from None
    root = parser.root
    body = _one(_select(root, "div", "view_cont"), "policy_html_invalid_structure")
    head = _one(
        [part for part in descendants(root) if part.tag == "head"], "policy_html_invalid_metadata"
    )
    urls = [
        part
        for part in descendants(head)
        if part.tag == "meta" and part.attrs.get("property") == "og:url"
    ]
    og_url = _one(urls, "policy_html_invalid_metadata").attrs.get("content")
    if og_url != canonical_url:
        raise AuditError("policy_html_url_mismatch")
    title_container = _one(_select(root, "div", "view_title"), "policy_html_invalid_metadata")
    title_node = _one(
        [part for part in descendants(title_container) if part.tag == "h1"],
        "policy_html_invalid_metadata",
    )
    title = metadata_text(title_node)
    variety = _one(_select(root, "div", "variety"), "policy_html_invalid_metadata")
    info = _one(_select(variety, "div", "info"), "policy_html_invalid_metadata")
    publisher_node = _one(_select(info, "a", "gotosite"), "policy_html_invalid_metadata")
    publisher = metadata_text(publisher_node)
    dates = re.findall(
        r"(?<![0-9.])[0-9]{4}\.[0-9]{2}\.[0-9]{2}(?![0-9.])",
        metadata_text(info, omit_publisher=True),
    )
    if not title or not publisher or len(dates) != 1:
        raise AuditError("policy_html_invalid_metadata")
    try:
        publication_date = date.fromisoformat(dates[0].replace(".", "-"))
    except ValueError:
        raise AuditError("policy_html_invalid_metadata") from None
    license_node = _one(_select(root, "div", "kogl_wrap"), "policy_html_invalid_license")
    license_type = _one(_select(license_node, "div", "type"), "policy_html_invalid_license")
    notice_node = _one(
        [
            child
            for child in license_type.children
            if isinstance(child, Node) and child.tag == "span"
        ],
        "policy_html_invalid_license",
    )
    notice = metadata_text(notice_node)
    wrapper_text = metadata_text(license_node)
    if (
        notice != _NOTICE
        or wrapper_text.count(_NOTICE) != 1
        or re.search(r"공공누리\s*제\s*[2-4]\s*유형", wrapper_text)
    ):
        raise AuditError("policy_html_invalid_license")
    text = body_text(body, limits.max_text_characters)
    return PolicyHtmlExtraction(
        source_id=source_id,
        canonical_url=canonical_url,
        title=title,
        publisher=publisher,
        publication_date=publication_date,
        attribution=_attribution(publisher, title, publication_date, canonical_url),
        license_notice=notice,
        license_url=_LICENSE_URL,
        text=text,
        raw_sha256=raw_hash,
        raw_bytes=len(raw),
        text_sha256=sha256(text.encode("utf-8")).hexdigest(),
        limits=limits,
    )


def to_policy_html_representation(
    extraction: PolicyHtmlExtraction, *, representation_id: UUID, document_version_id: UUID
) -> ParsedRepresentation:
    """Use caller UUID4 identities, no invented pages, tables or document versions."""
    if type(extraction) is not PolicyHtmlExtraction:
        raise AuditError("policy_html_invalid_result")
    extraction.__post_init__()
    try:
        return ParsedRepresentation(
            representation_id=representation_id,
            document_version_id=document_version_id,
            parser_name=extraction.parser_name,
            parser_version=extraction.parser_version,
            normalization_profile=extraction.normalization_profile,
            text=extraction.text,
            text_sha256=extraction.text_sha256,
            pages=(),
            tables=(),
        )
    except ValidationError:
        raise AuditError("policy_html_invalid_representation") from None


def locate_policy_html_quote(
    representation: ParsedRepresentation, *, quote: str, start: int | None = None
) -> TextQuoteSelector:
    """Exact code-point locations only; factual support remains unevaluated."""
    try:
        if type(representation) is not ParsedRepresentation:
            raise ValueError
        validated = ParsedRepresentation.model_validate(representation.model_dump(warnings=False))
        if (
            validated.parser_name != _PARSER_NAME
            or validated.parser_version != _PARSER_VERSION
            or validated.normalization_profile != _PROFILE
            or validated.pages
            or validated.tables
            or not _normalized_text(validated.text)
            or len(validated.text) > 1_000_000
        ):
            raise ValueError
    except (ValidationError, ValueError, TypeError, AttributeError, UnicodeError):
        raise AuditError("policy_html_invalid_representation") from None
    try:
        if type(quote) is not str or not quote.strip():
            raise ValueError
        quote.encode("utf-8")
    except (ValueError, UnicodeError):
        raise AuditError("invalid_quote") from None
    if start is not None and (type(start) is not int or start < 0):
        raise AuditError("invalid_quote_start")
    text = validated.text
    if start is None:
        start = text.find(quote)
        if start == -1:
            raise AuditError("quote_not_found")
        if text.find(quote, start + 1) != -1:
            raise AuditError("quote_ambiguous")
    elif text[start : start + len(quote)] != quote:
        raise AuditError("quote_not_found")
    end = start + len(quote)
    return TextQuoteSelector(
        start=start,
        end=end,
        quote=quote,
        prefix=text[max(0, start - 80) : start] or None,
        suffix=text[end : end + 80] or None,
    )
