"""Two-request public GET/read-POST capture with strict private artifact boundaries."""

import json
import logging
import re
from contextvars import ContextVar
from datetime import datetime
from typing import Annotated, Literal, Self

import httpx2 as httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from .html import MAX_HTML_BYTES, bounded_html, detail_fields, summary_text

ORIGIN = "https://likms.assembly.go.kr"
MAX_CAPTURE_BYTES = 8 * 1024 * 1024
_PRIVATE_HTTP = ContextVar("assembly_private_http", default=False)


class AssemblyError(ValueError):
    """Fixed public failure; never include inputs or remote diagnostics."""


class _PrivateHTTPFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _PRIVATE_HTTP.get()


_HTTP_FILTER = _PrivateHTTPFilter()


def canonical_url(bill_id: str) -> str:
    if (
        type(bill_id) is not str
        or re.fullmatch(r"[A-Za-z0-9_]{1,80}", bill_id, flags=re.ASCII) is None
    ):
        raise AssemblyError("Unable to validate Assembly identity")
    return ORIGIN + "/bill/bi/billDetailPage.do?billId=" + bill_id


class AssemblyCapture(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)

    schema_version: Literal[1]
    bill_id: Annotated[str, Field(min_length=1, max_length=80)] = Field(repr=False)
    canonical_url: Annotated[str, Field(max_length=200)] = Field(repr=False)
    collected_at: AwareDatetime = Field(repr=False)
    detail_html: Annotated[str, Field(max_length=MAX_HTML_BYTES)] = Field(repr=False)
    summary_html: Annotated[str, Field(max_length=MAX_HTML_BYTES)] = Field(repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid capture version")
        return value

    @model_validator(mode="after")
    def relationships(self) -> Self:
        if self.canonical_url != canonical_url(self.bill_id):
            raise ValueError("Invalid canonical URL")
        bounded_html(self.detail_html)
        bounded_html(self.summary_html)
        detail_fields(self.detail_html, self.bill_id)
        summary_text(self.summary_html)
        return self


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError("Invalid JSON constant")


def parse_capture(raw: str | bytes) -> AssemblyCapture:
    try:
        if type(raw) is str:
            if len(raw) > MAX_CAPTURE_BYTES:
                raise ValueError("Capture budget exceeded")
            raw = raw.encode("utf-8")
        if type(raw) is not bytes or len(raw) > MAX_CAPTURE_BYTES:
            raise ValueError("Capture budget exceeded")
        data = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique, parse_constant=_constant)
        return AssemblyCapture.model_validate_json(
            json.dumps(data, ensure_ascii=False, allow_nan=False), strict=True
        )
    except Exception:
        raise AssemblyError("Unable to validate Assembly capture") from None


def serialize_capture(capture: AssemblyCapture) -> bytes:
    """Bound all simple fields before serialization, including forged construct/copy graphs."""
    try:
        if (
            type(capture) is not AssemblyCapture
            or set(capture.__dict__) != set(AssemblyCapture.model_fields)
            or capture.__pydantic_extra__
        ):
            raise ValueError("Invalid capture model")
        for name, limit in (
            ("detail_html", MAX_HTML_BYTES),
            ("summary_html", MAX_HTML_BYTES),
            ("bill_id", 80),
            ("canonical_url", 200),
        ):
            value = capture.__dict__[name]
            if type(value) is not str or len(value) > limit:
                raise ValueError("Capture field budget exceeded")
        if type(capture.collected_at) is not datetime or type(capture.schema_version) is not int:
            raise ValueError("Invalid capture scalar")
        raw = capture.model_dump_json(warnings="error").encode("utf-8")
        parse_capture(raw)
        return raw
    except Exception:
        raise AssemblyError("Unable to validate Assembly capture") from None


def extract_assembly_summary(html: str) -> str:
    try:
        return summary_text(html)
    except Exception:
        raise AssemblyError("Unable to extract Assembly summary") from None


def _html(response: httpx.Response) -> str:
    if response.status_code != 200:
        raise ValueError("Invalid status")
    content_types = response.headers.get_list("content-type")
    if (
        len(content_types) != 1
        or re.fullmatch(
            r'text/html(?:\s*;\s*charset\s*=\s*(?:utf-8|"utf-8"))?\s*', content_types[0], flags=re.I
        )
        is None
    ):
        raise ValueError("Invalid content type")
    if response.headers.get("content-encoding", "identity").lower() != "identity":
        raise ValueError("Encoded response forbidden")
    lengths = response.headers.get_list("content-length")
    if lengths and (
        len(lengths) != 1
        or not lengths[0].isascii()
        or not lengths[0].isdigit()
        or len(lengths[0]) > 8
        or int(lengths[0]) > MAX_HTML_BYTES
    ):
        raise ValueError("Response size exceeded")
    parts: list[bytes] = []
    count = 0
    # iter_bytes handles already-buffered synthetic Responses too. Compressed
    # representations were rejected above, so byte budget covers source bytes.
    for part in response.iter_bytes(chunk_size=65_536):
        count += len(part)
        if count > MAX_HTML_BYTES:
            raise ValueError("Response size exceeded")
        parts.append(part)
    if lengths and count != int(lengths[0]):
        raise ValueError("Truncated response")
    return b"".join(parts).decode("utf-8", errors="strict")


def capture_assembly(
    bill_id: str, *, collected_at: datetime, transport: httpx.BaseTransport | None = None
) -> AssemblyCapture:
    """No retries, redirects, environment proxy, persisted cookies, DB or default storage."""
    try:
        url = canonical_url(bill_id)
        if (
            type(collected_at) is not datetime
            or collected_at.tzinfo is None
            or collected_at.utcoffset() is None
        ):
            raise ValueError("Explicit collection time required")
        # Logger filters are context-local: unrelated calls in other threads are
        # untouched. Known pinned HTTP stack emitters never log capture traffic.
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
                with client.stream("GET", url) as response:
                    detail = _html(response)
                fields, csrf, _ = detail_fields(detail, bill_id)
                with client.stream(
                    "POST",
                    ORIGIN + "/bill/bi/bill/detail/billInfo.do",
                    data=fields,
                    headers={
                        "Referer": url,
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRF-TOKEN": csrf,
                    },
                ) as response:
                    summary = _html(response)
                result = AssemblyCapture(
                    schema_version=1,
                    bill_id=bill_id,
                    canonical_url=url,
                    collected_at=collected_at,
                    detail_html=detail,
                    summary_html=summary,
                )
                # Ensure what the SDK returns can actually be saved within bounds.
                return parse_capture(serialize_capture(result))
        finally:
            _PRIVATE_HTTP.reset(private)
    except Exception:
        raise AssemblyError("Unable to capture Assembly source") from None
