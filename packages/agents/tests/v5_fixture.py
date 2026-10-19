"""Generate the synthetic cross-language fixture through the real v5 canvas builder.

Run from the repository root: uv run python packages/agents/tests/v5_fixture.py
Only IDs/time are fixed; model output is manufactured, never a semantic evaluation.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch
from uuid import UUID

from issuedigest_agents.research_v5 import AIOutputV5, build_canvas_v5
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchResult, ResearchRun, presentation_for

ROOT = Path(__file__).parents[3]
FIXTURE = ROOT / "packages/api-client/tests/fixtures/research-run-v5-generated.json"


def build_fixture():
    value = json.loads(
        (ROOT / "packages/api-client/tests/fixtures/research-run-generated.json").read_text()
    )
    bundle = EvidenceBundle.model_validate(value["result"]["canvas"]["research"]["evidence"][0])
    snapshot = UUID(value["snapshot_ids"][0])
    presentation = presentation_for(bundle, snapshot).model_copy(update={"title": "합성 자료"})
    output = AIOutputV5.model_validate(
        {
            "outcome": "answer",
            "message": "화면에 표시하지 않는 보조 message",
            "modules": [
                {
                    "kind": "summary",
                    "title": "합성 요약",
                    "claims": [
                        {
                            "text": text,
                            "citation_ids": [bundle.citations[0].citation_id],
                            "category": category,
                            "rationale": "선택 인용에 대한 합성 AI 설명입니다.",
                        }
                        for category, text in [
                            ("documented", "합성 문서가 존재합니다."),
                            ("attributed", "합성 자료는 테스트 전용이라고 설명합니다."),
                            ("uncertain", "이 인용으로 실제 조사 결과는 확인하기 어렵습니다."),
                        ]
                    ],
                }
            ],
        }
    )
    ids = iter(UUID(int=i, version=4) for i in range(1000, 1100))
    fixed_time = datetime(2026, 10, 15, 0, 0, 0, 123456, tzinfo=UTC)
    with (
        patch("issuedigest_agents.research.uuid4", side_effect=lambda: next(ids)),
        patch("issuedigest_agents.research_v3.uuid4", side_effect=lambda: next(ids)),
        patch("issuedigest_agents.research.datetime") as clock,
    ):
        clock.now.return_value = fixed_time
        canvas = build_canvas_v5(
            UUID(value["run_id"]),
            bundle.document.workspace_id,
            ((snapshot, bundle, presentation),),
            output,
        )
    value["result"] = ResearchResult(
        canvas=canvas, source_titles={bundle.document.document_id: presentation.title}
    ).model_dump(mode="json")
    return ResearchRun.model_validate(value).model_dump(mode="json")


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(build_fixture(), ensure_ascii=False, indent=2) + "\n")
