"""Explicit operator CLI: offline validation by default, no automatic migrations."""

import argparse
import json
import os
import sys
from collections.abc import Sequence
from typing import NoReturn

from sqlalchemy import create_engine

from .operator_security import private_engine_lifecycle, read_private_file
from .provisioning import (
    MAX_PLAN_BYTES,
    ProvisioningError,
    ProvisioningPlan,
    apply_plan,
    check_database,
    parse_plan,
    validate_database_url,
    validate_plan,
)


class _ArgumentError(ValueError):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _ArgumentError("Invalid provisioning arguments")


def _read_plan(path: str) -> ProvisioningPlan:
    try:
        return parse_plan(read_private_file(path, MAX_PLAN_BYTES))
    except Exception:
        raise ProvisioningError("Unable to read provisioning plan") from None


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(
        prog="workspace-provision",
        description="Validate a private workspace plan.",
        allow_abbrev=False,
    )
    parser.add_argument("plan", metavar="PRIVATE_PLAN")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--check-database", action="store_true", help="Check the database read-only."
    )
    modes.add_argument("--apply", action="store_true", help="Register the plan in one transaction.")
    try:
        args = parser.parse_args(argv)
    except _ArgumentError:
        print("Invalid provisioning arguments", file=sys.stderr)
        return 2
    try:
        plan = _read_plan(args.plan)
        if not args.apply and not args.check_database:
            result = validate_plan(plan)
        else:
            database_url = os.environ.get("ISSUEDIGEST_DATABASE_URL")
            if not database_url:
                raise ProvisioningError("Explicit database URL required")
            url = validate_database_url(database_url, plan)
            engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=False)
            with private_engine_lifecycle(engine):
                result = apply_plan(engine, plan) if args.apply else check_database(engine, plan)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("Unable to provision workspace", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
