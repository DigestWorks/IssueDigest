"""Finite display modules and proposed user actions; no executable UI fields."""

from typing import Annotated, Literal, Self

from pydantic import UUID4, Field, model_validator

from .contract_values import ContractModel, MultipleIds, NonBlank, NonemptyIds


class OpenEvidenceAction(ContractModel):
    kind: Literal["open_evidence"]
    citation_id: UUID4


class SelectDocumentAction(ContractModel):
    kind: Literal["select_document"]
    document_id: UUID4


class AskQuestionAction(ContractModel):
    kind: Literal["ask_question"]
    question: NonBlank


class SortAction(ContractModel):
    kind: Literal["sort"]
    field: Literal["source_date", "title"]
    direction: Literal["asc", "desc"]


CanvasAction = Annotated[
    OpenEvidenceAction | SelectDocumentAction | AskQuestionAction | SortAction,
    Field(discriminator="kind"),
]


class _Module(ContractModel):
    module_id: UUID4
    title: NonBlank
    span: Literal["half", "full"]
    citation_ids: NonemptyIds
    actions: tuple[CanvasAction, ...]

    @model_validator(mode="after")
    def unique_actions(self) -> Self:
        if len(set(self.actions)) != len(self.actions):
            raise ValueError("identical actions must not repeat")
        return self


class EvidenceModule(_Module):
    kind: Literal["evidence"]


class SummaryModule(_Module):
    kind: Literal["summary"]
    claim_ids: NonemptyIds


class ComparisonModule(_Module):
    kind: Literal["comparison"]
    claim_ids: MultipleIds


class TimelineModule(_Module):
    kind: Literal["timeline"]
    claim_ids: NonemptyIds


class GraphModule(_Module):
    kind: Literal["graph"]
    relation_ids: NonemptyIds


class ChartModule(_Module):
    kind: Literal["chart"]
    observation_ids: MultipleIds
    chart_type: Literal["bar"]


CanvasModule = Annotated[
    EvidenceModule | SummaryModule | ComparisonModule | TimelineModule | GraphModule | ChartModule,
    Field(discriminator="kind"),
]
