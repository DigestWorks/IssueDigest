"""Synthetic source-specific native SDK integration; no app or provider activation."""

import asyncio
import importlib
import importlib.util
import json
from copy import deepcopy
from hashlib import sha256

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
from pydantic_ai.tools import GenerateToolJsonSchema
from test_guarded_responses_stream import Body, events
from test_guarded_responses_stream import (
    restore_introduced_agent_modules as restore_introduced_agent_modules,
)
from test_numeric_evidence import document
from test_question_evidence_propositions import QUESTION, TEXT, packet

EMPTY = dict(
    propositions=[], coverage=dict(linked_proposition_ids=[], unresolved_reason="insufficient")
)
USAGE = dict(input_tokens=10, output_tokens=5, requests=1)


def api():
    name = "issuedigest_agents.guarded_question_evidence"
    assert importlib.util.find_spec(name) is not None, "Missing guarded question SDK"
    return importlib.import_module(name)


def rows(data):
    result = events(json.dumps(data))
    for row in result:
        for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if item is not None:
                item["name"] = "fill_question_evidence_v2"
    return result


async def exercise(src, data=None, *, stream=None, mutate=None, cancel=False, options=None):
    mod = api()
    body = stream or Body(rows(packet(src) if data is None else data))
    requests = []

    def serve(request):
        requests.append(request)
        if mutate:
            mutate(src)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)

    http = httpx.AsyncClient(transport=httpx.MockTransport(serve))
    client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
    kwargs = dict(client=client, model=" model ", source=src, question=QUESTION)
    kwargs.update(options or {})
    try:
        try:
            if cancel:
                task = asyncio.create_task(mod.run_guarded_question_evidence(**kwargs))
                await body.blocked.wait()
                task.cancel()
                got = await task
            else:
                got = await mod.run_guarded_question_evidence(**kwargs)
        except (Exception, asyncio.CancelledError) as error:
            got = error
        assert not client.is_closed() and not http.is_closed
        return got, body, requests
    finally:
        await client.close()


def run(src, data=None, **kwargs):
    return asyncio.run(exercise(src, data, **kwargs))


def failure(got, reason, *, known=None, started=True, complete=False, closed=True):
    assert isinstance(got, api().GuardedQuestionEvidenceError)
    assert str(got) == "Guarded Responses request failed"
    assert got.reason == reason
    assert got.known_usage.model_dump() == known if known else got.known_usage is None
    assert (got.may_have_started, got.usage_complete, got.stream_closed) == (
        started,
        complete,
        closed,
    )
    assert got.__cause__ is None and got.__suppress_context__


def test_complete_receipt_exact_wire_and_fresh_json_roundtrip():
    mod, src = api(), document(TEXT, "  e\u0301\nwhole extra quote ")
    got, body, requests = run(src)
    assert type(got) is mod.GuardedQuestionEvidenceGeneration
    assert got.profile == "guarded-question-evidence-v1"
    assert got.transport_profile == "guarded-responses-tool-v1"
    assert got.status == got.evidence.status == "unreviewed"
    assert got.evidence.model_dump(mode="json")["propositions"] == packet(src)["propositions"]
    assert got.usage.model_dump() == USAGE
    assert body.closed and len(requests) == 1
    wire = json.loads(requests[0].content)
    v2 = importlib.import_module("issuedigest_agents.question_evidence_generation_v2")
    prompt, tools = v2._preflight(src, QUESTION)
    schema = tools[0].output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    assert wire == dict(
        model=" model ",
        input=prompt,
        instructions=v2.QUESTION_EVIDENCE_V2_INSTRUCTIONS,
        stream=True,
        store=False,
        background=False,
        parallel_tool_calls=False,
        reasoning={"effort": "low"},
        service_tier="default",
        max_output_tokens=4000,
        tool_choice={"type": "function", "name": "fill_question_evidence_v2"},
        tools=[
            dict(
                type="function",
                name="fill_question_evidence_v2",
                strict=True,
                parameters=OpenAIJsonSchemaTransformer(schema, strict=True).walk(),
            )
        ],
    )
    assert json.loads(prompt)["question"] == QUESTION
    assert [q["text"] for q in json.loads(prompt)["quotes"]] == [
        TEXT,
        "  e\u0301\nwhole extra quote ",
    ]
    assert got.prompt_sha256 == sha256(prompt.encode()).hexdigest()
    for saved in (got, json.loads(got.model_dump_json())):
        checked = mod.validate_guarded_question_evidence(src, QUESTION, saved)
        assert checked == got and checked is not got and checked.evidence is not got.evidence


def test_empty_insufficient_is_structural_only():
    got, _, _ = run(document(TEXT), EMPTY)
    assert got.evidence.propositions == ()
    assert got.evidence.coverage.unresolved_reason == "insufficient"
    assert got.status == "unreviewed"


@pytest.mark.parametrize("kind", ["incomplete", "json", "whitespace", "transport", "cancel"])
def test_native_failures_retain_observations(kind):
    src = document(TEXT)
    stream = rows(EMPTY)
    known, complete, reason = None, False, kind
    if kind == "incomplete":
        stream[-1]["type"] = "response.incomplete"
        stream[-1]["response"]["status"] = "incomplete"
        known, complete, reason = USAGE, True, "protocol"
    elif kind == "json":
        stream = rows(EMPTY)
        for row in stream:
            if "delta" in row:
                row["delta"] = "{"
            if "arguments" in row:
                row["arguments"] = "{"
            for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
                if item and item["status"] == "completed":
                    item["arguments"] = "{"
        known, complete, reason = USAGE, True, "output"
    elif kind == "whitespace":
        stream[2]["delta"] = " " * 300
    elif kind in ("transport", "cancel"):
        stream = stream[:2]
    body = Body(stream, read_error=kind == "transport", wait=kind == "cancel")
    got, body, requests = run(src, stream=body, cancel=kind == "cancel")
    assert body.closed and len(requests) == 1
    if kind == "cancel":
        native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
        assert type(got) is native.GuardedResponsesCancelled
        assert got.reason == "cancelled" and got.stream_closed
    else:
        failure(got, reason, known=known, complete=complete)


@pytest.mark.parametrize("field", ["quote", "title", "bill_number"])
def test_source_mutation_during_await_rejects_with_terminal_usage(field):
    src = document(TEXT)

    def mutate(source):
        target = source[1].citations[0].selector if field == "quote" else source[2]
        object.__setattr__(target, field, "changed source")

    got, _, requests = run(src, mutate=mutate)
    failure(got, "output", known=USAGE, complete=True)
    assert len(requests) == 1


@pytest.mark.parametrize("kind", ["source", "question", "budget", "client", "model"])
def test_invalid_preflight_sends_zero_requests(kind):
    src, options = document(TEXT), {}
    if kind == "source":
        src = list(src)
    elif kind == "question":
        options["question"] = True
    elif kind == "budget":
        src = document("x" * 22000)
    elif kind == "client":
        options["client"] = object()
    else:
        options["model"] = " "
    got, _, requests = run(src, EMPTY, options=options)
    failure(got, "input", started=False, closed=False)
    assert requests == []


@pytest.mark.parametrize(
    "kind",
    [
        "profile",
        "transport",
        "hash",
        "missing",
        "extra",
        "usage",
        "constructed",
        "question",
        "source",
    ],
)
def test_saved_tampering_and_original_types_reject(kind):
    mod, src = api(), document(TEXT)
    got, _, _ = run(src)
    raw = deepcopy(got.model_dump(mode="json"))
    question = QUESTION
    if kind == "profile":
        raw["profile"] = "question-evidence-generation-v2"
    elif kind == "transport":
        raw["transport_profile"] = "other"
    elif kind == "hash":
        raw["prompt_sha256"] = "0" * 64
    elif kind == "missing":
        del raw["evidence"]["coverage"]["unresolved_reason"]
    elif kind == "extra":
        raw["extra"] = "secret"
    elif kind == "usage":
        raw["usage"]["requests"] = True
    elif kind == "constructed":
        raw = got.model_copy(update={"usage": got.usage.model_dump()})
    elif kind == "question":
        question += " "
    else:
        object.__setattr__(src[2], "title", "changed metadata")
    with pytest.raises(mod.GuardedQuestionEvidenceError):
        mod.validate_guarded_question_evidence(src, question, raw)


@pytest.mark.parametrize(
    "kind", ["output", "profile", "complete", "usage_type", "usage_budget", "unknown"]
)
def test_unchecked_native_boundary_never_manufactures_receipt(monkeypatch, kind):
    mod, src = api(), document(TEXT)
    native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
    contracts = importlib.import_module("issuedigest_agents.numeric_evidence")
    usage = contracts.KnownUsage(**USAGE)
    output = mod.QuestionEvidenceInput.model_validate_json(json.dumps(packet(src)), strict=True)
    if kind == "output":
        output = output.model_dump()
    if kind == "usage_type":
        usage = usage.model_copy(update={"requests": True})
    if kind == "usage_budget":
        usage = usage.model_copy(update={"output_tokens": 4001})
    result = native.GuardedResponsesToolResult(
        "wrong" if kind == "profile" else native.GUARDED_RESPONSES_PROFILE,
        output,
        usage,
        1 if kind == "complete" else True,
    )

    async def forged(**kwargs):
        if kind == "unknown":
            raise RuntimeError("sensitive raw detail")
        return result

    monkeypatch.setattr(mod, "run_guarded_responses_tool", forged)
    got, _, requests = run(src)
    known = usage.model_dump() if kind in ("output", "usage_budget") else None
    failure(
        got,
        "output",
        known=known,
        complete=kind in ("output", "usage_budget"),
        closed=kind in ("output", "usage_budget"),
    )
    assert requests == []


def test_cancellation_is_reraised_by_identity_and_no_app_imports(monkeypatch):
    import sys

    mod, src = api(), document(TEXT)
    native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
    original = native.GuardedResponsesCancelled(reason="cancelled", may_have_started=True)
    before = set(sys.modules)

    async def cancelled(**kwargs):
        raise original

    monkeypatch.setattr(mod, "run_guarded_responses_tool", cancelled)
    got, _, _ = run(src)
    assert got is original
    introduced = set(sys.modules) - before
    assert not any(
        name.startswith(("issuedigest_api", "issuedigest_worker", "dbos")) for name in introduced
    )


@pytest.mark.parametrize("actual", [False, True])
def test_every_required_saved_field_is_required_even_null_empty(actual):
    from pydantic import BaseModel

    mod, src = api(), document(TEXT)
    got, _, _ = run(src)

    def paths(value, prefix=()):
        if isinstance(value, dict):
            for key, child in value.items():
                yield (*prefix, key)
                yield from paths(child, (*prefix, key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from paths(child, (*prefix, index))

    for path in paths(got.model_dump(mode="json")):
        changed = deepcopy(got) if actual else got.model_dump(mode="json")
        parent = changed
        for key in path[:-1]:
            parent = getattr(parent, key) if isinstance(parent, BaseModel) else parent[key]
        del (parent.__dict__ if isinstance(parent, BaseModel) else parent)[path[-1]]
        with pytest.raises(mod.GuardedQuestionEvidenceError):
            mod.validate_guarded_question_evidence(src, QUESTION, changed)
