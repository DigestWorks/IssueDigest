"""Native synthetic final-generation contracts; no live provider or application."""

import asyncio
import importlib
import importlib.util
import json
from copy import deepcopy

import httpx2 as httpx
import pytest
from openai import AsyncOpenAI
from test_guarded_responses_stream import Body, events
from test_question_briefing import claim, proposal, receipt, reference, source
from test_question_briefing import restore_imports as restore_imports
from test_question_evidence_propositions import QUESTION, TEXT, packet, proposition

USAGE = dict(input_tokens=10, output_tokens=5, requests=1)


def api():
    name = "issuedigest_agents.question_briefing_generation"
    assert importlib.util.find_spec(name) is not None, "Missing final generation SDK"
    return importlib.import_module(name)


def rows(data, name="compose_question_briefing_v1"):
    result = events(json.dumps(data))
    for row in result:
        for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if item is not None:
                item["name"] = name
    return result


async def exercise(
    sources, receipts, data, *, stream=None, mutate=None, cancel=False, options=None
):
    mod = api()
    name = (
        "compose_question_briefing_v3"
        if (options or {}).get("input_format") == "question-briefing-source-v4"
        else "compose_question_briefing_v2"
        if (options or {}).get("input_format") == "question-briefing-source-v3"
        else "compose_question_briefing_v1"
    )
    body = stream or Body(rows(data, name))
    requests = []

    def serve(request):
        requests.append(request)
        if mutate:
            mutate()
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=body)

    http = httpx.AsyncClient(transport=httpx.MockTransport(serve))
    client = AsyncOpenAI(api_key="synthetic", http_client=http, max_retries=0)
    kwargs = dict(
        client=client, model="gpt-6.1-sol", question=QUESTION, sources=sources, receipts=receipts
    )
    kwargs.update(options or {})
    try:
        try:
            if cancel:
                task = asyncio.create_task(mod.run_question_briefing_generation(**kwargs))
                await body.blocked.wait()
                task.cancel()
                got = await task
            else:
                got = await mod.run_question_briefing_generation(**kwargs)
        except (Exception, asyncio.CancelledError) as error:
            got = error
        assert not client.is_closed() and not http.is_closed
        return got, body, requests
    finally:
        await client.close()


def run(sources, receipts, data, **kwargs):
    return asyncio.run(exercise(sources, receipts, data, **kwargs))


def setup():
    src = source()
    return (src,), (receipt(src),), proposal(claim(reference(src)))


def failure(got, reason, *, known=None, started=True, complete=False, closed=True):
    assert type(got) is api().QuestionBriefingGenerationError
    assert got.reason == reason
    assert str(got) == "Guarded Responses request failed"
    assert got.__cause__ is None and got.__context__ is None
    assert (got.known_usage.model_dump() if got.known_usage else None) == known
    assert (got.may_have_started, got.usage_complete, got.stream_closed) == (
        started,
        complete,
        closed,
    )


def test_native_complete_full_fidelity_wire_and_saved_roundtrip():
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    mod = api()
    sources = (source(TEXT + " 2026-10-26", "  e\u0301\noriginal extra quote "), source())
    data = packet(sources[0])
    data["propositions"].append(proposition(sources[0], "p2"))
    receipts = (receipt(sources[0], data), receipt(sources[1]))
    submitted = proposal(claim(reference(sources[0])), claim(reference(sources[1])))
    submitted["modules"] += [
        dict(kind="comparison", title="비교", claims=[claim(reference(s)) for s in sources]),
        dict(
            kind="timeline",
            title="날짜",
            claims=[claim(reference(sources[0]), event_date="2026-10-26")],
        ),
    ]
    got, body, requests = run(sources, receipts, submitted)
    assert type(got) is mod.QuestionBriefingGeneration
    assert body.closed and len(requests) == 1
    assert got.usage.model_dump() == USAGE
    assert got.aggregate_usage.model_dump() == dict(input_tokens=30, output_tokens=15, requests=3)
    assert tuple(s.receipt for s in got.briefing.sources) == receipts
    prompt = mod.question_briefing_prompt(QUESTION, sources, receipts)
    payload = json.loads(prompt)
    assert (
        payload["question"] == QUESTION and payload["input_format"] == "question-briefing-source-v1"
    )
    for src, rec, item in zip(sources, receipts, payload["sources"], strict=True):
        assert item == dict(
            snapshot_id=str(src[0]),
            source_sha256=rec.evidence.source_sha256,
            title=src[2].title,
            quotes=[
                dict(citation_id=str(c.citation_id), text=c.selector.quote)
                for c in src[1].citations
            ],
            evidence=rec.evidence.model_dump(mode="json"),
        )
    tool = mod._preflight(QUESTION, sources, receipts)[1][0]
    schema = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    assert json.loads(requests[0].content) == dict(
        model="gpt-6.1-sol",
        input=prompt,
        instructions=mod.BRIEFING_GENERATION_INSTRUCTIONS,
        stream=True,
        store=False,
        background=False,
        parallel_tool_calls=False,
        reasoning={"effort": "low"},
        service_tier="default",
        max_output_tokens=4000,
        tool_choice={"type": "function", "name": "compose_question_briefing_v1"},
        tools=[
            dict(
                type="function",
                name="compose_question_briefing_v1",
                strict=True,
                parameters=OpenAIJsonSchemaTransformer(schema, strict=True).walk(),
            )
        ],
    )
    for saved in (got, json.loads(got.model_dump_json())):
        checked = mod.validate_question_briefing_generation(QUESTION, sources, receipts, saved)
        assert checked == got and checked is not got


@pytest.mark.parametrize(
    "kind",
    [
        "model",
        "model_subclass",
        "client",
        "question",
        "source_list",
        "receipt",
        "no_link",
        "budget",
    ],
)
def test_preflight_fails_without_http(kind):
    sources, receipts, submitted = setup()
    options = {}
    if kind == "model":
        options["model"] = "other"
    elif kind == "model_subclass":

        class Text(str):
            pass

        options["model"] = Text("gpt-6.1-sol")
    elif kind == "client":
        options["client"] = object()
    elif kind == "question":
        options["question"] = True
    elif kind == "source_list":
        sources = list(sources)
    elif kind == "receipt":
        receipts = (receipts[0].model_copy(update={"status": "reviewed"}),)
    elif kind == "no_link":
        data = packet(sources[0])
        data["coverage"] = dict(linked_proposition_ids=[], unresolved_reason="insufficient")
        receipts = (receipt(sources[0], data),)
    else:
        # Every original receipt fits its own envelope; complete combined input does not.
        sources = tuple(source() for _ in range(3))
        receipts = tuple(receipt(src) for src in sources)
    got, _, requests = run(sources, receipts, submitted, options=options)
    failure(got, "input", started=False, closed=False)
    assert requests == []


@pytest.mark.parametrize(
    "kind", ["wrong_source", "unlinked", "dependency_only", "metadata_date", "missing", "extra"]
)
def test_native_unsupported_proposal_retains_final_cost(kind):
    sources, receipts, submitted = setup()
    src = sources[0]
    if kind in ("unlinked", "dependency_only"):
        data = packet(src)
        data["propositions"].append(proposition(src, "p2"))
        if kind == "dependency_only":
            data["propositions"][0]["depends_on_ids"] = ["p2"]
        receipts = (receipt(src, data),)
        submitted["modules"][0]["claims"][0]["references"][0]["proposition_id"] = "p2"
    elif kind == "wrong_source":
        from uuid import uuid4

        submitted["modules"][0]["claims"][0]["references"][0]["snapshot_id"] = str(uuid4())
    elif kind == "metadata_date":
        submitted["modules"].append(
            dict(
                kind="timeline",
                title="날짜",
                claims=[claim(reference(src), event_date="2026-10-26")],
            )
        )
    elif kind == "missing":
        del submitted["message"]
    else:
        submitted["private"] = "sensitive"
    got, body, requests = run(sources, receipts, submitted)
    failure(got, "output", known=USAGE, complete=True)
    assert body.closed and len(requests) == 1


@pytest.mark.parametrize(
    "kind", ["quote", "title", "metadata", "receipt_usage", "receipt_coverage"]
)
def test_mutation_across_native_await_rejects_even_unreferenced_inputs(kind):
    sources = (source(), source())
    receipts = tuple(receipt(src) for src in sources)
    submitted = proposal(claim(reference(sources[0])))

    def mutate():
        if kind == "quote":
            object.__setattr__(sources[1][1].citations[0].selector, "quote", "changed")
        elif kind in ("title", "metadata"):
            object.__setattr__(
                sources[1][2], "title" if kind == "title" else "bill_number", "changed"
            )
        elif kind == "receipt_usage":
            object.__setattr__(receipts[1].usage, "input_tokens", 11)
        else:
            object.__setattr__(receipts[1].evidence.coverage, "unresolved_reason", "changed")

    got, body, requests = run(sources, receipts, submitted, mutate=mutate)
    failure(got, "output", known=USAGE, complete=True)
    assert body.closed and len(requests) == 1


@pytest.mark.parametrize("stage", ["construction", "validation"])
def test_mutation_after_build_or_final_revalidation_rejects(monkeypatch, stage):
    mod = api()
    sources, receipts, submitted = setup()
    name = (
        "build_question_briefing"
        if stage == "construction"
        else "validate_question_briefing_generation"
    )
    original = getattr(mod, name)

    def changed(*args):
        result = original(*args)
        # Only change after actual final composition, not internal preflight probe.
        if stage == "validation" or args[-1].__class__.__name__ == "QuestionBriefingProposal":
            object.__setattr__(receipts[0].usage, "input_tokens", 11)
        return result

    monkeypatch.setattr(mod, name, changed)
    got, _, requests = run(sources, receipts, submitted)
    failure(got, "output", known=USAGE, complete=True)
    assert len(requests) == 1


@pytest.mark.parametrize(
    "kind", ["incomplete", "unknown_usage", "whitespace", "transport", "cancel"]
)
def test_native_failures_closure_and_cancel_identity(kind):
    sources, receipts, submitted = setup()
    stream = rows(submitted)
    known, complete, reason = None, False, kind
    if kind == "incomplete":
        stream[-1]["type"] = "response.incomplete"
        stream[-1]["response"]["status"] = "incomplete"
        known, complete, reason = USAGE, True, "protocol"
    elif kind == "unknown_usage":
        stream[-1]["response"]["usage"] = None
        reason = "usage"
    elif kind == "whitespace":
        stream[2]["delta"] = " " * 300
    else:
        stream = stream[:2]
    body = Body(stream, read_error=kind == "transport", wait=kind == "cancel")
    got, body, requests = run(sources, receipts, submitted, stream=body, cancel=kind == "cancel")
    assert body.closed and len(requests) == 1
    if kind == "cancel":
        native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
        assert type(got) is native.GuardedResponsesCancelled
        assert got.reason == "cancelled" and got.stream_closed and got.known_usage is None
    else:
        failure(got, reason, known=known, complete=complete)


@pytest.mark.parametrize(
    "kind",
    [
        "profile",
        "status",
        "model",
        "transport",
        "format",
        "prompt",
        "instructions",
        "usage_bool",
        "aggregate",
        "receipt",
        "uncertainty",
        "outcome",
        "module",
        "missing",
        "extra",
        "copy",
        "subclass",
        "raw_subclass",
    ],
)
def test_saved_generation_strict_fields_and_reconstruction(kind):
    mod = api()
    sources, receipts, submitted = setup()
    got, _, _ = run(sources, receipts, submitted)
    raw = got.model_dump(mode="json")
    if kind in ("profile", "status", "model"):
        raw[kind] = "changed"
    elif kind in ("transport", "format"):
        raw["transport_profile" if kind == "transport" else "input_format"] = "changed"
    elif kind in ("prompt", "instructions"):
        raw[kind + "_sha256"] = "0" * 64
    elif kind == "usage_bool":
        raw["usage"]["input_tokens"] = True
    elif kind == "aggregate":
        raw["aggregate_usage"]["input_tokens"] += 1
    elif kind == "receipt":
        raw["briefing"]["sources"][0]["receipt"]["usage"]["input_tokens"] += 1
    elif kind == "uncertainty":
        raw["briefing"]["modules"][0]["claims"][0]["epistemic_status"] = "uncertain"
    elif kind == "outcome":
        raw["briefing"]["outcome"] = "insufficient_evidence"
    elif kind == "module":
        raw["briefing"]["modules"][0]["title"] = "changed"
    elif kind == "missing":
        del raw["briefing"]["proposal"]["message"]
    elif kind == "extra":
        raw["cost"] = 0
    elif kind == "copy":
        raw = got.model_copy(update={"usage": got.usage.model_dump()})
    elif kind == "subclass":

        class Child(mod.QuestionBriefingGeneration):
            pass

        raw = Child(**got.__dict__)
    else:

        class ChildDict(dict):
            pass

        raw = ChildDict(raw)
    with pytest.raises(mod.QuestionBriefingGenerationError) as caught:
        mod.validate_question_briefing_generation(QUESTION, sources, receipts, raw)
    failure(caught.value, "input", started=False, closed=False)


@pytest.mark.parametrize("actual", [False, True])
def test_every_saved_field_required_in_actual_and_json(actual):
    from pydantic import BaseModel
    from test_question_briefing import paths

    mod = api()
    sources, receipts, submitted = setup()
    got, _, _ = run(sources, receipts, submitted)
    for path in paths(got.model_dump(mode="json")):
        changed = deepcopy(got) if actual else got.model_dump(mode="json")
        parent = changed
        for key in path[:-1]:
            parent = getattr(parent, key) if isinstance(parent, BaseModel) else parent[key]
        del (parent.__dict__ if isinstance(parent, BaseModel) else parent)[path[-1]]
        with pytest.raises(mod.QuestionBriefingGenerationError) as caught:
            mod.validate_question_briefing_generation(QUESTION, sources, receipts, changed)
        failure(caught.value, "input", started=False, closed=False)


@pytest.mark.parametrize(
    "kind",
    [
        "output",
        "output_subclass",
        "profile",
        "complete",
        "usage_type",
        "usage_budget",
        "unknown",
        "observations",
        "cancel",
    ],
)
def test_unchecked_native_boundaries_and_observations(monkeypatch, kind):
    mod = api()
    native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
    sources, receipts, submitted = setup()
    usage = mod.KnownUsage(**USAGE)
    output = mod.QuestionBriefingProposal.model_validate_json(json.dumps(submitted), strict=True)
    if kind == "output":
        output = output.model_dump()
    elif kind == "output_subclass":

        class Child(mod.QuestionBriefingProposal):
            pass

        output = Child(**output.__dict__)
    elif kind == "usage_type":
        usage = usage.model_copy(update={"requests": True})
    elif kind == "usage_budget":
        usage = usage.model_copy(update={"output_tokens": 4001})
    result = native.GuardedResponsesToolResult(
        "wrong" if kind == "profile" else native.GUARDED_RESPONSES_PROFILE,
        output,
        usage,
        1 if kind == "complete" else True,
    )
    cancelled = native.GuardedResponsesCancelled(reason="cancelled", may_have_started=True)

    async def forged(**kwargs):
        if kind == "unknown":
            raise RuntimeError("sensitive raw source and provider text")
        if kind == "observations":
            raise mod.GuardedResponsesError(
                reason="transport",
                known_usage=usage,
                may_have_started=True,
                usage_complete=False,
                stream_closed=False,
            )
        if kind == "cancel":
            raise cancelled
        return result

    monkeypatch.setattr(mod, "run_guarded_responses_tool", forged)
    got, _, requests = run(sources, receipts, submitted)
    assert requests == []
    if kind == "cancel":
        assert got is cancelled
    elif kind == "observations":
        failure(got, "transport", known=USAGE, closed=False)
    else:
        terminal = kind in ("output", "output_subclass", "usage_budget")
        failure(
            got,
            "output",
            known=usage.model_dump() if terminal else None,
            complete=terminal,
            closed=terminal,
        )


def test_exact_envelope_boundary_preserves_complete_input_and_one_byte_over_sends_nothing():
    mod = api()
    envelope = importlib.import_module("issuedigest_agents.role_bounded_runtime")._request_envelope
    first, second = source(), source(TEXT, "x")
    sources, receipts = (first, second), (receipt(first), receipt(second))
    prompt, tools, _ = mod._preflight(QUESTION, sources, receipts)
    remaining = 20000 - envelope(prompt, tools, mod.BRIEFING_GENERATION_INSTRUCTIONS, 4000)
    assert remaining > 0
    second = source(TEXT, "x" * (1 + remaining))
    sources, receipts = (first, second), (receipt(first), receipt(second))
    prompt, tools, _ = mod._preflight(QUESTION, sources, receipts)
    assert envelope(prompt, tools, mod.BRIEFING_GENERATION_INSTRUCTIONS, 4000) == 20000
    submitted = proposal(claim(reference(first)), claim(reference(second)))
    got, body, requests = run(sources, receipts, submitted)
    assert type(got) is mod.QuestionBriefingGeneration and body.closed and len(requests) == 1
    assert json.loads(prompt)["sources"][1]["quotes"][1]["text"] == "x" * (1 + remaining)
    second = source(TEXT, "x" * (2 + remaining))
    sources, receipts = (first, second), (receipt(first), receipt(second))
    got, _, requests = run(sources, receipts, submitted)
    failure(got, "input", started=False, closed=False)
    assert requests == []


def test_insufficient_generated_response_is_real_paid_result_not_probe():
    mod = api()
    sources, receipts, _ = setup()
    submitted = dict(outcome="insufficient_evidence", message="지원되는 답이 없습니다.", modules=[])
    got, body, requests = run(sources, receipts, submitted)
    assert type(got) is mod.QuestionBriefingGeneration
    assert got.briefing.message == submitted["message"]
    assert got.briefing.proposal.model_dump(mode="json") == submitted
    assert got.aggregate_usage.model_dump() == dict(input_tokens=20, output_tokens=10, requests=2)
    assert got.usage.model_dump() == USAGE and body.closed and len(requests) == 1


def test_prompt_is_pure_and_no_link_probe_is_never_a_success(monkeypatch):
    import socket
    import sys

    mod = api()
    sources, receipts, _ = setup()
    before = set(sys.modules)
    monkeypatch.setattr(socket.socket, "connect", lambda *a: pytest.fail("Unexpected network"))
    prompt = mod.question_briefing_prompt(QUESTION, sources, receipts)
    assert prompt == mod.question_briefing_prompt(QUESTION, sources, receipts)
    assert json.loads(prompt)["question"] == QUESTION
    data = packet(sources[0])
    data["coverage"] = dict(linked_proposition_ids=[], unresolved_reason="insufficient")
    with pytest.raises(mod.QuestionBriefingGenerationError) as caught:
        mod.question_briefing_prompt(QUESTION, sources, (receipt(sources[0], data),))
    failure(caught.value, "input", started=False, closed=False)
    assert not any(
        name.startswith(("issuedigest_api", "issuedigest_worker", "dbos"))
        for name in set(sys.modules) - before
    )


def test_native_v3_preserves_receipt_and_original_final_wire():
    from test_question_briefing import receipt_v3

    src = source()
    submitted = proposal(claim(reference(src)))
    old, _, old_requests = run((src,), (receipt(src),), submitted)
    evidence = receipt_v3(src)
    got, _, requests = run((src,), (evidence,), submitted)
    assert type(got) is api().QuestionBriefingGeneration
    assert requests[0].content == old_requests[0].content
    assert got.briefing.sources[0].receipt == evidence
    assert got.briefing.sources[0].receipt.profile == "guarded-question-evidence-v3"
    assert (
        api().validate_question_briefing_generation(
            QUESTION, (src,), (evidence,), got.model_dump(mode="json")
        )
        == got
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("prompt_sha256", "0" * 64),
        ("instructions_sha256", "0" * 64),
        ("input_format", "question-evidence-source-v2"),
        ("profile", "guarded-question-evidence-v2"),
    ],
)
def test_v3_invalid_original_metadata_stops_before_provider(field, value):
    from test_question_briefing import receipt_v3

    src = source()
    evidence = receipt_v3(src)
    object.__setattr__(evidence, field, value)
    got, _, requests = run((src,), (evidence,), proposal(claim(reference(src))))
    failure(got, "input", started=False, closed=False)
    assert requests == []


def test_native_v5_preserves_original_final_wire():
    from test_question_briefing import receipt_v5

    src = source(TEXT.replace("기관은 반복한다", "반복한다"))
    submitted = proposal(claim(reference(src)))
    old, _, old_requests = run((src,), (receipt(src),), submitted)
    evidence = receipt_v5(src)
    got, _, requests = run((src,), (evidence,), submitted)
    assert type(got) is api().QuestionBriefingGeneration
    assert requests[0].content == old_requests[0].content
    assert got.briefing.sources[0].receipt == evidence
    assert (
        api().validate_question_briefing_generation(
            QUESTION, (src,), (evidence,), got.model_dump(mode="json")
        )
        == got
    )


def test_v2_explicit_format_and_hash_pair_roundtrip():
    mod = api()
    sources, receipts, submitted = setup()
    got, body, requests = run(
        sources, receipts, submitted, options={"input_format": "question-briefing-source-v2"}
    )
    assert type(got) is mod.QuestionBriefingGeneration
    assert got.input_format == "question-briefing-source-v2"
    assert (
        mod.briefing_input_format_from_instructions_hash(got.instructions_sha256)
        == got.input_format
    )
    assert mod.validate_question_briefing_generation(QUESTION, sources, receipts, got) == got
    wire = json.loads(requests[0].content)
    assert wire["instructions"] == mod.briefing_generation_instructions(got.input_format)
    changed = got.model_dump(mode="json")
    changed["input_format"] = "question-briefing-source-v1"
    with pytest.raises(mod.QuestionBriefingGenerationError):
        mod.validate_question_briefing_generation(QUESTION, sources, receipts, changed)
    with pytest.raises(ValueError):
        mod.briefing_input_format_from_instructions_hash("0" * 64)


def test_unknown_input_format_fails_before_http():
    sources, receipts, submitted = setup()
    got, _, requests = run(sources, receipts, submitted, options={"input_format": "unknown"})
    failure(got, "input", started=False, closed=False)
    assert requests == []


def test_historical_v1_instructions_and_provider_request_bytes_are_stable():
    from hashlib import sha256

    mod = api()
    sources, receipts, submitted = setup()
    first, _, calls = run(sources, receipts, submitted)
    explicit, _, explicit_calls = run(
        sources, receipts, submitted, options={"input_format": "question-briefing-source-v1"}
    )
    assert calls[0].content == explicit_calls[0].content
    assert first == explicit
    assert sha256(mod.BRIEFING_GENERATION_INSTRUCTIONS.encode()).hexdigest() == (
        "026e3c82fbeb8a426635c8ef0a4224546715b31c89c49f6ecfbe50e92bbbc09d"
    )


@pytest.mark.parametrize("outcome", ["answer", "insufficient_evidence"])
def test_v3_outcome_specific_native_wire_and_canonical_receipt(outcome):
    mod = api()
    sources, receipts, answer = setup()
    branch = (
        {"outcome": "answer", "modules": answer["modules"]}
        if outcome == "answer"
        else {"outcome": "insufficient_evidence", "message": "근거의 한계"}
    )
    got, _, calls = run(
        sources,
        receipts,
        {"result": branch},
        options={"input_format": "question-briefing-source-v3"},
    )
    assert type(got) is mod.QuestionBriefingGeneration
    assert got.input_format == "question-briefing-source-v3"
    assert got.briefing.outcome == outcome
    assert mod.validate_question_briefing_generation(QUESTION, sources, receipts, got) == got
    wire = json.loads(calls[0].content)
    assert wire["tools"][0]["name"] == "compose_question_briefing_v2"
    assert "anyOf" in wire["tools"][0]["parameters"]["properties"]["result"]
    assert (
        mod.briefing_input_format_from_instructions_hash(got.instructions_sha256)
        == got.input_format
    )


def test_v3_rejects_answer_with_extra_message_without_dropping_it():
    sources, receipts, answer = setup()
    answer["message"] = "삭제하면 안 되는 한계"
    got, _, calls = run(
        sources,
        receipts,
        {"result": answer},
        options={"input_format": "question-briefing-source-v3"},
    )
    assert len(calls) == 1
    assert type(got) is api().QuestionBriefingGenerationError


def test_v4_structural_tool_native_to_canonical():
    sources, receipts, _ = setup()
    from test_briefing_input_v4 import answer

    got, _, calls = run(
        sources, receipts, answer(), options={"input_format": "question-briefing-source-v4"}
    )
    assert type(got) is api().QuestionBriefingGeneration
    assert got.input_format == "question-briefing-source-v4"
    assert got.briefing.modules[0].claims[0].event_date is None
    assert json.loads(calls[0].content)["tools"][0]["name"] == "compose_question_briefing_v3"
