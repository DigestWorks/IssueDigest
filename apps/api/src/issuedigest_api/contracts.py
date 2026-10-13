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
    ReplayBatch,
    ResearchBundle,
    RunExecutionBundle,
    RunHistory,
    SessionInfo,
    SubmissionAssessment,
    UsageBook,
)
from pydantic.json_schema import models_json_schema


def add_evidence_schemas(schema: dict[str, Any]) -> dict[str, Any]:
    """Return a new OpenAPI document; reject all existing component name collisions."""
    _, definitions = models_json_schema(
        [
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
            (CitationAnchorValidation, "validation"),
            (ResearchBundle, "validation"),
            (ComparisonAssessment, "validation"),
        ],
        ref_template="#/components/schemas/{model}",
    )
    result = deepcopy(schema)
    schemas = result.setdefault("components", {}).setdefault("schemas", {})
    additions = definitions["$defs"]
    collisions = schemas.keys() & additions.keys()
    if collisions:
        raise ValueError(f"OpenAPI component name collision: {', '.join(sorted(collisions))}")
    schemas.update(additions)
    return result
