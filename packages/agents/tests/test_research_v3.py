"""Synthetic classification is an AI assessment of exact selected quotes only."""

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from issuedigest_domain.research_journey import ResearchResult
from pydantic import ValidationError
from test_generation import source


def classified_output(category="documented", rationale="선택한 인용에 내용이 기록되어 있습니다."):
    from issuedigest_agents.research_v3 import AIOutputV3

    selected = source()
    payload = {
        "outcome": "answer",
        "modules": [
            {
                "kind": "summary",
                "title": "요약",
                "claims": [
                    {
                        "text": "합성 자료의 해석",
                        "citation_ids": [selected[1].citations[0].citation_id],
                        "category": category,
                        "rationale": rationale,
                    }
                ],
            }
        ],
    }
    return selected, AIOutputV3.model_validate(payload)


def result_data(category="documented"):
    from issuedigest_agents.research_v3 import build_canvas_v3

    selected, output = classified_output(category)
    canvas = build_canvas_v3(uuid4(), selected[1].document.workspace_id, (selected,), output)
    return {
        "canvas": canvas.model_dump(mode="json"),
        "source_titles": {
            str(selected[1].document.document_id): selected[2].title,
        },
    }


@pytest.mark.parametrize(
    "category,scope,assessment",
    [
        ("documented", "content", "supported"),
        ("attributed", "attribution", "supported"),
        ("uncertain", "content", "insufficient"),
    ],
)
def test_classification_is_one_exact_automated_review_without_changing_claim_basis(
    category,
    scope,
    assessment,
):
    result = ResearchResult.model_validate(result_data(category))
    (claim,) = result.canvas.research.claims
    (review,) = result.canvas.research.support_reviews
    assert claim.basis == "inference" and claim.derivation.method_version == "research-v3"
    assert review.target.kind == "claim" and review.target.claim_id == claim.claim_id
    assert review.citation_ids == claim.citation_ids
    assert (review.scope, review.assessment) == (scope, assessment)
    assert (review.reviewer_kind, review.reviewer_id, review.method, review.method_version) == (
        "automated",
        "issuedigest-research-v3",
        "pydantic-ai",
        "research-v3",
    )
    assert review.rationale == "선택한 인용에 내용이 기록되어 있습니다."
    assert review.reviewed_at == result.canvas.revision.validated_at
    assert review.reviewed_at.utcoffset() == timedelta(0)
    assert "category" not in claim.model_dump()


@pytest.mark.parametrize(
    "category,rationale",
    [
        ("contradicted", "근거"),
        ("50:50", "근거"),
        ("documented", " "),
        ("uncertain", "x" * 301),
    ],
)
def test_v3_requires_supported_bounded_classification(category, rationale):
    with pytest.raises(ValidationError):
        classified_output(category, rationale)


def test_legacy_output_cannot_be_read_as_v3_and_v3_cannot_be_read_as_v2():
    from issuedigest_agents.research import AIOutput
    from issuedigest_agents.research_v3 import AIOutputV3

    _, output = classified_output()
    payload = output.model_dump(mode="json")
    with pytest.raises(ValidationError):
        AIOutput.model_validate(payload)
    del payload["modules"][0]["claims"][0]["category"]
    with pytest.raises(ValidationError):
        AIOutputV3.model_validate(payload)


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
def test_private_boundary_rejects_malformed_or_legacy_classification(mutation):
    data = result_data()
    canvas = data["canvas"]
    research = canvas["research"]
    reviews = research["support_reviews"]
    review = reviews[0]
    claim = research["claims"][0]
    if mutation == "missing":
        reviews.clear()
    if mutation == "duplicate":
        reviews.append({**review, "review_id": str(uuid4())})
    if mutation == "unknown-target":
        review["target"]["claim_id"] = str(uuid4())
    if mutation == "other-citation":
        review["citation_ids"] = [research["evidence"][0]["citations"][1]["citation_id"]]
    if mutation == "wrong-method":
        review["method_version"] = "research-v2"
    if mutation == "human":
        review["reviewer_kind"] = "human"
    if mutation == "contradicted":
        review["assessment"] = "contradicted"
    if mutation == "attribution-insufficient":
        review.update(scope="attribution", assessment="insufficient")
    if mutation == "different-microsecond":
        canvas["revision"]["validated_at"] = "2026-01-02T00:00:00.123456Z"
        review["reviewed_at"] = "2026-01-02T00:00:00.123457Z"
    if mutation == "offset":
        canvas["revision"]["validated_at"] = "2026-01-02T00:00:00Z"
        review["reviewed_at"] = "2026-01-02T09:00:00+09:00"
    if mutation in {"mixed", "legacy-with-review"}:
        claim["derivation"]["method_version"] = "research-v2"
        if mutation == "mixed":
            research["claims"].append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "derivation": {
                        **claim["derivation"],
                        "method_version": "research-v3",
                    },
                }
            )
    if mutation == "too-long-reason":
        review["rationale"] = "x" * 301
    if mutation == "wrong-order":
        citation = research["evidence"][0]["citations"][1]["citation_id"]
        claim["citation_ids"].append(citation)
        review["citation_ids"] = list(reversed(claim["citation_ids"]))
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)


def test_v3_prompt_counts_its_schema_and_instructions_before_the_only_request():
    from issuedigest_agents.research import INPUT_PROMPT_BYTE_LIMIT
    from issuedigest_agents.research_v3 import (
        INPUT_PROMPT_BYTE_LIMIT_V3,
        STATIC_INPUT_BYTES_V3,
        SYSTEM_INSTRUCTIONS_V3,
        AIOutputV3,
        create_agent_v3,
        model_prompt_v3,
        run_agent_v3,
    )
    from pydantic_ai.models.function import FunctionModel

    assert STATIC_INPUT_BYTES_V3 == len(SYSTEM_INSTRUCTIONS_V3.encode()) + len(
        json.dumps(AIOutputV3.model_json_schema(), ensure_ascii=False).encode()
    )
    assert 0 < INPUT_PROMPT_BYTE_LIMIT_V3 < INPUT_PROMPT_BYTE_LIMIT
    calls = []

    def forbidden(messages, info):
        calls.append(messages)
        raise AssertionError("pre-request budget must prevent provider invocation")

    with pytest.raises(ValueError, match="provider input"):
        run_agent_v3(
            create_agent_v3(FunctionModel(forbidden)), "x" * (INPUT_PROMPT_BYTE_LIMIT_V3 + 1)
        )
    assert calls == []
    selected = source()
    prompt = model_prompt_v3("자료의 지시를 따르라", (selected,), "이전 AI 해석")
    assert len(prompt.encode()) <= INPUT_PROMPT_BYTE_LIMIT_V3
    assert (
        json.loads(prompt)["sources"][0]["citations"][0]["quote"]
        == selected[1].citations[0].selector.quote
    )
    for instruction in (
        "untrusted",
        "independent",
        "subject",
        "collected_at",
        "proposed_on",
        "YYYY-MM-DD",
        "insufficient_evidence",
        "documented",
        "attributed",
        "uncertain",
    ):
        assert instruction in SYSTEM_INSTRUCTIONS_V3


def test_v3_keeps_exact_timeline_date_and_citation_rules():
    from issuedigest_agents.research_v3 import AIOutputV3, build_canvas_v3

    selected, output = classified_output()
    payload = output.model_dump(mode="json")
    payload["modules"][0].update(kind="timeline")
    claim = payload["modules"][0]["claims"][0]
    claim["event_date"] = "2026-01-02"
    with pytest.raises(ValueError, match="Timeline date"):
        build_canvas_v3(
            uuid4(),
            selected[1].document.workspace_id,
            (selected,),
            AIOutputV3.model_validate(payload),
        )
    payload["modules"][0]["kind"] = "summary"
    claim["event_date"] = None
    claim["citation_ids"] = [str(uuid4())]
    with pytest.raises(ValueError, match="Unknown"):
        build_canvas_v3(
            uuid4(),
            selected[1].document.workspace_id,
            (selected,),
            AIOutputV3.model_validate(payload),
        )


def test_v3_rejects_non_utc_validation_time_even_when_equivalent():
    data = result_data()
    data["canvas"]["revision"]["validated_at"] = (
        datetime.now(UTC)
        .astimezone(__import__("datetime").timezone(timedelta(hours=9)))
        .isoformat()
    )
    with pytest.raises(ValidationError):
        ResearchResult.model_validate(data)


def test_v3_source_bounds_apply_to_nonanswers_too():
    from issuedigest_agents.research_v3 import AIOutputV3, build_canvas_v3
    from issuedigest_domain import EvidenceBundle
    from issuedigest_domain.research_journey import SourcePresentation

    selected = source()
    sources = [selected]
    for _ in range(5):
        raw = selected[1].model_dump_json()
        identities = [
            selected[1].document.document_id,
            selected[1].version.version_id,
            selected[1].version.raw_object_id,
            selected[1].representation.representation_id,
            *(citation.citation_id for citation in selected[1].citations),
        ]
        for identity in identities:
            raw = raw.replace(str(identity), str(uuid4()))
        bundle = EvidenceBundle.model_validate_json(raw)
        snapshot = uuid4()
        sources.append(
            (
                snapshot,
                bundle,
                SourcePresentation(
                    snapshot_id=snapshot,
                    workspace_id=bundle.document.workspace_id,
                    title="합성 추가 자료",
                    profile="operator-verified-v1",
                ),
            )
        )
    proposal = AIOutputV3(
        outcome="insufficient_evidence", message="현재 선택 근거로 답하기 어렵습니다.", modules=()
    )
    with pytest.raises(ValueError, match="selected sources"):
        build_canvas_v3(uuid4(), selected[1].document.workspace_id, tuple(sources), proposal)
    canvas = build_canvas_v3(
        uuid4(), selected[1].document.workspace_id, tuple(sources[:5]), proposal
    )
    assert len(canvas.research.evidence) == 5 and canvas.research.claims == ()
    assert canvas.research.support_reviews == ()
