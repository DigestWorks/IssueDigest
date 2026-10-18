"""Pure private comparison of exact policy captures; no collection or registration."""

import json
from hashlib import sha256
from typing import Annotated, Literal

from issuedigest_connectors import PolicyCapture, parse_policy_capture
from issuedigest_ingestion import extract_policy_html
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .models import PreparationError

MAX_POLICY_CHANGE_REPORT_BYTES = 64 * 1024
_Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_SemanticField = Literal[
    "text_sha256",
    "title",
    "publisher",
    "publication_date",
    "license_notice",
    "license_url",
    "parser_name",
    "parser_version",
    "normalization_profile",
]
_FIELDS: tuple[_SemanticField, ...] = (
    "text_sha256",
    "title",
    "publisher",
    "publication_date",
    "license_notice",
    "license_url",
    "parser_name",
    "parser_version",
    "normalization_profile",
)


class _PrivateModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class PolicySourceChange(_PrivateModel):
    source_id: Annotated[str, Field(pattern=r"^[0-9]{9}$")] = Field(repr=False)
    status: Literal["new", "changed", "unchanged", "not_observed"]
    before_fingerprint: _Digest | None = Field(repr=False)
    after_fingerprint: _Digest | None = Field(repr=False)
    changed_fields: tuple[_SemanticField, ...]


class PolicyChangeReport(_PrivateModel):
    schema_version: Literal[1]
    profile: Literal["policy-change-v1"]
    before_capture_sha256: _Digest | None = Field(repr=False)
    before_collected_at: AwareDatetime | None = Field(repr=False)
    after_capture_sha256: _Digest = Field(repr=False)
    after_collected_at: AwareDatetime = Field(repr=False)
    sources: Annotated[tuple[PolicySourceChange, ...], Field(min_length=1, max_length=4)] = Field(
        repr=False
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid report version")
        return value


def _semantics(capture: PolicyCapture) -> dict[str, dict[_SemanticField, str]]:
    result: dict[str, dict[_SemanticField, str]] = {}
    for article in capture.articles:
        raw = article.html.encode("utf-8")
        extraction = extract_policy_html(
            raw, expected_sha256=sha256(raw).hexdigest(), canonical_url=article.canonical_url
        )
        result[extraction.source_id] = {
            "text_sha256": extraction.text_sha256,
            "title": extraction.title,
            "publisher": extraction.publisher,
            "publication_date": extraction.publication_date.isoformat(),
            "license_notice": extraction.license_notice,
            "license_url": extraction.license_url,
            "parser_name": extraction.parser_name,
            "parser_version": extraction.parser_version,
            "normalization_profile": extraction.normalization_profile,
        }
    return result


def _fingerprint(semantic: dict[_SemanticField, str] | None) -> str | None:
    if semantic is None:
        return None
    return sha256(
        json.dumps(
            semantic, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def compare_policy_captures(
    current_raw: bytes, *, previous_raw: bytes | None = None
) -> PolicyChangeReport:
    """Compare validated semantics only; absence is not evidence of deletion/withdrawal."""
    try:
        if type(current_raw) is not bytes or (
            previous_raw is not None and type(previous_raw) is not bytes
        ):
            raise ValueError("Exact capture bytes required")
        current = parse_policy_capture(current_raw)
        previous = parse_policy_capture(previous_raw) if previous_raw is not None else None
        if previous is not None and (
            current.collected_at < previous.collected_at
            or (current.collected_at == previous.collected_at and current_raw != previous_raw)
        ):
            raise ValueError("Ambiguous capture order")
        after = _semantics(current)
        before = _semantics(previous) if previous is not None else {}
        sources: list[PolicySourceChange] = []
        for source_id in sorted(before.keys() | after.keys()):
            old, new = before.get(source_id), after.get(source_id)
            changed_fields: tuple[_SemanticField, ...] = ()
            status: Literal["new", "changed", "unchanged", "not_observed"]
            if old is None:
                status = "new"
            elif new is None:
                status = "not_observed"
            else:
                changed_fields = tuple(
                    sorted(field for field in _FIELDS if old[field] != new[field])
                )
                status = "changed" if changed_fields else "unchanged"
            sources.append(
                PolicySourceChange(
                    source_id=source_id,
                    status=status,
                    before_fingerprint=_fingerprint(old),
                    after_fingerprint=_fingerprint(new),
                    changed_fields=changed_fields,
                )
            )
        report = PolicyChangeReport(
            schema_version=1,
            profile="policy-change-v1",
            before_capture_sha256=sha256(previous_raw).hexdigest()
            if previous_raw is not None
            else None,
            before_collected_at=previous.collected_at if previous is not None else None,
            after_capture_sha256=sha256(current_raw).hexdigest(),
            after_collected_at=current.collected_at,
            sources=tuple(sources),
        )
        if (
            len(report.model_dump_json(warnings="error").encode("utf-8"))
            > MAX_POLICY_CHANGE_REPORT_BYTES
        ):
            raise ValueError("Report size exceeded")
        return report
    except Exception:
        raise PreparationError("Unable to compare policy captures") from None
