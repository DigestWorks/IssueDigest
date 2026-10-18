"""Explicit ownership for sync synthetic model tests; no implicit asyncio policy loop."""

import asyncio

import pytest


@pytest.fixture
def sync_model_loop():
    # PydanticAI run_sync drives the current loop. Runner installs one without
    # asyncio.get_event_loop's deprecated implicit main-thread creation and owns cleanup.
    with asyncio.Runner() as runner:
        loop = runner.get_loop()
        yield loop
    assert loop.is_closed()
