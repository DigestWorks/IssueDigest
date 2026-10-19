"""Explicit private operator policy capture, preparation and bounded journal commands."""

import json
import os
import re
import sys
from collections.abc import Sequence
from datetime import date, datetime

from issuedigest_connectors import (
    MAX_POLICY_CAPTURE_BYTES,
    MAX_POLICY_DISCOVERY_BYTES,
    capture_policy,
    discover_policy,
    parse_policy_discovery,
    policy_candidates,
    serialize_policy_capture,
    serialize_policy_discovery,
)
from issuedigest_storage.operator_security import private_engine_lifecycle
from issuedigest_storage.provisioning import MAX_PLAN_BYTES, parse_plan
from issuedigest_storage.public_briefing_cli import validate_database_url
from sqlalchemy import create_engine

from .cli import _ArgumentError, _Parser
from .files import check_private_output, read_private, write_private
from .policy_candidates import build_policy_candidate_report
from .policy_changes import compare_policy_captures
from .policy_collection import (
    MAX_POLICY_COLLECTION_JOB_BYTES,
    parse_policy_collection_job,
    policy_collection_status,
    poll_policy_collection,
)
from .policy_intake import (
    MAX_POLICY_INTAKE_APPROVAL_BYTES,
    intake_policy_capture,
    parse_policy_intake_approval,
)
from .policy_job import MAX_POLICY_JOB_BYTES, parse_policy_job
from .policy_prepare import prepare_policy_plan


def main(argv: Sequence[str] | None = None) -> int:
    parser = _Parser(prog="issuedigest-policy", allow_abbrev=False)
    commands = parser.add_subparsers(dest="operation", required=True, parser_class=_Parser)
    discover = commands.add_parser("discover", allow_abbrev=False)
    discover.add_argument("collected_at", metavar="AWARE_ISO_TIME")
    discover.add_argument("output", metavar="PRIVATE_NEW_DISCOVERY")
    capture = commands.add_parser("capture", allow_abbrev=False)
    capture.add_argument("discovery", metavar="PRIVATE_DISCOVERY")
    capture.add_argument("collected_at", metavar="AWARE_ISO_TIME")
    capture.add_argument("output", metavar="PRIVATE_NEW_CAPTURE")
    capture.add_argument("news_ids", nargs="+", metavar="EXPLICIT_ARTICLE_ID")
    compare = commands.add_parser("compare", allow_abbrev=False)
    compare.add_argument("capture", metavar="PRIVATE_CAPTURE")
    compare.add_argument("output", metavar="PRIVATE_NEW_OUTPUT")
    compare.add_argument("--previous", metavar="PRIVATE_CAPTURE")
    candidates = commands.add_parser("candidates", allow_abbrev=False)
    candidates.add_argument("discovery", metavar="PRIVATE_DISCOVERY")
    candidates.add_argument("since", metavar="YYYY-MM-DD")
    candidates.add_argument("through", metavar="YYYY-MM-DD")
    candidates.add_argument("output", metavar="PRIVATE_NEW_REPORT")
    candidates.add_argument("--previous", metavar="PRIVATE_DISCOVERY")
    prepare = commands.add_parser("prepare", allow_abbrev=False)
    prepare.add_argument("job", metavar="PRIVATE_APPROVED_JOB")
    prepare.add_argument("capture", metavar="PRIVATE_CAPTURE")
    prepare.add_argument("base", metavar="PRIVATE_BASE_PLAN")
    prepare.add_argument("output", metavar="PRIVATE_NEW_OUTPUT")
    prepare.add_argument("--output-kind", choices=("plan", "presentations"), default="plan")
    intake = commands.add_parser("intake", allow_abbrev=False)
    intake.add_argument("approval", metavar="PRIVATE_APPROVAL")
    intake_mode = intake.add_mutually_exclusive_group(required=True)
    intake_mode.add_argument("--check", action="store_true")
    intake_mode.add_argument("--apply", action="store_true")
    for operation in ("poll", "status"):
        command = commands.add_parser(operation, allow_abbrev=False)
        command.add_argument("job", metavar="PRIVATE_COLLECTION_JOB")
    try:
        args = parser.parse_args(argv)
    except _ArgumentError:
        print("Invalid policy arguments", file=sys.stderr)
        return 2
    try:
        if args.operation == "intake":
            return _intake_command(args.approval, apply=args.apply)
        if args.operation in {"poll", "status"}:
            return _collection_command(args.operation, args.job)
        check_private_output(args.output)
        if args.operation == "discover":
            discovery = discover_policy(collected_at=datetime.fromisoformat(args.collected_at))
            raw = serialize_policy_discovery(discovery)
            summary = {
                "schema_version": 1,
                "status": "discovered",
                "requests": 1,
                "candidates": len(policy_candidates(discovery)),
            }
        elif args.operation == "capture":
            discovery = parse_policy_discovery(
                read_private(args.discovery, MAX_POLICY_DISCOVERY_BYTES)
            )
            ids = tuple(args.news_ids)
            found = {candidate.news_id for candidate in policy_candidates(discovery)}
            if not 1 <= len(ids) <= 2 or len(ids) != len(set(ids)) or not set(ids) <= found:
                raise ValueError("Explicit discovered articles required")
            article_capture = capture_policy(
                ids, collected_at=datetime.fromisoformat(args.collected_at)
            )
            raw = serialize_policy_capture(article_capture)
            summary = {
                "schema_version": 1,
                "status": "captured",
                "requests": len(ids),
                "sources": len(ids),
            }
        elif args.operation == "candidates":
            if any(
                re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None
                for value in (args.since, args.through)
            ):
                raise ValueError("Invalid candidate dates")
            candidate_report = build_policy_candidate_report(
                read_private(args.discovery, MAX_POLICY_DISCOVERY_BYTES),
                since=date.fromisoformat(args.since),
                through=date.fromisoformat(args.through),
                previous_raw=read_private(args.previous, MAX_POLICY_DISCOVERY_BYTES)
                if args.previous is not None
                else None,
            )
            raw = candidate_report.model_dump_json(warnings="error").encode("utf-8")
            summary = {
                "schema_version": 1,
                "status": "candidates_reported",
                "candidates": sum(e.status != "not_observed" for e in candidate_report.entries),
                **{
                    status: sum(e.status == status for e in candidate_report.entries)
                    for status in ("new", "unchanged", "metadata_changed", "not_observed")
                },
            }
        elif args.operation == "compare":
            report = compare_policy_captures(
                read_private(args.capture, MAX_POLICY_CAPTURE_BYTES),
                previous_raw=read_private(args.previous, MAX_POLICY_CAPTURE_BYTES)
                if args.previous is not None
                else None,
            )
            raw = report.model_dump_json(warnings="error").encode("utf-8")
            summary = {
                "schema_version": 1,
                "status": "compared",
                **{
                    status: sum(source.status == status for source in report.sources)
                    for status in ("new", "changed", "unchanged", "not_observed")
                },
            }
        else:
            job = parse_policy_job(read_private(args.job, MAX_POLICY_JOB_BYTES))
            result = prepare_policy_plan(
                job,
                read_private(args.capture, MAX_POLICY_CAPTURE_BYTES),
                parse_plan(read_private(args.base, MAX_PLAN_BYTES)),
            )
            raw = (
                result.plan.model_dump_json(warnings="error").encode("utf-8")
                if args.output_kind == "plan"
                else json.dumps(
                    [p.model_dump(mode="json") for p in result.presentations],
                    ensure_ascii=False,
                    allow_nan=False,
                ).encode("utf-8")
            )
            summary = {
                "schema_version": 1,
                "status": "prepared",
                "sources": len(job.sources),
                "snapshots": len(result.plan.snapshots),
                "citations": sum(len(s.citations) for s in job.sources),
            }
        write_private(args.output, raw)
        print(json.dumps(summary, sort_keys=True))
        return 0
    except Exception:
        print("Unable to complete policy operation", file=sys.stderr)
        return 1


def _collection_command(operation: str, path: str) -> int:
    config = parse_policy_collection_job(read_private(path, MAX_POLICY_COLLECTION_JOB_BYTES))
    url = validate_database_url(os.environ.get("ISSUEDIGEST_DATABASE_URL", ""))
    if url.database != config.expected_database:
        raise ValueError("Invalid collection database")
    engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=False)
    with private_engine_lifecycle(engine):
        if operation == "poll":
            result = poll_policy_collection(engine, config)
            # An explicit allowlist prevents repository identifiers from becoming CLI output.
            summary = result.model_dump(
                mode="json",
                include={
                    "schema_version",
                    "outcome",
                    "failure_code",
                    "new",
                    "changed",
                    "unchanged",
                    "started_at",
                    "finished_at",
                },
            )
            exit_code = 1 if result.outcome == "failed" else 0
        else:
            state = policy_collection_status(engine, config)
            summary = state.model_dump(
                mode="json",
                include={
                    "schema_version": True,
                    "attempt_count": True,
                    "age_seconds": True,
                    "stale": True,
                    "latest": {"sequence", "state", "started_at", "finished_at", "failure_code"},
                    "last_success": {
                        "sequence",
                        "state",
                        "started_at",
                        "finished_at",
                        "failure_code",
                    },
                },
            )
            exit_code = 0
    # No output is published until connection cleanup and pool disposal succeed.
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    return exit_code


def _intake_command(path: str, *, apply: bool) -> int:
    approval = parse_policy_intake_approval(read_private(path, MAX_POLICY_INTAKE_APPROVAL_BYTES))
    url = validate_database_url(os.environ.get("ISSUEDIGEST_DATABASE_URL", ""))
    if url.database != approval.collection.expected_database:
        raise ValueError("Invalid intake database")
    engine = create_engine(url, hide_parameters=True, echo=False, pool_pre_ping=False)
    with private_engine_lifecycle(engine):
        result = intake_policy_capture(engine, approval, apply=apply)
        summary = result.model_dump(
            mode="json",
            include={
                "schema_version",
                "outcome",
                "sources",
                "new_versions",
                "reused_versions",
                "receipts_created",
            },
        )
    print(json.dumps(summary, sort_keys=True, allow_nan=False))
    return 0
