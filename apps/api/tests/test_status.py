from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from issuedigest_api.main import app

client = TestClient(app)


def test_liveness_reports_process_response():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_versioned_status_has_the_public_contract():
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    assert response.json() == {"service": "issuedigest-api", "api_version": "v1", "status": "ok"}


@pytest.mark.parametrize("path", ["/health/live", "/api/v1/status", "/missing"])
def test_request_id_is_a_new_server_uuid_even_for_errors(path):
    first = client.get(path, headers={"X-Request-ID": "client-controlled"})
    second = client.get(path)
    assert "X-Request-ID" in first.headers
    assert UUID(first.headers["X-Request-ID"]).version == 4
    assert first.headers["X-Request-ID"] != second.headers["X-Request-ID"]


def test_openapi_exposes_domain_models_and_request_id():
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/status" in paths
    for path, model in [("/health/live", "Liveness"), ("/api/v1/status", "ServiceStatus")]:
        response = paths[path]["get"]["responses"]["200"]
        assert response["content"]["application/json"]["schema"]["$ref"] == (
            f"#/components/schemas/{model}"
        )
        assert response["headers"]["X-Request-ID"]["schema"]["format"] == "uuid"
    status_schema = schema["components"]["schemas"]["ServiceStatus"]
    assert set(status_schema["required"]) == {"service", "api_version", "status"}
    assert status_schema["properties"]["service"]["const"] == "issuedigest-api"
    assert status_schema["properties"]["api_version"]["const"] == "v1"
    assert status_schema["properties"]["status"]["const"] == "ok"


def test_unhandled_error_still_returns_a_server_request_id():
    @app.get("/test-failure", include_in_schema=False)
    def fail():
        raise RuntimeError("test failure")

    response = TestClient(app, raise_server_exceptions=False).get("/test-failure")
    assert response.status_code == 500
    assert "X-Request-ID" in response.headers
    assert UUID(response.headers["X-Request-ID"]).version == 4
    assert response.json() == {"detail": "Internal server error"}
