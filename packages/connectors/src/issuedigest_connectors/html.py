"""Fail-closed public Assembly HTML profile; no DOM repair or external CSS execution."""

import re
from html.parser import HTMLParser

MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_TEXT = 100_000
_VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
_BLOCK = frozenset(
    (
        "address article aside blockquote dd div dl dt fieldset figcaption figure footer "
        "form h1 h2 h3 h4 h5 h6 header hr li main nav ol p pre section "
        "table tbody td th thead tr ul"
    ).split()
)
_IGNORED = frozenset({"script", "style", "template", "noscript", "head", "datalist"})
_UNSUPPORTED_RENDERING = frozenset(
    {
        "iframe",
        "object",
        "embed",
        "canvas",
        "svg",
        "math",
        "video",
        "audio",
        "details",
        "textarea",
        "select",
    }
)


def bounded_html(value: str) -> str:
    if type(value) is not str or len(value) > MAX_HTML_BYTES:
        raise ValueError("Invalid HTML")
    if len(value.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError("HTML budget exceeded")
    if any(ord(c) < 32 and c not in "\t\r\n\f" for c in value):
        raise ValueError("Invalid HTML character")
    return value


def normalize_text(value: str) -> str:
    """Collapse Unicode whitespace, retain explicit block lines and original code points."""
    return "\n".join(part for line in value.split("\n") if (part := " ".join(line.split())))


def _hidden(tag: str, attrs: dict[str, str | None]) -> bool:
    style = re.sub(r"\s+", "", attrs.get("style") or "").lower()
    return (
        tag in _IGNORED
        or (tag in {"dialog", "details"} and "open" not in attrs)
        or "popover" in attrs
        or "hidden" in attrs
        or "inert" in attrs
        or (attrs.get("aria-hidden") or "").lower() == "true"
        or re.search(
            r"(?:^|;)(?:display:none|visibility:(?:hidden|collapse))(?:!important)?(?:;|$)", style
        )
        is not None
    )


class _Document(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, bool]] = []
        self.styles: list[str | None] = []
        self.nodes = 0

    @property
    def hidden(self) -> bool:
        return bool(self.stack and self.stack[-1][1])

    def _attributes(
        self, tag: str, attributes: list[tuple[str, str | None]]
    ) -> dict[str, str | None]:
        self.nodes += 1
        if self.nodes > 50_000 or len(self.stack) >= 64 or len(attributes) > 64:
            raise ValueError("HTML structure budget exceeded")
        attrs = dict(attributes)
        if len(attrs) != len(attributes):
            raise ValueError("Duplicate attribute")
        if tag == "meta":
            if "charset" in attrs and (attrs["charset"] or "").lower() != "utf-8":
                raise ValueError("Non UTF-8 HTML declaration")
            if (attrs.get("http-equiv") or "").lower() == "content-type" and re.fullmatch(
                r'text/html\s*;\s*charset\s*=\s*(?:utf-8|"utf-8")\s*',
                attrs.get("content") or "",
                flags=re.I,
            ) is None:
                raise ValueError("Non UTF-8 HTML declaration")
        return attrs

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        attrs = self._attributes(tag, attributes)
        hidden = self.hidden or _hidden(tag, attrs)
        self.start(tag, attrs, hidden)
        if tag not in _VOID:
            self.stack.append((tag, hidden))
            self.styles.append(attrs.get("style"))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError("Malformed HTML nesting")
        self.end(tag)
        self.stack.pop()
        self.styles.pop()

    def start(self, tag: str, attrs: dict[str, str | None], hidden: bool) -> None:
        pass

    def end(self, tag: str) -> None:
        pass

    def parse(self, html: str) -> None:
        self.feed(bounded_html(html))
        self.close()
        self.finish()

    def finish(self) -> None:
        if self.stack:
            raise ValueError("Unclosed HTML")


class _VisibleDocument(_Document):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def start(self, tag: str, attrs: dict[str, str | None], hidden: bool) -> None:
        if not hidden and (tag in _BLOCK or tag == "br"):
            self.parts.append("\n")

    def end(self, tag: str) -> None:
        if not self.hidden and tag in _BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            # Whitespace in HTML source isn't a semantic line break.
            if any(tag == "pre" for tag, _ in self.stack):
                self.parts.append(data.replace("\r\n", "\n").replace("\r", "\n"))
            else:
                self.parts.append(re.sub(r"\s+", " ", data))


class _Summary(_VisibleDocument):
    def __init__(self) -> None:
        super().__init__()
        self.region: int | None = None
        self.count = 0
        self.characters = 0

    def start(self, tag: str, attrs: dict[str, str | None], hidden: bool) -> None:
        if attrs.get("id") == "prntSummary":
            self.count += 1
            if (
                self.count != 1
                or hidden
                or tag in _VOID
                or any(name in _UNSUPPORTED_RENDERING for name, _ in self.stack)
            ):
                raise ValueError("Ambiguous summary")
            for style in self.styles:
                if (
                    style
                    and re.fullmatch(
                        r"\s*height\s*:\s*(?:auto|[1-9][0-9]{0,3}px)\s*;?\s*",
                        style,
                        flags=re.I,
                    )
                    is None
                ):
                    raise ValueError("Unprofiled summary ancestor style")
            self.region = len(self.stack) + 1
        if self.region is not None:
            if not hidden:
                # Only the observed summary class and a positive pixel height
                # are profiled. Unknown CSS could change visibility/whitespace;
                # reject it rather than treating its text as official evidence.
                if attrs.get("class") and attrs["class"] != "theme_list_summary":
                    raise ValueError("Unprofiled summary CSS class")
                if (
                    attrs.get("style")
                    and re.fullmatch(
                        r"\s*height\s*:\s*[1-9][0-9]{0,3}px\s*;?\s*",
                        attrs["style"] or "",
                        flags=re.I,
                    )
                    is None
                ):
                    raise ValueError("Unprofiled summary style")
            ancestors = {name for name, _ in self.stack[self.region - 1 :]}
            if (
                tag in _UNSUPPORTED_RENDERING
                or "popover" in attrs
                or ("p" in ancestors and tag in _BLOCK)
                or (tag == "a" and "a" in ancestors)
                or (tag == "pre" and "pre" in ancestors)
            ):
                raise ValueError("Ambiguous summary structure")
            super().start(tag, attrs, hidden)

    def end(self, tag: str) -> None:
        if self.region is not None:
            super().end(tag)
            if self.region == len(self.stack):
                self.region = None

    def handle_data(self, data: str) -> None:
        if self.region is not None and not self.hidden:
            self.characters += len(data)
            if self.characters > MAX_HTML_BYTES:
                raise ValueError("Summary budget exceeded")
            super().handle_data(data)


def summary_text(html: str) -> str:
    parser = _Summary()
    parser.parse(html)
    text = normalize_text("".join(parser.parts))
    if parser.count != 1 or not text or len(text) > MAX_TEXT:
        raise ValueError("Invalid summary")
    return text


class _Detail(_VisibleDocument):
    def __init__(self) -> None:
        super().__init__()
        self.forms = 0
        self.form_depth: int | None = None
        self.fields: dict[str, str] = {}
        self.tokens: list[str] = []
        self.opaque_footer = False
        self.footer_depth = 0
        self.summary_selectors = 0

    def _summary_selector(self, attrs: dict[str, str | None]) -> None:
        if attrs.get("id") == "prntSummary":
            self.summary_selectors += 1
            if self.summary_selectors > 1:
                raise ValueError("Duplicate summary selector")

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        if (
            tag == "footer"
            and self.forms == 1
            and self.form_depth is None
            and len(self.tokens) == 1
            and all(name in {"html", "body"} for name, _ in self.stack)
        ):
            self.opaque_footer = True
        if not self.opaque_footer:
            super().handle_starttag(tag, attributes)
            return
        # An observed legacy footer embeds a broken document. It is opaque,
        # never repaired or used as evidence/metadata. Still scan the entire
        # bounded tail for critical selectors so ambiguity cannot hide here.
        attrs = self._attributes(tag, attributes)
        self._summary_selector(attrs)
        if (tag == "form" and attrs.get("id") == "form") or (
            tag == "meta" and attrs.get("name") == "_csrf"
        ):
            raise ValueError("Duplicate critical selector in footer")
        if tag not in _VOID:
            self.footer_depth += 1
            if self.footer_depth + len(self.stack) > 64:
                raise ValueError("Footer structure budget exceeded")

    def handle_endtag(self, tag: str) -> None:
        if self.opaque_footer:
            # This is only a resource counter, not a recovered DOM stack.
            self.footer_depth = max(0, self.footer_depth - 1)
        else:
            super().handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        if not self.opaque_footer:
            super().handle_data(data)

    def finish(self) -> None:
        if not self.opaque_footer:
            super().finish()

    def start(self, tag: str, attrs: dict[str, str | None], hidden: bool) -> None:
        self._summary_selector(attrs)
        super().start(tag, attrs, hidden)
        if tag == "form":
            if any(name == "form" for name, _ in self.stack):
                raise ValueError("Nested form")
            if attrs.get("id") == "form":
                self.forms += 1
                self.form_depth = len(self.stack) + 1
        if tag == "meta" and attrs.get("name") == "_csrf":
            token = attrs.get("content") or ""
            if (
                not token
                or len(token) > 4096
                or not token.isascii()
                or any(ord(c) < 33 or ord(c) > 126 for c in token)
            ):
                raise ValueError("Invalid token")
            self.tokens.append(token)
        if tag == "input" and self.form_depth is not None:
            name, value = attrs.get("name"), attrs.get("value")
            if name is None:
                return
            if (
                re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]{0,79}", name, flags=re.ASCII) is None
                or value is None
                or len(value) > 4096
                or name in self.fields
                or len(self.fields) >= 64
            ):
                raise ValueError("Invalid form field")
            self.fields[name] = value
            if sum(len(k) + len(v.encode("utf-8")) for k, v in self.fields.items()) > 16_384:
                raise ValueError("Form budget exceeded")

    def end(self, tag: str) -> None:
        super().end(tag)
        if tag == "form" and self.form_depth == len(self.stack):
            self.form_depth = None


def detail_fields(html: str, bill_id: str) -> tuple[dict[str, str], str, str]:
    parser = _Detail()
    parser.parse(html)
    if parser.forms != 1 or len(parser.tokens) != 1 or parser.fields.get("billId") != bill_id:
        raise ValueError("Invalid detail identity")
    return parser.fields, parser.tokens[0], normalize_text("".join(parser.parts))


def visible_text(html: str) -> str:
    parser = _VisibleDocument()
    parser.parse(html)
    return normalize_text("".join(parser.parts))
