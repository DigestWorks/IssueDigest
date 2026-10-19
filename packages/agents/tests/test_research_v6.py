"""Synthetic v6 provider→canonical contract; never a semantic model evaluation."""

import copy
import importlib
import json
from uuid import UUID, uuid4

import pytest
from issuedigest_domain.research_journey import ResearchResult
from model_loop import sync_model_loop as sync_model_loop
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from test_generation import source


def profile():
    return importlib.import_module("issuedigest_agents.research_v6")


def proposal():
    selected = source()
    return selected, {
        "outcome": "answer",
        "summary_title": "합성 비교 결론",
        "core_answer": {
            "text": "같은 방향입니다.",
            "citation_ids": [str(selected[1].citations[0].citation_id)],
            "rationale": "선택 인용의 합성 설명",
        },
        "additional_summary_claims": [],
        "details": [],
    }


def run_synthetic(prompt, response, inspect=None):
    calls = []

    def respond(messages, info):
        calls.append(True)
        if inspect:
            inspect(info)
        tool = next(t for t in info.output_tools if t.name == response["outcome"])
        return ModelResponse(parts=[ToolCallPart(tool.name, response)])

    agent = profile().create_agent_v6(FunctionModel(respond))
    return agent, calls


def test_core_answer_becomes_first_summary_with_exact_v6_attribution(sync_model_loop):
    v6 = profile()
    selected, response = proposal()
    response["additional_summary_claims"] = [
        {
            **response["core_answer"],
            "assessment": "uncertain",
            "text": "이 인용으로 전국 인지도는 확인하기 어렵습니다.",
        }
    ]
    response["details"] = [
        {
            "kind": "comparison",
            "title": "접힌 상세",
            "claims": [
                {**response["core_answer"], "assessment": "source_statement"},
                response["additional_summary_claims"][0],
            ],
        }
    ]
    prompt = v6.model_prompt_v6("방향을 비교해 주세요", (selected,))
    agent, calls = run_synthetic(prompt, response)
    output, _, _ = v6.run_agent_v6(agent, prompt)
    from issuedigest_agents.research_v3 import AIOutputV3

    assert v6.AIOutputV6 is AIOutputV3 and type(output) is AIOutputV3
    assert output.message is None
    assert output.modules[0].claims[0].text == "제공 자료에 따르면, 같은 방향입니다."
    assert "source_subject" not in output.model_dump_json()
    canvas = v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert [m.kind for m in canvas.revision.draft.modules] == ["summary", "comparison", "evidence"]
    review = canvas.research.support_reviews[0]
    assert (review.reviewer_id, review.method_version, review.scope, review.assessment) == (
        "issuedigest-research-v6",
        "research-v6",
        "attribution",
        "supported",
    )
    assert ResearchResult(canvas=canvas, source_titles={selected[1].document.document_id: "합성"})
    assert calls == [True]


@pytest.mark.parametrize(
    "mutation",
    [
        "uncertain-core",
        "other-subject",
        "documented-subject",
        "message",
        "summary-detail",
        "long-text",
        "unknown-id",
        "uppercase-id",
    ],
)
def test_provider_rejects_old_fields_and_unsupported_core_without_retry(sync_model_loop, mutation):
    v6 = profile()
    selected, response = proposal()
    core = response["core_answer"]
    match mutation:
        case "uncertain-core":
            core["assessment"] = "uncertain"
        case "other-subject":
            core["source_subject"] = "없는 합성 기관"
        case "documented-subject":
            core["category"] = "documented"
        case "message":
            response["message"] = "숨겨진 결론"
        case "summary-detail":
            response["details"] = [
                {"kind": "summary", "title": "잘못된 상세", "claims": [core.copy()]}
            ]
        case "long-text":
            core["text"] = "가" * 401
        case "unknown-id":
            core["citation_ids"] = [str(uuid4())]
        case "uppercase-id":
            core["citation_ids"] = ["ABCDEFAB-CDEF-4ABC-8DEF-ABCDEFABCDEF"]
    prompt = v6.model_prompt_v6("합성 질문", (selected,))
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises((UnexpectedModelBehavior, ValueError)):
        v6.run_agent_v6(agent, prompt)
    assert calls == [True]


@pytest.mark.parametrize("outcome", ["insufficient_evidence", "clarification_needed"])
def test_nonanswer_has_empty_modules_and_nonblank_scope_message(sync_model_loop, outcome):
    v6 = profile()
    selected = source()
    prompt = v6.model_prompt_v6("전국 찬성률은?", (selected,))
    agent, calls = run_synthetic(
        prompt,
        {
            "outcome": outcome,
            "modules": [],
            "message": "제공 자료로 핵심 질문에 답할 근거가 부족합니다.",
        },
    )
    output, _, _ = v6.run_agent_v6(agent, prompt)
    canvas = v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.revision.draft.outcome == outcome
    assert canvas.research.claims == canvas.research.support_reviews == ()
    assert calls == [True]


def test_worst_case_budget_reserves_every_raw_and_normalized_tool():
    v6 = profile()
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    sizes = v6._provider_schema_bytes_v6(v6._provider_tools_v6(ids))
    assert v6.STATIC_INPUT_BYTES_V6 == len(v6.SYSTEM_INSTRUCTIONS_V6.encode()) + max(sizes)
    assert v6.INPUT_PROMPT_BYTE_LIMIT_V6 == 24000 - 2500 - 2048 - v6.STATIC_INPUT_BYTES_V6 > 0
    for count in (1, 2, 32, 99):
        assert max(v6._provider_schema_bytes_v6(v6._provider_tools_v6(ids[:count]))) <= max(sizes)


@pytest.mark.parametrize(
    "mutation", ["question-id", "duplicate", "bad-uuid", "oversize", "bad-json"]
)
def test_invalid_prompt_and_injected_question_ids_never_expand_allowlist(sync_model_loop, mutation):
    v6 = profile()
    selected, response = proposal()
    outside = str(uuid4())
    payload = json.loads(v6.model_prompt_v6(outside, (selected,), outside))
    if mutation == "question-id":
        response["core_answer"]["citation_ids"] = [outside]
    if mutation == "duplicate":
        payload["sources"][0]["citations"].append(
            copy.deepcopy(payload["sources"][0]["citations"][0])
        )
    if mutation == "bad-uuid":
        payload["sources"][0]["citations"][0]["citation_id"] = str(UUID(int=1))
    prompt = json.dumps(payload)
    if mutation == "oversize":
        prompt = "가" * 24000
    if mutation == "bad-json":
        prompt = "{"
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises((ValueError, UnexpectedModelBehavior)):
        v6.run_agent_v6(agent, prompt)
    assert calls == ([True] if mutation == "question-id" else [])


def test_canonical_v6_rejects_all_uncertain_or_non_summary_core():
    v6 = profile()
    selected, response = proposal()
    from issuedigest_agents.research_v3 import AIOutputV3

    for kind, category in [("summary", "uncertain"), ("comparison", "documented")]:
        output = AIOutputV3.model_validate(
            {
                "outcome": "answer",
                "modules": [
                    {
                        "kind": kind,
                        "title": "합성",
                        "claims": [
                            {
                                **{
                                    k: v
                                    for k, v in response["core_answer"].items()
                                    if k != "source_subject"
                                },
                                "category": category,
                                "event_date": None,
                            }
                        ]
                        * (2 if kind == "comparison" else 1),
                    }
                ],
            }
        )
        with pytest.raises((ValueError, ValidationError)):
            v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), output)


def test_hundred_prompt_ids_fit_and_shared_schema_does_not_duplicate_enums(sync_model_loop):
    v6 = profile()
    selected, response = proposal()
    payload = json.loads(v6.model_prompt_v6("합성", (selected,)))
    ids = [str(UUID(int=i, version=4)) for i in range(1, 101)]
    payload["sources"] = [
        {
            **payload["sources"][0],
            "title": "합성",
            "citations": [{"citation_id": cid, "quote": "합성"} for cid in ids[start : start + 25]],
        }
        for start in range(0, 100, 25)
    ]
    prompt = json.dumps(payload, ensure_ascii=False)
    response["core_answer"]["citation_ids"] = [ids[-1]]

    def inspect(info):
        schema = json.dumps(info.output_tools[0].parameters_json_schema)
        assert schema.count(ids[-1]) == 1
        assert info.instructions == v6.SYSTEM_INSTRUCTIONS_V6
        assert info.model_settings == {"openai_store": False, "max_tokens": 2500, "timeout": 60}
        assert info.function_tools == []

    agent, calls = run_synthetic(prompt, response, inspect)
    output, _, _ = v6.run_agent_v6(agent, prompt)
    assert output.modules[0].claims[0].citation_ids == (UUID(ids[-1]),)
    assert calls == [True]


def test_actual_v6_builder_matches_shared_web_fixture():
    from v6_fixture import FIXTURE, build_fixture

    assert build_fixture() == json.loads(FIXTURE.read_text())


@pytest.mark.parametrize("text_size,valid", [(400, True), (401, False)])
def test_provider_body_and_original_canonical_character_limits(sync_model_loop, text_size, valid):
    v6 = profile()
    selected, response = proposal()
    response["core_answer"]["text"] = "나" * text_size
    prompt = v6.model_prompt_v6("합성 질문", (selected,))
    agent, calls = run_synthetic(prompt, response)
    if valid:
        output, _, _ = v6.run_agent_v6(agent, prompt)
        assert output.modules[0].claims[0].text == "제공 자료에 따르면, " + "나" * 400
        raw = output.model_dump()
        raw["modules"][0]["claims"][0]["text"] = "가" * 500
        assert len(v6.AIOutputV6.model_validate(raw).modules[0].claims[0].text) == 500
        raw["modules"][0]["claims"][0]["text"] += "가"
        with pytest.raises(ValidationError):
            v6.AIOutputV6.model_validate(raw)
    else:
        with pytest.raises(UnexpectedModelBehavior):
            v6.run_agent_v6(agent, prompt)
    assert calls == [True]


def test_actual_tool_budget_is_rechecked_before_request(monkeypatch):
    from pydantic_ai import ToolOutput

    v6 = profile()
    selected, response = proposal()
    prompt = v6.model_prompt_v6("합성", (selected,))
    original = v6._provider_tools_v6
    monkeypatch.setattr(
        v6,
        "_provider_tools_v6",
        lambda ids: [
            ToolOutput(t.output, name=t.name, description="x" * 24000, strict=True)
            for t in original(ids)
        ],
    )
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises(ValueError, match="provider input"):
        v6.run_agent_v6(agent, prompt)
    assert calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        "missing",
        "duplicate",
        "unknown-target",
        "other-citation",
        "wrong-method",
        "human",
        "contradicted",
        "attribution-insufficient",
        "different-microsecond",
        "offset",
        "mixed",
        "legacy-with-review",
        "too-long-reason",
        "wrong-order",
    ],
)
def test_v6_private_metadata_rejects_historical_and_malformed_results(mutation):
    from test_research_v4 import mutate_result
    from v6_fixture import build_fixture

    data = build_fixture()["result"]
    mutate_result(data, mutation)
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)


@pytest.mark.parametrize("version", ["v2", "v3", "v4", "v5"])
@pytest.mark.parametrize("field", ["claim", "review", "reviewer"])
def test_v6_rejects_mixed_version_identity(version, field):
    from v6_fixture import build_fixture

    data = build_fixture()["result"]
    research = data["canvas"]["research"]
    if field == "claim":
        research["claims"][0]["derivation"]["method_version"] = f"research-{version}"
    elif field == "review":
        research["support_reviews"][0]["method_version"] = f"research-{version}"
    else:
        research["support_reviews"][0]["reviewer_id"] = f"issuedigest-research-{version}"
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)


def test_request_local_types_do_not_keep_prior_citation_allowlist():
    import gc
    import weakref

    v6 = profile()
    first_id, next_id = str(uuid4()), str(uuid4())
    first = v6._provider_tools_v6((first_id,))
    reference = weakref.ref(first[0].output)
    next_tools = v6._provider_tools_v6((next_id,))
    assert first_id not in json.dumps(next_tools[0].output.model_json_schema())
    del first
    gc.collect()
    assert reference() is None


def test_normalized_provider_schemas_match_actual_preflight_bytes(sync_model_loop):
    from pydantic_ai.profiles.openai import openai_model_profile

    v6 = profile()
    selected, response = proposal()
    prompt = v6.model_prompt_v6("합성 질문", (selected,))
    ids = tuple(c["citation_id"] for s in json.loads(prompt)["sources"] for c in s["citations"])
    expected = v6._provider_schema_bytes_v6(v6._provider_tools_v6(ids))
    calls = []

    def respond(messages, info):
        calls.append(True)
        schemas = [
            dict(
                type="function",
                name=t.name,
                description=t.description,
                strict=t.strict,
                parameters=t.parameters_json_schema,
            )
            for t in info.output_tools
        ]
        actual_bytes = len(json.dumps(schemas, ensure_ascii=False).encode())
        assert actual_bytes == expected[1]
        assert (
            len(prompt.encode())
            + len(v6.SYSTEM_INSTRUCTIONS_V6.encode())
            + actual_bytes
            + 2048
            + 2500
            <= 24000
        )
        assert all(t.strict is True for t in info.output_tools)
        answer = info.output_tools[0].parameters_json_schema
        assert set(answer["required"]) == {
            "outcome",
            "summary_title",
            "core_answer",
            "additional_summary_claims",
            "details",
        }
        assert "default" not in json.dumps(answer)
        assert answer["$defs"]["ProviderCitationIdV6"]["enum"] == list(ids)
        assert set(answer["$defs"]["ProviderCoreAnswerV6"]["properties"]) == {
            "text",
            "rationale",
            "citation_ids",
        }
        assert answer["$defs"]["ProviderClaimV6"]["properties"]["assessment"]["enum"] == [
            "source_statement",
            "uncertain",
        ]
        return ModelResponse(parts=[ToolCallPart("answer", response)])

    agent = v6.create_agent_v6(FunctionModel(respond, profile=openai_model_profile("gpt-5.4-mini")))
    actual, _, _ = v6.run_agent_v6(agent, prompt)
    assert actual.modules[0].claims[0].text == "제공 자료에 따르면, 같은 방향입니다."
    assert calls == [True]


@pytest.mark.parametrize(
    "mutation",
    [
        "no-core",
        "four-additional",
        "three-details",
        "no-detail-claims",
        "five-detail-claims",
        "no-citations",
        "four-citations",
        "nonanswer-modules",
        "nonanswer-blank",
    ],
)
def test_provider_rejects_v6_shape_overflows_without_retry(sync_model_loop, mutation):
    v6 = profile()
    selected, response = proposal()
    core = {**response["core_answer"], "assessment": "source_statement"}
    match mutation:
        case "no-core":
            response.pop("core_answer")
        case "four-additional":
            response["additional_summary_claims"] = [core.copy()] * 4
        case "three-details":
            response["details"] = [
                {"kind": "comparison", "title": "합성", "claims": [core.copy()] * 2}
            ] * 3
        case "no-detail-claims":
            response["details"] = [{"kind": "comparison", "title": "합성", "claims": []}]
        case "five-detail-claims":
            response["details"] = [
                {"kind": "comparison", "title": "합성", "claims": [core.copy()] * 5}
            ]
        case "no-citations":
            response["core_answer"]["citation_ids"] = []
        case "four-citations":
            response["core_answer"]["citation_ids"] *= 4
        case "nonanswer-modules":
            response = {
                "outcome": "insufficient_evidence",
                "message": "제공 자료의 한계",
                "modules": ["허용되지 않은 문장"],
            }
        case "nonanswer-blank":
            response = {"outcome": "insufficient_evidence", "message": "  ", "modules": []}
    prompt = v6.model_prompt_v6("합성 질문", (selected,))
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises(UnexpectedModelBehavior):
        v6.run_agent_v6(agent, prompt)
    assert calls == [True]


def test_existing_canonical_subject_can_contain_attribution_separator():
    from v6_fixture import build_fixture

    data = build_fixture(
        canonical_subject="합성에 따르면, 별칭", quote="합성에 따르면, 별칭", body="가" * 400
    )
    assert (
        data["result"]["canvas"]["research"]["claims"][0]["text"]
        == "합성에 따르면, 별칭에 따르면, " + "가" * 400
    )


@pytest.mark.parametrize(
    "body", ["     ", "\t\n", "\u3000", "\u0085", "\ufeff", " \t\u0085\ufeff\u3000\n"]
)
def test_provider_rejects_blank_attributed_body_before_prefix_without_retry(sync_model_loop, body):
    v6 = profile()
    selected, response = proposal()
    response["core_answer"]["text"] = body
    prompt = v6.model_prompt_v6("합성", (selected,))
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises(UnexpectedModelBehavior):
        v6.run_agent_v6(agent, prompt)
    assert calls == [True]


@pytest.mark.parametrize(
    "body", ["     ", "\t\n", "\u3000", "\u0085", "\ufeff", " \t\u0085\ufeff\u3000\n"]
)
def test_final_canonical_v6_rejects_blank_attribution_suffix(body):
    from v6_fixture import build_fixture

    data = build_fixture()["result"]
    data["canvas"]["research"]["claims"][0]["text"] = "제공 자료에 따르면, " + body
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)


def test_actual_python_astral_400_body_matches_full_client_fixture():
    from v6_fixture import ASTRAL_FIXTURE, build_astral_fixture

    data = build_astral_fixture()
    assert data == json.loads(ASTRAL_FIXTURE.read_text())
    assert (
        data["result"]["canvas"]["research"]["claims"][0]["text"]
        == "제공 자료에 따르면, " + "🚀" * 400
    )


def test_provider_body_validation_preserves_valid_whitespace(sync_model_loop):
    v6 = profile()
    selected, response = proposal()
    response["core_answer"]["text"] = " \t합성 본문 😀 \n "
    prompt = v6.model_prompt_v6("합성", (selected,))
    agent, _ = run_synthetic(prompt, response)
    output, _, _ = v6.run_agent_v6(agent, prompt)
    assert output.modules[0].claims[0].text == "제공 자료에 따르면,  \t합성 본문 😀 \n "


@pytest.mark.parametrize("subject", ["\u0085", "\ufeff", " \t\u0085\ufeff\u3000\n"])
def test_final_canonical_v6_rejects_union_whitespace_subject(subject):
    from v6_fixture import build_fixture

    data = build_fixture(quote=subject + "합성")["result"]
    data["canvas"]["research"]["claims"][0]["text"] = subject + "에 따르면, 합성 본문"
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)


def test_existing_canonical_builder_preserves_union_whitespace_around_real_text():
    from v6_fixture import build_fixture

    subject = "\u0085\ufeff \t합성 주체\u3000\x1c"
    body = "\ufeff\u0085 합성 본문 😀 \x1f"
    data = build_fixture(canonical_subject=subject, body=body, quote=subject + " 합성 원문")
    assert (
        data["result"]["canvas"]["research"]["claims"][0]["text"] == subject + "에 따르면, " + body
    )


@pytest.mark.parametrize("category", ["documented", "uncertain"])
@pytest.mark.parametrize("body", ["\u0085", "\ufeff", " \t\u0085\ufeff\u3000\n"])
def test_final_canonical_v6_rejects_union_whitespace_unprefixed_body(category, body):
    from v6_fixture import build_fixture

    data = build_fixture()["result"]
    index = 1 if category == "uncertain" else 0
    research = data["canvas"]["research"]
    research["claims"][index]["text"] = body
    research["support_reviews"][index].update(
        scope="content", assessment="insufficient" if category == "uncertain" else "supported"
    )
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)
