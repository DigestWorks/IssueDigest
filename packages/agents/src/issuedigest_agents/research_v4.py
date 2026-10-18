"""New private attribution/numeric instruction profile; historical v2/v3 bytes stay frozen."""

import json
from uuid import UUID

from issuedigest_domain import CanvasBundle, EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from pydantic_ai import Agent
from pydantic_ai.models import Model

from .research import MAX_OUTPUT_TOKENS, MAX_RUN_TOKENS, PROVIDER_FRAMING_ALLOWANCE, _model_prompt
from .research_v3 import (
    SYSTEM_INSTRUCTIONS_V3,
    AIOutputV3,
    _build_classified_canvas,
    _create_classified_agent,
    run_agent_v3,
)

# The bounded structured output contract is identical. Versioning belongs to the
# instructions/agent/workflow/reviews, without changing the old schema's titles.
AIOutputV4 = AIOutputV3
SYSTEM_INSTRUCTIONS_V4 = SYSTEM_INSTRUCTIONS_V3 + (
    " Distinguish the fact that wording appears in a document from the truth of its statistics, "
    "effects, evaluations, assertions, plans or forecasts. A source's numerical announcement "
    "must be attributed to that institution or speaker, including its period and unit; merely "
    "being quoted in a document does not make the asserted statistic independently established. "
    "Use attributed for claims reporting such assertions, even when the document states them "
    "explicitly. Use documented for what the document itself records, such as its stated plan, "
    "without asserting that the plan happened. Separate targets, currently achieved results, "
    "forecasts and confirmed outcomes. Never turn a target or forecast into achieved performance. "
    "Compare quoted numbers only when the same subject, period and unit are established; "
    "when a simple numeric ordering is verified from comparable quoted numbers, state that "
    "ordering with the source attribution and target/result distinction instead of hiding it "
    "behind insufficient_evidence. Do not calculate new quantities or invent numbers, causal "
    "effects, contradictions, opposing sides or certainty. If subject, period, unit or status "
    "cannot be aligned, explain that limit without forcing a comparison or a conclusion."
)
STATIC_INPUT_BYTES_V4 = len(SYSTEM_INSTRUCTIONS_V4.encode("utf-8")) + len(
    json.dumps(AIOutputV4.model_json_schema(), ensure_ascii=False).encode("utf-8")
)
INPUT_PROMPT_BYTE_LIMIT_V4 = (
    MAX_RUN_TOKENS - MAX_OUTPUT_TOKENS - PROVIDER_FRAMING_ALLOWANCE - STATIC_INPUT_BYTES_V4
)


def create_agent_v4(model: Model | None = None) -> Agent[None, AIOutputV4]:
    return _create_classified_agent(model, version="v4", instructions=SYSTEM_INSTRUCTIONS_V4)


def model_prompt_v4(
    question: str,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    parent: str | None = None,
) -> str:
    return _model_prompt(question, sources, parent, byte_limit=INPUT_PROMPT_BYTE_LIMIT_V4)


def run_agent_v4(agent: Agent[None, AIOutputV4], prompt: str) -> tuple[AIOutputV4, int, int]:
    if len(prompt.encode("utf-8")) > INPUT_PROMPT_BYTE_LIMIT_V4:
        raise ValueError("provider input exceeds pre-request budget")
    return run_agent_v3(agent, prompt)


def build_canvas_v4(
    run_id: UUID,
    workspace_id: UUID,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    output: AIOutputV4,
) -> CanvasBundle:
    return _build_classified_canvas(run_id, workspace_id, sources, output, version="v4")
