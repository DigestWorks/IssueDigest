import pytest
from issuedigest_ingestion import AuditError, LegalHtmlLimits, extract_legal_html

URL = "https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq=123456&efYd=20261002"
HTML = """<html>
<input id="lsNm" value="가상 법률">
<input id="lsiSeq" value="123456">
<input id="efYd" value="20261002">
<div id="contentBody">
<div id="conTop">
<h2>가상 법률 <span>(약칭: 가상법)</span>
</h2>
<div class="ct_sub">
<span>[시행 2026. 10. 2.] [법률 제100호, 2026. 9. 29., 일부개정]</span>
</div>
</div>
<div id="conScroll">
<p>연락처 제외</p>
<div class="lawcon">
<p class="pty1_p4">제1조(목적) 가상 본문.<button>삭제</button>
<span hidden></span>
<script>악성</script>
</p>
<p class="pty1_de2_1">① 세부 조항.</p>
</div>
<div id="arDivArea">
<p class="pty3">부칙 제100호</p>
<p class="pty3_dep1">다만, 제2조는 2027년 4월 22일부터 시행한다.</p>
</div>
</div>
</div>
</html>"""


def test_extract_preserves_future_exception_and_skips_chrome():
    result = extract_legal_html(HTML.encode(), URL)
    assert result.law_name == "가상 법률"
    assert result.effective_date.isoformat() == "2026-10-02"
    assert "2027년 4월 22일" in result.text
    assert "① 세부 조항." in result.text
    for excluded in ("연락처", "삭제", "숨김", "악성"):
        assert excluded not in result.text


@pytest.mark.parametrize(
    "before,after",
    [
        ("123456", "654321"),
        ("20261002", "20261003"),
        ('id="conScroll"', 'id="other"'),
        ("</h2>", ""),
        ('id="arDivArea"', 'id="other"'),
    ],
)
def test_rejects_mismatch_and_missing_structure(before, after):
    with pytest.raises(AuditError):
        extract_legal_html(HTML.replace(before, after).encode(), URL)


@pytest.mark.parametrize(
    "extra",
    [
        '<div id="contentBody"></div>',
        '<input id="lsiSeq" value="123456">',
        '<div id="conTop"></div>',
    ],
)
def test_duplicate_metadata_and_containers(extra):
    with pytest.raises(AuditError):
        extract_legal_html((HTML + extra).encode(), URL)


def test_bounds_and_url():
    for limits in (
        LegalHtmlLimits(max_raw_bytes=10),
        LegalHtmlLimits(max_text_characters=10),
        LegalHtmlLimits(max_depth=2),
        LegalHtmlLimits(max_text_nodes=2),
    ):
        with pytest.raises(AuditError):
            extract_legal_html(HTML.encode(), URL, limits=limits)
    with pytest.raises(AuditError):
        extract_legal_html(HTML.encode(), URL.replace("www.law.go.kr", "evil.example"))


def test_rejects_conflicting_canonical_link_and_hidden_container():
    for html in (
        HTML + '<link rel="canonical" href="https://evil.example/">',
        HTML.replace('id="conScroll"', 'id="conScroll" hidden'),
    ):
        with pytest.raises(AuditError):
            extract_legal_html(html.encode(), URL)


@pytest.mark.parametrize(
    "before,after",
    [
        ('class="pty3_dep1"', 'class="pty3_dep1" hidden'),
        ('class="lawcon"', 'class="lawcon" style="display: none"'),
        ("제1조(목적) 가상 본문.", "제1조(목적) 가상 <span hidden>아니다</span> 본문."),
        ('<div id="arDivArea">', '<div id="arDivArea"><div hidden>'),
    ],
)
def test_hidden_statutory_content_fails_closed(before, after):
    html = HTML.replace(before, after)
    if before == '<div id="arDivArea">':
        html = html.replace(
            "</div>\n</div>\n</div>\n</html>", "</div></div>\n</div>\n</div>\n</html>"
        )
    with pytest.raises(AuditError):
        extract_legal_html(html.encode(), URL)


def test_hidden_navigation_and_form_controls_are_allowed():
    html = HTML.replace(
        "<p>연락처 제외</p>",
        '<nav hidden><p>숨김 메뉴</p><input value="검색"></nav><p>연락처 제외</p>',
    ).replace("<button>삭제</button>", "<button hidden>삭제</button>")
    result = extract_legal_html(html.encode(), URL)
    assert "숨김 메뉴" not in result.text
    assert "삭제" not in result.text
    assert "2027년 4월 22일" in result.text
