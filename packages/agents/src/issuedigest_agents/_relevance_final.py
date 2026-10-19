"""Bounded final execution shared only by the v9/v10 relevance profiles."""

from uuid import UUID

from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from pydantic import BaseModel
from pydantic_ai import Agent, AgentRunResult, UsageLimits
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from .research import MAX_OUTPUT_TOKENS, MAX_RUN_TOKENS, PROVIDER_FRAMING_ALLOWANCE, _model_prompt
from .research_v3 import AIOutputV3
from .research_v5 import _prompt_citation_ids_v5
from .research_v6 import _canonical_output_v6, _provider_schema_bytes_v6
from .research_v7 import _validate_result_usage, _validate_usage
from .research_v8 import (
    _prompt_dates_v8,
    _provider_tools_v8,
)


def _final_budget(prior_input_tokens: int, prior_output_tokens: int) -> tuple[int, int]:
    _validate_usage(prior_input_tokens, prior_output_tokens, total=20_000, output=1_000)
    return (
        MAX_RUN_TOKENS - prior_input_tokens - prior_output_tokens,
        min(2_000, MAX_OUTPUT_TOKENS - prior_output_tokens),
    )


def _final_prompt(
    question: str,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    parent: str | None = None,
    *,
    static_bytes: int,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> str:
    remaining, cap = _final_budget(prior_input_tokens, prior_output_tokens)
    # Preserve the common bounded whole-quote selection first. Dynamic budget pressure
    # must reject that complete prompt, never silently delete its candidate quotations.
    prompt = _model_prompt(question, sources, parent, byte_limit=2**31)
    if len(prompt.encode()) + static_bytes + PROVIDER_FRAMING_ALLOWANCE + cap > remaining:
        raise ValueError("provider input exceeds pre-request budget")
    return prompt


def _run_final(
    agent: Agent[None, AIOutputV3],
    prompt: str,
    *,
    instructions: str,
    static_bytes: int,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> tuple[AIOutputV3, int, int]:
    remaining, cap = _final_budget(prior_input_tokens, prior_output_tokens)
    if len(prompt.encode()) + static_bytes + PROVIDER_FRAMING_ALLOWANCE + cap > remaining:
        raise ValueError("provider input exceeds pre-request budget")
    tools = _provider_tools_v8(_prompt_citation_ids_v5(prompt), _prompt_dates_v8(prompt))
    actual_static = len(instructions.encode()) + max(_provider_schema_bytes_v6(tools))
    if len(prompt.encode()) + actual_static + PROVIDER_FRAMING_ALLOWANCE + cap > remaining:
        raise ValueError("provider input exceeds pre-request budget")
    result: AgentRunResult[BaseModel] = agent.run_sync(
        prompt,
        output_type=tools,
        model_settings=OpenAIResponsesModelSettings(openai_store=False, max_tokens=cap, timeout=45),
        usage_limits=UsageLimits(
            request_limit=1, output_tokens_limit=cap, total_tokens_limit=remaining
        ),
        retries=0,
    )
    _validate_result_usage(result, total=remaining, output=cap)
    return (
        _canonical_output_v6(result.output, prompt),
        result.usage.input_tokens,
        result.usage.output_tokens,
    )
