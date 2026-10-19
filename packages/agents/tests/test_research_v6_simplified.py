"""Synthetic regressions for the pre-release v6 provider protocol simplification."""

import pytest
from model_loop import sync_model_loop as sync_model_loop
from pydantic import ValidationError
from pydantic_ai.exceptions import UnexpectedModelBehavior
from test_research_v6 import profile, proposal, run_synthetic


def test_core_requires_no_category_subject_or_date_and_always_uses_material_prefix(sync_model_loop):
    v6 = profile()
    selected, response = proposal()
    response["additional_summary_claims"] = [
        {**response["core_answer"], "assessment": "source_statement"},
        {**response["core_answer"], "assessment": "uncertain", "text": "자료 범위의 한계입니다."},
    ]
    prompt = v6.model_prompt_v6("합성 질문", (selected,))
    agent, calls = run_synthetic(prompt, response)
    result, _, _ = v6.run_agent_v6(agent, prompt)
    assert [(c.category, c.text, c.event_date) for c in result.modules[0].claims] == [
        ("attributed", "제공 자료에 따르면, 같은 방향입니다.", None),
        ("attributed", "제공 자료에 따르면, 같은 방향입니다.", None),
        ("uncertain", "자료 범위의 한계입니다.", None),
    ]
    assert calls == [True]


@pytest.mark.parametrize("location", ["core", "summary", "comparison"])
@pytest.mark.parametrize(
    "old_field,value",
    [
        ("category", "documented"),
        ("source_subject", "없는 합성 기관"),
        ("event_date", None),
        ("event_date", "2026-01-01"),
    ],
)
def test_non_timeline_rejects_old_fields_without_repair(location, old_field, value):
    v6 = profile()
    selected, response = proposal()
    if location == "core":
        target = response["core_answer"]
    else:
        target = {**response["core_answer"], "assessment": "source_statement"}
        if location == "summary":
            response["additional_summary_claims"] = [target]
        else:
            response["details"] = [
                {"kind": "comparison", "title": "합성 비교", "claims": [target, target.copy()]}
            ]
    target[old_field] = value
    tool = v6._provider_tools_v6((str(selected[1].citations[0].citation_id),))[0].output
    with pytest.raises(ValidationError) as error:
        tool.model_validate(response)
    assert "extra_forbidden" in str(error.value)


def test_old_documented_nonnull_subject_combination_is_not_repaired(sync_model_loop):
    selected, response = proposal()
    response["core_answer"].update(
        category="documented", source_subject="없는 합성 기관", event_date=None
    )
    prompt = profile().model_prompt_v6("합성 질문", (selected,))
    agent, calls = run_synthetic(prompt, response)
    with pytest.raises(UnexpectedModelBehavior):
        profile().run_agent_v6(agent, prompt)
    assert calls == [True]


@pytest.mark.parametrize("event_date", [None, "2026-01", "2026-01-01T00:00:00", 1767225600])
def test_timeline_requires_exact_date_without_coercion(event_date):
    v6 = profile()
    selected, response = proposal()
    response["details"] = [
        {
            "kind": "timeline",
            "title": "합성 날짜",
            "claims": [
                {
                    **response["core_answer"],
                    "assessment": "source_statement",
                    "event_date": event_date,
                }
            ],
        }
    ]
    with pytest.raises(ValidationError):
        v6._provider_tools_v6((str(selected[1].citations[0].citation_id),))[
            0
        ].output.model_validate(response)


@pytest.mark.parametrize("quoted_date,valid", [("2026-01-01", True), ("2026-01", False)])
def test_timeline_date_is_checked_against_original_quote(sync_model_loop, quoted_date, valid):
    import hashlib
    from uuid import uuid4

    from issuedigest_domain import EvidenceBundle

    v6 = profile()
    selected, response = proposal()
    data = selected[1].model_dump(mode="json")
    quote = "합성 기록 " + quoted_date
    data["representation"].update(
        text=quote, text_sha256=hashlib.sha256(quote.encode()).hexdigest(), pages=[], tables=[]
    )
    data["citations"] = [
        {
            **data["citations"][0],
            "selector": {"kind": "text", "start": 0, "end": len(quote), "quote": quote},
        }
    ]
    selected = (selected[0], EvidenceBundle.model_validate(data), selected[2])
    response["details"] = [
        {
            "kind": "timeline",
            "title": "합성 일정",
            "claims": [
                {
                    **response["core_answer"],
                    "assessment": "source_statement",
                    "event_date": "2026-01-01",
                }
            ],
        }
    ]
    prompt = v6.model_prompt_v6("합성 날짜", (selected,))
    agent, calls = run_synthetic(prompt, response)
    result, _, _ = v6.run_agent_v6(agent, prompt)
    if valid:
        canvas = v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), result)
        assert canvas.research.claims[1].valid_period.start_date.isoformat() == "2026-01-01"
        assert canvas.research.evidence[0].representation.text == quote
    else:
        with pytest.raises(ValueError, match="Timeline date absent"):
            v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), result)
    assert calls == [True]


@pytest.mark.parametrize("field", ["text", "rationale"])
@pytest.mark.parametrize("body", ["\u0085", "\ufeff", " \t\u0085\ufeff\u3000\n"])
def test_provider_rejects_union_whitespace_body_and_rationale(field, body):
    v6 = profile()
    selected, response = proposal()
    response["core_answer"][field] = body
    with pytest.raises(ValidationError):
        v6._provider_tools_v6((str(selected[1].citations[0].citation_id),))[
            0
        ].output.model_validate(response)


def test_raw_and_normalized_hundred_id_schemas_have_no_dependent_fields():
    from uuid import UUID

    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    for tool in profile()._provider_tools_v6(ids):
        raw = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
        normalized = OpenAIJsonSchemaTransformer(raw, strict=True).walk()
        for schema in (raw, normalized):
            if tool.name == "answer":
                definitions = schema["$defs"]
                assert definitions["ProviderCitationIdV6"]["enum"] == list(ids)
                for name in ("ProviderCoreAnswerV6", "ProviderClaimV6", "ProviderTimelineClaimV6"):
                    properties = definitions[name]["properties"]
                    assert "category" not in properties and "source_subject" not in properties
                    assert ("event_date" in properties) == (name == "ProviderTimelineClaimV6")
                    assert set(definitions[name]["required"]) == set(properties)
                    assert definitions[name]["additionalProperties"] is False
                assert (
                    definitions["ProviderTimelineClaimV6"]["properties"]["event_date"]["format"]
                    == "date"
                )
            assert schema["additionalProperties"] is False


def test_documented_canonical_v6_still_builds_supported_content_review():
    from uuid import uuid4

    from issuedigest_agents.research_v3 import AIOutputV3

    v6 = profile()
    selected, response = proposal()
    output = AIOutputV3.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "summary",
                    "title": "기존 canonical 기록",
                    "claims": [{**response["core_answer"], "category": "documented"}],
                }
            ],
        }
    )
    canvas = v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.research.claims[0].text == "같은 방향입니다."
    review = canvas.research.support_reviews[0]
    assert (review.scope, review.assessment, review.method_version) == (
        "content",
        "supported",
        "research-v6",
    )


def test_prerelease_v6_provider_budget_and_prompt_goldens():
    import hashlib
    import json
    from uuid import UUID

    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema
    from test_research_profile_compatibility import prompt_sources

    v6 = profile()
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    raw, normalized = [], []
    for tool in v6._provider_tools_v6(ids):
        schema = tool.output.model_json_schema(schema_generator=GenerateToolJsonSchema)
        envelope = dict(
            type="function",
            name=tool.name,
            description=tool.description,
            strict=True,
            parameters=schema,
        )
        raw.append(envelope)
        normalized.append(
            {**envelope, "parameters": OpenAIJsonSchemaTransformer(schema, strict=True).walk()}
        )
    assert [len(json.dumps(s, ensure_ascii=False).encode()) for s in (raw, normalized)] == [
        8092,
        7952,
    ]
    assert [
        hashlib.sha256(json.dumps(s, ensure_ascii=False).encode()).hexdigest()
        for s in (raw, normalized)
    ] == [
        "1c8fa45e1c415e4c395d08c9953703ff83e1ffd2d50ee51f1d566fa73237b700",
        "15adddacdb4e91553d9f34ec567f32d963f77ee9eede267d8d180cc80f42f6e6",
    ]
    assert (
        hashlib.sha256(v6.SYSTEM_INSTRUCTIONS_V6.encode()).hexdigest()
        == "b6ae1e1905a8fc0a9199012b1eff06eb70b5606871ebed5ed7d038c5d9334eae"
    )
    assert (v6.STATIC_INPUT_BYTES_V6, v6.INPUT_PROMPT_BYTE_LIMIT_V6) == (11101, 8351)
    for repetitions, size, digest in [
        (30, 7936, "83a7a1913c4b5e90eebf003ea55d515b8f6de6d55aa3aecbb6bad2df51a13e82"),
        (34, 6124, "f563aa455ab4eb3137888f35184ccdee79084c0d2ab21451bc602e8d072e276f"),
    ]:
        prompt = v6.model_prompt_v6(
            "목표와 실적 및 전망을 비교해 주세요.", prompt_sources(repetitions), "이전 해석 " * 400
        )
        assert len(prompt.encode()) == size
        assert hashlib.sha256(prompt.encode()).hexdigest() == digest


@pytest.mark.parametrize("subject_size,valid", [(80, True), (81, False)])
def test_preserved_canonical_subject_limit_and_astral_body(subject_size, valid):
    from v6_fixture import build_fixture

    subject, body = "😀" * subject_size, "🚀" * 400
    if valid:
        value = build_fixture(canonical_subject=subject, body=body, quote=subject)
        assert (
            value["result"]["canvas"]["research"]["claims"][0]["text"]
            == subject + "에 따르면, " + body
        )
    else:
        with pytest.raises((ValueError, ValidationError)):
            build_fixture(canonical_subject=subject, body=body, quote=subject)


@pytest.mark.parametrize(
    "subject,valid",
    [("발표했다", True), ("합성청", False), ("다른 합성부", False), ("발표했다 ", False)],
)
def test_existing_canonical_subject_must_match_every_selected_original_quote(subject, valid):
    import hashlib
    from uuid import uuid4

    from issuedigest_agents.research_v3 import AIOutputV3
    from issuedigest_domain import EvidenceBundle

    v6 = profile()
    selected, response = proposal()
    data = selected[1].model_dump(mode="json")
    first, second = "합성청은 발표했다", "다른 합성부는 발표했다"
    text = first + " / " + second
    data["representation"].update(
        text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(), pages=[], tables=[]
    )
    data["citations"] = [
        {
            **citation,
            "selector": {"kind": "text", "start": start, "end": start + len(quote), "quote": quote},
        }
        for citation, start, quote in [
            (data["citations"][0], 0, first),
            (data["citations"][1], len(first) + 3, second),
        ]
    ]
    selected = (selected[0], EvidenceBundle.model_validate(data), selected[2])
    output = AIOutputV3.model_validate(
        {
            "outcome": "answer",
            "modules": [
                {
                    "kind": "summary",
                    "title": "합성 요약",
                    "claims": [
                        {
                            **response["core_answer"],
                            "citation_ids": [str(c.citation_id) for c in selected[1].citations],
                            "category": "attributed",
                            "text": subject + "에 따르면, 합성 해석입니다.",
                        }
                    ],
                }
            ],
        }
    )
    if valid:
        canvas = v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), output)
        assert canvas.research.claims[0].text == "발표했다에 따르면, 합성 해석입니다."
    else:
        with pytest.raises(ValueError):
            v6.build_canvas_v6(uuid4(), selected[1].document.workspace_id, (selected,), output)
