"""Explicit operator CLI: offline validation by default, no automatic migrations."""

import argparse
import json
import os
import stat
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import NoReturn

from sqlalchemy import create_engine

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
        target = Path(path)
        if not target.is_absolute() or len(target.parts) < 2:
            raise ValueError("Absolute private file required")
        # Anchor each directory descriptor so neither parent nor file symlinks are followed.
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        directory = os.open("/", directory_flags)
        try:
            for part in target.parts[1:-1]:
                child = os.open(part, directory_flags, dir_fd=directory)
                os.close(directory)
                directory = child
            # Nonblocking prevents a raced FIFO from hanging before the fstat guard.
            fd = os.open(
                target.parts[-1],
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                dir_fd=directory,
            )
        finally:
            os.close(directory)
        with os.fdopen(fd, "rb") as file:
            info = os.fstat(file.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) not in {0o400, 0o600}
                or info.st_size > MAX_PLAN_BYTES
            ):
                raise ValueError("Private regular file required")
            raw = file.read(MAX_PLAN_BYTES + 1)
        return parse_plan(raw)
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
            try:
                result = apply_plan(engine, plan) if args.apply else check_database(engine, plan)
            finally:
                engine.dispose()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("Unable to provision workspace", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
