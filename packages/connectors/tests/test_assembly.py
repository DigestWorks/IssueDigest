"""Public synthetic HTML only: network is replaced below the bounded HTTP client."""

import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs

import httpx2 as httpx
import pytest

BILL = "SYNTHETIC_01"
URL = "https://likms.assembly.go.kr/bill/bi/billDetailPage.do?billId=SYNTHETIC_01"
AT = datetime(2026, 10, 16, tzinfo=UTC)
GET = (
    '<html><head><meta name="_csrf" content="SYNTHETIC-TOKEN"></head><body>'
    '<form id="form" action="https://untrusted.test/ignored">'
    '<input name="billId" value="SYNTHETIC_01"><input name="mode" value="read">'
    "</form><h1>합성법안</h1><p>1234567</p></body></html>"
)
POST = '<div id="prntSummary"><p>제안 이유😀 &amp; e\u0301</p><p>주요<br>내용</p></div>'


def sdk():
    path = Path(__file__).parents[1] / "src/issuedigest_connectors/__init__.py"
    assert path.is_file(), "missing Assembly connector SDK"
    return importlib.import_module("issuedigest_connectors")


def fetch(get=GET, post=POST, handler=None):
    requests = []

    def respond(request):
        requests.append(request)
        if handler:
            return handler(request, len(requests))
        return httpx.Response(
            200,
            content=(get if len(requests) == 1 else post).encode(),
            headers={
                "content-type": "text/html; charset=UTF-8",
                "set-cookie": "session=synthetic; Path=/",
            },
        )

    result = sdk().capture_assembly(BILL, collected_at=AT, transport=httpx.MockTransport(respond))
    return result, requests


def test_capture_uses_exact_origin_cookie_csrf_and_two_bounded_requests():
    capture, requests = fetch()
    assert [(r.method, str(r.url)) for r in requests] == [
        ("GET", URL),
        ("POST", "https://likms.assembly.go.kr/bill/bi/bill/detail/billInfo.do"),
    ]
    assert requests[1].headers["cookie"] == "session=synthetic"
    assert requests[1].headers["x-csrf-token"] == "SYNTHETIC-TOKEN"
    assert requests[1].headers["referer"] == URL
    assert requests[1].headers["x-requested-with"] == "XMLHttpRequest"
    assert parse_qs(requests[1].content.decode()) == {"billId": [BILL], "mode": ["read"]}
    assert all(
        r.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 20.0)
        for r in requests
    )
    assert capture.detail_html == GET and capture.summary_html == POST
    assert capture.canonical_url == URL and capture.collected_at == AT
    assert (
        sdk().extract_assembly_summary(capture.summary_html) == "제안 이유😀 & e\u0301\n주요\n내용"
    )
    raw = sdk().serialize_capture(capture)
    assert sdk().parse_capture(raw) == capture
    assert BILL not in repr(capture) and "TOKEN" not in repr(capture)


@pytest.mark.parametrize("bill", ["", "x" * 81, "한글", "abc-1", "https://evil.test", "a?x", "a\n"])
def test_invalid_identity_rejected_before_transport(bill):
    requests = []
    with pytest.raises(sdk().AssemblyError):
        sdk().capture_assembly(
            bill, collected_at=AT, transport=httpx.MockTransport(lambda r: requests.append(r))
        )
    assert requests == []


@pytest.mark.parametrize(
    "bad",
    [
        GET.replace('id="form"', 'id="other"'),
        GET + '<form id="form"></form>',
        GET.replace('name="_csrf"', 'name="other"'),
        GET + '<meta name="_csrf" content="other">',
        GET.replace('value="SYNTHETIC_01"', 'value="OTHER"'),
        GET.replace("</form>", '<input name="billId" value="SYNTHETIC_01"></form>'),
        GET.replace("</form>", '<input name="mode" value="again"></form>'),
        GET.replace('value="read"', 'value="' + "x" * 4097 + '"'),
        GET.replace('content="SYNTHETIC-TOKEN"', 'content=""'),
        GET.replace("</form>", ""),
        GET.replace('<input name="mode"', '<form><input name="mode"'),
    ],
)
def test_ambiguous_form_or_token_fails_before_post(bad):
    seen = []

    def response(r, n):
        seen.append(n)
        return httpx.Response(200, content=bad.encode(), headers={"content-type": "text/html"})

    with pytest.raises(sdk().AssemblyError) as error:
        fetch(handler=response)
    assert seen == [1]
    assert str(error.value) == "Unable to capture Assembly source"
    assert BILL not in str(error.value)


@pytest.mark.parametrize("stage", [1, 2])
@pytest.mark.parametrize(
    "failure",
    ["redirect", "status", "type", "charset", "encoding", "utf8", "length", "stream", "transport"],
)
def test_bounded_response_failures_are_fixed_and_never_retried(stage, failure):
    seen = []

    class Large(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(34):
                yield b"x" * 65536

    def response(request, count):
        seen.append(count)
        if count != stage:
            return httpx.Response(200, content=GET.encode(), headers={"content-type": "text/html"})
        if failure == "transport":
            raise httpx.ReadTimeout("PRIVATE-MARKER", request=request)
        headers = {"content-type": "text/html"}
        if failure == "redirect":
            return httpx.Response(302, headers={"location": "https://evil.test/PRIVATE-MARKER"})
        if failure == "status":
            return httpx.Response(500)
        if failure == "type":
            headers["content-type"] = "application/json"
        if failure == "charset":
            headers["content-type"] += "; charset=euc-kr"
        if failure == "encoding":
            headers["content-encoding"] = "gzip"
        if failure == "length":
            headers["content-length"] = str(2 * 1024 * 1024 + 1)
        if failure == "stream":
            return httpx.Response(200, headers=headers, stream=Large())
        return httpx.Response(
            200, content=b"\xff" if failure == "utf8" else POST.encode(), headers=headers
        )

    with pytest.raises(sdk().AssemblyError) as error:
        fetch(handler=response)
    assert seen == list(range(1, stage + 1))
    assert str(error.value) == "Unable to capture Assembly source"


@pytest.mark.parametrize(
    "html,want",
    [
        (
            '<p>menu</p><div id="prntSummary"> A&nbsp;  B\tC\r\nD <br/> E </div><p>other</p>',
            "A B C D\nE",
        ),
        (
            '<div id="prntSummary"><script>bad</script><style>bad</style>'
            "<p>가😀e\u0301</p><p>나</p></div>",
            "가😀e\u0301\n나",
        ),
        (
            '<div id="prntSummary">one<span hidden>bad</span>'
            '<span aria-hidden="true">bad</span><span style="DISPLAY: none !important">bad</span>'
            '<span style="visibility:hidden">bad</span><template>bad</template>'
            "<noscript>bad</noscript><span inert>bad</span>two</div>",
            "onetwo",
        ),
    ],
)
def test_exact_summary_profile_excludes_nonvisible_content(html, want):
    assert sdk().extract_assembly_summary(html) == want


@pytest.mark.parametrize(
    "html",
    [
        "<div>missing</div>",
        '<div id="prntSummary"></div>',
        '<div id="prntSummary">a</div><div id="prntSummary">b</div>',
        '<div id="prntSummary">unclosed',
        '<div id="prntSummary"><p>x</div></p>',
        '<div id="prntSummary"><span>x</span></div></div>',
        '<div id="prntSummary" id="other">x</div>',
        '<div hidden><div id="prntSummary">x</div></div>',
        '<script><div id="prntSummary">x</div></script>',
        '<div id="prntSummary">' + "<span>" * 65 + "x" + "</span>" * 65 + "</div>",
        '<div id="prntSummary">' + "가" * 100001 + "</div>",
        '<div id="prntSummary"><img alt="invented"></div>',
    ],
)
def test_missing_ambiguous_malformed_or_oversize_summary_rejected(html):
    with pytest.raises(sdk().AssemblyError) as error:
        sdk().extract_assembly_summary(html)
    assert str(error.value) == "Unable to extract Assembly summary"


def test_capture_json_is_strict_bounded_and_revalidates_forged_models():
    a = sdk()
    capture, _ = fetch()
    data = json.loads(a.serialize_capture(capture))
    for changes in (
        {"schema_version": True},
        {"bill_id": "bad-"},
        {"canonical_url": "https://evil.test/"},
        {"collected_at": "2026-10-16T00:00:00"},
        {"extra": 1},
        {"detail_html": GET.replace(BILL, "OTHER")},
        {"summary_html": "x"},
    ):
        with pytest.raises(a.AssemblyError):
            a.parse_capture(json.dumps({**data, **changes}))
    raw = a.serialize_capture(capture)
    for bad in (
        raw[:-1] + b',"bill_id":"duplicate"}',
        raw[:-1] + b',"extra":NaN}',
        b"\xff",
        b" " * (8 * 1024 * 1024 + 1),
    ):
        with pytest.raises(a.AssemblyError):
            a.parse_capture(bad)
    for value in (
        capture.model_copy(update={"bill_id": "bad-"}),
        a.AssemblyCapture.model_construct(
            **{**capture.__dict__, "summary_html": "x" * (2 * 1024 * 1024 + 1)}
        ),
    ):
        with pytest.raises(a.AssemblyError):
            a.serialize_capture(value)


def test_client_does_not_use_environment_proxy_or_emit_private_http_logs(monkeypatch, caplog):
    import logging

    monkeypatch.setenv("HTTPS_PROXY", "http://invalid.test:1")
    monkeypatch.setenv("SSL_CERT_FILE", "/nonexistent/PRIVATE-MARKER")
    caplog.set_level(logging.DEBUG)

    def respond(request, count):
        # Emulate the transport log sites, including response header/debug traces.
        logging.getLogger("httpcore2.http11").debug("PRIVATE-MARKER cookie=SYNTHETIC-TOKEN")
        return httpx.Response(
            200,
            content=(GET if count == 1 else POST).encode(),
            headers={"content-type": "text/html"},
        )

    fetch(handler=respond)
    assert not caplog.records


def test_pre_summary_preserves_real_source_newlines_and_code_points():
    html = (
        '<pre id="prntSummary" class="theme_list_summary" style="height: 130px;">'
        "\r\n제안이유\r\n\r\n  e\u0301 😀 &lt;법&gt;\n주요내용<br>끝</pre>"
    )
    assert sdk().extract_assembly_summary(html) == "제안이유\ne\u0301 😀 <법>\n주요내용\n끝"


@pytest.mark.parametrize(
    "html",
    [
        '<div id="prntSummary"><p>one<div>two</div></p></div>',
        '<div id="prntSummary"><a><a>two</a></a></div>',
        '<pre id="prntSummary"><iframe>fallback</iframe>visible</pre>',
        '<pre id="prntSummary"><details><summary>show</summary>hidden</details></pre>',
    ],
)
def test_ambiguous_rendering_or_browser_repaired_nesting_fails_closed(html):
    with pytest.raises(sdk().AssemblyError):
        sdk().extract_assembly_summary(html)


def test_multiple_unrelated_forms_are_ignored_and_only_target_inputs_forwarded():
    other = '<form id="search"><input name="billId" value="OTHER"></form>'
    capture, requests = fetch(get=other + GET + other.replace('id="search"', 'id="footer"'))
    assert parse_qs(requests[1].content.decode())["billId"] == [BILL]
    assert capture.detail_html.startswith(other)


@pytest.mark.parametrize(
    "mutation", ["count", "aggregate", "token_size", "nested", "charset", "content_type_meta"]
)
def test_detail_additional_structural_and_field_limits_fail_before_post(mutation):
    extra = ""
    get = GET
    if mutation == "count":
        extra = "".join(f'<input name="field{i}" value="x">' for i in range(65))
    if mutation == "aggregate":
        extra = "".join(f'<input name="field{i}" value="' + "x" * 4000 + '">' for i in range(5))
    if mutation == "token_size":
        get = GET.replace('content="SYNTHETIC-TOKEN"', 'content="' + "x" * 4097 + '"')
    if mutation == "nested":
        get = '<form id="outside">' + GET + "</form>"
    if mutation == "charset":
        get = GET.replace("<head>", '<head><meta charset="euc-kr">')
    if mutation == "content_type_meta":
        get = GET.replace(
            "<head>", '<head><meta http-equiv="Content-Type" content="text/html; charset=euc-kr">'
        )
    get = get.replace("</form>", extra + "</form>", 1)
    seen = []

    def response(request, count):
        seen.append(count)
        return httpx.Response(200, content=get.encode(), headers={"content-type": "text/html"})

    with pytest.raises(sdk().AssemblyError):
        fetch(handler=response)
    assert seen == [1]


def test_capture_forged_oversize_graph_rejected_before_full_dump(monkeypatch):
    from pydantic import BaseModel

    capture, _ = fetch()
    capture = capture.model_copy(update={"detail_html": "x" * (2 * 1024 * 1024 + 1)})
    attempted = []

    def forbidden(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("full dump")

    monkeypatch.setattr(BaseModel, "model_dump_json", forbidden)
    with pytest.raises(sdk().AssemblyError):
        sdk().serialize_capture(capture)
    assert attempted == []


@pytest.mark.parametrize(
    "attributes",
    [
        'style="display:/**/none"',
        'style="opacity:0"',
        'style="color:transparent"',
        'class="hidden"',
        'style="white-space: normal"',
        'style="display:var(--mode)"',
    ],
)
def test_unsupported_visibility_rules_in_summary_fail_closed(attributes):
    html = f'<div id="prntSummary">visible<span {attributes}>ambiguous</span></div>'
    with pytest.raises(sdk().AssemblyError):
        sdk().extract_assembly_summary(html)


def test_concurrent_captures_keep_private_logs_suppressed_and_unrelated_logs_visible(caplog):
    import logging
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    caplog.set_level(logging.DEBUG)
    waiting, resume = Event(), Event()

    def slow_response(request, count):
        if count == 2:
            waiting.set()
            assert resume.wait(timeout=5)
            logging.getLogger("httpcore2.http11").debug("PRIVATE-MARKER after peer finished")
        return httpx.Response(
            200,
            content=(GET if count == 1 else POST).encode(),
            headers={"content-type": "text/html"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        slow = executor.submit(lambda: fetch(handler=slow_response))
        try:
            assert waiting.wait(timeout=5)
            fast = executor.submit(fetch)
            assert fast.result(timeout=5)[0].bill_id == BILL
            logging.getLogger("httpx2").info("unrelated request")
        finally:
            resume.set()
        assert slow.result(timeout=5)[0].bill_id == BILL
    assert [record.getMessage() for record in caplog.records] == ["unrelated request"]


def test_valid_main_form_ignores_bounded_malformed_trailing_footer_without_metadata():
    # The selected form and main body finish before the unrelated legacy footer.
    # No browser repair is used to derive data from this invalid nested document.
    html = GET.replace("</body>", "<footer><div><html></div>FOOTER-NOT-METADATA</footer></body>")
    capture, requests = fetch(get=html)
    assert len(requests) == 2 and capture.detail_html == html
    from issuedigest_connectors.html import detail_fields

    fields, _, display = detail_fields(html, BILL)
    assert fields["billId"] == BILL
    assert "합성법안" in display and "FOOTER-NOT-METADATA" not in display


@pytest.mark.parametrize(
    "critical",
    [
        '<form id="form"><input name="billId" value="SYNTHETIC_01"></form>',
        '<meta name="_csrf" content="second-token">',
    ],
)
def test_opaque_footer_still_rejects_duplicate_critical_selector(critical):
    html = GET.replace("</body>", "<footer><div><html></div>" + critical + "</footer></body>")
    seen = []

    def response(request, count):
        seen.append(count)
        return httpx.Response(200, content=html.encode(), headers={"content-type": "text/html"})

    with pytest.raises(sdk().AssemblyError):
        fetch(handler=response)
    assert seen == [1]


@pytest.mark.parametrize(
    "html,want",
    [
        ('<div id="prntSummary">visible<dialog>hidden</dialog></div>', "visible"),
        (
            '<div id="prntSummary">visible<datalist><option>hidden</option></datalist></div>',
            "visible",
        ),
    ],
)
def test_native_hidden_elements_never_become_summary_or_metadata(html, want):
    assert sdk().extract_assembly_summary(html) == want
    from issuedigest_connectors.html import visible_text

    assert visible_text(html) == want


@pytest.mark.parametrize(
    "html",
    [
        '<dialog id="prntSummary">hidden target</dialog>',
        '<datalist id="prntSummary"><option>hidden target</option></datalist>',
        '<dialog><div id="prntSummary">hidden ancestor</div></dialog>',
        '<datalist><div id="prntSummary">hidden ancestor</div></datalist>',
    ],
)
def test_native_hidden_context_cannot_constitute_or_contain_selected_summary(html):
    with pytest.raises(sdk().AssemblyError):
        sdk().extract_assembly_summary(html)


@pytest.mark.parametrize(
    "style", ["opacity:0", "color:transparent", "display:/**/none", "visibility:var(--state)"]
)
def test_unsupported_ancestor_visibility_fails_closed(style):
    html = f'<div style="{style}"><pre id="prntSummary">hidden ancestor</pre></div>'
    with pytest.raises(sdk().AssemblyError):
        sdk().extract_assembly_summary(html)


def test_profiled_ancestor_layout_allows_official_wrapper_and_ignores_unrelated_css_sibling():
    html = (
        '<html><div class="container bill_info" style="height: auto;">'
        '<form><div class="theme_area bill_info_div"><div class="theme_list">'
        '<pre id="prntSummary" class="theme_list_summary" style="height: 130px;">visible</pre>'
        '</div></div></form></div><div style="opacity:0">unrelated</div></html>'
    )
    assert sdk().extract_assembly_summary(html) == "visible"


@pytest.mark.parametrize("failure", ["unclosed_form", "duplicate_summary", "depth", "nodes"])
def test_opaque_footer_keeps_selected_structure_and_resource_bounds(failure):
    footer = "<footer><div><html></div>ignored</footer>"
    html = GET.replace("</body>", footer + "</body>")
    if failure == "unclosed_form":
        html = html.replace("</form>", "")
    if failure == "duplicate_summary":
        html = html.replace("<h1>", '<div id="prntSummary">placeholder</div><h1>')
        html = html.replace("ignored", '<pre id="prntSummary">another</pre>')
    if failure == "depth":
        html = html.replace("ignored", "<div>" * 65)
    if failure == "nodes":
        html = html.replace("ignored", "<br>" * 50_001)
    seen = []

    def response(request, count):
        seen.append(count)
        return httpx.Response(200, content=html.encode(), headers={"content-type": "text/html"})

    with pytest.raises(sdk().AssemblyError):
        fetch(handler=response)
    assert seen == [1]
