"""Strict shared values for execution, canvas and supplied usage contracts."""

import re
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    UUID4,
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)

from .sources import NonBlank as SourceNonBlank

__all__ = ["MoneyMicrowon", "NonBlank"]

NonBlank = Annotated[SourceNonBlank, Field(strict=True)]

MAX_SAFE_INT = 2**53 - 1
SafeCount = Annotated[int, Field(strict=True, ge=0, le=MAX_SAFE_INT)]
SafePositive = Annotated[int, Field(strict=True, ge=1, le=MAX_SAFE_INT)]
UniqueIds = Annotated[tuple[UUID4, ...], AfterValidator(lambda ids: unique_ids(ids))]
NonemptyIds = Annotated[UniqueIds, Field(min_length=1)]
MultipleIds = Annotated[UniqueIds, Field(min_length=2)]


def unique_ids(ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
    if len(ids) != len(set(ids)):
        raise ValueError("IDs must be unique")
    return ids


def _instant_input(value: object) -> object:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt ]", value):
        return value
    raise ValueError("instant must be an aware datetime or ISO datetime string")


def _utc(value: datetime) -> datetime:
    try:
        return value.astimezone(UTC)
    except (OverflowError, ValueError) as error:
        raise ValueError("instant is outside the UTC datetime range") from error


UtcInstant = Annotated[AwareDatetime, BeforeValidator(_instant_input), AfterValidator(_utc)]


def _money(value: str) -> str:
    if not re.fullmatch(r"0|[1-9][0-9]*", value):
        raise ValueError("money must be an exact nonnegative ASCII integer string")
    return value


MoneyMicrowon = Annotated[
    str,
    StringConstraints(strict=True, max_length=128, pattern=r"^(0|[1-9][0-9]*)$"),
    AfterValidator(_money),
]


def _decimal(value: str) -> str:
    if not re.fullmatch(r"(0|[1-9][0-9]*)(\.[0-9]+)?", value):
        raise ValueError("price must be an exact nonnegative ASCII decimal string")
    return value


PriceDecimal = Annotated[
    str,
    StringConstraints(strict=True, max_length=128, pattern=r"^(0|[1-9][0-9]*)(\.[0-9]+)?$"),
    AfterValidator(_decimal),
]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VersionedContract(ContractModel):
    schema_version: Literal[1] = 1

    @field_validator("schema_version", mode="before")
    @classmethod
    def strict_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("schema_version must be an integer")
        return value


def index_records[T: BaseModel](records: tuple[T, ...], field: str) -> dict[UUID, T]:
    result: dict[UUID, T] = {}
    for record in records:
        identity: UUID = getattr(record, field)
        if identity in result:
            raise ValueError(f"{field} must be unique")
        result[identity] = record
    return result


def require_model[T: BaseModel](value: T, model: type[T]) -> T:
    if not isinstance(value, model):
        raise ValueError(f"validated {model.__name__} required")
    return value


def require_safe_cursor(value: object) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SAFE_INT:
        raise ValueError("cursor must be a nonnegative safe integer")
    return value
