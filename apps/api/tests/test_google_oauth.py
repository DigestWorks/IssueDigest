"""Real signatures and synthetic fixed-endpoint transport; no Google network."""

import asyncio
import base64
import importlib
import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from issuedigest_api.auth_config import AuthConfig
from issuedigest_storage import ConsumedLogin, PendingLogin

CONFIG = AuthConfig(
    "postgresql+psycopg://synthetic/db",
    "https://localhost:8443",
    "synthetic-client",
    "synthetic-secret",
)
NONCE = secrets.token_urlsafe(32)
FLOW = ConsumedLogin(secrets.token_urlsafe(32), NONCE)


def module():
    assert importlib.util.find_spec("issuedigest_api.google_oauth") is not None
    return importlib.import_module("issuedigest_api.google_oauth")


@pytest.fixture(scope="module")
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "synthetic")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, cert.public_bytes(serialization.Encoding.PEM).decode()


def encoded(value):
    return (
        base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode())
        .decode()
        .rstrip("=")
    )


def claims(**changes):
    now = int(time.time())
    return {
        "iss": "https://accounts.google.com",
        "sub": "synthetic-subject",
        "aud": CONFIG.client_id,
        "iat": now - 10,
        "exp": now + 300,
        "nonce": NONCE,
        "email": "invited@gmail.com",
        "email_verified": True,
    } | changes


def signed(signing, payload=None, header=None):
    message = (
        encoded(header or {"alg": "RS256", "kid": "synthetic-key"})
        + "."
        + encoded(payload or claims())
    )
    signature = signing[0].sign(message.encode(), padding.PKCS1v15(), hashes.SHA256())
    return message + "." + base64.urlsafe_b64encode(signature).decode().rstrip("=")


def exchange(signing, payload=None, token=None, token_response=None, cert_response=None):
    requests = []

    def handle(request):
        requests.append(request)
        if str(request.url) == "https://oauth2.googleapis.com/token":
            return token_response or httpx2.Response(
                200,
                json={
                    "id_token": token or signed(signing, payload),
                    "access_token": "never-store",
                    "refresh_token": "never-store",
                },
            )
        assert str(request.url) == "https://www.googleapis.com/oauth2/v1/certs"
        return cert_response or httpx2.Response(200, json={"synthetic-key": signing[1]})

    provider = module().GoogleOAuthProvider(CONFIG, transport=httpx2.MockTransport(handle))
    return asyncio.run(provider.verify_code("synthetic-code", FLOW)), requests


def test_authorize_uses_minimal_scope_and_fixed_endpoint():
    provider = module().GoogleOAuthProvider(CONFIG)
    pending = PendingLogin(
        secrets.token_urlsafe(32), secrets.token_urlsafe(32), secrets.token_urlsafe(32), NONCE
    )
    url = urlsplit(provider.authorize_url(pending))
    assert url.scheme == "https" and url.netloc == "accounts.google.com"
    assert parse_qs(url.query) == {
        "client_id": [CONFIG.client_id],
        "redirect_uri": [CONFIG.callback_url],
        "response_type": ["code"],
        "scope": ["openid email"],
        "state": [pending.state],
        "nonce": [NONCE],
        "code_challenge": [pending.code_challenge],
        "code_challenge_method": ["S256"],
        "access_type": ["online"],
        "prompt": ["select_account"],
        "include_granted_scopes": ["false"],
    }
    assert CONFIG.client_secret not in provider.authorize_url(pending)


def test_real_signature_form_exchange_and_private_identity(signing):
    identity, requests = exchange(signing)
    assert identity.issuer == "https://accounts.google.com"
    assert identity.subject == "synthetic-subject"
    assert identity.email == "invited@gmail.com" and identity.authoritative_email
    assert "invited" not in repr(identity) and "synthetic-subject" not in repr(identity)
    assert len(requests) == 2
    request = requests[0]
    assert request.method == "POST" and not request.url.query
    assert parse_qs(request.content.decode()) == {
        "grant_type": ["authorization_code"],
        "client_id": [CONFIG.client_id],
        "client_secret": [CONFIG.client_secret],
        "code": ["synthetic-code"],
        "redirect_uri": [CONFIG.callback_url],
        "code_verifier": [FLOW.code_verifier],
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"iss": "https://evil.test"},
        {"sub": ""},
        {"sub": "한글"},
        {"sub": "x" * 256},
        {"aud": "wrong"},
        {"aud": [CONFIG.client_id]},
        {"azp": "wrong"},
        {"iat": True},
        {"exp": True},
        {"iat": int(time.time()) + 600},
        {"exp": 1},
        {"nonce": "wrong"},
        {"nonce": None},
        {"email_verified": "true"},
        {"email_verified": False},
        {"email": "a@@gmail.com"},
        {"email": "한글@gmail.com"},
        {"email": "a @gmail.com"},
    ],
)
def test_signed_invalid_claims_denied_without_sensitive_errors(signing, changes):
    with pytest.raises(module().ProviderDenied) as caught:
        exchange(signing, payload=claims(**changes))
    assert str(caught.value) == "Provider identity denied"


@pytest.mark.parametrize(
    "email,hd,authority",
    [
        ("USER@GMAIL.COM", None, True),
        ("invited@workspace.test", "workspace.test", True),
        ("invited@thirdparty.test", None, False),
        ("invited@workspace.test", "wrong.test", False),
    ],
)
def test_authoritative_binding_policy(signing, email, hd, authority):
    payload = claims(email=email, iss="accounts.google.com")
    if hd is not None:
        payload["hd"] = hd
    identity, _ = exchange(signing, payload=payload)
    assert identity.email == email.lower()
    assert identity.authoritative_email is authority
    assert identity.issuer == "https://accounts.google.com"


@pytest.mark.parametrize(
    "header",
    [
        {"alg": "none", "kid": "synthetic-key"},
        {"alg": "HS256", "kid": "synthetic-key"},
        {"alg": "RS256", "kid": "unknown"},
        {"alg": "RS256", "kid": " "},
        {"alg": "RS256", "kid": "x" * 257},
    ],
)
def test_wrong_header_or_unknown_key_denied(signing, header):
    with pytest.raises(module().ProviderDenied):
        exchange(signing, token=signed(signing, header=header))


@pytest.mark.parametrize(
    "token",
    [
        "bad",
        "a.b.c",
        "a=.b.c",
        "a.b.c.d",
        "x" * 16385,
        encoded({"alg": "RS256", "kid": "synthetic-key"})
        + "."
        + base64.urlsafe_b64encode(b'{"sub":"a","sub":"b"}').decode().rstrip("=")
        + ".YWJj",
    ],
)
def test_malformed_token_denied(signing, token):
    with pytest.raises(module().ProviderDenied):
        exchange(signing, token=token)


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(302, headers={"location": "https://evil.test"}),
        httpx2.Response(500),
        httpx2.Response(200, content=b"\xff"),
        httpx2.Response(200, content=b'{"id_token":"a","id_token":"b"}'),
        httpx2.Response(200, json=[]),
        httpx2.Response(200, json={}),
        httpx2.Response(200, content=b"x" * 65537),
    ],
)
def test_invalid_token_response_unavailable(signing, response):
    with pytest.raises(module().ProviderUnavailable) as caught:
        exchange(signing, token_response=response)
    assert str(caught.value) == "Provider unavailable"


@pytest.mark.parametrize(
    "response",
    [
        httpx2.Response(500),
        httpx2.Response(200, json=[]),
        httpx2.Response(200, json={"keys": []}),
        httpx2.Response(200, json={"synthetic-key": 7}),
        httpx2.Response(200, content=b'{"a":"x","a":"y"}'),
        httpx2.Response(200, content=b"x" * 65537),
    ],
)
def test_invalid_certs_response_unavailable(signing, response):
    with pytest.raises(module().ProviderUnavailable):
        exchange(signing, cert_response=response)


def test_signature_tampering_denied(signing):
    token = signed(signing)
    segments = token.split(".")
    segments[1] = encoded(claims(sub="attacker"))
    with pytest.raises(module().ProviderDenied):
        exchange(signing, token=".".join(segments))


def test_decoded_compressed_response_limit(signing):
    import gzip

    compressed = gzip.compress(b"x" * 65537)
    assert len(compressed) < 65536
    response = httpx2.Response(200, content=compressed, headers={"Content-Encoding": "gzip"})
    with pytest.raises(module().ProviderUnavailable):
        exchange(signing, token_response=response)


def test_client_tls_proxy_redirect_and_per_operation_deadline(monkeypatch, signing):
    google = module()
    real_client = httpx2.AsyncClient
    observed = []

    def configured_client(**kwargs):
        observed.append(kwargs)
        return real_client(**kwargs)

    monkeypatch.setattr(google.httpx2, "AsyncClient", configured_client)
    exchange(signing)
    settings = observed[0]
    assert settings["verify"] is True and settings["trust_env"] is False
    assert settings["follow_redirects"] is False
    timeout = settings["timeout"]
    assert timeout.connect == timeout.read == timeout.write == timeout.pool == 5


def test_entire_exchange_deadline_and_cancellation(monkeypatch):
    google = module()
    real_timeout = asyncio.timeout
    deadlines = []

    def bounded_deadline(seconds):
        deadlines.append(seconds)
        return real_timeout(0.03)

    monkeypatch.setattr(google.asyncio, "timeout", bounded_deadline)

    async def slow_transport(request):
        await asyncio.Event().wait()

    provider = google.GoogleOAuthProvider(CONFIG, transport=httpx2.MockTransport(slow_transport))
    with pytest.raises(google.ProviderUnavailable):
        asyncio.run(provider.verify_code("synthetic", FLOW))
    assert deadlines == [15]

    async def cancelled():
        task = asyncio.create_task(provider.verify_code("synthetic", FLOW))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancelled())


def test_header_urls_are_never_followed(signing):
    identity, requests = exchange(
        signing,
        token=signed(
            signing,
            header={
                "alg": "RS256",
                "kid": "synthetic-key",
                "jku": "https://evil.test",
                "x5u": "https://evil.test",
            },
        ),
    )
    assert identity.subject == "synthetic-subject"
    assert [str(request.url) for request in requests] == [
        "https://oauth2.googleapis.com/token",
        "https://www.googleapis.com/oauth2/v1/certs",
    ]


def test_identity_without_email_is_allowed_for_registered_subject(signing):
    payload = claims()
    del payload["email"]
    del payload["email_verified"]
    identity, _ = exchange(signing, payload=payload)
    assert identity.email is None and identity.authoritative_email is False
