"""Identity is explicit; claim evidence and supplied review are not proof of truth."""

import importlib
import importlib.util
import json
from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

contracts = (
    importlib.import_module("issuedigest_domain.knowledge")
    if importlib.util.find_spec("issuedigest_domain.knowledge")
    else None
)


def test_knowledge_contracts_available():
    assert contracts is not None, "knowledge contracts missing"


def entity(**changes):
    return contracts.Entity.model_validate(
        {
            "entity_id": uuid4(),
            "workspace_id": uuid4(),
            "kind": "person",
            "name": "홍길동",
            **changes,
        }
    )


def claim(**changes):
    return contracts.Claim.model_validate(
        {
            "claim_id": uuid4(),
            "workspace_id": uuid4(),
            "text": "화자가 제안을 지지한다고 말했다",
            "basis": "source_assertion",
            "speaker_entity_id": None,
            "subject_entity_ids": [],
            "citation_ids": [uuid4()],
            **changes,
        }
    )


def review(**changes):
    return {
        "review_id": uuid4(),
        "reviewer_kind": "human",
        "reviewer_id": "reviewer-1",
        "method": "reading",
        "method_version": "1",
        "reviewed_at": datetime.now(UTC),
        "rationale": "제공된 원문에서 확인",
        "citation_ids": [uuid4()],
        **changes,
    }


def test_same_name_entities_remain_distinct_and_unresolved():
    first, second = entity(), entity()
    assert first.name == second.name
    assert first.entity_id != second.entity_id
    assert first.source_identities == ()
    assert first.identity_review is None
    assert contracts.Entity.model_validate_json(first.model_dump_json()) == first


@pytest.mark.parametrize(
    "changes",
    [
        {"name": " "},
        {"name": 1},
        {"kind": "event"},
        {"aliases": [" "]},
        {"aliases": ["same", "same"]},
        {"aliases": [True]},
        {"raw_validity_text": " "},
        {"entity_id": UUID("12345678-1234-1231-9234-123456789012")},
        {"extra": "ignored"},
        {"source_identities": [{"provider": " ", "namespace": "person", "value": "1"}]},
        {"source_identities": [{"provider": "a", "namespace": "person", "value": 1}]},
        {"source_identities": [{"provider": "a", "namespace": "person", "value": "1"}] * 2},
    ],
)
def test_entity_rejects_invalid_or_duplicated_identity_input(changes):
    with pytest.raises(ValidationError):
        entity(**changes)


def test_entity_identity_is_three_part_key_and_aliases_preserve_spelling():
    item = entity(
        aliases=["A", "a"],
        source_identities=[
            {"provider": "a", "namespace": "person", "value": "1"},
            {"provider": "b", "namespace": "person", "value": "1"},
        ],
        valid_period={"start_date": date(2026, 1, 1), "end_date": date(2026, 1, 1)},
    )
    assert item.aliases == ("A", "a")
    with pytest.raises(ValidationError):
        item.source_identities[0].value = "changed"


@pytest.mark.parametrize("basis", ["source_assertion", "observation", "inference"])
def test_claim_basis_and_supplied_derivation_are_preserved(basis):
    derivation = {"method": "comparison", "method_version": "1", "rationale": "supplied inference"}
    item = claim(basis=basis, derivation=derivation if basis == "inference" else None)
    assert item.speaker_entity_id is None
    assert item.basis == basis
    assert contracts.Claim.model_validate_json(item.model_dump_json()) == item
    with pytest.raises(ValidationError):
        item.text = "changed"


@pytest.mark.parametrize(
    "changes",
    [
        {"basis": "inference"},
        {"basis": "guess"},
        {"citation_ids": []},
        {"text": " "},
        {"text": False},
        {"raw_event_time_text": " "},
        {
            "basis": "observation",
            "derivation": {"method": "a", "method_version": "1", "rationale": "r"},
        },
        {
            "basis": "source_assertion",
            "derivation": {"method": "a", "method_version": "1", "rationale": "r"},
        },
        {
            "basis": "inference",
            "derivation": {"method": " ", "method_version": "1", "rationale": "r"},
        },
    ],
)
def test_claim_rejects_unfounded_or_misclassified_derivation(changes):
    with pytest.raises(ValidationError):
        claim(**changes)


def test_claim_subject_and_citation_ids_are_unique():
    identity = uuid4()
    for field in ["subject_entity_ids", "citation_ids"]:
        with pytest.raises(ValidationError):
            claim(**{field: [identity, identity]})


@pytest.mark.parametrize(
    "value",
    [0, 1.5, True, "0", "1720000000", "2026-01-01", "2026-01-01T00:00:00", datetime(2026, 1, 1)],
)
def test_review_time_rejects_epochs_and_naive_or_date_only_inputs(value):
    payload = review(reviewed_at=value, assessment="confirmed")
    with pytest.raises(ValidationError):
        contracts.IdentityReview.model_validate(payload)
    with pytest.raises(ValidationError):
        contracts.IdentityReview.model_validate_json(json.dumps(payload, default=str))


def test_review_time_normalizes_aware_iso_datetime_to_utc():
    item = contracts.IdentityReview.model_validate(
        review(reviewed_at="2026-01-01T09:00:00+09:00", assessment="ambiguous")
    )
    assert item.reviewed_at == datetime(2026, 1, 1, tzinfo=UTC)
    assert item.model_dump(mode="json")["reviewed_at"] == "2026-01-01T00:00:00Z"
    assert contracts.IdentityReview.model_validate_json(item.model_dump_json()) == item
    aware = datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=9)))
    assert contracts.IdentityReview.model_validate(
        review(reviewed_at=aware, assessment="confirmed")
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"reviewer_kind": "system"},
        {"reviewer_id": " "},
        {"method": " "},
        {"method_version": True},
        {"rationale": " "},
        {"citation_ids": []},
        {"assessment": "resolved"},
        {"extra": "ignored"},
    ],
)
def test_identity_review_rejects_invalid_metadata(changes):
    with pytest.raises(ValidationError):
        contracts.IdentityReview.model_validate(review(**{"assessment": "confirmed", **changes}))


def test_review_citations_are_unique_and_review_input_is_immutable():
    identity = uuid4()
    with pytest.raises(ValidationError):
        contracts.IdentityReview.model_validate(
            review(citation_ids=[identity, identity], assessment="confirmed")
        )
    item = contracts.IdentityReview.model_validate(review(assessment="confirmed"))
    with pytest.raises(ValidationError):
        item.assessment = "ambiguous"


@pytest.mark.parametrize(
    "kind,scope", [("claim", "attribution"), ("claim", "content"), ("relation", "relation")]
)
def test_support_review_distinguishes_attribution_content_and_relation(kind, scope):
    target = {"kind": kind, f"{kind}_id": uuid4()}
    item = contracts.SupportReview.model_validate(
        review(target=target, scope=scope, assessment="supported")
    )
    assert item.target.kind == kind
    assert item.scope == scope
    assert contracts.SupportReview.model_validate_json(item.model_dump_json()) == item


@pytest.mark.parametrize(
    "kind,scope",
    [
        ("claim", "relation"),
        ("relation", "content"),
        ("relation", "attribution"),
        ("entity", "content"),
        ("document", "content"),
    ],
)
def test_support_review_rejects_wrong_target_tag_or_scope(kind, scope):
    with pytest.raises(ValidationError):
        contracts.SupportReview.model_validate(
            review(
                target={"kind": kind, f"{kind}_id": uuid4()}, scope=scope, assessment="supported"
            )
        )


@pytest.mark.parametrize("kind", ["Entity", "Claim", "Document", "Relation"])
def test_typed_references_reject_wrong_tag_unknown_fields_and_non_uuid4(kind):
    model = getattr(contracts, f"{kind}Reference")
    field = f"{kind.lower()}_id"
    item = model.model_validate({"kind": kind.lower(), field: uuid4()})
    assert model.model_validate_json(item.model_dump_json()) == item
    for changes in [{"kind": "unknown"}, {"extra": 1}, {field: 1}]:
        with pytest.raises(ValidationError):
            model.model_validate({**item.model_dump(), **changes})
