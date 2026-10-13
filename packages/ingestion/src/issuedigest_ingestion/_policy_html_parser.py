"""Bounded, selective HTML tree parsing; no browser, script or resource loading."""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

from .errors import AuditError

_VOID = frozenset(
    {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
)
_IGNORED = frozenset({"script", "style", "noscript", "template", "iframe", "figure", "figcaption"})
_INLINE = frozenset(
    {
        "a",
        "abbr",
        "b",
        "bdi",
        "bdo",
        "br",
        "cite",
        "code",
        "data",
        "del",
        "dfn",
        "em",
        "font",
        "i",
        "img",
        "ins",
        "kbd",
        "mark",
        "q",
        "rp",
        "rt",
        "ruby",
        "s",
        "samp",
        "small",
        "span",
        "strong",
        "sub",
        "sup",
        "time",
        "u",
        "var",
        "wbr",
    }
)


@dataclass
class Node:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    children: list["Node | str"] = field(default_factory=list)
    closed: bool = False
    malformed: bool = False

    def has_class(self, name: str) -> bool:
        return name in (self.attrs.get("class") or "").split()

    @property
    def ignored(self) -> bool:
        return self.tag in _IGNORED or self.has_class("imageWrap") or self.has_class("tooltip")


class PolicyParser(HTMLParser):
    def __init__(self, max_depth: int) -> None:
        super().__init__(convert_charrefs=True)
        self.root = Node("root", closed=True)
        self.stack = [self.root]
        self.max_depth = max_depth

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if len(self.stack) > self.max_depth:
            raise AuditError("policy_html_depth_limit_exceeded")
        node = Node(tag, dict(attrs), closed=tag in _VOID)
        node.malformed = len(attrs) != len(node.attrs)
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in _VOID:
            return
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                node = self.stack[index]
                if index != len(self.stack) - 1:
                    node.malformed = True
                node.closed = True
                del self.stack[index:]
                return
        # Unrelated page errors are tolerated, but errors inside selected nodes persist.
        self.stack[-1].malformed = True

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def descendants(node: Node, *, include_ignored: bool = False) -> Iterator[Node]:
    for child in node.children:
        if isinstance(child, Node) and (include_ignored or not child.ignored):
            yield child
            yield from descendants(child, include_ignored=include_ignored)


def require_complete(node: Node) -> None:
    if any(
        not part.closed or part.malformed
        for part in (node, *descendants(node, include_ignored=True))
    ):
        raise AuditError("policy_html_invalid_structure")


def text_content(node: Node, *, omit_publisher: bool = False) -> str:
    parts: list[str] = []
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
        elif not child.ignored and not (omit_publisher and child.has_class("gotosite")):
            parts.append(
                "\n" if child.tag == "br" else text_content(child, omit_publisher=omit_publisher)
            )
    return "".join(parts)


def metadata_text(node: Node, *, omit_publisher: bool = False) -> str:
    return re.sub(r"\s+", " ", text_content(node, omit_publisher=omit_publisher)).strip()


def body_text(node: Node, max_characters: int) -> str:
    paragraphs: list[str] = []

    def walk(current: Node, inside_paragraph: bool = False) -> None:
        if current.ignored:
            return
        if current.tag in {"table", "ul", "ol", "dl", "li", "dt", "dd"}:
            raise AuditError("policy_html_invalid_structure")
        if current.tag == "p":
            if inside_paragraph:
                raise AuditError("policy_html_invalid_structure")
            # Ordinary source whitespace collapses; only explicit br creates LF.
            pieces: list[str] = []

            def paragraph(part: Node) -> None:
                for child in part.children:
                    if isinstance(child, str):
                        pieces.append(re.sub(r"\s+", " ", child))
                    elif not child.ignored:
                        if child.tag not in _INLINE:
                            raise AuditError("policy_html_invalid_structure")
                        if child.tag == "br":
                            pieces.append("\n")
                        else:
                            paragraph(child)

            paragraph(current)
            text = "\n".join(
                re.sub(r"[^\S\n]+", " ", line).strip() for line in "".join(pieces).split("\n")
            ).strip()
            if text:
                paragraphs.append(text)
            inside_paragraph = True
        for child in current.children:
            if isinstance(child, str):
                if not inside_paragraph and child.strip():
                    raise AuditError("policy_html_invalid_structure")
            else:
                walk(child, inside_paragraph)

    walk(node)
    text = "\n\n".join(paragraphs)
    if len(text) > max_characters:
        raise AuditError("policy_html_text_limit_exceeded")
    if not text:
        raise AuditError("policy_html_empty_text")
    return text
