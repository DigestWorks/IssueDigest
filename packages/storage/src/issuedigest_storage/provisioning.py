"""Private operator plans and transactional registration; no public signup contract."""

import json
import re
from typing import Annotated, Literal, Self

from issuedigest_domain import EvidenceBundle
from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Connection, Engine, text
from sqlalchemy.engine import URL, make_url

from .auth_schema import auth_identity_invites
from .oauth import OAuthRepository, _email
from .operator_security import reject_json_constant as _reject_constant
from .operator_security import unique_json_object as _unique_object
from .repository import EvidenceRepository
from .schema import (
    citations,
    document_versions,
    evidence_snapshots,
    outbox,
    parsed_representations,
    snapshot_citations,
    source_documents,
)

MAX_PLAN_BYTES = 8 * 1024 * 1024
GOOGLE_ISSUER = "https://accounts.google.com"
_REQUIRED_TABLES = (
    source_documents,
    document_versions,
    parsed_representations,
    citations,
    evidence_snapshots,
    snapshot_citations,
    outbox,
    auth_identity_invites,
)


class ProvisioningError(ValueError):
    """Fixed operation errors, without private input or underlying exception text."""


class _PrivateModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class ProvisioningInvite(_PrivateModel):
    user_id: UUID4 = Field(repr=False)
    email: str = Field(repr=False)
    role: Literal["viewer", "editor", "owner"] = Field(repr=False)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _email(value)


class ProvisioningSnapshot(_PrivateModel):
    snapshot_id: UUID4 = Field(repr=False)
    bundle: EvidenceBundle = Field(repr=False)


class ProvisioningPlan(_PrivateModel):
    schema_version: Literal[1]
    expected_database: str = Field(repr=False)
    workspace_id: UUID4 = Field(repr=False)
    invites: Annotated[tuple[ProvisioningInvite, ...], Field(min_length=1, max_length=2)] = Field(
        repr=False
    )
    snapshots: Annotated[tuple[ProvisioningSnapshot, ...], Field(min_length=1, max_length=50)] = (
        Field(repr=False)
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid plan version")
        return value

    @field_validator("expected_database")
    @classmethod
    def database_identifier(cls, value: str) -> str:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value, flags=re.ASCII) is None:
            raise ValueError("Invalid database identifier")
        return value

    @model_validator(mode="after")
    def unique_and_consistent(self) -> Self:
        if (
            len({invite.email for invite in self.invites}) != len(self.invites)
            or len({invite.user_id for invite in self.invites}) != len(self.invites)
            or len({snapshot.snapshot_id for snapshot in self.snapshots}) != len(self.snapshots)
            or any(
                snapshot.bundle.document.workspace_id != self.workspace_id
                for snapshot in self.snapshots
            )
        ):
            raise ValueError("Invalid plan relationships")
        return self


def parse_plan(raw: str | bytes) -> ProvisioningPlan:
    """Validate unambiguous bounded UTF-8 JSON, never echoing private input."""
    try:
        encoded = raw.encode("utf-8") if isinstance(raw, str) else raw
        if not isinstance(encoded, bytes) or len(encoded) > MAX_PLAN_BYTES:
            raise ValueError("Invalid plan size")
        decoded = encoded.decode("utf-8")
        data = json.loads(
            decoded, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
        return ProvisioningPlan.model_validate_json(json.dumps(data, allow_nan=False))
    except Exception:
        raise ProvisioningError("Unable to validate provisioning plan") from None


def _revalidate(plan: ProvisioningPlan) -> ProvisioningPlan:
    try:
        if not isinstance(plan, ProvisioningPlan):
            raise ValueError("Invalid plan")
        # JSON revalidation catches model_construct/model_copy on all nested models.
        return parse_plan(plan.model_dump_json(warnings="error"))
    except Exception:
        raise ProvisioningError("Unable to validate provisioning plan") from None


def _summary(plan: ProvisioningPlan, status: str) -> dict[str, int | str]:
    return {
        "schema_version": 1,
        "status": status,
        "invites": len(plan.invites),
        "snapshots": len(plan.snapshots),
    }


def validate_plan(plan: ProvisioningPlan) -> dict[str, int | str]:
    """Pure validation with bounded counts only; no authorization/readiness claim."""
    return _summary(_revalidate(plan), "validated")


def validate_database_url(database_url: str | URL, plan: ProvisioningPlan) -> URL:
    """Reject wrong/overridden targets before creating or opening an engine."""
    try:
        url = make_url(database_url)
        if (
            url.drivername != "postgresql+psycopg"
            or url.database != plan.expected_database
            or url.query
        ):
            raise ValueError("Invalid target")
        return url
    except Exception:
        raise ProvisioningError("Unable to verify provisioning database") from None


def _verify_target(connection: Connection, plan: ProvisioningPlan, *, readonly: bool) -> None:
    row = connection.execute(
        text(
            "SELECT current_database(), version(), "
            "current_setting('transaction_isolation'), current_setting('transaction_read_only')"
        )
    ).one()
    if (
        row[0] != plan.expected_database
        or not isinstance(row[1], str)
        or not row[1].startswith("PostgreSQL ")
        or row[2] != "read committed"
        or row[3] != ("on" if readonly else "off")
    ):
        raise ProvisioningError("Unable to verify provisioning database")
    for table in _REQUIRED_TABLES:
        columns = connection.execute(
            text(
                "SELECT a.attname FROM pg_catalog.pg_class AS c "
                "JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace "
                "JOIN pg_catalog.pg_attribute AS a ON a.attrelid = c.oid "
                "WHERE n.nspname = 'public' AND c.relname = :table AND c.relkind = 'r' "
                "AND c.oid = pg_catalog.to_regclass(:table) "
                "AND a.attnum > 0 AND NOT a.attisdropped"
            ),
            {"table": table.name},
        ).scalars()
        if not set(table.c.keys()).issubset(set(columns)):
            raise ProvisioningError("Unable to verify provisioning database")


def _verify_engine_target(engine: Engine, plan: ProvisioningPlan) -> None:
    validate_database_url(engine.url, plan)
    if engine.dialect.name != "postgresql" or engine.dialect.driver != "psycopg":
        raise ProvisioningError("Unable to verify provisioning database")


def check_database(engine: Engine, plan: ProvisioningPlan) -> dict[str, int | str]:
    """Check one dedicated read-only transaction using SELECTs; never migrate."""
    try:
        validated = _revalidate(plan)
        _verify_engine_target(engine, validated)
        with engine.connect().execution_options(
            isolation_level="READ COMMITTED", postgresql_readonly=True
        ) as connection:
            with connection.begin():
                _verify_target(connection, validated, readonly=True)
        return _summary(validated, "database_checked")
    except Exception:
        raise ProvisioningError("Unable to check provisioning database") from None


def apply_plan(engine: Engine, plan: ProvisioningPlan) -> dict[str, int | str]:
    """Register all evidence and Google reservations, reporting only after commit."""
    try:
        validated = _revalidate(plan)
        _verify_engine_target(engine, validated)
        snapshots_created = invites_created = 0
        with engine.connect().execution_options(
            isolation_level="READ COMMITTED", postgresql_readonly=False
        ) as connection:
            with connection.begin():
                _verify_target(connection, validated, readonly=False)
                for snapshot in validated.snapshots:
                    snapshots_created += EvidenceRepository._save(
                        connection, snapshot.snapshot_id, snapshot.bundle
                    )
                for invite in validated.invites:
                    invites_created += OAuthRepository._register_invite(
                        connection,
                        GOOGLE_ISSUER,
                        invite.email,
                        invite.user_id,
                        validated.workspace_id,
                        invite.role,
                    )
        return {
            "schema_version": 1,
            "status": "applied",
            "invites_created": invites_created,
            "invites_unchanged": len(validated.invites) - invites_created,
            "snapshots_created": snapshots_created,
            "snapshots_unchanged": len(validated.snapshots) - snapshots_created,
        }
    except Exception:
        # The boundary includes context-manager commit and uncertain-commit failures.
        raise ProvisioningError("Unable to apply provisioning plan") from None
