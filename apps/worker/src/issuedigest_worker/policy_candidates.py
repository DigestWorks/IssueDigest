"""Pure comparison of visible list metadata; no article or rights assessment."""

from datetime import date
from hashlib import sha256
from typing import Annotated, Literal

from issuedigest_connectors import (
    PolicyCandidateMetadata,
    parse_policy_discovery,
    policy_candidate_metadata,
)
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from .models import PreparationError

MAX_POLICY_CANDIDATE_REPORT_BYTES = 512 * 1024
_Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
_Status = Literal["new", "unchanged", "metadata_changed", "not_observed"]


class PolicyCandidateEntry(PolicyCandidateMetadata):
    status: _Status


class PolicyCandidateReport(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)

    schema_version: Literal[1]
    current_discovery_sha256: _Digest = Field(repr=False)
    current_collected_at: AwareDatetime = Field(repr=False)
    previous_discovery_sha256: _Digest | None = Field(repr=False)
    previous_collected_at: AwareDatetime | None = Field(repr=False)
    since: date = Field(repr=False)
    through: date = Field(repr=False)
    entries: Annotated[tuple[PolicyCandidateEntry, ...], Field(max_length=200)] = Field(repr=False)

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid report version")
        return value


def build_policy_candidate_report(
    current_raw: bytes,
    *,
    since: date,
    through: date,
    previous_raw: bytes | None = None,
) -> PolicyCandidateReport:
    """Report first observations and metadata differences inside an inclusive date window."""
    try:
        if (
            type(current_raw) is not bytes
            or (previous_raw is not None and type(previous_raw) is not bytes)
            or type(since) is not date
            or type(through) is not date
            or since > through
        ):
            raise ValueError("Invalid report inputs")
        current = parse_policy_discovery(current_raw)
        previous = parse_policy_discovery(previous_raw) if previous_raw is not None else None
        if previous is not None and previous.collected_at >= current.collected_at:
            raise ValueError("Ambiguous discovery order")
        after = {item.news_id: item for item in policy_candidate_metadata(current)}
        before = (
            {item.news_id: item for item in policy_candidate_metadata(previous)}
            if previous is not None
            else {}
        )
        entries: list[PolicyCandidateEntry] = []
        for identity in sorted(after.keys() | before.keys()):
            item = after.get(identity)
            status: _Status
            if item is not None:
                if not since <= item.published_on <= through:
                    continue
                old = before.get(identity)
                status = (
                    "new" if old is None else "unchanged" if old == item else "metadata_changed"
                )
            else:
                item = before[identity]
                if not since <= item.published_on <= through:
                    continue
                status = "not_observed"
            entries.append(PolicyCandidateEntry(**item.model_dump(), status=status))
        report = PolicyCandidateReport(
            schema_version=1,
            current_discovery_sha256=sha256(current_raw).hexdigest(),
            current_collected_at=current.collected_at,
            previous_discovery_sha256=sha256(previous_raw).hexdigest()
            if previous_raw is not None
            else None,
            previous_collected_at=previous.collected_at if previous is not None else None,
            since=since,
            through=through,
            entries=tuple(entries),
        )
        if (
            len(report.model_dump_json(warnings="error").encode("utf-8"))
            > MAX_POLICY_CANDIDATE_REPORT_BYTES
        ):
            raise ValueError("Report size exceeded")
        return report
    except Exception:
        raise PreparationError("Unable to build policy candidate report") from None
