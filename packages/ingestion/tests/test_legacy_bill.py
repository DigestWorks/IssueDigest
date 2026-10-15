"""Synthetic legacy Bill metadata; no rows or values from the collection database."""

import json
from dataclasses import FrozenInstanceError, asdict, replace
from hashlib import sha256
from uuid import UUID

import pytest
from issuedigest_domain.citations import Citation, validate_citation
from issuedigest_ingestion import (
    AuditError,
    LegacyBillMetadata,
    locate_legacy_bill_quote,
    parse_legacy_bill_metadata,
    to_legacy_bill_representation,
)

SOURCE_ID = "SYNTHETIC_42"
URL = f"https://likms.assembly.go.kr/bill/billDetail.do?billId={SOURCE_ID}"
VERSION = UUID("11111111-1111-4111-8111-111111111111")
REPRESENTATION = UUID("22222222-2222-4222-8222-222222222222")


def bill(**changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "bill_id": SOURCE_ID,
        "assembly_number": 22,
        "bill_name": "합성 고등교육 법안😀",
        "bill_number": 2200001,
        "propose_date": "2026-03-30",
        "committee": "합성 위원회",
        "stage": None,
        "bill_result": None,
        "proposer_kind": "CONGRESSMAN",
        "bill_link": URL,
    }
    value.update(changes)
    return value


def raw_bill(**changes: object) -> bytes:
    return json.dumps(bill(**changes), ensure_ascii=False).encode("utf-8")


def parse(raw: bytes):
    return parse_legacy_bill_metadata(raw, expected_sha256=sha256(raw).hexdigest())


def test_renders_historical_metadata_and_exact_quote_with_version_bound_ids():
    raw = raw_bill()
    result = parse(raw)
    expected = (
        "합성 고등교육 법안😀\n"
        "기존 수집 DB의 법안 기본 정보입니다. "
        "법안 전문이 아니며 현재 처리 상태는 원문 출처에서 확인해 주세요.\n"
        "대수: 22대\n의안번호: 2200001\n제안일: 2026-03-30\n위원회: 합성 위원회\n"
        "수집 당시 단계: 미수집\n수집 당시 처리결과: 미수집\n발의구분: 의원 발의"
    )
    assert result.text == expected
    assert (result.raw_sha256, result.raw_bytes) == (sha256(raw).hexdigest(), len(raw))
    assert result.text_sha256 == sha256(expected.encode()).hexdigest()
    assert (result.source_id, result.canonical_url, result.bill_number, result.propose_date) == (
        SOURCE_ID,
        URL,
        2200001,
        "2026-03-30",
    )
    assert (result.parser_name, result.parser_version, result.normalization_profile) == (
        "legacy-bill-metadata",
        "1",
        "legacy-bill-metadata-v1",
    )
    with pytest.raises(FrozenInstanceError):
        result.text = "changed"
    representation = to_legacy_bill_representation(
        result, representation_id=REPRESENTATION, document_version_id=VERSION
    )
    assert representation.text == expected
    assert representation.text_sha256 == result.text_sha256
    assert (representation.pages, representation.tables) == ((), ())
    selector = locate_legacy_bill_quote(representation, quote="고등교육 법안😀")
    assert (selector.start, selector.end) == (3, 11)
    assert selector.prefix == "합성 "
    citation = Citation(
        citation_id=UUID("33333333-3333-4333-8333-333333333333"),
        document_version_id=VERSION,
        representation_id=REPRESENTATION,
        selector=selector,
    )
    assert validate_citation(citation, representation).anchor_status == "matched"


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b"\xff",
        b"{",
        b"[]",
        b'{"bill_id":"A","bill_id":"B"}',
        b'{"bill_id":NaN}',
        raw_bill(summary="AI text"),
        raw_bill(gpt_summary="AI text"),
        raw_bill(derived_title="AI text"),
        raw_bill(bill_name=""),
        raw_bill(bill_name="  "),
        raw_bill(bill_name="bad\nline"),
        raw_bill(bill_name="bad\x00name"),
        raw_bill(bill_name="x" * 256),
        raw_bill(bill_id="한글"),
        raw_bill(bill_id="A-B"),
        raw_bill(assembly_number=True),
        raw_bill(assembly_number=0),
        raw_bill(assembly_number=100),
        raw_bill(bill_number=True),
        raw_bill(bill_number=220001),
        raw_bill(bill_number=2300001),
        raw_bill(propose_date="2026-02-30"),
        raw_bill(propose_date="2026-3-30"),
        raw_bill(proposer_kind="OTHER"),
        raw_bill(committee="x\u007f"),
        raw_bill(bill_link=URL + "&extra=1"),
        raw_bill(bill_link=URL + "#fragment"),
        raw_bill(bill_link=URL.replace("https", "http")),
        raw_bill(bill_link=URL.replace("likms", "LIKMS")),
        raw_bill(bill_link=URL.replace(SOURCE_ID, "DIFFERENT")),
        raw_bill(bill_link=URL.replace("likms", "user@likms")),
        raw_bill(bill_link=URL.replace("billDetail.do", "billDetail.do:443")),
        raw_bill(bill_link=URL.replace("billId", "bill%49d")),
        json.dumps({k: v for k, v in bill().items() if k != "committee"}).encode(),
        raw_bill() + b" " * 65536,
    ],
)
def test_rejects_untrusted_bytes_and_fields_with_only_fixed_errors(raw):
    with pytest.raises(AuditError) as caught:
        parse(raw)
    assert str(caught.value).startswith("legacy_bill_")
    assert "SYNTHETIC" not in str(caught.value)


def test_rejects_wrong_hash_before_decoding_and_wrong_hash_format():
    with pytest.raises(AuditError, match="^legacy_bill_hash_mismatch$"):
        parse_legacy_bill_metadata(b"\xff", expected_sha256="0" * 64)
    with pytest.raises(AuditError, match="^invalid_expected_sha256$"):
        parse_legacy_bill_metadata(raw_bill(), expected_sha256="A" * 64)


def test_deep_json_is_a_fixed_error_instead_of_a_parser_exception():
    raw = b"[" * 10_000 + b"0" + b"]" * 10_000
    with pytest.raises(AuditError, match="^legacy_bill_invalid_json$"):
        parse(raw)


@pytest.mark.parametrize(
    ("kind", "label"),
    [
        ("CHAIRMAN", "위원장 제안"),
        ("CONGRESSMAN", "의원 발의"),
        ("GOVERNMENT", "정부 제출"),
        (None, "미수집"),
    ],
)
def test_renders_proposer_kind_for_readers_without_losing_source_enum(kind, label):
    result = parse(raw_bill(proposer_kind=kind))
    assert result.text.splitlines()[-1] == f"발의구분: {label}"
    assert result.proposer_kind == kind


def test_direct_result_construction_and_adapter_reject_tampering():
    result = parse(raw_bill())
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        LegacyBillMetadata(**asdict(result))
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        replace(result, raw_sha256="0" * 64)
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        replace(result, raw_bytes=1)
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        replace(result, text="false")
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        replace(result, canonical_url=URL + "#x")
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        replace(result, bill_number=2300001)
    with pytest.raises(AuditError, match="^legacy_bill_invalid_result$"):
        to_legacy_bill_representation(
            "untrusted", representation_id=REPRESENTATION, document_version_id=VERSION
        )  # type: ignore[arg-type]
    with pytest.raises(AuditError, match="^legacy_bill_invalid_representation$"):
        to_legacy_bill_representation(
            result,
            representation_id="not-a-uuid",
            document_version_id=VERSION,  # type: ignore[arg-type]
        )


def test_quote_locator_rejects_ambiguity_and_invalid_representation():
    result = parse(raw_bill(bill_name="반복 반복"))
    representation = to_legacy_bill_representation(
        result, representation_id=REPRESENTATION, document_version_id=VERSION
    )
    with pytest.raises(AuditError, match="^quote_ambiguous$"):
        locate_legacy_bill_quote(representation, quote="반복")
    selector = locate_legacy_bill_quote(representation, quote="반복", start=3)
    assert (selector.start, selector.end) == (3, 5)
    with pytest.raises(AuditError, match="^invalid_quote_start$"):
        locate_legacy_bill_quote(representation, quote="반복", start=True)
    with pytest.raises(AuditError, match="^quote_not_found$"):
        locate_legacy_bill_quote(representation, quote="반복", start=1)
    with pytest.raises(AuditError, match="^legacy_bill_invalid_representation$"):
        locate_legacy_bill_quote("untrusted", quote="반복")  # type: ignore[arg-type]
