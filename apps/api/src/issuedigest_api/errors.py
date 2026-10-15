"""Typed JSON bodies for fixed protected errors and sanitized UUID path validation."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceAuthenticationError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: Literal["Authentication required"]


class EvidenceNotFoundError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: Literal["Evidence not found"]


class EvidenceUnavailableError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: Literal["Evidence service unavailable"]


class EvidencePathValidationDetail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    type: str
    loc: tuple[Literal["path", "query"], Literal["workspace_id", "snapshot_id", "limit"]]
    msg: Literal["Invalid UUID4 path parameter", "Invalid catalog limit"]


class EvidencePathValidationError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: list[EvidencePathValidationDetail] = Field(min_length=1)


class AuthUnavailableError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: Literal["Authentication service unavailable"]


class OriginDeniedError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: Literal["Request origin denied"]


class EvidenceSearchRequestError(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    detail: Literal["Invalid evidence search request"]
