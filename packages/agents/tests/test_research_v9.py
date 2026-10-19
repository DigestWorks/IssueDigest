"""Synthetic final9 combined budget and historical byte contracts."""
import importlib
import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from pydantic_ai.usage import RequestUsage
from test_research_v6 import proposal


def profile():
    import issuedigest_agents
    assert (Path(issuedigest_agents.__file__).parent / 'research_v9.py').exists(), 'missing final9 implementation'
    return importlib.import_module('issuedigest_agents.research_v9')


@pytest.mark.parametrize('prior,cap', [(0,2000),(500,2000),(501,1999),(1000,1500)])
def test_combined_prior_drives_actual_final_output_cap(sync_model_loop, prior, cap):
    v9 = profile()
    selected, response = proposal()
    calls = []
    def respond(messages, info):
        calls.append(info)
        assert info.model_settings == dict(openai_store=False, max_tokens=cap, timeout=45)
        return ModelResponse(parts=[ToolCallPart('answer', response)], usage=RequestUsage(input_tokens=100,output_tokens=50))
    agent = v9.create_agent_v9(FunctionModel(respond))
    prompt = v9.model_prompt_v9('합성', (selected,), prior_input_tokens=600, prior_output_tokens=prior)
    output, inputs, outputs = v9.run_agent_v9(agent, prompt, prior_input_tokens=600, prior_output_tokens=prior)
    canvas = v9.build_canvas_v9(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.research.claims[0].derivation.method_version == 'research-v9'
    assert canvas.research.support_reviews[0].reviewer_id == 'issuedigest-research-v9'
    assert (inputs,outputs) == (100,50) and len(calls)==1


@pytest.mark.parametrize('inputs,outputs', [(True,0),(0,True),(-1,0),(0,-1),(0,1001),(20000,1)])
def test_combined_invalid_prior_is_rejected_before_provider(inputs,outputs):
    v9 = profile()
    selected, _ = proposal()
    with pytest.raises(ValueError):
        v9.model_prompt_v9('합성',(selected,),prior_input_tokens=inputs,prior_output_tokens=outputs)


def test_final9_does_not_drop_whole_quotes_to_fit_dynamic_budget():
    v9=profile()
    selected,_=proposal()
    with pytest.raises(ValueError,match='budget'):
        v9.model_prompt_v9('합성',(selected,),prior_input_tokens=19000,prior_output_tokens=1000)


def test_frozen_v8_worker_is_actual_baseline_bytes():
    path=Path(__file__).parents[3]/'apps/worker/tests/fixtures/research_worker_v8.py'
    assert path.exists(), 'missing historical v8 fixture'
    assert sha256(path.read_bytes()).hexdigest() == 'f81ce73041e29a000738e9f5d2523799f35d6cff915c26ad22b574eebaff0f95'
