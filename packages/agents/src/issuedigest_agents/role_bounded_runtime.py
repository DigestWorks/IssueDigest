"""Private one-request role runtime with explicit budgets and borrowed model ownership."""

from pydantic import BaseModel
from pydantic_ai import Agent, ToolOutput, UsageLimits, capture_run_messages
from pydantic_ai.messages import ModelMessage
from pydantic_ai.models import Model
from pydantic_ai.models.openai import OpenAIResponsesModelSettings

from .numeric_evidence import KnownUsage, _known_usage
from .numeric_selection import _captured_usage
from .numeric_selection_evaluation import _canonical_models
from .research import PROVIDER_FRAMING_ALLOWANCE
from .research_v5 import _provider_schema_bytes_v5
from .research_v7 import _validate_result_usage
from .scope_role_audit import _ObservedAuditModel
from .shared_measurement_context import _actual_models


class RoleRequestError(ValueError):
    """Known observed cost and possible dispatch survive sanitized stage failure."""

    def __init__(
        self, message: str, *, known_usage: KnownUsage | None = None, may_have_started: bool = False
    ):
        super().__init__(message)
        self.known_usage = known_usage
        self.may_have_started = may_have_started


def _request_envelope(
    prompt: str, tools: list[ToolOutput[BaseModel]], instructions: str, output_limit: int
) -> int:
    return (
        len(prompt.encode("utf-8"))
        + len(instructions.encode("utf-8"))
        + max(_provider_schema_bytes_v5(tools))
        + PROVIDER_FRAMING_ALLOWANCE
        + output_limit
    )


def _run_role_request(
    *,
    model: Model,
    prompt: str,
    tools: list[ToolOutput[BaseModel]],
    instructions: str,
    identity: str,
    total_limit: int,
    output_limit: int,
) -> tuple[BaseModel, KnownUsage]:
    """Return actual dynamic output and known single-stage usage; never own a client."""
    known = None
    captured: list[ModelMessage] = []
    observed = None
    try:
        if (
            not isinstance(model, Model)
            or type(total_limit) is not int
            or type(output_limit) is not int
            or output_limit <= 0
            or total_limit <= 0
            or len(tools) != 1
            or _request_envelope(prompt, tools, instructions, output_limit) > total_limit
        ):
            raise ValueError("Invalid stage request budget")
        output_type = tools[0].output
        if not isinstance(output_type, type) or not issubclass(output_type, BaseModel):
            raise ValueError("Expected dynamic tool model")
        observed = _ObservedAuditModel(model)
        agent: Agent[None, BaseModel] = Agent(
            observed, name=identity, instructions=instructions, output_type=tools, retries=0
        )
        with capture_run_messages() as captured:
            result = agent.run_sync(
                prompt,
                model_settings=OpenAIResponsesModelSettings(
                    openai_store=False, max_tokens=output_limit, timeout=30
                ),
                usage_limits=UsageLimits(
                    request_limit=1,
                    output_tokens_limit=output_limit,
                    total_tokens_limit=total_limit,
                ),
                retries=0,
            )
        known = _known_usage(result)
        _validate_result_usage(result, total=total_limit, output=output_limit)
        if (
            known is None
            or type(result.usage.requests) is not int
            or result.usage.requests != 1
            or known.requests != 1
            or known.output_tokens > output_limit
            or known.input_tokens + known.output_tokens > total_limit
        ):
            raise ValueError("Invalid single-stage raw usage")
        if type(result.output) is not output_type:
            raise ValueError("Expected actual dynamic output")
        _canonical_models(result.output, output_type)
        _actual_models(result.output, output_type)
        return result.output, known
    except Exception:
        if known is None:
            known = _captured_usage(observed.responses if observed is not None else captured)
        raise RoleRequestError(
            "Role request failed",
            known_usage=known,
            may_have_started=observed.request_started if observed else False,
        ) from None
