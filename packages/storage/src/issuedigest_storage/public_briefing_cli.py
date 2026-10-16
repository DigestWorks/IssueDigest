"""Offline full-plan review hash, then explicit trusted publication/check/withdrawal."""

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from typing import NoReturn

from issuedigest_domain.public_briefings import MAX_PLAN_BYTES, PublicBriefingPlan, plan_hash
from sqlalchemy import create_engine
from sqlalchemy.engine import URL, make_url

from .operator_security import (
    private_engine_lifecycle,
    read_private_file,
    reject_json_constant,
    unique_json_object,
)
from .public_briefings import PublicBriefingRepository


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise ValueError("Invalid public briefing arguments")


def parse_plan(raw: bytes) -> PublicBriefingPlan:
    try:
        if len(raw) > MAX_PLAN_BYTES:
            raise ValueError("Plan exceeds bounds")
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=unique_json_object,
            parse_constant=reject_json_constant,
        )
        return PublicBriefingPlan.model_validate_json(json.dumps(data, allow_nan=False))
    except Exception:
        raise ValueError("Unable to validate public briefing plan") from None


def validate_database_url(value: str) -> URL:
    try:
        url = make_url(value)
        if (
            url.drivername != "postgresql+psycopg"
            or url.query
            or url.database is None
            or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", url.database) is None
            or not url.host
        ):
            raise ValueError("Explicit PostgreSQL target required")
        return url
    except Exception:
        raise ValueError("Invalid public briefing database configuration") from None


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(
        prog="public-briefing",
        allow_abbrev=False,
        description=(
            "Review the complete validated plan offline. plan_sha256 is SHA256 of "
            "sorted compact UTF-8 JSON of the full validated plan, including defaults "
            "and UTC-normalized times. Review all content and individual source rights "
            "before supplying that digest to an explicit write."
        ),
    )
    parser.add_argument("plan", metavar="ABSOLUTE_PRIVATE_PLAN")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-database", action="store_true")
    modes.add_argument("--apply", action="store_true")
    modes.add_argument("--withdraw", action="store_true")
    parser.add_argument("--reviewed-sha256", metavar="FULL_PLAN_SHA256")
    try:
        args = parser.parse_args(argv)
    except ValueError:
        print("Invalid public briefing arguments", file=sys.stderr)
        return 2
    try:
        plan = parse_plan(read_private_file(args.plan, MAX_PLAN_BYTES))
        digest = plan_hash(plan)
        if args.apply or args.withdraw:
            if args.reviewed_sha256 != digest:
                raise ValueError("Exact reviewed publication hash required")
        elif args.reviewed_sha256 is not None:
            raise ValueError("Review hash is only used for explicit writes")
        result: dict[str, str] = {"status": "validated", "plan_sha256": digest}
        if args.apply or args.withdraw or args.check_database:
            url = validate_database_url(os.environ.get("ISSUEDIGEST_DATABASE_URL", ""))
            engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=False)
            with private_engine_lifecycle(engine):
                repository = PublicBriefingRepository(engine)
                if args.check_database:
                    result = repository.check(plan)
                elif args.withdraw:
                    repository.withdraw(plan, reviewed_sha256=digest)
                    result["status"] = "withdrawn"
                else:
                    detail = repository.publish(plan, reviewed_sha256=digest)
                    result = {
                        "status": "published",
                        "plan_sha256": digest,
                        "content_sha256": detail.content_sha256,
                    }
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print("Unable to operate public briefing", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
