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


@pytest.mark.parametrize(
    "message", [None, "", " \t ", "합성 보조 설명과 인용 ID는 별도 문장입니다."]
)
def test_answer_projects_auxiliary_message_out_of_canonical_canvas(message):
    selected = source()
    claim = AIClaim(text="합성 근거의 해석", citation_ids=(selected[1].citations[0].citation_id,))
    module = AIModule(kind="summary", title="요약", claims=(claim,))
    output = AIOutput(outcome="answer", message=message, modules=(module,))
    canvas = build_canvas(uuid4(), selected[1].document.workspace_id, (selected,), output)
    assert canvas.revision.draft.outcome == "answer"
    assert canvas.revision.draft.message is None
    assert canvas.research.claims[0].text == claim.text
    assert canvas.research.claims[0].citation_ids == claim.citation_ids
    assert canvas.revision.draft.modules[0].kind == "summary"
    assert canvas.revision.draft.modules[0].citation_ids == claim.citation_ids
    with pytest.raises(ValueError, match="Answer needs modules"):
        build_canvas(
            uuid4(),
            selected[1].document.workspace_id,
            (selected,),
            output.model_copy(update={"modules": ()}),
        )


@pytest.mark.parametrize("outcome", ["insufficient_evidence", "clarification_needed"])
def test_nonanswer_still_requires_a_nonblank_message(outcome):
    selected = source()
    for message in (None, "", "  "):
        with pytest.raises(ValueError, match="Insufficient response needs a message"):
            build_canvas(
                uuid4(),
                selected[1].document.workspace_id,
                (selected,),
                AIOutput(outcome=outcome, message=message, modules=()),
            )
    canvas = build_canvas(
        uuid4(),
        selected[1].document.workspace_id,
        (selected,),
        AIOutput(outcome=outcome, message="인용할 자료가 부족합니다.", modules=()),
    )
    assert canvas.revision.draft.message == "인용할 자료가 부족합니다."


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


def test_provider_envelope_rejects_oversized_prompt_before_model_call():
    from issuedigest_agents.research import INPUT_PROMPT_BYTE_LIMIT, create_agent, run_agent
    from pydantic_ai.models.test import TestModel

    with pytest.raises(ValueError, match="provider input"):
        run_agent(create_agent(TestModel()), "x" * (INPUT_PROMPT_BYTE_LIMIT + 1))


def test_provider_request_is_single_shot_with_bounded_output():
    from types import SimpleNamespace
    from unittest.mock import Mock

    from issuedigest_agents.research import MAX_OUTPUT_TOKENS, MAX_RUN_TOKENS, run_agent

    result = SimpleNamespace(
        output="proposal", usage=SimpleNamespace(input_tokens=10, output_tokens=5)
    )
    agent = Mock()
    agent.run_sync.return_value = result
    assert run_agent(agent, "bounded") == ("proposal", 10, 5)
    options = agent.run_sync.call_args.kwargs
    assert options["usage_limits"].request_limit == 1
    assert options["usage_limits"].total_tokens_limit == MAX_RUN_TOKENS
    assert options["model_settings"]["max_tokens"] == MAX_OUTPUT_TOKENS


def test_prompt_bounds_many_short_citations_and_unicode_metadata():
    from issuedigest_agents.research import (
        INPUT_PROMPT_BYTE_LIMIT,
        MAX_CITATIONS_PER_SOURCE,
        MAX_CITATIONS_TOTAL,
        model_prompt,
    )

    snapshot, bundle, title = source()
    payload = bundle.model_dump(mode="json")
    first = payload["citations"][0]
    payload["citations"] = [{**first, "citation_id": str(uuid4())} for _ in range(9600)]
    large = EvidenceBundle.model_validate(payload)
    prompt = model_prompt("질문 😀", ((snapshot, large, title),))
    citations = json.loads(prompt)["sources"][0]["citations"]
    assert 1 <= len(citations) <= MAX_CITATIONS_PER_SOURCE
    assert len(citations) <= MAX_CITATIONS_TOTAL
    assert len(prompt.encode("utf-8")) <= INPUT_PROMPT_BYTE_LIMIT
    long_title = title.model_copy(update={"title": "한😀" * INPUT_PROMPT_BYTE_LIMIT})
    with pytest.raises(ValueError, match="provider input"):
        model_prompt("질문", ((snapshot, bundle, long_title),))


def test_prompt_preserves_thirteen_exact_historical_citations():
    from issuedigest_agents.research import model_prompt

    snapshot, bundle, title = source()
    payload = bundle.model_dump(mode="json")
    first = payload["citations"][0]
    payload["citations"] = [{**first, "citation_id": str(uuid4())} for _ in range(13)]
    selected = EvidenceBundle.model_validate(payload)
    prompt = json.loads(model_prompt("자료 비교", ((snapshot, selected, title),)))
    assert [item["quote"] for item in prompt["sources"][0]["citations"]] == [
        item.selector.quote for item in selected.citations
    ]


def test_prompt_marks_selected_seed_and_keeps_related_source_as_context():
    from issuedigest_agents.research import model_prompt

    selected = source()
    related = (uuid4(), selected[1], selected[2])
    prompt = json.loads(
        model_prompt(
            "선택 자료를 요약",
            (selected, related),
            selected_snapshot_ids=(selected[0],),
        )
    )
    assert prompt["selected_snapshot_ids"] == [str(selected[0])]
    assert [document["snapshot_id"] for document in prompt["sources"]] == [
        str(selected[0]),
        str(related[0]),
    ]
    assert json.loads(model_prompt("기본 선택", (selected,)))["selected_snapshot_ids"] == [
        str(selected[0])
    ]

    uncitable = selected[1].model_copy(update={"citations": ()})
    with pytest.raises(ValueError):
        model_prompt(
            "선택 자료를 요약",
            ((selected[0], uncitable, selected[2]), related),
            selected_snapshot_ids=(selected[0],),
        )


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
