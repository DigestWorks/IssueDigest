"""Frozen v2/v3/v4 bytes are a durable/provider compatibility contract, not model quality."""

import hashlib
import json
from uuid import UUID

import pytest
from issuedigest_agents import research, research_v3, research_v4
from issuedigest_domain import EvidenceBundle
from test_generation import source


def prompt_sources(repetitions=100):
    _, bundle, presentation = source()
    data = bundle.model_dump(mode="json")
    text = "기관의 2026년 목표와 실적 및 전망은 서로 다르다. " * repetitions
    data["representation"].update(
        text=text, text_sha256=hashlib.sha256(text.encode()).hexdigest(), pages=[], tables=[]
    )
    data["citations"] = [
        {
            "citation_id": str(UUID(int=index, version=4)),
            "document_version_id": str(bundle.version.version_id),
            "representation_id": str(bundle.representation.representation_id),
            "selector": {"kind": "text", "start": 0, "end": len(text), "quote": text},
        }
        for index in range(1, 8)
    ]
    selected = EvidenceBundle.model_validate(data)
    return ((UUID(int=100, version=4), selected, presentation),)


@pytest.mark.parametrize(
    "schema,instructions,static,limit,expected",
    [
        (
            research.AIOutput,
            research.SYSTEM_INSTRUCTIONS,
            research.STATIC_INPUT_BYTES,
            research.INPUT_PROMPT_BYTE_LIMIT,
            (
                "17bf6dcc254e93b26fed4db408496cbc9de32b883ccbc1612b8043f0be1e400c",
                "0dd0f588597b7155526086e0ee330330632ba524c041f31880e39c57e57948c8",
                2143,
                17309,
            ),
        ),
        (
            research_v3.AIOutputV3,
            research_v3.SYSTEM_INSTRUCTIONS_V3,
            research_v3.STATIC_INPUT_BYTES_V3,
            research_v3.INPUT_PROMPT_BYTE_LIMIT_V3,
            (
                "6813fe9041065c112446108c4a320c2d581a7c101829810da81b4cafb509d0be",
                "ba983870e35d5a59fb4d16b3f7977b9cae03e055649b9bbc724eaa7127f28e3d",
                3403,
                16049,
            ),
        ),
        (
            research_v4.AIOutputV4,
            research_v4.SYSTEM_INSTRUCTIONS_V4,
            research_v4.STATIC_INPUT_BYTES_V4,
            research_v4.INPUT_PROMPT_BYTE_LIMIT_V4,
            (
                "52c3f9bf34e1b2fa5f9f4e0d6374914145f1ac6ca96283fd3eb35b75e4609b50",
                "ba983870e35d5a59fb4d16b3f7977b9cae03e055649b9bbc724eaa7127f28e3d",
                4639,
                14813,
            ),
        ),
    ],
)
def test_historical_instruction_schema_and_budget_bytes(
    schema, instructions, static, limit, expected
):
    assert (
        hashlib.sha256(instructions.encode()).hexdigest(),
        hashlib.sha256(
            json.dumps(schema.model_json_schema(), ensure_ascii=False).encode()
        ).hexdigest(),
        static,
        limit,
    ) == expected


@pytest.mark.parametrize(
    "prompt_builder",
    [research.model_prompt, research_v3.model_prompt_v3, research_v4.model_prompt_v4],
)
def test_historical_prompt_bytes_match_baseline_7ff6f69(prompt_builder):
    prompt = prompt_builder(
        "목표와 실적 및 전망을 비교해 주세요.", prompt_sources(), "이전 해석 " * 400
    )
    assert len(prompt.encode()) == 10546
    assert hashlib.sha256(prompt.encode()).hexdigest() == (
        "c451a0b61fb3713d5ad58c650272ee375b39dbb7496d1c51427afa75429412e1"
    )


@pytest.mark.parametrize(
    "prompt_builder,length,digest",
    [
        (
            research.model_prompt,
            16256,
            "55b0d644978d7c215b3e5d7452b227377442f885043bd36b3df0523486b260f3",
        ),
        (
            research_v3.model_prompt_v3,
            14176,
            "84d9741908344b40cd879f63878567828a31350177f65f83effb6b4d4569c7f1",
        ),
    ],
)
def test_historical_prompt_boundary_selection_matches_baseline(prompt_builder, length, digest):
    # This corpus fits six quotes in v2 but only five in v3; their byte limits matter.
    prompt = prompt_builder(
        "목표와 실적 및 전망을 비교해 주세요.", prompt_sources(30), "이전 해석 " * 400
    )
    assert len(prompt.encode()) == length
    assert hashlib.sha256(prompt.encode()).hexdigest() == digest


def test_historical_v4_prompt_selection_matches_baseline_2ed2bc7():
    # Six quotes fit v3; v4's larger frozen instructions allow only five here.
    prompt = research_v4.model_prompt_v4(
        "목표와 실적 및 전망을 비교해 주세요.", prompt_sources(28), "이전 해석 " * 400
    )
    assert len(prompt.encode()) == 13506
    assert hashlib.sha256(prompt.encode()).hexdigest() == (
        "3d84c960bbc64ee1725560c2f9c20a1f579fa693b621853694b384b860080bb9"
    )


def test_historical_v5_schema_instructions_and_prompt_are_frozen():
    from issuedigest_agents import research_v5 as v5

    assert hashlib.sha256(v5.SYSTEM_INSTRUCTIONS_V5.encode()).hexdigest() == (
        "d6c638701a31af0ab0e4015eec4bb406174173af72cff546dff70ea02e42cd75"
    )
    assert hashlib.sha256(
        json.dumps(v5.AIOutputV5.model_json_schema(), ensure_ascii=False).encode()
    ).hexdigest() == ("ba983870e35d5a59fb4d16b3f7977b9cae03e055649b9bbc724eaa7127f28e3d")
    assert (v5.STATIC_INPUT_BYTES_V5, v5.INPUT_PROMPT_BYTE_LIMIT_V5) == (10012, 9440)
    for repetitions, size, digest in [
        (28, 7668, "05eb4cf8b8acbf75736cae5e7498037a8c87e3be66658055f8e7f3d72f71b1e2"),
        (30, 7936, "83a7a1913c4b5e90eebf003ea55d515b8f6de6d55aa3aecbb6bad2df51a13e82"),
    ]:
        prompt = v5.model_prompt_v5(
            "목표와 실적 및 전망을 비교해 주세요.", prompt_sources(repetitions), "이전 해석 " * 400
        )
        assert len(prompt.encode()) == size
        assert hashlib.sha256(prompt.encode()).hexdigest() == digest


def test_historical_v5_raw_and_normalized_provider_tools_are_frozen():
    from issuedigest_agents import research_v5 as v5
    from pydantic_ai.profiles.openai import OpenAIJsonSchemaTransformer
    from pydantic_ai.tools import GenerateToolJsonSchema

    raw, normalized = [], []
    ids = tuple(str(UUID(int=i, version=4)) for i in range(1, 101))
    for tool in v5._provider_tools_v5(ids):
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
    assert hashlib.sha256(json.dumps(raw, ensure_ascii=False).encode()).hexdigest() == (
        "28ccec2d760237d1a8854e646593619f0dc4d1c7615375273542b84f8f4383ac"
    )
    assert hashlib.sha256(json.dumps(normalized, ensure_ascii=False).encode()).hexdigest() == (
        "d591a6df9adf220815bacb4f20cd82ac87ebbe96b21dda4819279e2a98471a9e"
    )
