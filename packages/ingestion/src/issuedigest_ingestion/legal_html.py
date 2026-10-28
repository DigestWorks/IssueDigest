"""Offline extraction of the official law.go.kr lsInfoR HTML paragraph profile.

The displayed effective date identifies the selected document, not the currentness
of each provision. Supplementary effective-date exceptions remain in the text.
"""

import re
import unicodedata
from dataclasses import dataclass, fields
from datetime import date
from hashlib import sha256

from ._policy_html_parser import Node, PolicyParser, descendants, require_complete
from .errors import AuditError

_URL = re.compile(
    r"https://www\.law\.go\.kr/LSW/lsInfoR\.do\?lsiSeq=([1-9][0-9]{0,11})&efYd=([0-9]{8})"
)


@dataclass(frozen=True)
class LegalHtmlLimits:
    max_raw_bytes: int = 2 * 1024 * 1024
    max_text_characters: int = 100_000
    max_depth: int = 128
    max_text_nodes: int = 100_000

    def __post_init__(self) -> None:
        for field, maximum in zip(
            fields(self), (2 * 1024 * 1024, 100_000, 128, 100_000), strict=True
        ):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 < value <= maximum:
                raise AuditError("invalid_legal_html_limits")


@dataclass(frozen=True)
class LegalHtmlExtraction:
    source_id: str
    canonical_url: str
    law_name: str
    title: str
    effective_date: date
    header: str
    text: str
    raw_sha256: str
    raw_bytes: int
    text_sha256: str
    parser_name: str = "law-go-kr-html"
    parser_version: str = "1"
    normalization_profile: str = "law-go-kr-paragraphs-v1"


def _hidden(node: Node) -> bool:
    style = re.sub(r"\s+", "", node.attrs.get("style") or "").lower()
    return (
        node.tag
        in {
            "script",
            "style",
            "noscript",
            "template",
            "iframe",
            "button",
            "input",
            "select",
            "textarea",
        }
        or "hidden" in node.attrs
        or (node.attrs.get("aria-hidden") or "").lower() == "true"
        or "display:none" in style
        or "visibility:hidden" in style
    )


def _text(node: Node, *, skip_span: bool = False) -> str:
    parts = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif not _hidden(child) and not (skip_span and child.tag == "span"):
            parts.append(" " if child.tag == "br" else _text(child))
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", "".join(parts)).strip())


_DEFAULT_LIMITS = LegalHtmlLimits()


def extract_legal_html(
    raw: bytes, canonical_url: str, *, limits: LegalHtmlLimits = _DEFAULT_LIMITS
) -> LegalHtmlExtraction:
    if type(limits) is not LegalHtmlLimits:
        raise AuditError("invalid_legal_html_limits")
    limits.__post_init__()
    match = _URL.fullmatch(canonical_url) if type(canonical_url) is str else None
    if match is None:
        raise AuditError("invalid_legal_html_url")
    source_id, effective = match.groups()
    try:
        expected_date = date(int(effective[:4]), int(effective[4:6]), int(effective[6:]))
    except ValueError:
        raise AuditError("invalid_legal_html_url") from None
    if type(raw) is not bytes or not raw or len(raw) > limits.max_raw_bytes:
        raise AuditError("legal_html_raw_limit_exceeded")

    class BoundedParser(PolicyParser):
        text_nodes = 0

        def handle_data(self, data: str) -> None:
            self.text_nodes += 1
            if self.text_nodes > limits.max_text_nodes:
                raise AuditError("legal_html_text_node_limit_exceeded")
            super().handle_data(data)

    parser = BoundedParser(limits.max_depth)
    try:
        parser.feed(raw.decode("utf-8-sig", errors="strict"))
        parser.close()
    except UnicodeError:
        raise AuditError("legal_html_invalid_encoding") from None
    all_nodes = list(descendants(parser.root, include_ignored=True))

    def one(nodes: list[Node]) -> Node:
        if len(nodes) != 1:
            raise AuditError("legal_html_invalid_structure")
        require_complete(nodes[0])
        return nodes[0]

    def by_id(identifier: str) -> Node:
        return one([n for n in all_nodes if n.attrs.get("id") == identifier])

    canonical_links = [
        n
        for n in all_nodes
        if n.tag == "link" and "canonical" in (n.attrs.get("rel") or "").split()
    ]
    if canonical_links and (
        len(canonical_links) != 1 or canonical_links[0].attrs.get("href") != canonical_url
    ):
        raise AuditError("legal_html_metadata_mismatch")
    metadata: dict[str, str] = {}
    for key in ("lsNm", "lsiSeq", "efYd"):
        n = one([n for n in all_nodes if n.attrs.get("id") == key or n.attrs.get("name") == key])
        if n.tag != "input" or not n.attrs.get("value"):
            raise AuditError("legal_html_invalid_metadata")
        value = n.attrs["value"]
        assert value is not None
        metadata[key] = value
    if metadata["lsiSeq"] != source_id or metadata["efYd"] != effective:
        raise AuditError("legal_html_metadata_mismatch")
    body, top, scroll, supplements = [
        by_id(k) for k in ("contentBody", "conTop", "conScroll", "arDivArea")
    ]
    if (
        top not in list(descendants(body))
        or scroll not in list(descendants(body))
        or supplements not in list(descendants(scroll))
    ):
        raise AuditError("legal_html_invalid_structure")
    for selected in (body, top, scroll, supplements):
        if _hidden(selected) or any(
            _hidden(ancestor) and selected in list(descendants(ancestor, include_ignored=True))
            for ancestor in all_nodes
        ):
            raise AuditError("legal_html_invalid_structure")
    heading = one([n for n in descendants(top) if n.tag == "h2"])
    law_name = _text(heading, skip_span=True)
    header = _text(one([n for n in descendants(top) if n.has_class("ct_sub")]))
    if law_name != unicodedata.normalize("NFC", metadata["lsNm"]) or not law_name:
        raise AuditError("legal_html_metadata_mismatch")
    displayed = re.match(r"\[시행\s+(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\]", header)
    if (
        not displayed
        or tuple(map(int, displayed.groups()))
        != (expected_date.year, expected_date.month, expected_date.day)
        or not re.search(r"\[법률 제\d+호,", header)
    ):
        raise AuditError("legal_html_metadata_mismatch")
    paragraphs: list[str] = []
    article_count = 0

    controls = {
        "script",
        "style",
        "noscript",
        "template",
        "iframe",
        "button",
        "input",
        "select",
        "textarea",
    }

    def substantive_text(node: Node) -> str:
        if node.tag in controls:
            return ""
        return "".join(
            child if isinstance(child, str) else substantive_text(child) for child in node.children
        ).strip()

    def require_visible_inline(node: Node, hidden: bool = False) -> None:
        if node.tag in controls:
            return
        hidden = hidden or _hidden(node)
        if hidden and substantive_text(node):
            raise AuditError("legal_html_hidden_statutory_content")
        for child in node.children:
            if isinstance(child, Node):
                require_visible_inline(child, hidden)

    def walk(
        node: Node, in_law: bool = False, in_supplement: bool = False, hidden: bool = False
    ) -> None:
        nonlocal article_count
        if node.tag in controls:
            return
        hidden = hidden or _hidden(node)
        in_law = in_law or node.has_class("lawcon")
        in_supplement = in_supplement or node is supplements
        if node.tag == "p" and (in_law or in_supplement or node.has_class("gtit")):
            require_visible_inline(node, hidden)
            value = _text(node)
            if value:
                paragraphs.append(value)
                if in_law:
                    article_count += 1
            return
        for child in node.children:
            if isinstance(child, Node):
                walk(child, in_law, in_supplement, hidden)

    walk(scroll)
    text = "\n".join([_text(heading), header, *paragraphs])
    if not article_count or not paragraphs:
        raise AuditError("legal_html_empty_text")
    if len(text) > limits.max_text_characters:
        raise AuditError("legal_html_text_limit_exceeded")
    return LegalHtmlExtraction(
        source_id,
        canonical_url,
        law_name,
        _text(heading),
        expected_date,
        header,
        text,
        sha256(raw).hexdigest(),
        len(raw),
        sha256(text.encode()).hexdigest(),
    )
