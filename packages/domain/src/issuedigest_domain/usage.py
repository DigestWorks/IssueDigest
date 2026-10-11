"""Supplied pricing and monthly usage snapshots; integer budget assessment only."""

from calendar import monthrange
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo

from pydantic import UUID4, Field, TypeAdapter, model_validator

from .contract_values import (
    ContractModel,
    MoneyMicrowon,
    NonBlank,
    NonemptyIds,
    PriceDecimal,
    SafeCount,
    SafePositive,
    UtcInstant,
    index_records,
    require_model,
)
from .observations import DateInterval

MAX_MONTHLY_MICROWON = 100000000000


def _validate_limit(value: str) -> None:
    if not 0 < int(value) <= MAX_MONTHLY_MICROWON:
        raise ValueError("monthly limit must be positive and at most 100000 KRW")


class PricingSnapshot(ContractModel):
    snapshot_id: UUID4
    provider: NonBlank
    operation: NonBlank
    model: NonBlank | None
    pricing_version: NonBlank
    exchange_rate_version: NonBlank
    captured_at: UtcInstant
    currency: Literal["KRW", "USD"]
    unit_price: PriceDecimal
    unit_quantity: SafePositive
    fx_krw_per_currency: PriceDecimal

    @model_validator(mode="after")
    def valid_exchange_rate(self) -> Self:
        # String inspection is exact and independent of Decimal context precision.
        whole, _, fraction = self.fx_krw_per_currency.partition(".")
        if not any(digit in "123456789" for digit in whole + fraction):
            raise ValueError("exchange rate must be positive")
        if self.currency == "KRW" and (whole != "1" or fraction.strip("0")):
            raise ValueError("KRW exchange rate must be exactly 1")
        return self


class BudgetWindow(ContractModel):
    workspace_id: UUID4
    period: DateInterval
    timezone: Literal["Asia/Seoul"] = "Asia/Seoul"
    limit_microwon: MoneyMicrowon
    committed_other_cost_microwon: MoneyMicrowon

    @model_validator(mode="after")
    def full_month_and_limit(self) -> Self:
        start, end = self.period.start_date, self.period.end_date
        if (
            start.day != 1
            or (start.year, start.month) != (end.year, end.month)
            or end.day != monthrange(start.year, start.month)[1]
        ):
            raise ValueError("budget period must be a complete calendar month")
        _validate_limit(self.limit_microwon)
        return self


class UsageReservation(ContractModel):
    reservation_id: UUID4
    workspace_id: UUID4
    run_id: UUID4
    period: DateInterval
    reserved_microwon: MoneyMicrowon
    status: Literal["held", "settled"]
    pricing_snapshot_ids: NonemptyIds
    created_at: UtcInstant
    settled_at: UtcInstant | None
    settled_microwon: MoneyMicrowon | None

    @model_validator(mode="after")
    def consistent_settlement(self) -> Self:
        if self.status == "held":
            if self.settled_at is not None or self.settled_microwon is not None:
                raise ValueError("held reservation cannot have settlement")
        elif (
            self.settled_at is None
            or self.settled_microwon is None
            or self.settled_at < self.created_at
        ):
            raise ValueError("settled reservation needs ordered time and actual cost")
        return self


class UsageEntry(ContractModel):
    entry_id: UUID4
    workspace_id: UUID4
    run_id: UUID4
    reservation_id: UUID4
    attempt_id: UUID4
    pricing_snapshot_id: UUID4
    provider: NonBlank
    operation: NonBlank
    model: NonBlank | None
    input_tokens: SafeCount | None
    output_tokens: SafeCount | None
    charge_status: Literal["confirmed", "estimated", "unknown", "not_charged"]
    cost_microwon: MoneyMicrowon | None
    provider_usage_ref: NonBlank | None

    @model_validator(mode="after")
    def consistent_charge(self) -> Self:
        if self.charge_status in {"confirmed", "estimated"} and self.cost_microwon is None:
            raise ValueError("confirmed/estimated charge requires cost")
        if self.charge_status == "not_charged" and self.cost_microwon != "0":
            raise ValueError("not_charged requires exact cost '0'")
        return self


class UsageBook(ContractModel):
    window: BudgetWindow
    pricing_snapshots: tuple[PricingSnapshot, ...]
    reservations: tuple[UsageReservation, ...]
    entries: tuple[UsageEntry, ...]

    @model_validator(mode="after")
    def consistent_book(self) -> Self:
        prices = index_records(self.pricing_snapshots, "snapshot_id")
        reservations = index_records(self.reservations, "reservation_id")
        index_records(self.entries, "entry_id")
        index_records(self.entries, "attempt_id")
        index_records(self.reservations, "run_id")
        for reservation in self.reservations:
            if (
                reservation.workspace_id != self.window.workspace_id
                or reservation.period != self.window.period
            ):
                raise ValueError("reservation workspace/month differs from budget window")
            try:
                local_date = reservation.created_at.astimezone(ZoneInfo("Asia/Seoul")).date()
            except (ValueError, OverflowError) as error:
                raise ValueError("reservation outside representable Seoul date") from error
            if not reservation.period.start_date <= local_date <= reservation.period.end_date:
                raise ValueError("reservation created outside its Seoul calendar month")
            for identity in reservation.pricing_snapshot_ids:
                if identity not in prices or prices[identity].captured_at > reservation.created_at:
                    raise ValueError("reservation price must exist and predate reservation")
        for entry in self.entries:
            if entry.workspace_id != self.window.workspace_id:
                raise ValueError("entry workspace differs from budget window")
            if entry.reservation_id not in reservations or entry.pricing_snapshot_id not in prices:
                raise ValueError("unknown reservation/price entry reference")
            reservation = reservations[entry.reservation_id]
            price = prices[entry.pricing_snapshot_id]
            if (
                entry.run_id != reservation.run_id
                or entry.pricing_snapshot_id not in reservation.pricing_snapshot_ids
            ):
                raise ValueError("entry run/price differs from reservation")
            if (entry.provider, entry.operation, entry.model) != (
                price.provider,
                price.operation,
                price.model,
            ):
                raise ValueError("entry provider/operation/model differs from price")
        for reservation in self.reservations:
            if reservation.status == "settled":
                entries = tuple(
                    entry
                    for entry in self.entries
                    if entry.reservation_id == reservation.reservation_id
                )
                if any(entry.charge_status in {"unknown", "estimated"} for entry in entries):
                    raise ValueError("settled reservation must contain only known final charges")
                total = sum(int(entry.cost_microwon or "0") for entry in entries)
                if int(reservation.settled_microwon or "0") != total:
                    raise ValueError("settled actual cost differs from known entry sum")
        return self


class BudgetAssessment(ContractModel):
    limit_microwon: MoneyMicrowon
    used_microwon: MoneyMicrowon
    requested_microwon: MoneyMicrowon
    remaining_microwon: MoneyMicrowon
    overrun_microwon: MoneyMicrowon
    allowed: Annotated[bool, Field(strict=True)]
    policy_version: Literal["issuedigest-budget-v1"] = "issuedigest-budget-v1"

    @model_validator(mode="after")
    def consistent_arithmetic(self) -> Self:
        _validate_limit(self.limit_microwon)
        limit, used, requested = (
            int(self.limit_microwon),
            int(self.used_microwon),
            int(self.requested_microwon),
        )
        if (int(self.remaining_microwon), int(self.overrun_microwon), self.allowed) != (
            max(limit - used, 0),
            max(used - limit, 0),
            used + requested <= limit,
        ):
            raise ValueError("budget result contradicts its integer arithmetic")
        return self


def assess_budget(book: UsageBook, requested_microwon: str) -> BudgetAssessment:
    """Assess all supplied monthly costs, preserving uncertain holds and overruns."""
    require_model(book, UsageBook)
    requested = TypeAdapter(MoneyMicrowon).validate_python(requested_microwon)
    used = int(book.window.committed_other_cost_microwon)
    for reservation in book.reservations:
        if reservation.status == "settled":
            used += int(reservation.settled_microwon or "0")
        else:
            known = sum(
                int(entry.cost_microwon or "0")
                for entry in book.entries
                if entry.reservation_id == reservation.reservation_id
            )
            used += max(int(reservation.reserved_microwon), known)
    limit = int(book.window.limit_microwon)
    return BudgetAssessment(
        limit_microwon=str(limit),
        used_microwon=str(used),
        requested_microwon=requested,
        remaining_microwon=str(max(limit - used, 0)),
        overrun_microwon=str(max(used - limit, 0)),
        allowed=used + int(requested) <= limit,
    )
