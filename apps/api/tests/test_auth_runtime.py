"""Configured runtime owns its engine and rejects bad settings before connections."""

import importlib

import pytest
from fastapi.testclient import TestClient
from issuedigest_api.auth_config import RuntimeConfigurationError
from test_auth_config import values


def runtime():
    assert importlib.util.find_spec("issuedigest_api.runtime") is not None
    return importlib.import_module("issuedigest_api.runtime")


def test_missing_configuration_does_not_attempt_database(monkeypatch):
    module = runtime()
    for key in values():
        monkeypatch.delenv(key, raising=False)
    attempted = []
    monkeypatch.setattr(module, "create_storage_engine", lambda value: attempted.append(True))
    with pytest.raises(RuntimeConfigurationError, match="^Invalid runtime configuration$"):
        module.create_configured_app()
    assert attempted == []


def test_invalid_origin_does_not_attempt_database(monkeypatch):
    module = runtime()
    for key, value in values(ISSUEDIGEST_PUBLIC_ORIGIN="https://user@evil.test").items():
        monkeypatch.setenv(key, value)
    attempted = []
    monkeypatch.setattr(module, "create_storage_engine", lambda value: attempted.append(True))
    with pytest.raises(RuntimeConfigurationError):
        module.create_configured_app()
    assert not attempted


def test_runtime_disposes_owned_engine_at_lifespan_exit(engine, monkeypatch):
    module = runtime()
    for key, value in values().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(module, "create_storage_engine", lambda _: engine)
    disposed = []
    monkeypatch.setattr(engine, "dispose", lambda: disposed.append(True))
    application = module.create_configured_app()
    assert not disposed
    with TestClient(application) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/api/v1/briefings").json() == {"items": []}
        assert client.get("/api/v1/auth/session").status_code == 401
    assert disposed == [True]


def test_runtime_disposes_engine_on_repository_failure(monkeypatch):
    module = runtime()
    for key, value in values().items():
        monkeypatch.setenv(key, value)

    class OwnedEngine:
        disposed = False

        def dispose(self):
            self.disposed = True

    owned = OwnedEngine()
    monkeypatch.setattr(module, "create_storage_engine", lambda _: owned)

    def broken(_):
        raise RuntimeError("PRIVATE")

    monkeypatch.setattr(module, "OAuthRepository", broken)
    with pytest.raises(RuntimeConfigurationError) as caught:
        module.create_configured_app()
    assert owned.disposed and "PRIVATE" not in str(caught.value)


def test_default_factory_never_reads_environment_or_connects(monkeypatch):
    import issuedigest_api.main as main

    def forbidden(*args):
        raise AssertionError("unexpected external configuration")

    monkeypatch.setattr(runtime(), "create_storage_engine", forbidden)
    for key in values():
        monkeypatch.setenv(key, "PRIVATE")
    with TestClient(main.create_app()) as client:
        assert client.get("/health/live").status_code == 200
        assert client.post("/api/v1/auth/google/start").status_code == 503


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.test:443",
        "https://EXAMPLE.test",
        "https://example.test:08443",
        "https://127.1",
        "https://127.0.0.01",
        "https://0x7f000001",
        "https://example.1",
    ],
)
def test_noncanonical_origin_rejected_before_storage_creation(monkeypatch, origin):
    module = runtime()
    for key, value in values(ISSUEDIGEST_PUBLIC_ORIGIN=origin).items():
        monkeypatch.setenv(key, value)
    attempted = []

    def unexpected_connection(_):
        attempted.append(True)
        raise AssertionError("storage should not be reached")

    monkeypatch.setattr(module, "create_storage_engine", unexpected_connection)
    with pytest.raises(RuntimeConfigurationError, match="^Invalid runtime configuration$"):
        module.create_configured_app()
    assert attempted == []
