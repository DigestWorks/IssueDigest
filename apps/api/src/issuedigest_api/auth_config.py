"""Explicit trusted OAuth configuration; no dotenv or credential discovery."""

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Self, TypeGuard
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url


class RuntimeConfigurationError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("Invalid runtime configuration")


def visible_ascii(value: object, maximum: int) -> TypeGuard[str]:
    return (
        isinstance(value, str)
        and 1 <= len(value) <= maximum
        and all(33 <= ord(char) <= 126 for char in value)
    )


@dataclass(frozen=True)
class AuthConfig:
    database_url: str = field(repr=False)
    public_origin: str
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)

    def __post_init__(self) -> None:
        try:
            if not visible_ascii(self.public_origin, 2048):
                raise ValueError
            if any(char in self.public_origin for char in "\\%?#"):
                raise ValueError
            parsed = urlsplit(self.public_origin)
            if (
                parsed.scheme != "https"
                or parsed.path
                or parsed.username is not None
                or parsed.password is not None
                or not parsed.hostname
                or parsed.netloc != self.public_origin.removeprefix("https://")
                or re.fullmatch(
                    r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*(?::[0-9]{1,5})?",
                    parsed.netloc,
                )
                is None
                or (parsed.port is not None and not 1 <= parsed.port <= 65535)
            ):
                raise ValueError
            if not visible_ascii(self.client_id, 256) or not visible_ascii(self.client_secret, 512):
                raise ValueError
            if not visible_ascii(self.database_url, 4096):
                raise ValueError
            if make_url(self.database_url).drivername != "postgresql+psycopg":
                raise ValueError
        except Exception:
            raise RuntimeConfigurationError() from None

    @property
    def callback_url(self) -> str:
        return self.public_origin + "/api/v1/auth/google/callback"

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> Self:
        try:
            return cls(
                *(
                    environment[key]
                    for key in (
                        "ISSUEDIGEST_DATABASE_URL",
                        "ISSUEDIGEST_PUBLIC_ORIGIN",
                        "ISSUEDIGEST_GOOGLE_CLIENT_ID",
                        "ISSUEDIGEST_GOOGLE_CLIENT_SECRET",
                    )
                )
            )
        except Exception:
            raise RuntimeConfigurationError() from None
