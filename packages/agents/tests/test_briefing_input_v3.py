"""Synthetic lossless v3 metadata projection and explicit outcome tool contracts."""

from hashlib import sha256

import pytest


def packet():
    return {
        "input_format": "question-briefing-source-v1",
        "question": "질문",
        "sources": [
            {
                "source_sha256": "a" * 64,
                "quotes": [{"citation_id": "c1", "text": "원문"}],
                "evidence": {
                    "source_sha256": "a" * 64,
                    "question_sha256": sha256("질문".encode()).hexdigest(),
                    "propositions": [],
                },
            }
        ],
    }


def test_v3_lossless_roundtrip_and_mismatched_hash_rejection():
    from issuedigest_agents.briefing_input_v3 import (
        decode_briefing_input_v3,
        encode_briefing_input_v3,
    )

    original = packet()
    encoded = encode_briefing_input_v3(original)
    assert encoded["input_format"] == "question-briefing-source-v3"
    assert "source_sha256" not in encoded["sources"][0]["evidence"]
    assert "question_sha256" not in encoded["sources"][0]["evidence"]
    assert decode_briefing_input_v3(encoded) == original
    for key in ("source_sha256", "question_sha256"):
        invalid = packet()
        invalid["sources"][0]["evidence"][key] = "b" * 64
        with pytest.raises(ValueError):
            encode_briefing_input_v3(invalid)


def test_v3_tool_union_has_no_answer_message_and_no_insufficient_modules():
    from issuedigest_agents.briefing_input_v3 import BriefingToolResultV3

    schema = BriefingToolResultV3.model_json_schema()
    assert "anyOf" in schema["properties"]["result"]
    branches = [
        schema["$defs"][branch["$ref"].split("/")[-1]]
        for branch in schema["properties"]["result"]["anyOf"]
    ]
    for branch in branches:
        assert branch["additionalProperties"] is False
        if branch["properties"]["outcome"]["const"] == "answer":
            assert "message" not in branch["properties"]
            assert branch["properties"]["modules"]["minItems"] == 1
        else:
            assert "modules" not in branch["properties"]
    got = BriefingToolResultV3.model_validate(
        {"result": {"outcome": "insufficient_evidence", "message": "한계"}}
    )
    assert got.canonical().model_dump(mode="json") == {
        "outcome": "insufficient_evidence",
        "message": "한계",
        "modules": [],
    }
    with pytest.raises(ValueError):
        BriefingToolResultV3.model_validate(
            {"result": {"outcome": "answer", "message": "보존해야 할 한계", "modules": []}}
        )
