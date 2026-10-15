import json
from pathlib import Path
from uuid import uuid4

import pytest
from issuedigest_agents.research import AIClaim, AIModule, AIOutput, build_canvas
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import SourcePresentation


def source():
    path = Path(__file__).resolve().parents[3] / "tests/fixtures/canvas-synthetic.json"
    data = json.loads(path.read_text())["research"]["evidence"][0]
    bundle = EvidenceBundle.model_validate(data)
    title = SourcePresentation(
        snapshot_id=uuid4(),
        workspace_id=bundle.document.workspace_id,
        title="합성 자료",
        profile="operator-verified-v1",
    )
    return title.snapshot_id, bundle, title


def test_canvas_rejects_unknown_citation_and_accepts_exact_one():
    selected = source()
    claim = AIClaim(
        text="문서의 의미를 해석한 주장", citation_ids=(selected[1].citations[0].citation_id,)
    )
    output = AIOutput(
        outcome="answer",
        message=None,
        modules=(AIModule(kind="summary", title="요약", claims=(claim,)),),
    )
    canvas = build_canvas(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.research.claims[0].basis == "inference"
    assert {module.kind for module in canvas.revision.draft.modules} == {"summary", "evidence"}
    wrong = output.model_copy(
        update={
            "modules": (
                AIModule(
                    kind="summary",
                    title="요약",
                    claims=(AIClaim(text="가짜", citation_ids=(uuid4(),)),),
                ),
            )
        }
    )
    with pytest.raises(ValueError):
        build_canvas(uuid4(), selected[1].document.workspace_id, (selected,), wrong)


def test_agent_usage_is_recorded_without_provider_call():
    from issuedigest_agents.research import create_agent, run_agent
    from pydantic_ai.models.test import TestModel

    claim = {"text": "합성 해석", "citation_ids": [str(uuid4())], "event_date": None}
    output = {
        "outcome": "answer",
        "message": None,
        "modules": [{"kind": "summary", "title": "요약", "claims": [claim]}],
    }
    proposal, input_tokens, output_tokens = run_agent(
        create_agent(TestModel(custom_output_args=output)), "합성 질문"
    )
    assert proposal.outcome == "answer"
    assert input_tokens >= 0 and output_tokens >= 0


def test_comparison_and_timeline_require_distinct_cited_facts():
    selected = source()
    citations = selected[1].citations
    comparison = AIOutput(
        outcome="answer",
        message=None,
        modules=(
            AIModule(
                kind="comparison",
                title="비교",
                claims=(
                    AIClaim(text="첫 해석", citation_ids=(citations[0].citation_id,)),
                    AIClaim(text="둘째 해석", citation_ids=(citations[1].citation_id,)),
                ),
            ),
        ),
    )
    canvas = build_canvas(uuid4(), selected[1].document.workspace_id, (selected,), comparison)
    assert {m.kind for m in canvas.revision.draft.modules} == {"comparison", "evidence"}
    from datetime import date

    dated = AIOutput(
        outcome="answer",
        message=None,
        modules=(
            AIModule(
                kind="timeline",
                title="시간",
                claims=(
                    AIClaim(
                        text="날짜를 추정할 수 없음",
                        citation_ids=(citations[0].citation_id,),
                        event_date=date(2026, 1, 2),
                    ),
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="Timeline date"):
        build_canvas(uuid4(), selected[1].document.workspace_id, (selected,), dated)


def test_timeline_uses_exact_date_in_canonical_quote():
    from datetime import date
    from hashlib import sha256

    snapshot, bundle, title = source()
    payload = bundle.model_dump(mode="json")
    text = "2026-01-02 접수된 합성 자료"
    payload["representation"].update(
        text=text, text_sha256=sha256(text.encode()).hexdigest(), pages=[], tables=[]
    )
    payload["citations"] = [payload["citations"][0]]
    payload["citations"][0]["selector"] = {
        "kind": "text",
        "start": 0,
        "end": len(text),
        "quote": text,
    }
    dated_bundle = EvidenceBundle.model_validate(payload)
    output = AIOutput(
        outcome="answer",
        message=None,
        modules=(
            AIModule(
                kind="timeline",
                title="연혁",
                claims=(
                    AIClaim(
                        text="접수 사실을 해석",
                        citation_ids=(dated_bundle.citations[0].citation_id,),
                        event_date=date(2026, 1, 2),
                    ),
                ),
            ),
        ),
    )
    canvas = build_canvas(
        uuid4(), dated_bundle.document.workspace_id, ((snapshot, dated_bundle, title),), output
    )
    assert canvas.research.claims[0].valid_period.start_date == date(2026, 1, 2)
