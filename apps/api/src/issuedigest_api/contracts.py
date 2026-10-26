"""Register domain-only components without inventing HTTP endpoints."""

from copy import deepcopy
from typing import Any

from issuedigest_domain import (
    BudgetAssessment,
    CanvasBundle,
    CitationAnchorValidation,
    ComparisonAssessment,
    EvidenceBundle,
    EvidenceCatalog,
    EvidenceSearchQuery,
    EvidenceSearchResult,
    ReplayBatch,
    ResearchBundle,
    RunExecutionBundle,
    RunHistory,
    SessionInfo,
    SubmissionAssessment,
    UsageBook,
)
from issuedigest_domain.question_submission import (
    BriefingJobList,
    BriefingJobSummary,
    QuestionSubmissionErrorEvent,
    QuestionSubmissionProgress,
    QuestionSubmissionRequest,
    QuestionSubmissionResult,
)
from issuedigest_domain.research_journey import ResearchRequest
from pydantic.json_schema import models_json_schema

from .errors import EvidenceSearchRequestError


def add_evidence_schemas(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a new OpenAPI document; reject all existing component name collisions."""
    _, definitions = models_json_schema(
        [
            (ResearchRequest, "validation"),
            (BriefingJobList, "validation"),
            (BriefingJobSummary, "validation"),
            (QuestionSubmissionRequest, "validation"),
            (QuestionSubmissionResult, "validation"),
            (QuestionSubmissionProgress, "validation"),
            (QuestionSubmissionErrorEvent, "validation"),
            (RunHistory, "validation"),
            (ReplayBatch, "validation"),
            (SubmissionAssessment, "validation"),
            (CanvasBundle, "validation"),
            (UsageBook, "validation"),
            (BudgetAssessment, "validation"),
            (RunExecutionBundle, "validation"),
            (EvidenceBundle, "validation"),
            (SessionInfo, "validation"),
            (EvidenceCatalog, "validation"),
            (EvidenceSearchQuery, "validation"),
            (EvidenceSearchResult, "validation"),
            (EvidenceSearchRequestError, "validation"),
            (CitationAnchorValidation, "validation"),
            (ResearchBundle, "validation"),
            (ComparisonAssessment, "validation"),
        ],
        ref_template="#/components/schemas/{model}",
    )
    result = deepcopy(schema)
    schemas = result.setdefault("components", {}).setdefault("schemas", {})
    additions = definitions["$defs"]

    def without_defaults(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: without_defaults(item) for key, item in value.items() if key != "default"}
        if isinstance(value, list):
            return [without_defaults(item) for item in value]
        return value

    collisions = {
        name
        for name in schemas.keys() & additions.keys()
        if without_defaults(schemas[name]) != without_defaults(additions[name])
    }
    if collisions:
        raise ValueError(f"OpenAPI component name collision: {', '.join(sorted(collisions))}")
    schemas.update(additions)
    return result
