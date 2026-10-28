"""V4 synthetic structural schema, source ordinal mapping and lossless metadata."""

import json
from copy import deepcopy
from uuid import uuid4

import pytest
from issuedigest_agents.briefing_input_v4 import (
    BriefingToolResultV4,
    decode_briefing_input_v4,
    encode_briefing_input_v4,
)
from test_briefing_input_v3 import packet


def answer():
    return {
        "result": {
            "outcome": "answer",
            "summary": {
                "title": "요약",
                "claims": [
                    {
                        "text": "근거의 한계를 보존한다",
                        "references": [{"source": 0, "proposition_id": "p1"}],
                    }
                ],
            },
            "details": [],
        }
    }


def test_v4_schema_encodes_summary_dates_and_comparison_constraints():
    schema = BriefingToolResultV4.model_json_schema()
    defs = schema["$defs"]
    assert "summary" in defs["Answer"]["required"]
    assert "kind" not in defs["Summary"]["properties"]
    assert "event_date" not in defs["Claim"]["properties"]
    assert defs["Claim"]["additionalProperties"] is False
    assert defs["DatedClaim"]["properties"]["event_date"]["type"] == "string"
    assert "event_date" in defs["DatedClaim"]["required"]
    assert defs["Compare"]["properties"]["claims"]["minItems"] == 2
    assert defs["Ref"]["properties"]["source"]["maximum"] == 4


def test_v4_canonical_preserves_fields_and_maps_server_source_identity():
    snapshot = uuid4()
    result = BriefingToolResultV4.model_validate_json(json.dumps(answer()))
    canonical = result.canonical(((snapshot,),))
    assert canonical.model_dump(mode="json") == {
        "outcome": "answer",
        "message": None,
        "modules": [
            {
                "kind": "summary",
                "title": "요약",
                "claims": [
                    {
                        "text": "근거의 한계를 보존한다",
                        "references": [{"snapshot_id": str(snapshot), "proposition_id": "p1"}],
                        "event_date": None,
                    }
                ],
            }
        ],
    }
    with pytest.raises(ValueError):
        result.canonical(())


@pytest.mark.parametrize("mutation", ["date", "summary", "message", "source", "kind"])
def test_v4_rejects_unsupported_or_missing_provider_fields(mutation):
    data = answer()
    claim = data["result"]["summary"]["claims"][0]
    if mutation == "date":
        claim["event_date"] = None
    elif mutation == "summary":
        del data["result"]["summary"]
    elif mutation == "message":
        data["result"]["message"] = "삭제 금지"
    elif mutation == "source":
        claim["references"][0]["source"] = 5
    else:
        data["result"]["summary"]["kind"] = "summary"
    with pytest.raises(ValueError):
        BriefingToolResultV4.model_validate_json(json.dumps(data))


def test_v4_lossless_shared_metadata_and_invalid_status_index():
    original = packet()
    original["sources"][0]["evidence"]["propositions"] = [{"epistemic_status": "source_statement"}]
    encoded = encode_briefing_input_v4(original)
    assert decode_briefing_input_v4(encoded) == original
    assert encoded["epistemic_statuses"] == ["source_statement"]
    bad = deepcopy(encoded)
    bad["sources"][0]["evidence"]["propositions"]["rows"][0][0] = True
    with pytest.raises(ValueError):
        decode_briefing_input_v4(bad)


def test_v4_actual_source_range_and_timeline_date_retention():
    import json

    data = answer()
    data["result"]["summary"]["claims"][0]["references"][0]["source"] = 4
    got = BriefingToolResultV4.model_validate_json(json.dumps(data))
    with pytest.raises(ValueError):
        got.canonical(((uuid4(),),))
    data = answer()
    claim = deepcopy(data["result"]["summary"]["claims"][0])
    claim["event_date"] = "2026-10-28"
    data["result"]["details"] = [{"kind": "timeline", "title": "시점", "claims": [claim]}]
    got = BriefingToolResultV4.model_validate_json(json.dumps(data))
    canonical = got.canonical(((uuid4(),),))
    assert str(canonical.modules[1].claims[0].event_date) == "2026-10-28"
    claim["event_date"] = None
    with pytest.raises(ValueError):
        BriefingToolResultV4.model_validate_json(json.dumps(data))


def test_v4_empty_source_propositions_roundtrip():
    original = packet()
    encoded = encode_briefing_input_v4(original)
    assert decode_briefing_input_v4(encoded) == original


@pytest.mark.parametrize("mutation", ["unused_status", "duplicate_status", "unused_columns"])
def test_v4_rejects_noncanonical_shared_metadata(mutation):
    original = packet()
    original["sources"][0]["evidence"]["propositions"] = [{"epistemic_status": "source_statement"}]
    encoded = encode_briefing_input_v4(original)
    if mutation == "unused_status":
        encoded["epistemic_statuses"].append("uncertain")
    elif mutation == "duplicate_status":
        encoded["epistemic_statuses"].append("source_statement")
        encoded["sources"][0]["evidence"]["propositions"]["rows"][0][0] = 1
    else:
        encoded = encode_briefing_input_v4(packet())
        encoded["proposition_columns"] = ["epistemic_status"]
    with pytest.raises(ValueError):
        decode_briefing_input_v4(encoded)
