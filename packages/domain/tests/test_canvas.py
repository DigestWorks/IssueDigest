"""Allowed proposal shapes and grounded revision references, using synthetic evidence."""

import importlib
import importlib.util
import json
from copy import deepcopy
from uuid import UUID

import pytest
from pydantic import ValidationError
from test_execution import module_data, uid
from test_research import bundle_data

cv = (
    importlib.import_module("issuedigest_domain.canvas")
    if importlib.util.find_spec("issuedigest_domain.canvas")
    else None
)
cm = (
    importlib.import_module("issuedigest_domain.canvas_modules")
    if importlib.util.find_spec("issuedigest_domain.canvas_modules")
    else None
)


def draft_data(**changes):
    return {
        "draft_id": uid(),
        "outcome": "answer",
        "modules": [module_data()],
        "message": None,
        **changes,
    }


def revision_data(research=None, **changes):
    research = research or bundle_data()
    return {
        "revision_id": uid(),
        "workspace_id": research["workspace_id"],
        "run_id": uid(),
        "revision_number": 1,
        "parent_revision_id": None,
        "selected_version_ids": [research["evidence"][0]["version"]["version_id"]],
        "draft": draft_data(
            modules=[
                module_data(citation_ids=[research["evidence"][0]["citations"][0]["citation_id"]])
            ]
        ),
        "validated_at": "2026-10-01T00:00:02Z",
        **changes,
    }


def canvas_data():
    research = bundle_data()
    return {"research": research, "revision": revision_data(research)}


def test_canvas_available():
    assert cv is not None and cm is not None, "canvas contracts missing"


@pytest.fixture(autouse=True)
def require_contract(request):
    if (cv is None or cm is None) and request.node.name != "test_canvas_available":
        pytest.skip("not available")


@pytest.mark.parametrize(
    "kind,fields",
    [
        ("evidence", {}),
        ("summary", {"claim_ids": [uid()]}),
        ("comparison", {"claim_ids": [uid(), uid()]}),
        ("timeline", {"claim_ids": [uid()]}),
        ("graph", {"relation_ids": [uid()]}),
        ("chart", {"observation_ids": [uid(), uid()], "chart_type": "bar"}),
    ],
)
def test_allowlisted_module_and_action_shapes(kind, fields):
    module = module_data(
        kind=kind,
        **fields,
        actions=[
            {"kind": "ask_question", "question": "다른 질문"},
            {"kind": "sort", "field": "title", "direction": "asc"},
        ],
    )
    draft = cv.CanvasDraft.model_validate(draft_data(modules=[module]))
    assert draft.modules[0].kind == kind and isinstance(draft.modules[0].actions, tuple)
    assert cv.CanvasDraft.model_validate_json(draft.model_dump_json()) == draft


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "html"},
        {"html": "<div>"},
        {"url": "https://example.com"},
        {"actions": [{"kind": "execute", "tool": "x"}]},
        {"kind": "chart", "observation_ids": [uid()], "chart_type": "bar"},
        {"kind": "chart", "observation_ids": [uid(), uid()], "chart_type": "pie"},
        {"kind": "summary"},
        {"kind": "comparison", "claim_ids": [uid()]},
        {"citation_ids": []},
        {"title": "  "},
    ],
)
def test_rejects_unknown_and_incomplete_modules(change):
    with pytest.raises(ValidationError):
        cv.CanvasDraft.model_validate(draft_data(modules=[module_data(**change)]))


@pytest.mark.parametrize(
    "outcome",
    ["insufficient_evidence", "clarification_needed", "provider_refusal", "incomplete_output"],
)
def test_nonanswer_requires_message_and_empty_modules(outcome):
    draft = cv.CanvasDraft.model_validate(
        draft_data(outcome=outcome, modules=[], message="입력 안내")
    )
    assert draft.modules == ()
    for change in [{"message": None}, {"modules": [module_data()]}]:
        with pytest.raises(ValidationError):
            cv.CanvasDraft.model_validate({**draft.model_dump(), **change})
    if outcome in ["provider_refusal", "incomplete_output"]:
        with pytest.raises(ValidationError):
            cv.CanvasRevision.model_validate(revision_data(draft=draft))


def test_duplicate_module_and_action_rejected_distinct_questions_and_sorts_allowed():
    module = module_data()
    with pytest.raises(ValidationError):
        cv.CanvasDraft.model_validate(draft_data(modules=[module, module]))
    action = {"kind": "ask_question", "question": "질문"}
    with pytest.raises(ValidationError):
        cv.CanvasDraft.model_validate(draft_data(modules=[module_data(actions=[action, action])]))
    assert cv.CanvasDraft.model_validate(
        draft_data(
            modules=[
                module_data(
                    actions=[
                        action,
                        {**action, "question": "다른 질문"},
                        {"kind": "sort", "field": "title", "direction": "asc"},
                        {"kind": "sort", "field": "title", "direction": "desc"},
                    ]
                )
            ]
        )
    )


def test_canvas_reference_selection_actions_and_claim_union():
    data = canvas_data()
    proof = data["research"]["evidence"][0]
    module = data["revision"]["draft"]["modules"][0]
    module.update(
        kind="comparison",
        claim_ids=[c["claim_id"] for c in data["research"]["claims"]],
        actions=[
            {"kind": "open_evidence", "citation_id": module["citation_ids"][0]},
            {"kind": "select_document", "document_id": proof["document"]["document_id"]},
        ],
    )
    assert cv.CanvasBundle.model_validate(data).revision.draft.modules[0].kind == "comparison"
    for change in [
        {"workspace_id": uid()},
        {"selected_version_ids": []},
        {"selected_version_ids": [uid()]},
    ]:
        with pytest.raises(ValidationError):
            cv.CanvasBundle.model_validate({**data, "revision": {**data["revision"], **change}})
    for change in [
        {"claim_ids": [uid(), uid()]},
        {"citation_ids": [uid()]},
        {"actions": [{"kind": "open_evidence", "citation_id": uid()}]},
        {"actions": [{"kind": "select_document", "document_id": uid()}]},
    ]:
        invalid = deepcopy(data)
        invalid["revision"]["draft"]["modules"][0].update(change)
        with pytest.raises(ValidationError):
            cv.CanvasBundle.model_validate(invalid)


def test_timeline_requires_claim_valid_period():
    data = canvas_data()
    data["revision"]["draft"]["modules"][0].update(
        kind="timeline", claim_ids=[data["research"]["claims"][0]["claim_id"]]
    )
    with pytest.raises(ValidationError):
        cv.CanvasBundle.model_validate(data)
    data["research"]["claims"][0]["valid_period"] = {
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
    }
    assert cv.CanvasBundle.model_validate_json(json.dumps(data))


def chart_data():
    data = canvas_data()
    citations = data["revision"]["draft"]["modules"][0]["citation_ids"]
    context = {
        "metric": "응답 비율",
        "unit": "%",
        "period": {"start_date": "2026-01-01", "end_date": "2026-01-31"},
        "population": "성인",
        "geography": "전국",
        "question": "질문",
        "methodology": "전화",
        "sample_size": 1000,
        "weighting": "보고",
        "denominator": "응답자",
        "series_id": "synthetic",
        "dimensions": [],
    }
    data["research"]["observations"] = [
        {
            "observation_id": uid(),
            "workspace_id": data["research"]["workspace_id"],
            "raw_value": value,
            "value": value,
            "context": context,
            "citation_ids": citations,
        }
        for value in ["45.5", "50.1"]
    ]
    data["revision"]["draft"]["modules"][0].update(
        kind="chart",
        chart_type="bar",
        observation_ids=[o["observation_id"] for o in data["research"]["observations"]],
    )
    return data


def test_chart_only_known_values_with_same_context():
    data = chart_data()
    assert cv.CanvasBundle.model_validate_json(json.dumps(data))
    for change in [
        {"value": None, "missing_reason": "not_reported"},
        {"context": {**data["research"]["observations"][1]["context"], "population": "청년"}},
        {"context": {**data["research"]["observations"][1]["context"], "unit": None}},
    ]:
        invalid = deepcopy(data)
        invalid["research"]["observations"][1].update(change)
        with pytest.raises(ValidationError):
            cv.CanvasBundle.model_validate_json(json.dumps(invalid))


def test_promote_revision_checks_parent_expected_number_workspace_without_mutation():
    data = canvas_data()
    candidate = cv.CanvasBundle.model_validate(data)
    assert cv.promote_revision(None, candidate, None) is candidate.revision
    current = candidate.revision
    second = deepcopy(data)
    second["revision"].update(
        revision_id=uid(), parent_revision_id=str(current.revision_id), revision_number=2
    )
    candidate = cv.CanvasBundle.model_validate(second)
    assert cv.promote_revision(current, candidate, current.revision_id) is candidate.revision
    assert current.revision_number == 1
    for expected in [None, UUID(uid())]:
        with pytest.raises(ValueError):
            cv.promote_revision(current, candidate, expected)
    for change in [
        {"parent_revision_id": uid()},
        {"revision_number": 3},
        {"revision_id": str(current.revision_id), "parent_revision_id": None, "revision_number": 1},
    ]:
        invalid = deepcopy(second)
        invalid["revision"].update(change)
        with pytest.raises(ValueError):
            cv.promote_revision(
                current, cv.CanvasBundle.model_validate(invalid), current.revision_id
            )
    with pytest.raises(ValueError):
        cv.promote_revision(None, candidate, None)


@pytest.mark.parametrize(
    "field,value",
    [
        ("revision_number", True),
        ("revision_number", "1"),
        ("revision_number", 2**53),
        ("schema_version", True),
        ("schema_version", "1"),
    ],
)
def test_revision_strict_safe_numbers(field, value):
    with pytest.raises(ValidationError):
        cv.CanvasRevision.model_validate({**revision_data(), field: value})


def test_grounding_requires_exact_union_not_any_selected_citation():
    from test_research import evidence

    data = canvas_data()
    proof = evidence(data["research"]["workspace_id"])
    data["research"]["evidence"].append(proof)
    data["revision"]["selected_version_ids"].append(proof["version"]["version_id"])
    module = data["revision"]["draft"]["modules"][0]
    module.update(kind="summary", claim_ids=[data["research"]["claims"][0]["claim_id"]])
    assert cv.CanvasBundle.model_validate(data)
    module["citation_ids"].append(proof["citations"][0]["citation_id"])
    with pytest.raises(ValidationError):
        cv.CanvasBundle.model_validate(data)
    data["research"]["claims"][0]["citation_ids"].append(proof["citations"][0]["citation_id"])
    assert cv.CanvasBundle.model_validate(data)
    module["citation_ids"].pop()
    with pytest.raises(ValidationError):
        cv.CanvasBundle.model_validate(data)


def test_graph_uses_relation_citation_union_and_chart_unknown_observation_rejected():
    data = canvas_data()
    module = data["revision"]["draft"]["modules"][0]
    module.update(kind="graph", relation_ids=[data["research"]["relations"][0]["relation_id"]])
    assert cv.CanvasBundle.model_validate(data)
    module["relation_ids"] = [uid()]
    with pytest.raises(ValidationError):
        cv.CanvasBundle.model_validate(data)
    data = chart_data()
    data["revision"]["draft"]["modules"][0]["observation_ids"][0] = uid()
    with pytest.raises(ValidationError):
        cv.CanvasBundle.model_validate_json(json.dumps(data))


def test_revision_parent_self_duplicate_selection_and_workspace_promotion():
    data = revision_data()
    for change in [
        {"parent_revision_id": data["revision_id"]},
        {"revision_number": 2},
        {"selected_version_ids": data["selected_version_ids"] * 2},
    ]:
        with pytest.raises(ValidationError):
            cv.CanvasRevision.model_validate({**data, **change})
    current = cv.CanvasRevision.model_validate(data)
    candidate = canvas_data()
    candidate["revision"].update(parent_revision_id=str(current.revision_id), revision_number=2)
    with pytest.raises(ValueError):
        cv.promote_revision(current, cv.CanvasBundle.model_validate(candidate), current.revision_id)
