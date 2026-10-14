"""Bounded local HWPX extraction. No licensing or semantic metadata inference."""

import re
import struct
from dataclasses import dataclass, fields
from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from typing import NoReturn
from uuid import UUID
from xml.etree.ElementTree import Element, TreeBuilder
from xml.parsers import expat
from zipfile import BadZipFile, ZipFile
from zlib import error as ZlibError

from issuedigest_domain.citations import TableCellSelector, TextQuoteSelector
from issuedigest_domain.sources import ParsedRepresentation, ParsedTable, TableCell
from pydantic import ValidationError

from .errors import AuditError

_SEC = "http://www.hancom.co.kr/hwpml/2011/section"
_HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
_OPF = "http://www.idpf.org/2007/opf/"
_NAME = "hwpx"
_VERSION = "1"
_PROFILE = "hwpx-flow-v1"
_SECTION_BREAK = "\n\f\n"


def _tag(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


def _fail(code: str = "invalid_structure") -> NoReturn:
    raise AuditError(f"hwpx_{code}") from None


@dataclass(frozen=True)
class HwpxLimits:
    max_raw_bytes: int = 16 * 1024 * 1024
    max_member_bytes: int = 8 * 1024 * 1024
    max_total_bytes: int = 32 * 1024 * 1024
    max_members: int = 512
    max_sections: int = 64
    max_nodes: int = 100_000
    max_depth: int = 128
    max_text_characters: int = 1_000_000
    max_tables: int = 1_000
    max_cells: int = 20_000
    max_grid_slots: int = 100_000

    def __post_init__(self) -> None:
        maxima = (
            64 * 1024 * 1024,
            16 * 1024 * 1024,
            64 * 1024 * 1024,
            2048,
            256,
            200_000,
            256,
            1_000_000,
            2000,
            40_000,
            200_000,
        )
        for field, maximum in zip(fields(self), maxima, strict=True):
            value = getattr(self, field.name)
            if type(value) is not int or not 0 < value <= maximum:
                _fail("invalid_limits")


def _limits(value: HwpxLimits) -> None:
    if type(value) is not HwpxLimits:
        _fail("invalid_limits")
    value.__post_init__()


@dataclass(frozen=True)
class HwpxSpan:
    """A Unicode code-point interval; empty cells have no spans."""

    start: int
    end: int


@dataclass(frozen=True)
class HwpxTextSpan:
    start: int
    end: int
    section_index: int
    table_id: str | None = None
    cell_id: str | None = None


@dataclass(frozen=True)
class HwpxSection:
    section_index: int
    member_name: str
    start: int
    end: int


@dataclass(frozen=True)
class HwpxCell:
    cell_id: str
    row: int
    column: int
    row_span: int
    column_span: int
    text: str
    spans: tuple[HwpxSpan, ...]


@dataclass(frozen=True)
class HwpxTable:
    table_id: str
    section_index: int
    row_count: int
    column_count: int
    parent_cell_id: str | None
    start: int
    end: int
    cells: tuple[HwpxCell, ...]


@dataclass(frozen=True)
class HwpxExtraction:
    text: str
    raw_sha256: str
    raw_bytes: int
    text_sha256: str
    sections: tuple[HwpxSection, ...]
    spans: tuple[HwpxTextSpan, ...]
    tables: tuple[HwpxTable, ...]
    limits: HwpxLimits
    parser_name: str = _NAME
    parser_version: str = _VERSION
    normalization_profile: str = _PROFILE

    def __post_init__(self) -> None:
        _validate_result(self)


def _hash(value: object) -> bool:
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def _int(value: object, maximum: int, *, positive: bool = False) -> int:
    if type(value) is not str or len(value) > 10 or re.fullmatch("[0-9]+", value) is None:
        _fail()
    number = int(value)
    if number > maximum or (positive and number == 0):
        _fail()
    return number


def _path(value: object) -> str:
    if (
        type(value) is not str
        or not value
        or len(value) > 256
        or any(ord(c) < 32 for c in value)
        or any(c in value for c in "\\:%?#")
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        _fail("invalid_package")
    return value


class _Xml:
    def __init__(self, limits: HwpxLimits) -> None:
        self.limits = limits
        self.nodes = 0

    def parse(self, raw: bytes) -> Element:
        builder = TreeBuilder()
        parser = expat.ParserCreate(namespace_separator="}")
        depth = 0

        def name(value: str) -> str:
            return "{" + value if "}" in value else value

        def start(tag: str, attrs: dict[str, str]) -> None:
            nonlocal depth
            depth += 1
            self.nodes += 1
            if depth > self.limits.max_depth:
                _fail("depth_limit_exceeded")
            if self.nodes > self.limits.max_nodes:
                _fail("node_limit_exceeded")
            builder.start(name(tag), {name(k): v for k, v in attrs.items()})

        def end(tag: str) -> None:
            nonlocal depth
            builder.end(name(tag))
            depth -= 1

        def forbidden(*args: object) -> None:
            _fail("invalid_xml")

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.CharacterDataHandler = builder.data
        parser.StartDoctypeDeclHandler = forbidden
        parser.EntityDeclHandler = forbidden
        parser.ExternalEntityRefHandler = lambda *args: 0
        parser.ProcessingInstructionHandler = forbidden
        try:
            parser.Parse(raw, True)
            return builder.close()
        except (expat.ExpatError, ValueError):
            _fail("invalid_xml")


def _one(node: Element, tag: str) -> Element:
    found = [child for child in node if child.tag == tag]
    if len(found) != 1:
        _fail()
    return found[0]


def _zip(raw: bytes, limits: HwpxLimits) -> ZipFile:
    # Bound central-directory entry allocation before ZipFile builds ZipInfo objects.
    end = raw.rfind(b"PK\x05\x06", max(0, len(raw) - 65557))
    if end < 0 or end + 22 > len(raw):
        _fail("invalid_package")
    disk, central_disk, disk_count, count, size, offset, comment = struct.unpack_from(
        "<4H2IH", raw, end + 4
    )
    if (
        disk
        or central_disk
        or disk_count != count
        or count == 65535
        or offset + size != end
        or end + 22 + comment != len(raw)
    ):
        _fail("invalid_package")
    if count > limits.max_members:
        _fail("member_limit_exceeded")
    cursor = offset
    observed = 0
    while cursor < end:
        if cursor + 46 > end or raw[cursor : cursor + 4] != b"PK\x01\x02":
            _fail("invalid_package")
        observed += 1
        if observed > limits.max_members:
            _fail("member_limit_exceeded")
        name_size, extra_size, comment_size = struct.unpack_from("<3H", raw, cursor + 28)
        cursor += 46 + name_size + extra_size + comment_size
    if cursor != end or observed != count:
        _fail("invalid_package")
    archive = ZipFile(BytesIO(raw))
    try:
        entries = archive.infolist()
        if len(entries) != count:
            _fail("invalid_package")
        names: set[str] = set()
        total = 0
        for info in entries:
            name = _path(info.orig_filename)
            if name != info.filename:
                _fail("invalid_package")
            if name in names or info.flag_bits & 1 or info.compress_type not in {0, 8}:
                _fail("invalid_package")
            names.add(name)
            if info.file_size > limits.max_member_bytes:
                _fail("member_byte_limit_exceeded")
            total += info.file_size
            if total > limits.max_total_bytes:
                _fail("total_byte_limit_exceeded")
        # CRC/stream integrity applies to every member, even inert previews/images.
        # Chunked reads avoid retaining those assets or trusting a decompressed size.
        for info in entries:
            read = 0
            with archive.open(info) as stream:
                while chunk := stream.read(65536):
                    read += len(chunk)
                    if read > info.file_size or read > limits.max_member_bytes:
                        _fail("member_byte_limit_exceeded")
            if read != info.file_size:
                _fail("invalid_package")
        return archive
    except BaseException:
        archive.close()
        raise


def _sections(root: Element, names: set[str], limits: HwpxLimits) -> tuple[str, ...]:
    if root.tag != _tag(_OPF, "package"):
        _fail()
    manifest = _one(root, _tag(_OPF, "manifest"))
    spine = _one(root, _tag(_OPF, "spine"))
    items: dict[str, str] = {}
    paths: set[str] = set()
    for child in manifest:
        if child.tag != _tag(_OPF, "item"):
            _fail()
        identifier = child.get("id")
        href = _path(child.get("href"))
        # Official HWPX hrefs are package-root-relative; conventional OPF relative
        # Contents paths are supported only when their exact root member is absent.
        resolved = href if href in names else str(PurePosixPath("Contents") / href)
        if not identifier or identifier in items or resolved in paths or resolved not in names:
            _fail("invalid_package")
        items[identifier] = resolved
        paths.add(resolved)
    selected: list[str] = []
    seen: set[str] = set()
    for child in spine:
        identifier = child.get("idref")
        if child.tag != _tag(_OPF, "itemref") or identifier not in items or identifier in seen:
            _fail("invalid_package")
        assert identifier is not None
        seen.add(identifier)
        linear = child.get("linear", "yes")
        if linear not in {"yes", "no"}:
            _fail("invalid_package")
        if linear == "no":
            continue
        if len(selected) >= limits.max_members:
            _fail("member_limit_exceeded")
        selected.append(items[identifier])
    if not selected:
        _fail("invalid_package")
    return tuple(selected)


# These subtrees are visual/layout/control metadata, never body evidence.
_INERT = {
    "pic",
    "shapeComment",
    "header",
    "footer",
    "secPr",
    "colPr",
    "lineSegArray",
    "linesegarray",
    "drawText",
    "rect",
    "ellipse",
    "arc",
    "polygon",
    "curve",
    "line",
    "connectLine",
    "ole",
    "equation",
    "chart",
    "video",
    "textart",
    "compose",
    "bookmark",
    "fieldBegin",
    "fieldEnd",
    "autoNum",
    "newNum",
    "pageNum",
    "pageHiding",
    "pageNumCtrl",
    "pageBorderFill",
    "footNote",
    "endNote",
}
_TABLE_META = {
    "sz",
    "pos",
    "outMargin",
    "inMargin",
    "cellzoneList",
    "cellSz",
    "cellMargin",
    "cellAddr",
    "cellSpan",
}


def _local(node: Element) -> str:
    prefix = "{" + _HP + "}"
    if not node.tag.startswith(prefix):
        _fail()
    return node.tag[len(prefix) :]


def _whitespace(node: Element) -> None:
    if node.text and node.text.strip():
        _fail()
    if any(child.tail and child.tail.strip() for child in node):
        _fail()


class _Flow:
    def __init__(self, limits: HwpxLimits) -> None:
        self.limits = limits
        self.parts: list[str] = []
        self.length = 0
        self.spans: list[HwpxTextSpan] = []
        self.fragment_text: dict[int, str] = {}
        self.tables: list[HwpxTable | None] = []
        self.sections: list[HwpxSection] = []
        self.section_index = 0
        self.section_tables = 0
        self.cells = 0
        self.grid = 0

    def append(self, text: str) -> None:
        if self.length + len(text) > self.limits.max_text_characters:
            _fail("text_limit_exceeded")
        self.parts.append(text)
        self.length += len(text)

    def emit(self, text: str, owner: tuple[str, str] | None) -> None:
        if not text:
            return
        if self.spans and self.spans[-1].section_index == self.section_index:
            self.append("\n")
        start = self.length
        self.append(text)
        self.fragment_text[start] = text
        self.spans.append(
            HwpxTextSpan(
                start,
                self.length,
                self.section_index,
                owner[0] if owner else None,
                owner[1] if owner else None,
            )
        )

    def paragraph(self, node: Element, owner: tuple[str, str] | None) -> None:
        _whitespace(node)
        pending: list[str] = []
        pending_length = 0

        def add(value: str) -> None:
            nonlocal pending_length
            pending_length += len(value)
            if pending_length + self.length > self.limits.max_text_characters:
                _fail("text_limit_exceeded")
            pending.append(value)

        def flush() -> None:
            nonlocal pending_length
            self.emit("".join(pending), owner)
            pending.clear()
            pending_length = 0

        def run(container: Element) -> None:
            _whitespace(container)
            for child in container:
                kind = _local(child)
                if kind in _INERT:
                    continue
                if kind == "t":
                    add(child.text or "")
                    for control in child:
                        control_kind = _local(control)
                        if control_kind == "lineBreak":
                            add("\n")
                        elif control_kind == "tab":
                            add("\t")
                        elif control_kind == "nbSpace":
                            add("\u00a0")
                        elif control_kind == "fwSpace":
                            add("\u3000")
                        else:
                            _fail()
                        if len(control) or (control.text and control.text.strip()):
                            _fail()
                        add(control.tail or "")
                elif kind == "tbl":
                    flush()
                    self.table(child, owner)
                elif kind == "ctrl":
                    run(child)
                else:
                    _fail()

        for child in node:
            kind = _local(child)
            if kind == "run":
                run(child)
            elif kind in _INERT:
                continue
            else:
                _fail()
        flush()

    def content(self, node: Element, owner: tuple[str, str] | None) -> None:
        _whitespace(node)
        for child in node:
            kind = _local(child)
            if kind == "p":
                self.paragraph(child, owner)
            elif kind == "tbl":
                self.table(child, owner)
            elif kind in _INERT:
                continue
            else:
                _fail()

    def table(self, node: Element, owner: tuple[str, str] | None) -> None:
        if len(self.tables) >= self.limits.max_tables:
            _fail("table_limit_exceeded")
        rows = _int(node.get("rowCnt"), self.limits.max_grid_slots, positive=True)
        cols = _int(node.get("colCnt"), self.limits.max_grid_slots, positive=True)
        slots = rows * cols
        if slots + self.grid > self.limits.max_grid_slots:
            _fail("grid_limit_exceeded")
        self.grid += slots
        occupied: set[tuple[int, int]] = set()
        index = len(self.tables)
        table_id = f"s{self.section_index}-t{self.section_tables}"
        self.section_tables += 1
        self.tables.append(None)
        start = self.length
        cells: list[HwpxCell] = []
        _whitespace(node)
        row_nodes: list[Element] = []
        for child in node:
            kind = _local(child)
            if kind == "tr":
                row_nodes.append(child)
            elif kind not in _TABLE_META:
                _fail()
        if len(row_nodes) != rows:
            _fail()
        for row_index, row_node in enumerate(row_nodes):
            _whitespace(row_node)
            for cell_node in row_node:
                if _local(cell_node) != "tc":
                    _fail()
                if self.cells >= self.limits.max_cells:
                    _fail("cell_limit_exceeded")
                self.cells += 1
                _whitespace(cell_node)
                addr = _one(cell_node, _tag(_HP, "cellAddr"))
                span = _one(cell_node, _tag(_HP, "cellSpan"))
                row = _int(addr.get("rowAddr"), rows)
                col = _int(addr.get("colAddr"), cols)
                rs = _int(span.get("rowSpan"), rows, positive=True)
                cs = _int(span.get("colSpan"), cols, positive=True)
                if row != row_index or row + rs > rows or col + cs > cols:
                    _fail()
                for r in range(row, row + rs):
                    for c in range(col, col + cs):
                        if (r, c) in occupied:
                            _fail()
                        occupied.add((r, c))
                cell_id = f"{table_id}-r{row}-c{col}"
                sublist = _one(cell_node, _tag(_HP, "subList"))
                for child in cell_node:
                    if _local(child) not in _TABLE_META | {"subList"}:
                        _fail()
                first = len(self.spans)
                self.content(sublist, (table_id, cell_id))
                own = tuple(
                    HwpxSpan(s.start, s.end) for s in self.spans[first:] if s.cell_id == cell_id
                )
                # Avoid flattening nested cell text into an enclosing cell.
                text = "\n".join(self.fragment_text[s.start] for s in own)
                cells.append(HwpxCell(cell_id, row, col, rs, cs, text, own))
        if len(occupied) != slots:
            _fail()
        self.tables[index] = HwpxTable(
            table_id,
            self.section_index,
            rows,
            cols,
            owner[1] if owner else None,
            start,
            self.length,
            tuple(cells),
        )


def _number(value: object, maximum: int, *, positive: bool = False) -> bool:
    return type(value) is int and (1 if positive else 0) <= value <= maximum


def _validate_result(result: HwpxExtraction) -> None:
    try:
        if type(result) is not HwpxExtraction:
            raise ValueError
        _limits(result.limits)
        limits = result.limits
        if (
            type(result.text) is not str
            or not result.text.strip()
            or len(result.text) > limits.max_text_characters
            or not _hash(result.raw_sha256)
            or not _hash(result.text_sha256)
            or not _number(result.raw_bytes, limits.max_raw_bytes, positive=True)
            or result.text_sha256 != sha256(result.text.encode("utf-8")).hexdigest()
            or (result.parser_name, result.parser_version, result.normalization_profile)
            != (_NAME, _VERSION, _PROFILE)
        ):
            raise ValueError
        if (
            type(result.sections) is not tuple
            or type(result.spans) is not tuple
            or type(result.tables) is not tuple
            or not 0 < len(result.sections) <= limits.max_sections
            or len(result.spans) > limits.max_nodes
            or len(result.tables) > limits.max_tables
        ):
            raise ValueError
        previous = 0
        members: set[str] = set()
        for i, section in enumerate(result.sections):
            if (
                type(section) is not HwpxSection
                or type(section.section_index) is not int
                or section.section_index != i
                or section.member_name in members
                or not _number(section.start, len(result.text))
                or not _number(section.end, len(result.text))
                or section.start > section.end
            ):
                raise ValueError
            _path(section.member_name)
            if section.start != previous + (len(_SECTION_BREAK) if i else 0):
                raise ValueError
            if i and result.text[previous : section.start] != _SECTION_BREAK:
                raise ValueError
            previous = section.end
            members.add(section.member_name)
        if previous != len(result.text):
            raise ValueError
        span_map: dict[tuple[str, str], list[HwpxSpan]] = {}
        by_section: dict[int, list[HwpxTextSpan]] = {}
        previous = -1
        for span in result.spans:
            if (
                type(span) is not HwpxTextSpan
                or not _number(span.section_index, len(result.sections) - 1)
                or not _number(span.start, len(result.text))
                or not _number(span.end, len(result.text), positive=True)
                or span.end <= span.start
                or span.start < previous
            ):
                raise ValueError
            section = result.sections[span.section_index]
            if span.start < section.start or span.end > section.end:
                raise ValueError
            if span.table_id is None:
                if span.cell_id is not None:
                    raise ValueError
            elif type(span.table_id) is not str or type(span.cell_id) is not str:
                raise ValueError
            else:
                span_map.setdefault((span.table_id, span.cell_id), []).append(
                    HwpxSpan(span.start, span.end)
                )
            by_section.setdefault(span.section_index, []).append(span)
            previous = span.end
        for section in result.sections:
            spans = by_section.get(section.section_index, [])
            previous = section.start
            for i, span in enumerate(spans):
                if span.start != previous + (1 if i else 0):
                    raise ValueError
                if i and result.text[previous : span.start] != "\n":
                    raise ValueError
                previous = span.end
            if previous != section.end:
                raise ValueError
        table_counts: dict[int, int] = {}
        all_cells: dict[str, tuple[HwpxTable, HwpxCell]] = {}
        total_cells = total_grid = 0
        for table in result.tables:
            if (
                type(table) is not HwpxTable
                or not _number(table.section_index, len(result.sections) - 1)
                or not _number(table.row_count, limits.max_grid_slots, positive=True)
                or not _number(table.column_count, limits.max_grid_slots, positive=True)
                or type(table.cells) is not tuple
                or not _number(table.start, len(result.text))
                or not _number(table.end, len(result.text))
                or table.end < table.start
            ):
                raise ValueError
            index = table_counts.get(table.section_index, 0)
            if table.table_id != f"s{table.section_index}-t{index}":
                raise ValueError
            table_counts[table.section_index] = index + 1
            section = result.sections[table.section_index]
            if table.start < section.start or table.end > section.end:
                raise ValueError
            total_grid += table.row_count * table.column_count
            total_cells += len(table.cells)
            if total_grid > limits.max_grid_slots or total_cells > limits.max_cells:
                raise ValueError
            occupied: set[tuple[int, int]] = set()
            previous_address = (-1, -1)
            for cell in table.cells:
                if (
                    type(cell) is not HwpxCell
                    or type(cell.cell_id) is not str
                    or type(cell.text) is not str
                    or type(cell.spans) is not tuple
                    or not _number(cell.row, table.row_count - 1)
                    or not _number(cell.column, table.column_count - 1)
                    or not _number(cell.row_span, table.row_count, positive=True)
                    or not _number(cell.column_span, table.column_count, positive=True)
                    or cell.row + cell.row_span > table.row_count
                    or cell.column + cell.column_span > table.column_count
                    or cell.cell_id != f"{table.table_id}-r{cell.row}-c{cell.column}"
                    or cell.cell_id in all_cells
                    or (cell.row, cell.column) <= previous_address
                ):
                    raise ValueError
                previous_address = (cell.row, cell.column)
                for row in range(cell.row, cell.row + cell.row_span):
                    for col in range(cell.column, cell.column + cell.column_span):
                        if (row, col) in occupied:
                            raise ValueError
                        occupied.add((row, col))
                if len(cell.spans) > limits.max_nodes or any(
                    type(span) is not HwpxSpan
                    or not _number(span.start, len(result.text))
                    or not _number(span.end, len(result.text), positive=True)
                    or span.end <= span.start
                    for span in cell.spans
                ):
                    raise ValueError
                expected = tuple(span_map.pop((table.table_id, cell.cell_id), []))
                if (
                    cell.spans != expected
                    or any(span.start < table.start or span.end > table.end for span in expected)
                    or cell.text != "\n".join(result.text[s.start : s.end] for s in expected)
                ):
                    raise ValueError
                all_cells[cell.cell_id] = (table, cell)
            if len(occupied) != table.row_count * table.column_count:
                raise ValueError
        if span_map:
            raise ValueError
        for table in result.tables:
            if table.parent_cell_id is not None:
                if type(table.parent_cell_id) is not str or table.parent_cell_id not in all_cells:
                    raise ValueError
                parent, _ = all_cells[table.parent_cell_id]
                if (
                    parent is table
                    or parent.section_index != table.section_index
                    or parent.start > table.start
                    or parent.end < table.end
                    or result.tables.index(parent) >= result.tables.index(table)
                ):
                    raise ValueError
    except (AuditError, ValueError, TypeError, AttributeError, UnicodeError, KeyError):
        _fail("invalid_result")


def extract_hwpx(
    raw: bytes, *, expected_sha256: str, limits: HwpxLimits | None = None
) -> HwpxExtraction:
    """Extract an already acquired snapshot; never fetch or interpret embedded instructions."""
    limits = HwpxLimits() if limits is None else limits
    _limits(limits)
    if type(raw) is not bytes or not raw:
        _fail("invalid_raw")
    if not _hash(expected_sha256):
        raise AuditError("invalid_expected_sha256")
    if len(raw) > limits.max_raw_bytes:
        _fail("raw_byte_limit_exceeded")
    raw_hash = sha256(raw).hexdigest()
    if raw_hash != expected_sha256:
        _fail("hash_mismatch")
    xml = _Xml(limits)
    flow = _Flow(limits)
    try:
        with _zip(raw, limits) as archive:
            if archive.read("mimetype") != b"application/hwp+zip":
                _fail("invalid_package")
            names = set(archive.namelist())
            if "META-INF/manifest.xml" in names:
                encryption = xml.parse(archive.read("META-INF/manifest.xml"))
                for node in encryption.iter():
                    if node.tag.rsplit("}", 1)[-1] in {"encryption-data", "encrypted-key"}:
                        _fail("encrypted")
            selected = _sections(xml.parse(archive.read("Contents/content.hpf")), names, limits)
            nonbody_roots = {
                "Contents/header.xml": _tag("http://www.hancom.co.kr/hwpml/2011/head", "head"),
                "settings.xml": _tag(
                    "http://www.hancom.co.kr/hwpml/2011/app", "HWPApplicationSetting"
                ),
                "Contents/settings.xml": _tag(
                    "http://www.hancom.co.kr/hwpml/2011/app", "HWPApplicationSetting"
                ),
            }
            for member in selected:
                root = xml.parse(archive.read(member))
                if member in nonbody_roots:
                    if root.tag != nonbody_roots[member]:
                        _fail()
                    continue
                if root.tag != _tag(_SEC, "sec"):
                    _fail()
                i = len(flow.sections)
                if i >= limits.max_sections:
                    _fail("section_limit_exceeded")
                flow.section_index = i
                flow.section_tables = 0
                if i:
                    flow.append(_SECTION_BREAK)
                start = flow.length
                flow.content(root, None)
                flow.sections.append(HwpxSection(i, member, start, flow.length))
    except (
        BadZipFile,
        KeyError,
        OSError,
        RuntimeError,
        EOFError,
        struct.error,
        ValueError,
        ZlibError,
    ):
        _fail("invalid_package")
    text = "".join(flow.parts)
    if not text.strip():
        _fail("empty_text")
    tables = tuple(table for table in flow.tables if table is not None)
    return HwpxExtraction(
        text,
        raw_hash,
        len(raw),
        sha256(text.encode("utf-8")).hexdigest(),
        tuple(flow.sections),
        tuple(flow.spans),
        tables,
        limits,
    )


def to_hwpx_representation(
    extraction: HwpxExtraction, *, representation_id: UUID, document_version_id: UUID
) -> ParsedRepresentation:
    """Map exact text/cells into existing contracts; units, periods and pages stay unset."""
    _validate_result(extraction)
    try:
        if type(representation_id) is not UUID or type(document_version_id) is not UUID:
            raise ValueError
        return ParsedRepresentation(
            representation_id=representation_id,
            document_version_id=document_version_id,
            text=extraction.text,
            text_sha256=extraction.text_sha256,
            pages=(),
            parser_name=_NAME,
            parser_version=_VERSION,
            normalization_profile=_PROFILE,
            tables=tuple(
                ParsedTable(
                    table_id=table.table_id,
                    cells=tuple(
                        TableCell(cell_id=cell.cell_id, text=cell.text) for cell in table.cells
                    ),
                )
                for table in extraction.tables
            ),
        )
    except (ValidationError, ValueError, TypeError, UnicodeError):
        _fail("invalid_representation")


def _representation(value: ParsedRepresentation) -> ParsedRepresentation:
    try:
        if type(value) is not ParsedRepresentation:
            raise ValueError
        # Bound containers/text before model_dump recursively copies caller objects.
        if (
            type(value.text) is not str
            or len(value.text) > 1_000_000
            or type(value.pages) is not tuple
            or value.pages
            or type(value.tables) is not tuple
            or len(value.tables) > 2000
            or any(
                type(v) is not str or len(v) > 64
                for v in (value.parser_name, value.parser_version, value.normalization_profile)
            )
        ):
            raise ValueError
        cell_count = text_count = 0
        for table in value.tables:
            if (
                type(table) is not ParsedTable
                or type(table.cells) is not tuple
                or type(table.table_id) is not str
                or len(table.table_id) > 96
            ):
                raise ValueError
            cell_count += len(table.cells)
            if cell_count > 40_000:
                raise ValueError
            for cell in table.cells:
                if (
                    type(cell) is not TableCell
                    or type(cell.text) is not str
                    or type(cell.cell_id) is not str
                    or len(cell.cell_id) > 96
                ):
                    raise ValueError
                text_count += len(cell.text)
                if text_count > 1_000_000:
                    raise ValueError
                if any(
                    getattr(cell, field) is not None
                    for field in (
                        "unit",
                        "period",
                        "question",
                        "population",
                        "methodology",
                        "sample_size",
                        "weighting",
                    )
                ):
                    raise ValueError
        validated = ParsedRepresentation.model_validate(value.model_dump(warnings=False))
        if (validated.parser_name, validated.parser_version, validated.normalization_profile) != (
            _NAME,
            _VERSION,
            _PROFILE,
        ) or not validated.text.strip():
            raise ValueError
        for table in validated.tables:
            if not re.fullmatch(r"s[0-9]+-t[0-9]+", table.table_id):
                raise ValueError
            for cell in table.cells:
                if not re.fullmatch(re.escape(table.table_id) + r"-r[0-9]+-c[0-9]+", cell.cell_id):
                    raise ValueError
                cell.text.encode("utf-8")
        return validated
    except (ValidationError, ValueError, TypeError, AttributeError, UnicodeError):
        _fail("invalid_representation")


def locate_hwpx_quote(
    representation: ParsedRepresentation, *, quote: str, start: int | None = None
) -> TextQuoteSelector:
    """Return an exact Unicode interval; repeated quotes require an explicit start."""
    validated = _representation(representation)
    try:
        if type(quote) is not str or not quote.strip() or len(quote) > len(validated.text):
            raise ValueError
        quote.encode("utf-8")
    except (ValueError, UnicodeError):
        raise AuditError("invalid_quote") from None
    if start is not None and (type(start) is not int or start < 0):
        raise AuditError("invalid_quote_start")
    text = validated.text
    if start is None:
        start = text.find(quote)
        if start < 0:
            raise AuditError("quote_not_found")
        if text.find(quote, start + 1) >= 0:
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


def locate_hwpx_cell(
    representation: ParsedRepresentation, *, table_id: str, cell_id: str
) -> TableCellSelector:
    """Select complete exact cell text, including literal unit/period wording."""
    validated = _representation(representation)
    if (
        type(table_id) is not str
        or type(cell_id) is not str
        or len(table_id) > 96
        or len(cell_id) > 96
    ):
        _fail("invalid_cell_selector")
    for table in validated.tables:
        if table.table_id == table_id:
            for cell in table.cells:
                if cell.cell_id == cell_id:
                    return TableCellSelector(table_id=table_id, cell_id=cell_id, quote=cell.text)
    _fail("cell_not_found")
