"""Strict immutable question selection contracts, without source or actor data."""

import importlib
from uuid import uuid4

import pytest
from pydantic import ValidationError


def api():
    name = "issuedigest_domain.question_source_plan"
    assert importlib.util.find_spec(name), "Missing question selection domain"
    return importlib.import_module(name)


def fields():
    return dict(
        plan_id=uuid4(),
        workspace_id=uuid4(),
        request_id=uuid4(),
        question=" exact ",
        status="selected",
        reason=None,
        sources=(api().QuestionSourceChoice(snapshot_id=uuid4(), source_sha256="a" * 64),),
    )


def test_roundtrip_preserves_question_and_freezes():
    plan = api().QuestionSourcePlan(**fields())
    assert plan.question == " exact "
    assert api().QuestionSourcePlan.model_validate_json(plan.model_dump_json(), strict=True) == plan
    with pytest.raises(ValidationError):
        plan.question = "changed"


@pytest.mark.parametrize(
    "key,value",
    [
        ("question", True),
        ("question", " "),
        ("question", "a" * 1501),
        ("plan_id", str(uuid4())),
        ("workspace_id", True),
        ("status", "pending"),
        ("reason", "no_terms"),
        ("sources", ()),
        ("actor_id", uuid4()),
        ("profile", "other"),
        ("retrieval_profile", "other"),
    ],
)
def test_rejects_invalid_plan(key, value):
    data = fields()
    data[key] = value
    with pytest.raises(ValidationError):
        api().QuestionSourcePlan(**data)


def test_choice_and_state_constraints():
    cls = api().QuestionSourcePlan
    data = fields()
    for choices in (data["sources"] * 2, data["sources"] * 6, list(data["sources"])):
        with pytest.raises(ValidationError):
            cls(**(data | {"sources": choices}))
    for reason in ("no_terms", "no_candidates"):
        assert (
            cls(**(data | {"status": "no_match", "reason": reason, "sources": ()})).reason == reason
        )
    with pytest.raises(ValidationError):
        cls(**(data | {"status": "no_match", "sources": ()}))
    for hashed in ("A" * 64, "a" * 63, True):
        with pytest.raises(ValidationError):
            api().QuestionSourceChoice(snapshot_id=uuid4(), source_sha256=hashed)
