"""Bounded native Responses tool transport; callers still validate source and meaning.

Closing the local HTTP response does not establish provider cancellation or final cost.
This result is not a stored generation receipt and does not activate any app runtime.
"""

import asyncio
import json
import math
import re
import sys
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Literal, cast

from httpx2 import AsyncByteStream
from openai import AsyncOpenAI, AsyncStream
from openai.types.responses import FunctionToolParam, ResponseStreamEvent
from pydantic import BaseModel
from pydantic_ai import ToolOutput
from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
from pydantic_ai.tools import GenerateToolJsonSchema

from .json_whitespace_guard import JsonWhitespaceGuard, JsonWhitespaceGuardError
from .numeric_evidence import KnownUsage
from .numeric_selection_evaluation import _canonical_models
from .role_bounded_runtime import _request_envelope
from .shared_measurement_context import _actual_models

GUARDED_RESPONSES_PROFILE: Literal["guarded-responses-tool-v1"] = "guarded-responses-tool-v1"
STREAM_TOTAL_TOKEN_LIMIT = 20000
STREAM_OUTPUT_TOKEN_LIMIT = 4000
STREAM_DEADLINE_SECONDS = 60
STREAM_CLOSE_DEADLINE_SECONDS = 1
STREAM_ARGUMENT_BYTE_LIMIT = 80000
STREAM_EVENT_LIMIT = 10000

Reason = Literal[
    "input",
    "whitespace",
    "protocol",
    "transport",
    "timeout",
    "usage",
    "output",
    "limit",
    "cancelled",
]
_MESSAGE = "Guarded Responses request failed"


@dataclass(frozen=True)
class GuardedResponsesToolResult:
    profile: Literal["guarded-responses-tool-v1"]
    output: BaseModel
    usage: KnownUsage
    usage_complete: Literal[True]


class _Observations:
    def __init__(
        self,
        *,
        reason: Reason,
        known_usage: KnownUsage | None = None,
        may_have_started: bool = False,
        usage_complete: bool = False,
        stream_closed: bool = False,
    ) -> None:
        self._reason = reason
        self._known_usage = known_usage
        self._may_have_started = may_have_started
        self._usage_complete = usage_complete
        self._stream_closed = stream_closed

    @property
    def reason(self) -> Reason:
        return self._reason

    @property
    def known_usage(self) -> KnownUsage | None:
        return self._known_usage

    @property
    def may_have_started(self) -> bool:
        return self._may_have_started

    @property
    def usage_complete(self) -> bool:
        return self._usage_complete

    @property
    def stream_closed(self) -> bool:
        return self._stream_closed


class GuardedResponsesError(ValueError, _Observations):
    def __init__(self, **observations: Any) -> None:
        ValueError.__init__(self, _MESSAGE)
        _Observations.__init__(self, **observations)


class GuardedResponsesCancelled(asyncio.CancelledError, _Observations):
    def __init__(self, **observations: Any) -> None:
        asyncio.CancelledError.__init__(self, _MESSAGE)
        _Observations.__init__(self, **observations)


class _Failure(Exception):
    def __init__(self, reason: Reason) -> None:
        self.reason = reason


class _BoundedBody(AsyncByteStream):
    """Own only an acquired response body; confirm one cooperative close attempt."""

    def __init__(self, body: AsyncByteStream, operation_deadline: asyncio.Timeout) -> None:
        self._body = body
        self._operation_deadline = operation_deadline
        self._attempted = False
        self.confirmed_closed = False
        self._failure: Reason | None = None
        self.primary_reason: Reason | None = None

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self._body:
            yield chunk

    async def aclose(self) -> None:
        if self.confirmed_closed:
            return
        if self._attempted:
            raise _Failure(self._failure or "transport") from None
        self._attempted = True
        # Native AsyncStream invokes close from its generator's finally. Preserve
        # that already-active failure if body cleanup raises a different exception.
        pending = sys.exception()
        if isinstance(pending, asyncio.CancelledError):
            self.primary_reason = "timeout" if self._operation_deadline.expired() else "cancelled"
        elif isinstance(pending, TimeoutError):
            self.primary_reason = "timeout"
        elif isinstance(pending, Exception):
            self.primary_reason = "transport"
        close_deadline = asyncio.timeout(STREAM_CLOSE_DEADLINE_SECONDS)
        try:
            async with close_deadline:
                await self._body.aclose()
                self.confirmed_closed = True
            if close_deadline.expired():
                raise _Failure("timeout")
        except asyncio.CancelledError:
            self._failure = self.primary_reason or "cancelled"
            raise
        except Exception:
            close_reason: Reason = "timeout" if close_deadline.expired() else "transport"
            self._failure = self.primary_reason or close_reason
            raise _Failure(self._failure) from None


def _require(condition: bool, reason: Reason = "protocol") -> None:
    if not condition:
        raise _Failure(reason)


def _string(value: Any) -> bool:
    return type(value) is str and bool(value)


def _index(value: Any) -> bool:
    return type(value) is int and value >= 0


def _snapshot(value: Any) -> str:
    _require(type(value) is str)
    JsonWhitespaceGuard().feed(value)
    return cast(str, value)


class _State:
    def __init__(self, name: str) -> None:
        self.name = name
        self.response_id: str | None = None
        self.sequence = -1
        self.events = 0
        self.items: dict[int, tuple[str, str]] = {}
        self.finished: set[int] = set()
        self.function_index: int | None = None
        self.call_id: str | None = None
        self.arguments = ""
        self.argument_bytes = 0
        self.guard = JsonWhitespaceGuard()
        self.arguments_done = False
        self.known_usage: KnownUsage | None = None
        self.usage_complete = False

    def usage(self, usage: Any, *, terminal: bool) -> None:
        if usage is None and not terminal:
            return
        _require(isinstance(usage, dict), "usage")
        values = [usage.get(key) for key in ("input_tokens", "output_tokens", "total_tokens")]
        _require(all(_index(value) for value in values), "usage")
        inputs, outputs, total = values
        _require(total == inputs + outputs, "usage")
        prior = self.known_usage
        _require(
            prior is None or (inputs >= prior.input_tokens and outputs >= prior.output_tokens),
            "usage",
        )
        self.known_usage = KnownUsage(input_tokens=inputs, output_tokens=outputs, requests=1)
        self.usage_complete = terminal
        _require(
            outputs <= STREAM_OUTPUT_TOKEN_LIMIT and total <= STREAM_TOTAL_TOKEN_LIMIT, "usage"
        )

    def append(self, text: Any) -> None:
        _require(type(text) is str)
        self.guard.feed(text)  # A rejected chunk must never contribute even a prefix.
        size = len(text.encode("utf-8"))
        _require(self.argument_bytes + size <= STREAM_ARGUMENT_BYTE_LIMIT, "limit")
        self.arguments += text
        self.argument_bytes += size

    def identity(self, item: dict[str, Any], index: Any, *, final: bool) -> None:
        _require(_index(index) and index == self.function_index)
        _require(self.items.get(index) == (item.get("id"), "function_call"))
        _require(
            item.get("type") == "function_call"
            and item.get("name") == self.name
            and item.get("call_id") == self.call_id
        )
        _require(_snapshot(item.get("arguments")) == self.arguments)
        if final:
            _require(item.get("status") == "completed")

    def consume(self, event: dict[str, Any]) -> bool:
        response: Any
        item: Any
        index: Any
        self.events += 1
        _require(self.events <= STREAM_EVENT_LIMIT, "limit")
        sequence: Any = event.get("sequence_number")
        _require(_index(sequence) and sequence > self.sequence)
        self.sequence = sequence
        kind = event.get("type")
        if kind == "response.created":
            _require(self.response_id is None)
            response = event.get("response")
            _require(isinstance(response, dict) and _string(response.get("id")))
            self.response_id = response["id"]
            self.usage(response.get("usage"), terminal=False)
            _require(response.get("status") == "in_progress" and not response.get("output"))
            _require(response.get("error") is None and response.get("incomplete_details") is None)
            return False
        _require(self.response_id is not None)
        if kind in (
            "response.in_progress",
            "response.completed",
            "response.incomplete",
            "response.failed",
        ):
            response = event.get("response")
            _require(isinstance(response, dict) and response.get("id") == self.response_id)
            terminal = kind != "response.in_progress"
            self.usage(response.get("usage"), terminal=terminal)
            if not terminal:
                _require(response.get("status") == "in_progress" and not response.get("output"))
                _require(
                    response.get("error") is None and response.get("incomplete_details") is None
                )
                return False
            _require(kind == "response.completed" and response.get("status") == "completed")
            _require(response.get("error") is None and response.get("incomplete_details") is None)
            _require(
                self.arguments_done
                and self.function_index is not None
                and self.finished == self.items.keys()
            )
            output = response.get("output")
            _require(type(output) is list and len(output) == len(self.items))
            for index, item in enumerate(output):
                _require(isinstance(item, dict))
                _require(self.items.get(index) == (item.get("id"), item.get("type")))
                if item.get("type") == "function_call":
                    self.identity(item, index, final=True)
                else:
                    _require(
                        item.get("type") == "reasoning"
                        and item.get("status") in (None, "completed")
                    )
                    _require("arguments" not in item)
            return True
        if kind in ("response.output_item.added", "response.output_item.done"):
            item = event.get("item")
            index = event.get("output_index")
            _require(isinstance(item, dict) and _index(index) and _string(item.get("id")))
            item_kind = item.get("type")
            _require(item_kind in ("reasoning", "function_call"))
            if kind.endswith(".added"):
                _require(
                    index not in self.items
                    and item["id"] not in {v[0] for v in self.items.values()}
                )
                if item_kind == "function_call":
                    _require(
                        self.function_index is None
                        and item.get("name") == self.name
                        and _string(item.get("call_id"))
                        and item.get("status") == "in_progress"
                    )
                    self.function_index, self.call_id = index, item["call_id"]
                    self.append(item.get("arguments"))
                else:
                    _require(
                        "arguments" not in item and item.get("status") in (None, "in_progress")
                    )
                self.items[index] = (item["id"], item_kind)
            else:
                _require(
                    index not in self.finished and self.items.get(index) == (item["id"], item_kind)
                )
                if item_kind == "function_call":
                    _require(self.arguments_done)
                    self.identity(item, index, final=True)
                else:
                    _require("arguments" not in item and item.get("status") in (None, "completed"))
                self.finished.add(index)
            return False
        if kind in (
            "response.function_call_arguments.delta",
            "response.function_call_arguments.done",
        ):
            index = event.get("output_index")
            _require(
                _index(index)
                and index == self.function_index
                and not self.arguments_done
                and self.items.get(index) == (event.get("item_id"), "function_call")
            )
            for key, expected in (("name", self.name), ("call_id", self.call_id)):
                _require(key not in event or event[key] == expected)
            if kind.endswith(".delta"):
                self.append(event.get("delta"))
            else:
                _require(_snapshot(event.get("arguments")) == self.arguments)
                self.arguments_done = True
            return False
        if type(kind) is str and kind.startswith(
            (
                "response.reasoning_text.",
                "response.reasoning_summary_text.",
                "response.reasoning_summary_part.",
            )
        ):
            index = event.get("output_index")
            _require(
                _index(index)
                and self.items.get(index) == (event.get("item_id"), "reasoning")
                and index not in self.finished
            )
            _require(not any(key in event for key in ("arguments", "delta_arguments", "call_id")))
            return False
        raise _Failure("protocol")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, "output")
        result[key] = value
    return result


def _constant(value: str) -> Any:
    raise _Failure("output")


def _finite_numbers(value: Any) -> None:
    if type(value) is float:
        _require(math.isfinite(value), "output")
    elif isinstance(value, dict):
        for child in value.values():
            _finite_numbers(child)
    elif isinstance(value, list):
        for child in value:
            _finite_numbers(child)


def _prepare(
    client: AsyncOpenAI, model: str, prompt: str, instructions: str, tool: ToolOutput[BaseModel]
) -> FunctionToolParam:
    _require(isinstance(client, AsyncOpenAI) and not client.is_closed(), "input")
    _require(type(client.max_retries) is int and client.max_retries == 0, "input")
    _require(
        all(type(value) is str and bool(value.strip()) for value in (model, prompt, instructions)),
        "input",
    )
    _require(type(tool) is ToolOutput and tool.strict is True, "input")
    _require(
        type(tool.name) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", tool.name) is not None,
        "input",
    )
    _require(tool.description is None or type(tool.description) is str, "input")
    output = tool.output
    _require(isinstance(output, type) and issubclass(output, BaseModel), "input")
    output = cast(type[BaseModel], output)
    _require(output.model_config.get("extra") == "forbid", "input")
    raw = output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    parameters = OpenAIJsonSchemaTransformer(raw, strict=True).walk()
    _require(
        _request_envelope(prompt, [tool], instructions, STREAM_OUTPUT_TOKEN_LIMIT)
        <= STREAM_TOTAL_TOKEN_LIMIT,
        "input",
    )
    native: FunctionToolParam = {
        "type": "function",
        "name": cast(str, tool.name),
        "strict": True,
        "parameters": parameters,
    }
    if tool.description is not None:
        native["description"] = tool.description
    return native


async def run_guarded_responses_tool(
    *, client: AsyncOpenAI, model: str, prompt: str, instructions: str, tool: ToolOutput[BaseModel]
) -> GuardedResponsesToolResult:
    """Consume one borrowed native request, rejecting unsafe arguments before assembly."""
    try:
        native = _prepare(client, model, prompt, instructions, tool)
    except Exception:
        raise GuardedResponsesError(reason="input") from None
    state = _State(native["name"])
    stream: AsyncStream[ResponseStreamEvent] | None = None
    body: _BoundedBody | None = None
    reason: Reason | None = None
    output: BaseModel | None = None
    stream_closed = False
    cancelled = False
    may_have_started = False
    task = asyncio.current_task()
    cancellations = task.cancelling() if task is not None else 0
    deadline = asyncio.timeout(STREAM_DEADLINE_SECONDS)
    try:
        async with deadline:
            may_have_started = True
            stream = await client.responses.create(
                model=model,
                input=prompt,
                instructions=instructions,
                tools=[native],
                tool_choice={"type": "function", "name": native["name"]},
                stream=True,
                store=False,
                background=False,
                parallel_tool_calls=False,
                reasoning={"effort": "low"},
                service_tier="default",
                max_output_tokens=STREAM_OUTPUT_TOKEN_LIMIT,
                timeout=STREAM_DEADLINE_SECONDS,
            )
            body = _BoundedBody(cast(AsyncByteStream, stream.response.stream), deadline)
            stream.response.stream = body
            terminal = False
            async for event in stream:
                if state.consume(event.model_dump(exclude_unset=True, warnings=False)):
                    terminal = True
                    break
            _require(terminal)
            try:
                parsed = json.loads(
                    state.arguments, object_pairs_hook=_pairs, parse_constant=_constant
                )
                _require(type(parsed) is dict, "output")
                _finite_numbers(parsed)
                output_type = cast(type[BaseModel], tool.output)
                output = output_type.model_validate_json(state.arguments, strict=True)
                _require(type(output) is output_type, "output")
                _canonical_models(output, output_type)
                _actual_models(output, output_type)
            except Exception:
                raise _Failure("output") from None
    except asyncio.CancelledError:
        cancelled = True
        reason = body.primary_reason if body is not None and body.primary_reason else "cancelled"
    except TimeoutError:
        reason = "timeout"
    except JsonWhitespaceGuardError:
        reason = "whitespace"
    except _Failure as exc:
        reason = exc.reason
        cancelled = reason == "cancelled"
        if task is not None and task.cancelling() > cancellations:
            cancelled = True
            if reason == "timeout" and (body is None or body.primary_reason is None):
                reason = "cancelled"
    except Exception:
        # The SDK closes in its generator's finally. A failed close may replace
        # CancelledError; preserve the task's outstanding cancellation intent.
        if task is not None and task.cancelling() > cancellations:
            cancelled = True
            reason = (
                body.primary_reason if body is not None and body.primary_reason else "cancelled"
            )
        else:
            reason = "timeout" if deadline.expired() else "transport"
    finally:
        if stream is not None:
            close_deadline = asyncio.timeout(STREAM_CLOSE_DEADLINE_SECONDS)
            try:
                async with close_deadline:
                    # httpx marks is_closed before awaiting its body close. Confirm closure
                    # explicitly even if native EOF/error cleanup already set that flag.
                    if stream.response.is_closed:
                        await cast(AsyncByteStream, stream.response.stream).aclose()
                    else:
                        await stream.close()
                    stream_closed = (
                        body is not None and body.confirmed_closed and stream.response.is_closed
                    )
            except asyncio.CancelledError:
                cancelled = True
                reason = reason or "cancelled"
            except Exception:
                if task is not None and task.cancelling() > cancellations:
                    cancelled = True
                close_reason: Reason = "timeout" if close_deadline.expired() else "transport"
                reason = reason or ("cancelled" if cancelled else close_reason)
    if reason is not None:
        error_type = GuardedResponsesCancelled if cancelled else GuardedResponsesError
        raise error_type(
            reason=reason,
            known_usage=state.known_usage,
            may_have_started=may_have_started,
            usage_complete=state.usage_complete,
            stream_closed=stream_closed,
        ) from None
    assert output is not None and state.known_usage is not None
    return GuardedResponsesToolResult(GUARDED_RESPONSES_PROFILE, output, state.known_usage, True)
