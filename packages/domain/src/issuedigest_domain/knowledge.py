"""Explicit identity, attributed claims, derivation and supplied review records."""

import re
from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import (
    UUID4,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from .observations import DateInterval
from .sources import NonBlank

EntityKind = Literal["person", "organization", "bill", "policy", "issue", "place"]
ClaimBasis = Literal["source_assertion", "observation", "inference"]
CitationIds = Annotated[tuple[UUID4, ...], Field(min_length=1)]


class SourceIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    provider: NonBlank
    namespace: NonBlank
    value: NonBlank


class _ReviewMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    review_id: UUID4
    reviewer_kind: Literal["human", "automated"]
    reviewer_id: NonBlank
    method: NonBlank
    method_version: NonBlank
    reviewed_at: AwareDatetime
    rationale: NonBlank
    citation_ids: CitationIds

    @field_validator("reviewed_at", mode="before")
    @classmethod
    def datetime_input(cls, value: object) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and re.match(r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ]", value):
            return datetime.fromisoformat(value)
        raise ValueError("reviewed_at requires datetime or ISO datetime string")

    @field_validator("reviewed_at")
    @classmethod
    def utc_instant(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def unique_citations(self) -> Self:
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("review citation_ids must be unique")
        return self


class IdentityReview(_ReviewMetadata):
    assessment: Literal["confirmed", "ambiguous"]


class Entity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: UUID4
    workspace_id: UUID4
    kind: EntityKind
    name: NonBlank
    aliases: tuple[NonBlank, ...] = ()
    source_identities: tuple[SourceIdentity, ...] = ()
    valid_period: DateInterval | None = None
    raw_validity_text: NonBlank | None = None
    identity_review: IdentityReview | None = None

    @model_validator(mode="after")
    def unique_identity_inputs(self) -> Self:
        if len(set(self.aliases)) != len(self.aliases):
            raise ValueError("aliases must be unique")
        keys = [
            (identity.provider, identity.namespace, identity.value)
            for identity in self.source_identities
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("source identities must be unique")
        return self


class EntityReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["entity"] = "entity"
    entity_id: UUID4


class ClaimReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["claim"] = "claim"
    claim_id: UUID4


class DocumentReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["document"] = "document"
    document_id: UUID4


class RelationReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    kind: Literal["relation"] = "relation"
    relation_id: UUID4


class DerivationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    method: NonBlank
    method_version: NonBlank
    rationale: NonBlank


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: UUID4
    workspace_id: UUID4
    text: NonBlank
    basis: ClaimBasis
    speaker_entity_id: UUID4 | None = None
    subject_entity_ids: tuple[UUID4, ...] = ()
    citation_ids: CitationIds
    valid_period: DateInterval | None = None
    raw_event_time_text: NonBlank | None = None
    derivation: DerivationRecord | None = None

    @model_validator(mode="after")
    def valid_basis_and_references(self) -> Self:
        validate_derivation(self.basis, self.derivation)
        if len(set(self.subject_entity_ids)) != len(self.subject_entity_ids):
            raise ValueError("subject_entity_ids must be unique")
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("claim citation_ids must be unique")
        return self


def validate_derivation(basis: ClaimBasis, derivation: DerivationRecord | None) -> None:
    """Check recorded inference provenance, without judging its meaning."""
    if (basis == "inference") != (derivation is not None):
        raise ValueError("derivation is required exclusively for inference")


class SupportReview(_ReviewMetadata):
    target: Annotated[ClaimReference | RelationReference, Field(discriminator="kind")]
    scope: Literal["attribution", "content", "relation"]
    assessment: Literal["supported", "contradicted", "insufficient"]

    @model_validator(mode="after")
    def target_scope(self) -> Self:
        if (self.target.kind == "relation") != (self.scope == "relation"):
            raise ValueError("review scope must match target kind")
        return self
