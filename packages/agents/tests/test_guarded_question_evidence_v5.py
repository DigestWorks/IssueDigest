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
from test_question_evidence_propositions import QUESTION
from test_question_evidence_propositions import packet as canonical_packet
from test_question_text_references import text_only


def packet(src):
    return text_only(canonical_packet(src))


TEXT = (
    "🧪 기관은 좌석·수용 인원 각각 3 이내를 계획한다. "
    "승인 후 다음 달 신청 예정이며 법적 지위 부여 아님. e\u0301.\n끝"
)

EMPTY = dict(
    propositions=[], coverage=dict(linked_proposition_ids=[], unresolved_reason="insufficient")
)
SUFFIX = (
    " Field rules: fill subject_refs and predicate_refs with exact spans when supported."
    " If subject_refs or predicate_refs is empty, epistemic_status must be uncertain."
    " Empty quantity metric_refs or relative-time anchor_refs also requires uncertain."
    " Broad supporting_refs cannot replace these fields; never invent missing references."
)
USAGE = dict(input_tokens=10, output_tokens=5, requests=1)


def api():
    name = "issuedigest_agents.guarded_question_evidence_v5"
    assert importlib.util.find_spec(name) is not None, "Missing guarded question SDK"
    return importlib.import_module(name)


def rows(data):
    result = events(json.dumps(data))
    for row in result:
        for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if item is not None:
                item["name"] = "fill_question_evidence_v5"
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
                task = asyncio.create_task(mod.run_guarded_question_evidence_v5(**kwargs))
                await body.blocked.wait()
                task.cancel()
                got = await task
            else:
                got = await mod.run_guarded_question_evidence_v5(**kwargs)
        except (Exception, asyncio.CancelledError) as error:
            got = error
        assert not client.is_closed() and not http.is_closed
        return got, body, requests
    finally:
        await client.close()


def run(src, data=None, **kwargs):
    return asyncio.run(exercise(src, data, **kwargs))


def failure(got, reason, *, known=None, started=True, complete=False, closed=True):
    assert isinstance(got, api().GuardedQuestionEvidenceV5Error)
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
    assert type(got) is mod.GuardedQuestionEvidenceGenerationV5
    assert got.profile == "guarded-question-evidence-v5"
    assert got.transport_profile == "guarded-responses-tool-v1"
    assert got.status == got.evidence.status == "unreviewed"
    assert (
        got.evidence.model_dump(mode="json")["propositions"]
        == canonical_packet(src)["propositions"]
    )
    assert got.usage.model_dump() == USAGE
    assert body.closed and len(requests) == 1
    wire = json.loads(requests[0].content)
    prompt, tools = mod._preflight(src, QUESTION)
    schema = tools[0].output.model_json_schema(schema_generator=GenerateToolJsonSchema)
    assert wire == dict(
        model=" model ",
        input=prompt,
        instructions=mod.GUARDED_QUESTION_V5_INSTRUCTIONS,
        stream=True,
        store=False,
        background=False,
        parallel_tool_calls=False,
        reasoning={"effort": "low"},
        service_tier="default",
        max_output_tokens=4000,
        tool_choice={"type": "function", "name": "fill_question_evidence_v5"},
        tools=[
            dict(
                type="function",
                name="fill_question_evidence_v5",
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
    assert mod.REFERENCE_RULES_SUFFIX == SUFFIX
    assert (
        got.instructions_sha256
        == sha256((mod.GUARDED_QUESTION_V5_INSTRUCTIONS).encode()).hexdigest()
    )
    assert got.prompt_sha256 == sha256(prompt.encode()).hexdigest()
    for saved in (got, json.loads(got.model_dump_json())):
        checked = mod.validate_guarded_question_evidence_v5(src, QUESTION, saved)
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
    assert got.diagnostic_stage == "source_integrity"


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
        "input_format",
        "instructions_hash",
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
        raw["profile"] = "question-evidence-generation-v5"
    elif kind == "transport":
        raw["transport_profile"] = "other"
    elif kind == "input_format":
        raw["input_format"] = "question-evidence-source-v3"
    elif kind == "instructions_hash":
        raw["instructions_sha256"] = "0" * 64
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
    with pytest.raises(mod.GuardedQuestionEvidenceV5Error) as rejected:
        mod.validate_guarded_question_evidence_v5(src, question, raw)
    assert rejected.value.diagnostic_stage == (
        "evidence_contract" if kind in ("question", "source") else "generation_receipt"
    )


@pytest.mark.parametrize(
    "kind", ["output", "profile", "complete", "usage_type", "usage_budget", "unknown"]
)
def test_unchecked_native_boundary_never_manufactures_receipt(monkeypatch, kind):
    mod, src = api(), document(TEXT)
    native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
    contracts = importlib.import_module("issuedigest_agents.numeric_evidence")
    usage = contracts.KnownUsage(**USAGE)
    output = mod.QuestionEvidenceTextInput.model_validate_json(json.dumps(packet(src)), strict=True)
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
    assert (
        got.diagnostic_stage
        == {
            "output": "native_output",
            "profile": "native_receipt",
            "complete": "native_receipt",
            "usage_type": "native_usage",
            "usage_budget": "native_usage",
            "unknown": "stream",
        }[kind]
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
        with pytest.raises(mod.GuardedQuestionEvidenceV5Error):
            mod.validate_guarded_question_evidence_v5(src, QUESTION, changed)


@pytest.mark.parametrize("field", ["subject", "predicate", "metric", "anchor"])
@pytest.mark.parametrize("status", ["source_statement", "uncertain"])
def test_empty_field_rules_remain_strict_without_repair(field, status):
    src = document(TEXT)
    data = packet(src)
    prop = data["propositions"][0]
    prop["epistemic_status"] = status
    if field in ("subject", "predicate"):
        prop[field + "_refs"] = []
    elif field == "metric":
        prop["facets"][0]["value"]["metric_refs"] = []
    else:
        prop["facets"][4]["value"]["anchor_refs"] = []
    got, _, requests = run(src, data)
    assert len(requests) == 1
    if status == "source_statement":
        failure(got, "output", known=USAGE, complete=True)
    else:
        assert (
            text_only(got.evidence.model_dump(mode="json"))["propositions"] == data["propositions"]
        )
        assert got.status == "unreviewed"


@pytest.mark.parametrize("field", ["profile", "instructions_sha256"])
def test_historical_receipt_substitutions_reject_both_directions(field):
    mod, src = api(), document(TEXT)
    old = importlib.import_module("issuedigest_agents.guarded_question_evidence")
    got, _, _ = run(src)
    raw = got.model_dump(mode="json")
    historical = dict(
        raw,
        profile="guarded-question-evidence-v1",
        instructions_sha256=sha256(old.QUESTION_EVIDENCE_V2_INSTRUCTIONS.encode()).hexdigest(),
    )
    changed = dict(raw)
    changed[field] = historical[field]
    with pytest.raises(mod.GuardedQuestionEvidenceV5Error):
        mod.validate_guarded_question_evidence_v5(src, QUESTION, changed)
    historical[field] = raw[field]
    with pytest.raises(old.GuardedQuestionEvidenceError):
        old.validate_guarded_question_evidence(src, QUESTION, historical)


def test_new_envelope_exact_boundary_and_over_sends_nothing():
    mod = api()
    envelope = importlib.import_module("issuedigest_agents.role_bounded_runtime")._request_envelope
    src = document("x")
    prompt, tools = mod._preflight(src, QUESTION)
    remaining = 20000 - envelope(prompt, tools, mod.GUARDED_QUESTION_V5_INSTRUCTIONS, 4000)
    src = document("x" * (1 + remaining))
    prompt, tools = mod._preflight(src, QUESTION)
    assert envelope(prompt, tools, mod.GUARDED_QUESTION_V5_INSTRUCTIONS, 4000) == 20000
    got, _, requests = run(src, EMPTY)
    assert type(got) is mod.GuardedQuestionEvidenceGenerationV5 and len(requests) == 1
    got, _, requests = run(document("x" * (2 + remaining)), EMPTY)
    failure(got, "input", started=False, closed=False)
    assert requests == []


@pytest.mark.parametrize("stage", ["construction", "validation"])
def test_source_mutation_after_completion_retains_original_usage(monkeypatch, stage):
    mod, src = api(), document(TEXT)
    name = (
        "build_question_scoped_text_evidence"
        if stage == "construction"
        else "validate_guarded_question_evidence_v5"
    )
    original = getattr(mod, name)

    def changed(*args):
        result = original(*args)
        object.__setattr__(src[2], "title", "changed after original check")
        return result

    monkeypatch.setattr(mod, name, changed)
    got, _, requests = run(src)
    failure(got, "output", known=USAGE, complete=True)
    assert len(requests) == 1


def test_native_observations_are_forwarded_without_inventing_completion(monkeypatch):
    mod, src = api(), document(TEXT)
    usage = mod.KnownUsage(**USAGE)

    async def observed(**kwargs):
        raise mod.GuardedResponsesError(
            reason="transport",
            known_usage=usage,
            may_have_started=True,
            usage_complete=False,
            stream_closed=False,
        )

    monkeypatch.setattr(mod, "run_guarded_responses_tool", observed)
    got, _, requests = run(src)
    failure(got, "transport", known=USAGE, complete=False, closed=False)
    assert requests == []


def test_contract_rejection_has_source_stage_after_native_schema_acceptance():
    src = document(TEXT)
    data = packet(src)
    data["propositions"][0]["subject_refs"] = []
    data["propositions"][0]["epistemic_status"] = "source_statement"
    got, _, requests = run(src, data)
    failure(got, "output", known=USAGE, complete=True)
    assert got.diagnostic_stage == "evidence_contract"
    assert len(requests) == 1


def test_native_json_stage_survives_source_wrapper():
    stream = rows(EMPTY)
    for row in stream:
        if "delta" in row:
            row["delta"] = "{"
        if "arguments" in row:
            row["arguments"] = "{"
        for value in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if value and value["status"] == "completed":
                value["arguments"] = "{"
    got, _, _ = run(document(TEXT), stream=Body(stream))
    failure(got, "output", known=USAGE, complete=True)
    assert got.diagnostic_stage == "json_parse"


def test_provider_schema_has_only_text_references_and_all_eight_facets():
    mod, src = api(), document(TEXT)
    _, tools = mod._preflight(src, QUESTION)
    schema = tools[0].output.model_json_schema()
    assert schema["$defs"]["EvidenceRef"]["properties"].keys() == {"citation_id", "text"}
    assert not any(f'"{name}"' in json.dumps(schema) for name in ("start", "end", "occurrence"))
    got, _, _ = run(src)
    assert {f.kind for f in got.evidence.propositions[0].facets} == {
        "quantity",
        "bound",
        "distribution",
        "time",
        "eligibility",
        "prerequisite",
        "legal_effect",
        "procedure",
    }


@pytest.mark.parametrize("text", ["기관", "missing", "é", "aa"])
def test_missing_normalized_and_overlapping_ambiguous_text_never_repairs(text):
    src = document("기관 기관 aaa e\u0301")
    data = dict(
        propositions=[
            dict(
                id="p1",
                epistemic_status="uncertain",
                supporting_refs=[dict(citation_id=str(src[1].citations[0].citation_id), text=text)],
                subject_refs=[],
                predicate_refs=[],
                facets=[],
                depends_on_ids=[],
            )
        ],
        coverage=dict(linked_proposition_ids=["p1"], unresolved_reason=None),
    )
    before = deepcopy(data)
    got, _, requests = run(src, data)
    failure(got, "output", known=USAGE, complete=True)
    assert got.diagnostic_stage == "evidence_contract" and len(requests) == 1
    assert data == before


@pytest.mark.parametrize("field", ["start", "end", "occurrence"])
def test_provider_offsets_and_occurrence_are_rejected(field):
    src = document(TEXT)
    data = packet(src)
    data["propositions"][0]["supporting_refs"][0][field] = 0
    got, _, requests = run(src, data)
    failure(got, "output", known=USAGE, complete=True)
    assert got.diagnostic_stage == "dto_schema" and len(requests) == 1


def test_wrong_tool_is_rejected_without_retry():
    stream = rows(EMPTY)
    stream[1]["item"]["name"] = "fill_question_evidence_v2"
    got, body, requests = run(document(TEXT), stream=Body(stream))
    failure(got, "protocol")
    assert body.closed and len(requests) == 1


def test_timeout_and_failed_close_preserve_observations(monkeypatch):
    native = importlib.import_module("issuedigest_agents.guarded_responses_stream")
    monkeypatch.setattr(native, "STREAM_DEADLINE_SECONDS", 0.01)
    got, body, requests = run(document(TEXT), stream=Body(rows(EMPTY)[:1], wait=True))
    failure(got, "timeout")
    assert body.closed and len(requests) == 1
    got, body, requests = run(document(TEXT), stream=Body(rows(EMPTY), close_error=True))
    failure(got, "transport", known=USAGE, complete=True, closed=False)
    assert not body.closed and len(requests) == 1


def test_scoped_instructions_and_shared_transport():
    mod = api()
    old = importlib.import_module("issuedigest_agents.guarded_question_evidence_v4")
    assert "complete JSON arguments" in mod.GUARDED_QUESTION_V5_INSTRUCTIONS
    assert "supporting_refs" in mod.GUARDED_QUESTION_V5_INSTRUCTIONS
    assert "same proposition" in mod.GUARDED_QUESTION_V5_INSTRUCTIONS
    assert mod.REFERENCE_RULES_SUFFIX == old.REFERENCE_RULES_SUFFIX == SUFFIX
    assert mod.run_guarded_responses_tool is old.run_guarded_responses_tool


def test_v3_receipts_and_v5_receipts_cannot_be_substituted():
    mod, src = api(), document(TEXT)
    old = importlib.import_module("issuedigest_agents.guarded_question_evidence_v3")
    receipt, _, _ = run(src)
    raw = receipt.model_dump(mode="json")
    with pytest.raises(old.GuardedQuestionEvidenceV3Error):
        old.validate_guarded_question_evidence_v3(src, QUESTION, raw)
    historical = dict(
        raw,
        profile="guarded-question-evidence-v3",
        input_format="question-evidence-source-v3",
        prompt_sha256=sha256(old._preflight(src, QUESTION)[0].encode()).hexdigest(),
        instructions_sha256=sha256(old.GUARDED_QUESTION_V3_INSTRUCTIONS.encode()).hexdigest(),
    )
    checked = old.validate_guarded_question_evidence_v3(src, QUESTION, historical)
    assert checked.status == "unreviewed"
    with pytest.raises(mod.GuardedQuestionEvidenceV5Error):
        mod.validate_guarded_question_evidence_v5(src, QUESTION, historical)


def test_compact_instruction_preserves_string_whitespace_and_accepts_formatted_json():
    src = document(TEXT, "  preserve  spaces\n\tand e\u0301 ")
    data = packet(src)
    arguments = json.dumps(data, ensure_ascii=False, indent=1)
    stream = events(arguments)
    for row in stream:
        for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if item is not None:
                item["name"] = "fill_question_evidence_v5"
    got, _, requests = run(src, stream=Body(stream))
    assert type(got) is api().GuardedQuestionEvidenceGenerationV5
    assert text_only(got.evidence.model_dump(mode="json"))["propositions"] == data["propositions"]
    prompt = json.loads(json.loads(requests[0].content)["input"])
    assert [q["text"] for q in prompt["quotes"]] == [TEXT, "  preserve  spaces\n\tand e\u0301 "]


@pytest.mark.parametrize("padding", [256, 257])
def test_native_whitespace_guard_boundary_is_unchanged(padding):
    arguments = " " * padding + json.dumps(EMPTY)
    stream = events(arguments)
    for row in stream:
        for item in [row.get("item"), *row.get("response", {}).get("output", [])]:
            if item is not None:
                item["name"] = "fill_question_evidence_v5"
    got, body, requests = run(document(TEXT), stream=Body(stream))
    assert body.closed and len(requests) == 1
    if padding == 256:
        assert type(got) is api().GuardedQuestionEvidenceGenerationV5
    else:
        failure(got, "whitespace")


def test_scoped_global_duplicates_roundtrip_all_facets():
    from test_question_evidence_propositions import ref

    src = document(
        TEXT + " 기관 좌석 수용 인원 각각 3 이내 계획한다 승인 후 다음 달 신청 예정 지위 부여 아님"
    )
    data = packet(src)
    data["propositions"][0]["supporting_refs"] = [text_only(ref(src, TEXT))]
    got, _, requests = run(src, data)
    assert type(got) is api().GuardedQuestionEvidenceGenerationV5
    assert len(requests) == 1
    for saved in (got, got.model_dump(mode="json")):
        assert api().validate_guarded_question_evidence_v5(src, QUESTION, saved) == got


@pytest.mark.parametrize("support,subject", [("x3y z3w", "3"), ("3", "3")])
def test_scoped_ambiguity_rejects_after_native_completion(support, subject):
    from test_question_scoped_text_references import scoped

    src, data = scoped("x3y z3w", [support], subject)
    got, _, requests = run(src, data)
    failure(got, "output", known=USAGE, complete=True)
    assert got.diagnostic_stage == "evidence_contract" and len(requests) == 1


@pytest.mark.parametrize("kind", ["support", "child"])
def test_saved_canonical_valid_but_scoped_ambiguous_rejects(kind):
    from issuedigest_agents.question_evidence_propositions import (
        build_question_evidence_propositions,
    )
    from test_question_evidence_propositions import ref
    from test_question_scoped_text_references import scoped

    src, data = scoped("x3y z3w", ["x3y"], "3")
    got, _, _ = run(src, data)
    raw = got.model_dump(mode="json")
    prop = raw["evidence"]["propositions"][0]
    prop["supporting_refs"] = [ref(src, "x3y z3w" if kind == "child" else "3")]
    # Positional canonical validation accepts these; text resolution must reject them.
    evidence = build_question_evidence_propositions(
        src,
        QUESTION,
        dict(propositions=raw["evidence"]["propositions"], coverage=raw["evidence"]["coverage"]),
    )
    raw["evidence"] = evidence.model_dump(mode="json")
    with pytest.raises(api().GuardedQuestionEvidenceV5Error) as rejected:
        api().validate_guarded_question_evidence_v5(src, QUESTION, raw)
    assert rejected.value.diagnostic_stage == "evidence_contract"
