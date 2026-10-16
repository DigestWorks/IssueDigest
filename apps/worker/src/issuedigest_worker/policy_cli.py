"""Explicit private operator discovery/capture and offline preparation; no DB commands."""

import json
import sys
from collections.abc import Sequence
from datetime import datetime

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
from issuedigest_storage.provisioning import MAX_PLAN_BYTES, parse_plan

from .cli import _ArgumentError, _Parser
from .files import check_private_output, read_private, write_private
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
    prepare = commands.add_parser("prepare", allow_abbrev=False)
    prepare.add_argument("job", metavar="PRIVATE_APPROVED_JOB")
    prepare.add_argument("capture", metavar="PRIVATE_CAPTURE")
    prepare.add_argument("base", metavar="PRIVATE_BASE_PLAN")
    prepare.add_argument("output", metavar="PRIVATE_NEW_OUTPUT")
    prepare.add_argument("--output-kind", choices=("plan", "presentations"), default="plan")
    try:
        args = parser.parse_args(argv)
    except _ArgumentError:
        print("Invalid policy arguments", file=sys.stderr)
        return 2
    try:
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
