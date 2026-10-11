"""Synthetic monthly usage accounting, with integer money and conservative holds."""

import importlib
import importlib.util
import json
from copy import deepcopy
from decimal import localcontext

import pytest
from pydantic import TypeAdapter, ValidationError
from test_execution import uid

us = (
    importlib.import_module("issuedigest_domain.usage")
    if importlib.util.find_spec("issuedigest_domain.usage")
    else None
)


def pricing_data(**changes):
    return {
        "snapshot_id": uid(),
        "provider": "synthetic",
        "operation": "generate",
        "model": None,
        "pricing_version": "1",
        "exchange_rate_version": "1",
        "captured_at": "2026-09-30T15:00:00Z",
        "currency": "KRW",
        "unit_price": "0.000001",
        "unit_quantity": 1,
        "fx_krw_per_currency": "1.00",
        **changes,
    }


def book_data():
    workspace, run, reservation = uid(), uid(), uid()
    price = pricing_data()
    period = {"start_date": "2026-10-01", "end_date": "2026-10-31"}
    return {
        "window": {
            "workspace_id": workspace,
            "period": period,
            "timezone": "Asia/Seoul",
            "limit_microwon": "100000000000",
            "committed_other_cost_microwon": "30000000000",
        },
        "pricing_snapshots": [price],
        "reservations": [
            {
                "reservation_id": reservation,
                "workspace_id": workspace,
                "run_id": run,
                "period": period,
                "reserved_microwon": "5000000000",
                "status": "held",
                "pricing_snapshot_ids": [price["snapshot_id"]],
                "created_at": "2026-09-30T15:00:01Z",
                "settled_at": None,
                "settled_microwon": None,
            }
        ],
        "entries": [
            {
                "entry_id": uid(),
                "workspace_id": workspace,
                "run_id": run,
                "reservation_id": reservation,
                "attempt_id": uid(),
                "pricing_snapshot_id": price["snapshot_id"],
                "provider": price["provider"],
                "operation": price["operation"],
                "model": price["model"],
                "input_tokens": None,
                "output_tokens": 0,
                "charge_status": "unknown",
                "cost_microwon": None,
                "provider_usage_ref": None,
            }
        ],
    }


def test_usage_available():
    assert us is not None, "usage contracts missing"


@pytest.fixture(autouse=True)
def require_contract(request):
    if us is None and request.node.name != "test_usage_available":
        pytest.skip("not available")


def book(data):
    return us.UsageBook.model_validate_json(json.dumps(data))


def test_budget_keeps_unknown_hold_and_counts_other_monthly_cost():
    validated = book(book_data())
    result = us.assess_budget(validated, "65000000000")
    assert result.model_dump() == {
        "limit_microwon": "100000000000",
        "used_microwon": "35000000000",
        "requested_microwon": "65000000000",
        "remaining_microwon": "65000000000",
        "overrun_microwon": "0",
        "allowed": True,
        "policy_version": "issuedigest-budget-v1",
    }
    assert not us.assess_budget(validated, "65000000001").allowed
    assert validated.reservations[0].status == "held"


def test_budget_sums_each_retry_and_preserves_cost_above_reservation():
    data = book_data()
    data["entries"][0].update(charge_status="confirmed", cost_microwon="40000000000")
    data["entries"].append(
        {
            **data["entries"][0],
            "entry_id": uid(),
            "attempt_id": uid(),
            "cost_microwon": "40000000001",
        }
    )
    result = us.assess_budget(book(data), "0")
    assert (
        result.used_microwon,
        result.remaining_microwon,
        result.overrun_microwon,
        result.allowed,
    ) == ("110000000001", "0", "10000000001", False)
    data["reservations"][0].update(
        status="settled", settled_at="2026-11-01T00:00:00Z", settled_microwon="80000000001"
    )
    result = us.assess_budget(book(data), "1")
    assert result.used_microwon == "110000000001" and not result.allowed


def test_budget_integer_arithmetic_ignores_decimal_context_and_float_precision():
    data = book_data()
    data["window"]["committed_other_cost_microwon"] = "0"
    data["reservations"][0]["reserved_microwon"] = "0"
    costs = ["9007199254740993", "123456789012345678901234567890", "7"]
    data["entries"] = [
        {
            **data["entries"][0],
            "entry_id": uid(),
            "attempt_id": uid(),
            "charge_status": "confirmed",
            "cost_microwon": cost,
        }
        for cost in costs
    ]
    with localcontext() as context:
        context.prec = 2
        result = us.assess_budget(book(data), "0")
    assert result.used_microwon == "123456789012354686100489308890"
    assert result.overrun_microwon == "123456789012354686000489308890"


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        1,
        1.0,
        -1,
        "01",
        "-1",
        "+1",
        "1e6",
        "1.0",
        " 1",
        "1 ",
        "1\n",
        "１",
        "",
        "1" * 129,
    ],
)
def test_money_rejects_coercion_and_noncanonical_strings(value):
    with pytest.raises(ValidationError):
        TypeAdapter(us.MoneyMicrowon).validate_python(value)
    with pytest.raises(ValidationError):
        us.assess_budget(book(book_data()), value)


@pytest.mark.parametrize("value", ["0", "1", "9007199254740993", "9" * 128])
def test_money_keeps_exact_ascii_integer(value):
    assert TypeAdapter(us.MoneyMicrowon).validate_python(value) == value


@pytest.mark.parametrize(
    "field,value",
    [
        ("unit_price", True),
        ("unit_price", 0.1),
        ("unit_price", "01"),
        ("unit_price", "1e-3"),
        ("unit_price", "-0"),
        ("unit_price", "1\n"),
        ("unit_price", "１"),
        ("unit_price", "1" * 129),
        ("fx_krw_per_currency", "0"),
        ("fx_krw_per_currency", "2"),
        ("unit_quantity", True),
        ("unit_quantity", "1"),
        ("unit_quantity", 2**53),
    ],
)
def test_pricing_is_strict_bounded_and_krw_fx_exactly_one(field, value):
    with pytest.raises(ValidationError):
        us.PricingSnapshot.model_validate({**pricing_data(), field: value})


def test_usd_decimal_prices_and_fx_preserve_input_strings():
    data = pricing_data(currency="USD", unit_price="0.000010", fx_krw_per_currency="1300.00100")
    price = us.PricingSnapshot.model_validate(data)
    assert price.unit_price == "0.000010" and price.fx_krw_per_currency == "1300.00100"


@pytest.mark.parametrize(
    "change",
    [
        {"limit_microwon": "0"},
        {"limit_microwon": "100000000001"},
        {"timezone": "UTC"},
        {"period": {"start_date": "2026-10-02", "end_date": "2026-10-31"}},
        {"period": {"start_date": "2026-10-01", "end_date": "2026-11-30"}},
    ],
)
def test_budget_window_requires_full_month_and_whole_operation_limit(change):
    data = book_data()
    data["window"].update(change)
    with pytest.raises(ValidationError):
        book(data)


@pytest.mark.parametrize(
    "change",
    [
        "reservation_workspace",
        "entry_workspace",
        "period",
        "created_outside",
        "future_price",
        "price_ref",
        "entry_price_not_reserved",
        "reservation_ref",
        "run_ref",
        "provider",
        "operation",
        "model",
        "duplicate_price",
        "duplicate_reservation",
        "same_run",
        "duplicate_entry",
        "duplicate_attempt",
    ],
)
def test_usage_book_rejects_conflicting_references(change):
    data = book_data()
    reservation, entry = data["reservations"][0], data["entries"][0]
    if change == "reservation_workspace":
        reservation["workspace_id"] = uid()
    if change == "entry_workspace":
        entry["workspace_id"] = uid()
    if change == "period":
        reservation["period"] = {"start_date": "2026-11-01", "end_date": "2026-11-30"}
    if change == "created_outside":
        reservation["created_at"] = "2026-09-30T14:59:59Z"
    if change == "future_price":
        data["pricing_snapshots"][0]["captured_at"] = "2026-10-02T00:00:00Z"
    if change == "price_ref":
        reservation["pricing_snapshot_ids"] = [uid()]
    if change == "entry_price_not_reserved":
        price = pricing_data()
        data["pricing_snapshots"].append(price)
        entry["pricing_snapshot_id"] = price["snapshot_id"]
    if change == "reservation_ref":
        entry["reservation_id"] = uid()
    if change == "run_ref":
        entry["run_id"] = uid()
    if change in ["provider", "operation", "model"]:
        entry[change] = "different"
    if change == "duplicate_price":
        data["pricing_snapshots"].append(deepcopy(data["pricing_snapshots"][0]))
    if change == "duplicate_reservation":
        data["reservations"].append(deepcopy(reservation))
    if change == "same_run":
        data["reservations"].append({**reservation, "reservation_id": uid()})
    if change == "duplicate_entry":
        data["entries"].append(deepcopy(entry))
    if change == "duplicate_attempt":
        data["entries"].append({**entry, "entry_id": uid()})
    with pytest.raises(ValidationError):
        book(data)


@pytest.mark.parametrize(
    "change",
    [
        {"charge_status": "confirmed", "cost_microwon": None},
        {"charge_status": "estimated", "cost_microwon": None},
        {"charge_status": "not_charged", "cost_microwon": None},
        {"charge_status": "not_charged", "cost_microwon": "1"},
        {"input_tokens": True},
        {"output_tokens": "1"},
        {"input_tokens": 2**53},
    ],
)
def test_usage_entry_charge_cost_and_safe_tokens(change):
    data = book_data()
    data["entries"][0].update(change)
    with pytest.raises(ValidationError):
        book(data)


def test_settled_requires_exact_known_total_and_allows_empty_zero():
    data = book_data()
    reservation = data["reservations"][0]
    reservation.update(status="settled", settled_at="2026-11-02T00:00:00Z", settled_microwon="0")
    with pytest.raises(ValidationError):
        book(data)
    data["entries"][0].update(charge_status="estimated", cost_microwon="0")
    with pytest.raises(ValidationError):
        book(data)
    data["entries"][0].update(charge_status="confirmed", cost_microwon="1")
    with pytest.raises(ValidationError):
        book(data)
    reservation["settled_microwon"] = "1"
    assert book(data).reservations[0].status == "settled"
    data["entries"] = []
    reservation["settled_microwon"] = "0"
    assert us.assess_budget(book(data), "0").used_microwon == "30000000000"


def test_result_model_rejects_self_contradiction():
    result = us.assess_budget(book(book_data()), "0").model_dump()
    for change in [
        {"remaining_microwon": "0"},
        {"used_microwon": "0"},
        {"overrun_microwon": "1"},
        {"allowed": False},
        {"allowed": 1},
        {"limit_microwon": "100000000001"},
    ]:
        with pytest.raises(ValidationError):
            us.BudgetAssessment.model_validate({**result, **change})


def test_usage_book_tuple_frozen_and_json_roundtrip():
    validated = book(book_data())
    assert isinstance(validated.entries, tuple) and isinstance(
        validated.reservations[0].pricing_snapshot_ids, tuple
    )
    with pytest.raises(ValidationError):
        validated.entries[0].cost_microwon = "0"
    assert us.UsageBook.model_validate_json(validated.model_dump_json()) == validated


def test_estimated_and_unknown_costs_above_hold_still_count():
    data = book_data()
    for status in ["unknown", "estimated"]:
        data["entries"][0].update(charge_status=status, cost_microwon="70000000000")
        assert us.assess_budget(book(data), "0").used_microwon == "100000000000"
        assert not us.assess_budget(book(data), "1").allowed


@pytest.mark.parametrize(
    "change",
    [
        {"settled_at": "2026-10-01T00:00:00Z"},
        {"settled_microwon": "0"},
        {"status": "settled"},
        {"status": "settled", "settled_at": "2026-09-01T00:00:00Z", "settled_microwon": "0"},
        {"pricing_snapshot_ids": []},
    ],
)
def test_reservation_rejects_settlement_shape_and_order(change):
    data = book_data()
    data["reservations"][0].update(change)
    with pytest.raises(ValidationError):
        book(data)


def test_leap_february_full_month_and_seoul_boundary():
    data = book_data()
    period = {"start_date": "2024-02-01", "end_date": "2024-02-29"}
    data["window"]["period"] = period
    data["reservations"][0].update(period=period, created_at="2024-01-31T15:00:00Z")
    data["pricing_snapshots"][0]["captured_at"] = "2024-01-31T14:59:59Z"
    assert book(data)
    data["reservations"][0]["created_at"] = "2024-02-29T15:00:00Z"
    with pytest.raises(ValidationError):
        book(data)
