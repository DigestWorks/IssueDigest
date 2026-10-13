"""Immutable session and protected workspace catalog contracts."""

from typing import Annotated, Literal, Self

from pydantic import UUID4, AnyHttpUrl, Field, StrictBool, field_validator, model_validator

from .contract_values import ContractModel, UtcInstant, VersionedContract
from .sources import NonBlank, NonNegativeInt, SourceKind, SourceUrl


class WorkspaceMembership(ContractModel):
    workspace_id: UUID4
    role: Literal["viewer", "editor", "owner"]


class SessionInfo(VersionedContract):
    user_id: UUID4
    memberships: Annotated[tuple[WorkspaceMembership, ...], Field(max_length=100)]

    @model_validator(mode="after")
    def ordered_unique_memberships(self) -> Self:
        ids = [str(item.workspace_id) for item in self.memberships]
        if ids != sorted(set(ids)):
            raise ValueError("memberships must have unique workspace IDs in ascending order")
        return self


class EvidenceSummary(ContractModel):
    snapshot_id: UUID4
    document_id: UUID4
    provider: NonBlank
    source_id: NonBlank
    source_kind: SourceKind
    canonical_url: SourceUrl | None = None
    collected_at: UtcInstant
    excerpt: Annotated[str, Field(max_length=160)]
    citation_count: NonNegativeInt

    @field_validator("canonical_url")
    @classmethod
    def no_url_credentials(cls, value: AnyHttpUrl | None) -> AnyHttpUrl | None:
        if value is not None and (value.username is not None or value.password is not None):
            raise ValueError("source URL must not include credentials")
        return value


class EvidenceCatalog(VersionedContract):
    workspace_id: UUID4
    items: Annotated[tuple[EvidenceSummary, ...], Field(max_length=50)]
    has_more: StrictBool

    @model_validator(mode="after")
    def unique_snapshots(self) -> Self:
        if len({item.snapshot_id for item in self.items}) != len(self.items):
            raise ValueError("catalog snapshot IDs must be unique")
        return self
