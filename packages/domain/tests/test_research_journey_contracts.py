import json
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from issuedigest_domain import EvidenceBundle
from issuedigest_domain.research_journey import ResearchRequest, presentation_for
from pydantic import ValidationError


def test_request_accepts_question_only_and_rejects_blank_or_injected_fields() -> None:
    assert ResearchRequest(request_id=uuid4(), question="질문").parent_run_id is None
    with pytest.raises(ValidationError):
        ResearchRequest(request_id=uuid4(), question=" ")
    for field in ("snapshot_ids", "workspace_id", "sources"):
        with pytest.raises(ValidationError):
            ResearchRequest.model_validate(
                {"request_id": uuid4(), "question": "질문", field: [uuid4()]}
            )


def test_verified_bill_profile_yields_name_number_and_date() -> None:
    fixture = Path(__file__).resolve().parents[3] / "tests/fixtures/canvas-synthetic.json"
    payload = json.loads(fixture.read_text())["research"]["evidence"][0]
    text = "정보공개법 일부개정법률안\n기본 정보\n대수: 22대\n의안번호: 2200001\n제안일: 2026-01-02"
    payload["document"]["source_kind"] = "bill"
    payload["document"]["source_id"] = "private"
    payload["representation"].update(
        normalization_profile="legacy-bill-metadata-v1",
        text=text,
        text_sha256=sha256(text.encode()).hexdigest(),
        pages=[],
        tables=[],
    )
    payload["citations"] = []
    bundle = EvidenceBundle.model_validate(payload)
    presentation = presentation_for(bundle, uuid4())
    assert (presentation.title, presentation.bill_number, str(presentation.proposed_on)) == (
        "정보공개법 일부개정법률안",
        "2200001",
        "2026-01-02",
    )
    payload["representation"]["normalization_profile"] = "identity"
    assert presentation_for(EvidenceBundle.model_validate(payload), uuid4()).title == "법안 자료"


def test_presentation_rejects_uuid_or_blank_title() -> None:
    from issuedigest_domain.research_journey import SourcePresentation

    for title in (str(uuid4()), "   "):
        with pytest.raises(ValidationError):
            SourcePresentation(
                snapshot_id=uuid4(),
                workspace_id=uuid4(),
                title=title,
                profile="operator-verified-v1",
            )


def test_run_provenance_bounds_and_completed_result_integrity() -> None:
    from issuedigest_domain.research_journey import ResearchRun

    fixture = (
        Path(__file__).resolve().parents[3]
        / "packages/api-client/tests/fixtures/research-run-generated.json"
    )
    data = json.loads(fixture.read_text())
    assert ResearchRun.model_validate(data).status == "completed"
    for snapshots in ([], [str(uuid4()) for _ in range(6)], [data["snapshot_ids"][0]] * 2):
        with pytest.raises(ValidationError):
            ResearchRun.model_validate({**data, "snapshot_ids": snapshots})
    with pytest.raises(ValidationError):
        ResearchRun.model_validate({**data, "result": None})
    assert (
        ResearchRun.model_validate(
            {**data, "snapshot_ids": [], "status": "queued", "result": None}
        ).snapshot_ids
        == ()
    )
