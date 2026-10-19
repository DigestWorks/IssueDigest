"""Explicit private, reproducible lexical retrieval evaluation; no writes or model calls."""

import json
import re
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import Annotated, Literal, Self
from uuid import UUID

from issuedigest_domain import build_search_projection
from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import Connection, Engine, select, text
from sqlalchemy.engine import URL

from .operator_security import reject_json_constant, unique_json_object
from .public_briefing_cli import validate_database_url as _validate_url
from .repository import EvidenceRepository, _digest, _payload
from .research_retrieval import RETRIEVAL_PROFILE, question_terms, retrieve_snapshot_ids
from .schema import evidence_snapshots
from .search import _manifest, _unit_values
from .search_schema import projections, units

MAX_JOB_BYTES = 256 * 1024
SnapshotIDs = Annotated[tuple[UUID4, ...], Field(min_length=1, max_length=50)]
Family = Annotated[tuple[UUID4, ...], Field(min_length=1, max_length=10)]


class _PrivateModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid", hide_input_in_errors=True)


class EvaluationCase(_PrivateModel):
    case_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$", repr=False)
    question: str = Field(min_length=1, max_length=1500, repr=False)
    expected_families: Annotated[tuple[Family, ...], Field(max_length=5)] = Field(repr=False)
    no_match: bool

    @model_validator(mode="after")
    def valid_gold(self) -> Self:
        members = [identity for family in self.expected_families for identity in family]
        if (
            not self.question.strip()
            or self.no_match != (len(self.expected_families) == 0)
            or len(set(members)) != len(members)
        ):
            raise ValueError("Invalid gold")
        return self


class EvaluationJob(_PrivateModel):
    schema_version: Literal[1]
    expected_database: str = Field(repr=False)
    workspace_id: UUID4 = Field(repr=False)
    corpus_snapshot_ids: SnapshotIDs = Field(repr=False)
    cases: Annotated[tuple[EvaluationCase, ...], Field(min_length=1, max_length=40)] = Field(
        repr=False
    )

    @field_validator("schema_version", mode="before")
    @classmethod
    def integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("Invalid version")
        return value

    @field_validator("expected_database")
    @classmethod
    def database_identifier(cls, value: str) -> str:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", value, flags=re.ASCII) is None:
            raise ValueError("Invalid database")
        return value

    @model_validator(mode="after")
    def valid_scope(self) -> Self:
        corpus = set(self.corpus_snapshot_ids)
        if (
            len(corpus) != len(self.corpus_snapshot_ids)
            or len({case.case_id for case in self.cases}) != len(self.cases)
            or any(
                identity not in corpus
                for case in self.cases
                for family in case.expected_families
                for identity in family
            )
        ):
            raise ValueError("Invalid scope")
        return self


class SnapshotFingerprint(_PrivateModel):
    snapshot_id: UUID4 = Field(repr=False)
    canonical_sha256: str
    projection_sha256: str
    projection_profile: str


class CaseResult(_PrivateModel):
    case: EvaluationCase = Field(repr=False)
    terms: tuple[str, ...] = Field(repr=False)
    ranked_snapshot_ids: tuple[UUID4, ...] = Field(repr=False)
    # One rank per gold member, in declared family/member order; None means absent.
    family_ranks: tuple[tuple[int | None, ...], ...] = Field(repr=False)
    found_families: int
    family_recall_at_5: float | None
    hit_at_1: bool | None
    all_required_at_5: bool | None
    negative_no_match: bool | None


class EvaluationReport(_PrivateModel):
    schema_version: Literal[1] = 1
    retrieval_profile: str
    job: EvaluationJob = Field(repr=False)
    job_sha256: str
    question_gold_sha256: str
    declared_corpus_sha256: str
    corpus_sha256: str
    fingerprints: tuple[SnapshotFingerprint, ...] = Field(repr=False)
    cases: tuple[CaseResult, ...] = Field(repr=False)
    summary: dict[str, int | float | None]


def _job_data(raw: bytes) -> object:
    """Decode bounded operator JSON without ambiguous keys or non-finite constants."""
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_JOB_BYTES:
        raise ValueError("Invalid size")
    data = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=unique_json_object,
        parse_constant=reject_json_constant,
    )
    return data


def parse_job(raw: bytes) -> EvaluationJob:
    """Only bounded raw bytes are accepted, including at the SDK evaluation boundary."""
    try:
        return EvaluationJob.model_validate_json(json.dumps(_job_data(raw), allow_nan=False))
    except Exception:
        raise ValueError("Unable to validate retrieval evaluation job") from None


def validate_database_url(value: str | URL, job: EvaluationJob) -> URL:
    """Reuse operator URL guards and require the explicitly declared database name."""
    url = _validate_url(
        value.render_as_string(hide_password=False) if isinstance(value, URL) else value
    )
    if url.database != job.expected_database:
        raise ValueError("Unable to verify retrieval evaluation database")
    return url


def _fingerprints(conn: Connection, job: EvaluationJob) -> tuple[SnapshotFingerprint, ...]:
    actual = tuple(
        conn.scalars(
            select(evidence_snapshots.c.snapshot_id)
            .where(evidence_snapshots.c.workspace_id == job.workspace_id)
            .order_by(evidence_snapshots.c.snapshot_id)
            .limit(51)
        )
    )
    if set(actual) != set(job.corpus_snapshot_ids):
        raise ValueError("Invalid corpus")
    result = []
    for identity in actual:
        bundle = EvidenceRepository._load(conn, job.workspace_id, identity)
        if bundle is None:
            raise ValueError("Missing canonical evidence")
        projection = build_search_projection(bundle)
        manifest = _manifest(bundle, identity, projection)
        stored = (
            conn.execute(
                select(projections).where(
                    projections.c.workspace_id == job.workspace_id,
                    projections.c.snapshot_id == identity,
                )
            )
            .mappings()
            .one_or_none()
        )
        stored_units = (
            conn.execute(
                select(units)
                .where(units.c.workspace_id == job.workspace_id, units.c.snapshot_id == identity)
                .order_by(units.c.ordinal)
            )
            .mappings()
            .all()
        )
        if (
            stored is None
            or dict(stored) != manifest
            or [dict(unit) for unit in stored_units]
            != [_unit_values(job.workspace_id, identity, unit) for unit in projection.units]
        ):
            raise ValueError("Invalid projection")
        result.append(
            SnapshotFingerprint(
                snapshot_id=identity,
                canonical_sha256=manifest["canonical_sha256"],
                projection_sha256=manifest["projection_sha256"],
                projection_profile=projection.profile,
            )
        )
    return tuple(result)


def _case_result(conn: Connection, job: EvaluationJob, case: EvaluationCase) -> CaseResult:
    terms = question_terms(case.question)
    ranked = retrieve_snapshot_ids(conn, job.workspace_id, terms)
    return _ranked_case_result(job, case, terms, ranked)


def _ranked_case_result(
    job: EvaluationJob, case: EvaluationCase, terms: tuple[str, ...], ranked: tuple[UUID, ...]
) -> CaseResult:
    """Validate runtime ranks and measure gold families without repairing search output."""
    if (
        type(ranked) is not tuple
        or len(ranked) > 5
        or len(set(ranked)) != len(ranked)
        or any(identity not in job.corpus_snapshot_ids for identity in ranked)
    ):
        raise ValueError("Invalid retrieval result")
    ranks = {identity: rank for rank, identity in enumerate(ranked, 1)}
    families = tuple(
        tuple(ranks.get(member) for member in family) for family in case.expected_families
    )
    found = sum(any(rank is not None for rank in family) for family in families)
    return CaseResult(
        case=case,
        terms=terms,
        ranked_snapshot_ids=ranked,
        family_ranks=families,
        found_families=found,
        family_recall_at_5=None if case.no_match else found / len(families),
        hit_at_1=None if case.no_match else any(1 in family for family in families),
        all_required_at_5=None if case.no_match else found == len(families),
        negative_no_match=(not ranked) if case.no_match else None,
    )


def evaluate(engine: Engine, raw: bytes) -> EvaluationReport:
    """Evaluate all cases in one read-only REPEATABLE READ transaction, or fail wholly."""
    try:
        job = parse_job(raw)
        with _evaluation_connection(engine, job) as conn:
            fingerprints = _fingerprints(conn, job)
            cases = tuple(_case_result(conn, job, case) for case in job.cases)
        summary = _summary(cases)
        return EvaluationReport(
            retrieval_profile=RETRIEVAL_PROFILE,
            job=job,
            job_sha256=_digest(_payload(job)),
            question_gold_sha256=_digest([_payload(case) for case in job.cases]),
            declared_corpus_sha256=_digest(sorted(map(str, job.corpus_snapshot_ids))),
            corpus_sha256=_digest([_payload(fp) for fp in fingerprints]),
            fingerprints=fingerprints,
            cases=cases,
            summary=summary,
        )
    except Exception:
        raise ValueError("Unable to evaluate retrieval") from None


def _summary(cases: Sequence[CaseResult]) -> dict[str, int | float | None]:
    """Use the existing positive/negative case denominators for either search path."""
    positive = [case for case in cases if not case.case.no_match]
    negative = [case for case in cases if case.case.no_match]
    summary: dict[str, int | float | None] = {
        "cases": len(cases),
        "positive_cases": len(positive),
        "negative_cases": len(negative),
        "hit_at_1": sum(bool(c.hit_at_1) for c in positive) / len(positive) if positive else None,
        "macro_family_recall_at_5": (
            sum(c.family_recall_at_5 or 0 for c in positive) / len(positive) if positive else None
        ),
        "all_required_at_5": (
            sum(bool(c.all_required_at_5) for c in positive) / len(positive) if positive else None
        ),
        "negative_no_match": (
            sum(bool(c.negative_no_match) for c in negative) / len(negative) if negative else None
        ),
    }
    return summary


@contextmanager
def _evaluation_connection(engine: Engine, job: EvaluationJob) -> Iterator[Connection]:
    """Verify target identity and hold one read-only repeatable snapshot for all cases."""
    validate_database_url(engine.url, job)
    if engine.dialect.name != "postgresql" or engine.dialect.driver != "psycopg":
        raise ValueError("Invalid engine")
    with engine.connect().execution_options(
        isolation_level="REPEATABLE READ", postgresql_readonly=True
    ) as conn:
        with conn.begin():
            target = conn.execute(
                text(
                    "SELECT current_database(), version(), "
                    "current_setting('transaction_isolation'), "
                    "current_setting('transaction_read_only')"
                )
            ).one()
            if (
                target[0] != job.expected_database
                or not target[1].startswith("PostgreSQL ")
                or target[2:] != ("repeatable read", "on")
            ):
                raise ValueError("Invalid database")
            yield conn
