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


NONCANONICAL_ORIGINS = [
    "https://example.test:443",
    "https://EXAMPLE.test",
    "https://example.test:08443",
    "https://localhost:016173",
    "https://127.1",
    "https://127.0.0.01",
    "https://0x7f000001",
    "https://0X7F000001",
    "https://2130706433",
    "https://0177.0.0.1",
    "https://127.0.0.0x1",
    "https://example.1",
    "https://example.09",
    "https://example.0x1",
    "https://example.0x",
]


@pytest.mark.parametrize("origin", NONCANONICAL_ORIGINS)
def test_noncanonical_browser_origins_fail_at_configuration(origin):
    with pytest.raises(configuration().RuntimeConfigurationError) as caught:
        configuration().AuthConfig.from_environment(values(ISSUEDIGEST_PUBLIC_ORIGIN=origin))
    assert str(caught.value) == "Invalid runtime configuration"


@pytest.mark.parametrize(
    "origin",
    [
        "https://example.test",
        "https://example.test:8443",
        "https://localhost:16173",
        "https://127.0.0.1",
        "https://127.0.0.1:16173",
        "https://example.123a",
        "https://example.0xg",
    ],
)
def test_canonical_origins_preserve_exact_registered_callback(origin):
    config = configuration().AuthConfig.from_environment(values(ISSUEDIGEST_PUBLIC_ORIGIN=origin))
    assert config.public_origin == origin
    assert config.callback_url == origin + "/api/v1/auth/google/callback"
