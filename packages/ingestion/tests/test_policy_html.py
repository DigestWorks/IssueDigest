"""Synthetic policy pages; no government article content or external requests."""

from dataclasses import FrozenInstanceError, replace
from datetime import date, datetime
from hashlib import sha256
from uuid import UUID

import issuedigest_ingestion as ingestion
import pytest
from issuedigest_domain.citations import Citation, validate_citation
from issuedigest_domain.sources import ParsedRepresentation
from pydantic import ValidationError

URL = "https://www.korea.kr/news/policyNewsView.do?newsId=123456789"
NOTICE = "이 자료는 텍스트에 한하여 공공누리 제1유형(출처표시)의 조건에 따라 이용할 수 있습니다."
VERSION = UUID("11111111-1111-4111-8111-111111111111")
REPRESENTATION = UUID("22222222-2222-4222-8222-222222222222")


def api(name: str):
    value = getattr(ingestion, name, None)
    assert callable(value), f"{name} must expose official policy HTML behavior"
    return value


def page(body: str = "<p>한글😀é repeat</p><p>repeat tail</p>") -> bytes:
    return (
        '<!doctype html><html><head><meta property="og:url" '
        f'content="{URL}"><meta property="og:published_time" content="not-a-time">'
        '</head><body><nav>PRIVATE MENU</nav><div class="view_title"><h1>합성 정책</h1>'
        '</div><div class="variety"><div class="info">2026.10.01 '
        '<a class="gotosite">합성부<span class="tooltip">PRIVATE TOOLTIP</span></a>'
        f'</div></div><div class="view_cont">{body}</div>'
        f'<div class="kogl_wrap"><div class="type"><span>{NOTICE}</span></div></div>'
        "<aside>PRIVATE AI SUMMARY</aside></body></html>"
    ).encode()


def extract(raw: bytes | None = None, **kwargs):
    raw = page() if raw is None else raw
    return api("extract_policy_html")(
        raw, expected_sha256=sha256(raw).hexdigest(), canonical_url=URL, **kwargs
    )


def representation(body: str = "<p>한글😀é repeat</p><p>repeat tail</p>"):
    return api("to_policy_html_representation")(
        extract(page(body)), representation_id=REPRESENTATION, document_version_id=VERSION
    )


def test_extracts_normalized_paragraphs_and_verified_metadata_without_fetch(monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("external request forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    raw = b"\xef\xbb\xbf" + page(
        "<p>  한글<b>😀</b>é &amp; &#65; \r\n space<br> next\tword </p>"
        "<figure><p>PRIVATE CAPTION</p><figcaption>PRIVATE FIGCAPTION</figcaption></figure>"
        '<div class="imageWrap"><p>PRIVATE PHOTO</p></div>'
        '<p><img src="https://example.invalid/image" alt="PRIVATE ALT">'
        'tail <span class="tooltip">PRIVATE TOOLTIP</span>'
        "<script>PRIVATE SCRIPT</script><style>PRIVATE STYLE</style>"
        "<noscript>PRIVATE NOSCRIPT</noscript><template><p>PRIVATE TEMPLATE</p></template>"
        '<iframe src="https://example.invalid/">PRIVATE IFRAME</iframe></p><p> \t </p>'
    )
    result = extract(raw)
    assert result.text == "한글😀é & A space\nnext word\n\ntail"
    assert (result.source_id, result.canonical_url) == ("123456789", URL)
    assert (result.title, result.publisher, result.publication_date) == (
        "합성 정책",
        "합성부",
        date(2026, 10, 1),
    )
    assert result.attribution == f"합성부 · 대한민국 정책브리핑 · 합성 정책 · 2026-10-01 · {URL}"
    assert result.license_notice == NOTICE
    assert result.license_url == "https://www.kogl.or.kr/info/license.do"
    assert (result.raw_sha256, result.raw_bytes) == (sha256(raw).hexdigest(), len(raw))
    assert result.text_sha256 == sha256(result.text.encode()).hexdigest()
    assert (result.parser_name, result.parser_version, result.normalization_profile) == (
        "korea-policy-html",
        "1",
        "korea-policy-paragraphs-v1",
    )
    with pytest.raises(FrozenInstanceError):
        result.text = "changed"


@pytest.mark.parametrize(
    "url",
    [
        URL + "#fragment",
        URL + "&x=1",
        URL + "\n",
        URL.replace("https", "http"),
        URL.replace("www.korea.kr", "www.korea.kr:443"),
        URL.replace("www.korea.kr", "user@www.korea.kr"),
        URL.replace("www.korea.kr", "WWW.korea.kr"),
        URL.replace("newsId", "news%49d"),
        URL.replace("123456789", "１２３４５６７８９"),
        URL.replace("/news/", "/news\\"),
        1,
    ],
)
def test_canonical_url_requires_literal_supported_form(url):
    with pytest.raises(ingestion.AuditError, match="^invalid_policy_html_url$"):
        api("extract_policy_html")(
            page(), expected_sha256=sha256(page()).hexdigest(), canonical_url=url
        )


@pytest.mark.parametrize(
    ("old", "new", "error"),
    [
        (
            f'content="{URL}"',
            'content="https://example.invalid/PRIVATE"',
            "policy_html_url_mismatch",
        ),
        ('<meta property="og:url"', '<meta property="other"', "policy_html_invalid_metadata"),
        (
            "</head>",
            f'<meta property="og:url" content="{URL}"></head>',
            "policy_html_invalid_metadata",
        ),
        ("<h1>합성 정책</h1>", "<h1> </h1>", "policy_html_invalid_metadata"),
        (
            "<h1>합성 정책</h1>",
            "<h1>합성 정책</h1><h1>duplicate</h1>",
            "policy_html_invalid_metadata",
        ),
        ('class="view_title"', 'class="other"', "policy_html_invalid_metadata"),
        ("2026.10.01", "2026.02.30", "policy_html_invalid_metadata"),
        ("2026.10.01", "2026.10.01 2026.10.02", "policy_html_invalid_metadata"),
        ('class="info"', 'class="other"', "policy_html_invalid_metadata"),
        ("합성부<span", " <span", "policy_html_invalid_metadata"),
        ("</a>", '</a><a class="gotosite">duplicate</a>', "policy_html_invalid_metadata"),
        ('class="gotosite"', 'class="other"', "policy_html_invalid_metadata"),
        ('class="kogl_wrap"', 'class="other"', "policy_html_invalid_license"),
        (NOTICE, NOTICE + NOTICE, "policy_html_invalid_license"),
        (
            NOTICE,
            NOTICE.replace("텍스트에 한하여", "사진과 텍스트에"),
            "policy_html_invalid_license",
        ),
        (NOTICE, NOTICE.replace("제1유형", "제2유형"), "policy_html_invalid_license"),
        (NOTICE, NOTICE.replace("제1유형", "제3유형"), "policy_html_invalid_license"),
        (NOTICE, NOTICE.replace("제1유형", "제4유형"), "policy_html_invalid_license"),
        (NOTICE, NOTICE + " 공공누리 제2유형", "policy_html_invalid_license"),
        (NOTICE, "<script>" + NOTICE + "</script>", "policy_html_invalid_license"),
        (NOTICE, '<img alt="' + NOTICE + '">', "policy_html_invalid_license"),
        (
            "</html>",
            '<div class="kogl_wrap">' + NOTICE + "</div></html>",
            "policy_html_invalid_license",
        ),
    ],
)
def test_metadata_and_license_fail_closed(old, new, error):
    raw = page().decode().replace(old, new).encode()
    with pytest.raises(ingestion.AuditError, match=f"^{error}$"):
        extract(raw)


@pytest.mark.parametrize(
    "body",
    [
        "<table><tr><td>PRIVATE</td></tr></table><p>text</p>",
        "<p>text<ul><li>PRIVATE</li></ul></p>",
        "<ol><li>PRIVATE</li></ol><p>text</p>",
        "<div>PRIVATE outside</div><p>text</p>",
        "PRIVATE outside<p>text</p>",
        "<p>first<p>second</p></p>",
        '<p>text</p><div class="view_cont"><p>duplicate</p></div>',
    ],
)
def test_rejects_unsupported_or_ambiguous_body(body):
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_structure$"):
        extract(page(body))


@pytest.mark.parametrize("marker", ["</p>", "</h1>", "</a>", "</head>", "</div>"])
def test_rejects_truncated_selected_subtrees(marker):
    raw = page()
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_structure$"):
        extract(raw[: raw.index(marker.encode())])


def test_ignores_unrelated_html_errors_and_normalizes_notice_markup():
    raw = page().decode().replace("<nav>PRIVATE MENU</nav>", "<nav><b>menu</nav>")
    raw = raw.replace(NOTICE, NOTICE.replace("텍스트에", "<b>텍스트에</b>").replace(" ", "\n\t"))
    assert extract(raw.encode()).license_notice == NOTICE


@pytest.mark.parametrize(
    ("raw", "error"),
    [
        ("PRIVATE", "invalid_policy_html_raw"),
        (bytearray(b"PRIVATE"), "invalid_policy_html_raw"),
        (b"", "policy_html_empty_raw"),
        (b"\xffPRIVATE", "policy_html_invalid_utf8"),
        (b"PRIVATE no html", "policy_html_invalid_structure"),
    ],
)
def test_rejects_bad_raw_input(raw, error):
    digest = sha256(raw).hexdigest() if isinstance(raw, bytes) else "0" * 64
    with pytest.raises(ingestion.AuditError, match=f"^{error}$"):
        api("extract_policy_html")(raw, expected_sha256=digest, canonical_url=URL)


@pytest.mark.parametrize("digest", ["", "A" * 64, "g" * 64, "0" * 63, "0" * 64 + "\n", 1])
def test_rejects_malformed_expected_digest(digest):
    with pytest.raises(ingestion.AuditError, match="^invalid_expected_sha256$"):
        api("extract_policy_html")(page(), expected_sha256=digest, canonical_url=URL)


def test_rejects_hash_mismatch():
    with pytest.raises(ingestion.AuditError, match="^policy_html_hash_mismatch$"):
        api("extract_policy_html")(page(), expected_sha256="0" * 64, canonical_url=URL)


@pytest.mark.parametrize("field", ["max_raw_bytes", "max_text_characters", "max_depth"])
@pytest.mark.parametrize("value", [True, False, 0, -1, "1", 1.0, 9_000_000])
def test_limits_reject_bad_values(field, value):
    with pytest.raises(ingestion.AuditError, match="^invalid_policy_html_limits$"):
        api("PolicyHtmlLimits")(**{field: value})


def test_limits_reject_bypassed_instance_and_non_limits():
    limits = api("PolicyHtmlLimits")()
    object.__setattr__(limits, "max_depth", True)
    for invalid in [limits, {}, True]:
        with pytest.raises(ingestion.AuditError, match="^invalid_policy_html_limits$"):
            extract(limits=invalid)


def test_whole_result_limits_and_exact_boundaries():
    raw = page("<p>a</p><p>😀</p>")
    limits = api("PolicyHtmlLimits")(max_raw_bytes=len(raw), max_text_characters=4)
    assert extract(raw, limits=limits).text == "a\n\n😀"
    for kwargs, error in [
        ({"max_raw_bytes": len(raw) - 1}, "policy_html_byte_limit_exceeded"),
        ({"max_text_characters": 3}, "policy_html_text_limit_exceeded"),
        ({"max_depth": 3}, "policy_html_depth_limit_exceeded"),
    ]:
        with pytest.raises(ingestion.AuditError, match=f"^{error}$"):
            extract(raw, limits=api("PolicyHtmlLimits")(**kwargs))
    assert extract(page("<p>" + "<span>" * 123 + "x" + "</span>" * 123 + "</p>")).text == "x"
    with pytest.raises(ingestion.AuditError, match="^policy_html_depth_limit_exceeded$"):
        extract(page("<p>" + "<span>" * 125 + "x" + "</span>" * 125 + "</p>"))


def test_empty_paragraph_result_is_rejected():
    with pytest.raises(ingestion.AuditError, match="^policy_html_empty_text$"):
        extract(page('<p> \n </p><img alt="PRIVATE">'))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_id", "987654321"),
        ("canonical_url", URL + "#PRIVATE"),
        ("title", " "),
        ("publisher", ""),
        ("publication_date", datetime(2026, 10, 1)),
        ("attribution", "PRIVATE"),
        ("license_notice", "PRIVATE"),
        ("license_url", "https://example.invalid/"),
        ("text", "changed"),
        ("text_sha256", "0" * 64),
        ("raw_sha256", "A" * 64),
        ("raw_bytes", True),
        ("raw_bytes", 8 * 1024 * 1024 + 1),
        ("parser_name", "other"),
        ("parser_version", "2"),
        ("normalization_profile", "other"),
        ("limits", {}),
    ],
)
def test_result_constructor_and_adapter_revalidate_forged_results(field, value):
    result = extract()
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_result$"):
        replace(result, **{field: value})
    object.__setattr__(result, field, value)
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_result$"):
        api("to_policy_html_representation")(
            result, representation_id=REPRESENTATION, document_version_id=VERSION
        )


def test_adapter_preserves_contract_and_unicode_quote_support_boundary():
    rep = representation()
    assert (rep.representation_id, rep.document_version_id) == (REPRESENTATION, VERSION)
    assert (rep.pages, rep.tables) == ((), ())
    selector = api("locate_policy_html_quote")(rep, quote="😀é")
    assert (selector.start, selector.end, selector.prefix, selector.suffix) == (
        2,
        5,
        "한글",
        " repeat\n\nrepeat tail",
    )
    citation = Citation(
        citation_id=UUID("33333333-3333-4333-8333-333333333333"),
        representation_id=REPRESENTATION,
        document_version_id=VERSION,
        selector=selector,
    )
    status = validate_citation(citation, rep)
    assert (status.anchor_status, status.support_status) == ("matched", "not_evaluated")
    with pytest.raises(ValidationError):
        api("to_policy_html_representation")(
            extract(), representation_id=UUID(int=1), document_version_id=VERSION
        )


@pytest.mark.parametrize(
    ("quote", "start", "error"),
    [
        ("", None, "invalid_quote"),
        (" ", None, "invalid_quote"),
        (1, None, "invalid_quote"),
        ("\ud800", None, "invalid_quote"),
        ("repeat", None, "quote_ambiguous"),
        ("absent", None, "quote_not_found"),
        ("é", None, "quote_not_found"),
        ("repeat", 0, "quote_not_found"),
        ("repeat", 1000, "quote_not_found"),
        ("repeat", True, "invalid_quote_start"),
        ("repeat", -1, "invalid_quote_start"),
        ("repeat", 6.0, "invalid_quote_start"),
        ("repeat", "6", "invalid_quote_start"),
    ],
)
def test_exact_quote_rejects_bad_ambiguous_or_mismatching_input(quote, start, error):
    with pytest.raises(ingestion.AuditError, match=f"^{error}$"):
        api("locate_policy_html_quote")(representation(), quote=quote, start=start)


def test_overlapping_quotes_require_exact_start_and_context_is_bounded():
    rep = representation("<p>" + "x" * 90 + "aaa" + "😀" * 90 + "</p>")
    with pytest.raises(ingestion.AuditError, match="^quote_ambiguous$"):
        api("locate_policy_html_quote")(rep, quote="aa")
    selector = api("locate_policy_html_quote")(rep, quote="aa", start=91)
    assert (selector.start, selector.end) == (91, 93)
    assert selector.prefix == "x" * 79 + "a"
    assert selector.suffix == "😀" * 80


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("text_sha256", "0" * 64),
        ("parser_name", "pypdf"),
        ("parser_version", "2"),
        ("normalization_profile", "other"),
        ("pages", [{"page_number": 1, "start": 0, "end": 2}]),
        ("representation_id", UUID(int=1)),
        ("text", ""),
    ],
)
def test_locator_revalidates_bypassed_domain_models(field, value):
    rep = representation().model_copy(update={field: value})
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_representation$"):
        api("locate_policy_html_quote")(rep, quote="repeat")
    forged = ParsedRepresentation.model_construct(**rep.model_dump(warnings=False))
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_representation$"):
        api("locate_policy_html_quote")(forged, quote="repeat")


def test_invalid_representation_does_not_emit_serializer_details():
    import warnings

    rep = representation().model_copy(update={"pages": [{"PRIVATE": "PRIVATE TEXT"}]})
    with warnings.catch_warnings(record=True) as emitted:
        warnings.simplefilter("always")
        with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_representation$"):
            api("locate_policy_html_quote")(rep, quote="repeat")
    assert emitted == []


def test_license_notice_is_selected_within_wrapper_not_unrelated_rights_text():
    raw = (
        page()
        .decode()
        .replace(
            f"<span>{NOTICE}</span></div></div>",
            f'<span>{NOTICE}</span></div><div class="info">'
            '제3자 사진은 별도 허가가 필요합니다. <a href="/policy">정책 안내</a></div></div>',
        )
    )
    result = extract(raw.encode())
    assert result.license_notice == NOTICE
    assert result.text == "한글😀é repeat\n\nrepeat tail"


@pytest.mark.parametrize(
    "extra",
    [
        '<div class="info">공공누리 제2유형</div>',
        f'<div class="type"><span>{NOTICE}</span></div>',
    ],
)
def test_license_wrapper_rejects_competing_types_and_duplicate_notice(extra):
    raw = (
        page()
        .decode()
        .replace(f"<span>{NOTICE}</span></div></div>", f"<span>{NOTICE}</span></div>{extra}</div>")
    )
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_license$"):
        extract(raw.encode())


@pytest.mark.parametrize(
    ("body", "error"),
    [
        ("<p>" + "x" * 100_001 + "</p>", "policy_html_text_limit_exceeded"),
        ("<p>x</p>" + " " * (2 * 1024 * 1024), "policy_html_byte_limit_exceeded"),
    ],
)
def test_default_limits_reject_oversized_whole_input(body, error):
    with pytest.raises(ingestion.AuditError, match=f"^{error}$"):
        extract(page(body))


def test_custom_limits_allow_large_valid_result_and_are_immutable():
    limits = api("PolicyHtmlLimits")(
        max_raw_bytes=8 * 1024 * 1024, max_text_characters=1_000_000, max_depth=256
    )
    result = extract(page("<p>" + "한" * 100_001 + "</p>"), limits=limits)
    assert len(result.text) == 100_001
    assert (
        api("to_policy_html_representation")(
            result, representation_id=REPRESENTATION, document_version_id=VERSION
        ).text
        == result.text
    )
    with pytest.raises(FrozenInstanceError):
        limits.max_depth = 1


@pytest.mark.parametrize("body", ["<p>a\rb\r\nc</p>", "<div><span> </span><p>a b c</p></div>"])
def test_cr_and_whitespace_wrappers_preserve_normalized_paragraph(body):
    assert extract(page(body)).text == "a b c"


@pytest.mark.parametrize("text", [" a ", "a\tb", "a\rb", "a  b", "\na\n", "a\n b"])
def test_direct_result_rejects_unnormalized_text_even_with_matching_hash(text):
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_result$"):
        replace(extract(), text=text, text_sha256=sha256(text.encode()).hexdigest())


@pytest.mark.parametrize("body", ["<p>a<div>b</div></p>", "<p>a<h2>b</h2></p>"])
def test_block_elements_inside_paragraph_are_ambiguous(body):
    with pytest.raises(ingestion.AuditError, match="^policy_html_invalid_structure$"):
        extract(page(body))


def test_unrelated_info_class_malformed_markup_is_not_selected_metadata():
    raw = page().decode().replace("<nav>PRIVATE MENU</nav>", '<nav><div class="info">menu</nav>')
    assert extract(raw.encode()).publisher == "합성부"
