"""Configuration rejects ambiguous origins before any storage is created."""

import importlib

import pytest


def configuration():
    return importlib.import_module("issuedigest_api.auth_config")


def values(**changes):
    return {
        "ISSUEDIGEST_DATABASE_URL": "postgresql+psycopg://synthetic/db",
        "ISSUEDIGEST_PUBLIC_ORIGIN": "https://localhost:8443",
        "ISSUEDIGEST_GOOGLE_CLIENT_ID": "synthetic.apps.googleusercontent.com",
        "ISSUEDIGEST_GOOGLE_CLIENT_SECRET": "synthetic-client-secret",
    } | changes


def test_valid_config_has_fixed_callback_and_hidden_credentials():
    assert importlib.util.find_spec("issuedigest_api.auth_config") is not None
    config = configuration().AuthConfig.from_environment(values())
    assert config.callback_url == "https://localhost:8443/api/v1/auth/google/callback"
    assert "synthetic-client-secret" not in repr(config)
    assert "postgresql" not in repr(config)


@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost",
        "https://example.test/",
        "https://user@example.test",
        "https://example.test?x=1",
        "https://example.test#x",
        "https://example.test\\evil",
        "https://example.test%2f",
        "https://example.test:0",
        "https://example.test:65536",
        "https:// example.test",
        "https://example.test/path",
    ],
)
def test_ambiguous_origins_rejected_without_echo(origin):
    assert importlib.util.find_spec("issuedigest_api.auth_config") is not None
    with pytest.raises(configuration().RuntimeConfigurationError) as caught:
        configuration().AuthConfig.from_environment(values(ISSUEDIGEST_PUBLIC_ORIGIN=origin))
    assert str(caught.value) == "Invalid runtime configuration"


@pytest.mark.parametrize("key", list(values()))
def test_required_values_are_explicit(key):
    assert importlib.util.find_spec("issuedigest_api.auth_config") is not None
    environment = values()
    del environment[key]
    with pytest.raises(configuration().RuntimeConfigurationError):
        configuration().AuthConfig.from_environment(environment)
