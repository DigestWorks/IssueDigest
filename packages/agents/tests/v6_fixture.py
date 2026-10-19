"""Synthetic v6 provider DTO through actual conversion and builder, for Python/JS/UI."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from issuedigest_agents.research_v6 import (
    _canonical_output_v6,
    _provider_tools_v6,
    build_canvas_v6,
    model_prompt_v6,
)
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchResult, ResearchRun, presentation_for

ROOT = Path(__file__).parents[3]
FIXTURE = ROOT / "packages/api-client/tests/fixtures/research-run-v6-generated.json"
ASTRAL_FIXTURE = ROOT / "packages/api-client/tests/fixtures/research-run-v6-astral-generated.json"


def build_fixture(
    *,
    canonical_subject=None,
    body="두 합성 지표는 같은 방향입니다.",
    quote=None,
    summary_title="합성 비교 결론",
):
    value = json.loads(
        (ROOT / "packages/api-client/tests/fixtures/research-run-generated.json").read_text()
    )
    bundle = EvidenceBundle.model_validate(value["result"]["canvas"]["research"]["evidence"][0])
    if quote is not None:
        data = bundle.model_dump(mode="json")
        data["representation"].update(
            text=quote, text_sha256=hashlib.sha256(quote.encode()).hexdigest(), pages=[], tables=[]
        )
        data["citations"] = [
            {
                **data["citations"][0],
                "selector": {"kind": "text", "start": 0, "end": len(quote), "quote": quote},
            }
        ]
        bundle = EvidenceBundle.model_validate(data)
    snapshot = UUID(value["snapshot_ids"][0])
    presentation = presentation_for(bundle, snapshot).model_copy(update={"title": "합성 자료"})
    sources = ((snapshot, bundle, presentation),)
    prompt = model_prompt_v6("두 합성 지표는 같은 방향인가요?", sources)
    claim = dict(
        text=body,
        rationale="선택 인용에 대한 합성 AI 설명입니다.",
        citation_ids=[str(bundle.citations[0].citation_id)],
    )
    limit = {
        **claim,
        "assessment": "uncertain",
        "text": "이 인용으로 전국 인지도는 확인하기 어렵습니다.",
    }
    recorded = {
        **claim,
        "assessment": "source_statement",
        "text": "합성 문서에 기록되어 있습니다.",
    }
    tools = _provider_tools_v6((str(bundle.citations[0].citation_id),))
    output = _canonical_output_v6(
        tools[0].output.model_validate(
            {
                "outcome": "answer",
                "summary_title": summary_title,
                "core_answer": claim,
                "additional_summary_claims": [limit],
                "details": [
                    {
                        "kind": "comparison",
                        "title": "합성 비교 상세",
                        "claims": [recorded, {**claim, "assessment": "source_statement"}],
                    }
                ],
            }
        ),
        prompt,
    )
    # Explicitly exercise the preserved canonical custom-subject boundary separately
    # from the new provider policy. Generated shared fixtures never use this override.
    if canonical_subject is not None:
        output.modules[0].claims[0].text = canonical_subject + "에 따르면, " + body
    ids = iter(UUID(int=i, version=4) for i in range(1000, 1100))
    fixed_time = datetime(2026, 10, 15, 0, 0, 0, 123456, tzinfo=UTC)
    with (
        patch("issuedigest_agents.research.uuid4", side_effect=lambda: next(ids)),
        patch("issuedigest_agents.research_v3.uuid4", side_effect=lambda: next(ids)),
        patch("issuedigest_agents.research.datetime") as clock,
    ):
        clock.now.return_value = fixed_time
        canvas = build_canvas_v6(
            UUID(value["run_id"]), bundle.document.workspace_id, sources, output
        )
    value["question"] = "두 합성 지표는 같은 방향인가요?"
    value["result"] = ResearchResult(
        canvas=canvas, source_titles={bundle.document.document_id: presentation.title}
    ).model_dump(mode="json")
    return ResearchRun.model_validate(value).model_dump(mode="json")


def build_astral_fixture():
    return build_fixture(body="🚀" * 400, quote="😀" * 80, summary_title="🌏" * 100)


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(build_fixture(), ensure_ascii=False, indent=2) + "\n")
    ASTRAL_FIXTURE.write_text(
        json.dumps(build_astral_fixture(), ensure_ascii=False, indent=2) + "\n"
    )
