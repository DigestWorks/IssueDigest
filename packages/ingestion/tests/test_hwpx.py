"""Synthetic HWPX snapshots exercise extraction and exact evidence boundaries."""

from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from uuid import UUID
from zipfile import ZIP_DEFLATED, ZipFile

import issuedigest_ingestion as api
import pytest
from issuedigest_domain.citations import Citation, validate_citation

SEC = "http://www.hancom.co.kr/hwpml/2011/section"
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
OPF = "http://www.idpf.org/2007/opf/"


def paragraph(text: str) -> str:
    return f"<hp:p><hp:run><hp:t>{text}</hp:t></hp:run></hp:p>"


def cell(text: str, row: int = 0, col: int = 0, rowspan: int = 1, colspan: int = 1) -> str:
    return (
        f'<hp:tc><hp:cellAddr rowAddr="{row}" colAddr="{col}"/>'
        f'<hp:cellSpan rowSpan="{rowspan}" colSpan="{colspan}"/>'
        f"<hp:subList>{text}</hp:subList></hp:tc>"
    )


def table(cells: str, rows: int = 1, cols: int = 1) -> str:
    return f'<hp:tbl rowCnt="{rows}" colCnt="{cols}"><hp:tr>{cells}</hp:tr></hp:tbl>'


def section(body: str) -> str:
    return f'<hs:sec xmlns:hs="{SEC}" xmlns:hp="{HP}">{body}</hs:sec>'


def package(
    bodies: tuple[str, ...], *, hpf: str | None = None, extras: dict[str, bytes] | None = None
) -> bytes:
    if hpf is None:
        manifest = '<opf:item id="head" href="Contents/header.xml" media-type="application/xml"/>'
        manifest += "".join(
            f'<opf:item id="s{i}" href="Contents/section{i}.xml" media-type="application/xml"/>'
            for i in range(len(bodies))
        )
        spine = '<opf:itemref idref="head" linear="no"/>'
        spine += "".join(f'<opf:itemref idref="s{i}"/>' for i in reversed(range(len(bodies))))
        hpf = (
            f'<opf:package xmlns:opf="{OPF}"><opf:manifest>{manifest}</opf:manifest>'
            f"<opf:spine>{spine}</opf:spine></opf:package>"
        )
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", b"application/hwp+zip")
        archive.writestr("Contents/content.hpf", hpf)
        archive.writestr(
            "Contents/header.xml", b'<hh:head xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head"/>'
        )
        for i, body in enumerate(bodies):
            archive.writestr(f"Contents/section{i}.xml", section(body))
        for name, value in (extras or {}).items():
            archive.writestr(name, value)
    return out.getvalue()


def function(name: str):  # type: ignore[no-untyped-def]
    fn = getattr(api, name, None)
    assert callable(fn), f"missing public HWPX boundary: {name}"
    return fn


def extract(raw: bytes, **kwargs):  # type: ignore[no-untyped-def]
    return function("extract_hwpx")(raw, expected_sha256=sha256(raw).hexdigest(), **kwargs)


def representation(result):  # type: ignore[no-untyped-def]
    return function("to_hwpx_representation")(
        result,
        document_version_id=UUID("11111111-1111-4111-8111-111111111111"),
        representation_id=UUID("22222222-2222-4222-8222-222222222222"),
    )


def test_spine_mixed_flow_unicode_and_nested_cells_have_exact_distinct_evidence():
    # Losing after-table text, normalizing Unicode, or merging nested cell ownership is a bug.
    nested = table(cell(paragraph("중첩")))
    outer = table(
        cell(
            paragraph("단위: 억원😀 e\u0301")
            + "<hp:p><hp:run>"
            + nested
            + "<hp:t>2026~2028년</hp:t></hp:run></hp:p>",
            colspan=2,
        ),
        cols=2,
    )
    raw = package(
        (
            paragraph("뒤 구역"),
            "<hp:p><hp:run><hp:t>앞</hp:t>"
            + outer
            + "<hp:t>뒤</hp:t><hp:pic><hp:t>그림지시</hp:t></hp:pic></hp:run></hp:p>",
        )
    )
    result = extract(raw)
    assert result.text == "앞\n단위: 억원😀 e\u0301\n중첩\n2026~2028년\n뒤\n\f\n뒤 구역"
    assert result == extract(raw)
    assert result.tables[0].cells[0].text == "단위: 억원😀 e\u0301\n2026~2028년"
    assert (result.tables[0].cells[0].row, result.tables[0].cells[0].column_span) == (0, 2)
    assert result.tables[1].parent_cell_id == result.tables[0].cells[0].cell_id
    assert result.tables[1].cells[0].text == "중첩"
    rep = representation(result)
    assert rep.pages == ()
    assert rep.tables[0].cells[0].unit is None and rep.tables[0].cells[0].period is None
    selectors = [
        function("locate_hwpx_quote")(rep, quote="😀 e\u0301"),
        function("locate_hwpx_cell")(
            rep, table_id=rep.tables[0].table_id, cell_id=rep.tables[0].cells[0].cell_id
        ),
    ]
    assert (selectors[0].start, selectors[0].end) == (8, 12)
    for selector in selectors:
        anchor = validate_citation(
            Citation(
                citation_id=UUID("33333333-3333-4333-8333-333333333333"),
                representation_id=rep.representation_id,
                document_version_id=rep.document_version_id,
                selector=selector,
            ),
            rep,
        )
        assert (anchor.anchor_status, anchor.support_status) == ("matched", "not_evaluated")


@pytest.mark.parametrize(
    "body",
    [
        "<hp:p><hp:run><hp:unknown><hp:t>소실</hp:t></hp:unknown></hp:run></hp:p>",
        "<hp:p><hp:run><hp:t>앞</hp:t></hp:run>",
        '<hp:p xmlns:hp="wrong"><hp:run><hp:t>위장</hp:t></hp:run></hp:p>',
        table(cell(paragraph("A")) + cell(paragraph("B"))),
        table(cell(paragraph("A"), col=1)),
        table(cell(paragraph("A"), rowspan=2)),
        table(cell(paragraph("A")), rows=1000000),
        '<!DOCTYPE sec [<!ENTITY x "누출">]>' + paragraph("&x;"),
    ],
)
def test_rejects_evidence_loss_and_unbounded_or_overlapping_geometry(body):
    with pytest.raises(api.AuditError) as error:
        extract(package((body,)))
    assert str(error.value).startswith("hwpx_")
    assert "누출" not in str(error.value)


def test_packaging_refs_paths_duplicates_hash_and_corruption_are_fixed_errors():
    raw = package((paragraph("본문"),))
    with pytest.raises(api.AuditError, match="^hwpx_hash_mismatch$"):
        function("extract_hwpx")(raw, expected_sha256="0" * 64)
    bad_hpf = f'<opf:package xmlns:opf="{OPF}"><opf:manifest><opf:item id="s" '
    for href in [
        "../secret",
        "/Contents/section0.xml",
        "https://evil/section0.xml",
        "Contents/missing.xml",
    ]:
        hpf = (
            bad_hpf + f'href="{href}"/></opf:manifest><opf:spine>'
            '<opf:itemref idref="s"/></opf:spine></opf:package>'
        )
        with pytest.raises(api.AuditError):
            extract(package((paragraph("본문"),), hpf=hpf))
    with pytest.raises(api.AuditError):
        extract(raw[:-10])
    with pytest.raises(api.AuditError):
        extract(package((paragraph("본문"),), extras={"../secret": b"inert"}))


def test_limits_checked_at_raw_xml_text_members_sections_cells_and_grid_boundaries():
    raw = package((paragraph("한글😀"),))
    limits = function("HwpxLimits")
    for options in [
        dict(max_raw_bytes=len(raw) - 1),
        dict(max_member_bytes=2),
        dict(max_total_bytes=10),
        dict(max_members=2),
        dict(max_nodes=2),
        dict(max_depth=2),
        dict(max_text_characters=2),
    ]:
        with pytest.raises(api.AuditError):
            extract(raw, limits=limits(**options))
    for body, options in [
        (table(cell(paragraph("A")) + cell(paragraph("B"), col=1), cols=2), dict(max_cells=1)),
        (table(cell(paragraph("A"), colspan=2), cols=2), dict(max_grid_slots=1)),
        (table(cell(paragraph("A"))), dict(max_tables=1)),
    ]:
        bodies = (body, body) if "max_tables" in options else (body,)
        with pytest.raises(api.AuditError):
            extract(package(bodies), limits=limits(**options))
    with pytest.raises(api.AuditError):
        extract(package((paragraph("A"), paragraph("B"))), limits=limits(max_sections=1))
    with pytest.raises(api.AuditError):
        extract(raw, limits=limits(max_raw_bytes=True))


def test_empty_cells_inert_controls_and_explicit_duplicate_quote_locations():
    result = extract(
        package(
            (
                paragraph("반복 반복")
                + table(cell(""))
                + "<hp:p><hp:run><hp:ctrl><hp:header>"
                + paragraph("비본문")
                + "</hp:header></hp:ctrl></hp:run></hp:p>",
            )
        )
    )
    assert result.text == "반복 반복"
    assert result.tables[0].cells[0].text == ""
    rep = representation(result)
    with pytest.raises(api.AuditError, match="^quote_ambiguous$"):
        function("locate_hwpx_quote")(rep, quote="반복")
    selector = function("locate_hwpx_quote")(rep, quote="반복", start=3)
    assert (selector.start, selector.end) == (3, 5)
    with pytest.raises(api.AuditError):
        function("locate_hwpx_quote")(rep, quote="반복", start=True)


def test_revalidates_mutated_extraction_limits_representation_and_caller_ids():
    result = extract(package((table(cell(paragraph("원문"))),)))
    invalid = replace(result.tables[0].cells[0], row=10)
    forged = replace(result.tables[0], cells=(invalid,))
    with pytest.raises(api.AuditError):
        representation(replace(result, tables=(forged,)))
    object.__setattr__(result.limits, "max_text_characters", True)
    with pytest.raises(api.AuditError):
        representation(result)
    result = extract(package((paragraph("원문"),)))
    with pytest.raises(api.AuditError, match="^hwpx_invalid_representation$"):
        function("to_hwpx_representation")(
            result, representation_id="secret", document_version_id=UUID(int=1)
        )
    rep = representation(result)
    bad = rep.model_copy(update={"text": "secret"})
    with pytest.raises(api.AuditError, match="^hwpx_invalid_representation$"):
        function("locate_hwpx_quote")(bad, quote="secret")


def test_rejects_zip_count_forgery_duplicate_members_and_encryption_metadata():
    import struct
    from warnings import catch_warnings, simplefilter

    raw = package((paragraph("본문"),))
    forged = bytearray(raw)
    end = forged.rfind(b"PK\x05\x06")
    struct.pack_into("<HH", forged, end + 8, 1, 1)
    with pytest.raises(api.AuditError, match="^hwpx_member_limit_exceeded$"):
        extract(bytes(forged), limits=function("HwpxLimits")(max_members=2))
    out = BytesIO()
    with catch_warnings():
        simplefilter("ignore", UserWarning)
        with ZipFile(out, "w") as archive:
            archive.writestr("mimetype", b"application/hwp+zip")
            archive.writestr("mimetype", b"application/hwp+zip")
    with pytest.raises(api.AuditError):
        extract(out.getvalue())
    encrypted = package(
        (paragraph("본문"),),
        extras={"META-INF/manifest.xml": b"<manifest><encryption-data/></manifest>"},
    )
    with pytest.raises(api.AuditError, match="^hwpx_encrypted$"):
        extract(encrypted)


def test_multirow_merged_coordinates_and_inline_controls_preserve_literal_text():
    body = (
        '<hp:tbl rowCnt="2" colCnt="2"><hp:tr>'
        + cell(paragraph("병합"), rowspan=2)
        + cell(paragraph("위"), col=1)
        + "</hp:tr><hp:tr>"
        + cell(paragraph("아래"), row=1, col=1)
        + "</hp:tr></hp:tbl>"
    )
    result = extract(package((body + paragraph("A<hp:tab/>B<hp:lineBreak/>C"),)))
    assert result.text == "병합\n위\n아래\nA\tB\nC"
    assert [(c.row, c.column, c.row_span, c.column_span) for c in result.tables[0].cells] == [
        (0, 0, 2, 1),
        (0, 1, 1, 1),
        (1, 1, 1, 1),
    ]
    for cell_value in result.tables[0].cells:
        assert all(result.text[s.start : s.end] == cell_value.text for s in cell_value.spans)


def test_bounds_caller_forgery_before_recursive_serialization_and_result_iteration():
    result = extract(package((table(cell(paragraph("A"))),)))
    bad_cell = replace(result.tables[0].cells[0], spans=(api.HwpxSpan(0, True),))
    with pytest.raises(api.AuditError):
        representation(replace(result, tables=(replace(result.tables[0], cells=(bad_cell,)),)))
    rep = representation(result)
    giant = (
        rep.tables[0].cells[0].model_copy(update={"cell_id": "s0-t0-r" + "0" * 1_000_001 + "-c0"})
    )
    bad = rep.model_copy(update={"tables": (rep.tables[0].model_copy(update={"cells": (giant,)}),)})
    with pytest.raises(api.AuditError, match="^hwpx_invalid_representation$"):
        function("locate_hwpx_quote")(bad, quote="A")


def test_official_header_without_linear_flag_is_inert_and_body_spine_order_is_kept():
    hpf = f'''<opf:package xmlns:opf="{OPF}"><opf:manifest>
    <opf:item id="h" href="Contents/header.xml"/>
    <opf:item id="s0" href="Contents/section0.xml"/>
    <opf:item id="s1" href="Contents/section1.xml"/>
    </opf:manifest><opf:spine><opf:itemref idref="h"/>
    <opf:itemref idref="s1"/><opf:itemref idref="s0"/></opf:spine></opf:package>'''
    raw = package((paragraph("첫 파일"), paragraph("먼저 본문")), hpf=hpf)
    result = extract(raw, limits=function("HwpxLimits")(max_sections=2))
    assert result.text == "먼저 본문\n\f\n첫 파일"
    assert [s.member_name for s in result.sections] == [
        "Contents/section1.xml",
        "Contents/section0.xml",
    ]


def test_nul_zip_member_names_do_not_silently_truncate_to_safe_names():
    raw = package((paragraph("본문"),), extras={"picxures": b"inert"})
    raw = raw.replace(b"picxures", b"pic\x00ures")
    with pytest.raises(api.AuditError, match="^hwpx_invalid_package$"):
        extract(raw)
