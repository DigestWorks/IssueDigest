"""Bounded explicit official policy GETs and private UTF-8 captures; no import IO."""

import json
import logging
import re
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Annotated, Literal, Self

import httpx2 as httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from ._policy_list import ARTICLE_PATH, ORIGIN, result_entries, result_metadata
from .assembly import _HTTP_FILTER, _PRIVATE_HTTP, _constant, _html, _unique
from .html import MAX_HTML_BYTES, bounded_html

POLICY_LIST_URL = ORIGIN + "/news/policyNewsList.do"
MAX_POLICY_CAPTURE_BYTES = 8 * 1024 * 1024 + 16_384
MAX_POLICY_DISCOVERY_BYTES = 4 * 1024 * 1024 + 8192


class PolicyError(ValueError):
    """Fixed safe failures, never source/URL/transport diagnostics."""


def policy_url(news_id: str) -> str:
    if type(news_id) is not str or re.fullmatch(r"[0-9]{9}", news_id) is None:
        raise PolicyError("Unable to validate policy identity")
    return ORIGIN + ARTICLE_PATH + news_id


class _PrivateModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class PolicyCandidate(_PrivateModel):
    news_id: str = Field(repr=False)
    canonical_url: str = Field(repr=False)
    title: str = Field(repr=False)


class PolicyCandidateMetadata(PolicyCandidate):
    published_on: date = Field(repr=False)
    publisher: Annotated[str, Field(min_length=1, max_length=200)] = Field(repr=False)

    @model_validator(mode="after")
    def valid_metadata(self) -> Self:
        if (
            self.canonical_url != policy_url(self.news_id)
            or not 1 <= len(self.title) <= 300
            or self.title != " ".join(self.title.split())
            or self.publisher != " ".join(self.publisher.split())
        ):
            raise ValueError("Invalid candidate metadata")
        return self


class PolicyArticle(_PrivateModel):
    news_id: Annotated[str, Field(min_length=9, max_length=9)] = Field(repr=False)
    canonical_url: Annotated[str, Field(max_length=100)] = Field(repr=False)
    html: Annotated[str, Field(max_length=MAX_HTML_BYTES)] = Field(repr=False)

    @model_validator(mode="after")
    def valid_article(self) -> Self:
        if self.canonical_url != policy_url(self.news_id):
            raise ValueError("Invalid article identity")
        bounded_html(self.html)
        if not self.html.strip():
            raise ValueError("Empty article")
        return self


class _Capture(_PrivateModel):
    schema_version: Literal[1]
    collected_at: AwareDatetime = Field(repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid capture version")
        return value


class PolicyDiscovery(_Capture):
    list_html: Annotated[str, Field(max_length=MAX_HTML_BYTES)] = Field(repr=False)

    @model_validator(mode="after")
    def valid_list(self) -> Self:
        result_entries(self.list_html)
        return self


class PolicyCapture(_Capture):
    articles: Annotated[tuple[PolicyArticle, ...], Field(min_length=1, max_length=2)] = Field(
        repr=False
    )

    @model_validator(mode="after")
    def unique_articles(self) -> Self:
        if len({a.news_id for a in self.articles}) != len(self.articles):
            raise ValueError("Duplicate articles")
        return self


def _parse[C: (PolicyDiscovery, PolicyCapture)](raw: str | bytes, model: type[C], limit: int) -> C:
    try:
        if type(raw) is str:
            if len(raw) > limit:
                raise ValueError("Capture size exceeded")
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or len(raw) > limit:
            raise ValueError("Capture size exceeded")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
        return model.model_validate_json(
            json.dumps(data, ensure_ascii=False, allow_nan=False), strict=True
        )
    except Exception:
        raise PolicyError("Unable to validate policy capture") from None


def parse_policy_discovery(raw: str | bytes) -> PolicyDiscovery:
    return _parse(raw, PolicyDiscovery, MAX_POLICY_DISCOVERY_BYTES)


def parse_policy_capture(raw: str | bytes) -> PolicyCapture:
    return _parse(raw, PolicyCapture, MAX_POLICY_CAPTURE_BYTES)


def _shape(value: BaseModel, expected: type[BaseModel]) -> None:
    if (
        type(value) is not expected
        or set(value.__dict__) != set(expected.model_fields)
        or value.__pydantic_extra__
    ):
        raise ValueError("Invalid model shape")


def _serialize[C: (PolicyDiscovery, PolicyCapture)](value: C, model: type[C], limit: int) -> bytes:
    try:
        _shape(value, model)
        if type(value.schema_version) is not int or type(value.collected_at) is not datetime:
            raise ValueError("Invalid capture scalar")
        if type(value) is PolicyDiscovery:
            bounded_html(value.list_html)
        elif type(value) is PolicyCapture:
            if type(value.articles) is not tuple or not 1 <= len(value.articles) <= 2:
                raise ValueError("Invalid article count")
            for article in value.articles:
                _shape(article, PolicyArticle)
                bounded_html(article.html)
                if (
                    type(article.canonical_url) is not str
                    or len(article.canonical_url) > 100
                    or article.canonical_url != policy_url(article.news_id)
                ):
                    raise ValueError("Invalid article identity")
        raw = value.model_dump_json(warnings="error").encode("utf-8")
        _parse(raw, model, limit)
        return raw
    except Exception:
        raise PolicyError("Unable to validate policy capture") from None


def serialize_policy_discovery(capture: PolicyDiscovery) -> bytes:
    return _serialize(capture, PolicyDiscovery, MAX_POLICY_DISCOVERY_BYTES)


def serialize_policy_capture(capture: PolicyCapture) -> bytes:
    return _serialize(capture, PolicyCapture, MAX_POLICY_CAPTURE_BYTES)


def policy_candidates(capture: PolicyDiscovery) -> tuple[PolicyCandidate, ...]:
    try:
        capture = parse_policy_discovery(serialize_policy_discovery(capture))
        return tuple(
            PolicyCandidate(news_id=identity, canonical_url=policy_url(identity), title=title)
            for identity, title in result_entries(capture.list_html)
        )
    except Exception:
        raise PolicyError("Unable to validate policy discovery") from None


def policy_candidate_metadata(capture: PolicyDiscovery) -> tuple[PolicyCandidateMetadata, ...]:
    """Validate visible discovery metadata without asserting article content or rights."""
    try:
        capture = parse_policy_discovery(serialize_policy_discovery(capture))
        return tuple(
            PolicyCandidateMetadata(
                news_id=identity,
                canonical_url=policy_url(identity),
                title=title,
                published_on=published_on,
                publisher=publisher,
            )
            for identity, title, published_on, publisher in result_metadata(capture.list_html)
        )
    except Exception:
        raise PolicyError("Unable to validate policy discovery") from None


def _time(collected_at: datetime) -> None:
    if (
        type(collected_at) is not datetime
        or collected_at.tzinfo is None
        or collected_at.utcoffset() is None
    ):
        raise ValueError("Explicit aware collection time required")


@contextmanager
def _client(transport: httpx.BaseTransport | None) -> Iterator[httpx.Client]:
    # Same context-local suppression as Assembly; no remote diagnostic reaches logs.
    for name in (
        "httpx2",
        "httpcore2.connection",
        "httpcore2.http11",
        "httpcore2.http2",
        "httpcore2.proxy",
        "httpcore2.socks",
    ):
        logging.getLogger(name).addFilter(_HTTP_FILTER)
    private = _PRIVATE_HTTP.set(True)
    try:
        # One transport lifetime per batch; every request clears response cookies.
        with httpx.Client(
            transport=transport
            if transport is not None
            else httpx.HTTPTransport(verify=True, trust_env=False, retries=0),
            verify=True,
            trust_env=False,
            follow_redirects=False,
            timeout=20.0,
            headers={"Accept": "text/html", "Accept-Encoding": "identity"},
        ) as client:
            yield client
    finally:
        _PRIVATE_HTTP.reset(private)


def _get(client: httpx.Client, url: str) -> str:
    client.cookies.clear()
    try:
        with client.stream("GET", url) as response:
            return _html(response)
    finally:
        client.cookies.clear()


def discover_policy(
    *, collected_at: datetime, transport: httpx.BaseTransport | None = None
) -> PolicyDiscovery:
    try:
        _time(collected_at)
        with _client(transport) as client:
            capture = PolicyDiscovery(
                schema_version=1, collected_at=collected_at, list_html=_get(client, POLICY_LIST_URL)
            )
        return parse_policy_discovery(serialize_policy_discovery(capture))
    except Exception:
        raise PolicyError("Unable to discover policy sources") from None


def capture_policy(
    news_ids: tuple[str, ...],
    *,
    collected_at: datetime,
    transport: httpx.BaseTransport | None = None,
) -> PolicyCapture:
    """Capture only explicit literal IDs, at most two, no retries or discovery traversal."""
    try:
        _time(collected_at)
        if type(news_ids) is not tuple or not 1 <= len(news_ids) <= 2:
            raise ValueError("Invalid article count")
        urls = tuple(policy_url(identity) for identity in news_ids)
        if len(set(news_ids)) != len(news_ids):
            raise ValueError("Duplicate article identity")
        with _client(transport) as client:
            capture = PolicyCapture(
                schema_version=1,
                collected_at=collected_at,
                articles=tuple(
                    PolicyArticle(news_id=identity, canonical_url=url, html=_get(client, url))
                    for identity, url in zip(news_ids, urls, strict=True)
                ),
            )
        return parse_policy_capture(serialize_policy_capture(capture))
    except Exception:
        raise PolicyError("Unable to capture policy sources") from None
