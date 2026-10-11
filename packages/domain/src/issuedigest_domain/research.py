"""Immutable workspace research transport with supplied-object integrity checks."""

from typing import Literal, Self
from uuid import UUID

from pydantic import UUID4, BaseModel, ConfigDict, field_validator, model_validator

from .evidence import EvidenceBundle
from .knowledge import (
    Claim,
    ClaimReference,
    DocumentReference,
    Entity,
    EntityReference,
    IdentityReview,
    SupportReview,
)
from .observations import Observation
from .relations import Relation, RelationEndpoint
from .sources import DocumentVersion, SourceDocument


class ResearchBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    schema_version: Literal[1] = 1
    workspace_id: UUID4
    evidence: tuple[EvidenceBundle, ...]
    entities: tuple[Entity, ...]
    claims: tuple[Claim, ...]
    relations: tuple[Relation, ...]
    observations: tuple[Observation, ...]
    support_reviews: tuple[SupportReview, ...]

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_references(self) -> Self:
        entities = _index(self.entities, "entity_id")
        claims = _index(self.claims, "claim_id")
        relations = _index(self.relations, "relation_id")
        _index(self.observations, "observation_id")
        reviews: tuple[IdentityReview | SupportReview, ...] = (
            *(
                entity.identity_review
                for entity in self.entities
                if entity.identity_review is not None
            ),
            *self.support_reviews,
        )
        _index(reviews, "review_id")
        workspace_records: tuple[Entity | Claim | Relation | Observation, ...] = (
            *self.entities,
            *self.claims,
            *self.relations,
            *self.observations,
        )
        for record in workspace_records:
            if record.workspace_id != self.workspace_id:
                raise ValueError("record workspace_id does not match research bundle")
        documents: dict[UUID, SourceDocument] = {}
        versions: dict[UUID, DocumentVersion] = {}
        representations: set[UUID] = set()
        citation_documents: dict[UUID, UUID] = {}
        for proof in self.evidence:
            if proof.document.workspace_id != self.workspace_id:
                raise ValueError("document workspace_id does not match research bundle")
            _consistent_object(documents, proof.document.document_id, proof.document)
            _consistent_object(versions, proof.version.version_id, proof.version)
            if proof.representation.representation_id in representations:
                raise ValueError("representation_id must be unique across evidence")
            representations.add(proof.representation.representation_id)
            for citation in proof.citations:
                if citation.citation_id in citation_documents:
                    raise ValueError("citation_id must be unique across evidence")
                citation_documents[citation.citation_id] = proof.document.document_id
        for cited_record in (*self.claims, *self.relations, *self.observations, *reviews):
            if any(identity not in citation_documents for identity in cited_record.citation_ids):
                raise ValueError("unknown citation reference")
        identities: dict[tuple[str, str, str], UUID] = {}
        for entity in self.entities:
            for identity in entity.source_identities:
                key = (identity.provider, identity.namespace, identity.value)
                if key in identities:
                    raise ValueError("external source identity belongs to multiple entities")
                identities[key] = entity.entity_id
        for claim in self.claims:
            if claim.speaker_entity_id is not None and claim.speaker_entity_id not in entities:
                raise ValueError("unknown speaker entity")
            if any(identity not in entities for identity in claim.subject_entity_ids):
                raise ValueError("unknown subject entity")
        for observation in self.observations:
            if (
                observation.subject_entity_id is not None
                and observation.subject_entity_id not in entities
            ):
                raise ValueError("unknown observation subject entity")
        for relation in self.relations:
            _resolve_endpoint(relation.source, entities, claims, documents)
            _resolve_endpoint(relation.target, entities, claims, documents)
            if isinstance(relation.source, EntityReference) and isinstance(
                relation.target, EntityReference
            ):
                source_kind = entities[relation.source.entity_id].kind
                target_kind = entities[relation.target.entity_id].kind
                allowed_targets = {
                    "introduced_by": {"person", "organization"},
                    "reviewed_by": {"organization"},
                    "alternative_to": {"bill"},
                }[relation.predicate]
                if source_kind != "bill" or target_kind not in allowed_targets:
                    raise ValueError("entity kinds do not match predicate direction")
            if relation.predicate == "mentions":
                # Local Relation validation guarantees the document source tag.
                if not isinstance(relation.source, DocumentReference):
                    raise ValueError("mentions requires a document source")
                if any(
                    citation_documents[identity] != relation.source.document_id
                    for identity in relation.citation_ids
                ):
                    raise ValueError("mentions citations must belong to the source document")
        for review in self.support_reviews:
            target: Claim | Relation | None
            if isinstance(review.target, ClaimReference):
                target = claims.get(review.target.claim_id)
            else:
                target = relations.get(review.target.relation_id)
            if target is None:
                raise ValueError("unknown support review target")
            if not set(review.citation_ids) <= set(target.citation_ids):
                raise ValueError("review citations must be a subset of target citations")
        return self


def _index[T: BaseModel](records: tuple[T, ...], field: str) -> dict[UUID, T]:
    index: dict[UUID, T] = {}
    for record in records:
        identity = getattr(record, field)
        if identity in index:
            raise ValueError(f"{field} must be unique within research bundle")
        index[identity] = record
    return index


def _consistent_object[T: BaseModel](index: dict[UUID, T], identity: UUID, record: T) -> None:
    if identity in index and index[identity] != record:
        raise ValueError("shared document/version ID has conflicting metadata")
    index[identity] = record


def _resolve_endpoint(
    endpoint: RelationEndpoint,
    entities: dict[UUID, Entity],
    claims: dict[UUID, Claim],
    documents: dict[UUID, SourceDocument],
) -> None:
    if isinstance(endpoint, EntityReference):
        exists = endpoint.entity_id in entities
    elif isinstance(endpoint, ClaimReference):
        exists = endpoint.claim_id in claims
    else:
        exists = endpoint.document_id in documents
    if not exists:
        raise ValueError("unknown typed relation endpoint")
