"""Private v9 final: frozen v8 protocol with combined planner/selector accounting."""

from uuid import UUID

from issuedigest_domain import CanvasBundle, EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from pydantic import BaseModel
from pydantic_ai import Agent, AgentRunResult, UsageLimits
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from .research import MAX_OUTPUT_TOKENS, MAX_RUN_TOKENS, PROVIDER_FRAMING_ALLOWANCE, _model_prompt
from .research_v3 import AIOutputV3, _build_classified_canvas, _create_classified_agent
from .research_v5 import _prompt_citation_ids_v5
from .research_v6 import _canonical_output_v6, _provider_schema_bytes_v6
from .research_v7 import _validate_result_usage, _validate_usage
from .research_v8 import (
    STATIC_INPUT_BYTES_V8,
    SYSTEM_INSTRUCTIONS_V8,
    _prompt_dates_v8,
    _provider_tools_v8,
)

AIOutputV9 = AIOutputV3
STATIC_INPUT_BYTES_V9 = STATIC_INPUT_BYTES_V8
SYSTEM_INSTRUCTIONS_V9 = SYSTEM_INSTRUCTIONS_V8


def _budget_v9(prior_input_tokens: int, prior_output_tokens: int) -> tuple[int, int]:
    _validate_usage(prior_input_tokens, prior_output_tokens, total=20_000, output=1_000)
    return (
        MAX_RUN_TOKENS - prior_input_tokens - prior_output_tokens,
        min(2_000, MAX_OUTPUT_TOKENS - prior_output_tokens),
    )


def create_agent_v9(model: Model) -> Agent[None, AIOutputV9]:
    """Borrow the caller's existing model; never create or close a provider client."""
    if not isinstance(model, Model):
        raise ValueError("Caller-owned model required")
    return _create_classified_agent(model, version="v9", instructions=SYSTEM_INSTRUCTIONS_V9)


def model_prompt_v9(
    question: str,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    parent: str | None = None,
    *,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> str:
    remaining, cap = _budget_v9(prior_input_tokens, prior_output_tokens)
    # Preserve the common bounded whole-quote selection first. Dynamic budget pressure
    # must reject that complete prompt, never silently delete its candidate quotations.
    prompt = _model_prompt(question, sources, parent, byte_limit=2**31)
    if len(prompt.encode()) + STATIC_INPUT_BYTES_V9 + PROVIDER_FRAMING_ALLOWANCE + cap > remaining:
        raise ValueError("provider input exceeds pre-request budget")
    return prompt


def run_agent_v9(
    agent: Agent[None, AIOutputV9],
    prompt: str,
    *,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> tuple[AIOutputV9, int, int]:
    remaining, cap = _budget_v9(prior_input_tokens, prior_output_tokens)
    if len(prompt.encode()) + STATIC_INPUT_BYTES_V9 + PROVIDER_FRAMING_ALLOWANCE + cap > remaining:
        raise ValueError("provider input exceeds pre-request budget")
    tools = _provider_tools_v8(_prompt_citation_ids_v5(prompt), _prompt_dates_v8(prompt))
    actual_static = len(SYSTEM_INSTRUCTIONS_V9.encode()) + max(_provider_schema_bytes_v6(tools))
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


def build_canvas_v9(
    run_id: UUID,
    workspace_id: UUID,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    output: AIOutputV9,
) -> CanvasBundle:
    return _build_classified_canvas(run_id, workspace_id, sources, output, version="v9")
