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


def test_evidence_components_resolve_without_adding_http_paths():
    schema = TestClient(main.app).get("/openapi.json").json()
    assert set(schema["paths"]) == {"/health/live", "/api/v1/status"}
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


def test_component_collision_fails_without_mutating_input():
    from issuedigest_api import contracts

    original = {"components": {"schemas": {"Citation": {"type": "string"}}}, "paths": {}}
    with pytest.raises(ValueError, match="Citation"):
        contracts.add_evidence_schemas(original)
    assert original == {"components": {"schemas": {"Citation": {"type": "string"}}}, "paths": {}}


def test_research_and_comparison_components_resolve_discriminators_without_new_paths():
    schema = TestClient(main.app).get("/openapi.json").json()
    schemas = schema["components"]["schemas"]
    assert set(schema["paths"]) == {"/health/live", "/api/v1/status"}
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
