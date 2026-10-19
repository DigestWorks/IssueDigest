"""Reviewed publication is an explicit copy; synthetic evidence never grants rights."""

import importlib
import importlib.util
import json
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from conftest import public_plan_data as plan_data

pb = (
    importlib.import_module("issuedigest_domain.public_briefings")
    if importlib.util.find_spec("issuedigest_domain.public_briefings")
    else None
)


def test_publication_contract_exists():
    assert pb is not None, "public publication contracts missing"


@pytest.fixture(autouse=True)
def require_contract(request):
    if pb is None and request.node.name != "test_publication_contract_exists":
        pytest.skip("not available")


def test_public_copy_preserves_exact_evidence_and_remaps_all_ids():
    plan = pb.PublicBriefingPlan.model_validate(plan_data())
    result = pb.publish_copy(plan, datetime(2026, 10, 14, tzinfo=UTC))
    assert result == pb.publish_copy(plan, result.published_at)
    assert pb.PublicBriefingDetail.model_validate_json(result.model_dump_json()) == result
    old, new = plan.canvas.research.evidence[0], result.canvas.research.evidence[0]
    assert new.representation.text == old.representation.text
    assert new.representation.pages == old.representation.pages
    assert new.representation.tables == old.representation.tables
    assert new.citations[0].selector == old.citations[0].selector
    assert new.version.collected_at == old.version.collected_at
    assert new.document.source_id == str(new.document.document_id)
    assert new.representation.parser_name == "public-reviewed-copy"
    assert result.source_titles == {new.document.document_id: plan.sources[0].title}
    raw = result.model_dump_json()
    assert "private-reviewer" not in raw
    for token in json.dumps(plan.canvas.model_dump(mode="json")).replace('"', " ").split():
        try:
            identity = UUID(token.strip(",:[]{}"))
        except ValueError:
            continue
        assert str(identity) not in raw
    assert UUID(str(new.document.document_id)).version == 4
    assert result.content_sha256 == pb.content_hash(result)


@pytest.mark.parametrize(
    "url",
    [
        "http://www.korea.kr/news/policyNewsView.do?newsId=1",
        "https://korea.kr/news/policyNewsView.do?newsId=1",
        "https://www.korea.kr/news/policyNewsView.do?newsId=１",
        "https://www.korea.kr/news/policyNewsView.do?newsId=1&other=2",
        "https://www.korea.kr/news/policyNewsView.do?newsId=1#fragment",
        "https://secret@www.korea.kr/news/policyNewsView.do?newsId=1",
        "https://www.korea.kr:443/news/policyNewsView.do?newsId=1",
    ],
)
def test_only_individually_approved_official_urls(url):
    data = plan_data()
    data["sources"][0]["official_url"] = url
    data["canvas"]["research"]["evidence"][0]["document"]["canonical_url"] = url
    with pytest.raises(ValidationError):
        pb.PublicBriefingPlan.model_validate(data)


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(slug="bad--slug"),
        lambda d: d.update(version=True),
        lambda d: d.update(version=2**53),
        lambda d: d.update(title=" "),
        lambda d: d["sources"][0].update(text_sha256="b" * 64),
        lambda d: d["sources"][0].update(photos_excluded=False),
        lambda d: d["sources"][0].update(photos_excluded=1),
        lambda d: d["sources"][0].update(checked_at="2026-10-11T00:00:00Z"),
        lambda d: d["sources"].append(deepcopy(d["sources"][0])),
        lambda d: d["canvas"]["revision"]["draft"]["modules"][0].update(
            actions=[{"kind": "ask_question", "question": "private"}]
        ),
        lambda d: d["canvas"]["research"].update(evidence=[]),
        lambda d: d["canvas"]["research"]["evidence"][0]["citations"][0]["selector"].update(
            quote="not the quote"
        ),
    ],
)
def test_publication_rejects_unsafe_or_unreviewed_inputs(change):
    data = plan_data()
    change(data)
    with pytest.raises(ValidationError):
        pb.PublicBriefingPlan.model_validate(data)


def test_full_plan_hash_includes_private_review_and_revalidates_forged_models():
    first = pb.PublicBriefingPlan.model_validate(plan_data())
    second = first.model_copy(update={"title": "새 공개 제목"})
    assert pb.plan_hash(first) != pb.plan_hash(second)
    reviewed = first.model_copy(
        update={
            "sources": (
                first.sources[0].model_copy(update={"reviewer": "another-private-reviewer"}),
            )
        }
    )
    assert pb.plan_hash(first) != pb.plan_hash(reviewed)
    with pytest.raises(ValueError):
        pb.publish_copy(first.model_copy(update={"version": True}), datetime.now(UTC))
    detail = pb.publish_copy(first, datetime(2026, 10, 14, tzinfo=UTC))
    with pytest.raises(ValidationError):
        pb.PublicBriefingDetail.model_validate_json(
            detail.model_copy(update={"content_sha256": "0" * 64}).model_dump_json()
        )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["canvas"]["revision"]["draft"]["modules"][0].update(span="half"),
        lambda d: d["canvas"]["revision"]["draft"]["modules"][0].update(actions=[]),
        lambda d: d["canvas"]["revision"]["draft"]["modules"].pop(),
        lambda d: d["canvas"]["research"]["claims"][0].update(raw_event_time_text="private"),
        lambda d: d["canvas"]["research"]["claims"][0]["derivation"].update(rationale="x" * 201),
        lambda d: d["canvas"]["revision"].update(
            revision_number=2, parent_revision_id=str(uuid4())
        ),
        lambda d: d["sources"][0].update(title=str(uuid4())),
    ],
)
def test_public_python_scope_matches_strict_research_display_subset(change):
    data = plan_data()
    change(data)
    with pytest.raises(ValidationError):
        pb.PublicBriefingPlan.model_validate(data)


def test_baseline_can_predate_collection_but_not_source_publication():
    data = plan_data()
    data["as_of"] = "2026-10-12T00:00:00Z"
    assert pb.PublicBriefingPlan.model_validate(data).as_of.day == 12
    data["as_of"] = "2026-10-11T00:00:00Z"
    with pytest.raises(ValidationError):
        pb.PublicBriefingPlan.model_validate(data)


def test_plan_rejects_raw_document_url_before_url_library_normalizes_it():
    data = plan_data()
    data["canvas"]["research"]["evidence"][0]["document"]["canonical_url"] = (
        "https://www.korea.kr:443/news/policyNewsView.do?newsId=148000001"
    )
    with pytest.raises(ValidationError):
        pb.PublicBriefingPlan.model_validate(data)


@pytest.mark.parametrize("version", ["v3", "v4", "v5", "v6", "v7", "v8", "v9", "v10"])
@pytest.mark.parametrize("stripped", [False, True])
def test_public_profile_never_accepts_private_classification_even_without_reviews(
    stripped, version
):
    data = plan_data()
    claim = data["canvas"]["research"]["claims"][0]
    claim["derivation"]["method_version"] = f"research-{version}"
    if not stripped:
        data["canvas"]["research"]["support_reviews"] = [
            {
                "review_id": str(uuid4()),
                "reviewer_kind": "automated",
                "reviewer_id": f"issuedigest-research-{version}",
                "method": "pydantic-ai",
                "method_version": f"research-{version}",
                "reviewed_at": data["canvas"]["revision"]["validated_at"],
                "rationale": "합성 평가",
                "citation_ids": claim["citation_ids"],
                "target": {"kind": "claim", "claim_id": claim["claim_id"]},
                "scope": "content",
                "assessment": "supported",
            }
        ]
    with pytest.raises(ValidationError):
        pb.PublicBriefingPlan.model_validate(data)
