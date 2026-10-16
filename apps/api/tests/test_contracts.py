"""Components travel through the real API/export boundary without fake routes."""

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from issuedigest_api import main


def walk_references(value):
    if isinstance(value, dict):
        if "$ref" in value:
            yield value["$ref"]
        for child in value.values():
            yield from walk_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_references(child)


def test_evidence_components_resolve_with_canonical_protected_http_path():
    schema = TestClient(main.app).get("/openapi.json").json()
    assert set(schema["paths"]) == {
        "/health/live",
        "/api/v1/status",
        "/api/v1/briefings",
        "/api/v1/briefings/{slug}",
        "/api/v1/briefings/{slug}/versions/{version}",
        "/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}",
        "/api/v1/workspaces/{workspace_id}/evidence",
        "/api/v1/workspaces/{workspace_id}/evidence/search",
        "/api/v1/workspaces/{workspace_id}/research",
        "/api/v1/workspaces/{workspace_id}/research/{run_id}",
        "/api/v1/workspaces/{workspace_id}/research/{run_id}/cancel",
        "/api/v1/auth/google/start",
        "/api/v1/auth/google/callback",
        "/api/v1/auth/session",
        "/api/v1/auth/logout",
    }
    schemas = schema["components"]["schemas"]
    assert "EvidenceBundle" in schemas
    assert "CitationAnchorValidation" in schemas
    assert schemas["Citation"]["properties"]["selector"]["discriminator"]["propertyName"] == "kind"
    for reference in walk_references(schema):
        assert reference.startswith("#/components/schemas/")
        assert reference.removeprefix("#/components/schemas/") in schemas


def test_http_and_export_script_produce_identical_contract(tmp_path):
    output = tmp_path / "openapi.json"
    root = Path(__file__).parents[3]
    subprocess.run(
        [sys.executable, str(root / "scripts/export_openapi.py"), str(output)], cwd=root, check=True
    )
    assert json.loads(output.read_text()) == TestClient(main.app).get("/openapi.json").json()


def test_catalog_limit_publishes_standard_integer_bounds():
    schema = TestClient(main.app).get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/workspaces/{workspace_id}/evidence"]["get"]
    limit = next(parameter for parameter in operation["parameters"] if parameter["name"] == "limit")
    assert limit["in"] == "query"
    assert limit["required"] is False
    assert limit["schema"]["type"] == "integer"
    assert limit["schema"]["minimum"] == 1
    assert limit["schema"]["maximum"] == 50
    assert limit["schema"]["default"] == 20
    assert "ge" not in limit["schema"] and "le" not in limit["schema"]


def test_component_collision_fails_without_mutating_input():
    from issuedigest_api import contracts

    original = {"components": {"schemas": {"Citation": {"type": "string"}}}, "paths": {}}
    with pytest.raises(ValueError, match="Citation"):
        contracts.add_evidence_schemas(original)
    assert original == {"components": {"schemas": {"Citation": {"type": "string"}}}, "paths": {}}


def test_research_and_comparison_components_preserve_discriminators():
    schema = TestClient(main.app).get("/openapi.json").json()
    schemas = schema["components"]["schemas"]
    assert set(schema["paths"]) == {
        "/health/live",
        "/api/v1/status",
        "/api/v1/briefings",
        "/api/v1/briefings/{slug}",
        "/api/v1/briefings/{slug}/versions/{version}",
        "/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}",
        "/api/v1/workspaces/{workspace_id}/evidence",
        "/api/v1/workspaces/{workspace_id}/evidence/search",
        "/api/v1/workspaces/{workspace_id}/research",
        "/api/v1/workspaces/{workspace_id}/research/{run_id}",
        "/api/v1/workspaces/{workspace_id}/research/{run_id}/cancel",
        "/api/v1/auth/google/start",
        "/api/v1/auth/google/callback",
        "/api/v1/auth/session",
        "/api/v1/auth/logout",
    }
    names = {
        "ResearchBundle",
        "SourceIdentity",
        "Entity",
        "Claim",
        "DerivationRecord",
        "IdentityReview",
        "SupportReview",
        "EntityReference",
        "ClaimReference",
        "DocumentReference",
        "RelationReference",
        "Relation",
        "DateInterval",
        "Dimension",
        "ComparisonContext",
        "Observation",
        "ComparisonReason",
        "ComparisonAssessment",
    }
    assert names <= schemas.keys()
    for model, field, tags in [
        ("Relation", "source", {"entity", "claim", "document"}),
        ("Relation", "target", {"entity", "claim", "document"}),
        ("SupportReview", "target", {"claim", "relation"}),
    ]:
        discriminator = schemas[model]["properties"][field]["discriminator"]
        assert discriminator["propertyName"] == "kind"
        assert set(discriminator["mapping"]) == tags
        for reference in discriminator["mapping"].values():
            assert reference.removeprefix("#/components/schemas/") in schemas
    for reference in walk_references(schema):
        assert reference.removeprefix("#/components/schemas/") in schemas
    import issuedigest_domain as domain

    for name in names:
        assert name in domain.__all__
        assert getattr(domain, name).model_json_schema()["title"] == name


@pytest.mark.parametrize("name", ["ResearchBundle", "ComparisonAssessment", "EntityReference"])
def test_research_component_collision_rejects_input_without_mutation(name):
    from issuedigest_api import contracts

    original = {"components": {"schemas": {name: {"type": "string"}}}, "paths": {}}
    with pytest.raises(ValueError, match=name):
        contracts.add_evidence_schemas(original)
    assert original == {"components": {"schemas": {name: {"type": "string"}}}, "paths": {}}


EXECUTION_MODELS = {
    "ExecutionVersions",
    "RunInput",
    "RunSubmission",
    "Run",
    "SubmissionAssessment",
    "RunEvent",
    "RunHistory",
    "RunSnapshot",
    "ReplayBatch",
    "CallAttempt",
    "CanvasDraft",
    "CanvasRevision",
    "CanvasBundle",
    "BudgetWindow",
    "PricingSnapshot",
    "UsageReservation",
    "UsageEntry",
    "UsageBook",
    "BudgetAssessment",
    "RunExecutionBundle",
    "EvidenceModule",
    "SummaryModule",
    "ComparisonModule",
    "TimelineModule",
    "GraphModule",
    "ChartModule",
    "OpenEvidenceAction",
    "SelectDocumentAction",
    "AskQuestionAction",
    "SortAction",
}


def test_execution_components_registered_public_and_legacy_unchanged():
    import issuedigest_domain as domain
    from pydantic.json_schema import models_json_schema

    schema = TestClient(main.app).get("/openapi.json").json()
    schemas = schema["components"]["schemas"]
    assert EXECUTION_MODELS <= schemas.keys()
    assert set(schema["paths"]) == {
        "/health/live",
        "/api/v1/status",
        "/api/v1/briefings",
        "/api/v1/briefings/{slug}",
        "/api/v1/briefings/{slug}/versions/{version}",
        "/api/v1/workspaces/{workspace_id}/evidence/{snapshot_id}",
        "/api/v1/workspaces/{workspace_id}/evidence",
        "/api/v1/workspaces/{workspace_id}/evidence/search",
        "/api/v1/workspaces/{workspace_id}/research",
        "/api/v1/workspaces/{workspace_id}/research/{run_id}",
        "/api/v1/workspaces/{workspace_id}/research/{run_id}/cancel",
        "/api/v1/auth/google/start",
        "/api/v1/auth/google/callback",
        "/api/v1/auth/session",
        "/api/v1/auth/logout",
    }
    _, legacy = models_json_schema(
        [
            (domain.EvidenceBundle, "validation"),
            (domain.CitationAnchorValidation, "validation"),
            (domain.ResearchBundle, "validation"),
            (domain.ComparisonAssessment, "validation"),
        ],
        ref_template="#/components/schemas/{model}",
    )
    for name, definition in legacy["$defs"].items():
        assert schemas[name] == definition
    for name in EXECUTION_MODELS:
        assert name in domain.__all__
        assert getattr(domain, name).model_json_schema()["title"] == name
    for name in [
        "hash_run_input",
        "assess_submission",
        "replay_run",
        "events_after",
        "may_start_paid_step",
        "promote_revision",
        "assess_budget",
        "CanvasModule",
        "CanvasAction",
        "RunEventPayload",
        "MoneyMicrowon",
    ]:
        assert name in domain.__all__
    for reference in walk_references(schema):
        assert reference.removeprefix("#/components/schemas/") in schemas
    for model, field, tags in [
        (
            "RunEvent",
            "payload",
            {
                "run.accepted",
                "stage.changed",
                "module.ready",
                "run.cancel_requested",
                "run.awaiting_reconciliation",
                "run.reconciliation_resolved",
                "run.succeeded",
                "run.failed",
                "run.cancelled",
            },
        ),
        (
            "ModuleReadyPayload",
            "module",
            {"evidence", "summary", "comparison", "timeline", "graph", "chart"},
        ),
    ]:
        discriminator = schemas[model]["properties"][field]["discriminator"]
        assert discriminator["propertyName"] == "kind"
        assert set(discriminator["mapping"]) == tags
        for reference in discriminator["mapping"].values():
            assert reference.removeprefix("#/components/schemas/") in schemas
    assert schemas["RunEvent"]["properties"]["seq"]["maximum"] == 2**53 - 1
    assert schemas["UsageEntry"]["properties"]["cost_microwon"]["anyOf"][0]["type"] == "string"
    assert (
        schemas["EvidenceModule"]["properties"]["actions"]["items"]["discriminator"]["propertyName"]
        == "kind"
    )
    for name in EXECUTION_MODELS:
        assert schemas[name]["additionalProperties"] is False


@pytest.mark.parametrize(
    "name", ["RunHistory", "RunExecutionBundle", "CanvasRevision", "UsageBook"]
)
def test_execution_schema_collision_does_not_mutate_input(name):
    from issuedigest_api import contracts

    original = {"components": {"schemas": {name: {"type": "string"}}}, "paths": {}}
    with pytest.raises(ValueError, match=name):
        contracts.add_evidence_schemas(original)
    assert original == {"components": {"schemas": {name: {"type": "string"}}}, "paths": {}}


@pytest.mark.parametrize(
    "model,field,minimum",
    [
        ("EvidenceModule", "citation_ids", 1),
        ("SummaryModule", "citation_ids", 1),
        ("ComparisonModule", "citation_ids", 1),
        ("TimelineModule", "citation_ids", 1),
        ("GraphModule", "citation_ids", 1),
        ("ChartModule", "citation_ids", 1),
        ("SummaryModule", "claim_ids", 1),
        ("ComparisonModule", "claim_ids", 2),
        ("TimelineModule", "claim_ids", 1),
        ("GraphModule", "relation_ids", 1),
        ("ChartModule", "observation_ids", 2),
        ("AwaitingReconciliationPayload", "attempt_ids", 1),
        ("ReconciliationResolvedPayload", "attempt_ids", 1),
        ("UsageReservation", "pricing_snapshot_ids", 1),
    ],
)
def test_actual_execution_schema_preserves_minimum_id_array_cardinality(model, field, minimum):
    schema = TestClient(main.app).get("/openapi.json").json()
    array = schema["components"]["schemas"][model]["properties"][field]
    assert array["type"] == "array"
    assert array.get("minItems") == minimum, "actual OpenAPI loses minimum array cardinality"
    assert "minLength" not in array, "array constraints must not use the string length keyword"
