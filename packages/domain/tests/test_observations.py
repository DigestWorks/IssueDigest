"""Conservative comparison contracts preserve supplied values and uncertainty."""

import importlib
import importlib.util
import json
from datetime import date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

contracts = (
    importlib.import_module("issuedigest_domain.observations")
    if importlib.util.find_spec("issuedigest_domain.observations")
    else None
)


def test_observation_contracts_available():
    assert contracts is not None, "observation contracts missing"


def context(**changes):
    return {
        "metric": "support",
        "unit": "%",
        "population": "adults",
        "geography": "KR",
        "question": "Support proposal?",
        "methodology": "phone",
        "sample_size": 1000,
        "weighting": "age",
        "denominator": "respondents",
        "series_id": "series-1",
        "period": {"start_date": date(2026, 1, 1), "end_date": date(2026, 1, 2)},
        "dimensions": [{"key": "age", "value": "all"}, {"key": "sex", "value": "all"}],
        **changes,
    }


def observation(workspace=None, **changes):
    return contracts.Observation.model_validate(
        {
            "observation_id": uuid4(),
            "workspace_id": workspace or uuid4(),
            "subject_entity_id": None,
            "raw_value": " 40.00% ",
            "value": "40.00",
            "context": context(),
            "citation_ids": [uuid4()],
            **changes,
        }
    )


def test_same_context_ignores_values_and_dimension_order_and_never_aggregates():
    first = observation()
    second = observation(
        first.workspace_id,
        value="-0.000",
        raw_value="-0.000%",
        context=context(dimensions=list(reversed(context()["dimensions"]))),
    )
    before = first.model_dump_json()
    result = contracts.assess_comparison((first, second))
    assert result.status == "same_context"
    assert result.reasons == ()
    assert result.observation_ids == (first.observation_id, second.observation_id)
    assert result.aggregation_status == "not_evaluated"
    assert first.model_dump_json() == before
    assert contracts.ComparisonAssessment.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "field,replacement",
    [
        ("metric", "opposition"),
        ("unit", "persons"),
        ("population", "youth"),
        ("geography", "US"),
        ("question", "Different question?"),
        ("methodology", "online"),
        ("sample_size", 900),
        ("weighting", "region"),
        ("denominator", "all adults"),
        ("series_id", "series-2"),
        ("dimensions", [{"key": "age", "value": "youth"}]),
        ("period", {"start_date": date(2026, 1, 2), "end_date": date(2026, 1, 3)}),
    ],
)
def test_different_known_conditions_are_reported(field, replacement):
    first = observation()
    second = observation(first.workspace_id, context=context(**{field: replacement}))
    result = contracts.assess_comparison((first, second))
    assert result.status == "different_context"
    assert [(r.field, r.kind, r.observation_ids) for r in result.reasons] == [
        (field, "different", (first.observation_id, second.observation_id))
    ]


@pytest.mark.parametrize(
    "field",
    [
        "unit",
        "period",
        "population",
        "geography",
        "question",
        "methodology",
        "sample_size",
        "weighting",
        "denominator",
        "series_id",
    ],
)
def test_missing_conditions_do_not_become_known_defaults(field):
    first = observation(context=context(**{field: None}))
    second = observation(first.workspace_id)
    result = contracts.assess_comparison((first, second))
    assert result.status == "insufficient_context"
    assert [(r.field, r.kind, r.observation_ids) for r in result.reasons] == [
        (field, "missing", (first.observation_id,))
    ]


def test_different_precedes_missing_and_reasons_have_stable_field_and_input_order():
    first = observation(
        context=context(unit=None), value=None, raw_value=None, missing_reason="not_reported"
    )
    second = observation(first.workspace_id)
    third = observation(first.workspace_id, context=context(unit="count", question=None))
    result = contracts.assess_comparison((first, second, third))
    assert result.status == "different_context"
    assert [(r.field, r.kind, r.observation_ids) for r in result.reasons] == [
        ("unit", "missing", (first.observation_id,)),
        ("unit", "different", (second.observation_id, third.observation_id)),
        ("question", "missing", (third.observation_id,)),
        ("value", "missing", (first.observation_id,)),
    ]


def test_empty_dimensions_and_partial_distribution_are_not_an_aggregation_certificate():
    first = observation(context=context(dimensions=[]), value="20")
    second = observation(first.workspace_id, context=context(dimensions=[]), value="30")
    assert contracts.assess_comparison((first, second)).status == "same_context"
    assert contracts.assess_comparison((first, second)).aggregation_status == "not_evaluated"


@pytest.mark.parametrize(
    "value",
    [
        1,
        True,
        1.2,
        "NaN",
        "Infinity",
        "1e3",
        "1,000",
        " 1",
        "1 ",
        "00",
        "01",
        "+1",
        ".1",
        "1.",
        "1\n",
        "１",
        "1" * 129,
    ],
)
def test_numeric_value_rejects_coercion_or_noncanonical_decimal(value):
    with pytest.raises(ValidationError):
        observation(value=value)


@pytest.mark.parametrize(
    "value", ["-0", "-0.00", "123456789012345678901234567890.00100", "1" * 128]
)
def test_decimal_precision_and_negative_zero_are_preserved(value):
    item = observation(value=value)
    assert item.value == value
    assert contracts.Observation.model_validate_json(item.model_dump_json()).value == value


@pytest.mark.parametrize(
    "changes",
    [
        {"raw_value": None},
        {"raw_value": " \t"},
        {"raw_value": 1},
        {"value": None},
        {"missing_reason": "withheld"},
        {"value": None, "missing_reason": "unknown"},
        {"raw_period": " "},
        {"citation_ids": []},
        {"workspace_id": True},
        {"surprise": 1},
    ],
)
def test_observation_rejects_inconsistent_or_invalid_fields(changes):
    with pytest.raises(ValidationError):
        observation(**changes)


@pytest.mark.parametrize(
    "missing_reason", ["not_reported", "unreadable", "not_applicable", "withheld"]
)
def test_missing_value_is_preserved_without_zero_imputation(missing_reason):
    item = observation(
        value=None,
        raw_value="unreadable",
        missing_reason=missing_reason,
        raw_period="2026년 상반기",
        context=context(period=None),
    )
    assert item.value is None
    assert item.raw_value == "unreadable"
    assert item.context.period is None


@pytest.mark.parametrize("value", [True, 1.0, "1", 0, -1])
def test_sample_size_is_a_strict_positive_integer(value):
    with pytest.raises(ValidationError):
        observation(context=context(sample_size=value))


@pytest.mark.parametrize("value", [" ", 1, True])
def test_context_strings_reject_blank_and_numeric_input(value):
    with pytest.raises(ValidationError):
        observation(context=context(unit=value))


def test_duplicate_dimension_keys_and_citations_are_rejected():
    with pytest.raises(ValidationError):
        observation(
            context=context(dimensions=[{"key": "age", "value": "x"}, {"key": "age", "value": "y"}])
        )
    citation = uuid4()
    with pytest.raises(ValidationError):
        observation(citation_ids=[citation, citation])


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 1, 1),
        "2026-1-01",
        "2026-01",
        "2026",
        "2026-02-30",
        "2026-01-01T00:00:00Z",
        0,
        True,
    ],
)
def test_period_dates_reject_invented_or_coerced_precision(value):
    with pytest.raises(ValidationError):
        contracts.DateInterval(start_date=value, end_date=date(2026, 12, 31))
    with pytest.raises(ValidationError):
        contracts.DateInterval.model_validate_json(
            json.dumps(
                {
                    "start_date": value.isoformat() if isinstance(value, datetime) else value,
                    "end_date": "2026-12-31",
                }
            )
        )


def test_period_is_inclusive_strict_and_immutable():
    period = contracts.DateInterval(start_date=date(2026, 1, 1), end_date=date(2026, 1, 1))
    assert contracts.DateInterval.model_validate_json(period.model_dump_json()) == period
    with pytest.raises(ValidationError):
        contracts.DateInterval(start_date="2026-01-01", end_date="2026-01-02")
    with pytest.raises(ValidationError):
        contracts.DateInterval(start_date=date(2026, 1, 2), end_date=date(2026, 1, 1))
    with pytest.raises(ValidationError):
        period.end_date = date(2027, 1, 1)
    item = observation()
    assert isinstance(item.context.dimensions, tuple)
    with pytest.raises(ValidationError):
        item.context.dimensions[0].value = "changed"


def test_comparison_rejects_short_duplicate_cross_workspace_or_unvalidated_input():
    first = observation()
    for items in [(first,), (first, first), (first, observation()), (first, {})]:
        with pytest.raises(ValueError):
            contracts.assess_comparison(items)
    with pytest.raises(ValueError):
        contracts.assess_comparison([first, observation(first.workspace_id)])


@pytest.mark.parametrize(
    "changes",
    [
        {"observation_ids": []},
        {"observation_ids": ["same", "same"]},
        {"policy_version": "v2"},
        {"aggregation_status": "allowed"},
        {"status": "different_context"},
    ],
)
def test_assessment_rejects_invalid_result_contract(changes):
    with pytest.raises(ValidationError):
        contracts.ComparisonAssessment.model_validate(
            {
                "observation_ids": [uuid4(), uuid4()],
                "status": "same_context",
                "reasons": [],
                **changes,
            }
        )


@pytest.mark.parametrize(
    "case",
    [
        "outside",
        "duplicate",
        "empty",
        "different_single",
        "value_different",
        "reason_duplicate",
        "wrong_status",
    ],
)
def test_assessment_validates_reason_membership_cardinality_and_status(case):
    first, second, outside = uuid4(), uuid4(), uuid4()
    reason = {"field": "unit", "kind": "missing", "observation_ids": [first]}
    if case == "outside":
        reason["observation_ids"] = [outside]
    elif case == "duplicate":
        reason["observation_ids"] = [first, first]
    elif case == "empty":
        reason["observation_ids"] = []
    elif case == "different_single":
        reason["kind"] = "different"
    elif case == "value_different":
        reason.update(field="value", kind="different", observation_ids=[first, second])
    reasons = [reason, reason] if case == "reason_duplicate" else [reason]
    payload = {
        "observation_ids": [first, second],
        "status": "insufficient_context",
        "reasons": reasons,
    }
    if case == "wrong_status":
        payload["status"] = "same_context"
    with pytest.raises(ValidationError):
        contracts.ComparisonAssessment.model_validate_json(json.dumps(payload, default=str))


def test_result_duplicate_valid_ids_and_unknown_reason_fields_are_rejected():
    first, second = uuid4(), uuid4()
    for changes in [
        {"observation_ids": [first, first]},
        {"reasons": [{"field": "unknown", "kind": "missing", "observation_ids": [first]}]},
    ]:
        with pytest.raises(ValidationError):
            contracts.ComparisonAssessment.model_validate(
                {
                    "observation_ids": [first, second],
                    "status": "same_context",
                    "reasons": [],
                    **changes,
                }
            )


def test_json_date_shape_rejects_non_ascii_and_trailing_newline():
    for start in ["２０２６-01-01", "2026-０１-01", "2026-01-01\n"]:
        with pytest.raises(ValidationError):
            contracts.DateInterval.model_validate_json(
                json.dumps(
                    {
                        "start_date": start,
                        "end_date": "2026-12-31",
                    }
                )
            )
