"""Limited, versioned directional vocabulary; no graph projection or inference."""

from typing import Annotated, Literal, Self

from pydantic import UUID4, BaseModel, ConfigDict, Field, model_validator

from .knowledge import (
    CitationIds,
    ClaimBasis,
    ClaimReference,
    DerivationRecord,
    DocumentReference,
    EntityReference,
    validate_derivation,
)
from .observations import DateInterval

RelationEndpoint = Annotated[
    EntityReference | ClaimReference | DocumentReference, Field(discriminator="kind")
]
RelationPredicate = Literal[
    "introduced_by", "reviewed_by", "alternative_to", "supports", "contradicts", "mentions"
]


class Relation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    relation_id: UUID4
    workspace_id: UUID4
    ontology_version: Literal["issuedigest-relations-v1"] = "issuedigest-relations-v1"
    predicate: RelationPredicate
    source: RelationEndpoint
    target: RelationEndpoint
    basis: ClaimBasis
    citation_ids: CitationIds
    valid_period: DateInterval | None = None
    derivation: DerivationRecord | None = None

    @model_validator(mode="after")
    def valid_structure(self) -> Self:
        validate_derivation(self.basis, self.derivation)
        if len(set(self.citation_ids)) != len(self.citation_ids):
            raise ValueError("relation citation_ids must be unique")
        if self.source == self.target:
            raise ValueError("same typed endpoint self relation is not allowed")
        expected = {
            "introduced_by": ("entity", "entity"),
            "reviewed_by": ("entity", "entity"),
            "alternative_to": ("entity", "entity"),
            "supports": ("claim", "claim"),
            "contradicts": ("claim", "claim"),
            "mentions": ("document", "entity"),
        }[self.predicate]
        if (self.source.kind, self.target.kind) != expected:
            raise ValueError("relation endpoint tags do not match predicate direction")
        return self
