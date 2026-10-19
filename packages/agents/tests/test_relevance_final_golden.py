"""Freeze final9 provider boundary before extracting its common final runner."""

import json
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_v6 import proposal


@pytest.mark.parametrize("dates", [0, 1, 16])
def test_final9_actual_request_and_canonical_golden(sync_model_loop, dates, monkeypatch):
    from issuedigest_agents import research_v9 as sdk
    from issuedigest_agents.research_v6 import _provider_schema_bytes_v6
    from issuedigest_agents.research_v8 import _provider_tools_v8
    from v9_fixture import build_fixture

    assert sha256(sdk.SYSTEM_INSTRUCTIONS_V9.encode()).hexdigest() == (
        "91df818c434cedf73ba3602bcf4f8a77c5ca47e500580e80238dbfd443e9c47a"
    )
    assert len(sdk.SYSTEM_INSTRUCTIONS_V9.encode()) == 3599
    assert sdk.STATIC_INPUT_BYTES_V9 == 11907
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    exact_dates = tuple(f"2026-10-{i:02}" for i in range(1, dates + 1))
    assert (
        _provider_schema_bytes_v6(_provider_tools_v8(ids, exact_dates))
        == {0: (7070, 6964), 1: (8097, 7957), 16: (8308, 8168)}[dates]
    )
    selected, response = proposal()
    prompt = sdk.model_prompt_v9(
        "질문", (selected,), prior_input_tokens=600, prior_output_tokens=900
    )
    payload = json.loads(prompt)
    payload["sources"][0]["snapshot_id"] = "<original-snapshot>"
    assert sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest() == (
        "95adc9e0aa4727b7f01bd84899ce50c12157fe19a3f172666497de4b8e2abcf6"
    )
    baseline = json.loads(
        Path("packages/api-client/tests/fixtures/research-run-v9-generated.json").read_text()
    )
    assert build_fixture() == baseline
    calls = []

    def respond(messages, info):
        calls.append(True)
        assert messages[-1].parts[0].content == prompt
        assert info.instructions == sdk.SYSTEM_INSTRUCTIONS_V9
        assert info.model_settings == dict(openai_store=False, max_tokens=1600, timeout=45)
        assert not info.allow_text_output and info.function_tools == []
        return ModelResponse(
            parts=[ToolCallPart("answer", response)],
            usage=RequestUsage(input_tokens=100, output_tokens=50),
        )

    from issuedigest_agents import research_v3

    creations = []
    lifetimes = []

    def forbidden_client(*args, **kwargs):
        creations.append(True)
        raise AssertionError("Borrowed final9 must not create a default client")

    class BorrowedModel(FunctionModel):
        async def __aenter__(self):
            lifetimes.append("enter")
            return self

        async def __aexit__(self, *args):
            lifetimes.append("exit")

    monkeypatch.setattr(research_v3, "AsyncOpenAI", forbidden_client)
    borrowed = BorrowedModel(respond)
    agent = sdk.create_agent_v9(borrowed)
    assert agent.model is borrowed
    output, inputs, outputs = sdk.run_agent_v9(
        agent, prompt, prior_input_tokens=600, prior_output_tokens=900
    )
    assert output.modules[0].claims[0].text.startswith("제공 자료에 따르면, ")
    assert (inputs, outputs) == (100, 50) and calls == [True]
    assert creations == [] and lifetimes == []
