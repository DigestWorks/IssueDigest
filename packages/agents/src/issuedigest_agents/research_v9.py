"""Private v9 final: frozen v8 protocol with combined planner/selector accounting."""

from uuid import UUID

from issuedigest_domain import CanvasBundle, EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from pydantic_ai import Agent
from pydantic_ai.models import Model

from ._relevance_final import _final_budget, _final_prompt, _run_final
from .research_v3 import AIOutputV3, _build_classified_canvas, _create_classified_agent
from .research_v8 import (
    STATIC_INPUT_BYTES_V8,
    SYSTEM_INSTRUCTIONS_V8,
)

AIOutputV9 = AIOutputV3
STATIC_INPUT_BYTES_V9 = STATIC_INPUT_BYTES_V8
SYSTEM_INSTRUCTIONS_V9 = SYSTEM_INSTRUCTIONS_V8


def _budget_v9(prior_input_tokens: int, prior_output_tokens: int) -> tuple[int, int]:
    return _final_budget(prior_input_tokens, prior_output_tokens)


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
    return _final_prompt(
        question,
        sources,
        parent,
        static_bytes=STATIC_INPUT_BYTES_V9,
        prior_input_tokens=prior_input_tokens,
        prior_output_tokens=prior_output_tokens,
    )


def run_agent_v9(
    agent: Agent[None, AIOutputV9],
    prompt: str,
    *,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> tuple[AIOutputV9, int, int]:
    return _run_final(
        agent,
        prompt,
        instructions=SYSTEM_INSTRUCTIONS_V9,
        static_bytes=STATIC_INPUT_BYTES_V9,
        prior_input_tokens=prior_input_tokens,
        prior_output_tokens=prior_output_tokens,
    )


def build_canvas_v9(
    run_id: UUID,
    workspace_id: UUID,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    output: AIOutputV9,
) -> CanvasBundle:
    return _build_classified_canvas(run_id, workspace_id, sources, output, version="v9")
