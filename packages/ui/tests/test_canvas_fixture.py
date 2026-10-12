"""Synthetic shared JSON stays valid against the existing Python CanvasBundle contract."""

from pathlib import Path

from issuedigest_domain.canvas import CanvasBundle


def test_shared_synthetic_canvas_is_server_validated():
    fixture = Path(__file__).parents[3] / "tests/fixtures/canvas-synthetic.json"
    bundle = CanvasBundle.model_validate_json(fixture.read_text())
    assert [module.kind for module in bundle.revision.draft.modules] == [
        "evidence",
        "summary",
        "comparison",
        "timeline",
        "graph",
        "chart",
    ]
    assert all(proof.document.provider == "synthetic-test" for proof in bundle.research.evidence)
    assert len(bundle.revision.selected_version_ids) == 1
    assert len(bundle.research.evidence) == 2
