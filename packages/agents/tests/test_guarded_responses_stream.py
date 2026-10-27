"""Real native SDK over synthetic SSE; no provider or source inputs."""

import asyncio
import importlib
import importlib.util
import json
import sys
from collections.abc import AsyncIterator, Iterator
from copy import deepcopy
from dataclasses import FrozenInstanceError
from typing import Any, cast

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict
from pydantic_ai import ToolOutput


@pytest.fixture(scope="module", autouse=True)
def restore_introduced_agent_modules() -> Iterator[None]:
    package = importlib.import_module("issuedigest_agents")
    existing = set(sys.modules)
    attributes = vars(package).copy()
    try:
        yield
    finally:
        for name in set(sys.modules) - existing:
            if name.startswith("issuedigest_agents."):
                sys.modules.pop(name, None)
        # Restore package attributes too: from-package imports can otherwise reuse
        # unloaded helpers whose model classes precede later frozen reload tests.
        for name in set(vars(package)) - attributes.keys():
            delattr(package, name)
        for name, value in attributes.items():
            setattr(package, name, value)


class Output(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


def api() -> Any:
    name = "issuedigest_agents.guarded_responses_stream"
    assert importlib.util.find_spec(name) is not None, "Missing guarded native transport"
    return importlib.import_module(name)


def item(arguments: str = '{"text":"ok"}', **changes: Any) -> dict[str, Any]:
    return dict(
        type="function_call",
        id="fc_1",
        call_id="call_1",
        name="answer",
        arguments=arguments,
        status="completed",
        **changes,
    )


def response(status: Any = "completed", arguments: Any = '{"text":"ok"}', usage: Any = None) -> Any:
    return dict(
        id="resp_1",
        object="response",
        created_at=1,
        status=status,
        error=None,
        incomplete_details=None,
        output=[item(arguments)],
        usage=usage or dict(input_tokens=10, output_tokens=5, total_tokens=15),
    )


def events(
    arguments: str = '{"text":"ok"}', chunks: list[str] | None = None, initial: str = ""
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [
        dict(
            type="response.created",
            response={**response("in_progress"), "output": [], "usage": None},
        ),
        dict(
            type="response.output_item.added",
            output_index=0,
            item={**item(initial), "status": "in_progress"},
        ),
    ]
    rows += [
        dict(
            type="response.function_call_arguments.delta",
            output_index=0,
            item_id="fc_1",
            delta=chunk,
        )
        for chunk in ([arguments] if chunks is None else chunks)
    ]
    rows += [
        dict(
            type="response.function_call_arguments.done",
            output_index=0,
            item_id="fc_1",
            arguments=arguments,
        ),
        dict(type="response.output_item.done", output_index=0, item=item(arguments)),
        dict(type="response.completed", response=response(arguments=arguments)),
    ]
    return numbered(rows)


def numbered(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{**row, "sequence_number": i} for i, row in enumerate(rows)]


class Body(httpx.AsyncByteStream):
    def __init__(
        self,
        rows: list[dict[str, Any]],
        *,
        wait: bool = False,
        close_error: bool = False,
        read_error: bool = False,
    ) -> None:
        self.rows = rows
        self.consumed = 0
        self.closed = False
        self.wait = wait
        self.close_error = close_error
        self.read_error = read_error
        self.blocked = asyncio.Event()

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for row in self.rows:
            self.consumed += 1
            yield ("event: " + row["type"] + "\ndata: " + json.dumps(row) + "\n\n").encode()
        if self.read_error:
            raise httpx.ReadError("sensitive transport details")
        if self.wait:
            self.blocked.set()
            await asyncio.Event().wait()

    async def aclose(self) -> None:
        if self.close_error:
            raise RuntimeError("sensitive close details")
        self.closed = True


async def harness(
    rows: list[dict[str, Any]] | None = None,
    *,
    body: Body | None = None,
    kwargs: dict[str, Any] | None = None,
    client_kwargs: dict[str, Any] | None = None,
    cancel: bool = False,
) -> tuple[Any, Body, list[httpx.Request]]:
    mod = api()
    body = body or Body(events() if rows is None else rows)
    requests: list[httpx.Request] = []

    def serve(request: Any) -> Any:
        requests.append(request)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)

    http = httpx.AsyncClient(transport=httpx.MockTransport(serve))
    client_options: dict[str, Any] = dict(
        api_key="synthetic",
        base_url="https://synthetic.invalid/v1",
        http_client=http,
        max_retries=0,
    )
    client_options.update(client_kwargs or {})
    client = AsyncOpenAI(**client_options)
    options = dict(
        client=client,
        model=" model ",
        prompt=" full prompt ",
        instructions=" full instructions ",
        tool=ToolOutput(Output, name="answer", description=" exact description ", strict=True),
    )
    options.update(kwargs or {})
    try:
        try:
            if cancel:
                task = asyncio.create_task(mod.run_guarded_responses_tool(**options))
                await body.blocked.wait()
                task.cancel()
                result = await task
            else:
                result = await mod.run_guarded_responses_tool(**options)
        except BaseException as exc:
            result = exc
        assert not client.is_closed()
        assert not http.is_closed
        return (result, body, requests)
    finally:
        await client.close()


def run(*args: Any, **kwargs: Any) -> tuple[Any, Body, list[httpx.Request]]:
    return asyncio.run(harness(*args, **kwargs))


def failure(
    result: Any,
    reason: str,
    *,
    known: dict[str, int] | None = None,
    complete: bool = False,
    closed: bool = True,
    started: bool = True,
) -> None:
    mod = api()
    assert isinstance(result, mod.GuardedResponsesError)
    assert str(result) == "Guarded Responses request failed"
    assert "sensitive" not in repr(result)
    assert result.__cause__ is None
    assert result.__suppress_context__
    assert result.reason == reason
    assert result.usage_complete is complete
    assert result.stream_closed is closed
    assert result.may_have_started is started
    if known is None:
        assert result.known_usage is None
    else:
        assert result.known_usage.model_dump() == known


USAGE = dict(input_tokens=10, output_tokens=5, requests=1)


@pytest.mark.parametrize("chunks", [None, list('{"text":"ok"}'), ["", '{"text":', "", '"ok"}', ""]])
def test_complete_native_request_preserves_wire_options_and_borrowed_client(chunks: Any) -> None:
    result, body, requests = run(events(chunks=chunks))
    assert isinstance(result, api().GuardedResponsesToolResult)
    assert type(result.output) is Output
    assert result.output.text == "ok"
    assert result.usage.model_dump() == USAGE
    assert result.usage_complete is True
    assert result.profile == "guarded-responses-tool-v1"
    with pytest.raises(FrozenInstanceError):
        result.profile = "changed"
    assert body.closed
    assert len(requests) == 1
    wire = json.loads(requests[0].content)
    assert wire == dict(
        model=" model ",
        input=" full prompt ",
        instructions=" full instructions ",
        stream=True,
        store=False,
        background=False,
        parallel_tool_calls=False,
        reasoning={"effort": "low"},
        service_tier="default",
        max_output_tokens=4000,
        tool_choice={"type": "function", "name": "answer"},
        tools=[
            dict(
                type="function",
                name="answer",
                description=" exact description ",
                strict=True,
                parameters={
                    "additionalProperties": False,
                    "properties": {"text": {"type": "string"}},
                    "required": ["text"],
                    "type": "object",
                },
            )
        ],
    )
    assert requests[0].extensions["timeout"]["read"] == 60


@pytest.mark.parametrize(
    "arguments",
    [" " * 256 + '{"text":"ok"}', json.dumps({"text": " " * 300 + '한😀\\"'}, ensure_ascii=False)],
)
def test_lexical_guard_accepts_boundary_and_quoted_whitespace_unicode(arguments: Any) -> None:
    result, _, _ = run(events(arguments, chunks=list(arguments)))
    assert isinstance(result, api().GuardedResponsesToolResult)
    assert result.output.text == json.loads(arguments)["text"]


@pytest.mark.parametrize("where", ["delta", "added", "arguments_done", "item_done", "terminal"])
def test_whitespace_in_any_argument_surface_stops_without_draining(where: Any) -> None:
    rows = events()
    bad = " " * 257 + '{"text":"ok"}'
    index = {"delta": 2, "added": 1, "arguments_done": 3, "item_done": 4, "terminal": 5}[where]
    if where == "delta":
        rows[index]["delta"] = bad
    elif where == "arguments_done":
        rows[index]["arguments"] = bad
    elif where == "terminal":
        rows[index]["response"]["output"][0]["arguments"] = bad
    else:
        rows[index]["item"]["arguments"] = bad
    result, body, _ = run(rows)
    failure(
        result,
        "whitespace",
        known=USAGE if where == "terminal" else None,
        complete=where == "terminal",
    )
    assert body.consumed == index + 1


@pytest.mark.parametrize(
    "options",
    [
        dict(model=" "),
        dict(prompt=""),
        dict(instructions=1),
        dict(tool=ToolOutput(Output, name="bad.name", strict=True)),
        dict(tool=ToolOutput(Output, name="answer", strict=False)),
        dict(client=None),
    ],
)
def test_invalid_preflight_never_dispatches(options: Any) -> None:
    result, body, requests = run(kwargs=options)
    failure(result, "input", closed=False, started=False)
    assert not requests
    assert not body.closed


@pytest.mark.parametrize(
    "mutation",
    [
        "sequence_bool",
        "sequence_repeat",
        "wrong_id",
        "wrong_index",
        "wrong_item",
        "wrong_name",
        "wrong_call",
        "unknown",
        "text",
        "refusal",
        "second_tool",
        "duplicate_done",
        "missing_args_done",
        "missing_item_done",
        "snapshot",
        "early_delta",
        "created_twice",
        "wrong_terminal_id",
        "terminal_status",
        "terminal_error",
        "reasoning_collision",
    ],
)
def test_protocol_identity_order_and_completion_are_fail_closed(mutation: Any) -> None:
    rows = events()
    terminal_usage = False
    if mutation == "sequence_bool":
        rows[2]["sequence_number"] = True
    elif mutation == "sequence_repeat":
        rows[2]["sequence_number"] = 1
    elif mutation == "wrong_id":
        rows.insert(
            1,
            dict(type="response.in_progress", response={**response("in_progress"), "id": "wrong"}),
        )
    elif mutation == "wrong_index":
        rows[2]["output_index"] = True
    elif mutation == "wrong_item":
        rows[2]["item_id"] = "wrong"
    elif mutation == "wrong_name":
        rows[1]["item"]["name"] = "wrong"
    elif mutation == "wrong_call":
        rows[4]["item"]["call_id"] = "wrong"
    elif mutation in ("unknown", "text", "refusal"):
        rows[2]["type"] = {
            "unknown": "response.future",
            "text": "response.output_text.delta",
            "refusal": "response.refusal.delta",
        }[mutation]
    elif mutation == "second_tool":
        rows.insert(
            2,
            dict(type="response.output_item.added", output_index=1, item={**item(), "id": "fc_2"}),
        )
    elif mutation == "duplicate_done":
        rows.insert(4, deepcopy(rows[3]))
    elif mutation == "missing_args_done":
        del rows[3]
        terminal_usage = False
    elif mutation == "missing_item_done":
        del rows[4]
        terminal_usage = True
    elif mutation == "snapshot":
        rows[3]["arguments"] = '{"text":"changed"}'
    elif mutation == "early_delta":
        rows[1], rows[2] = (rows[2], rows[1])
    elif mutation == "created_twice":
        rows.insert(1, deepcopy(rows[0]))
    elif mutation == "wrong_terminal_id":
        rows[-1]["response"]["id"] = "wrong"
    elif mutation == "terminal_status":
        rows[-1]["response"]["status"] = "incomplete"
        terminal_usage = True
    elif mutation == "terminal_error":
        rows[-1]["response"]["error"] = {"code": "x", "message": "sensitive"}
        terminal_usage = True
    elif mutation == "reasoning_collision":
        rows.insert(
            2,
            dict(
                type="response.output_item.added",
                output_index=0,
                item=dict(type="reasoning", id="r1", summary=[]),
            ),
        )
    if mutation not in ("sequence_bool", "sequence_repeat"):
        rows = numbered(rows)
    result, _, _ = run(rows)
    failure(result, "protocol", known=USAGE if terminal_usage else None, complete=terminal_usage)


@pytest.mark.parametrize(
    "arguments",
    [
        '{"text":3}',
        '{"text":"ok","extra":1}',
        '{"text":"ok","text":"duplicate"}',
        '{"text":NaN}',
        '{"text":Infinity}',
        "[]",
        "{broken",
    ],
)
def test_invalid_complete_output_retains_final_usage(arguments: Any) -> None:
    result, _, _ = run(events(arguments))
    failure(result, "output", known=USAGE, complete=True)


@pytest.mark.parametrize(
    "usage",
    [
        None,
        {},
        dict(input_tokens=-1, output_tokens=5, total_tokens=4),
        dict(input_tokens=True, output_tokens=5, total_tokens=6),
        dict(input_tokens=10, output_tokens=5, total_tokens=16),
        dict(input_tokens="10", output_tokens=5, total_tokens=15),
    ],
)
def test_bad_terminal_usage_never_becomes_free(usage: Any) -> None:
    rows = events()
    rows[-1]["response"]["usage"] = usage
    result, _, _ = run(rows)
    failure(result, "usage")


@pytest.mark.parametrize("status", ["incomplete", "failed"])
def test_terminal_failure_retains_final_usage(status: Any) -> None:
    rows = events()
    rows[-1]["type"] = "response." + status
    rows[-1]["response"]["status"] = status
    result, _, _ = run(rows)
    failure(result, "protocol", known=USAGE, complete=True)


def test_observed_usage_survives_whitespace_but_is_not_final() -> None:
    rows = events()
    rows[0]["response"]["usage"] = dict(input_tokens=10, output_tokens=5, total_tokens=15)
    rows[2]["delta"] = " " * 257
    result, _, _ = run(rows)
    failure(result, "whitespace", known=USAGE)


def test_decreasing_usage_retains_last_valid_observation() -> None:
    rows = events()
    rows[0]["response"]["usage"] = dict(input_tokens=11, output_tokens=5, total_tokens=16)
    result, _, _ = run(rows)
    failure(result, "usage", known=dict(input_tokens=11, output_tokens=5, requests=1))


@pytest.mark.parametrize("inputs,outputs", [(10, 4001), (20000, 1)])
def test_overbudget_final_usage_is_not_clipped(inputs: Any, outputs: Any) -> None:
    rows = events()
    rows[-1]["response"]["usage"] = dict(
        input_tokens=inputs, output_tokens=outputs, total_tokens=inputs + outputs
    )
    result, _, _ = run(rows)
    failure(
        result,
        "usage",
        known=dict(input_tokens=inputs, output_tokens=outputs, requests=1),
        complete=True,
    )


def test_eof_without_terminal_never_returns_partial_output() -> None:
    result, _, _ = run(events()[:-1])
    failure(result, "protocol")


def test_transport_failure_is_sanitized_and_closed() -> None:
    result, _, _ = run(body=Body(events()[:1], read_error=True))
    failure(result, "transport")


def test_close_failure_does_not_replace_primary_whitespace_failure() -> None:
    rows = events()
    rows[2]["delta"] = " " * 257
    result, body, _ = run(body=Body(rows, close_error=True))
    failure(result, "whitespace", closed=False)
    assert not body.closed


def test_external_cancellation_remains_cancellation_and_retains_observations() -> None:
    rows = events()[:1]
    rows[0]["response"]["usage"] = dict(input_tokens=10, output_tokens=5, total_tokens=15)
    result, body, _ = run(body=Body(rows, wait=True), cancel=True)
    assert isinstance(result, api().GuardedResponsesCancelled)
    assert issubclass(type(result), asyncio.CancelledError)
    assert not isinstance(result, Exception)
    assert result.reason == "cancelled"
    assert result.known_usage.model_dump() == USAGE
    assert result.usage_complete is False
    assert result.stream_closed and body.closed
    assert str(result) == "Guarded Responses request failed"


def test_deadline_closes_without_waiting_sixty_seconds(monkeypatch: Any) -> None:
    monkeypatch.setattr(api(), "STREAM_DEADLINE_SECONDS", 0.01)
    result, _, _ = run(body=Body(events()[:1], wait=True))
    failure(result, "timeout")


def test_utf8_bound_and_event_count_bound(monkeypatch: Any) -> None:
    monkeypatch.setattr(api(), "STREAM_ARGUMENT_BYTE_LIMIT", 14)
    result, _, _ = run(events('{"text":"😀"}'))
    failure(result, "limit")
    monkeypatch.setattr(api(), "STREAM_EVENT_LIMIT", 2)
    result, body, _ = run()
    failure(result, "limit")
    assert body.consumed == 3


def test_cancellation_stays_cancellation_when_native_finally_close_fails() -> None:
    result, body, _ = run(body=Body(events()[:1], wait=True, close_error=True), cancel=True)
    assert isinstance(result, api().GuardedResponsesCancelled)
    assert result.reason == "cancelled"
    assert result.stream_closed is False
    assert not body.closed


def test_error_observations_are_readonly_properties() -> None:
    result, _, _ = run(events()[:-1])
    for name in ("reason", "known_usage", "may_have_started", "usage_complete", "stream_closed"):
        with pytest.raises(AttributeError):
            setattr(result, name, None)


def test_prior_suppressed_cancellation_does_not_reclassify_transport_failure() -> None:

    async def scenario() -> Any:
        task = asyncio.current_task()
        assert task is not None
        task.cancel()
        try:
            await asyncio.sleep(0)
        except asyncio.CancelledError:
            pass
        return await harness(body=Body(events()[:1], read_error=True))

    result, _, _ = asyncio.run(scenario())
    failure(result, "transport")


def test_deadline_preserved_when_native_finally_close_fails(monkeypatch: Any) -> None:
    monkeypatch.setattr(api(), "STREAM_DEADLINE_SECONDS", 0.01)
    result, _, _ = run(body=Body(events()[:1], wait=True, close_error=True))
    failure(result, "timeout", closed=False)


@pytest.mark.parametrize("retries", [True, False, 1, 2])
def test_preflight_disables_sdk_retry_before_any_http(retries: Any) -> None:
    result, _, requests = run(client_kwargs=dict(max_retries=retries))
    failure(result, "input", closed=False, started=False)
    assert not requests


@pytest.mark.parametrize(
    "tool",
    [
        ToolOutput(Output, name="answer", strict=cast(Any, 1)),
        ToolOutput(Output, name="", strict=True),
        ToolOutput(Output, name="한글", strict=True),
        ToolOutput(Output, name="a" * 65, strict=True),
        ToolOutput(str, name="answer", strict=True),
        ToolOutput(cast(Any, Output(text="example")), name="answer", strict=True),
    ],
)
def test_preflight_tool_identity_and_output_class_are_required(tool: Any) -> None:
    result, _, requests = run(kwargs=dict(tool=tool))
    failure(result, "input", closed=False, started=False)
    assert not requests


def test_preflight_requires_extra_forbid_and_exact_tool_type() -> None:

    class Loose(BaseModel):
        text: str

    class DerivedTool(ToolOutput[BaseModel]):
        pass

    for tool in (
        ToolOutput(Loose, name="answer", strict=True),
        DerivedTool(Output, name="answer", strict=True),
    ):
        result, _, requests = run(kwargs=dict(tool=tool))
        failure(result, "input", closed=False, started=False)
        assert not requests


def test_preflight_bounds_full_prompt_without_truncation() -> None:
    result, _, requests = run(kwargs=dict(prompt="x" * 20000))
    failure(result, "input", closed=False, started=False)
    assert not requests


def test_none_description_is_omitted_from_native_tool() -> None:
    result, _, requests = run(kwargs=dict(tool=ToolOutput(Output, name="answer", strict=True)))
    assert isinstance(result, api().GuardedResponsesToolResult)
    assert "description" not in json.loads(requests[0].content)["tools"][0]


def test_nonempty_added_arguments_join_deltas_without_rewriting() -> None:
    arguments = '{"text":"한😀"}'
    rows = events(arguments, initial=arguments[:9], chunks=["", arguments[9:], ""])
    result, _, _ = run(rows)
    assert result.output.text == "한😀"


def test_whitespace_run_continues_from_added_into_first_delta() -> None:
    rows = events(initial=" " * 256, chunks=[" ", '{"text":"ok"}'])
    result, body, _ = run(rows)
    failure(result, "whitespace")
    assert body.consumed == 3


@pytest.mark.parametrize("where", ["item_done", "terminal"])
def test_complete_snapshots_cannot_replace_stream_arguments(where: Any) -> None:
    rows = events()
    if where == "terminal":
        rows[-1]["response"]["output"][0]["arguments"] = '{"text":"replacement"}'
    else:
        rows[4]["item"]["arguments"] = '{"text":"replacement"}'
    result, _, _ = run(rows)
    failure(
        result,
        "protocol",
        known=USAGE if where == "terminal" else None,
        complete=where == "terminal",
    )


def test_reasoning_is_permitted_and_terminal_stops_without_suffix_drain() -> None:
    rows = events()
    for row in rows:
        if "output_index" in row:
            row["output_index"] = 1
    reasoning = dict(type="reasoning", id="r1", summary=[])
    rows[1:1] = [
        dict(type="response.output_item.added", output_index=0, item=reasoning),
        dict(
            type="response.reasoning_summary_text.delta",
            output_index=0,
            item_id="r1",
            summary_index=0,
            delta="discard this reasoning",
        ),
        dict(type="response.output_item.done", output_index=0, item=reasoning),
    ]
    rows[-1]["response"]["output"].insert(0, reasoning)
    rows.append(dict(type="response.output_text.delta", delta="must not consume"))
    result, body, _ = run(numbered(rows))
    assert isinstance(result, api().GuardedResponsesToolResult)
    assert body.consumed == len(rows) - 1


@pytest.mark.parametrize(
    "usage",
    [
        dict(input_tokens=-1, output_tokens=5, total_tokens=4),
        dict(input_tokens=10, output_tokens=True, total_tokens=11),
        dict(input_tokens=10, output_tokens=5, total_tokens=17),
    ],
)
def test_malformed_nonterminal_observation_retains_prior_counters(usage: Any) -> None:
    rows = events()
    rows[0]["response"]["usage"] = dict(input_tokens=10, output_tokens=5, total_tokens=15)
    rows.insert(
        1, dict(type="response.in_progress", response={**response("in_progress"), "usage": usage})
    )
    result, _, _ = run(numbered(rows))
    failure(result, "usage", known=USAGE)


def test_successful_terminal_with_close_failure_stays_failure_and_keeps_usage() -> None:
    result, _, _ = run(body=Body(events(), close_error=True))
    failure(result, "transport", known=USAGE, complete=True, closed=False)
    assert result.diagnostic_stage == "stream"


@pytest.mark.parametrize(
    "arguments,stage", [("{", "json_parse"), ("[]", "json_value"), ("{}", "dto_schema")]
)
def test_output_rejection_stage_survives_secondary_close_failure(arguments, stage):
    result, _, _ = run(body=Body(events(arguments), close_error=True))
    failure(result, "output", known=USAGE, complete=True, closed=False)
    assert result.diagnostic_stage == stage


def test_http_failure_does_not_retry_or_leak_provider_details() -> None:

    async def scenario() -> Any:
        calls: list[httpx.Request] = []

        def serve(request: Any) -> Any:
            calls.append(request)
            return httpx.Response(500, json={"error": {"message": "sensitive provider payload"}})

        async with httpx.AsyncClient(transport=httpx.MockTransport(serve)) as http:
            client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
            try:
                await api().run_guarded_responses_tool(
                    client=client,
                    model="m",
                    prompt="p",
                    instructions="i",
                    tool=ToolOutput(Output, name="answer", strict=True),
                )
            except api().GuardedResponsesError as exc:
                failure(exc, "transport", closed=False)
            else:
                pytest.fail("HTTP error became a successful result")
            assert len(calls) == 1
            assert not client.is_closed()
            await client.close()

    asyncio.run(scenario())


def test_in_progress_cannot_smuggle_untracked_output() -> None:
    rows = events()
    rows.insert(
        1,
        dict(
            type="response.in_progress",
            response={
                **response("in_progress"),
                "usage": None,
                "output": [dict(type="message", id="msg_1", content=[])],
            },
        ),
    )
    result, _, _ = run(numbered(rows))
    failure(result, "protocol")


def test_closed_borrowed_client_is_rejected_without_dispatch() -> None:

    async def scenario() -> Any:
        requests: list[httpx.Request] = []

        def serve(request: Any) -> Any:
            requests.append(request)
            raise AssertionError("closed client dispatched")

        http = httpx.AsyncClient(transport=httpx.MockTransport(serve))
        client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
        await client.close()
        with pytest.raises(api().GuardedResponsesError) as caught:
            await api().run_guarded_responses_tool(
                client=client,
                model="m",
                prompt="p",
                instructions="i",
                tool=ToolOutput(Output, name="answer", strict=True),
            )
        failure(caught.value, "input", closed=False, started=False)
        assert not requests

    asyncio.run(scenario())


def test_schema_failure_is_sanitized_before_dispatch() -> None:

    class BadSchema(Output):
        @classmethod
        def __get_pydantic_json_schema__(cls, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("sensitive schema metadata")

    result, _, requests = run(kwargs=dict(tool=ToolOutput(BadSchema, name="answer", strict=True)))
    failure(result, "input", closed=False, started=False)
    assert not requests


@pytest.mark.parametrize("size", [80000, 80001])
def test_actual_utf8_limit_accepts_boundary_and_rejects_one_more_byte(size: Any) -> None:
    arguments = '{"text":"' + "😀" * 19997 + "a" * (size - 80000 + 1) + '"}'
    assert len(arguments.encode()) == size
    result, _, _ = run(events(arguments))
    if size == 80000:
        assert isinstance(result, api().GuardedResponsesToolResult)
    else:
        failure(result, "limit")


@pytest.mark.parametrize("mask_cancellation", [False, True])
def test_external_cancellation_during_failure_cleanup_still_propagates_as_cancellation(
    mask_cancellation: bool,
) -> None:
    class ClosingBody(Body):
        async def aclose(self) -> None:
            self.blocked.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if mask_cancellation:
                    raise RuntimeError("sensitive cleanup details") from None
                raise

    rows = events()
    rows[2]["delta"] = " " * 257
    result, _, _ = run(body=ClosingBody(rows), cancel=True)
    assert isinstance(result, api().GuardedResponsesCancelled)
    assert result.reason == "whitespace"
    assert result.stream_closed is False


@pytest.mark.parametrize("number", ["1e999", "-1e999"])
@pytest.mark.parametrize("location", ["scalar", "object", "array"])
def test_exponent_overflow_is_rejected_before_strict_output(number: str, location: str) -> None:
    class FloatOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: float

    class NestedOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: dict[str, float]

    class ArrayOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: tuple[float, ...]

    value, output = {
        "scalar": (number, FloatOutput),
        "object": ('{"nested":' + number + "}", NestedOutput),
        "array": ("[" + number + "]", ArrayOutput),
    }[location]
    arguments = '{"text":' + value + "}"
    result, _, _ = run(
        events(arguments), kwargs=dict(tool=ToolOutput(output, name="answer", strict=True))
    )
    failure(result, "output", known=USAGE, complete=True)


@pytest.mark.parametrize("primary", ["success", "whitespace", "timeout"])
@pytest.mark.parametrize("mask_close_timeout", [False, True])
def test_stalled_cooperative_finally_close_has_its_own_deadline(
    primary: str, mask_close_timeout: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api(), "STREAM_CLOSE_DEADLINE_SECONDS", 0.005, raising=False)
    monkeypatch.setattr(api(), "STREAM_DEADLINE_SECONDS", 0.005 if primary == "timeout" else 60)

    async def scenario() -> Any:
        release = asyncio.Event()

        class StalledBody(Body):
            attempts = 0

            async def aclose(self) -> None:
                self.attempts += 1
                # A confirmed native close is idempotent; it must not reach the
                # second-call stall during the transport's final confirmation.
                if primary == "timeout" and self.attempts == 1:
                    await super().aclose()
                    return
                try:
                    await release.wait()
                except asyncio.CancelledError:
                    if mask_close_timeout:
                        raise RuntimeError("sensitive close timeout details") from None
                    raise
                await super().aclose()

        rows = events() if primary != "timeout" else events()[:1]
        if primary != "success":
            rows[0]["response"]["usage"] = dict(input_tokens=10, output_tokens=5, total_tokens=15)
        if primary == "whitespace":
            rows[2]["delta"] = " " * 257
        body = StalledBody(rows, wait=primary == "timeout")
        # The release keeps the RED run finite without timing assertions. The fixed
        # path must finish before this fallback event fires and leave no cleanup task.
        timer = asyncio.get_running_loop().call_later(0.03, release.set)
        try:
            result, _, _ = await harness(body=body)
            assert not release.is_set()
            assert not isinstance(result, asyncio.CancelledError)
            failure(
                result,
                "timeout" if primary == "success" else primary,
                known=USAGE,
                complete=primary == "success",
                closed=primary == "timeout",
            )
            assert body.attempts == 1
        finally:
            timer.cancel()

    asyncio.run(scenario())


@pytest.mark.parametrize("primary", ["timeout", "cancelled", "transport"])
def test_native_finally_cooperative_close_is_bounded_on_pending_read_failure(
    primary: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api(), "STREAM_CLOSE_DEADLINE_SECONDS", 0.005)
    monkeypatch.setattr(api(), "STREAM_DEADLINE_SECONDS", 0.005 if primary == "timeout" else 60)

    async def scenario() -> None:
        release = asyncio.Event()

        class StalledBody(Body):
            attempts = 0

            async def aclose(self) -> None:
                self.attempts += 1
                await release.wait()
                await super().aclose()

        rows = events()[:1]
        rows[0]["response"]["usage"] = dict(input_tokens=10, output_tokens=5, total_tokens=15)
        body = StalledBody(rows, wait=primary != "transport", read_error=primary == "transport")
        timer = asyncio.get_running_loop().call_later(0.03, release.set)
        try:
            result, _, _ = await harness(body=body, cancel=primary == "cancelled")
            assert not release.is_set()
            assert not body.closed
            assert body.attempts == 1
            if primary == "cancelled":
                assert isinstance(result, api().GuardedResponsesCancelled)
                assert result.reason == "cancelled"
                assert result.known_usage.model_dump() == USAGE
                assert result.usage_complete is False
                assert result.stream_closed is False
            else:
                failure(result, primary, known=USAGE, closed=False)
        finally:
            timer.cancel()

    asyncio.run(scenario())


def test_native_cancelled_error_survives_close_failure_without_task_cancel_count() -> None:
    class CancelledBody(Body):
        async def __aiter__(self) -> AsyncIterator[bytes]:
            async for chunk in super().__aiter__():
                yield chunk
            raise asyncio.CancelledError("sensitive transport cancellation")

    result, _, _ = run(body=CancelledBody(events()[:1], close_error=True))
    assert isinstance(result, api().GuardedResponsesCancelled)
    assert result.reason == "cancelled"
    assert result.stream_closed is False
    assert str(result) == "Guarded Responses request failed"


@pytest.mark.parametrize("number, expected", [("1e308", 1e308), ("-1e308", -1e308), ("0.0", 0.0)])
def test_finite_float_numbers_still_validate(number: str, expected: float) -> None:
    class FloatOutput(BaseModel):
        model_config = ConfigDict(extra="forbid")
        text: float

    result, _, _ = run(
        events('{"text":' + number + "}"),
        kwargs=dict(tool=ToolOutput(FloatOutput, name="answer", strict=True)),
    )
    assert isinstance(result, api().GuardedResponsesToolResult)
    assert result.output.text == expected


@pytest.mark.parametrize("primary", ["transport", "timeout"])
@pytest.mark.parametrize("mask_cancellation", [False, True])
def test_native_cleanup_external_cancel_keeps_earlier_primary_reason(
    primary: str, mask_cancellation: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(api(), "STREAM_DEADLINE_SECONDS", 0.005 if primary == "timeout" else 60)
    monkeypatch.setattr(api(), "STREAM_CLOSE_DEADLINE_SECONDS", 0.05)

    class ClosingBody(Body):
        attempts = 0

        async def __aiter__(self) -> AsyncIterator[bytes]:
            async for chunk in super().__aiter__():
                yield chunk
            # The transport mode raises ReadError in super; timeout mode waits for
            # the operation timer without signalling the test's close-start event.
            await asyncio.Event().wait()

        async def aclose(self) -> None:
            self.attempts += 1
            self.blocked.set()
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                if mask_cancellation:
                    raise RuntimeError("sensitive native cleanup details") from None
                raise

    rows = events()[:1]
    rows[0]["response"]["usage"] = dict(input_tokens=10, output_tokens=5, total_tokens=15)
    body = ClosingBody(rows, read_error=primary == "transport")
    result, _, _ = run(body=body, cancel=True)
    assert isinstance(result, api().GuardedResponsesCancelled)
    assert result.reason == primary
    assert result.known_usage.model_dump() == USAGE
    assert result.usage_complete is False
    assert result.stream_closed is False
    assert body.attempts == 1
    assert not body.closed
    assert str(result) == "Guarded Responses request failed"
    assert result.__cause__ is None


@pytest.mark.parametrize(
    "arguments,stage",
    [
        ("{", "json_parse"),
        ("[]", "json_value"),
        ('{"text":"secret","text":"other"}', "json_value"),
        ('{"text":NaN}', "json_value"),
        ('{"text":1e999}', "json_value"),
        ('{"text":42}', "dto_schema"),
    ],
)
def test_rejection_diagnostic_distinguishes_real_native_output(arguments, stage):
    got, body, requests = run(events(arguments))
    failure(got, "output", known=dict(input_tokens=10, output_tokens=5, requests=1), complete=True)
    assert got.diagnostic_stage == stage
    assert body.closed and len(requests) == 1
    assert "secret" not in str(got)


@pytest.mark.parametrize("stage", ["secret raw body", [], {}, 42])
def test_diagnostic_rejects_untrusted_values(stage):
    error = api().GuardedResponsesError(reason="output", diagnostic_stage=stage)
    assert error.diagnostic_stage is None
    assert "secret" not in str(error)
