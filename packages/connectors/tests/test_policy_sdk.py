"""Synthetic official-policy discovery, bounded HTTP and private artifact contracts."""

import importlib
import json
import logging
from datetime import UTC, datetime

import httpx2 as httpx
import pytest

AT = datetime(2026, 10, 16, tzinfo=UTC)
LIST_URL = "https://www.korea.kr/news/policyNewsList.do"
URL = "https://www.korea.kr/news/policyNewsView.do?newsId=123456789"


def sdk():
    module = importlib.import_module("issuedigest_connectors")
    assert callable(getattr(module, "discover_policy", None)), "missing policy discovery SDK"
    return module


def entry(identity="123456789", title="합성 정책", href=None):
    href = href or f"/news/policyNewsView.do?newsId={identity}"
    return (
        f'<li><a href="{href}" onclick="PRIVATE-IGNORE">'
        '<span class="thumb"><img src="https://untrusted.test/PRIVATE"></span>'
        f'<span class="text"><strong>{title}</strong><span class="lead">NOT EVIDENCE</span>'
        '<span class="source"><span>2026.10.16</span><span>합성부</span></span>'
        "</span></a></li>"
    )


def listing(entries=None):
    return (
        '<html><head><meta charset="utf-8"></head><body>'
        '<a href="/news/policyNewsView.do?newsId=999999999">HERO</a>'
        '<div class="list_type"><form>search</form></div>'
        '<div class="article_body"><div class="list_type"><ul>'
        + (entry() + entry() + entry("234567890") if entries is None else entries)
        + "</ul></div></div><footer><a "
        'href="/news/policyNewsView.do?newsId=888888888">FOOTER</a></footer>'
        "<script>PRIVATE SCRIPT</script></body></html>"
    )


def respond(html, requests):
    def run(request):
        requests.append(request)
        return httpx.Response(200, content=html.encode(), headers={"content-type": "text/html"})

    return run


def test_unique_actual_results_only_and_exact_capture_bytes():
    a = sdk()
    requests = []
    raw_html = listing()
    capture = a.discover_policy(
        collected_at=AT, transport=httpx.MockTransport(respond(raw_html, requests))
    )
    assert [(c.news_id, c.canonical_url, c.title) for c in a.policy_candidates(capture)] == [
        ("123456789", URL, "합성 정책"),
        ("234567890", URL.replace("123456789", "234567890"), "합성 정책"),
    ]
    assert capture.list_html.encode() == raw_html.encode()
    assert [str(r.url) for r in requests] == [LIST_URL]
    assert a.parse_policy_discovery(a.serialize_policy_discovery(capture)) == capture
    assert repr(capture) == "PolicyDiscovery(schema_version=1)"


@pytest.mark.parametrize(
    "html",
    [
        listing(""),
        listing('<li class="no_result">empty</li>'),
        listing().replace('<div class="list_type"><ul>', '<div class="changed"><ul>'),
        listing().replace("</ul></div></div>", "</ul><ul>" + entry() + "</ul></div></div>"),
        listing().replace("</strong>", ""),
        listing().replace('<span class="text">', '<span hidden class="text">'),
        listing().replace("<ul>", "<ul><script>unsafe</script>"),
    ],
)
def test_changed_empty_ambiguous_or_hidden_result_structure_fails_closed(html):
    a = sdk()
    with pytest.raises(a.PolicyError, match="^Unable to discover policy sources$"):
        a.discover_policy(collected_at=AT, transport=httpx.MockTransport(respond(html, [])))


@pytest.mark.parametrize(
    "href",
    [
        URL + "&track=PRIVATE",
        "/news/policyNewsView.do?newsId=123456789#fragment",
        "//www.korea.kr/news/policyNewsView.do?newsId=123456789",
        "https://evil.test/news/policyNewsView.do?newsId=123456789",
        "/news/policyNewsView.do?newsId=１２３４５６７８９",
        "/other?newsId=123456789",
    ],
)
def test_tracking_and_other_urls_never_become_candidates(href):
    a = sdk()
    capture = a.discover_policy(
        collected_at=AT,
        transport=httpx.MockTransport(respond(listing(entry() + entry(href=href)), [])),
    )
    assert [c.canonical_url for c in a.policy_candidates(capture)] == [URL]


def test_article_batch_is_explicit_max_two_and_never_sends_auth_or_cookies(monkeypatch):
    a = sdk()
    monkeypatch.setenv("HTTP_PROXY", "http://PRIVATE:secret@untrusted.test")
    monkeypatch.setenv("NETRC", "/PRIVATE")
    requests = []

    def run(request):
        requests.append(request)
        return httpx.Response(
            200,
            content=b"<html>EXACT\r\n</html>",
            headers={"content-type": 'text/html; charset="utf-8"', "set-cookie": "PRIVATE=secret"},
        )

    capture = a.capture_policy(
        ("123456789", "234567890"), collected_at=AT, transport=httpx.MockTransport(run)
    )
    assert [str(r.url) for r in requests] == [URL, URL.replace("123456789", "234567890")]
    assert all(r.method == "GET" and r.headers["accept-encoding"] == "identity" for r in requests)
    assert all(
        "cookie" not in r.headers
        and "authorization" not in r.headers
        and "proxy-authorization" not in r.headers
        for r in requests
    )
    assert all(
        r.extensions["timeout"] == dict.fromkeys(("connect", "read", "write", "pool"), 20.0)
        for r in requests
    )
    assert capture.articles[0].html == "<html>EXACT\r\n</html>"
    assert a.parse_policy_capture(a.serialize_policy_capture(capture)) == capture
    assert repr(capture) == "PolicyCapture(schema_version=1)"
    for ids in [
        (),
        ("123456789",) * 2,
        ("123456789", "234567890", "345678901"),
        (URL,),
        ("１２３４５６７８９",),
    ]:
        before = len(requests)
        with pytest.raises(a.PolicyError):
            a.capture_policy(ids, collected_at=AT, transport=httpx.MockTransport(run))
        assert len(requests) == before


@pytest.mark.parametrize(
    "failure",
    [
        "redirect",
        "status",
        "compressed",
        "encoding",
        "invalid_utf8",
        "length",
        "truncated",
        "stream",
        "timeout",
        "transport",
    ],
)
def test_bounded_http_fails_once_and_suppresses_private_remote_diagnostics(failure, caplog):
    a = sdk()
    calls = []

    def run(request):
        calls.append(request)
        logging.getLogger("httpx2").warning("PRIVATE URL key")
        logging.getLogger("httpcore2.http11").debug("PRIVATE URL key")
        if failure in {"timeout", "transport"}:
            raise (httpx.ReadTimeout if failure == "timeout" else httpx.ConnectError)(
                "PRIVATE URL key"
            )
        headers = {"content-type": "text/html"}
        content = b"<html>ok</html>"
        status = 200
        if failure == "redirect":
            status, headers["location"] = 302, "https://evil.test/PRIVATE"
        if failure == "status":
            status = 500
        if failure == "compressed":
            headers["content-encoding"] = "gzip"
        if failure == "encoding":
            headers["content-type"] = "text/html; charset=cp949"
        if failure == "invalid_utf8":
            content = b"\xff"
        if failure == "length":
            headers["content-length"] = "2097153"
        if failure == "truncated":
            headers["content-length"] = "99"
        if failure == "stream":
            content = b"x" * 2097153
        return httpx.Response(status, content=content, headers=headers)

    with caplog.at_level(logging.DEBUG), pytest.raises(a.PolicyError) as err:
        a.capture_policy(("123456789",), collected_at=AT, transport=httpx.MockTransport(run))
    assert len(calls) == 1
    assert str(err.value) == "Unable to capture policy sources"
    assert err.value.__suppress_context__
    assert "PRIVATE" not in caplog.text


def test_strict_artifacts_and_forged_models_revalidated():
    a = sdk()
    capture = a.capture_policy(
        ("123456789",),
        collected_at=AT,
        transport=httpx.MockTransport(respond("<html>x</html>", [])),
    )
    raw = a.serialize_policy_capture(capture)
    data = json.loads(raw)
    for bad in [
        b"\xff",
        raw[:-1] + b',"schema_version":1}',
        raw[:-1] + b',"extra":NaN}',
        json.dumps({**data, "extra": 1}),
        json.dumps({**data, "schema_version": True}),
        b" " * (a.MAX_POLICY_CAPTURE_BYTES + 1),
    ]:
        with pytest.raises(a.PolicyError):
            a.parse_policy_capture(bad)
    for forged in [
        capture.model_copy(update={"articles": capture.articles * 3}),
        capture.model_copy(update={"schema_version": True}),
        capture.model_copy(update={"collected_at": "PRIVATE"}),
        capture.model_copy(
            update={"articles": (capture.articles[0].model_copy(update={"html": "x" * 2097153}),)}
        ),
    ]:
        with pytest.raises(a.PolicyError):
            a.serialize_policy_capture(forged)


def test_injected_transport_has_one_bounded_batch_lifetime():
    a = sdk()

    class ClosingTransport(httpx.BaseTransport):
        def __init__(self):
            self.closed = 0
            self.requests = 0

        def handle_request(self, request):
            assert not self.closed, "transport reused after close"
            self.requests += 1
            return httpx.Response(
                200, content=b"<html>x</html>", headers={"content-type": "text/html"}
            )

        def close(self):
            self.closed += 1

    transport = ClosingTransport()
    result = a.capture_policy(("123456789", "234567890"), collected_at=AT, transport=transport)
    assert len(result.articles) == transport.requests == 2
    assert transport.closed == 1


def test_recommendation_and_footer_list_regions_are_never_results():
    a = sdk()
    unrelated = '<div class="list_type"><ul>' + entry("999999999", "PRIVATE BANNER") + "</ul></div>"
    html = unrelated + listing() + "<footer>" + unrelated + "</footer>"
    capture = a.discover_policy(collected_at=AT, transport=httpx.MockTransport(respond(html, [])))
    assert [c.news_id for c in a.policy_candidates(capture)] == ["123456789", "234567890"]
    with pytest.raises(a.PolicyError):
        a.discover_policy(collected_at=AT, transport=httpx.MockTransport(respond(unrelated, [])))


def test_default_transport_enforces_tls_and_no_environment_retries(monkeypatch):
    a = sdk()
    module = importlib.import_module("issuedigest_connectors.policy_sdk")
    options = []

    class DefaultTransport(httpx.BaseTransport):
        def handle_request(self, request):
            assert str(request.url) == URL
            assert not any(
                name in request.headers
                for name in ("cookie", "authorization", "proxy-authorization")
            )
            return httpx.Response(
                200, content=b"<html>x</html>", headers={"content-type": "text/html"}
            )

    def factory(**kwargs):
        options.append(kwargs)
        return DefaultTransport()

    monkeypatch.setenv("HTTPS_PROXY", "https://PRIVATE:secret@evil.test")
    monkeypatch.setenv("SSL_CERT_FILE", "/PRIVATE/nonexistent")
    monkeypatch.setattr(module.httpx, "HTTPTransport", factory)
    capture = a.capture_policy(("123456789",), collected_at=AT)
    assert len(capture.articles) == 1
    assert options == [{"verify": True, "trust_env": False, "retries": 0}]


@pytest.mark.parametrize("timestamp", [datetime(2026, 10, 16), "2026-10-16T00:00:00Z", None])
def test_invalid_collection_time_prevents_all_http(timestamp):
    a = sdk()
    requests = []
    transport = httpx.MockTransport(lambda request: requests.append(request))
    with pytest.raises(a.PolicyError):
        a.discover_policy(collected_at=timestamp, transport=transport)
    with pytest.raises(a.PolicyError):
        a.capture_policy(("123456789",), collected_at=timestamp, transport=transport)
    assert requests == []


def test_discovery_artifact_duplicate_json_and_construct_are_private_and_bounded():
    a = sdk()
    capture = a.discover_policy(
        collected_at=AT, transport=httpx.MockTransport(respond(listing(), []))
    )
    raw = a.serialize_policy_discovery(capture)
    for bad in [
        raw[:-1] + b',"list_html":"PRIVATE"}',
        raw[:-1] + b',"extra":Infinity}',
        b"\xff",
        b" " * (a.MAX_POLICY_DISCOVERY_BYTES + 1),
    ]:
        with pytest.raises(a.PolicyError):
            a.parse_policy_discovery(bad)
    for forged in [
        capture.model_copy(update={"list_html": "x" * 2097153}),
        capture.model_copy(update={"list_html": listing().replace("article_body", "other")}),
        capture.model_copy(update={"schema_version": True}),
        capture.model_copy(update={"extra": "PRIVATE"}),
    ]:
        with pytest.raises(a.PolicyError):
            a.serialize_policy_discovery(forged)


def test_stream_budget_stops_reading_before_another_chunk_or_article():
    a = sdk()
    reads = []
    requests = []

    class OversizedStream(httpx.SyncByteStream):
        def __iter__(self):
            for index in range(4):
                reads.append(index)
                yield b"x" * 1048576

    def run(request):
        requests.append(request)
        return httpx.Response(200, stream=OversizedStream(), headers={"content-type": "text/html"})

    with pytest.raises(a.PolicyError):
        a.capture_policy(
            ("123456789", "234567890"), collected_at=AT, transport=httpx.MockTransport(run)
        )
    assert len(requests) == 1
    assert reads == [0, 1, 2]
