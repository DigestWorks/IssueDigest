"""Strict, offline rendering of historical Bill metadata supplied by a caller."""

import json
import re
import unicodedata
from dataclasses import InitVar, dataclass
from datetime import date
from hashlib import sha256
from typing import NoReturn, TypedDict, cast
from uuid import UUID

from issuedigest_domain.citations import TextQuoteSelector
from issuedigest_domain.sources import ParsedRepresentation
from pydantic import ValidationError

from .errors import AuditError

_KEYS = frozenset(
    {
        "bill_id",
        "assembly_number",
        "bill_name",
        "bill_number",
        "propose_date",
        "committee",
        "stage",
        "bill_result",
        "proposer_kind",
        "bill_link",
    }
)
_ID = re.compile(r"[A-Za-z0-9_]{1,255}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_HASH = re.compile(r"[0-9a-f]{64}")
_BASE_URL = "https://likms.assembly.go.kr/bill/billDetail.do?billId="
_NOTICE = (
    "기존 수집 DB의 법안 기본 정보입니다. "
    "법안 전문이 아니며 현재 처리 상태는 원문 출처에서 확인해 주세요."
)
_NAME = "legacy-bill-metadata"
_VERSION = "1"
_PROFILE = "legacy-bill-metadata-v1"
_KINDS = frozenset({"CHAIRMAN", "CONGRESSMAN", "GOVERNMENT"})
_KIND_LABELS = {
    "CHAIRMAN": "위원장 제안",
    "CONGRESSMAN": "의원 발의",
    "GOVERNMENT": "정부 제출",
}
_MAX_RAW_BYTES = 64 * 1024
_VERIFIED = object()


class _BillFields(TypedDict):
    bill_id: str
    assembly_number: int
    bill_name: str
    bill_number: int
    propose_date: str
    committee: str | None
    stage: str | None
    bill_result: str | None
    proposer_kind: str | None
    bill_link: str


def _fail(code: str) -> NoReturn:
    raise AuditError(code) from None


def _hash(value: object) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _text(value: object) -> bool:
    return (
        type(value) is str
        and 1 <= len(value) <= 255
        and bool(value.strip())
        and all(
            not unicodedata.category(char).startswith("C") and char not in "\u2028\u2029"
            for char in value
        )
    )


def _validate_bill(value: object) -> _BillFields:
    if type(value) is not dict or value.keys() != _KEYS:
        _fail("legacy_bill_invalid_metadata")
    bill = value
    source_id = bill["bill_id"]
    assembly = bill["assembly_number"]
    number = bill["bill_number"]
    proposed = bill["propose_date"]
    if (
        type(source_id) is not str
        or _ID.fullmatch(source_id) is None
        or not _text(bill["bill_name"])
        or type(assembly) is not int
        or not 1 <= assembly <= 99
        or type(number) is not int
        or not 1_000_000 <= number <= 9_999_999
        or f"{number:07d}"[:2] != f"{assembly:02d}"
        or type(proposed) is not str
        or _DATE.fullmatch(proposed) is None
    ):
        _fail("legacy_bill_invalid_metadata")
    try:
        date.fromisoformat(proposed)
    except ValueError:
        _fail("legacy_bill_invalid_metadata")
    for key in ("committee", "stage", "bill_result"):
        if bill[key] is not None and not _text(bill[key]):
            _fail("legacy_bill_invalid_metadata")
    kind = bill["proposer_kind"]
    if kind is not None and (type(kind) is not str or kind not in _KINDS):
        _fail("legacy_bill_invalid_metadata")
    if type(bill["bill_link"]) is not str or bill["bill_link"] != _BASE_URL + source_id:
        _fail("legacy_bill_invalid_url")
    return cast("_BillFields", bill)


def _display(value: str | None) -> str:
    return "미수집" if value is None else value


def _render(bill: _BillFields) -> str:
    proposer = bill["proposer_kind"]
    return "\n".join(
        (
            str(bill["bill_name"]),
            _NOTICE,
            f"대수: {bill['assembly_number']}대",
            f"의안번호: {bill['bill_number']}",
            f"제안일: {bill['propose_date']}",
            f"위원회: {_display(bill['committee'])}",
            f"수집 당시 단계: {_display(bill['stage'])}",
            f"수집 당시 처리결과: {_display(bill['bill_result'])}",
            f"발의구분: {_KIND_LABELS[proposer] if proposer is not None else '미수집'}",
        )
    )


@dataclass(frozen=True)
class LegacyBillMetadata:
    source_id: str
    canonical_url: str
    assembly_number: int
    bill_name: str
    bill_number: int
    propose_date: str
    committee: str | None
    stage: str | None
    bill_result: str | None
    proposer_kind: str | None
    text: str
    raw_sha256: str
    raw_bytes: int
    text_sha256: str
    parser_name: str = _NAME
    parser_version: str = _VERSION
    normalization_profile: str = _PROFILE
    _verified: InitVar[object] = None

    def __post_init__(self, _verified: object) -> None:
        if _verified is not _VERIFIED:
            _fail("legacy_bill_invalid_result")
        self._validate()

    def _validate(self) -> None:
        try:
            bill = _validate_bill(
                {
                    "bill_id": self.source_id,
                    "bill_link": self.canonical_url,
                    "assembly_number": self.assembly_number,
                    "bill_name": self.bill_name,
                    "bill_number": self.bill_number,
                    "propose_date": self.propose_date,
                    "committee": self.committee,
                    "stage": self.stage,
                    "bill_result": self.bill_result,
                    "proposer_kind": self.proposer_kind,
                }
            )
            if (
                type(self.raw_bytes) is not int
                or not 0 < self.raw_bytes <= _MAX_RAW_BYTES
                or not _hash(self.raw_sha256)
                or not _hash(self.text_sha256)
                or type(self.text) is not str
                or self.text != _render(bill)
                or self.text_sha256 != sha256(self.text.encode("utf-8")).hexdigest()
                or self.parser_name != _NAME
                or self.parser_version != _VERSION
                or self.normalization_profile != _PROFILE
            ):
                raise ValueError
        except (AuditError, ValueError, TypeError, AttributeError, UnicodeError):
            _fail("legacy_bill_invalid_result")


def _no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError
        result[key] = value
    return result


def _no_constant(_: str) -> NoReturn:
    raise ValueError


def parse_legacy_bill_metadata(raw: bytes, *, expected_sha256: str) -> LegacyBillMetadata:
    """Verify exact JSON bytes and render collection-time metadata without I/O."""
    if type(raw) is not bytes:
        _fail("legacy_bill_invalid_raw")
    if not _hash(expected_sha256):
        raise AuditError("invalid_expected_sha256")
    if not raw:
        _fail("legacy_bill_invalid_raw")
    if len(raw) > _MAX_RAW_BYTES:
        _fail("legacy_bill_byte_limit_exceeded")
    raw_hash = sha256(raw).hexdigest()
    if raw_hash != expected_sha256:
        _fail("legacy_bill_hash_mismatch")
    try:
        bill = _validate_bill(
            json.loads(
                raw.decode("utf-8", errors="strict"),
                object_pairs_hook=_no_duplicates,
                parse_constant=_no_constant,
            )
        )
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _fail("legacy_bill_invalid_json")
    text = _render(bill)
    return LegacyBillMetadata(
        source_id=bill["bill_id"],
        canonical_url=bill["bill_link"],
        assembly_number=bill["assembly_number"],
        bill_name=bill["bill_name"],
        bill_number=bill["bill_number"],
        propose_date=bill["propose_date"],
        committee=bill["committee"],
        stage=bill["stage"],
        bill_result=bill["bill_result"],
        proposer_kind=bill["proposer_kind"],
        text=text,
        raw_sha256=raw_hash,
        raw_bytes=len(raw),
        text_sha256=sha256(text.encode("utf-8")).hexdigest(),
        _verified=_VERIFIED,
    )


def to_legacy_bill_representation(
    metadata: LegacyBillMetadata, *, representation_id: UUID, document_version_id: UUID
) -> ParsedRepresentation:
    """Attach caller-owned UUID4 identities to validated metadata text."""
    if type(metadata) is not LegacyBillMetadata:
        _fail("legacy_bill_invalid_result")
    metadata._validate()
    try:
        return ParsedRepresentation(
            representation_id=representation_id,
            document_version_id=document_version_id,
            parser_name=metadata.parser_name,
            parser_version=metadata.parser_version,
            normalization_profile=metadata.normalization_profile,
            text=metadata.text,
            text_sha256=metadata.text_sha256,
            pages=(),
            tables=(),
        )
    except ValidationError:
        _fail("legacy_bill_invalid_representation")


def locate_legacy_bill_quote(
    representation: ParsedRepresentation, *, quote: str, start: int | None = None
) -> TextQuoteSelector:
    """Locate an exact Unicode code-point quote; support is not evaluated."""
    try:
        if type(representation) is not ParsedRepresentation:
            raise ValueError
        valid = ParsedRepresentation.model_validate(representation.model_dump(warnings=False))
        if (
            valid.parser_name != _NAME
            or valid.parser_version != _VERSION
            or valid.normalization_profile != _PROFILE
            or valid.pages
            or valid.tables
            or not valid.text.startswith(_NOTICE, valid.text.find("\n") + 1)
        ):
            raise ValueError
    except (ValidationError, ValueError, TypeError, AttributeError, UnicodeError):
        _fail("legacy_bill_invalid_representation")
    try:
        if type(quote) is not str or not quote.strip():
            raise ValueError
        quote.encode("utf-8")
    except (ValueError, UnicodeError):
        _fail("invalid_quote")
    if start is not None and (type(start) is not int or start < 0):
        _fail("invalid_quote_start")
    text = valid.text
    if start is None:
        start = text.find(quote)
        if start < 0:
            _fail("quote_not_found")
        if text.find(quote, start + 1) >= 0:
            _fail("quote_ambiguous")
    elif text[start : start + len(quote)] != quote:
        _fail("quote_not_found")
    end = start + len(quote)
    return TextQuoteSelector(
        start=start,
        end=end,
        quote=quote,
        prefix=text[max(0, start - 80) : start] or None,
        suffix=text[end : end + 80] or None,
    )
