"""Private v10 final: short numeric explanations atop the frozen v8 tools."""

from uuid import UUID

from issuedigest_domain import CanvasBundle, EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from pydantic_ai import Agent
from pydantic_ai.models import Model

from ._relevance_final import _final_prompt, _run_final
from .research import MAX_CITATIONS_TOTAL
from .research_v3 import AIOutputV3, _build_classified_canvas, _create_classified_agent
from .research_v6 import _provider_schema_bytes_v6
from .research_v8 import (
    SYSTEM_INSTRUCTIONS_V8,
    _provider_tools_v8,
)

AIOutputV10 = AIOutputV3
SYSTEM_INSTRUCTIONS_V10 = SYSTEM_INSTRUCTIONS_V8 + (
    " V10: In the first core answer, briefly explain the numeric relationship that answers "
    "the question. State which figures are included in which total; never frame that total "
    "as another amount to add. Keep each number's unit, subject, period and baseline. "
    "Distinguish planned targets, observed interim results and conditional forecasts; "
    "include the forecast's material condition in that first answer. Preserve lower/upper "
    "bounds and open ends: at least is not exactly or at most, and no upper limit is implied. "
    "For comparisons across sources or topics, separate each source's figures and basis; "
    "do not imply matching measures, dates or causation. If selected quotes cannot answer "
    "the core question, use insufficient_evidence with empty modules."
)


def _worst_case_static_bytes_v10() -> int:
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, MAX_CITATIONS_TOTAL + 1))
    return len(SYSTEM_INSTRUCTIONS_V10.encode()) + max(
        max(
            _provider_schema_bytes_v6(
                _provider_tools_v8(ids, tuple(f"2026-10-{i:02}" for i in range(1, count + 1)))
            )
        )
        for count in (0, 1, 16)
    )


STATIC_INPUT_BYTES_V10 = _worst_case_static_bytes_v10()


def create_agent_v10(model: Model) -> Agent[None, AIOutputV10]:
    """Borrow the caller's existing model; never create or close a provider client."""
    if not isinstance(model, Model):
        raise ValueError("Caller-owned model required")
    return _create_classified_agent(model, version="v10", instructions=SYSTEM_INSTRUCTIONS_V10)


def model_prompt_v10(
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
        static_bytes=STATIC_INPUT_BYTES_V10,
        prior_input_tokens=prior_input_tokens,
        prior_output_tokens=prior_output_tokens,
    )


def run_agent_v10(
    agent: Agent[None, AIOutputV10],
    prompt: str,
    *,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> tuple[AIOutputV10, int, int]:
    return _run_final(
        agent,
        prompt,
        instructions=SYSTEM_INSTRUCTIONS_V10,
        static_bytes=STATIC_INPUT_BYTES_V10,
        prior_input_tokens=prior_input_tokens,
        prior_output_tokens=prior_output_tokens,
    )


def build_canvas_v10(
    run_id: UUID,
    workspace_id: UUID,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    output: AIOutputV10,
) -> CanvasBundle:
    return _build_classified_canvas(run_id, workspace_id, sources, output, version="v10")
