"""Private v8: frozen v6 DTOs narrowed to exact dates from selected quotations."""

import re
from datetime import date
from typing import Literal, get_args
from uuid import UUID

from issuedigest_domain import CanvasBundle, EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation
from pydantic import BaseModel, Field, create_model
from pydantic_ai import Agent, AgentRunResult, ToolOutput, UsageLimits
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from .research import MAX_CITATIONS_TOTAL, PROVIDER_FRAMING_ALLOWANCE, _model_prompt
from .research_v3 import AIOutputV3, _build_classified_canvas, _create_classified_agent
from .research_v5 import _prompt_citation_ids_v5, _PromptV5
from .research_v6 import (
    SYSTEM_INSTRUCTIONS_V6,
    _canonical_output_v6,
    _provider_schema_bytes_v6,
    _provider_tools_v6,
)
from .research_v7 import FINAL_MAX_OUTPUT_TOKENS, _remaining, _validate_result_usage

AIOutputV8 = AIOutputV3
SYSTEM_INSTRUCTIONS_V8 = SYSTEM_INSTRUCTIONS_V6 + (
    " V8: Only the first16 distinct valid exact dates in source/citation/quote order are "
    "allowed. No dates means no timeline. Use each date only with its own cited quote. "
    "Never take dates from question/prior/title/provider/proposed_on/collected_at or infer "
    "days from month/week/year-end/relative periods; explain those periods as written. "
    "Preserve inclusion/subset/component relations explicitly with exact quotes: included "
    "items are not independent totals. Do not add quantities. Targets are plans, interim "
    "results observations, forecasts conditional; never present targets as achieved results."
)
MAX_SOURCE_DATES_V8 = 16


def _prompt_dates_v8(prompt: str) -> tuple[str, ...]:
    # Reuse the frozen strict prompt shape and citation guard before inspecting only quotes.
    _prompt_citation_ids_v5(prompt)
    payload = _PromptV5.model_validate_json(prompt)
    dates: dict[str, None] = {}
    for source in payload.sources:
        for citation in source.citations:
            for match in re.finditer(
                r"(?<![0-9])[0-9]{4}-[0-9]{2}-[0-9]{2}(?![0-9])", citation.quote
            ):
                literal = match.group()
                try:
                    date.fromisoformat(literal)
                except ValueError:
                    continue
                dates.setdefault(literal, None)
                if len(dates) == MAX_SOURCE_DATES_V8:
                    return tuple(dates)
    return tuple(dates)


def _provider_tools_v8(
    citation_ids: tuple[str, ...], dates: tuple[str, ...]
) -> list[ToolOutput[BaseModel]]:
    tools = _provider_tools_v6(citation_ids)
    answer = tools[0].output
    if not isinstance(answer, type) or not issubclass(answer, BaseModel):
        raise ValueError("Unexpected frozen answer type")
    details = get_args(answer.model_fields["details"].annotation)
    if len(details) != 2 or details[1] is not Ellipsis:
        raise ValueError("Unexpected frozen detail shape")
    alternatives = get_args(details[0])
    if len(alternatives) != 2 or any(
        not isinstance(t, type) or not issubclass(t, BaseModel) for t in alternatives
    ):
        raise ValueError("Unexpected frozen detail types")
    comparison, timeline = alternatives
    if get_args(comparison.model_fields["kind"].annotation) != ("comparison",) or get_args(
        timeline.model_fields["kind"].annotation
    ) != ("timeline",):
        raise ValueError("Unexpected frozen detail kinds")
    detail = comparison
    if dates:
        if (
            len(dates) > MAX_SOURCE_DATES_V8
            or len(set(dates)) != len(dates)
            or any(date.fromisoformat(d).isoformat() != d for d in dates)
        ):
            raise ValueError("Invalid source dates")
        claims = get_args(timeline.model_fields["claims"].annotation)
        if len(claims) != 2 or claims[1] is not Ellipsis or not issubclass(claims[0], BaseModel):
            raise ValueError("Unexpected frozen timeline claims")
        claim = create_model(
            "ProviderTimelineClaimV8",
            __base__=claims[0],
            event_date=(Literal[*dates], ...),  # type: ignore[arg-type]
        )
        narrowed = create_model(
            "ProviderTimelineV8",
            __base__=timeline,
            claims=(tuple[claim, ...], Field(min_length=1, max_length=4)),  # type: ignore[valid-type]
        )
        detail = comparison | narrowed
    narrowed_answer = create_model(
        "ProviderAnswerV8",
        __base__=answer,
        details=(tuple[detail, ...], Field(max_length=2)),  # type: ignore[valid-type]
    )
    return [
        ToolOutput(
            narrowed_answer, name=tools[0].name, description=tools[0].description, strict=True
        ),
        *tools[1:],
    ]


def _worst_case_static_bytes_v8() -> int:
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, MAX_CITATIONS_TOTAL + 1))
    dates = tuple(f"2026-10-{i:02}" for i in range(1, MAX_SOURCE_DATES_V8 + 1))
    return len(SYSTEM_INSTRUCTIONS_V8.encode()) + max(
        _provider_schema_bytes_v6(_provider_tools_v8(ids, dates))
    )


STATIC_INPUT_BYTES_V8 = _worst_case_static_bytes_v8()


def create_agent_v8(model: Model | None = None) -> Agent[None, AIOutputV8]:
    return _create_classified_agent(model, version="v8", instructions=SYSTEM_INSTRUCTIONS_V8)


def model_prompt_v8(
    question: str,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    parent: str | None = None,
    *,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> str:
    remaining = _remaining(prior_input_tokens, prior_output_tokens)
    limit = remaining - STATIC_INPUT_BYTES_V8 - PROVIDER_FRAMING_ALLOWANCE - FINAL_MAX_OUTPUT_TOKENS
    return _model_prompt(question, sources, parent, byte_limit=limit)


def run_agent_v8(
    agent: Agent[None, AIOutputV8],
    prompt: str,
    *,
    prior_input_tokens: int,
    prior_output_tokens: int,
) -> tuple[AIOutputV8, int, int]:
    remaining = _remaining(prior_input_tokens, prior_output_tokens)
    limit = remaining - STATIC_INPUT_BYTES_V8 - PROVIDER_FRAMING_ALLOWANCE - FINAL_MAX_OUTPUT_TOKENS
    if len(prompt.encode()) > limit:
        raise ValueError("provider input exceeds pre-request budget")
    tools = _provider_tools_v8(_prompt_citation_ids_v5(prompt), _prompt_dates_v8(prompt))
    actual_static = len(SYSTEM_INSTRUCTIONS_V8.encode()) + max(_provider_schema_bytes_v6(tools))
    if (
        len(prompt.encode()) + actual_static + PROVIDER_FRAMING_ALLOWANCE + FINAL_MAX_OUTPUT_TOKENS
        > remaining
    ):
        raise ValueError("provider input exceeds pre-request budget")
    result: AgentRunResult[BaseModel] = agent.run_sync(
        prompt,
        output_type=tools,
        model_settings=OpenAIResponsesModelSettings(
            openai_store=False, max_tokens=FINAL_MAX_OUTPUT_TOKENS, timeout=45
        ),
        usage_limits=UsageLimits(
            request_limit=1,
            output_tokens_limit=FINAL_MAX_OUTPUT_TOKENS,
            total_tokens_limit=remaining,
        ),
        retries=0,
    )
    _validate_result_usage(result, total=remaining, output=FINAL_MAX_OUTPUT_TOKENS)
    return (
        _canonical_output_v6(result.output, prompt),
        result.usage.input_tokens,
        result.usage.output_tokens,
    )


def build_canvas_v8(
    run_id: UUID,
    workspace_id: UUID,
    sources: tuple[tuple[UUID, EvidenceBundle, SourcePresentation], ...],
    output: AIOutputV8,
) -> CanvasBundle:
    return _build_classified_canvas(run_id, workspace_id, sources, output, version="v8")
