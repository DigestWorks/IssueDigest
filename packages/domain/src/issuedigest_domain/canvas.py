"""Grounded internal proposals and immutable revisions; no renderer or storage CAS."""

from typing import Literal, Self
from uuid import UUID

from pydantic import UUID4, model_validator

from .canvas_modules import (
    CanvasModule,
    ChartModule,
    ComparisonModule,
    EvidenceModule,
    GraphModule,
    OpenEvidenceAction,
    SelectDocumentAction,
    SummaryModule,
    TimelineModule,
)
from .contract_values import (
    ContractModel,
    NonBlank,
    SafePositive,
    UniqueIds,
    UtcInstant,
    VersionedContract,
    index_records,
    require_model,
)
from .observations import assess_comparison
from .research import ResearchBundle


class CanvasDraft(VersionedContract):
    draft_id: UUID4
    outcome: Literal[
        "answer",
        "insufficient_evidence",
        "clarification_needed",
        "provider_refusal",
        "incomplete_output",
    ]
    modules: tuple[CanvasModule, ...]
    message: NonBlank | None

    @model_validator(mode="after")
    def consistent_outcome(self) -> Self:
        index_records(self.modules, "module_id")
        if self.outcome == "answer":
            if not self.modules or self.message is not None:
                raise ValueError("answer requires modules and no message")
        elif self.modules or self.message is None:
            raise ValueError("nonanswer requires an empty module tuple and message")
        return self


class CanvasRevision(VersionedContract):
    revision_id: UUID4
    workspace_id: UUID4
    run_id: UUID4
    revision_number: SafePositive
    parent_revision_id: UUID4 | None
    selected_version_ids: UniqueIds
    draft: CanvasDraft
    validated_at: UtcInstant
    validation_policy: Literal["issuedigest-canvas-v1"] = "issuedigest-canvas-v1"

    @model_validator(mode="after")
    def consistent_revision(self) -> Self:
        if self.draft.outcome in {"provider_refusal", "incomplete_output"}:
            raise ValueError("failed draft cannot become a revision")
        if self.parent_revision_id is None and self.revision_number != 1:
            raise ValueError("root revision must have number 1")
        if self.parent_revision_id == self.revision_id:
            raise ValueError("revision cannot be its own parent")
        return self


class CanvasBundle(ContractModel):
    research: ResearchBundle
    revision: CanvasRevision

    @model_validator(mode="after")
    def grounded_modules(self) -> Self:
        research, revision = self.research, self.revision
        if research.workspace_id != revision.workspace_id:
            raise ValueError("canvas research workspace mismatch")
        versions = {proof.version.version_id for proof in research.evidence}
        selected = set(revision.selected_version_ids)
        if not selected <= versions:
            raise ValueError("unknown selected version")
        selected_documents = {
            proof.document.document_id
            for proof in research.evidence
            if proof.version.version_id in selected
        }
        selected_citations = {
            citation.citation_id
            for proof in research.evidence
            if proof.version.version_id in selected
            for citation in proof.citations
        }
        claims = {claim.claim_id: claim for claim in research.claims}
        relations = {relation.relation_id: relation for relation in research.relations}
        observations = {
            observation.observation_id: observation for observation in research.observations
        }
        for module in revision.draft.modules:
            if not set(module.citation_ids) <= selected_citations:
                raise ValueError("module citations must exist in selected versions")
            citations: set[UUID] = set()
            if isinstance(module, (SummaryModule, ComparisonModule, TimelineModule)):
                for identity in module.claim_ids:
                    if identity not in claims:
                        raise ValueError("unknown claim reference")
                    claim = claims[identity]
                    if isinstance(module, TimelineModule) and claim.valid_period is None:
                        raise ValueError("timeline requires known claim valid_period")
                    citations.update(claim.citation_ids)
            elif isinstance(module, GraphModule):
                for identity in module.relation_ids:
                    if identity not in relations:
                        raise ValueError("unknown relation reference")
                    citations.update(relations[identity].citation_ids)
            elif isinstance(module, ChartModule):
                if any(identity not in observations for identity in module.observation_ids):
                    raise ValueError("unknown observation reference")
                values = tuple(observations[identity] for identity in module.observation_ids)
                if (
                    any(value.value is None for value in values)
                    or assess_comparison(values).status != "same_context"
                ):
                    raise ValueError("chart requires known values and same comparison context")
                citations.update(identity for value in values for identity in value.citation_ids)
            if not isinstance(module, EvidenceModule) and set(module.citation_ids) != citations:
                raise ValueError("module citations must equal referenced records' citation union")
            for action in module.actions:
                if (
                    isinstance(action, OpenEvidenceAction)
                    and action.citation_id not in module.citation_ids
                ):
                    raise ValueError("open_evidence must refer to this module's citations")
                if (
                    isinstance(action, SelectDocumentAction)
                    and action.document_id not in selected_documents
                ):
                    raise ValueError("select_document must refer to selected documents")
        return self


def promote_revision(
    current: CanvasRevision | None,
    candidate: CanvasBundle,
    expected_revision_id: UUID4 | None,
) -> CanvasRevision:
    """Validate a supplied successor; return it without mutating current or storage."""
    require_model(candidate, CanvasBundle)
    revision = candidate.revision
    if current is None:
        if (
            expected_revision_id is not None
            or revision.parent_revision_id is not None
            or revision.revision_number != 1
        ):
            raise ValueError("initial promotion requires no expected/parent revision and number 1")
    else:
        require_model(current, CanvasRevision)
        if current.revision_id != expected_revision_id:
            raise ValueError("expected revision conflict")
        if (
            revision.workspace_id != current.workspace_id
            or revision.revision_id == current.revision_id
        ):
            raise ValueError("successor must be a different revision in the same workspace")
        if (
            revision.parent_revision_id != current.revision_id
            or revision.revision_number != current.revision_number + 1
        ):
            raise ValueError("successor parent/number conflict")
    return revision
