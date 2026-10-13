"""Bounded Google OpenID exchange with fixed endpoints and signature verification."""

import asyncio
import base64
import hmac
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx2
from google.auth import transport as google_transport
from google.oauth2 import id_token
from issuedigest_storage import ConsumedLogin, PendingLogin

from .auth_config import AuthConfig, visible_ascii

GOOGLE_ISSUER = "https://accounts.google.com"
AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CERTS_URL = "https://www.googleapis.com/oauth2/v1/certs"
RESPONSE_LIMIT = 65536
TOKEN_LIMIT = 16384


class ProviderUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Provider unavailable")


class ProviderDenied(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Provider identity denied")


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str = field(repr=False)
    email: str | None = field(repr=False)
    authoritative_email: bool


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _json(raw: bytes) -> dict[str, Any]:
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_object,
        parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
    )
    if not isinstance(value, dict):
        raise ValueError
    return value


def _segment(segment: str) -> bytes:
    if not segment or re.fullmatch(r"[A-Za-z0-9_-]+", segment) is None:
        raise ValueError
    raw = base64.b64decode(segment + "=" * (-len(segment) % 4), altchars=b"-_", validate=True)
    if base64.urlsafe_b64encode(raw).decode().rstrip("=") != segment:
        raise ValueError
    return raw


def _validate_token(token: str) -> None:
    if not isinstance(token, str) or not 1 <= len(token) <= TOKEN_LIMIT:
        raise ValueError
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError
    header = _json(_segment(parts[0]))
    _json(_segment(parts[1]))  # Parse strictly before SDK reparses; never trust unsigned claims.
    _segment(parts[2])
    if header.get("alg") != "RS256" or not visible_ascii(header.get("kid"), 256):
        raise ValueError


class _CertificateResponse(google_transport.Response):
    def __init__(self, data: bytes):
        self._data = data

    @property
    def status(self) -> int:
        return 200

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def headers(self) -> dict[str, str]:
        return {"content-type": "application/json"}


class _InlineCertificates(google_transport.Request):
    """The SDK can only read the certificates already fetched within our deadline."""

    def __init__(self, data: bytes):
        self._data = data

    def __call__(
        self,
        url: str,
        method: str = "GET",
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> google_transport.Response:
        if url != CERTS_URL or method != "GET":
            raise ValueError
        return _CertificateResponse(self._data)


class GoogleOAuthProvider:
    def __init__(self, config: AuthConfig, *, transport: httpx2.AsyncBaseTransport | None = None):
        self._config = config
        self._transport = transport

    def authorize_url(self, pending: PendingLogin) -> str:
        return (
            AUTHORIZE_URL
            + "?"
            + urlencode(
                {
                    "client_id": self._config.client_id,
                    "redirect_uri": self._config.callback_url,
                    "response_type": "code",
                    "scope": "openid email",
                    "state": pending.state,
                    "nonce": pending.oidc_nonce,
                    "code_challenge": pending.code_challenge,
                    "code_challenge_method": "S256",
                    "access_type": "online",
                    "prompt": "select_account",
                    "include_granted_scopes": "false",
                }
            )
        )

    @staticmethod
    async def _fetch(
        client: httpx2.AsyncClient, method: str, url: str, data: dict[str, str] | None = None
    ) -> dict[str, Any]:
        async with client.stream(method, url, data=data) as response:
            if response.status_code != 200:
                raise ProviderUnavailable()
            decoded = bytearray()
            async for chunk in response.aiter_bytes(chunk_size=4096):
                decoded.extend(chunk)
                if len(decoded) > RESPONSE_LIMIT:
                    raise ProviderUnavailable()
            return _json(bytes(decoded))

    async def verify_code(self, code: str, flow: ConsumedLogin) -> VerifiedIdentity:
        try:
            async with asyncio.timeout(15):
                async with httpx2.AsyncClient(
                    verify=True,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=httpx2.Timeout(5),
                    transport=self._transport,
                ) as client:
                    token_response = await self._fetch(
                        client,
                        "POST",
                        TOKEN_URL,
                        {
                            "grant_type": "authorization_code",
                            "client_id": self._config.client_id,
                            "client_secret": self._config.client_secret,
                            "code": code,
                            "redirect_uri": self._config.callback_url,
                            "code_verifier": flow.code_verifier,
                        },
                    )
                    token = token_response.get("id_token")
                    if not isinstance(token, str) or not token:
                        raise ProviderUnavailable()
                    try:
                        _validate_token(token)
                    except Exception:
                        raise ProviderDenied() from None
                    certificates = await self._fetch(client, "GET", CERTS_URL)
                    if (
                        not certificates
                        or "keys" in certificates
                        or any(
                            not visible_ascii(key, 256) or not isinstance(value, str) or not value
                            for key, value in certificates.items()
                        )
                    ):
                        raise ProviderUnavailable()
                    try:
                        claims = await asyncio.to_thread(
                            id_token.verify_oauth2_token,
                            token,
                            _InlineCertificates(json.dumps(certificates).encode()),
                            audience=self._config.client_id,
                        )
                        return self._identity(claims, flow.oidc_nonce)
                    except Exception:
                        raise ProviderDenied() from None
        except ProviderDenied:
            raise
        except Exception:
            raise ProviderUnavailable() from None

    def _identity(self, claims: Any, nonce: str) -> VerifiedIdentity:
        if not isinstance(claims, dict):
            raise ValueError
        issuer, subject = claims.get("iss"), claims.get("sub")
        issued, expires = claims.get("iat"), claims.get("exp")
        now = time.time()
        if (
            issuer not in {GOOGLE_ISSUER, "accounts.google.com"}
            or not visible_ascii(subject, 255)
            or claims.get("aud") != self._config.client_id
            or ("azp" in claims and claims["azp"] != self._config.client_id)
            or type(issued) is not int
            or type(expires) is not int
            or not issued <= now < expires
            or expires <= issued
            or not isinstance(claims.get("nonce"), str)
            or not hmac.compare_digest(claims["nonce"], nonce)
        ):
            raise ValueError
        email = claims.get("email")
        authoritative = False
        if "email" in claims:
            if (
                not visible_ascii(email, 320)
                or email.count("@") != 1
                or not all(email.split("@"))
                or claims.get("email_verified") is not True
            ):
                raise ValueError
            email = email.lower()
            domain = email.split("@")[1]
            hosted = claims.get("hd")
            authoritative = domain == "gmail.com" or (
                isinstance(hosted, str)
                and visible_ascii(hosted, 253)
                and hosted == hosted.lower()
                and hosted == domain
                and re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", hosted) is not None
            )
        return VerifiedIdentity(GOOGLE_ISSUER, subject, email, authoritative)
