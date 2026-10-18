"""Fixed direct-result policy list profile; inert HTML, never a source of evidence."""

import re
from dataclasses import dataclass, field

from .html import _VOID, _Document

ORIGIN = "https://www.korea.kr"
ARTICLE_PATH = "/news/policyNewsView.do?newsId="


@dataclass(repr=False)
class _Node:
    tag: str
    attrs: dict[str, str | None] = field(default_factory=dict)
    hidden: bool = False
    children: list["_Node | str"] = field(default_factory=list)

    def matches(self, tag: str, class_name: str | None = None) -> bool:
        return self.tag == tag and (
            class_name is None or class_name in (self.attrs.get("class") or "").split()
        )


class _List(_Document):
    def __init__(self) -> None:
        super().__init__()
        self.root = _Node("root")
        self.parents = [self.root]
        self.bodies: list[_Node] = []

    def start(self, tag: str, attrs: dict[str, str | None], hidden: bool) -> None:
        # Native hidden/unsupported rendering is outside this static source profile.
        hidden = hidden or tag in {"details", "dialog", "iframe", "object", "svg"}
        node = _Node(tag, attrs, hidden or self.parents[-1].hidden)
        self.parents[-1].children.append(node)
        if node.matches("div", "article_body"):
            self.bodies.append(node)
        if tag not in _VOID:
            self.parents.append(node)

    def end(self, tag: str) -> None:
        self.parents.pop()

    def handle_data(self, data: str) -> None:
        self.parents[-1].children.append(data)


def _nodes(node: _Node) -> list[_Node]:
    if node.hidden or any(isinstance(c, str) and c.strip() for c in node.children):
        raise ValueError("Invalid result structure")
    return [c for c in node.children if isinstance(c, _Node)]


def _one(node: _Node, tag: str, class_name: str | None = None) -> _Node:
    found = [c for c in _nodes(node) if c.matches(tag, class_name)]
    if len(found) != 1 or found[0].hidden:
        raise ValueError("Invalid result structure")
    return found[0]


def _text(node: _Node) -> str:
    if node.hidden:
        raise ValueError("Hidden result metadata")
    return "".join(c if isinstance(c, str) else _text(c) for c in node.children)


def result_entries(html: str) -> tuple[tuple[str, str], ...]:
    parser = _List()
    parser.parse(html)
    if len(parser.bodies) != 1:
        raise ValueError("Missing or ambiguous result body")
    lists = [
        child
        for region in _nodes(parser.bodies[0])
        if region.matches("div", "list_type")
        for child in _nodes(region)
        if child.matches("ul")
    ]
    if len(lists) != 1:
        raise ValueError("Missing or ambiguous result list")
    entries = _nodes(lists[0])
    if not 1 <= len(entries) <= 100:
        raise ValueError("Empty or oversized result list")
    result: dict[str, str] = {}
    for entry in entries:
        if not entry.matches("li") or len(_nodes(entry)) != 1:
            raise ValueError("Invalid result entry")
        anchor = _one(entry, "a")
        text = _one(anchor, "span", "text")
        title_node = _one(text, "strong")
        title = " ".join(_text(title_node).split())
        source = _one(text, "span", "source")
        if (
            not title
            or len(title) > 300
            or len(_nodes(source)) != 2
            or any(c.tag != "span" or not _text(c).strip() for c in _nodes(source))
        ):
            raise ValueError("Invalid result metadata")
        href = anchor.attrs.get("href") or ""
        match = re.fullmatch(
            r"(?:https://www\.korea\.kr)?/news/policyNewsView\.do\?newsId=([0-9]{9})", href
        )
        # A noncanonical link is never stripped/normalized into a candidate.
        if match is not None:
            identity = match[1]
            if identity in result and result[identity] != title:
                raise ValueError("Conflicting duplicate result")
            result[identity] = title
    if not result:
        raise ValueError("No canonical results")
    return tuple(result.items())
