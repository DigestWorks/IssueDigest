"""Public process-status contracts; these do not claim storage or worker readiness."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Liveness(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"]


class ServiceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Literal["issuedigest-api"]
    api_version: Literal["v1"]
    status: Literal["ok"]
