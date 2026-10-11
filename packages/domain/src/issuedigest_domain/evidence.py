"""Single-document immutable evidence transport; no storage or authorization."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from .citations import Citation, validate_citation
from .sources import DocumentVersion, ParsedRepresentation, SourceDocument


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    document: SourceDocument
    version: DocumentVersion
    representation: ParsedRepresentation
    citations: tuple[Citation, ...]

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_chain(self) -> Self:
        if self.version.document_id != self.document.document_id:
            raise ValueError("version document_id does not match document")
        if self.representation.document_version_id != self.version.version_id:
            raise ValueError("representation document_version_id does not match version")
        if len({citation.citation_id for citation in self.citations}) != len(self.citations):
            raise ValueError("citation_id must be unique within a bundle")
        for citation in self.citations:
            validate_citation(citation, self.representation)
        return self
